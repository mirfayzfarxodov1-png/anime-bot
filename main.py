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
VIP_PRICE = int(os.getenv("VIP_PRICE", "VIP UZUR HOZIRCHA ISHLAMAYDI "))
PHONE_NUMBER_1 = os.getenv("PHONE_NUMBER_1", "+998938138110")
PHONE_NUMBER_2 = os.getenv("PHONE_NUMBER_2", "+998500741888")
CARD_NUMBER = os.getenv("CARD_NUMBER", "yoq")
BOT_VERSION = "8.0.0"
BOT_USERNAME = os.getenv("BOT_USERNAME", "@AniComplex_Rasmiy_bot")

# Mini App sozlamalari
MINI_APP_PORT = int(os.getenv("MINI_APP_PORT", "8080"))
MINI_APP_HOST = os.getenv("MINI_APP_HOST", "0.0.0.0")
MINI_APP_URL = os.getenv("MINI_APP_URL", "")

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
