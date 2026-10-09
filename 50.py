import logging
import sqlite3
import re
import os
import io
import json
import math
import asyncio
import random
import string
import time
import uuid
import zipfile
import tempfile
import secrets
import threading
from html import escape as html_escape
import requests
import urllib3
from datetime import datetime, timedelta, timezone
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update
)
from telegram.error import BadRequest, Conflict
try:
    from flask import Flask, request, jsonify, Response
except ImportError:
    Flask = None
    request = jsonify = Response = None

try:
    from waitress import serve as waitress_serve
except ImportError:
    waitress_serve = None

from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters
)

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ---------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------
# !! SECURITY: Token / keys ab code me hardcode nahi hain.
# Pehle ke token/keys leak ho chuke hain -> BotFather se /revoke karke NAYA token lo
# aur ye env variables set karo:
#   BOT_TOKEN, STORE_API_KEY, MASTER_KEY
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_ID = 6480827931
DEFAULT_ADMIN_USERNAME = "Rohit_BhaiTOP"

API_URL = "https://bantibhaiya.to/api/reseller_v1.php"
DEFAULT_API_KEY = os.getenv("STORE_API_KEY", "NONE")
MASTER_KEY = os.getenv("MASTER_KEY", "NONE")

ZAPUPI_API_BASE = "https://pay.zapupi.com/api"
DEFAULT_ZAPUPI_KEY = "YOUR_ZAPUPI_KEY_HERE"

DB_PATH = os.getenv("DB_PATH", "surajbot.db")
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", os.getenv("PORT", "5000")))
MIN_DEPOSIT = 1.0
MAX_PID_LEN = 30
MAX_DISCOUNT = 99.0

logging.basicConfig(level=logging.INFO)

PROCESSING_PURCHASES = set()
SPINNING_USERS = set()
BACKGROUND_TASKS = set()

LANGUAGES = {
    "en": "🇬🇧 English", "hi": "🇮🇳 हिन्दी", "bn": "🇧🇩 বাংলা", "as": "🇮🇳 অসমীয়া",
    "ta": "🇮🇳 தமிழ்", "ur": "🇵🇰 اردو", "bho": "🇮🇳 भोजपुरी", "pa": "🇮🇳 ਪੰਜਾਬੀ",
    "gu": "🇮🇳 ગુજરાતી", "mr": "🇮🇳 मराठी", "or": "🇮🇳 ଓଡ଼ିଆ"
}

MAINTENANCE_MSG = (
    "🛠 **UNDER MAINTENANCE**\n"
    "━━━━━━━━━━━━━━━━━━━━\n\n"
    "The bot is temporarily offline for maintenance.\n"
    "Please check back again shortly — thank you for your patience."
)

# ============================================================
# PREMIUM EMOJI IDS
# ============================================================
EMOJI_DEVICE_SELECT = "5397857289216484878"
EMOJI_CHOOSE_DEVICE = "6145426283007320286"
EMOJI_CATEGORY = "5431721976769027887"
EMOJI_PRODUCT = "6053003934031684683"
EMOJI_PLAN = "5017179932451668652"
EMOJI_PURCHASE_SUCCESS = "6311888443622299860"
EMOJI_YOUR_KEY = "6311935044017461530"
EMOJI_YOUR_BALANCE = "6210881885246071421"
EMOJI_PROFILE = "5373012449597335010"
EMOJI_ADD_BALANCE = "6095654445339647423"
EMOJI_LUCKY_SPIN = "5888529492871221275"
EMOJI_SPIN_NOW = "6230960110030561348"
EMOJI_REFER = "6210555407602033687"
EMOJI_UPGRADE_RESELLER = "5217822164362739968"
EMOJI_SHOP_BOT = "6147500597592464127"
EMOJI_HISTORY = "6032594876506312598"
EMOJI_HOW_TO = "5260293700088511294"
EMOJI_SUPPORT = "6235717714023814969"

EMOJI_MAINTENANCE_PRODUCT = "6096010343509663420"
EMOJI_CAT_LINE_1 = "6161030148301791023"
EMOJI_CAT_LINE_2 = "6161384908305473924"
EMOJI_CAT_LINE_3 = "6160948518153363716"

EMOJI_PROD_LINE_1 = "6145230677311759438"
EMOJI_PROD_LINE_2 = "6147772829799555115"
EMOJI_PROD_LINE_3 = "6278223759811812961"

EMOJI_PLAN_BOTH_SIDES = "5215484787325676090"
EMOJI_SELECT_PLAN = "6278223759811812961"
EMOJI_GAMEPLAY_VIDEO = "5944753741512052670"

EMOJI_CATEGORY_HEADER = "5215484787325676090"
EMOJI_SUPPORT_L1 = "5443038326535759644"
EMOJI_SUPPORT_L2 = "6233351461921627749"
EMOJI_SUPPORT_L3 = "5443038326535759644"

EMOJI_PROFILE_L1 = "5474625972751837256"
EMOJI_PROFILE_L2 = "6195222374355311655"
EMOJI_PROFILE_L3 = "5447410659077661506"
EMOJI_PROFILE_L4 = "6192822213486321961"
EMOJI_PROFILE_L5 = "6192842983948162969"

EMOJI_RESELLER_L1 = "5416117059207572332"
EMOJI_RESELLER_L2 = "6312070107854018137"
EMOJI_RESELLER_L3 = "6145572453629304637"
EMOJI_RESELLER_L4 = "6235357684095262824"

EMOJI_CONTACT_ADMIN_BTN = "5443038326535759644"

EMOJI_HISTORY_HEADER = "5282843764451195532"

BACK_ICON = "6145575558890660225"

# ---- Top Buyers Leaderboard ----
EMOJI_LEADERBOARD_BTN = "6181666151899079958"   # main menu button icon
EMOJI_LB_TROPHY = "6230916451687997623"         # header trophy
EMOJI_LB_NAME = "6161068493769810928"           # Name line
EMOJI_LB_ORDERS = "6145292889913039900"         # Total Orders line
EMOJI_LB_SPEND = "6233058686885961086"          # Total Spend line
EMOJI_LB_REFRESH = "6230960110030561348"        # Refresh button icon

LEADERBOARD_LIMIT = 5

# ============================================================
# CUSTOM EMOJI MAP FOR TEXT RENDERING
# ============================================================
CUSTOM_EMOJI_MAP = {
    "🛍️": "6145292889913039900",
    "💰": "6233058686885961086",
    "🎉": "6233339470372938278",
    "🚀": "6233029979324554127",
    "💎": "6230781293362158919",
    "🏆": "6230916451687997623",
    "🏪": "6147500597592464127",
    "📱": "5395316940614937989",
    "🔙": "6145575558890660225",
    "👤": "6161068493769810928",
    "📛": "6161068493769810928",
    "🏷️": "6161068493769810928",
    "🆔": "6161068493769810928",
    "💸": "6161068493769810928",
    "💳": "5429651785352501917",
    "🧾": "6032594876506312598",
    "💵": "6032594876506312598",
    "🗓️": "6032594876506312598",
    "🎁": "5350452584119279096",
    "🔗": "5350452584119279096",
    "👥": "5350452584119279096",
    "✅": "5350452584119279096",
    "📢": "5350452584119279096",
    "☎️": "6210671723906342799",
    "👨‍💻": "6210671723906342799",
    "🎫": "6210671723906342799",
    "📸": "6210671723906342799",
    "🎙️": "6210671723906342799",
    "📝": "6210671723906342799",
    "⏳": "6210671723906342799",
    "🎰": "5382194935057372936",
    "🎡": "5382194935057372936",
    "😅": "5382194935057372936",
    "⏰": "5382194935057372936",
    "💼": "5382194935057372936",
    "🍀": "5382194935057372936",
    "❓": "5260293700088511294",
    "▶️": "5260293700088511294",
    "📥": "6161336001512874965",
    "🔥": "5447410659077661506",
    "🌟": "5447410659077661506",
    "📂": "6147500597592464127",
    "📦": "6147500597592464127",
    "🛠": "6096010343509663420",
}

I18N = {
    "welcome": {
        "en": "💎━━ Suraj Shop Bot ━💎\n\n👋 Welcome, **{name}**\n\n💰 **Balance:** ₹{bal:.2f}\n🆔 **User ID:** `{uid}`\n\n🚀 **Tap Shop Now to Start!**",
        "hi": "💎━━ ऑल स्टोर शॉप बॉट ━💎\n\n👋 स्वागत है, **{name}**\n\n💰 **बैलेंस:** ₹{bal:.2f}\n🆔 **यूजर आईडी:** `{uid}`\n\n🚀 **शुरू करने के लिए Shop Now दबाएं!**",
    },
    "btn_shop": {"en": "Shop Now", "hi": "अभी खरीदें", "bn": "কেনাকাটা করুন", "as": "এতিয়াই ক্ৰয় কৰক",
        "ta": "இப்போது வாங்கு", "ur": "ابھی خریدیں", "bho": "अभी खरीदीं", "pa": "ਹੁਣੇ ਖਰੀਦੋ",
        "gu": "હમણાં ખરીદો", "mr": "आता खरेदी करा", "or": "ଏବେ କ୍ରୟ କରନ୍ତୁ"},
    "btn_upgrade": {"en": "Upgrade To Reseller", "hi": "रीसेलर में अपग्रेड करें", "bn": "রিসেলার আপগ্রেড", "as": "ৰিচেলাৰ লৈ উন্নীত কৰক",
        "ta": "மறுவிற்பனையாளராக மேம்படுத்து", "ur": "ریسیلار میں اپ گریڈ کریں", "bho": "रीसेलर में अपग्रेड करीं", "pa": "ਰੀਸੈਲਰ ਵਿੱਚ ਅੱਪਗ੍ਰੇਡ ਕਰੋ",
        "gu": "રિસેલરમાં અપગ્રેડ કરો", "mr": "रिसेलरमध्ये श्रेणीसुधार करा", "or": "ରିସେଲର୍ କୁ ଅପଗ୍ରେଡ୍ କରନ୍ତୁ"},
    "btn_profile": {"en": "My Profile", "hi": "मेरी प्रोफाइल", "bn": "আমার প্রোফাইল", "as": "মোৰ প্ৰফাইল",
        "ta": "என் சுயவிவரம்", "ur": "میری پروفائل", "bho": "हमार प्रोफाइल", "pa": "ਮੇਰੀ ਪ੍ਰੋਫਾਈਲ",
        "gu": "મારી પ્રોફાઇલ", "mr": "माझी प्रोफाईल", "or": "ମୋର ପ୍ରୋଫାଇଲ୍"},
    "btn_add_bal": {"en": "Add Balance", "hi": "बैलेंस जोड़ें", "bn": "ব্যালেন্স যোগ করুন", "as": "বেলেঞ্চ যোগ কৰক",
        "ta": "இருப்பு சேர்", "ur": "بیلنس شامل کریں", "bho": "बैलेंस जोड़ीं", "pa": "ਬੈਲੇਂਸ ਜੋੜੋ",
        "gu": "બેલેન્સ ઉમેરો", "mr": "शिल्लक जोडा", "or": "ବାଲାନ୍ସ ଯୋଡନ୍ତୁ"},
    "btn_history": {"en": "All History", "hi": "सभी इतिहास", "bn": "সম্পূর্ণ ইতিহাস", "as": "সম্পূৰ্ণ ইতিহাস",
        "ta": "அனைத்து வரலாறு", "ur": "تمام تاریخ", "bho": "सगरी इतिहास", "pa": "ਸਾਰਾ ਇਤਿਹਾਸ",
        "gu": "બધો ઇતિહાસ", "mr": "सर्व इतिहास", "or": "ସମସ୍ତ ଇତିହାସ"},
    "btn_refer": {"en": "Refer & Earn", "hi": "रेफर और कमाएं", "bn": "রেফার এবং আয়", "as": "ৰেফাৰ কৰি উপাৰ্জন কৰক",
        "ta": "பரிந்துரைத்து சம்பாதி", "ur": "ریفر اور کمائیں", "bho": "रेफर करीं आ कमाईं", "pa": "ਰੈਫਰ ਕਰੋ ਅਤੇ ਕਮਾਓ",
        "gu": "રેફર કરો અને કમાઓ", "mr": "संदर्भ द्या आणि कमवा", "or": "ରେଫର୍ ଏବଂ ରୋଜଗାର କରନ୍ତୁ"},
    "btn_spin": {"en": "Lucky Spin", "hi": "लकी स्पिन", "bn": "লাকি স্পিন", "as": "লকী স্পিন",
        "ta": "லக்கி ஸ்பின்", "ur": "لکی اسپن", "bho": "लकी स्पिन", "pa": "ਲੱਕੀ ਸਪਿਨ",
        "gu": "લકી સ્પિન", "mr": "लकी स्पिन", "or": "ଲକି ସ୍ପିନ୍"},
    "btn_how": {"en": "How To Use", "hi": "कैसे उपयोग करें", "bn": "ব্যবহার নির্দেশিকা", "as": "ব্যৱহাৰৰ নিয়ম",
        "ta": "எப்படி பயன்படுத்துவது", "ur": "استعمال کرنے کا طریقہ", "bho": "कईसे इस्तेमाल करें", "pa": "ਕਿਵੇਂ ਵਰਤਣਾ ਹੈ",
        "gu": "કેવી રીતે ઉપયોગ કરવો", "mr": "कसे वापरायचे", "or": "କିପରି ବ୍ୟବହାର କରିବେ"},
    "btn_support": {"en": "Support", "hi": "एडमिन सहायता", "bn": "এডমিন সাপোর্ট", "as": "এডমিন সহায়",
        "ta": "நிர்வாக ஆதரவு", "ur": "ایڈمین سپورٹ", "bho": "एडमिन सपोर्ट", "pa": "ਐਡਮਿਨ ਸਹਾਇਤਾ",
        "gu": "એડમિન સપોર્ટ", "mr": "एडमिन सहाय्य", "or": "ଆଡମିନ୍ ସପୋର୍ଟ"},
    "btn_back": {"en": "Back", "hi": "वापस", "bn": "ফিরে যান", "as": "ঘূৰি যাওক",
        "ta": "திரும்பு", "ur": "واپس", "bho": "लौटीं", "pa": "ਵਾਪਸ",
        "gu": "પાછા", "mr": "परत", "or": "ଫେରନ୍ତୁ"},
    "btn_leaderboard": {"en": "Top Buyers Leaderboard", "hi": "टॉप बायर्स लीडरबोर्ड", "bn": "টপ বায়ার্স লিডারবোর্ড", "as": "টপ বায়াৰ্ছ লিডাৰবৰ্ড",
        "ta": "சிறந்த வாங்குபவர்கள்", "ur": "ٹاپ بائرز لیڈربورڈ", "bho": "टॉप बायर्स लीडरबोर्ड", "pa": "ਟੌਪ ਖਰੀਦਦਾਰ ਲੀਡਰਬੋਰਡ",
        "gu": "ટોપ બાયર્સ લીડરબોર્ડ", "mr": "टॉप बायर्स लीडरबोर्ड", "or": "ଟପ୍ ବାୟର୍ସ ଲିଡରବୋର୍ଡ"},
}


def get_txt(key, lang_code="en", default_str=""):
    return I18N.get(key, {}).get(lang_code, I18N.get(key, {}).get("en", default_str or key))


def escape_markdown(text):
    """Escape for legacy Markdown."""
    if not text:
        return ""
    return str(text).replace("\\", "\\\\").replace("*", "\\*").replace("_", "\\_").replace("`", "\\`").replace("[", "\\[")


# ============================================================
# MARKDOWNV2 HELPERS
# ============================================================
MDV2_SPECIAL = set(r'_*[]()~`>#+-=|{}.!')


def get_custom_emoji_map():
    return CUSTOM_EMOJI_MAP.copy()


def _escape_and_emoji(text, emoji_map):
    out = []
    for ch in text:
        if ch in emoji_map:
            out.append(f"![{ch}](tg://emoji?id={emoji_map[ch]})")
        elif ch in MDV2_SPECIAL or ch == "\\":
            out.append("\\" + ch)
        else:
            out.append(ch)
    return "".join(out)


def render_markdownv2(raw_text, emoji_map=None):
    emoji_map = emoji_map or get_custom_emoji_map()
    parts = re.split(r'(\*\*.*?\*\*|`.*?`)', raw_text, flags=re.S)
    out = []
    for part in parts:
        if part.startswith('**') and part.endswith('**'):
            out.append('*' + _escape_and_emoji(part[2:-2], emoji_map) + '*')
        elif part.startswith('`') and part.endswith('`'):
            out.append(part)
        else:
            out.append(_escape_and_emoji(part, emoji_map))
    return "".join(out)


def rtext(raw_text):
    return render_markdownv2(raw_text, get_custom_emoji_map())


def emj(emoji_id):
    return f"![\u2b50](tg://emoji?id={emoji_id})"


def md_escape(text):
    """Escape MarkdownV2 special chars for plain text."""
    if text is None:
        return ""
    return "".join("\\" + c if (c in MDV2_SPECIAL or c == "\\") else c for c in str(text))


def code_escape(text):
    """Escape text that goes INSIDE a MarkdownV2 `code` span."""
    if text is None:
        return ""
    return str(text).replace("\\", "\\\\").replace("`", "\\`")


def fmt_amount(x):
    try:
        return md_escape(f"{float(x):.2f}")
    except Exception:
        return md_escape(str(x))


def fmt_pct(x):
    """5.0 -> '5', 7.5 -> '7.5'"""
    try:
        v = float(x)
    except (TypeError, ValueError):
        return "0"
    if v == int(v):
        return str(int(v))
    return f"{v:.2f}".rstrip("0").rstrip(".")


# ============================================================
# SAFE SEND / EDIT HELPERS (parse error aaye to plain text me fallback)
# ============================================================
def _plain_text(text):
    text = re.sub(r'!\[(.*?)\]\(tg://emoji\?id=\d+\)', r'\1', text)
    text = text.replace("**", "").replace("*", "").replace("`", "").replace("\\", "")
    return text


def _prep(text, parse_mode):
    if parse_mode == "Markdown" and text:
        text = text.replace("**", "*")
    return text


async def sedit(query, text, reply_markup=None, parse_mode="Markdown"):
    text = _prep(text, parse_mode)
    try:
        await query.edit_message_text(text, parse_mode=parse_mode, reply_markup=reply_markup)
    except BadRequest as e:
        if "not modified" in str(e).lower():
            return
        logging.warning(f"edit parse fail, plain fallback: {e}")
        try:
            await query.edit_message_text(_plain_text(text), reply_markup=reply_markup)
        except BadRequest as e2:
            if "not modified" not in str(e2).lower():
                raise


async def sreply(message, text, reply_markup=None, parse_mode="Markdown"):
    text = _prep(text, parse_mode)
    try:
        return await message.reply_text(text, parse_mode=parse_mode, reply_markup=reply_markup)
    except BadRequest as e:
        logging.warning(f"reply parse fail, plain fallback: {e}")
        return await message.reply_text(_plain_text(text), reply_markup=reply_markup)


async def ssend(bot, chat_id, text, reply_markup=None, parse_mode="Markdown"):
    text = _prep(text, parse_mode)
    try:
        return await bot.send_message(chat_id=chat_id, text=text, parse_mode=parse_mode, reply_markup=reply_markup)
    except BadRequest as e:
        logging.warning(f"send parse fail, plain fallback: {e}")
        return await bot.send_message(chat_id=chat_id, text=_plain_text(text), reply_markup=reply_markup)


async def ans(query, text=None, show_alert=False):
    try:
        await query.answer(text, show_alert=show_alert) if text else await query.answer()
    except Exception:
        pass


def db():
    return sqlite3.connect(DB_PATH, timeout=30)


def track_task(coro):
    t = asyncio.create_task(coro)
    BACKGROUND_TASKS.add(t)
    t.add_done_callback(BACKGROUND_TASKS.discard)
    return t


def parse_amount(s, allow_zero=False):
    try:
        v = float(str(s).strip())
    except (TypeError, ValueError):
        return None
    if not math.isfinite(v) or v < 0 or (v == 0 and not allow_zero):
        return None
    return round(v, 2)


# ============================================================
# BUTTON HELPERS
# ============================================================
MAX_BULK_ITEMS = 50


def parse_lines(text):
    """Line by line input -> non-empty stripped lines."""
    return [ln.strip() for ln in str(text).split("\n") if ln.strip()]


def numbered_list(items):
    return "\n".join(f"{i}. {escape_markdown(x)}" for i, x in enumerate(items, 1))


def normalize_pid(raw):
    pid = re.sub(r"\s+", "_", str(raw).strip()).upper()
    if re.fullmatch(rf"[A-Z0-9_\-]{{1,{MAX_PID_LEN}}}", pid):
        return pid
    return None


def rename_pids(cursor, mapping):
    """PID rename: products + plans + keys teeno me. Swap safe (2-phase). Commit caller karega."""
    items = [(o, n) for o, n in mapping.items() if o != n]
    for i, (o, _n) in enumerate(items):
        tmp = f"__TMP{i}__"
        cursor.execute("UPDATE products SET pid = ? WHERE pid = ?", (tmp, o))
        cursor.execute("UPDATE plans SET product_pid = ? WHERE product_pid = ?", (tmp, o))
        cursor.execute("UPDATE keys SET product_pid = ? WHERE product_pid = ?", (tmp, o))
    for i, (_o, n) in enumerate(items):
        tmp = f"__TMP{i}__"
        cursor.execute("UPDATE products SET pid = ? WHERE pid = ?", (n, tmp))
        cursor.execute("UPDATE plans SET product_pid = ? WHERE product_pid = ?", (n, tmp))
        cursor.execute("UPDATE keys SET product_pid = ? WHERE product_pid = ?", (n, tmp))
    return len(items)


# Telegram sirf primary / success / danger styles accept karta hai.
# "secondary" ka matlab "koi style nahi" (None) -> default grey button.
BUTTON_STYLES = {
    "primary": {"style": "primary"},
    "success": {"style": "success"},
    "danger": {"style": "danger"},
    "secondary": {"style": None},
}

_TG_VALID_STYLES = ("primary", "success", "danger")


def _match_emoji_prefix(text):
    if not text:
        return None
    for emoji_char in sorted(CUSTOM_EMOJI_MAP.keys(), key=len, reverse=True):
        if text.startswith(emoji_char):
            return emoji_char
    return None


def _mk_button(text, style_val, icon_id, **kw):
    """InlineKeyboardButton banao. Invalid style kabhi Telegram ko nahi bhejte.
    Purana python-telegram-bot version ho to api_kwargs se bhejo (crash nahi hoga)."""
    extra = {}
    if icon_id:
        extra["icon_custom_emoji_id"] = str(icon_id)
    if style_val in _TG_VALID_STYLES:
        extra["style"] = style_val
    try:
        return InlineKeyboardButton(text=text, **extra, **kw)
    except TypeError:
        return InlineKeyboardButton(text=text, api_kwargs=(extra or None), **kw)


def colored_button(text, callback_data, style="secondary", icon_custom_emoji_id=None):
    style_info = BUTTON_STYLES.get(style, BUTTON_STYLES["secondary"])
    matched = _match_emoji_prefix(text)
    if matched:
        text = text[len(matched):].strip()
    return _mk_button(text, style_info["style"], icon_custom_emoji_id, callback_data=callback_data)


def colored_url_button(text, url, style="secondary", icon_custom_emoji_id=None):
    style_info = BUTTON_STYLES.get(style, BUTTON_STYLES["secondary"])
    matched = _match_emoji_prefix(text)
    if matched:
        text = text[len(matched):].strip()
    return _mk_button(text, style_info["style"], icon_custom_emoji_id, url=url)


def colored_back_button(callback_data="admin_back_panel", text="Back"):
    return colored_button(text, callback_data, style="danger", icon_custom_emoji_id=BACK_ICON)


def user_back_kb(txt="Back", cb="main_menu"):
    return InlineKeyboardMarkup([[colored_button(txt, cb, style="danger", icon_custom_emoji_id=BACK_ICON)]])


def zigzag_rows(buttons):
    rows = []
    i = 0
    take_two = False
    n = len(buttons)
    while i < n:
        size = 2 if take_two else 1
        chunk = buttons[i:i + size]
        rows.append([colored_button(lbl, cb, style=st) for (lbl, cb, st) in chunk])
        i += len(chunk)
        take_two = not take_two
    return rows


VALID_STYLES = ("danger", "success", "primary")


def norm_style(style, fallback="primary"):
    s = (style or "").strip().lower()
    return s if s in VALID_STYLES else fallback


def get_category_style(cat_id, cursor=None):
    own_conn = cursor is None
    if own_conn:
        conn = db()
        cursor = conn.cursor()
    cursor.execute("SELECT button_style FROM categories WHERE id = ?", (cat_id,))
    row = cursor.fetchone()
    if own_conn:
        conn.close()
    return norm_style(row[0] if row else None, "success")


def set_category_style(cat_id, style):
    style = norm_style(style, "success")
    conn = db()
    conn.execute("UPDATE categories SET button_style = ? WHERE id = ?", (style, cat_id))
    conn.commit()
    conn.close()


def set_product_style(pid, style):
    style = norm_style(style, "primary")
    conn = db()
    conn.execute("UPDATE products SET button_style = ? WHERE pid = ?", (style, pid))
    conn.commit()
    conn.close()


def set_plan_style(plan_id, style):
    style = norm_style(style, "primary")
    conn = db()
    conn.execute("UPDATE plans SET button_style = ? WHERE id = ?", (style, plan_id))
    conn.commit()
    conn.close()


def style_pick_keyboard(prefix: str, back_cb: str):
    return [
        [
            colored_button("Danger", f"{prefix}_danger", style="danger"),
            colored_button("Success", f"{prefix}_success", style="success"),
            colored_button("Primary", f"{prefix}_primary", style="primary"),
        ],
        [colored_back_button(back_cb)]
    ]


# ============================================================
# DATABASE
# ============================================================
# Har table ke saare zaroori columns. Agar purani DB me koi column missing hai
# to init_db() usse automatically add kar deta hai.
REQUIRED_COLUMNS = {
    "users": {
        "username": "TEXT",
        "full_name": "TEXT",
        "balance": "REAL DEFAULT 0.0",
        "is_reseller": "INTEGER DEFAULT 0",
        "total_deposit": "REAL DEFAULT 0.0",
        "referred_by": "INTEGER DEFAULT 0",
        "has_purchased": "INTEGER DEFAULT 0",
        "last_spin_time": "INTEGER DEFAULT 0",
        "lang": "TEXT DEFAULT 'en'",
    },
    "products": {
        "name": "TEXT",
        "category": "TEXT DEFAULT ''",
        "is_maintenance": "INTEGER DEFAULT 0",
        "group_link": "TEXT DEFAULT ''",
        "demo_video": "TEXT DEFAULT ''",
        "button_style": "TEXT DEFAULT 'primary'",
        "emoji_id": "TEXT DEFAULT ''",
    },
    "categories": {
        "name": "TEXT",
        "sort_order": "INTEGER DEFAULT 0",
        "button_style": "TEXT DEFAULT 'success'",
    },
    "plans": {
        "product_pid": "TEXT",
        "duration": "TEXT",
        "remote_duration": "TEXT",
        "price": "REAL DEFAULT 0.0",
        "reseller_price": "REAL DEFAULT 0.0",
        "button_style": "TEXT DEFAULT 'primary'",
    },
    "keys": {
        "product_pid": "TEXT",
        "duration": "TEXT",
        "key_value": "TEXT",
    },
    "history": {
        "user_id": "INTEGER",
        "item_name": "TEXT",
        "key_value": "TEXT",
        "price": "REAL",
        "date": "TIMESTAMP",
    },
    "payments": {
        "user_id": "INTEGER",
        "amount": "REAL",
        "status": "TEXT",
        "plan_id": "INTEGER",
        "purpose": "TEXT DEFAULT 'balance'",
        "provider": "TEXT DEFAULT 'zapupi'",
        "date": "TIMESTAMP",
    },
    "custom_prices": {
        "user_id": "INTEGER",
        "plan_id": "INTEGER",
        "price": "REAL",
    },
    "tickets": {
        "user_id": "INTEGER",
        "status": "TEXT DEFAULT 'open'",
        "created_at": "TIMESTAMP",
    },
    "settings": {
        "value": "TEXT",
    },
}


def ensure_schema(cursor):
    for table, cols in REQUIRED_COLUMNS.items():
        try:
            cursor.execute(f'PRAGMA table_info("{table}")')
            existing = {r[1] for r in cursor.fetchall()}
        except Exception as e:
            logging.error(f"PRAGMA failed for {table}: {e}")
            continue
        for col, decl in cols.items():
            if col not in existing:
                try:
                    cursor.execute(f'ALTER TABLE "{table}" ADD COLUMN "{col}" {decl}')
                    logging.info(f"Migration: added column {table}.{col}")
                except Exception as e:
                    logging.error(f"Migration failed for {table}.{col}: {e}")


def init_db():
    conn = db()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            full_name TEXT,
            balance REAL DEFAULT 0.0,
            is_reseller INTEGER DEFAULT 0,
            total_deposit REAL DEFAULT 0.0,
            referred_by INTEGER DEFAULT 0,
            has_purchased INTEGER DEFAULT 0,
            last_spin_time INTEGER DEFAULT 0,
            lang TEXT DEFAULT 'en'
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            pid TEXT PRIMARY KEY,
            name TEXT,
            category TEXT DEFAULT ''
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_pid TEXT,
            duration TEXT,
            remote_duration TEXT,
            price REAL DEFAULT 0.0,
            reseller_price REAL DEFAULT 0.0
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS keys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_pid TEXT,
            duration TEXT,
            key_value TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            item_name TEXT,
            key_value TEXT,
            price REAL,
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            order_id TEXT PRIMARY KEY,
            user_id INTEGER,
            amount REAL,
            status TEXT,
            plan_id INTEGER,
            purpose TEXT DEFAULT 'balance'
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS custom_prices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            plan_id INTEGER,
            price REAL,
            UNIQUE(user_id, plan_id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tickets (
            ticket_id TEXT PRIMARY KEY,
            user_id INTEGER,
            status TEXT DEFAULT 'open',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)

    # Reseller API keys: one active API credential per reseller account.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reseller_api_keys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL UNIQUE,
            api_key TEXT NOT NULL UNIQUE,
            active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_used_at TIMESTAMP
        )
    """)
    conn.commit()

    # Purani DB me jo columns missing hain unhe add karo
    ensure_schema(cursor)
    conn.commit()

    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('reseller_upgrade_price', '449')")
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('how_to_use_video', '')")
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('zapupi_key', ?)", (DEFAULT_ZAPUPI_KEY,))
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('store_api_key', ?)", (DEFAULT_API_KEY,))
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('support_username', ?)", (DEFAULT_ADMIN_USERNAME,))
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('bot_maintenance', '0')")
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('reseller_enabled', '1')")
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('global_discount', '0')")

    conn.commit()
    conn.close()


init_db()


# ============================================================
# HELPERS & API
# ============================================================
def get_user(user_id, username=None, full_name=None, referrer_id=0):
    conn = db()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, username, full_name, balance, is_reseller, total_deposit, referred_by, has_purchased, last_spin_time, lang FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    if not user:
        ref_by = referrer_id if (referrer_id and referrer_id != user_id) else 0
        cursor.execute("INSERT OR IGNORE INTO users (user_id, username, full_name, referred_by, lang) VALUES (?, ?, ?, ?, 'en')", (user_id, username, full_name, ref_by))
        conn.commit()
        user = (user_id, username, full_name, 0.0, 0, 0.0, ref_by, 0, 0, 'en')
    else:
        updated_uname = username if username is not None else (user[1] if user[1] is not None else "")
        updated_fname = full_name if full_name is not None else (user[2] if user[2] is not None else "")
        if updated_uname != user[1] or updated_fname != user[2]:
            cursor.execute("UPDATE users SET username = ?, full_name = ? WHERE user_id = ?", (updated_uname, updated_fname, user_id))
            conn.commit()
        user = (
            user[0], updated_uname, updated_fname,
            user[3] if user[3] is not None else 0.0,
            user[4] if user[4] is not None else 0,
            user[5] if user[5] is not None else 0.0,
            user[6] if user[6] is not None else 0,
            user[7] if user[7] is not None else 0,
            user[8] if user[8] is not None else 0,
            user[9] if user[9] is not None else 'en',
        )
    conn.close()
    return user


def set_user_lang(user_id, lang):
    conn = db()
    conn.execute("UPDATE users SET lang = ? WHERE user_id = ?", (lang, user_id))
    conn.commit()
    conn.close()


def update_balance(user_id, amount, count_as_deposit=False):
    conn = db()
    if count_as_deposit and amount > 0:
        conn.execute("UPDATE users SET balance = balance + ?, total_deposit = total_deposit + ? WHERE user_id = ?", (amount, amount, user_id))
    else:
        conn.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
    conn.commit()
    conn.close()


def get_setting(key, default=""):
    conn = db()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
    res = cursor.fetchone()
    conn.close()
    return res[0] if res is not None else str(default)


def set_setting(key, value):
    conn = db()
    conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, str(value)))
    conn.commit()
    conn.close()


def get_reseller_price():
    try:
        return float(get_setting('reseller_upgrade_price', '449'))
    except (TypeError, ValueError):
        return 449.0


def get_zapupi_key():
    return (get_setting('zapupi_key', '') or '').strip()


def generate_reseller_api_key():
    return "rk_" + secrets.token_urlsafe(32)


def ensure_reseller_api_key(user_id, force_new=False):
    """Return the reseller's API key, creating/replacing it when required."""
    conn = db()
    cur = conn.cursor()
    try:
        cur.execute("SELECT api_key FROM reseller_api_keys WHERE user_id = ? AND active = 1", (user_id,))
        row = cur.fetchone()
        if row and row[0] and not force_new:
            return row[0]

        key = generate_reseller_api_key()
        if force_new:
            cur.execute("UPDATE reseller_api_keys SET active = 0 WHERE user_id = ?", (user_id,))
        cur.execute(
            "INSERT OR REPLACE INTO reseller_api_keys (user_id, api_key, active) VALUES (?, ?, 1)",
            (user_id, key),
        )
        conn.commit()
        return key
    finally:
        conn.close()


def get_reseller_by_api_key(api_key):
    key = (api_key or '').strip()
    if not key:
        return None
    conn = db()
    cur = conn.cursor()
    try:
        cur.execute(
            """SELECT r.user_id, u.username, u.full_name, u.balance, u.is_reseller
               FROM reseller_api_keys r
               JOIN users u ON u.user_id = r.user_id
               WHERE r.api_key = ? AND r.active = 1""",
            (key,),
        )
        row = cur.fetchone()
        if row:
            cur.execute("UPDATE reseller_api_keys SET last_used_at = CURRENT_TIMESTAMP WHERE api_key = ?", (key,))
            conn.commit()
        return row
    finally:
        conn.close()


def get_store_api_key():
    return (get_setting('store_api_key', DEFAULT_API_KEY) or '').strip()


def get_support_username():
    return (get_setting('support_username', DEFAULT_ADMIN_USERNAME) or '').strip()


def is_bot_maintenance():
    return (get_setting('bot_maintenance', '0') or '0').strip() == '1'


def set_bot_maintenance(flag_on: bool):
    set_setting('bot_maintenance', '1' if flag_on else '0')


def is_reseller_enabled():
    return (get_setting('reseller_enabled', '1') or '1').strip() == '1'


def set_reseller_enabled(flag_on: bool):
    set_setting('reseller_enabled', '1' if flag_on else '0')


# ---------------- GLOBAL DISCOUNT ----------------
def get_global_discount():
    """Percent (0-99). 0 = no discount."""
    try:
        v = float(get_setting('global_discount', '0') or 0)
    except (TypeError, ValueError):
        return 0.0
    if not math.isfinite(v) or v < 0:
        return 0.0
    return min(v, MAX_DISCOUNT)


def set_global_discount(pct):
    try:
        v = float(pct)
    except (TypeError, ValueError):
        v = 0.0
    if not math.isfinite(v) or v < 0:
        v = 0.0
    set_setting('global_discount', str(round(min(v, MAX_DISCOUNT), 2)))


def apply_discount(price):
    d = get_global_discount()
    price = float(price or 0.0)
    if d <= 0:
        return price
    return max(0.0, round(price * (1 - d / 100.0), 2))


async def send_maintenance_notice(update: Update):
    if update.callback_query:
        await ans(update.callback_query)
        try:
            await sedit(update.callback_query, MAINTENANCE_MSG)
            return
        except Exception:
            pass
        try:
            await sreply(update.callback_query.message, MAINTENANCE_MSG)
        except Exception:
            pass
    elif update.effective_message:
        try:
            await sreply(update.effective_message, MAINTENANCE_MSG)
        except Exception:
            pass


IST_OFFSET = timedelta(hours=5, minutes=30)


def to_ist_str(utc_str):
    if not utc_str:
        return "N/A"
    try:
        dt = datetime.strptime(str(utc_str)[:19], "%Y-%m-%d %H:%M:%S")
    except Exception:
        return str(utc_str)
    ist_dt = dt + IST_OFFSET
    return ist_dt.strftime("%d %b %Y, %I:%M %p")


def generate_ticket_id():
    conn = db()
    cursor = conn.cursor()
    while True:
        tid = "TKT-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
        cursor.execute("SELECT 1 FROM tickets WHERE ticket_id = ?", (tid,))
        if not cursor.fetchone():
            conn.close()
            return tid


def build_premium_welcome_text(name, bal, uid):
    n = md_escape(name)
    disc = get_global_discount()
    sale_line = f"🔥 *{md_escape(fmt_pct(disc))}% OFF on all products\\!*\n\n" if disc > 0 else ""
    return (
        f"{emj('6163205892834598715')}━━ *Suraj Shop Bot* ━━{emj('6163205892834598715')}\n\n"
        f"{emj('5472055112702629499')} Welcome, *{n}*\n\n"
        f"{emj('6160948518153363716')} ━ *STORE HIGHLIGHTS* ━ {emj('6160948518153363716')}\n\n"
        f"{emj('6160968017304888311')} Premium Game Keys\n"
        f"{emj('6161030148301791023')} Instant Delivery 24/7\n"
        f"{emj('6097972589513154745')} 100% Secure Payment\n"
        f"{emj('6098001906959916194')} Best Prices Guaranteed\n"
        f"{emj('6098294647635844755')} Professional Support\n\n"
        f"{sale_line}"
        f"{emj('6199422882435571592')} Balance: ₹{fmt_amount(bal)}\n"
        f"{emj('6145426283007320286')} User ID: `{uid}`\n\n"
        f"{emj('6097957492703109785')} Tap Shop Now to Start\\!"
    )


# ============================================================
# TOP BUYERS LEADERBOARD
# ============================================================
def get_top_buyers(limit=LEADERBOARD_LIMIT):
    """History table se top buyers: (user_id, name, total_orders, total_spend)."""
    conn = db()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT h.user_id,
                   COALESCE(NULLIF(TRIM(u.full_name), ''), NULLIF(TRIM(u.username), ''), 'N/A') AS nm,
                   COUNT(*) AS orders,
                   COALESCE(SUM(h.price), 0) AS spend
            FROM history h
            LEFT JOIN users u ON u.user_id = h.user_id
            GROUP BY h.user_id
            ORDER BY spend DESC, orders DESC
            LIMIT ?
            """,
            (limit,)
        )
        return cur.fetchall()
    finally:
        conn.close()


def build_leaderboard_text(rows):
    medals = ["🥇", "🥈", "🥉", "🏅", "🎖️"]
    header = (
        f"{emj(EMOJI_LB_TROPHY)} *TOP {LEADERBOARD_LIMIT} BUYERS LEADERBOARD* {emj(EMOJI_LB_TROPHY)}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"_Ranked by total successful purchase value\\._\n\n"
    )
    if not rows:
        return header + "_No purchases yet\\. Be the first one on the board\\!_"

    body = ""
    for i, (_uid, name, orders, spend) in enumerate(rows, 1):
        medal = medals[i - 1] if i <= len(medals) else "🏅"
        nm = str(name or "N/A")
        if len(nm) > 25:
            nm = nm[:25] + "..."
        body += (
            f"{medal} *TOP {i}*\n"
            f"{emj(EMOJI_LB_NAME)} *Name:* {md_escape(nm)}\n"
            f"{emj(EMOJI_LB_ORDERS)} *Total Orders:* {orders}\n"
            f"{emj(EMOJI_LB_SPEND)} *Total Spend:* ₹{fmt_amount(spend)}\n"
            f"─────────────────────\n"
        )
    return header + body


# ============================================================
# BACKUP / RESTORE
# ============================================================
BACKUP_TABLES = [
    "users", "products", "categories", "plans", "keys", "reseller_api_keys",
    "history", "payments", "custom_prices", "tickets", "settings",
]

BACKUP_LABELS = {
    "users": "Users (balance / reseller)",
    "products": "Products",
    "categories": "Categories",
    "plans": "Plans (price / reseller price)",
    "keys": "Keys stock",
    "reseller_api_keys": "Reseller API credentials",
    "history": "Purchase history",
    "payments": "Payments",
    "custom_prices": "Custom prices",
    "tickets": "Tickets",
    "settings": "Settings (API keys / payment / prices / discount)",
}

MAX_RESTORE_BYTES = 20 * 1024 * 1024  # Telegram bot download limit ~20MB


def dump_tables_from_conn(conn):
    """Saari tables ka data {table: {"columns": [...], "rows": [[...]]}} format me."""
    out = {}
    cur = conn.cursor()
    for t in BACKUP_TABLES:
        try:
            cur.execute(f'PRAGMA table_info("{t}")')
            cols = [r[1] for r in cur.fetchall()]
            if not cols:
                continue
            col_sql = ", ".join(f'"{c}"' for c in cols)
            cur.execute(f'SELECT {col_sql} FROM "{t}"')
            rows = [list(r) for r in cur.fetchall()]
            out[t] = {"columns": cols, "rows": rows}
        except Exception as e:
            logging.error(f"Backup dump failed for table {t}: {e}")
    return out


def backup_filename():
    ist_now = datetime.now(timezone.utc) + IST_OFFSET
    return "store_backup_" + ist_now.strftime("%Y%m%d_%H%M%S") + ".zip"


def build_backup_zip():
    """Blocking. Returns (zip_bytes, counts). asyncio.to_thread se chalao."""
    conn = db()
    try:
        tables = dump_tables_from_conn(conn)
        fd, tmp = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        try:
            dst = sqlite3.connect(tmp)
            try:
                conn.backup(dst)
            finally:
                dst.close()
            with open(tmp, "rb") as f:
                db_bytes = f.read()
        finally:
            try:
                os.remove(tmp)
            except Exception:
                pass
    finally:
        conn.close()

    counts = {t: len(v["rows"]) for t, v in tables.items()}
    payload = {
        "meta": {
            "created_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
            "version": 1,
            "counts": counts,
        },
        "tables": tables,
    }
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("backup.json", json.dumps(payload, ensure_ascii=False))
        zf.writestr("surajbot.db", db_bytes)
    return buf.getvalue(), counts


def backup_summary_text(counts):
    lines = []
    for t in BACKUP_TABLES:
        if t in counts:
            lines.append(f"• {BACKUP_LABELS.get(t, t)}: {counts[t]}")
    return "\n".join(lines) if lines else "(empty)"


def _validate_tables(tables):
    if not isinstance(tables, dict):
        raise ValueError("Backup format galat hai.")
    clean = {}
    for t in BACKUP_TABLES:
        blk = tables.get(t)
        if not blk:
            continue
        cols = blk.get("columns")
        rows = blk.get("rows")
        if not isinstance(cols, list) or not isinstance(rows, list):
            raise ValueError(f"Table '{t}' ka format galat hai.")
        for r in rows:
            if not isinstance(r, list) or len(r) != len(cols):
                raise ValueError(f"Table '{t}' me corrupted row mili.")
        clean[t] = {"columns": cols, "rows": rows}
    if not clean:
        raise ValueError("Backup me koi data table nahi mila.")
    return clean


def parse_backup_zip(raw: bytes):
    """Blocking. ZIP validate karke tables dict return karta hai."""
    zf = zipfile.ZipFile(io.BytesIO(raw))
    infos = {i.filename: i for i in zf.infolist()}

    if "backup.json" in infos:
        if infos["backup.json"].file_size > 200 * 1024 * 1024:
            raise ValueError("backup.json bahut bada hai.")
        payload = json.loads(zf.read("backup.json").decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("backup.json galat hai.")
        return _validate_tables(payload.get("tables"))

    db_name = next((n for n in infos if n.lower().endswith(".db")), None)
    if db_name:
        if infos[db_name].file_size > 200 * 1024 * 1024:
            raise ValueError("DB file bahut badi hai.")
        fd, tmp = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        try:
            with open(tmp, "wb") as f:
                f.write(zf.read(db_name))
            c = sqlite3.connect(tmp)
            try:
                tables = dump_tables_from_conn(c)
            finally:
                c.close()
        finally:
            try:
                os.remove(tmp)
            except Exception:
                pass
        return _validate_tables(tables)

    raise ValueError("ZIP me backup.json ya .db file nahi mili.")


def apply_restore(tables):
    """Blocking. Backup ke tables se current DB replace karta hai (ek transaction me)."""
    init_db()
    conn = db()
    counts = {}
    try:
        cur = conn.cursor()
        cur.execute("BEGIN IMMEDIATE")
        for t in BACKUP_TABLES:
            if t not in tables:
                continue
            cur.execute(f'PRAGMA table_info("{t}")')
            cur_cols = {r[1] for r in cur.fetchall()}
            b_cols = tables[t]["columns"]
            use = [(i, c) for i, c in enumerate(b_cols) if c in cur_cols]
            cur.execute(f'DELETE FROM "{t}"')
            if use:
                col_sql = ", ".join(f'"{c}"' for _, c in use)
                ph = ", ".join("?" for _ in use)
                sql = f'INSERT OR REPLACE INTO "{t}" ({col_sql}) VALUES ({ph})'
                rows = [[row[i] for i, _ in use] for row in tables[t]["rows"]]
                cur.executemany(sql, rows)
            counts[t] = len(tables[t]["rows"])
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    init_db()  # missing default settings wapas fill ho jayengi
    return counts


REORDER_CATEGORIES_TEXT = (
    "↕️ **REORDER CATEGORIES** ↕️\n"
    "━━━━━━━━━━━━━━━━━━━━\n\n"
    "📌 This is the order categories appear in for users (top → bottom) on the 🛍️ Shop Now screen.\n\n"
    "⬆️ / ⬇️ moves a category up or down one spot — tap repeatedly to send it all the way to the top, the bottom, or anywhere in the middle.\n\n"
    "👇 **Current order:**"
)


def build_category_reorder_keyboard(cursor):
    cursor.execute("SELECT id, name FROM categories ORDER BY sort_order, id")
    cats = cursor.fetchall()
    keyboard = []
    total = len(cats)
    for idx, c in enumerate(cats):
        c_id, c_name = c[0], c[1]
        row = [colored_button(f"{idx + 1}. {c_name}", "admin_reorder_categories", style="secondary")]
        if idx > 0:
            row.append(colored_button("⬆️", f"catmove_up_{c_id}", style="primary"))
        if idx < total - 1:
            row.append(colored_button("⬇️", f"catmove_down_{c_id}", style="primary"))
        keyboard.append(row)
    keyboard.append([colored_back_button("admin_back_panel")])
    return cats, keyboard


def move_category(cursor, cat_id: int, direction: str):
    cursor.execute("SELECT id FROM categories ORDER BY sort_order, id")
    ids = [r[0] for r in cursor.fetchall()]
    if cat_id not in ids:
        return
    pos = ids.index(cat_id)
    swap_pos = pos - 1 if direction == "up" else pos + 1
    if not (0 <= swap_pos < len(ids)):
        return
    for i, cid in enumerate(ids):
        cursor.execute("UPDATE categories SET sort_order = ? WHERE id = ?", (i, cid))
    id_a, id_b = ids[pos], ids[swap_pos]
    cursor.execute("UPDATE categories SET sort_order = ? WHERE id = ?", (swap_pos, id_a))
    cursor.execute("UPDATE categories SET sort_order = ? WHERE id = ?", (pos, id_b))


def mask_secret(s):
    if not s:
        return "Not Set"
    if len(s) <= 8:
        return s[:2] + "*****" + s[-1:] if len(s) > 1 else s
    return f"{s[:5]}*****{s[-3:]}"


def get_custom_price(user_id, plan_id):
    conn = db()
    cursor = conn.cursor()
    cursor.execute("SELECT price FROM custom_prices WHERE user_id = ? AND plan_id = ?", (user_id, plan_id))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row is not None else None


def set_custom_price(user_id, plan_id, price):
    conn = db()
    conn.execute("INSERT OR REPLACE INTO custom_prices (user_id, plan_id, price) VALUES (?, ?, ?)", (user_id, plan_id, price))
    conn.commit()
    conn.close()


def get_effective_price(user_id, plan_id, normal_price, reseller_price, is_reseller):
    """Custom price (admin ne user ke liye fix kiya) hamesha jeetta hai.
    Warna normal/reseller price pe global discount lagta hai."""
    custom = get_custom_price(user_id, plan_id)
    if custom is not None:
        return custom
    base = reseller_price if is_reseller else normal_price
    return apply_discount(base)


def is_low_balance_error(msg):
    if not msg:
        return False
    msg_l = str(msg).lower()
    keywords = ["insufficient", "low balance", "low_balance", "not enough balance",
                "add balance", "recharge", "out of stock", "no stock", "wallet balance"]
    return any(k in msg_l for k in keywords)


def call_reseller_api(pid, remote_duration=None):
    """Blocking call - hamesha asyncio.to_thread ke through chalao."""
    active_api_key = get_store_api_key()
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'x-master-key': MASTER_KEY,
        'User-Agent': 'Mozilla/5.0'
    }
    data = {
        'api_key': active_api_key,
        'action': 'buy',
        'pid': pid,
        'product_id': pid,
    }
    if remote_duration:
        data['duration'] = remote_duration
        data['sku'] = remote_duration
        data['plan'] = remote_duration

    try:
        response = requests.post(API_URL, data=data, headers=headers, timeout=20, verify=False)
    except Exception as e:
        return False, f"API Request Failed: {e}"

    try:
        res_json = response.json()
    except Exception:
        raw = (response.text or "").strip()
        if not raw or "error" in raw.lower():
            return False, raw or "Empty API Response"
        return True, raw

    if not isinstance(res_json, dict):
        return True, str(res_json)

    if res_json.get("status") == "error" or res_json.get("error"):
        return False, res_json.get("msg", res_json.get("error", "API Order Failed!"))

    key = res_json.get("key") or res_json.get("code") or res_json.get("data") or str(res_json)
    return True, key


async def process_referral_reward(context: ContextTypes.DEFAULT_TYPE, user_id: int):
    conn = db()
    cursor = conn.cursor()
    cursor.execute("SELECT referred_by, has_purchased FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    referred_by = 0
    reward = False
    if row:
        referred_by, has_purchased = row[0], row[1]
        if has_purchased == 0:
            cursor.execute("UPDATE users SET has_purchased = 1 WHERE user_id = ?", (user_id,))
            if referred_by and referred_by > 0 and referred_by != user_id:
                cursor.execute("UPDATE users SET balance = balance + 1.0 WHERE user_id = ?", (referred_by,))
                reward = True
            conn.commit()
    conn.close()
    if reward:
        try:
            await ssend(
                context.bot, referred_by,
                "🎉 **Referral Reward Credited!**\n\nA user you referred made their first purchase! **₹1.00** has been added to your balance."
            )
        except Exception as e:
            logging.error(f"Failed to send referral reward alert: {e}")


async def send_purchase_admin_alert(context: ContextTypes.DEFAULT_TYPE, user_id: int, prod_name: str, duration: str, key_delivered: str, cost: float, purchase_type: str):
    conn = db()
    cursor = conn.cursor()
    cursor.execute("SELECT full_name, username, balance FROM users WHERE user_id = ?", (user_id,))
    u_row = cursor.fetchone()
    conn.close()
    full_name = escape_markdown(u_row[0]) if u_row and u_row[0] else "N/A"
    username = f"@{escape_markdown(u_row[1])}" if u_row and u_row[1] else "N/A"
    balance = u_row[2] if u_row and u_row[2] is not None else 0.0
    safe_key = str(key_delivered).replace("`", "'")
    try:
        await ssend(
            context.bot, ADMIN_ID,
            f"🛒 **NEW PURCHASE NOTIFICATION**\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🏷️ **Type:** {escape_markdown(purchase_type)}\n"
            f"📦 **Product:** {escape_markdown(prod_name)}\n"
            f"⏱️ **Plan:** {escape_markdown(duration)}\n"
            f"🔑 **Key:** `{safe_key}`\n"
            f"💵 **Price Paid:** ₹{cost:.2f}\n\n"
            f"👤 **Name:** {full_name}\n"
            f"🏷️ **Username:** {username}\n"
            f"🆔 **User ID:** `{user_id}`\n"
            f"💰 **Available Balance:** ₹{balance:.2f}\n"
            f"━━━━━━━━━━━━━━━━━━━━"
        )
    except Exception as e:
        logging.error(f"Failed to notify admin on purchase: {e}")


async def send_admin_low_balance_alert(context: ContextTypes.DEFAULT_TYPE, user_id: int, prod_name: str, duration: str, price: float, reason: str):
    conn = db()
    cursor = conn.cursor()
    cursor.execute("SELECT full_name, username, balance, is_reseller FROM users WHERE user_id = ?", (user_id,))
    u_row = cursor.fetchone()
    conn.close()
    full_name = escape_markdown(u_row[0]) if u_row and u_row[0] else "N/A"
    username = f"@{escape_markdown(u_row[1])}" if u_row and u_row[1] else "N/A"
    wallet_balance = u_row[2] if u_row and u_row[2] is not None else 0.0
    acc_type = "🌟 Reseller" if (u_row and u_row[3]) else "👤 User"
    try:
        await ssend(
            context.bot, ADMIN_ID,
            f"⚠️ **LOW API BALANCE / ORDER FAILED** ⚠️\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 **Name:** {full_name}\n"
            f"🏷️ **Username:** {username}\n"
            f"🆔 **User ID:** `{user_id}`\n"
            f"💰 **Wallet Balance:** ₹{wallet_balance:.2f}\n"
            f"🏷️ **Account Type:** {acc_type}\n\n"
            f"📦 **Product:** {escape_markdown(prod_name)}\n"
            f"⏱️ **Plan:** {escape_markdown(duration)}\n"
            f"💵 **Price:** ₹{price:.2f}\n\n"
            f"❌ **Reason:** {escape_markdown(reason)}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"👉 Please top up the reseller panel / restock, then ask the user to retry."
        )
    except Exception as e:
        logging.error(f"Failed to notify admin of low API balance: {e}")


def _insufficient_text(prod_name, duration, cost, balance):
    deficit = round(cost - balance, 2)
    return (
        f"⚠️ *Not Enough Balance Yet\\!*\n\n"
        f"📦 *Item:* {md_escape(prod_name)} \\({md_escape(duration)}\\)\n"
        f"💵 *Item Price:* ₹{fmt_amount(cost)}\n"
        f"💰 *Your Balance:* ₹{fmt_amount(balance)}\n"
        f"🧾 *Need To Buy:* ₹{fmt_amount(deficit)}\n\n"
        f"Please go to 🛍️ Shop Now and buy again to complete the order\\."
    )


async def finalize_purchase(context: ContextTypes.DEFAULT_TYPE, user_id: int, plan_id, purchase_type="Manual/Balance"):
    conn = db()
    cursor = conn.cursor()

    cursor.execute("SELECT product_pid, duration, remote_duration, price, reseller_price FROM plans WHERE id = ?", (plan_id,))
    plan = cursor.fetchone()
    if not plan:
        conn.close()
        return False, "❌ This plan no longer exists\\.", ""

    cursor.execute("SELECT name, group_link FROM products WHERE pid = ?", (plan[0],))
    prod_row = cursor.fetchone()
    prod_name = prod_row[0] if prod_row else "Unknown Product"
    group_link = (prod_row[1] if prod_row and len(prod_row) > 1 and prod_row[1] else "").strip()

    cursor.execute("SELECT balance, is_reseller FROM users WHERE user_id = ?", (user_id,))
    bal_row = cursor.fetchone()
    if not bal_row:
        balance, is_reseller = 0.0, 0
    else:
        balance = bal_row[0] if bal_row[0] is not None else 0.0
        is_reseller = bal_row[1] if bal_row[1] is not None else 0

    cost = get_effective_price(user_id, plan_id, plan[3], plan[4], is_reseller)

    if balance < cost:
        conn.close()
        return False, _insufficient_text(prod_name, plan[1], cost, balance), ""

    cursor.execute("SELECT id, key_value FROM keys WHERE product_pid = ? AND duration = ? ORDER BY id LIMIT 1", (plan[0], plan[1]))
    key_data = cursor.fetchone()

    if key_data:
        key_id, key_delivered = key_data
        # Atomic: balance tabhi katega jab sach me bacha ho
        cursor.execute("UPDATE users SET balance = balance - ? WHERE user_id = ? AND balance >= ?", (cost, user_id, cost))
        if cursor.rowcount == 0:
            conn.rollback()
            conn.close()
            return False, _insufficient_text(prod_name, plan[1], cost, balance), ""
        cursor.execute("DELETE FROM keys WHERE id = ?", (key_id,))
        if cursor.rowcount == 0:
            # Kisi aur ne wahi key abhi le li
            conn.rollback()
            conn.close()
            return False, "⚠️ Stock just changed\\. Please tap the plan again\\.", ""
    else:
        conn.close()  # API call ke dauran DB connection khula nahi rakhna
        success, api_msg = await asyncio.to_thread(call_reseller_api, plan[0], plan[2])
        if not success:
            reason = api_msg if is_low_balance_error(api_msg) else f"API Error: {api_msg}"
            await send_admin_low_balance_alert(context, user_id, prod_name, plan[1], cost, reason)
            return False, (
                f"❌ *Purchase Failed\\!*\n\n"
                f"📦 *Item:* {md_escape(prod_name)}\n"
                f"⏱️ *Duration:* {md_escape(plan[1])}\n\n"
                f"⏳ Our stock/API is temporarily unavailable\\. Please wait a few minutes and try again\\.\n"
                f"💰 *Balance Deducted:* ₹0\\.00 \\(Safe\\)\n\n"
                f"If this keeps happening, contact ☎️ Admin Support\\."
            ), ""
        key_delivered = str(api_msg)
        purchase_type = "API"
        conn = db()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (cost, user_id))

    cursor.execute("INSERT INTO history (user_id, item_name, key_value, price) VALUES (?, ?, ?, ?)",
                   (user_id, f"{prod_name} ({plan[1]})", key_delivered, cost))
    conn.commit()
    conn.close()

    await process_referral_reward(context, user_id)
    await send_purchase_admin_alert(context, user_id, prod_name, plan[1], key_delivered, cost, purchase_type)

    text = (
        f"{emj(EMOJI_PURCHASE_SUCCESS)} *Purchase Successful* {emj(EMOJI_PURCHASE_SUCCESS)}\n\n"
        f"📦 *Item:* {md_escape(prod_name)}\n"
        f"⏱️ *Duration:* {md_escape(plan[1])}\n"
        f"{emj(EMOJI_YOUR_KEY)} *Your Key:* `{code_escape(key_delivered)}`\n"
        f"💵 *Price:* ₹{fmt_amount(cost)}\n"
        f"{emj(EMOJI_YOUR_BALANCE)} *Your Balance:* ₹{fmt_amount(balance - cost)}"
    )
    return True, text, group_link


async def deliver_purchase_result(context: ContextTypes.DEFAULT_TYPE, chat_id: int, text: str, back_btn_txt: str = "Back", group_link: str = "", parse_mode: str = "MarkdownV2"):
    keyboard = []
    if group_link:
        keyboard.append([colored_url_button("Join Updates", group_link, style="primary", icon_custom_emoji_id="5350452584119279096")])
    keyboard.append([colored_button(back_btn_txt, "main_menu", style="danger", icon_custom_emoji_id=BACK_ICON)])
    await ssend(context.bot, chat_id, text, InlineKeyboardMarkup(keyboard), parse_mode)


async def show_product_plans_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, pid: str, user_id: int):
    conn = db()
    cursor = conn.cursor()
    cursor.execute("SELECT name, is_maintenance, demo_video, category FROM products WHERE pid = ?", (pid,))
    prod = cursor.fetchone()

    cursor.execute("SELECT is_reseller, lang FROM users WHERE user_id = ?", (user_id,))
    u_row = cursor.fetchone()
    is_reseller = u_row[0] if u_row and u_row[0] is not None else 0

    back_to_products_cb = "user_shop"
    if prod:
        cat_name = prod[3] if prod[3] else ''
        if cat_name:
            cursor.execute("SELECT id FROM categories WHERE name = ?", (cat_name,))
            crow = cursor.fetchone()
            back_to_products_cb = f"shop_cat_{crow[0]}" if crow else "user_shop"
        else:
            back_to_products_cb = "shop_cat_0"
    back_kb = user_back_kb("Back", back_to_products_cb)

    async def _send(text, kb, pm):
        if update.callback_query:
            await sedit(update.callback_query, text, kb, pm)
        else:
            await sreply(update.message, text, kb, pm)

    if prod and prod[1]:
        conn.close()
        await _send(f"🛠 **{escape_markdown(prod[0])}**\n\nThis product is in maintenance now. Please check back later.", back_kb, "Markdown")
        return

    cursor.execute("SELECT id, duration, price, reseller_price, button_style FROM plans WHERE product_pid = ? ORDER BY id", (pid,))
    plans = cursor.fetchall()
    conn.close()

    if not prod or not plans:
        await _send("⚠️ Product/Plans currently unavailable.", back_kb, "Markdown")
        return

    keyboard = []
    for pl in plans:
        cost = get_effective_price(user_id, pl[0], pl[2], pl[3], is_reseller)
        plan_style = norm_style(pl[4], "primary")
        keyboard.append([colored_button(
            f"{pl[1]} - ₹{cost:.2f}",
            f"buy_final_{pl[0]}",
            style=plan_style,
            icon_custom_emoji_id=EMOJI_PLAN
        )])
    demo_video = prod[2] if prod[2] else ""
    if demo_video:
        keyboard.append([colored_url_button("Check Gameplay Video", demo_video, style="primary", icon_custom_emoji_id=EMOJI_GAMEPLAY_VIDEO)])
    keyboard.append([colored_button("Back", back_to_products_cb, style="danger", icon_custom_emoji_id=BACK_ICON)])

    disc = get_global_discount()
    disc_line = f"🔥 *{md_escape(fmt_pct(disc))}% OFF applied on all plans\\!*\n" if disc > 0 else ""

    text = (
        f"{emj(EMOJI_PROD_LINE_1)} *{md_escape(prod[0])}* {emj(EMOJI_PROD_LINE_1)}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"{disc_line}"
        f"{emj(EMOJI_PROD_LINE_2)} *AVAILABLE PLANS & PRICING*\n\n"
        f"{emj(EMOJI_PROD_LINE_3)} *Select Your Plan Below* {emj(EMOJI_PROD_LINE_3)}"
    )
    await _send(text, InlineKeyboardMarkup(keyboard), "MarkdownV2")


async def finalize_reseller_upgrade(context: ContextTypes.DEFAULT_TYPE, user_id: int):
    price = get_reseller_price()
    conn = db()
    cursor = conn.cursor()
    cursor.execute("SELECT balance, is_reseller, full_name, username FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    if not row:
        balance, is_reseller, full_name, username = 0.0, 0, "N/A", "N/A"
    else:
        balance = row[0] if row[0] is not None else 0.0
        is_reseller = row[1] if row[1] is not None else 0
        full_name = row[2] if row[2] is not None else "N/A"
        username = row[3] if row[3] is not None else "N/A"

    if is_reseller:
        conn.close()
        return False, "✅ You're already a **Reseller**! 🌟"

    if balance < price:
        conn.close()
        deficit = round(price - balance, 2)
        return False, (
            f"⚠️ **Still Short On Balance!**\n\n"
            f"💎 **Upgrade Price:** ₹{price:.2f}\n"
            f"💰 **Your Balance:** ₹{balance:.2f}\n"
            f"🧾 **Need To Buy:** ₹{deficit:.2f}\n\n"
            f"Please try again from the Main Menu."
        )

    cursor.execute("UPDATE users SET balance = balance - ?, is_reseller = 1 WHERE user_id = ? AND balance >= ?", (price, user_id, price))
    if cursor.rowcount == 0:
        conn.rollback()
        conn.close()
        return False, "⚠️ Balance changed. Please try again from the Main Menu."
    conn.commit()
    conn.close()

    try:
        user_uname = f"@{escape_markdown(username)}" if username and username != "N/A" else "N/A"
        await ssend(
            context.bot, ADMIN_ID,
            f"🔥 **NEW RESELLER UPGRADE!** 🔥\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 **Name:** {escape_markdown(full_name)}\n"
            f"🏷️ **Username:** {user_uname}\n"
            f"🆔 **User ID:** `{user_id}`\n"
            f"💵 **Paid Amount:** ₹{price:.2f}\n"
            f"━━━━━━━━━━━━━━━━━━━━"
        )
    except Exception as e:
        logging.error(f"Failed to notify admin: {e}")

    api_key = ensure_reseller_api_key(user_id)
    text = (
        f"🎉 **Upgrade Successful!**\n\n"
        f"You are now a **Reseller** 🌟\n"
        f"💵 **Amount Deducted:** ₹{price:.2f}\n\n"
        f"🔑 **Reseller API Key:** `{api_key}`\n"
        f"📚 **API Docs:** `/api/docs`\n\n"
        f"Enjoy special reseller pricing on all products!"
    )
    return True, text


# ============================================================
# ZAPUPI
# ============================================================
def create_zapupi_order(amount: float, remark: str = ""):
    """Blocking - asyncio.to_thread se chalao. Returns (ok, payment_url_or_error, order_id)."""
    zap_key = get_zapupi_key()
    if not zap_key or zap_key.strip() == DEFAULT_ZAPUPI_KEY:
        return False, "ZAPUPI_KEY_NOT_SET", None

    order_id = "ORD" + str(int(time.time() * 1000)) + uuid.uuid4().hex[:6].upper()
    payload = {
        "zap_key": zap_key,
        "order_id": order_id,
        "amount": str(amount),
    }
    if remark:
        payload["remark"] = remark[:100]

    try:
        resp = requests.post(f"{ZAPUPI_API_BASE}/create-order", json=payload, timeout=15)
    except Exception as e:
        logging.error(f"ZapUPI create-order network error (order_id={order_id}): {e}")
        return False, f"Network error contacting ZapUPI: {e}", None

    logging.info(f"ZapUPI create-order HTTP {resp.status_code} | order_id={order_id} | amount={amount} | body={resp.text[:500]}")

    if resp.status_code != 200:
        return False, f"ZapUPI HTTP {resp.status_code}: {resp.text[:200]}", None

    try:
        res = resp.json()
    except Exception:
        return False, f"ZapUPI returned non-JSON response: {resp.text[:200]}", None

    status = str(res.get("status", "")).strip().lower()
    if status != "success":
        return False, (res.get("message") or res.get("msg") or f"ZapUPI Order Creation Failed: {res}"), None

    data_block = res.get("data") if isinstance(res.get("data"), dict) else res
    payment_url = (
        data_block.get("payment_url") or data_block.get("payment_link")
        or data_block.get("checkout_url") or data_block.get("url")
        or res.get("payment_url")
    )
    returned_order_id = data_block.get("order_id") or res.get("order_id") or order_id

    if not payment_url:
        logging.error(f"ZapUPI create-order succeeded but no payment_url found in response: {res}")
        return False, f"No payment_url in ZapUPI response: {res}", None

    return True, payment_url, returned_order_id


def verify_zapupi_order(order_id: str):
    """Blocking - asyncio.to_thread se chalao. Returns (is_success, amount)."""
    zap_key = get_zapupi_key()
    payload = {"zap_key": zap_key, "order_id": order_id}
    try:
        resp = requests.post(f"{ZAPUPI_API_BASE}/order-status", json=payload, timeout=10)
    except Exception as e:
        logging.error(f"ZapUPI order-status network error ({order_id}): {e}")
        return False, 0.0

    if resp.status_code != 200:
        logging.error(f"ZapUPI order-status HTTP {resp.status_code} ({order_id}): {resp.text[:300]}")
        return False, 0.0

    try:
        res = resp.json()
    except Exception:
        logging.error(f"ZapUPI order-status non-JSON response ({order_id}): {resp.text[:300]}")
        return False, 0.0

    data_block = res.get("data") if isinstance(res.get("data"), dict) else res
    status = str(data_block.get("status") or res.get("status") or "").strip().lower()

    if status in ("success", "paid", "completed"):
        raw_amt = data_block.get("pay_amount") or data_block.get("amount") or res.get("amount") or 0.0
        try:
            amt = float(raw_amt)
        except (TypeError, ValueError):
            amt = 0.0
        return True, amt
    return False, 0.0


async def poll_payment_status(context: ContextTypes.DEFAULT_TYPE, order_id: str, user_id: int, msg_id: int, purpose: str, pending_plan_id, amount_needed: float):
    max_seconds = 300
    interval = 5
    elapsed = 0

    while elapsed < max_seconds:
        await asyncio.sleep(interval)
        elapsed += interval

        try:
            is_success, amt = await asyncio.to_thread(verify_zapupi_order, order_id)
            if not is_success:
                continue

            credit_amt = amt if amt and amt > 0 else amount_needed

            conn = db()
            cursor = conn.cursor()
            # Atomic claim: sirf ek hi baar credit hoga
            cursor.execute(
                "UPDATE payments SET status = 'SUCCESS', amount = ?, date = datetime('now') WHERE order_id = ? AND status = 'PENDING'",
                (credit_amt, order_id)
            )
            if cursor.rowcount == 0:
                conn.close()
                return
            cursor.execute("UPDATE users SET balance = balance + ?, total_deposit = total_deposit + ? WHERE user_id = ?", (credit_amt, credit_amt, user_id))
            cursor.execute("SELECT full_name, username, lang FROM users WHERE user_id = ?", (user_id,))
            u_info = cursor.fetchone()
            conn.commit()
            conn.close()

            full_name = escape_markdown(u_info[0]) if u_info and u_info[0] else "N/A"
            username = f"@{escape_markdown(u_info[1])}" if u_info and u_info[1] else "N/A"
            u_lang = u_info[2] if u_info and u_info[2] else 'en'
            back_btn_txt = get_txt("btn_back", u_lang)

            try:
                await ssend(
                    context.bot, ADMIN_ID,
                    f"🔔 **Auto-Payment Verified!**\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"👤 **Name:** {full_name}\n"
                    f"🏷️ **Username:** {username}\n"
                    f"🆔 **User ID:** `{user_id}`\n"
                    f"💵 **Amount Credited:** ₹{credit_amt:.2f}\n"
                    f"🏷️ **Purpose:** {escape_markdown(purpose)}\n"
                    f"💳 **Gateway:** ZAPUPI\n"
                    f"🆔 **Order ID:** `{order_id}`\n"
                    f"━━━━━━━━━━━━━━━━━━━━"
                )
            except Exception:
                pass

            try:
                await context.bot.delete_message(chat_id=user_id, message_id=msg_id)
            except Exception:
                pass

            if purpose == 'plan' and pending_plan_id:
                success, text, group_link = await finalize_purchase(context, user_id, pending_plan_id, purchase_type="Direct QR / Auto UPI")
                await deliver_purchase_result(context, user_id, text, back_btn_txt, group_link)
            elif purpose == 'reseller':
                success, text = await finalize_reseller_upgrade(context, user_id)
                await deliver_purchase_result(context, user_id, text, back_btn_txt, parse_mode="Markdown")
            else:
                dep_text = (
                    f"{emj('6089118454302909415')} *Payment Received & Verified\\!* {emj('6089118454302909415')}\n\n"
                    f"{emj('6334666613698075229')} *Amount Credited:* ₹{fmt_amount(credit_amt)}\n"
                    f"{emj('6199422882435571592')} *Order ID:* `{code_escape(order_id)}`"
                )
                await deliver_purchase_result(context, user_id, dep_text, back_btn_txt, parse_mode="MarkdownV2")
            return
        except Exception as e:
            logging.error(f"Polling Exception ({order_id}): {e}")

    conn = db()
    conn.execute("UPDATE payments SET status = 'EXPIRED' WHERE order_id = ? AND status = 'PENDING'", (order_id,))
    conn.commit()
    conn.close()

    try:
        try:
            await context.bot.delete_message(chat_id=user_id, message_id=msg_id)
        except Exception:
            pass
        expired_text = (
            f"Your payment link for ₹{amount_needed:.2f} expired because no payment was received within 5 minutes.\n\n"
            f"You can try again anytime."
        )
        retry_markup = InlineKeyboardMarkup([[colored_button("Try Again", "user_shop", style="success")]])
        await context.bot.send_message(chat_id=user_id, text=expired_text, reply_markup=retry_markup)
    except Exception as e:
        logging.error(f"Failed to send expired msg: {e}")


async def raise_payment_qr(context: ContextTypes.DEFAULT_TYPE, user_id: int, target_amount: float, current_balance: float, purpose: str, label: str, plan_id=None):
    """Sirf manual 'Add Balance' flow ke liye."""
    deficit = round(target_amount - current_balance, 2)
    if deficit <= 0:
        deficit = round(target_amount, 2)

    ok, payment_url_or_err, order_id = await asyncio.to_thread(create_zapupi_order, deficit, f"{label} | {user_id}")
    if not ok:
        if payment_url_or_err == "ZAPUPI_KEY_NOT_SET":
            return False, "UPI_NOT_SET"
        logging.error(f"raise_payment_qr failed for user {user_id} (₹{deficit}, purpose={purpose}): {payment_url_or_err}")
        try:
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=(
                    f"⚠️ ZapUPI Order Creation Failed\n"
                    f"User: {user_id}\n"
                    f"Amount: ₹{deficit:.2f}\n"
                    f"Purpose: {purpose}\n\n"
                    f"Reason:\n{str(payment_url_or_err)[:500]}"
                )
            )
        except Exception:
            pass
        return False, payment_url_or_err

    payment_url = payment_url_or_err

    conn = db()
    conn.execute(
        "INSERT OR REPLACE INTO payments (order_id, user_id, amount, status, plan_id, purpose, provider, date) VALUES (?, ?, ?, 'PENDING', ?, ?, 'zapupi', datetime('now'))",
        (order_id, user_id, deficit, plan_id, purpose)
    )
    conn.commit()
    conn.close()

    purpose_title_map = {
        'plan': "🛒 Product Purchase",
        'reseller': "🌟 Reseller Upgrade",
        'balance': "💰 Wallet Deposit",
    }
    purpose_title = purpose_title_map.get(purpose, "💳 Payment")

    caption = (
        f"{emj(EMOJI_ADD_BALANCE)} *COMPLETE YOUR PAYMENT* {emj(EMOJI_ADD_BALANCE)}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🏷️ *Type:* {md_escape(purpose_title)}\n"
        f"📦 *For:* {md_escape(label)}\n"
        f"{emj('6145426283007320286')} *Amount To Pay:* ₹{fmt_amount(deficit)}\n\n"
        f"{emj('6199422882435571592')} *Pay Within:* 5 Minutes ⏳\n"
        f"{emj('6311891639077967303')} *Amount Credited Automatically* ⚡\n\n"
        f"👇 Tap *Pay Now* below and complete the UPI payment\\.\n"
        f"✅ Your balance will be added here instantly once payment is confirmed\\!"
    )
    keyboard = [
        [colored_url_button("Pay Now", payment_url, style="success", icon_custom_emoji_id="6145426283007320286")],
        [colored_button("Cancel / Back", "cancel_qr", style="danger", icon_custom_emoji_id=BACK_ICON)]
    ]

    try:
        msg = await ssend(context.bot, user_id, caption, InlineKeyboardMarkup(keyboard), "MarkdownV2")
    except Exception as e:
        logging.error(f"Failed to send ZapUPI payment link to {user_id} (order {order_id}): {e}")
        try:
            conn2 = db()
            conn2.execute("UPDATE payments SET status = 'EXPIRED' WHERE order_id = ?", (order_id,))
            conn2.commit()
            conn2.close()
        except Exception:
            pass
        return False, "QR_SEND_FAILED"

    track_task(poll_payment_status(context, order_id, user_id, msg.message_id, purpose, plan_id, deficit))
    return True, order_id


# ============================================================
# START & MAIN MENU
# ============================================================
def build_main_menu_keyboard(u_lang):
    keyboard = [
        [colored_button(get_txt("btn_shop", u_lang), "user_shop", style="success", icon_custom_emoji_id="6145292889913039900")],
        [colored_button(get_txt("btn_profile", u_lang), "user_profile", style="primary", icon_custom_emoji_id=EMOJI_PROFILE), colored_button(get_txt("btn_add_bal", u_lang), "user_add_balance", style="success", icon_custom_emoji_id=EMOJI_ADD_BALANCE)],
        [colored_button(get_txt("btn_history", u_lang), "user_history", style="primary", icon_custom_emoji_id="5282843764451195532"), colored_button(get_txt("btn_refer", u_lang), "user_refer_earn", style="success", icon_custom_emoji_id=EMOJI_REFER)],
    ]
    if is_reseller_enabled():
        keyboard.append([colored_button(get_txt("btn_upgrade", u_lang), "user_upgrade_reseller", style="success", icon_custom_emoji_id=EMOJI_UPGRADE_RESELLER)])
    keyboard += [
        [colored_button(get_txt("btn_leaderboard", u_lang), "user_leaderboard", style="primary", icon_custom_emoji_id=EMOJI_LEADERBOARD_BTN)],
        [colored_button(get_txt("btn_spin", u_lang), "user_lucky_spin", style="primary", icon_custom_emoji_id=EMOJI_LUCKY_SPIN), colored_button(get_txt("btn_how", u_lang), "user_how_to_use", style="danger", icon_custom_emoji_id=EMOJI_HOW_TO)],
        [colored_button(get_txt("btn_support", u_lang), "user_support", style="danger", icon_custom_emoji_id=EMOJI_SUPPORT)]
    ]
    return keyboard


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_info = update.effective_user
    if is_bot_maintenance() and user_info.id != ADMIN_ID:
        await send_maintenance_notice(update)
        return

    referrer_id = 0
    product_deep_link = None
    if context.args and len(context.args) > 0:
        arg = context.args[0]
        if arg.startswith("ref_"):
            try:
                referrer_id = int(arg.replace("ref_", ""))
            except ValueError:
                pass
        elif arg.startswith("prod_"):
            product_deep_link = arg.replace("prod_", "")

    context.user_data['state'] = None
    user_data = get_user(user_info.id, user_info.username, user_info.full_name, referrer_id)
    u_lang = user_data[9] or 'en'

    if product_deep_link:
        await show_product_plans_menu(update, context, product_deep_link, user_info.id)
        return

    keyboard = build_main_menu_keyboard(u_lang)
    welcome_msg = build_premium_welcome_text(user_info.first_name or "User", user_data[3], user_data[0])
    markup = InlineKeyboardMarkup(keyboard)

    if update.message:
        await sreply(update.message, welcome_msg, markup, "MarkdownV2")
    else:
        try:
            await sedit(update.callback_query, welcome_msg, markup, "MarkdownV2")
        except Exception:
            await ssend(context.bot, user_info.id, welcome_msg, markup, "MarkdownV2")


async def cancel_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['state'] = None
    context.user_data.pop('restore_data', None)
    await update.message.reply_text("✅ Cancelled. /start ya /admin use karo.")


async def user_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    user_id = query.from_user.id

    if is_bot_maintenance() and user_id != ADMIN_ID:
        await send_maintenance_notice(update)
        return

    user = get_user(user_id, query.from_user.username, query.from_user.full_name)
    u_lang = user[9] or 'en'
    back_btn_txt = get_txt("btn_back", u_lang)
    back_kb = user_back_kb(back_btn_txt)

    if data == "main_menu":
        await ans(query)
        context.user_data['state'] = None
        await start(update, context)

    elif data == "cancel_qr":
        await ans(query)
        context.user_data['state'] = None
        try:
            await query.message.delete()
        except Exception:
            pass
        await start(update, context)

    elif data == "user_leaderboard":
        await ans(query)
        try:
            rows = await asyncio.to_thread(get_top_buyers, LEADERBOARD_LIMIT)
        except Exception as e:
            logging.error(f"Leaderboard query failed: {e}")
            rows = []
        text = build_leaderboard_text(rows)
        keyboard = [
            [colored_button("Refresh Leaderboard", "user_leaderboard", style="primary", icon_custom_emoji_id=EMOJI_LB_REFRESH)],
            [colored_button(back_btn_txt, "main_menu", style="danger", icon_custom_emoji_id=BACK_ICON)]
        ]
        await sedit(query, text, InlineKeyboardMarkup(keyboard), "MarkdownV2")

    elif data == "user_profile":
        await ans(query)
        name = md_escape(user[2] if user[2] else "N/A")
        uname = f"@{md_escape(user[1])}" if user[1] else "N/A"
        uid = user[0]
        bal = user[3]
        acc_type = "🌟 Reseller" if user[4] else "👤 User"

        conn = db()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*), COALESCE(SUM(price), 0) FROM history WHERE user_id = ?", (uid,))
        row = cursor.fetchone()
        conn.close()
        orders = (row[0] if row and row[0] is not None else 0)
        spend = (row[1] if row and row[1] is not None else 0.0)

        text = (
            f"{emj(EMOJI_PROFILE)} *MY PROFILE* {emj(EMOJI_PROFILE)}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{emj(EMOJI_PROFILE_L1)} *Name:* {name}\n"
            f"{emj(EMOJI_PROFILE_L2)} *Username:* {uname}\n"
            f"{emj(EMOJI_PROFILE_L3)} *User ID:* `{uid}`\n"
            f"{emj(EMOJI_PROFILE_L4)} *Account Type:* {md_escape(acc_type)}\n"
            f"{emj(EMOJI_PROFILE_L5)} *Balance:* ₹{fmt_amount(bal)}\n"
            f"{emj('6145292889913039900')} *Total Orders:* {orders}\n"
            f"{emj('5233326571099534068')} *Total Spend:* ₹{fmt_amount(spend)}\n"
            f"━━━━━━━━━━━━━━━━━━━━"
        )
        keyboard = [
            [colored_button(get_txt("btn_add_bal", u_lang), "user_add_balance", style="success", icon_custom_emoji_id=EMOJI_ADD_BALANCE)],
            [colored_button(back_btn_txt, "main_menu", style="danger", icon_custom_emoji_id=BACK_ICON)]
        ]
        await sedit(query, text, InlineKeyboardMarkup(keyboard), "MarkdownV2")

    elif data == "user_add_balance":
        await ans(query)
        context.user_data['state'] = 'WAIT_DEPOSIT_AMT'
        text = (
            f"{emj(EMOJI_ADD_BALANCE)} *Auto UPI Payment Deposit* {emj(EMOJI_ADD_BALANCE)}\n\n"
            f"Enter the amount you want to deposit to your wallet \\(minimum ₹{fmt_amount(MIN_DEPOSIT)}\\):\n"
            f"_\\(Example: `50` or `100`\\)_"
        )
        await sedit(query, text, back_kb, "MarkdownV2")

    elif data == "user_how_to_use":
        await ans(query)
        vid_url = get_setting('how_to_use_video', '')
        text = (
            f"{emj(EMOJI_HOW_TO)} *HOW TO PURCHASE KEYS* {emj(EMOJI_HOW_TO)}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"1\ufe0f\u20e3 Tap *Add Balance* and deposit via UPI\\.\n"
            f"2\ufe0f\u20e3 Click *Shop Now* and select a product\\.\n"
            f"3\ufe0f\u20e3 Pick your desired plan duration and confirm\\.\n"
            f"4\ufe0f\u20e3 Key is delivered instantly\\! \u26a1"
        )
        keyboard = []
        if vid_url and vid_url.startswith("http"):
            keyboard.append([colored_url_button("Watch Video Tutorial", vid_url, style="primary", icon_custom_emoji_id=EMOJI_HOW_TO)])
        keyboard.append([colored_button(back_btn_txt, "main_menu", style="danger", icon_custom_emoji_id=BACK_ICON)])
        await sedit(query, text, InlineKeyboardMarkup(keyboard), "MarkdownV2")

    elif data == "user_refer_earn":
        await ans(query)
        bot_username = context.bot.username
        ref_link = f"https://t.me/{bot_username}?start=ref_{user_id}"

        conn = db()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users WHERE referred_by = ?", (user_id,))
        total_refs = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM users WHERE referred_by = ? AND has_purchased = 1", (user_id,))
        successful_refs = cursor.fetchone()[0]
        conn.close()

        earned = successful_refs * 1.0

        text = (
            f"{emj(EMOJI_REFER)} *REFER & EARN* {emj(EMOJI_REFER)}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"Earn *₹{fmt_amount(1.0)}* for every friend who makes their first purchase\\!\n\n"
            f"👥 *Referred:* {total_refs}   ✅ *Purchased:* {successful_refs}\n"
            f"💰 *Earned:* ₹{fmt_amount(earned)}\n\n"
            f"🔗 *Your Link:*\n`{code_escape(ref_link)}`"
        )

        share_msg = f"🛒 Buy top-quality digital keys instantly!\nJoin using my referral link to get started:\n{ref_link}"
        share_url = f"https://t.me/share/url?url={requests.utils.quote(ref_link)}&text={requests.utils.quote(share_msg)}"

        keyboard = [
            [colored_url_button("Share Link", share_url, style="primary", icon_custom_emoji_id=EMOJI_REFER)],
            [colored_button(back_btn_txt, "main_menu", style="danger", icon_custom_emoji_id=BACK_ICON)]
        ]
        await sedit(query, text, InlineKeyboardMarkup(keyboard), "MarkdownV2")

    elif data == "user_lucky_spin":
        await ans(query)
        current_time = int(time.time())
        last_spin = user[8]
        cooldown = 86400
        balance = user[3]

        intro_text = (
            f"{emj(EMOJI_LUCKY_SPIN)} *LUCKY SPIN* {emj(EMOJI_LUCKY_SPIN)}\n\n"
            f"Win up to *₹{fmt_amount(1.0)}* free — 1 spin per 24h\\!\n"
            f"💰 Balance: ₹{fmt_amount(balance)}"
        )

        if current_time - last_spin < cooldown:
            remaining = cooldown - (current_time - last_spin)
            hours = remaining // 3600
            minutes = (remaining % 3600) // 60
            seconds = remaining % 60
            intro_text += f"\n\n⏳ Next spin in: {hours:02d}h {minutes:02d}m {seconds:02d}s"
            keyboard = [[colored_button(back_btn_txt, "main_menu", style="danger", icon_custom_emoji_id=BACK_ICON)]]
        else:
            keyboard = [
                [colored_button("Spin Now", "user_spin_now", style="success", icon_custom_emoji_id=EMOJI_SPIN_NOW)],
                [colored_button(back_btn_txt, "main_menu", style="danger", icon_custom_emoji_id=BACK_ICON)]
            ]

        await sedit(query, intro_text, InlineKeyboardMarkup(keyboard), "MarkdownV2")

    elif data == "user_spin_now":
        if user_id in SPINNING_USERS:
            await ans(query, "⏳ Spin chal raha hai...", True)
            return
        SPINNING_USERS.add(user_id)
        try:
            current_time = int(time.time())
            cooldown = 86400

            # Atomic claim - double spin nahi ho sakta
            conn = db()
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE users SET last_spin_time = ? WHERE user_id = ? AND (last_spin_time IS NULL OR last_spin_time <= ?)",
                (current_time, user_id, current_time - cooldown)
            )
            claimed = cursor.rowcount > 0
            conn.commit()
            conn.close()

            if not claimed:
                last_spin = user[8]
                remaining = max(0, cooldown - (current_time - last_spin))
                hours = remaining // 3600
                minutes = (remaining % 3600) // 60
                seconds = remaining % 60
                await ans(query, f"⏳ Next spin in {hours:02d}h {minutes:02d}m {seconds:02d}s...", True)
                return

            await ans(query)

            spin_emojis = ["🍒", "🍋", "🍇", "🍉", "⭐", "💎", "7️⃣", "🔔", "🍀"]
            try:
                for _ in range(6):
                    frame = "  ".join(random.choice(spin_emojis) for _ in range(3))
                    await sedit(
                        query,
                        f"🎰 *SPINNING\\.\\.\\.* 🎰\n━━━━━━━━━━━━━━━━━━━━\n\n"
                        f"┃  {frame}  ┃\n\n"
                        f"🍀 Good luck\\!",
                        None, "MarkdownV2"
                    )
                    await asyncio.sleep(0.6)
            except Exception:
                pass

            if random.random() < 0.03:
                reward = round(random.uniform(0.10, 1.00), 2)
                update_balance(user_id, reward)
                spin_result = (
                    f"🎰 *LUCKY SPIN RESULT* 🎰\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"┃  💰  💰  💰  ┃\n\n"
                    f"🎉 *CONGRATULATIONS\\!* 🎉\n"
                    f"You won *₹{fmt_amount(reward)}*\\!\n\n"
                    f"⏳ Next spin available in 24h 00m 00s\\.\\.\\."
                )
            else:
                spin_result = (
                    f"🎰 *LUCKY SPIN RESULT* 🎰\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"┃  😅  😅  😅  ┃\n\n"
                    f"😢 *Better luck next time\\!*\n\n"
                    f"⏳ Next spin available in 24h 00m 00s\\.\\.\\."
                )

            await sedit(query, spin_result, back_kb, "MarkdownV2")
        finally:
            SPINNING_USERS.discard(user_id)

    elif data == "user_support":
        await ans(query)
        context.user_data['state'] = None
        s_uname = get_support_username().replace("@", "")
        text = (
            f"{emj(EMOJI_SUPPORT_L1)} *SUPPORT* {emj(EMOJI_SUPPORT_L1)}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{emj(EMOJI_SUPPORT_L2)} Need help with a payment or order? Tap *Contact Admin* below\\.\n\n"
            f"{emj(EMOJI_SUPPORT_L3)} Or open a ticket — send text, screenshot 📸 or voice note 🎙️ and admin will reply here\\."
        )
        keyboard = [
            [colored_url_button("Contact Admin", f"https://t.me/{s_uname}", style="primary", icon_custom_emoji_id=EMOJI_CONTACT_ADMIN_BTN)],
            [colored_button("Open Ticket", "user_open_ticket", style="success", icon_custom_emoji_id=EMOJI_SUPPORT)],
            [colored_button(back_btn_txt, "main_menu", style="danger", icon_custom_emoji_id=BACK_ICON)]
        ]
        await sedit(query, text, InlineKeyboardMarkup(keyboard), "MarkdownV2")

    elif data == "user_open_ticket":
        await ans(query)
        ticket_id = generate_ticket_id()
        conn = db()
        conn.execute("INSERT INTO tickets (ticket_id, user_id, status) VALUES (?, ?, 'open')", (ticket_id, user_id))
        conn.commit()
        conn.close()

        context.user_data['state'] = 'WAIT_TICKET_MSG'
        context.user_data['open_ticket_id'] = ticket_id

        text = (
            f"🎫 *TICKET CREATED* — `{code_escape(ticket_id)}`\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📝 Send your message now — text ✍️, a screenshot 📸 or a voice note 🎙️ — describing your issue\\.\n\n"
            f"⏳ Our admin will receive it instantly and reply to you right here\\."
        )
        await sedit(query, text, back_kb, "MarkdownV2")

    elif data == "user_upgrade_reseller":
        if not is_reseller_enabled():
            await ans(query, "❌ Reseller upgrades are currently unavailable.", True)
            return
        await ans(query)
        try:
            price = get_reseller_price()
            text = (
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"{emj(EMOJI_RESELLER_L1)} *UPGRADE TO RESELLER*\n"
                f"━━━━━━━━━━━━━━━━━━━━\n\n"
                f"{emj(EMOJI_RESELLER_L2)} *Benefits:*\n\n"
                f"• Special reseller prices on ALL products\n"
                f"• Priority support\n"
                f"• Balance tracking dashboard\n\n"
                f"{emj(EMOJI_RESELLER_L3)} *One\\-time Investment:* ₹{fmt_amount(price)}\n\n"
                f"{emj(EMOJI_RESELLER_L4)} Ready to upgrade? ⬇️"
            )
            keyboard = [
                [colored_button("Upgrade Now", "user_reseller_upgrade_now", style="success", icon_custom_emoji_id=EMOJI_UPGRADE_RESELLER)],
                [colored_button(back_btn_txt, "main_menu", style="danger", icon_custom_emoji_id=BACK_ICON)]
            ]
            await sedit(query, text, InlineKeyboardMarkup(keyboard), "MarkdownV2")
        except Exception as e:
            logging.error(f"Failed to show reseller upgrade screen for user {user_id}: {e}")
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text="⚠️ Something went wrong while loading the Reseller Upgrade screen. Please try again or contact Support.",
                    reply_markup=back_kb
                )
            except Exception:
                pass

    elif data == "user_reseller_upgrade_now":
        if not is_reseller_enabled():
            await ans(query, "❌ Reseller upgrades are currently unavailable.", True)
            return
        if user[4]:
            await ans(query, "✅ You're already a Reseller!", True)
            return
        if user_id in PROCESSING_PURCHASES:
            await ans(query, "⏳ Your upgrade is already being processed...", True)
            return
        PROCESSING_PURCHASES.add(user_id)
        try:
            await ans(query)
            price = get_reseller_price()
            balance = user[3]
            if balance >= price:
                success, text = await finalize_reseller_upgrade(context, user_id)
                try:
                    await query.message.delete()
                except Exception:
                    pass
                if success:
                    await deliver_purchase_result(context, user_id, text, back_btn_txt, parse_mode="Markdown")
                else:
                    await ssend(context.bot, user_id, text, back_kb, "Markdown")
            else:
                deficit = round(price - balance, 2)
                insufficient_text = (
                    f"⚠️ *INSUFFICIENT BALANCE* ⚠️\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"💎 *Upgrade:* Reseller Plan\n"
                    f"💵 *Price:* ₹{fmt_amount(price)}\n"
                    f"💰 *Your Balance:* ₹{fmt_amount(balance)}\n"
                    f"🧾 *Need To Buy:* ₹{fmt_amount(deficit)}\n\n"
                    f"👉 Please Add Balance from below and try again\\."
                )
                add_bal_kb = InlineKeyboardMarkup([
                    [colored_button(get_txt("btn_add_bal", u_lang), "user_add_balance", style="success", icon_custom_emoji_id=EMOJI_ADD_BALANCE)],
                    [colored_button(back_btn_txt, "main_menu", style="danger", icon_custom_emoji_id=BACK_ICON)]
                ])
                await sedit(query, insufficient_text, add_bal_kb, "MarkdownV2")
        except Exception as e:
            logging.error(f"Reseller upgrade flow failed for user {user_id}: {e}")
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text="⚠️ Something went wrong while processing your reseller upgrade. Please try again or contact Support.",
                    reply_markup=back_kb
                )
            except Exception:
                pass
        finally:
            PROCESSING_PURCHASES.discard(user_id)

    elif data == "user_history":
        await ans(query)
        conn = db()
        cursor = conn.cursor()
        cursor.execute("SELECT item_name, key_value, price, date FROM history WHERE user_id = ? ORDER BY id DESC LIMIT 8", (user_id,))
        purchase_rows = cursor.fetchall()
        cursor.execute("SELECT amount, provider, date FROM payments WHERE user_id = ? AND status = 'SUCCESS' ORDER BY (date IS NULL), date DESC LIMIT 8", (user_id,))
        deposit_rows = cursor.fetchall()
        conn.close()

        entries = []
        for r in purchase_rows:
            entries.append({"type": "purchase", "date": r[3], "item": r[0], "key": r[1], "price": r[2]})
        for r in deposit_rows:
            entries.append({"type": "deposit", "date": r[2], "amount": r[0], "provider": r[1]})

        entries.sort(key=lambda e: str(e["date"] or ""), reverse=True)
        entries = entries[:10]

        if not entries:
            body = "No history found"
        else:
            body = ""
            for e in entries:
                when = md_escape(to_ist_str(e["date"]))
                if e["type"] == "purchase":
                    body += (
                        f"🛒 *Purchase*\n"
                        f"📦 *Item:* {md_escape(e['item'])}\n"
                        f"🔑 *Key:* `{code_escape(e['key'])}`\n"
                        f"💵 *Amount:* ₹{fmt_amount(e['price'])}\n"
                        f"🗓️ *Date:* {when} \\(IST\\)\n"
                        f"─────────────────────\n"
                    )
                else:
                    method = f"UPI \\({md_escape((e['provider'] or 'zapupi').upper())}\\)" if e.get('provider') else "UPI"
                    body += (
                        f"💰 *Deposit*\n"
                        f"💵 *Amount:* ₹{fmt_amount(e['amount'])}\n"
                        f"💳 *Method:* {method}\n"
                        f"🗓️ *Date:* {when} \\(IST\\)\n"
                        f"─────────────────────\n"
                    )

        header = (
            f"{emj(EMOJI_HISTORY_HEADER)} *Your Last Activity* {emj(EMOJI_HISTORY_HEADER)}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
        )
        text = header + body
        if len(text) > 3900:
            text = text[:3800].rsplit("\n", 1)[0] + "\n_\\.\\.\\. list truncated_"

        await sedit(query, text, back_kb, "MarkdownV2")

    elif data == "user_shop":
        await ans(query)
        conn = db()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, button_style FROM categories ORDER BY sort_order, id")
        categories = cursor.fetchall()
        cursor.execute("SELECT COUNT(*) FROM products WHERE category IS NULL OR category = ''")
        uncategorized_count = cursor.fetchone()[0] or 0
        conn.close()

        keyboard = []
        if not categories and uncategorized_count == 0:
            text = (
                f"{emj(EMOJI_SHOP_BOT)} *SURAJ SHOP BOT* {emj(EMOJI_SHOP_BOT)}\n"
                f"━━━━━━━━━━━━━━━━━━━━\n\n"
                f"No products available yet\\. Please check back later\\."
            )
        else:
            for c in categories:
                cat_style = norm_style(c[2], "success")
                keyboard.append([colored_button(f"{c[1]}", f"shop_cat_{c[0]}", style=cat_style, icon_custom_emoji_id=EMOJI_CATEGORY)])
            if uncategorized_count > 0:
                keyboard.append([colored_button("Other Products", "shop_cat_0", style="success", icon_custom_emoji_id=EMOJI_CATEGORY)])
            text = (
                f"{emj(EMOJI_SHOP_BOT)} *ALL STORE SHOP BOT* {emj(EMOJI_SHOP_BOT)}\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"{emj(EMOJI_DEVICE_SELECT)} *Select Your Device* {emj(EMOJI_DEVICE_SELECT)}"
            )

        keyboard.append([colored_button("Back", "main_menu", style="danger", icon_custom_emoji_id=BACK_ICON)])
        await sedit(query, text, InlineKeyboardMarkup(keyboard), "MarkdownV2")

    elif data.startswith("shop_cat_"):
        await ans(query)
        cat_id = data.split("_", 2)[2]
        conn = db()
        cursor = conn.cursor()
        if cat_id == "0":
            cursor.execute("SELECT pid, name, is_maintenance, button_style, emoji_id FROM products WHERE category IS NULL OR category = '' ORDER BY name")
            cat_name = "Other Products"
        else:
            cursor.execute("SELECT name FROM categories WHERE id = ?", (cat_id,))
            crow = cursor.fetchone()
            cat_name = crow[0] if crow else "Category"
            cursor.execute("SELECT pid, name, is_maintenance, button_style, emoji_id FROM products WHERE category = ? ORDER BY name", (cat_name,))
        products = cursor.fetchall()
        conn.close()

        keyboard = []
        if not products:
            text = (
                f"{emj(EMOJI_CATEGORY_HEADER)} *{md_escape(cat_name)}*\n"
                f"━━━━━━━━━━━━━━━━━━━━\n\n"
                f"_No products available in this category yet\\._"
            )
        else:
            for p in products:
                pid, pname = p[0], p[1]
                in_maint = p[2]
                prod_style = "danger" if in_maint else norm_style(p[3], "primary")
                custom_emoji = (p[4] or "").strip() if len(p) > 4 else ""
                # Maintenance icon sabse upar; warna admin ka set kiya hua emoji; warna default
                prod_icon = EMOJI_MAINTENANCE_PRODUCT if in_maint else (custom_emoji or EMOJI_PRODUCT)
                keyboard.append([colored_button(f"{pname}", f"shop_prod_{pid}", style=prod_style, icon_custom_emoji_id=prod_icon)])

            text = (
                f"{emj(EMOJI_CATEGORY_HEADER)} *{md_escape(cat_name)}*\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"{emj(EMOJI_CAT_LINE_1)} Select Your Product\n"
                f"{emj(EMOJI_CAT_LINE_2)} Browse The List Below\n"
                f"{emj(EMOJI_CAT_LINE_3)} Tap Any Item To View Plans"
            )

        keyboard.append([colored_button("Back", "user_shop", style="danger", icon_custom_emoji_id=BACK_ICON)])
        await sedit(query, text, InlineKeyboardMarkup(keyboard), "MarkdownV2")

    elif data.startswith("shop_prod_"):
        await ans(query)
        pid = data.split("_", 2)[2]
        await show_product_plans_menu(update, context, pid, user_id)

    elif data.startswith("buy_final_"):
        plan_id = data.split("_", 2)[2]
        try:
            conn = db()
            cursor = conn.cursor()
            cursor.execute("SELECT product_pid, duration, price, reseller_price FROM plans WHERE id = ?", (plan_id,))
            plan = cursor.fetchone()

            if not plan:
                conn.close()
                await ans(query, "❌ Plan not found!", True)
                return

            cursor.execute("SELECT name, is_maintenance FROM products WHERE pid = ?", (plan[0],))
            prod_row = cursor.fetchone()
            prod_name = prod_row[0] if prod_row else "Unknown Product"
            in_maint = prod_row and prod_row[1]

            if in_maint:
                conn.close()
                await ans(query)
                text = f"🛠 *{md_escape(prod_name)}*\n\nThis product is in maintenance now\\. Please check back later\\."
                await sedit(query, text, back_kb, "MarkdownV2")
                return

            cursor.execute("SELECT balance, is_reseller FROM users WHERE user_id = ?", (user_id,))
            b_row = cursor.fetchone()
            balance = b_row[0] if b_row and b_row[0] is not None else 0.0
            is_reseller = b_row[1] if b_row and b_row[1] is not None else 0
            conn.close()

            cost = get_effective_price(user_id, plan_id, plan[2], plan[3], is_reseller)
            await ans(query)

            if balance >= cost:
                after_bal = balance - cost
                confirm_text = (
                    f"{emj('6233058686885961086')} *CONFIRM YOUR PURCHASE* {emj('6233058686885961086')}\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"{emj('6233339470372938278')} *Product:* {md_escape(prod_name)}\n"
                    f"{emj('6233029979324554127')} *Duration:* {md_escape(plan[1])}\n"
                    f"{emj('6230781293362158919')} *Price:* ₹{fmt_amount(cost)}\n"
                    f"{emj('6230960110030561348')} *Current Balance:* ₹{fmt_amount(balance)}\n"
                    f"{emj('6195222374355311655')} *Balance After:* ₹{fmt_amount(after_bal)}\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"Tap *Confirm Purchase* to receive your key instantly\\."
                )
                confirm_keyboard = [
                    [colored_button("Confirm Purchase", f"confirm_buy_{plan_id}", style="success", icon_custom_emoji_id="6145334203203462531")],
                    [colored_button("Cancel", "main_menu", style="danger", icon_custom_emoji_id=BACK_ICON)]
                ]
                await sedit(query, confirm_text, InlineKeyboardMarkup(confirm_keyboard), "MarkdownV2")
            else:
                deficit = round(cost - balance, 2)
                insufficient_text = (
                    f"⚠️ *INSUFFICIENT BALANCE* ⚠️\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"📦 *Product:* {md_escape(prod_name)}\n"
                    f"⏱️ *Plan:* {md_escape(plan[1])}\n"
                    f"💵 *Price:* ₹{fmt_amount(cost)}\n"
                    f"💰 *Your Balance:* ₹{fmt_amount(balance)}\n"
                    f"🧾 *Need To Buy:* ₹{fmt_amount(deficit)}\n\n"
                    f"👉 Please Add Balance from below and try again\\."
                )
                await sedit(
                    query, insufficient_text,
                    InlineKeyboardMarkup([
                        [colored_button(get_txt("btn_add_bal", u_lang), "user_add_balance", style="success", icon_custom_emoji_id=EMOJI_ADD_BALANCE)],
                        [colored_button(back_btn_txt, "main_menu", style="danger", icon_custom_emoji_id=BACK_ICON)]
                    ]),
                    "MarkdownV2"
                )
        except Exception as e:
            logging.error(f"buy_final_ failed for user {user_id}, plan {plan_id}: {e}")
            try:
                await context.bot.send_message(chat_id=user_id, text="⚠️ Something went wrong. Please try again or send /start.")
            except Exception:
                pass

    elif data.startswith("confirm_buy_"):
        plan_id = data.split("_", 2)[2]

        if user_id in PROCESSING_PURCHASES:
            await ans(query, "⏳ Your purchase is already being processed, please wait...", True)
            return
        PROCESSING_PURCHASES.add(user_id)

        try:
            await ans(query)
            try:
                await query.message.delete()
            except Exception:
                pass

            conn = db()
            cursor = conn.cursor()
            cursor.execute("SELECT product_pid, duration, price, reseller_price FROM plans WHERE id = ?", (plan_id,))
            plan = cursor.fetchone()

            if not plan:
                conn.close()
                await ssend(context.bot, user_id, "❌ This plan no longer exists\\.", back_kb, "MarkdownV2")
                return

            cursor.execute("SELECT name, is_maintenance FROM products WHERE pid = ?", (plan[0],))
            prod_row = cursor.fetchone()
            prod_name = prod_row[0] if prod_row else "Unknown Product"
            in_maint = prod_row and prod_row[1]

            if in_maint:
                conn.close()
                text = f"🛠 *{md_escape(prod_name)}*\n\nThis product is in maintenance now\\. Please check back later\\."
                await ssend(context.bot, user_id, text, back_kb, "MarkdownV2")
                return

            cursor.execute("SELECT balance, is_reseller FROM users WHERE user_id = ?", (user_id,))
            b_row = cursor.fetchone()
            balance = b_row[0] if b_row and b_row[0] is not None else 0.0
            is_reseller = b_row[1] if b_row and b_row[1] is not None else 0
            conn.close()

            cost = get_effective_price(user_id, plan_id, plan[2], plan[3], is_reseller)

            if balance < cost:
                deficit = round(cost - balance, 2)
                await ssend(
                    context.bot, user_id,
                    (
                        f"⚠️ *INSUFFICIENT BALANCE* ⚠️\n\n"
                        f"📦 *Product:* {md_escape(prod_name)}\n"
                        f"⏱️ *Plan:* {md_escape(plan[1])}\n"
                        f"💵 *Price:* ₹{fmt_amount(cost)}\n"
                        f"💰 *Your Balance:* ₹{fmt_amount(balance)}\n"
                        f"🧾 *Need To Buy:* ₹{fmt_amount(deficit)}\n\n"
                        f"Please Add Balance and try again from *Shop Now*\\."
                    ),
                    InlineKeyboardMarkup([
                        [colored_button(get_txt("btn_add_bal", u_lang), "user_add_balance", style="success", icon_custom_emoji_id=EMOJI_ADD_BALANCE)],
                        [colored_button(back_btn_txt, "main_menu", style="danger", icon_custom_emoji_id=BACK_ICON)]
                    ]),
                    "MarkdownV2"
                )
                return

            success, text, group_link = await finalize_purchase(context, user_id, plan_id, purchase_type="Manual/Balance")
            await deliver_purchase_result(context, user_id, text, back_btn_txt, group_link, parse_mode="MarkdownV2")
        except Exception as e:
            logging.error(f"Purchase confirmation failed for user {user_id}, plan {plan_id}: {e}")
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text="⚠️ Something went wrong while completing your purchase. If your balance was deducted, please contact Support.",
                    reply_markup=back_kb
                )
            except Exception:
                pass
        finally:
            PROCESSING_PURCHASES.discard(user_id)

    else:
        await ans(query)


# ============================================================
# ADMIN PANEL
# ============================================================
ADMIN_PANEL_TEXT = "⚡ **Admin Control Panel** ⚡"


def get_admin_panel_markup():
    maint_on = is_bot_maintenance()
    maint_label = "🛠 Bot Maintenance: ON" if maint_on else "✅ Bot Maintenance: OFF"
    reseller_on = is_reseller_enabled()
    reseller_label = "🌟 Reseller Menu: ON" if reseller_on else "🚫 Reseller Menu: OFF"
    disc = get_global_discount()
    disc_label = f"🏷️ Discount: {fmt_pct(disc)}% ON" if disc > 0 else "🏷️ Discount: OFF"

    flat_buttons = [
        (maint_label, "admin_toggle_maintenance", "danger" if maint_on else "success"),
        (reseller_label, "admin_toggle_reseller_menu", "success" if reseller_on else "danger"),
        (disc_label, "admin_discount", "success" if disc > 0 else "primary"),
        ("😀 Set Emojis", "admin_set_emojis", "primary"),
        ("💾 Backup", "admin_backup", "success"),
        ("♻️ Restore", "admin_restore", "danger"),
        ("📊 Bot Stats", "admin_bot_stats", "primary"),
        ("➕ Add Product", "admin_add_prod", "success"),
        ("🗑️ Remove Product", "admin_rem_prod", "danger"),
        ("📂 Add Category", "admin_add_category", "success"),
        ("🗑️ Remove Category", "admin_rem_category", "danger"),
        ("↕️ Reorder Categories", "admin_reorder_categories", "primary"),
        ("🔀 Assign Category", "admin_assign_category", "primary"),
        ("🎨 Set Button Style", "admin_style_menu", "primary"),
        ("➕ Add Plan", "admin_add_plan", "success"),
        ("🗑️ Remove Plan", "admin_rem_plan", "danger"),
        ("🔑 Add Keys", "admin_add_keys", "success"),
        ("🗑️ Remove Keys", "admin_rem_keys", "danger"),
        ("🔍 Check Keys Stock", "admin_check_keys", "primary"),
        ("🔗 Product Deep Links", "admin_prod_links", "primary"),
        ("🛠 Maintenance Mode", "admin_maintenance_prod", "primary"),
        ("🔗 Set Group Link", "admin_set_group_link", "primary"),
        ("🎥 Set Product Video", "admin_set_prod_video", "primary"),
        ("💵 Set Custom Price", "admin_set_custom_price", "primary"),
        ("🗑️ Remove Custom Price", "admin_rem_custom_price", "danger"),
        ("➕ Add Reseller", "admin_add_reseller", "success"),
        ("➖ Remove Reseller", "admin_rem_reseller", "danger"),
        ("👥 My Resellers", "admin_my_resellers", "primary"),
        ("⚙️ Set Plan Reseller Price", "admin_set_reseller_price", "primary"),
        ("💎 Set Upgrade Price", "admin_set_upgrade_price", "primary"),
        ("💠 Payment Settings", "admin_set_payment", "primary"),
        ("🔑 Store API Key", "admin_set_store_api", "primary"),
        ("☎️ Set Support Link", "admin_set_support_uname", "primary"),
        ("💲 Change Product Price", "admin_change_price", "primary"),
        ("✏️ Rename Product", "admin_change_name", "primary"),
        ("🆔 Change PID", "admin_change_pid", "primary"),
        ("🎬 Set HowToVideo", "admin_set_how_video", "primary"),
        ("📢 Broadcast", "admin_broadcast", "primary"),
        ("➕ Add Balance", "admin_add_bal", "success"),
        ("➖ Remove Balance", "admin_rem_bal", "danger"),
        ("🔍 Check Balance", "admin_check_bal", "primary"),
    ]
    keyboard = zigzag_rows(flat_buttons)
    keyboard.append([colored_button("Back To Main Menu", "main_menu", style="danger", icon_custom_emoji_id=BACK_ICON)])
    return keyboard


async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    context.user_data['state'] = None
    await sreply(update.message, ADMIN_PANEL_TEXT, InlineKeyboardMarkup(get_admin_panel_markup()))


async def reopen_admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE, confirm_msg: str = None):
    if confirm_msg:
        await sreply(update.message, confirm_msg)
    await sreply(update.message, ADMIN_PANEL_TEXT, InlineKeyboardMarkup(get_admin_panel_markup()))


async def refresh_admin_panel(context: ContextTypes.DEFAULT_TYPE, query, message_text=ADMIN_PANEL_TEXT):
    try:
        await sedit(query, message_text, InlineKeyboardMarkup(get_admin_panel_markup()))
    except Exception as e:
        logging.error(f"Failed to refresh admin panel: {e}")


def back_only(cb="admin_back_panel"):
    return InlineKeyboardMarkup([[colored_back_button(cb)]])


def product_picker_keyboard(cursor, cb_prefix, back_cb="admin_back_panel", style="primary", only_with_plans=True, label_prefix="📦"):
    """Product list buttons (har product ka ek button). 'Reply markup is too long' se bachne ke liye
    plans ki lambi list ek saath nahi dikhate - pehle product, phir uske plans."""
    if only_with_plans:
        cursor.execute(
            "SELECT p.pid, p.name FROM products p WHERE EXISTS (SELECT 1 FROM plans pl WHERE pl.product_pid = p.pid) ORDER BY p.name"
        )
    else:
        cursor.execute("SELECT pid, name FROM products ORDER BY name")
    prods = cursor.fetchall()
    keyboard = [[colored_button(f"{label_prefix} {p[1]}", f"{cb_prefix}{p[0]}", style=style)] for p in prods[:90]]
    keyboard.append([colored_back_button(back_cb)])
    return prods, keyboard


DISCOUNT_PRESETS = [5, 6, 8, 10, 20, 50]


def build_discount_menu():
    cur = get_global_discount()
    if cur > 0:
        status = f"✅ ACTIVE — **{fmt_pct(cur)}% OFF**"
    else:
        status = "❌ OFF (no discount)"
    text = (
        "🏷️ **GLOBAL DISCOUNT** 🏷️\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Current: {status}\n\n"
        "Jo % select karoge wo **sabhi products / plans** par **sabhi users** ko milega "
        "(normal + reseller price dono par).\n"
        "_Admin ke set kiye Custom Price par discount nahi lagta._\n\n"
        "👇 Select discount:"
    )
    row1 = [
        colored_button(f"{p}%", f"admin_disc_set_{p}", style="success" if abs(cur - p) < 1e-9 else "primary")
        for p in DISCOUNT_PRESETS[:3]
    ]
    row2 = [
        colored_button(f"{p}%", f"admin_disc_set_{p}", style="success" if abs(cur - p) < 1e-9 else "primary")
        for p in DISCOUNT_PRESETS[3:]
    ]
    keyboard = [
        row1,
        row2,
        [colored_button("Custom %", "admin_disc_custom", style="primary")],
        [colored_button("Remove Discount (0%)", "admin_disc_off", style="danger")],
        [colored_back_button("admin_back_panel")],
    ]
    return text, InlineKeyboardMarkup(keyboard)


async def _admin_dispatch(update, context, query, conn):
    data = query.data
    cursor = conn.cursor()

    if data == "admin_back_panel":
        context.user_data['state'] = None
        await refresh_admin_panel(context, query)

    elif data == "admin_toggle_maintenance":
        new_state = not is_bot_maintenance()
        set_bot_maintenance(new_state)
        await ans(query, "🛠 Maintenance ENABLED" if new_state else "✅ Bot Maintenance DISABLED — the bot is live for everyone again!", True)
        await refresh_admin_panel(context, query)

    elif data == "admin_toggle_reseller_menu":
        new_state = not is_reseller_enabled()
        set_reseller_enabled(new_state)
        await ans(query, f"🌟 Reseller Menu {'ENABLED' if new_state else 'DISABLED'}!", True)
        await refresh_admin_panel(context, query)

    # ---------------- GLOBAL DISCOUNT ----------------
    elif data == "admin_discount" or data.startswith("admin_disc_set_") or data == "admin_disc_off":
        context.user_data['state'] = None
        if data.startswith("admin_disc_set_"):
            try:
                v = float(data.split("admin_disc_set_", 1)[1])
            except ValueError:
                v = None
            if v is not None and 0 < v <= MAX_DISCOUNT:
                set_global_discount(v)
                await ans(query, f"✅ {fmt_pct(v)}% discount ON for all products!", True)
        elif data == "admin_disc_off":
            set_global_discount(0)
            await ans(query, "❌ Discount removed.", True)
        text, markup = build_discount_menu()
        await sedit(query, text, markup)

    elif data == "admin_disc_custom":
        context.user_data['state'] = 'WAIT_DISCOUNT_CUSTOM'
        await sedit(
            query,
            "✏️ **CUSTOM DISCOUNT**\n\n"
            f"➡️ Discount % bhejo (1 se {fmt_pct(MAX_DISCOUNT)} ke beech):\n"
            "*(Example: `15` ya `12.5`)*\n\n"
            "Jitna doge utna % sabhi products pe sabko milega.\n\n/cancel to abort",
            back_only("admin_discount")
        )

    # ---------------- SET EMOJIS ----------------
    elif data == "admin_set_emojis":
        context.user_data['state'] = None
        cursor.execute("SELECT pid, name, emoji_id FROM products ORDER BY name")
        prods = cursor.fetchall()
        if not prods:
            await sedit(query, "❌ Pehle koi product add karo.", back_only())
            return
        keyboard = []
        for pid, pname, eid in prods[:90]:
            label = f"{pname} — Emoji Set" if eid else f"{pname} — Default"
            keyboard.append([colored_button(label, f"emojiprod_{pid}", style="success" if eid else "primary")])
        keyboard.append([colored_back_button("admin_back_panel")])
        await sedit(
            query,
            "😀 **SET PRODUCT EMOJIS** 😀\n\n"
            "Product select karo — uske baad **Custom Emoji ID** bhejo.\n"
            "Wo emoji shop me us product ke button ke aage dikhega.\n\n"
            "👇 Select product:",
            InlineKeyboardMarkup(keyboard)
        )

    elif data.startswith("emojiprod_"):
        pid = data.split("emojiprod_", 1)[1]
        cursor.execute("SELECT name, emoji_id FROM products WHERE pid = ?", (pid,))
        row = cursor.fetchone()
        if not row:
            await ans(query, "❌ Product not found!", True)
            return
        context.user_data['emoji_pid'] = pid
        context.user_data['state'] = 'WAIT_PROD_EMOJI_ID'
        curr = row[1] if row[1] else "Default"
        await sedit(
            query,
            f"😀 **SET EMOJI — {escape_markdown(row[0])}**\n\n"
            f"Current Emoji ID: `{curr}`\n\n"
            f"➡️ Naya **Custom Emoji ID** bhejo (sirf number), ya seedha ek **premium emoji** bhej do.\n"
            f"*(Example: `6145292889913039900`)*\n\n"
            f"`clear` bhejo to default emoji wapas aa jayega.\n\n/cancel to abort",
            back_only("admin_set_emojis")
        )

    # ---------------- BACKUP / RESTORE ----------------
    elif data == "admin_backup":
        await ans(query, "⏳ Backup ban raha hai...")
        zip_bytes, counts = await asyncio.to_thread(build_backup_zip)
        fname = backup_filename()
        bio = io.BytesIO(zip_bytes)
        bio.name = fname
        caption = (
            "💾 Store Backup Ready\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"{backup_summary_text(counts)}\n\n"
            "⚠️ Is ZIP me API keys, payment key aur keys stock hai — kisi ko share mat karo.\n"
            "Restore ke liye ♻️ Restore dabake ye ZIP bhejo."
        )
        await context.bot.send_document(chat_id=ADMIN_ID, document=bio, filename=fname, caption=caption[:1000])

    elif data == "admin_restore":
        context.user_data['state'] = 'WAIT_RESTORE_ZIP'
        context.user_data.pop('restore_data', None)
        await sedit(
            query,
            "♻️ RESTORE BACKUP\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "➡️ Ab apna backup ZIP file (document ke roop me) bhejo.\n\n"
            "⚠️ Restore karne par abhi ka saara data (products, plans, keys, users balance, settings) "
            "backup wale data se REPLACE ho jayega. Confirm se pehle ek safety backup bhi aapko mil jayega.\n\n"
            "/cancel to abort",
            back_only()
        )

    elif data == "admin_restore_cancel":
        context.user_data.pop('restore_data', None)
        context.user_data['state'] = None
        await ans(query, "❌ Restore cancelled.")
        await refresh_admin_panel(context, query)

    elif data == "admin_restore_confirm":
        tables = context.user_data.pop('restore_data', None)
        context.user_data['state'] = None
        if not tables:
            await ans(query, "❌ Session expire ho gaya. Dobara ♻️ Restore karo.", True)
            return
        await ans(query, "⏳ Restoring...")

        # Safety backup (restore se pehle ka data)
        try:
            safe_zip, _ = await asyncio.to_thread(build_backup_zip)
            sname = "pre_restore_" + backup_filename()
            sbio = io.BytesIO(safe_zip)
            sbio.name = sname
            await context.bot.send_document(
                chat_id=ADMIN_ID, document=sbio, filename=sname,
                caption="🛡 Safety backup (restore se pehle ka data). Zarurat pade to isse restore kar sakte ho."
            )
        except Exception as e:
            logging.error(f"Pre-restore safety backup failed: {e}")

        try:
            counts = await asyncio.to_thread(apply_restore, tables)
        except Exception as e:
            logging.exception("Restore failed")
            await sedit(
                query,
                f"❌ Restore failed (purana data safe hai):\n{type(e).__name__}: {str(e)[:300]}",
                back_only()
            )
            return

        await sedit(
            query,
            "✅ RESTORE COMPLETE\n━━━━━━━━━━━━━━━━━━━━\n\n" + backup_summary_text(counts),
            back_only()
        )

    elif data == "admin_bot_stats":
        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0] or 0
        cursor.execute("SELECT COUNT(*) FROM users WHERE has_purchased = 1")
        active_buyers = cursor.fetchone()[0] or 0
        cursor.execute("SELECT COUNT(*), COALESCE(SUM(price), 0) FROM history")
        total_sales_count, total_sales_amt = cursor.fetchone()
        cursor.execute("SELECT COUNT(*) FROM users WHERE is_reseller = 1")
        total_resellers = cursor.fetchone()[0] or 0
        cursor.execute("SELECT COUNT(*), COALESCE(SUM(price), 0) FROM history WHERE date(date) = date('now')")
        today_sales_count, today_sales_amt = cursor.fetchone()
        cursor.execute("SELECT COUNT(*) FROM products")
        total_products = cursor.fetchone()[0] or 0

        text = (
            f"📊 **BOT STATS (LIVE)** 📊\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"👥 **Total Registered Users:** {total_users}\n"
            f"🛒 **Active Buyers:** {active_buyers}\n"
            f"💰 **Total Sales:** {total_sales_count or 0} orders (₹{(total_sales_amt or 0.0):.2f})\n"
            f"🌟 **Total Resellers:** {total_resellers}\n"
            f"📅 **Today's Sales:** {today_sales_count or 0} orders (₹{(today_sales_amt or 0.0):.2f})\n"
            f"📦 **Total Active Products:** {total_products}\n"
            f"━━━━━━━━━━━━━━━━━━━━"
        )
        keyboard = [
            [colored_button("🔄 Refresh", "admin_bot_stats", style="primary")],
            [colored_back_button("admin_back_panel")]
        ]
        await sedit(query, text, InlineKeyboardMarkup(keyboard))

    elif data == "admin_set_support_uname":
        curr = get_support_username()
        context.user_data['state'] = 'WAIT_SUPPORT_UNAME'
        await sedit(
            query,
            f"☎️ **SET SUPPORT USERNAME**\n\n"
            f"Current Username: `@{curr}`\n\n"
            f"➡️ Send new Telegram username (without @):\n*(Example: `Rohit_BhaiTOP`)*\n\n/cancel to abort",
        )

    # ---------------- PRODUCTS ----------------
    elif data == "admin_add_prod":
        context.user_data['state'] = 'WAIT_PROD_NAME'
        await sedit(query, "➡️ **BULK ADD PRODUCTS — Step 1/2**\n\nProduct names bhejo **line by line** (jitne chahiye utne):\n`Drip`\n`HG`\n`Pato`\n\n/cancel to abort")

    elif data == "admin_rem_prod":
        cursor.execute("SELECT pid, name FROM products ORDER BY name")
        prods = cursor.fetchall()
        if not prods:
            await sedit(query, "No products to remove.", back_only())
            return
        keyboard = [[colored_button(f"❌ {p[1]} ({p[0]})", f"del_prod_{p[0]}", style="danger")] for p in prods[:90]]
        keyboard.append([colored_back_button("admin_back_panel")])
        await sedit(query, "Select product to remove:", InlineKeyboardMarkup(keyboard))

    elif data.startswith("del_prod_"):
        pid = data.split("_", 2)[2]
        cursor.execute("DELETE FROM custom_prices WHERE plan_id IN (SELECT id FROM plans WHERE product_pid = ?)", (pid,))
        cursor.execute("DELETE FROM products WHERE pid = ?", (pid,))
        cursor.execute("DELETE FROM plans WHERE product_pid = ?", (pid,))
        cursor.execute("DELETE FROM keys WHERE product_pid = ?", (pid,))
        conn.commit()
        await ans(query, "✅ Product removed!", True)
        await refresh_admin_panel(context, query)

    # ---------------- CATEGORIES ----------------
    elif data == "admin_add_category":
        context.user_data['state'] = 'WAIT_CATEGORY_NAME'
        await sedit(query, "📂 **ADD CATEGORY** 📂\n\n➡️ Enter new **Category Name**:\n*(Example: `📱 Mobile Games` or `💻 PC Games`)*\n\n/cancel to abort")

    elif data == "admin_rem_category":
        cursor.execute("SELECT id, name FROM categories ORDER BY sort_order, id")
        cats = cursor.fetchall()
        if not cats:
            await sedit(query, "📂 No categories found yet.", back_only())
            return
        keyboard = [[colored_button(f"❌ {c[1]}", f"del_category_{c[0]}", style="danger")] for c in cats]
        keyboard.append([colored_back_button("admin_back_panel")])
        await sedit(query, "🗑️ **REMOVE CATEGORY** 🗑️\n\nSelect category to remove:\n_(Its products become uncategorized — not deleted.)_", InlineKeyboardMarkup(keyboard))

    elif data.startswith("del_category_"):
        cat_id = data.split("del_category_", 1)[1]
        cursor.execute("SELECT name FROM categories WHERE id = ?", (cat_id,))
        crow = cursor.fetchone()
        if crow:
            cursor.execute("UPDATE products SET category = '' WHERE category = ?", (crow[0],))
            cursor.execute("DELETE FROM categories WHERE id = ?", (cat_id,))
            conn.commit()
            await ans(query, f"✅ Category '{crow[0]}' removed!", True)
        else:
            await ans(query, "❌ Already removed!", True)
        await refresh_admin_panel(context, query)

    elif data == "admin_reorder_categories":
        cats, keyboard = build_category_reorder_keyboard(cursor)
        if not cats:
            await sedit(query, "📂 No categories found yet. Add one first with 📂 Add Category.", back_only())
            return
        await sedit(query, REORDER_CATEGORIES_TEXT, InlineKeyboardMarkup(keyboard))

    elif data.startswith("catmove_up_") or data.startswith("catmove_down_"):
        direction = "up" if data.startswith("catmove_up_") else "down"
        prefix = "catmove_up_" if direction == "up" else "catmove_down_"
        try:
            cat_id = int(data.split(prefix, 1)[1])
        except ValueError:
            cat_id = None
        if cat_id is not None:
            move_category(cursor, cat_id, direction)
            conn.commit()
        cats, keyboard = build_category_reorder_keyboard(cursor)
        if not cats:
            await sedit(query, "✅ No categories left.", back_only())
            return
        await sedit(query, REORDER_CATEGORIES_TEXT, InlineKeyboardMarkup(keyboard))

    elif data == "admin_assign_category":
        cursor.execute("SELECT pid, name, category FROM products ORDER BY name")
        prods = cursor.fetchall()
        if not prods:
            await sedit(query, "❌ Pehle koi product add karo.", back_only())
            return
        keyboard = []
        for p in prods[:90]:
            tag = f" [{p[2]}]" if p[2] else " [—]"
            keyboard.append([colored_button(f"📦 {p[1]}{tag}", f"assigncat_prod_{p[0]}", style="primary")])
        keyboard.append([colored_back_button("admin_back_panel")])
        await sedit(query, "🔀 **ASSIGN CATEGORY** 🔀\n\nSelect a product (current category in brackets) 👇", InlineKeyboardMarkup(keyboard))

    elif data.startswith("assigncat_prod_"):
        pid = data.split("assigncat_prod_", 1)[1]
        cursor.execute("SELECT id, name FROM categories ORDER BY sort_order, id")
        cats = cursor.fetchall()
        if not cats:
            await sedit(query, "❌ No categories exist yet.\n\nFirst add one with 📂 Add Category.", back_only())
            return
        context.user_data['assigncat_pid'] = pid
        keyboard = [[colored_button(f"📂 {c[1]}", f"assigncat_set_{c[0]}", style="success")] for c in cats]
        keyboard.append([colored_button("🚫 Uncategorized", "assigncat_set_0", style="danger")])
        keyboard.append([colored_back_button("admin_assign_category")])
        await sedit(query, "📂 **Select category to assign this product to:**", InlineKeyboardMarkup(keyboard))

    elif data.startswith("assigncat_set_"):
        cat_id = data.split("assigncat_set_", 1)[1]
        pid = context.user_data.get('assigncat_pid')
        if not pid:
            await ans(query, "❌ Session expired, please try again.", True)
            return
        if cat_id == "0":
            cursor.execute("UPDATE products SET category = '' WHERE pid = ?", (pid,))
            conn.commit()
            await ans(query, "✅ Product uncategorized!", True)
        else:
            cursor.execute("SELECT name FROM categories WHERE id = ?", (cat_id,))
            crow = cursor.fetchone()
            if not crow:
                await ans(query, "❌ Category not found!", True)
                return
            cursor.execute("UPDATE products SET category = ? WHERE pid = ?", (crow[0], pid))
            conn.commit()
            await ans(query, f"✅ Product assigned to '{crow[0]}'!", True)
        await refresh_admin_panel(context, query)

    # ---------------- STYLES ----------------
    elif data == "admin_style_menu":
        text = (
            "🎨 **BUTTON STYLE CUSTOMIZATION** 🎨\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "Choose what you want to re-color:\n\n"
            "📂 **Category buttons** — shown on 🛍️ Shop Now\n"
            "📦 **Product buttons** — shown inside a category\n"
            "⏱️ **Plan buttons** — shown inside a product\n\n"
            "👇 Pick one below:"
        )
        keyboard = [
            [colored_button("📂 Category Buttons", "style_cat_list", style="success")],
            [colored_button("📦 Product Buttons", "style_prod_list", style="primary")],
            [colored_button("⏱️ Plan Buttons", "style_plan_list", style="primary")],
            [colored_back_button("admin_back_panel")]
        ]
        await sedit(query, text, InlineKeyboardMarkup(keyboard))

    elif data in ("style_cat_list",) or data.startswith("style_cat_set_"):
        if data.startswith("style_cat_set_"):
            rest = data.split("style_cat_set_", 1)[1]
            cat_id, _, style = rest.rpartition("_")
            set_category_style(cat_id, style)
            await ans(query, f"✅ Category style set to {style.capitalize()}!", True)
        cursor.execute("SELECT id, name, button_style FROM categories ORDER BY sort_order, id")
        cats = cursor.fetchall()
        if not cats:
            await sedit(query, "📂 No categories found yet.", back_only("admin_style_menu"))
            return
        keyboard = []
        for c in cats:
            style = norm_style(c[2], "success")
            keyboard.append([colored_button(f"{c[1]} ({style})", f"style_cat_pick_{c[0]}", style=style)])
        keyboard.append([colored_back_button("admin_style_menu")])
        await sedit(query, "📂 **Select a category to re-color:**", InlineKeyboardMarkup(keyboard))

    elif data.startswith("style_cat_pick_"):
        cat_id = data.split("style_cat_pick_", 1)[1]
        cursor.execute("SELECT name FROM categories WHERE id = ?", (cat_id,))
        row = cursor.fetchone()
        if not row:
            await ans(query, "❌ Category not found!", True)
            return
        keyboard = style_pick_keyboard(f"style_cat_set_{cat_id}", "style_cat_list")
        await sedit(query, f"🎨 **{escape_markdown(row[0])}**\n\nChoose a new button style:", InlineKeyboardMarkup(keyboard))

    elif data == "style_prod_list" or data.startswith("style_prod_set_"):
        if data.startswith("style_prod_set_"):
            rest = data.split("style_prod_set_", 1)[1]
            pid, _, style = rest.rpartition("_")
            set_product_style(pid, style)
            await ans(query, f"✅ Product style set to {style.capitalize()}!", True)
        cursor.execute("SELECT pid, name, button_style FROM products ORDER BY name")
        prods = cursor.fetchall()
        if not prods:
            await sedit(query, "No products found.", back_only("admin_style_menu"))
            return
        keyboard = []
        for p in prods[:90]:
            style = norm_style(p[2], "primary")
            keyboard.append([colored_button(f"{p[1]} ({style})", f"style_prod_pick_{p[0]}", style=style)])
        keyboard.append([colored_back_button("admin_style_menu")])
        await sedit(query, "📦 **Select a product to re-color:**\n_(Maintenance products still show as Danger to users.)_", InlineKeyboardMarkup(keyboard))

    elif data.startswith("style_prod_pick_"):
        pid = data.split("style_prod_pick_", 1)[1]
        cursor.execute("SELECT name FROM products WHERE pid = ?", (pid,))
        row = cursor.fetchone()
        if not row:
            await ans(query, "❌ Product not found!", True)
            return
        keyboard = style_pick_keyboard(f"style_prod_set_{pid}", "style_prod_list")
        await sedit(query, f"🎨 **{escape_markdown(row[0])}**\n\nChoose a new button style:", InlineKeyboardMarkup(keyboard))

    elif data == "style_plan_list" or data.startswith("style_plan_allset_"):
        if data.startswith("style_plan_allset_"):
            style = norm_style(data.split("style_plan_allset_", 1)[1], "primary")
            cursor.execute("UPDATE plans SET button_style = ?", (style,))
            conn.commit()
            await ans(query, f"✅ All plans set to {style.capitalize()}!", True)
        cursor.execute("SELECT pid, name FROM products ORDER BY name")
        prods = cursor.fetchall()
        keyboard = [[colored_button("🌍 Apply Style To ALL Plans (All Products)", "style_plan_all", style="success")]]
        keyboard += [[colored_button(f"📦 {p[1]}", f"style_plan_prod_{p[0]}", style="primary")] for p in prods[:88]]
        keyboard.append([colored_back_button("admin_style_menu")])
        await sedit(query, "⏱️ **Select a product to view its plans, or apply one style to every plan at once:**", InlineKeyboardMarkup(keyboard))

    elif data == "style_plan_all":
        keyboard = style_pick_keyboard("style_plan_allset", "style_plan_list")
        await sedit(query, "🎨 **Apply Style To ALL Plans**\n\nThis will re-color every plan button across every product.\n\nChoose the style:", InlineKeyboardMarkup(keyboard))

    elif data.startswith("style_plan_prod_") or data.startswith("style_plan_set_"):
        if data.startswith("style_plan_set_"):
            rest = data.split("style_plan_set_", 1)[1]
            plan_id, _, style = rest.rpartition("_")
            set_plan_style(plan_id, style)
            await ans(query, f"✅ Plan style set to {style.capitalize()}!", True)
            pid = context.user_data.get('style_plan_back_pid')
            if not pid:
                cursor.execute("SELECT product_pid FROM plans WHERE id = ?", (plan_id,))
                r = cursor.fetchone()
                pid = r[0] if r else None
            if not pid:
                await refresh_admin_panel(context, query)
                return
        else:
            pid = data.split("style_plan_prod_", 1)[1]
        cursor.execute("SELECT id, duration, button_style FROM plans WHERE product_pid = ? ORDER BY id", (pid,))
        plans = cursor.fetchall()
        if not plans:
            await sedit(query, "No plans found for this product.", back_only("style_plan_list"))
            return
        keyboard = []
        for pl in plans:
            style = norm_style(pl[2], "primary")
            keyboard.append([colored_button(f"{pl[1]} ({style})", f"style_plan_pick_{pl[0]}", style=style)])
        keyboard.append([colored_back_button("style_plan_list")])
        await sedit(query, "⏱️ **Select a plan to re-color:**", InlineKeyboardMarkup(keyboard))

    elif data.startswith("style_plan_pick_"):
        plan_id = data.split("style_plan_pick_", 1)[1]
        cursor.execute("SELECT plans.duration, products.name, products.pid FROM plans JOIN products ON plans.product_pid = products.pid WHERE plans.id = ?", (plan_id,))
        row = cursor.fetchone()
        if not row:
            await ans(query, "❌ Plan not found!", True)
            return
        context.user_data['style_plan_back_pid'] = row[2]
        keyboard = style_pick_keyboard(f"style_plan_set_{plan_id}", f"style_plan_prod_{row[2]}")
        await sedit(query, f"🎨 **{escape_markdown(row[1])} — {escape_markdown(row[0])}**\n\nChoose a new button style:", InlineKeyboardMarkup(keyboard))

    # ---------------- PLANS ----------------
    elif data == "admin_add_plan":
        cursor.execute("SELECT pid, name FROM products ORDER BY name")
        prods = cursor.fetchall()
        if not prods:
            await sedit(query, "❌ First add a product!", back_only())
            return
        keyboard = [[colored_button(f"📦 {p[1]}", f"add_plan_prod_{p[0]}", style="success")] for p in prods[:90]]
        keyboard.append([colored_back_button("admin_back_panel")])
        await sedit(query, "Select Product for Plan:", InlineKeyboardMarkup(keyboard))

    elif data.startswith("add_plan_prod_"):
        pid = data.split("add_plan_prod_", 1)[1]
        context.user_data['temp_pid'] = pid
        context.user_data['state'] = 'WAIT_PLAN_DURATION'
        await sedit(query, "➡️ **BULK ADD PLANS — Step 1/4**\n\nDurations bhejo **line by line** (users ko jo dikhega):\n`1 Hour`\n`3 Days`\n`7 Days`\n\n/cancel to abort")

    elif data == "admin_rem_plan":
        prods, keyboard = product_picker_keyboard(cursor, "delplanprod_", style="danger", label_prefix="🗑️")
        if not prods:
            await sedit(query, "No active plans found.", back_only())
            return
        await sedit(query, "🗑️ **REMOVE PLAN**\n\nSelect product:", InlineKeyboardMarkup(keyboard))

    elif data.startswith("delplanprod_"):
        pid = data.split("delplanprod_", 1)[1]
        cursor.execute("SELECT name FROM products WHERE pid = ?", (pid,))
        prow = cursor.fetchone()
        cursor.execute("SELECT id, duration FROM plans WHERE product_pid = ? ORDER BY id", (pid,))
        plans = cursor.fetchall()
        if not plans:
            await sedit(query, "No plans found for this product.", back_only("admin_rem_plan"))
            return
        keyboard = [[colored_button(f"❌ {pl[1]}", f"del_plan_{pl[0]}", style="danger")] for pl in plans[:90]]
        keyboard.append([colored_back_button("admin_rem_plan")])
        await sedit(query, f"🗑️ **{escape_markdown(prow[0] if prow else pid)}**\n\nSelect Plan to remove:", InlineKeyboardMarkup(keyboard))

    elif data.startswith("del_plan_"):
        plan_id = data.split("_", 2)[2]
        cursor.execute("DELETE FROM custom_prices WHERE plan_id = ?", (plan_id,))
        cursor.execute("DELETE FROM plans WHERE id = ?", (plan_id,))
        conn.commit()
        await ans(query, "✅ Plan removed!", True)
        await refresh_admin_panel(context, query)

    # ---------------- KEYS ----------------
    elif data == "admin_add_keys":
        cursor.execute("SELECT pid, name FROM products ORDER BY name")
        prods = cursor.fetchall()
        if not prods:
            await sedit(query, "❌ First add a product!", back_only())
            return
        keyboard = [[colored_button(f"📦 {p[1]}", f"key_prod_{p[0]}", style="success")] for p in prods[:90]]
        keyboard.append([colored_back_button("admin_back_panel")])
        await sedit(query, "Select Product to add keys:", InlineKeyboardMarkup(keyboard))

    elif data.startswith("key_prod_"):
        pid = data.split("key_prod_", 1)[1]
        cursor.execute("SELECT id, duration FROM plans WHERE product_pid = ? ORDER BY id", (pid,))
        plans = cursor.fetchall()
        if not plans:
            await sedit(query, "❌ Is product me koi plan nahi hai. Pehle ➕ Add Plan karo.", back_only("admin_add_keys"))
            return
        keyboard = [[colored_button(f"⏱️ {pl[1]}", f"key_plan_{pl[0]}", style="primary")] for pl in plans]
        keyboard.append([colored_back_button("admin_add_keys")])
        await sedit(query, "Select Duration for keys:", InlineKeyboardMarkup(keyboard))

    elif data.startswith("key_plan_"):
        plan_id = data.split("key_plan_", 1)[1]
        cursor.execute("SELECT product_pid, duration FROM plans WHERE id = ?", (plan_id,))
        row = cursor.fetchone()
        if not row:
            await ans(query, "❌ Plan not found!", True)
            return
        context.user_data['key_pid'] = row[0]
        context.user_data['key_dur'] = row[1]
        context.user_data['state'] = 'WAIT_KEYS_INPUT'
        await sedit(query, "➡️ Send keys line by line:\n\n/cancel to abort")

    elif data == "admin_check_keys":
        cursor.execute("""
            SELECT products.name, keys.duration, keys.key_value
            FROM keys LEFT JOIN products ON keys.product_pid = products.pid
            ORDER BY products.name, keys.duration, keys.id
        """)
        all_keys = cursor.fetchall()
        text = "🔍 **Current Key Stock & Details** 🔍\n━━━━━━━━━━━━━━━━━━━━\n\n"
        if not all_keys:
            text += "⚠️ No keys available in local stock inventory."
        else:
            current_header = None
            for row in all_keys:
                p_name = escape_markdown(row[0]) if row[0] else "Unknown Product"
                p_dur = escape_markdown(row[1])
                header = f"📦 **{p_name}** | ⏱️ **{p_dur}**\n"
                if header != current_header:
                    current_header = header
                    text += f"\n{header}"
                text += f"• `{str(row[2]).replace('`', chr(39))}`\n"
                if len(text) > 3800:
                    text += "\n*(List truncated due to message length limit)*"
                    break
        await sedit(query, text, back_only())

    elif data == "admin_rem_keys":
        cursor.execute("""
            SELECT DISTINCT products.pid, products.name FROM keys
            JOIN products ON keys.product_pid = products.pid ORDER BY products.name
        """)
        prods = cursor.fetchall()
        if not prods:
            await sedit(query, "🗑️ **Remove Keys**\n\n⚠️ No keys found.", back_only())
            return
        keyboard = [[colored_button(f"📦 {p[1]}", f"remkeyprod_{p[0]}", style="danger")] for p in prods[:90]]
        keyboard.append([colored_back_button("admin_back_panel")])
        await sedit(query, "🗑️ **Select Product to remove keys from:**", InlineKeyboardMarkup(keyboard))

    elif data.startswith("remkeyprod_"):
        pid = data.split("_", 1)[1]
        cursor.execute("SELECT name FROM products WHERE pid = ?", (pid,))
        prod_row = cursor.fetchone()
        prod_name = escape_markdown(prod_row[0]) if prod_row else escape_markdown(pid)
        cursor.execute("SELECT DISTINCT duration FROM keys WHERE product_pid = ?", (pid,))
        durations = [r[0] for r in cursor.fetchall()]
        if not durations:
            await sedit(query, f"🗑️ **{prod_name}**\n\n⚠️ No keys found.", back_only("admin_rem_keys"))
            return
        context.user_data['remkey_pid'] = pid
        context.user_data['remkey_durations'] = durations
        keyboard = [[colored_button(f"⏱️ {d}", f"remkeydur_{i}", style="primary")] for i, d in enumerate(durations)]
        keyboard.append([colored_back_button("admin_rem_keys")])
        await sedit(query, f"🗑️ **{prod_name}**\n\nSelect Plan/Duration:", InlineKeyboardMarkup(keyboard))

    elif data.startswith("remkeydur_") or data.startswith("remkeydel_"):
        if data.startswith("remkeydel_"):
            key_id = data.split("_", 1)[1]
            cursor.execute("SELECT id FROM keys WHERE id = ?", (key_id,))
            if not cursor.fetchone():
                await ans(query, "❌ Already removed!", True)
            else:
                cursor.execute("DELETE FROM keys WHERE id = ?", (key_id,))
                conn.commit()
                await ans(query, "✅ Key removed!", True)
            pid = context.user_data.get('remkey_pid')
            duration = context.user_data.get('remkey_selected_dur')
            if not pid or not duration:
                await refresh_admin_panel(context, query)
                return
        else:
            idx = int(data.split("_", 1)[1])
            pid = context.user_data.get('remkey_pid')
            durations = context.user_data.get('remkey_durations', [])
            if pid is None or idx >= len(durations):
                await ans(query, "❌ Session expired, please try again.", True)
                return
            duration = durations[idx]
            context.user_data['remkey_selected_dur'] = duration

        cursor.execute("SELECT name FROM products WHERE pid = ?", (pid,))
        prod_row = cursor.fetchone()
        prod_name = escape_markdown(prod_row[0]) if prod_row else escape_markdown(pid)
        safe_duration = escape_markdown(duration)
        cursor.execute("SELECT id, key_value FROM keys WHERE product_pid = ? AND duration = ? ORDER BY id", (pid, duration))
        keys_rows = cursor.fetchall()
        if not keys_rows:
            await sedit(query, f"🗑️ **{prod_name}** | ⏱️ **{safe_duration}**\n\n⚠️ No keys found.", back_only(f"remkeyprod_{pid}"))
            return
        text = f"🗑️ **REMOVE KEYS**\n📦 **Product:** {prod_name}\n⏱️ **Plan:** {safe_duration}\n━━━━━━━━━━━━━━━━━━━━\n\n"
        keyboard = []
        for k_id, k_val in keys_rows[:40]:
            k_val = str(k_val)
            text += f"🔑 `{k_val.replace('`', chr(39))}`\n"
            keyboard.append([colored_button(f"❌ Remove Now — {k_val[:20]}", f"remkeydel_{k_id}", style="danger")])
            if len(text) > 3500:
                text += "\n*(List truncated — remove some keys and refresh)*"
                break
        keyboard.append([colored_back_button(f"remkeyprod_{pid}")])
        await sedit(query, text, InlineKeyboardMarkup(keyboard))

    # ---------------- LINKS / MAINTENANCE / GROUP / VIDEO ----------------
    elif data == "admin_prod_links":
        cursor.execute("SELECT pid, name FROM products ORDER BY name")
        prods = cursor.fetchall()
        bot_uname = context.bot.username
        text = "🔗 **ALL PRODUCTS UNIQUE DEEP LINKS** 🔗\n━━━━━━━━━━━━━━━━━━━━\n\n"
        if not prods:
            text += "❌ No products found. First add products."
        else:
            for p in prods:
                link = f"https://t.me/{bot_uname}?start=prod_{p[0]}"
                text += f"📦 **Product:** {escape_markdown(p[1])}\n🆔 **PID:** `{p[0]}`\n🔗 **Direct Link:**\n`{link}`\n------------------------------------\n"
                if len(text) > 3800:
                    text += "\n*(truncated)*"
                    break
        await sedit(query, text, back_only())

    elif data == "admin_maintenance_prod" or data.startswith("toggle_maint_"):
        if data.startswith("toggle_maint_"):
            pid = data.split("_", 2)[2]
            cursor.execute("SELECT name, is_maintenance FROM products WHERE pid = ?", (pid,))
            row = cursor.fetchone()
            if not row:
                await ans(query, "❌ Product not found!", True)
                return
            new_state = 0 if row[1] else 1
            cursor.execute("UPDATE products SET is_maintenance = ? WHERE pid = ?", (new_state, pid))
            conn.commit()
            await ans(query, f"🛠 {row[0]} set to Maintenance!" if new_state else f"✅ {row[0]} is Active again!", True)
        cursor.execute("SELECT pid, name, is_maintenance FROM products ORDER BY name")
        prods = cursor.fetchall()
        if not prods:
            await sedit(query, "No products found.", back_only())
            return
        keyboard = []
        for pid, pname, in_maint in prods[:90]:
            label = f"🛠 {pname} (Under Maintenance)" if in_maint else f"✅ {pname} (Active)"
            keyboard.append([colored_button(label, f"toggle_maint_{pid}", style="danger" if in_maint else "success")])
        keyboard.append([colored_back_button("admin_back_panel")])
        await sedit(query, "🛠 **Select a product to toggle Maintenance Mode:**", InlineKeyboardMarkup(keyboard))

    elif data == "admin_set_group_link":
        cursor.execute("SELECT pid, name, group_link FROM products ORDER BY name")
        prods = cursor.fetchall()
        if not prods:
            await sedit(query, "No products found.", back_only())
            return
        keyboard = []
        for pid, pname, gl in prods[:90]:
            label = f"🔗 {pname} (Set)" if gl else f"➕ {pname} (Not Set)"
            keyboard.append([colored_button(label, f"grplink_prod_{pid}", style="success" if gl else "primary")])
        keyboard.append([colored_back_button("admin_back_panel")])
        await sedit(query, "🔗 **Select a product to set its Group/Updates Link:**", InlineKeyboardMarkup(keyboard))

    elif data.startswith("grplink_prod_"):
        pid = data.split("_", 2)[2]
        cursor.execute("SELECT name, group_link FROM products WHERE pid = ?", (pid,))
        row = cursor.fetchone()
        if not row:
            await ans(query, "❌ Product not found!", True)
            return
        context.user_data['grplink_pid'] = pid
        context.user_data['state'] = 'WAIT_GROUP_LINK'
        curr = row[1] if row[1] else "Not Set"
        await sedit(
            query,
            f"🔗 **SET GROUP LINK — {escape_markdown(row[0])}**\n\n"
            f"Current Link: `{curr}`\n\n"
            f"➡️ Send the Telegram group/channel invite link (or `clear` to remove):\n"
            f"*(Example: `https://t.me/+5xJE88q0GoA3MWE1`)*\n\n/cancel to abort"
        )

    elif data == "admin_set_prod_video":
        cursor.execute("SELECT pid, name, demo_video FROM products ORDER BY name")
        prods = cursor.fetchall()
        if not prods:
            await sedit(query, "No products found.", back_only())
            return
        keyboard = []
        for pid, pname, dv in prods[:90]:
            label = f"🎥 {pname} (Set)" if dv else f"➕ {pname} (Not Set)"
            keyboard.append([colored_button(label, f"prodvideo_prod_{pid}", style="success" if dv else "primary")])
        keyboard.append([colored_back_button("admin_back_panel")])
        await sedit(query, "🎥 **Select a product to set its Demo Video Link:**", InlineKeyboardMarkup(keyboard))

    elif data.startswith("prodvideo_prod_"):
        pid = data.split("_", 2)[2]
        cursor.execute("SELECT name, demo_video FROM products WHERE pid = ?", (pid,))
        row = cursor.fetchone()
        if not row:
            await ans(query, "❌ Product not found!", True)
            return
        context.user_data['prodvideo_pid'] = pid
        context.user_data['state'] = 'WAIT_PROD_VIDEO_LINK'
        curr = row[1] if row[1] else "Not Set"
        await sedit(
            query,
            f"🎥 **SET DEMO VIDEO — {escape_markdown(row[0])}**\n\n"
            f"Current Link: `{curr}`\n\n"
            f"➡️ Send the video/Telegram link (or `clear` to remove):\n"
            f"*(Example: `https://t.me/+uAZyCSJUFGwxYmRl`)*\n\n/cancel to abort"
        )

    # ---------------- CUSTOM PRICES ----------------
    elif data == "admin_set_custom_price":
        cursor.execute("SELECT pid, name FROM products ORDER BY name")
        prods = cursor.fetchall()
        if not prods:
            await sedit(query, "No products found.", back_only())
            return
        keyboard = [[colored_button(f"📦 {p[1]}", f"custprice_prod_{p[0]}", style="primary")] for p in prods[:90]]
        keyboard.append([colored_back_button("admin_back_panel")])
        await sedit(query, "💵 **Select Product for Custom Price:**", InlineKeyboardMarkup(keyboard))

    elif data.startswith("custprice_prod_"):
        pid = data.split("_", 2)[2]
        cursor.execute("SELECT id, duration FROM plans WHERE product_pid = ? ORDER BY id", (pid,))
        plans = cursor.fetchall()
        if not plans:
            await sedit(query, "No plans found for this product.", back_only("admin_set_custom_price"))
            return
        keyboard = [[colored_button(f"⏱️ {pl[1]}", f"custprice_plan_{pl[0]}", style="primary")] for pl in plans]
        keyboard.append([colored_back_button("admin_set_custom_price")])
        await sedit(query, "Select Plan:", InlineKeyboardMarkup(keyboard))

    elif data.startswith("custprice_plan_"):
        plan_id = data.split("_", 2)[2]
        context.user_data['custprice_plan_id'] = plan_id
        context.user_data['state'] = 'WAIT_CUSTOM_PRICE_INPUT'
        await sedit(query, "➡️ Send **User ID** and **Price** separated by space:\n*(Example: `123456789 25`)*\n\n/cancel to abort")

    elif data == "admin_rem_custom_price":
        cursor.execute("""
            SELECT DISTINCT products.pid, products.name FROM custom_prices
            JOIN plans ON custom_prices.plan_id = plans.id
            JOIN products ON plans.product_pid = products.pid ORDER BY products.name
        """)
        prods = cursor.fetchall()
        if not prods:
            await sedit(query, "No custom prices set for any product yet.", back_only())
            return
        keyboard = [[colored_button(f"📦 {p[1]}", f"remcustprice_prod_{p[0]}", style="danger")] for p in prods[:90]]
        keyboard.append([colored_back_button("admin_back_panel")])
        await sedit(query, "🗑️ **Select Product to view/remove Custom Prices:**", InlineKeyboardMarkup(keyboard))

    elif data.startswith("remcustprice_prod_"):
        pid = data.split("_", 2)[2]
        cursor.execute("""
            SELECT DISTINCT plans.id, plans.duration FROM plans
            JOIN custom_prices ON custom_prices.plan_id = plans.id
            WHERE plans.product_pid = ?
        """, (pid,))
        plans = cursor.fetchall()
        if not plans:
            await sedit(query, "No custom prices set for this product's plans.", back_only("admin_rem_custom_price"))
            return
        keyboard = [[colored_button(f"⏱️ {pl[1]}", f"remcustprice_plan_{pl[0]}", style="primary")] for pl in plans]
        keyboard.append([colored_back_button("admin_rem_custom_price")])
        await sedit(query, "Select Plan:", InlineKeyboardMarkup(keyboard))

    elif data.startswith("remcustprice_plan_"):
        plan_id = data.split("_", 2)[2]
        cursor.execute("""
            SELECT products.pid, products.name, plans.duration FROM plans
            JOIN products ON plans.product_pid = products.pid WHERE plans.id = ?
        """, (plan_id,))
        plan_info = cursor.fetchone()
        pid = plan_info[0] if plan_info else None
        prod_name = escape_markdown(plan_info[1]) if plan_info else "Unknown"
        plan_dur = escape_markdown(plan_info[2]) if plan_info else "Unknown"
        back_cb = f"remcustprice_prod_{pid}" if pid else "admin_rem_custom_price"
        cursor.execute("""
            SELECT custom_prices.id, custom_prices.user_id, custom_prices.price, users.full_name, users.username
            FROM custom_prices LEFT JOIN users ON custom_prices.user_id = users.user_id
            WHERE custom_prices.plan_id = ? ORDER BY custom_prices.id DESC
        """, (plan_id,))
        rows = cursor.fetchall()
        if not rows:
            await sedit(query, "No custom prices set for this plan.", back_only(back_cb))
            return
        text = f"🗑️ **CUSTOM PRICES**\n📦 **Product:** {prod_name}\n⏱️ **Plan:** {plan_dur}\n━━━━━━━━━━━━━━━━━━━━\n\n"
        keyboard = []
        for cp_id, uid, price, fname, uname in rows[:60]:
            display_name = escape_markdown(fname) if fname else "N/A"
            display_uname = f"@{escape_markdown(uname)}" if uname else "N/A"
            text += f"👤 **Name:** {display_name}\n🏷️ **Username:** {display_uname}\n🆔 **User ID:** `{uid}`\n💵 **Price:** ₹{price:.2f}\n------------------------------------\n"
            keyboard.append([colored_button(f"❌ Remove — {uid} (₹{price:.2f})", f"remcustprice_del_{cp_id}", style="danger")])
        keyboard.append([colored_back_button(back_cb)])
        if len(text) > 3900:
            text = text[:3800].rsplit("\n", 1)[0] + "\n*(truncated)*"
        await sedit(query, text, InlineKeyboardMarkup(keyboard))

    elif data.startswith("remcustprice_del_"):
        cp_id = data.split("_", 2)[2]
        cursor.execute("SELECT plan_id, user_id, price FROM custom_prices WHERE id = ?", (cp_id,))
        cp_row = cursor.fetchone()
        if not cp_row:
            await ans(query, "❌ Already removed!", True)
            return
        cursor.execute("DELETE FROM custom_prices WHERE id = ?", (cp_id,))
        conn.commit()
        await ans(query, f"✅ Custom price removed for user {cp_row[1]}!", True)
        await refresh_admin_panel(context, query)

    # ---------------- PAYMENT / API SETTINGS ----------------
    elif data == "admin_set_payment":
        text = (
            f"💠 **ZAPUPI PAYMENT SETTINGS** 💠\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"⚡ **Active Gateway:** ZapUPI\n\n"
            f"🔑 Zap Key: `{mask_secret(get_zapupi_key())}`\n\n"
            f"Select what you want to change:"
        )
        keyboard = [
            [colored_button("✏️ Set ZapUPI Key", "admin_input_zapupi_key", style="primary")],
            [colored_back_button("admin_back_panel")]
        ]
        await sedit(query, text, InlineKeyboardMarkup(keyboard))

    elif data == "admin_input_zapupi_key":
        context.user_data['state'] = 'WAIT_ZAPUPI_KEY'
        await sedit(query, "➡️ Send your new ZapUPI Zap Key:\n*(Get it from your ZapUPI dashboard)*\n\n/cancel to abort")

    elif data == "admin_set_store_api":
        text = (
            f"🔑 **STORE API SETTINGS** 🔑\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🌐 Endpoint: `{API_URL}`\n"
            f"🔑 API Key: `{mask_secret(get_store_api_key())}`\n\n"
            f"➡️ Tap below to update the key:"
        )
        keyboard = [
            [colored_button("✏️ Set API Key", "admin_input_store_api", style="primary")],
            [colored_back_button("admin_back_panel")]
        ]
        await sedit(query, text, InlineKeyboardMarkup(keyboard))

    elif data == "admin_input_store_api":
        context.user_data['state'] = 'WAIT_STORE_API_KEY'
        await sedit(query, f"🔑 Current API Key: `{mask_secret(get_store_api_key())}`\n\n➡️ Send new Reseller API Key:\n\n/cancel to abort")

    elif data == "admin_set_reseller_price":
        prods, keyboard = product_picker_keyboard(cursor, "resprod_", style="primary", label_prefix="⚙️")
        if not prods:
            await sedit(query, "No plans found.", back_only())
            return
        await sedit(query, "⚙️ **SET PLAN RESELLER PRICE**\n\nSelect Product:", InlineKeyboardMarkup(keyboard))

    elif data.startswith("resprod_"):
        pid = data.split("resprod_", 1)[1]
        cursor.execute("SELECT name FROM products WHERE pid = ?", (pid,))
        prow = cursor.fetchone()
        cursor.execute("SELECT id, duration, price, reseller_price FROM plans WHERE product_pid = ? ORDER BY id", (pid,))
        plans = cursor.fetchall()
        if not plans:
            await sedit(query, "No plans found for this product.", back_only("admin_set_reseller_price"))
            return
        keyboard = [
            [colored_button(f"⚙️ {p[1]} (Normal ₹{(p[2] or 0):.2f} | Reseller ₹{(p[3] or 0):.2f})", f"set_plan_reseller_{p[0]}", style="primary")]
            for p in plans[:90]
        ]
        keyboard.append([colored_back_button("admin_set_reseller_price")])
        await sedit(
            query,
            f"⚙️ **{escape_markdown(prow[0] if prow else pid)}**\n\nSelect Plan to change Reseller Price:",
            InlineKeyboardMarkup(keyboard)
        )

    elif data.startswith("set_plan_reseller_"):
        plan_id = data.split("set_plan_reseller_", 1)[1]
        context.user_data['edit_plan_id'] = plan_id
        context.user_data['state'] = 'WAIT_PLAN_RESELLER_PRICE'
        await sedit(query, "➡️ Enter new Reseller Price for this plan:\n*(Example: `20`)*\n\n/cancel to abort")

    elif data == "admin_set_upgrade_price":
        curr = get_reseller_price()
        context.user_data['state'] = 'WAIT_RESELLER_UPGRADE_PRICE'
        await sedit(
            query,
            f"💎 **SET RESELLER UPGRADE PRICE**\n\n"
            f"Current Upgrade Price: ₹{curr:.2f}\n\n"
            f"➡️ Send new upgrade price:\n*(Example: `449`)*\n\n/cancel to abort"
        )

    elif data == "admin_add_reseller":
        context.user_data['state'] = 'WAIT_ADD_RESELLER_ID'
        await sedit(query, "➡️ Send User ID to promote to Reseller:\n\n/cancel to abort")

    elif data == "admin_rem_reseller":
        context.user_data['state'] = 'WAIT_REM_RESELLER_ID'
        await sedit(query, "➡️ Send User ID to demote from Reseller:\n\n/cancel to abort")

    elif data == "admin_my_resellers":
        cursor.execute("SELECT user_id, full_name, username FROM users WHERE is_reseller = 1")
        resellers = cursor.fetchall()
        text = "👥 **MY RESELLERS LIST** 👥\n━━━━━━━━━━━━━━━━━━━━\n\n"
        if not resellers:
            text += "No active resellers found."
        else:
            for r in resellers:
                r_name = escape_markdown(r[1]) if r[1] else "N/A"
                r_uname = f"@{escape_markdown(r[2])}" if r[2] else "N/A"
                text += f"👤 **Name:** {r_name}\n🏷️ **Username:** {r_uname}\n🆔 **ID:** `{r[0]}`\n------------------------------------\n"
                if len(text) > 3800:
                    text += "\n*(truncated)*"
                    break
        await sedit(query, text, back_only())

    elif data == "admin_change_price":
        prods, keyboard = product_picker_keyboard(cursor, "chgprod_", style="primary", label_prefix="💲")
        if not prods:
            await sedit(query, "No active plans found.", back_only())
            return
        await sedit(query, "💲 **CHANGE PRODUCT PRICE**\n\nSelect Product:", InlineKeyboardMarkup(keyboard))

    elif data.startswith("chgprod_"):
        pid = data.split("chgprod_", 1)[1]
        cursor.execute("SELECT name FROM products WHERE pid = ?", (pid,))
        prow = cursor.fetchone()
        cursor.execute("SELECT id, duration, price FROM plans WHERE product_pid = ? ORDER BY id", (pid,))
        plans = cursor.fetchall()
        if not plans:
            await sedit(query, "No plans found for this product.", back_only("admin_change_price"))
            return
        keyboard = [
            [colored_button(f"💲 {p[1]} - ₹{(p[2] or 0):.2f}", f"chg_price_{p[0]}", style="primary")]
            for p in plans[:90]
        ]
        keyboard.append([colored_back_button("admin_change_price")])
        await sedit(
            query,
            f"💲 **{escape_markdown(prow[0] if prow else pid)}**\n\nSelect Plan to change Normal Price:",
            InlineKeyboardMarkup(keyboard)
        )

    elif data.startswith("chg_price_"):
        plan_id = data.split("_", 2)[2]
        context.user_data['chg_plan_id'] = plan_id
        context.user_data['state'] = 'WAIT_NEW_PLAN_PRICE'
        await sedit(query, "➡️ Enter new Normal Price:\n*(Example: `50`)*\n\n/cancel to abort")

    elif data == "admin_change_name":
        cursor.execute("SELECT pid, name FROM products ORDER BY name")
        prods = cursor.fetchall()
        if not prods:
            await sedit(query, "No products found.", back_only())
            return
        keyboard = [[colored_button(f"✏️ {p[1]}", f"rename_prod_{p[0]}", style="primary")] for p in prods[:90]]
        keyboard.append([colored_back_button("admin_back_panel")])
        await sedit(query, "Select Product to Rename:", InlineKeyboardMarkup(keyboard))

    elif data.startswith("rename_prod_"):
        pid = data.split("_", 2)[2]
        context.user_data['rename_pid'] = pid
        context.user_data['state'] = 'WAIT_NEW_PROD_NAME'
        await sedit(query, "➡️ Enter new Product Name:\n\n/cancel to abort")

    elif data == "admin_change_pid":
        cursor.execute("SELECT pid, name FROM products ORDER BY name")
        prods = cursor.fetchall()
        if not prods:
            await sedit(query, "No products found.", back_only())
            return
        keyboard = [[colored_button("✏️ Change ALL (Bulk)", "chgpid_bulk", style="success")]]
        keyboard += [[colored_button(f"📦 {p[1]} — {p[0]}", f"chgpid_prod_{p[0]}", style="primary")] for p in prods[:88]]
        keyboard.append([colored_back_button("admin_back_panel")])
        await sedit(
            query,
            "🆔 **CHANGE PID** 🆔\n\n"
            "Har button me *Product — Current PID* dikh raha hai.\n\n"
            "👇 Ek product chuno, ya sabka PID ek saath badalne ke liye **Change ALL** dabao:",
            InlineKeyboardMarkup(keyboard)
        )

    elif data.startswith("chgpid_prod_"):
        pid = data.split("chgpid_prod_", 1)[1]
        cursor.execute("SELECT name FROM products WHERE pid = ?", (pid,))
        row = cursor.fetchone()
        if not row:
            await ans(query, "❌ Product not found!", True)
            return
        context.user_data['chgpid_old'] = pid
        context.user_data['state'] = 'WAIT_NEW_PID'
        await sedit(
            query,
            f"🆔 **CHANGE PID — {escape_markdown(row[0])}**\n\n"
            f"Current PID: `{pid}`\n\n"
            f"➡️ Naya PID bhejo (letters, numbers, underscore ya dash — max {MAX_PID_LEN}):\n\n/cancel to abort"
        )

    elif data == "chgpid_bulk":
        cursor.execute("SELECT pid, name FROM products ORDER BY name")
        prods = cursor.fetchall()
        if not prods:
            await sedit(query, "No products found.", back_only())
            return
        context.user_data['bulkpid_order'] = [p[0] for p in prods]
        context.user_data['state'] = 'WAIT_BULK_PID'
        listing = "\n".join(f"{i}. {escape_markdown(p[1])} — `{p[0]}`" for i, p in enumerate(prods, 1))
        if len(listing) > 3000:
            listing = listing[:3000].rsplit("\n", 1)[0] + "\n..."
        await sedit(
            query,
            f"✏️ **CHANGE ALL PIDs**\n\nCurrent order:\n{listing}\n\n"
            f"➡️ Ab **{len(prods)} naye PID** bhejo — line by line, isi order me.\n"
            f"Jisko change nahi karna uski line me `-` likho.\n\n/cancel to abort"
        )

    elif data == "admin_set_how_video":
        context.user_data['state'] = 'WAIT_HOW_VIDEO_URL'
        await sedit(query, "➡️ Send video tutorial URL:\n*(Example: `https://youtube.com/...` or send `clear` to remove)*\n\n/cancel to abort")

    elif data == "admin_add_bal":
        context.user_data['state'] = 'WAIT_ADD_BAL_INPUT'
        await sedit(query, "➡️ Send User ID and Amount separated by space:\n*(Example: `123456789 100`)*\n\n/cancel to abort")

    elif data == "admin_rem_bal":
        context.user_data['state'] = 'WAIT_REM_BAL_INPUT'
        await sedit(query, "➡️ Send User ID and Amount separated by space:\n*(Example: `123456789 50`)*\n\n/cancel to abort")

    elif data == "admin_check_bal":
        context.user_data['state'] = 'WAIT_CHECK_BAL_ID'
        await sedit(query, "➡️ Send User ID to check balance:\n\n/cancel to abort")

    elif data == "admin_broadcast":
        context.user_data['state'] = 'WAIT_BROADCAST_MSG'
        await sedit(
            query,
            "📢 **BROADCAST MESSAGE**\n\n"
            "Send ANYTHING to broadcast to all users — Text, Photo, Video, Voice note, etc.\n\n"
            "Whatever you send will be copied exactly as-is to every user.",
            InlineKeyboardMarkup([[colored_button("❌ Cancel", "admin_broadcast_cancel", style="danger")]])
        )

    elif data == "admin_broadcast_cancel":
        context.user_data['state'] = None
        await ans(query, "❌ Broadcast cancelled.")
        await refresh_admin_panel(context, query)

    elif data.startswith("ticket_reply_"):
        ticket_id = data.split("ticket_reply_", 1)[1]
        cursor.execute("SELECT user_id FROM tickets WHERE ticket_id = ?", (ticket_id,))
        trow = cursor.fetchone()
        if not trow:
            return
        context.user_data['state'] = 'WAIT_TICKET_REPLY'
        context.user_data['reply_ticket_id'] = ticket_id
        context.user_data['reply_user_id'] = trow[0]
        await ssend(context.bot, ADMIN_ID, f"✍️ **Send your reply now** for Ticket `{ticket_id}`:")

    else:
        logging.warning(f"Unhandled admin callback: {data}")


async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Wrapper: connection hamesha close hoti hai, query ek hi baar answer hota hai,
    aur koi error aaye to admin ko reason dikhta hai."""
    query = update.callback_query
    if query.from_user.id != ADMIN_ID:
        await ans(query)
        return
    conn = db()
    try:
        await _admin_dispatch(update, context, query, conn)
    except Exception as e:
        logging.exception("Admin callback failed")
        try:
            await context.bot.send_message(chat_id=ADMIN_ID, text=f"⚠️ Admin action failed:\n{type(e).__name__}: {str(e)[:300]}")
        except Exception:
            pass
    finally:
        conn.close()
        await ans(query)


# ============================================================
# TEXT INPUT HANDLER
# ============================================================
async def handle_text_inputs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or not update.message:
        return
    user_id = update.effective_user.id
    state = context.user_data.get('state')
    if not state:
        return

    if is_bot_maintenance() and user_id != ADMIN_ID:
        context.user_data['state'] = None
        await send_maintenance_notice(update)
        return

    try:
        await _handle_state(update, context, user_id, state)
    except Exception as e:
        logging.exception("Text input handler failed")
        context.user_data['state'] = None
        try:
            if user_id == ADMIN_ID:
                await update.message.reply_text(f"⚠️ Error: {type(e).__name__}: {str(e)[:300]}\n\nState reset. /admin se dobara try karo.")
            else:
                await update.message.reply_text("⚠️ Something went wrong. Please try again or send /start.")
        except Exception:
            pass


async def _handle_state(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, state: str):
    if state == 'WAIT_BROADCAST_MSG':
        if user_id != ADMIN_ID:
            return
        context.user_data['state'] = None
        conn = db()
        users = conn.execute("SELECT user_id FROM users").fetchall()
        conn.close()
        src_chat_id = update.effective_chat.id
        src_msg_id = update.message.message_id
        sent, failed = 0, 0
        await update.message.reply_text(f"📢 Starting broadcast to {len(users)} users... ⏳")
        for u in users:
            try:
                await context.bot.copy_message(chat_id=u[0], from_chat_id=src_chat_id, message_id=src_msg_id)
                sent += 1
            except Exception:
                failed += 1
            await asyncio.sleep(0.05)
        await reopen_admin_panel(update, context, f"✅ Broadcast Completed!\n\nSuccessful: {sent}\nFailed: {failed}")
        return

    if state == 'WAIT_RESTORE_ZIP':
        if user_id != ADMIN_ID:
            return
        doc = update.message.document
        if not doc:
            await update.message.reply_text("❌ Backup ZIP file document ke roop me bhejo.\n\n/cancel to abort")
            return
        if doc.file_size and doc.file_size > MAX_RESTORE_BYTES:
            await update.message.reply_text("❌ File bahut badi hai (max 20MB).")
            return
        await update.message.reply_text("⏳ Backup file check ho rahi hai...")
        try:
            tg_file = await doc.get_file()
            raw = bytes(await tg_file.download_as_bytearray())
            tables = await asyncio.to_thread(parse_backup_zip, raw)
        except zipfile.BadZipFile:
            await update.message.reply_text("❌ Ye valid ZIP file nahi hai. Sahi backup ZIP bhejo.")
            return
        except Exception as e:
            logging.exception("Restore parse failed")
            await update.message.reply_text(f"❌ Backup read nahi ho paya: {str(e)[:300]}")
            return

        context.user_data['restore_data'] = tables
        context.user_data['state'] = None
        counts = {t: len(v["rows"]) for t, v in tables.items()}
        confirm_kb = InlineKeyboardMarkup([
            [colored_button("✅ Confirm Restore", "admin_restore_confirm", style="success")],
            [colored_button("❌ Cancel", "admin_restore_cancel", style="danger")],
        ])
        await update.message.reply_text(
            "♻️ RESTORE PREVIEW\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{backup_summary_text(counts)}\n\n"
            "⚠️ Confirm karne par abhi ka data isse REPLACE ho jayega.\n"
            "(Restore se pehle ek safety backup aapko mil jayega.)",
            reply_markup=confirm_kb
        )
        return

    if state == 'WAIT_TICKET_MSG':
        ticket_id = context.user_data.get('open_ticket_id')
        context.user_data['state'] = None
        context.user_data['open_ticket_id'] = None
        if not ticket_id:
            await update.message.reply_text("❌ Ticket session expired. Please open a new ticket.")
            return
        user_obj = update.effective_user
        full_name = escape_markdown(user_obj.full_name) if user_obj.full_name else "N/A"
        uname = f"@{escape_markdown(user_obj.username)}" if user_obj.username else "N/A"
        header_text = (
            f"🎫 **NEW SUPPORT TICKET** 🎫\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🆔 **Ticket ID:** `{ticket_id}`\n"
            f"👤 **Name:** {full_name}\n"
            f"🏷️ **Username:** {uname}\n"
            f"🆔 **User ID:** `{user_id}`\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"👇 **Message:**"
        )
        try:
            await ssend(context.bot, ADMIN_ID, header_text)
            await context.bot.copy_message(chat_id=ADMIN_ID, from_chat_id=update.effective_chat.id, message_id=update.message.message_id)
            await ssend(
                context.bot, ADMIN_ID,
                f"💬 Tap below to reply to {full_name} on Ticket `{ticket_id}`:",
                InlineKeyboardMarkup([[colored_button("💬 Reply to Ticket", f"ticket_reply_{ticket_id}", style="primary")]])
            )
        except Exception as e:
            logging.error(f"Failed to forward ticket {ticket_id} to admin: {e}")
        await sreply(update.message, f"✅ Ticket `{ticket_id}` submitted! 🎫\n\nOur admin will reply here soon. 🙏")
        return

    if state == 'WAIT_TICKET_REPLY':
        if user_id != ADMIN_ID:
            return
        ticket_id = context.user_data.get('reply_ticket_id')
        target_user_id = context.user_data.get('reply_user_id')
        context.user_data['state'] = None
        context.user_data['reply_ticket_id'] = None
        context.user_data['reply_user_id'] = None
        if not ticket_id or not target_user_id:
            await update.message.reply_text("❌ Reply session expired.")
            return
        try:
            await ssend(context.bot, target_user_id, f"💬 **Support Reply — Ticket** `{ticket_id}` 💬")
            await context.bot.copy_message(chat_id=target_user_id, from_chat_id=update.effective_chat.id, message_id=update.message.message_id)
            await sreply(update.message, f"✅ Reply sent for Ticket `{ticket_id}`!")
        except Exception as e:
            await update.message.reply_text(f"❌ Failed to deliver reply: {e}")
        return

    if not update.message.text:
        return
    text = update.message.text.strip()

    if state == 'WAIT_DEPOSIT_AMT':
        amt = parse_amount(text)
        if amt is None or amt < MIN_DEPOSIT:
            await update.message.reply_text(f"❌ Invalid amount. Minimum deposit ₹{MIN_DEPOSIT:.0f}. Enter a number like 50.")
            return
        context.user_data['state'] = None
        ok, info = await raise_payment_qr(context, user_id, amt, 0.0, purpose='balance', label="Wallet Deposit")
        if not ok:
            if info == "UPI_NOT_SET":
                await update.message.reply_text("❌ Payments Not Set Up Yet!\n\nPlease contact admin.")
            else:
                await update.message.reply_text("❌ Payment Link Generation Failed. Please try again later.")
        return

    if user_id != ADMIN_ID:
        return

    conn = db()
    cursor = conn.cursor()
    try:
        if state == 'WAIT_DISCOUNT_CUSTOM':
            v = parse_amount(text.replace("%", "").strip(), allow_zero=True)
            if v is None or v > MAX_DISCOUNT:
                await update.message.reply_text(
                    f"❌ Invalid. 0 se {fmt_pct(MAX_DISCOUNT)} ke beech number bhejo (jaise 15 ya 12.5)."
                )
                return
            set_global_discount(v)
            context.user_data['state'] = None
            if v > 0:
                msg = f"✅ {fmt_pct(v)}% discount ab sabhi products pe sabko mil raha hai! 🏷️"
            else:
                msg = "✅ Discount removed."
            await reopen_admin_panel(update, context, msg)

        elif state == 'WAIT_PROD_EMOJI_ID':
            pid = context.user_data.get('emoji_pid')
            if not pid:
                context.user_data['state'] = None
                await update.message.reply_text("❌ Session expire ho gaya. /admin se dobara Set Emojis karo.")
                return
            cursor.execute("SELECT name FROM products WHERE pid = ?", (pid,))
            prow = cursor.fetchone()
            if not prow:
                context.user_data['state'] = None
                await update.message.reply_text("❌ Product nahi mila.")
                return

            if text.lower() == 'clear':
                new_val = ''
            else:
                new_val = None
                # 1) Seedha premium emoji bheja ho to uski ID nikal lo
                for ent in (update.message.entities or []):
                    cid = getattr(ent, "custom_emoji_id", None)
                    if ent.type == "custom_emoji" and cid:
                        new_val = str(cid)
                        break
                # 2) Warna text me ID number
                if not new_val and re.fullmatch(r"\d{5,25}", text):
                    new_val = text
                if not new_val:
                    await update.message.reply_text(
                        "❌ Invalid Emoji ID. Sirf number bhejo (jaise 6145292889913039900), "
                        "ya premium emoji bhejo, ya `clear` likho.\n\n/cancel to abort"
                    )
                    return

            cursor.execute("UPDATE products SET emoji_id = ? WHERE pid = ?", (new_val, pid))
            conn.commit()
            context.user_data['state'] = None
            context.user_data.pop('emoji_pid', None)
            if new_val:
                msg = f"✅ Emoji set for {escape_markdown(prow[0])}!\nShop me ab us product ke aage ye emoji dikhega."
            else:
                msg = f"✅ Emoji removed for {escape_markdown(prow[0])} (default emoji wapas)."
            await reopen_admin_panel(update, context, msg)

        elif state == 'WAIT_SUPPORT_UNAME':
            s_uname = text.replace("@", "").strip()
            if not re.fullmatch(r"[A-Za-z0-9_]{3,32}", s_uname):
                await update.message.reply_text("❌ Invalid username. Sirf letters/numbers/underscore (3-32).")
                return
            set_setting('support_username', s_uname)
            context.user_data['state'] = None
            await reopen_admin_panel(update, context, f"✅ Support username updated to `@{s_uname}`!")

        elif state == 'WAIT_PROD_NAME':
            names = parse_lines(text)
            if not names:
                await update.message.reply_text("❌ Koi naam nahi mila. Product names line by line bhejo.")
                return
            if len(names) > MAX_BULK_ITEMS:
                await update.message.reply_text(f"❌ Ek baar me max {MAX_BULK_ITEMS} products add ho sakte hain.")
                return
            too_long = [n for n in names if len(n) > 60]
            if too_long:
                await update.message.reply_text("❌ Naam 60 characters se chhota hona chahiye:\n" + "\n".join(too_long[:5]))
                return
            context.user_data['temp_prod_names'] = names
            context.user_data['state'] = 'WAIT_PROD_PID'
            await sreply(
                update.message,
                f"✅ **{len(names)} products** mile:\n\n{numbered_list(names)}\n\n"
                f"➡️ **Step 2/2:** Ab inke **PID** bhejo — line by line, isi order me (exactly {len(names)} lines):\n"
                f"`DRIP`\n`HG`\n`PATO`\n\n/cancel to abort"
            )

        elif state == 'WAIT_PROD_PID':
            names = context.user_data.get('temp_prod_names') or []
            if not names:
                context.user_data['state'] = None
                await update.message.reply_text("❌ Session expire ho gaya. /admin se dobara Add Product karo.")
                return
            raw_pids = parse_lines(text)
            if len(raw_pids) != len(names):
                await update.message.reply_text(
                    f"❌ {len(names)} PID chahiye, aapne {len(raw_pids)} bheje. Dobara bhejo (line by line, isi order me)."
                )
                return
            pids = []
            for i, rp in enumerate(raw_pids, 1):
                np_ = normalize_pid(rp)
                if not np_:
                    await update.message.reply_text(
                        f"❌ Line {i} ka PID invalid hai: {rp}\nSirf A-Z, 0-9, _ ya - allowed, max {MAX_PID_LEN} characters. Dobara bhejo."
                    )
                    return
                pids.append(np_)
            dups = sorted({x for x in pids if pids.count(x) > 1})
            if dups:
                await update.message.reply_text("❌ Duplicate PID mile: " + ", ".join(dups) + "\nHar product ka PID alag hona chahiye. Dobara bhejo.")
                return
            added, updated = 0, 0
            lines_out = []
            for name, pid in zip(names, pids):
                cursor.execute("SELECT 1 FROM products WHERE pid = ?", (pid,))
                existed = cursor.fetchone() is not None
                cursor.execute(
                    "INSERT INTO products (pid, name, category) VALUES (?, ?, '') "
                    "ON CONFLICT(pid) DO UPDATE SET name = excluded.name",
                    (pid, name)
                )
                if existed:
                    updated += 1
                else:
                    added += 1
                lines_out.append(f"• {escape_markdown(name)} → `{pid}`")
            conn.commit()
            context.user_data['state'] = None
            context.user_data.pop('temp_prod_names', None)
            msg = (
                f"✅ **Bulk Add Done!**\n\n➕ New: {added}\n♻️ Updated (PID pehle se tha): {updated}\n\n"
                + "\n".join(lines_out)
                + "\n\n🔀 Category assign karna aur ➕ Add Plan karna mat bhoolna."
            )
            await reopen_admin_panel(update, context, msg[:4000])

        elif state == 'WAIT_CATEGORY_NAME':
            cat_name = text.strip()
            if not cat_name or len(cat_name) > 40:
                await update.message.reply_text("❌ Category name 1-40 characters ka hona chahiye.")
                return
            cursor.execute("SELECT 1 FROM categories WHERE name = ?", (cat_name,))
            if cursor.fetchone():
                await update.message.reply_text("❌ Ye category pehle se exist karti hai. Dusra naam bhejo.")
                return
            cursor.execute("SELECT COALESCE(MAX(sort_order), -1) + 1 FROM categories")
            next_order = cursor.fetchone()[0]
            cursor.execute("INSERT INTO categories (name, sort_order) VALUES (?, ?)", (cat_name, next_order))
            conn.commit()
            context.user_data['state'] = None
            await reopen_admin_panel(update, context, f"✅ Category **{escape_markdown(cat_name)}** added! 📂")

        elif state == 'WAIT_PLAN_DURATION':
            durs = parse_lines(text)
            if not durs:
                await update.message.reply_text("❌ Koi duration nahi mili. Line by line bhejo.")
                return
            if len(durs) > MAX_BULK_ITEMS:
                await update.message.reply_text(f"❌ Ek baar me max {MAX_BULK_ITEMS} plans add ho sakte hain.")
                return
            if any(len(d) > 30 for d in durs):
                await update.message.reply_text("❌ Har duration 1-30 characters ki honi chahiye. Dobara bhejo.")
                return
            dup_in_list = sorted({d for d in durs if durs.count(d) > 1})
            if dup_in_list:
                await update.message.reply_text("❌ List me duplicate duration: " + ", ".join(dup_in_list))
                return
            pid = context.user_data.get('temp_pid')
            cursor.execute("SELECT duration FROM plans WHERE product_pid = ?", (pid,))
            existing = {r[0] for r in cursor.fetchall()}
            clash = [d for d in durs if d in existing]
            if clash:
                await update.message.reply_text("❌ Ye durations is product me pehle se hain: " + ", ".join(clash) + "\nList se hatake dobara bhejo.")
                return
            context.user_data['temp_plan_durs'] = durs
            context.user_data['state'] = 'WAIT_PLAN_REMOTE_DUR'
            await sreply(
                update.message,
                f"✅ **{len(durs)} durations** mile:\n\n{numbered_list(durs)}\n\n"
                f"➡️ **Step 2/4:** Ab **Remote API duration code** bhejo — line by line, isi order me (exactly {len(durs)} lines):\n"
                f"`1h`\n`3d`\n`7d`\n\n/cancel to abort"
            )

        elif state == 'WAIT_PLAN_REMOTE_DUR':
            durs = context.user_data.get('temp_plan_durs') or []
            if not durs:
                context.user_data['state'] = None
                await update.message.reply_text("❌ Session expire ho gaya. /admin se dobara Add Plan karo.")
                return
            remotes = parse_lines(text)
            if len(remotes) != len(durs):
                await update.message.reply_text(f"❌ {len(durs)} remote codes chahiye, aapne {len(remotes)} bheje. Dobara bhejo.")
                return
            context.user_data['temp_plan_remotes'] = remotes
            context.user_data['state'] = 'WAIT_PLAN_PRICE'
            await sreply(
                update.message,
                f"➡️ **Step 3/4:** Ab **Normal Price (₹)** bhejo — line by line, isi order me (exactly {len(durs)} lines):\n\n"
                f"{numbered_list(durs)}\n\n`50`\n`120`\n`300`\n\n/cancel to abort"
            )

        elif state == 'WAIT_PLAN_PRICE':
            durs = context.user_data.get('temp_plan_durs') or []
            if not durs:
                context.user_data['state'] = None
                await update.message.reply_text("❌ Session expire ho gaya. /admin se dobara Add Plan karo.")
                return
            raw = parse_lines(text)
            if len(raw) != len(durs):
                await update.message.reply_text(f"❌ {len(durs)} prices chahiye, aapne {len(raw)} bheje. Dobara bhejo.")
                return
            prices = []
            for i, r in enumerate(raw, 1):
                v = parse_amount(r)
                if v is None:
                    await update.message.reply_text(f"❌ Line {i} ka price invalid hai: {r}\nSirf number bhejo, jaise 50. Dobara bhejo.")
                    return
                prices.append(v)
            context.user_data['temp_plan_prices'] = prices
            context.user_data['state'] = 'WAIT_PLAN_RESELLER_PRICE_INIT'
            await sreply(
                update.message,
                f"➡️ **Step 4/4:** Ab **Reseller Price (₹)** bhejo — line by line, isi order me (exactly {len(durs)} lines):\n\n"
                f"{numbered_list(durs)}\n\n`40`\n`100`\n`250`\n\n/cancel to abort"
            )

        elif state == 'WAIT_PLAN_RESELLER_PRICE_INIT':
            durs = context.user_data.get('temp_plan_durs') or []
            remotes = context.user_data.get('temp_plan_remotes') or []
            prices = context.user_data.get('temp_plan_prices') or []
            pid = context.user_data.get('temp_pid')
            if not pid or not durs or len(remotes) != len(durs) or len(prices) != len(durs):
                context.user_data['state'] = None
                await update.message.reply_text("❌ Session expire ho gaya. /admin se dobara Add Plan karo.")
                return
            raw = parse_lines(text)
            if len(raw) != len(durs):
                await update.message.reply_text(f"❌ {len(durs)} reseller prices chahiye, aapne {len(raw)} bheje. Dobara bhejo.")
                return
            r_prices = []
            for i, r in enumerate(raw, 1):
                v = parse_amount(r)
                if v is None:
                    await update.message.reply_text(f"❌ Line {i} ka price invalid hai: {r}\nSirf number bhejo, jaise 40. Dobara bhejo.")
                    return
                r_prices.append(v)
            cursor.executemany(
                "INSERT INTO plans (product_pid, duration, remote_duration, price, reseller_price, button_style) VALUES (?, ?, ?, ?, ?, 'primary')",
                [(pid, d, rm, pr, rp) for d, rm, pr, rp in zip(durs, remotes, prices, r_prices)]
            )
            conn.commit()
            context.user_data['state'] = None
            for k in ('temp_plan_durs', 'temp_plan_remotes', 'temp_plan_prices'):
                context.user_data.pop(k, None)
            out = [
                f"{i}. {escape_markdown(d)} | remote `{rm}` | ₹{pr:.2f} | reseller ₹{rp:.2f}"
                for i, (d, rm, pr, rp) in enumerate(zip(durs, remotes, prices, r_prices), 1)
            ]
            await reopen_admin_panel(update, context, (f"✅ **{len(durs)} plans added!**\n\n" + "\n".join(out))[:4000])

        elif state == 'WAIT_NEW_PID':
            old = context.user_data.get('chgpid_old')
            if not old:
                context.user_data['state'] = None
                await update.message.reply_text("❌ Session expire ho gaya. /admin se dobara Change PID karo.")
                return
            new = normalize_pid(text)
            if not new:
                await update.message.reply_text(f"❌ Invalid PID. Sirf A-Z, 0-9, _ ya - allowed, max {MAX_PID_LEN} characters. Dobara bhejo.")
                return
            if new == old:
                await update.message.reply_text("❌ Ye to wahi PID hai. Naya PID bhejo.")
                return
            cursor.execute("SELECT 1 FROM products WHERE pid = ?", (new,))
            if cursor.fetchone():
                await update.message.reply_text("❌ Ye PID kisi aur product ka hai. Dusra PID bhejo.")
                return
            try:
                rename_pids(cursor, {old: new})
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            context.user_data['state'] = None
            context.user_data.pop('chgpid_old', None)
            await reopen_admin_panel(
                update, context,
                f"✅ PID changed: `{old}` → `{new}`\n\nPlans aur keys bhi update ho gaye. Purane deep links ab kaam nahi karenge."
            )

        elif state == 'WAIT_BULK_PID':
            order = context.user_data.get('bulkpid_order') or []
            if not order:
                context.user_data['state'] = None
                await update.message.reply_text("❌ Session expire ho gaya. /admin se dobara Change PID karo.")
                return
            lines = parse_lines(text)
            if len(lines) != len(order):
                await update.message.reply_text(f"❌ {len(order)} lines chahiye, aapne {len(lines)} bheji. Dobara bhejo (na badalna ho to `-` likho).")
                return
            mapping, final = {}, []
            for i, (old, ln) in enumerate(zip(order, lines), 1):
                if ln == "-":
                    final.append(old)
                    continue
                n = normalize_pid(ln)
                if not n:
                    await update.message.reply_text(f"❌ Line {i} ka PID invalid hai: {ln}\nSirf A-Z, 0-9, _ ya - allowed, max {MAX_PID_LEN}. Dobara bhejo.")
                    return
                final.append(n)
                if n != old:
                    mapping[old] = n
            if len(set(final)) != len(final):
                await update.message.reply_text("❌ Duplicate PID mile. Har product ka PID alag hona chahiye. Dobara bhejo.")
                return
            cursor.execute("SELECT pid FROM products")
            outside = {r[0] for r in cursor.fetchall()} - set(order)
            clash = [n for n in final if n in outside]
            if clash:
                await update.message.reply_text("❌ Ye PID kisi aur product ke hain: " + ", ".join(clash))
                return
            if not mapping:
                context.user_data['state'] = None
                await reopen_admin_panel(update, context, "ℹ️ Koi PID change nahi hua.")
                return
            try:
                count = rename_pids(cursor, mapping)
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            context.user_data['state'] = None
            context.user_data.pop('bulkpid_order', None)
            out = "\n".join(f"• `{o}` → `{n}`" for o, n in mapping.items())
            await reopen_admin_panel(
                update, context,
                (f"✅ **{count} PID changed!**\n\n{out}\n\nPlans aur keys bhi update ho gaye. Purane deep links ab kaam nahi karenge.")[:4000]
            )

        elif state == 'WAIT_KEYS_INPUT':
            pid = context.user_data.get('key_pid')
            dur = context.user_data.get('key_dur')
            if not pid or not dur:
                context.user_data['state'] = None
                await update.message.reply_text("❌ Session expire ho gaya. /admin se dobara Add Keys karo.")
                return
            keys_list = [k.strip() for k in text.split("\n") if k.strip()]
            if not keys_list:
                await update.message.reply_text("❌ Koi key nahi mili. Keys line by line bhejo.")
                return
            cursor.executemany("INSERT INTO keys (product_pid, duration, key_value) VALUES (?, ?, ?)", [(pid, dur, k) for k in keys_list])
            conn.commit()
            context.user_data['state'] = None
            await reopen_admin_panel(update, context, f"✅ Added {len(keys_list)} keys successfully!")

        elif state == 'WAIT_ZAPUPI_KEY':
            set_setting('zapupi_key', text)
            context.user_data['state'] = None
            await reopen_admin_panel(update, context, "✅ ZapUPI Key updated!")

        elif state == 'WAIT_STORE_API_KEY':
            set_setting('store_api_key', text)
            context.user_data['state'] = None
            await reopen_admin_panel(update, context, "✅ Store API Key set!")

        elif state == 'WAIT_PLAN_RESELLER_PRICE':
            r_price = parse_amount(text)
            if r_price is None:
                await update.message.reply_text("❌ Invalid amount.")
                return
            plan_id = context.user_data.get('edit_plan_id')
            cursor.execute("UPDATE plans SET reseller_price = ? WHERE id = ?", (r_price, plan_id))
            conn.commit()
            context.user_data['state'] = None
            await reopen_admin_panel(update, context, "✅ Plan Reseller Price updated!")

        elif state == 'WAIT_RESELLER_UPGRADE_PRICE':
            price = parse_amount(text)
            if price is None:
                await update.message.reply_text("❌ Invalid price.")
                return
            set_setting('reseller_upgrade_price', str(price))
            context.user_data['state'] = None
            await reopen_admin_panel(update, context, f"✅ Reseller Upgrade Price set to ₹{price:.2f}!")

        elif state in ('WAIT_ADD_RESELLER_ID', 'WAIT_REM_RESELLER_ID'):
            try:
                uid = int(text)
            except ValueError:
                await update.message.reply_text("❌ Invalid User ID.")
                return
            flag = 1 if state == 'WAIT_ADD_RESELLER_ID' else 0
            cursor.execute("UPDATE users SET is_reseller = ? WHERE user_id = ?", (flag, uid))
            found = cursor.rowcount > 0
            conn.commit()
            context.user_data['state'] = None
            if not found:
                await reopen_admin_panel(update, context, f"❌ User `{uid}` database me nahi mila (usne bot /start nahi kiya).")
            else:
                word = "promoted to" if flag else "demoted from"
                if flag:
                    api_key = ensure_reseller_api_key(uid)
                    await reopen_admin_panel(update, context, f"✅ User `{uid}` promoted to Reseller!\n\n🔑 API Key: `{api_key}`\n📚 Docs: /api/docs")
                else:
                    conn2 = db()
                    conn2.execute("UPDATE reseller_api_keys SET active = 0 WHERE user_id = ?", (uid,))
                    conn2.commit(); conn2.close()
                    await reopen_admin_panel(update, context, f"✅ User `{uid}` demoted from Reseller!\n🔒 API key disabled.")

        elif state == 'WAIT_NEW_PLAN_PRICE':
            price = parse_amount(text)
            if price is None:
                await update.message.reply_text("❌ Invalid price.")
                return
            plan_id = context.user_data.get('chg_plan_id')
            cursor.execute("UPDATE plans SET price = ? WHERE id = ?", (price, plan_id))
            conn.commit()
            context.user_data['state'] = None
            await reopen_admin_panel(update, context, "✅ Plan Normal Price updated!")

        elif state == 'WAIT_NEW_PROD_NAME':
            pid = context.user_data.get('rename_pid')
            cursor.execute("UPDATE products SET name = ? WHERE pid = ?", (text, pid))
            conn.commit()
            context.user_data['state'] = None
            await reopen_admin_panel(update, context, "✅ Product renamed successfully!")

        elif state == 'WAIT_HOW_VIDEO_URL':
            if text.lower() == 'clear':
                set_setting('how_to_use_video', '')
                context.user_data['state'] = None
                await reopen_admin_panel(update, context, "✅ How-To-Use video removed!")
            else:
                set_setting('how_to_use_video', text)
                context.user_data['state'] = None
                await reopen_admin_panel(update, context, "✅ How-To-Use video URL updated!")

        elif state == 'WAIT_GROUP_LINK':
            pid = context.user_data.get('grplink_pid')
            value = '' if text.lower() == 'clear' else text
            cursor.execute("UPDATE products SET group_link = ? WHERE pid = ?", (value, pid))
            conn.commit()
            context.user_data['state'] = None
            await reopen_admin_panel(update, context, "✅ Group/Updates link updated!")

        elif state == 'WAIT_PROD_VIDEO_LINK':
            pid = context.user_data.get('prodvideo_pid')
            value = '' if text.lower() == 'clear' else text
            cursor.execute("UPDATE products SET demo_video = ? WHERE pid = ?", (value, pid))
            conn.commit()
            context.user_data['state'] = None
            await reopen_admin_panel(update, context, "✅ Demo video link updated!")

        elif state in ('WAIT_ADD_BAL_INPUT', 'WAIT_REM_BAL_INPUT'):
            parts = text.split()
            if len(parts) != 2:
                await sreply(update.message, "❌ Invalid format. Use: `<user_id> <amount>`")
                return
            try:
                uid = int(parts[0])
            except ValueError:
                await update.message.reply_text("❌ Invalid User ID.")
                return
            amt = parse_amount(parts[1])
            if amt is None:
                await update.message.reply_text("❌ Invalid Amount.")
                return
            sign = 1 if state == 'WAIT_ADD_BAL_INPUT' else -1
            cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (sign * amt, uid))
            found = cursor.rowcount > 0
            conn.commit()
            context.user_data['state'] = None
            if not found:
                await reopen_admin_panel(update, context, f"❌ User `{uid}` database me nahi mila.")
            elif sign > 0:
                await reopen_admin_panel(update, context, f"✅ ₹{amt:.2f} added to user `{uid}`'s balance!")
            else:
                await reopen_admin_panel(update, context, f"✅ ₹{amt:.2f} removed from user `{uid}`'s balance!")

        elif state == 'WAIT_CUSTOM_PRICE_INPUT':
            parts = text.split()
            if len(parts) != 2:
                await sreply(update.message, "❌ Invalid format. Use: `<user_id> <price>`")
                return
            try:
                uid = int(parts[0])
            except ValueError:
                await update.message.reply_text("❌ Invalid User ID.")
                return
            price = parse_amount(parts[1], allow_zero=True)
            if price is None:
                await update.message.reply_text("❌ Invalid Price.")
                return
            plan_id = context.user_data.get('custprice_plan_id')
            cursor.execute("INSERT OR REPLACE INTO custom_prices (user_id, plan_id, price) VALUES (?, ?, ?)", (uid, plan_id, price))
            conn.commit()
            context.user_data['state'] = None
            await reopen_admin_panel(update, context, f"✅ Custom price ₹{price:.2f} set for user `{uid}`!")

        elif state == 'WAIT_CHECK_BAL_ID':
            try:
                uid = int(text)
            except ValueError:
                await update.message.reply_text("❌ Invalid User ID.")
                return
            cursor.execute("SELECT full_name, username, balance, is_reseller FROM users WHERE user_id = ?", (uid,))
            row = cursor.fetchone()
            context.user_data['state'] = None
            if not row:
                await update.message.reply_text("❌ User not found.")
            else:
                name = escape_markdown(row[0]) if row[0] else "N/A"
                uname = f"@{escape_markdown(row[1])}" if row[1] else "N/A"
                bal = row[2] if row[2] is not None else 0.0
                acc = "🌟 Reseller" if row[3] else "👤 User"
                await sreply(
                    update.message,
                    f"🔍 **USER BALANCE INFO** 🔍\n\n"
                    f"👤 **Name:** {name}\n"
                    f"🏷️ **Username:** {uname}\n"
                    f"🆔 **User ID:** `{uid}`\n"
                    f"💰 **Balance:** ₹{bal:.2f}\n"
                    f"🏷️ **Account Type:** {acc}"
                )
    finally:
        conn.close()


# ============================================================
# RESELLER PRODUCT BUY API + FLASK DOCUMENTATION
# ============================================================
API_APP = Flask(__name__) if Flask else None


def _api_auth():
    key = request.headers.get("X-API-Key", "").strip() if request else ""
    if not key and request:
        auth = request.headers.get("Authorization", "").strip()
        if auth.lower().startswith("bearer "):
            key = auth[7:].strip()
    reseller = get_reseller_by_api_key(key)
    if not reseller:
        return None, (jsonify({"success": False, "error": "Invalid or inactive API key"}), 401)
    if not int(reseller[4] or 0):
        return None, (jsonify({"success": False, "error": "Reseller account is inactive"}), 403)
    return reseller, None


def _api_plan_json(row):
    plan_id, pid, product_name, duration, remote_duration, price, reseller_price, stock = row
    return {
        "plan_id": plan_id,
        "pid": pid,
        "product": product_name,
        "duration": duration,
        "remote_duration": remote_duration,
        "price": round(float(reseller_price if reseller_price is not None else price or 0), 2),
        "stock": int(stock or 0),
    }


def _api_find_plan(pid, duration):
    conn = db()
    try:
        cur = conn.cursor()
        cur.execute(
            """SELECT p.id, p.product_pid, pr.name, p.duration, p.remote_duration,
                      p.price, p.reseller_price,
                      (SELECT COUNT(*) FROM keys k WHERE k.product_pid=p.product_pid AND k.duration=p.duration)
               FROM plans p JOIN products pr ON pr.pid=p.product_pid
               WHERE p.product_pid=? AND (p.duration=? OR p.remote_duration=?)
               ORDER BY CASE WHEN p.duration=? THEN 0 ELSE 1 END, p.id LIMIT 1""",
            (pid, duration, duration, duration),
        )
        return cur.fetchone()
    finally:
        conn.close()


def _api_purchase(user_id, pid, duration):
    plan = _api_find_plan(pid, duration)
    if not plan:
        return {"success": False, "error": "Product/duration not found"}, 404

    plan_id, product_pid, product_name, plan_duration, remote_duration, normal_price, reseller_price, _stock = plan
    price = float(reseller_price if reseller_price is not None else normal_price or 0)
    price = apply_discount(price)

    conn = db()
    try:
        cur = conn.cursor()
        cur.execute("SELECT balance, is_reseller FROM users WHERE user_id=?", (user_id,))
        user = cur.fetchone()
        if not user or not int(user[1] or 0):
            return {"success": False, "error": "Reseller account not found/inactive"}, 403
        balance = float(user[0] or 0)
        if balance < price:
            return {"success": False, "error": "Insufficient balance", "balance": round(balance,2), "required": round(price,2)}, 402

        # Prefer locally stocked keys. Atomic balance deduction + key removal.
        cur.execute("SELECT id, key_value FROM keys WHERE product_pid=? AND duration=? ORDER BY id LIMIT 1", (product_pid, plan_duration))
        key_row = cur.fetchone()
        if key_row:
            key_id, key_value = key_row
            cur.execute("UPDATE users SET balance=balance-? WHERE user_id=? AND balance>=?", (price, user_id, price))
            if cur.rowcount != 1:
                conn.rollback()
                return {"success": False, "error": "Balance changed; retry"}, 409
            cur.execute("DELETE FROM keys WHERE id=?", (key_id,))
            if cur.rowcount != 1:
                conn.rollback()
                return {"success": False, "error": "Stock changed; retry"}, 409
            purchase_type = "API/LocalStock"
        else:
            conn.close()
            ok, result = call_reseller_api(product_pid, remote_duration)
            if not ok:
                return {"success": False, "error": str(result)}, 502
            key_value = str(result)
            conn = db()
            cur = conn.cursor()
            cur.execute("UPDATE users SET balance=balance-? WHERE user_id=? AND balance>=?", (price, user_id, price))
            if cur.rowcount != 1:
                conn.rollback()
                return {"success": False, "error": "Insufficient balance after API fulfillment; key not charged"}, 402
            purchase_type = "API/RemoteStock"

        cur.execute(
            "INSERT INTO history (user_id, item_name, key_value, price) VALUES (?, ?, ?, ?)",
            (user_id, f"{product_name} ({plan_duration}) [Reseller API]", key_value, price),
        )
        cur.execute("UPDATE users SET has_purchased=1 WHERE user_id=?", (user_id,))
        conn.commit()
        new_balance = balance - price
        return {
            "success": True,
            "product": product_name,
            "pid": product_pid,
            "duration": plan_duration,
            "key": key_value,
            "price": round(price,2),
            "balance": round(new_balance,2),
            "purchase_type": purchase_type,
        }, 200
    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        logging.exception("Reseller API purchase failed")
        return {"success": False, "error": "Internal server error"}, 500
    finally:
        try:
            conn.close()
        except Exception:
            pass


if API_APP:
    @API_APP.get("/")
    def api_home():
        return Response("<meta http-equiv='refresh' content='0;url=/api/docs'>", mimetype="text/html")

    @API_APP.get("/api/docs")
    @API_APP.get("/docs")
    def api_docs():
        html = """<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>
<title>Reseller Product Buy API</title><style>body{font-family:Arial,sans-serif;background:#0f1115;color:#eee;max-width:900px;margin:auto;padding:24px}code,pre{background:#171a21;padding:12px;border-radius:8px;display:block;overflow:auto}h1{color:#7dd3fc}h2{margin-top:28px}table{width:100%;border-collapse:collapse}td,th{padding:9px;border-bottom:1px solid #333;text-align:left}</style></head><body>
<h1>Reseller Product Buy API</h1><p>Use your reseller API key to list products and purchase a product by PID + duration. Responses are JSON.</p>
<h2>Authentication</h2><pre>X-API-Key: rk_your_reseller_key</pre><p>Bearer authentication is also supported: <code>Authorization: Bearer rk_your_reseller_key</code></p>
<h2>GET /api/products</h2><p>Returns all active products/plans and reseller prices.</p><pre>curl -H "X-API-Key: rk_your_reseller_key" https://YOUR-DOMAIN/api/products</pre>
<h2>POST /api/buy</h2><p>Buys one key. The reseller wallet is charged automatically. Local stock is used first; if empty, the configured upstream reseller API is used.</p><pre>curl -X POST https://YOUR-DOMAIN/api/buy \
-H "X-API-Key: rk_your_reseller_key" -H "Content-Type: application/json" \
-d '{"pid":"GAME001","duration":"30 Days"}'</pre>
<h2>POST /api/buy fields</h2><table><tr><th>Field</th><th>Required</th><th>Description</th></tr><tr><td>pid</td><td>Yes</td><td>Product PID</td></tr><tr><td>duration</td><td>Yes</td><td>Plan duration, e.g. 1 Day / 7 Days / 30 Days</td></tr></table>
<h2>GET /api/me</h2><pre>curl -H "X-API-Key: rk_your_reseller_key" https://YOUR-DOMAIN/api/me</pre>
<h2>Responses</h2><pre>{"success":true,"product":"Example","pid":"GAME001","duration":"30 Days","key":"YOUR-KEY","price":10.0,"balance":90.0}</pre>
<p>Keep the API key private. Never expose it in frontend JavaScript or public repositories.</p></body></html>"""
        return Response(html, mimetype="text/html")

    @API_APP.get("/api/me")
    def api_me():
        reseller, err = _api_auth()
        if err: return err
        return jsonify({"success": True, "user_id": reseller[0], "username": reseller[1], "name": reseller[2], "balance": round(float(reseller[3] or 0),2), "is_reseller": True})

    @API_APP.get("/api/products")
    def api_products():
        reseller, err = _api_auth()
        if err: return err
        conn = db()
        try:
            cur = conn.cursor()
            cur.execute("""SELECT p.id,p.product_pid,pr.name,p.duration,p.remote_duration,p.price,p.reseller_price,
                          (SELECT COUNT(*) FROM keys k WHERE k.product_pid=p.product_pid AND k.duration=p.duration)
                          FROM plans p JOIN products pr ON pr.pid=p.product_pid ORDER BY pr.name,p.id""")
            rows = cur.fetchall()
            return jsonify({"success": True, "products": [_api_plan_json(r) for r in rows], "count": len(rows)})
        finally:
            conn.close()

    @API_APP.post("/api/buy")
    def api_buy():
        reseller, err = _api_auth()
        if err: return err
        data = request.get_json(silent=True) or request.form.to_dict()
        pid = str(data.get("pid") or data.get("product_id") or "").strip()
        duration = str(data.get("duration") or data.get("plan") or data.get("sku") or "").strip()
        if not pid or not duration:
            return jsonify({"success": False, "error": "pid and duration are required"}), 400
        result, status = _api_purchase(reseller[0], pid, duration)
        return jsonify(result), status

    @API_APP.get("/api/health")
    def api_health():
        return jsonify({"success": True, "service": "reseller-product-api"})


def start_api_server():
    if not API_APP:
        logging.error("Flask is not installed. Install Flask to enable the reseller API/documentation server.")
        return
    try:
        logging.info("Reseller API starting on %s:%s", API_HOST, API_PORT)
        if waitress_serve is None:
            raise RuntimeError("Waitress is missing. Install requirements.txt")
        waitress_serve(API_APP, host=API_HOST, port=API_PORT, threads=8)
    except Exception:
        logging.exception("Reseller API server stopped")


def start_api_server_thread():
    if API_APP:
        t = threading.Thread(target=start_api_server, name="reseller-api", daemon=True)
        t.start()


# ============================================================
# GLOBAL ERROR HANDLER
# ============================================================
_LAST_ERR_ALERT = {}


async def global_error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    err = context.error

    # Conflict (2 instances chal rahe hain) ko admin/user ko spam nahi karna
    if isinstance(err, Conflict):
        logging.warning("Conflict: koi dusra bot instance bhi chal raha hai (same token). Usse band karo.")
        return

    logging.error(f"Unhandled exception: {err}", exc_info=err)

    # Admin ko asli error dikhao (60 sec me same error sirf ek baar) - debugging aasan
    try:
        err_txt = f"{type(err).__name__}: {str(err)[:300]}"
        now = time.time()
        if now - _LAST_ERR_ALERT.get(err_txt, 0) > 60:
            _LAST_ERR_ALERT[err_txt] = now
            await context.bot.send_message(chat_id=ADMIN_ID, text=f"⚠️ Bot Error:\n{err_txt}")
    except Exception:
        pass

    try:
        if isinstance(update, Update) and update.effective_chat:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="⚠️ Something went wrong. Please try again or send /start."
            )
    except Exception:
        pass


# ============================================================
# SINGLE INSTANCE LOCK (same machine pe double run rokta hai)
# ============================================================
_LOCK_FH = None


def ensure_single_instance():
    global _LOCK_FH
    try:
        import fcntl
    except ImportError:
        return  # Windows pe fcntl nahi hota
    _LOCK_FH = open("surajbot.lock", "w")
    try:
        fcntl.flock(_LOCK_FH, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        raise SystemExit("Bot pehle se chal raha hai. Purana instance band karo.")


# ============================================================
# RESELLER API KEY COMMAND
# ============================================================
async def myapi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    user = get_user(uid, update.effective_user.username, update.effective_user.full_name)
    if not user or not int(user[4] or 0):
        await update.message.reply_text("❌ Ye command sirf active resellers ke liye hai.")
        return
    key = ensure_reseller_api_key(uid)
    await update.message.reply_text(
        "🔑 Your Reseller API Key\n\n"
        f"{key}\n\n"
        "API Docs: /api/docs\n"
        "Keep this key private."
    )


# ============================================================
# ENTRYPOINT
# ============================================================
def main():
    if not BOT_TOKEN:
        raise SystemExit(
            "BOT_TOKEN set nahi hai. BotFather se naya token lo aur env variable BOT_TOKEN me daalo "
            "(sath me STORE_API_KEY aur MASTER_KEY bhi)."
        )

    ensure_single_instance()
    start_api_server_thread()

    app = Application.builder().token(BOT_TOKEN).concurrent_updates(True).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CommandHandler("cancel", cancel_cmd))
    app.add_handler(CommandHandler("myapi", myapi))

    admin_pattern = (
        r"^(admin_|del_prod_|del_plan_|delplanprod_|add_plan_prod_|key_prod_|key_plan_|"
        r"toggle_maint_|grplink_prod_|resprod_|set_plan_reseller_|chgprod_|chg_price_|rename_prod_|"
        r"prodvideo_prod_|custprice_prod_|custprice_plan_|remcustprice_prod_|"
        r"remcustprice_plan_|remcustprice_del_|remkeyprod_|remkeydur_|remkeydel_|"
        r"ticket_reply_|del_category_|assigncat_prod_|assigncat_set_|"
        r"catmove_up_|catmove_down_|style_cat_|style_prod_|style_plan_|chgpid_|emojiprod_)"
    )
    app.add_handler(CallbackQueryHandler(admin_callback, pattern=admin_pattern))
    app.add_handler(CallbackQueryHandler(user_callback))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_text_inputs))
    app.add_error_handler(global_error_handler)

    logging.info("Bot started, polling for updates...")
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == "__main__":
    if not BOT_TOKEN:
        raise SystemExit("BOT_TOKEN environment variable is required. Set it in Railway Variables.")
    main()
