#!/usr/bin/env python3
# ================================================================
# ANICOMPLEX RASMIY BOT v8.0.0
# ================================================================

import asyncio
import logging
import os
import sys
import re
import json
import threading
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Union, Tuple
from http.server import HTTPServer, SimpleHTTPRequestHandler

try:
    from dotenv import load_dotenv
    import aiosqlite
    from aiogram import Bot, Dispatcher, types, F, BaseMiddleware
    from aiogram.client.default import DefaultBotProperties
    from aiogram.enums import ParseMode, ChatMemberStatus, ChatType
    from aiogram.filters import Command
    from aiogram.types import (
        Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton,
        ReplyKeyboardMarkup, KeyboardButton, InputMediaPhoto,
        WebAppInfo, MenuButtonWebApp
    )
    from aiogram.fsm.context import FSMContext
    from aiogram.fsm.state import StatesGroup, State
    from aiogram.fsm.storage.memory import MemoryStorage
    from aiogram.utils.keyboard import InlineKeyboardBuilder
except ImportError as e:
    print(f"❌ Import xatosi: {e}")
    print("Iltimos, quyidagi buyruq bilan kutubxonalarni o'rniting:")
    print("pip install aiogram aiosqlite python-dotenv")
    sys.exit(1)

load_dotenv()

# ================= KONFIGURATSIYA =================
BOT_TOKEN = os.getenv("BOT_TOKEN", "8331186676:AAFXLtBCy96UZ0VjVyL-KRUzzPzSLknjKlQ")
ADMINS_STR = os.getenv("ADMINS", "5675087151,8404514882")
ADMINS = [int(x.strip()) for x in ADMINS_STR.split(",") if x.strip().isdigit()]
MAIN_CHANNEL = os.getenv("MAIN_CHANNEL", "@AniComplex_Rasmiy")
POST_CHANNEL = os.getenv("POST_CHANNEL", "@AniComplex_Rasmiy")
AUTHOR_LINK = "https://t.me/AniComplexVIP"
AUTHOR_USERNAME = "@AniComplexVIP"
SUPPORT_LINK = "https://t.me/mirfayz_prime2"
SUPPORT_USERNAME = "@mirfayz_prime2"

# ✅ TUZATILGAN: VIP_PRICE
VIP_PRICE_STR = os.getenv("VIP_PRICE", "50000")
try:
    VIP_PRICE = int(VIP_PRICE_STR) if VIP_PRICE_STR.isdigit() else 50000
except:
    VIP_PRICE = 50000

PHONE_NUMBER_1 = os.getenv("PHONE_NUMBER_1", "+998938138110")
PHONE_NUMBER_2 = os.getenv("PHONE_NUMBER_2", "+998500741888")
CARD_NUMBER = os.getenv("CARD_NUMBER", "yoq")
BOT_VERSION = "8.0.0"
BOT_USERNAME = os.getenv("BOT_USERNAME", "@AniComplex_Rasmiy_bot")

# Mini App sozlamalari
MINI_APP_PORT = int(os.getenv("MINI_APP_PORT", "8080"))
MINI_APP_HOST = os.getenv("MINI_APP_HOST", "0.0.0.0")
MINI_APP_URL = os.getenv("MINI_APP_URL", "https://anime-bot-zxh9.onrender.com")

# ================= LOGGING =================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ================= BOT VA DISPATCHER =================
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# ================= DATABASE =================
DB_NAME = 'anime_bot.db'

class Database:
    def __init__(self):
        self.conn = None
    
    async def connect(self):
        self.conn = await aiosqlite.connect(DB_NAME)
        self.conn.row_factory = aiosqlite.Row
        await self._init_tables()
        await self._migrate_tables()
        logger.info("✅ Database connected")
    
    async def _init_tables(self):
        # Media table
        await self.conn.execute('''
        CREATE TABLE IF NOT EXISTS media (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code INTEGER UNIQUE NOT NULL,
            name TEXT UNIQUE NOT NULL,
            genre TEXT, status TEXT DEFAULT 'ongoing',
            total_parts INTEGER DEFAULT 0, views INTEGER DEFAULT 0,
            rating REAL DEFAULT 0, rating_count INTEGER DEFAULT 0,
            is_vip INTEGER DEFAULT 0, image_url TEXT,
            description TEXT, voice TEXT, quality TEXT DEFAULT '720p',
            release_year INTEGER, created_at TEXT, updated_at TEXT,
            post_message_id INTEGER, post_channel TEXT
        )''')
        
        # Parts table
        await self.conn.execute('''
        CREATE TABLE IF NOT EXISTS parts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            media_id INTEGER, part_number INTEGER,
            file_id TEXT, caption TEXT, is_vip INTEGER DEFAULT 0,
            duration INTEGER DEFAULT 0, file_size INTEGER DEFAULT 0,
            views INTEGER DEFAULT 0, created_at TEXT,
            post_message_id INTEGER, post_channel TEXT,
            FOREIGN KEY (media_id) REFERENCES media (id) ON DELETE CASCADE
        )''')
        
        # Users table
        await self.conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY, username TEXT,
            first_name TEXT, last_name TEXT, phone TEXT,
            is_vip INTEGER DEFAULT 0, vip_expiry TEXT,
            is_blocked INTEGER DEFAULT 0, language TEXT DEFAULT 'uz',
            registered_at TEXT, last_active TEXT, total_views INTEGER DEFAULT 0,
            is_subscribed INTEGER DEFAULT 0
        )''')
        
        # Admins table
        await self.conn.execute('''CREATE TABLE IF NOT EXISTS admins (user_id INTEGER PRIMARY KEY, added_by INTEGER, added_at TEXT, permissions TEXT DEFAULT 'all')''')
        
        # Favorites table
        await self.conn.execute('''CREATE TABLE IF NOT EXISTS favorites (user_id INTEGER, media_id INTEGER, added_at TEXT, PRIMARY KEY (user_id, media_id))''')
        
        # Notifications table
        await self.conn.execute('''CREATE TABLE IF NOT EXISTS notifications (user_id INTEGER, media_id INTEGER, media_name TEXT, is_active INTEGER DEFAULT 1, created_at TEXT, PRIMARY KEY (user_id, media_id))''')
        
        # VIP requests table
        await self.conn.execute('''CREATE TABLE IF NOT EXISTS vip_requests (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, phone_number TEXT, amount INTEGER, payment_proof TEXT, status TEXT DEFAULT 'pending', created_at TEXT, processed_at TEXT, processed_by INTEGER)''')
        
        # Forced channels table
        await self.conn.execute('''CREATE TABLE IF NOT EXISTS forced_channels (id INTEGER PRIMARY KEY AUTOINCREMENT, channel_username TEXT UNIQUE, channel_link TEXT, is_active INTEGER DEFAULT 1, added_at TEXT, added_by INTEGER)''')
        
        # Ratings table
        await self.conn.execute('''CREATE TABLE IF NOT EXISTS ratings (user_id INTEGER, media_id INTEGER, rating INTEGER, created_at TEXT, PRIMARY KEY (user_id, media_id))''')
        
        # Watch history table
        await self.conn.execute('''CREATE TABLE IF NOT EXISTS watch_history (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, media_id INTEGER, part_number INTEGER, watched_at TEXT)''')
        
        # Referrals table
        await self.conn.execute('''CREATE TABLE IF NOT EXISTS referrals (id INTEGER PRIMARY KEY AUTOINCREMENT, referrer_id INTEGER, referred_id INTEGER, is_rewarded INTEGER DEFAULT 0, created_at TEXT)''')
        
        # Daily stats table
        await self.conn.execute('''CREATE TABLE IF NOT EXISTS daily_stats (date TEXT PRIMARY KEY, new_users INTEGER DEFAULT 0, active_users INTEGER DEFAULT 0, total_views INTEGER DEFAULT 0, new_media INTEGER DEFAULT 0)''')
        
        # Reports table
        await self.conn.execute('''CREATE TABLE IF NOT EXISTS reports (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, media_id INTEGER, reason TEXT, status TEXT DEFAULT 'pending', created_at TEXT)''')
        
        # Multi part sessions table
        await self.conn.execute('''CREATE TABLE IF NOT EXISTS multi_part_sessions (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, media_id INTEGER, media_name TEXT, parts_data TEXT, total_parts INTEGER DEFAULT 0, created_at TEXT)''')
        
        # Suggestions table
        await self.conn.execute('''CREATE TABLE IF NOT EXISTS suggestions (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, suggestion TEXT, status TEXT DEFAULT 'pending', created_at TEXT, responded_at TEXT)''')
        
        # Groups table
        await self.conn.execute('''CREATE TABLE IF NOT EXISTS groups (id INTEGER PRIMARY KEY, title TEXT, username TEXT, added_by INTEGER, added_at TEXT, is_active INTEGER DEFAULT 1)''')
        
        # Likes table
        await self.conn.execute('''CREATE TABLE IF NOT EXISTS likes (user_id INTEGER, media_id INTEGER, created_at TEXT, PRIMARY KEY (user_id, media_id))''')
        
        # Comments table
        await self.conn.execute('''CREATE TABLE IF NOT EXISTS comments (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, media_id INTEGER, username TEXT, text TEXT, created_at TEXT)''')
        
        # Mini app users table
        await self.conn.execute('''CREATE TABLE IF NOT EXISTS mini_app_users (id INTEGER PRIMARY KEY, first_name TEXT, last_name TEXT, username TEXT, registered_at TEXT)''')
        
        await self.conn.commit()
        
        # Create indexes
        try: await self.conn.execute('CREATE INDEX IF NOT EXISTS idx_media_code ON media(code)')
        except: pass
        try: await self.conn.execute('CREATE INDEX IF NOT EXISTS idx_media_name ON media(name)')
        except: pass
        try: await self.conn.execute('CREATE INDEX IF NOT EXISTS idx_parts_media ON parts(media_id)')
        except: pass
        
        await self.conn.commit()
        
        # Default admins
        now = datetime.now().isoformat()
        for admin_id in ADMINS:
            await self.conn.execute("INSERT OR IGNORE INTO admins (user_id, added_by, added_at) VALUES (?,?,?)", (admin_id, admin_id, now))
        await self.conn.commit()
        
        # Daily stats
        today = datetime.now().strftime("%Y-%m-%d")
        await self.conn.execute("INSERT OR IGNORE INTO daily_stats (date) VALUES (?)", (today,))
        await self.conn.commit()
        
        logger.info("✅ All tables created")
    
    async def _migrate_tables(self):
        """Yo'q ustunlarni qo'shish"""
        migrations = {
            'media': {'rating': 'REAL DEFAULT 0', 'rating_count': 'INTEGER DEFAULT 0', 'release_year': 'INTEGER', 'post_message_id': 'INTEGER', 'post_channel': 'TEXT', 'updated_at': 'TEXT'},
            'parts': {'duration': 'INTEGER DEFAULT 0', 'file_size': 'INTEGER DEFAULT 0', 'post_message_id': 'INTEGER', 'post_channel': 'TEXT', 'views': 'INTEGER DEFAULT 0'},
            'users': {'is_vip': 'INTEGER DEFAULT 0', 'vip_expiry': 'TEXT', 'total_views': 'INTEGER DEFAULT 0', 'phone': 'TEXT', 'is_blocked': 'INTEGER DEFAULT 0', 'is_subscribed': 'INTEGER DEFAULT 0'},
            'vip_requests': {'processed_at': 'TEXT', 'processed_by': 'INTEGER'},
            'referrals': {'is_rewarded': 'INTEGER DEFAULT 0'},
            'forced_channels': {'added_by': 'INTEGER', 'added_at': 'TEXT'},
            'suggestions': {'responded_at': 'TEXT'},
            'multi_part_sessions': {'user_id': 'INTEGER', 'media_id': 'INTEGER', 'media_name': 'TEXT', 'parts_data': 'TEXT', 'total_parts': 'INTEGER DEFAULT 0', 'created_at': 'TEXT'},
            'groups': {'title': 'TEXT', 'username': 'TEXT', 'added_by': 'INTEGER', 'added_at': 'TEXT', 'is_active': 'INTEGER DEFAULT 1'},
        }
        
        for table, columns in migrations.items():
            for col, col_type in columns.items():
                try:
                    await self.conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_type}")
                except:
                    pass
        await self.conn.commit()
    
    async def add_user(self, uid, username="", first_name="", last_name=""):
        now = datetime.now().isoformat()
        await self.conn.execute("INSERT OR IGNORE INTO users (id,username,first_name,last_name,registered_at,last_active) VALUES(?,?,?,?,?,?)", 
                               (uid, username, first_name, last_name, now, now))
        await self.conn.commit()
        today = datetime.now().strftime("%Y-%m-%d")
        await self.conn.execute("UPDATE daily_stats SET new_users=new_users+1 WHERE date=?", (today,))
        await self.conn.commit()
    
    async def update_activity(self, uid):
        await self.conn.execute("UPDATE users SET last_active=? WHERE id=?", (datetime.now().isoformat(), uid))
        await self.conn.commit()
    
    async def get_user(self, uid):
        async with self.conn.execute("SELECT * FROM users WHERE id=?", (uid,)) as c:
            return await c.fetchone()
    
    async def get_all_users(self, only_active=False):
        q = "SELECT id FROM users WHERE is_blocked=0" if only_active else "SELECT id FROM users"
        async with self.conn.execute(q) as c:
            return await c.fetchall()
    
    async def get_user_count(self):
        async with self.conn.execute("SELECT COUNT(*) FROM users WHERE is_blocked=0") as c:
            row = await c.fetchone()
            return row[0] if row else 0
    
    async def is_admin(self, uid):
        async with self.conn.execute("SELECT 1 FROM admins WHERE user_id=?", (uid,)) as c:
            return await c.fetchone() is not None or uid in ADMINS
    
    async def is_owner(self, uid):
        return uid in ADMINS
    
    async def add_admin(self, uid, added_by):
        now = datetime.now().isoformat()
        await self.conn.execute("INSERT OR IGNORE INTO admins (user_id,added_by,added_at) VALUES(?,?,?)", (uid, added_by, now))
        await self.conn.commit()
    
    async def remove_admin(self, uid):
        if uid not in ADMINS:
            await self.conn.execute("DELETE FROM admins WHERE user_id=?", (uid,))
            await self.conn.commit()
            return True
        return False
    
    async def get_admin_count(self):
        async with self.conn.execute("SELECT COUNT(*) FROM admins") as c:
            row = await c.fetchone()
            return row[0] if row else 0
    
    async def is_vip(self, uid):
        async with self.conn.execute("SELECT is_vip,vip_expiry FROM users WHERE id=?", (uid,)) as c:
            row = await c.fetchone()
            if not row or row["is_vip"] != 1:
                return False
            if row["vip_expiry"]:
                try:
                    if datetime.fromisoformat(row["vip_expiry"]) > datetime.now():
                        return True
                    await self.conn.execute("UPDATE users SET is_vip=0,vip_expiry=NULL WHERE id=?", (uid,))
                    await self.conn.commit()
                except:
                    return True
            return True
    
    async def set_vip(self, uid, days=30):
        expiry = (datetime.now() + timedelta(days=days)).isoformat()
        await self.conn.execute("UPDATE users SET is_vip=1,vip_expiry=? WHERE id=?", (expiry, uid))
        await self.conn.commit()
    
    async def remove_vip(self, uid):
        await self.conn.execute("UPDATE users SET is_vip=0,vip_expiry=NULL WHERE id=?", (uid,))
        await self.conn.commit()
    
    async def get_vip_count(self):
        async with self.conn.execute("SELECT COUNT(*) FROM users WHERE is_vip=1") as c:
            row = await c.fetchone()
            return row[0] if row else 0
    
    async def check_all_vip_expiry(self):
        await self.conn.execute("UPDATE users SET is_vip=0,vip_expiry=NULL WHERE is_vip=1 AND vip_expiry<?", 
                               (datetime.now().isoformat(),))
        await self.conn.commit()
    
    async def add_vip_request(self, uid, phone, amount, proof=""):
        now = datetime.now().isoformat()
        await self.conn.execute("INSERT INTO vip_requests (user_id,phone_number,amount,payment_proof,status,created_at) VALUES(?,?,?,?,'pending',?)", 
                               (uid, phone, amount, proof, now))
        await self.conn.commit()
        return await self.get_last_insert_id()
    
    async def get_vip_requests(self, status="pending"):
        async with self.conn.execute("SELECT * FROM vip_requests WHERE status=? ORDER BY created_at DESC", (status,)) as c:
            return await c.fetchall()
    
    async def get_vip_request(self, rid):
        async with self.conn.execute("SELECT * FROM vip_requests WHERE id=?", (rid,)) as c:
            return await c.fetchone()
    
    async def update_vip_request(self, rid, status, processed_by):
        now = datetime.now().isoformat()
        await self.conn.execute("UPDATE vip_requests SET status=?,processed_at=?,processed_by=? WHERE id=?", 
                               (status, now, processed_by, rid))
        await self.conn.commit()
    
    async def add_media(self, code, name, genre, image_url="", description="", voice="", quality="720p", release_year=None, is_vip=False):
        if await self.fetch_one("SELECT id FROM media WHERE code=?", (code,)):
            return False, "Bu kod mavjud!"
        if await self.fetch_one("SELECT id FROM media WHERE name=?", (name,)):
            return False, "Bu nom mavjud!"
        now = datetime.now().isoformat()
        await self.conn.execute('''INSERT INTO media (code,name,genre,image_url,description,voice,quality,release_year,is_vip,created_at,updated_at) 
                                 VALUES(?,?,?,?,?,?,?,?,?,?,?)''', 
                               (code, name, genre, image_url, description, voice, quality, release_year, 1 if is_vip else 0, now, now))
        await self.conn.commit()
        today = datetime.now().strftime("%Y-%m-%d")
        await self.conn.execute("UPDATE daily_stats SET new_media=new_media+1 WHERE date=?", (today,))
        await self.conn.commit()
        return True, await self.get_last_insert_id()
    
    async def get_media_by_code(self, code):
        async with self.conn.execute("SELECT * FROM media WHERE code=?", (code,)) as c:
            return await c.fetchone()
    
    async def get_media_by_id(self, mid):
        async with self.conn.execute("SELECT * FROM media WHERE id=?", (mid,)) as c:
            return await c.fetchone()
    
    async def search_media(self, query):
        async with self.conn.execute("SELECT * FROM media WHERE name LIKE ? ORDER BY name", (f"%{query}%",)) as c:
            return await c.fetchall()
    
    async def get_all_media(self, user_is_vip=False):
        q = "SELECT id,name,code,total_parts,status,is_vip,views,rating,image_url FROM media"
        if not user_is_vip:
            q += " WHERE is_vip=0"
        async with self.conn.execute(q + " ORDER BY name") as c:
            return await c.fetchall()
    
    async def get_ongoing_media(self, user_is_vip=False):
        q = "SELECT id,name,code,total_parts,views,rating FROM media WHERE status='ongoing'"
        if not user_is_vip:
            q += " AND is_vip=0"
        async with self.conn.execute(q + " ORDER BY name") as c:
            return await c.fetchall()
    
    async def get_completed_media(self, user_is_vip=False):
        q = "SELECT id,name,code,total_parts,views,rating FROM media WHERE status='completed'"
        if not user_is_vip:
            q += " AND is_vip=0"
        async with self.conn.execute(q + " ORDER BY name") as c:
            return await c.fetchall()
    
    async def get_most_viewed(self, limit=10, user_is_vip=False):
        q = "SELECT id,name,code,views,is_vip,rating,image_url FROM media"
        if not user_is_vip:
            q += " WHERE is_vip=0"
        async with self.conn.execute(q + " ORDER BY views DESC LIMIT ?", (limit,)) as c:
            return await c.fetchall()
    
    async def get_highest_rated(self, limit=10, user_is_vip=False):
        q = "SELECT id,name,code,rating,rating_count,is_vip,image_url FROM media WHERE rating_count>0"
        if not user_is_vip:
            q += " AND is_vip=0"
        async with self.conn.execute(q + " ORDER BY rating DESC LIMIT ?", (limit,)) as c:
            return await c.fetchall()
    
    async def get_recent_media(self, limit=10, user_is_vip=False):
        q = "SELECT id,name,code,created_at,is_vip,image_url FROM media"
        if not user_is_vip:
            q += " WHERE is_vip=0"
        async with self.conn.execute(q + " ORDER BY created_at DESC LIMIT ?", (limit,)) as c:
            return await c.fetchall()
    
    async def get_random_media(self, user_is_vip=False):
        q = "SELECT id,name,code,image_url FROM media"
        if not user_is_vip:
            q += " WHERE is_vip=0"
        async with self.conn.execute(q + " ORDER BY RANDOM() LIMIT 1") as c:
            return await c.fetchone()
    
    async def get_media_by_genre(self, genre, user_is_vip=False):
        q = "SELECT id,name,code,total_parts,status,is_vip,views,rating,image_url FROM media WHERE genre LIKE ?"
        if not user_is_vip:
            q += " AND is_vip=0"
        async with self.conn.execute(q + " ORDER BY name", (f"%{genre}%",)) as c:
            return await c.fetchall()
    
    async def get_all_genres(self):
        async with self.conn.execute("SELECT DISTINCT genre FROM media WHERE genre!='' AND genre IS NOT NULL") as c:
            rows = await c.fetchall()
            genres = set()
            for row in rows:
                if row["genre"]:
                    for g in row["genre"].split(","):
                        if g.strip():
                            genres.add(g.strip())
            return sorted(list(genres))
    
    async def update_media(self, mid, field, value):
        now = datetime.now().isoformat()
        await self.conn.execute(f"UPDATE media SET {field}=?,updated_at=? WHERE id=?", (value, now, mid))
        await self.conn.commit()
    
    async def update_media_post_info(self, mid, msg_id, channel):
        await self.conn.execute("UPDATE media SET post_message_id=?,post_channel=? WHERE id=?", (msg_id, channel, mid))
        await self.conn.commit()
    
    async def delete_media(self, mid):
        for t in ['parts','favorites','notifications','ratings','watch_history','reports','likes','comments']:
            await self.conn.execute(f"DELETE FROM {t} WHERE media_id=?", (mid,))
        await self.conn.execute("DELETE FROM media WHERE id=?", (mid,))
        await self.conn.commit()
    
    async def increment_views(self, mid):
        await self.conn.execute("UPDATE media SET views=views+1 WHERE id=?", (mid,))
        await self.conn.commit()
        today = datetime.now().strftime("%Y-%m-%d")
        await self.conn.execute("UPDATE daily_stats SET total_views=total_views+1 WHERE date=?", (today,))
        await self.conn.commit()
    
    async def get_media_count(self):
        async with self.conn.execute("SELECT COUNT(*) FROM media") as c:
            row = await c.fetchone()
            return row[0] if row else 0
    
    async def get_ongoing_count(self):
        async with self.conn.execute("SELECT COUNT(*) FROM media WHERE status='ongoing'") as c:
            row = await c.fetchone()
            return row[0] if row else 0
    
    async def add_part(self, mid, pnum, file_id, caption="", is_vip=False, duration=0, file_size=0):
        now = datetime.now().isoformat()
        await self.conn.execute("INSERT INTO parts (media_id,part_number,file_id,caption,is_vip,duration,file_size,created_at) VALUES(?,?,?,?,?,?,?,?)", 
                               (mid, pnum, file_id, caption, 1 if is_vip else 0, duration, file_size, now))
        await self.conn.execute("UPDATE media SET total_parts=total_parts+1,updated_at=? WHERE id=?", (now, mid))
        await self.conn.commit()
        media = await self.get_media_by_id(mid)
        if media:
            await self.notify_new_part(mid, media["name"], pnum)
        return await self.get_last_insert_id()
    
    async def get_parts(self, mid, user_is_vip=False):
        if user_is_vip:
            async with self.conn.execute("SELECT * FROM parts WHERE media_id=? ORDER BY part_number", (mid,)) as c:
                return await c.fetchall()
        async with self.conn.execute("SELECT * FROM parts WHERE media_id=? AND is_vip=0 ORDER BY part_number", (mid,)) as c:
            return await c.fetchall()
    
    async def get_part(self, pid):
        async with self.conn.execute("SELECT * FROM parts WHERE id=?", (pid,)) as c:
            return await c.fetchone()
    
    async def get_part_by_number(self, mid, pnum):
        async with self.conn.execute("SELECT * FROM parts WHERE media_id=? AND part_number=?", (mid, pnum)) as c:
            return await c.fetchone()
    
    async def update_part(self, pid, field, value):
        await self.conn.execute(f"UPDATE parts SET {field}=? WHERE id=?", (value, pid))
        await self.conn.commit()
    
    async def update_part_post_info(self, pid, msg_id, channel):
        await self.conn.execute("UPDATE parts SET post_message_id=?,post_channel=? WHERE id=?", (msg_id, channel, pid))
        await self.conn.commit()
    
    async def delete_part(self, pid):
        part = await self.get_part(pid)
        if part:
            await self.conn.execute("DELETE FROM parts WHERE id=?", (pid,))
            await self.conn.execute("UPDATE media SET total_parts=total_parts-1 WHERE id=?", (part["media_id"],))
            await self.conn.commit()
            return True
        return False
    
    async def increment_part_views(self, pid):
        await self.conn.execute("UPDATE parts SET views=views+1 WHERE id=?", (pid,))
        await self.conn.commit()
    
    async def get_parts_count(self):
        async with self.conn.execute("SELECT COUNT(*) FROM parts") as c:
            row = await c.fetchone()
            return row[0] if row else 0
    
    async def add_favorite(self, uid, mid):
        await self.conn.execute("INSERT OR IGNORE INTO favorites (user_id,media_id,added_at) VALUES(?,?,?)", 
                               (uid, mid, datetime.now().isoformat()))
        await self.conn.commit()
    
    async def remove_favorite(self, uid, mid):
        await self.conn.execute("DELETE FROM favorites WHERE user_id=? AND media_id=?", (uid, mid))
        await self.conn.commit()
    
    async def get_favorites(self, uid):
        async with self.conn.execute("SELECT media_id FROM favorites WHERE user_id=? ORDER BY added_at DESC", (uid,)) as c:
            return await c.fetchall()
    
    async def is_favorite(self, uid, mid):
        async with self.conn.execute("SELECT 1 FROM favorites WHERE user_id=? AND media_id=?", (uid, mid)) as c:
            return await c.fetchone() is not None
    
    async def add_notification(self, uid, mid, media_name):
        await self.conn.execute("INSERT OR IGNORE INTO notifications (user_id,media_id,media_name,is_active,created_at) VALUES(?,?,?,1,?)", 
                               (uid, mid, media_name, datetime.now().isoformat()))
        await self.conn.commit()
    
    async def remove_notification(self, uid, mid):
        await self.conn.execute("DELETE FROM notifications WHERE user_id=? AND media_id=?", (uid, mid))
        await self.conn.commit()
    
    async def has_notification(self, uid, mid):
        async with self.conn.execute("SELECT 1 FROM notifications WHERE user_id=? AND media_id=? AND is_active=1", (uid, mid)) as c:
            return await c.fetchone() is not None
    
    async def get_notifications(self, uid):
        async with self.conn.execute("SELECT media_id,media_name FROM notifications WHERE user_id=? AND is_active=1", (uid,)) as c:
            return await c.fetchall()
    
    async def get_users_by_notification(self, mid):
        async with self.conn.execute("SELECT user_id FROM notifications WHERE media_id=? AND is_active=1", (mid,)) as c:
            return await c.fetchall()
    
    async def notify_new_part(self, mid, media_name, pnum):
        users = await self.get_users_by_notification(mid)
        for u in users:
            try:
                await bot.send_message(u["user_id"], f"🔔 <b>Yangi qism!</b>\n\n🎬 {media_name}\n📀 {pnum}-qism qo'shildi!")
                await asyncio.sleep(0.05)
            except:
                pass
    
    async def add_rating(self, uid, mid, rating):
        await self.conn.execute("INSERT OR REPLACE INTO ratings (user_id,media_id,rating,created_at) VALUES(?,?,?,?)", 
                               (uid, mid, rating, datetime.now().isoformat()))
        await self.conn.commit()
        async with self.conn.execute("SELECT AVG(rating) as avg, COUNT(*) as cnt FROM ratings WHERE media_id=?", (mid,)) as c:
            row = await c.fetchone()
            if row:
                await self.conn.execute("UPDATE media SET rating=?,rating_count=? WHERE id=?", (row["avg"] or 0, row["cnt"] or 0, mid))
                await self.conn.commit()
    
    async def get_user_rating(self, uid, mid):
        async with self.conn.execute("SELECT rating FROM ratings WHERE user_id=? AND media_id=?", (uid, mid)) as c:
            row = await c.fetchone()
            return row["rating"] if row else None
    
    async def add_report(self, uid, mid, reason):
        await self.conn.execute("INSERT INTO reports (user_id,media_id,reason,status,created_at) VALUES(?,?,?,'pending',?)", 
                               (uid, mid, reason, datetime.now().isoformat()))
        await self.conn.commit()
    
    async def get_reports(self, status="pending"):
        async with self.conn.execute("SELECT * FROM reports WHERE status=? ORDER BY created_at DESC", (status,)) as c:
            return await c.fetchall()
    
    async def add_referral(self, ref_id, refd_id):
        now = datetime.now().isoformat()
        await self.conn.execute("INSERT INTO referrals (referrer_id,referred_id,created_at) VALUES(?,?,?)", (ref_id, refd_id, now))
        await self.conn.commit()
        async with self.conn.execute("SELECT COUNT(*) as cnt FROM referrals WHERE referrer_id=? AND is_rewarded=0", (ref_id,)) as c:
            row = await c.fetchone()
            if row and row["cnt"] >= 5:
                await self.conn.execute("UPDATE users SET is_vip=1,vip_expiry=? WHERE id=?", 
                                       ((datetime.now()+timedelta(days=1)).isoformat(), ref_id))
                await self.conn.execute("UPDATE referrals SET is_rewarded=1 WHERE referrer_id=?", (ref_id,))
                await self.conn.commit()
                return True
        return False
    
    async def get_referral_count(self, uid):
        async with self.conn.execute("SELECT COUNT(*) FROM referrals WHERE referrer_id=?", (uid,)) as c:
            row = await c.fetchone()
            return row[0] if row else 0
    
    async def get_stats(self):
        return {
            "users": await self.get_user_count(),
            "media": await self.get_media_count(),
            "parts": await self.get_parts_count(),
            "vip_users": await self.get_vip_count(),
            "admins": await self.get_admin_count(),
            "ongoing": await self.get_ongoing_count(),
            "total_views": await self.get_total_views()
        }
    
    async def get_total_views(self):
        async with self.conn.execute("SELECT SUM(views) FROM media") as c:
            row = await c.fetchone()
            return row[0] if row and row[0] else 0
    
    async def get_daily_stats(self, days=7):
        async with self.conn.execute("SELECT * FROM daily_stats ORDER BY date DESC LIMIT ?", (days,)) as c:
            return await c.fetchall()
    
    async def add_forced_channel(self, username, link, added_by):
        now = datetime.now().isoformat()
        await self.conn.execute("INSERT OR IGNORE INTO forced_channels (channel_username,channel_link,is_active,added_at,added_by) VALUES(?,?,1,?,?)", 
                               (username, link, now, added_by))
        await self.conn.commit()
    
    async def remove_forced_channel(self, cid):
        await self.conn.execute("DELETE FROM forced_channels WHERE id=?", (cid,))
        await self.conn.commit()
    
    async def get_forced_channels(self):
        async with self.conn.execute("SELECT id,channel_username,channel_link FROM forced_channels WHERE is_active=1") as c:
            return await c.fetchall()
    
    async def get_all_forced_channels(self):
        async with self.conn.execute("SELECT * FROM forced_channels ORDER BY channel_username") as c:
            return await c.fetchall()
    
    async def add_suggestion(self, uid, text):
        await self.conn.execute("INSERT INTO suggestions (user_id,suggestion,status,created_at) VALUES(?,?,'pending',?)", 
                               (uid, text, datetime.now().isoformat()))
        await self.conn.commit()
    
    async def get_suggestions(self, status="pending"):
        async with self.conn.execute("SELECT * FROM suggestions WHERE status=? ORDER BY created_at DESC", (status,)) as c:
            return await c.fetchall()
    
    async def add_like(self, uid, mid):
        await self.conn.execute("INSERT OR IGNORE INTO likes (user_id,media_id,created_at) VALUES(?,?,?)", 
                               (uid, mid, datetime.now().isoformat()))
        await self.conn.commit()
    
    async def remove_like(self, uid, mid):
        await self.conn.execute("DELETE FROM likes WHERE user_id=? AND media_id=?", (uid, mid))
        await self.conn.commit()
    
    async def get_likes(self, mid):
        async with self.conn.execute("SELECT COUNT(*) FROM likes WHERE media_id=?", (mid,)) as c:
            row = await c.fetchone()
            return row[0] if row else 0
    
    async def has_liked(self, uid, mid):
        async with self.conn.execute("SELECT 1 FROM likes WHERE user_id=? AND media_id=?", (uid, mid)) as c:
            return await c.fetchone() is not None
    
    async def add_comment(self, uid, mid, username, text):
        await self.conn.execute("INSERT INTO comments (user_id,media_id,username,text,created_at) VALUES(?,?,?,?,?)", 
                               (uid, mid, username, text, datetime.now().isoformat()))
        await self.conn.commit()
    
    async def get_comments(self, mid):
        async with self.conn.execute("SELECT * FROM comments WHERE media_id=? ORDER BY created_at DESC", (mid,)) as c:
            return await c.fetchall()
    
    async def add_group(self, gid, title="", username="", added_by=0):
        now = datetime.now().isoformat()
        await self.conn.execute("INSERT OR REPLACE INTO groups (id,title,username,added_by,added_at,is_active) VALUES(?,?,?,?,?,1)", 
                               (gid, title, username, added_by, now))
        await self.conn.commit()
    
    async def get_all_groups(self):
        async with self.conn.execute("SELECT * FROM groups WHERE is_active=1 ORDER BY title") as c:
            return await c.fetchall()
    
    async def add_watch_history(self, uid, mid, pnum):
        now = datetime.now().isoformat()
        await self.conn.execute("INSERT INTO watch_history (user_id,media_id,part_number,watched_at) VALUES(?,?,?,?)", 
                               (uid, mid, pnum, now))
        await self.conn.execute("UPDATE users SET total_views=total_views+1 WHERE id=?", (uid,))
        await self.conn.commit()
    
    async def get_continue_watching(self, uid, limit=5):
        async with self.conn.execute('''SELECT m.id,m.name,m.code,m.total_parts,MAX(w.part_number) as last_part 
                                      FROM watch_history w JOIN media m ON w.media_id=m.id 
                                      WHERE w.user_id=? AND m.total_parts>w.part_number 
                                      GROUP BY w.media_id ORDER BY MAX(w.watched_at) DESC LIMIT ?''', (uid, limit)) as c:
            return await c.fetchall()
    
    async def register_mini_app_user(self, uid, first_name="", last_name="", username=""):
        await self.conn.execute("INSERT OR REPLACE INTO mini_app_users (id,first_name,last_name,username,registered_at) VALUES(?,?,?,?,?)", 
                               (uid, first_name, last_name, username, datetime.now().isoformat()))
        await self.conn.commit()
    
    async def create_multi_part_session(self, uid, mid, media_name):
        await self.conn.execute("INSERT INTO multi_part_sessions (user_id,media_id,media_name,parts_data,total_parts,created_at) VALUES(?,?,?,'[]',0,?)", 
                               (uid, mid, media_name, datetime.now().isoformat()))
        await self.conn.commit()
    
    async def add_to_multi_part_session(self, uid, pnum, file_id, caption=""):
        session = await self.get_multi_part_session(uid)
        if not session:
            return False
        parts = json.loads(session["parts_data"] or "[]")
        parts.append({"part_number": pnum, "file_id": file_id, "caption": caption})
        await self.conn.execute("UPDATE multi_part_sessions SET parts_data=?,total_parts=? WHERE user_id=?", 
                               (json.dumps(parts), len(parts), uid))
        await self.conn.commit()
        return True
    
    async def get_multi_part_session(self, uid):
        async with self.conn.execute("SELECT * FROM multi_part_sessions WHERE user_id=?", (uid,)) as c:
            return await c.fetchone()
    
    async def save_multi_part_session(self, uid, is_vip=False):
        session = await self.get_multi_part_session(uid)
        if not session:
            return 0
        parts = json.loads(session["parts_data"] or "[]")
        saved = 0
        for p in parts:
            if not await self.get_part_by_number(session["media_id"], p["part_number"]):
                await self.add_part(session["media_id"], p["part_number"], p["file_id"], p.get("caption", ""), is_vip=is_vip)
                saved += 1
        await self.conn.execute("DELETE FROM multi_part_sessions WHERE user_id=?", (uid,))
        await self.conn.commit()
        return saved
    
    async def clear_multi_part_session(self, uid):
        await self.conn.execute("DELETE FROM multi_part_sessions WHERE user_id=?", (uid,))
        await self.conn.commit()
    
    async def fetch_one(self, q, p=()):
        async with self.conn.execute(q, p) as c:
            return await c.fetchone()
    
    async def fetch_all(self, q, p=()):
        async with self.conn.execute(q, p) as c:
            return await c.fetchall()
    
    async def execute(self, q, p=()):
        await self.conn.execute(q, p)
        await self.conn.commit()
    
    async def get_last_insert_id(self):
        async with self.conn.execute("SELECT last_insert_rowid()") as c:
            return (await c.fetchone())[0]
    
    async def close(self):
        if self.conn:
            await self.conn.close()

db = Database()

# ================= STATE CLASSES =================
class SearchStates(StatesGroup):
    waiting_name = State()
    waiting_code = State()

class AdminStates(StatesGroup):
    waiting_broadcast = State()
    waiting_media_name = State()
    waiting_media_code = State()
    waiting_media_genre = State()
    waiting_media_image = State()
    waiting_media_description = State()
    waiting_media_voice = State()
    waiting_media_quality = State()
    waiting_media_year = State()
    waiting_post_channel = State()
    waiting_part_media = State()
    waiting_part_number = State()
    waiting_part_video = State()
    waiting_part_post = State()
    waiting_multi_part_media = State()
    waiting_admin_id = State()
    waiting_vip_days = State()
    waiting_delete_confirm = State()
    waiting_vip_user_id = State()
    waiting_remove_vip_user_id = State()
    waiting_add_admin_id = State()
    waiting_remove_admin_id = State()

class VIPStates(StatesGroup):
    waiting_phone = State()
    waiting_proof = State()

class EditMediaStates(StatesGroup):
    waiting_media_select = State()
    waiting_field = State()
    waiting_value = State()

class EditPartStates(StatesGroup):
    waiting_media_select = State()
    waiting_part_select = State()
    waiting_field = State()
    waiting_value = State()

class SuggestionStates(StatesGroup):
    waiting_suggestion = State()

class MultiPartStates(StatesGroup):
    waiting_video = State()

class PostStates(StatesGroup):
    waiting_channel = State()
    waiting_confirm = State()

# ================= FORMAT FUNCTIONS =================
def format_media_info(media) -> str:
    status_emoji = {"ongoing": "🟢", "completed": "✅", "hiatus": "⏸"}
    status_text = {"ongoing": "Davom etmoqda", "completed": "Tugallangan", "hiatus": "To'xtatilgan"}
    
    media_status = media["status"] if "status" in media.keys() else "ongoing"
    genre_str = media["genre"] if "genre" in media.keys() and media["genre"] else ""
    genres = genre_str.split(",") if genre_str else ["Noma'lum"]
    genre_hashtags = " ".join([f"#{g.strip()}" for g in genres if g.strip()])
    
    rating_val = media["rating"] if "rating" in media.keys() and media["rating"] else 0
    rating_stars = "⭐" * min(5, int(rating_val / 2)) if rating_val > 0 else "❌"
    rating_count_val = media["rating_count"] if "rating_count" in media.keys() and media["rating_count"] else 0
    
    voice_val = media["voice"] if "voice" in media.keys() and media["voice"] else AUTHOR_USERNAME
    quality_val = media["quality"] if "quality" in media.keys() and media["quality"] else "720p"
    views_val = media["views"] if "views" in media.keys() and media["views"] else 0
    is_vip_val = media["is_vip"] if "is_vip" in media.keys() and media["is_vip"] else 0
    description_val = media["description"] if "description" in media.keys() and media["description"] else ""
    
    text = "✽───〔•°⛩°•〕───✽\n"
    text += f"🏷 <b>Anime nomi</b> : {media['name']}\n"
    text += ". . . . . . . . . . . . . . . . . . . . . . . ──\n"
    text += f"🖋 <b>Janri</b> : {genre_hashtags}\n"
    text += ". . . ── . . . . . . . . . . . . . . . . . . . .\n"
    text += f"🎞 <b>Qismlar soni</b> : {media['total_parts']}\n"
    text += ". . . . . . . . . . . . . . . . . . . . . . . ──\n"
    nomalum = "Noma'lum"
    text += f"📊 <b>Holati</b> : {status_emoji.get(media_status, '❓')} {status_text.get(media_status, nomalum)}\n"
    text += ". . . ── . . . . . . . . . . . . . . . . . . . .\n"
    text += f"🎙 <b>Ovoz berdi</b> : {voice_val}\n"
    text += ". . . ── . . . . . . . . . . . . . . . . . . . .\n"
    text += f"💿 <b>Sifat</b> : {quality_val}\n"
    text += ". . . ── . . . . . . . . . . . . . . . . . . . .\n"
    text += f"💭 <b>Tili</b> : O'zbek tilida\n"
    text += ". . . ── . . . . . . . . . . . . . . . . . . . .\n"
    text += f"⭐ <b>Reyting</b> : {rating_stars} {rating_val:.1f}/10 ({rating_count_val} ta baho)\n"
    text += "✽───〔•°⛩°•〕───✽\n\n"
    text += f"🔢 <b>Kod</b> : <code>{media['code']}</code>\n"
    text += f"👁 <b>Ko'rilgan</b> : {views_val} marta\n"
    
    if is_vip_val:
        text += "👑 <b>VIP kontent</b>\n"
    
    if description_val:
        text += f"\n📝 <b>Tavsif:</b>\n{description_val}\n"
    
    return text

def format_number(num) -> str:
    if num >= 1_000_000:
        return f"{num/1_000_000:.1f}M"
    elif num >= 1_000:
        return f"{num/1_000:.1f}K"
    return str(num)

def get_welcome_text() -> str:
    text = "🎬 <b>AniComplex Rasmiy Bot</b> 🎬\n\n"
    text += "✨ <b>Botimizga xush kelibsiz!</b> ✨\n\n"
    text += "📚 <b>Bot imkoniyatlari:</b>\n"
    text += "🔍 Kod, nom yoki janr orqali qidiruv\n"
    text += "⭐ Sevimlilarga qo'shish\n"
    text += "🔔 Yangi qismlar haqida bildirishnoma\n"
    text += "⭐ Anime reytingi (1-10)\n"
    text += "👑 VIP a'zolik (30 kun)\n"
    text += "🤖 Guruhga qo'shish\n"
    text += "💬 Taklif va shikoyatlar\n"
    text += "🎲 Random anime tavsiyasi\n"
    text += "📊 Tomosha tarixi\n"
    text += "👥 Do'stlarni taklif qilish\n\n"
    text += f"📢 <b>Kanal:</b> {MAIN_CHANNEL}\n"
    text += f"👨‍💻 <b>Muallif:</b> <a href='{AUTHOR_LINK}'>{AUTHOR_USERNAME}</a>\n"
    text += f"🆘 <b>Yordam:</b> <a href='{SUPPORT_LINK}'>{SUPPORT_USERNAME}</a>\n\n"
    text += f"🔢 <b>Bot versiyasi:</b> {BOT_VERSION}\n\n"
    text += "⬇️ <b>Quyidagi tugmalardan foydalaning:</b>"
    return text

# ================= GURUH FUNKSIYALARI =================
async def should_reply_in_group(message: Message) -> bool:
    """Guruhda bot javob berishi kerakligini tekshiradi"""
    chat_type = message.chat.type
    
    if chat_type not in [ChatType.GROUP, ChatType.SUPERGROUP]:
        return True
    
    settings = await db.get_group_settings(message.chat.id)
    
    if not settings.get("bot_enabled", 1):
        return False
    
    bot_username = (await bot.get_me()).username
    text = message.text or message.caption or ""
    
    if text.startswith('/'):
        allowed_commands = ['/start', '/help', '/anime', '/search', '/code', '/watch', '/random']
        for cmd in allowed_commands:
            if text.startswith(cmd):
                return True
        return False
    
    if f"@{bot_username}" in text.lower():
        return True
    
    if message.reply_to_message and message.reply_to_message.from_user.id == bot.id:
        return True
    
    return False

# ================= MENUS =================
def get_main_menu(user_is_vip=False, is_group=False) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="🔍 Qidiruv", callback_data="search_menu")],
        [InlineKeyboardButton(text="⭐ Sevimlilar", callback_data="favorites"),
         InlineKeyboardButton(text="🔔 Bildirishnoma", callback_data="notifications")],
        [InlineKeyboardButton(text="📋 Media ro'yxati", callback_data="list_all")],
        [InlineKeyboardButton(text="📊 Davom eting", callback_data="continue_watching")],
        [InlineKeyboardButton(text="🟢 Davom etayotganlar", callback_data="ongoing_media"),
         InlineKeyboardButton(text="✅ Tugallanganlar", callback_data="completed_media")],
        [InlineKeyboardButton(text="🏆 Eng ko'p ko'rilganlar", callback_data="most_viewed"),
         InlineKeyboardButton(text="⭐ Eng yaxshi reyting", callback_data="highest_rated")],
        [InlineKeyboardButton(text="🆕 So'ngi qo'shilganlar", callback_data="recent_media"),
         InlineKeyboardButton(text="🎲 Random Anime", callback_data="random_media")],
    ]
    
    if is_group:
        buttons.append([InlineKeyboardButton(text="🤖 Guruhga qo'shish", callback_data="add_to_group")])
    else:
        buttons.append([InlineKeyboardButton(text="👑 VIP bo'lish", callback_data="become_vip")])
        if user_is_vip:
            buttons.insert(4, [InlineKeyboardButton(text="👑 VIP Media", callback_data="vip_media")])
        buttons.append([InlineKeyboardButton(text="🤖 Guruhga qo'shish", callback_data="add_to_group")])
        if MINI_APP_URL and MINI_APP_URL.startswith("https://"):
            buttons.append([InlineKeyboardButton(text="🎮 Mini App", web_app=WebAppInfo(url=MINI_APP_URL))])
        buttons.append([InlineKeyboardButton(text="💬 Taklif yuborish", callback_data="suggestion"),
                        InlineKeyboardButton(text="🎁 Do'stlarni taklif", callback_data="referral")])
        buttons.append([InlineKeyboardButton(text="🔐 Admin panel", callback_data="admin_panel")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_search_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Anime nomi orqali", callback_data="search_by_name")],
        [InlineKeyboardButton(text="🔢 Kod orqali", callback_data="search_by_code")],
        [InlineKeyboardButton(text="🎭 Janr orqali qidirish", callback_data="search_by_genre")],
        [InlineKeyboardButton(text="🎲 Random Anime", callback_data="random_media")],
        [InlineKeyboardButton(text="🔙 Bosh menyu", callback_data="back_to_start")]
    ])

def get_admin_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="📊 Statistika"), KeyboardButton(text="➕ Media qo'shish")],
        [KeyboardButton(text="📢 Media post qilish"), KeyboardButton(text="📢 Qism post qilish")],
        [KeyboardButton(text="✏️ Media tahrirlash"), KeyboardButton(text="🗑 Media o'chirish")],
        [KeyboardButton(text="📀 Qism qo'shish"), KeyboardButton(text="🎬 Ko'p qism qo'shish")],
        [KeyboardButton(text="✏️ Qism tahrirlash"), KeyboardButton(text="🗑 Qism o'chirish")],
        [KeyboardButton(text="📨 Xabar yuborish"), KeyboardButton(text="👑 VIP so'rovlar")],
        [KeyboardButton(text="👑 VIP berish"), KeyboardButton(text="👑 VIP olib tashlash")],
        [KeyboardButton(text="👥 Admin qo'shish"), KeyboardButton(text="👥 Admin o'chirish")],
        [KeyboardButton(text="🔗 Majburiy kanal"), KeyboardButton(text="📝 Takliflar")],
        [KeyboardButton(text="⚠️ Shikoyatlar"), KeyboardButton(text="📊 Daily stats")],
        [KeyboardButton(text="🔙 Bosh menyu")]
    ], resize_keyboard=True)

def get_media_edit_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Nomi", callback_data="edit_name"),
         InlineKeyboardButton(text="🔢 Kod", callback_data="edit_code")],
        [InlineKeyboardButton(text="🎭 Janr", callback_data="edit_genre"),
         InlineKeyboardButton(text="📊 Holat", callback_data="edit_status")],
        [InlineKeyboardButton(text="🖼 Rasm", callback_data="edit_image"),
         InlineKeyboardButton(text="📝 Tavsif", callback_data="edit_description")],
        [InlineKeyboardButton(text="🎙 Ovoz", callback_data="edit_voice"),
         InlineKeyboardButton(text="💿 Sifat", callback_data="edit_quality")],
        [InlineKeyboardButton(text="👑 VIP", callback_data="edit_vip"),
         InlineKeyboardButton(text="📅 Yil", callback_data="edit_year")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="cancel_edit")]
    ])

def get_back_button() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Bosh menyu", callback_data="back_to_start")]
    ])

# ================= SUBSCRIPTION MIDDLEWARE =================
class SubscriptionMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        user_id = None
        
        if isinstance(event, Message):
            user_id = event.from_user.id
            if event.text and (event.text.startswith("/start") or event.text.startswith("/cancel")):
                return await handler(event, data)
        elif isinstance(event, CallbackQuery):
            user_id = event.from_user.id
            if event.data in ["confirm_subscription", "check_subscription", "back_to_start"]:
                return await handler(event, data)
        
        if not user_id:
            return await handler(event, data)
        
        channels = await db.get_forced_channels()
        if not channels:
            return await handler(event, data)
        
        not_subscribed = []
        for ch in channels:
            try:
                member = await bot.get_chat_member(ch["channel_username"], user_id)
                if member.status in [ChatMemberStatus.LEFT, ChatMemberStatus.KICKED]:
                    not_subscribed.append(ch)
            except Exception:
                not_subscribed.append(ch)
        
        if not_subscribed:
            text = "❌ <b>Botdan foydalanish uchun quyidagi kanal(lar)ga a'zo bo'ling:</b>\n\n"
            keyboard = InlineKeyboardMarkup(inline_keyboard=[])
            for ch in not_subscribed:
                text += f"• {ch['channel_username']}\n"
                keyboard.inline_keyboard.append([InlineKeyboardButton(text=f"📢 {ch['channel_username']}", url=ch['channel_link'])])
            text += "\n✅ A'zo bo'lgandan so'ng <b>A'zo bo'ldim</b> tugmasini bosing."
            keyboard.inline_keyboard.append([InlineKeyboardButton(text="✅ A'zo bo'ldim", callback_data="check_subscription")])
            
            if isinstance(event, Message):
                await event.answer(text, reply_markup=keyboard)
            else:
                try:
                    await event.message.edit_text(text, reply_markup=keyboard)
                except:
                    await event.message.answer(text, reply_markup=keyboard)
            return
        
        return await handler(event, data)

dp.message.middleware(SubscriptionMiddleware())
dp.callback_query.middleware(SubscriptionMiddleware())

# ================= BOT GURUHGA QO'SHILGANDA =================
@dp.my_chat_member()
async def bot_added_to_group(event: types.ChatMemberUpdated):
    if event.new_chat_member.status in [ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR]:
        chat = event.chat
        if chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
            await db.add_group(chat.id, chat.title or "", chat.username or "", event.from_user.id)
            logger.info(f"✅ Guruh saqlandi: {chat.title}")

# ================= START HANDLER =================
@dp.message(Command("start"))
async def cmd_start(message: Message):
    user_id = message.from_user.id
    chat_type = message.chat.type
    
    await db.add_user(user_id, message.from_user.username or "", message.from_user.first_name or "", message.from_user.last_name or "")
    await db.update_activity(user_id)
    user_is_vip = await db.is_vip(user_id)
    
    # Guruhda start
    if chat_type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        await db.add_group(message.chat.id, message.chat.title or "", message.chat.username or "", user_id)
        
        member = await bot.get_chat_member(message.chat.id, user_id)
        if member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR]:
            await message.answer(
                "🤖 <b>AniComplex Guruh Boti</b>\n\n"
                "✅ Bot guruhga muvaffaqiyatli qo'shildi!\n\n"
                "📌 <b>Qanday ishlatiladi:</b>\n"
                "• <code>/anime [nomi]</code> - Anime qidirish\n"
                "• <code>/code [raqam]</code> - Kod orqali topish\n"
                "• <code>/watch [kod]</code> - Tomosha qilish\n"
                "• <code>/random</code> - Random anime\n"
                "• <code>/help</code> - Yordam\n\n"
                "⚠️ <b>Eslatma:</b> Bot faqat komandalarga javob beradi!\n"
                "Botni @mention qilib ham ishlatishingiz mumkin."
            )
        return
    
    # Shaxsiy chat (davomi...)
    args = message.text.split()
    if len(args) > 1 and args[1].startswith("ref_"):
        try:
            ref_id = int(args[1].split("_")[1])
            if ref_id != user_id:
                if await db.add_referral(ref_id, user_id):
                    await bot.send_message(ref_id, "🎉 5 ta do'st taklif qildingiz! 1 kun VIP sovg'a!")
        except:
            pass
    
    if len(args) > 1 and args[1].startswith("code_"):
        try:
            code = int(args[1].split("_")[1])
            media = await db.get_media_by_code(code)
            if media:
                await show_media_details(message, media["id"], user_is_vip)
                return
        except:
            pass
    
    if len(args) > 1 and args[1].startswith("part_"):
        try:
            part_id = int(args[1].split("_")[1])
            await play_part_direct(message, part_id, user_is_vip)
            return
        except:
            pass
    
    await message.answer(get_welcome_text(), reply_markup=get_main_menu(user_is_vip))

async def play_part_direct(event: Union[Message, CallbackQuery], part_id: int, user_is_vip: bool):
    part = await db.get_part(part_id)
    if not part:
        await safe_reply(event, "❌ Qism topilmadi!")
        return
    if part["is_vip"] and not user_is_vip:
        await safe_reply(event, "🔒 VIP kontent!")
        return
    
    await db.increment_part_views(part_id)
    media = await db.get_media_by_id(part["media_id"])
    await db.add_watch_history(event.from_user.id, media["id"], part["part_number"])
    
    text = f"🎬 <b>{media['name']}</b>\n📀 <b>{part['part_number']}-qism</b>"
    if part["caption"]:
        text += f"\n{part['caption']}"
    
    try:
        if isinstance(event, Message):
            await event.answer_video(video=part["file_id"], caption=text)
        else:
            await event.message.answer_video(video=part["file_id"], caption=text)
    except:
        await safe_reply(event, f"❌ Video yuklanmadi!\n👨‍💻 Yordam: {SUPPORT_USERNAME}")

@dp.callback_query(F.data == "check_subscription")
async def check_subscription(callback: CallbackQuery):
    channels = await db.get_forced_channels()
    not_subscribed = []
    for ch in channels:
        try:
            member = await bot.get_chat_member(ch["channel_username"], callback.from_user.id)
            if member.status in [ChatMemberStatus.LEFT, ChatMemberStatus.KICKED]:
                not_subscribed.append(ch)
        except:
            not_subscribed.append(ch)
    
    if not_subscribed:
        text = "❌ <b>Siz hali quyidagi kanal(lar)ga a'zo emassiz:</b>\n\n"
        keyboard = InlineKeyboardMarkup(inline_keyboard=[])
        for ch in not_subscribed:
            text += f"• {ch['channel_username']}\n"
            keyboard.inline_keyboard.append([InlineKeyboardButton(text=f"📢 {ch['channel_username']}", url=ch['channel_link'])])
        keyboard.inline_keyboard.append([InlineKeyboardButton(text="✅ A'zo bo'ldim", callback_data="check_subscription")])
        try:
            await callback.message.edit_text(text, reply_markup=keyboard)
        except:
            await callback.message.answer(text, reply_markup=keyboard)
    else:
        user_is_vip = await db.is_vip(callback.from_user.id)
        try:
            await callback.message.delete()
        except:
            pass
        await callback.message.answer(get_welcome_text(), reply_markup=get_main_menu(user_is_vip))
    await callback.answer()

@dp.callback_query(F.data == "back_to_start")
async def back_to_start(callback: CallbackQuery):
    user_is_vip = await db.is_vip(callback.from_user.id)
    try:
        await callback.message.delete()
    except:
        pass
    await callback.message.answer(get_welcome_text(), reply_markup=get_main_menu(user_is_vip))
    await callback.answer()

@dp.message(F.text == "🔙 Bosh menyu")
async def back_to_main(message: Message):
    await message.answer(get_welcome_text(), reply_markup=get_main_menu(await db.is_vip(message.from_user.id)))

# ================= GURUHGA QO'SHISH =================
@dp.callback_query(F.data == "add_to_group")
async def add_to_group_start(callback: CallbackQuery):
    groups = await db.get_all_groups()
    text = "🤖 <b>Guruhga qo'shish</b>\n\n"
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    
    if groups:
        text += "📋 <b>Mavjud guruhlar:</b>\n\n"
        for g in groups[:10]:
            text += f"• {g['title']}\n"
            if g['username']:
                kb.inline_keyboard.append([InlineKeyboardButton(text=f"➕ {g['title']}", url=f"https://t.me/{g['username']}")])
    else:
        text += "📭 Hozircha guruhlar mavjud emas\n\n"
    
    text += "\n📌 <b>Yangi guruh qo'shish:</b>\n1. Botni guruhingizga qo'shing\n2. Botga ADMIN huquqini bering\n3. Guruhda /start yuboring\n\n👨‍💻 Yordam: " + SUPPORT_USERNAME
    kb.inline_keyboard.append([InlineKeyboardButton(text="🔙 Bosh menyu", callback_data="back_to_start")])
    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()

# ================= SEARCH HANDLERS =================
@dp.callback_query(F.data == "search_menu")
async def search_menu_callback(callback: CallbackQuery):
    await callback.message.edit_text("🔍 <b>Qidiruv tipini tanlang</b>", reply_markup=get_search_menu())
    await callback.answer()

@dp.callback_query(F.data == "search_by_name")
async def search_by_name_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("📝 <b>Anime nomini kiriting:</b>\n\n🔙 /cancel", reply_markup=get_back_button())
    await state.set_state(SearchStates.waiting_name)
    await callback.answer()

@dp.message(SearchStates.waiting_name)
async def search_by_name_result(message: Message, state: FSMContext):
    query = message.text.strip()
    user_is_vip = await db.is_vip(message.from_user.id)
    results = await db.search_media(query)
    filtered = [m for m in results if not m["is_vip"] or user_is_vip]
    
    if not filtered:
        await message.answer(f"❌ '{query}' bo'yicha topilmadi!", reply_markup=get_back_button())
        await state.clear()
        return
    
    builder = InlineKeyboardBuilder()
    for m in filtered:
        star = "⭐" if (m["rating"] or 0) > 7 else ""
        builder.button(text=f"{star} {m['name']} [{m['code']}]", callback_data=f"view_media_{m['id']}")
    builder.adjust(1)
    builder.row(InlineKeyboardButton(text="🔙 Qidiruvga qaytish", callback_data="search_menu"))
    
    await message.answer(f"🔍 '{query}' bo'yicha {len(filtered)} ta natija:", reply_markup=builder.as_markup())
    await state.clear()

@dp.callback_query(F.data == "search_by_code")
async def search_by_code_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("🔢 <b>Anime kodini kiriting:</b>\n\n🔙 /cancel", reply_markup=get_back_button())
    await state.set_state(SearchStates.waiting_code)
    await callback.answer()

@dp.message(SearchStates.waiting_code)
async def search_by_code_result(message: Message, state: FSMContext):
    try:
        code = int(message.text.strip())
        media = await db.get_media_by_code(code)
        if media:
            await show_media_details(message, media["id"], await db.is_vip(message.from_user.id))
        else:
            await message.answer(f"❌ {code} kodli media topilmadi!", reply_markup=get_back_button())
    except:
        await message.answer("❌ Faqat raqam kiriting!")
    await state.clear()

@dp.callback_query(F.data == "search_by_genre")
async def search_by_genre_start(callback: CallbackQuery):
    genres = await db.get_all_genres()
    if not genres:
        await callback.answer("❌ Janrlar mavjud emas!", show_alert=True)
        return
    
    builder = InlineKeyboardBuilder()
    for g in genres[:20]:
        builder.button(text=f"#{g}", callback_data=f"genre_select_{g}")
    builder.adjust(2)
    builder.row(InlineKeyboardButton(text="🔙 Qidiruvga qaytish", callback_data="search_menu"))
    await callback.message.edit_text(f"🎭 <b>Janrni tanlang</b> ({len(genres)} ta)", reply_markup=builder.as_markup())
    await callback.answer()

@dp.callback_query(F.data.startswith("genre_select_"))
async def genre_result(callback: CallbackQuery):
    genre = callback.data.replace("genre_select_", "")
    results = await db.get_media_by_genre(genre, await db.is_vip(callback.from_user.id))
    if not results:
        await callback.answer(f"❌ #{genre} topilmadi!", show_alert=True)
        return
    
    builder = InlineKeyboardBuilder()
    for m in results:
        star = "⭐" if (m["rating"] or 0) > 7 else ""
        builder.button(text=f"{star} {m['name']} [{m['code']}]", callback_data=f"view_media_{m['id']}")
    builder.adjust(1)
    builder.row(InlineKeyboardButton(text="🔙 Janrlarga qaytish", callback_data="search_by_genre"))
    await callback.message.edit_text(f"🎭 <b>#{genre}</b> da {len(results)} ta anime:", reply_markup=builder.as_markup())
    await callback.answer()

# ================= GURUH UCHUN MAXSUS KOMANDALAR =================
@dp.message(Command("anime"))
async def anime_command(message: Message):
    if not await should_reply_in_group(message):
        return
    
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("❌ Iltimos, anime nomini kiriting:\n<code>/anime One Piece</code>")
        return
    
    query = args[1].strip()
    user_is_vip = await db.is_vip(message.from_user.id)
    results = await db.search_media(query)
    filtered = [m for m in results if not m["is_vip"] or user_is_vip]
    
    if not filtered:
        await message.answer(f"❌ '{query}' bo'yicha topilmadi!")
        return
    
    builder = InlineKeyboardBuilder()
    for m in filtered[:10]:
        builder.button(text=f"{m['name']} [{m['code']}]", callback_data=f"view_media_{m['id']}")
    builder.adjust(1)
    
    await message.answer(f"🔍 '{query}' bo'yicha {len(filtered)} ta natija:", reply_markup=builder.as_markup())

@dp.message(Command("search"))
async def search_command(message: Message):
    await anime_command(message)

@dp.message(Command("code"))
async def code_command(message: Message):
    if not await should_reply_in_group(message):
        return
    
    args = message.text.split()
    if len(args) < 2:
        await message.answer("❌ Iltimos, anime kodini kiriting:\n<code>/code 104</code>")
        return
    
    try:
        code = int(args[1].strip())
        media = await db.get_media_by_code(code)
        if media:
            await show_media_details(message, media["id"], await db.is_vip(message.from_user.id))
        else:
            await message.answer(f"❌ {code} kodli anime topilmadi!")
    except ValueError:
        await message.answer("❌ Kod faqat raqam bo'lishi kerak!")

@dp.message(Command("watch"))
async def watch_command(message: Message):
    if not await should_reply_in_group(message):
        return
    
    args = message.text.split()
    if len(args) < 2:
        await message.answer("❌ Iltimos, anime kodini kiriting:\n<code>/watch 104</code>")
        return
    
    try:
        code = int(args[1].strip())
        media = await db.get_media_by_code(code)
        if not media:
            await message.answer(f"❌ {code} kodli anime topilmadi!")
            return
        
        user_is_vip = await db.is_vip(message.from_user.id)
        if media["is_vip"] and not user_is_vip:
            await message.answer(f"🔒 <b>{media['name']}</b> VIP kontent!\n\n👑 VIP bo'lish uchun botga /start yuboring")
            return
        
        parts = await db.get_parts(media["id"], user_is_vip)
        if not parts:
            await message.answer("📀 Hozircha qismlar mavjud emas!")
            return
        
        builder = InlineKeyboardBuilder()
        for part in parts[:20]:
            builder.button(text=f"{part['part_number']}-qism", callback_data=f"watch_part_{part['id']}")
        builder.adjust(5)
        
        await message.answer(f"📺 <b>{media['name']}</b>\n\nQismni tanlang:", reply_markup=builder.as_markup())
    except ValueError:
        await message.answer("❌ Kod faqat raqam bo'lishi kerak!")

@dp.message(Command("random"))
async def random_command(message: Message):
    if not await should_reply_in_group(message):
        return
    
    user_is_vip = await db.is_vip(message.from_user.id)
    media = await db.get_random_media(user_is_vip)
    
    if not media:
        await message.answer("❌ Hozircha media yo'q!")
        return
    
    await show_media_details(message, media["id"], user_is_vip)

@dp.message(Command("help"))
async def help_command(message: Message):
    if not await should_reply_in_group(message):
        return
    
    chat_type = message.chat.type
    if chat_type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        help_text = (
            "🤖 <b>AniComplex Guruh Boti</b>\n\n"
            "📌 <b>Qanday ishlatiladi:</b>\n\n"
            "🔍 <b>Anime qidirish:</b>\n"
            "   • <code>/anime [nomi]</code> - Nom bo'yicha qidirish\n"
            "   • <code>/code [raqam]</code> - Kod orqali topish\n\n"
            "📺 <b>Tomosha qilish:</b>\n"
            "   • <code>/watch [kod]</code> - Animani ochish\n"
            "   • <code>/random</code> - Random anime\n\n"
            "💡 <b>Botni @mention qilib ham ishlatishingiz mumkin!</b>\n\n"
            f"📢 <b>Kanal:</b> {MAIN_CHANNEL}\n"
            f"🆘 <b>Yordam:</b> {SUPPORT_USERNAME}"
        )
        await message.answer(help_text)
    else:
        await message.answer(get_welcome_text(), reply_markup=get_main_menu(await db.is_vip(message.from_user.id)))

# ================= MEDIA LIST HANDLERS =================
@dp.callback_query(F.data == "ongoing_media")
async def ongoing_media(callback: CallbackQuery):
    user_is_vip = await db.is_vip(callback.from_user.id)
    results = await db.get_ongoing_media(user_is_vip)
    
    if not results:
        await callback.answer("❌ Hozircha davom etayotgan animelar yo'q!", show_alert=True)
        return
    
    builder = InlineKeyboardBuilder()
    for media in results:
        rating_val = media["rating"] if "rating" in media else 0
        rating_star = "⭐" if rating_val > 7 else ""
        builder.button(
            text=f"🟢 {rating_star} {media['name']} [{media['code']}] - {media['total_parts']} qism",
            callback_data=f"view_media_{media['id']}"
        )
    builder.adjust(1)
    builder.row(InlineKeyboardButton(text="🔙 Bosh menyu", callback_data="back_to_start"))
    
    await callback.message.edit_text(
        f"🟢 <b>Davom etayotgan animelar</b>\n\n📊 Jami: {len(results)} ta anime",
        reply_markup=builder.as_markup()
    )
    await callback.answer()

@dp.callback_query(F.data == "completed_media")
async def completed_media(callback: CallbackQuery):
    user_is_vip = await db.is_vip(callback.from_user.id)
    results = await db.get_completed_media(user_is_vip)
    
    if not results:
        await callback.answer("❌ Hozircha tugallangan animelar yo'q!", show_alert=True)
        return
    
    builder = InlineKeyboardBuilder()
    for media in results:
        rating_val = media["rating"] if "rating" in media else 0
        rating_star = "⭐" if rating_val > 7 else ""
        builder.button(
            text=f"✅ {rating_star} {media['name']} [{media['code']}] - {media['total_parts']} qism",
            callback_data=f"view_media_{media['id']}"
        )
    builder.adjust(1)
    builder.row(InlineKeyboardButton(text="🔙 Bosh menyu", callback_data="back_to_start"))
    
    await callback.message.edit_text(
        f"✅ <b>Tugallangan animelar</b>\n\n📊 Jami: {len(results)} ta anime",
        reply_markup=builder.as_markup()
    )
    await callback.answer()

@dp.callback_query(F.data == "most_viewed")
async def most_viewed(callback: CallbackQuery):
    user_is_vip = await db.is_vip(callback.from_user.id)
    results = await db.get_most_viewed(15, user_is_vip)
    
    if not results:
        await callback.answer("❌ Hozircha media yo'q!", show_alert=True)
        return
    
    builder = InlineKeyboardBuilder()
    for i, media in enumerate(results, 1):
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
        vip = "👑 " if media["is_vip"] else ""
        views_val = media["views"] if "views" in media else 0
        builder.button(
            text=f"{medal} {vip}{media['name']} [{media['code']}] 👁 {format_number(views_val)}",
            callback_data=f"view_media_{media['id']}"
        )
    builder.adjust(1)
    builder.row(InlineKeyboardButton(text="🔙 Qidiruvga qaytish", callback_data="search_menu"))
    
    await callback.message.edit_text(
        "🏆 <b>Eng ko'p ko'rilgan animelar</b>\n\nTOP 15:",
        reply_markup=builder.as_markup()
    )
    await callback.answer()

@dp.callback_query(F.data == "highest_rated")
async def highest_rated(callback: CallbackQuery):
    user_is_vip = await db.is_vip(callback.from_user.id)
    results = await db.get_highest_rated(15, user_is_vip)
    
    if not results:
        await callback.answer("❌ Hozircha reytinglar mavjud emas!", show_alert=True)
        return
    
    builder = InlineKeyboardBuilder()
    for i, media in enumerate(results, 1):
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
        vip = "👑 " if media["is_vip"] else ""
        rating_val = media["rating"] if "rating" in media else 0
        stars = "⭐" * min(5, int(rating_val / 2))
        builder.button(
            text=f"{medal} {vip}{media['name']} [{media['code']}] {stars} {rating_val:.1f}",
            callback_data=f"view_media_{media['id']}"
        )
    builder.adjust(1)
    builder.row(InlineKeyboardButton(text="🔙 Qidiruvga qaytish", callback_data="search_menu"))
    
    await callback.message.edit_text(
        "⭐ <b>Eng yaxshi reytingli animelar</b>\n\nTOP 15:",
        reply_markup=builder.as_markup()
    )
    await callback.answer()

@dp.callback_query(F.data == "recent_media")
async def recent_media(callback: CallbackQuery):
    user_is_vip = await db.is_vip(callback.from_user.id)
    results = await db.get_recent_media(15, user_is_vip)
    
    if not results:
        await callback.answer("❌ Hozircha media yo'q!", show_alert=True)
        return
    
    builder = InlineKeyboardBuilder()
    for media in results:
        vip = "👑 " if media["is_vip"] else ""
        date = media["created_at"][:10] if media["created_at"] else ""
        builder.button(
            text=f"🆕 {vip}{media['name']} [{media['code']}] ({date})",
            callback_data=f"view_media_{media['id']}"
        )
    builder.adjust(1)
    builder.row(InlineKeyboardButton(text="🔙 Qidiruvga qaytish", callback_data="search_menu"))
    
    await callback.message.edit_text(
        "🆕 <b>So'ngi qo'shilgan animelar</b>\n\nTOP 15:",
        reply_markup=builder.as_markup()
    )
    await callback.answer()

@dp.callback_query(F.data == "random_media")
async def random_media(callback: CallbackQuery):
    user_is_vip = await db.is_vip(callback.from_user.id)
    media = await db.get_random_media(user_is_vip)
    
    if not media:
        await callback.answer("❌ Hozircha media yo'q!", show_alert=True)
        return
    
    await show_media_details(callback, media["id"], user_is_vip)
    await callback.answer()

@dp.callback_query(F.data == "continue_watching")
async def continue_watching(callback: CallbackQuery):
    results = await db.get_continue_watching(callback.from_user.id)
    
    if not results:
        await callback.answer("📊 Davom etayotgan animelar yo'q!", show_alert=True)
        return
    
    builder = InlineKeyboardBuilder()
    for media in results:
        builder.button(
            text=f"📺 {media['name']} [{media['code']}] - {media['last_part']}/{media['total_parts']}",
            callback_data=f"watch_media_{media['id']}"
        )
    builder.adjust(1)
    builder.row(InlineKeyboardButton(text="🔙 Bosh menyu", callback_data="back_to_start"))
    
    await callback.message.edit_text(
        "📊 <b>Davom etayotgan animelar</b>\n\nTomosha qilishda davom eting:",
        reply_markup=builder.as_markup()
    )
    await callback.answer()

@dp.callback_query(F.data == "list_all")
async def list_all_media(callback: CallbackQuery):
    user_is_vip = await db.is_vip(callback.from_user.id)
    media_list = await db.get_all_media(user_is_vip)
    
    if not media_list:
        await callback.message.edit_text("📭 Hozircha media mavjud emas!", reply_markup=get_back_button())
        await callback.answer()
        return
    
    builder = InlineKeyboardBuilder()
    for media in media_list:
        status = "✅" if media["status"] == "completed" else "🟢"
        vip = "👑 " if media["is_vip"] else ""
        builder.button(
            text=f"{status} {vip}{media['name']} [{media['code']}]",
            callback_data=f"view_media_{media['id']}"
        )
    builder.adjust(1)
    builder.row(InlineKeyboardButton(text="🔙 Bosh menyu", callback_data="back_to_start"))
    
    await callback.message.edit_text(
        f"📚 <b>MEDIA RO'YXATI</b>\n\n📊 Jami: {len(media_list)} ta media\n\n👇 Kerakli animeni tanlang:",
        reply_markup=builder.as_markup()
    )
    await callback.answer()

# ================= MEDIA DISPLAY =================
async def show_media_details(event, media_id, user_is_vip=False):
    media = await db.get_media_by_id(media_id)
    if not media:
        await safe_reply(event, "❌ Media topilmadi!")
        return
    
    if media["is_vip"] and not user_is_vip:
        await safe_reply(event, f"🔒 <b>{media['name']}</b> VIP kontent!\n\n👑 VIP bo'lish uchun /start -> VIP bo'lish")
        return
    
    await db.increment_views(media_id)
    
    uid = event.from_user.id if hasattr(event, 'from_user') else 0
    is_fav = await db.is_favorite(uid, media_id) if uid else False
    is_notif = await db.has_notification(uid, media_id) if uid else False
    likes = await db.get_likes(media_id)
    comments = await db.get_comments(media_id)
    user_rating = await db.fetch_one("SELECT rating FROM ratings WHERE user_id=? AND media_id=?", (uid, media_id)) if uid else None
    
    fav_text = "❌ Sevimlilardan o'chirish" if is_fav else "⭐ Sevimlilarga qo'shish"
    fav_cb = f"remove_favorite_{media_id}" if is_fav else f"add_favorite_{media_id}"
    notif_text = "🔕 Bildirishnomani o'chirish" if is_notif else "🔔 Bildirishnoma yoqish"
    notif_cb = f"remove_notification_{media_id}" if is_notif else f"add_notification_{media_id}"
    
    text = format_media_info(media)
    text += f"\n❤️ {likes} layk | 💬 {len(comments)} izoh"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📺 Tomosha qilish", callback_data=f"watch_media_{media_id}")],
        [InlineKeyboardButton(text=fav_text, callback_data=fav_cb),
         InlineKeyboardButton(text=notif_text, callback_data=notif_cb)],
        [InlineKeyboardButton(text=f"⭐ Baho berish" + (f" ({user_rating['rating']}/10)" if user_rating else ""), callback_data=f"rate_media_{media_id}")],
        [InlineKeyboardButton(text="❤️ Layk", callback_data=f"like_media_{media_id}"),
         InlineKeyboardButton(text="💬 Izoh", callback_data=f"comment_media_{media_id}")],
        [InlineKeyboardButton(text="⚠️ Shikoyat qilish", callback_data=f"report_media_{media_id}")],
        [InlineKeyboardButton(text="🔙 Bosh menyu", callback_data="back_to_start")]
    ])
    
    if media["image_url"]:
        await safe_send_photo(event, media["image_url"], text, keyboard)
    else:
        await safe_reply(event, text, reply_markup=keyboard)

async def safe_reply(event, text, **kwargs):
    try:
        if isinstance(event, CallbackQuery) and event.message:
            return await event.message.edit_text(text, **kwargs)
        return await event.answer(text, **kwargs)
    except:
        try:
            if isinstance(event, CallbackQuery) and event.message:
                return await event.message.answer(text, **kwargs)
            return await event.answer(text, **kwargs)
        except:
            return None

async def safe_send_photo(event, photo, caption=None, reply_markup=None, **kwargs):
    try:
        if isinstance(event, CallbackQuery):
            try:
                return await event.message.edit_media(InputMediaPhoto(media=photo, caption=caption, parse_mode=ParseMode.HTML), reply_markup=reply_markup)
            except:
                return await event.message.answer_photo(photo, caption=caption, reply_markup=reply_markup)
        return await event.answer_photo(photo, caption=caption, reply_markup=reply_markup)
    except:
        if caption:
            return await safe_reply(event, caption, reply_markup=reply_markup)
        return None

@dp.callback_query(F.data.startswith("view_media_"))
async def view_media(callback: CallbackQuery):
    media_id = int(callback.data.split("_")[2])
    await show_media_details(callback, media_id, await db.is_vip(callback.from_user.id))
    await callback.answer()

@dp.callback_query(F.data.startswith("watch_media_"))
async def watch_media(callback: CallbackQuery):
    media_id = int(callback.data.split("_")[2])
    user_is_vip = await db.is_vip(callback.from_user.id)
    media = await db.get_media_by_id(media_id)
    
    if not media:
        await callback.answer("Media topilmadi!")
        return
    if media["is_vip"] and not user_is_vip:
        await callback.answer("🔒 VIP kontent!", show_alert=True)
        return
    
    parts = await db.get_parts(media_id, user_is_vip)
    if not parts:
        await callback.answer("📀 Qismlar mavjud emas!", show_alert=True)
        return
    
    builder = InlineKeyboardBuilder()
    for part in parts:
        vip = "👑 " if part["is_vip"] else ""
        builder.button(text=f"{vip}{part['part_number']}-qism", callback_data=f"watch_part_{part['id']}")
    builder.adjust(5)
    builder.row(InlineKeyboardButton(text="🔙 Media ma'lumotlari", callback_data=f"view_media_{media_id}"))
    builder.row(InlineKeyboardButton(text="🏠 Bosh menyu", callback_data="back_to_start"))
    
    rating_val = media["rating"] if "rating" in media else 0
    rating_count_val = media["rating_count"] if "rating_count" in media else 0
    text = f"📺 <b>{media['name']}</b>\n\n📹 Qismlarni tanlang:\n📀 Jami: {len(parts)} ta qism\n⭐ Reyting: {rating_val:.1f}/10 ({rating_count_val} ta baho)"
    
    try:
        if callback.message.photo or callback.message.video:
            await callback.message.edit_caption(caption=text, reply_markup=builder.as_markup())
        else:
            await callback.message.edit_text(text, reply_markup=builder.as_markup())
    except:
        await callback.message.answer(text, reply_markup=builder.as_markup())
    await callback.answer()

@dp.callback_query(F.data.startswith("watch_part_"))
async def watch_part(callback: CallbackQuery):
    part_id = int(callback.data.split("_")[2])
    part = await db.get_part(part_id)
    user_is_vip = await db.is_vip(callback.from_user.id)
    
    if not part:
        await callback.answer("Qism topilmadi!")
        return
    if part["is_vip"] and not user_is_vip:
        await callback.answer("🔒 VIP kontent!", show_alert=True)
        return
    
    await db.increment_part_views(part_id)
    media = await db.get_media_by_id(part["media_id"])
    await db.add_watch_history(callback.from_user.id, media["id"], part["part_number"])
    
    text = f"🎬 <b>{media['name']}</b>\n📀 <b>{part['part_number']}-qism</b>\n"
    if part["caption"]:
        text += f"\n{part['caption']}"
    rating_val = media["rating"] if "rating" in media else 0
    text += f"\n\n⭐ Reyting: {rating_val:.1f}/10"
    
    try:
        await callback.message.answer_video(video=part["file_id"], caption=text)
    except Exception as e:
        logger.error(f"Video error: {e}")
        await callback.message.answer(f"❌ Video yuklab bo'lmadi!\n👨‍💻 Yordam: {SUPPORT_USERNAME}")
    await callback.answer()

# ================= FAVORITES =================
@dp.callback_query(F.data.startswith("add_favorite_"))
async def add_favorite(callback: CallbackQuery):
    media_id = int(callback.data.split("_")[2])
    await db.add_favorite(callback.from_user.id, media_id)
    await callback.answer("✅ Sevimlilarga qo'shildi!", show_alert=True)
    await show_media_details(callback, media_id, await db.is_vip(callback.from_user.id))

@dp.callback_query(F.data.startswith("remove_favorite_"))
async def remove_favorite(callback: CallbackQuery):
    media_id = int(callback.data.split("_")[2])
    await db.remove_favorite(callback.from_user.id, media_id)
    await callback.answer("❌ Sevimlilardan o'chirildi!", show_alert=True)
    await show_media_details(callback, media_id, await db.is_vip(callback.from_user.id))

@dp.callback_query(F.data == "favorites")
async def show_favorites(callback: CallbackQuery):
    favs = await db.get_favorites(callback.from_user.id)
    user_is_vip = await db.is_vip(callback.from_user.id)
    
    if not favs:
        await callback.answer("⭐ Sevimlilar ro'yxatingiz bo'sh!", show_alert=True)
        return
    
    builder = InlineKeyboardBuilder()
    count = 0
    for fav in favs:
        media = await db.get_media_by_id(fav["media_id"])
        if media and (not media["is_vip"] or user_is_vip):
            rating_val = media["rating"] if "rating" in media else 0
            rating_star = "⭐" if rating_val > 7 else ""
            builder.button(text=f"{rating_star} {media['name']} [{media['code']}]", callback_data=f"view_media_{media['id']}")
            count += 1
    builder.adjust(1)
    builder.row(InlineKeyboardButton(text="🔙 Bosh menyu", callback_data="back_to_start"))
    
    await callback.message.edit_text(f"⭐ <b>Sevimli animelaringiz</b>\n\n📊 Jami: {count} ta", reply_markup=builder.as_markup())
    await callback.answer()

# ================= NOTIFICATIONS =================
@dp.callback_query(F.data.startswith("add_notification_"))
async def add_notification(callback: CallbackQuery):
    media_id = int(callback.data.split("_")[2])
    media = await db.get_media_by_id(media_id)
    if media:
        await db.add_notification(callback.from_user.id, media_id, media["name"])
        await callback.answer("🔔 Bildirishnoma yoqildi!", show_alert=True)
    await show_media_details(callback, media_id, await db.is_vip(callback.from_user.id))

@dp.callback_query(F.data.startswith("remove_notification_"))
async def remove_notification(callback: CallbackQuery):
    media_id = int(callback.data.split("_")[2])
    await db.remove_notification(callback.from_user.id, media_id)
    await callback.answer("🔕 Bildirishnoma o'chirildi!", show_alert=True)
    await show_media_details(callback, media_id, await db.is_vip(callback.from_user.id))

@dp.callback_query(F.data == "notifications")
async def show_notifications(callback: CallbackQuery):
    notifs = await db.get_notifications(callback.from_user.id)
    if not notifs:
        await callback.answer("🔔 Bildirishnomalar ro'yxatingiz bo'sh!", show_alert=True)
        return
    
    text = "🔔 <b>Bildirishnoma yoqilgan animelar</b>\n\n"
    for n in notifs:
        text += f"• {n['media_name']}\n"
    text += f"\n📊 Jami: {len(notifs)} ta anime\n⚠️ Yangi qism chiqqanda xabar olasiz"
    
    await callback.message.edit_text(text, reply_markup=get_back_button())
    await callback.answer()

# ================= RATINGS =================
@dp.callback_query(F.data.startswith("rate_media_"))
async def rate_media_start(callback: CallbackQuery, state: FSMContext):
    media_id = int(callback.data.split("_")[2])
    await state.update_data(rate_media_id=media_id)
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=str(i), callback_data=f"set_rating_{i}") for i in range(1, 6)],
        [InlineKeyboardButton(text=str(i), callback_data=f"set_rating_{i}") for i in range(6, 11)]
    ])
    
    text = "⭐ <b>Animega baho bering (1-10):</b>\n\n1-2: Yomon | 3-4: O'rtacha | 5-6: Yaxshi\n7-8: Ajoyib | 9-10: Shoh asar"
    
    try:
        if callback.message.photo or callback.message.video:
            await callback.message.edit_caption(caption=text, reply_markup=kb)
        else:
            await callback.message.edit_text(text, reply_markup=kb)
    except:
        await callback.message.answer(text, reply_markup=kb)
    await callback.answer()

@dp.callback_query(F.data.startswith("set_rating_"))
async def set_rating(callback: CallbackQuery, state: FSMContext):
    rating = int(callback.data.split("_")[2])
    data = await state.get_data()
    media_id = data.get("rate_media_id")
    if media_id:
        await db.add_rating(callback.from_user.id, media_id, rating)
        await callback.answer(f"✅ Baho {rating}/10 qo'yildi!", show_alert=True)
    await state.clear()

# ================= REPORTS =================
@dp.callback_query(F.data.startswith("report_media_"))
async def report_media_start(callback: CallbackQuery, state: FSMContext):
    media_id = int(callback.data.split("_")[2])
    await state.update_data(report_media_id=media_id)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔞 Noo'rin kontent", callback_data="report_submit_inappropriate")],
        [InlineKeyboardButton(text="📀 Sifatli emas", callback_data="report_submit_quality")],
        [InlineKeyboardButton(text="🔗 Havola ishlamaydi", callback_data="report_submit_broken")],
        [InlineKeyboardButton(text="📝 Boshqa sabab", callback_data="report_submit_other")],
        [InlineKeyboardButton(text="🔙 Ortga", callback_data=f"view_media_{media_id}")]
    ])
    
    await callback.message.edit_text("⚠️ <b>Shikoyat sababini tanlang:</b>", reply_markup=keyboard)
    await callback.answer()

@dp.callback_query(F.data.startswith("report_submit_"))
async def report_media_submit(callback: CallbackQuery, state: FSMContext):
    reasons = {"inappropriate": "Noo'rin kontent", "quality": "Sifatli emas", "broken": "Havola ishlamaydi", "other": "Boshqa sabab"}
    key = callback.data.replace("report_submit_", "")
    if key in reasons:
        data = await state.get_data()
        media_id = data.get("report_media_id")
        if media_id:
            await db.add_report(callback.from_user.id, media_id, reasons[key])
            await callback.answer("✅ Shikoyatingiz qabul qilindi!", show_alert=True)
            for admin_id in ADMINS:
                try:
                    await bot.send_message(admin_id, f"⚠️ <b>Yangi shikoyat</b>\n\n👤 {callback.from_user.full_name}\n🆔 <code>{callback.from_user.id}</code>\n🎬 Media ID: {media_id}\n📝 Sabab: {reasons[key]}")
                except:
                    pass
    await state.clear()

# ================= LIKES & COMMENTS =================
@dp.callback_query(F.data.startswith("like_media_"))
async def like_media(callback: CallbackQuery):
    media_id = int(callback.data.split("_")[2])
    if await db.has_liked(callback.from_user.id, media_id):
        await db.remove_like(callback.from_user.id, media_id)
        await callback.answer("❤️ Layk olib tashlandi!", show_alert=True)
    else:
        await db.add_like(callback.from_user.id, media_id)
        await callback.answer("❤️ Layk bosildi!", show_alert=True)

@dp.callback_query(F.data.startswith("comment_media_"))
async def comment_media_start(callback: CallbackQuery, state: FSMContext):
    media_id = int(callback.data.split("_")[2])
    await state.update_data(comment_media_id=media_id)
    await callback.message.answer("💬 <b>Izohingizni yozing:</b>\n\n/cancel - bekor qilish")
    await state.set_state(SuggestionStates.waiting_suggestion)
    await callback.answer()

@dp.message(SuggestionStates.waiting_suggestion)
async def handle_suggestion_or_comment(message: Message, state: FSMContext):
    data = await state.get_data()
    comment_mid = data.get("comment_media_id")
    
    if comment_mid:
        # Bu izoh
        await db.add_comment(message.from_user.id, comment_mid, message.from_user.username or message.from_user.first_name, message.text.strip())
        await message.answer("✅ <b>Izohingiz qabul qilindi!</b>")
    else:
        # Bu taklif
        if len(message.text.strip()) < 10:
            await message.answer("❌ Taklif juda qisqa! Kamida 10 belgi yozing.")
            return
        await db.add_suggestion(message.from_user.id, message.text.strip())
        await message.answer("✅ <b>Taklifingiz qabul qilindi!</b>")
        for admin_id in ADMINS:
            try:
                await bot.send_message(admin_id, f"💬 <b>Yangi taklif</b>\n\n👤 {message.from_user.full_name}\n🆔 {message.from_user.id}\n📝 {message.text[:500]}")
            except:
                pass
    await state.clear()

# ================= VIP FUNCTIONS =================
@dp.callback_query(F.data == "become_vip")
async def become_vip(callback: CallbackQuery):
    text = f"👑 <b>VIP a'zolik</b> 👑\n\n"
    text += f"💰 <b>Narxi:</b> {VIP_PRICE} so'm / 30 kun\n\n"
    text += "📋 <b>VIP afzalliklari:</b>\n"
    text += "• 🔓 Barcha VIP kontentlarni ko'rish\n"
    text += "• 🎬 VIP animelarni tomosha qilish\n"
    text += "• 📀 VIP qismlarni ko'rish\n"
    text += "• ⭐ Yangiliklardan birinchi bo'lib xabardor bo'lish\n"
    text += "• 🎁 Maxsus aksiyalar va sovg'alar\n\n"
    text += "💳 <b>To'lov qilish uchun:</b>\n\n"
    text += f"📞 {PHONE_NUMBER_1}\n"
    text += f"📞 {PHONE_NUMBER_2}\n\n"
    text += f"💳 {CARD_NUMBER}\n\n"
    text += "⬇️ Pul o'tkazgandan so'ng <b>✅ To'lov qildim</b> tugmasini bosing"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ To'lov qildim", callback_data="vip_paid")],
        [InlineKeyboardButton(text="🔙 Bosh menyu", callback_data="back_to_start")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()

@dp.callback_query(F.data == "vip_paid")
async def vip_paid(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "📞 <b>Pul o'tkazgan telefon raqamingizni yuboring:</b>\n\nMasalan: +998901234567\n\n🔙 Bekor qilish: /cancel"
    )
    await state.set_state(VIPStates.waiting_phone)
    await callback.answer()

@dp.message(VIPStates.waiting_phone)
async def vip_phone(message: Message, state: FSMContext):
    phone = message.text.strip()
    if not re.match(r'^\+998\d{9}$', phone):
        await message.answer("❌ Noto'g'ri format! +998XXXXXXXXX ko'rinishida yuboring.")
        return
    
    await state.update_data(phone=phone)
    await message.answer("🖼 <b>To'lov chekini yuboring</b> (rasm):\n\nPul o'tkazganligingizni tasdiqlovchi screenshot yoki rasmni yuboring.")
    await state.set_state(VIPStates.waiting_proof)

@dp.message(VIPStates.waiting_proof, F.photo)
async def vip_proof(message: Message, state: FSMContext):
    data = await state.get_data()
    phone = data.get("phone")
    photo = message.photo[-1]
    
    request_id = await db.add_vip_request(message.from_user.id, phone, VIP_PRICE, photo.file_id)
    
    for admin_id in ADMINS:
        try:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"approve_vip_{request_id}"),
                 InlineKeyboardButton(text="❌ Rad etish", callback_data=f"reject_vip_{request_id}")]
            ])
            text = f"👑 <b>Yangi VIP so'rovi</b>\n\n👤 {message.from_user.full_name}\n🆔 {message.from_user.id}\n📞 {phone}\n💰 {VIP_PRICE} so'm"
            await bot.send_photo(admin_id, photo=photo.file_id, caption=text, reply_markup=keyboard)
        except Exception as e:
            logger.error(f"Admin message failed: {e}")
    
    await message.answer(
        f"✅ <b>So'rovingiz qabul qilindi!</b>\n\nAdminlar tomonidan tekshirilgandan so'ng VIP a'zolik faollashtiriladi.\n⏳ Bu odatda 5-10 daqiqa vaqt oladi.\n\n📢 Kanalimizga obuna bo'ling: {MAIN_CHANNEL}"
    )
    await state.clear()

@dp.callback_query(F.data.startswith("approve_vip_"))
async def approve_vip(callback: CallbackQuery):
    if callback.from_user.id not in ADMINS:
        await callback.answer("❌ Faqat bot egasi!", show_alert=True)
        return
    
    request_id = int(callback.data.split("_")[2])
    request = await db.get_vip_request(request_id)
    
    if request:
        await db.set_vip(request["user_id"], 30)
        await db.update_vip_request(request_id, "approved", callback.from_user.id)
        
        try:
            if callback.message.photo:
                await callback.message.edit_caption(caption=f"✅ VIP a'zolik tasdiqlandi!\n👤 Foydalanuvchi: {request['user_id']}")
            else:
                await callback.message.edit_text(f"✅ VIP a'zolik tasdiqlandi!\n👤 Foydalanuvchi: {request['user_id']}")
        except:
            await callback.message.answer(f"✅ VIP a'zolik tasdiqlandi!\n👤 Foydalanuvchi: {request['user_id']}")
        
        try:
            await bot.send_message(request["user_id"], "🎉 <b>Tabriklaymiz!</b> Siz VIP a'zo bo'ldingiz!\n\n👑 Endi barcha VIP kontentlarni ko'rishingiz mumkin.\n📅 VIP muddati: 30 kun\n\n🔥 Botdan zavqlaning!")
        except:
            pass
    
    await callback.answer()

@dp.callback_query(F.data.startswith("reject_vip_"))
async def reject_vip(callback: CallbackQuery):
    if callback.from_user.id not in ADMINS:
        await callback.answer("❌ Faqat bot egasi!", show_alert=True)
        return
    
    request_id = int(callback.data.split("_")[2])
    request = await db.get_vip_request(request_id)
    
    if request:
        await db.update_vip_request(request_id, "rejected", callback.from_user.id)
        
        try:
            if callback.message.photo:
                await callback.message.edit_caption(caption=f"❌ VIP so'rovi rad etildi!\n👤 Foydalanuvchi: {request['user_id']}")
            else:
                await callback.message.edit_text(f"❌ VIP so'rovi rad etildi!\n👤 Foydalanuvchi: {request['user_id']}")
        except:
            await callback.message.answer(f"❌ VIP so'rovi rad etildi!\n👤 Foydalanuvchi: {request['user_id']}")
        
        try:
            await bot.send_message(request["user_id"], f"❌ <b>Kechirasiz</b>, VIP so'rovingiz rad etildi.\n\n💡 Iltimos, to'lov ma'lumotlarini tekshirib, qaytadan urinib ko'ring.\n🆘 Yordam: {SUPPORT_USERNAME}")
        except:
            pass
    
    await callback.answer()

@dp.callback_query(F.data == "vip_media")
async def vip_media(callback: CallbackQuery):
    if not await db.is_vip(callback.from_user.id):
        await callback.answer("❌ Bu bo'lim faqat VIP a'zolar uchun!", show_alert=True)
        return
    
    media_list = await db.fetch_all("SELECT id,name,code,rating,image_url FROM media WHERE is_vip=1 ORDER BY name")
    if not media_list:
        await callback.message.edit_text("📭 Hozircha VIP media mavjud emas!", reply_markup=get_back_button())
        await callback.answer()
        return
    
    builder = InlineKeyboardBuilder()
    for media in media_list:
        rating_val = media["rating"] if "rating" in media else 0
        stars = "⭐" * min(5, int(rating_val / 2)) if rating_val > 0 else ""
        builder.button(text=f"👑 {media['name']} [{media['code']}] {stars}", callback_data=f"view_media_{media['id']}")
    builder.adjust(1)
    builder.row(InlineKeyboardButton(text="🔙 Bosh menyu", callback_data="back_to_start"))
    
    await callback.message.edit_text(
        f"👑 <b>VIP Media ro'yxati</b>\n\n📊 Jami: {len(media_list)} ta VIP media\n🔓 Barcha VIP kontentlar faqat VIP a'zolar uchun!",
        reply_markup=builder.as_markup()
    )
    await callback.answer()

# ================= REFERRALS =================
@dp.callback_query(F.data == "referral")
async def referral_info(callback: CallbackQuery):
    bot_info = await bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start=ref_{callback.from_user.id}"
    count = await db.get_referral_count(callback.from_user.id)
    
    text = "🎁 <b>Referral dasturi</b>\n\n"
    text += "Do'stlaringizni taklif qiling va sovg'alar yutib oling!\n\n"
    text += f"🔗 <b>Sizning referral linkingiz:</b>\n"
    text += f"<code>{ref_link}</code>\n\n"
    text += f"👥 Taklif qilganlar: {count} ta\n"
    text += "🎁 Har 5 ta taklif uchun 1 kun VIP!\n\n"
    text += "⚡️ Do'stlaringizga ulashing va VIP bo'ling!"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📤 Ulashish", url=f"https://t.me/share/url?url={ref_link}&text=AniComplex botiga taklif qilaman!")],
        [InlineKeyboardButton(text="🔙 Bosh menyu", callback_data="back_to_start")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()

# ================= SUGGESTIONS =================
@dp.callback_query(F.data == "suggestion")
async def suggestion_start(callback: CallbackQuery, state: FSMContext):
    text = "💬 <b>Taklif va shikoyatlar</b>\n\n"
    text += "Bot haqida taklif, shikoyat yoki yangi g'oyalaringizni yozib qoldiring.\n\n"
    text += "📝 <b>Taklifingizni yozing:</b>\n"
    text += "• Yangi funksiyalar\n"
    text += "• Anime takliflari\n"
    text += "• Xatoliklar haqida\n"
    text += "• Umumiy fikrlar\n\n"
    text += "🔙 Bekor qilish uchun /cancel"
    
    await callback.message.edit_text(text, reply_markup=get_back_button())
    await state.set_state(SuggestionStates.waiting_suggestion)
    await callback.answer()

# ================= ADMIN PANEL =================
@dp.callback_query(F.data == "admin_panel")
async def admin_panel(callback: CallbackQuery):
    if not await db.is_admin(callback.from_user.id):
        await callback.answer("❌ Siz admin emassiz!", show_alert=True)
        return
    
    stats = await db.get_stats()
    text = f"🔐 <b>Admin Panel</b>\n\n"
    text += f"👥 Foydalanuvchilar: {stats['users']}\n"
    text += f"👑 Adminlar: {stats['admins']}\n"
    text += f"🎬 Media: {stats['media']}\n"
    text += f"📀 Qismlar: {stats['parts']}\n"
    text += f"👑 VIP: {stats['vip_users']}\n"
    text += f"🟢 Ongoing: {stats['ongoing']}\n"
    text += f"👁 Jami ko'rishlar: {format_number(stats['total_views'])}\n\n"
    text += f"📅 {datetime.now().strftime('%d.%m.%Y %H:%M')}"
    
    try:
        await callback.message.delete()
    except:
        pass
    
    await callback.message.answer(text, reply_markup=get_admin_menu())
    await callback.answer()

# ================= ADMIN STATISTICS =================
@dp.message(F.text == "📊 Statistika")
async def admin_stats(message: Message):
    if not await db.is_admin(message.from_user.id):
        await message.answer("❌ Ruxsat yo'q!")
        return
    
    stats = await db.get_stats()
    text = f"📊 <b>Bot statistikasi</b>\n\n"
    text += f"👥 Foydalanuvchilar: {stats['users']}\n"
    text += f"👑 Adminlar: {stats['admins']}\n"
    text += f"🎬 Media: {stats['media']}\n"
    text += f"📀 Qismlar: {stats['parts']}\n"
    text += f"👑 VIP: {stats['vip_users']}\n"
    text += f"🟢 Ongoing: {stats['ongoing']}\n"
    text += f"👁 Jami ko'rishlar: {format_number(stats['total_views'])}"
    await message.answer(text)

@dp.message(F.text == "📊 Daily stats")
async def admin_daily_stats(message: Message):
    if not await db.is_admin(message.from_user.id):
        await message.answer("❌ Ruxsat yo'q!")
        return
    
    stats = await db.get_daily_stats(7)
    text = "📊 <b>Oxirgi 7 kunlik statistika</b>\n\n"
    for stat in reversed(stats):
        text += f"📅 {stat['date']}:\n"
        text += f"   👥 Yangi: +{stat['new_users']}\n"
        text += f"   📊 Faol: {stat['active_users']}\n"
        text += f"   👁 Ko'rishlar: {stat['total_views']}\n"
        text += f"   🎬 Yangi media: +{stat['new_media']}\n\n"
    
    await message.answer(text)

# ================= ADMIN MEDIA MANAGEMENT =================
@dp.message(F.text == "➕ Media qo'shish")
async def add_media_start(message: Message, state: FSMContext):
    if not await db.is_admin(message.from_user.id):
        return
    await message.answer("📝 Anime nomini kiriting:\n🔙 Bekor qilish: /cancel")
    await state.set_state(AdminStates.waiting_media_name)

@dp.message(AdminStates.waiting_media_name)
async def add_media_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("🔢 Kod kiriting (faqat raqam, masalan: 1, 2, 3):")
    await state.set_state(AdminStates.waiting_media_code)

@dp.message(AdminStates.waiting_media_code)
async def add_media_code(message: Message, state: FSMContext):
    try:
        code = int(message.text.strip())
        await state.update_data(code=code)
        await message.answer("🎭 Janrlarini kiriting (vergul bilan):\nMisol: Jangari, Drama, Sarguzasht")
        await state.set_state(AdminStates.waiting_media_genre)
    except ValueError:
        await message.answer("❌ Faqat raqam kiriting!")

@dp.message(AdminStates.waiting_media_genre)
async def add_media_genre(message: Message, state: FSMContext):
    await state.update_data(genre=message.text)
    await message.answer("🖼 Rasm URL yoki rasm yuboring (yoki /skip):")
    await state.set_state(AdminStates.waiting_media_image)

@dp.message(AdminStates.waiting_media_image, F.photo)
async def add_media_image_photo(message: Message, state: FSMContext):
    await state.update_data(image=message.photo[-1].file_id)
    await message.answer("📝 Anime tavsifini kiriting (yoki /skip):")
    await state.set_state(AdminStates.waiting_media_description)

@dp.message(AdminStates.waiting_media_image, F.text)
async def add_media_image_text(message: Message, state: FSMContext):
    image = message.text if message.text != "/skip" else ""
    await state.update_data(image=image)
    await message.answer("📝 Anime tavsifini kiriting (yoki /skip):")
    await state.set_state(AdminStates.waiting_media_description)

@dp.message(AdminStates.waiting_media_description)
async def add_media_description(message: Message, state: FSMContext):
    desc = message.text if message.text != "/skip" else ""
    await state.update_data(description=desc)
    await message.answer(f"🎙 Ovoz beruvchi(lar)ni kiriting:\nMasalan: {AUTHOR_USERNAME}")
    await state.set_state(AdminStates.waiting_media_voice)

@dp.message(AdminStates.waiting_media_voice)
async def add_media_voice(message: Message, state: FSMContext):
    await state.update_data(voice=message.text)
    await message.answer("💿 Sifatni kiriting:\nMasalan: 720p, 1080p, 480p")
    await state.set_state(AdminStates.waiting_media_quality)

@dp.message(AdminStates.waiting_media_quality)
async def add_media_quality(message: Message, state: FSMContext):
    await state.update_data(quality=message.text)
    await message.answer("📅 Chiqarilgan yilini kiriting (yoki /skip):\nMasalan: 2024")
    await state.set_state(AdminStates.waiting_media_year)

@dp.message(AdminStates.waiting_media_year)
async def add_media_year(message: Message, state: FSMContext):
    year = message.text if message.text != "/skip" else None
    if year and not str(year).isdigit():
        await message.answer("❌ Faqat raqam kiriting yoki /skip")
        return
    await state.update_data(year=int(year) if year and year.isdigit() else None)
    await save_new_media(message, state)

async def save_new_media(message: Message, state: FSMContext):
    data = await state.get_data()
    success, result = await db.add_media(
        code=data["code"], name=data["name"], genre=data["genre"],
        image_url=data.get("image", ""), description=data.get("description", ""),
        voice=data.get("voice", AUTHOR_USERNAME), quality=data.get("quality", "720p"),
        release_year=data.get("year"), is_vip=False
    )
    if success:
        media_id = result
        await message.answer(f"✅ <b>{data['name']}</b> qo'shildi!\n🔢 Kod: <code>{data['code']}</code>\n🎭 Janr: {data['genre']}")
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📢 Kanalga post qilish", callback_data=f"post_media_{media_id}")],
            [InlineKeyboardButton(text="❌ Keyinroq", callback_data="cancel_post")]
        ])
        await message.answer("📢 Bu mediani kanalga post qilasizmi?", reply_markup=keyboard)
    else:
        await message.answer(f"❌ {result}")
    await state.clear()

# ================= ADMIN MEDIA POST =================
@dp.callback_query(F.data.startswith("post_media_"))
async def post_media_start(callback: CallbackQuery, state: FSMContext):
    media_id = int(callback.data.split("_")[2])
    media = await db.get_media_by_id(media_id)
    if not media:
        await callback.answer("Media topilmadi!")
        return
    
    await state.update_data(media_id=media_id)
    await callback.message.edit_text(
        f"📢 <b>Post qilinadigan kanal username'ini kiriting:</b>\n\n"
        f"Masalan: @AniComplex_Rasmiy\n\n⚠️ Bot kanalda admin bo'lishi shart!\n\n🔙 /cancel"
    )
    await state.set_state(AdminStates.waiting_post_channel)
    await callback.answer()

@dp.message(AdminStates.waiting_post_channel)
async def post_media_channel(message: Message, state: FSMContext):
    channel = message.text.strip()
    if not channel.startswith("@"):
        channel = "@" + channel
    
    try:
        member = await bot.get_chat_member(channel, bot.id)
        if member.status not in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR]:
            await message.answer("❌ Bot kanalda admin emas! Avval botni admin qiling.")
            return
    except Exception as e:
        await message.answer(f"❌ Kanal topilmadi!\nXato: {e}")
        return
    
    data = await state.get_data()
    media = await db.get_media_by_id(data.get("media_id"))
    if not media:
        await message.answer("❌ Media topilmadi!")
        await state.clear()
        return
    
    text = format_media_info(media)
    bot_info = await bot.get_me()
    watch_link = f"https://t.me/{bot_info.username}?start=code_{media['code']}"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📺 Tomosha qilish", url=watch_link)],
        [InlineKeyboardButton(text="📢 Kanal", url=f"https://t.me/{MAIN_CHANNEL.replace('@', '')}")]
    ])
    
    try:
        if media["image_url"]:
            msg = await bot.send_photo(channel, media["image_url"], caption=text, reply_markup=keyboard)
        else:
            msg = await bot.send_message(channel, text, reply_markup=keyboard)
        await db.update_media_post_info(media["id"], msg.message_id, channel)
        await message.answer(f"✅ Media {channel} kanaliga post qilindi!")
    except Exception as e:
        await message.answer(f"❌ Post qilishda xatolik: {e}")
    await state.clear()

@dp.callback_query(F.data == "cancel_post")
async def cancel_post(callback: CallbackQuery):
    await callback.message.edit_text("✅ Media saqlandi, post qilinmadi.")
    await callback.answer()

# ================= ADMIN MEDIA EDIT =================
@dp.message(F.text == "✏️ Media tahrirlash")
async def edit_media_start(message: Message, state: FSMContext):
    if not await db.is_admin(message.from_user.id):
        return
    await message.answer("🔢 Tahrirlamoqchi bo'lgan media kodini kiriting:")
    await state.set_state(EditMediaStates.waiting_media_select)

@dp.message(EditMediaStates.waiting_media_select)
async def edit_media_select(message: Message, state: FSMContext):
    try:
        code = int(message.text.strip())
        media = await db.get_media_by_code(code)
        if not media:
            await message.answer("❌ Media topilmadi!")
            return
        await state.update_data(media_id=media["id"], media_name=media["name"])
        await message.answer(f"✏️ <b>{media['name']}</b> tahrirlash\n\nQaysi maydonni o'zgartirmoqchisiz?", reply_markup=get_media_edit_menu())
        await state.set_state(EditMediaStates.waiting_field)
    except ValueError:
        await message.answer("❌ Faqat raqam kiriting!")

@dp.callback_query(EditMediaStates.waiting_field, F.data.startswith("edit_"))
async def edit_media_field(callback: CallbackQuery, state: FSMContext):
    field = callback.data.split("_")[1]
    field_names = {
        "name": "yangi nomini", "code": "yangi kodni", "genre": "yangi janrlarini",
        "status": "yangi holatini (ongoing/completed/hiatus)", "image": "yangi rasm URL yoki rasm yuboring",
        "description": "yangi tavsifini", "voice": "yangi ovoz(lar)ni",
        "quality": "yangi sifatni", "vip": "VIP holatini (0/1)", "year": "yangi yilni"
    }
    await state.update_data(edit_field=field)
    await callback.message.edit_text(f"✏️ {field_names.get(field, 'yangi qiymatini')} kiriting:")
    await state.set_state(EditMediaStates.waiting_value)
    await callback.answer()

@dp.callback_query(F.data == "cancel_edit")
async def cancel_edit(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Tahrirlash bekor qilindi!")
    await callback.answer()

@dp.message(EditMediaStates.waiting_value, F.photo)
async def edit_media_value_photo(message: Message, state: FSMContext):
    data = await state.get_data()
    if data.get("edit_field") == "image":
        await db.update_media(data["media_id"], "image_url", message.photo[-1].file_id)
        await message.answer("✅ Rasm yangilandi!")
    await state.clear()

@dp.message(EditMediaStates.waiting_value, F.text)
async def edit_media_value_text(message: Message, state: FSMContext):
    data = await state.get_data()
    media_id, field, value = data["media_id"], data["edit_field"], message.text.strip()
    
    if field == "code":
        try:
            code = int(value)
            if await db.fetch_one("SELECT id FROM media WHERE code=? AND id!=?", (code, media_id)):
                await message.answer("❌ Bunday kod mavjud!")
                return
            await db.update_media(media_id, "code", code)
            await message.answer(f"✅ Kod {code} ga o'zgartirildi!")
        except ValueError:
            await message.answer("❌ Faqat raqam kiriting!")
            return
    elif field == "status":
        if value not in ["ongoing", "completed", "hiatus"]:
            await message.answer("❌ ongoing/completed/hiatus bo'lishi kerak!")
            return
        await db.update_media(media_id, "status", value)
        await message.answer(f"✅ Holat '{value}' ga o'zgartirildi!")
    elif field == "vip":
        if value in ["0", "1"]:
            await db.update_media(media_id, "is_vip", int(value))
            await message.answer(f"✅ VIP holati {'yoqilgan' if value=='1' else 'ochirilgan'}!")
        else:
            await message.answer("❌ 0 yoki 1 kiriting!")
            return
    elif field == "year":
        try:
            await db.update_media(media_id, "release_year", int(value))
            await message.answer(f"✅ Yil {value} ga o'zgartirildi!")
        except ValueError:
            await message.answer("❌ Faqat raqam kiriting!")
            return
    else:
        await db.update_media(media_id, field, value)
        await message.answer(f"✅ {field} o'zgartirildi!")
    await state.clear()

# ================= ADMIN MEDIA DELETE =================
@dp.message(F.text == "🗑 Media o'chirish")
async def delete_media_start(message: Message, state: FSMContext):
    if not await db.is_admin(message.from_user.id):
        return
    await message.answer("🔢 O'chirmoqchi bo'lgan media kodini kiriting:")
    await state.set_state(AdminStates.waiting_delete_confirm)

@dp.message(AdminStates.waiting_delete_confirm)
async def delete_media_confirm(message: Message, state: FSMContext):
    try:
        code = int(message.text.strip())
        media = await db.get_media_by_code(code)
        if not media:
            await message.answer("❌ Media topilmadi!")
            await state.clear()
            return
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Ha, o'chirish", callback_data=f"confirm_delete_media_{media['id']}"),
             InlineKeyboardButton(text="❌ Yo'q", callback_data="cancel_delete")]
        ])
        await message.answer(
            f"⚠️ <b>{media['name']}</b> ni o'chirmoqchimisiz?\n\n🔢 Kod: {media['code']}\n📀 Qismlar: {media['total_parts']} ta\n\n❗️ BU AMALNI QAYTARIB BO'LMAYDI!",
            reply_markup=keyboard
        )
        await state.update_data(media_id=media["id"])
    except ValueError:
        await message.answer("❌ Faqat raqam kiriting!")
        await state.clear()

@dp.callback_query(F.data.startswith("confirm_delete_media_"))
async def confirm_delete_media(callback: CallbackQuery, state: FSMContext):
    media_id = int(callback.data.split("_")[3])
    media = await db.get_media_by_id(media_id)
    if media:
        await db.delete_media(media_id)
        await callback.message.edit_text(f"✅ <b>{media['name']}</b> o'chirildi!")
    else:
        await callback.message.edit_text("❌ Media topilmadi!")
    await state.clear()
    await callback.answer()

@dp.callback_query(F.data == "cancel_delete")
async def cancel_delete(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ O'chirish bekor qilindi!")
    await callback.answer()

@dp.message(F.text == "📢 Media post qilish")
async def post_media_menu(message: Message, state: FSMContext):
    if not await db.is_admin(message.from_user.id):
        return
    await message.answer("🔢 Post qilmoqchi bo'lgan media kodini kiriting:")
    await state.set_state(PostStates.waiting_confirm)

@dp.message(PostStates.waiting_confirm)
async def post_media_select(message: Message, state: FSMContext):
    try:
        code = int(message.text.strip())
        media = await db.get_media_by_code(code)
        if not media:
            await message.answer("❌ Media topilmadi!")
            await state.clear()
            return
        await state.update_data(media_id=media["id"])
        await message.answer(f"📢 <b>Kanal username'ini kiriting:</b>\n\nMasalan: @AniComplex_Rasmiy\n\n⚠️ Bot kanalda admin bo'lishi shart!")
        await state.set_state(AdminStates.waiting_post_channel)
    except ValueError:
        await message.answer("❌ Faqat raqam kiriting!")
        await state.clear()

# ================= ADMIN PARTS MANAGEMENT =================
@dp.message(F.text == "📀 Qism qo'shish")
async def add_part_start(message: Message, state: FSMContext):
    if not await db.is_admin(message.from_user.id):
        return
    await message.answer("🔢 Media kodini kiriting:\n🔙 Bekor qilish: /cancel")
    await state.set_state(AdminStates.waiting_part_media)

@dp.message(AdminStates.waiting_part_media)
async def add_part_media(message: Message, state: FSMContext):
    try:
        code = int(message.text.strip())
        media = await db.get_media_by_code(code)
        if not media:
            await message.answer("❌ Media topilmadi! Qayta kiriting:")
            return
        await state.update_data(media_id=media["id"], media_name=media["name"], media_code=code)
        await message.answer(f"📺 {media['name']}\n\n📀 Qism raqamini kiriting:")
        await state.set_state(AdminStates.waiting_part_number)
    except ValueError:
        await message.answer("❌ Faqat raqam kiriting!")

@dp.message(AdminStates.waiting_part_number)
async def add_part_number(message: Message, state: FSMContext):
    try:
        part_num = int(message.text.strip())
        data = await state.get_data()
        if await db.get_part_by_number(data["media_id"], part_num):
            await message.answer(f"⚠️ {part_num}-qism mavjud! Boshqa raqam kiriting:")
            return
        await state.update_data(part_number=part_num)
        await message.answer(f"🎬 {part_num}-qism videosini yuboring:")
        await state.set_state(AdminStates.waiting_part_video)
    except ValueError:
        await message.answer("❌ Faqat raqam kiriting!")

@dp.message(AdminStates.waiting_part_video, F.video)
async def add_part_video(message: Message, state: FSMContext):
    data = await state.get_data()
    part_id = await db.add_part(
        media_id=data["media_id"], part_number=data["part_number"],
        file_id=message.video.file_id, caption=message.caption or "",
        duration=message.video.duration or 0, file_size=message.video.file_size or 0
    )
    await message.answer(f"✅ <b>{data['media_name']}</b> ning <b>{data['part_number']}-qismi</b> qo'shildi!\n\n🔔 Bildirishnoma yoqilganlarga xabar yuborildi.")
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Kanalga post qilish", callback_data=f"post_part_{part_id}")],
        [InlineKeyboardButton(text="❌ Keyinroq", callback_data="cancel_post")]
    ])
    await message.answer("📢 Bu qismni kanalga post qilasizmi?", reply_markup=keyboard)
    await state.clear()

# ================= ADMIN PART POST =================
@dp.callback_query(F.data.startswith("post_part_"))
async def post_part_start(callback: CallbackQuery, state: FSMContext):
    if callback.data.startswith("post_part_select_"):
        return
    
    try:
        parts = callback.data.split("_")
        if len(parts) >= 3 and parts[2].isdigit():
            part_id = int(parts[2])
        else:
            await callback.answer("❌ Noto'g'ri format!", show_alert=True)
            return
    except:
        await callback.answer("❌ Xatolik!", show_alert=True)
        return
    
    part = await db.get_part(part_id)
    if not part:
        await callback.answer("Qism topilmadi!")
        return
    
    await state.update_data(part_id=part_id)
    await callback.message.edit_text(f"📢 <b>Post qilinadigan kanal username'ini kiriting:</b>\n\nMasalan: @AniComplex_Rasmiy\n\n⚠️ Bot kanalda admin bo'lishi shart!\n\n🔙 /cancel")
    await state.set_state(AdminStates.waiting_part_post)
    await callback.answer()

@dp.message(AdminStates.waiting_part_post)
async def post_part_channel(message: Message, state: FSMContext):
    channel = message.text.strip()
    if not channel.startswith("@"):
        channel = "@" + channel
    
    try:
        member = await bot.get_chat_member(channel, bot.id)
        if member.status not in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR]:
            await message.answer("❌ Bot kanalda admin emas!")
            return
    except:
        await message.answer("❌ Kanal topilmadi!")
        return
    
    data = await state.get_data()
    part = await db.get_part(data.get("part_id"))
    if not part:
        await message.answer("❌ Qism topilmadi!")
        await state.clear()
        return
    
    media = await db.get_media_by_id(part["media_id"])
    bot_info = await bot.get_me()
    watch_link = f"https://t.me/{bot_info.username}?start=part_{part['id']}"
    
    text = f"🎬 <b>{media['name']}</b>\n📀 <b>{part['part_number']}-qism</b>\n"
    if part["caption"]:
        text += f"\n{part['caption']}\n"
    text += f"\n🔢 Kod: <code>{media['code']}</code>"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📺 Tomosha qilish", url=watch_link)],
        [InlineKeyboardButton(text="📢 Kanal", url=f"https://t.me/{MAIN_CHANNEL.replace('@', '')}")]
    ])
    
    try:
        msg = await bot.send_video(channel, part["file_id"], caption=text, reply_markup=keyboard)
        await db.update_part_post_info(part["id"], msg.message_id, channel)
        await message.answer(f"✅ Qism {channel} kanaliga post qilindi!")
    except Exception as e:
        await message.answer(f"❌ Post qilishda xatolik: {e}")
    await state.clear()

# ================= ADMIN PART EDIT =================
@dp.message(F.text == "✏️ Qism tahrirlash")
async def edit_part_start(message: Message, state: FSMContext):
    if not await db.is_admin(message.from_user.id):
        return
    await state.update_data(action="edit")
    await message.answer("🔢 Tahrirlamoqchi bo'lgan media kodini kiriting:\n🔙 /cancel")
    await state.set_state(EditPartStates.waiting_media_select)

@dp.message(EditPartStates.waiting_media_select)
async def edit_part_media_select(message: Message, state: FSMContext):
    try:
        code = int(message.text.strip())
        media = await db.get_media_by_code(code)
        if not media:
            await message.answer("❌ Media topilmadi!")
            return
        
        data = await state.get_data()
        action = data.get("action", "edit")
        await state.update_data(media_id=media["id"], media_name=media["name"])
        
        parts = await db.get_parts(media["id"], True)
        if not parts:
            await message.answer("❌ Bu mediada qismlar mavjud emas!")
            await state.clear()
            return
        
        builder = InlineKeyboardBuilder()
        for part in parts:
            vip = "👑 " if part["is_vip"] else ""
            part_id = part["id"]
            if action == "post":
                cb = f"post_part_select_{part_id}"
            elif action == "delete":
                cb = f"delete_part_select_{part_id}"
            else:
                cb = f"edit_part_select_{part_id}"
            builder.button(text=f"{vip}{part['part_number']}-qism", callback_data=cb)
        builder.adjust(3)
        builder.row(InlineKeyboardButton(text="🔙 Bekor qilish", callback_data="cancel_edit"))
        
        action_text = {"edit": "tahrirlamoqchisiz", "delete": "o'chirmoqchisiz", "post": "post qilmoqchisiz"}.get(action, "tanlamoqchisiz")
        await message.answer(f"📺 <b>{media['name']}</b>\n\nQaysi qismni {action_text}?", reply_markup=builder.as_markup())
        await state.set_state(EditPartStates.waiting_part_select)
    except ValueError:
        await message.answer("❌ Faqat raqam kiriting!")

@dp.callback_query(F.data.startswith("edit_part_select_"))
async def edit_part_select(callback: CallbackQuery, state: FSMContext):
    try:
        part_id = int(callback.data.split("_")[3])
    except:
        await callback.answer("❌ Xatolik!", show_alert=True)
        return
    
    part = await db.get_part(part_id)
    if not part:
        await callback.answer("Qism topilmadi!")
        return
    
    await state.update_data(part_id=part_id, part_number=part["part_number"])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📹 Video", callback_data="edit_part_video"),
         InlineKeyboardButton(text="📝 Caption", callback_data="edit_part_caption")],
        [InlineKeyboardButton(text="🔢 Qism raqami", callback_data="edit_part_number"),
         InlineKeyboardButton(text="👑 VIP", callback_data="edit_part_vip")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="cancel_edit")]
    ])
    
    await callback.message.edit_text(f"✏️ {part['part_number']}-qismni tahrirlash\n\nQaysi maydonni o'zgartirmoqchisiz?", reply_markup=keyboard)
    await state.set_state(EditPartStates.waiting_field)
    await callback.answer()

@dp.callback_query(EditPartStates.waiting_field, F.data.startswith("edit_part_"))
async def edit_part_field(callback: CallbackQuery, state: FSMContext):
    field = callback.data.split("_")[2]
    field_names = {
        "video": "yangi videoni", "caption": "yangi caption ni",
        "number": "yangi qism raqamini", "vip": "VIP holatini (0 yoki 1)"
    }
    await state.update_data(edit_field=field)
    await callback.message.edit_text(f"✏️ {field_names.get(field, 'yangi qiymatini')} kiriting:")
    await state.set_state(EditPartStates.waiting_value)
    await callback.answer()

@dp.message(EditPartStates.waiting_value, F.video)
async def edit_part_value_video(message: Message, state: FSMContext):
    data = await state.get_data()
    if data.get("edit_field") == "video":
        await db.update_part(data["part_id"], "file_id", message.video.file_id)
        await message.answer("✅ Video yangilandi!")
    await state.clear()

@dp.message(EditPartStates.waiting_value, F.text)
async def edit_part_value_text(message: Message, state: FSMContext):
    data = await state.get_data()
    part_id, field, value = data["part_id"], data["edit_field"], message.text.strip()
    
    if field == "number":
        try:
            new_num = int(value)
            part = await db.get_part(part_id)
            existing = await db.get_part_by_number(part["media_id"], new_num)
            if existing and existing["id"] != part_id:
                await message.answer(f"⚠️ {new_num}-qism mavjud!")
                return
            await db.update_part(part_id, "part_number", new_num)
            await message.answer(f"✅ Qism raqami {new_num} ga o'zgartirildi!")
        except ValueError:
            await message.answer("❌ Faqat raqam kiriting!")
    elif field == "caption":
        await db.update_part(part_id, "caption", value)
        await message.answer("✅ Caption yangilandi!")
    elif field == "vip":
        if value in ["0", "1"]:
            await db.update_part(part_id, "is_vip", int(value))
            await message.answer(f"✅ VIP holati {'yoqilgan' if value=='1' else 'ochirilgan'}!")
        else:
            await message.answer("❌ 0 yoki 1 kiriting!")
    await state.clear()

# ================= ADMIN PART DELETE =================
@dp.message(F.text == "🗑 Qism o'chirish")
async def delete_part_start(message: Message, state: FSMContext):
    if not await db.is_admin(message.from_user.id):
        return
    await state.update_data(action="delete")
    await message.answer("🔢 Media kodini kiriting:\n🔙 /cancel")
    await state.set_state(EditPartStates.waiting_media_select)

@dp.message(EditPartStates.waiting_media_select)
async def delete_part_media_select(message: Message, state: FSMContext):
    try:
        code = int(message.text.strip())
        media = await db.get_media_by_code(code)
        if not media:
            await message.answer("❌ Media topilmadi!")
            return
        
        await state.update_data(media_id=media["id"], media_name=media["name"])
        parts = await db.get_parts(media["id"], True)
        if not parts:
            await message.answer("❌ Bu mediada qismlar mavjud emas!")
            await state.clear()
            return
        
        part_numbers = sorted([str(p["part_number"]) for p in parts], key=int)
        await message.answer(
            f"📺 <b>{media['name']}</b>\n\n📀 Mavjud qismlar: {', '.join(part_numbers)}\n\n"
            f"🗑 <b>O'chirmoqchi bo'lgan qism raqamlarini kiriting:</b>\n\n"
            f"📌 Format: 1,2,3,4 yoki 1-5 yoki 1,3,5-7\n🔙 /cancel",
            reply_markup=get_back_button()
        )
        await state.set_state(EditPartStates.waiting_part_select)
    except ValueError:
        await message.answer("❌ Faqat raqam kiriting!")

def parse_part_numbers(text: str) -> list:
    numbers = set()
    for part in text.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            start, end = part.split("-")
            for i in range(int(start), int(end) + 1):
                numbers.add(i)
        else:
            numbers.add(int(part))
    return sorted(list(numbers))

@dp.message(EditPartStates.waiting_part_select, F.text)
async def delete_parts_by_numbers(message: Message, state: FSMContext):
    data = await state.get_data()
    media_id = data.get("media_id")
    if not media_id:
        await message.answer("❌ Media topilmadi!")
        await state.clear()
        return
    
    try:
        part_numbers = parse_part_numbers(message.text.strip().replace(" ", ""))
    except ValueError as e:
        await message.answer(f"❌ Noto'g'ri format: {e}\n\nTo'g'ri: 1,2,3,4 yoki 1-5")
        return
    
    if not part_numbers:
        await message.answer("❌ Hech qanday qism raqami topilmadi!")
        return
    
    existing = {p["part_number"] for p in await db.get_parts(media_id, True)}
    valid = sorted([n for n in part_numbers if n in existing])
    invalid = [n for n in part_numbers if n not in existing]
    
    if not valid:
        await message.answer(f"❌ Kiritilgan qismlar mavjud emas!\n\nMavjud: {', '.join(map(str, sorted(existing)))}")
        return
    
    text = f"⚠️ <b>{data.get('media_name')}</b>\n\n🗑 O'chiriladigan: {', '.join(map(str, valid))}\n📊 Jami: {len(valid)} ta"
    if invalid:
        text += f"\n⚠️ Topilmagan: {', '.join(map(str, invalid))}"
    text += "\n\n❗️ BU AMALNI QAYTARIB BO'LMAYDI!\n\nTasdiqlaysizmi?"
    
    await state.update_data(delete_part_numbers=valid)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Ha, o'chirish", callback_data="confirm_delete_parts"),
         InlineKeyboardButton(text="❌ Yo'q", callback_data="cancel_delete")]
    ])
    await message.answer(text, reply_markup=keyboard)

@dp.callback_query(F.data == "confirm_delete_parts")
async def confirm_delete_parts(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    media_id, part_numbers = data.get("media_id"), data.get("delete_part_numbers", [])
    if not media_id or not part_numbers:
        await callback.message.edit_text("❌ Ma'lumot topilmadi!")
        await state.clear()
        return
    
    deleted = 0
    for pnum in part_numbers:
        part = await db.get_part_by_number(media_id, pnum)
        if part and await db.delete_part(part["id"]):
            deleted += 1
    
    await callback.message.edit_text(f"✅ <b>Qismlar o'chirildi!</b>\n\n✅ O'chirilgan: {deleted} ta\n📊 Jami: {len(part_numbers)} ta")
    await state.clear()
    await callback.answer()

@dp.message(F.text == "📢 Qism post qilish")
async def post_part_menu(message: Message, state: FSMContext):
    if not await db.is_admin(message.from_user.id):
        return
    await state.update_data(action="post")
    await message.answer("🔢 Media kodini kiriting:\n🔙 /cancel")
    await state.set_state(EditPartStates.waiting_media_select)

@dp.callback_query(F.data.startswith("post_part_select_"))
async def post_part_select(callback: CallbackQuery, state: FSMContext):
    try:
        parts = callback.data.split("_")
        if len(parts) >= 4 and parts[3].isdigit():
            part_id = int(parts[3])
        else:
            await callback.answer("❌ Noto'g'ri format!", show_alert=True)
            return
    except:
        await callback.answer("❌ Xatolik!", show_alert=True)
        return
    
    await state.update_data(part_id=part_id)
    await callback.message.edit_text(f"📢 <b>Post qilinadigan kanal username'ini kiriting:</b>\n\nMasalan: @AniComplex_Rasmiy\n\n⚠️ Bot kanalda admin bo'lishi shart!")
    await state.set_state(AdminStates.waiting_part_post)
    await callback.answer()

# ================= ADMIN VIP MANAGEMENT =================
@dp.message(F.text == "👑 VIP so'rovlar")
async def admin_vip_requests(message: Message):
    if not await db.is_admin(message.from_user.id):
        await message.answer("❌ Ruxsat yo'q!")
        return
    
    requests = await db.get_vip_requests("pending")
    if not requests:
        await message.answer("📭 Kutilayotgan VIP so'rovlar yo'q")
        return
    
    text = "👑 <b>Kutilayotgan VIP so'rovlar</b>\n\n"
    for req in requests[:10]:
        text += f"🆔 So'rov ID: <code>{req['id']}</code>\n👤 Foydalanuvchi: <code>{req['user_id']}</code>\n📞 Tel: {req['phone_number']}\n💰 {req['amount']} so'm\n📅 {req['created_at'][:10]}\n\n"
    await message.answer(text)

@dp.message(F.text == "👑 VIP berish")
async def give_vip_start(message: Message, state: FSMContext):
    if not await db.is_admin(message.from_user.id):
        await message.answer("❌ Ruxsat yo'q!")
        return
    await message.answer("👤 VIP bermoqchi bo'lgan foydalanuvchi ID sini kiriting:")
    await state.set_state(AdminStates.waiting_vip_user_id)

@dp.message(AdminStates.waiting_vip_user_id)
async def give_vip_id(message: Message, state: FSMContext):
    try:
        user_id = int(message.text.strip())
        await state.update_data(user_id=user_id)
        await message.answer("📅 VIP muddatini kiriting (kun):\nMasalan: 30")
        await state.set_state(AdminStates.waiting_vip_days)
    except ValueError:
        await message.answer("❌ Faqat raqam kiriting!")

@dp.message(AdminStates.waiting_vip_days)
async def give_vip_days(message: Message, state: FSMContext):
    try:
        days = int(message.text.strip())
        data = await state.get_data()
        await db.set_vip(data["user_id"], days)
        await message.answer(f"✅ Foydalanuvchi {data['user_id']} ga {days} kun VIP berildi!")
        try:
            await bot.send_message(data["user_id"], f"🎉 <b>Tabriklaymiz!</b> Sizga {days} kun VIP a'zolik berildi!\n\n👑 Endi barcha VIP kontentlarni ko'rishingiz mumkin.")
        except:
            pass
    except ValueError:
        await message.answer("❌ Faqat raqam kiriting!")
    await state.clear()

@dp.message(F.text == "👑 VIP olib tashlash")
async def remove_vip_start(message: Message, state: FSMContext):
    if not await db.is_admin(message.from_user.id):
        await message.answer("❌ Ruxsat yo'q!")
        return
    await message.answer("👤 VIP olib tashlamoqchi bo'lgan foydalanuvchi ID sini kiriting:")
    await state.set_state(AdminStates.waiting_remove_vip_user_id)

@dp.message(AdminStates.waiting_remove_vip_user_id)
async def remove_vip_id(message: Message, state: FSMContext):
    try:
        user_id = int(message.text.strip())
        await db.remove_vip(user_id)
        await message.answer(f"✅ Foydalanuvchi {user_id} dan VIP olib tashlandi!")
        try:
            await bot.send_message(user_id, f"❌ Sizdan VIP a'zolik olib tashlandi.\n\n💡 Qayta VIP bo'lish uchun /start -> VIP bo'lish")
        except:
            pass
    except ValueError:
        await message.answer("❌ Faqat raqam kiriting!")
    await state.clear()

# ================= ADMIN MANAGEMENT =================
@dp.message(F.text == "👥 Admin qo'shish")
async def add_admin_start(message: Message, state: FSMContext):
    if not await db.is_owner(message.from_user.id):
        await message.answer("❌ Faqat bot egasi admin qo'sha oladi!")
        return
    await message.answer("👤 Admin qilmoqchi bo'lgan foydalanuvchi ID sini kiriting:")
    await state.set_state(AdminStates.waiting_add_admin_id)

@dp.message(AdminStates.waiting_add_admin_id)
async def add_admin_id(message: Message, state: FSMContext):
    try:
        user_id = int(message.text.strip())
        await db.add_admin(user_id, message.from_user.id)
        await message.answer(f"✅ Foydalanuvchi {user_id} admin qilib tayinlandi!")
        try:
            await bot.send_message(user_id, "🎉 Siz admin etib tayinlandingiz! Botni boshqarish huquqiga egasiz.\n\n🔐 Admin panel: /start -> Admin panel")
        except:
            pass
    except ValueError:
        await message.answer("❌ Faqat raqam kiriting!")
    await state.clear()

@dp.message(F.text == "👥 Admin o'chirish")
async def remove_admin_start(message: Message, state: FSMContext):
    if not await db.is_owner(message.from_user.id):
        await message.answer("❌ Faqat bot egasi admin o'chira oladi!")
        return
    await message.answer("👤 Adminlikdan o'chirmoqchi bo'lgan foydalanuvchi ID sini kiriting:")
    await state.set_state(AdminStates.waiting_remove_admin_id)

@dp.message(AdminStates.waiting_remove_admin_id)
async def remove_admin_id(message: Message, state: FSMContext):
    try:
        user_id = int(message.text.strip())
        if user_id in ADMINS:
            await message.answer("❌ Ownerlarni o'chirib bo'lmaydi!")
            await state.clear()
            return
        if await db.remove_admin(user_id):
            await message.answer(f"✅ Foydalanuvchi {user_id} adminlikdan o'chirildi!")
        else:
            await message.answer(f"⚠️ Foydalanuvchi {user_id} admin emas!")
    except ValueError:
        await message.answer("❌ Faqat raqam kiriting!")
    await state.clear()

# ================= FORCED CHANNELS MANAGEMENT =================
@dp.message(F.text == "🔗 Majburiy kanal")
async def forced_channels_menu(message: Message):
    if not await db.is_admin(message.from_user.id):
        await message.answer("❌ Ruxsat yo'q!")
        return
    
    channels = await db.get_all_forced_channels()
    text = "🔗 <b>Majburiy kanallar</b>\n\n"
    if channels:
        for ch in channels:
            status = "✅" if ch["is_active"] else "❌"
            text += f"{status} {ch['channel_username']}\n"
    else:
        text += "📭 Hozircha majburiy kanallar yo'q\n\n"
    text += "\n📌 <b>Qo'shish:</b> <code>/add_channel @kanal</code>\n📌 <b>O'chirish:</b> <code>/remove_channel @kanal</code>"
    await message.answer(text)

@dp.message(Command("add_channel"))
async def add_channel(message: Message):
    if not await db.is_admin(message.from_user.id):
        return
    args = message.text.split()
    if len(args) < 2:
        await message.answer("❌ /add_channel @kanal")
        return
    
    ch_input = args[1].strip()
    if ch_input.startswith("https://t.me/"):
        username = ch_input.split("/")[-1].split("?")[0]
        ch_username, ch_link = "@" + username, ch_input
    elif ch_input.startswith("@"):
        ch_username, ch_link = ch_input, "https://t.me/" + ch_input.replace("@", "")
    else:
        ch_username, ch_link = "@" + ch_input, "https://t.me/" + ch_input
    
    try:
        member = await bot.get_chat_member(ch_username, bot.id)
        if member.status not in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR]:
            await message.answer("❌ Bot kanalda admin bo'lishi kerak!")
            return
    except:
        await message.answer("❌ Kanal topilmadi yoki bot admin emas!")
        return
    
    await db.add_forced_channel(ch_username, ch_link, message.from_user.id)
    await message.answer(f"✅ {ch_username} majburiy kanallar ro'yxatiga qo'shildi!")

@dp.message(Command("remove_channel"))
async def remove_channel(message: Message):
    if not await db.is_admin(message.from_user.id):
        return
    args = message.text.split()
    if len(args) < 2:
        await message.answer("❌ /remove_channel @kanal")
        return
    
    ch_input = args[1].strip()
    ch_username = ch_input if ch_input.startswith("@") else "@" + ch_input
    
    channels = await db.get_all_forced_channels()
    for ch in channels:
        if ch["channel_username"] == ch_username:
            await db.remove_forced_channel(ch["id"])
            await message.answer(f"✅ {ch_username} o'chirildi!")
            return
    await message.answer(f"❌ {ch_username} topilmadi!")

# ================= ADMIN SUGGESTIONS & REPORTS =================
@dp.message(F.text == "📝 Takliflar")
async def admin_suggestions(message: Message):
    if not await db.is_admin(message.from_user.id):
        return
    suggestions = await db.get_suggestions("pending")
    if not suggestions:
        await message.answer("📭 Kutilayotgan takliflar yo'q")
        return
    
    text = "💬 <b>Kutilayotgan takliflar</b>\n\n"
    for sug in suggestions[:5]:
        text += f"🆔 ID: <code>{sug['user_id']}</code>\n📝 Taklif: {sug['suggestion'][:100]}...\n📅 {sug['created_at'][:10]}\n\n"
    await message.answer(text)

@dp.message(F.text == "⚠️ Shikoyatlar")
async def admin_reports(message: Message):
    if not await db.is_admin(message.from_user.id):
        return
    reports = await db.get_reports("pending")
    if not reports:
        await message.answer("📭 Kutilayotgan shikoyatlar yo'q")
        return
    
    text = "⚠️ <b>Kutilayotgan shikoyatlar</b>\n\n"
    for rep in reports[:5]:
        media = await db.get_media_by_id(rep["media_id"])
        text += f"🆔 ID: <code>{rep['user_id']}</code>\n🎬 Media: {media['name'] if media else 'Nomalum'}\n📝 Sabab: {rep['reason']}\n📅 {rep['created_at'][:10]}\n\n"
    await message.answer(text)

# ================= MULTIPLE PARTS UPLOAD =================
@dp.message(F.text == "🎬 Ko'p qism qo'shish")
async def multi_part_start(message: Message, state: FSMContext):
    if not await db.is_admin(message.from_user.id):
        return
    await message.answer("🔢 Media kodini kiriting:\n🔙 Bekor qilish: /cancel")
    await state.set_state(AdminStates.waiting_multi_part_media)

@dp.message(AdminStates.waiting_multi_part_media)
async def multi_part_media(message: Message, state: FSMContext):
    try:
        code = int(message.text.strip())
        media = await db.get_media_by_code(code)
        if not media:
            await message.answer("❌ Media topilmadi!")
            return
        
        await db.create_multi_part_session(message.from_user.id, media["id"], media["name"])
        await message.answer(
            f"📺 <b>{media['name']}</b>\n\n🎬 <b>Ko'p qism qo'shish rejimi</b>\n\n"
            f"📌 <b>QO'LLANMA:</b>\n"
            f"1️⃣ Qism videosini yuboring\n"
            f"2️⃣ Video captioniga qism raqamini yozing (masalan: 1)\n"
            f"3️⃣ Bot qabul qilganini tasdiqlaydi\n"
            f"4️⃣ Barcha qismlarni yuborgandan so'ng /done yuboring\n\n"
            f"✅ Qabul qilingan qismlar soni: 0\n\n🔙 Bekor qilish: /cancel"
        )
        await state.set_state(MultiPartStates.waiting_video)
    except ValueError:
        await message.answer("❌ Faqat raqam kiriting!")

@dp.message(MultiPartStates.waiting_video, F.video)
async def multi_part_video(message: Message, state: FSMContext):
    session = await db.get_multi_part_session(message.from_user.id)
    if not session:
        await message.answer("❌ Sessiya topilmadi!")
        await state.clear()
        return
    
    caption = message.caption or ""
    match = re.search(r'^(\d+)', caption)
    part_number = int(match.group(1)) if match else len(json.loads(session["parts_data"] or "[]")) + 1
    
    parts = json.loads(session["parts_data"] or "[]")
    if any(p["part_number"] == part_number for p in parts):
        await message.answer(f"⚠️ {part_number}-qism allaqachon qabul qilingan!")
        return
    if await db.get_part_by_number(session["media_id"], part_number):
        await message.answer(f"⚠️ {part_number}-qism bazada mavjud!")
        return
    
    await db.add_to_multi_part_session(message.from_user.id, part_number, message.video.file_id, caption)
    session = await db.get_multi_part_session(message.from_user.id)
    parts = json.loads(session["parts_data"] or "[]")
    await message.answer(f"✅ <b>{part_number}-qism qabul qilindi!</b>\n\n📊 Jami: {len(parts)} ta qism\n\n➕ Davom eting yoki /done")

@dp.message(MultiPartStates.waiting_video, Command("done"))
async def multi_part_done(message: Message, state: FSMContext):
    session = await db.get_multi_part_session(message.from_user.id)
    if not session:
        await message.answer("❌ Sessiya topilmadi!")
        await state.clear()
        return
    
    saved = await db.save_multi_part_session(message.from_user.id)
    if saved > 0:
        await message.answer(f"✅ <b>{session['media_name']}</b> ga <b>{saved}</b> ta qism qo'shildi!\n\n🔔 Bildirishnomalar yuborildi.")
    else:
        await message.answer("❌ Hech qanday qism qo'shilmadi!")
    await state.clear()

# ================= ADMIN BROADCAST =================
@dp.message(F.text == "📨 Xabar yuborish")
async def broadcast_start(message: Message, state: FSMContext):
    if not await db.is_admin(message.from_user.id):
        return
    await message.answer("📢 <b>Xabar yuborish</b>\n\nBarcha foydalanuvchilarga yuboriladigan xabar matnini yuboring.\n\n📌 HTML formatda yozishingiz mumkin.\nRasm, video yoki matn.\n🔙 /cancel")
    await state.set_state(AdminStates.waiting_broadcast)

@dp.message(AdminStates.waiting_broadcast)
async def broadcast_send(message: Message, state: FSMContext):
    users = await db.get_all_users(only_active=True)
    sent, failed = 0, 0
    status_msg = await message.answer(f"📨 Xabar {len(users)} ta foydalanuvchiga yuborilmoqda...")
    
    for u in users:
        try:
            if message.photo:
                await bot.send_photo(u["id"], message.photo[-1].file_id, caption=message.caption or "", parse_mode=ParseMode.HTML)
            elif message.video:
                await bot.send_video(u["id"], message.video.file_id, caption=message.caption or "", parse_mode=ParseMode.HTML)
            elif message.document:
                await bot.send_document(u["id"], message.document.file_id, caption=message.caption or "", parse_mode=ParseMode.HTML)
            else:
                await bot.send_message(u["id"], message.html_text, parse_mode=ParseMode.HTML)
            sent += 1
            await asyncio.sleep(0.05)
        except:
            failed += 1
    
    await status_msg.edit_text(f"✅ <b>Xabar yuborildi!</b>\n\n✅ Muvaffaqiyatli: {sent}\n❌ Muvaffaqiyatsiz: {failed}\n📊 Jami: {len(users)} ta")

# ================= CANCEL COMMAND =================
@dp.message(Command("cancel"))
async def cancel_command(message: Message, state: FSMContext):
    if await state.get_state():
        await state.clear()
        await db.clear_multi_part_session(message.from_user.id)
        user_is_vip = await db.is_vip(message.from_user.id)
        await message.answer("✅ Amal bekor qilindi!", reply_markup=get_main_menu(user_is_vip))
    else:
        await message.answer("❌ Hech qanday amal davom etmayapti!")

# ================= GURUHDA MATN XABARLARGA JAVOB BERISH =================
@dp.message(F.text)
async def handle_text_in_group(message: Message):
    chat_type = message.chat.type
    if chat_type not in [ChatType.GROUP, ChatType.SUPERGROUP]:
        return
    
    if not await should_reply_in_group(message):
        return
    
    try:
        text = message.text.strip()
        if text.isdigit():
            code = int(text)
            media = await db.get_media_by_code(code)
            if media:
                await show_media_details(message, media["id"], await db.is_vip(message.from_user.id))
                return
    except:
        pass

@dp.callback_query()
async def unknown_callback(callback: CallbackQuery):
    await callback.answer("❌ Xato! Iltimos, qaytadan urinib ko'ring.")

# ================= BACKGROUND TASKS =================
async def vip_expiry_checker():
    while True:
        await asyncio.sleep(86400)
        await db.check_all_vip_expiry()
        logger.info("VIP expiry checked")

# ================= GURUH ADMIN KOMANDALARI =================
@dp.message(Command("enable_bot"))
async def enable_bot(message: Message):
    if message.chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP]:
        await message.answer("❌ Bu komanda faqat guruhlarda ishlaydi!")
        return
    
    member = await bot.get_chat_member(message.chat.id, message.from_user.id)
    if member.status not in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR] and message.from_user.id not in ADMINS:
        await message.answer("❌ Faqat guruh adminlari bu komandani ishlata oladi!")
        return
    
    await db.update_group_settings(message.chat.id, bot_enabled=True)
    await message.answer("✅ <b>Bot yoqildi!</b>\n\nBot endi komandalarga javob beradi.")

@dp.message(Command("disable_bot"))
async def disable_bot(message: Message):
    if message.chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP]:
        await message.answer("❌ Bu komanda faqat guruhlarda ishlaydi!")
        return
    
    member = await bot.get_chat_member(message.chat.id, message.from_user.id)
    if member.status not in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR] and message.from_user.id not in ADMINS:
        await message.answer("❌ Faqat guruh adminlari bu komandani ishlata oladi!")
        return
    
    await db.update_group_settings(message.chat.id, bot_enabled=False)
    await message.answer("❌ <b>Bot o'chirildi!</b>\n\nBot endi javob bermaydi. Qayta yoqish: /enable_bot")

# ================= MINI APP SERVER (SODDA VERSIYA) =================
MINI_APP_HTML = '''<!DOCTYPE html>
<html lang="uz">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
    <title>AniComplex | Anime World Premium</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <style>
        /* ============================================ */
        /* 1. RESET VA ASOSIY STILLAR (1-100 qator)    */
        /* ============================================ */
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            -webkit-tap-highlight-color: transparent;
        }

        :root {
            --primary: #e74c3c;
            --primary-dark: #c0392b;
            --secondary: #f39c12;
            --dark: #0a0a0f;
            --dark-card: rgba(20,20,35,0.85);
            --glass-border: rgba(231,76,60,0.3);
            --text-primary: #ffffff;
            --text-secondary: rgba(255,255,255,0.7);
            --text-muted: rgba(255,255,255,0.5);
            --success: #27ae60;
            --warning: #f39c12;
            --danger: #e74c3c;
            --info: #3498db;
            --transition-fast: 0.2s ease;
            --transition-normal: 0.3s ease;
            --transition-slow: 0.5s ease;
            --border-radius-sm: 12px;
            --border-radius-md: 18px;
            --border-radius-lg: 25px;
            --border-radius-xl: 35px;
            --border-radius-xxl: 60px;
            --shadow-sm: 0 2px 8px rgba(0,0,0,0.1);
            --shadow-md: 0 4px 15px rgba(0,0,0,0.2);
            --shadow-lg: 0 8px 30px rgba(0,0,0,0.3);
            --shadow-glow: 0 0 20px rgba(231,76,60,0.3);
            --shadow-glow-strong: 0 0 40px rgba(231,76,60,0.6);
        }

        body {
            font-family: 'Poppins', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', sans-serif;
            background: var(--dark);
            color: var(--text-primary);
            min-height: 100vh;
            overflow-x: hidden;
            position: relative;
            line-height: 1.5;
            -webkit-font-smoothing: antialiased;
            -moz-osx-font-smoothing: grayscale;
        }

        /* ============================================ */
        /* 2. FON VE ZARARCHALAR (101-250 qator)       */
        /* ============================================ */
        .bg-gradient {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            z-index: 0;
            background: radial-gradient(circle at 20% 30%, #1a1a2e, #0a0a0f);
        }

        .bg-gradient::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: url('data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSI0MCIgaGVpZ2h0PSI0MCIgdmlld0JveD0iMCAwIDQwIDQwIj48cGF0aCBmaWxsPSIjZTc0YzNjIiBmaWxsLW9wYWNpdHk9IjAuMDUiIGQ9Ik0wIDBoNDB2NDBIMHoiLz48L3N2Zz4=');
            background-repeat: repeat;
            opacity: 0.3;
            pointer-events: none;
        }

        .particles {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            z-index: 1;
            pointer-events: none;
            overflow: hidden;
        }

        .particle {
            position: absolute;
            border-radius: 50%;
            animation: floatParticle linear infinite;
        }

        @keyframes floatParticle {
            0% {
                transform: translateY(100vh) scale(0);
                opacity: 0;
            }
            10% {
                opacity: 0.8;
            }
            90% {
                opacity: 0.8;
            }
            100% {
                transform: translateY(-10vh) scale(1);
                opacity: 0;
            }
        }

        /* ============================================ */
        /* 3. GLASS MORPHISM KOMPONENTLARI (251-400)    */
        /* ============================================ */
        .glass-card {
            background: var(--dark-card);
            backdrop-filter: blur(20px);
            border-radius: var(--border-radius-lg);
            border: 1px solid var(--glass-border);
            box-shadow: var(--shadow-md);
            transition: all var(--transition-normal);
        }

        .glass-card:hover {
            border-color: var(--primary);
            box-shadow: var(--shadow-glow);
            transform: translateY(-2px);
        }

        .glass-card-dark {
            background: rgba(10,10,20,0.8);
            backdrop-filter: blur(15px);
            border-radius: var(--border-radius-md);
            border: 1px solid rgba(255,255,255,0.08);
        }

        /* ============================================ */
        /* 4. ANIMATSIYALAR (401-550)                  */
        /* ============================================ */
        @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }

        @keyframes fadeInUp {
            from {
                opacity: 0;
                transform: translateY(30px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }

        @keyframes fadeInDown {
            from {
                opacity: 0;
                transform: translateY(-30px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }

        @keyframes fadeInLeft {
            from {
                opacity: 0;
                transform: translateX(-30px);
            }
            to {
                opacity: 1;
                transform: translateX(0);
            }
        }

        @keyframes fadeInRight {
            from {
                opacity: 0;
                transform: translateX(30px);
            }
            to {
                opacity: 1;
                transform: translateX(0);
            }
        }

        @keyframes slideUp {
            from {
                opacity: 0;
                transform: translateY(50px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }

        @keyframes slideDown {
            from {
                opacity: 0;
                transform: translateY(-50px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }

        @keyframes scaleIn {
            from {
                opacity: 0;
                transform: scale(0.9);
            }
            to {
                opacity: 1;
                transform: scale(1);
            }
        }

        @keyframes pulse {
            0%, 100% {
                transform: scale(1);
                box-shadow: var(--shadow-glow);
            }
            50% {
                transform: scale(1.02);
                box-shadow: var(--shadow-glow-strong);
            }
        }

        @keyframes pulse-fast {
            0%, 100% {
                transform: scale(1);
            }
            50% {
                transform: scale(1.05);
            }
        }

        @keyframes shimmer {
            0% {
                background-position: -200% 0;
            }
            100% {
                background-position: 200% 0;
            }
        }

        @keyframes spin {
            from {
                transform: rotate(0deg);
            }
            to {
                transform: rotate(360deg);
            }
        }

        @keyframes spin-slow {
            from {
                transform: rotate(0deg);
            }
            to {
                transform: rotate(360deg);
            }
        }

        @keyframes bounce {
            0%, 100% {
                transform: translateY(0);
            }
            50% {
                transform: translateY(-8px);
            }
        }

        @keyframes bounce-soft {
            0%, 100% {
                transform: translateY(0);
            }
            50% {
                transform: translateY(-4px);
            }
        }

        @keyframes heartBeat {
            0%, 100% {
                transform: scale(1);
            }
            25% {
                transform: scale(1.3);
            }
            50% {
                transform: scale(1.1);
            }
            75% {
                transform: scale(1.2);
            }
        }

        @keyframes shake {
            0%, 100% {
                transform: translateX(0);
            }
            25% {
                transform: translateX(-5px);
            }
            75% {
                transform: translateX(5px);
            }
        }

        @keyframes glow {
            0%, 100% {
                box-shadow: var(--shadow-glow);
            }
            50% {
                box-shadow: var(--shadow-glow-strong);
            }
        }

        @keyframes rotate360 {
            from {
                transform: rotate(0deg);
            }
            to {
                transform: rotate(360deg);
            }
        }

        @keyframes ripple {
            0% {
                transform: scale(0);
                opacity: 0.6;
            }
            100% {
                transform: scale(3);
                opacity: 0;
            }
        }

        @keyframes float {
            0%, 100% {
                transform: translateY(0px);
            }
            50% {
                transform: translateY(-10px);
            }
        }

        @keyframes float-slow {
            0%, 100% {
                transform: translateY(0px);
            }
            50% {
                transform: translateY(-15px);
            }
        }

        @keyframes zoomIn {
            from {
                opacity: 0;
                transform: scale(0.8);
            }
            to {
                opacity: 1;
                transform: scale(1);
            }
        }

        @keyframes zoomOut {
            from {
                opacity: 1;
                transform: scale(1);
            }
            to {
                opacity: 0;
                transform: scale(0.8);
            }
        }

        .animate-fade-in { animation: fadeIn 0.5s ease forwards; }
        .animate-fade-in-up { animation: fadeInUp 0.6s ease forwards; }
        .animate-fade-in-down { animation: fadeInDown 0.6s ease forwards; }
        .animate-fade-in-left { animation: fadeInLeft 0.5s ease forwards; }
        .animate-fade-in-right { animation: fadeInRight 0.5s ease forwards; }
        .animate-slide-up { animation: slideUp 0.6s ease forwards; }
        .animate-slide-down { animation: slideDown 0.6s ease forwards; }
        .animate-scale-in { animation: scaleIn 0.4s ease forwards; }
        .animate-pulse { animation: pulse 2s infinite; }
        .animate-pulse-fast { animation: pulse-fast 1s infinite; }
        .animate-bounce { animation: bounce 2s infinite; }
        .animate-bounce-soft { animation: bounce-soft 1.5s infinite; }
        .animate-spin { animation: spin 1s linear infinite; }
        .animate-spin-slow { animation: spin-slow 3s linear infinite; }
        .animate-float { animation: float 3s ease-in-out infinite; }
        .animate-float-slow { animation: float-slow 4s ease-in-out infinite; }
        .animate-glow { animation: glow 2s infinite; }
        .animate-shimmer { animation: shimmer 2s infinite; }

        /* ============================================ */
        /* 5. CONTAINER VA LAYOUT (551-650)            */
        /* ============================================ */
        .container {
            position: relative;
            z-index: 2;
            max-width: 550px;
            margin: 0 auto;
            padding: 20px 16px 90px;
            min-height: 100vh;
        }

        /* ============================================ */
        /* 6. HEADER STILLARI (651-750)                */
        /* ============================================ */
        .header {
            text-align: center;
            padding: 30px 20px;
            margin-bottom: 25px;
            position: relative;
            overflow: hidden;
            animation: fadeInUp 0.6s ease;
        }

        .header::before {
            content: '';
            position: absolute;
            top: -50%;
            left: -50%;
            width: 200%;
            height: 200%;
            background: linear-gradient(45deg, transparent, rgba(231,76,60,0.08), transparent);
            animation: rotate360 12s linear infinite;
            pointer-events: none;
        }

        .header::after {
            content: '';
            position: absolute;
            bottom: 0;
            left: 10%;
            width: 80%;
            height: 2px;
            background: linear-gradient(90deg, transparent, var(--primary), var(--secondary), var(--primary), transparent);
            border-radius: 2px;
        }

        .header h1 {
            font-size: 44px;
            font-weight: 800;
            background: linear-gradient(135deg, var(--primary), var(--secondary), var(--primary));
            background-size: 200% auto;
            -webkit-background-clip: text;
            background-clip: text;
            -webkit-text-fill-color: transparent;
            animation: shimmer 3s linear infinite;
            position: relative;
            z-index: 1;
            letter-spacing: -0.5px;
        }

        .header .subtitle {
            color: var(--text-secondary);
            font-size: 14px;
            margin-top: 8px;
            position: relative;
            z-index: 1;
        }

        .header-badge {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            background: linear-gradient(135deg, var(--success), #2ecc71);
            padding: 6px 16px;
            border-radius: var(--border-radius-xxl);
            font-size: 12px;
            font-weight: 600;
            margin-top: 12px;
            animation: bounce 2s infinite;
        }

        /* ============================================ */
        /* 7. AUTH FORM STILLARI (751-850)             */
        /* ============================================ */
        .auth-card {
            padding: 40px 28px;
            text-align: center;
            animation: fadeInUp 0.7s ease;
        }

        .auth-card h2 {
            font-size: 28px;
            margin-bottom: 25px;
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            -webkit-background-clip: text;
            background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .auth-card .auth-icon {
            font-size: 60px;
            margin-bottom: 15px;
            animation: bounce 2s infinite;
        }

        .auth-input {
            width: 100%;
            padding: 16px 20px;
            margin: 12px 0;
            background: rgba(255,255,255,0.08);
            border: 1.5px solid rgba(255,255,255,0.12);
            border-radius: var(--border-radius-xxl);
            color: var(--text-primary);
            font-size: 15px;
            transition: all var(--transition-normal);
            outline: none;
        }

        .auth-input:focus {
            border-color: var(--primary);
            box-shadow: 0 0 20px rgba(231,76,60,0.3);
            transform: scale(1.02);
        }

        .auth-input::placeholder {
            color: var(--text-muted);
        }

        /* ============================================ */
        /* 8. BUTTONLAR (851-950)                      */
        /* ============================================ */
        .btn {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            padding: 14px 24px;
            border: none;
            border-radius: var(--border-radius-xxl);
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: all var(--transition-normal);
            text-decoration: none;
        }

        .btn-primary {
            background: linear-gradient(135deg, var(--primary), var(--primary-dark));
            color: white;
            box-shadow: var(--shadow-sm);
        }

        .btn-primary:hover {
            transform: translateY(-2px);
            box-shadow: var(--shadow-glow);
        }

        .btn-primary:active {
            transform: scale(0.96);
        }

        .btn-secondary {
            background: rgba(255,255,255,0.1);
            color: var(--text-primary);
            border: 1px solid rgba(255,255,255,0.15);
        }

        .btn-secondary:active {
            transform: scale(0.96);
        }

        .btn-outline {
            background: transparent;
            border: 1.5px solid var(--primary);
            color: var(--primary);
        }

        .btn-outline:active {
            transform: scale(0.96);
        }

        .btn-glow {
            background: linear-gradient(135deg, var(--primary), var(--primary-dark));
            border: none;
            border-radius: var(--border-radius-xxl);
            padding: 14px 28px;
            color: white;
            font-weight: 600;
            font-size: 16px;
            cursor: pointer;
            width: 100%;
            animation: pulse 2s infinite;
            transition: all var(--transition-normal);
        }

        .btn-glow:active {
            transform: scale(0.96);
        }

        .btn-block {
            width: 100%;
        }

        .btn-sm {
            padding: 8px 16px;
            font-size: 13px;
        }

        .btn-lg {
            padding: 16px 32px;
            font-size: 18px;
        }

        .search-btn {
            background: linear-gradient(135deg, var(--primary), var(--primary-dark));
            border: none;
            border-radius: var(--border-radius-xxl);
            padding: 12px 28px;
            color: white;
            cursor: pointer;
            transition: all var(--transition-normal);
        }

        .search-btn:active {
            transform: scale(0.95);
        }

        /* ============================================ */
        /* 9. SEARCH BAR STILLARI (951-1050)           */
        /* ============================================ */
        .search-container {
            margin-bottom: 20px;
            animation: fadeInUp 0.6s ease;
        }

        .search-bar {
            display: flex;
            gap: 10px;
            background: rgba(255,255,255,0.08);
            border-radius: var(--border-radius-xxl);
            padding: 6px;
            border: 1px solid var(--glass-border);
            transition: all var(--transition-normal);
        }

        .search-bar:focus-within {
            border-color: var(--primary);
            box-shadow: var(--shadow-glow);
            transform: scale(1.01);
        }

        .search-bar input {
            flex: 1;
            background: transparent;
            border: none;
            padding: 14px 20px;
            color: var(--text-primary);
            font-size: 15px;
            outline: none;
        }

        .search-bar input::placeholder {
            color: var(--text-muted);
        }

        /* ============================================ */
        /* 10. TABS STILLARI (1051-1150)               */
        /* ============================================ */
        .tabs {
            display: flex;
            gap: 10px;
            margin: 20px 0 25px;
            overflow-x: auto;
            padding-bottom: 5px;
            animation: fadeInUp 0.7s ease;
            scrollbar-width: none;
            -ms-overflow-style: none;
        }

        .tabs::-webkit-scrollbar {
            display: none;
        }

        .tab {
            padding: 10px 22px;
            background: rgba(255,255,255,0.08);
            border: 1px solid rgba(255,255,255,0.12);
            border-radius: var(--border-radius-xxl);
            color: var(--text-secondary);
            font-size: 13px;
            font-weight: 600;
            cursor: pointer;
            white-space: nowrap;
            transition: all var(--transition-normal);
        }

        .tab:hover {
            background: rgba(255,255,255,0.15);
            transform: translateY(-1px);
        }

        .tab.active {
            background: linear-gradient(135deg, var(--primary), var(--primary-dark));
            color: white;
            border-color: transparent;
            animation: pulse 2s infinite;
        }

        /* ============================================ */
        /* 11. MEDIA GRID VA KARTALAR (1151-1300)      */
        /* ============================================ */
        .media-grid {
            display: flex;
            flex-direction: column;
            gap: 16px;
            margin: 20px 0 30px;
        }

        .media-card {
            background: linear-gradient(135deg, rgba(25,25,40,0.85), rgba(15,15,25,0.9));
            backdrop-filter: blur(12px);
            border-radius: var(--border-radius-md);
            overflow: hidden;
            border: 1px solid rgba(231,76,60,0.2);
            cursor: pointer;
            transition: all var(--transition-normal);
            display: flex;
            animation: fadeInUp 0.5s ease;
            position: relative;
        }

        .media-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: linear-gradient(135deg, transparent, rgba(231,76,60,0.05), transparent);
            opacity: 0;
            transition: opacity var(--transition-normal);
            pointer-events: none;
        }

        .media-card:hover::before {
            opacity: 1;
        }

        .media-card:hover {
            transform: translateX(8px) scale(1.01);
            border-color: var(--primary);
            box-shadow: 0 8px 25px rgba(231,76,60,0.25);
        }

        .media-card:active {
            transform: scale(0.98);
        }

        .media-card img {
            width: 110px;
            height: 150px;
            object-fit: cover;
            flex-shrink: 0;
            transition: transform var(--transition-normal);
        }

        .media-card:hover img {
            transform: scale(1.05);
        }

        .media-info {
            padding: 14px;
            flex: 1;
            display: flex;
            flex-direction: column;
            gap: 6px;
        }

        .media-title {
            font-size: 16px;
            font-weight: 700;
            margin-bottom: 4px;
            display: -webkit-box;
            -webkit-line-clamp: 2;
            -webkit-box-orient: vertical;
            overflow: hidden;
        }

        .media-meta {
            font-size: 12px;
            color: var(--text-secondary);
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
        }

        .media-badge {
            display: inline-flex;
            align-items: center;
            gap: 4px;
            padding: 2px 8px;
            background: rgba(0,0,0,0.3);
            border-radius: 20px;
            font-size: 10px;
        }

        .rating-stars {
            color: var(--secondary);
            font-size: 11px;
            margin-top: 4px;
        }

        .media-stats {
            display: flex;
            gap: 12px;
            margin-top: 6px;
            font-size: 11px;
            color: var(--text-muted);
        }

        /* ============================================ */
        /* 12. PLAYER SECTION (1301-1450)              */
        /* ============================================ */
        .player-section {
            background: linear-gradient(135deg, rgba(20,20,35,0.95), rgba(10,10,20,0.98));
            backdrop-filter: blur(20px);
            border-radius: var(--border-radius-lg);
            padding: 18px;
            animation: scaleIn 0.5s ease;
        }

        .player-section video {
            width: 100%;
            border-radius: var(--border-radius-md);
            background: #000;
            box-shadow: var(--shadow-md);
        }

        .player-title {
            font-size: 18px;
            font-weight: 700;
            margin: 12px 0 8px;
            text-align: center;
        }

        .player-info {
            display: flex;
            justify-content: space-between;
            margin: 10px 0;
            padding: 8px 12px;
            background: rgba(0,0,0,0.3);
            border-radius: var(--border-radius-sm);
            font-size: 12px;
        }

        /* ============================================ */
        /* 13. QISM BUTTONLARI (1451-1550)             */
        /* ============================================ */
        .part-buttons {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            margin: 18px 0;
        }

        .part-btn {
            background: rgba(255,255,255,0.08);
            border: 1px solid rgba(255,255,255,0.12);
            border-radius: var(--border-radius-sm);
            padding: 10px 18px;
            color: var(--text-primary);
            font-size: 13px;
            font-weight: 500;
            cursor: pointer;
            transition: all var(--transition-fast);
        }

        .part-btn:hover {
            background: rgba(255,255,255,0.15);
            transform: translateY(-1px);
        }

        .part-btn.active {
            background: linear-gradient(135deg, var(--primary), var(--primary-dark));
            border-color: transparent;
        }

        .part-btn:active {
            transform: scale(0.94);
        }

        /* ============================================ */
        /* 14. ACTION BUTTONLARI (1551-1650)           */
        /* ============================================ */
        .action-buttons {
            display: flex;
            gap: 15px;
            margin: 18px 0;
        }

        .action-btn {
            display: flex;
            align-items: center;
            gap: 8px;
            background: rgba(255,255,255,0.08);
            border: 1px solid rgba(255,255,255,0.12);
            border-radius: var(--border-radius-xxl);
            padding: 10px 22px;
            color: var(--text-primary);
            cursor: pointer;
            transition: all var(--transition-normal);
            font-size: 14px;
            font-weight: 500;
        }

        .action-btn:hover {
            background: rgba(255,255,255,0.15);
            transform: translateY(-1px);
        }

        .action-btn:active {
            transform: scale(0.95);
        }

        .action-btn.liked {
            background: linear-gradient(135deg, var(--primary), var(--primary-dark));
            animation: heartBeat 0.5s ease;
        }

        /* ============================================ */
        /* 15. COMMENTS SEKTSIYASI (1651-1780)         */
        /* ============================================ */
        .comments-section {
            margin: 18px 0;
            background: rgba(0,0,0,0.3);
            border-radius: var(--border-radius-md);
            padding: 15px;
            animation: slideUp 0.3s ease;
        }

        .comments-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }

        .comments-count {
            font-size: 13px;
            color: var(--text-muted);
        }

        .comment {
            background: rgba(0,0,0,0.35);
            border-radius: var(--border-radius-md);
            padding: 12px;
            margin: 10px 0;
            animation: fadeInLeft 0.3s ease;
            transition: all var(--transition-fast);
        }

        .comment:hover {
            background: rgba(0,0,0,0.5);
            transform: translateX(3px);
        }

        .comment-header {
            display: flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 6px;
        }

        .comment-avatar {
            width: 28px;
            height: 28px;
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 12px;
        }

        .comment-user {
            font-weight: 700;
            color: var(--primary);
            font-size: 13px;
        }

        .comment-time {
            font-size: 10px;
            color: var(--text-muted);
            margin-left: auto;
        }

        .comment-text {
            font-size: 13px;
            margin-top: 6px;
            padding-left: 36px;
            color: var(--text-secondary);
            line-height: 1.4;
        }

        .comment-input {
            display: flex;
            gap: 10px;
            margin-top: 18px;
        }

        .comment-input input {
            flex: 1;
            background: rgba(0,0,0,0.4);
            border: 1px solid rgba(255,255,255,0.15);
            border-radius: var(--border-radius-xxl);
            padding: 12px 18px;
            color: var(--text-primary);
            font-size: 14px;
            outline: none;
            transition: all var(--transition-normal);
        }

        .comment-input input:focus {
            border-color: var(--primary);
            box-shadow: 0 0 10px rgba(231,76,60,0.2);
        }

        .comment-input button {
            background: linear-gradient(135deg, var(--primary), var(--primary-dark));
            border: none;
            border-radius: var(--border-radius-xxl);
            padding: 12px 22px;
            color: white;
            font-weight: 600;
            cursor: pointer;
            transition: all var(--transition-normal);
        }

        .comment-input button:active {
            transform: scale(0.95);
        }

        /* ============================================ */
        /* 16. LOADING SKELETON (1781-1880)            */
        /* ============================================ */
        .skeleton {
            background: linear-gradient(90deg, rgba(255,255,255,0.06) 25%, rgba(255,255,255,0.12) 50%, rgba(255,255,255,0.06) 75%);
            background-size: 200% 100%;
            animation: shimmer 1.5s infinite;
            border-radius: var(--border-radius-md);
        }

        .skeleton-card {
            display: flex;
            gap: 12px;
            padding: 12px;
            background: rgba(255,255,255,0.05);
            border-radius: var(--border-radius-md);
            margin-bottom: 12px;
        }

        .skeleton-img {
            width: 100px;
            height: 140px;
            border-radius: var(--border-radius-sm);
        }

        .skeleton-text {
            height: 14px;
            margin: 8px 0;
            border-radius: 7px;
        }

        .skeleton-title {
            height: 18px;
            width: 70%;
            margin-bottom: 12px;
        }

        /* ============================================ */
        /* 17. EMPTY STATE (1881-1950)                 */
        /* ============================================ */
        .empty-state {
            text-align: center;
            padding: 60px 20px;
            background: rgba(255,255,255,0.05);
            border-radius: var(--border-radius-lg);
            animation: fadeInUp 0.6s ease;
        }

        .empty-state .icon {
            font-size: 80px;
            margin-bottom: 20px;
            animation: bounce 2s infinite;
        }

        .empty-state h3 {
            font-size: 20px;
            margin-bottom: 10px;
        }

        .empty-state p {
            color: var(--text-muted);
            font-size: 14px;
            margin-bottom: 20px;
        }

        /* ============================================ */
        /* 18. BOTTOM NAVIGATION (1951-2050)           */
        /* ============================================ */
        .bottom-nav {
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            background: linear-gradient(135deg, rgba(15,15,25,0.98), rgba(10,10,20,0.98));
            backdrop-filter: blur(20px);
            border-top: 1px solid rgba(231,76,60,0.4);
            padding: 10px 20px;
            display: flex;
            justify-content: space-around;
            z-index: 100;
            animation: slideUp 0.8s ease;
        }

        .nav-item {
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 4px;
            background: none;
            border: none;
            color: var(--text-muted);
            font-size: 11px;
            cursor: pointer;
            padding: 8px 18px;
            border-radius: var(--border-radius-xxl);
            transition: all var(--transition-normal);
        }

        .nav-item:hover {
            color: var(--primary);
            transform: translateY(-2px);
        }

        .nav-item.active {
            color: var(--primary);
            background: rgba(231,76,60,0.15);
        }

        .nav-item:active {
            transform: scale(0.94);
        }

        .nav-icon {
            font-size: 24px;
            margin-bottom: 2px;
        }

        /* ============================================ */
        /* 19. TOAST NOTIFICATION (2051-2120)          */
        /* ============================================ */
        .toast {
            position: fixed;
            bottom: 100px;
            left: 50%;
            transform: translateX(-50%);
            background: rgba(0,0,0,0.95);
            backdrop-filter: blur(10px);
            color: white;
            padding: 12px 28px;
            border-radius: var(--border-radius-xxl);
            font-size: 14px;
            z-index: 200;
            animation: slideUp 0.3s ease;
            border-left: 4px solid var(--primary);
            white-space: nowrap;
            max-width: 90%;
            white-space: normal;
            text-align: center;
            box-shadow: var(--shadow-lg);
        }

        .toast-success {
            border-left-color: var(--success);
        }

        .toast-error {
            border-left-color: var(--danger);
        }

        .toast-warning {
            border-left-color: var(--warning);
        }

        /* ============================================ */
        /* 20. MODAL DIALOG (2121-2200)                */
        /* ============================================ */
        .modal {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.8);
            backdrop-filter: blur(8px);
            z-index: 300;
            display: flex;
            align-items: center;
            justify-content: center;
            animation: fadeIn 0.3s ease;
        }

        .modal-content {
            background: linear-gradient(135deg, rgba(25,25,40,0.98), rgba(15,15,25,0.98));
            backdrop-filter: blur(20px);
            border-radius: var(--border-radius-lg);
            padding: 25px;
            width: 90%;
            max-width: 350px;
            text-align: center;
            animation: scaleIn 0.3s ease;
            border: 1px solid rgba(231,76,60,0.3);
        }

        .modal-content h3 {
            margin-bottom: 15px;
            font-size: 22px;
        }

        .modal-buttons {
            display: flex;
            gap: 12px;
            margin-top: 20px;
        }

        .modal-buttons button {
            flex: 1;
        }

        /* ============================================ */
        /* 21. UTILITY CLASSES (2201-2300)             */
        /* ============================================ */
        .hidden { display: none !important; }
        .text-center { text-align: center; }
        .text-left { text-align: left; }
        .text-right { text-align: right; }
        .text-primary { color: var(--primary); }
        .text-secondary { color: var(--secondary); }
        .text-success { color: var(--success); }
        .text-muted { color: var(--text-muted); }
        .mt-0 { margin-top: 0; }
        .mt-1 { margin-top: 4px; }
        .mt-2 { margin-top: 8px; }
        .mt-3 { margin-top: 12px; }
        .mt-4 { margin-top: 16px; }
        .mt-5 { margin-top: 20px; }
        .mb-0 { margin-bottom: 0; }
        .mb-1 { margin-bottom: 4px; }
        .mb-2 { margin-bottom: 8px; }
        .mb-3 { margin-bottom: 12px; }
        .mb-4 { margin-bottom: 16px; }
        .mb-5 { margin-bottom: 20px; }
        .mx-auto { margin-left: auto; margin-right: auto; }
        .w-100 { width: 100%; }
        .cursor-pointer { cursor: pointer; }
        .rounded-full { border-radius: var(--border-radius-xxl); }
        .rounded-lg { border-radius: var(--border-radius-lg); }
        .rounded-md { border-radius: var(--border-radius-md); }
        .shadow-glow { box-shadow: var(--shadow-glow); }
    </style>
</head>
<body>

<div class="bg-gradient"></div>
<div class="particles" id="particles"></div>

<div class="container">
    <!-- HEADER -->
    <div class="header glass-card">
        <h1>🎬 AniComplex</h1>
        <p class="subtitle">Anime olamiga xush kelibsiz!</p>
        <div class="header-badge hidden" id="userBadge">👤 Foydalanuvchi</div>
    </div>

    <!-- AUTH SECTION -->
    <div id="authSection" class="auth-card glass-card">
        <div class="auth-icon">🎭</div>
        <h2>📝 Ro'yxatdan o'tish</h2>
        <input type="text" id="firstNameInput" class="auth-input" placeholder="👤 Ismingiz" autocomplete="off">
        <input type="text" id="usernameInput" class="auth-input" placeholder="📱 Telegram username" autocomplete="off">
        <button class="btn-glow" onclick="register()">✅ Kirish</button>
        <p class="text-muted mt-3" style="font-size: 12px;">Telegram orqali avtomatik tizimga kirasiz</p>
    </div>

    <!-- MAIN SECTION -->
    <div id="mainSection" class="hidden">
        <div class="search-container">
            <div class="search-bar">
                <input type="text" id="searchInput" placeholder="🔍 Anime qidirish (nomi, kod, janr...)">
                <button class="search-btn" onclick="searchAnime()">🔍</button>
            </div>
        </div>

        <div class="tabs" id="tabs">
            <button class="tab active" onclick="loadTab('all')">📋 Barchasi</button>
            <button class="tab" onclick="loadTab('ongoing')">🟢 Davom etmoqda</button>
            <button class="tab" onclick="loadTab('completed')">✅ Tugallangan</button>
            <button class="tab" onclick="loadTab('popular')">🏆 Mashhur</button>
            <button class="tab" onclick="loadTab('vip')">👑 VIP</button>
            <button class="tab" onclick="loadTab('recent')">🆕 Yangi</button>
        </div>

        <div id="mediaGrid" class="media-grid">
            <!-- skeleton loader -->
            <div class="skeleton-card">
                <div class="skeleton-img skeleton"></div>
                <div style="flex:1">
                    <div class="skeleton skeleton-title"></div>
                    <div class="skeleton skeleton-text" style="width:60%"></div>
                    <div class="skeleton skeleton-text" style="width:40%"></div>
                    <div class="skeleton skeleton-text" style="width:50%"></div>
                </div>
            </div>
            <div class="skeleton-card">
                <div class="skeleton-img skeleton"></div>
                <div style="flex:1">
                    <div class="skeleton skeleton-title"></div>
                    <div class="skeleton skeleton-text" style="width:60%"></div>
                    <div class="skeleton skeleton-text" style="width:40%"></div>
                    <div class="skeleton skeleton-text" style="width:50%"></div>
                </div>
            </div>
            <div class="skeleton-card">
                <div class="skeleton-img skeleton"></div>
                <div style="flex:1">
                    <div class="skeleton skeleton-title"></div>
                    <div class="skeleton skeleton-text" style="width:60%"></div>
                    <div class="skeleton skeleton-text" style="width:40%"></div>
                    <div class="skeleton skeleton-text" style="width:50%"></div>
                </div>
            </div>
        </div>

        <div id="playerSection" class="player-section hidden">
            <video id="videoPlayer" controls preload="metadata"></video>
            <h3 id="playerTitle" class="player-title"></h3>
            <div class="player-info">
                <span>⭐ <span id="playerRating">0</span>/10</span>
                <span>👁 <span id="playerViews">0</span></span>
                <span>📀 <span id="playerParts">0</span> qism</span>
            </div>
            <div class="action-buttons">
                <button class="action-btn" id="likeBtn" onclick="toggleLike()">❤️ <span id="likeCount">0</span></button>
                <button class="action-btn" onclick="toggleComments()">💬 <span id="commentCount">0</span></button>
                <button class="action-btn" onclick="shareMedia()">📤 Ulashish</button>
            </div>
            <div id="commentsSection" class="comments-section hidden">
                <div class="comments-header">
                    <span>💬 Izohlar</span>
                    <span class="comments-count" id="commentsCount">0 ta izoh</span>
                </div>
                <div id="commentsList"></div>
                <div class="comment-input">
                    <input type="text" id="commentInput" placeholder="Izoh yozing...">
                    <button onclick="addComment()">➤ Yuborish</button>
                </div>
            </div>
            <div class="part-buttons" id="partButtons"></div>
            <button class="btn-primary btn-block" onclick="closePlayer()" style="margin-top: 10px;">🔙 Orqaga</button>
        </div>
    </div>
</div>

<div class="bottom-nav hidden" id="bottomNav">
    <button class="nav-item active" onclick="loadTab('all')"><span class="nav-icon">🏠</span> Bosh</button>
    <button class="nav-item" onclick="scrollToSearch()"><span class="nav-icon">🔍</span> Qidiruv</button>
    <button class="nav-item" onclick="loadTab('popular')"><span class="nav-icon">🔥</span> Mashhur</button>
    <button class="nav-item" onclick="loadTab('ongoing')"><span class="nav-icon">🆕</span> Yangi</button>
    <button class="nav-item" onclick="showProfile()"><span class="nav-icon">👤</span> Profil</button>
</div>

<script>
// ============================================ //
// 1. TELEGRAM WEBAPP INIT (2301-2350)         //
// ============================================ //
const tg = window.Telegram.WebApp;
tg.ready();
tg.expand();
tg.enableClosingConfirmation();

// ============================================ //
// 2. PARTICLES GENERATION (2351-2400)         //
// ============================================ //
function generateParticles() {
    const container = document.getElementById('particles');
    for (let i = 0; i < 80; i++) {
        const particle = document.createElement('div');
        particle.className = 'particle';
        const size = Math.random() * 5 + 2;
        const duration = Math.random() * 18 + 8;
        const delay = Math.random() * 12;
        const colors = ['#e74c3c', '#f39c12', 'rgba(255,255,255,0.5)', '#3498db', '#2ecc71'];
        const randomColor = colors[Math.floor(Math.random() * colors.length)];
        particle.style.cssText = `
            width: ${size}px;
            height: ${size}px;
            left: ${Math.random() * 100}%;
            background: ${randomColor};
            animation-duration: ${duration}s;
            animation-delay: ${delay}s;
        `;
        container.appendChild(particle);
    }
}
generateParticles();

// ============================================ //
// 3. GLOBAL VARIABLES (2401-2450)             //
// ============================================ //
let currentUser = null;
let currentMedia = null;
let currentPart = 1;
let isLiked = false;
let mediaData = [];
let allGenres = [];
let watchHistory = [];
let favorites = [];
let notifications = [];

// ============================================ //
// 4. LOCAL STORAGE FUNCTIONS (2451-2500)      //
// ============================================ //
function saveToLocalStorage(key, data) {
    try {
        localStorage.setItem(`anicomplex_${key}`, JSON.stringify(data));
    } catch(e) {
        console.error('LocalStorage error:', e);
    }
}

function loadFromLocalStorage(key) {
    try {
        const data = localStorage.getItem(`anicomplex_${key}`);
        return data ? JSON.parse(data) : null;
    } catch(e) {
        return null;
    }
}

function saveUserData() {
    if (currentUser) {
        saveToLocalStorage('user', currentUser);
    }
}

function loadUserData() {
    const user = loadFromLocalStorage('user');
    if (user) {
        currentUser = user;
    }
}

// ============================================ //
// 5. AUTHENTICATION FUNCTIONS (2501-2600)     //
// ============================================ //
function checkAuth() {
    loadUserData();
    if (currentUser && currentUser.id) {
        document.getElementById('authSection').classList.add('hidden');
        document.getElementById('mainSection').classList.remove('hidden');
        document.getElementById('bottomNav').classList.remove('hidden');
        document.getElementById('userBadge').classList.remove('hidden');
        document.getElementById('userBadge').innerHTML = `👤 ${currentUser.first_name || 'User'}`;
        loadMedia();
        loadUserPreferences();
    }
}

function register() {
    const firstName = document.getElementById('firstNameInput').value.trim();
    const username = document.getElementById('usernameInput').value.trim();
    
    if (!firstName) {
        showToast("❌ Iltimos, ismingizni kiriting!", true);
        tg.HapticFeedback.notificationOccurred('error');
        return;
    }
    
    const telegramUser = tg.initDataUnsafe?.user;
    
    currentUser = {
        id: telegramUser?.id || Date.now(),
        first_name: firstName,
        username: username || telegramUser?.username || firstName,
        last_name: telegramUser?.last_name || '',
        language_code: telegramUser?.language_code || 'uz',
        is_premium: telegramUser?.is_premium || false,
        registered_at: new Date().toISOString(),
        last_active: new Date().toISOString(),
        preferences: {
            theme: 'dark',
            notifications: true,
            auto_play: false
        }
    };
    
    saveUserData();
    
    // API ga yuborish
    fetch('/api/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(currentUser)
    }).catch(() => console.log('API not available'));
    
    showToast(`✅ Xush kelibsiz, ${firstName}!`);
    tg.HapticFeedback.notificationOccurred('success');
    
    document.getElementById('authSection').classList.add('hidden');
    document.getElementById('mainSection').classList.remove('hidden');
    document.getElementById('bottomNav').classList.remove('hidden');
    document.getElementById('userBadge').classList.remove('hidden');
    document.getElementById('userBadge').innerHTML = `👤 ${firstName}`;
    
    loadMedia();
    loadUserPreferences();
}

function loadUserPreferences() {
    favorites = loadFromLocalStorage('favorites') || [];
    watchHistory = loadFromLocalStorage('watchHistory') || [];
    notifications = loadFromLocalStorage('notifications') || [];
}

function saveFavorites() {
    saveToLocalStorage('favorites', favorites);
}

function saveWatchHistory() {
    saveToLocalStorage('watchHistory', watchHistory.slice(0, 50));
}

function addToWatchHistory(mediaId, partNumber) {
    watchHistory.unshift({
        media_id: mediaId,
        part_number: partNumber,
        timestamp: new Date().toISOString()
    });
    if (watchHistory.length > 50) watchHistory.pop();
    saveWatchHistory();
}

// ============================================ //
// 6. TOAST NOTIFICATION (2601-2650)           //
// ============================================ //
function showToast(message, isError = false, duration = 2500) {
    const existingToast = document.querySelector('.toast');
    if (existingToast) existingToast.remove();
    
    const toast = document.createElement('div');
    toast.className = 'toast';
    if (isError) toast.classList.add('toast-error');
    toast.textContent = message;
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.style.animation = 'zoomOut 0.3s ease forwards';
        setTimeout(() => toast.remove(), 300);
    }, duration);
}

// ============================================ //
// 7. MEDIA LOADING FROM BOT (2651-2750)       //
// ============================================ //
async function loadMedia() {
    const grid = document.getElementById('mediaGrid');
    
    // Show skeletons
    grid.innerHTML = '';
    for (let i = 0; i < 4; i++) {
        grid.innerHTML += `
            <div class="skeleton-card">
                <div class="skeleton-img skeleton"></div>
                <div style="flex:1">
                    <div class="skeleton skeleton-title"></div>
                    <div class="skeleton skeleton-text" style="width:60%"></div>
                    <div class="skeleton skeleton-text" style="width:40%"></div>
                    <div class="skeleton skeleton-text" style="width:50%"></div>
                </div>
            </div>
        `;
    }
    
    try {
        // Botdan media olish
        const response = await fetch('/api/media');
        const data = await response.json();
        
        if (data.data && data.data.length > 0) {
            mediaData = data.data;
            extractGenres();
            renderMedia(mediaData);
        } else {
            showEmptyState();
        }
    } catch (error) {
        console.log('API not available, waiting for bot data');
        showEmptyState();
    }
}

function extractGenres() {
    const genresSet = new Set();
    mediaData.forEach(media => {
        if (media.genre) {
            media.genre.split(',').forEach(g => {
                const trimmed = g.trim();
                if (trimmed) genresSet.add(trimmed);
            });
        }
    });
    allGenres = Array.from(genresSet).sort();
}

function showEmptyState() {
    const grid = document.getElementById('mediaGrid');
    grid.innerHTML = `
        <div class="empty-state">
            <div class="icon">🎬</div>
            <h3>Hozircha media mavjud emas</h3>
            <p>Botga anime qo'shilganda<br>avtomatik ko'rinadi</p>
            <button class="btn-outline" onclick="loadMedia()" style="margin-top: 15px;">🔄 Yangilash</button>
        </div>
    `;
}

// ============================================ //
// 8. RENDER MEDIA (2751-2850)                 //
// ============================================ //
function renderMedia(mediaList) {
    const grid = document.getElementById('mediaGrid');
    
    if (!mediaList || mediaList.length === 0) {
        showEmptyState();
        return;
    }
    
    grid.innerHTML = '';
    
    mediaList.forEach((media, index) => {
        const card = document.createElement('div');
        card.className = 'media-card';
        card.style.animationDelay = `${index * 0.03}s`;
        card.onclick = () => openPlayer(media);
        
        const stars = media.rating ? '⭐'.repeat(Math.min(5, Math.floor(media.rating / 2))) : '';
        const ratingNum = (media.rating || 0).toFixed(1);
        const viewsFormatted = formatNumber(media.views || 0);
        const likesFormatted = formatNumber(media.likes || 0);
        const statusIcon = media.status === 'completed' ? '✅' : '🟢';
        const statusText = media.status === 'completed' ? 'Tugallangan' : 'Davom etmoqda';
        const vipBadge = media.is_vip ? '<span class="media-badge">👑 VIP</span>' : '';
        const imageUrl = media.image_url || 'https://i.imgur.com/anime_default.jpg';
        
        card.innerHTML = `
            <img src="${imageUrl}" alt="${escapeHtml(media.name)}" loading="lazy" onerror="this.src='https://i.imgur.com/anime_default.jpg'">
            <div class="media-info">
                <div class="media-title">🎬 ${escapeHtml(media.name)}</div>
                <div class="media-meta">
                    <span>📀 ${media.total_parts || 0} qism</span>
                    <span>${statusIcon} ${statusText}</span>
                    ${vipBadge}
                </div>
                <div class="media-stats">
                    <span>👁 ${viewsFormatted}</span>
                    <span>❤️ ${likesFormatted}</span>
                </div>
                <div class="rating-stars">${stars} ${ratingNum}/10</div>
            </div>
        `;
        grid.appendChild(card);
    });
    
    // Genre taglarni qo'shish
    if (allGenres.length > 0) {
        const tabsContainer = document.getElementById('tabs');
        const genreTabs = allGenres.slice(0, 6).map(g => 
            `<button class="tab" onclick="loadGenre('${g}')">#${g}</button>`
        ).join('');
        tabsContainer.innerHTML += genreTabs;
    }
}

function loadGenre(genre) {
    const filtered = mediaData.filter(m => m.genre && m.genre.includes(genre));
    renderMedia(filtered);
    showToast(`#${genre} - ${filtered.length} ta anime topildi`);
}

function loadTab(type) {
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    if (event?.target) event.target.classList.add('active');
    
    let filtered = [...mediaData];
    switch(type) {
        case 'ongoing':
            filtered = mediaData.filter(m => m.status === 'ongoing');
            break;
        case 'completed':
            filtered = mediaData.filter(m => m.status === 'completed');
            break;
        case 'popular':
            filtered = [...mediaData].sort((a,b) => (b.views||0) - (a.views||0));
            break;
        case 'vip':
            filtered = mediaData.filter(m => m.is_vip === 1 || m.is_vip === true);
            break;
        case 'recent':
            filtered = [...mediaData].sort((a,b) => new Date(b.created_at||0) - new Date(a.created_at||0));
            break;
        default:
            filtered = mediaData;
    }
    
    renderMedia(filtered);
    tg.HapticFeedback.impactOccurred('light');
}

// ============================================ //
// 9. SEARCH FUNCTIONS (2851-2900)             //
// ============================================ //
function searchAnime() {
    const query = document.getElementById('searchInput').value.trim().toLowerCase();
    if (!query) {
        loadMedia();
        return;
    }
    
    const filtered = mediaData.filter(m => 
        m.name.toLowerCase().includes(query) ||
        (m.code && m.code.toString().includes(query)) ||
        (m.genre && m.genre.toLowerCase().includes(query))
    );
    
    renderMedia(filtered);
    
    if (filtered.length === 0) {
        showToast(`❌ "${query}" bo'yicha hech narsa topilmadi`, true);
    } else {
        showToast(`🔍 ${filtered.length} ta natija topildi`);
    }
}

function scrollToSearch() {
    document.getElementById('searchInput').focus();
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

// ============================================ //
// 10. PLAYER FUNCTIONS (2901-3050)            //
// ============================================ //
function openPlayer(media) {
    currentMedia = media;
    
    document.getElementById('mediaGrid').classList.add('hidden');
    document.querySelector('.tabs').classList.add('hidden');
    document.querySelector('.search-container').classList.add('hidden');
    document.getElementById('playerSection').classList.remove('hidden');
    document.getElementById('playerTitle').textContent = media.name;
    document.getElementById('playerRating').textContent = (media.rating || 0).toFixed(1);
    document.getElementById('playerViews').textContent = formatNumber(media.views || 0);
    document.getElementById('playerParts').textContent = media.total_parts || 0;
    document.getElementById('likeCount').textContent = formatNumber(media.likes || 0);
    document.getElementById('commentCount').textContent = (media.comments || []).length;
    document.getElementById('commentsCount').textContent = `${(media.comments || []).length} ta izoh`;
    
    const likeBtn = document.getElementById('likeBtn');
    if (favorites.includes(media.id)) {
        likeBtn.classList.add('liked');
        isLiked = true;
    } else {
        likeBtn.classList.remove('liked');
        isLiked = false;
    }
    
    // Part buttons
    const pb = document.getElementById('partButtons');
    pb.innerHTML = '';
    const totalParts = Math.min(media.total_parts || 0, 50);
    
    if (totalParts === 0) {
        pb.innerHTML = '<div class="text-muted" style="text-align:center;padding:20px;">📀 Hozircha qismlar mavjud emas</div>';
    } else {
        for (let i = 1; i <= totalParts; i++) {
            const btn = document.createElement('button');
            btn.className = 'part-btn';
            btn.innerHTML = `<span>${i}</span>`;
            btn.title = `${i}-qism`;
            btn.onclick = () => loadPart(i);
            pb.appendChild(btn);
        }
    }
    
    // Comments
    loadComments();
    
    // Add to watch history
    addToWatchHistory(media.id, 1);
    
    tg.HapticFeedback.impactOccurred('medium');
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

function loadPart(partNum) {
    currentPart = partNum;
    
    document.querySelectorAll('.part-btn').forEach(btn => btn.classList.remove('active'));
    const btns = document.querySelectorAll('.part-btn');
    if (btns[partNum - 1]) btns[partNum - 1].classList.add('active');
    
    const video = document.getElementById('videoPlayer');
    const parts = currentMedia.parts || [];
    const part = parts.find(p => p.part_number === partNum);
    
    if (part && part.file_id) {
        // Telegram video ID dan URL olish
        video.src = part.file_id;
    } else {
        // Demo video
        video.src = `https://sample-videos.com/video321/mp4/720/big_buck_bunny_720p_1mb.mp4`;
    }
    
    video.load();
    addToWatchHistory(currentMedia.id, partNum);
    
    // Report to bot
    fetch('/api/watch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            user_id: currentUser?.id,
            media_id: currentMedia?.id,
            part_number: partNum
        })
    }).catch(() => {});
}

function closePlayer() {
    document.getElementById('playerSection').classList.add('hidden');
    document.getElementById('mediaGrid').classList.remove('hidden');
    document.querySelector('.tabs').classList.remove('hidden');
    document.querySelector('.search-container').classList.remove('hidden');
    document.getElementById('commentsSection').classList.add('hidden');
    
    const video = document.getElementById('videoPlayer');
    video.pause();
    video.src = '';
    
    loadMedia();
    tg.HapticFeedback.impactOccurred('light');
}

// ============================================ //
// 11. LIKES FUNCTIONS (3051-3120)             //
// ============================================ //
function toggleLike() {
    isLiked = !isLiked;
    const btn = document.getElementById('likeBtn');
    
    btn.style.animation = 'heartBeat 0.4s ease';
    setTimeout(() => btn.style.animation = '', 400);
    
    btn.classList.toggle('liked', isLiked);
    const countSpan = document.getElementById('likeCount');
    let currentCount = parseInt(countSpan.textContent.replace(/[^0-9]/g, '')) || 0;
    let newCount = currentCount + (isLiked ? 1 : -1);
    countSpan.textContent = formatNumber(newCount);
    
    if (currentMedia) {
        currentMedia.likes = (currentMedia.likes || 0) + (isLiked ? 1 : -1);
    }
    
    if (isLiked) {
        if (!favorites.includes(currentMedia?.id)) {
            favorites.push(currentMedia?.id);
            saveFavorites();
        }
        showToast("❤️ Sevimlilarga qo'shildi!");
    } else {
        favorites = favorites.filter(id => id !== currentMedia?.id);
        saveFavorites();
        showToast("💔 Sevimlilardan o'chirildi");
    }
    
    fetch('/api/like', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
            user_id: currentUser?.id, 
            media_id: currentMedia?.id, 
            liked: isLiked 
        })
    }).catch(() => {});
    
    tg.HapticFeedback.notificationOccurred('success');
}

// ============================================ //
// 12. COMMENTS FUNCTIONS (3121-3200)          //
// ============================================ //
function toggleComments() {
    const commentsSection = document.getElementById('commentsSection');
    commentsSection.classList.toggle('hidden');
    if (!commentsSection.classList.contains('hidden')) {
        loadComments();
    }
}

function loadComments() {
    const list = document.getElementById('commentsList');
    const comments = currentMedia?.comments || [];
    
    if (comments.length === 0) {
        list.innerHTML = `
            <div class="text-center text-muted" style="padding: 30px;">
                💬 Hozircha izohlar yo'q
                <br><small>Birinchi izoh qoldiring!</small>
            </div>
        `;
        return;
    }
    
    list.innerHTML = comments.map(c => `
        <div class="comment">
            <div class="comment-header">
                <div class="comment-avatar">👤</div>
                <span class="comment-user">${escapeHtml(c.username || 'Anonim')}</span>
                <span class="comment-time">${formatTime(c.created_at || c.timestamp)}</span>
            </div>
            <div class="comment-text">${escapeHtml(c.text)}</div>
        </div>
    `).join('');
}

function addComment() {
    const input = document.getElementById('commentInput');
    const text = input.value.trim();
    
    if (!text) {
        showToast("❌ Izoh yozing!", true);
        return;
    }
    
    if (text.length > 500) {
        showToast("❌ Izoh 500 belgidan oshmasligi kerak!", true);
        return;
    }
    
    const comment = {
        id: Date.now(),
        username: currentUser?.username || currentUser?.first_name || 'Anonim',
        user_id: currentUser?.id,
        text: text,
        created_at: new Date().toISOString()
    };
    
    if (!currentMedia.comments) currentMedia.comments = [];
    currentMedia.comments.unshift(comment);
    
    document.getElementById('commentCount').textContent = formatNumber(currentMedia.comments.length);
    document.getElementById('commentsCount').textContent = `${currentMedia.comments.length} ta izoh`;
    loadComments();
    input.value = '';
    
    const commentDiv = document.querySelector('.comments-section');
    commentDiv.style.animation = 'none';
    setTimeout(() => commentDiv.style.animation = 'slideUp 0.3s ease', 10);
    
    fetch('/api/comment', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
            user_id: currentUser?.id,
            username: currentUser?.username,
            media_id: currentMedia?.id, 
            text: text 
        })
    }).catch(() => {});
    
    tg.HapticFeedback.notificationOccurred('success');
    showToast("✅ Izoh qo'shildi!");
}

function shareMedia() {
    if (!currentMedia) return;
    
    const botUsername = window.Telegram.WebApp.initDataUnsafe?.user?.username || 'AniComplex_Rasmiy_bot';
    const shareUrl = `https://t.me/share/url?url=https://t.me/${botUsername}?start=code_${currentMedia.code}&text=🎬 ${encodeURIComponent(currentMedia.name)} - AniComplex botda tomosha qiling!`;
    
    tg.openTelegramLink(shareUrl);
    showToast("📤 Ulashish oynasi ochilmoqda");
}

// ============================================ //
// 13. UTILITY FUNCTIONS (3201-3280)           //
// ============================================ //
function formatNumber(num) {
    if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
    if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
    return num.toString();
}

function formatTime(isoString) {
    if (!isoString) return 'hozir';
    const date = new Date(isoString);
    const now = new Date();
    const diff = now - date;
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);
    
    if (minutes < 1) return 'hozir';
    if (minutes < 60) return `${minutes} daqiqa oldin`;
    if (hours < 24) return `${hours} soat oldin`;
    if (days < 7) return `${days} kun oldin`;
    return date.toLocaleDateString('uz-UZ');
}

function escapeHtml(str) {
    if (!str) return '';
    return str
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

function showProfile() {
    const user = currentUser;
    if (!user) return;
    
    const modal = document.createElement('div');
    modal.className = 'modal';
    modal.innerHTML = `
        <div class="modal-content">
            <h3>👤 Profil</h3>
            <p><strong>Ism:</strong> ${escapeHtml(user.first_name)}</p>
            <p><strong>Username:</strong> @${escapeHtml(user.username)}</p>
            <p><strong>ID:</strong> ${user.id}</p>
            <p><strong>Ro'yxatdan o'tgan:</strong> ${new Date(user.registered_at).toLocaleDateString('uz-UZ')}</p>
            <p><strong>⭐ Sevimlilar:</strong> ${favorites.length} ta</p>
            <p><strong>📜 Tomosha tarixi:</strong> ${watchHistory.length} ta</p>
            <div class="modal-buttons">
                <button class="btn-secondary" onclick="this.closest('.modal').remove()">Yopish</button>
            </div>
        </div>
    `;
    document.body.appendChild(modal);
    modal.onclick = (e) => {
        if (e.target === modal) modal.remove();
    };
}

// ============================================ //
// 14. AUTO REFRESH (3281-3320)                //
// ============================================ //
let refreshInterval = setInterval(() => {
    if (!document.getElementById('playerSection').classList.contains('hidden')) return;
    if (document.getElementById('mediaGrid') && !document.getElementById('mediaGrid').classList.contains('hidden')) {
        loadMedia();
    }
}, 30000);

// ============================================ //
// 15. BACK BUTTON HANDLER (3321-3350)         //
// ============================================ //
if (tg.BackButton) {
    tg.BackButton.onClick(() => {
        if (!document.getElementById('playerSection').classList.contains('hidden')) {
            closePlayer();
        } else if (document.querySelector('.modal')) {
            document.querySelector('.modal').remove();
        } else {
            tg.close();
        }
    });
}

// ============================================ //
// 16. INITIALIZE APP (3351-3380)              //
// ============================================ //
checkAuth();

// Clean up on page unload
window.addEventListener('beforeunload', () => {
    if (refreshInterval) clearInterval(refreshInterval);
});

// Add CSS for modal if not already present
if (!document.querySelector('#modal-styles')) {
    const style = document.createElement('style');
    style.id = 'modal-styles';
    style.textContent = `
        .modal {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.8);
            backdrop-filter: blur(8px);
            z-index: 300;
            display: flex;
            align-items: center;
            justify-content: center;
            animation: fadeIn 0.3s ease;
        }
        .modal-content {
            background: linear-gradient(135deg, rgba(25,25,40,0.98), rgba(15,15,25,0.98));
            backdrop-filter: blur(20px);
            border-radius: 25px;
            padding: 25px;
            width: 90%;
            max-width: 350px;
            text-align: center;
            animation: scaleIn 0.3s ease;
            border: 1px solid rgba(231,76,60,0.3);
        }
        .modal-content p {
            margin: 10px 0;
            text-align: left;
        }
        .modal-buttons {
            display: flex;
            gap: 12px;
            margin-top: 20px;
        }
        .modal-buttons button {
            flex: 1;
        }
        @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }
        @keyframes scaleIn {
            from { opacity: 0; transform: scale(0.9); }
            to { opacity: 1; transform: scale(1); }
        }
    `;
    document.head.appendChild(style);
}

console.log('✅ AniComplex Mini App loaded successfully!');
</script>
</body>
</html>'''

def run_mini_app_server():
    """Mini App uchun HTTP server"""
    class MiniAppHandler(SimpleHTTPRequestHandler):
        def do_GET(self):
            if self.path == '/' or self.path == '/index.html':
                self.send_response(200)
                self.send_header('Content-type', 'text/html; charset=utf-8')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(MINI_APP_HTML.encode('utf-8'))
            else:
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(b'{"status":"ok"}')
        
        def log_message(self, format, *args):
            pass
    
    server = HTTPServer((MINI_APP_HOST, MINI_APP_PORT), MiniAppHandler)
    print(f"🌐 Mini App server: http://{MINI_APP_HOST}:{MINI_APP_PORT}")
    server.serve_forever()

# ================= MINI APP API ENDPOINTS =================
from aiohttp import web
import json

class MiniAppAPI:
    """Mini App uchun API endpointlar"""
    
    @staticmethod
    async def get_media(request):
        """Barcha medialarni qaytaradi"""
        media_list = []
        try:
            async with db.conn.execute("""
                SELECT id, name, code, total_parts, status, rating, rating_count, 
                       image_url, views, is_vip, description, genre, created_at
                FROM media WHERE is_vip=0 OR is_vip=1
                ORDER BY id DESC
            """) as c:
                rows = await c.fetchall()
                for row in rows:
                    # Like va comment larni olish
                    likes = await db.get_likes(row['id'])
                    async with db.conn.execute(
                        "SELECT username, text, created_at FROM comments WHERE media_id=? ORDER BY created_at DESC LIMIT 20", 
                        (row['id'],)
                    ) as cc:
                        comments = await cc.fetchall()
                    
                    media_list.append({
                        "id": row['id'],
                        "name": row['name'],
                        "code": row['code'],
                        "total_parts": row['total_parts'],
                        "status": row['status'] or "ongoing",
                        "rating": float(row['rating'] or 0),
                        "rating_count": row['rating_count'] or 0,
                        "image_url": row['image_url'] or "",
                        "views": row['views'] or 0,
                        "likes": likes,
                        "comments": [{"username": c['username'] or "Anonim", "text": c['text'], "created_at": c['created_at']} for c in comments],
                        "is_vip": row['is_vip'] or 0,
                        "description": row['description'] or "",
                        "genre": row['genre'] or "",
                        "created_at": row['created_at']
                    })
        except Exception as e:
            logger.error(f"API get_media error: {e}")
        
        return web.json_response({"status": "ok", "data": media_list})
    
    @staticmethod
    async def register_user(request):
        """Foydalanuvchini ro'yxatdan o'tkazish"""
        try:
            data = await request.json()
            user_id = data.get('id')
            first_name = data.get('first_name', '')
            username = data.get('username', '')
            
            if user_id:
                await db.add_user(user_id, username, first_name, "")
                logger.info(f"New user registered from MiniApp: {user_id}")
                return web.json_response({"status": "ok", "message": "User registered"})
        except Exception as e:
            logger.error(f"API register error: {e}")
        
        return web.json_response({"status": "error"}, status=400)
    
    @staticmethod
    async def add_like(request):
        """Layk qo'shish"""
        try:
            data = await request.json()
            media_id = data.get('media_id')
            user_id = data.get('user_id')
            liked = data.get('liked', True)
            
            if user_id and media_id:
                if liked:
                    await db.add_like(user_id, media_id)
                else:
                    await db.remove_like(user_id, media_id)
                return web.json_response({"status": "ok"})
        except Exception as e:
            logger.error(f"API like error: {e}")
        
        return web.json_response({"status": "error"}, status=400)
    
    @staticmethod
    async def add_comment(request):
        """Izoh qo'shish"""
        try:
            data = await request.json()
            media_id = data.get('media_id')
            user_id = data.get('user_id')
            text = data.get('text', '')
            username = data.get('username', 'Anonim')
            
            if media_id and text:
                await db.add_comment(user_id or 0, media_id, username, text)
                logger.info(f"New comment on media {media_id}")
                return web.json_response({"status": "ok"})
        except Exception as e:
            logger.error(f"API comment error: {e}")
        
        return web.json_response({"status": "error"}, status=400)
    
    @staticmethod
    async def get_media_count(request):
        """Media sonini qaytaradi"""
        try:
            count = await db.get_media_count()
            return web.json_response({"count": count})
        except:
            return web.json_response({"count": 0})


# ================= YANGI: ROOT SAHIFANI KO'RSATISH =================
async def handle_root(request):
    """Asosiy Mini App HTML sahifasini qaytaradi"""
    # MINI_APP_HTML o'zgaruvchisi sizda mavjud (juda uzun)
    return web.Response(text=MINI_APP_HTML, content_type='text/html')


# ================= API SERVER YARATISH =================
api_app = web.Application()

# ROOT manzilini qo'shamiz (asosiy sahifa)
api_app.router.add_get('/', handle_root)
api_app.router.add_get('/index.html', handle_root)

# API manzillar
api_app.router.add_get('/api/media', MiniAppAPI.get_media)
api_app.router.add_get('/api/media/count', MiniAppAPI.get_media_count)
api_app.router.add_post('/api/register', MiniAppAPI.register_user)
api_app.router.add_post('/api/like', MiniAppAPI.add_like)
api_app.router.add_post('/api/comment', MiniAppAPI.add_comment)


async def start_api_server():
    """API serverni ishga tushirish"""
    runner = web.AppRunner(api_app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8080)
    await site.start()
    logger.info("✅ MiniApp API server running on port 8080")

# ================= MAIN =================
async def main():
    print("=" * 70)
    print(f"🤖 ANICOMPLEX BOT v{BOT_VERSION}")
    print(f"👑 Ownerlar: {ADMINS}")
    print(f"📢 Kanal: {MAIN_CHANNEL}")
    print(f"👨‍💻 Muallif: {AUTHOR_USERNAME}")
    print(f"👑 VIP narxi: {VIP_PRICE} so'm/oy")
    print("=" * 70)
    
    await db.connect()
    print("✅ Database ulandi")
    
    await db.check_all_vip_expiry()
    print("✅ VIP muddatlari tekshirildi")
    
    # API server (aiohttp) ishga tushadi. U / va /api/* manzillariga javob beradi.
    await start_api_server()
    print("✅ MiniApp API server ishga tushdi (port 8080)")
    
    # ⚠️ ESKI HTTPServer-ni ISHGA TUSHIRMAYMIZ! (o'chiriladi)
    # if MINI_APP_URL and MINI_APP_URL.startswith("https://"):
    #     mini_app_thread = threading.Thread(target=run_mini_app_server, daemon=True)
    #     mini_app_thread.start()
    #     try:
    #         await bot.set_chat_menu_button(...)
    #     except: pass
    
    try:
        await bot.delete_webhook(drop_pending_updates=True)
    except:
        pass
    
    asyncio.create_task(vip_expiry_checker())
    
    print("✅ Bot to'liq ishga tushdi!")
    print("=" * 70)
    
    try:
        await dp.start_polling(bot)
    except KeyboardInterrupt:
        print("\n⚠️ To'xtatildi")
    finally:
        await db.close()
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
