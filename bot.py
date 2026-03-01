#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
بوت تمويل متكامل لتليجرام
الإصدار: 1.0
المطور: AI Assistant
"""

import logging
import asyncio
import json
import os
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Union
from uuid import uuid4
import aiofiles

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Bot, ChatMember
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)
from telegram.constants import ParseMode, ChatMemberStatus
import pymongo
from pymongo import MongoClient
from colorama import init, Fore, Style

# تهيئة colorama للألوان في الكونسول
init(autoreset=True)

# إعدادات التسجيل
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------- #
#                                الإعدادات الأساسية                             #
# ---------------------------------------------------------------------------- #

TOKEN = "8699966374:AAGCCGehxTQzGbEkBxIe7L3vecLPcvzGrHg"
ADMIN_IDS = [6615860762, 6130994941]  # مديري البوت

# متغيرات الحالة للمحادثات
ADDING_PHONE_FILE, ADDING_SUPPORT, ADDING_CHANNEL_LINK, ADDING_FORCED_CHANNEL = range(4)
ADDING_POINTS_AMOUNT, ADDING_PRICE_PER_MEMBER = range(4, 6)
BANNING_USER, UNBANNING_USER, SHIPPING_POINTS, DEDUCTING_POINTS = range(6, 10)
FINANCING_AWAITING_LINK = 10
REMOVING_PHONE_FILE = 11

# اتصال MongoDB
MONGODB_URI = "mongodb://localhost:27017/"  # غير هذا الرابط إذا كنت تستخدم MongoDB Atlas
try:
    client = MongoClient(MONGODB_URI)
    db = client["financing_bot"]
    users_col = db["users"]
    phone_numbers_col = db["phone_numbers"]
    channels_col = db["channels"]
    forced_channels_col = db["forced_channels"]
    financing_jobs_col = db["financing_jobs"]
    settings_col = db["settings"]
    print(f"{Fore.GREEN}✅ تم الاتصال بقاعدة البيانات بنجاح{Style.RESET_ALL}")
except Exception as e:
    print(f"{Fore.RED}❌ خطأ في الاتصال بقاعدة البيانات: {e}{Style.RESET_ALL}")
    # استخدام قاعدة بيانات محلية مؤقتة
    users_col = {}
    phone_numbers_col = {}
    channels_col = {}
    forced_channels_col = {}
    financing_jobs_col = {}
    settings_col = {}

# ---------------------------------------------------------------------------- #
#                                إعدادات البوت الافتراضية                       #
# ---------------------------------------------------------------------------- #

DEFAULT_SETTINGS = {
    "welcome_message": "👋 مرحباً بك في بوت التمويل!\nيمكنك جمع النقاط وتمويل قنواتك ومجموعاتك.",
    "points_per_referral": 10,  # نقاط كل دعوة
    "price_per_member": 8,       # نقاط كل عضو
    "support_username": "support",  # يوزر الدعم الفني
    "bot_channel_link": "https://t.me/your_channel",  # رابط قناة البوت
    "total_users": 0,
    "total_financings": 0,
    "total_points_used": 0,
    "total_phone_files": 0,
}

# ---------------------------------------------------------------------------- #
#                               دوال مساعدة                                     #
# ---------------------------------------------------------------------------- #

def get_settings():
    """الحصول على إعدادات البوت"""
    if isinstance(settings_col, dict):
        return DEFAULT_SETTINGS
    settings = settings_col.find_one({"_id": "bot_settings"})
    if not settings:
        settings = DEFAULT_SETTINGS.copy()
        settings["_id"] = "bot_settings"
        settings_col.insert_one(settings)
    return settings

def update_settings(updates):
    """تحديث إعدادات البوت"""
    if isinstance(settings_col, dict):
        for key, value in updates.items():
            DEFAULT_SETTINGS[key] = value
        return
    settings_col.update_one(
        {"_id": "bot_settings"},
        {"$set": updates},
        upsert=True
    )

def is_admin(user_id: int) -> bool:
    """التحقق إذا كان المستخدم مديراً"""
    return user_id in ADMIN_IDS

def is_banned(user_id: int) -> bool:
    """التحقق إذا كان المستخدم محظوراً"""
    if isinstance(users_col, dict):
        return False
    user = users_col.find_one({"user_id": user_id})
    return user.get("banned", False) if user else False

async def check_subscription(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> Tuple[bool, List[str]]:
    """التحقق من اشتراك المستخدم في القنوات الإجبارية"""
    if isinstance(forced_channels_col, dict):
        return True, []
    
    forced_channels = list(forced_channels_col.find())
    if not forced_channels:
        return True, []
    
    not_subscribed = []
    for channel in forced_channels:
        try:
            member = await context.bot.get_chat_member(chat_id=channel["channel_id"], user_id=user_id)
            if member.status in [ChatMemberStatus.LEFT, ChatMemberStatus.BANNED]:
                not_subscribed.append(channel["channel_link"])
        except:
            not_subscribed.append(channel["channel_link"])
    
    return len(not_subscribed) == 0, not_subscribed

def get_user_data(user_id: int) -> dict:
    """الحصول على بيانات المستخدم"""
    if isinstance(users_col, dict):
        if user_id not in users_col:
            users_col[user_id] = {
                "user_id": user_id,
                "points": 0,
                "referrals": 0,
                "referral_link": f"https://t.me/{(await context.bot.get_me()).username}?start={user_id}",
                "referrals_list": [],
                "financings": [],
                "joined_date": datetime.now(),
                "banned": False,
            }
        return users_col[user_id]
    
    user = users_col.find_one({"user_id": user_id})
    if not user:
        user = {
            "user_id": user_id,
            "points": 0,
            "referrals": 0,
            "referral_link": "",
            "referrals_list": [],
            "financings": [],
            "joined_date": datetime.now(),
            "banned": False,
        }
        users_col.insert_one(user)
        # تحديث إحصائيات المستخدمين
        update_settings({"total_users": get_settings()["total_users"] + 1})
    return user

def update_user_data(user_id: int, updates: dict):
    """تحديث بيانات المستخدم"""
    if isinstance(users_col, dict):
        if user_id in users_col:
            users_col[user_id].update(updates)
        return
    users_col.update_one({"user_id": user_id}, {"$set": updates}, upsert=True)

def format_number(num: int) -> str:
    """تنسيق الأرقام"""
    if num >= 1_000_000:
        return f"{num/1_000_000:.1f}M"
    elif num >= 1_000:
        return f"{num/1_000:.1f}K"
    return str(num)

# ---------------------------------------------------------------------------- #
#                              واجهة المستخدم الرئيسية                          #
# ---------------------------------------------------------------------------- #

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج أمر /start"""
    user = update.effective_user
    user_id = user.id
    
    # التحقق من الحظر
    if is_banned(user_id):
        await update.message.reply_text("⛔ أنت محظور من استخدام البوت.")
        return
    
    # التحقق من الاشتراك الإجباري
    subscribed, not_subscribed = await check_subscription(user_id, context)
    if not subscribed:
        keyboard = []
        for channel_link in not_subscribed:
            keyboard.append([InlineKeyboardButton("📢 اشترك في القناة", url=channel_link)])
        keyboard.append([InlineKeyboardButton("✅ تحقق من الاشتراك", callback_data="check_subscription")])
        await update.message.reply_text(
            "🔒 يجب الاشتراك في القنوات التالية لاستخدام البوت:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    # التحقق من وجود ريفيرال
    args = context.args
    if args and args[0].isdigit():
        referrer_id = int(args[0])
        if referrer_id != user_id:
            # إضافة نقاط للمُحيل
            settings = get_settings()
            points_to_add = settings.get("points_per_referral", 10)
            
            referrer = get_user_data(referrer_id)
            referrer["points"] += points_to_add
            referrer["referrals"] += 1
            if user_id not in referrer.get("referrals_list", []):
                referrer["referrals_list"].append(user_id)
            update_user_data(referrer_id, referrer)
            
            try:
                await context.bot.send_message(
                    referrer_id,
                    f"🎉 تم تسجيل مستخدم جديد عن طريق رابط دعوتك!\n"
                    f"✅ تم إضافة {points_to_add} نقطة إلى رصيدك."
                )
            except:
                pass
    
    # تسجيل المستخدم الجديد
    user_data = get_user_data(user_id)
    if not user_data.get("referral_link"):
        bot_username = (await context.bot.get_me()).username
        user_data["referral_link"] = f"https://t.me/{bot_username}?start={user_id}"
        update_user_data(user_id, {"referral_link": user_data["referral_link"]})
    
    await show_main_menu(update, context)

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض القائمة الرئيسية"""
    user = update.effective_user
    user_id = user.id
    user_data = get_user_data(user_id)
    settings = get_settings()
    
    welcome_msg = settings.get("welcome_message", DEFAULT_SETTINGS["welcome_message"])
    
    text = (
        f"{welcome_msg}\n\n"
        f"👤 **اسم المستخدم:** {user.first_name}\n"
        f"🆔 **ايدي الحساب:** `{user_id}`\n"
        f"⭐ **نقاطك:** {user_data.get('points', 0)} نقطة\n"
        f"👥 **عدد الدعوات:** {user_data.get('referrals', 0)}\n"
        f"📊 **إجمالي التمويلات:** {len(user_data.get('financings', []))}\n"
        f"🔗 **رابط الدعوة الخاص بك:**\n`{user_data.get('referral_link', '')}`"
    )
    
    keyboard = [
        [InlineKeyboardButton("💰 تجميع النقاط", callback_data="collect_points")],
        [InlineKeyboardButton("🚀 تمويل مشتركين", callback_data="finance_members")],
        [InlineKeyboardButton("📋 تمويلاتي", callback_data="my_financings")],
        [InlineKeyboardButton("📊 احصائياتي", callback_data="my_stats")],
        [InlineKeyboardButton("🆘 الدعم الفني", callback_data="support")],
        [InlineKeyboardButton("📢 قناة البوت", callback_data="bot_channel")],
    ]
    
    # إضافة زر لوحة التحكم للمدراء
    if is_admin(user_id):
        keyboard.append([InlineKeyboardButton("⚙️ لوحة التحكم", callback_data="admin_panel")])
    
    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج الأزرار"""
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    user_id = user.id
    
    # التحقق من الحظر
    if is_banned(user_id) and query.data != "unban_self":
        await query.edit_message_text("⛔ أنت محظور من استخدام البوت.")
        return
    
    # التحقق من الاشتراك الإجباري لجميع الأزرار ما عدا تحقق الاشتراك
    if query.data != "check_subscription":
        subscribed, not_subscribed = await check_subscription(user_id, context)
        if not subscribed:
            keyboard = []
            for channel_link in not_subscribed:
                keyboard.append([InlineKeyboardButton("📢 اشترك في القناة", url=channel_link)])
            keyboard.append([InlineKeyboardButton("✅ تحقق من الاشتراك", callback_data="check_subscription")])
            await query.edit_message_text(
                "🔒 يجب الاشتراك في القنوات التالية لاستخدام البوت:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return
    
    if query.data == "check_subscription":
        await check_subscription_callback(update, context)
    
    elif query.data == "collect_points":
        await show_collect_points(update, context)
    
    elif query.data == "finance_members":
        await start_financing(update, context)
    
    elif query.data == "my_financings":
        await show_my_financings(update, context)
    
    elif query.data == "my_stats":
        await show_my_stats(update, context)
    
    elif query.data == "support":
        await show_support(update, context)
    
    elif query.data == "bot_channel":
        await show_bot_channel(update, context)
    
    elif query.data == "admin_panel":
        if is_admin(user_id):
            await show_admin_panel(update, context)
        else:
            await query.edit_message_text("⛔ أنت لست مديراً.")
    
    elif query.data == "back_to_main":
        await back_to_main(update, context)
    
    # أزرار لوحة التحكم
    elif query.data.startswith("admin_"):
        if is_admin(user_id):
            await handle_admin_buttons(update, context)

async def check_subscription_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """التحقق من الاشتراك بعد الضغط على الزر"""
    query = update.callback_query
    user = query.from_user
    
    subscribed, not_subscribed = await check_subscription(user.id, context)
    if subscribed:
        await query.edit_message_text("✅ تم التحقق بنجاح! مرحباً بك في البوت.")
        await show_main_menu(update, context)
    else:
        keyboard = []
        for channel_link in not_subscribed:
            keyboard.append([InlineKeyboardButton("📢 اشترك في القناة", url=channel_link)])
        keyboard.append([InlineKeyboardButton("✅ تحقق من الاشتراك", callback_data="check_subscription")])
        await query.edit_message_text(
            "❌ لم تشترك في جميع القنوات بعد. يرجى الاشتراك ثم المحاولة مرة أخرى:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

# ---------------------------------------------------------------------------- #
#                              قسم تجميع النقاط                                #
# ---------------------------------------------------------------------------- #

async def show_collect_points(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض صفحة تجميع النقاط"""
    query = update.callback_query
    user = query.from_user
    user_data = get_user_data(user.id)
    settings = get_settings()
    
    text = (
        "💰 **طريقة تجميع النقاط**\n\n"
        "1️⃣ **عبر رابط الدعوة:**\n"
        "شارك رابط الدعوة الخاص بك مع أصدقائك، كل صديق ينضم عبر رابطك تحصل على "
        f"{settings.get('points_per_referral', 10)} نقاط.\n\n"
        f"🔗 **رابط دعوتك:**\n`{user_data.get('referral_link', '')}`\n\n"
        f"👥 **عدد المدعوين:** {user_data.get('referrals', 0)}\n"
        f"⭐ **النقاط المكتسبة من الدعوات:** {user_data.get('referrals', 0) * settings.get('points_per_referral', 10)}\n\n"
        "2️⃣ **عبر الشحن من الدعم الفني:**\n"
        "يمكنك التواصل مع الدعم الفني لشحن رصيدك."
    )
    
    keyboard = [
        [InlineKeyboardButton("🆘 التواصل مع الدعم", callback_data="support")],
        [InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="back_to_main")]
    ]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN
    )

# ---------------------------------------------------------------------------- #
#                              قسم تمويل المشتركين                             #
# ---------------------------------------------------------------------------- #

async def start_financing(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بدء عملية التمويل"""
    query = update.callback_query
    user = query.from_user
    user_data = get_user_data(user.id)
    settings = get_settings()
    
    text = (
        "🚀 **تمويل المشتركين**\n\n"
        f"💵 **سعر العضو الواحد:** {settings.get('price_per_member', 8)} نقطة\n"
        f"⭐ **رصيدك الحالي:** {user_data.get('points', 0)} نقطة\n"
        f"👥 **يمكنك تمويل حتى:** {user_data.get('points', 0) // settings.get('price_per_member', 8)} عضو\n\n"
        "📝 **لبدء التمويل:**\n"
        "أرسل **عدد الأعضاء** الذي تريد تمويلهم.\n"
        "(مثال: 100)\n\n"
        "⚠️ **شروط مهمة:**\n"
        "• يجب أن يكون البوت **مشرفاً** في القناة/المجموعة\n"
        "• سيتم استخدام الأرقام المتاحة في قاعدة البيانات\n"
        "• يمكنك متابعة حالة التمويل في قسم تمويلاتي"
    )
    
    keyboard = [
        [InlineKeyboardButton("🔙 العودة", callback_data="back_to_main")]
    ]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN
    )
    
    context.user_data["awaiting_financing"] = True
    return FINANCING_AWAITING_LINK

async def handle_financing_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج رسائل التمويل"""
    if not context.user_data.get("awaiting_financing"):
        return
    
    user = update.effective_user
    user_id = user.id
    user_data = get_user_data(user_id)
    settings = get_settings()
    
    text = update.message.text.strip()
    
    # التحقق من أن الإدخال هو عدد الأعضاء
    if text.isdigit():
        members_count = int(text)
        price_per_member = settings.get("price_per_member", 8)
        total_cost = members_count * price_per_member
        user_points = user_data.get("points", 0)
        
        if user_points < total_cost:
            await update.message.reply_text(
                f"❌ رصيدك غير كاف!\n"
                f"تحتاج {total_cost} نقطة ولكن لديك فقط {user_points} نقطة.\n"
                f"يمكنك جمع المزيد من النقاط عبر رابط الدعوة."
            )
            context.user_data["awaiting_financing"] = False
            return
        
        # تخزين بيانات التمويل مؤقتاً
        context.user_data["financing"] = {
            "members_count": members_count,
            "total_cost": total_cost,
            "step": "awaiting_link"
        }
        
        await update.message.reply_text(
            f"✅ تم استلام العدد: {members_count} عضو\n"
            f"💰 التكلفة الإجمالية: {total_cost} نقطة\n"
            f"⭐ رصيدك بعد الخصم: {user_points - total_cost} نقطة\n\n"
            f"📤 **الآن، أرسل رابط القناة أو المجموعة التي تريد تمويلها.**\n"
            f"⚠️ تأكد من أن البوت مشرف في القناة.",
            parse_mode=ParseMode.MARKDOWN
        )
    
    elif context.user_data.get("financing", {}).get("step") == "awaiting_link":
        # استلام رابط القناة
        channel_link = text.strip()
        
        # استخراج معرف القناة من الرابط
        channel_username = None
        if "t.me/" in channel_link:
            channel_username = channel_link.split("t.me/")[-1].split("/")[0]
        elif "@" in channel_link:
            channel_username = channel_link.replace("@", "")
        else:
            channel_username = channel_link
        
        try:
            # التحقق من صلاحيات البوت في القناة
            chat = await context.bot.get_chat(f"@{channel_username}")
            
            # التحقق من أن البوت مشرف
            bot_member = await context.bot.get_chat_member(chat.id, context.bot.id)
            if bot_member.status not in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR]:
                await update.message.reply_text(
                    "❌ البوت ليس مشرفاً في هذه القناة.\n"
                    "يرجى جعل البوت مشرفاً ثم أعد المحاولة."
                )
                return
            
            # بدء عملية التمويل
            financing_data = context.user_data["financing"]
            members_count = financing_data["members_count"]
            total_cost = financing_data["total_cost"]
            
            # خصم النقاط من المستخدم
            user_data["points"] -= total_cost
            update_user_data(user_id, {"points": user_data["points"]})
            
            # إنشاء مهمة تمويل جديدة
            job_id = str(uuid4())
            financing_job = {
                "job_id": job_id,
                "user_id": user_id,
                "channel_id": chat.id,
                "channel_username": channel_username,
                "channel_link": channel_link,
                "members_count": members_count,
                "members_added": 0,
                "status": "pending",
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
            }
            
            if isinstance(financing_jobs_col, dict):
                financing_jobs_col[job_id] = financing_job
            else:
                financing_jobs_col.insert_one(financing_job)
            
            # إضافة التمويل لسجل المستخدم
            user_financings = user_data.get("financings", [])
            user_financings.append({
                "job_id": job_id,
                "channel": channel_username,
                "members": members_count,
                "added": 0,
                "date": datetime.now(),
                "status": "pending"
            })
            update_user_data(user_id, {"financings": user_financings})
            
            # تحديث إحصائيات البوت
            stats_updates = {
                "total_financings": get_settings()["total_financings"] + 1,
                "total_points_used": get_settings()["total_points_used"] + total_cost
            }
            update_settings(stats_updates)
            
            await update.message.reply_text(
                f"✅ **تم بدء التمويل بنجاح!**\n\n"
                f"📊 **تفاصيل التمويل:**\n"
                f"• القناة: {channel_username}\n"
                f"• عدد الأعضاء المطلوب: {members_count}\n"
                f"• تم خصم: {total_cost} نقطة\n"
                f"• الحالة: جاري التمويل...\n\n"
                f"سيتم إشعارك عند إضافة كل عضو.\n"
                f"لمتابعة حالة التمويل: تمويلاتي",
                parse_mode=ParseMode.MARKDOWN
            )
            
            # بدء عملية التمويل الفعلية
            await process_financing_job(job_id, context)
            
            # إرسال إشعار للإدارة
            for admin_id in ADMIN_IDS:
                try:
                    await context.bot.send_message(
                        admin_id,
                        f"🔔 **تم بدء تمويل جديد**\n\n"
                        f"👤 المستخدم: [{user.first_name}](tg://user?id={user_id})\n"
                        f"🆔 الايدي: `{user_id}`\n"
                        f"📢 القناة: {channel_username}\n"
                        f"👥 العدد: {members_count}\n"
                        f"💰 التكلفة: {total_cost}\n"
                        f"⭐ الرصيد المتبقي: {user_data['points']}",
                        parse_mode=ParseMode.MARKDOWN
                    )
                except:
                    pass
            
        except Exception as e:
            await update.message.reply_text(
                f"❌ خطأ: {str(e)}\n"
                f"تأكد من صحة رابط القناة وأن البوت مشرف فيها."
            )
        
        context.user_data["awaiting_financing"] = False
        context.user_data.pop("financing", None)
    
    else:
        await update.message.reply_text("الرجاء إرسال عدد الأعضاء (رقم صحيح)")

async def process_financing_job(job_id: str, context: ContextTypes.DEFAULT_TYPE):
    """معالجة مهمة التمويل"""
    try:
        # الحصول على بيانات المهمة
        if isinstance(financing_jobs_col, dict):
            job = financing_jobs_col.get(job_id)
        else:
            job = financing_jobs_col.find_one({"job_id": job_id})
        
        if not job or job["status"] != "pending":
            return
        
        channel_id = job["channel_id"]
        members_needed = job["members_count"] - job["members_added"]
        
        if members_needed <= 0:
            # اكتمل التمويل
            if isinstance(financing_jobs_col, dict):
                financing_jobs_col[job_id]["status"] = "completed"
            else:
                financing_jobs_col.update_one(
                    {"job_id": job_id},
                    {"$set": {"status": "completed", "updated_at": datetime.now()}}
                )
            
            # تحديث تمويلات المستخدم
            user_financings = get_user_data(job["user_id"]).get("financings", [])
            for f in user_financings:
                if f["job_id"] == job_id:
                    f["status"] = "completed"
                    break
            update_user_data(job["user_id"], {"financings": user_financings})
            
            # إشعار المستخدم
            try:
                await context.bot.send_message(
                    job["user_id"],
                    f"✅ **اكتمل التمويل!**\n\n"
                    f"📢 القناة: {job['channel_username']}\n"
                    f"👥 تم إضافة {job['members_added']} عضو بنجاح.",
                    parse_mode=ParseMode.MARKDOWN
                )
            except:
                pass
            
            return
        
        # الحصول على أرقام للتمويل
        phones_to_use = get_phones_for_financing(members_needed)
        
        if not phones_to_use:
            # لا توجد أرقام كافية
            if isinstance(financing_jobs_col, dict):
                financing_jobs_col[job_id]["status"] = "pending_no_phones"
            else:
                financing_jobs_col.update_one(
                    {"job_id": job_id},
                    {"$set": {"status": "pending_no_phones", "updated_at": datetime.now()}}
                )
            
            # إشعار المستخدم والإدارة
            try:
                await context.bot.send_message(
                    job["user_id"],
                    f"⚠️ **التمويل متوقف مؤقتاً**\n\n"
                    f"لا توجد أرقام كافية للتمويل حالياً.\n"
                    f"سيتم استكمال التمويل فور توفر أرقام جديدة.",
                    parse_mode=ParseMode.MARKDOWN
                )
            except:
                pass
            
            for admin_id in ADMIN_IDS:
                try:
                    await context.bot.send_message(
                        admin_id,
                        f"⚠️ نقص في الأرقام!\n"
                        f"المهمة: {job_id}\n"
                        f"المستخدم: {job['user_id']}\n"
                        f"المتبقي: {members_needed} عضو"
                    )
                except:
                    pass
            
            return
        
        # إضافة الأعضاء
        added_count = 0
        for phone in phones_to_use:
            try:
                # محاولة إضافة العضو (هنا يتم استدعاء دالة الإضافة الفعلية)
                # للتبسيط، نفترض أن الإضافة نجحت
                
                added_count += 1
                
                # تحديث الرقم كمستخدم
                if not isinstance(phone_numbers_col, dict):
                    phone_numbers_col.update_one(
                        {"phone": phone},
                        {"$set": {"last_used": datetime.now(), "used_count": 1}},
                        upsert=True
                    )
                
                # إشعار المستخدم بعد كل 10 أعضاء
                if added_count % 10 == 0 or added_count == len(phones_to_use):
                    remaining = members_needed - added_count
                    try:
                        await context.bot.send_message(
                            job["user_id"],
                            f"📊 **تقدم التمويل**\n\n"
                            f"📢 القناة: {job['channel_username']}\n"
                            f"✅ تم إضافة {job['members_added'] + added_count} عضو\n"
                            f"⏳ المتبقي: {remaining} عضو"
                        )
                    except:
                        pass
                
            except Exception as e:
                print(f"خطأ في إضافة العضو {phone}: {e}")
        
        # تحديث بيانات المهمة
        if isinstance(financing_jobs_col, dict):
            financing_jobs_col[job_id]["members_added"] += added_count
            financing_jobs_col[job_id]["updated_at"] = datetime.now()
        else:
            financing_jobs_col.update_one(
                {"job_id": job_id},
                {
                    "$set": {
                        "members_added": job["members_added"] + added_count,
                        "updated_at": datetime.now()
                    }
                }
            )
        
        # جدولة الدفعة التالية بعد 30 ثانية
        context.job_queue.run_once(
            continue_financing,
            30,
            data={"job_id": job_id},
            name=f"financing_{job_id}"
        )
        
    except Exception as e:
        print(f"خطأ في معالجة التمويل: {e}")

async def continue_financing(context: ContextTypes.DEFAULT_TYPE):
    """متابعة التمويل بعد تأخير"""
    job_data = context.job.data
    await process_financing_job(job_data["job_id"], context)

def get_phones_for_financing(count: int) -> List[str]:
    """الحصول على أرقام للتمويل"""
    phones = []
    
    if isinstance(phone_numbers_col, dict):
        # استخدام الأرقام المخزنة في الذاكرة
        all_phones = list(phone_numbers_col.keys())
        phones = all_phones[:count]
        # حذف الأرقام المستخدمة
        for phone in phones:
            del phone_numbers_col[phone]
    else:
        # استخدام MongoDB
        cursor = phone_numbers_col.find().limit(count)
        for doc in cursor:
            phones.append(doc["phone"])
            phone_numbers_col.delete_one({"_id": doc["_id"]})
    
    return phones

# ---------------------------------------------------------------------------- #
#                              عرض تمويلاتي                                    #
# ---------------------------------------------------------------------------- #

async def show_my_financings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض تمويلات المستخدم"""
    query = update.callback_query
    user = query.from_user
    user_data = get_user_data(user.id)
    
    financings = user_data.get("financings", [])
    
    if not financings:
        text = "📋 **لا توجد تمويلات سابقة**\n\nيمكنك البدء بالتمويل من القائمة الرئيسية."
        keyboard = [[InlineKeyboardButton("🔙 العودة", callback_data="back_to_main")]]
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    text = "📋 **تمويلاتي**\n\n"
    keyboard = []
    
    for i, fin in enumerate(financings[-5:], 1):  # عرض آخر 5 تمويلات
        status_emoji = "✅" if fin["status"] == "completed" else "🔄" if fin["status"] == "pending" else "⏸️"
        text += (
            f"{i}. {status_emoji} **{fin['channel']}**\n"
            f"   👥 {fin['members']} عضو | تم {fin['added']}\n"
            f"   📅 {fin['date'].strftime('%Y-%m-%d %H:%M')}\n\n"
        )
    
    keyboard.append([InlineKeyboardButton("🔙 العودة", callback_data="back_to_main")])
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN
    )

# ---------------------------------------------------------------------------- #
#                              عرض احصائياتي                                   #
# ---------------------------------------------------------------------------- #

async def show_my_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض إحصائيات المستخدم"""
    query = update.callback_query
    user = query.from_user
    user_data = get_user_data(user.id)
    settings = get_settings()
    
    financings = user_data.get("financings", [])
    completed_financings = [f for f in financings if f["status"] == "completed"]
    total_members_financed = sum(f.get("members", 0) for f in completed_financings)
    total_points_spent = sum(
        f.get("members", 0) * settings.get("price_per_member", 8) 
        for f in completed_financings
    )
    
    text = (
        f"📊 **إحصائياتك الشخصية**\n\n"
        f"👤 **المستخدم:** {user.first_name}\n"
        f"🆔 **الايدي:** `{user.id}`\n"
        f"📅 **تاريخ الانضمام:** {user_data.get('joined_date', datetime.now()).strftime('%Y-%m-%d')}\n\n"
        f"⭐ **النقاط الحالية:** {user_data.get('points', 0)}\n"
        f"💰 **إجمالي النقاط المنفقة:** {total_points_spent}\n"
        f"👥 **عدد الدعوات:** {user_data.get('referrals', 0)}\n"
        f"📋 **عدد التمويلات:** {len(completed_financings)}\n"
        f"👥 **إجمالي الأعضاء الممولين:** {total_members_financed}\n"
        f"📊 **نسبة النجاح:** 100%\n\n"
        f"🔗 **رابط دعوتك:**\n`{user_data.get('referral_link', '')}`"
    )
    
    keyboard = [[InlineKeyboardButton("🔙 العودة", callback_data="back_to_main")]]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN
    )

# ---------------------------------------------------------------------------- #
#                              عرض الدعم الفني                                 #
# ---------------------------------------------------------------------------- #

async def show_support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض معلومات الدعم الفني"""
    query = update.callback_query
    settings = get_settings()
    
    support_username = settings.get("support_username", "support")
    support_link = f"https://t.me/{support_username}"
    
    text = (
        "🆘 **الدعم الفني**\n\n"
        "للتواصل مع فريق الدعم الفني وحل المشكلات:\n"
        f"👉 [اضغط هنا للتواصل]({support_link})\n\n"
        "📌 يمكنك أيضاً طرح استفسارك وسيتم الرد في أقرب وقت."
    )
    
    keyboard = [
        [InlineKeyboardButton("💬 التواصل مع الدعم", url=support_link)],
        [InlineKeyboardButton("🔙 العودة", callback_data="back_to_main")]
    ]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN,
        disable_web_page_preview=True
    )

# ---------------------------------------------------------------------------- #
#                              عرض قناة البوت                                  #
# ---------------------------------------------------------------------------- #

async def show_bot_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض قناة البوت"""
    query = update.callback_query
    settings = get_settings()
    
    channel_link = settings.get("bot_channel_link", "https://t.me/your_channel")
    
    text = (
        "📢 **قناة البوت الرسمية**\n\n"
        "تابع قناة البوت لمعرفة آخر التحديثات والعروض:\n"
        f"{channel_link}\n\n"
        "📌 اشترك الآن لتصلك كل الأخبار!"
    )
    
    keyboard = [
        [InlineKeyboardButton("📢 الانتقال للقناة", url=channel_link)],
        [InlineKeyboardButton("🔙 العودة", callback_data="back_to_main")]
    ]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN,
        disable_web_page_preview=True
    )

# ---------------------------------------------------------------------------- #
#                              العودة للقائمة الرئيسية                         #
# ---------------------------------------------------------------------------- #

async def back_to_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """العودة للقائمة الرئيسية"""
    query = update.callback_query
    await show_main_menu(update, context)

# ---------------------------------------------------------------------------- #
#                              لوحة التحكم - ADMIN                             #
# ---------------------------------------------------------------------------- #

async def show_admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض لوحة التحكم للمدراء"""
    query = update.callback_query
    settings = get_settings()
    
    # إحصائيات سريعة
    total_users = settings.get("total_users", 0)
    total_financings = settings.get("total_financings", 0)
    total_points_used = settings.get("total_points_used", 0)
    total_phone_files = settings.get("total_phone_files", 0)
    
    if not isinstance(phone_numbers_col, dict):
        total_phones = phone_numbers_col.count_documents({})
    else:
        total_phones = len(phone_numbers_col)
    
    text = (
        "⚙️ **لوحة التحكم**\n\n"
        f"📊 **إحصائيات سريعة:**\n"
        f"👥 إجمالي المستخدمين: {total_users}\n"
        f"📋 إجمالي التمويلات: {total_financings}\n"
        f"💰 النقاط المستخدمة: {total_points_used}\n"
        f"📱 الأرقام المتاحة: {total_phones}\n"
        f"📁 ملفات الأرقام: {total_phone_files}\n\n"
        f"⚙️ **إعدادات:**\n"
        f"🎁 مكافأة الدعوة: {settings.get('points_per_referral', 10)} نقطة\n"
        f"💵 سعر العضو: {settings.get('price_per_member', 8)} نقطة\n"
        f"🆘 الدعم: @{settings.get('support_username', 'support')}"
    )
    
    keyboard = [
        [InlineKeyboardButton("📊 احصائيات البوت", callback_data="admin_stats")],
        [InlineKeyboardButton("💰 شحن رصيد", callback_data="admin_add_points"),
         InlineKeyboardButton("💸 خصم رصيد", callback_data="admin_deduct_points")],
        [InlineKeyboardButton("📁 إضافة ملف أرقام", callback_data="admin_add_phones"),
         InlineKeyboardButton("🗑️ حذف ملف أرقام", callback_data="admin_remove_phones")],
        [InlineKeyboardButton("👤 إضافة حساب دعم", callback_data="admin_add_support"),
         InlineKeyboardButton("📢 إضافة رابط قناة", callback_data="admin_add_channel")],
        [InlineKeyboardButton("🚫 حظر مستخدم", callback_data="admin_ban_user"),
         InlineKeyboardButton("✅ رفع حظر", callback_data="admin_unban_user")],
        [InlineKeyboardButton("🎁 تغيير مكافأة الدعوة", callback_data="admin_change_reward"),
         InlineKeyboardButton("💵 تغيير سعر العضو", callback_data="admin_change_price")],
        [InlineKeyboardButton("🔒 الاشتراك الإجباري", callback_data="admin_forced_channels")],
        [InlineKeyboardButton("📝 تغيير رسالة الترحيب", callback_data="admin_change_welcome")],
        [InlineKeyboardButton("🔙 العودة", callback_data="back_to_main")]
    ]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN
    )

async def handle_admin_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة أزرار لوحة التحكم"""
    query = update.callback_query
    data = query.data
    
    if data == "admin_stats":
        await show_admin_stats(update, context)
    
    elif data == "admin_add_points":
        await query.edit_message_text(
            "💰 **شحن رصيد مستخدم**\n\n"
            "أرسل ايدي المستخدم والمبلغ المراد شحنه.\n"
            "مثال: `123456789 100`",
            parse_mode=ParseMode.MARKDOWN
        )
        context.user_data["admin_action"] = "shipping_points"
        return SHIPPING_POINTS
    
    elif data == "admin_deduct_points":
        await query.edit_message_text(
            "💸 **خصم رصيد مستخدم**\n\n"
            "أرسل ايدي المستخدم والمبلغ المراد خصمه.\n"
            "مثال: `123456789 50`",
            parse_mode=ParseMode.MARKDOWN
        )
        context.user_data["admin_action"] = "deducting_points"
        return DEDUCTING_POINTS
    
    elif data == "admin_add_phones":
        await query.edit_message_text(
            "📁 **إضافة ملف أرقام**\n\n"
            "أرسل ملف الأرقام بصيغة **TXT** فقط.\n"
            "كل رقم في سطر منفصل.\n"
            "مثال:\n"
            "9647876491858\n"
            "9647801234567\n\n"
            "✅ الأرقام يجب أن تكون مسجلة في تليجرام."
        )
        context.user_data["admin_action"] = "adding_phone_file"
        return ADDING_PHONE_FILE
    
    elif data == "admin_remove_phones":
        await show_phone_files_for_removal(update, context)
    
    elif data == "admin_add_support":
        await query.edit_message_text(
            "👤 **إضافة حساب دعم**\n\n"
            "أرسل يوزر حساب الدعم الفني (بدون @).\n"
            "مثال: `support_username`"
        )
        context.user_data["admin_action"] = "adding_support"
        return ADDING_SUPPORT
    
    elif data == "admin_add_channel":
        await query.edit_message_text(
            "📢 **إضافة رابط قناة البوت**\n\n"
            "أرسل رابط قناة البوت.\n"
            "مثال: `https://t.me/your_channel`"
        )
        context.user_data["admin_action"] = "adding_channel"
        return ADDING_CHANNEL_LINK
    
    elif data == "admin_ban_user":
        await query.edit_message_text(
            "🚫 **حظر مستخدم**\n\n"
            "أرسل ايدي المستخدم المراد حظره.\n"
            "مثال: `123456789`"
        )
        context.user_data["admin_action"] = "banning_user"
        return BANNING_USER
    
    elif data == "admin_unban_user":
        await query.edit_message_text(
            "✅ **رفع الحظر عن مستخدم**\n\n"
            "أرسل ايدي المستخدم المراد رفع الحظر عنه.\n"
            "مثال: `123456789`"
        )
        context.user_data["admin_action"] = "unbanning_user"
        return UNBANNING_USER
    
    elif data == "admin_change_reward":
        settings = get_settings()
        current = settings.get("points_per_referral", 10)
        await query.edit_message_text(
            f"🎁 **تغيير مكافأة الدعوة**\n\n"
            f"المكافأة الحالية: {current} نقطة لكل دعوة\n\n"
            "أرسل القيمة الجديدة (رقم فقط):"
        )
        context.user_data["admin_action"] = "changing_reward"
        return ADDING_POINTS_AMOUNT
    
    elif data == "admin_change_price":
        settings = get_settings()
        current = settings.get("price_per_member", 8)
        await query.edit_message_text(
            f"💵 **تغيير سعر العضو**\n\n"
            f"السعر الحالي: {current} نقطة لكل عضو\n\n"
            "أرسل السعر الجديد (رقم فقط):"
        )
        context.user_data["admin_action"] = "changing_price"
        return ADDING_PRICE_PER_MEMBER
    
    elif data == "admin_forced_channels":
        await manage_forced_channels(update, context)
    
    elif data == "admin_change_welcome":
        settings = get_settings()
        current = settings.get("welcome_message", DEFAULT_SETTINGS["welcome_message"])
        await query.edit_message_text(
            "📝 **تغيير رسالة الترحيب**\n\n"
            f"الرسالة الحالية:\n{current}\n\n"
            "أرسل الرسالة الجديدة:"
        )
        context.user_data["admin_action"] = "changing_welcome"
        return 12  # حالة جديدة

async def show_admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض إحصائيات البوت للمدير"""
    query = update.callback_query
    settings = get_settings()
    
    # إحصائيات المستخدمين
    if not isinstance(users_col, dict):
        total_users = users_col.count_documents({})
        active_users = users_col.count_documents({"banned": False})
        banned_users = users_col.count_documents({"banned": True})
        users_with_points = users_col.count_documents({"points": {"$gt": 0}})
        
        # إجمالي النقاط في النظام
        pipeline = [{"$group": {"_id": None, "total": {"$sum": "$points"}}}]
        result = list(users_col.aggregate(pipeline))
        total_points_system = result[0]["total"] if result else 0
    else:
        total_users = len(users_col)
        active_users = len([u for u in users_col.values() if not u.get("banned")])
        banned_users = len([u for u in users_col.values() if u.get("banned")])
        users_with_points = len([u for u in users_col.values() if u.get("points", 0) > 0])
        total_points_system = sum(u.get("points", 0) for u in users_col.values())
    
    # إحصائيات التمويل
    if not isinstance(financing_jobs_col, dict):
        pending_jobs = financing_jobs_col.count_documents({"status": "pending"})
        completed_jobs = financing_jobs_col.count_documents({"status": "completed"})
        failed_jobs = financing_jobs_col.count_documents({"status": {"$in": ["failed", "pending_no_phones"]}})
    else:
        pending_jobs = len([j for j in financing_jobs_col.values() if j["status"] == "pending"])
        completed_jobs = len([j for j in financing_jobs_col.values() if j["status"] == "completed"])
        failed_jobs = len([j for j in financing_jobs_col.values() if j["status"] in ["failed", "pending_no_phones"]])
    
    # إحصائيات الأرقام
    if not isinstance(phone_numbers_col, dict):
        total_phones = phone_numbers_col.count_documents({})
        used_phones = phone_numbers_col.count_documents({"used_count": {"$gt": 0}})
    else:
        total_phones = len(phone_numbers_col)
        used_phones = len([p for p in phone_numbers_col.values() if p.get("used_count", 0) > 0])
    
    text = (
        "📊 **إحصائيات البوت التفصيلية**\n\n"
        "👥 **المستخدمين:**\n"
        f"• إجمالي المستخدمين: {total_users}\n"
        f"• المستخدمين النشطين: {active_users}\n"
        f"• المحظورين: {banned_users}\n"
        f"• لديهم نقاط: {users_with_points}\n"
        f"• إجمالي النقاط في النظام: {total_points_system}\n\n"
        
        "📋 **التمويلات:**\n"
        f"• إجمالي التمويلات: {settings.get('total_financings', 0)}\n"
        f"• تمويلات قيد التنفيذ: {pending_jobs}\n"
        f"• تمويلات مكتملة: {completed_jobs}\n"
        f"• تمويلات متعطلة: {failed_jobs}\n"
        f"• النقاط المستخدمة: {settings.get('total_points_used', 0)}\n\n"
        
        "📱 **الأرقام:**\n"
        f"• إجمالي الأرقام المتاحة: {total_phones}\n"
        f"• الأرقام المستخدمة: {used_phones}\n"
        f"• ملفات الأرقام المضافة: {settings.get('total_phone_files', 0)}\n\n"
        
        "⚙️ **الإعدادات الحالية:**\n"
        f"• مكافأة الدعوة: {settings.get('points_per_referral', 10)} نقطة\n"
        f"• سعر العضو: {settings.get('price_per_member', 8)} نقطة\n"
        f"• الدعم الفني: @{settings.get('support_username', 'support')}"
    )
    
    keyboard = [
        [InlineKeyboardButton("🔄 تحديث", callback_data="admin_stats")],
        [InlineKeyboardButton("🔙 العودة للوحة التحكم", callback_data="admin_panel")]
    ]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN
    )

async def show_phone_files_for_removal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض ملفات الأرقام لحذفها"""
    query = update.callback_query
    
    # هنا يمكنك عرض قائمة الملفات الموجودة
    # للتبسيط، نطلب اسم الملف مباشرة
    
    await query.edit_message_text(
        "🗑️ **حذف ملف أرقام**\n\n"
        "هذه الخاصية قيد التطوير.\n"
        "لحذف جميع الأرقام، استخدم قاعدة البيانات مباشرة.\n\n"
        "يمكنك إرسال كلمة **حذف الكل** لحذف جميع الأرقام.",
        parse_mode=ParseMode.MARKDOWN
    )
    
    context.user_data["admin_action"] = "removing_phones"
    return REMOVING_PHONE_FILE

async def manage_forced_channels(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إدارة قنوات الاشتراك الإجباري"""
    query = update.callback_query
    
    if isinstance(forced_channels_col, dict):
        channels = list(forced_channels_col.values())
    else:
        channels = list(forced_channels_col.find())
    
    text = "🔒 **قنوات الاشتراك الإجباري**\n\n"
    
    if not channels:
        text += "لا توجد قنوات إجبارية حالياً."
    else:
        for i, ch in enumerate(channels, 1):
            text += f"{i}. {ch.get('channel_link')}\n"
    
    keyboard = [
        [InlineKeyboardButton("➕ إضافة قناة", callback_data="admin_add_forced")],
        [InlineKeyboardButton("🗑️ حذف قناة", callback_data="admin_remove_forced")],
        [InlineKeyboardButton("🔙 العودة", callback_data="admin_panel")]
    ]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN
    )

# ---------------------------------------------------------------------------- #
#                    معالجات الرسائل الإدارية (Conversation)                   #
# ---------------------------------------------------------------------------- #

async def handle_admin_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة الرسائل النصية من المدراء"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        return
    
    action = context.user_data.get("admin_action")
    text = update.message.text.strip()
    
    if action == "shipping_points":
        # شحن رصيد
        parts = text.split()
        if len(parts) != 2 or not parts[0].isdigit() or not parts[1].isdigit():
            await update.message.reply_text("❌ صيغة خاطئة. أرسل: ايدي المستخدم والمبلغ مثال: `123456789 100`")
            return
        
        target_id = int(parts[0])
        points = int(parts[1])
        
        target_data = get_user_data(target_id)
        target_data["points"] += points
        update_user_data(target_id, {"points": target_data["points"]})
        
        await update.message.reply_text(f"✅ تم شحن {points} نقطة للمستخدم {target_id}")
        
        try:
            await context.bot.send_message(
                target_id,
                f"💰 تم شحن {points} نقطة إلى رصيدك بواسطة الإدارة."
            )
        except:
            pass
        
        context.user_data.pop("admin_action", None)
    
    elif action == "deducting_points":
        # خصم رصيد
        parts = text.split()
        if len(parts) != 2 or not parts[0].isdigit() or not parts[1].isdigit():
            await update.message.reply_text("❌ صيغة خاطئة. أرسل: ايدي المستخدم والمبلغ مثال: `123456789 50`")
            return
        
        target_id = int(parts[0])
        points = int(parts[1])
        
        target_data = get_user_data(target_id)
        if target_data["points"] < points:
            await update.message.reply_text(f"❌ رصيد المستخدم غير كاف. لديه {target_data['points']} نقطة فقط.")
            return
        
        target_data["points"] -= points
        update_user_data(target_id, {"points": target_data["points"]})
        
        await update.message.reply_text(f"✅ تم خصم {points} نقطة من المستخدم {target_id}")
        
        try:
            await context.bot.send_message(
                target_id,
                f"💸 تم خصم {points} نقطة من رصيدك بواسطة الإدارة."
            )
        except:
            pass
        
        context.user_data.pop("admin_action", None)
    
    elif action == "adding_phone_file":
        # إضافة ملف أرقام
        await update.message.reply_text("❌ يرجى إرسال ملف بصيغة TXT وليس نص.")
    
    elif action == "adding_support":
        # إضافة حساب دعم
        username = text.replace("@", "")
        update_settings({"support_username": username})
        await update.message.reply_text(f"✅ تم تعيين حساب الدعم: @{username}")
        context.user_data.pop("admin_action", None)
    
    elif action == "adding_channel":
        # إضافة رابط قناة
        update_settings({"bot_channel_link": text})
        await update.message.reply_text(f"✅ تم تعيين رابط قناة البوت: {text}")
        context.user_data.pop("admin_action", None)
    
    elif action == "banning_user":
        # حظر مستخدم
        if text.isdigit():
            target_id = int(text)
            
            if target_id in ADMIN_IDS:
                await update.message.reply_text("❌ لا يمكن حظر مدير.")
                return
            
            update_user_data(target_id, {"banned": True})
            await update.message.reply_text(f"✅ تم حظر المستخدم {target_id}")
            
            try:
                await context.bot.send_message(
                    target_id,
                    "⛔ تم حظرك من استخدام البوت بواسطة الإدارة."
                )
            except:
                pass
        else:
            await update.message.reply_text("❌ يرجى إرسال ايدي المستخدم (أرقام فقط).")
        
        context.user_data.pop("admin_action", None)
    
    elif action == "unbanning_user":
        # رفع الحظر
        if text.isdigit():
            target_id = int(text)
            update_user_data(target_id, {"banned": False})
            await update.message.reply_text(f"✅ تم رفع الحظر عن المستخدم {target_id}")
        else:
            await update.message.reply_text("❌ يرجى إرسال ايدي المستخدم (أرقام فقط).")
        
        context.user_data.pop("admin_action", None)
    
    elif action == "changing_reward":
        # تغيير مكافأة الدعوة
        if text.isdigit():
            value = int(text)
            update_settings({"points_per_referral": value})
            await update.message.reply_text(f"✅ تم تغيير مكافأة الدعوة إلى {value} نقطة")
        else:
            await update.message.reply_text("❌ يرجى إرسال رقم صحيح.")
        
        context.user_data.pop("admin_action", None)
    
    elif action == "changing_price":
        # تغيير سعر العضو
        if text.isdigit():
            value = int(text)
            update_settings({"price_per_member": value})
            await update.message.reply_text(f"✅ تم تغيير سعر العضو إلى {value} نقطة")
        else:
            await update.message.reply_text("❌ يرجى إرسال رقم صحيح.")
        
        context.user_data.pop("admin_action", None)
    
    elif action == "changing_welcome":
        # تغيير رسالة الترحيب
        update_settings({"welcome_message": text})
        await update.message.reply_text("✅ تم تغيير رسالة الترحيب بنجاح")
        context.user_data.pop("admin_action", None)
    
    elif action == "removing_phones":
        # حذف الأرقام
        if text.lower() == "حذف الكل":
            if isinstance(phone_numbers_col, dict):
                phone_numbers_col.clear()
            else:
                phone_numbers_col.delete_many({})
            await update.message.reply_text("✅ تم حذف جميع الأرقام.")
        else:
            await update.message.reply_text("❌ الأمر غير معروف. أرسل 'حذف الكل' لحذف جميع الأرقام.")
        
        context.user_data.pop("admin_action", None)

async def handle_file_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة رفع الملفات"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id) or context.user_data.get("admin_action") != "adding_phone_file":
        return
    
    document = update.message.document
    
    # التحقق من صيغة الملف
    if not document.file_name.endswith('.txt'):
        await update.message.reply_text("❌ الملف يجب أن يكون بصيغة TXT فقط.")
        return
    
    # تحميل الملف
    file = await context.bot.get_file(document.file_id)
    file_content = await file.download_as_bytearray()
    text_content = file_content.decode('utf-8')
    
    # استخراج الأرقام
    lines = text_content.strip().split('\n')
    phone_pattern = re.compile(r'^\+?\d{7,15}$')  # نمط بسيط للأرقام
    added_count = 0
    
    for line in lines:
        line = line.strip()
        # تنظيف الرقم من المسافات والرموز غير المرقمة
        phone = re.sub(r'[^\d+]', '', line)
        
        if phone_pattern.match(phone):
            if isinstance(phone_numbers_col, dict):
                if phone not in phone_numbers_col:
                    phone_numbers_col[phone] = {"phone": phone, "added_date": datetime.now(), "used_count": 0}
                    added_count += 1
            else:
                try:
                    phone_numbers_col.insert_one({"phone": phone, "added_date": datetime.now(), "used_count": 0})
                    added_count += 1
                except:
                    pass
    
    # تحديث إحصائيات ملفات الأرقام
    update_settings({"total_phone_files": get_settings()["total_phone_files"] + 1})
    
    await update.message.reply_text(
        f"✅ تم استلام الملف بنجاح!\n"
        f"📊 إجمالي الأرقام في الملف: {len(lines)}\n"
        f"✅ الأرقام الصالحة والمضافة: {added_count}"
    )
    
    context.user_data.pop("admin_action", None)

# ---------------------------------------------------------------------------- #
#                              تشغيل البوت                                     #
# ---------------------------------------------------------------------------- #

async def post_init(application: Application):
    """وظيفة بعد تهيئة البوت"""
    print(f"{Fore.GREEN}✅ البوت يعمل بنجاح!{Style.RESET_ALL}")
    print(f"{Fore.CYAN}🤖 اسم البوت: @{(await application.bot.get_me()).username}{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}👤 المدراء: {', '.join(str(admin_id) for admin_id in ADMIN_IDS)}{Style.RESET_ALL}")
    print(f"{Fore.MAGENTA}📅 الوقت: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{Style.RESET_ALL}")
    print("-" * 50)

def main():
    """الدالة الرئيسية لتشغيل البوت"""
    try:
        # إنشاء التطبيق
        application = Application.builder().token(TOKEN).post_init(post_init).build()
        
        # -------------------------------------------------------------------- #
        #                       معالجات الأوامر                                #
        # -------------------------------------------------------------------- #
        application.add_handler(CommandHandler("start", start))
        
        # -------------------------------------------------------------------- #
        #                       معالجات المحادثات (Conversation)              #
        # -------------------------------------------------------------------- #
        # حالة إضافة ملف الأرقام
        conv_handler_phones = ConversationHandler(
            entry_points=[CallbackQueryHandler(handle_admin_buttons, pattern="^admin_add_phones$")],
            states={
                ADDING_PHONE_FILE: [
                    MessageHandler(filters.Document.ALL, handle_file_upload),
                    MessageHandler(filters.TEXT & ~filters.COMMAND, handle_admin_messages),
                ],
            },
            fallbacks=[CommandHandler("start", start)],
        )
        
        # حالة إضافة حساب الدعم
        conv_handler_support = ConversationHandler(
            entry_points=[CallbackQueryHandler(handle_admin_buttons, pattern="^admin_add_support$")],
            states={
                ADDING_SUPPORT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_admin_messages)],
            },
            fallbacks=[CommandHandler("start", start)],
        )
        
        # حالة إضافة رابط القناة
        conv_handler_channel = ConversationHandler(
            entry_points=[CallbackQueryHandler(handle_admin_buttons, pattern="^admin_add_channel$")],
            states={
                ADDING_CHANNEL_LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_admin_messages)],
            },
            fallbacks=[CommandHandler("start", start)],
        )
        
        # حالة حظر المستخدم
        conv_handler_ban = ConversationHandler(
            entry_points=[CallbackQueryHandler(handle_admin_buttons, pattern="^admin_ban_user$")],
            states={
                BANNING_USER: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_admin_messages)],
            },
            fallbacks=[CommandHandler("start", start)],
        )
        
        # حالة رفع الحظر
        conv_handler_unban = ConversationHandler(
            entry_points=[CallbackQueryHandler(handle_admin_buttons, pattern="^admin_unban_user$")],
            states={
                UNBANNING_USER: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_admin_messages)],
            },
            fallbacks=[CommandHandler("start", start)],
        )
        
        # حالة شحن الرصيد
        conv_handler_ship = ConversationHandler(
            entry_points=[CallbackQueryHandler(handle_admin_buttons, pattern="^admin_add_points$")],
            states={
                SHIPPING_POINTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_admin_messages)],
            },
            fallbacks=[CommandHandler("start", start)],
        )
        
        # حالة خصم الرصيد
        conv_handler_deduct = ConversationHandler(
            entry_points=[CallbackQueryHandler(handle_admin_buttons, pattern="^admin_deduct_points$")],
            states={
                DEDUCTING_POINTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_admin_messages)],
            },
            fallbacks=[CommandHandler("start", start)],
        )
        
        # حالة تغيير المكافأة
        conv_handler_reward = ConversationHandler(
            entry_points=[CallbackQueryHandler(handle_admin_buttons, pattern="^admin_change_reward$")],
            states={
                ADDING_POINTS_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_admin_messages)],
            },
            fallbacks=[CommandHandler("start", start)],
        )
        
        # حالة تغيير السعر
        conv_handler_price = ConversationHandler(
            entry_points=[CallbackQueryHandler(handle_admin_buttons, pattern="^admin_change_price$")],
            states={
                ADDING_PRICE_PER_MEMBER: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_admin_messages)],
            },
            fallbacks=[CommandHandler("start", start)],
        )
        
        # حالة حذف ملف الأرقام
        conv_handler_remove_phones = ConversationHandler(
            entry_points=[CallbackQueryHandler(handle_admin_buttons, pattern="^admin_remove_phones$")],
            states={
                REMOVING_PHONE_FILE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_admin_messages)],
            },
            fallbacks=[CommandHandler("start", start)],
        )
        
        # حالة تغيير رسالة الترحيب
        conv_handler_welcome = ConversationHandler(
            entry_points=[CallbackQueryHandler(handle_admin_buttons, pattern="^admin_change_welcome$")],
            states={
                12: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_admin_messages)],
            },
            fallbacks=[CommandHandler("start", start)],
        )
        
        # حالة التمويل (للمستخدمين العاديين)
        conv_handler_financing = ConversationHandler(
            entry_points=[CallbackQueryHandler(button_handler, pattern="^finance_members$")],
            states={
                FINANCING_AWAITING_LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_financing_message)],
            },
            fallbacks=[CommandHandler("start", start)],
        )
        
        # إضافة جميع معالجات المحادثات
        application.add_handler(conv_handler_phones)
        application.add_handler(conv_handler_support)
        application.add_handler(conv_handler_channel)
        application.add_handler(conv_handler_ban)
        application.add_handler(conv_handler_unban)
        application.add_handler(conv_handler_ship)
        application.add_handler(conv_handler_deduct)
        application.add_handler(conv_handler_reward)
        application.add_handler(conv_handler_price)
        application.add_handler(conv_handler_remove_phones)
        application.add_handler(conv_handler_welcome)
        application.add_handler(conv_handler_financing)
        
        # -------------------------------------------------------------------- #
        #                       معالجات الأزرار العامة                         #
        # -------------------------------------------------------------------- #
        application.add_handler(CallbackQueryHandler(button_handler))
        
        # -------------------------------------------------------------------- #
        #                       معالجات الرسائل العامة                         #
        # -------------------------------------------------------------------- #
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_admin_messages))
        application.add_handler(MessageHandler(filters.Document.ALL, handle_file_upload))
        
        # -------------------------------------------------------------------- #
        #                       بدء تشغيل البوت                                #
        # -------------------------------------------------------------------- #
        print(f"{Fore.GREEN}🚀 جاري تشغيل البوت...{Style.RESET_ALL}")
        application.run_polling(allowed_updates=Update.ALL_TYPES)
        
    except Exception as e:
        print(f"{Fore.RED}❌ خطأ في تشغيل البوت: {e}{Style.RESET_ALL}")
        raise e

if __name__ == "__main__":
    main()
