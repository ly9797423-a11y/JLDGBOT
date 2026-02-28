#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
🤖 بوت تمويل متكامل لتليجرام
الإصدار: 2.0.0
المطور: مطور البوت
التاريخ: 2024
"""

import logging
import asyncio
import json
import os
import sys
import re
import time
import random
import string
import hashlib
import base64
import sqlite3
import threading
import queue
import signal
import uuid
import shutil
import tempfile
import zipfile
import csv
import io
import math
import functools
import inspect
import traceback
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Tuple, Union, Any, Callable
from collections import defaultdict, deque, Counter
from dataclasses import dataclass, field, asdict
from enum import Enum, auto
from pathlib import Path
from contextlib import contextmanager, suppress
from functools import wraps
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import warnings
warnings.filterwarnings('ignore')

# مكتبات خارجية
try:
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ParseMode, ChatMember, Chat, User, Message, Bot, CallbackQuery
    from telegram.ext import (
        Application, CommandHandler, CallbackQueryHandler, MessageHandler, 
        filters, ContextTypes, ConversationHandler, JobQueue, PicklePersistence
    )
    from telegram.constants import ChatMemberStatus, ChatType
    from telegram.error import TelegramError, BadRequest, Forbidden, TimedOut, NetworkError, RetryAfter
    import aiofiles
    import aiohttp
    from dotenv import load_dotenv
    import redis.asyncio as redis
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
    import requests
    from telethon import TelegramClient, events, sync
    from telethon.tl.functions.messages import AddChatUserRequest, InviteToChannelRequest
    from telethon.tl.types import InputPeerUser, InputPeerChannel, InputPeerChat
    import socks
    import colorama
    from colorama import Fore, Style, init
    import psutil
    import yaml
    import schedule
except ImportError as e:
    print(f"❌ خطأ في استيراد المكتبات: {e}")
    print("📦 يرجى تثبيت المكتبات المطلوبة: pip install -r requirements.txt")
    sys.exit(1)

# تهيئة colorama
init(autoreset=True)

# ==================== إعدادات البوت الأساسية ====================

# توكن البوت
BOT_TOKEN = "8699966374:AAGCCGehxTQzGbEkBxIe7L3vecLPcvzGrHg"

# معرفي المديرين
ADMIN_IDS = [6615860762, 6130994941]

# إعدادات التسجيل المتقدمة
LOG_LEVEL = logging.INFO
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# إنشاء مجلد للسجلات إذا لم يكن موجوداً
os.makedirs("logs", exist_ok=True)

# إعداد التسجيل في ملف وفي الكونسول
logging.basicConfig(
    level=LOG_LEVEL,
    format=LOG_FORMAT,
    datefmt=LOG_DATE_FORMAT,
    handlers=[
        logging.FileHandler(f"logs/bot_{datetime.now().strftime('%Y%m%d')}.log", encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# ==================== الثوابت والمتغيرات العامة ====================

# إصدار البوت
BOT_VERSION = "2.0.0"
BOT_NAME = "تمويل برو"
BOT_DESCRIPTION = "بوت تمويل متكامل للقنوات والمجموعات"

# مسارات الملفات
DATA_DIR = "data"
USERS_DB_PATH = os.path.join(DATA_DIR, "users.json")
SETTINGS_PATH = os.path.join(DATA_DIR, "settings.json")
FUNDING_DB_PATH = os.path.join(DATA_DIR, "funding.json")
INVITES_DB_PATH = os.path.join(DATA_DIR, "invites.json")
NUMBERS_FILES_DB_PATH = os.path.join(DATA_DIR, "numbers_files.json")
BANNED_USERS_PATH = os.path.join(DATA_DIR, "banned.json")
FORCE_SUB_PATH = os.path.join(DATA_DIR, "force_sub.json")
LOGS_DIR = "logs"
TEMP_DIR = "temp"
BACKUP_DIR = "backups"

# إنشاء المجلدات المطلوبة
for directory in [DATA_DIR, LOGS_DIR, TEMP_DIR, BACKUP_DIR]:
    os.makedirs(directory, exist_ok=True)

# ==================== فئات التعداد (Enums) ====================

class UserStatus(Enum):
    """حالة المستخدم"""
    ACTIVE = "active"
    BANNED = "banned"
    LIMITED = "limited"
    VIP = "vip"

class FundingStatus(Enum):
    """حالة طلب التمويل"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"

class MemberSource(Enum):
    """مصدر الأعضاء"""
    NUMBERS_FILE = "numbers_file"
    BOT_USERS = "bot_users"
    MIXED = "mixed"

class UserRole(Enum):
    """صلاحية المستخدم"""
    USER = "user"
    VIP_USER = "vip"
    MODERATOR = "moderator"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"

class LogLevel(Enum):
    """مستوى السجل"""
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    DEBUG = "DEBUG"
    CRITICAL = "CRITICAL"

class NotificationType(Enum):
    """نوع الإشعار"""
    FUNDING_START = "funding_start"
    FUNDING_PROGRESS = "funding_progress"
    FUNDING_COMPLETE = "funding_complete"
    FUNDING_FAILED = "funding_failed"
    POINTS_ADDED = "points_added"
    POINTS_DEDUCTED = "points_deducted"
    INVITE_REWARD = "invite_reward"
    WELCOME = "welcome"
    ADMIN_ALERT = "admin_alert"

# ==================== فئات البيانات (Data Classes) ====================

@dataclass
class User:
    """بيانات المستخدم"""
    user_id: int
    username: str = None
    first_name: str = None
    last_name: str = None
    points: int = 0
    invited_by: int = None
    invites_count: int = 0
    total_invites: int = 0
    total_fundings: int = 0
    total_members_funded: int = 0
    total_points_earned: int = 0
    total_points_spent: int = 0
    role: str = UserRole.USER.value
    status: str = UserStatus.ACTIVE.value
    joined_date: str = None
    last_active: str = None
    language: str = "ar"
    phone_number: str = None
    is_bot: bool = False
    is_premium: bool = False
    daily_points: int = 0
    weekly_points: int = 0
    monthly_points: int = 0
    achievements: List[str] = field(default_factory=list)
    badges: List[str] = field(default_factory=list)
    notes: str = None
    warning_count: int = 0
    last_warning_date: str = None
    muted_until: str = None

    def to_dict(self):
        """تحويل إلى قاموس"""
        return {
            'user_id': self.user_id,
            'username': self.username,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'points': self.points,
            'invited_by': self.invited_by,
            'invites_count': self.invites_count,
            'total_invites': self.total_invites,
            'total_fundings': self.total_fundings,
            'total_members_funded': self.total_members_funded,
            'total_points_earned': self.total_points_earned,
            'total_points_spent': self.total_points_spent,
            'role': self.role,
            'status': self.status,
            'joined_date': self.joined_date,
            'last_active': self.last_active,
            'language': self.language,
            'phone_number': self.phone_number,
            'is_bot': self.is_bot,
            'is_premium': self.is_premium,
            'daily_points': self.daily_points,
            'weekly_points': self.weekly_points,
            'monthly_points': self.monthly_points,
            'achievements': self.achievements,
            'badges': self.badges,
            'notes': self.notes,
            'warning_count': self.warning_count,
            'last_warning_date': self.last_warning_date,
            'muted_until': self.muted_until
        }

    @classmethod
    def from_dict(cls, data):
        """إنشاء من قاموس"""
        return cls(**data)

@dataclass
class FundingRequest:
    """طلب تمويل"""
    request_id: str
    user_id: int
    chat_id: int
    chat_title: str
    chat_link: str
    chat_type: str
    members_count: int
    cost: int
    status: str
    source: str
    added_members: int = 0
    failed_members: int = 0
    used_numbers: List[str] = field(default_factory=list)
    created_at: str = None
    started_at: str = None
    completed_at: str = None
    last_update: str = None
    priority: int = 0
    notes: str = None
    admin_notes: str = None
    approved_by: int = None
    approved_at: str = None
    cancelled_by: int = None
    cancelled_at: str = None
    cancelled_reason: str = None

    def to_dict(self):
        """تحويل إلى قاموس"""
        return {
            'request_id': self.request_id,
            'user_id': self.user_id,
            'chat_id': self.chat_id,
            'chat_title': self.chat_title,
            'chat_link': self.chat_link,
            'chat_type': self.chat_type,
            'members_count': self.members_count,
            'cost': self.cost,
            'status': self.status,
            'source': self.source,
            'added_members': self.added_members,
            'failed_members': self.failed_members,
            'used_numbers': self.used_numbers,
            'created_at': self.created_at,
            'started_at': self.started_at,
            'completed_at': self.completed_at,
            'last_update': self.last_update,
            'priority': self.priority,
            'notes': self.notes,
            'admin_notes': self.admin_notes,
            'approved_by': self.approved_by,
            'approved_at': self.approved_at,
            'cancelled_by': self.cancelled_by,
            'cancelled_at': self.cancelled_at,
            'cancelled_reason': self.cancelled_reason
        }

    @classmethod
    def from_dict(cls, data):
        """إنشاء من قاموس"""
        return cls(**data)

@dataclass
class NumbersFile:
    """ملف الأرقام"""
    file_id: str
    file_name: str
    original_name: str
    added_by: int
    added_at: str
    numbers: List[str] = field(default_factory=list)
    used_numbers: List[str] = field(default_factory=list)
    valid_numbers: int = 0
    invalid_numbers: int = 0
    duplicate_numbers: int = 0
    country_codes: Dict[str, int] = field(default_factory=dict)
    total_count: int = 0
    used_count: int = 0
    last_used: str = None
    is_active: bool = True
    notes: str = None
    hash: str = None

    def to_dict(self):
        """تحويل إلى قاموس"""
        return {
            'file_id': self.file_id,
            'file_name': self.file_name,
            'original_name': self.original_name,
            'added_by': self.added_by,
            'added_at': self.added_at,
            'numbers': self.numbers,
            'used_numbers': self.used_numbers,
            'valid_numbers': self.valid_numbers,
            'invalid_numbers': self.invalid_numbers,
            'duplicate_numbers': self.duplicate_numbers,
            'country_codes': self.country_codes,
            'total_count': self.total_count,
            'used_count': self.used_count,
            'last_used': self.last_used,
            'is_active': self.is_active,
            'notes': self.notes,
            'hash': self.hash
        }

    @classmethod
    def from_dict(cls, data):
        """إنشاء من قاموس"""
        return cls(**data)

@dataclass
class InviteLink:
    """رابط دعوة"""
    user_id: int
    link_code: str
    full_link: str
    created_at: str
    uses_count: int = 0
    unique_uses: int = 0
    last_use: str = None
    is_active: bool = True
    expires_at: str = None
    max_uses: int = None

    def to_dict(self):
        """تحويل إلى قاموس"""
        return {
            'user_id': self.user_id,
            'link_code': self.link_code,
            'full_link': self.full_link,
            'created_at': self.created_at,
            'uses_count': self.uses_count,
            'unique_uses': self.unique_uses,
            'last_use': self.last_use,
            'is_active': self.is_active,
            'expires_at': self.expires_at,
            'max_uses': self.max_uses
        }

    @classmethod
    def from_dict(cls, data):
        """إنشاء من قاموس"""
        return cls(**data)

@dataclass
class SystemStats:
    """إحصائيات النظام"""
    total_users: int = 0
    active_users_today: int = 0
    active_users_week: int = 0
    active_users_month: int = 0
    banned_users: int = 0
    vip_users: int = 0
    
    total_fundings: int = 0
    completed_fundings: int = 0
    pending_fundings: int = 0
    failed_fundings: int = 0
    cancelled_fundings: int = 0
    
    total_members_added: int = 0
    total_members_failed: int = 0
    
    total_points: int = 0
    points_earned_today: int = 0
    points_spent_today: int = 0
    
    total_invites: int = 0
    total_invites_today: int = 0
    
    numbers_files_count: int = 0
    total_numbers: int = 0
    available_numbers: int = 0
    used_numbers: int = 0
    
    bot_uptime: str = None
    last_backup: str = None
    memory_usage: float = 0
    cpu_usage: float = 0
    disk_usage: float = 0
    
    daily_stats: Dict[str, Any] = field(default_factory=dict)
    weekly_stats: Dict[str, Any] = field(default_factory=dict)
    monthly_stats: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self):
        """تحويل إلى قاموس"""
        return asdict(self)

# ==================== مدير قواعد البيانات ====================

class DatabaseManager:
    """مدير قواعد البيانات"""
    
    def __init__(self):
        self.data_dir = DATA_DIR
        self.locks = defaultdict(asyncio.Lock)
        self.cache = {}
        self.cache_ttl = 300  # 5 دقائق
        self.last_cache_cleanup = time.time()
        
        # تحميل البيانات
        self.users = self._load_data('users.json', {})
        self.settings = self._load_data('settings.json', self._default_settings())
        self.funding_requests = self._load_data('funding.json', {})
        self.invite_links = self._load_data('invites.json', {})
        self.numbers_files = self._load_data('numbers_files.json', {})
        self.banned_users = set(self._load_data('banned.json', []))
        self.force_sub_channels = self._load_data('force_sub.json', [])
        self.stats = self._load_data('stats.json', SystemStats().to_dict())
        
        # بدء مهمة تنظيف الكاش
        asyncio.create_task(self._cleanup_cache_loop())
    
    def _default_settings(self):
        """الإعدادات الافتراضية"""
        return {
            'welcome_message': '🎉 مرحباً بك في بوت التمويل!\nيمكنك جمع النقاط وتمويل قنواتك.',
            'points_per_invite': 5,
            'points_per_member': 8,
            'support_username': 'support',
            'channel_link': 'https://t.me/your_channel',
            'min_funding_members': 10,
            'max_funding_members': 1000,
            'daily_invite_limit': 50,
            'daily_funding_limit': 10,
            'require_force_sub': True,
            'enable_notifications': True,
            'auto_backup': True,
            'backup_interval_hours': 24,
            'max_users_per_file': 10000,
            'allowed_country_codes': ['966', '962', '20', '971', '973', '974', '965', '968'],
            'bot_language': 'ar',
            'currency_symbol': '💰',
            'points_name': 'نقطة',
            'maintenance_mode': False,
            'maintenance_message': '⚠️ البوت تحت الصيانة حالياً، يرجى المحاولة لاحقاً.',
            'version': BOT_VERSION,
            'last_update': datetime.now().isoformat()
        }
    
    def _load_data(self, filename: str, default=None):
        """تحميل البيانات من ملف JSON"""
        filepath = os.path.join(self.data_dir, filename)
        try:
            if os.path.exists(filepath):
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    logger.info(f"✅ تم تحميل {filename} بنجاح")
                    return data
            else:
                # إنشاء الملف بالقيمة الافتراضية
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(default, f, ensure_ascii=False, indent=2)
                logger.info(f"📁 تم إنشاء {filename}")
                return default
        except Exception as e:
            logger.error(f"❌ خطأ في تحميل {filename}: {e}")
            return default if default is not None else {}
    
    async def _save_data(self, filename: str, data):
        """حفظ البيانات إلى ملف JSON"""
        filepath = os.path.join(self.data_dir, filename)
        async with self.locks[filename]:
            try:
                # إنشاء نسخة احتياطية
                if os.path.exists(filepath):
                    backup_path = os.path.join(BACKUP_DIR, f"{filename}.{datetime.now().strftime('%Y%m%d_%H%M%S')}.bak")
                    shutil.copy2(filepath, backup_path)
                
                # حفظ البيانات
                async with aiofiles.open(filepath, 'w', encoding='utf-8') as f:
                    await f.write(json.dumps(data, ensure_ascii=False, indent=2))
                
                # تحديث الكاش
                self.cache[filename] = {
                    'data': data,
                    'timestamp': time.time()
                }
                
                logger.debug(f"✅ تم حفظ {filename} بنجاح")
                return True
            except Exception as e:
                logger.error(f"❌ خطأ في حفظ {filename}: {e}")
                return False
    
    async def _cleanup_cache_loop(self):
        """تنظيف الكاش بشكل دوري"""
        while True:
            await asyncio.sleep(60)  # كل دقيقة
            current_time = time.time()
            expired_keys = [
                key for key, value in self.cache.items()
                if current_time - value['timestamp'] > self.cache_ttl
            ]
            for key in expired_keys:
                del self.cache[key]
    
    async def get_user(self, user_id: int, create_if_missing: bool = True) -> Optional[User]:
        """الحصول على بيانات المستخدم"""
        user_id = str(user_id)
        
        # التحقق من الكاش
        cache_key = f"user_{user_id}"
        if cache_key in self.cache:
            cache_data = self.cache[cache_key]
            if time.time() - cache_data['timestamp'] < self.cache_ttl:
                return User.from_dict(cache_data['data'])
        
        # البحث في قاعدة البيانات
        if user_id in self.users:
            user_dict = self.users[user_id]
            user = User.from_dict(user_dict)
            
            # تحديث الكاش
            self.cache[cache_key] = {
                'data': user_dict,
                'timestamp': time.time()
            }
            
            return user
        
        # إنشاء مستخدم جديد إذا كان مطلوباً
        if create_if_missing:
            user = User(
                user_id=int(user_id),
                joined_date=datetime.now().isoformat(),
                last_active=datetime.now().isoformat()
            )
            await self.save_user(user)
            return user
        
        return None
    
    async def save_user(self, user: User) -> bool:
        """حفظ بيانات المستخدم"""
        user_id = str(user.user_id)
        self.users[user_id] = user.to_dict()
        
        # تحديث الكاش
        self.cache[f"user_{user_id}"] = {
            'data': user.to_dict(),
            'timestamp': time.time()
        }
        
        return await self._save_data('users.json', self.users)
    
    async def update_user_points(self, user_id: int, points_change: int, reason: str = None) -> Tuple[bool, int]:
        """تحديث نقاط المستخدم"""
        user = await self.get_user(user_id)
        if not user:
            return False, 0
        
        old_points = user.points
        user.points += points_change
        
        if points_change > 0:
            user.total_points_earned += points_change
        else:
            user.total_points_spent += abs(points_change)
        
        user.last_active = datetime.now().isoformat()
        
        # تسجيل العملية
        logger.info(f"💰 تحديث نقاط المستخدم {user_id}: {old_points} -> {user.points} ({points_change:+}) - {reason}")
        
        await self.save_user(user)
        return True, user.points
    
    async def get_funding_request(self, request_id: str) -> Optional[FundingRequest]:
        """الحصول على طلب تمويل"""
        if request_id in self.funding_requests:
            return FundingRequest.from_dict(self.funding_requests[request_id])
        return None
    
    async def save_funding_request(self, request: FundingRequest) -> bool:
        """حفظ طلب تمويل"""
        self.funding_requests[request.request_id] = request.to_dict()
        return await self._save_data('funding.json', self.funding_requests)
    
    async def update_funding_status(self, request_id: str, status: str, **kwargs):
        """تحديث حالة طلب تمويل"""
        if request_id in self.funding_requests:
            request = self.funding_requests[request_id]
            request['status'] = status
            request['last_update'] = datetime.now().isoformat()
            
            for key, value in kwargs.items():
                if key in request:
                    request[key] = value
            
            await self._save_data('funding.json', self.funding_requests)
    
    async def add_numbers_file(self, file_data: NumbersFile) -> str:
        """إضافة ملف أرقام"""
        file_id = file_data.file_id or str(uuid.uuid4())
        file_data.file_id = file_id
        self.numbers_files[file_id] = file_data.to_dict()
        await self._save_data('numbers_files.json', self.numbers_files)
        return file_id
    
    async def get_available_numbers(self, count: int, exclude_used: bool = True) -> List[str]:
        """الحصول على أرقام متاحة"""
        available = []
        
        for file_id, file_data in self.numbers_files.items():
            if not file_data.get('is_active', True):
                continue
            
            numbers = file_data.get('numbers', [])
            used = set(file_data.get('used_numbers', [])) if exclude_used else set()
            
            for number in numbers:
                if number not in used:
                    available.append(number)
                    if len(available) >= count:
                        break
            
            if len(available) >= count:
                break
        
        return available[:count]
    
    async def mark_numbers_used(self, numbers: List[str], request_id: str = None):
        """تحديد أرقام كمستخدمة"""
        for number in numbers:
            for file_id, file_data in self.numbers_files.items():
                if number in file_data.get('numbers', []):
                    if 'used_numbers' not in file_data:
                        file_data['used_numbers'] = []
                    
                    if number not in file_data['used_numbers']:
                        file_data['used_numbers'].append(number)
                        
                        # تحديث الإحصائيات
                        file_data['used_count'] = len(file_data['used_numbers'])
                        file_data['last_used'] = datetime.now().isoformat()
                        
                        # تسجيل العملية
                        logger.info(f"📞 تم استخدام الرقم {number} من الملف {file_id}")
        
        await self._save_data('numbers_files.json', self.numbers_files)
    
    async def get_invite_link(self, user_id: int) -> Optional[InviteLink]:
        """الحصول على رابط دعوة المستخدم"""
        user_id = str(user_id)
        
        if user_id in self.invite_links:
            return InviteLink.from_dict(self.invite_links[user_id])
        
        # إنشاء رابط جديد
        link_code = f"{user_id}_{uuid.uuid4().hex[:8]}"
        bot_username = "YourBotUsername"  # يجب تغييره
        full_link = f"https://t.me/{bot_username}?start={link_code}"
        
        invite_link = InviteLink(
            user_id=int(user_id),
            link_code=link_code,
            full_link=full_link,
            created_at=datetime.now().isoformat()
        )
        
        self.invite_links[user_id] = invite_link.to_dict()
        await self._save_data('invites.json', self.invite_links)
        
        return invite_link
    
    async def use_invite_link(self, link_code: str, new_user_id: int) -> Optional[int]:
        """استخدام رابط دعوة"""
        for uid, link_data in self.invite_links.items():
            if link_data.get('link_code') == link_code:
                # تحديث الإحصائيات
                link_data['uses_count'] = link_data.get('uses_count', 0) + 1
                
                # التحقق من المستخدمين الفريدين
                if 'used_by' not in link_data:
                    link_data['used_by'] = []
                
                if new_user_id not in link_data['used_by']:
                    link_data['used_by'].append(new_user_id)
                    link_data['unique_uses'] = len(link_data['used_by'])
                
                link_data['last_use'] = datetime.now().isoformat()
                
                await self._save_data('invites.json', self.invite_links)
                return int(uid)
        
        return None
    
    async def ban_user(self, user_id: int, reason: str = None) -> bool:
        """حظر مستخدم"""
        user_id = str(user_id)
        self.banned_users.add(user_id)
        
        # تحديث حالة المستخدم في قاعدة البيانات
        user = await self.get_user(int(user_id), create_if_missing=False)
        if user:
            user.status = UserStatus.BANNED.value
            user.notes = f"محظور: {reason}" if reason else "محظور"
            await self.save_user(user)
        
        await self._save_data('banned.json', list(self.banned_users))
        
        logger.warning(f"🔒 تم حظر المستخدم {user_id} - السبب: {reason}")
        return True
    
    async def unban_user(self, user_id: int) -> bool:
        """رفع حظر مستخدم"""
        user_id = str(user_id)
        if user_id in self.banned_users:
            self.banned_users.remove(user_id)
            
            # تحديث حالة المستخدم
            user = await self.get_user(int(user_id), create_if_missing=False)
            if user:
                user.status = UserStatus.ACTIVE.value
                await self.save_user(user)
            
            await self._save_data('banned.json', list(self.banned_users))
            
            logger.info(f"🔓 تم رفع الحظر عن المستخدم {user_id}")
            return True
        
        return False
    
    async def add_force_channel(self, channel: str) -> bool:
        """إضافة قناة للاشتراك الإجباري"""
        if channel not in self.force_sub_channels:
            self.force_sub_channels.append(channel)
            await self._save_data('force_sub.json', self.force_sub_channels)
            logger.info(f"📢 تم إضافة قناة للاشتراك الإجباري: {channel}")
            return True
        return False
    
    async def remove_force_channel(self, channel: str) -> bool:
        """حذف قناة من الاشتراك الإجباري"""
        if channel in self.force_sub_channels:
            self.force_sub_channels.remove(channel)
            await self._save_data('force_sub.json', self.force_sub_channels)
            logger.info(f"📢 تم حذف قناة من الاشتراك الإجباري: {channel}")
            return True
        return False
    
    async def get_stats(self) -> SystemStats:
        """الحصول على إحصائيات النظام"""
        # تحديث الإحصائيات
        stats = SystemStats()
        
        # إحصائيات المستخدمين
        stats.total_users = len(self.users)
        stats.banned_users = len(self.banned_users)
        
        # حساب المستخدمين النشطين
        now = datetime.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = now - timedelta(days=7)
        month_start = now - timedelta(days=30)
        
        for user_data in self.users.values():
            last_active = user_data.get('last_active')
            if last_active:
                last_active_dt = datetime.fromisoformat(last_active)
                if last_active_dt >= today_start:
                    stats.active_users_today += 1
                if last_active_dt >= week_start:
                    stats.active_users_week += 1
                if last_active_dt >= month_start:
                    stats.active_users_month += 1
            
            if user_data.get('role') == UserRole.VIP_USER.value:
                stats.vip_users += 1
        
        # إحصائيات التمويل
        for request_data in self.funding_requests.values():
            stats.total_fundings += 1
            
            if request_data['status'] == FundingStatus.COMPLETED.value:
                stats.completed_fundings += 1
                stats.total_members_added += request_data.get('added_members', 0)
                stats.total_members_failed += request_data.get('failed_members', 0)
            elif request_data['status'] == FundingStatus.PENDING.value:
                stats.pending_fundings += 1
            elif request_data['status'] == FundingStatus.FAILED.value:
                stats.failed_fundings += 1
            elif request_data['status'] == FundingStatus.CANCELLED.value:
                stats.cancelled_fundings += 1
        
        # إحصائيات النقاط
        stats.total_points = sum(u.get('points', 0) for u in self.users.values())
        
        # إحصائيات الملفات
        stats.numbers_files_count = len(self.numbers_files)
        
        for file_data in self.numbers_files.values():
            stats.total_numbers += file_data.get('total_count', 0)
            stats.used_numbers += file_data.get('used_count', 0)
        
        stats.available_numbers = stats.total_numbers - stats.used_numbers
        
        # إحصائيات النظام
        stats.bot_uptime = self.stats.get('bot_uptime')
        stats.last_backup = self.stats.get('last_backup')
        
        # استخدام الموارد
        stats.memory_usage = psutil.Process().memory_percent()
        stats.cpu_usage = psutil.cpu_percent(interval=1)
        stats.disk_usage = psutil.disk_usage('/').percent
        
        return stats
    
    async def update_stats(self):
        """تحديث إحصائيات النظام"""
        stats = await self.get_stats()
        self.stats = stats.to_dict()
        await self._save_data('stats.json', self.stats)
    
    async def create_backup(self) -> str:
        """إنشاء نسخة احتياطية"""
        backup_id = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = os.path.join(BACKUP_DIR, f"backup_{backup_id}")
        os.makedirs(backup_path, exist_ok=True)
        
        # نسخ جميع ملفات البيانات
        for filename in os.listdir(DATA_DIR):
            src = os.path.join(DATA_DIR, filename)
            dst = os.path.join(backup_path, filename)
            if os.path.isfile(src):
                shutil.copy2(src, dst)
        
        # إنشاء ملف وصف
        info = {
            'backup_id': backup_id,
            'created_at': datetime.now().isoformat(),
            'version': BOT_VERSION,
            'files': os.listdir(backup_path)
        }
        
        with open(os.path.join(backup_path, 'backup_info.json'), 'w', encoding='utf-8') as f:
            json.dump(info, f, ensure_ascii=False, indent=2)
        
        # تحديث آخر نسخة احتياطية
        self.stats['last_backup'] = datetime.now().isoformat()
        await self._save_data('stats.json', self.stats)
        
        logger.info(f"💾 تم إنشاء نسخة احتياطية: {backup_id}")
        return backup_path
    
    async def restore_backup(self, backup_id: str) -> bool:
        """استعادة نسخة احتياطية"""
        backup_path = os.path.join(BACKUP_DIR, f"backup_{backup_id}")
        
        if not os.path.exists(backup_path):
            logger.error(f"❌ النسخة الاحتياطية غير موجودة: {backup_id}")
            return False
        
        try:
            # نسخ احتياطي للبيانات الحالية
            await self.create_backup()
            
            # استعادة الملفات
            for filename in os.listdir(backup_path):
                if filename.endswith('.json'):
                    src = os.path.join(backup_path, filename)
                    dst = os.path.join(DATA_DIR, filename)
                    shutil.copy2(src, dst)
            
            # إعادة تحميل البيانات
            self.users = self._load_data('users.json', {})
            self.funding_requests = self._load_data('funding.json', {})
            self.invite_links = self._load_data('invites.json', {})
            self.numbers_files = self._load_data('numbers_files.json', {})
            self.banned_users = set(self._load_data('banned.json', []))
            self.force_sub_channels = self._load_data('force_sub.json', [])
            self.stats = self._load_data('stats.json', SystemStats().to_dict())
            
            logger.info(f"✅ تم استعادة النسخة الاحتياطية: {backup_id}")
            return True
        
        except Exception as e:
            logger.error(f"❌ خطأ في استعادة النسخة الاحتياطية: {e}")
            return False

# ==================== مدير البوت الرئيسي ====================

class FundingBot:
    """البوت الرئيسي"""
    
    def __init__(self):
        self.token = BOT_TOKEN
        self.admin_ids = ADMIN_IDS
        self.db = DatabaseManager()
        self.application = None
        self.start_time = datetime.now()
        self.is_running = False
        self.task_queue = asyncio.Queue()
        self.active_fundings = {}
        self.funding_semaphore = asyncio.Semaphore(5)  # حد أقصى 5 تمويلات متزامنة
        
        # إعداد المعالجات
        self._setup_handlers()
        
        logger.info(f"🚀 تم تهيئة البوت - الإصدار {BOT_VERSION}")
    
    def _setup_handlers(self):
        """إعداد معالجات الأوامر"""
        # قائمة حالات المحادثة
        self.conversation_states = {
            'ADD_NUMBERS_FILE': 1,
            'ADD_SUPPORT': 2,
            'ADD_CHANNEL_LINK': 3,
            'ADD_FORCE_CHANNEL': 4,
            'REMOVE_FORCE_CHANNEL': 5,
            'CHARGE_POINTS_USER': 6,
            'CHARGE_POINTS_AMOUNT': 7,
            'DEDUCT_POINTS_USER': 8,
            'DEDUCT_POINTS_AMOUNT': 9,
            'BAN_USER': 10,
            'UNBAN_USER': 11,
            'CHANGE_INVITE_REWARD': 12,
            'CHANGE_MEMBER_PRICE': 13,
            'CHANGE_WELCOME': 14,
            'FUNDING_MEMBERS_COUNT': 15,
            'FUNDING_CHAT_LINK': 16,
            'BROADCAST_MESSAGE': 17,
            'ADD_VIP_USER': 18,
            'REMOVE_VIP_USER': 19,
            'SETTINGS_VALUE': 20,
            'BACKUP_NAME': 21,
            'FILTER_WORDS': 22,
        }
    
    async def start(self):
        """بدء تشغيل البوت"""
        try:
            # إنشاء التطبيق
            self.application = Application.builder().token(self.token).build()
            
            # إضافة المعالجات
            self._add_handlers()
            
            # بدء البوت
            self.is_running = True
            
            # بدء المهام الخلفية
            asyncio.create_task(self._background_tasks())
            
            logger.info("✅ البوت يعمل الآن...")
            
            # تشغيل البوت
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling()
            
            # الانتظار حتى يتم إيقاف البوت
            while self.is_running:
                await asyncio.sleep(1)
        
        except Exception as e:
            logger.error(f"❌ خطأ في تشغيل البوت: {e}")
            logger.error(traceback.format_exc())
    
    async def stop(self):
        """إيقاف تشغيل البوت"""
        self.is_running = False
        
        if self.application:
            await self.application.updater.stop()
            await self.application.stop()
            await self.application.shutdown()
        
        logger.info("🛑 تم إيقاف البوت")
    
    def _add_handlers(self):
        """إضافة جميع المعالجات"""
        
        # ========== معالج /start ==========
        async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
            """معالج أمر /start"""
            user = update.effective_user
            user_id = user.id
            username = user.username or user.first_name
            
            # التحقق من وضع الصيانة
            if self.db.settings.get('maintenance_mode') and user_id not in self.admin_ids:
                await update.message.reply_text(self.db.settings['maintenance_message'])
                return
            
            # التحقق من الحظر
            if str(user_id) in self.db.banned_users:
                await update.message.reply_text("🚫 أنت محظور من استخدام البوت.")
                return
            
            # معالجة بارامتر بدء التشغيل (الدعوة)
            args = context.args
            if args:
                inviter_id = await self._process_invite(args[0], user_id, username)
                if inviter_id:
                    # إشعار المدعو
                    try:
                        await context.bot.send_message(
                            inviter_id,
                            f"🎉 تم دعوة مستخدم جديد!\n"
                            f"👤 المستخدم: {username}\n"
                            f"💰 رصيدك: {self.db.users.get(str(inviter_id), {}).get('points', 0)} نقطة"
                        )
                    except:
                        pass
            
            # تسجيل دخول المستخدم
            user_data = await self.db.get_user(user_id)
            user_data.username = username
            user_data.first_name = user.first_name
            user_data.last_name = user.last_name
            user_data.last_active = datetime.now().isoformat()
            await self.db.save_user(user_data)
            
            # التحقق من الاشتراك الإجباري
            if self.db.settings.get('require_force_sub'):
                not_joined = await self._check_force_subscription(user_id, context)
                if not_joined:
                    await self._send_force_sub_message(update, not_joined)
                    return
            
            # إرسال رسالة الترحيب
            await self._send_welcome_message(update, user_data)
        
        # ========== معالج النصوص ==========
        async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
            """معالج النصوص"""
            user_id = update.effective_user.id
            text = update.message.text
            state = context.user_data.get('state')
            
            # التحقق من وضع الصيانة
            if self.db.settings.get('maintenance_mode') and user_id not in self.admin_ids:
                await update.message.reply_text(self.db.settings['maintenance_message'])
                return
            
            # التحقق من الحظر
            if str(user_id) in self.db.banned_users:
                await update.message.reply_text("🚫 أنت محظور من استخدام البوت.")
                return
            
            # التحقق من الاشتراك الإجباري
            if self.db.settings.get('require_force_sub') and user_id not in self.admin_ids:
                not_joined = await self._check_force_subscription(user_id, context)
                if not_joined:
                    await self._send_force_sub_message(update, not_joined)
                    return
            
            # معالجة حسب الحالة
            if state == self.conversation_states['FUNDING_MEMBERS_COUNT']:
                await self._handle_funding_members_count(update, context, text)
            elif state == self.conversation_states['FUNDING_CHAT_LINK']:
                await self._handle_funding_chat_link(update, context, text)
            elif state == self.conversation_states['CHARGE_POINTS_USER'] and user_id in self.admin_ids:
                await self._handle_charge_user(update, context, text)
            elif state == self.conversation_states['CHARGE_POINTS_AMOUNT'] and user_id in self.admin_ids:
                await self._handle_charge_amount(update, context, text)
            elif state == self.conversation_states['DEDUCT_POINTS_USER'] and user_id in self.admin_ids:
                await self._handle_deduct_user(update, context, text)
            elif state == self.conversation_states['DEDUCT_POINTS_AMOUNT'] and user_id in self.admin_ids:
                await self._handle_deduct_amount(update, context, text)
            elif state == self.conversation_states['BAN_USER'] and user_id in self.admin_ids:
                await self._handle_ban_user(update, context, text)
            elif state == self.conversation_states['UNBAN_USER'] and user_id in self.admin_ids:
                await self._handle_unban_user(update, context, text)
            elif state == self.conversation_states['CHANGE_INVITE_REWARD'] and user_id in self.admin_ids:
                await self._handle_change_invite_reward(update, context, text)
            elif state == self.conversation_states['CHANGE_MEMBER_PRICE'] and user_id in self.admin_ids:
                await self._handle_change_member_price(update, context, text)
            elif state == self.conversation_states['CHANGE_WELCOME'] and user_id in self.admin_ids:
                await self._handle_change_welcome(update, context, text)
            elif state == self.conversation_states['ADD_SUPPORT'] and user_id in self.admin_ids:
                await self._handle_add_support(update, context, text)
            elif state == self.conversation_states['ADD_CHANNEL_LINK'] and user_id in self.admin_ids:
                await self._handle_add_channel(update, context, text)
            elif state == self.conversation_states['ADD_FORCE_CHANNEL'] and user_id in self.admin_ids:
                await self._handle_add_force_channel(update, context, text)
            elif state == self.conversation_states['BROADCAST_MESSAGE'] and user_id in self.admin_ids:
                await self._handle_broadcast(update, context, text)
            else:
                await update.message.reply_text("❌ أمر غير معروف. استخدم /start")
        
        # ========== معالج الملفات ==========
        async def document_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
            """معالج الملفات"""
            user_id = update.effective_user.id
            
            # التحقق من الصلاحية
            if user_id not in self.admin_ids:
                await update.message.reply_text("🚫 هذا الأمر متاح للإدارة فقط.")
                return
            
            # التحقق من الحالة
            if context.user_data.get('state') != self.conversation_states['ADD_NUMBERS_FILE']:
                await update.message.reply_text("❌ يرجى استخدام الأمر من لوحة التحكم أولاً.")
                return
            
            document = update.message.document
            
            # التحقق من صيغة الملف
            if not document.file_name.endswith('.txt'):
                await update.message.reply_text(
                    "❌ الصيغة غير مدعومة. يرجى إرسال ملف بصيغة TXT فقط.\n"
                    "ملاحظة: كل رقم في سطر منفصل."
                )
                return
            
            # إرسال رسالة انتظار
            wait_msg = await update.message.reply_text("⏳ جاري معالجة الملف...")
            
            try:
                # تحميل الملف
                file = await context.bot.get_file(document.file_id)
                file_content = await file.download_as_bytearray()
                content = file_content.decode('utf-8')
                
                # معالجة الأرقام
                numbers = await self._process_numbers_file(content)
                
                # حفظ الملف
                file_data = NumbersFile(
                    file_id=document.file_id,
                    file_name=document.file_name,
                    original_name=document.file_name,
                    added_by=user_id,
                    added_at=datetime.now().isoformat(),
                    numbers=numbers['valid'],
                    valid_numbers=numbers['valid_count'],
                    invalid_numbers=numbers['invalid_count'],
                    duplicate_numbers=numbers['duplicate_count'],
                    country_codes=numbers['country_codes'],
                    total_count=numbers['total_count'],
                    hash=numbers['file_hash']
                )
                
                file_id = await self.db.add_numbers_file(file_data)
                
                # إرسال التقرير
                report = (
                    f"✅ تم إضافة الملف بنجاح!\n\n"
                    f"📁 اسم الملف: {document.file_name}\n"
                    f"🆔 معرف الملف: {file_id[:8]}...\n\n"
                    f"📊 إحصائيات الأرقام:\n"
                    f"• إجمالي الأرقام: {numbers['total_count']}\n"
                    f"• ✅ صالح: {numbers['valid_count']}\n"
                    f"• ❌ غير صالح: {numbers['invalid_count']}\n"
                    f"• 🔄 مكرر: {numbers['duplicate_count']}\n\n"
                    f"🌍 رموز الدول:\n"
                )
                
                for code, count in list(numbers['country_codes'].items())[:5]:
                    report += f"• +{code}: {count} رقم\n"
                
                if len(numbers['country_codes']) > 5:
                    report += f"• ... و {len(numbers['country_codes']) - 5} دولة أخرى\n"
                
                await wait_msg.edit_text(report)
                
            except Exception as e:
                logger.error(f"❌ خطأ في معالجة الملف: {e}")
                await wait_msg.edit_text(f"❌ حدث خطأ أثناء معالجة الملف: {str(e)}")
            
            # إعادة تعيين الحالة
            context.user_data['state'] = None
        
        # ========== معالج الأزرار ==========
        async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
            """معالج الأزرار"""
            query = update.callback_query
            await query.answer()
            
            user_id = query.from_user.id
            data = query.data
            
            # التحقق من وضع الصيانة
            if self.db.settings.get('maintenance_mode') and user_id not in self.admin_ids:
                await query.edit_message_text(self.db.settings['maintenance_message'])
                return
            
            # التحقق من الحظر
            if str(user_id) in self.db.banned_users:
                await query.edit_message_text("🚫 أنت محظور من استخدام البوت.")
                return
            
            # التحقق من الاشتراك الإجباري
            if self.db.settings.get('require_force_sub') and user_id not in self.admin_ids and not data.startswith('force_sub_'):
                not_joined = await self._check_force_subscription(user_id, context)
                if not_joined:
                    await self._send_force_sub_message(query, not_joined)
                    return
            
            # معالجة الأزرار
            if data == "main_menu":
                await self._show_main_menu(query, user_id)
            elif data == "collect_points":
                await self._show_collect_points(query, user_id)
            elif data == "fund_members":
                await self._show_funding_form(query, context, user_id)
            elif data == "my_fundings":
                await self._show_my_fundings(query, user_id)
            elif data == "my_stats":
                await self._show_my_stats(query, user_id)
            elif data == "support":
                await self._show_support(query)
            elif data == "channel":
                await self._show_channel(query)
            elif data == "admin_panel" and user_id in self.admin_ids:
                await self._show_admin_panel(query)
            elif data == "admin_stats" and user_id in self.admin_ids:
                await self._show_admin_stats(query)
            elif data == "admin_charge" and user_id in self.admin_ids:
                await self._show_charge_form(query, context)
            elif data == "admin_deduct" and user_id in self.admin_ids:
                await self._show_deduct_form(query, context)
            elif data == "admin_add_file" and user_id in self.admin_ids:
                await self._show_add_file_form(query, context)
            elif data == "admin_delete_file" and user_id in self.admin_ids:
                await self._show_delete_file_menu(query)
            elif data.startswith("delete_file_") and user_id in self.admin_ids:
                await self._handle_delete_file(query, data)
            elif data == "admin_add_support" and user_id in self.admin_ids:
                await self._show_add_support_form(query, context)
            elif data == "admin_add_channel" and user_id in self.admin_ids:
                await self._show_add_channel_form(query, context)
            elif data == "admin_ban" and user_id in self.admin_ids:
                await self._show_ban_form(query, context)
            elif data == "admin_unban" and user_id in self.admin_ids:
                await self._show_unban_form(query, context)
            elif data == "admin_force_sub" and user_id in self.admin_ids:
                await self._show_force_sub_menu(query)
            elif data == "admin_add_force" and user_id in self.admin_ids:
                await self._show_add_force_form(query, context)
            elif data.startswith("remove_force_") and user_id in self.admin_ids:
                await self._handle_remove_force(query, data)
            elif data == "admin_change_invite" and user_id in self.admin_ids:
                await self._show_change_invite_form(query, context)
            elif data == "admin_change_price" and user_id in self.admin_ids:
                await self._show_change_price_form(query, context)
            elif data == "admin_change_welcome" and user_id in self.admin_ids:
                await self._show_change_welcome_form(query, context)
            elif data == "admin_backup" and user_id in self.admin_ids:
                await self._handle_backup(query)
            elif data == "admin_restore" and user_id in self.admin_ids:
                await self._show_restore_menu(query)
            elif data.startswith("restore_") and user_id in self.admin_ids:
                await self._handle_restore(query, data)
            elif data == "admin_settings" and user_id in self.admin_ids:
                await self._show_settings_menu(query)
            elif data == "admin_broadcast" and user_id in self.admin_ids:
                await self._show_broadcast_form(query, context)
            elif data == "admin_vip" and user_id in self.admin_ids:
                await self._show_vip_menu(query)
            elif data == "admin_add_vip" and user_id in self.admin_ids:
                await self._show_add_vip_form(query, context)
            elif data == "admin_remove_vip" and user_id in self.admin_ids:
                await self._show_remove_vip_form(query, context)
            elif data.startswith("view_funding_") and user_id in self.admin_ids:
                await self._show_funding_details(query, data)
            elif data.startswith("cancel_funding_") and user_id in self.admin_ids:
                await self._handle_cancel_funding(query, data)
            elif data.startswith("approve_funding_") and user_id in self.admin_ids:
                await self._handle_approve_funding(query, data)
            elif data.startswith("pause_funding_") and user_id in self.admin_ids:
                await self._handle_pause_funding(query, data)
            elif data.startswith("resume_funding_") and user_id in self.admin_ids:
                await self._handle_resume_funding(query, data)
        
        # إضافة المعالجات إلى التطبيق
        self.application.add_handler(CommandHandler("start", start_command))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
        self.application.add_handler(MessageHandler(filters.Document.ALL, document_handler))
        self.application.add_handler(CallbackQueryHandler(button_handler))
    
    async def _process_invite(self, param: str, new_user_id: int, username: str) -> Optional[int]:
        """معالجة رابط الدعوة"""
        try:
            # استخراج معرف المدعو
            if '_' in param:
                inviter_id = int(param.split('_')[0])
                
                # التحقق من أن المدعو ليس نفسه
                if inviter_id == new_user_id:
                    return None
                
                # استخدام رابط الدعوة
                used_by = await self.db.use_invite_link(param, new_user_id)
                
                if used_by:
                    # إضافة نقاط للمدعو
                    points = self.db.settings['points_per_invite']
                    await self.db.update_user_points(inviter_id, points, f"دعوة مستخدم جديد: {username}")
                    
                    logger.info(f"🎉 تم استخدام رابط دعوة: {inviter_id} -> {new_user_id}")
                    return inviter_id
            
        except Exception as e:
            logger.error(f"❌ خطأ في معالجة الدعوة: {e}")
        
        return None
    
    async def _check_force_subscription(self, user_id: int, context: ContextTypes.DEFAULT_TYPE) -> List[str]:
        """التحقق من الاشتراك الإجباري"""
        not_joined = []
        
        for channel in self.db.force_sub_channels:
            try:
                member = await context.bot.get_chat_member(chat_id=channel, user_id=user_id)
                if member.status in [ChatMemberStatus.LEFT, ChatMemberStatus.BANNED]:
                    not_joined.append(channel)
            except:
                not_joined.append(channel)
        
        return not_joined
    
    async def _send_force_sub_message(self, update_or_query, not_joined: List[str]):
        """إرسال رسالة الاشتراك الإجباري"""
        text = "🔒 *الاشتراك الإجباري*\n\n"
        text += "يجب الاشتراك في القنوات التالية لاستخدام البوت:\n\n"
        
        for channel in not_joined:
            text += f"• {channel}\n"
        
        text += "\n✅ بعد الاشتراك، اضغط على /start لتحديث الحالة."
        
        keyboard = [[InlineKeyboardButton("🔄 تحديث", callback_data="main_menu")]]
        
        if hasattr(update_or_query, 'edit_message_text'):
            await update_or_query.edit_message_text(
                text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            await update_or_query.message.reply_text(
                text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
    
    async def _send_welcome_message(self, update: Update, user_data: User):
        """إرسال رسالة الترحيب"""
        welcome = self.db.settings['welcome_message']
        
        text = (
            f"👋 *مرحباً بك {user_data.username}!*\n\n"
            f"🆔 الايدي: `{user_data.user_id}`\n"
            f"💰 نقاطك: {user_data.points}\n"
            f"👥 عدد الدعوات: {user_data.invites_count}\n\n"
            f"{welcome}"
        )
        
        # أزرار القائمة الرئيسية
        keyboard = [
            [InlineKeyboardButton("💰 تجميع النقاط", callback_data="collect_points")],
            [InlineKeyboardButton("🚀 تمويل مشتركين", callback_data="fund_members")],
            [InlineKeyboardButton("📊 تمويلاتي", callback_data="my_fundings")],
            [InlineKeyboardButton("📈 إحصائياتي", callback_data="my_stats")],
            [InlineKeyboardButton("🆘 الدعم الفني", callback_data="support")],
            [InlineKeyboardButton("📢 قناة البوت", callback_data="channel")],
        ]
        
        # إضافة زر لوحة التحكم للمدراء
        if user_data.user_id in self.admin_ids:
            keyboard.append([InlineKeyboardButton("⚙️ لوحة التحكم", callback_data="admin_panel")])
        
        await update.message.reply_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def _show_main_menu(self, query: CallbackQuery, user_id: int):
        """عرض القائمة الرئيسية"""
        user_data = await self.db.get_user(user_id)
        
        text = (
            f"👋 *مرحباً بك {user_data.username}!*\n\n"
            f"🆔 الايدي: `{user_id}`\n"
            f"💰 نقاطك: {user_data.points}\n"
            f"👥 عدد الدعوات: {user_data.invites_count}\n\n"
            f"{self.db.settings['welcome_message']}"
        )
        
        keyboard = [
            [InlineKeyboardButton("💰 تجميع النقاط", callback_data="collect_points")],
            [InlineKeyboardButton("🚀 تمويل مشتركين", callback_data="fund_members")],
            [InlineKeyboardButton("📊 تمويلاتي", callback_data="my_fundings")],
            [InlineKeyboardButton("📈 إحصائياتي", callback_data="my_stats")],
            [InlineKeyboardButton("🆘 الدعم الفني", callback_data="support")],
            [InlineKeyboardButton("📢 قناة البوت", callback_data="channel")],
        ]
        
        if user_id in self.admin_ids:
            keyboard.append([InlineKeyboardButton("⚙️ لوحة التحكم", callback_data="admin_panel")])
        
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def _show_collect_points(self, query: CallbackQuery, user_id: int):
        """عرض صفحة تجميع النقاط"""
        invite_link = await self.db.get_invite_link(user_id)
        user_data = await self.db.get_user(user_id)
        
        text = (
            "🔗 *رابط الدعوة الخاص بك*\n\n"
            "شارك الرابط التالي مع أصدقائك، وكل شخص يدخل عن طريق الرابط ستحصل على نقاط!\n\n"
            f"🔗 *الرابط:*\n`{invite_link.full_link}`\n\n"
            f"💰 *النقاط لكل دعوة:* {self.db.settings['points_per_invite']} نقطة\n"
            f"👥 *إجمالي من دعوتهم:* {user_data.invites_count}\n"
            f"👤 *المستخدمين الفريدين:* {invite_link.unique_uses}\n\n"
            "📊 *إحصائيات الدعوات:*\n"
            f"• إجمالي النقاط من الدعوات: {user_data.total_points_earned}\n"
            f"• آخر دعوة: {invite_link.last_use or 'لا يوجد'}\n\n"
            "🔄 *للشحن:*\n"
            "يمكنك التواصل مع الدعم الفني لشحن رصيدك مباشرة."
        )
        
        keyboard = [
            [InlineKeyboardButton("🔗 نسخ الرابط", callback_data="copy_link")],
            [InlineKeyboardButton("📊 إحصائيات الدعوات", callback_data="invite_stats")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")]
        ]
        
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def _show_funding_form(self, query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE, user_id: int):
        """عرض نموذج التمويل"""
        user_data = await self.db.get_user(user_id)
        
        # التحقق من الحد الأقصى اليومي
        today_fundings = sum(
            1 for r in self.db.funding_requests.values()
            if r['user_id'] == user_id and 
            r['created_at'].startswith(datetime.now().strftime('%Y-%m-%d'))
        )
        
        if today_fundings >= self.db.settings['daily_funding_limit']:
            await query.edit_message_text(
                f"❌ لقد تجاوزت الحد الأقصى للتمويلات اليومية ({self.db.settings['daily_funding_limit']}).\n"
                "يرجى المحاولة غداً."
            )
            return
        
        text = (
            "🚀 *تمويل مشتركين*\n\n"
            f"💰 *رصيدك الحالي:* {user_data.points} نقطة\n"
            f"💵 *تكلفة العضو الواحد:* {self.db.settings['points_per_member']} نقطة\n"
            f"📊 *الحد الأدنى:* {self.db.settings['min_funding_members']} عضو\n"
            f"📈 *الحد الأقصى:* {self.db.settings['max_funding_members']} عضو\n\n"
            "📝 *أرسل لي عدد الأعضاء الذي تريد تمويلهم*\n"
            "(مثال: 100)"
        )
        
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN
        )
        
        context.user_data['state'] = self.conversation_states['FUNDING_MEMBERS_COUNT']
    
    async def _handle_funding_members_count(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
        """معالجة إدخال عدد الأعضاء للتمويل"""
        user_id = update.effective_user.id
        user_data = await self.db.get_user(user_id)
        
        try:
            members_count = int(text)
            
            # التحقق من الحدود
            if members_count < self.db.settings['min_funding_members']:
                await update.message.reply_text(
                    f"❌ الحد الأدنى للتمويل هو {self.db.settings['min_funding_members']} عضو."
                )
                return
            
            if members_count > self.db.settings['max_funding_members']:
                await update.message.reply_text(
                    f"❌ الحد الأقصى للتمويل هو {self.db.settings['max_funding_members']} عضو."
                )
                return
            
            # حساب التكلفة
            cost = members_count * self.db.settings['points_per_member']
            
            if user_data.points < cost:
                await update.message.reply_text(
                    f"❌ *رصيدك غير كافٍ*\n\n"
                    f"💰 رصيدك: {user_data.points}\n"
                    f"💵 التكلفة: {cost}\n"
                    f"⚡ الناقص: {cost - user_data.points}\n\n"
                    f"🔄 يمكنك شحن رصيدك عبر:\n"
                    f"• دعوة أصدقاء\n"
                    f"• التواصل مع الدعم الفني"
                )
                context.user_data['state'] = None
                return
            
            # حفظ البيانات مؤقتاً
            context.user_data['funding_members'] = members_count
            context.user_data['funding_cost'] = cost
            
            await update.message.reply_text(
                f"✅ *تم حساب التكلفة*\n\n"
                f"👥 عدد الأعضاء: {members_count}\n"
                f"💰 التكلفة: {cost} نقطة\n"
                f"💳 الرصيد بعد الخصم: {user_data.points - cost}\n\n"
                f"📢 *الآن أرسل رابط قناتك أو مجموعتك*\n\n"
                f"⚠️ *ملاحظات مهمة:*\n"
                f"• تأكد أن البوت مشرف في القناة/المجموعة\n"
                f"• القناة يجب أن تكون عامة\n"
                f"• يفضل أن تكون القناة مفتوحة"
            )
            
            context.user_data['state'] = self.conversation_states['FUNDING_CHAT_LINK']
            
        except ValueError:
            await update.message.reply_text("❌ يرجى إرسال عدد صحيح.")
    
    async def _handle_funding_chat_link(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
        """معالجة رابط القناة وبدء التمويل"""
        user_id = update.effective_user.id
        chat_link = text.strip()
        members_count = context.user_data.get('funding_members')
        cost = context.user_data.get('funding_cost')
        
        if not members_count or not cost:
            await update.message.reply_text("❌ حدث خطأ، يرجى المحاولة مرة أخرى.")
            context.user_data['state'] = None
            return
        
        # إرسال رسالة انتظار
        wait_msg = await update.message.reply_text("⏳ جاري التحقق من القناة...")
        
        try:
            # استخراج معرف القناة
            if 't.me/' in chat_link:
                chat_username = chat_link.split('t.me/')[-1].split('/')[0]
                if chat_username.startswith('@'):
                    chat_username = chat_username[1:]
                
                chat = await context.bot.get_chat(f"@{chat_username}")
            elif chat_link.startswith('@'):
                chat = await context.bot.get_chat(chat_link)
            else:
                try:
                    chat_id = int(chat_link)
                    chat = await context.bot.get_chat(chat_id)
                except:
                    await wait_msg.edit_text("❌ رابط القناة غير صالح.")
                    context.user_data['state'] = None
                    return
            
            # التحقق من أن البوت مشرف
            bot_member = await context.bot.get_chat_member(chat.id, context.bot.id)
            if bot_member.status not in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR]:
                await wait_msg.edit_text(
                    "❌ *البوت ليس مشرفاً في هذه القناة*\n\n"
                    "يرجى جعل البوت مشرف ثم حاول مرة أخرى.\n\n"
                    "🔧 *الصلاحيات المطلوبة:*\n"
                    "• إضافة أعضاء\n"
                    "• إرسال رسائل"
                )
                context.user_data['state'] = None
                return
            
            # خصم النقاط
            await self.db.update_user_points(user_id, -cost, f"تمويل {members_count} عضو")
            
            # إنشاء طلب تمويل
            request_id = str(uuid.uuid4())
            funding_request = FundingRequest(
                request_id=request_id,
                user_id=user_id,
                chat_id=chat.id,
                chat_title=chat.title or "بدون عنوان",
                chat_link=chat_link,
                chat_type=chat.type,
                members_count=members_count,
                cost=cost,
                status=FundingStatus.PENDING.value,
                source=MemberSource.NUMBERS_FILE.value,
                created_at=datetime.now().isoformat()
            )
            
            await self.db.save_funding_request(funding_request)
            
            await wait_msg.edit_text(
                f"✅ *تم بدء عملية التمويل بنجاح!*\n\n"
                f"📢 القناة: {chat_link}\n"
                f"👥 عدد الأعضاء: {members_count}\n"
                f"💰 التكلفة: {cost} نقطة\n"
                f"🆔 معرف الطلب: `{request_id[:8]}...`\n\n"
                f"⏳ سيتم إعلامك عند إضافة كل عضو.\n"
                f"📊 يمكنك متابعة حالة التمويل من قائمة 'تمويلاتي'"
            )
            
            # إشعار الإدارة
            await self._notify_admins_new_funding(funding_request, context)
            
            # بدء التمويل في الخلفية
            asyncio.create_task(self._process_funding(request_id, context))
            
        except Exception as e:
            logger.error(f"❌ خطأ في بدء التمويل: {e}")
            await wait_msg.edit_text(
                f"❌ حدث خطأ أثناء بدء التمويل.\n"
                f"الخطأ: {str(e)}\n\n"
                f"تأكد من صحة الرابط وأن البوت مشرف في القناة."
            )
        
        context.user_data['state'] = None
    
    async def _process_funding(self, request_id: str, context: ContextTypes.DEFAULT_TYPE):
        """معالجة طلب التمويل في الخلفية"""
        # استخدام semaphore للتحكم بعدد التمويلات المتزامنة
        async with self.funding_semaphore:
            request = await self.db.get_funding_request(request_id)
            if not request:
                logger.error(f"❌ طلب التمويل غير موجود: {request_id}")
                return
            
            try:
                # تحديث الحالة
                request.status = FundingStatus.PROCESSING.value
                request.started_at = datetime.now().isoformat()
                await self.db.save_funding_request(request)
                
                # الحصول على أرقام متاحة
                available_numbers = await self.db.get_available_numbers(request.members_count)
                
                if len(available_numbers) < request.members_count:
                    # لا توجد أرقام كافية
                    request.status = FundingStatus.FAILED.value
                    request.notes = "لا توجد أرقام كافية"
                    await self.db.save_funding_request(request)
                    
                    # إرجاع النقاط
                    await self.db.update_user_points(
                        request.user_id, 
                        request.cost, 
                        "استرداد نقاط بسبب نقص الأرقام"
                    )
                    
                    # إشعار المستخدم
                    try:
                        await context.bot.send_message(
                            request.user_id,
                            f"❌ *فشل التمويل*\n\n"
                            f"عذراً، لا توجد أرقام كافية حالياً.\n"
                            f"💰 تم إرجاع {request.cost} نقطة إلى رصيدك."
                        )
                    except:
                        pass
                    
                    # إشعار الإدارة
                    await self._notify_admins_funding_failed(request, context, "نقص الأرقام")
                    
                    return
                
                # بدء إضافة الأعضاء
                added = 0
                failed = 0
                used_numbers = []
                
                for i, number in enumerate(available_numbers[:request.members_count], 1):
                    try:
                        # محاكاة إضافة العضو
                        await asyncio.sleep(random.uniform(1, 3))
                        
                        # هنا يتم وضع كود إضافة العضو الفعلي
                        # باستخدام Telethon أو أي مكتبة أخرى
                        
                        added += 1
                        used_numbers.append(number)
                        
                        # إرسال تحديث كل 10 أعضاء
                        if i % 10 == 0 or i == request.members_count:
                            request.added_members = added
                            request.failed_members = failed
                            request.last_update = datetime.now().isoformat()
                            await self.db.save_funding_request(request)
                            
                            # إرسال تحديث للمستخدم
                            try:
                                await context.bot.send_message(
                                    request.user_id,
                                    f"📊 *تحديث التمويل*\n\n"
                                    f"✅ تم إضافة {added} عضو\n"
                                    f"⏳ المتبقي: {request.members_count - added}\n"
                                    f"📊 التقدم: {int((added/request.members_count)*100)}%"
                                )
                            except:
                                pass
                    
                    except Exception as e:
                        logger.error(f"❌ فشل إضافة العضو {number}: {e}")
                        failed += 1
                
                # تحديث الأرقام المستخدمة
                if used_numbers:
                    await self.db.mark_numbers_used(used_numbers, request_id)
                
                # تحديث الطلب
                request.added_members = added
                request.failed_members = failed
                request.used_numbers = used_numbers
                
                if added >= request.members_count:
                    request.status = FundingStatus.COMPLETED.value
                    message = f"✅ *اكتمل التمويل بنجاح!*\n\n"
                elif added > 0:
                    request.status = FundingStatus.COMPLETED.value  # أو PARTIAL
                    message = f"⚠️ *اكتمل التمويل جزئياً*\n\n"
                else:
                    request.status = FundingStatus.FAILED.value
                    message = f"❌ *فشل التمويل*\n\n"
                
                request.completed_at = datetime.now().isoformat()
                await self.db.save_funding_request(request)
                
                # إرسال التقرير النهائي للمستخدم
                try:
                    await context.bot.send_message(
                        request.user_id,
                        f"{message}"
                        f"📢 القناة: {request.chat_link}\n"
                        f"✅ تمت الإضافة: {added}\n"
                        f"❌ فشل: {failed}\n"
                        f"📊 نسبة النجاح: {int((added/request.members_count)*100) if request.members_count else 0}%\n\n"
                        f"🆔 معرف الطلب: `{request_id[:8]}...`"
                    )
                except:
                    pass
                
                # إشعار الإدارة
                await self._notify_admins_funding_complete(request, context)
                
            except Exception as e:
                logger.error(f"❌ خطأ في معالجة التمويل {request_id}: {e}")
                logger.error(traceback.format_exc())
                
                request.status = FundingStatus.FAILED.value
                request.notes = str(e)
                await self.db.save_funding_request(request)
                
                # إشعار الإدارة
                await self._notify_admins_funding_failed(request, context, str(e))
    
    async def _show_my_fundings(self, query: CallbackQuery, user_id: int):
        """عرض تمويلات المستخدم"""
        user_fundings = []
        
        for req_id, req_data in self.db.funding_requests.items():
            if req_data.get('user_id') == user_id:
                status_emoji = {
                    FundingStatus.PENDING.value: "⏳",
                    FundingStatus.PROCESSING.value: "⚙️",
                    FundingStatus.COMPLETED.value: "✅",
                    FundingStatus.FAILED.value: "❌",
                    FundingStatus.CANCELLED.value: "🚫"
                }.get(req_data['status'], "❓")
                
                created = datetime.fromisoformat(req_data['created_at'])
                time_diff = datetime.now() - created
                
                if time_diff.days > 0:
                    time_str = f"منذ {time_diff.days} يوم"
                elif time_diff.seconds > 3600:
                    time_str = f"منذ {time_diff.seconds // 3600} ساعة"
                else:
                    time_str = f"منذ {time_diff.seconds // 60} دقيقة"
                
                user_fundings.append(
                    f"{status_emoji} *{req_data['chat_title'][:20]}*\n"
                    f"🆔 `{req_id[:8]}...`\n"
                    f"👥 {req_data['added_members']}/{req_data['members_count']}\n"
                    f"📅 {time_str}"
                )
        
        if not user_fundings:
            text = "📊 ليس لديك أي تمويلات سابقة."
        else:
            text = "📊 *تمويلاتك*\n\n" + "\n\n".join(user_fundings[:10])
            
            if len(user_fundings) > 10:
                text += f"\n\n... و {len(user_fundings) - 10} تمويل آخر"
        
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")]]
        
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def _show_my_stats(self, query: CallbackQuery, user_id: int):
        """عرض إحصائيات المستخدم"""
        user_data = await self.db.get_user(user_id)
        
        # حساب إحصائيات إضافية
        total_fundings = sum(1 for r in self.db.funding_requests.values() if r['user_id'] == user_id)
        completed_fundings = sum(1 for r in self.db.funding_requests.values() 
                                if r['user_id'] == user_id and r['status'] == FundingStatus.COMPLETED.value)
        total_members = sum(r.get('added_members', 0) for r in self.db.funding_requests.values() if r['user_id'] == user_id)
        
        # حساب الرتبة
        all_users_points = [(uid, u.get('points', 0)) for uid, u in self.db.users.items()]
        all_users_points.sort(key=lambda x: x[1], reverse=True)
        
        rank = 1
        for i, (uid, _) in enumerate(all_users_points, 1):
            if int(uid) == user_id:
                rank = i
                break
        
        joined_date = datetime.fromisoformat(user_data.joined_date) if user_data.joined_date else datetime.now()
        days_since_joined = (datetime.now() - joined_date).days or 1
        
        text = (
            "📈 *إحصائياتك الشخصية*\n\n"
            f"🆔 *الايدي:* `{user_id}`\n"
            f"👤 *اسم المستخدم:* {user_data.username}\n"
            f"🏆 *الرتبة:* #{rank} من {len(self.db.users)}\n\n"
            f"💰 *النقاط:*\n"
            f"• الحالية: {user_data.points}\n"
            f"• المكتسبة: {user_data.total_points_earned}\n"
            f"• المنفقة: {user_data.total_points_spent}\n"
            f"• المعدل اليومي: {user_data.total_points_earned // days_since_joined}\n\n"
            f"👥 *الدعوات:*\n"
            f"• إجمالي الدعوات: {user_data.total_invites}\n"
            f"• المكافآت: {user_data.total_invites * self.db.settings['points_per_invite']}\n\n"
            f"📊 *التمويلات:*\n"
            f"• إجمالي: {total_fundings}\n"
            f"• المكتملة: {completed_fundings}\n"
            f"• الأعضاء الممولة: {total_members}\n\n"
            f"📅 *التواريخ:*\n"
            f"• التسجيل: {joined_date.strftime('%Y-%m-%d')}\n"
            f"• آخر نشاط: {user_data.last_active[:10] if user_data.last_active else 'غير معروف'}"
        )
        
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")]]
        
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def _show_support(self, query: CallbackQuery):
        """عرض معلومات الدعم الفني"""
        text = (
            "🆘 *الدعم الفني*\n\n"
            f"للتواصل مع الدعم الفني، يرجى التواصل مع:\n"
            f"@{self.db.settings['support_username']}\n\n"
            "📋 *للاستفسارات حول:*\n"
            "• شحن الرصيد\n"
            "• مشاكل التمويل\n"
            "• استفسارات عامة\n"
            "• اقتراحات وشكاوى"
        )
        
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")]]
        
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def _show_channel(self, query: CallbackQuery):
        """عرض رابط قناة البوت"""
        text = (
            "📢 *قناة البوت*\n\n"
            f"تابع قناة البوت لمعرفة آخر التحديثات والعروض:\n"
            f"{self.db.settings['channel_link']}\n\n"
            "✨ *مميزات القناة:*\n"
            "• عروض حصرية\n"
            "• تحديثات البوت\n"
            "• مسابقات وجوائز"
        )
        
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")]]
        
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    # ==================== دوال لوحة التحكم ====================
    
    async def _show_admin_panel(self, query: CallbackQuery):
        """عرض لوحة التحكم"""
        text = (
            "⚙️ *لوحة التحكم*\n\n"
            "مرحباً بك في لوحة التحكم. اختر الأمر الذي تريد تنفيذه:\n\n"
            "📊 *إحصائيات وإدارة*\n"
            "💰 *شحن وخصم الرصيد*\n"
            "📁 *إدارة ملفات الأرقام*\n"
            "🔒 *إدارة الحظر*\n"
            "📢 *إدارة القنوات*\n"
            "⚡ *إعدادات البوت*"
        )
        
        keyboard = [
            [InlineKeyboardButton("📊 إحصائيات البوت", callback_data="admin_stats")],
            [InlineKeyboardButton("💰 شحن رصيد", callback_data="admin_charge")],
            [InlineKeyboardButton("💸 خصم رصيد", callback_data="admin_deduct")],
            [InlineKeyboardButton("📁 إضافة ملف أرقام", callback_data="admin_add_file")],
            [InlineKeyboardButton("🗑️ حذف ملف أرقام", callback_data="admin_delete_file")],
            [InlineKeyboardButton("🔒 حظر مستخدم", callback_data="admin_ban")],
            [InlineKeyboardButton("🔓 رفع حظر", callback_data="admin_unban")],
            [InlineKeyboardButton("📢 الاشتراك الإجباري", callback_data="admin_force_sub")],
            [InlineKeyboardButton("⚙️ إعدادات متقدمة", callback_data="admin_settings")],
            [InlineKeyboardButton("📢 إرسال رسالة", callback_data="admin_broadcast")],
            [InlineKeyboardButton("💾 نسخ احتياطي", callback_data="admin_backup")],
            [InlineKeyboardButton("🔄 استعادة نسخة", callback_data="admin_restore")],
            [InlineKeyboardButton("👑 إدارة VIP", callback_data="admin_vip")],
            [InlineKeyboardButton("🔙 رجوع للقائمة الرئيسية", callback_data="main_menu")]
        ]
        
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def _show_admin_stats(self, query: CallbackQuery):
        """عرض إحصائيات البوت"""
        stats = await self.db.get_stats()
        
        uptime = datetime.now() - self.start_time
        uptime_str = f"{uptime.days} يوم {uptime.seconds // 3600} ساعة"
        
        text = (
            "📊 *إحصائيات البوت*\n\n"
            f"👥 *المستخدمين:*\n"
            f"• الإجمالي: {stats.total_users}\n"
            f"• نشط اليوم: {stats.active_users_today}\n"
            f"• نشط الأسبوع: {stats.active_users_week}\n"
            f"• نشط الشهر: {stats.active_users_month}\n"
            f"• محظورين: {stats.banned_users}\n"
            f"• VIP: {stats.vip_users}\n\n"
            f"📊 *التمويلات:*\n"
            f"• الإجمالي: {stats.total_fundings}\n"
            f"• مكتمل: {stats.completed_fundings}\n"
            f"• قيد الانتظار: {stats.pending_fundings}\n"
            f"• فشل: {stats.failed_fundings}\n"
            f"• ملغي: {stats.cancelled_fundings}\n"
            f"• الأعضاء المضافة: {stats.total_members_added}\n\n"
            f"💰 *النقاط:*\n"
            f"• الإجمالي: {stats.total_points}\n"
            f"• مكتسب اليوم: {stats.points_earned_today}\n"
            f"• منفق اليوم: {stats.points_spent_today}\n\n"
            f"📁 *الأرقام:*\n"
            f"• ملفات: {stats.numbers_files_count}\n"
            f"• إجمالي الأرقام: {stats.total_numbers}\n"
            f"• متاح: {stats.available_numbers}\n"
            f"• مستخدم: {stats.used_numbers}\n\n"
            f"⚙️ *النظام:*\n"
            f"• وقت التشغيل: {uptime_str}\n"
            f"• آخر نسخة: {stats.last_backup or 'لم تعمل'}\n"
            f"• الذاكرة: {stats.memory_usage:.1f}%\n"
            f"• المعالج: {stats.cpu_usage:.1f}%\n"
            f"• القرص: {stats.disk_usage:.1f}%"
        )
        
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel")]]
        
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def _show_charge_form(self, query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE):
        """عرض نموذج شحن الرصيد"""
        text = "💰 *شحن رصيد*\n\nأرسل ايدي المستخدم المراد شحن رصيده."
        
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN)
        context.user_data['state'] = self.conversation_states['CHARGE_POINTS_USER']
    
    async def _handle_charge_user(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
        """معالجة إدخال ايدي المستخدم للشحن"""
        try:
            target_id = int(text)
            context.user_data['charge_target'] = target_id
            
            await update.message.reply_text(
                f"💰 أرسل المبلغ المراد شحنه للمستخدم {target_id}:"
            )
            context.user_data['state'] = self.conversation_states['CHARGE_POINTS_AMOUNT']
            
        except ValueError:
            await update.message.reply_text("❌ يرجى إرسال ايدي صحيح.")
    
    async def _handle_charge_amount(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
        """معالجة إدخال مبلغ الشحن"""
        try:
            amount = int(text)
            if amount <= 0:
                await update.message.reply_text("❌ يرجى إرسال مبلغ أكبر من 0.")
                return
            
            target_id = context.user_data.get('charge_target')
            if not target_id:
                await update.message.reply_text("❌ حدث خطأ، يرجى المحاولة مرة أخرى.")
                context.user_data['state'] = None
                return
            
            # شحن الرصيد
            success, new_balance = await self.db.update_user_points(
                target_id, amount, f"شحن من قبل الإدارة"
            )
            
            if success:
                await update.message.reply_text(
                    f"✅ *تم شحن الرصيد بنجاح*\n\n"
                    f"👤 المستخدم: {target_id}\n"
                    f"💰 المبلغ المضاف: {amount}\n"
                    f"💳 الرصيد الحالي: {new_balance}"
                )
                
                # إشعار المستخدم
                try:
                    await context.bot.send_message(
                        target_id,
                        f"💰 *تم شحن رصيدك*\n\n"
                        f"المبلغ: +{amount} نقطة\n"
                        f"الرصيد الحالي: {new_balance}\n\n"
                        f"شكراً لاستخدامك البوت!"
                    )
                except:
                    pass
            else:
                await update.message.reply_text(f"❌ المستخدم {target_id} غير موجود.")
            
        except ValueError:
            await update.message.reply_text("❌ يرجى إرسال رقم صحيح.")
        
        context.user_data['state'] = None
    
    async def _show_deduct_form(self, query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE):
        """عرض نموذج خصم الرصيد"""
        text = "💸 *خصم رصيد*\n\nأرسل ايدي المستخدم المراد خصم رصيده."
        
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN)
        context.user_data['state'] = self.conversation_states['DEDUCT_POINTS_USER']
    
    async def _handle_deduct_user(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
        """معالجة إدخال ايدي المستخدم للخصم"""
        try:
            target_id = int(text)
            context.user_data['deduct_target'] = target_id
            
            await update.message.reply_text(
                f"💸 أرسل المبلغ المراد خصمه من المستخدم {target_id}:"
            )
            context.user_data['state'] = self.conversation_states['DEDUCT_POINTS_AMOUNT']
            
        except ValueError:
            await update.message.reply_text("❌ يرجى إرسال ايدي صحيح.")
    
    async def _handle_deduct_amount(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
        """معالجة إدخال مبلغ الخصم"""
        try:
            amount = int(text)
            if amount <= 0:
                await update.message.reply_text("❌ يرجى إرسال مبلغ أكبر من 0.")
                return
            
            target_id = context.user_data.get('deduct_target')
            if not target_id:
                await update.message.reply_text("❌ حدث خطأ، يرجى المحاولة مرة أخرى.")
                context.user_data['state'] = None
                return
            
            # التحقق من وجود المستخدم
            user_data = await self.db.get_user(target_id, create_if_missing=False)
            if not user_data:
                await update.message.reply_text(f"❌ المستخدم {target_id} غير موجود.")
                context.user_data['state'] = None
                return
            
            if user_data.points < amount:
                await update.message.reply_text(
                    f"❌ رصيد المستخدم غير كافٍ.\n"
                    f"💰 رصيده الحالي: {user_data.points}"
                )
                context.user_data['state'] = None
                return
            
            # خصم الرصيد
            success, new_balance = await self.db.update_user_points(
                target_id, -amount, f"خصم من قبل الإدارة"
            )
            
            await update.message.reply_text(
                f"✅ *تم خصم الرصيد بنجاح*\n\n"
                f"👤 المستخدم: {target_id}\n"
                f"💰 المبلغ المخصوم: {amount}\n"
                f"💳 الرصيد الحالي: {new_balance}"
            )
            
            # إشعار المستخدم
            try:
                await context.bot.send_message(
                    target_id,
                    f"💸 *تم خصم من رصيدك*\n\n"
                    f"المبلغ: -{amount} نقطة\n"
                    f"الرصيد الحالي: {new_balance}"
                )
            except:
                pass
            
        except ValueError:
            await update.message.reply_text("❌ يرجى إرسال رقم صحيح.")
        
        context.user_data['state'] = None
    
    async def _show_add_file_form(self, query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE):
        """عرض نموذج إضافة ملف أرقام"""
        text = (
            "📁 *إضافة ملف أرقام*\n\n"
            "أرسل ملف TXT يحتوي على أرقام الهواتف.\n"
            "كل رقم في سطر منفصل.\n\n"
            "✅ *شروط الأرقام الصحيحة:*\n"
            "• تبدأ برمز الدولة (مثال: 966XXXXXXXXX)\n"
            "• تتكون من 10-14 رقم\n"
            "• أرقام فقط (بدون مسافات أو رموز)\n\n"
            "📝 *مثال:*\n"
            "966501234567\n"
            "966501234568\n"
            "966501234569"
        )
        
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN)
        context.user_data['state'] = self.conversation_states['ADD_NUMBERS_FILE']
    
    async def _process_numbers_file(self, content: str) -> Dict[str, Any]:
        """معالجة ملف الأرقام"""
        lines = content.strip().split('\n')
        valid = []
        invalid = []
        seen = set()
        country_codes = defaultdict(int)
        
        for line in lines:
            number = line.strip()
            if not number:
                continue
            
            # تنظيف الرقم
            cleaned = re.sub(r'[^0-9]', '', number)
            
            # التحقق من صحة الرقم
            if 10 <= len(cleaned) <= 14 and cleaned not in seen:
                # استخراج رمز الدولة
                country_code = cleaned[:3]
                if country_code in self.db.settings['allowed_country_codes']:
                    valid.append(cleaned)
                    seen.add(cleaned)
                    country_codes[country_code] += 1
                else:
                    invalid.append(cleaned)
            else:
                invalid.append(cleaned)
        
        # حساب المكررات
        duplicates = len(lines) - len(seen) - len(invalid)
        
        # إنشاء hash للملف
        file_hash = hashlib.sha256(content.encode()).hexdigest()
        
        return {
            'valid': valid,
            'valid_count': len(valid),
            'invalid_count': len(invalid),
            'duplicate_count': duplicates,
            'total_count': len(valid) + len(invalid) + duplicates,
            'country_codes': dict(country_codes),
            'file_hash': file_hash
        }
    
    async def _show_delete_file_menu(self, query: CallbackQuery):
        """عرض قائمة حذف الملفات"""
        if not self.db.numbers_files:
            await query.edit_message_text(
                "📁 لا توجد ملفات أرقام لحذفها.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel")
                ]])
            )
            return
        
        text = "🗑️ *حذف ملف أرقام*\n\nاختر الملف الذي تريد حذفه:\n\n"
        keyboard = []
        
        for file_id, file_data in list(self.db.numbers_files.items())[:10]:
            available = file_data.get('total_count', 0) - file_data.get('used_count', 0)
            added = datetime.fromisoformat(file_data['added_at']).strftime('%Y-%m-%d')
            
            text += f"🆔 `{file_id[:8]}...`\n"
            text += f"📁 {file_data['file_name'][:30]}\n"
            text += f"📊 إجمالي: {file_data['total_count']} | متاح: {available}\n"
            text += f"📅 {added}\n\n"
            
            keyboard.append([InlineKeyboardButton(
                f"🗑️ حذف {file_data['file_name'][:20]}", 
                callback_data=f"delete_file_{file_id}"
            )])
        
        if len(self.db.numbers_files) > 10:
            text += f"... و {len(self.db.numbers_files) - 10} ملف آخر"
        
        keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel")])
        
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def _handle_delete_file(self, query: CallbackQuery, data: str):
        """معالجة حذف ملف"""
        file_id = data.replace('delete_file_', '')
        
        if file_id in self.db.numbers_files:
            file_data = self.db.numbers_files[file_id]
            del self.db.numbers_files[file_id]
            await self.db._save_data('numbers_files.json', self.db.numbers_files)
            
            await query.edit_message_text(
                f"✅ تم حذف الملف بنجاح.\n\n"
                f"📁 اسم الملف: {file_data['file_name']}\n"
                f"📊 إجمالي الأرقام: {file_data['total_count']}",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel")
                ]])
            )
        else:
            await query.edit_message_text(
                "❌ الملف غير موجود.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel")
                ]])
            )
    
    async def _show_add_support_form(self, query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE):
        """عرض نموذج إضافة حساب دعم"""
        text = (
            "🆘 *إضافة حساب دعم*\n\n"
            f"الحساب الحالي: @{self.db.settings['support_username']}\n\n"
            "أرسل يوزر حساب الدعم الفني الجديد (بدون @)."
        )
        
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN)
        context.user_data['state'] = self.conversation_states['ADD_SUPPORT']
    
    async def _handle_add_support(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
        """معالجة إضافة حساب دعم"""
        support = text.strip().replace('@', '')
        self.db.settings['support_username'] = support
        await self.db._save_data('settings.json', self.db.settings)
        
        await update.message.reply_text(
            f"✅ تم تعيين حساب الدعم الفني إلى @{support} بنجاح."
        )
        context.user_data['state'] = None
    
    async def _show_add_channel_form(self, query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE):
        """عرض نموذج إضافة رابط قناة"""
        text = (
            "📢 *إضافة رابط قناة*\n\n"
            f"الرابط الحالي: {self.db.settings['channel_link']}\n\n"
            "أرسل رابط قناة البوت الجديد."
        )
        
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN)
        context.user_data['state'] = self.conversation_states['ADD_CHANNEL_LINK']
    
    async def _handle_add_channel(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
        """معالجة إضافة رابط قناة"""
        channel = text.strip()
        self.db.settings['channel_link'] = channel
        await self.db._save_data('settings.json', self.db.settings)
        
        await update.message.reply_text(
            f"✅ تم تعيين رابط القناة إلى:\n{channel}"
        )
        context.user_data['state'] = None
    
    async def _show_ban_form(self, query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE):
        """عرض نموذج حظر مستخدم"""
        text = "🔒 *حظر مستخدم*\n\nأرسل ايدي المستخدم المراد حظره."
        
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN)
        context.user_data['state'] = self.conversation_states['BAN_USER']
    
    async def _handle_ban_user(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
        """معالجة حظر مستخدم"""
        try:
            target_id = int(text)
            
            if target_id in self.admin_ids:
                await update.message.reply_text("❌ لا يمكن حظر مدير البوت.")
                context.user_data['state'] = None
                return
            
            await self.db.ban_user(target_id, "حظر من قبل الإدارة")
            
            await update.message.reply_text(
                f"✅ تم حظر المستخدم {target_id} بنجاح."
            )
            
        except ValueError:
            await update.message.reply_text("❌ يرجى إرسال ايدي صحيح.")
        
        context.user_data['state'] = None
    
    async def _show_unban_form(self, query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE):
        """عرض نموذج رفع حظر"""
        text = "🔓 *رفع حظر*\n\nأرسل ايدي المستخدم المراد رفع الحظر عنه."
        
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN)
        context.user_data['state'] = self.conversation_states['UNBAN_USER']
    
    async def _handle_unban_user(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
        """معالجة رفع حظر"""
        try:
            target_id = int(text)
            
            success = await self.db.unban_user(target_id)
            
            if success:
                await update.message.reply_text(
                    f"✅ تم رفع الحظر عن المستخدم {target_id} بنجاح."
                )
            else:
                await update.message.reply_text(
                    f"❌ المستخدم {target_id} غير محظور."
                )
            
        except ValueError:
            await update.message.reply_text("❌ يرجى إرسال ايدي صحيح.")
        
        context.user_data['state'] = None
    
    async def _show_force_sub_menu(self, query: CallbackQuery):
        """عرض قائمة الاشتراك الإجباري"""
        text = "📢 *الاشتراك الإجباري*\n\n"
        
        if self.db.force_sub_channels:
            text += "القنوات الحالية:\n"
            for i, channel in enumerate(self.db.force_sub_channels, 1):
                text += f"{i}. {channel}\n"
        else:
            text += "لا توجد قنوات اشتراك إجباري حالياً.\n"
        
        text += f"\n✅ حالة الاشتراك الإجباري: {'مفعل' if self.db.settings['require_force_sub'] else 'معطل'}"
        
        keyboard = [
            [InlineKeyboardButton("➕ إضافة قناة", callback_data="admin_add_force")],
            [InlineKeyboardButton("❌ حذف قناة", callback_data="admin_remove_force")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel")]
        ]
        
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def _show_add_force_form(self, query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE):
        """عرض نموذج إضافة قناة للاشتراك الإجباري"""
        text = (
            "📢 *إضافة قناة للاشتراك الإجباري*\n\n"
            "أرسل معرف القناة (مثال: @channel_username)\n\n"
            "ملاحظة: يجب أن يكون البوت مشرفاً في القناة."
        )
        
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN)
        context.user_data['state'] = self.conversation_states['ADD_FORCE_CHANNEL']
    
    async def _handle_add_force_channel(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
        """معالجة إضافة قناة للاشتراك الإجباري"""
        channel = text.strip()
        
        # التحقق من صحة القناة
        try:
            if not channel.startswith('@'):
                channel = '@' + channel
            
            chat = await context.bot.get_chat(channel)
            
            # التحقق من أن البوت مشرف
            bot_member = await context.bot.get_chat_member(chat.id, context.bot.id)
            if bot_member.status not in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR]:
                await update.message.reply_text(
                    "❌ البوت ليس مشرفاً في هذه القناة.\n"
                    "يرجى جعل البوت مشرف ثم حاول مرة أخرى."
                )
                context.user_data['state'] = None
                return
            
            success = await self.db.add_force_channel(channel)
            
            if success:
                await update.message.reply_text(
                    f"✅ تم إضافة القناة {channel} للاشتراك الإجباري بنجاح."
                )
            else:
                await update.message.reply_text(
                    f"⚠️ القناة {channel} موجودة بالفعل."
                )
            
        except Exception as e:
            await update.message.reply_text(
                f"❌ خطأ: {str(e)}\nتأكد من صحة معرف القناة."
            )
        
        context.user_data['state'] = None
    
    async def _handle_remove_force(self, query: CallbackQuery, data: str):
        """معالجة حذف قناة من الاشتراك الإجباري"""
        channel = data.replace('remove_force_', '')
        
        success = await self.db.remove_force_channel(channel)
        
        if success:
            await query.edit_message_text(
                f"✅ تم حذف القناة {channel} من الاشتراك الإجباري.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 رجوع", callback_data="admin_force_sub")
                ]])
            )
        else:
            await query.edit_message_text(
                f"❌ القناة غير موجودة.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 رجوع", callback_data="admin_force_sub")
                ]])
            )
    
    async def _show_change_invite_form(self, query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE):
        """عرض نموذج تغيير مكافأة الدعوة"""
        text = (
            "🎁 *تغيير مكافأة الدعوة*\n\n"
            f"المكافأة الحالية: {self.db.settings['points_per_invite']} نقطة\n\n"
            "أرسل القيمة الجديدة (عدد صحيح موجب)."
        )
        
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN)
        context.user_data['state'] = self.conversation_states['CHANGE_INVITE_REWARD']
    
    async def _handle_change_invite_reward(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
        """معالجة تغيير مكافأة الدعوة"""
        try:
            value = int(text)
            if value <= 0:
                await update.message.reply_text("❌ يرجى إرسال قيمة أكبر من 0.")
                return
            
            old_value = self.db.settings['points_per_invite']
            self.db.settings['points_per_invite'] = value
            await self.db._save_data('settings.json', self.db.settings)
            
            await update.message.reply_text(
                f"✅ تم تغيير مكافأة الدعوة من {old_value} إلى {value} نقطة."
            )
            
        except ValueError:
            await update.message.reply_text("❌ يرجى إرسال رقم صحيح.")
        
        context.user_data['state'] = None
    
    async def _show_change_price_form(self, query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE):
        """عرض نموذج تغيير سعر العضو"""
        text = (
            "💵 *تغيير سعر العضو*\n\n"
            f"السعر الحالي: {self.db.settings['points_per_member']} نقطة\n\n"
            "أرسل القيمة الجديدة (عدد صحيح موجب)."
        )
        
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN)
        context.user_data['state'] = self.conversation_states['CHANGE_MEMBER_PRICE']
    
    async def _handle_change_member_price(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
        """معالجة تغيير سعر العضو"""
        try:
            value = int(text)
            if value <= 0:
                await update.message.reply_text("❌ يرجى إرسال قيمة أكبر من 0.")
                return
            
            old_value = self.db.settings['points_per_member']
            self.db.settings['points_per_member'] = value
            await self.db._save_data('settings.json', self.db.settings)
            
            await update.message.reply_text(
                f"✅ تم تغيير سعر العضو من {old_value} إلى {value} نقطة."
            )
            
        except ValueError:
            await update.message.reply_text("❌ يرجى إرسال رقم صحيح.")
        
        context.user_data['state'] = None
    
    async def _show_change_welcome_form(self, query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE):
        """عرض نموذج تغيير رسالة الترحيب"""
        text = (
            "✏️ *تغيير رسالة الترحيب*\n\n"
            f"الرسالة الحالية:\n{self.db.settings['welcome_message']}\n\n"
            "أرسل الرسالة الجديدة."
        )
        
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN)
        context.user_data['state'] = self.conversation_states['CHANGE_WELCOME']
    
    async def _handle_change_welcome(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
        """معالجة تغيير رسالة الترحيب"""
        old_message = self.db.settings['welcome_message']
        self.db.settings['welcome_message'] = text
        await self.db._save_data('settings.json', self.db.settings)
        
        await update.message.reply_text(
            f"✅ تم تغيير رسالة الترحيب بنجاح.\n\n"
            f"الرسالة القديمة: {old_message}\n"
            f"الرسالة الجديدة: {text}"
        )
        
        context.user_data['state'] = None
    
    async def _show_settings_menu(self, query: CallbackQuery):
        """عرض قائمة الإعدادات المتقدمة"""
        text = (
            "⚙️ *الإعدادات المتقدمة*\n\n"
            "اختر الإعداد الذي تريد تعديله:\n\n"
            f"• مكافأة الدعوة: {self.db.settings['points_per_invite']}\n"
            f"• سعر العضو: {self.db.settings['points_per_member']}\n"
            f"• الحد الأدنى للتمويل: {self.db.settings['min_funding_members']}\n"
            f"• الحد الأقصى للتمويل: {self.db.settings['max_funding_members']}\n"
            f"• حد الدعوات اليومي: {self.db.settings['daily_invite_limit']}\n"
            f"• حد التمويل اليومي: {self.db.settings['daily_funding_limit']}\n"
            f"• الاشتراك الإجباري: {'مفعل' if self.db.settings['require_force_sub'] else 'معطل'}\n"
            f"• الإشعارات: {'مفعلة' if self.db.settings['enable_notifications'] else 'معطلة'}\n"
            f"• وضع الصيانة: {'مفعل' if self.db.settings['maintenance_mode'] else 'معطل'}"
        )
        
        keyboard = [
            [InlineKeyboardButton("🎁 تغيير مكافأة الدعوة", callback_data="admin_change_invite")],
            [InlineKeyboardButton("💵 تغيير سعر العضو", callback_data="admin_change_price")],
            [InlineKeyboardButton("📝 تغيير رسالة الترحيب", callback_data="admin_change_welcome")],
            [InlineKeyboardButton("🔄 تفعيل/تعطيل الاشتراك الإجباري", callback_data="toggle_force_sub")],
            [InlineKeyboardButton("🔧 تفعيل/تعطيل وضع الصيانة", callback_data="toggle_maintenance")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel")]
        ]
        
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def _show_broadcast_form(self, query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE):
        """عرض نموذج إرسال رسالة جماعية"""
        text = (
            "📢 *إرسال رسالة جماعية*\n\n"
            "أرسل الرسالة التي تريد إرسالها لجميع المستخدمين.\n\n"
            "يمكنك استخدام:\n"
            "• نص عادي\n"
            "• Markdown للتنسيق\n"
            "• صور وملفات (كرسالة)"
        )
        
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN)
        context.user_data['state'] = self.conversation_states['BROADCAST_MESSAGE']
    
    async def _handle_broadcast(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
        """معالجة إرسال رسالة جماعية"""
        await update.message.reply_text("⏳ جاري إرسال الرسالة للمستخدمين...")
        
        sent = 0
        failed = 0
        
        for user_id_str in self.db.users.keys():
            try:
                await context.bot.send_message(
                    int(user_id_str),
                    f"📢 *رسالة من الإدارة*\n\n{text}"
                )
                sent += 1
                await asyncio.sleep(0.05)  # تجنب سبام
            except:
                failed += 1
        
        await update.message.reply_text(
            f"✅ *تم إرسال الرسالة*\n\n"
            f"✓ تم الإرسال: {sent}\n"
            f"✗ فشل: {failed}\n"
            f"📊 الإجمالي: {sent + failed}"
        )
        
        context.user_data['state'] = None
    
    async def _show_vip_menu(self, query: CallbackQuery):
        """عرض قائمة إدارة VIP"""
        vip_users = []
        for user_id_str, user_data in self.db.users.items():
            if user_data.get('role') == UserRole.VIP_USER.value:
                vip_users.append(f"• {user_data.get('username', 'بدون اسم')} (`{user_id_str}`)")
        
        text = "👑 *إدارة المستخدمين VIP*\n\n"
        
        if vip_users:
            text += "المستخدمين VIP حالياً:\n" + "\n".join(vip_users[:10])
            if len(vip_users) > 10:
                text += f"\n... و {len(vip_users) - 10} آخرين"
        else:
            text += "لا يوجد مستخدمين VIP حالياً."
        
        keyboard = [
            [InlineKeyboardButton("➕ إضافة VIP", callback_data="admin_add_vip")],
            [InlineKeyboardButton("❌ حذف VIP", callback_data="admin_remove_vip")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel")]
        ]
        
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def _show_add_vip_form(self, query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE):
        """عرض نموذج إضافة VIP"""
        text = "👑 *إضافة مستخدم VIP*\n\nأرسل ايدي المستخدم."
        
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN)
        context.user_data['state'] = self.conversation_states['ADD_VIP_USER']
    
    async def _show_remove_vip_form(self, query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE):
        """عرض نموذج حذف VIP"""
        text = "👑 *حذف مستخدم VIP*\n\nأرسل ايدي المستخدم."
        
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN)
        context.user_data['state'] = self.conversation_states['REMOVE_VIP_USER']
    
    async def _handle_backup(self, query: CallbackQuery):
        """معالجة إنشاء نسخة احتياطية"""
        await query.edit_message_text("⏳ جاري إنشاء النسخة الاحتياطية...")
        
        try:
            backup_path = await self.db.create_backup()
            
            # إنشاء ملف مضغوط
            zip_path = os.path.join(TEMP_DIR, f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip")
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, _, files in os.walk(backup_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, backup_path)
                        zipf.write(file_path, arcname)
            
            # إرسال الملف
            with open(zip_path, 'rb') as f:
                await query.message.reply_document(
                    document=f,
                    filename=os.path.basename(zip_path),
                    caption=f"✅ تم إنشاء النسخة الاحتياطية بنجاح\n📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                )
            
            # تنظيف الملفات المؤقتة
            os.remove(zip_path)
            
        except Exception as e:
            await query.edit_message_text(f"❌ خطأ في إنشاء النسخة الاحتياطية: {e}")
    
    async def _show_restore_menu(self, query: CallbackQuery):
        """عرض قائمة استعادة النسخ الاحتياطية"""
        backups = []
        for item in os.listdir(BACKUP_DIR):
            if item.startswith('backup_') and os.path.isdir(os.path.join(BACKUP_DIR, item)):
                backup_id = item.replace('backup_', '')
                backups.append(backup_id)
        
        if not backups:
            await query.edit_message_text(
                "📂 لا توجد نسخ احتياطية متاحة.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel")
                ]])
            )
            return
        
        text = "🔄 *استعادة نسخة احتياطية*\n\nاختر النسخة التي تريد استعادتها:\n\n"
        keyboard = []
        
        for backup_id in sorted(backups, reverse=True)[:10]:
            backup_path = os.path.join(BACKUP_DIR, f"backup_{backup_id}")
            info_path = os.path.join(backup_path, 'backup_info.json')
            
            if os.path.exists(info_path):
                with open(info_path, 'r', encoding='utf-8') as f:
                    info = json.load(f)
                created = info.get('created_at', 'غير معروف')[:16]
            else:
                created = backup_id[:10] + ' ' + backup_id[11:16]
            
            text += f"• `{backup_id}` - {created}\n"
            keyboard.append([InlineKeyboardButton(
                f"🔄 استعادة {backup_id[:8]}...", 
                callback_data=f"restore_{backup_id}"
            )])
        
        keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel")])
        
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def _handle_restore(self, query: CallbackQuery, data: str):
        """معالجة استعادة نسخة احتياطية"""
        backup_id = data.replace('restore_', '')
        
        await query.edit_message_text("⏳ جاري استعادة النسخة الاحتياطية...")
        
        try:
            success = await self.db.restore_backup(backup_id)
            
            if success:
                await query.edit_message_text(
                    f"✅ تم استعادة النسخة الاحتياطية {backup_id} بنجاح.\n\n"
                    "🔄 يرجى إعادة تشغيل البوت لتطبيق التغييرات.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel")
                    ]])
                )
            else:
                await query.edit_message_text(
                    f"❌ فشل استعادة النسخة الاحتياطية.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel")
                    ]])
                )
                
        except Exception as e:
            await query.edit_message_text(f"❌ خطأ في الاستعادة: {e}")
    
    async def _show_funding_details(self, query: CallbackQuery, data: str):
        """عرض تفاصيل طلب تمويل"""
        request_id = data.replace('view_funding_', '')
        request = await self.db.get_funding_request(request_id)
        
        if not request:
            await query.edit_message_text("❌ طلب التمويل غير موجود.")
            return
        
        status_emoji = {
            FundingStatus.PENDING.value: "⏳",
            FundingStatus.PROCESSING.value: "⚙️",
            FundingStatus.COMPLETED.value: "✅",
            FundingStatus.FAILED.value: "❌",
            FundingStatus.CANCELLED.value: "🚫"
        }.get(request.status, "❓")
        
        created = datetime.fromisoformat(request.created_at)
        
        text = (
            f"{status_emoji} *تفاصيل طلب التمويل*\n\n"
            f"🆔 *المعرف:* `{request_id[:8]}...`\n"
            f"👤 *المستخدم:* {request.user_id}\n"
            f"📢 *القناة:* {request.chat_title}\n"
            f"🔗 *الرابط:* {request.chat_link}\n"
            f"📊 *النوع:* {request.chat_type}\n\n"
            f"👥 *الأعضاء المطلوبة:* {request.members_count}\n"
            f"➕ *الأعضاء المضافة:* {request.added_members}\n"
            f"❌ *الأعضاء الفاشلة:* {request.failed_members}\n"
            f"💰 *التكلفة:* {request.cost}\n"
            f"📊 *الحالة:* {request.status}\n\n"
            f"📅 *تاريخ الإنشاء:* {created.strftime('%Y-%m-%d %H:%M')}\n"
            f"🕐 *آخر تحديث:* {request.last_update[:16] if request.last_update else 'لم يحدث'}"
        )
        
        if request.status == FundingStatus.PENDING.value:
            keyboard = [
                [InlineKeyboardButton("✅ موافقة", callback_data=f"approve_funding_{request_id}"),
                 InlineKeyboardButton("❌ رفض", callback_data=f"cancel_funding_{request_id}")],
                [InlineKeyboardButton("🔒 حظر المستخدم", callback_data=f"ban_user_{request.user_id}")],
                [InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel")]
            ]
        elif request.status == FundingStatus.PROCESSING.value:
            keyboard = [
                [InlineKeyboardButton("⏸️ إيقاف مؤقت", callback_data=f"pause_funding_{request_id}")],
                [InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel")]
            ]
        else:
            keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel")]]
        
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def _handle_cancel_funding(self, query: CallbackQuery, data: str):
        """معالجة إلغاء طلب تمويل"""
        request_id = data.replace('cancel_funding_', '')
        request = await self.db.get_funding_request(request_id)
        
        if not request:
            await query.edit_message_text("❌ طلب التمويل غير موجود.")
            return
        
        # تحديث الحالة
        request.status = FundingStatus.CANCELLED.value
        request.cancelled_at = datetime.now().isoformat()
        request.cancelled_by = query.from_user.id
        await self.db.save_funding_request(request)
        
        # إرجاع النقاط
        await self.db.update_user_points(
            request.user_id,
            request.cost,
            "استرداد نقاط بسبب إلغاء التمويل"
        )
        
        # إشعار المستخدم
        try:
            await context.bot.send_message(
                request.user_id,
                f"❌ *تم إلغاء طلب التمويل*\n\n"
                f"🆔 المعرف: `{request_id[:8]}...`\n"
                f"💰 تم إرجاع {request.cost} نقطة إلى رصيدك."
            )
        except:
            pass
        
        await query.edit_message_text(
            f"✅ تم إلغاء التمويل {request_id[:8]}... بنجاح.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel")
            ]])
        )
    
    async def _handle_approve_funding(self, query: CallbackQuery, data: str):
        """معالجة الموافقة على طلب تمويل"""
        request_id = data.replace('approve_funding_', '')
        request = await self.db.get_funding_request(request_id)
        
        if not request:
            await query.edit_message_text("❌ طلب التمويل غير موجود.")
            return
        
        # تحديث الحالة
        request.status = FundingStatus.PROCESSING.value
        request.approved_by = query.from_user.id
        request.approved_at = datetime.now().isoformat()
        await self.db.save_funding_request(request)
        
        await query.edit_message_text(
            f"✅ تمت الموافقة على التمويل {request_id[:8]}...\n"
            "سيبدأ التمويل قريباً.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel")
            ]])
        )
        
        # بدء التمويل
        asyncio.create_task(self._process_funding(request_id, self.application.context_types.context()))
    
    async def _handle_pause_funding(self, query: CallbackQuery, data: str):
        """معالجة إيقاف تمويل مؤقت"""
        request_id = data.replace('pause_funding_', '')
        request = await self.db.get_funding_request(request_id)
        
        if not request:
            await query.edit_message_text("❌ طلب التمويل غير موجود.")
            return
        
        request.status = FundingStatus.PAUSED.value
        await self.db.save_funding_request(request)
        
        await query.edit_message_text(
            f"⏸️ تم إيقاف التمويل {request_id[:8]}... مؤقتاً.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel")
            ]])
        )
    
    async def _handle_resume_funding(self, query: CallbackQuery, data: str):
        """معالجة استئناف تمويل"""
        request_id = data.replace('resume_funding_', '')
        request = await self.db.get_funding_request(request_id)
        
        if not request:
            await query.edit_message_text("❌ طلب التمويل غير موجود.")
            return
        
        request.status = FundingStatus.PROCESSING.value
        await self.db.save_funding_request(request)
        
        await query.edit_message_text(
            f"▶️ تم استئناف التمويل {request_id[:8]}...",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel")
            ]])
        )
    
    async def _notify_admins_new_funding(self, request: FundingRequest, context: ContextTypes.DEFAULT_TYPE):
        """إشعار المدراء بطلب تمويل جديد"""
        for admin_id in self.admin_ids:
            try:
                keyboard = InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔍 عرض التفاصيل", callback_data=f"view_funding_{request.request_id}")
                ]])
                
                await context.bot.send_message(
                    admin_id,
                    f"📢 *طلب تمويل جديد*\n\n"
                    f"👤 المستخدم: {request.user_id}\n"
                    f"📢 القناة: {request.chat_title}\n"
                    f"👥 عدد الأعضاء: {request.members_count}\n"
                    f"💰 التكلفة: {request.cost}\n"
                    f"🆔 المعرف: `{request.request_id[:8]}...`",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=keyboard
                )
            except:
                pass
    
    async def _notify_admins_funding_complete(self, request: FundingRequest, context: ContextTypes.DEFAULT_TYPE):
        """إشعار المدراء باكتمال التمويل"""
        for admin_id in self.admin_ids:
            try:
                await context.bot.send_message(
                    admin_id,
                    f"✅ *اكتمال تمويل*\n\n"
                    f"👤 المستخدم: {request.user_id}\n"
                    f"📢 القناة: {request.chat_title}\n"
                    f"👥 الأعضاء المضافة: {request.added_members}/{request.members_count}\n"
                    f"🆔 المعرف: `{request.request_id[:8]}...`",
                    parse_mode=ParseMode.MARKDOWN
                )
            except:
                pass
    
    async def _notify_admins_funding_failed(self, request: FundingRequest, context: ContextTypes.DEFAULT_TYPE, reason: str):
        """إشعار المدراء بفشل التمويل"""
        for admin_id in self.admin_ids:
            try:
                await context.bot.send_message(
                    admin_id,
                    f"❌ *فشل تمويل*\n\n"
                    f"👤 المستخدم: {request.user_id}\n"
                    f"📢 القناة: {request.chat_title}\n"
                    f"📊 السبب: {reason}\n"
                    f"🆔 المعرف: `{request.request_id[:8]}...`",
                    parse_mode=ParseMode.MARKDOWN
                )
            except:
                pass
    
    async def _background_tasks(self):
        """المهام الخلفية"""
        while self.is_running:
            try:
                # تحديث الإحصائيات كل ساعة
                await asyncio.sleep(3600)
                await self.db.update_stats()
                
                # إنشاء نسخة احتياطية تلقائية
                if self.db.settings.get('auto_backup'):
                    last_backup = self.db.stats.get('last_backup')
                    if last_backup:
                        last = datetime.fromisoformat(last_backup)
                        hours_since = (datetime.now() - last).total_seconds() / 3600
                        if hours_since >= self.db.settings['backup_interval_hours']:
                            await self.db.create_backup()
                
            except Exception as e:
                logger.error(f"❌ خطأ في المهام الخلفية: {e}")
                await asyncio.sleep(60)

# ==================== الدالة الرئيسية ====================

async def main():
    """الدالة الرئيسية"""
    bot = None
    
    try:
        # عرض شاشة البداية
        print(f"""
{Fore.CYAN}╔════════════════════════════════════════════════════════════╗
{Fore.CYAN}║                                                            ║
{Fore.CYAN}║     {Fore.YELLOW}████████╗███╗   ███╗██████╗ ██╗██╗     {Fore.CYAN}           ║
{Fore.CYAN}║     {Fore.YELLOW}╚══██╔══╝████╗ ████║██╔══██╗██║██║     {Fore.CYAN}           ║
{Fore.CYAN}║        {Fore.YELLOW}██║   ██╔████╔██║██████╔╝██║██║     {Fore.CYAN}           ║
{Fore.CYAN}║        {Fore.YELLOW}██║   ██║╚██╔╝██║██╔══██╗██║██║     {Fore.CYAN}           ║
{Fore.CYAN}║        {Fore.YELLOW}██║   ██║ ╚═╝ ██║██████╔╝██║███████╗{Fore.CYAN}           ║
{Fore.CYAN}║        {Fore.YELLOW}╚═╝   ╚═╝     ╚═╝╚═════╝ ╚═╝╚══════╝{Fore.CYAN}           ║
{Fore.CYAN}║                                                            ║
{Fore.CYAN}║              {Fore.GREEN}بوت تمويل متكامل v{BOT_VERSION}{Fore.CYAN}                    ║
{Fore.CYAN}║              {Fore.WHITE}تم التطوير بواسطة: مطور البوت{Fore.CYAN}                  ║
{Fore.CYAN}║                                                            ║
{Fore.CYAN}╚════════════════════════════════════════════════════════════╝{Style.RESET_ALL}
        """)
        
        # إنشاء وتشغيل البوت
        bot = FundingBot()
        
        # معالجة إشارات الإيقاف
        loop = asyncio.get_running_loop()
        
        def stop_handler():
            asyncio.create_task(bot.stop())
        
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, stop_handler)
        
        # بدء البوت
        await bot.start()
        
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}⚠️ تم إيقاف البوت بواسطة المستخدم{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}❌ خطأ غير متوقع: {e}{Style.RESET_ALL}")
        traceback.print_exc()
    finally:
        if bot:
            await bot.stop()
        print(f"{Fore.GREEN}👋 وداعاً...{Style.RESET_ALL}")

# ==================== نقطة الدخول ====================

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}⚠️ تم إيقاف البوت{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}❌ خطأ فادح: {e}{Style.RESET_ALL}")
        traceback.print_exc()
