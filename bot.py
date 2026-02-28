"""
بوت تمويل متكامل لتليجرام
المطور: وفقاً لمواصفات المشروع
الإصدار: 1.0
"""

import logging
import asyncio
import json
import os
import random
import string
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Union
from uuid import uuid4
from collections import defaultdict

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
)
from telegram.constants import ChatMemberStatus
import aiofiles

# ==================== إعدادات البوت ====================
TOKEN = "8699966374:AAGCCGehxTQzGbEkBxIe7L3vecLPcvzGrHg"
ADMIN_IDS = [6615860762, 6130994941]  # مديري البوت

# إعدادات التسجيل
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# ==================== قواعد البيانات المؤقتة (يمكن تحويلها لاحقًا إلى MongoDB) ====================

# قاعدة بيانات المستخدمين
users_db = {}  # user_id -> {id, username, points, invited_by, invites_count, banned, created_at, last_active}

# قاعدة بيانات القنوات المحظورة للاشتراك الإجباري
force_sub_channels = []  # قائمة معرفات القنوات

# إعدادات البوت
bot_settings = {
    "welcome_message": "🎉 مرحباً بك في بوت التمويل!\nيمكنك جمع النقاط وتمويل قنواتك.",
    "points_per_invite": 5,  # نقاط كل دعوة
    "points_per_member": 8,  # نقاط كل عضو عند التمويل
    "support_username": "support_bot",  # يوزر الدعم الفني
    "channel_link": "https://t.me/your_channel",  # رابط قناة البوت
}

# قاعدة بيانات ملفات الأرقام
numbers_files_db = {}  # file_id -> {name, numbers, used_numbers, created_at, added_by}

# قاعدة بيانات طلبات التمويل
funding_requests_db = {}  # request_id -> {user_id, chat_id, chat_link, members_count, cost, status, added_members, created_at}

# قاعدة بيانات روابط الدعوة
invite_links_db = {}  # user_id -> {link, created_at, uses_count}

# قاعدة بيانات المستخدمين المحظورين
banned_users = set()

# ==================== حالات المحادثة ====================
(
    ADD_NUMBERS_FILE,
    ADD_SUPPORT,
    ADD_CHANNEL_LINK,
    ADD_FORCE_CHANNEL,
    REMOVE_FORCE_CHANNEL,
    CHARGE_POINTS_STEP1,
    CHARGE_POINTS_STEP2,
    DEDUCT_POINTS_STEP1,
    DEDUCT_POINTS_STEP2,
    BAN_USER_STEP,
    UNBAN_USER_STEP,
    CHANGE_INVITE_REWARD_STEP,
    CHANGE_MEMBER_PRICE_STEP,
    FUNDING_STEP1,
    FUNDING_STEP2,
) = range(16)

# ==================== دوال مساعدة ====================

def generate_invite_link(user_id: int) -> str:
    """توليد رابط دعوة فريد للمستخدم"""
    unique_code = f"{user_id}_{uuid4().hex[:8]}"
    bot_username = "YourBotUsername"  # يجب تغييره إلى يوزر البوت الفعلي
    return f"https://t.me/{bot_username}?start={unique_code}"

def parse_start_param(param: str) -> Optional[int]:
    """تحليل بارامتر بدء التشغيل لاستخراج معرف المدعو"""
    try:
        if '_' in param:
            inviter_id = int(param.split('_')[0])
            return inviter_id
    except:
        pass
    return None

def format_number(num: int) -> str:
    """تنسيق الأرقام (1000 -> 1,000)"""
    return f"{num:,}"

def is_admin(user_id: int) -> bool:
    """التحقق ما إذا كان المستخدم مديراً"""
    return user_id in ADMIN_IDS

def is_banned(user_id: int) -> bool:
    """التحقق ما إذا كان المستخدم محظوراً"""
    return user_id in banned_users

def get_user_data(user_id: int, username: str = None) -> dict:
    """الحصول على بيانات المستخدم أو إنشاء حساب جديد"""
    if user_id not in users_db:
        users_db[user_id] = {
            "id": user_id,
            "username": username,
            "points": 0,
            "invited_by": None,
            "invites_count": 0,
            "banned": False,
            "created_at": datetime.now().isoformat(),
            "last_active": datetime.now().isoformat(),
        }
    else:
        users_db[user_id]["last_active"] = datetime.now().isoformat()
        if username:
            users_db[user_id]["username"] = username
    
    return users_db[user_id]

def save_numbers_file(file_id: str, filename: str, numbers: List[str], added_by: int) -> dict:
    """حفظ ملف الأرقام"""
    file_data = {
        "id": file_id,
        "name": filename,
        "numbers": numbers,
        "used_numbers": [],
        "created_at": datetime.now().isoformat(),
        "added_by": added_by,
        "total_count": len(numbers),
        "used_count": 0,
    }
    numbers_files_db[file_id] = file_data
    return file_data

def get_available_numbers(count: int) -> List[str]:
    """الحصول على أرقام متاحة للتمويل"""
    available_numbers = []
    for file_id, file_data in numbers_files_db.items():
        unused = [n for n in file_data["numbers"] if n not in file_data["used_numbers"]]
        available_numbers.extend(unused)
        
        if len(available_numbers) >= count:
            break
    
    return available_numbers[:count]

def mark_numbers_as_used(numbers: List[str]):
    """تحديد الأرقام كمستخدمة"""
    for number in numbers:
        for file_id, file_data in numbers_files_db.items():
            if number in file_data["numbers"] and number not in file_data["used_numbers"]:
                file_data["used_numbers"].append(number)
                file_data["used_count"] = len(file_data["used_numbers"])
                break

def get_total_available_numbers() -> int:
    """الحصول على إجمالي الأرقام المتاحة"""
    total = 0
    for file_data in numbers_files_db.values():
        total += len(file_data["numbers"]) - len(file_data["used_numbers"])
    return total

def get_total_numbers_count() -> int:
    """الحصول على إجمالي الأرقام (مستخدمة + غير مستخدمة)"""
    total = 0
    for file_data in numbers_files_db.values():
        total += len(file_data["numbers"])
    return total

def get_users_count() -> int:
    """الحصول على عدد المستخدمين"""
    return len(users_db)

def get_total_points() -> int:
    """الحصول على إجمالي النقاط في النظام"""
    total = 0
    for user_data in users_db.values():
        total += user_data["points"]
    return total

def get_funding_stats() -> dict:
    """الحصول على إحصائيات التمويل"""
    completed = 0
    pending = 0
    cancelled = 0
    total_members_added = 0
    
    for request in funding_requests_db.values():
        if request["status"] == "completed":
            completed += 1
            total_members_added += request.get("added_members", 0)
        elif request["status"] == "pending":
            pending += 1
        elif request["status"] == "cancelled":
            cancelled += 1
    
    return {
        "completed": completed,
        "pending": pending,
        "cancelled": cancelled,
        "total_members_added": total_members_added,
    }

# ==================== دوال لوحة المفاتيح ====================

def get_main_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """لوحة المفاتيح الرئيسية للمستخدم"""
    user_data = get_user_data(user_id)
    
    keyboard = [
        [InlineKeyboardButton("💰 تجميع النقاط", callback_data="collect_points")],
        [InlineKeyboardButton("🚀 تمويل مشتركين", callback_data="fund_members")],
        [InlineKeyboardButton("📊 تمويلاتي", callback_data="my_fundings")],
        [InlineKeyboardButton("📈 إحصائياتي", callback_data="my_stats")],
        [InlineKeyboardButton("🆘 الدعم الفني", callback_data="support")],
        [InlineKeyboardButton("📢 قناة البوت", callback_data="channel")],
    ]
    
    return InlineKeyboardMarkup(keyboard)

def get_admin_keyboard() -> InlineKeyboardMarkup:
    """لوحة المفاتيح للإدارة"""
    keyboard = [
        [InlineKeyboardButton("📊 إحصائيات البوت", callback_data="admin_stats")],
        [InlineKeyboardButton("💰 شحن رصيد", callback_data="admin_charge")],
        [InlineKeyboardButton("💸 خصم رصيد", callback_data="admin_deduct")],
        [InlineKeyboardButton("📁 إضافة ملف أرقام", callback_data="admin_add_file")],
        [InlineKeyboardButton("🗑️ حذف ملف أرقام", callback_data="admin_delete_file")],
        [InlineKeyboardButton("🆘 إضافة حساب دعم", callback_data="admin_add_support")],
        [InlineKeyboardButton("📢 إضافة رابط قناة", callback_data="admin_add_channel")],
        [InlineKeyboardButton("🔒 حظر مستخدم", callback_data="admin_ban")],
        [InlineKeyboardButton("🔓 رفع حظر", callback_data="admin_unban")],
        [InlineKeyboardButton("📢 الاشتراك الإجباري", callback_data="admin_force_sub")],
        [InlineKeyboardButton("🎁 تغيير مكافأة الدعوة", callback_data="admin_change_invite")],
        [InlineKeyboardButton("💵 تغيير سعر العضو", callback_data="admin_change_price")],
        [InlineKeyboardButton("✏️ تغيير رسالة الترحيب", callback_data="admin_change_welcome")],
    ]
    
    return InlineKeyboardMarkup(keyboard)

def get_force_sub_keyboard() -> InlineKeyboardMarkup:
    """لوحة المفاتيح للاشتراك الإجباري"""
    keyboard = []
    
    for channel in force_sub_channels:
        keyboard.append([InlineKeyboardButton(f"📢 {channel}", callback_data=f"force_sub_{channel}")])
    
    keyboard.append([InlineKeyboardButton("➕ إضافة قناة", callback_data="admin_add_force")])
    keyboard.append([InlineKeyboardButton("❌ حذف قناة", callback_data="admin_remove_force")])
    keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="admin_back")])
    
    return InlineKeyboardMarkup(keyboard)

def get_funding_control_keyboard(request_id: str, user_id: int) -> InlineKeyboardMarkup:
    """لوحة التحكم في طلب التمويل للإدارة"""
    keyboard = [
        [InlineKeyboardButton("❌ إلغاء التمويل", callback_data=f"cancel_funding_{request_id}")],
        [InlineKeyboardButton("🔒 حظر المستخدم", callback_data=f"ban_user_{user_id}")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="admin_back")],
    ]
    
    return InlineKeyboardMarkup(keyboard)

# ==================== دوال التحقق من الاشتراك ====================

async def check_force_subscription(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> Tuple[bool, List[str]]:
    """التحقق من اشتراك المستخدم في القنوات الإجبارية"""
    if not force_sub_channels:
        return True, []
    
    not_joined = []
    for channel in force_sub_channels:
        try:
            member = await context.bot.get_chat_member(chat_id=channel, user_id=user_id)
            if member.status in [ChatMemberStatus.LEFT, ChatMemberStatus.BANNED]:
                not_joined.append(channel)
        except:
            not_joined.append(channel)
    
    return len(not_joined) == 0, not_joined

async def force_sub_message(not_joined: List[str]) -> str:
    """رسالة الاشتراك الإجباري"""
    message = "🔒 *الاشتراك الإجباري*\n\n"
    message += "يجب الاشتراك في القنوات التالية لاستخدام البوت:\n\n"
    
    for channel in not_joined:
        message += f"• {channel}\n"
    
    message += "\nبعد الاشتراك، اضغط على /start لتحديث الحالة."
    
    return message

# ==================== معالج /start ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج أمر /start"""
    user = update.effective_user
    user_id = user.id
    username = user.username or user.first_name
    
    # التحقق من الحظر
    if is_banned(user_id):
        await update.message.reply_text("🚫 أنت محظور من استخدام البوت.")
        return
    
    # التحقق من الاشتراك الإجباري
    subscribed, not_joined = await check_force_subscription(user_id, context)
    if not subscribed:
        await update.message.reply_text(
            await force_sub_message(not_joined),
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True,
        )
        return
    
    # معالجة بارامتر بدء التشغيل (الدعوة)
    args = context.args
    if args:
        inviter_id = parse_start_param(args[0])
        if inviter_id and inviter_id != user_id:
            # تحديث بيانات المدعو
            inviter_data = get_user_data(inviter_id)
            user_data = get_user_data(user_id, username)
            
            # إذا لم يكن للمستخدم مدعو سابقاً
            if not user_data["invited_by"]:
                user_data["invited_by"] = inviter_id
                
                # إضافة نقاط للمدعو
                inviter_data["points"] += bot_settings["points_per_invite"]
                inviter_data["invites_count"] += 1
                
                # إشعار المدعو
                try:
                    await context.bot.send_message(
                        inviter_id,
                        f"🎉 تم دعوة مستخدم جديد!\n"
                        f"👤 المستخدم: {username}\n"
                        f"💰 رصيدك: {inviter_data['points']} نقطة",
                    )
                except:
                    pass
    
    # تسجيل دخول المستخدم
    user_data = get_user_data(user_id, username)
    
    # إعداد رسالة الترحيب
    welcome_msg = bot_settings["welcome_message"]
    user_info = (
        f"👋 مرحباً بك {username}!\n\n"
        f"🆔 ايديك: {user_id}\n"
        f"💰 نقاطك: {user_data['points']}\n"
        f"👥 عدد من دعوتهم: {user_data['invites_count']}\n\n"
        f"{welcome_msg}"
    )
    
    # عرض القائمة الرئيسية
    await update.message.reply_text(
        user_info,
        reply_markup=get_main_keyboard(user_id),
    )

# ==================== معالج النصوص للملفات ====================

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج استلام الملفات (للإدارة فقط)"""
    user_id = update.effective_user.id
    
    # التحقق من أن المستخدم مدير
    if not is_admin(user_id):
        await update.message.reply_text("🚫 هذا الأمر متاح للإدارة فقط.")
        return
    
    # التحقق من وجود حالة إضافة ملف
    if context.user_data.get("state") != ADD_NUMBERS_FILE:
        return
    
    document = update.message.document
    
    # التحقق من صيغة الملف
    if not document.file_name.endswith('.txt'):
        await update.message.reply_text("❌ الصيغة غير مدعومة. يرجى إرسال ملف بصيغة TXT فقط.")
        return
    
    # تحميل الملف
    file = await context.bot.get_file(document.file_id)
    file_path = f"temp_{document.file_id}.txt"
    await file.download_to_drive(file_path)
    
    # قراءة الأرقام من الملف
    numbers = []
    try:
        async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
            content = await f.read()
            numbers = [line.strip() for line in content.split('\n') if line.strip()]
    except Exception as e:
        logger.error(f"خطأ في قراءة الملف: {e}")
        await update.message.reply_text("❌ حدث خطأ أثناء قراءة الملف.")
        
        # حذف الملف المؤقت
        if os.path.exists(file_path):
            os.remove(file_path)
        
        context.user_data["state"] = None
        return
    
    # حذف الملف المؤقت
    if os.path.exists(file_path):
        os.remove(file_path)
    
    # حفظ الأرقام
    file_data = save_numbers_file(document.file_id, document.file_name, numbers, user_id)
    
    await update.message.reply_text(
        f"✅ تم إضافة الملف بنجاح!\n\n"
        f"📁 اسم الملف: {document.file_name}\n"
        f"🔢 عدد الأرقام: {len(numbers)}\n"
        f"🆔 معرف الملف: {document.file_id}"
    )
    
    context.user_data["state"] = None

# ==================== معالج الأزرار (CallbackQuery) ====================

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج الأزرار"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    
    # التحقق من الحظر
    if is_banned(user_id) and not data.startswith("admin_"):
        await query.edit_message_text("🚫 أنت محظور من استخدام البوت.")
        return
    
    # التحقق من الاشتراك الإجباري (للمستخدمين العاديين)
    if not is_admin(user_id) and not data.startswith("admin_"):
        subscribed, not_joined = await check_force_subscription(user_id, context)
        if not subscribed:
            await query.edit_message_text(
                await force_sub_message(not_joined),
                parse_mode=ParseMode.MARKDOWN,
                disable_web_page_preview=True,
            )
            return
    
    # ==================== معالجة أزرار المستخدمين ====================
    
    if data == "collect_points":
        # زر تجميع النقاط
        user_data = get_user_data(user_id)
        
        # إنشاء رابط الدعوة إذا لم يكن موجوداً
        if user_id not in invite_links_db:
            invite_links_db[user_id] = {
                "link": generate_invite_link(user_id),
                "created_at": datetime.now().isoformat(),
                "uses_count": 0,
            }
        
        invite_link = invite_links_db[user_id]["link"]
        
        text = (
            "🔗 *رابط الدعوة الخاص بك*\n\n"
            "شارك الرابط التالي مع أصدقائك، وكل شخص يدخل عن طريق الرابط ستحصل على نقاط!\n\n"
            f"🔗 الرابط: {invite_link}\n"
            f"💰 النقاط لكل دعوة: {bot_settings['points_per_invite']} نقطة\n"
            f"👥 إجمالي من دعوتهم: {user_data['invites_count']}\n\n"
            "🔄 *للشحن:*\n"
            "يمكنك التواصل مع الدعم الفني لشحن رصيدك."
        )
        
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="back_main")]]
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard),
            disable_web_page_preview=True,
        )
    
    elif data == "fund_members":
        # زر تمويل مشتركين
        user_data = get_user_data(user_id)
        
        text = (
            "🚀 *تمويل مشتركين*\n\n"
            f"💰 رصيدك الحالي: {user_data['points']} نقطة\n"
            f"💵 تكلفة العضو الواحد: {bot_settings['points_per_member']} نقطة\n\n"
            "📝 أرسل لي عدد الأعضاء الذي تريد تمويلهم.\n"
            "مثال: 100"
        )
        
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="back_main")]]
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        
        # تعيين حالة المحادثة لاستقبال عدد الأعضاء
        context.user_data["state"] = FUNDING_STEP1
    
    elif data == "my_fundings":
        # زر تمويلاتي
        user_fundings = []
        for req_id, req_data in funding_requests_db.items():
            if req_data["user_id"] == user_id:
                status_text = {
                    "pending": "⏳ قيد التنفيذ",
                    "completed": "✅ مكتمل",
                    "cancelled": "❌ ملغي",
                }.get(req_data["status"], req_data["status"])
                
                user_fundings.append(
                    f"🆔 الطلب: {req_id[:8]}...\n"
                    f"📢 القناة: {req_data['chat_link']}\n"
                    f"👥 الأعضاء: {req_data['added_members']}/{req_data['members_count']}\n"
                    f"📊 الحالة: {status_text}\n"
                    f"📅 التاريخ: {req_data['created_at'][:10]}\n"
                )
        
        if not user_fundings:
            text = "📊 ليس لديك أي تمويلات سابقة."
        else:
            text = "📊 *تمويلاتك*\n\n" + "\n".join(user_fundings)
        
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="back_main")]]
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
    
    elif data == "my_stats":
        # زر إحصائياتي
        user_data = get_user_data(user_id)
        
        # حساب إحصائيات المستخدم
        total_fundings = sum(1 for r in funding_requests_db.values() if r["user_id"] == user_id)
        completed_fundings = sum(1 for r in funding_requests_db.values() if r["user_id"] == user_id and r["status"] == "completed")
        total_members_funded = sum(r.get("added_members", 0) for r in funding_requests_db.values() if r["user_id"] == user_id)
        
        text = (
            "📈 *إحصائياتك الشخصية*\n\n"
            f"🆔 الايدي: {user_id}\n"
            f"👤 اسم المستخدم: {user_data['username']}\n"
            f"💰 النقاط الحالية: {user_data['points']}\n"
            f"👥 عدد الدعوات: {user_data['invites_count']}\n"
            f"📊 إجمالي التمويلات: {total_fundings}\n"
            f"✅ التمويلات المكتملة: {completed_fundings}\n"
            f"👥 الأعضاء الممولة: {total_members_funded}\n"
            f"📅 تاريخ التسجيل: {user_data['created_at'][:10]}"
        )
        
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="back_main")]]
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
    
    elif data == "support":
        # زر الدعم الفني
        text = f"🆘 *الدعم الفني*\n\nللتواصل مع الدعم الفني، يرجى التواصل مع:\n@{bot_settings['support_username']}"
        
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="back_main")]]
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
    
    elif data == "channel":
        # زر قناة البوت
        text = f"📢 *قناة البوت*\n\nتابع قناة البوت لمعرفة آخر التحديثات:\n{bot_settings['channel_link']}"
        
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="back_main")]]
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard),
            disable_web_page_preview=True,
        )
    
    elif data == "back_main":
        # زر الرجوع للقائمة الرئيسية
        user_data = get_user_data(user_id)
        
        text = (
            f"👋 مرحباً بك {user_data['username']}!\n\n"
            f"🆔 ايديك: {user_id}\n"
            f"💰 نقاطك: {user_data['points']}\n"
            f"👥 عدد من دعوتهم: {user_data['invites_count']}\n\n"
            f"{bot_settings['welcome_message']}"
        )
        
        await query.edit_message_text(
            text,
            reply_markup=get_main_keyboard(user_id),
        )
        
        # إعادة تعيين حالة المحادثة
        context.user_data["state"] = None
    
    # ==================== معالجة أزرار الإدارة ====================
    
    elif data == "admin_stats" and is_admin(user_id):
        # إحصائيات البوت
        users_count = get_users_count()
        total_points = get_total_points()
        available_numbers = get_total_available_numbers()
        total_numbers = get_total_numbers_count()
        funding_stats = get_funding_stats()
        
        text = (
            "📊 *إحصائيات البوت*\n\n"
            f"👥 إجمالي المستخدمين: {users_count}\n"
            f"💰 إجمالي النقاط: {total_points}\n"
            f"📁 ملفات الأرقام: {len(numbers_files_db)}\n"
            f"🔢 الأرقام المتاحة: {available_numbers}/{total_numbers}\n"
            f"📊 التمويلات:\n"
            f"  ✅ مكتملة: {funding_stats['completed']}\n"
            f"  ⏳ قيد التنفيذ: {funding_stats['pending']}\n"
            f"  ❌ ملغية: {funding_stats['cancelled']}\n"
            f"  👥 أعضاء مضافين: {funding_stats['total_members_added']}"
        )
        
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_admin_keyboard(),
        )
    
    elif data == "admin_charge" and is_admin(user_id):
        # شحن رصيد
        text = "💰 *شحن رصيد*\n\nأرسل ايدي المستخدم المراد شحن رصيده."
        
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
        )
        context.user_data["state"] = CHARGE_POINTS_STEP1
    
    elif data == "admin_deduct" and is_admin(user_id):
        # خصم رصيد
        text = "💸 *خصم رصيد*\n\nأرسل ايدي المستخدم المراد خصم رصيده."
        
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
        )
        context.user_data["state"] = DEDUCT_POINTS_STEP1
    
    elif data == "admin_add_file" and is_admin(user_id):
        # إضافة ملف أرقام
        text = (
            "📁 *إضافة ملف أرقام*\n\n"
            "أرسل ملف TXT يحتوي على أرقام الهواتف.\n"
            "كل رقم في سطر منفصل.\n\n"
            "مثال:\n"
            "966501234567\n"
            "966501234568\n"
            "966501234569"
        )
        
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
        )
        context.user_data["state"] = ADD_NUMBERS_FILE
    
    elif data == "admin_delete_file" and is_admin(user_id):
        # حذف ملف أرقام
        if not numbers_files_db:
            await query.edit_message_text(
                "📁 لا توجد ملفات أرقام لحذفها.",
                reply_markup=get_admin_keyboard(),
            )
            return
        
        text = "🗑️ *حذف ملف أرقام*\n\nاختر الملف الذي تريد حذفه:\n\n"
        keyboard = []
        
        for file_id, file_data in numbers_files_db.items():
            available = len(file_data["numbers"]) - len(file_data["used_numbers"])
            text += f"🆔 {file_id[:8]}... - {file_data['name']}\n"
            text += f"   📊 إجمالي: {file_data['total_count']} | متاح: {available}\n\n"
            
            keyboard.append([InlineKeyboardButton(
                f"🗑️ {file_data['name'][:20]}", 
                callback_data=f"delete_file_{file_id}"
            )])
        
        keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="admin_back")])
        
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
    
    elif data.startswith("delete_file_") and is_admin(user_id):
        # حذف ملف محدد
        file_id = data.replace("delete_file_", "")
        
        if file_id in numbers_files_db:
            del numbers_files_db[file_id]
            await query.edit_message_text(
                f"✅ تم حذف الملف بنجاح.",
                reply_markup=get_admin_keyboard(),
            )
        else:
            await query.edit_message_text(
                f"❌ الملف غير موجود.",
                reply_markup=get_admin_keyboard(),
            )
    
    elif data == "admin_add_support" and is_admin(user_id):
        # إضافة حساب دعم
        text = "🆘 *إضافة حساب دعم*\n\nأرسل يوزر حساب الدعم الفني (بدون @)."
        
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
        )
        context.user_data["state"] = ADD_SUPPORT
    
    elif data == "admin_add_channel" and is_admin(user_id):
        # إضافة رابط قناة
        text = "📢 *إضافة رابط قناة*\n\nأرسل رابط قناة البوت."
        
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
        )
        context.user_data["state"] = ADD_CHANNEL_LINK
    
    elif data == "admin_ban" and is_admin(user_id):
        # حظر مستخدم
        text = "🔒 *حظر مستخدم*\n\nأرسل ايدي المستخدم المراد حظره."
        
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
        )
        context.user_data["state"] = BAN_USER_STEP
    
    elif data == "admin_unban" and is_admin(user_id):
        # رفع حظر
        text = "🔓 *رفع حظر*\n\nأرسل ايدي المستخدم المراد رفع الحظر عنه."
        
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
        )
        context.user_data["state"] = UNBAN_USER_STEP
    
    elif data == "admin_force_sub" and is_admin(user_id):
        # الاشتراك الإجباري
        text = "📢 *الاشتراك الإجباري*\n\n"
        
        if force_sub_channels:
            text += "القنوات الحالية:\n"
            for i, channel in enumerate(force_sub_channels, 1):
                text += f"{i}. {channel}\n"
        else:
            text += "لا توجد قنوات اشتراك إجباري حالياً."
        
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_force_sub_keyboard(),
        )
    
    elif data == "admin_add_force" and is_admin(user_id):
        # إضافة قناة للاشتراك الإجباري
        text = "📢 *إضافة قناة للاشتراك الإجباري*\n\nأرسل معرف القناة (مثال: @channel_username)."
        
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
        )
        context.user_data["state"] = ADD_FORCE_CHANNEL
    
    elif data == "admin_remove_force" and is_admin(user_id):
        # حذف قناة من الاشتراك الإجباري
        if not force_sub_channels:
            await query.edit_message_text(
                "📢 لا توجد قنوات لحذفها.",
                reply_markup=get_admin_keyboard(),
            )
            return
        
        text = "📢 *حذف قناة من الاشتراك الإجباري*\n\nاختر القناة التي تريد حذفها:\n\n"
        keyboard = []
        
        for channel in force_sub_channels:
            keyboard.append([InlineKeyboardButton(
                f"🗑️ {channel}", 
                callback_data=f"remove_force_{channel}"
            )])
        
        keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="admin_back")])
        
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
    
    elif data.startswith("remove_force_") and is_admin(user_id):
        # حذف قناة محددة
        channel = data.replace("remove_force_", "")
        
        if channel in force_sub_channels:
            force_sub_channels.remove(channel)
            await query.edit_message_text(
                f"✅ تم حذف القناة {channel} من الاشتراك الإجباري.",
                reply_markup=get_admin_keyboard(),
            )
        else:
            await query.edit_message_text(
                f"❌ القناة غير موجودة.",
                reply_markup=get_admin_keyboard(),
            )
    
    elif data == "admin_change_invite" and is_admin(user_id):
        # تغيير مكافأة الدعوة
        text = f"🎁 *تغيير مكافأة الدعوة*\n\nالمكافأة الحالية: {bot_settings['points_per_invite']} نقطة\n\nأرسل القيمة الجديدة."
        
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
        )
        context.user_data["state"] = CHANGE_INVITE_REWARD_STEP
    
    elif data == "admin_change_price" and is_admin(user_id):
        # تغيير سعر العضو
        text = f"💵 *تغيير سعر العضو*\n\nالسعر الحالي: {bot_settings['points_per_member']} نقطة\n\nأرسل القيمة الجديدة."
        
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
        )
        context.user_data["state"] = CHANGE_MEMBER_PRICE_STEP
    
    elif data == "admin_change_welcome" and is_admin(user_id):
        # تغيير رسالة الترحيب
        text = f"✏️ *تغيير رسالة الترحيب*\n\nالرسالة الحالية:\n{bot_settings['welcome_message']}\n\nأرسل الرسالة الجديدة."
        
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
        )
        context.user_data["state"] = "CHANGE_WELCOME"
    
    elif data == "admin_back" and is_admin(user_id):
        # رجوع للوحة التحكم
        await query.edit_message_text(
            "🖥️ *لوحة التحكم*\n\nاختر الأمر الذي تريد تنفيذه:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_admin_keyboard(),
        )
        context.user_data["state"] = None
    
    elif data.startswith("cancel_funding_") and is_admin(user_id):
        # إلغاء تمويل
        request_id = data.replace("cancel_funding_", "")
        
        if request_id in funding_requests_db:
            funding_requests_db[request_id]["status"] = "cancelled"
            
            # إشعار المستخدم
            try:
                await context.bot.send_message(
                    funding_requests_db[request_id]["user_id"],
                    f"❌ تم إلغاء طلب التمويل الخاص بك.\n"
                    f"🆔 معرف الطلب: {request_id[:8]}..."
                )
            except:
                pass
            
            await query.edit_message_text(
                f"✅ تم إلغاء التمويل بنجاح.",
                reply_markup=get_admin_keyboard(),
            )
        else:
            await query.edit_message_text(
                f"❌ الطلب غير موجود.",
                reply_markup=get_admin_keyboard(),
            )
    
    elif data.startswith("ban_user_") and is_admin(user_id):
        # حظر مستخدم من طلب تمويل
        target_user_id = int(data.replace("ban_user_", ""))
        
        if target_user_id in ADMIN_IDS:
            await query.edit_message_text(
                "❌ لا يمكن حظر مدير البوت.",
                reply_markup=get_admin_keyboard(),
            )
            return
        
        banned_users.add(target_user_id)
        
        if target_user_id in users_db:
            users_db[target_user_id]["banned"] = True
        
        await query.edit_message_text(
            f"✅ تم حظر المستخدم {target_user_id} بنجاح.",
            reply_markup=get_admin_keyboard(),
        )

# ==================== معالج النصوص للمستخدمين ====================

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج النصوص للمستخدمين"""
    user_id = update.effective_user.id
    text = update.message.text
    state = context.user_data.get("state")
    
    # التحقق من الحظر
    if is_banned(user_id):
        await update.message.reply_text("🚫 أنت محظور من استخدام البوت.")
        return
    
    # التحقق من الاشتراك الإجباري (للمستخدمين العاديين)
    if not is_admin(user_id):
        subscribed, not_joined = await check_force_subscription(user_id, context)
        if not subscribed:
            await update.message.reply_text(
                await force_sub_message(not_joined),
                parse_mode=ParseMode.MARKDOWN,
                disable_web_page_preview=True,
            )
            return
    
    # ==================== معالجة حالات المستخدمين ====================
    
    if state == FUNDING_STEP1:
        # استقبال عدد الأعضاء للتمويل
        try:
            members_count = int(text)
            if members_count <= 0:
                await update.message.reply_text("❌ يرجى إرسال عدد صحيح أكبر من 0.")
                return
            
            user_data = get_user_data(user_id)
            cost = members_count * bot_settings["points_per_member"]
            
            if user_data["points"] < cost:
                await update.message.reply_text(
                    f"❌ رصيدك غير كافٍ.\n"
                    f"💰 رصيدك: {user_data['points']}\n"
                    f"💵 التكلفة: {cost}\n"
                    f"⚡ الناقص: {cost - user_data['points']}"
                )
                context.user_data["state"] = None
                return
            
            context.user_data["funding_members_count"] = members_count
            context.user_data["funding_cost"] = cost
            
            await update.message.reply_text(
                f"✅ تم حساب التكلفة:\n"
                f"👥 عدد الأعضاء: {members_count}\n"
                f"💰 التكلفة: {cost} نقطة\n"
                f"💳 رصيدك بعد الخصم: {user_data['points'] - cost}\n\n"
                f"📢 الآن أرسل رابط قناتك أو مجموعتك.\n"
                f"⚠️ تأكد أن البوت مشرف في القناة/المجموعة."
            )
            context.user_data["state"] = FUNDING_STEP2
        
        except ValueError:
            await update.message.reply_text("❌ يرجى إرسال عدد صحيح.")
    
    elif state == FUNDING_STEP2:
        # استقبال رابط القناة وبدء التمويل
        chat_link = text.strip()
        members_count = context.user_data.get("funding_members_count")
        cost = context.user_data.get("funding_cost")
        
        if not members_count or not cost:
            await update.message.reply_text("❌ حدث خطأ، يرجى المحاولة مرة أخرى.")
            context.user_data["state"] = None
            return
        
        # التحقق من صلاحية البوت في القناة/المجموعة
        try:
            # محاولة استخراج معرف القناة من الرابط
            if "t.me/" in chat_link:
                chat_username = chat_link.split("t.me/")[-1].split("/")[0]
                chat = await context.bot.get_chat(f"@{chat_username}")
            else:
                chat = await context.bot.get_chat(chat_link)
            
            # التحقق من أن البوت مشرف
            bot_member = await context.bot.get_chat_member(chat.id, context.bot.id)
            if bot_member.status not in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR]:
                await update.message.reply_text(
                    "❌ البوت ليس مشرفاً في هذه القناة/المجموعة.\n"
                    "يرجى جعل البوت مشرف ثم حاول مرة أخرى."
                )
                return
            
            # خصم النقاط من المستخدم
            user_data = get_user_data(user_id)
            if user_data["points"] < cost:
                await update.message.reply_text("❌ رصيدك غير كافٍ.")
                context.user_data["state"] = None
                return
            
            user_data["points"] -= cost
            
            # إنشاء طلب تمويل جديد
            request_id = str(uuid4())
            funding_requests_db[request_id] = {
                "id": request_id,
                "user_id": user_id,
                "chat_id": chat.id,
                "chat_link": chat_link,
                "members_count": members_count,
                "cost": cost,
                "status": "pending",
                "added_members": 0,
                "created_at": datetime.now().isoformat(),
            }
            
            # إشعار الإدارة
            for admin_id in ADMIN_IDS:
                try:
                    keyboard = InlineKeyboardMarkup([[
                        InlineKeyboardButton("🔍 عرض التفاصيل", callback_data=f"view_funding_{request_id}")
                    ]])
                    
                    await context.bot.send_message(
                        admin_id,
                        f"📢 *طلب تمويل جديد*\n\n"
                        f"👤 المستخدم: {user_id}\n"
                        f"📢 القناة: {chat_link}\n"
                        f"👥 عدد الأعضاء: {members_count}\n"
                        f"💰 التكلفة: {cost}\n"
                        f"🆔 معرف الطلب: {request_id[:8]}...",
                        parse_mode=ParseMode.MARKDOWN,
                        reply_markup=keyboard,
                    )
                except:
                    pass
            
            # بدء عملية التمويل
            await update.message.reply_text(
                f"✅ تم بدء عملية التمويل بنجاح!\n"
                f"📢 القناة: {chat_link}\n"
                f"👥 عدد الأعضاء: {members_count}\n"
                f"💰 المتبقي: {members_count} عضو\n\n"
                f"سيتم إعلامك عند إضافة كل عضو."
            )
            
            # بدء إضافة الأعضاء في الخلفية
            asyncio.create_task(process_funding(request_id, context))
            
        except Exception as e:
            logger.error(f"خطأ في بدء التمويل: {e}")
            await update.message.reply_text(
                "❌ حدث خطأ أثناء بدء التمويل.\n"
                "تأكد من صحة الرابط وأن البوت مشرف في القناة."
            )
        
        context.user_data["state"] = None
    
    # ==================== معالجة حالات الإدارة ====================
    
    elif state == CHARGE_POINTS_STEP1 and is_admin(user_id):
        # استقبال ايدي المستخدم للشحن
        try:
            target_id = int(text)
            context.user_data["charge_target"] = target_id
            await update.message.reply_text("💰 أرسل المبلغ المراد شحنه.")
            context.user_data["state"] = CHARGE_POINTS_STEP2
        except ValueError:
            await update.message.reply_text("❌ يرجى إرسال ايدي صحيح.")
    
    elif state == CHARGE_POINTS_STEP2 and is_admin(user_id):
        # استقبال المبلغ للشحن
        try:
            amount = int(text)
            if amount <= 0:
                await update.message.reply_text("❌ يرجى إرسال مبلغ أكبر من 0.")
                return
            
            target_id = context.user_data.get("charge_target")
            if not target_id:
                await update.message.reply_text("❌ حدث خطأ، يرجى المحاولة مرة أخرى.")
                context.user_data["state"] = None
                return
            
            # شحن الرصيد
            user_data = get_user_data(target_id)
            user_data["points"] += amount
            
            await update.message.reply_text(
                f"✅ تم شحن رصيد المستخدم {target_id} بنجاح.\n"
                f"💰 المبلغ المضاف: {amount}\n"
                f"💳 الرصيد الحالي: {user_data['points']}"
            )
            
            # إشعار المستخدم
            try:
                await context.bot.send_message(
                    target_id,
                    f"💰 تم شحن رصيدك بمبلغ {amount} نقطة.\n"
                    f"💳 رصيدك الحالي: {user_data['points']}"
                )
            except:
                pass
            
        except ValueError:
            await update.message.reply_text("❌ يرجى إرسال رقم صحيح.")
        
        context.user_data["state"] = None
    
    elif state == DEDUCT_POINTS_STEP1 and is_admin(user_id):
        # استقبال ايدي المستخدم للخصم
        try:
            target_id = int(text)
            context.user_data["deduct_target"] = target_id
            await update.message.reply_text("💸 أرسل المبلغ المراد خصمه.")
            context.user_data["state"] = DEDUCT_POINTS_STEP2
        except ValueError:
            await update.message.reply_text("❌ يرجى إرسال ايدي صحيح.")
    
    elif state == DEDUCT_POINTS_STEP2 and is_admin(user_id):
        # استقبال المبلغ للخصم
        try:
            amount = int(text)
            if amount <= 0:
                await update.message.reply_text("❌ يرجى إرسال مبلغ أكبر من 0.")
                return
            
            target_id = context.user_data.get("deduct_target")
            if not target_id:
                await update.message.reply_text("❌ حدث خطأ، يرجى المحاولة مرة أخرى.")
                context.user_data["state"] = None
                return
            
            # خصم الرصيد
            if target_id not in users_db:
                await update.message.reply_text(f"❌ المستخدم {target_id} غير موجود.")
                context.user_data["state"] = None
                return
            
            user_data = users_db[target_id]
            if user_data["points"] < amount:
                await update.message.reply_text(
                    f"❌ رصيد المستخدم غير كافٍ.\n"
                    f"💰 رصيده: {user_data['points']}"
                )
                context.user_data["state"] = None
                return
            
            user_data["points"] -= amount
            
            await update.message.reply_text(
                f"✅ تم خصم رصيد المستخدم {target_id} بنجاح.\n"
                f"💰 المبلغ المخصوم: {amount}\n"
                f"💳 الرصيد الحالي: {user_data['points']}"
            )
            
            # إشعار المستخدم
            try:
                await context.bot.send_message(
                    target_id,
                    f"💸 تم خصم {amount} نقطة من رصيدك.\n"
                    f"💳 رصيدك الحالي: {user_data['points']}"
                )
            except:
                pass
            
        except ValueError:
            await update.message.reply_text("❌ يرجى إرسال رقم صحيح.")
        
        context.user_data["state"] = None
    
    elif state == ADD_SUPPORT and is_admin(user_id):
        # إضافة حساب دعم
        support_username = text.strip().replace("@", "")
        bot_settings["support_username"] = support_username
        
        await update.message.reply_text(
            f"✅ تم تعيين حساب الدعم الفني إلى @{support_username} بنجاح."
        )
        context.user_data["state"] = None
    
    elif state == ADD_CHANNEL_LINK and is_admin(user_id):
        # إضافة رابط قناة
        channel_link = text.strip()
        bot_settings["channel_link"] = channel_link
        
        await update.message.reply_text(
            f"✅ تم تعيين رابط القناة إلى:\n{channel_link}"
        )
        context.user_data["state"] = None
    
    elif state == ADD_FORCE_CHANNEL and is_admin(user_id):
        # إضافة قناة للاشتراك الإجباري
        channel = text.strip()
        
        if channel not in force_sub_channels:
            force_sub_channels.append(channel)
            await update.message.reply_text(f"✅ تم إضافة القناة {channel} للاشتراك الإجباري.")
        else:
            await update.message.reply_text(f"⚠️ القناة {channel} موجودة بالفعل.")
        
        context.user_data["state"] = None
    
    elif state == BAN_USER_STEP and is_admin(user_id):
        # حظر مستخدم
        try:
            target_id = int(text)
            
            if target_id in ADMIN_IDS:
                await update.message.reply_text("❌ لا يمكن حظر مدير البوت.")
                context.user_data["state"] = None
                return
            
            banned_users.add(target_id)
            
            if target_id in users_db:
                users_db[target_id]["banned"] = True
            
            await update.message.reply_text(f"✅ تم حظر المستخدم {target_id} بنجاح.")
            
        except ValueError:
            await update.message.reply_text("❌ يرجى إرسال ايدي صحيح.")
        
        context.user_data["state"] = None
    
    elif state == UNBAN_USER_STEP and is_admin(user_id):
        # رفع حظر
        try:
            target_id = int(text)
            
            if target_id in banned_users:
                banned_users.remove(target_id)
            
            if target_id in users_db:
                users_db[target_id]["banned"] = False
            
            await update.message.reply_text(f"✅ تم رفع الحظر عن المستخدم {target_id} بنجاح.")
            
        except ValueError:
            await update.message.reply_text("❌ يرجى إرسال ايدي صحيح.")
        
        context.user_data["state"] = None
    
    elif state == CHANGE_INVITE_REWARD_STEP and is_admin(user_id):
        # تغيير مكافأة الدعوة
        try:
            new_reward = int(text)
            if new_reward <= 0:
                await update.message.reply_text("❌ يرجى إرسال قيمة أكبر من 0.")
                return
            
            bot_settings["points_per_invite"] = new_reward
            await update.message.reply_text(f"✅ تم تغيير مكافأة الدعوة إلى {new_reward} نقطة.")
            
        except ValueError:
            await update.message.reply_text("❌ يرجى إرسال رقم صحيح.")
        
        context.user_data["state"] = None
    
    elif state == CHANGE_MEMBER_PRICE_STEP and is_admin(user_id):
        # تغيير سعر العضو
        try:
            new_price = int(text)
            if new_price <= 0:
                await update.message.reply_text("❌ يرجى إرسال قيمة أكبر من 0.")
                return
            
            bot_settings["points_per_member"] = new_price
            await update.message.reply_text(f"✅ تم تغيير سعر العضو إلى {new_price} نقطة.")
            
        except ValueError:
            await update.message.reply_text("❌ يرجى إرسال رقم صحيح.")
        
        context.user_data["state"] = None
    
    elif state == "CHANGE_WELCOME" and is_admin(user_id):
        # تغيير رسالة الترحيب
        new_welcome = text.strip()
        bot_settings["welcome_message"] = new_welcome
        await update.message.reply_text(f"✅ تم تغيير رسالة الترحيب إلى:\n{new_welcome}")
        context.user_data["state"] = None

# ==================== معالج عرض تفاصيل التمويل ====================

async def view_funding_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج عرض تفاصيل التمويل للإدارة"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    # التحقق من أن المستخدم مدير
    if not is_admin(user_id):
        await query.edit_message_text("🚫 هذا الأمر متاح للإدارة فقط.")
        return
    
    data = query.data
    request_id = data.replace("view_funding_", "")
    
    if request_id not in funding_requests_db:
        await query.edit_message_text("❌ طلب التمويل غير موجود.")
        return
    
    request = funding_requests_db[request_id]
    
    status_text = {
        "pending": "⏳ قيد التنفيذ",
        "completed": "✅ مكتمل",
        "cancelled": "❌ ملغي",
    }.get(request["status"], request["status"])
    
    text = (
        f"📢 *تفاصيل طلب التمويل*\n\n"
        f"🆔 معرف الطلب: {request_id[:8]}...\n"
        f"👤 المستخدم: {request['user_id']}\n"
        f"📢 القناة: {request['chat_link']}\n"
        f"👥 الأعضاء المطلوبة: {request['members_count']}\n"
        f"➕ الأعضاء المضافة: {request['added_members']}\n"
        f"💰 التكلفة: {request['cost']}\n"
        f"📊 الحالة: {status_text}\n"
        f"📅 تاريخ الإنشاء: {request['created_at'][:16]}"
    )
    
    await query.edit_message_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_funding_control_keyboard(request_id, request['user_id']),
    )

# ==================== معالج إضافة الأعضاء (في الخلفية) ====================

async def process_funding(request_id: str, context: ContextTypes.DEFAULT_TYPE):
    """معالجة طلب التمويل في الخلفية"""
    if request_id not in funding_requests_db:
        return
    
    request = funding_requests_db[request_id]
    chat_id = request["chat_id"]
    members_count = request["members_count"]
    user_id = request["user_id"]
    
    # الحصول على أرقام متاحة
    available_numbers = get_available_numbers(members_count)
    
    if not available_numbers:
        # لا توجد أرقام متاحة
        try:
            await context.bot.send_message(
                user_id,
                f"❌ عذراً، لا توجد أرقام متاحة حالياً للتمويل.\n"
                f"سيتم إرجاع النقاط إلى رصيدك."
            )
            
            # إرجاع النقاط
            if user_id in users_db:
                users_db[user_id]["points"] += request["cost"]
            
            # تحديث حالة الطلب
            request["status"] = "cancelled"
            
            # إشعار الإدارة
            for admin_id in ADMIN_IDS:
                try:
                    await context.bot.send_message(
                        admin_id,
                        f"⚠️ فشل تمويل:\n"
                        f"👤 المستخدم: {user_id}\n"
                        f"📢 القناة: {request['chat_link']}\n"
                        f"❌ السبب: لا توجد أرقام متاحة"
                    )
                except:
                    pass
            
        except:
            pass
        
        return
    
    # إضافة الأعضاء واحداً تلو الآخر
    added_count = 0
    for i, phone_number in enumerate(available_numbers):
        if i >= members_count:
            break
        
        try:
            # محاولة إضافة العضو
            # هذه محاكاة - يجب استبدالها بالكود الفعلي لإضافة الأعضاء
            await asyncio.sleep(2)  # محاكاة وقت الإضافة
            
            added_count += 1
            request["added_members"] = added_count
            
            # تحديث الأرقام المستخدمة
            mark_numbers_as_used([phone_number])
            
            # إرسال تحديث للمستخدم كل 5 أعضاء
            if added_count % 5 == 0 or added_count == members_count:
                try:
                    await context.bot.send_message(
                        user_id,
                        f"📢 تحديث التمويل:\n"
                        f"✅ تم إضافة {added_count} عضو حتى الآن.\n"
                        f"⏳ المتبقي: {members_count - added_count}"
                    )
                except:
                    pass
            
        except Exception as e:
            logger.error(f"خطأ في إضافة العضو {phone_number}: {e}")
            continue
    
    # تحديث حالة الطلب
    if added_count >= members_count:
        request["status"] = "completed"
        final_message = f"✅ اكتمل تمويل قناتك!\n👥 تم إضافة {added_count} عضو."
    else:
        request["status"] = "pending"
        final_message = f"⚠️ اكتمل التمويل جزئياً.\n✅ تم إضافة {added_count} من أصل {members_count} عضو."
    
    # إرسال الإشعار النهائي للمستخدم
    try:
        await context.bot.send_message(user_id, final_message)
    except:
        pass
    
    # إشعار الإدارة
    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_message(
                admin_id,
                f"📢 *تقرير تمويل*\n\n"
                f"👤 المستخدم: {user_id}\n"
                f"📢 القناة: {request['chat_link']}\n"
                f"✅ الأعضاء المضافة: {added_count}/{members_count}\n"
                f"📊 الحالة: {request['status']}",
                parse_mode=ParseMode.MARKDOWN,
            )
        except:
            pass

# ==================== الدالة الرئيسية ====================

async def post_init(application: Application):
    """دالة ما بعد التهيئة"""
    # تعيين وصف البوت
    await application.bot.set_my_description(
        "🤖 بوت تمويل متكامل\n"
        "يمكنك جمع النقاط وتمويل قنواتك ومجموعاتك"
    )
    
    # تعيين الأوامر
    commands = [
        ("start", "بدء استخدام البوت"),
    ]
    await application.bot.set_my_commands(commands)

def main():
    """الدالة الرئيسية لتشغيل البوت"""
    # إنشاء التطبيق
    application = (
        Application.builder()
        .token(TOKEN)
        .post_init(post_init)
        .concurrent_updates(True)
        .build()
    )
    
    # إضافة المعالجات
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler, pattern="^(?!view_funding_).*$"))
    application.add_handler(CallbackQueryHandler(view_funding_callback, pattern="^view_funding_"))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    
    # تشغيل البوت
    print("🤖 البوت يعمل الآن...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
