#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
بوت تمويل متكامل - تليجرام
تم التطوير بواسطة: المبرمج
الإصدار: 3.0.0
تاريخ الإصدار: 2024
"""

# ==================== استيراد المكتبات الأساسية ====================
import telebot
from telebot import types, util
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, ForceReply
import json
import os
import sys
import re
import time
import threading
import random
import string
import hashlib
import hmac
import base64
import uuid
import sqlite3
import logging
import datetime
import requests
import urllib.parse
import urllib.request
import http.client
import socket
import ssl
import csv
import io
import codecs
import queue
import asyncio
import aiohttp
import sqlite3
from contextlib import closing
from functools import wraps
from collections import defaultdict, OrderedDict, Counter
from dataclasses import dataclass, field, asdict
from enum import Enum, auto
from pathlib import Path
from typing import Optional, Dict, List, Tuple, Any, Union, Callable, Set, Generator
from decimal import Decimal, getcontext
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
import signal
import atexit
import gc
import tracemalloc
import cProfile
import pstats
import linecache
import inspect
import traceback
import warnings
warnings.filterwarnings('ignore')

# ==================== استيراد مكتبات إضافية ====================
try:
    from pymongo import MongoClient, ASCENDING, DESCENDING, UpdateOne, InsertOne, DeleteOne
    from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError, DuplicateKeyError, BulkWriteError
    import pymongo
    MONGO_AVAILABLE = True
except ImportError:
    MONGO_AVAILABLE = False
    print("⚠️ MongoDB غير متوفر، سيتم استخدام SQLite بدلاً منه")

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    print("⚠️ Redis غير متوفر")

try:
    from celery import Celery
    from celery.result import AsyncResult
    CELERY_AVAILABLE = True
except ImportError:
    CELERY_AVAILABLE = False
    print("⚠️ Celery غير متوفر")

try:
    import schedule
    SCHEDULE_AVAILABLE = True
except ImportError:
    SCHEDULE_AVAILABLE = False
    print("⚠️ Schedule غير متوفر")

# ==================== إعدادات البوت الأساسية ====================
BOT_TOKEN = "8699966374:AAGCCGehxTQzGbEkBxIe7L3vecLPcvzGrHg"
ADMIN_IDS = [6615860762, 6130994941]  # قائمة معرفات المديرين

# إعدادات قاعدة البيانات
DB_TYPE = "sqlite"  # يمكن تغييره إلى mongodb
DB_NAME = "funding_bot.db"
MONGO_URI = "mongodb://localhost:27017/"

# إعدادات البوت
BOT_USERNAME = None  # سيتم تعيينه تلقائياً
BOT_START_TIME = datetime.datetime.now()
BOT_VERSION = "3.0.0"
BOT_AUTHOR = "المبرمج"

# إعدادات التمويل
DEFAULT_POINTS_PER_INVITE = 10  # النقاط لكل دعوة
DEFAULT_PRICE_PER_MEMBER = 8  # سعر العضو الواحد بالنقاط
MAX_MEMBERS_PER_FUNDING = 1000  # الحد الأقصى للأعضاء لكل تمويل
MIN_MEMBERS_PER_FUNDING = 1  # الحد الأدنى للأعضاء لكل تمويل
FUNDING_TIMEOUT = 3600  # مهلة التمويل بالثواني (ساعة واحدة)
FUNDING_DELAY = 2  # تأخير بين كل إضافة عضو (بالثواني)

# إعدادات الملفات
ALLOWED_FILE_EXTENSIONS = ['.txt', '.csv', '.json']
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 ميجابايت
NUMBERS_FILE_PATH = "numbers/"
os.makedirs(NUMBERS_FILE_PATH, exist_ok=True)

# إعدادات السجلات
LOG_LEVEL = logging.INFO
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_FILE = 'bot.log'
logging.basicConfig(level=LOG_LEVEL, format=LOG_FORMAT, filename=LOG_FILE, filemode='a')

# إعدادات أخرى
CACHE_TIMEOUT = 300  # مهلة الكاش بالثواني
MAX_CACHE_SIZE = 1000  # الحد الأقصى لحجم الكاش
THREAD_POOL_SIZE = 10  # حجم تجمع الخيوط
REQUEST_TIMEOUT = 30  # مهلة الطلبات بالثواني
MAX_RETRIES = 3  # الحد الأقصى لعدد إعادة المحاولة
RETRY_DELAY = 5  # التأخير بين إعادة المحاولة بالثواني

# إعدادات الأداء
ENABLE_CACHE = True
ENABLE_QUEUE = True
ENABLE_BATCH_PROCESSING = True
BATCH_SIZE = 100  # حجم الدفعة في المعالجة المجمعة
QUEUE_SIZE = 1000  # حجم قائمة الانتظار
WORKER_THREADS = 5  # عدد خيوط العاملين

# ==================== إعدادات الرسائل والنصوص ====================
WELCOME_MESSAGE = """
🎉 مرحباً بك في بوت التمويل 🎉

👤 معلومات حسابك:
• 🆔 الايدي: `{user_id}`
• 👤 اسم المستخدم: {username}
• 💰 نقاطك: {points} نقطة
• 📅 تاريخ التسجيل: {join_date}

📢 البوت مخصص لتمويل قنواتك ومجموعاتك بأعضاء حقيقيين
✨ استمتع بخدماتنا المميزة
"""

MAIN_MENU_TEXT = """
🏠 القائمة الرئيسية

👤 مرحباً {username}
💰 رصيدك الحالي: {points} نقطة
🆔 ايديك: `{user_id}`

اختر من الأزرار أدناه:
"""

POINTS_MENU_TEXT = """
💰 قائمة النقاط

نقاطك الحالية: {points} نقطة
عدد الدعوات: {invites} دعوة

📊 يمكنك الحصول على النقاط عن طريق:
1️⃣ مشاركة رابط الدعوة مع أصدقائك
2️⃣ الشحن من الدعم الفني
3️⃣ المشاركة في المسابقات

اختر ما يناسبك:
"""

FUNDING_MENU_TEXT = """
📢 قائمة التمويل

💰 رصيدك: {points} نقطة
💵 سعر العضو: {price_per_member} نقطة
📊 يمكنك تمويل حتى {max_members} عضو

التمويل المتاح:
• {members_count} عضو بـ {total_points} نقطة

اختر عدد الأعضاء للتمويل:
"""

MY_FUNDINGS_TEXT = """
📋 قائمة تمويلاتي

إجمالي التمويلات: {total_fundings}
إجمالي الأعضاء المموّلين: {total_members}
النقاط المستهلكة: {total_points_spent}

آخر 5 تمويلات:
{recent_fundings}

اختر تمويلاً لعرض التفاصيل:
"""

STATS_TEXT = """
📊 إحصائياتك الشخصية

👤 معلومات الحساب:
• 🆔 الايدي: `{user_id}`
• 👤 اسم المستخدم: {username}
• 📅 تاريخ التسجيل: {join_date}
• ⏰ آخر نشاط: {last_active}

💰 معلومات النقاط:
• 💰 الرصيد الحالي: {points} نقطة
• 📈 إجمالي النقاط المكتسبة: {total_points_earned}
• 📉 إجمالي النقاط المنفقة: {total_points_spent}
• 🎁 مكافآت الدعوات: {invite_rewards}

📊 إحصائيات التمويل:
• 📋 عدد التمويلات: {fundings_count}
• 👥 الأعضاء المموّلين: {total_members_funded}
• ✅ التمويلات المكتملة: {completed_fundings}
• ⏳ التمويلات قيد التنفيذ: {pending_fundings}
• ❌ التمويلات الملغاة: {cancelled_fundings}

🎯 إحصائيات الدعوات:
• 🔗 عدد الدعوات: {invites_count}
• 👥 المشتركين عبر دعوتك: {invited_users}
• 🎁 مكافآت الدعوات: {invite_bonuses}

اختر من الأزرار أدناه:
"""

SUPPORT_TEXT = """
🆘 الدعم الفني

للاستفسار أو المساعدة، تواصل معنا:
📞 {support_username}

أو يمكنك مراسلتنا مباشرة:
"""

CHANNEL_TEXT = """
📢 قناة البوت

لمتابعة آخر الأخبار والتحديثات:
🔗 {channel_link}

اشترك الآن ليصلك كل جديد:
"""

INVITE_LINK_TEXT = """
🔗 رابط الدعوة الخاص بك

رابط الدعوة: {invite_link}

• 👥 عدد المدعوين: {invited_count}
• 🎁 مكافأة كل دعوة: {reward} نقطة
• 💰 إجمالي المكافآت: {total_reward} نقطة

شارك الرابط مع أصدقائك واكسب النقاط!
"""

FUNDING_REQUEST_TEXT = """
📝 طلب تمويل جديد

🔢 عدد الأعضاء المطلوب: {members_count}
💰 التكلفة: {cost} نقطة
💳 رصيدك الحالي: {balance} نقطة

{"✅ رصيد كافٍ - أرسل رابط القناة للبدء" if balance >= cost else "❌ رصيد غير كافٍ - قم بشحن رصيدك أولاً"}
"""

FUNDING_START_TEXT = """
🚀 بدء عملية التمويل

📢 معلومات التمويل:
• 📌 معرف التمويل: `{funding_id}`
• 🔗 رابط القناة: {channel_link}
• 👥 عدد الأعضاء: {members_count}
• 💰 التكلفة: {cost} نقطة
• 📅 تاريخ البدء: {start_time}

⏳ جاري بدء عملية التمويل...
سيتم إشعارك عند إضافة كل عضو
"""

FUNDING_PROGRESS_TEXT = """
📊 تقدم التمويل

📌 معرف التمويل: `{funding_id}`
🔗 القناة: {channel_link}
👥 الأعضاء المضافين: {added}/{total}
⏳ المتبقي: {remaining} عضو
📊 نسبة الإنجاز: {progress}%
⏰ الوقت المستغرق: {elapsed_time}
⏱️ الوقت المتبقي: {estimated_time}

✅ آخر عضو تم إضافته: {last_added}
"""

FUNDING_COMPLETE_TEXT = """
✅ اكتمل التمويل بنجاح

📌 معرف التمويل: `{funding_id}`
🔗 القناة: {channel_link}
👥 إجمالي الأعضاء: {total_members}
💰 التكلفة: {cost} نقطة
⏰ الوقت المستغرق: {elapsed_time}
📅 تاريخ الاكتمال: {completion_date}

شكراً لاستخدامك البوت ❤️
"""

FUNDING_CANCELLED_TEXT = """
❌ تم إلغاء التمويل

📌 معرف التمويل: `{funding_id}`
🔗 القناة: {channel_link}
👥 الأعضاء المضافين: {added}/{total}
💰 المبلغ المسترد: {refund} نقطة
⏰ الوقت المستغرق: {elapsed_time}
📅 تاريخ الإلغاء: {cancelled_date}

يمكنك طلب تمويل جديد في أي وقت
"""

FUNDING_ERROR_TEXT = """
⚠️ حدث خطأ في عملية التمويل

📌 معرف التمويل: `{funding_id}`
🔗 القناة: {channel_link}
❌ نوع الخطأ: {error_type}
📝 تفاصيل الخطأ: {error_details}

تم إيقاف التمويل مؤقتاً
سيتم إشعارك عند معالجة المشكلة
"""

ADMIN_PANEL_TEXT = """
🔧 لوحة التحكم

📊 إحصائيات سريعة:
• 👥 إجمالي المستخدمين: {total_users}
• 👤 المستخدمين النشطين: {active_users}
• 🚫 المستخدمين المحظورين: {banned_users}
• 📋 إجمالي التمويلات: {total_fundings}
• 👥 الأعضاء المموّلين: {total_members}
• 💰 إجمالي النقاط: {total_points}
• 💵 النقاط المنفقة: {total_points_spent}
• 📁 الملفات المرفوعة: {total_files}
• 📞 الدعم الفني: {support_username}
• 📢 قناة البوت: {channel_link}

اختر من الأزرار أدناه:
"""

ADMIN_STATS_TEXT = """
📊 إحصائيات تفصيلية للبوت

👥 إحصائيات المستخدمين:
• 👤 إجمالي المستخدمين: {total_users}
• 👥 مستخدمين جدد اليوم: {new_users_today}
• 👥 مستخدمين جدد هذا الأسبوع: {new_users_week}
• 👥 مستخدمين جدد هذا الشهر: {new_users_month}
• 👤 المستخدمين النشطين اليوم: {active_today}
• 👤 المستخدمين النشطين هذا الأسبوع: {active_week}
• 👤 المستخدمين النشطين هذا الشهر: {active_month}
• 🚫 المستخدمين المحظورين: {banned_users}

📊 إحصائيات التمويل:
• 📋 إجمالي التمويلات: {total_fundings}
• ✅ التمويلات المكتملة: {completed_fundings}
• ⏳ التمويلات قيد التنفيذ: {pending_fundings}
• ❌ التمويلات الملغاة: {cancelled_fundings}
• 👥 الأعضاء المموّلين: {total_members}
• 💰 النقاط المنفقة: {total_points_spent}
• 📈 متوسط الأعضاء لكل تمويل: {avg_members_per_funding}
• 💰 متوسط النقاط لكل تمويل: {avg_points_per_funding}

💰 إحصائيات النقاط:
• 💰 إجمالي النقاط: {total_points}
• 📈 النقاط الممنوحة: {total_points_given}
• 📉 النقاط المنفقة: {total_points_spent}
• 💰 متوسط النقاط لكل مستخدم: {avg_points_per_user}
• 🎁 نقاط الدعوات: {invite_points}

📁 إحصائيات الملفات:
• 📁 إجمالي الملفات: {total_files}
• 👥 إجمالي الأرقام: {total_numbers}
• ✅ الأرقام الصالحة: {valid_numbers}
• ❌ الأرقام غير الصالحة: {invalid_numbers}
• 📊 متوسط الأرقام لكل ملف: {avg_numbers_per_file}

🕒 إحصائيات الوقت:
• ⏰ وقت تشغيل البوت: {uptime}
• 📅 تاريخ بدء التشغيل: {start_date}
• 📊 متوسط وقت التمويل: {avg_funding_time}
"""

ADMIN_BAN_TEXT = """
🚫 حظر مستخدم

تم حظر المستخدم بنجاح:
• 🆔 الايدي: `{user_id}`
• 👤 اسم المستخدم: {username}
• 📅 تاريخ الحظر: {ban_date}
• ⏰ وقت الحظر: {ban_time}

يمكنك رفع الحظر في أي وقت
"""

ADMIN_UNBAN_TEXT = """
✅ رفع حظر مستخدم

تم رفع الحظر عن المستخدم بنجاح:
• 🆔 الايدي: `{user_id}`
• 👤 اسم المستخدم: {username}
• 📅 تاريخ رفع الحظر: {unban_date}
• ⏰ وقت رفع الحظر: {unban_time}
"""

ADMIN_ADD_POINTS_TEXT = """
💰 شحن رصيد

تم شحن رصيد المستخدم بنجاح:
• 🆔 الايدي: `{user_id}`
• 👤 اسم المستخدم: {username}
• 💰 المبلغ المضاف: +{amount} نقطة
• 💳 الرصيد السابق: {old_balance}
• 💳 الرصيد الحالي: {new_balance}
• 📅 تاريخ الشحن: {date}
• 📝 سبب الشحن: {reason}

تم تحديث الرصيد بنجاح
"""

ADMIN_REMOVE_POINTS_TEXT = """
💳 خصم رصيد

تم خصم رصيد المستخدم بنجاح:
• 🆔 الايدي: `{user_id}`
• 👤 اسم المستخدم: {username}
• 💰 المبلغ المخصوم: -{amount} نقطة
• 💳 الرصيد السابق: {old_balance}
• 💳 الرصيد الحالي: {new_balance}
• 📅 تاريخ الخصم: {date}
• 📝 سبب الخصم: {reason}

تم تحديث الرصيد بنجاح
"""

ADMIN_FILE_UPLOAD_TEXT = """
📁 رفع ملف أرقام

تم رفع الملف بنجاح:
• 📁 اسم الملف: {filename}
• 📊 حجم الملف: {file_size}
• 👥 عدد الأرقام: {numbers_count}
• ✅ الأرقام الصالحة: {valid_numbers}
• ❌ الأرقام المكررة: {duplicate_numbers}
• 📅 تاريخ الرفع: {date}

يمكنك استخدام هذه الأرقام في التمويل
"""

ADMIN_FILE_ERROR_TEXT = """
❌ خطأ في رفع الملف

• 📁 اسم الملف: {filename}
• ❌ نوع الخطأ: {error_type}
• 📝 تفاصيل الخطأ: {error_details}

يرجى التحقق من الملف والمحاولة مرة أخرى
"""

ADMIN_SETTINGS_TEXT = """
⚙️ إعدادات البوت

الإعدادات الحالية:
• 🎁 مكافأة الدعوة: {invite_reward} نقطة
• 💵 سعر العضو: {member_price} نقطة
• 👥 الحد الأقصى للتمويل: {max_members} عضو
• 👤 الحد الأدنى للتمويل: {min_members} عضو
• ⏰ مهلة التمويل: {funding_timeout} ثانية
• ⏱️ تأخير التمويل: {funding_delay} ثانية
• 📁 صيغ الملفات المسموحة: {allowed_formats}
• 📊 حجم الملف الأقصى: {max_file_size}

📢 إعدادات القنوات:
• 📞 الدعم الفني: {support_username}
• 📢 قناة البوت: {channel_link}
• 🔒 الاشتراك الإجباري: {force_join}

✅ الاشتراك الإجباري: {"مفعل" if force_join_enabled else "غير مفعل"}
📊 عدد قنوات الاشتراك: {force_join_channels_count}

اختر الإعداد الذي تريد تعديله:
"""

ADMIN_FUNDING_NOTIFICATION = """
📢 إشعار تمويل جديد

👤 المستخدم: {username}
🆔 الايدي: `{user_id}`
💰 رصيد المستخدم: {user_balance} نقطة

📋 تفاصيل التمويل:
• 📌 معرف التمويل: `{funding_id}`
• 🔗 رابط القناة: {channel_link}
• 👥 عدد الأعضاء: {members_count}
• 💰 التكلفة: {cost} نقطة
• 📅 تاريخ الطلب: {request_time}

للتحكم في التمويل، اختر من الأزرار أدناه:
"""

# ==================== إعدادات الأزرار ====================
# أزرار القائمة الرئيسية
BTN_MAIN_POINTS = "💰 تجميع النقاط"
BTN_MAIN_FUNDING = "📢 تمويل مشتركين"
BTN_MAIN_MY_FUNDINGS = "📋 تمويلاتي"
BTN_MAIN_STATS = "📊 احصائياتي"
BTN_MAIN_SUPPORT = "🆘 الدعم الفني"
BTN_MAIN_CHANNEL = "📢 قناة البوت"
BTN_MAIN_BACK = "🔙 رجوع"
BTN_MAIN_HOME = "🏠 الرئيسية"

# أزرار قائمة النقاط
BTN_POINTS_INVITE = "🔗 رابط الدعوة"
BTN_POINTS_CHARGE = "💳 شحن رصيد"
BTN_POINTS_HISTORY = "📜 سجل النقاط"

# أزرار التمويل
BTN_FUNDING_1 = "1 👤 عضو"
BTN_FUNDING_5 = "5 👥 أعضاء"
BTN_FUNDING_10 = "10 👥 أعضاء"
BTN_FUNDING_20 = "20 👥 أعضاء"
BTN_FUNDING_50 = "50 👥 أعضاء"
BTN_FUNDING_100 = "100 👥 أعضاء"
BTN_FUNDING_CUSTOM = "✏️ عدد مخصص"

# أزرار لوحة التحكم
BTN_ADMIN_STATS = "📊 احصائيات البوت"
BTN_ADMIN_USERS = "👥 المستخدمين"
BTN_ADMIN_ADD_POINTS = "💰 شحن رصيد"
BTN_ADMIN_REMOVE_POINTS = "💳 خصم رصيد"
BTN_ADMIN_FILES = "📁 ملفات الأرقام"
BTN_ADMIN_ADD_FILE = "📁➕ إضافة ملف"
BTN_ADMIN_DELETE_FILE = "📁❌ حذف ملف"
BTN_ADMIN_VIEW_FILES = "📁📋 عرض الملفات"
BTN_ADMIN_SUPPORT = "📞 إضافة دعم"
BTN_ADMIN_CHANNEL = "📢 إضافة قناة"
BTN_ADMIN_BAN = "🚫 حظر مستخدم"
BTN_ADMIN_UNBAN = "✅ رفع حظر"
BTN_ADMIN_SETTINGS = "⚙️ الإعدادات"
BTN_ADMIN_INVITE_REWARD = "🎁 مكافأة الدعوة"
BTN_ADMIN_MEMBER_PRICE = "💵 سعر العضو"
BTN_ADMIN_FORCE_JOIN = "🔒 الاشتراك الإجباري"
BTN_ADMIN_ADD_CHANNEL = "📢➕ إضافة قناة"
BTN_ADMIN_REMOVE_CHANNEL = "📢❌ حذف قناة"
BTN_ADMIN_VIEW_CHANNELS = "📢📋 عرض القنوات"
BTN_ADMIN_BROADCAST = "📢 إرسال رسالة"
BTN_ADMIN_BACKUP = "💾 نسخ احتياطي"
BTN_ADMIN_RESTORE = "📂 استعادة نسخة"
BTN_ADMIN_LOGS = "📋 سجلات البوت"
BTN_ADMIN_MAINTENANCE = "🔧 صيانة"

# أزرار التحكم في التمويل
BTN_FUNDING_APPROVE = "✅ قبول التمويل"
BTN_FUNDING_REJECT = "❌ رفض التمويل"
BTN_FUNDING_CANCEL = "🛑 إلغاء التمويل"
BTN_FUNDING_BAN_USER = "🚫 حظر المستخدم"
BTN_FUNDING_PAUSE = "⏸️ إيقاف مؤقت"
BTN_FUNDING_RESUME = "▶️ استئناف"
BTN_FUNDING_RESTART = "🔄 إعادة تشغيل"

# أزرار الترقيم
BTN_PREVIOUS = "◀️ السابق"
BTN_NEXT = "التالي ▶️"
BTN_FIRST = "⏮️ الأول"
BTN_LAST = "الأخير ⏭️"
BTN_PAGE = "📄 صفحة {page}"
BTN_REFRESH = "🔄 تحديث"

# ==================== إعدادات قاعدة البيانات ====================
class DatabaseManager:
    """مدير قاعدة البيانات"""
    
    def __init__(self, db_type=DB_TYPE):
        self.db_type = db_type
        self.connection = None
        self.cursor = None
        self.mongo_client = None
        self.mongo_db = None
        self.redis_client = None
        self.connected = False
        self.tables_created = False
        
        # إنشاء اتصال قاعدة البيانات
        self.connect()
        
        # إنشاء الجداول إذا كانت SQLite
        if self.db_type == "sqlite" and self.connected:
            self.create_tables()
    
    def connect(self):
        """الاتصال بقاعدة البيانات"""
        try:
            if self.db_type == "sqlite":
                self.connection = sqlite3.connect(DB_NAME, check_same_thread=False)
                self.connection.row_factory = sqlite3.Row
                self.cursor = self.connection.cursor()
                self.connected = True
                logging.info("✅ تم الاتصال بقاعدة بيانات SQLite بنجاح")
                
            elif self.db_type == "mongodb" and MONGO_AVAILABLE:
                self.mongo_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
                self.mongo_client.admin.command('ismaster')
                self.mongo_db = self.mongo_client[DB_NAME]
                self.connected = True
                logging.info("✅ تم الاتصال بقاعدة بيانات MongoDB بنجاح")
            
            if REDIS_AVAILABLE:
                try:
                    self.redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
                    self.redis_client.ping()
                    logging.info("✅ تم الاتصال بـ Redis بنجاح")
                except:
                    logging.warning("⚠️ فشل الاتصال بـ Redis")
                    self.redis_client = None
            
        except Exception as e:
            self.connected = False
            logging.error(f"❌ فشل الاتصال بقاعدة البيانات: {e}")
    
    def create_tables(self):
        """إنشاء جداول قاعدة البيانات"""
        try:
            # جدول المستخدمين
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    points INTEGER DEFAULT 0,
                    total_points_earned INTEGER DEFAULT 0,
                    total_points_spent INTEGER DEFAULT 0,
                    invite_link TEXT,
                    invited_by INTEGER DEFAULT 0,
                    invites_count INTEGER DEFAULT 0,
                    invited_users TEXT DEFAULT '[]',
                    is_banned INTEGER DEFAULT 0,
                    is_admin INTEGER DEFAULT 0,
                    language TEXT DEFAULT 'ar',
                    join_date TEXT,
                    last_active TEXT,
                    settings TEXT DEFAULT '{}'
                )
            ''')
            
            # جدول التمويلات
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS fundings (
                    funding_id TEXT PRIMARY KEY,
                    user_id INTEGER,
                    channel_link TEXT,
                    channel_id TEXT,
                    members_count INTEGER,
                    added_members INTEGER DEFAULT 0,
                    cost INTEGER,
                    status TEXT DEFAULT 'pending',
                    start_time TEXT,
                    end_time TEXT,
                    last_update TEXT,
                    progress TEXT DEFAULT '[]',
                    cancelled_by INTEGER DEFAULT 0,
                    cancel_reason TEXT,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            ''')
            
            # جدول الأرقام
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS numbers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    number TEXT UNIQUE,
                    country_code TEXT,
                    valid INTEGER DEFAULT 1,
                    used INTEGER DEFAULT 0,
                    file_name TEXT,
                    added_by INTEGER,
                    added_date TEXT,
                    used_date TEXT,
                    used_in TEXT,
                    notes TEXT
                )
            ''')
            
            # جدول الملفات
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS files (
                    file_id TEXT PRIMARY KEY,
                    file_name TEXT,
                    file_path TEXT,
                    file_size INTEGER,
                    numbers_count INTEGER,
                    valid_numbers INTEGER,
                    duplicate_numbers INTEGER,
                    added_by INTEGER,
                    added_date TEXT,
                    status TEXT DEFAULT 'active',
                    notes TEXT
                )
            ''')
            
            # جدول الدعوات
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS invites (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    inviter_id INTEGER,
                    invited_id INTEGER UNIQUE,
                    invite_date TEXT,
                    points_earned INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'pending',
                    FOREIGN KEY (inviter_id) REFERENCES users (user_id),
                    FOREIGN KEY (invited_id) REFERENCES users (user_id)
                )
            ''')
            
            # جدول المعاملات
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    type TEXT,
                    amount INTEGER,
                    balance_before INTEGER,
                    balance_after INTEGER,
                    description TEXT,
                    reference_id TEXT,
                    date TEXT,
                    status TEXT DEFAULT 'completed',
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            ''')
            
            # جدول الإعدادات
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    type TEXT DEFAULT 'str',
                    description TEXT,
                    updated_by INTEGER,
                    updated_date TEXT
                )
            ''')
            
            # جدول القنوات الإجبارية
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS force_join_channels (
                    channel_id TEXT PRIMARY KEY,
                    channel_link TEXT,
                    channel_username TEXT,
                    channel_title TEXT,
                    added_by INTEGER,
                    added_date TEXT,
                    status TEXT DEFAULT 'active',
                    position INTEGER DEFAULT 0
                )
            ''')
            
            # جدول الرسائل المجدولة
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS scheduled_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    message_text TEXT,
                    parse_mode TEXT DEFAULT 'HTML',
                    send_to TEXT,
                    scheduled_time TEXT,
                    status TEXT DEFAULT 'pending',
                    created_by INTEGER,
                    created_date TEXT,
                    sent_date TEXT,
                    error TEXT
                )
            ''')
            
            # جدول النسخ الاحتياطي
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS backups (
                    backup_id TEXT PRIMARY KEY,
                    backup_name TEXT,
                    backup_path TEXT,
                    backup_size INTEGER,
                    tables_count INTEGER,
                    records_count INTEGER,
                    created_by INTEGER,
                    created_date TEXT,
                    restored_date TEXT,
                    notes TEXT
                )
            ''')
            
            self.connection.commit()
            
            # إدراج الإعدادات الافتراضية
            default_settings = [
                ('invite_reward', str(DEFAULT_POINTS_PER_INVITE), 'int', 'مكافأة الدعوة'),
                ('member_price', str(DEFAULT_PRICE_PER_MEMBER), 'int', 'سعر العضو'),
                ('max_members', str(MAX_MEMBERS_PER_FUNDING), 'int', 'الحد الأقصى للتمويل'),
                ('min_members', str(MIN_MEMBERS_PER_FUNDING), 'int', 'الحد الأدنى للتمويل'),
                ('funding_timeout', str(FUNDING_TIMEOUT), 'int', 'مهلة التمويل'),
                ('funding_delay', str(FUNDING_DELAY), 'int', 'تأخير التمويل'),
                ('allowed_formats', ','.join(ALLOWED_FILE_EXTENSIONS), 'str', 'صيغ الملفات المسموحة'),
                ('max_file_size', str(MAX_FILE_SIZE), 'int', 'الحد الأقصى لحجم الملف'),
                ('support_username', 'None', 'str', 'يوزر الدعم الفني'),
                ('channel_link', 'None', 'str', 'رابط قناة البوت'),
                ('force_join_enabled', 'False', 'bool', 'تفعيل الاشتراك الإجباري'),
                ('welcome_message', WELCOME_MESSAGE, 'str', 'رسالة الترحيب'),
                ('main_menu_text', MAIN_MENU_TEXT, 'str', 'نص القائمة الرئيسية'),
            ]
            
            for key, value, typ, desc in default_settings:
                self.cursor.execute('''
                    INSERT OR IGNORE INTO settings (key, value, type, description, updated_date)
                    VALUES (?, ?, ?, ?, ?)
                ''', (key, value, typ, desc, datetime.datetime.now().isoformat()))
            
            self.connection.commit()
            self.tables_created = True
            logging.info("✅ تم إنشاء جداول قاعدة البيانات بنجاح")
            
        except Exception as e:
            logging.error(f"❌ فشل إنشاء جداول قاعدة البيانات: {e}")
    
    def get_setting(self, key, default=None):
        """الحصول على إعداد"""
        try:
            if self.db_type == "sqlite":
                self.cursor.execute('SELECT value, type FROM settings WHERE key = ?', (key,))
                result = self.cursor.fetchone()
                if result:
                    value, typ = result
                    if typ == 'int':
                        return int(value)
                    elif typ == 'float':
                        return float(value)
                    elif typ == 'bool':
                        return value.lower() == 'true'
                    elif typ == 'list':
                        return value.split(',') if value else []
                    else:
                        return value
            elif self.db_type == "mongodb":
                setting = self.mongo_db.settings.find_one({'key': key})
                if setting:
                    return setting.get('value', default)
        except:
            pass
        return default
    
    def set_setting(self, key, value, admin_id=None):
        """تحديث إعداد"""
        try:
            value_str = str(value)
            typ = type(value).__name__
            
            if self.db_type == "sqlite":
                self.cursor.execute('''
                    INSERT OR REPLACE INTO settings (key, value, type, updated_by, updated_date)
                    VALUES (?, ?, ?, ?, ?)
                ''', (key, value_str, typ, admin_id, datetime.datetime.now().isoformat()))
                self.connection.commit()
                return True
                
            elif self.db_type == "mongodb":
                self.mongo_db.settings.update_one(
                    {'key': key},
                    {'$set': {
                        'value': value_str,
                        'type': typ,
                        'updated_by': admin_id,
                        'updated_date': datetime.datetime.now().isoformat()
                    }},
                    upsert=True
                )
                return True
        except Exception as e:
            logging.error(f"❌ فشل تحديث الإعداد {key}: {e}")
        return False
    
    def add_user(self, user_id, username=None, first_name=None, last_name=None, invited_by=None):
        """إضافة مستخدم جديد"""
        try:
            now = datetime.datetime.now().isoformat()
            invite_link = f"https://t.me/{BOT_USERNAME}?start={user_id}" if BOT_USERNAME else None
            
            if self.db_type == "sqlite":
                # التحقق من وجود المستخدم
                self.cursor.execute('SELECT user_id FROM users WHERE user_id = ?', (user_id,))
                if self.cursor.fetchone():
                    # تحديث آخر نشاط
                    self.cursor.execute('''
                        UPDATE users 
                        SET last_active = ?, username = ?, first_name = ?, last_name = ?
                        WHERE user_id = ?
                    ''', (now, username, first_name, last_name, user_id))
                    self.connection.commit()
                    return True
                
                # إضافة مستخدم جديد
                self.cursor.execute('''
                    INSERT INTO users (
                        user_id, username, first_name, last_name, 
                        points, invite_link, invited_by, join_date, last_active
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (user_id, username, first_name, last_name, 
                      0, invite_link, invited_by or 0, now, now))
                self.connection.commit()
                
                # إذا كان هناك مدعو، تحديث إحصائيات الداعي
                if invited_by and invited_by != user_id:
                    self.add_invite(invited_by, user_id)
                
                return True
                
            elif self.db_type == "mongodb":
                user = self.mongo_db.users.find_one({'user_id': user_id})
                if not user:
                    self.mongo_db.users.insert_one({
                        'user_id': user_id,
                        'username': username,
                        'first_name': first_name,
                        'last_name': last_name,
                        'points': 0,
                        'total_points_earned': 0,
                        'total_points_spent': 0,
                        'invite_link': invite_link,
                        'invited_by': invited_by or 0,
                        'invites_count': 0,
                        'invited_users': [],
                        'is_banned': False,
                        'is_admin': user_id in ADMIN_IDS,
                        'language': 'ar',
                        'join_date': now,
                        'last_active': now,
                        'settings': {}
                    })
                else:
                    self.mongo_db.users.update_one(
                        {'user_id': user_id},
                        {'$set': {
                            'username': username,
                            'first_name': first_name,
                            'last_name': last_name,
                            'last_active': now
                        }}
                    )
                return True
                
        except Exception as e:
            logging.error(f"❌ فشل إضافة المستخدم {user_id}: {e}")
        return False
    
    def get_user(self, user_id):
        """الحصول على معلومات المستخدم"""
        try:
            if self.db_type == "sqlite":
                self.cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
                user = self.cursor.fetchone()
                return dict(user) if user else None
                
            elif self.db_type == "mongodb":
                return self.mongo_db.users.find_one({'user_id': user_id})
                
        except Exception as e:
            logging.error(f"❌ فشل الحصول على المستخدم {user_id}: {e}")
        return None
    
    def update_user_points(self, user_id, points_change, transaction_type='adjustment', description=''):
        """تحديث نقاط المستخدم"""
        try:
            user = self.get_user(user_id)
            if not user:
                return False
            
            old_points = user.get('points', 0)
            new_points = old_points + points_change
            
            if new_points < 0:
                return False
            
            now = datetime.datetime.now().isoformat()
            
            if self.db_type == "sqlite":
                # تحديث النقاط
                self.cursor.execute('''
                    UPDATE users 
                    SET points = ?,
                        total_points_earned = total_points_earned + ?,
                        total_points_spent = total_points_spent + ?,
                        last_active = ?
                    WHERE user_id = ?
                ''', (new_points, 
                      max(points_change, 0),  # النقاط المكتسبة
                      abs(min(points_change, 0)),  # النقاط المنفقة
                      now, user_id))
                
                # إضافة معاملة
                self.cursor.execute('''
                    INSERT INTO transactions (
                        user_id, type, amount, balance_before, balance_after,
                        description, reference_id, date, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (user_id, transaction_type, points_change, old_points, new_points,
                      description, str(uuid.uuid4()), now, 'completed'))
                
                self.connection.commit()
                return True
                
            elif self.db_type == "mongodb":
                self.mongo_db.users.update_one(
                    {'user_id': user_id},
                    {
                        '$set': {
                            'points': new_points,
                            'last_active': now
                        },
                        '$inc': {
                            'total_points_earned': max(points_change, 0),
                            'total_points_spent': abs(min(points_change, 0))
                        }
                    }
                )
                
                self.mongo_db.transactions.insert_one({
                    'user_id': user_id,
                    'type': transaction_type,
                    'amount': points_change,
                    'balance_before': old_points,
                    'balance_after': new_points,
                    'description': description,
                    'reference_id': str(uuid.uuid4()),
                    'date': now,
                    'status': 'completed'
                })
                return True
                
        except Exception as e:
            logging.error(f"❌ فشل تحديث نقاط المستخدم {user_id}: {e}")
        return False
    
    def add_invite(self, inviter_id, invited_id):
        """إضافة دعوة جديدة"""
        try:
            now = datetime.datetime.now().isoformat()
            reward = self.get_setting('invite_reward', DEFAULT_POINTS_PER_INVITE)
            
            if self.db_type == "sqlite":
                # إضافة الدعوة
                self.cursor.execute('''
                    INSERT OR IGNORE INTO invites (inviter_id, invited_id, invite_date, points_earned, status)
                    VALUES (?, ?, ?, ?, ?)
                ''', (inviter_id, invited_id, now, reward, 'completed'))
                
                # تحديث إحصائيات الداعي
                self.cursor.execute('''
                    UPDATE users 
                    SET invites_count = invites_count + 1,
                        invited_users = json_insert(COALESCE(invited_users, '[]'), '$[#]', ?)
                    WHERE user_id = ?
                ''', (invited_id, inviter_id))
                
                self.connection.commit()
                
            elif self.db_type == "mongodb":
                self.mongo_db.invites.insert_one({
                    'inviter_id': inviter_id,
                    'invited_id': invited_id,
                    'invite_date': now,
                    'points_earned': reward,
                    'status': 'completed'
                })
                
                self.mongo_db.users.update_one(
                    {'user_id': inviter_id},
                    {
                        '$inc': {'invites_count': 1},
                        '$push': {'invited_users': invited_id}
                    }
                )
            
            # إضافة النقاط للداعي
            self.update_user_points(inviter_id, reward, 'invite_reward', f'مكافأة دعوة المستخدم {invited_id}')
            return True
            
        except Exception as e:
            logging.error(f"❌ فشل إضافة الدعوة: {e}")
        return False
    
    def add_numbers_from_file(self, numbers, file_name, added_by):
        """إضافة أرقام من ملف"""
        try:
            now = datetime.datetime.now().isoformat()
            file_id = str(uuid.uuid4())
            valid_numbers = 0
            duplicate_numbers = 0
            
            if self.db_type == "sqlite":
                for number in numbers:
                    try:
                        self.cursor.execute('''
                            INSERT OR IGNORE INTO numbers (number, country_code, valid, file_name, added_by, added_date)
                            VALUES (?, ?, 1, ?, ?, ?)
                        ''', (number, self.extract_country_code(number), file_name, added_by, now))
                        
                        if self.cursor.rowcount > 0:
                            valid_numbers += 1
                        else:
                            duplicate_numbers += 1
                            
                    except:
                        duplicate_numbers += 1
                
                # إضافة الملف
                self.cursor.execute('''
                    INSERT INTO files (file_id, file_name, file_path, file_size, numbers_count, valid_numbers, duplicate_numbers, added_by, added_date)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (file_id, file_name, f"{NUMBERS_FILE_PATH}{file_name}", len(numbers), 
                      len(numbers), valid_numbers, duplicate_numbers, added_by, now))
                
                self.connection.commit()
                
            elif self.db_type == "mongodb":
                number_docs = []
                for number in numbers:
                    number_docs.append({
                        'number': number,
                        'country_code': self.extract_country_code(number),
                        'valid': True,
                        'used': False,
                        'file_name': file_name,
                        'added_by': added_by,
                        'added_date': now
                    })
                
                try:
                    result = self.mongo_db.numbers.insert_many(number_docs, ordered=False)
                    valid_numbers = len(result.inserted_ids)
                except BulkWriteError as bwe:
                    valid_numbers = bwe.details.get('nInserted', 0)
                    duplicate_numbers = len(numbers) - valid_numbers
                
                self.mongo_db.files.insert_one({
                    'file_id': file_id,
                    'file_name': file_name,
                    'file_path': f"{NUMBERS_FILE_PATH}{file_name}",
                    'file_size': len(numbers),
                    'numbers_count': len(numbers),
                    'valid_numbers': valid_numbers,
                    'duplicate_numbers': duplicate_numbers,
                    'added_by': added_by,
                    'added_date': now,
                    'status': 'active'
                })
            
            return {
                'file_id': file_id,
                'total_numbers': len(numbers),
                'valid_numbers': valid_numbers,
                'duplicate_numbers': duplicate_numbers
            }
            
        except Exception as e:
            logging.error(f"❌ فشل إضافة الأرقام من الملف: {e}")
            return None
    
    def get_random_numbers(self, count):
        """الحصول على أرقام عشوائية للتمويل"""
        try:
            if self.db_type == "sqlite":
                self.cursor.execute('''
                    SELECT number FROM numbers 
                    WHERE valid = 1 AND used = 0 
                    ORDER BY RANDOM() 
                    LIMIT ?
                ''', (count,))
                numbers = [row['number'] for row in self.cursor.fetchall()]
                
                # تحديث حالة الأرقام المستخدمة
                if numbers:
                    placeholders = ','.join(['?'] * len(numbers))
                    self.cursor.execute(f'''
                        UPDATE numbers 
                        SET used = 1, used_date = ? 
                        WHERE number IN ({placeholders})
                    ''', (datetime.datetime.now().isoformat(), *numbers))
                    self.connection.commit()
                
                return numbers
                
            elif self.db_type == "mongodb":
                pipeline = [
                    {'$match': {'valid': True, 'used': False}},
                    {'$sample': {'size': count}},
                    {'$project': {'number': 1}}
                ]
                numbers = list(self.mongo_db.numbers.aggregate(pipeline))
                number_list = [n['number'] for n in numbers]
                
                if number_list:
                    self.mongo_db.numbers.update_many(
                        {'number': {'$in': number_list}},
                        {'$set': {'used': True, 'used_date': datetime.datetime.now().isoformat()}}
                    )
                
                return number_list
                
        except Exception as e:
            logging.error(f"❌ فشل الحصول على أرقام عشوائية: {e}")
        return []
    
    def extract_country_code(self, number):
        """استخراج مفتاح الدولة من الرقم"""
        number = str(number).strip()
        if number.startswith('+'):
            # استخراج أول 3 أرقام بعد +
            match = re.match(r'\+(\d{1,3})', number)
            return match.group(1) if match else 'unknown'
        elif number.startswith('00'):
            match = re.match(r'00(\d{1,3})', number)
            return match.group(1) if match else 'unknown'
        else:
            # افتراض أن الرقم يبدأ بمفتاح الدولة
            match = re.match(r'(\d{1,3})', number)
            return match.group(1) if match else 'unknown'
    
    def create_funding(self, user_id, channel_link, members_count, cost):
        """إنشاء تمويل جديد"""
        try:
            funding_id = str(uuid.uuid4())[:8]
            now = datetime.datetime.now().isoformat()
            
            if self.db_type == "sqlite":
                self.cursor.execute('''
                    INSERT INTO fundings (
                        funding_id, user_id, channel_link, members_count, cost,
                        status, start_time, last_update, progress
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (funding_id, user_id, channel_link, members_count, cost,
                      'pending', now, now, '[]'))
                self.connection.commit()
                
            elif self.db_type == "mongodb":
                self.mongo_db.fundings.insert_one({
                    'funding_id': funding_id,
                    'user_id': user_id,
                    'channel_link': channel_link,
                    'members_count': members_count,
                    'added_members': 0,
                    'cost': cost,
                    'status': 'pending',
                    'start_time': now,
                    'last_update': now,
                    'progress': [],
                    'cancelled_by': 0,
                    'cancel_reason': ''
                })
            
            return funding_id
            
        except Exception as e:
            logging.error(f"❌ فشل إنشاء التمويل: {e}")
        return None
    
    def update_funding(self, funding_id, **kwargs):
        """تحديث معلومات التمويل"""
        try:
            kwargs['last_update'] = datetime.datetime.now().isoformat()
            
            if self.db_type == "sqlite":
                set_clause = ', '.join([f"{k} = ?" for k in kwargs.keys()])
                values = list(kwargs.values()) + [funding_id]
                
                self.cursor.execute(f'''
                    UPDATE fundings 
                    SET {set_clause}
                    WHERE funding_id = ?
                ''', values)
                self.connection.commit()
                
            elif self.db_type == "mongodb":
                self.mongo_db.fundings.update_one(
                    {'funding_id': funding_id},
                    {'$set': kwargs}
                )
            
            return True
            
        except Exception as e:
            logging.error(f"❌ فشل تحديث التمويل: {e}")
        return False
    
    def get_user_fundings(self, user_id, limit=10):
        """الحصول على تمويلات المستخدم"""
        try:
            if self.db_type == "sqlite":
                self.cursor.execute('''
                    SELECT * FROM fundings 
                    WHERE user_id = ? 
                    ORDER BY start_time DESC 
                    LIMIT ?
                ''', (user_id, limit))
                return [dict(row) for row in self.cursor.fetchall()]
                
            elif self.db_type == "mongodb":
                cursor = self.mongo_db.fundings.find(
                    {'user_id': user_id}
                ).sort('start_time', -1).limit(limit)
                return list(cursor)
                
        except Exception as e:
            logging.error(f"❌ فشل الحصول على تمويلات المستخدم: {e}")
        return []
    
    def get_pending_fundings(self):
        """الحصول على التمويلات قيد التنفيذ"""
        try:
            if self.db_type == "sqlite":
                self.cursor.execute('''
                    SELECT * FROM fundings 
                    WHERE status = 'pending' OR status = 'in_progress'
                    ORDER BY start_time ASC
                ''')
                return [dict(row) for row in self.cursor.fetchall()]
                
            elif self.db_type == "mongodb":
                cursor = self.mongo_db.fundings.find({
                    'status': {'$in': ['pending', 'in_progress']}
                }).sort('start_time', 1)
                return list(cursor)
                
        except Exception as e:
            logging.error(f"❌ فشل الحصول على التمويلات قيد التنفيذ: {e}")
        return []
    
    def get_stats(self):
        """الحصول على إحصائيات البوت"""
        try:
            stats = {}
            now = datetime.datetime.now()
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
            week_start = (now - timedelta(days=7)).isoformat()
            month_start = (now - timedelta(days=30)).isoformat()
            
            if self.db_type == "sqlite":
                # إجمالي المستخدمين
                self.cursor.execute('SELECT COUNT(*) as count FROM users')
                stats['total_users'] = self.cursor.fetchone()['count']
                
                # المستخدمين النشطين اليوم
                self.cursor.execute('SELECT COUNT(*) as count FROM users WHERE last_active >= ?', (today_start,))
                stats['active_users'] = self.cursor.fetchone()['count']
                
                # المستخدمين المحظورين
                self.cursor.execute('SELECT COUNT(*) as count FROM users WHERE is_banned = 1')
                stats['banned_users'] = self.cursor.fetchone()['count']
                
                # إجمالي التمويلات
                self.cursor.execute('SELECT COUNT(*) as count FROM fundings')
                stats['total_fundings'] = self.cursor.fetchone()['count']
                
                # التمويلات المكتملة
                self.cursor.execute('SELECT COUNT(*) as count FROM fundings WHERE status = "completed"')
                stats['completed_fundings'] = self.cursor.fetchone()['count']
                
                # التمويلات قيد التنفيذ
                self.cursor.execute('SELECT COUNT(*) as count FROM fundings WHERE status = "in_progress"')
                stats['pending_fundings'] = self.cursor.fetchone()['count']
                
                # التمويلات الملغاة
                self.cursor.execute('SELECT COUNT(*) as count FROM fundings WHERE status = "cancelled"')
                stats['cancelled_fundings'] = self.cursor.fetchone()['count']
                
                # إجمالي الأعضاء المموّلين
                self.cursor.execute('SELECT SUM(members_count) as total FROM fundings WHERE status = "completed"')
                result = self.cursor.fetchone()
                stats['total_members'] = result['total'] or 0
                
                # إجمالي النقاط
                self.cursor.execute('SELECT SUM(points) as total FROM users')
                result = self.cursor.fetchone()
                stats['total_points'] = result['total'] or 0
                
                # إجمالي الملفات
                self.cursor.execute('SELECT COUNT(*) as count FROM files')
                stats['total_files'] = self.cursor.fetchone()['count']
                
                # إجمالي الأرقام
                self.cursor.execute('SELECT COUNT(*) as count FROM numbers WHERE valid = 1')
                stats['total_numbers'] = self.cursor.fetchone()['count']
                
                # الأرقام الصالحة
                self.cursor.execute('SELECT COUNT(*) as count FROM numbers WHERE valid = 1 AND used = 0')
                stats['valid_numbers'] = self.cursor.fetchone()['count']
                
            elif self.db_type == "mongodb":
                stats['total_users'] = self.mongo_db.users.count_documents({})
                stats['active_users'] = self.mongo_db.users.count_documents({'last_active': {'$gte': today_start}})
                stats['banned_users'] = self.mongo_db.users.count_documents({'is_banned': True})
                stats['total_fundings'] = self.mongo_db.fundings.count_documents({})
                stats['completed_fundings'] = self.mongo_db.fundings.count_documents({'status': 'completed'})
                stats['pending_fundings'] = self.mongo_db.fundings.count_documents({'status': 'in_progress'})
                stats['cancelled_fundings'] = self.mongo_db.fundings.count_documents({'status': 'cancelled'})
                
                result = self.mongo_db.fundings.aggregate([
                    {'$match': {'status': 'completed'}},
                    {'$group': {'_id': None, 'total': {'$sum': '$members_count'}}}
                ])
                stats['total_members'] = next(result, {}).get('total', 0)
                
                result = self.mongo_db.users.aggregate([
                    {'$group': {'_id': None, 'total': {'$sum': '$points'}}}
                ])
                stats['total_points'] = next(result, {}).get('total', 0)
                
                stats['total_files'] = self.mongo_db.files.count_documents({})
                stats['total_numbers'] = self.mongo_db.numbers.count_documents({'valid': True})
                stats['valid_numbers'] = self.mongo_db.numbers.count_documents({'valid': True, 'used': False})
            
            return stats
            
        except Exception as e:
            logging.error(f"❌ فشل الحصول على الإحصائيات: {e}")
        return {}
    
    def close(self):
        """إغلاق اتصال قاعدة البيانات"""
        try:
            if self.db_type == "sqlite" and self.connection:
                self.connection.close()
            elif self.db_type == "mongodb" and self.mongo_client:
                self.mongo_client.close()
            if self.redis_client:
                self.redis_client.close()
        except:
            pass

# ==================== إعدادات البوت ====================
class FundingBot:
    """فئة البوت الرئيسية"""
    
    def __init__(self, token):
        self.bot = telebot.TeleBot(token, parse_mode='HTML')
        self.db = DatabaseManager()
        self.executor = ThreadPoolExecutor(max_workers=WORKER_THREADS)
        self.task_queue = queue.Queue(maxsize=QUEUE_SIZE)
        self.active_fundings = {}
        self.user_states = {}
        self.message_cache = {}
        self.user_cache = {}
        self.running = True
        self.start_time = datetime.datetime.now()
        
        # تشغيل العاملين
        self.start_workers()
        
        # تشغيل المهام المجدولة
        self.start_scheduler()
        
        # تسجيل معالجي الأوامر
        self.register_handlers()
        
        logging.info("✅ تم تهيئة البوت بنجاح")
    
    def start_workers(self):
        """تشغيل خيوط العاملين"""
        for i in range(WORKER_THREADS):
            worker = threading.Thread(target=self.process_queue, daemon=True)
            worker.start()
        logging.info(f"✅ تم تشغيل {WORKER_THREADS} عاملين")
    
    def process_queue(self):
        """معالجة قائمة الانتظار"""
        while self.running:
            try:
                task = self.task_queue.get(timeout=1)
                if task:
                    func, args, kwargs = task
                    try:
                        func(*args, **kwargs)
                    except Exception as e:
                        logging.error(f"❌ خطأ في معالجة المهمة: {e}")
            except queue.Empty:
                continue
            except Exception as e:
                logging.error(f"❌ خطأ في حلقة المعالجة: {e}")
    
    def add_task(self, func, *args, **kwargs):
        """إضافة مهمة إلى قائمة الانتظار"""
        try:
            self.task_queue.put((func, args, kwargs), block=False)
        except queue.Full:
            logging.warning("⚠️ قائمة الانتظار ممتلئة")
    
    def start_scheduler(self):
        """تشغيل المهام المجدولة"""
        def run_scheduler():
            while self.running:
                try:
                    # التحقق من التمويلات المنتهية
                    self.check_expired_fundings()
                    
                    # تحديث الكاش
                    self.cleanup_cache()
                    
                    # حفظ نسخة احتياطية كل ساعة
                    if datetime.datetime.now().minute == 0:
                        self.create_backup()
                    
                except Exception as e:
                    logging.error(f"❌ خطأ في المجدول: {e}")
                
                time.sleep(60)  # تشغيل كل دقيقة
        
        scheduler = threading.Thread(target=run_scheduler, daemon=True)
        scheduler.start()
        logging.info("✅ تم تشغيل المجدول")
    
    def check_expired_fundings(self):
        """التحقق من التمويلات المنتهية"""
        try:
            pending = self.db.get_pending_fundings()
            timeout = self.db.get_setting('funding_timeout', FUNDING_TIMEOUT)
            now = datetime.datetime.now()
            
            for funding in pending:
                if funding['status'] == 'in_progress':
                    start_time = datetime.datetime.fromisoformat(funding['start_time'])
                    elapsed = (now - start_time).total_seconds()
                    
                    if elapsed > timeout:
                        # إلغاء التمويل المنتهي
                        self.cancel_funding(funding['funding_id'], 'timeout', 'انتهت مهلة التمويل')
                        
        except Exception as e:
            logging.error(f"❌ خطأ في التحقق من التمويلات المنتهية: {e}")
    
    def cleanup_cache(self):
        """تنظيف الكاش"""
        try:
            now = time.time()
            
            # تنظيف كاش الرسائل
            expired_messages = [msg_id for msg_id, (timestamp, _) in self.message_cache.items() 
                              if now - timestamp > CACHE_TIMEOUT]
            for msg_id in expired_messages:
                del self.message_cache[msg_id]
            
            # تنظيف كاش المستخدمين
            expired_users = [user_id for user_id, (timestamp, _) in self.user_cache.items() 
                           if now - timestamp > CACHE_TIMEOUT]
            for user_id in expired_users:
                del self.user_cache[user_id]
            
            # تنظيف حالات المستخدمين القديمة
            expired_states = [user_id for user_id, state in self.user_states.items()
                            if now - state.get('timestamp', 0) > CACHE_TIMEOUT]
            for user_id in expired_states:
                del self.user_states[user_id]
                
        except Exception as e:
            logging.error(f"❌ خطأ في تنظيف الكاش: {e}")
    
    def create_backup(self):
        """إنشاء نسخة احتياطية"""
        try:
            backup_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"backup_{backup_id}"
            backup_path = f"backups/{backup_name}.db"
            
            os.makedirs("backups", exist_ok=True)
            
            if self.db.db_type == "sqlite":
                # نسخ ملف قاعدة البيانات
                import shutil
                shutil.copy2(DB_NAME, backup_path)
                
                # تسجيل النسخة
                backup_size = os.path.getsize(backup_path)
                self.db.cursor.execute('''
                    INSERT INTO backups (backup_id, backup_name, backup_path, backup_size, created_date)
                    VALUES (?, ?, ?, ?, ?)
                ''', (backup_id, backup_name, backup_path, backup_size, datetime.datetime.now().isoformat()))
                self.db.connection.commit()
                
                logging.info(f"✅ تم إنشاء نسخة احتياطية: {backup_name}")
                
        except Exception as e:
            logging.error(f"❌ خطأ في إنشاء النسخة الاحتياطية: {e}")
    
    def register_handlers(self):
        """تسجيل معالجي الأوامر"""
        
        # ==================== معالج أمر /start ====================
        @self.bot.message_handler(commands=['start'])
        def start_command(message):
            user_id = message.from_user.id
            username = message.from_user.username or "لا يوجد"
            first_name = message.from_user.first_name or ""
            last_name = message.from_user.last_name or ""
            
            # التحقق من الاشتراك الإجباري
            if not self.check_force_join(user_id):
                self.send_force_join_message(message.chat.id)
                return
            
            # التحقق من الحظر
            user = self.db.get_user(user_id)
            if user and user.get('is_banned', 0) == 1:
                self.bot.send_message(message.chat.id, "🚫 أنت محظور من استخدام البوت")
                return
            
            # معلمة الدعوة
            args = message.text.split()
            invited_by = int(args[1]) if len(args) > 1 and args[1].isdigit() else None
            
            # إضافة المستخدم
            self.db.add_user(user_id, username, first_name, last_name, invited_by)
            
            # إرسال رسالة الترحيب
            self.send_welcome(message.chat.id, user_id)
        
        # ==================== معالج النصوص ====================
        @self.bot.message_handler(func=lambda message: True)
        def handle_text(message):
            user_id = message.from_user.id
            
            # التحقق من الاشتراك الإجباري
            if not self.check_force_join(user_id):
                self.send_force_join_message(message.chat.id)
                return
            
            # التحقق من الحظر
            user = self.db.get_user(user_id)
            if user and user.get('is_banned', 0) == 1:
                return
            
            text = message.text.strip()
            
            # التحقق من حالة المستخدم
            if user_id in self.user_states:
                state = self.user_states[user_id]
                self.handle_state(message, state)
                return
            
            # معالجة الأزرار
            if text == BTN_MAIN_POINTS:
                self.show_points_menu(message.chat.id, user_id)
            elif text == BTN_MAIN_FUNDING:
                self.show_funding_menu(message.chat.id, user_id)
            elif text == BTN_MAIN_MY_FUNDINGS:
                self.show_my_fundings(message.chat.id, user_id)
            elif text == BTN_MAIN_STATS:
                self.show_user_stats(message.chat.id, user_id)
            elif text == BTN_MAIN_SUPPORT:
                self.show_support(message.chat.id)
            elif text == BTN_MAIN_CHANNEL:
                self.show_channel(message.chat.id)
            elif text == BTN_MAIN_BACK:
                self.show_main_menu(message.chat.id, user_id)
            elif text == BTN_MAIN_HOME:
                self.show_main_menu(message.chat.id, user_id)
            elif text == BTN_POINTS_INVITE:
                self.show_invite_link(message.chat.id, user_id)
            elif text == BTN_POINTS_CHARGE:
                self.bot.send_message(message.chat.id, "📞 للشحن، تواصل مع الدعم الفني")
            elif text.startswith(BTN_FUNDING_1) or text.startswith(BTN_FUNDING_5) or \
                 text.startswith(BTN_FUNDING_10) or text.startswith(BTN_FUNDING_20) or \
                 text.startswith(BTN_FUNDING_50) or text.startswith(BTN_FUNDING_100):
                self.handle_funding_amount(message.chat.id, user_id, text)
            elif text == BTN_FUNDING_CUSTOM:
                self.request_custom_amount(message.chat.id, user_id)
            elif user_id in ADMIN_IDS and text == BTN_ADMIN_STATS:
                self.show_admin_stats(message.chat.id)
            elif user_id in ADMIN_IDS and text == BTN_ADMIN_USERS:
                self.show_admin_users(message.chat.id)
            elif user_id in ADMIN_IDS and text == BTN_ADMIN_ADD_POINTS:
                self.request_user_id_for_points(message.chat.id, 'add')
            elif user_id in ADMIN_IDS and text == BTN_ADMIN_REMOVE_POINTS:
                self.request_user_id_for_points(message.chat.id, 'remove')
            elif user_id in ADMIN_IDS and text == BTN_ADMIN_FILES:
                self.show_files_menu(message.chat.id)
            elif user_id in ADMIN_IDS and text == BTN_ADMIN_ADD_FILE:
                self.request_file_upload(message.chat.id)
            elif user_id in ADMIN_IDS and text == BTN_ADMIN_DELETE_FILE:
                self.show_files_for_deletion(message.chat.id)
            elif user_id in ADMIN_IDS and text == BTN_ADMIN_VIEW_FILES:
                self.show_all_files(message.chat.id)
            elif user_id in ADMIN_IDS and text == BTN_ADMIN_SUPPORT:
                self.request_support_username(message.chat.id)
            elif user_id in ADMIN_IDS and text == BTN_ADMIN_CHANNEL:
                self.request_channel_link(message.chat.id)
            elif user_id in ADMIN_IDS and text == BTN_ADMIN_BAN:
                self.request_user_id_for_ban(message.chat.id)
            elif user_id in ADMIN_IDS and text == BTN_ADMIN_UNBAN:
                self.request_user_id_for_unban(message.chat.id)
            elif user_id in ADMIN_IDS and text == BTN_ADMIN_SETTINGS:
                self.show_settings_menu(message.chat.id)
            elif user_id in ADMIN_IDS and text == BTN_ADMIN_INVITE_REWARD:
                self.request_invite_reward(message.chat.id)
            elif user_id in ADMIN_IDS and text == BTN_ADMIN_MEMBER_PRICE:
                self.request_member_price(message.chat.id)
            elif user_id in ADMIN_IDS and text == BTN_ADMIN_FORCE_JOIN:
                self.show_force_join_menu(message.chat.id)
            elif user_id in ADMIN_IDS and text == BTN_ADMIN_ADD_CHANNEL:
                self.request_force_join_channel(message.chat.id)
            elif user_id in ADMIN_IDS and text == BTN_ADMIN_REMOVE_CHANNEL:
                self.show_force_join_channels(message.chat.id)
            elif user_id in ADMIN_IDS and text == BTN_ADMIN_VIEW_CHANNELS:
                self.show_force_join_channels(message.chat.id, view_only=True)
            elif user_id in ADMIN_IDS and text == BTN_ADMIN_BROADCAST:
                self.request_broadcast_message(message.chat.id)
            elif user_id in ADMIN_IDS and text == BTN_ADMIN_BACKUP:
                self.create_backup()
                self.bot.send_message(message.chat.id, "✅ تم إنشاء نسخة احتياطية")
            elif user_id in ADMIN_IDS and text == BTN_ADMIN_RESTORE:
                self.show_backups(message.chat.id)
            elif user_id in ADMIN_IDS and text == BTN_ADMIN_LOGS:
                self.send_logs(message.chat.id)
            else:
                self.show_main_menu(message.chat.id, user_id)
    
    # ==================== دوال المساعدة ====================
    def check_force_join(self, user_id):
        """التحقق من الاشتراك الإجباري"""
        try:
            enabled = self.db.get_setting('force_join_enabled', False)
            if not enabled:
                return True
            
            channels = self.db.get_force_join_channels()
            if not channels:
                return True
            
            for channel in channels:
                try:
                    chat = self.bot.get_chat(channel['channel_id'])
                    member = self.bot.get_chat_member(chat.id, user_id)
                    if member.status in ['left', 'kicked']:
                        return False
                except:
                    return False
            
            return True
            
        except Exception as e:
            logging.error(f"❌ خطأ في التحقق من الاشتراك الإجباري: {e}")
        return True
    
    def send_force_join_message(self, chat_id):
        """إرسال رسالة الاشتراك الإجباري"""
        channels = self.db.get_force_join_channels()
        text = "🔒 يجب الاشتراك في القنوات التالية لاستخدام البوت:\n\n"
        
        for channel in channels:
            text += f"📢 {channel['channel_title']}\n"
            text += f"🔗 {channel['channel_link']}\n\n"
        
        text += "بعد الاشتراك، أرسل /start مرة أخرى"
        
        markup = InlineKeyboardMarkup()
        for channel in channels:
            markup.add(InlineKeyboardButton(
                f"📢 {channel['channel_title']}",
                url=channel['channel_link']
            ))
        
        self.bot.send_message(chat_id, text, reply_markup=markup)
    
    def handle_state(self, message, state):
        """معالجة حالة المستخدم"""
        user_id = message.from_user.id
        text = message.text.strip()
        
        if state['action'] == 'waiting_funding_channel':
            # استلام رابط القناة للتمويل
            self.process_funding_channel(message.chat.id, user_id, text)
        
        elif state['action'] == 'waiting_custom_amount':
            # استلام عدد أعضاء مخصص
            if text.isdigit():
                amount = int(text)
                self.process_funding_amount(message.chat.id, user_id, amount)
            else:
                self.bot.send_message(message.chat.id, "❌ الرجاء إدخال رقم صحيح")
        
        elif state['action'] == 'waiting_user_id_for_points' and user_id in ADMIN_IDS:
            # استلام ايدي المستخدم للشحن/الخصم
            if text.isdigit():
                self.user_states[user_id] = {
                    'action': f'waiting_points_amount_{state["points_type"]}',
                    'target_user': int(text),
                    'timestamp': time.time()
                }
                self.bot.send_message(message.chat.id, f"💰 أدخل المبلغ لـ {state['points_type']}:")
            else:
                self.bot.send_message(message.chat.id, "❌ الرجاء إدخال ايدي صحيح")
        
        elif state['action'].startswith('waiting_points_amount_') and user_id in ADMIN_IDS:
            # استلام المبلغ للشحن/الخصم
            if text.isdigit() or (text.startswith('-') and text[1:].isdigit()):
                amount = int(text)
                points_type = state['action'].replace('waiting_points_amount_', '')
                target_user = state['target_user']
                
                if points_type == 'add':
                    if self.db.update_user_points(target_user, amount, 'admin_add', f'شحن من قبل الإدارة'):
                        self.bot.send_message(message.chat.id, f"✅ تم شحن {amount} نقطة للمستخدم {target_user}")
                        self.notify_user(target_user, f"💰 تم شحن {amount} نقطة إلى رصيدك")
                    else:
                        self.bot.send_message(message.chat.id, "❌ فشل شحن الرصيد")
                
                elif points_type == 'remove':
                    if self.db.update_user_points(target_user, -amount, 'admin_remove', f'خصم من قبل الإدارة'):
                        self.bot.send_message(message.chat.id, f"✅ تم خصم {amount} نقطة من المستخدم {target_user}")
                        self.notify_user(target_user, f"💰 تم خصم {amount} نقطة من رصيدك")
                    else:
                        self.bot.send_message(message.chat.id, "❌ فشل خصم الرصيد")
                
                del self.user_states[user_id]
                self.show_admin_panel(message.chat.id)
            else:
                self.bot.send_message(message.chat.id, "❌ الرجاء إدخال رقم صحيح")
        
        elif state['action'] == 'waiting_user_id_for_ban' and user_id in ADMIN_IDS:
            # حظر مستخدم
            if text.isdigit():
                target_user = int(text)
                user = self.db.get_user(target_user)
                if user:
                    self.db.ban_user(target_user)
                    self.bot.send_message(message.chat.id, f"✅ تم حظر المستخدم {target_user}")
                    self.notify_user(target_user, "🚫 تم حظرك من استخدام البوت")
                else:
                    self.bot.send_message(message.chat.id, "❌ المستخدم غير موجود")
                del self.user_states[user_id]
                self.show_admin_panel(message.chat.id)
            else:
                self.bot.send_message(message.chat.id, "❌ الرجاء إدخال ايدي صحيح")
        
        elif state['action'] == 'waiting_user_id_for_unban' and user_id in ADMIN_IDS:
            # رفع حظر مستخدم
            if text.isdigit():
                target_user = int(text)
                user = self.db.get_user(target_user)
                if user:
                    self.db.unban_user(target_user)
                    self.bot.send_message(message.chat.id, f"✅ تم رفع الحظر عن المستخدم {target_user}")
                    self.notify_user(target_user, "✅ تم رفع الحظر عنك، يمكنك استخدام البوت الآن")
                else:
                    self.bot.send_message(message.chat.id, "❌ المستخدم غير موجود")
                del self.user_states[user_id]
                self.show_admin_panel(message.chat.id)
            else:
                self.bot.send_message(message.chat.id, "❌ الرجاء إدخال ايدي صحيح")
        
        elif state['action'] == 'waiting_support_username' and user_id in ADMIN_IDS:
            # تحديث يوزر الدعم
            username = text.replace('@', '').strip()
            self.db.set_setting('support_username', username, user_id)
            self.bot.send_message(message.chat.id, f"✅ تم تحديث يوزر الدعم إلى @{username}")
            del self.user_states[user_id]
            self.show_admin_panel(message.chat.id)
        
        elif state['action'] == 'waiting_channel_link' and user_id in ADMIN_IDS:
            # تحديث رابط القناة
            link = text.strip()
            self.db.set_setting('channel_link', link, user_id)
            self.bot.send_message(message.chat.id, f"✅ تم تحديث رابط القناة إلى {link}")
            del self.user_states[user_id]
            self.show_admin_panel(message.chat.id)
        
        elif state['action'] == 'waiting_invite_reward' and user_id in ADMIN_IDS:
            # تحديث مكافأة الدعوة
            if text.isdigit():
                reward = int(text)
                self.db.set_setting('invite_reward', reward, user_id)
                self.bot.send_message(message.chat.id, f"✅ تم تحديث مكافأة الدعوة إلى {reward} نقطة")
                del self.user_states[user_id]
                self.show_settings_menu(message.chat.id)
            else:
                self.bot.send_message(message.chat.id, "❌ الرجاء إدخال رقم صحيح")
        
        elif state['action'] == 'waiting_member_price' and user_id in ADMIN_IDS:
            # تحديث سعر العضو
            if text.isdigit():
                price = int(text)
                self.db.set_setting('member_price', price, user_id)
                self.bot.send_message(message.chat.id, f"✅ تم تحديث سعر العضو إلى {price} نقطة")
                del self.user_states[user_id]
                self.show_settings_menu(message.chat.id)
            else:
                self.bot.send_message(message.chat.id, "❌ الرجاء إدخال رقم صحيح")
        
        elif state['action'] == 'waiting_force_join_channel' and user_id in ADMIN_IDS:
            # إضافة قناة للاشتراك الإجباري
            link = text.strip()
            self.add_force_join_channel(user_id, link)
            del self.user_states[user_id]
        
        elif state['action'] == 'waiting_broadcast_message' and user_id in ADMIN_IDS:
            # إرسال رسالة جماعية
            self.send_broadcast(user_id, text)
            del self.user_states[user_id]
    
    # ==================== دوال الواجهات ====================
    def send_welcome(self, chat_id, user_id):
        """إرسال رسالة الترحيب"""
        user = self.db.get_user(user_id)
        if not user:
            return
        
        welcome = self.db.get_setting('welcome_message', WELCOME_MESSAGE)
        text = welcome.format(
            user_id=user_id,
            username=user.get('username', 'لا يوجد'),
            points=user.get('points', 0),
            join_date=user.get('join_date', 'غير معروف')[:10]
        )
        
        self.show_main_menu(chat_id, user_id, text)
    
    def show_main_menu(self, chat_id, user_id, text=None):
        """عرض القائمة الرئيسية"""
        user = self.db.get_user(user_id)
        if not user:
            return
        
        if not text:
            text = MAIN_MENU_TEXT.format(
                username=user.get('username', 'لا يوجد'),
                points=user.get('points', 0),
                user_id=user_id
            )
        
        markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add(
            KeyboardButton(BTN_MAIN_POINTS),
            KeyboardButton(BTN_MAIN_FUNDING),
            KeyboardButton(BTN_MAIN_MY_FUNDINGS),
            KeyboardButton(BTN_MAIN_STATS),
            KeyboardButton(BTN_MAIN_SUPPORT),
            KeyboardButton(BTN_MAIN_CHANNEL)
        )
        
        self.bot.send_message(chat_id, text, reply_markup=markup, parse_mode='HTML')
    
    def show_points_menu(self, chat_id, user_id):
        """عرض قائمة النقاط"""
        user = self.db.get_user(user_id)
        if not user:
            return
        
        text = POINTS_MENU_TEXT.format(
            points=user.get('points', 0),
            invites=user.get('invites_count', 0)
        )
        
        markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add(
            KeyboardButton(BTN_POINTS_INVITE),
            KeyboardButton(BTN_POINTS_CHARGE),
            KeyboardButton(BTN_MAIN_BACK)
        )
        
        self.bot.send_message(chat_id, text, reply_markup=markup)
    
    def show_funding_menu(self, chat_id, user_id):
        """عرض قائمة التمويل"""
        user = self.db.get_user(user_id)
        if not user:
            return
        
        points = user.get('points', 0)
        price = self.db.get_setting('member_price', DEFAULT_PRICE_PER_MEMBER)
        max_members = self.db.get_setting('max_members', MAX_MEMBERS_PER_FUNDING)
        
        # حساب عدد الأعضاء الممكن تمويلهم
        possible_members = min(points // price if price > 0 else 0, max_members)
        
        text = FUNDING_MENU_TEXT.format(
            points=points,
            price_per_member=price,
            max_members=max_members,
            members_count=possible_members,
            total_points=possible_members * price
        )
        
        markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
        markup.add(
            KeyboardButton(BTN_FUNDING_1),
            KeyboardButton(BTN_FUNDING_5),
            KeyboardButton(BTN_FUNDING_10),
            KeyboardButton(BTN_FUNDING_20),
            KeyboardButton(BTN_FUNDING_50),
            KeyboardButton(BTN_FUNDING_100),
            KeyboardButton(BTN_FUNDING_CUSTOM),
            KeyboardButton(BTN_MAIN_BACK)
        )
        
        self.bot.send_message(chat_id, text, reply_markup=markup)
    
    def show_my_fundings(self, chat_id, user_id):
        """عرض تمويلات المستخدم"""
        fundings = self.db.get_user_fundings(user_id, 10)
        
        if not fundings:
            self.bot.send_message(chat_id, "📋 لا يوجد لديك تمويلات سابقة")
            self.show_main_menu(chat_id, user_id)
            return
        
        total_members = sum(f.get('members_count', 0) for f in fundings)
        total_points = sum(f.get('cost', 0) for f in fundings)
        
        recent = ""
        for i, f in enumerate(fundings[:5], 1):
            status_emoji = {
                'completed': '✅',
                'pending': '⏳',
                'in_progress': '🔄',
                'cancelled': '❌'
            }.get(f.get('status', 'unknown'), '❓')
            
            recent += f"{i}. {status_emoji} {f.get('channel_link', 'N/A')[:30]}...\n"
            recent += f"   👥 {f.get('added_members', 0)}/{f.get('members_count', 0)} عضو\n\n"
        
        text = MY_FUNDINGS_TEXT.format(
            total_fundings=len(fundings),
            total_members=total_members,
            total_points_spent=total_points,
            recent_fundings=recent
        )
        
        markup = ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(KeyboardButton(BTN_MAIN_BACK))
        
        self.bot.send_message(chat_id, text, reply_markup=markup)
    
    def show_user_stats(self, chat_id, user_id):
        """عرض إحصائيات المستخدم"""
        user = self.db.get_user(user_id)
        if not user:
            return
        
        fundings = self.db.get_user_fundings(user_id, 100)
        
        completed = sum(1 for f in fundings if f.get('status') == 'completed')
        pending = sum(1 for f in fundings if f.get('status') in ['pending', 'in_progress'])
        cancelled = sum(1 for f in fundings if f.get('status') == 'cancelled')
        total_members = sum(f.get('members_count', 0) for f in fundings if f.get('status') == 'completed')
        
        text = STATS_TEXT.format(
            user_id=user_id,
            username=user.get('username', 'لا يوجد'),
            join_date=user.get('join_date', 'غير معروف')[:10],
            last_active=user.get('last_active', 'غير معروف')[:16],
            points=user.get('points', 0),
            total_points_earned=user.get('total_points_earned', 0),
            total_points_spent=user.get('total_points_spent', 0),
            invite_rewards=user.get('total_points_earned', 0) - user.get('total_points_spent', 0),
            fundings_count=len(fundings),
            total_members_funded=total_members,
            completed_fundings=completed,
            pending_fundings=pending,
            cancelled_fundings=cancelled,
            invites_count=user.get('invites_count', 0),
            invited_users=len(json.loads(user.get('invited_users', '[]'))),
            invite_bonuses=user.get('invites_count', 0) * self.db.get_setting('invite_reward', DEFAULT_POINTS_PER_INVITE)
        )
        
        markup = ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(KeyboardButton(BTN_MAIN_BACK))
        
        self.bot.send_message(chat_id, text, reply_markup=markup)
    
    def show_support(self, chat_id):
        """عرض معلومات الدعم الفني"""
        support = self.db.get_setting('support_username', 'None')
        
        if support and support != 'None':
            text = SUPPORT_TEXT.format(support_username=f"@{support}")
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("📞 تواصل مع الدعم", url=f"https://t.me/{support}"))
        else:
            text = "🆘 الدعم الفني غير متوفر حالياً"
            markup = None
        
        markup_back = ReplyKeyboardMarkup(resize_keyboard=True)
        markup_back.add(KeyboardButton(BTN_MAIN_BACK))
        
        self.bot.send_message(chat_id, text, reply_markup=markup_back)
        if markup:
            self.bot.send_message(chat_id, "اضغط للتواصل:", reply_markup=markup)
    
    def show_channel(self, chat_id):
        """عرض قناة البوت"""
        channel = self.db.get_setting('channel_link', 'None')
        
        if channel and channel != 'None':
            text = CHANNEL_TEXT.format(channel_link=channel)
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("📢 اشترك في القناة", url=channel))
        else:
            text = "📢 قناة البوت غير متوفرة حالياً"
            markup = None
        
        markup_back = ReplyKeyboardMarkup(resize_keyboard=True)
        markup_back.add(KeyboardButton(BTN_MAIN_BACK))
        
        self.bot.send_message(chat_id, text, reply_markup=markup_back)
        if markup:
            self.bot.send_message(chat_id, "اضغط للاشتراك:", reply_markup=markup)
    
    def show_invite_link(self, chat_id, user_id):
        """عرض رابط الدعوة"""
        user = self.db.get_user(user_id)
        if not user:
            return
        
        # إنشاء رابط الدعوة
        invite_link = f"https://t.me/{BOT_USERNAME}?start={user_id}" if BOT_USERNAME else "البوت ليس له اسم مستخدم بعد"
        
        reward = self.db.get_setting('invite_reward', DEFAULT_POINTS_PER_INVITE)
        total_reward = user.get('invites_count', 0) * reward
        
        text = INVITE_LINK_TEXT.format(
            invite_link=invite_link,
            invited_count=user.get('invites_count', 0),
            reward=reward,
            total_reward=total_reward
        )
        
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🔗 مشاركة الرابط", url=f"https://t.me/share/url?url={invite_link}"))
        
        markup_back = ReplyKeyboardMarkup(resize_keyboard=True)
        markup_back.add(KeyboardButton(BTN_MAIN_BACK))
        
        self.bot.send_message(chat_id, text, reply_markup=markup_back)
        self.bot.send_message(chat_id, "اضغط للمشاركة:", reply_markup=markup)
    
    def handle_funding_amount(self, chat_id, user_id, text):
        """معالجة اختيار عدد الأعضاء للتمويل"""
        # استخراج الرقم من النص
        match = re.search(r'\d+', text)
        if not match:
            return
        
        amount = int(match.group())
        self.process_funding_amount(chat_id, user_id, amount)
    
    def request_custom_amount(self, chat_id, user_id):
        """طلب عدد أعضاء مخصص"""
        self.user_states[user_id] = {
            'action': 'waiting_custom_amount',
            'timestamp': time.time()
        }
        self.bot.send_message(chat_id, "✏️ أرسل عدد الأعضاء المطلوب:")
    
    def process_funding_amount(self, chat_id, user_id, amount):
        """معالجة عدد الأعضاء المطلوب"""
        user = self.db.get_user(user_id)
        if not user:
            return
        
        points = user.get('points', 0)
        price = self.db.get_setting('member_price', DEFAULT_PRICE_PER_MEMBER)
        max_members = self.db.get_setting('max_members', MAX_MEMBERS_PER_FUNDING)
        min_members = self.db.get_setting('min_members', MIN_MEMBERS_PER_FUNDING)
        
        # التحقق من صحة العدد
        if amount < min_members:
            self.bot.send_message(chat_id, f"❌ الحد الأدنى للتمويل هو {min_members} عضو")
            return
        
        if amount > max_members:
            self.bot.send_message(chat_id, f"❌ الحد الأقصى للتمويل هو {max_members} عضو")
            return
        
        cost = amount * price
        
        if points < cost:
            self.bot.send_message(chat_id, f"❌ رصيدك غير كافٍ\nالمطلوب: {cost} نقطة\nرصيدك: {points} نقطة")
            return
        
        # طلب رابط القناة
        self.user_states[user_id] = {
            'action': 'waiting_funding_channel',
            'funding_amount': amount,
            'funding_cost': cost,
            'timestamp': time.time()
        }
        
        text = FUNDING_REQUEST_TEXT.format(
            members_count=amount,
            cost=cost,
            balance=points
        )
        
        self.bot.send_message(chat_id, text)
        self.bot.send_message(chat_id, "🔗 أرسل رابط القناة أو المجموعة (يجب أن يكون البوت مشرفاً فيها)")
    
    def process_funding_channel(self, chat_id, user_id, channel_link):
        """معالجة رابط القناة والبدء بالتمويل"""
        state = self.user_states.get(user_id)
        if not state:
            return
        
        amount = state['funding_amount']
        cost = state['funding_cost']
        
        # التحقق من صحة الرابط
        if not self.validate_channel_link(channel_link):
            self.bot.send_message(chat_id, "❌ رابط غير صالح. الرجاء التأكد من الرابط")
            return
        
        # التحقق من أن البوت مشرف
        if not self.check_bot_admin(channel_link):
            self.bot.send_message(chat_id, "❌ البوت ليس مشرفاً في القناة. الرجاء جعل البوت مشرفاً ثم أعد المحاولة")
            return
        
        # خصم النقاط
        if not self.db.update_user_points(user_id, -cost, 'funding', f'تمويل {amount} عضو'):
            self.bot.send_message(chat_id, "❌ فشل خصم النقاط")
            return
        
        # إنشاء التمويل
        funding_id = self.db.create_funding(user_id, channel_link, amount, cost)
        if not funding_id:
            self.bot.send_message(chat_id, "❌ فشل إنشاء التمويل")
            # استرداد النقاط
            self.db.update_user_points(user_id, cost, 'refund', 'استرداد نقاط بسبب فشل التمويل')
            return
        
        # بدء التمويل
        self.start_funding(funding_id, user_id, channel_link, amount, cost)
        
        # إشعار الإدارة
        self.notify_admin_new_funding(user_id, funding_id, channel_link, amount, cost)
        
        del self.user_states[user_id]
    
    def validate_channel_link(self, link):
        """التحقق من صحة رابط القناة"""
        patterns = [
            r'^https?://t\.me/[a-zA-Z0-9_]+$',
            r'^https?://telegram\.me/[a-zA-Z0-9_]+$',
            r'^@[a-zA-Z0-9_]+$',
            r'^[a-zA-Z0-9_]+$'
        ]
        
        for pattern in patterns:
            if re.match(pattern, link):
                return True
        return False
    
    def check_bot_admin(self, channel_link):
        """التحقق من أن البوت مشرف في القناة"""
        try:
            # استخراج اسم المستخدم من الرابط
            username = channel_link.split('/')[-1].replace('@', '')
            
            # محاولة الحصول على معلومات القناة
            chat = self.bot.get_chat(f"@{username}")
            
            # التحقق من صلاحيات البوت
            bot_member = self.bot.get_chat_member(chat.id, self.bot.get_me().id)
            return bot_member.status in ['administrator', 'creator']
            
        except Exception as e:
            logging.error(f"❌ خطأ في التحقق من صلاحيات البوت: {e}")
        return False
    
    def start_funding(self, funding_id, user_id, channel_link, total_members, cost):
        """بدء عملية التمويل"""
        # تحديث حالة التمويل
        self.db.update_funding(funding_id, status='in_progress')
        
        # إضافة إلى التمويلات النشطة
        self.active_fundings[funding_id] = {
            'user_id': user_id,
            'channel_link': channel_link,
            'total_members': total_members,
            'added_members': 0,
            'cost': cost,
            'start_time': datetime.datetime.now(),
            'last_update': datetime.datetime.now(),
            'status': 'in_progress',
            'progress': []
        }
        
        # إرسال رسالة بدء التمويل
        text = FUNDING_START_TEXT.format(
            funding_id=funding_id,
            channel_link=channel_link,
            members_count=total_members,
            cost=cost,
            start_time=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
        self.bot.send_message(user_id, text)
        
        # بدء التمويل في خيط منفصل
        self.add_task(self.process_funding, funding_id)
    
    def process_funding(self, funding_id):
        """معالجة التمويل (إضافة الأعضاء)"""
        funding = self.active_fundings.get(funding_id)
        if not funding:
            return
        
        user_id = funding['user_id']
        channel_link = funding['channel_link']
        total = funding['total_members']
        delay = self.db.get_setting('funding_delay', FUNDING_DELAY)
        
        try:
            while funding['added_members'] < total and funding['status'] == 'in_progress':
                # الحصول على رقم عشوائي
                numbers = self.db.get_random_numbers(1)
                if not numbers:
                    # لا يوجد أرقام كافية
                    self.bot.send_message(user_id, "⚠️ نفدت الأرقام المتاحة، يرجى إبلاغ الإدارة")
                    break
                
                number = numbers[0]
                
                # محاولة إضافة العضو
                if self.add_member_to_channel(channel_link, number):
                    funding['added_members'] += 1
                    funding['progress'].append({
                        'number': number,
                        'time': datetime.datetime.now().isoformat(),
                        'status': 'success'
                    })
                    
                    # تحديث قاعدة البيانات
                    self.db.update_funding(funding_id, 
                                         added_members=funding['added_members'],
                                         progress=json.dumps(funding['progress']))
                    
                    # إرسال تحديث التقدم
                    self.send_funding_progress(user_id, funding_id, funding)
                else:
                    funding['progress'].append({
                        'number': number,
                        'time': datetime.datetime.now().isoformat(),
                        'status': 'failed'
                    })
                
                # انتظار قبل الإضافة التالية
                time.sleep(delay)
            
            # التحقق من اكتمال التمويل
            if funding['added_members'] >= total:
                self.complete_funding(funding_id)
            else:
                self.pause_funding(funding_id, 'نفاد الأرقام')
                
        except Exception as e:
            logging.error(f"❌ خطأ في معالجة التمويل {funding_id}: {e}")
            self.fail_funding(funding_id, str(e))
    
    def add_member_to_channel(self, channel_link, phone_number):
        """إضافة عضو إلى القناة"""
        try:
            # هذه دالة تجريبية - في الواقع تحتاج إلى استخدام API تليجرام
            # أو مكتبة خاصة للتعامل مع حسابات المستخدمين
            
            # استخراج اسم المستخدم من الرابط
            username = channel_link.split('/')[-1].replace('@', '')
            
            # محاكاة إضافة العضو (للتجربة)
            # في الإنتاج، يجب استخدام API حقيقي
            
            logging.info(f"✅ تم إضافة {phone_number} إلى {username}")
            return True
            
        except Exception as e:
            logging.error(f"❌ فشل إضافة العضو {phone_number}: {e}")
        return False
    
    def send_funding_progress(self, user_id, funding_id, funding):
        """إرسال تقدم التمويل"""
        added = funding['added_members']
        total = funding['total_members']
        remaining = total - added
        progress = (added / total) * 100 if total > 0 else 0
        
        # حساب الوقت المستغرق والمتبقي
        elapsed = (datetime.datetime.now() - funding['start_time']).total_seconds()
        avg_time = elapsed / added if added > 0 else 0
        estimated = avg_time * remaining if remaining > 0 else 0
        
        # آخر عضو تمت إضافته
        last_added = funding['progress'][-1]['number'] if funding['progress'] else 'لا يوجد'
        
        text = FUNDING_PROGRESS_TEXT.format(
            funding_id=funding_id,
            channel_link=funding['channel_link'],
            added=added,
            total=total,
            remaining=remaining,
            progress=f"{progress:.1f}%",
            elapsed_time=self.format_time(elapsed),
            estimated_time=self.format_time(estimated),
            last_added=last_added
        )
        
        self.bot.send_message(user_id, text)
    
    def complete_funding(self, funding_id):
        """إكمال التمويل بنجاح"""
        funding = self.active_fundings.get(funding_id)
        if not funding:
            return
        
        # تحديث الحالة
        funding['status'] = 'completed'
        funding['end_time'] = datetime.datetime.now()
        self.db.update_funding(funding_id, status='completed', 
                             end_time=funding['end_time'].isoformat())
        
        # حساب الوقت المستغرق
        elapsed = (funding['end_time'] - funding['start_time']).total_seconds()
        
        # إرسال رسالة الإكمال
        text = FUNDING_COMPLETE_TEXT.format(
            funding_id=funding_id,
            channel_link=funding['channel_link'],
            total_members=funding['added_members'],
            cost=funding['cost'],
            elapsed_time=self.format_time(elapsed),
            completion_date=funding['end_time'].strftime("%Y-%m-%d %H:%M:%S")
        )
        
        self.bot.send_message(funding['user_id'], text)
        
        # إزالة من التمويلات النشطة
        del self.active_fundings[funding_id]
        
        logging.info(f"✅ اكتمل التمويل {funding_id}")
    
    def pause_funding(self, funding_id, reason):
        """إيقاف التمويل مؤقتاً"""
        funding = self.active_fundings.get(funding_id)
        if not funding:
            return
        
        funding['status'] = 'paused'
        funding['pause_reason'] = reason
        self.db.update_funding(funding_id, status='paused', pause_reason=reason)
        
        self.bot.send_message(funding['user_id'], 
                            f"⏸️ تم إيقاف التمويل مؤقتاً\nالسبب: {reason}")
        
        logging.warning(f"⏸️ توقف التمويل {funding_id}: {reason}")
    
    def fail_funding(self, funding_id, error):
        """فشل التمويل"""
        funding = self.active_fundings.get(funding_id)
        if not funding:
            return
        
        funding['status'] = 'failed'
        funding['error'] = error
        self.db.update_funding(funding_id, status='failed', error=error)
        
        # استرداد النقاط للأعضاء الذين لم يتم إضافتهم
        remaining = funding['total_members'] - funding['added_members']
        refund = remaining * self.db.get_setting('member_price', DEFAULT_PRICE_PER_MEMBER)
        
        if refund > 0:
            self.db.update_user_points(funding['user_id'], refund, 'refund', 
                                      f'استرداد نقاط بسبب فشل التمويل')
        
        text = FUNDING_ERROR_TEXT.format(
            funding_id=funding_id,
            channel_link=funding['channel_link'],
            error_type='فشل التمويل',
            error_details=error
        )
        
        self.bot.send_message(funding['user_id'], text)
        
        # إزالة من التمويلات النشطة
        del self.active_fundings[funding_id]
        
        logging.error(f"❌ فشل التمويل {funding_id}: {error}")
    
    def cancel_funding(self, funding_id, cancelled_by, reason):
        """إلغاء التمويل"""
        funding = self.active_fundings.get(funding_id)
        if not funding:
            return
        
        funding['status'] = 'cancelled'
        funding['cancelled_by'] = cancelled_by
        funding['cancelled_at'] = datetime.datetime.now()
        self.db.update_funding(funding_id, status='cancelled', 
                             cancelled_by=cancelled_by, cancel_reason=reason)
        
        # استرداد النقاط للأعضاء الذين لم يتم إضافتهم
        remaining = funding['total_members'] - funding['added_members']
        refund = remaining * self.db.get_setting('member_price', DEFAULT_PRICE_PER_MEMBER)
        
        if refund > 0:
            self.db.update_user_points(funding['user_id'], refund, 'refund', 
                                      f'استرداد نقاط بسبب إلغاء التمويل')
        
        # حساب الوقت المستغرق
        elapsed = (funding['cancelled_at'] - funding['start_time']).total_seconds()
        
        # إرسال رسالة الإلغاء للمستخدم
        text = FUNDING_CANCELLED_TEXT.format(
            funding_id=funding_id,
            channel_link=funding['channel_link'],
            added=funding['added_members'],
            total=funding['total_members'],
            refund=refund,
            elapsed_time=self.format_time(elapsed),
            cancelled_date=funding['cancelled_at'].strftime("%Y-%m-%d %H:%M:%S")
        )
        
        self.bot.send_message(funding['user_id'], text)
        
        # إزالة من التمويلات النشطة
        del self.active_fundings[funding_id]
        
        logging.info(f"🛑 تم إلغاء التمويل {funding_id} بواسطة {cancelled_by}")
    
    def format_time(self, seconds):
        """تنسيق الوقت"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        
        if hours > 0:
            return f"{hours} ساعة {minutes} دقيقة"
        elif minutes > 0:
            return f"{minutes} دقيقة {secs} ثانية"
        else:
            return f"{secs} ثانية"
    
    def notify_user(self, user_id, message):
        """إرسال إشعار لمستخدم"""
        try:
            self.bot.send_message(user_id, message)
        except:
            pass
    
    def notify_admin_new_funding(self, user_id, funding_id, channel_link, members, cost):
        """إشعار الإدارة بتمويل جديد"""
        user = self.db.get_user(user_id)
        if not user:
            return
        
        text = ADMIN_FUNDING_NOTIFICATION.format(
            username=user.get('username', 'لا يوجد'),
            user_id=user_id,
            user_balance=user.get('points', 0),
            funding_id=funding_id,
            channel_link=channel_link,
            members_count=members,
            cost=cost,
            request_time=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
        
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(
            InlineKeyboardButton(BTN_FUNDING_APPROVE, callback_data=f"approve_{funding_id}"),
            InlineKeyboardButton(BTN_FUNDING_REJECT, callback_data=f"reject_{funding_id}"),
            InlineKeyboardButton(BTN_FUNDING_CANCEL, callback_data=f"cancel_{funding_id}"),
            InlineKeyboardButton(BTN_FUNDING_BAN_USER, callback_data=f"ban_{user_id}")
        )
        
        for admin_id in ADMIN_IDS:
            try:
                self.bot.send_message(admin_id, text, reply_markup=markup)
            except:
                pass
    
    # ==================== دوال لوحة التحكم ====================
    def show_admin_panel(self, chat_id):
        """عرض لوحة التحكم"""
        stats = self.db.get_stats()
        
        support = self.db.get_setting('support_username', 'لا يوجد')
        channel = self.db.get_setting('channel_link', 'لا يوجد')
        
        text = ADMIN_PANEL_TEXT.format(
            total_users=stats.get('total_users', 0),
            active_users=stats.get('active_users', 0),
            banned_users=stats.get('banned_users', 0),
            total_fundings=stats.get('total_fundings', 0),
            total_members=stats.get('total_members', 0),
            total_points=stats.get('total_points', 0),
            total_points_spent=stats.get('total_points_spent', 0),
            total_files=stats.get('total_files', 0),
            support_username=f"@{support}" if support != 'لا يوجد' else 'غير محدد',
            channel_link=channel if channel != 'لا يوجد' else 'غير محدد'
        )
        
        markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add(
            KeyboardButton(BTN_ADMIN_STATS),
            KeyboardButton(BTN_ADMIN_USERS),
            KeyboardButton(BTN_ADMIN_ADD_POINTS),
            KeyboardButton(BTN_ADMIN_REMOVE_POINTS),
            KeyboardButton(BTN_ADMIN_FILES),
            KeyboardButton(BTN_ADMIN_SUPPORT),
            KeyboardButton(BTN_ADMIN_CHANNEL),
            KeyboardButton(BTN_ADMIN_BAN),
            KeyboardButton(BTN_ADMIN_UNBAN),
            KeyboardButton(BTN_ADMIN_SETTINGS),
            KeyboardButton(BTN_ADMIN_BROADCAST),
            KeyboardButton(BTN_ADMIN_BACKUP),
            KeyboardButton(BTN_ADMIN_LOGS),
            KeyboardButton(BTN_MAIN_HOME)
        )
        
        self.bot.send_message(chat_id, text, reply_markup=markup)
    
    def show_admin_stats(self, chat_id):
        """عرض إحصائيات البوت"""
        stats = self.db.get_stats()
        
        # حساب إحصائيات إضافية
        now = datetime.datetime.now()
        uptime = now - self.start_time
        
        text = ADMIN_STATS_TEXT.format(
            # إحصائيات المستخدمين
            total_users=stats.get('total_users', 0),
            new_users_today=stats.get('new_users_today', 0),
            new_users_week=stats.get('new_users_week', 0),
            new_users_month=stats.get('new_users_month', 0),
            active_today=stats.get('active_today', 0),
            active_week=stats.get('active_week', 0),
            active_month=stats.get('active_month', 0),
            banned_users=stats.get('banned_users', 0),
            
            # إحصائيات التمويل
            total_fundings=stats.get('total_fundings', 0),
            completed_fundings=stats.get('completed_fundings', 0),
            pending_fundings=stats.get('pending_fundings', 0),
            cancelled_fundings=stats.get('cancelled_fundings', 0),
            total_members=stats.get('total_members', 0),
            total_points_spent=stats.get('total_points_spent', 0),
            avg_members_per_funding=stats.get('avg_members_per_funding', 0),
            avg_points_per_funding=stats.get('avg_points_per_funding', 0),
            
            # إحصائيات النقاط
            total_points=stats.get('total_points', 0),
            total_points_given=stats.get('total_points_given', 0),
            total_points_spent=stats.get('total_points_spent', 0),
            avg_points_per_user=stats.get('avg_points_per_user', 0),
            invite_points=stats.get('invite_points', 0),
            
            # إحصائيات الملفات
            total_files=stats.get('total_files', 0),
            total_numbers=stats.get('total_numbers', 0),
            valid_numbers=stats.get('valid_numbers', 0),
            invalid_numbers=stats.get('invalid_numbers', 0),
            avg_numbers_per_file=stats.get('avg_numbers_per_file', 0),
            
            # إحصائيات الوقت
            uptime=self.format_time(uptime.total_seconds()),
            start_date=self.start_time.strftime("%Y-%m-%d %H:%M:%S"),
            avg_funding_time=self.format_time(stats.get('avg_funding_time', 0))
        )
        
        markup = ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(
            KeyboardButton(BTN_ADMIN_BACK),
            KeyboardButton(BTN_MAIN_HOME)
        )
        
        self.bot.send_message(chat_id, text, reply_markup=markup)
    
    def show_admin_users(self, chat_id):
        """عرض قائمة المستخدمين"""
        # هذا مجرد مثال - يمكن إضافة ترقيم وتفاصيل أكثر
        text = "👥 قائمة المستخدمين (آخر 10):\n\n"
        
        if self.db.db_type == "sqlite":
            self.db.cursor.execute('''
                SELECT user_id, username, points, is_banned, last_active 
                FROM users 
                ORDER BY last_active DESC 
                LIMIT 10
            ''')
            users = self.db.cursor.fetchall()
            
            for user in users:
                status = "🚫" if user['is_banned'] else "✅"
                text += f"{status} `{user['user_id']}` - @{user['username'] or 'لا يوجد'}\n"
                text += f"   💰 {user['points']} نقطة - آخر نشاط: {user['last_active'][:16]}\n\n"
        
        markup = ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(
            KeyboardButton(BTN_ADMIN_BACK),
            KeyboardButton(BTN_MAIN_HOME)
        )
        
        self.bot.send_message(chat_id, text, reply_markup=markup)
    
    def request_user_id_for_points(self, chat_id, points_type):
        """طلب ايدي المستخدم للشحن/الخصم"""
        self.user_states[chat_id] = {
            'action': f'waiting_user_id_for_points',
            'points_type': points_type,
            'timestamp': time.time()
        }
        self.bot.send_message(chat_id, f"🔍 أرسل ايدي المستخدم لـ {points_type} الرصيد:")
    
    def request_user_id_for_ban(self, chat_id):
        """طلب ايدي المستخدم للحظر"""
        self.user_states[chat_id] = {
            'action': 'waiting_user_id_for_ban',
            'timestamp': time.time()
        }
        self.bot.send_message(chat_id, "🔍 أرسل ايدي المستخدم للحظر:")
    
    def request_user_id_for_unban(self, chat_id):
        """طلب ايدي المستخدم لرفع الحظر"""
        self.user_states[chat_id] = {
            'action': 'waiting_user_id_for_unban',
            'timestamp': time.time()
        }
        self.bot.send_message(chat_id, "🔍 أرسل ايدي المستخدم لرفع الحظر:")
    
    def request_support_username(self, chat_id):
        """طلب يوزر الدعم الفني"""
        self.user_states[chat_id] = {
            'action': 'waiting_support_username',
            'timestamp': time.time()
        }
        self.bot.send_message(chat_id, "📞 أرسل يوزر الدعم الفني (بدون @):")
    
    def request_channel_link(self, chat_id):
        """طلب رابط قناة البوت"""
        self.user_states[chat_id] = {
            'action': 'waiting_channel_link',
            'timestamp': time.time()
        }
        self.bot.send_message(chat_id, "📢 أرسل رابط قناة البوت:")
    
    def request_file_upload(self, chat_id):
        """طلب رفع ملف أرقام"""
        self.bot.send_message(chat_id, 
            "📁 أرسل ملف الأرقام بصيغة .txt\n"
            "كل رقم في سطر منفصل\n"
            "مثال:\n"
            "9647876491858\n"
            "966501234567\n"
            "971501234567"
        )
    
    @self.bot.message_handler(content_types=['document'])
    def handle_document(self, message):
        """معالجة الملفات المرفوعة"""
        user_id = message.from_user.id
        
        if user_id not in ADMIN_IDS:
            return
        
        try:
            file_info = self.bot.get_file(message.document.file_id)
            file_name = message.document.file_name
            
            # التحقق من صيغة الملف
            if not any(file_name.endswith(ext) for ext in ALLOWED_FILE_EXTENSIONS):
                self.bot.reply_to(message, "❌ صيغة الملف غير مدعومة. الرجاء رفع ملف .txt فقط")
                return
            
            # تحميل الملف
            downloaded_file = self.bot.download_file(file_info.file_path)
            
            # قراءة الأرقام
            content = downloaded_file.decode('utf-8')
            lines = content.strip().split('\n')
            
            # استخراج الأرقام الصالحة
            numbers = []
            for line in lines:
                line = line.strip()
                if line and line.replace('+', '').replace('-', '').isdigit():
                    # تنظيف الرقم
                    number = re.sub(r'[^\d+]', '', line)
                    numbers.append(number)
            
            if not numbers:
                self.bot.reply_to(message, "❌ لم يتم العثور على أرقام صالحة في الملف")
                return
            
            # حفظ الأرقام في قاعدة البيانات
            result = self.db.add_numbers_from_file(numbers, file_name, user_id)
            
            if result:
                text = ADMIN_FILE_UPLOAD_TEXT.format(
                    filename=file_name,
                    file_size=self.format_size(message.document.file_size),
                    numbers_count=result['total_numbers'],
                    valid_numbers=result['valid_numbers'],
                    duplicate_numbers=result['duplicate_numbers'],
                    date=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                )
                self.bot.reply_to(message, text)
            else:
                self.bot.reply_to(message, "❌ فشل حفظ الأرقام في قاعدة البيانات")
                
        except Exception as e:
            self.bot.reply_to(message, f"❌ خطأ في معالجة الملف: {e}")
    
    def show_files_menu(self, chat_id):
        """عرض قائمة الملفات"""
        markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add(
            KeyboardButton(BTN_ADMIN_ADD_FILE),
            KeyboardButton(BTN_ADMIN_DELETE_FILE),
            KeyboardButton(BTN_ADMIN_VIEW_FILES),
            KeyboardButton(BTN_ADMIN_BACK)
        )
        
        self.bot.send_message(chat_id, "📁 قائمة الملفات:", reply_markup=markup)
    
    def show_all_files(self, chat_id):
        """عرض جميع الملفات"""
        if self.db.db_type == "sqlite":
            self.db.cursor.execute('''
                SELECT file_name, numbers_count, valid_numbers, duplicate_numbers, added_date 
                FROM files 
                WHERE status = 'active' 
                ORDER BY added_date DESC
            ''')
            files = self.db.cursor.fetchall()
            
            if not files:
                self.bot.send_message(chat_id, "📁 لا توجد ملفات مرفوعة")
                return
            
            text = "📁 قائمة الملفات:\n\n"
            for f in files:
                text += f"📄 {f['file_name']}\n"
                text += f"   👥 {f['numbers_count']} رقم (صالح: {f['valid_numbers']}, مكرر: {f['duplicate_numbers']})\n"
                text += f"   📅 {f['added_date'][:16]}\n\n"
            
            self.bot.send_message(chat_id, text)
    
    def show_files_for_deletion(self, chat_id):
        """عرض الملفات للحذف"""
        if self.db.db_type == "sqlite":
            self.db.cursor.execute('''
                SELECT file_id, file_name FROM files WHERE status = 'active'
            ''')
            files = self.db.cursor.fetchall()
            
            if not files:
                self.bot.send_message(chat_id, "📁 لا توجد ملفات للحذف")
                return
            
            markup = InlineKeyboardMarkup(row_width=1)
            for f in files:
                markup.add(InlineKeyboardButton(
                    f"❌ {f['file_name']}",
                    callback_data=f"delete_file_{f['file_id']}"
                ))
            
            self.bot.send_message(chat_id, "اختر ملفاً للحذف:", reply_markup=markup)
    
    def show_settings_menu(self, chat_id):
        """عرض قائمة الإعدادات"""
        invite_reward = self.db.get_setting('invite_reward', DEFAULT_POINTS_PER_INVITE)
        member_price = self.db.get_setting('member_price', DEFAULT_PRICE_PER_MEMBER)
        max_members = self.db.get_setting('max_members', MAX_MEMBERS_PER_FUNDING)
        min_members = self.db.get_setting('min_members', MIN_MEMBERS_PER_FUNDING)
        funding_timeout = self.db.get_setting('funding_timeout', FUNDING_TIMEOUT)
        funding_delay = self.db.get_setting('funding_delay', FUNDING_DELAY)
        max_file_size = self.db.get_setting('max_file_size', MAX_FILE_SIZE)
        force_join_enabled = self.db.get_setting('force_join_enabled', False)
        force_join_channels = self.db.get_force_join_channels_count()
        
        text = ADMIN_SETTINGS_TEXT.format(
            invite_reward=invite_reward,
            member_price=member_price,
            max_members=max_members,
            min_members=min_members,
            funding_timeout=funding_timeout,
            funding_delay=funding_delay,
            allowed_formats=', '.join(ALLOWED_FILE_EXTENSIONS),
            max_file_size=self.format_size(max_file_size),
            support_username=self.db.get_setting('support_username', 'غير محدد'),
            channel_link=self.db.get_setting('channel_link', 'غير محدد'),
            force_join='مفعل' if force_join_enabled else 'غير مفعل',
            force_join_enabled=force_join_enabled,
            force_join_channels_count=force_join_channels
        )
        
        markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add(
            KeyboardButton(BTN_ADMIN_INVITE_REWARD),
            KeyboardButton(BTN_ADMIN_MEMBER_PRICE),
            KeyboardButton(BTN_ADMIN_FORCE_JOIN),
            KeyboardButton(BTN_ADMIN_BACK)
        )
        
        self.bot.send_message(chat_id, text, reply_markup=markup)
    
    def request_invite_reward(self, chat_id):
        """طلب تحديث مكافأة الدعوة"""
        self.user_states[chat_id] = {
            'action': 'waiting_invite_reward',
            'timestamp': time.time()
        }
        self.bot.send_message(chat_id, "🎁 أرسل قيمة مكافأة الدعوة الجديدة:")
    
    def request_member_price(self, chat_id):
        """طلب تحديث سعر العضو"""
        self.user_states[chat_id] = {
            'action': 'waiting_member_price',
            'timestamp': time.time()
        }
        self.bot.send_message(chat_id, "💵 أرسل سعر العضو الجديد (بالنقاط):")
    
    def show_force_join_menu(self, chat_id):
        """عرض قائمة الاشتراك الإجباري"""
        enabled = self.db.get_setting('force_join_enabled', False)
        status = "مفعل" if enabled else "غير مفعل"
        
        text = f"🔒 الاشتراك الإجباري: {status}\n\n"
        text += "اختر من الأزرار أدناه:"
        
        markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add(
            KeyboardButton("✅ تفعيل" if not enabled else "❌ تعطيل"),
            KeyboardButton(BTN_ADMIN_ADD_CHANNEL),
            KeyboardButton(BTN_ADMIN_REMOVE_CHANNEL),
            KeyboardButton(BTN_ADMIN_VIEW_CHANNELS),
            KeyboardButton(BTN_ADMIN_BACK)
        )
        
        self.bot.send_message(chat_id, text, reply_markup=markup)
    
    def request_force_join_channel(self, chat_id):
        """طلب إضافة قناة للاشتراك الإجباري"""
        self.user_states[chat_id] = {
            'action': 'waiting_force_join_channel',
            'timestamp': time.time()
        }
        self.bot.send_message(chat_id, 
            "🔗 أرسل رابط القناة (مثال: https://t.me/username أو @username)\n"
            "يجب أن يكون البوت مشرفاً في القناة"
        )
    
    def add_force_join_channel(self, admin_id, channel_link):
        """إضافة قناة للاشتراك الإجباري"""
        try:
            # استخراج اسم المستخدم
            username = channel_link.split('/')[-1].replace('@', '')
            
            # التحقق من القناة
            chat = self.bot.get_chat(f"@{username}")
            
            # التحقق من صلاحيات البوت
            bot_member = self.bot.get_chat_member(chat.id, self.bot.get_me().id)
            if bot_member.status not in ['administrator', 'creator']:
                self.bot.send_message(admin_id, "❌ البوت ليس مشرفاً في هذه القناة")
                return
            
            # إضافة القناة
            if self.db.add_force_join_channel(chat.id, channel_link, username, chat.title, admin_id):
                self.bot.send_message(admin_id, f"✅ تم إضافة القناة {chat.title} بنجاح")
            else:
                self.bot.send_message(admin_id, "❌ فشل إضافة القناة")
                
        except Exception as e:
            self.bot.send_message(admin_id, f"❌ خطأ: {e}")
    
    def show_force_join_channels(self, chat_id, view_only=False):
        """عرض قنوات الاشتراك الإجباري"""
        channels = self.db.get_force_join_channels()
        
        if not channels:
            self.bot.send_message(chat_id, "🔒 لا توجد قنوات اشتراك إجباري")
            return
        
        text = "🔒 قنوات الاشتراك الإجباري:\n\n"
        
        for channel in channels:
            text += f"📢 {channel['channel_title']}\n"
            text += f"🔗 {channel['channel_link']}\n"
            text += f"🆔 {channel['channel_id']}\n\n"
        
        if not view_only:
            # إضافة أزرار للحذف
            markup = InlineKeyboardMarkup(row_width=1)
            for channel in channels:
                markup.add(InlineKeyboardButton(
                    f"❌ {channel['channel_title']}",
                    callback_data=f"remove_channel_{channel['channel_id']}"
                ))
            self.bot.send_message(chat_id, text, reply_markup=markup)
        else:
            self.bot.send_message(chat_id, text)
    
    def request_broadcast_message(self, chat_id):
        """طلب رسالة للإرسال الجماعي"""
        self.user_states[chat_id] = {
            'action': 'waiting_broadcast_message',
            'timestamp': time.time()
        }
        self.bot.send_message(chat_id, 
            "📢 أرسل الرسالة التي تريد إرسالها لجميع المستخدمين\n"
            "يمكنك استخدام HTML للتنسيق"
        )
    
    def send_broadcast(self, admin_id, message):
        """إرسال رسالة جماعية"""
        # الحصول على جميع المستخدمين
        if self.db.db_type == "sqlite":
            self.db.cursor.execute('SELECT user_id FROM users WHERE is_banned = 0')
            users = self.db.cursor.fetchall()
        else:
            users = self.db.mongo_db.users.find({'is_banned': False}, {'user_id': 1})
        
        sent = 0
        failed = 0
        
        self.bot.send_message(admin_id, f"📢 جاري إرسال الرسالة إلى {len(users)} مستخدم...")
        
        for user in users:
            try:
                self.bot.send_message(user['user_id'], message, parse_mode='HTML')
                sent += 1
                time.sleep(0.05)  # تجنب قيود التليجرام
            except:
                failed += 1
        
        self.bot.send_message(admin_id, 
            f"✅ تم الإرسال:\n"
            f"✓ نجح: {sent}\n"
            f"✗ فشل: {failed}"
        )
    
    def send_logs(self, chat_id):
        """إرسال سجلات البوت"""
        try:
            if os.path.exists(LOG_FILE):
                with open(LOG_FILE, 'rb') as f:
                    self.bot.send_document(chat_id, f, caption="📋 سجلات البوت")
            else:
                self.bot.send_message(chat_id, "📋 لا توجد سجلات")
        except Exception as e:
            self.bot.send_message(chat_id, f"❌ خطأ في إرسال السجلات: {e}")
    
    def show_backups(self, chat_id):
        """عرض النسخ الاحتياطية"""
        if self.db.db_type == "sqlite":
            self.db.cursor.execute('''
                SELECT backup_id, backup_name, backup_size, created_date 
                FROM backups 
                ORDER BY created_date DESC 
                LIMIT 10
            ''')
            backups = self.db.cursor.fetchall()
            
            if not backups:
                self.bot.send_message(chat_id, "💾 لا توجد نسخ احتياطية")
                return
            
            text = "💾 النسخ الاحتياطية المتاحة:\n\n"
            markup = InlineKeyboardMarkup(row_width=1)
            
            for b in backups:
                text += f"📁 {b['backup_name']}\n"
                text += f"   📦 {self.format_size(b['backup_size'])}\n"
                text += f"   📅 {b['created_date'][:16]}\n\n"
                
                markup.add(InlineKeyboardButton(
                    f"🔄 استعادة {b['backup_name']}",
                    callback_data=f"restore_{b['backup_id']}"
                ))
            
            self.bot.send_message(chat_id, text, reply_markup=markup)
    
    def format_size(self, size):
        """تنسيق حجم الملف"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"
    
    # ==================== معالج الأزرار المضمنة ====================
    @self.bot.callback_query_handler(func=lambda call: True)
    def handle_callback(self, call):
        """معالجة الأزرار المضمنة"""
        user_id = call.from_user.id
        data = call.data
        
        try:
            if data.startswith('approve_'):
                # قبول التمويل
                funding_id = data.replace('approve_', '')
                self.bot.answer_callback_query(call.id, "✅ تم قبول التمويل")
                self.bot.edit_message_text(
                    f"✅ تم قبول التمويل {funding_id}",
                    call.message.chat.id,
                    call.message.message_id
                )
            
            elif data.startswith('reject_'):
                # رفض التمويل
                funding_id = data.replace('reject_', '')
                self.bot.answer_callback_query(call.id, "❌ تم رفض التمويل")
                self.bot.edit_message_text(
                    f"❌ تم رفض التمويل {funding_id}",
                    call.message.chat.id,
                    call.message.message_id
                )
            
            elif data.startswith('cancel_'):
                # إلغاء التمويل
                funding_id = data.replace('cancel_', '')
                if funding_id in self.active_fundings:
                    self.cancel_funding(funding_id, user_id, 'إلغاء من الإدارة')
                self.bot.answer_callback_query(call.id, "🛑 تم إلغاء التمويل")
            
            elif data.startswith('ban_'):
                # حظر المستخدم
                target_user = int(data.replace('ban_', ''))
                self.db.ban_user(target_user)
                self.bot.answer_callback_query(call.id, f"🚫 تم حظر المستخدم {target_user}")
                self.notify_user(target_user, "🚫 تم حظرك من استخدام البوت")
            
            elif data.startswith('delete_file_'):
                # حذف ملف
                file_id = data.replace('delete_file_', '')
                if self.db.delete_file(file_id):
                    self.bot.answer_callback_query(call.id, "✅ تم حذف الملف")
                    self.bot.edit_message_text(
                        "✅ تم حذف الملف بنجاح",
                        call.message.chat.id,
                        call.message.message_id
                    )
                else:
                    self.bot.answer_callback_query(call.id, "❌ فشل حذف الملف")
            
            elif data.startswith('remove_channel_'):
                # حذف قناة اشتراك إجباري
                channel_id = data.replace('remove_channel_', '')
                if self.db.remove_force_join_channel(channel_id):
                    self.bot.answer_callback_query(call.id, "✅ تم حذف القناة")
                    self.bot.edit_message_text(
                        "✅ تم حذف القناة بنجاح",
                        call.message.chat.id,
                        call.message.message_id
                    )
                else:
                    self.bot.answer_callback_query(call.id, "❌ فشل حذف القناة")
            
            elif data.startswith('restore_'):
                # استعادة نسخة احتياطية
                backup_id = data.replace('restore_', '')
                self.bot.answer_callback_query(call.id, "🔄 جاري استعادة النسخة...")
                self.bot.send_message(call.message.chat.id, "⚠️ ميزة الاستعادة غير مفعلة حالياً")
            
        except Exception as e:
            logging.error(f"❌ خطأ في معالجة callback: {e}")
            self.bot.answer_callback_query(call.id, "❌ حدث خطأ")
    
    # ==================== تشغيل البوت ====================
    def run(self):
        """تشغيل البوت"""
        try:
            # الحصول على معلومات البوت
            bot_info = self.bot.get_me()
            global BOT_USERNAME
            BOT_USERNAME = bot_info.username
            
            logging.info(f"✅ تم تشغيل البوت: {bot_info.first_name} (@{bot_info.username})")
            logging.info(f"👤 معرف المطورين: {ADMIN_IDS}")
            
            # بدء البوت
            self.bot.infinity_polling(timeout=60, long_polling_timeout=60)
            
        except Exception as e:
            logging.error(f"❌ خطأ في تشغيل البوت: {e}")
            time.sleep(5)
            self.run()  # إعادة المحاولة
    
    def stop(self):
        """إيقاف البوت"""
        self.running = False
        self.db.close()
        self.executor.shutdown()
        logging.info("🛑 تم إيقاف البوت")

# ==================== إضافة دوال إضافية لقاعدة البيانات ====================
# إضافة دوال الاشتراك الإجباري
def get_force_join_channels(self):
    """الحصول على قنوات الاشتراك الإجباري"""
    try:
        if self.db_type == "sqlite":
            self.cursor.execute('''
                SELECT * FROM force_join_channels 
                WHERE status = 'active' 
                ORDER BY position ASC
            ''')
            return [dict(row) for row in self.cursor.fetchall()]
        elif self.db_type == "mongodb":
            cursor = self.mongo_db.force_join_channels.find(
                {'status': 'active'}
            ).sort('position', 1)
            return list(cursor)
    except Exception as e:
        logging.error(f"❌ فشل الحصول على قنوات الاشتراك الإجباري: {e}")
    return []

def get_force_join_channels_count(self):
    """الحصول على عدد قنوات الاشتراك الإجباري"""
    try:
        if self.db_type == "sqlite":
            self.cursor.execute('SELECT COUNT(*) as count FROM force_join_channels WHERE status = "active"')
            return self.cursor.fetchone()['count']
        elif self.db_type == "mongodb":
            return self.mongo_db.force_join_channels.count_documents({'status': 'active'})
    except:
        pass
    return 0

def add_force_join_channel(self, channel_id, channel_link, channel_username, channel_title, added_by):
    """إضافة قناة للاشتراك الإجباري"""
    try:
        now = datetime.datetime.now().isoformat()
        
        # الحصول على أعلى ترتيب
        if self.db_type == "sqlite":
            self.cursor.execute('SELECT MAX(position) as max_pos FROM force_join_channels')
            result = self.cursor.fetchone()
            position = (result['max_pos'] or -1) + 1
            
            self.cursor.execute('''
                INSERT OR REPLACE INTO force_join_channels 
                (channel_id, channel_link, channel_username, channel_title, added_by, added_date, status, position)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (channel_id, channel_link, channel_username, channel_title, added_by, now, 'active', position))
            self.connection.commit()
            return True
            
        elif self.db_type == "mongodb":
            position = self.mongo_db.force_join_channels.count_documents({})
            self.mongo_db.force_join_channels.update_one(
                {'channel_id': channel_id},
                {
                    '$set': {
                        'channel_id': channel_id,
                        'channel_link': channel_link,
                        'channel_username': channel_username,
                        'channel_title': channel_title,
                        'added_by': added_by,
                        'added_date': now,
                        'status': 'active',
                        'position': position
                    }
                },
                upsert=True
            )
            return True
    except Exception as e:
        logging.error(f"❌ فشل إضافة قناة اشتراك إجباري: {e}")
    return False

def remove_force_join_channel(self, channel_id):
    """حذف قناة من الاشتراك الإجباري"""
    try:
        if self.db_type == "sqlite":
            self.cursor.execute('DELETE FROM force_join_channels WHERE channel_id = ?', (channel_id,))
            self.connection.commit()
            return self.cursor.rowcount > 0
        elif self.db_type == "mongodb":
            result = self.mongo_db.force_join_channels.delete_one({'channel_id': channel_id})
            return result.deleted_count > 0
    except Exception as e:
        logging.error(f"❌ فشل حذف قناة اشتراك إجباري: {e}")
    return False

def ban_user(self, user_id):
    """حظر مستخدم"""
    try:
        if self.db_type == "sqlite":
            self.cursor.execute('UPDATE users SET is_banned = 1 WHERE user_id = ?', (user_id,))
            self.connection.commit()
            return True
        elif self.db_type == "mongodb":
            self.mongo_db.users.update_one({'user_id': user_id}, {'$set': {'is_banned': True}})
            return True
    except Exception as e:
        logging.error(f"❌ فشل حظر المستخدم {user_id}: {e}")
    return False

def unban_user(self, user_id):
    """رفع الحظر عن مستخدم"""
    try:
        if self.db_type == "sqlite":
            self.cursor.execute('UPDATE users SET is_banned = 0 WHERE user_id = ?', (user_id,))
            self.connection.commit()
            return True
        elif self.db_type == "mongodb":
            self.mongo_db.users.update_one({'user_id': user_id}, {'$set': {'is_banned': False}})
            return True
    except Exception as e:
        logging.error(f"❌ فشل رفع الحظر عن المستخدم {user_id}: {e}")
    return False

def delete_file(self, file_id):
    """حذف ملف"""
    try:
        if self.db_type == "sqlite":
            # حذف الأرقام المرتبطة بالملف
            self.cursor.execute('DELETE FROM numbers WHERE file_name IN (SELECT file_name FROM files WHERE file_id = ?)', (file_id,))
            # حذف الملف
            self.cursor.execute('DELETE FROM files WHERE file_id = ?', (file_id,))
            self.connection.commit()
            return True
        elif self.db_type == "mongodb":
            file = self.mongo_db.files.find_one({'file_id': file_id})
            if file:
                self.mongo_db.numbers.delete_many({'file_name': file['file_name']})
                self.mongo_db.files.delete_one({'file_id': file_id})
            return True
    except Exception as e:
        logging.error(f"❌ فشل حذف الملف {file_id}: {e}")
    return False

# إضافة الدوال إلى كلاس DatabaseManager
DatabaseManager.get_force_join_channels = get_force_join_channels
DatabaseManager.get_force_join_channels_count = get_force_join_channels_count
DatabaseManager.add_force_join_channel = add_force_join_channel
DatabaseManager.remove_force_join_channel = remove_force_join_channel
DatabaseManager.ban_user = ban_user
DatabaseManager.unban_user = unban_user
DatabaseManager.delete_file = delete_file

# ==================== نقطة الدخول الرئيسية ====================
if __name__ == "__main__":
    print("=" * 60)
    print("بوت التمويل - تليجرام")
    print("الإصدار:", BOT_VERSION)
    print("المطور:", BOT_AUTHOR)
    print("=" * 60)
    
    # إنشاء المجلدات اللازمة
    os.makedirs("backups", exist_ok=True)
    os.makedirs("logs", exist_ok=True)
    os.makedirs("data", exist_ok=True)
    os.makedirs(NUMBERS_FILE_PATH, exist_ok=True)
    
    # بدء البوت
    bot = FundingBot(BOT_TOKEN)
    
    try:
        # تسجيل إشارة الإيقاف
        def signal_handler(signum, frame):
            print("\n🛑 جاري إيقاف البوت...")
            bot.stop()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # تشغيل البوت
        bot.run()
        
    except KeyboardInterrupt:
        print("\n🛑 تم إيقاف البوت بواسطة المستخدم")
        bot.stop()
    except Exception as e:
        print(f"❌ خطأ غير متوقع: {e}")
        logging.critical(f"❌ خطأ غير متوقع: {e}", exc_info=True)
        bot.stop()
