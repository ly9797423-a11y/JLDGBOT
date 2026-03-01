import logging
import sqlite3
import asyncio
import re
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Set
import os
import json
import random
import string
from telethon import TelegramClient, events, Button
from telethon.tl.functions.channels import InviteToChannelRequest, EditBannedRequest
from telethon.tl.types import InputPeerUser, InputPeerChannel, InputPeerChat, ChatBannedRights
from telethon.errors import UserPrivacyRestrictedError, FloodWaitError, ChatAdminRequiredError, UserNotParticipantError
import aiofiles
import hashlib

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Bot configuration
BOT_TOKEN = "8699966374:AAGCCGehxTQzGbEkBxIe7L3vecLPcvzGrHg"
API_ID = 20459452  # استخدم API ID الخاص بك
API_HASH = "973e61dee6c9e51a8d02cc7927dcc389"  # استخدم API HASH الخاص بك
ADMIN_IDS = [6615860762, 6130994941]

# Initialize bot
bot = TelegramClient('bot', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

# Database setup
conn = sqlite3.connect('funding_bot.db', check_same_thread=False)
cursor = conn.cursor()

# Create tables
cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    first_name TEXT,
    points INTEGER DEFAULT 0,
    referrals INTEGER DEFAULT 0,
    referrer_id INTEGER,
    banned INTEGER DEFAULT 0,
    joined_date TIMESTAMP,
    total_fundings INTEGER DEFAULT 0,
    total_spent_points INTEGER DEFAULT 0
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS referral_links (
    user_id INTEGER PRIMARY KEY,
    link TEXT UNIQUE,
    clicks INTEGER DEFAULT 0
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS phone_numbers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    phone TEXT UNIQUE,
    added_date TIMESTAMP,
    used INTEGER DEFAULT 0,
    used_for TEXT
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS fundings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    chat_id TEXT,
    chat_title TEXT,
    members_count INTEGER,
    cost_points INTEGER,
    status TEXT DEFAULT 'pending',
    start_date TIMESTAMP,
    completed_members INTEGER DEFAULT 0,
    remaining_members INTEGER,
    current_phone_index INTEGER DEFAULT 0
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS support (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS channel_link (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    link TEXT UNIQUE
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS required_channels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_link TEXT UNIQUE,
    channel_username TEXT
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS banned_users (
    user_id INTEGER PRIMARY KEY
)
''')

# Insert default settings
default_settings = [
    ('welcome_message', 'مرحباً بك في بوت التمويل 🚀'),
    ('referral_reward', '10'),
    ('member_cost', '8'),
    ('min_withdraw', '100'),
    ('max_withdraw', '10000')
]

for key, value in default_settings:
    cursor.execute('INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)', (key, value))

conn.commit()

# Helper functions
def get_setting(key: str) -> str:
    cursor.execute('SELECT value FROM settings WHERE key = ?', (key,))
    result = cursor.fetchone()
    return result[0] if result else ''

def update_setting(key: str, value: str):
    cursor.execute('UPDATE settings SET value = ? WHERE key = ?', (value, key))
    conn.commit()

def get_user_points(user_id: int) -> int:
    cursor.execute('SELECT points FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    return result[0] if result else 0

def update_user_points(user_id: int, points: int, operation: str = 'add'):
    if operation == 'add':
        cursor.execute('UPDATE users SET points = points + ? WHERE user_id = ?', (points, user_id))
    else:
        cursor.execute('UPDATE users SET points = points - ? WHERE user_id = ?', (points, user_id))
    conn.commit()

def get_or_create_user(user_id: int, username: str = '', first_name: str = '', referrer_id: int = None):
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    user = cursor.fetchone()
    
    if not user:
        cursor.execute('''
            INSERT INTO users (user_id, username, first_name, points, joined_date)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, username, first_name, 0, datetime.now()))
        conn.commit()
        
        # Handle referral
        if referrer_id and referrer_id != user_id:
            cursor.execute('SELECT * FROM users WHERE user_id = ?', (referrer_id,))
            if cursor.fetchone():
                cursor.execute('UPDATE users SET referrer_id = ? WHERE user_id = ?', (referrer_id, user_id))
                conn.commit()
                
                # Add points to referrer
                reward = int(get_setting('referral_reward'))
                update_user_points(referrer_id, reward, 'add')
                cursor.execute('UPDATE users SET referrals = referrals + 1 WHERE user_id = ?', (referrer_id,))
                conn.commit()
    
    return user

def generate_referral_link(user_id: int) -> str:
    bot_username = (bot.loop.run_until_complete(bot.get_me())).username
    link = f"https://t.me/{bot_username}?start={user_id}"
    
    cursor.execute('INSERT OR REPLACE INTO referral_links (user_id, link) VALUES (?, ?)', (user_id, link))
    conn.commit()
    
    return link

def is_banned(user_id: int) -> bool:
    if user_id in ADMIN_IDS:
        return False
    cursor.execute('SELECT 1 FROM banned_users WHERE user_id = ?', (user_id,))
    return cursor.fetchone() is not None

def check_membership(func):
    async def wrapper(event):
        user_id = event.sender_id
        
        # Skip for admins
        if user_id in ADMIN_IDS:
            return await func(event)
        
        # Check if user is banned
        if is_banned(user_id):
            await event.respond("🚫 لقد تم حظرك من استخدام البوت.")
            return
        
        # Check required channels
        cursor.execute('SELECT channel_link, channel_username FROM required_channels')
        channels = cursor.fetchall()
        
        if channels:
            not_joined = []
            for channel_link, channel_username in channels:
                try:
                    if channel_username:
                        entity = await bot.get_entity(channel_username)
                    else:
                        # Extract username from link
                        parts = channel_link.split('/')
                        username = parts[-1]
                        entity = await bot.get_entity(username)
                    
                    participant = await bot.get_permissions(entity, user_id)
                    if not participant:
                        not_joined.append(channel_link)
                except:
                    not_joined.append(channel_link)
            
            if not_joined:
                buttons = []
                for link in not_joined:
                    buttons.append([Button.url('📢 اشتراك', link)])
                buttons.append([Button.inline('✅ تحقق من الاشتراك', b'check_sub')])
                
                await event.respond(
                    "⚠️ يجب الاشتراك في القنوات التالية لاستخدام البوت:",
                    buttons=buttons
                )
                return
        
        return await func(event)
    
    return wrapper

# User interface
async def get_main_menu(user_id: int) -> Tuple[str, List]:
    cursor.execute('SELECT username, first_name, points, referrals FROM users WHERE user_id = ?', (user_id,))
    user_data = cursor.fetchone()
    
    if not user_data:
        username, first_name, points, referrals = '', '', 0, 0
    else:
        _, username, first_name, points, referrals, *_ = user_data
    
    welcome = get_setting('welcome_message')
    
    text = f"{welcome}\n\n"
    text += f"👤 المستخدم: {first_name or username or str(user_id)}\n"
    text += f"🆔 الايدي: {user_id}\n"
    text += f"⭐ نقاطك: {points}\n"
    text += f"👥 referrals: {referrals}\n"
    
    buttons = [
        [Button.inline("💰 تجميع النقاط", b'earn_points')],
        [Button.inline("🚀 تمويل مشتركين", b'fund_members')],
        [Button.inline("📊 تمويلاتي", b'my_fundings')],
        [Button.inline("📈 احصائياتي", b'my_stats')],
        [Button.inline("🆘 الدعم الفني", b'support')],
        [Button.inline("📢 قناة البوت", b'bot_channel')]
    ]
    
    return text, buttons

@bot.on(events.NewMessage(pattern='/start(?: (.+))?'))
@check_membership
async def start_handler(event):
    user_id = event.sender_id
    username = event.sender.username or ''
    first_name = event.sender.first_name or ''
    
    referrer_id = None
    if event.pattern_match and event.pattern_match.group(1):
        try:
            referrer_id = int(event.pattern_match.group(1))
        except:
            pass
    
    get_or_create_user(user_id, username, first_name, referrer_id)
    
    text, buttons = await get_main_menu(user_id)
    await event.respond(text, buttons=buttons)

@bot.on(events.CallbackQuery)
async def callback_handler(event):
    user_id = event.sender_id
    data = event.data.decode()
    
    if is_banned(user_id) and user_id not in ADMIN_IDS:
        await event.answer("🚫 لقد تم حظرك من استخدام البوت.", alert=True)
        return
    
    # Check subscription for inline buttons except check_sub
    if data != 'check_sub':
        cursor.execute('SELECT channel_link, channel_username FROM required_channels')
        channels = cursor.fetchall()
        
        if channels and user_id not in ADMIN_IDS:
            not_joined = []
            for channel_link, channel_username in channels:
                try:
                    if channel_username:
                        entity = await bot.get_entity(channel_username)
                    else:
                        parts = channel_link.split('/')
                        username = parts[-1]
                        entity = await bot.get_entity(username)
                    
                    participant = await bot.get_permissions(entity, user_id)
                    if not participant:
                        not_joined.append(channel_link)
                except:
                    not_joined.append(channel_link)
            
            if not_joined:
                buttons = []
                for link in not_joined:
                    buttons.append([Button.url('📢 اشتراك', link)])
                buttons.append([Button.inline('✅ تحقق من الاشتراك', b'check_sub')])
                
                await event.edit(
                    "⚠️ يجب الاشتراك في القنوات التالية لاستخدام البوت:",
                    buttons=buttons
                )
                return
    
    if data == 'check_sub':
        await start_handler(event)
        return
    
    if data == 'earn_points':
        await earn_points_handler(event)
    
    elif data == 'fund_members':
        await fund_members_handler(event)
    
    elif data == 'my_fundings':
        await my_fundings_handler(event)
    
    elif data == 'my_stats':
        await my_stats_handler(event)
    
    elif data == 'support':
        cursor.execute('SELECT username FROM support ORDER BY id DESC LIMIT 1')
        support = cursor.fetchone()
        if support:
            username = support[0].replace('@', '')
            await event.respond(f"🆘 للدعم الفني: @{username}")
        else:
            await event.respond("لا يوجد دعم فني حالياً.")
    
    elif data == 'bot_channel':
        cursor.execute('SELECT link FROM channel_link ORDER BY id DESC LIMIT 1')
        channel = cursor.fetchone()
        if channel:
            await event.respond(f"📢 قناة البوت: {channel[0]}")
        else:
            await event.respond("لا يوجد قناة للبوت حالياً.")
    
    elif data.startswith('cancel_funding_'):
        funding_id = int(data.split('_')[2])
        await cancel_funding(event, funding_id)
    
    # Admin panel handlers
    elif user_id in ADMIN_IDS:
        if data == 'admin_panel':
            await admin_panel_handler(event)
        
        elif data == 'admin_stats':
            await admin_stats_handler(event)
        
        elif data == 'admin_balance':
            await admin_balance_handler(event)
        
        elif data == 'admin_add_phones':
            await admin_add_phones_handler(event)
        
        elif data == 'admin_phones_list':
            await admin_phones_list_handler(event)
        
        elif data == 'admin_add_support':
            await admin_add_support_handler(event)
        
        elif data == 'admin_add_channel':
            await admin_add_channel_handler(event)
        
        elif data == 'admin_ban_user':
            await admin_ban_user_handler(event)
        
        elif data == 'admin_unban_user':
            await admin_unban_user_handler(event)
        
        elif data == 'admin_set_referral_reward':
            await admin_set_referral_reward_handler(event)
        
        elif data == 'admin_set_member_cost':
            await admin_set_member_cost_handler(event)
        
        elif data == 'admin_required_channels':
            await admin_required_channels_handler(event)
        
        elif data == 'admin_add_required_channel':
            await admin_add_required_channel_handler(event)
        
        elif data == 'admin_remove_required_channel':
            await admin_remove_required_channel_handler(event)
        
        elif data == 'admin_welcome_message':
            await admin_welcome_message_handler(event)
        
        elif data.startswith('process_funding_'):
            funding_id = int(data.split('_')[2])
            await process_funding_approval(event, funding_id)

async def earn_points_handler(event):
    user_id = event.sender_id
    link = generate_referral_link(user_id)
    
    cursor.execute('SELECT referrals FROM users WHERE user_id = ?', (user_id,))
    referrals = cursor.fetchone()[0]
    
    reward = get_setting('referral_reward')
    
    text = f"🔗 رابط الدعوة الخاص بك:\n{link}\n\n"
    text += f"👥 عدد من دعوتهم: {referrals}\n"
    text += f"💰 مكافأة كل دعوة: {reward} نقطة\n\n"
    text += "شارك الرابط مع أصدقائك، عندما ينضموا عبر رابطك ستحصل على النقاط!"
    
    buttons = [[Button.inline("🔙 العودة", b'back_to_main')]]
    await event.edit(text, buttons=buttons)

async def fund_members_handler(event):
    user_id = event.sender_id
    points = get_user_points(user_id)
    member_cost = int(get_setting('member_cost'))
    
    max_members = points // member_cost
    
    if max_members == 0:
        text = f"⚠️ ليس لديك نقاط كافية!\n"
        text += f"نقاطك الحالية: {points}\n"
        text += f"سعر العضو: {member_cost} نقطة\n"
        text += f"يمكنك شراء {max_members} عضو كحد أقصى\n\n"
        text += "💰 قم بتجميع النقاط أولاً من خلال رابط الدعوة."
        
        buttons = [
            [Button.inline("💰 تجميع النقاط", b'earn_points')],
            [Button.inline("🔙 العودة", b'back_to_main')]
        ]
        await event.edit(text, buttons=buttons)
        return
    
    text = f"🚀 مرحباً بك في قسم التمويل\n\n"
    text += f"نقاطك الحالية: {points}\n"
    text += f"سعر العضو الواحد: {member_cost} نقطة\n"
    text += f"يمكنك شراء حتى {max_members} عضو\n\n"
    text += "أرسل عدد الأعضاء الذي تريد تمويلهم:"
    
    # Set state for user
    async with bot.conversation(event.sender_id) as conv:
        try:
            response = await conv.get_response(timeout=60)
            count = int(response.text)
            
            total_cost = count * member_cost
            
            if total_cost > points:
                await event.respond(f"⚠️ نقاطك غير كافية! تحتاج {total_cost} نقطة ولديك {points} فقط.")
                return
            
            if count < 1 or count > max_members:
                await event.respond(f"⚠️ الرجاء إدخال عدد بين 1 و {max_members}")
                return
            
            await event.respond(f"التكلفة الإجمالية: {total_cost} نقطة\nأرسل رابط قناتك أو مجموعتك الآن:")
            
            link_response = await conv.get_response(timeout=60)
            chat_link = link_response.text.strip()
            
            # Extract chat info from link
            chat_username = None
            chat_id = None
            
            if 't.me/' in chat_link:
                parts = chat_link.split('/')
                username = parts[-1]
                try:
                    entity = await bot.get_entity(username)
                    chat_id = str(entity.id)
                    chat_username = username
                    chat_title = getattr(entity, 'title', username)
                    
                    # Check if bot is admin
                    try:
                        me = await bot.get_me()
                        permissions = await bot.get_permissions(entity, me.id)
                        if not permissions.is_admin:
                            await event.respond("⚠️ يجب أن تكون البوت أدمن في القناة أو المجموعة!")
                            return
                    except:
                        await event.respond("⚠️ يجب أن تكون البوت أدمن في القناة أو المجموعة!")
                        return
                    
                except Exception as e:
                    await event.respond(f"⚠️ خطأ في الرابط: {str(e)}")
                    return
            
            # Create funding record
            cursor.execute('''
                INSERT INTO fundings (user_id, chat_id, chat_title, members_count, cost_points, start_date, remaining_members)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, chat_id, chat_title, count, total_cost, datetime.now(), count))
            conn.commit()
            
            funding_id = cursor.lastrowid
            
            # Deduct points
            update_user_points(user_id, total_cost, 'subtract')
            
            # Notify admins
            for admin_id in ADMIN_IDS:
                try:
                    buttons = [
                        [Button.inline("✅ موافقة", f'process_funding_{funding_id}'.encode()),
                         Button.inline("❌ رفض", f'reject_funding_{funding_id}'.encode())]
                    ]
                    await bot.send_message(
                        admin_id,
                        f"🔔 طلب تمويل جديد\n"
                        f"👤 المستخدم: {user_id}\n"
                        f"📊 عدد الأعضاء: {count}\n"
                        f"💰 التكلفة: {total_cost} نقطة\n"
                        f"🔗 الرابط: {chat_link}\n"
                        f"🆔 معاملة: {funding_id}",
                        buttons=buttons
                    )
                except:
                    pass
            
            await event.respond(
                f"✅ تم استلام طلب التمويل!\n"
                f"عدد الأعضاء: {count}\n"
                f"التكلفة: {total_cost} نقطة\n"
                f"سيتم البدء بالتمويل قريباً بعد موافقة الإدارة."
            )
            
        except ValueError:
            await event.respond("⚠️ الرجاء إدخال رقم صحيح")
        except asyncio.TimeoutError:
            await event.respond("⏰ انتهت المهلة، الرجاء المحاولة مرة أخرى")

async def process_funding_approval(event, funding_id: int):
    if event.sender_id not in ADMIN_IDS:
        return
    
    cursor.execute('SELECT * FROM fundings WHERE id = ?', (funding_id,))
    funding = cursor.fetchone()
    
    if not funding:
        await event.answer("التمويل غير موجود", alert=True)
        return
    
    # Update status
    cursor.execute('UPDATE fundings SET status = "processing" WHERE id = ?', (funding_id,))
    conn.commit()
    
    await event.edit("✅ تم الموافقة على التمويل، جاري البدء...")
    
    # Start funding process
    asyncio.create_task(process_funding(funding_id))

async def process_funding(funding_id: int):
    cursor.execute('SELECT * FROM fundings WHERE id = ?', (funding_id,))
    funding = cursor.fetchone()
    
    if not funding:
        return
    
    user_id, chat_id, chat_title, members_count, cost_points, status, start_date, completed_members, remaining_members, current_phone_index = funding[1:]
    
    # Get phone numbers
    cursor.execute('SELECT phone FROM phone_numbers WHERE used = 0')
    phones = cursor.fetchall()
    
    if not phones and members_count > 0:
        # Use bot users as fallback
        cursor.execute('SELECT user_id FROM users WHERE user_id NOT IN (SELECT user_id FROM fundings WHERE status = "processing") LIMIT ?', (members_count,))
        bot_users = cursor.fetchall()
        
        if not bot_users:
            await notify_funding_complete(funding_id, "لا يوجد أرقام كافية للتمويل")
            return
        
        phones = [(str(user[0]),) for user in bot_users]
    
    if not phones:
        await notify_funding_complete(funding_id, "لا يوجد أرقام للتمويل")
        return
    
    try:
        # Get chat entity
        if str(chat_id).startswith('-100'):
            entity = InputPeerChannel(int(chat_id), 0)
        else:
            entity = await bot.get_entity(int(chat_id))
        
        added_count = 0
        for i, (phone,) in enumerate(phones[:members_count]):
            try:
                # Try to add as user
                user_id_to_add = int(phone) if phone.isdigit() else None
                
                if user_id_to_add:
                    try:
                        user_entity = await bot.get_entity(user_id_to_add)
                        await bot(InviteToChannelRequest(entity, [user_entity]))
                    except:
                        # Try alternative method
                        await bot.edit_permissions(entity, user_id_to_add, view_messages=True, send_messages=True)
                
                # Mark phone as used
                cursor.execute('UPDATE phone_numbers SET used = 1, used_for = ? WHERE phone = ?', (chat_id, phone))
                conn.commit()
                
                added_count += 1
                
                # Update progress
                cursor.execute('''
                    UPDATE fundings 
                    SET completed_members = ?, remaining_members = ?, current_phone_index = ?
                    WHERE id = ?
                ''', (added_count, members_count - added_count, i, funding_id))
                conn.commit()
                
                # Notify user every 10 members
                if added_count % 10 == 0:
                    try:
                        await bot.send_message(
                            user_id,
                            f"📊 تقدم التمويل:\n"
                            f"تم إضافة {added_count} من {members_count}\n"
                            f"المتبقي: {members_count - added_count}"
                        )
                    except:
                        pass
                
                # Small delay to avoid flood
                await asyncio.sleep(2)
                
            except FloodWaitError as e:
                logger.warning(f"Flood wait: {e.seconds} seconds")
                await asyncio.sleep(e.seconds)
            except Exception as e:
                logger.error(f"Error adding user {phone}: {e}")
                continue
        
        # Complete funding
        cursor.execute('UPDATE fundings SET status = "completed" WHERE id = ?', (funding_id,))
        conn.commit()
        
        # Notify user
        try:
            await bot.send_message(
                user_id,
                f"✅ تم اكتمال التمويل بنجاح!\n"
                f"تم إضافة {added_count} من {members_count} عضو"
            )
        except:
            pass
        
        # Notify admins
        for admin_id in ADMIN_IDS:
            try:
                await bot.send_message(
                    admin_id,
                    f"✅ اكتمل التمويل #{funding_id}\n"
                    f"تم إضافة {added_count} عضو"
                )
            except:
                pass
        
    except Exception as e:
        logger.error(f"Funding error: {e}")
        await notify_funding_complete(funding_id, f"خطأ: {str(e)}")

async def notify_funding_complete(funding_id: int, message: str):
    cursor.execute('SELECT user_id FROM fundings WHERE id = ?', (funding_id,))
    result = cursor.fetchone()
    if result:
        user_id = result[0]
        try:
            await bot.send_message(user_id, f"⚠️ {message}")
        except:
            pass

async def my_fundings_handler(event):
    user_id = event.sender_id
    
    cursor.execute('''
        SELECT id, chat_title, members_count, completed_members, status, start_date 
        FROM fundings 
        WHERE user_id = ? 
        ORDER BY start_date DESC 
        LIMIT 10
    ''', (user_id,))
    
    fundings = cursor.fetchall()
    
    if not fundings:
        text = "📊 لا يوجد لديك تمويلات سابقة"
        buttons = [[Button.inline("🔙 العودة", b'back_to_main')]]
        await event.edit(text, buttons=buttons)
        return
    
    text = "📊 آخر 10 تمويلات لك:\n\n"
    
    for funding in fundings:
        id, title, total, completed, status, date = funding
        status_emoji = {
            'pending': '⏳',
            'processing': '⚙️',
            'completed': '✅',
            'cancelled': '❌'
        }.get(status, '❓')
        
        text += f"{status_emoji} {title}\n"
        text += f"🆔 {id} | {total} عضو | تم {completed}\n"
        text += f"📅 {date[:10]}\n\n"
    
    buttons = [[Button.inline("🔙 العودة", b'back_to_main')]]
    await event.edit(text, buttons=buttons)

async def my_stats_handler(event):
    user_id = event.sender_id
    
    cursor.execute('''
        SELECT 
            COUNT(*) as total_fundings,
            SUM(members_count) as total_members,
            SUM(cost_points) as total_spent,
            MAX(members_count) as max_funding
        FROM fundings 
        WHERE user_id = ? AND status = 'completed'
    ''', (user_id,))
    
    stats = cursor.fetchone()
    
    cursor.execute('SELECT points, referrals FROM users WHERE user_id = ?', (user_id,))
    user_data = cursor.fetchone()
    points, referrals = user_data if user_data else (0, 0)
    
    total_fundings, total_members, total_spent, max_funding = stats if stats and stats[0] else (0, 0, 0, 0)
    
    text = "📈 احصائياتك:\n\n"
    text += f"⭐ النقاط الحالية: {points}\n"
    text += f"👥 عدد الدعوات: {referrals}\n"
    text += f"📊 عدد التمويلات: {total_fundings}\n"
    text += f"👥 أعضاء تم تمويلهم: {total_members or 0}\n"
    text += f"💰 نقاط منفقة: {total_spent or 0}\n"
    text += f"🏆 أكبر تمويل: {max_funding or 0} عضو"
    
    buttons = [[Button.inline("🔙 العودة", b'back_to_main')]]
    await event.edit(text, buttons=buttons)

# Admin panel handlers
async def admin_panel_handler(event):
    text = "🔧 لوحة التحكم\n\nاختر ما تريد:"
    
    buttons = [
        [Button.inline("📊 احصائيات البوت", b'admin_stats')],
        [Button.inline("💰 شحن/خصم رصيد", b'admin_balance')],
        [Button.inline("📱 اضافة ملف أرقام", b'admin_add_phones')],
        [Button.inline("📋 قائمة الأرقام", b'admin_phones_list')],
        [Button.inline("🆘 اضافة حساب دعم", b'admin_add_support')],
        [Button.inline("📢 اضافة رابط قناة", b'admin_add_channel')],
        [Button.inline("🚫 حظر مستخدم", b'admin_ban_user')],
        [Button.inline("✅ رفع حظر", b'admin_unban_user')],
        [Button.inline("💰 تغيير مكافأة الدعوة", b'admin_set_referral_reward')],
        [Button.inline("💵 تغيير سعر العضو", b'admin_set_member_cost')],
        [Button.inline("📢 الاشتراك الاجباري", b'admin_required_channels')],
        [Button.inline("✏️ تغيير رسالة الترحيب", b'admin_welcome_message')],
        [Button.inline("🔙 العودة", b'back_to_main')]
    ]
    
    await event.edit(text, buttons=buttons)

async def admin_stats_handler(event):
    # User stats
    cursor.execute('SELECT COUNT(*) FROM users')
    total_users = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM users WHERE joined_date > date("now", "-1 day")')
    new_users_today = cursor.fetchone()[0]
    
    # Points stats
    cursor.execute('SELECT SUM(points) FROM users')
    total_points = cursor.fetchone()[0] or 0
    
    # Funding stats
    cursor.execute('SELECT COUNT(*) FROM fundings')
    total_fundings = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM fundings WHERE status = "completed"')
    completed_fundings = cursor.fetchone()[0]
    
    cursor.execute('SELECT SUM(members_count) FROM fundings WHERE status = "completed"')
    total_members_added = cursor.fetchone()[0] or 0
    
    # Phone numbers
    cursor.execute('SELECT COUNT(*) FROM phone_numbers')
    total_phones = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM phone_numbers WHERE used = 0')
    available_phones = cursor.fetchone()[0]
    
    # Settings
    referral_reward = get_setting('referral_reward')
    member_cost = get_setting('member_cost')
    
    text = "📊 احصائيات البوت:\n\n"
    text += f"👥 المستخدمين:\n"
    text += f"الإجمالي: {total_users}\n"
    text += f"جدد اليوم: {new_users_today}\n\n"
    
    text += f"💰 النقاط:\n"
    text += f"إجمالي النقاط: {total_points}\n\n"
    
    text += f"📊 التمويلات:\n"
    text += f"الكل: {total_fundings}\n"
    text += f"مكتملة: {completed_fundings}\n"
    text += f"أعضاء تمت إضافتهم: {total_members_added}\n\n"
    
    text += f"📱 الأرقام:\n"
    text += f"الإجمالي: {total_phones}\n"
    text += f"المتاح: {available_phones}\n\n"
    
    text += f"⚙️ الإعدادات:\n"
    text += f"مكافأة الدعوة: {referral_reward}\n"
    text += f"سعر العضو: {member_cost}"
    
    buttons = [[Button.inline("🔙 العودة للوحة التحكم", b'admin_panel')]]
    await event.edit(text, buttons=buttons)

async def admin_balance_handler(event):
    async with bot.conversation(event.sender_id) as conv:
        await event.respond("أرسل ايدي المستخدم:")
        
        try:
            user_id_response = await conv.get_response(timeout=60)
            target_user_id = int(user_id_response.text.strip())
            
            # Check if user exists
            cursor.execute('SELECT points FROM users WHERE user_id = ?', (target_user_id,))
            user = cursor.fetchone()
            
            if not user:
                await event.respond("المستخدم غير موجود!")
                return
            
            current_points = user[0]
            
            await event.respond(f"نقاط المستخدم الحالية: {current_points}\nأرسل المبلغ (استخدم + للشحن و - للخصم مثل: +100 أو -50):")
            
            amount_response = await conv.get_response(timeout=60)
            amount_text = amount_response.text.strip()
            
            if amount_text.startswith('+'):
                amount = int(amount_text[1:])
                update_user_points(target_user_id, amount, 'add')
                operation = "شحن"
            elif amount_text.startswith('-'):
                amount = int(amount_text[1:])
                update_user_points(target_user_id, amount, 'subtract')
                operation = "خصم"
            else:
                await event.respond("صيغة غير صحيحة!")
                return
            
            cursor.execute('SELECT points FROM users WHERE user_id = ?', (target_user_id,))
            new_points = cursor.fetchone()[0]
            
            await event.respond(f"✅ تم {operation} {amount} نقطة\nالنقاط الجديدة: {new_points}")
            
            # Notify user
            try:
                await bot.send_message(
                    target_user_id,
                    f"💰 تم {operation} رصيدك بمقدار {amount} نقطة\nرصيدك الحالي: {new_points}"
                )
            except:
                pass
            
        except ValueError:
            await event.respond("الرجاء إدخال أرقام صحيحة")
        except asyncio.TimeoutError:
            await event.respond("انتهت المهلة")

async def admin_add_phones_handler(event):
    async with bot.conversation(event.sender_id) as conv:
        await event.respond("أرسل ملف الأرقام بصيغة TXT (كل رقم في سطر):")
        
        try:
            response = await conv.get_response(timeout=120)
            
            if response.document:
                # Download file
                file_path = await response.download_media()
                
                # Read file
                async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                    content = await f.read()
                
                # Extract phone numbers (basic pattern)
                numbers = re.findall(r'[\d\+\s\(\)\-]{7,}', content)
                
                # Clean numbers
                cleaned_numbers = []
                for num in numbers:
                    # Remove non-digits
                    clean = re.sub(r'\D', '', num)
                    if len(clean) >= 10 and len(clean) <= 15:
                        cleaned_numbers.append(clean)
                
                # Remove duplicates
                cleaned_numbers = list(set(cleaned_numbers))
                
                # Save to database
                added = 0
                skipped = 0
                
                for phone in cleaned_numbers:
                    try:
                        cursor.execute('INSERT OR IGNORE INTO phone_numbers (phone, added_date) VALUES (?, ?)', (phone, datetime.now()))
                        if cursor.rowcount > 0:
                            added += 1
                        else:
                            skipped += 1
                    except:
                        skipped += 1
                
                conn.commit()
                
                # Delete temp file
                os.remove(file_path)
                
                await event.respond(
                    f"✅ تمت المعالجة:\n"
                    f"تم إضافة {added} رقم\n"
                    f"تم تخطي {skipped} رقم (مكرر أو غير صالح)"
                )
            else:
                # Manual input
                numbers = response.text.strip().split('\n')
                
                added = 0
                skipped = 0
                
                for line in numbers:
                    phone = re.sub(r'\D', '', line.strip())
                    if phone and len(phone) >= 10 and len(phone) <= 15:
                        try:
                            cursor.execute('INSERT OR IGNORE INTO phone_numbers (phone, added_date) VALUES (?, ?)', (phone, datetime.now()))
                            if cursor.rowcount > 0:
                                added += 1
                            else:
                                skipped += 1
                        except:
                            skipped += 1
                
                conn.commit()
                
                await event.respond(f"✅ تم إضافة {added} رقم وتخطي {skipped}")
                
        except asyncio.TimeoutError:
            await event.respond("انتهت المهلة")

async def admin_phones_list_handler(event):
    cursor.execute('SELECT COUNT(*), SUM(CASE WHEN used = 0 THEN 1 ELSE 0 END) FROM phone_numbers')
    total, available = cursor.fetchone()
    
    cursor.execute('SELECT phone, used FROM phone_numbers ORDER BY added_date DESC LIMIT 20')
    recent = cursor.fetchall()
    
    text = f"📱 إحصائيات الأرقام:\n"
    text += f"الإجمالي: {total or 0}\n"
    text += f"المتاح: {available or 0}\n"
    text += f"المستخدم: {(total or 0) - (available or 0)}\n\n"
    
    text += "آخر 20 رقم:\n"
    for phone, used in recent:
        status = "✅ مستخدم" if used else "🆓 متاح"
        text += f"{phone} - {status}\n"
    
    buttons = [
        [Button.inline("🗑 حذف كل الأرقام المستخدمة", b'admin_delete_used_phones')],
        [Button.inline("🔙 العودة", b'admin_panel')]
    ]
    
    await event.edit(text, buttons=buttons)

async def admin_add_support_handler(event):
    async with bot.conversation(event.sender_id) as conv:
        await event.respond("أرسل يوزر الدعم الفني (مع @ أو بدون):")
        
        try:
            response = await conv.get_response(timeout=60)
            username = response.text.strip().replace('@', '')
            
            cursor.execute('INSERT OR REPLACE INTO support (username) VALUES (?)', (username,))
            conn.commit()
            
            await event.respond(f"✅ تم تعيين يوزر الدعم الفني: @{username}")
            
        except asyncio.TimeoutError:
            await event.respond("انتهت المهلة")

async def admin_add_channel_handler(event):
    async with bot.conversation(event.sender_id) as conv:
        await event.respond("أرسل رابط قناة البوت:")
        
        try:
            response = await conv.get_response(timeout=60)
            link = response.text.strip()
            
            cursor.execute('INSERT OR REPLACE INTO channel_link (link) VALUES (?)', (link,))
            conn.commit()
            
            await event.respond(f"✅ تم تعيين رابط القناة: {link}")
            
        except asyncio.TimeoutError:
            await event.respond("انتهت المهلة")

async def admin_ban_user_handler(event):
    async with bot.conversation(event.sender_id) as conv:
        await event.respond("أرسل ايدي المستخدم لحظره:")
        
        try:
            response = await conv.get_response(timeout=60)
            user_id = int(response.text.strip())
            
            if user_id in ADMIN_IDS:
                await event.respond("لا يمكن حظر الأدمن!")
                return
            
            cursor.execute('INSERT OR IGNORE INTO banned_users (user_id) VALUES (?)', (user_id,))
            conn.commit()
            
            await event.respond(f"✅ تم حظر المستخدم {user_id}")
            
        except ValueError:
            await event.respond("الرجاء إدخال ايدي صحيح")
        except asyncio.TimeoutError:
            await event.respond("انتهت المهلة")

async def admin_unban_user_handler(event):
    async with bot.conversation(event.sender_id) as conv:
        await event.respond("أرسل ايدي المستخدم لرفع الحظر:")
        
        try:
            response = await conv.get_response(timeout=60)
            user_id = int(response.text.strip())
            
            cursor.execute('DELETE FROM banned_users WHERE user_id = ?', (user_id,))
            conn.commit()
            
            await event.respond(f"✅ تم رفع الحظر عن المستخدم {user_id}")
            
        except ValueError:
            await event.respond("الرجاء إدخال ايدي صحيح")
        except asyncio.TimeoutError:
            await event.respond("انتهت المهلة")

async def admin_set_referral_reward_handler(event):
    async with bot.conversation(event.sender_id) as conv:
        await event.respond("أرسل عدد النقاط كمكافأة للدعوة:")
        
        try:
            response = await conv.get_response(timeout=60)
            reward = int(response.text.strip())
            
            update_setting('referral_reward', str(reward))
            
            await event.respond(f"✅ تم تعيين مكافأة الدعوة: {reward} نقطة")
            
        except ValueError:
            await event.respond("الرجاء إدخال رقم صحيح")
        except asyncio.TimeoutError:
            await event.respond("انتهت المهلة")

async def admin_set_member_cost_handler(event):
    async with bot.conversation(event.sender_id) as conv:
        await event.respond("أرسل سعر العضو الواحد بالنقاط:")
        
        try:
            response = await conv.get_response(timeout=60)
            cost = int(response.text.strip())
            
            update_setting('member_cost', str(cost))
            
            await event.respond(f"✅ تم تعيين سعر العضو: {cost} نقطة")
            
        except ValueError:
            await event.respond("الرجاء إدخال رقم صحيح")
        except asyncio.TimeoutError:
            await event.respond("انتهت المهلة")

async def admin_required_channels_handler(event):
    cursor.execute('SELECT channel_link FROM required_channels')
    channels = cursor.fetchall()
    
    text = "📢 قنوات الاشتراك الاجباري:\n\n"
    
    if channels:
        for i, (link,) in enumerate(channels, 1):
            text += f"{i}. {link}\n"
    else:
        text += "لا توجد قنوات مضافة حالياً"
    
    buttons = [
        [Button.inline("➕ اضافة قناة", b'admin_add_required_channel')],
        [Button.inline("➖ حذف قناة", b'admin_remove_required_channel')],
        [Button.inline("🔙 العودة", b'admin_panel')]
    ]
    
    await event.edit(text, buttons=buttons)

async def admin_add_required_channel_handler(event):
    async with bot.conversation(event.sender_id) as conv:
        await event.respond("أرسل رابط القناة:")
        
        try:
            response = await conv.get_response(timeout=60)
            link = response.text.strip()
            
            # Extract username from link if possible
            username = None
            if 't.me/' in link:
                parts = link.split('/')
                username = parts[-1]
            
            cursor.execute('INSERT OR IGNORE INTO required_channels (channel_link, channel_username) VALUES (?, ?)', (link, username))
            conn.commit()
            
            await event.respond(f"✅ تم اضافة القناة: {link}")
            
        except asyncio.TimeoutError:
            await event.respond("انتهت المهلة")

async def admin_remove_required_channel_handler(event):
    cursor.execute('SELECT id, channel_link FROM required_channels')
    channels = cursor.fetchall()
    
    if not channels:
        await event.respond("لا توجد قنوات مضافة")
        return
    
    text = "اختر القناة للحذف:\n\n"
    buttons = []
    
    for id, link in channels:
        text += f"🆔 {id}: {link}\n"
        buttons.append([Button.inline(f"حذف {link[:20]}...", f'delete_channel_{id}'.encode())])
    
    buttons.append([Button.inline("🔙 العودة", b'admin_panel')])
    
    await event.edit(text, buttons=buttons)

async def admin_welcome_message_handler(event):
    async with bot.conversation(event.sender_id) as conv:
        await event.respond("أرسل رسالة الترحيب الجديدة:")
        
        try:
            response = await conv.get_response(timeout=60)
            message = response.text.strip()
            
            update_setting('welcome_message', message)
            
            await event.respond(f"✅ تم تحديث رسالة الترحيب")
            
        except asyncio.TimeoutError:
            await event.respond("انتهت المهلة")

@bot.on(events.CallbackQuery(data=b'back_to_main'))
@check_membership
async def back_to_main(event):
    text, buttons = await get_main_menu(event.sender_id)
    await event.edit(text, buttons=buttons)

@bot.on(events.CallbackQuery(data=b'admin_delete_used_phones'))
async def delete_used_phones(event):
    if event.sender_id not in ADMIN_IDS:
        return
    
    cursor.execute('DELETE FROM phone_numbers WHERE used = 1')
    deleted = cursor.rowcount
    conn.commit()
    
    await event.answer(f"✅ تم حذف {deleted} رقم مستخدم", alert=True)
    await admin_phones_list_handler(event)

@bot.on(events.CallbackQuery(pattern=b'delete_channel_'))
async def delete_channel(event):
    if event.sender_id not in ADMIN_IDS:
        return
    
    channel_id = int(event.data.decode().split('_')[2])
    cursor.execute('DELETE FROM required_channels WHERE id = ?', (channel_id,))
    conn.commit()
    
    await event.answer("✅ تم حذف القناة", alert=True)
    await admin_required_channels_handler(event)

@bot.on(events.CallbackQuery(pattern=b'reject_funding_'))
async def reject_funding(event):
    if event.sender_id not in ADMIN_IDS:
        return
    
    funding_id = int(event.data.decode().split('_')[2])
    
    cursor.execute('SELECT user_id, cost_points FROM fundings WHERE id = ?', (funding_id,))
    funding = cursor.fetchone()
    
    if funding:
        user_id, cost = funding
        
        # Return points to user
        update_user_points(user_id, cost, 'add')
        
        # Update funding status
        cursor.execute('UPDATE fundings SET status = "cancelled" WHERE id = ?', (funding_id,))
        conn.commit()
        
        # Notify user
        try:
            await bot.send_message(
                user_id,
                f"❌ تم رفض طلب التمويل رقم {funding_id}\nتم إرجاع {cost} نقطة إلى رصيدك"
            )
        except:
            pass
    
    await event.edit("✅ تم رفض التمويل وإرجاع النقاط")

async def cancel_funding(event, funding_id: int):
    if event.sender_id not in ADMIN_IDS:
        return
    
    cursor.execute('SELECT user_id, cost_points, status FROM fundings WHERE id = ?', (funding_id,))
    funding = cursor.fetchone()
    
    if funding and funding[2] in ['pending', 'processing']:
        user_id, cost, _ = funding
        
        # Return points
        update_user_points(user_id, cost, 'add')
        
        # Update status
        cursor.execute('UPDATE fundings SET status = "cancelled" WHERE id = ?', (funding_id,))
        conn.commit()
        
        # Notify user
        try:
            await bot.send_message(
                user_id,
                f"⚠️ تم إلغاء تمويلك رقم {funding_id}\nتم إرجاع {cost} نقطة إلى رصيدك"
            )
        except:
            pass
        
        await event.answer("✅ تم إلغاء التمويل وإرجاع النقاط", alert=True)

async def main():
    print("🚀 Bot is starting...")
    print(f"Bot token: {BOT_TOKEN}")
    print(f"Admin IDs: {ADMIN_IDS}")
    
    await bot.run_until_disconnected()

if __name__ == '__main__':
    try:
        bot.loop.run_until_complete(main())
    except KeyboardInterrupt:
        print("Bot stopped by user")
    except Exception as e:
        logger.error(f"Error: {e}")
    finally:
        conn.close()
