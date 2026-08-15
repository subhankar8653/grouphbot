#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════╗
║   🛡️  GUARDIAN GROUP PROTECTION BOT  v10.0        ║
║   ⚡  MongoDB Persistent Database                ║
║   🔗  Advanced Link Detection                    ║
║   🕵️  Hidden Link Detection                     ║
║   ✍️  Stylish Font Detection                    ║
║   ✅  Linked Channel Forwards Allowed            ║
║   👑  Immortal Users System                      ║
║   🗑️  Sticker/Media Auto Delete                 ║
║   📝  Custom Blacklist & Whitelist               ║
║   🌊  Anti-Flood / Anti-Raid                     ║
║   🎭  Captcha Verification                       ║
║   💀  FBan / Global Ban System                   ║
╚══════════════════════════════════════════════════╝

  NOTE: this header is a developer-only code comment.
  It is never sent to Telegram — it does not affect
  bot UI, styling, or anything users/admins see.
"""

import re, os, asyncio, time, random, string, json, html
from datetime import datetime, timedelta, time as dtime
from telegram import Update, ChatPermissions, ChatMember, InlineKeyboardButton, InlineKeyboardMarkup, ForceReply
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from threading import Thread
from flask import Flask
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from telegram.error import RetryAfter, Forbidden, BadRequest, TimedOut, NetworkError
import aiohttp

# ═══════════════════════════════════════════════════════════
#  CONFIG — Railway Environment Variables
# ═══════════════════════════════════════════════════════════
BOT_TOKEN        = os.environ.get("BOT_TOKEN", "")
OWNER_ID         = int(os.environ.get("OWNER_ID", "0"))
MONGO_URL        = os.environ.get("MONGO_URL", "mongodb://localhost:27017")

if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN environment variable not set!")
if not OWNER_ID:
    raise ValueError("❌ OWNER_ID environment variable not set!")

# ═══════════════════════════════════════════════════════════
#  DESIGN CONSTANTS — Premium Message Templates
# ═══════════════════════════════════════════════════════════

# Top-level decorative borders
BORDER_TOP    = "╔" + "═" * 40 + "╗"
BORDER_MID    = "╠" + "═" * 40 + "╣"
BORDER_BOT    = "╚" + "═" * 40 + "╝"
BORDER_LINE   = "║  "
THIN_DIV      = "┄" * 42
DASH_DIV      = "─" * 42

# Status icons
ICON_ON       = "🟢"
ICON_OFF      = "🔴"
ICON_WARN     = "⚠️"
ICON_SHIELD   = "🛡️"
ICON_CROWN    = "👑"
ICON_LOCK     = "🔐"
ICON_CHECK    = "✅"
ICON_CROSS    = "❌"
ICON_FIRE     = "🔥"
ICON_STAR     = "⭐"
ICON_ROBOT    = "🤖"
ICON_CHART    = "📊"
ICON_GEAR     = "⚙️"
ICON_SWORD    = "⚔️"
ICON_BOLT     = "⚡"
ICON_DIAMOND  = "💎"

# ═══════════════════════════════════════════════════════════
#  WARNING MESSAGES — Redesigned
# ═══════════════════════════════════════════════════════════
WARN_MSG = {
    1: (
        "🟡 *𝗪𝗔𝗥𝗡𝗜𝗡𝗚 𝟭/𝟰*\n"
        "──────────────\n"
        "Rule violation detected.\n"
        "⏱ Muted for *35 seconds*\n\n"
        "_Please be careful next time._"
    ),
    2: (
        "🟠 *𝗪𝗔𝗥𝗡𝗜𝗡𝗚 𝟮/𝟰*\n"
        "──────────────\n"
        "Another rule was broken.\n"
        "⏱ Muted for *60 seconds*\n\n"
        "_Only 2 chances left._"
    ),
    3: (
        "🔴 *𝗪𝗔𝗥𝗡𝗜𝗡𝗚 𝟯/𝟰 — 𝗟𝗔𝗦𝗧 𝗖𝗛𝗔𝗡𝗖𝗘*\n"
        "──────────────\n"
        "⚡ Next violation = *1 week mute in this group.*\n"
        "⏱ Muted for *120 seconds*\n\n"
        "_This is your final warning._"
    ),
    4: (
        "💀 *𝗪𝗔𝗥𝗡𝗜𝗡𝗚 𝟰/𝟰 — 𝗠𝗔𝗫 𝗥𝗘𝗔𝗖𝗛𝗘𝗗*\n"
        "──────────────\n"
        "🗓 *1 week* mute — applied in *this group*\n"
        "🔐 Only an admin can lift it.\n\n"
        "_The limit was reached._"
    ),
}

VIOLATION_MSG = {
    "bot":          "🤖 External bot usernames aren't allowed here.",
    "url":          "🔗 Links and URLs aren't allowed here.",
    "username":     "👤 External @mentions aren't allowed here.",
    "forward":      "↩️ Forwarded messages aren't allowed here.",
    "adult_emoji":  "🔞 Adult emojis aren't allowed here.",
    "adult_word":   "🚫 Inappropriate language detected.",
    "blacklist":    "⛔ That word is blacklisted in this group.",
    "flood":        "🌊 Slow down — anti-flood triggered.",
    "stylish_font": "✍️ Stylish or fancy fonts aren't allowed here.",
    "hidden_link":  "🔗 Hidden links in text aren't allowed here.",
    "location":     "📍 Sharing location isn't allowed here.",
    "contact":      "📇 Sharing contacts isn't allowed here.",
    "hashtag":      "#️⃣ Hashtags aren't allowed here.",
    "voice":        "🎙️ Voice messages aren't allowed here.",
    "chinese":      "🈲 Chinese-language text isn't allowed here.",
    "premium_emoji": "💎 Premium emojis with text aren't allowed here.",
    "quote":        "❝ Quoting/forwarding content from other chats isn't allowed here.",
}

# Usernames that are always exempt from @mention filtering
EXEMPT_USERNAMES = {"admin", "owner", "request", "sbnime"}

MUTE_TIME  = {1: 35, 2: 60, 3: 120, 4: 604800}

# Guardian's own commands — /settings → "Other-Bot Commands" filter tabhi delete karta hai
# jab command yahan list mein NAHI ho (matlab kisi doosre bot ke liye tha).
OWN_COMMANDS = {
    "start","help","rule","rules","setrules","id","setlinked","testmute","mute","unmute",
    "ban","unban","warn","warnings","resetwarnings","rep","repboard","reputation",
    "del","purge","immortal","unimmortal","immortals","addblacklist","removeblacklist",
    "blacklist","addwhitelist","removewhitelist","whitelist","sticker_delete","autodelete",
    "captcha","broadcast","groups","regroup","globalmutes","unglobalmute","gblacklist","gwhitelist",
    "stats","power","unpower","fban","gunban","gclearwarn","adexempt",
    "unadexempt","premium","addteacher",
    "removeteacher","teachers","settings",
}

# ═══════════════════════════════════════════════════════════
#  /settings PANEL — Filter toggle defaults (per group)
#  Admin/Owner /settings se in sabko on/off kar sakte hain.
# ═══════════════════════════════════════════════════════════
DEFAULT_FILTERS = {
    "antispam":     True,   # master: blacklist + adult-word + stylish-font + hidden-link
    "antiflood":    True,   # message flood/rate limiting
    "imagefilter":  False,  # unsafe image filter (best-effort, needs AI vision to be fully accurate)
    "noevents":     False,  # join/left service messages auto-delete
    "nolinks":      True,   # plain URL/link messages block
    "noforwards":   True,   # forwarded messages block (linked channel exempt)
    "nolocations":  False,  # location messages block
    "nocontacts":   False,  # contact-card messages block
    "nocommands":   False,  # other-bots' commands block (spam-command protection)
    "nohashtags":   False,  # hashtag-heavy messages block
    "novoice":      False,  # voice note messages block
    "nochinese":    False,  # Chinese-language text messages block
    "nopremiumemoji": False,  # Telegram Premium (custom) emoji-with-text block — new + edited both
    "noquotes":     False,  # cross-chat "Quote" (other channel quote-forward) block
    "nobots":       True,   # auto-kick bots added by non-admins
    "profanity":    True,   # built-in bad-words filter
    "blacklist":    True,   # group + global blacklist word enforcement
    "whitelist":    True,   # whitelist exceptions apply
    "welcome":      True,   # welcome message on join
    "warncaptcha":  True,   # auto-unmute captcha on warning/mute (off = old admin-only unmute button)
}

FILTER_LABELS = {
    "antispam":    "🚨 𝗔𝗻𝘁𝗶𝘀𝗽𝗮𝗺 𝗙𝗶𝗹𝘁𝗲𝗿",
    "antiflood":   "🌊 𝗔𝗻𝘁𝗶-𝗙𝗹𝗼𝗼𝗱",
    "imagefilter": "🖼️ 𝗨𝗻𝘀𝗮𝗳𝗲 𝗜𝗺𝗮𝗴𝗲 𝗙𝗶𝗹𝘁𝗲𝗿",
    "noevents":    "🚪 𝗝𝗼𝗶𝗻/𝗟𝗲𝗳𝘁 𝗘𝘃𝗲𝗻𝘁𝘀",
    "nolinks":     "🔗 𝗟𝗶𝗻𝗸𝘀 𝗙𝗶𝗹𝘁𝗲𝗿",
    "noforwards":  "↩️ 𝗙𝗼𝗿𝘄𝗮𝗿𝗱𝘀 𝗙𝗶𝗹𝘁𝗲𝗿",
    "nolocations": "📍 𝗟𝗼𝗰𝗮𝘁𝗶𝗼𝗻𝘀 𝗙𝗶𝗹𝘁𝗲𝗿",
    "nocontacts":  "📇 𝗖𝗼𝗻𝘁𝗮𝗰𝘁𝘀 𝗙𝗶𝗹𝘁𝗲𝗿",
    "nocommands":  "🤖 𝗢𝘁𝗵𝗲𝗿-𝗕𝗼𝘁 𝗖𝗼𝗺𝗺𝗮𝗻𝗱𝘀",
    "nohashtags":  "#️⃣ 𝗛𝗮𝘀𝗵𝘁𝗮𝗴𝘀 𝗙𝗶𝗹𝘁𝗲𝗿",
    "novoice":     "🎙️ 𝗩𝗼𝗶𝗰𝗲 𝗙𝗶𝗹𝘁𝗲𝗿",
    "nochinese":   "🈲 𝗖𝗵𝗶𝗻𝗲𝘀𝗲 𝗧𝗲𝘅𝘁 𝗙𝗶𝗹𝘁𝗲𝗿",
    "nopremiumemoji": "💎 𝗣𝗿𝗲𝗺𝗶𝘂𝗺 𝗘𝗺𝗼𝗷𝗶 𝗙𝗶𝗹𝘁𝗲𝗿",
    "noquotes":    "❝ 𝗤𝘂𝗼𝘁𝗲 𝗙𝗼𝗿𝘄𝗮𝗿𝗱 𝗙𝗶𝗹𝘁𝗲𝗿",
    "nobots":      "🛑 𝗔𝗱𝗱𝗶𝗻𝗴 𝗦𝗽𝗮𝗺𝗯𝗼𝘁𝘀",
    "profanity":   "🤬 𝗕𝗮𝗱 𝗪𝗼𝗿𝗱𝘀 𝗙𝗶𝗹𝘁𝗲𝗿",
    "blacklist":   "⛔ 𝗕𝗮𝗱 𝗗𝗼𝗺𝗮𝗶𝗻𝘀/𝗪𝗼𝗿𝗱𝘀",
    "whitelist":   "✅ 𝗦𝗮𝗳𝗲 𝗗𝗼𝗺𝗮𝗶𝗻𝘀/𝗪𝗼𝗿𝗱𝘀",
    "welcome":     "👋 𝗪𝗲𝗹𝗰𝗼𝗺𝗲 𝗠𝗲𝘀𝘀𝗮𝗴𝗲",
    "warncaptcha": "🔐 𝗪𝗮𝗿𝗻 𝗔𝘂𝘁𝗼-𝗨𝗻𝗺𝘂𝘁𝗲 𝗖𝗮𝗽𝘁𝗰𝗵𝗮",
}
# ── Filters grouped into categories for a cleaner /settings → Filters UI ──
FILTER_GROUPS = [
    ("🛡️ 𝗖𝗼𝗿𝗲 𝗣𝗿𝗼𝘁𝗲𝗰𝘁𝗶𝗼𝗻", ["antispam", "antiflood", "nobots", "profanity"]),
    ("🚫 𝗖𝗼𝗻𝘁𝗲𝗻𝘁 𝗙𝗶𝗹𝘁𝗲𝗿𝘀", ["nolinks", "noforwards", "nolocations", "nocontacts",
                             "nocommands", "nohashtags", "novoice", "nochinese", "imagefilter",
                             "nopremiumemoji", "noquotes"]),
    ("📋 𝗪𝗼𝗿𝗱 𝗟𝗶𝘀𝘁𝘀", ["blacklist", "whitelist"]),
    ("👥 𝗚𝗿𝗼𝘂𝗽 𝗕𝗲𝗵𝗮𝘃𝗶𝗼𝘂𝗿", ["noevents", "welcome", "warncaptcha"]),
]

# ═══════════════════════════════════════════════════════════
#  AUTO-RULES — /rules ka default text seedha in filter toggles se
#  banta hai. Admin jo bhi /settings → Filters me ON karega, wahi
#  line yahan rule ban ke user ko dikhegi — alag se kahin maintain
#  nahi karna padta. (Sirf tab use hota hai jab /setrules se koi
#  custom rules text set na ho.)
# ═══════════════════════════════════════════════════════════
# key -> rule line shown when that filter is ON. Order below = display order.
FILTER_RULE_LINES = [
    ("nolinks",        "🔗 Sharing links, URLs or hidden links"),
    ("noforwards",     "↩️ Forwarding messages _(linked channel is exempt)_"),
    ("blacklist",      "⛔ Using blacklisted words"),
    ("profanity",      "🗣️ Abusive or adult language"),
    ("nocontacts",     "📇 Sharing contact cards"),
    ("nolocations",    "📍 Sharing live location / venues"),
    ("nohashtags",     "#️⃣ Hashtag spam"),
    ("novoice",        "🎙️ Voice messages & video notes"),
    ("nochinese",      "🈲 Chinese-language text"),
    ("nopremiumemoji", "💎 Premium emoji used with text"),
    ("noquotes",       "❝ Quote-forwarding from other chats"),
    ("nocommands",     "🤖 Other bots' commands"),
    ("nobots",         "🛑 Adding other bots to the group"),
    ("antiflood",      "🌊 Flooding / spamming messages quickly"),
    ("imagefilter",    "🖼️ Sending unsafe / NSFW images"),
]
# These have no dedicated toggle but are always enforced together with the
# "antispam" master filter, so they only appear in /rules when antispam is ON.
ANTISPAM_ALWAYS_RULES = [
    "🔞 Adult emojis (2 or more in one message)",
    "🎨 Stylish / fancy unicode fonts",
    "🤖 Unapproved external bot @usernames",
    "📛 Random @username tagging of unrelated people",
]

GMUTE_DURATION = 604800   # 1 week — global mute ki duration (seconds)
# Warning expiry times (seconds). 4th warning (jo gmute trigger karta hai) ki
# expiry GMUTE_DURATION ke barabar honi chahiye — None NAHI, warna woh warning
# kabhi expire nahi hoti aur gmute hatne ke baad bhi warnings count rehta hai.
WARN_EXP   = {1: 21600, 2: 57600, 3: 97200, 4: GMUTE_DURATION}

# ── Thank-you keywords — reply karke bole to 1 warning kam / reputation +1 ──
THANK_YOU_WORDS = {
    "thank you", "thanks", "thank u", "thx", "tnx", "tysm", "ty",
    "thankyou", "thanku", "thnx", "thnks",
    "shukriya", "shukriyaa", "dhanyawad", "dhanyabad", "dhanyvad",
    "asa shukriya", "bahut shukriya", "bohot shukriya", "bahot shukriya",
}

# ═══════════════════════════════════════════════════════════
#  GUARDIAN COIN / REPUTATION ECONOMY — CONFIG
#  • Har "Thank You" = 100 Reputation Points
#  • 1 warning maaf karne ka cost = 100 Reputation Points
#  • 10,000 Reputation Points = 1 Guardian Coin = ₹1
#  • Guardian Coin sirf "accepted" groups ke reputation se banta hai.
#    Non-accepted group ka reputation SIRF warning maaf karne ke
#    kaam aata hai, coin mein convert nahi hota.
#  • Min withdrawal = 10 Guardian Coins (₹10)
# ═══════════════════════════════════════════════════════════
REP_PER_THANK        = 100      # 1 thank you = 100 rep points
REP_PER_WARN_REMOVE  = 100      # 1 warning maaf = 100 rep points
REP_PER_GUARDIAN_COIN  = 10000    # 10,000 rep = 1 Guardian Coin (₹1)
MIN_WITHDRAW_COINS   = 10       # Min ₹10 withdrawal

# ═══════════════════════════════════════════════════════════
#  DETECTION PATTERNS
# ═══════════════════════════════════════════════════════════
BOT_RE = re.compile(r'@(\w{5,}bot)\b', re.I)

# Matches any @username mention (3+ chars after @)
USERNAME_RE = re.compile(r'@(\w{3,})\b')

URL_RE = re.compile(
    r'('
    r'https?://\S+'
    r'|www\.\S+'
    r'|t\.me/\S+'
    r'|wa\.me/\S+'
    r'|bit\.ly/\S+'
    r'|youtu\.be/\S+'
    r'|[a-zA-Z0-9_-]{2,}\.[a-zA-Z0-9_-]{2,}/\S*'
    r'|[a-zA-Z0-9_-]{2,}\.[a-zA-Z]{2,15}'
    r')',
    re.I
)

ADULT_EMOJIS = [
    '🍑','🍆','💦','🔞','👅','💋','🍒','🍌','🥒','🌶️',
    '👙','🩲','🩱','🫦','🥵','🤤'
]

DEFAULT_ADULT_WORDS = [
    # English
    'sex','xxx','porn','nude','naked','boob','dick','pussy','cock',
    'fuck','fucking','fucker','bitch','whore','slut','ass','asshole',
    'horny','onlyfans','webcam','adult','18+','nsfw','xvideo','xnxx',
    'xhamster','pornhub','brazzers','blowjob','handjob','orgasm','cum',
    'strip','stripper','escort','call girl',
    # Hindi/Hinglish
    'chut','lund','loda','lauda','gaand','gand','chod','chuda',
    'madarchod','behenchod','bhenchod','bhosd','bhosdike','chud',
    'randi','raand','hijra','kutiya','muth','hilana','pelna','chodna',
    'chudai','chudwa','dalla','dalal','maal','badan','jism','nanga','nangi',
]

WHITELIST_ABBREVIATIONS = [
    'Mr.','Mrs.','Dr.','Sr.','Jr.','a.m.','p.m.','A.M.','P.M.','e.g.','i.e.','etc.'
]

# ─── Stylish / Unicode Font Detection ───────────────────────
# Mathematical Alphanumeric Symbols block + other fancy ranges
STYLISH_FONT_RANGES = [
    (0x1D400, 0x1D7FF),  # Mathematical Bold/Italic/Script/Fraktur/Double-struck etc.
    (0xFF01,  0xFF5E),   # Fullwidth Latin letters
    (0x1F170, 0x1F171),  # 🅰 🅱 type chars
    (0x24B6,  0x24E9),   # Ⓐ-ⓩ circled letters
    (0x1F1E6, 0x1F1FF),  # Regional indicator letters (flag combos)
]

def has_stylish_font(text: str) -> bool:
    """Return True if text contains Unicode stylish/fancy font characters."""
    for ch in text:
        cp = ord(ch)
        for start, end in STYLISH_FONT_RANGES:
            if start <= cp <= end:
                return True
    return False

# ─── Hidden Link (text entity hyperlink) detection ──────────
# Telegram sends MessageEntity of type text_link when someone
# hides a URL behind display text.  We flag this as a violation.
def has_hidden_link(msg) -> bool:
    """Return True if message has a text_link entity (hidden hyperlink)."""
    from telegram import MessageEntity
    for entity_list in [msg.entities or [], msg.caption_entities or []]:
        for ent in entity_list:
            if ent.type == MessageEntity.TEXT_LINK:
                return True
    return False

# ─── Premium Emoji detection ─────────────────────────────────
# Sirf Telegram Premium users hi "custom_emoji" entity type ke
# animated/premium emoji bhej sakte hain — isi se pehchaante hain.
def has_premium_emoji(msg) -> bool:
    """Return True if message text/caption contains a Telegram Premium (custom) emoji."""
    from telegram import MessageEntity
    for entity_list in [msg.entities or [], msg.caption_entities or []]:
        for ent in entity_list:
            if ent.type == MessageEntity.CUSTOM_EMOJI:
                return True
    return False

# ─── Cross-chat "Quote" detection ────────────────────────────
# Jab koi kisi doosre channel/group ke message ka hissa "Quote"
# karke yahan bhejta hai, Telegram us message par `external_reply`
# field bharta hai (origin doosre chat ka hota hai). Same-chat
# normal replies mein yah field nahi hota, isliye safe hai.
# (Requires python-telegram-bot >= 20.8 — Bot API 7.0 field;
# getattr fallback purane version par bhi crash nahi hone dega.)
def has_external_quote(msg) -> bool:
    """Return True if message quotes/replies to content from another chat/channel."""
    return getattr(msg, "external_reply", None) is not None

# Flood control
FLOOD_DATA = {}
FLOOD_LIMIT   = 5
FLOOD_WINDOW  = 8

CACHE     = {}
MAX_CACHE = 100

CAPTCHA_PENDING = {}

# ── Warn/Mute Auto-Unmute Captcha ──
# Jab bhi kisi user ko blacklist/link/violation ki wajah se warning
# milti hai aur wo mute ho jaata hai, uske saath ek aasan math captcha
# attach hota hai. Captcha sahi solve karte hi: (1) mute turant hat
# jaata hai, (2) us user ki SAARI warnings clear ho jaati hain — taaki
# galti se mute hue log khud hi, bina kisi admin ke, apna account fix
# kar sakein. Key format: "{chat_id}_{user_id}" -> {"answer": str}
MUTE_CAPTCHA_PENDING = {}

# ═══════════════════════════════════════════════════════════
#  PREMIUM — Bio Guard & Edit Guard state
# ═══════════════════════════════════════════════════════════
# NOTE: two SEPARATE caches, one per direction. Earlier both directions
# shared one dict/key, so checking a flagged user's bio (found clean)
# stamped the same key that the "still clean, scan for new violation"
# path also reads — which blocked the *next* scan for the full 30 min,
# even though the user had just added a link back. Keeping them apart
# means clearing a violation and adding a new one both get picked up
# fast, independently of each other.
CLEAN_CHECK_CACHE: dict[tuple, float] = {}      # (chat_id,user_id) -> last scan while bio was clean
FLAGGED_CHECK_CACHE: dict[tuple, float] = {}    # (chat_id,user_id) -> last recheck while shadow-flagged
BIO_RECHECK_SEC = 20                            # clean user: how often we scan their bio for a new violation
SHADOW_RECHECK_SEC = 5                          # flagged user: how often we recheck if they cleaned it up
                                                 # (both kept short — small cooldown just avoids hammering
                                                 # get_chat() if someone spams messages back to back)
SHADOW_MSG_COUNT: dict[tuple, int] = {}         # (chat_id,user_id) -> msgs since last notice
SHADOW_FLOOD: dict[tuple, list] = {}            # (chat_id,user_id) -> [timestamps]
SHADOW_FLOOD_LIMIT  = 10
SHADOW_FLOOD_WINDOW = 60
SHADOW_PUNISH_THRESHOLD = 5                     # after this many bio-blocked messages, switch
                                                 # to the normal warn/mute escalation (same as a
                                                 # normal link/blacklist violation) instead of
                                                 # just silently deleting the message

# ── Bio Guard: manual "🔄 Recheck" button ──
# The automatic recheck (above) depends on the user sending a message,
# which can be flaky: their message may get gated by SHADOW_RECHECK_SEC,
# or Telegram's own servers can briefly serve a stale cached bio right
# after it's edited. A button gives the user a direct, explicit way to
# force a fresh get_chat() + re-scan on demand, instead of only ever
# hoping a message triggers it. Small per-user cooldown just stops
# someone from spam-tapping it.
BIORECHECK_COOLDOWN: dict[tuple, float] = {}    # (chat_id,user_id) -> last manual recheck
BIORECHECK_COOLDOWN_SEC = 4

def _biorecheck_markup(chat_id: int, user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("🔄 𝗥𝗲𝗰𝗵𝗲𝗰𝗸 𝗠𝘆 𝗕𝗶𝗼 𝗡𝗼𝘄", callback_data=f"biorecheck_{chat_id}_{user_id}")
    ]])


# ── Premium Panel: "➕ Add" buttons for Bio Domains / Bio Words ──
# Button click sends a ForceReply prompt (unique marker text); a small,
# narrowly-filtered MessageHandler catches the admin's reply to THAT
# specific message and adds it — no separate typed command needed.
BIODOMAIN_ADD_MARKER = "🌐 𝗥𝗲𝗽𝗹𝘆 𝘁𝗼 𝗔𝗱𝗱 𝗕𝗶𝗼 𝗗𝗼𝗺𝗮𝗶𝗻"
BIOWORD_ADD_MARKER   = "🕵️ 𝗥𝗲𝗽𝗹𝘆 𝘁𝗼 𝗔𝗱𝗱 𝗕𝗶𝗼 𝗪𝗼𝗿𝗱"

class _BioAddReplyFilter(filters.MessageFilter):
    """Matches ONLY a text reply to one of our own ForceReply prompts
    above — deliberately narrow so it never intercepts normal group
    chat (which still needs to reach check_msg for moderation)."""
    def filter(self, message):
        r = message.reply_to_message
        if not r or not r.from_user or not r.from_user.is_bot:
            return False
        txt = r.text or r.caption or ""
        return txt.startswith(BIODOMAIN_ADD_MARKER) or txt.startswith(BIOWORD_ADD_MARKER)

BIO_ADD_REPLY_FILTER = _BioAddReplyFilter()


async def bio_add_reply_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Handles the admin's reply to a '➕ Add Domain/Word' ForceReply prompt."""
    msg = update.message
    ch = update.effective_chat
    replied = msg.reply_to_message
    prompt_text = replied.text or replied.caption or ""

    if not await sender_is_admin(ctx, update):
        warn = await msg.reply_text("🔒 Admins only can do this.")
        asyncio.create_task(delete_after(ctx, ch.id, warn.message_id, 10))
        asyncio.create_task(msg.delete())
        return

    value_raw = (msg.text or "").strip()
    if not value_raw:
        return

    if prompt_text.startswith(BIODOMAIN_ADD_MARKER):
        domain = extract_domain(value_raw)
        if not domain:
            reply = await msg.reply_text(
                "❌ That doesn't look like a valid domain — try again (e.g. `instagram.com`).",
                parse_mode='Markdown'
            )
            asyncio.create_task(delete_after(ctx, ch.id, reply.message_id, 15))
            return
        g = db.get_group(ch.id)
        if g.get("bio_link_domains") is None:
            db.update_group(ch.id, {"bio_link_domains": DEFAULT_BIO_LINK_DOMAINS.copy()})
        db.add_bio_domain(ch.id, domain)
        confirm = await msg.reply_text(f"🌐 Added to Bio Link Domains: `{domain}`", parse_mode='Markdown')
        asyncio.create_task(delete_after(ctx, ch.id, confirm.message_id, 15))

    elif prompt_text.startswith(BIOWORD_ADD_MARKER):
        word = value_raw.lower()
        if db.get_biowords(ch.id) is None:
            db.set_biowords(ch.id, list(set((db.get_blacklist(ch.id) or []) + (db.get_gblacklist() or []))))
        db.add_bioword(ch.id, word)
        confirm = await msg.reply_text(f"🕵️ Added to Bio Words: `{word}`", parse_mode='Markdown')
        asyncio.create_task(delete_after(ctx, ch.id, confirm.message_id, 15))
    else:
        return

    asyncio.create_task(replied.delete())
    asyncio.create_task(msg.delete())


# ── Bio Guard: Username check — resolved-type cache ──
# "users_only" mode has to tell a channel/group's @username apart from an
# ordinary Telegram user's @username. IMPORTANT constraint: Telegram's
# Bot API can only resolve a channel/group's @username reliably (public
# entities are always look-up-able) — it generally CANNOT resolve an
# arbitrary private user's @username unless the bot already has some
# direct context on that user. So get_chat() failing is actually the
# *common* case for a perfectly ordinary user, not a red flag — we must
# fail OPEN (allow) when we can't resolve it, and only ever block when
# we get positive confirmation it's a channel/group/supergroup. Failing
# closed here was blocking real users' own usernames incorrectly.
USERNAME_TYPE_CACHE: dict[str, tuple] = {}      # uname(lower) -> (is_blocked_type_bool, checked_at)
USERNAME_TYPE_CACHE_TTL = 300

async def _username_is_channel_or_group(ctx, uname: str) -> bool:
    """True ONLY if @uname is confirmed to be a channel or group/supergroup
    — the one case users_only mode should block. Anything else (a plain
    user, a bot, or unresolvable) returns False, i.e. allowed."""
    cached = USERNAME_TYPE_CACHE.get(uname)
    if cached and time.time() - cached[1] < USERNAME_TYPE_CACHE_TTL:
        return cached[0]
    is_blocked_type = False
    try:
        chat = await ctx.bot.get_chat(f"@{uname}")
        is_blocked_type = chat.type in ("channel", "group", "supergroup")
    except Exception:
        # Can't resolve it — almost always means it's an ordinary user
        # Telegram won't disclose to the bot without prior context, NOT
        # a working channel/group link. Don't punish the user for that.
        is_blocked_type = False
    USERNAME_TYPE_CACHE[uname] = (is_blocked_type, time.time())
    return is_blocked_type


def _bio_violation_what(kind: str, matched, in_bio: bool = False) -> str:
    """Human-readable 'what' phrase for a bio-guard hit, shared by every
    notice/punishment message so link/blacklist/username all read consistently."""
    suffix = " in your bio" if in_bio else ""
    if kind == "link":
        return f"a *link* (`{matched}`){suffix}" if matched else f"a *link*{suffix}"
    if kind == "username":
        return f"a username (`{matched}`){suffix}" if matched else f"a username{suffix}"
    return f"the blacklisted word `{matched}`{suffix}"


async def bio_violation(bio: str, chat_id: int, g: dict, ctx=None):
    """Check a bio string for a link, a blacklisted word, or (Premium) an
    @username — each check individually toggleable from the Premium panel.
    Returns (kind, matched_word_or_none) — kind is 'link', 'blacklist',
    'username', or None.

    Bio Link Guard has three modes (g["bio_link_guard"]):
      "off"       — link check disabled.
      "blacklist" — only trips if the link's DOMAIN is on this group's
                    Bio Link Domains list (g["bio_link_domains"],
                    defaults to t.me + telegram.me). A link to a domain
                    NOT on that list (e.g. instagram.com) is ignored.
      "all"       — ANY link at all trips it (default — old behaviour).

    Bio Words (g/db "bio_words") are a list fully independent from the
    group's main /blacklist: until an admin customizes it via
    /addbioword or /removebioword it just mirrors the main blacklist +
    global blacklist, but any edit from then on only ever affects this
    bio-only list — never the main one.

    Bio Username Guard has two ON modes (g["bio_username_guard"]):
      "full"       — ANY @username in the bio is blocked, no exceptions.
      "users_only" — a @username is blocked only if it's CONFIRMED to be
                     a channel or group/supergroup; an ordinary user's
                     @username (or anything we can't resolve — which is
                     the normal case for private users) is allowed.
      "off"        — check disabled (default).
    """
    if not bio:
        return None, None

    link_mode = _bio_link_mode(g)
    if link_mode == "all":
        if check_link(bio):
            return "link", None
    elif link_mode == "blacklist":
        domains = g.get("bio_link_domains")
        if domains is None:
            domains = DEFAULT_BIO_LINK_DOMAINS
        dom = check_link_domain(bio, domains)
        if dom:
            return "link", dom
    # link_mode == "off" -> skip link check entirely

    if g.get("bio_blacklist_guard", True):
        bio_words = db.get_biowords(chat_id)
        if bio_words is None:
            bio_words = list(set((db.get_blacklist(chat_id) or []) + (db.get_gblacklist() or [])))
        else:
            bio_words = list(set(bio_words))
        if bio_words:
            r = build_blacklist_re(bio_words)
            if r:
                m = r.search(bio)
                if m:
                    return "blacklist", m.group(1)

    uname_mode = g.get("bio_username_guard", "off")
    if uname_mode in ("full", "users_only"):
        for match in USERNAME_RE.findall(bio):
            uname = match.lower()
            if uname in EXEMPT_USERNAMES:
                continue
            if uname_mode == "full":
                return "username", f"@{match}"
            # users_only — block only a CONFIRMED channel/group/supergroup
            # username; everything else (a plain user, unresolvable) passes.
            if ctx is not None and await _username_is_channel_or_group(ctx, uname):
                return "username", f"@{match}"

    return None, None


# ═══════════════════════════════════════════════════════════
#  MONGODB DATABASE
# ═══════════════════════════════════════════════════════════
class SeenUser:
    """Lightweight User-lookalike (id/first_name/username) built from our
    own seen-users index, so user_name()/user_mention() can render a nice
    name/mention for a target resolved by @username or userid — without
    needing a live Telegram API object."""
    __slots__ = ("id", "first_name", "username")

    def __init__(self, id_, first_name=None, username=None):
        self.id = id_
        self.first_name = first_name
        self.username = username


class DB:
    def __init__(self):
        try:
            self.client = MongoClient(MONGO_URL, serverSelectionTimeoutMS=5000)
            self.client.admin.command('ping')
            self.db = self.client["guardiangroupbot"]
            print("✅ MongoDB Connected!")
        except ConnectionFailure as e:
            raise RuntimeError(f"❌ MongoDB connection failed: {e}")

        self.users    = self.db["users"]
        self.groups   = self.db["groups"]
        self.gmutes   = self.db["gmutes"]
        self.stats_c  = self.db["stats"]
        self.immortal = self.db["immortal"]
        self.blacklist= self.db["blacklist"]
        self.gblacklist = self.db["global_blacklist"]
        self.fbans    = self.db["fbans"]          # fban list
        self.powered  = self.db["powered_users"]  # users with /fban power
        self.communities = self.db["communities"]  # admin_id -> [group_id,...] (for /gban & scoped /unmute)
        self.ad_exempt = self.db["autodel_exempt"] # bots exempt from autodelete
        self.reputation = self.db["reputation"]   # group-wise reputation points (SEPARATE from leaderboard)
        self.activity  = self.db["activity"]      # daily message-count tracking (leaderboard source)
        self.guardian_pts = self.db["guardian_points"]   # global guardian points wallet per user
        self.rep_daily  = self.db["rep_daily_limit"] # daily rep-give tracking (3/day cap)
        self.accepted_rep_groups = self.db["accepted_rep_groups"]  # groups jinka rep Guardian Coin mein convert hota hai
        self.withdrawals = self.db["withdrawals"]    # Guardian Coin withdrawal requests
        # user_index: username/user_id se seen-user lookup — Telegram Bot API
        # khud arbitrary @username ya user_id ko resolve NAHI kar sakta jab
        # tak bot ne us user ka koi message/join kahin dekha na ho. Isliye
        # har group message + naye member pe yahan ek chhoti si local index
        # banate hain, taaki /ban, /mute, /warn waghera @username ya userid
        # se bhi reliably kaam karein (sirf reply pe depend na karna pade).
        self.user_index = self.db["user_index"]
        # msg_log: per (chat_id,user_id) bounded list of recent message_ids —
        # Telegram ka ban-time revoke_messages sirf pichhle 48 ghante ke
        # messages delete karta hai (platform ki hard limit). Isse aage
        # jaakar bhi /ban aur /warn par purane messages delete karne ke
        # liye humein khud message_ids track karne padte hain.
        self.msg_log  = self.db["msg_log"]

        if not self.stats_c.find_one({"_id": "global"}):
            self.stats_c.insert_one({"_id": "global", "warnings": 0, "mutes": 0, "scanned": 0, "gmutes": 0})

        # ── Indexes ──────────────────────────────────────────────
        # In se pehle koi index nahi tha, matlab reputation/activity/withdrawals
        # collections pe har query FULL COLLECTION SCAN karti thi — jitna data
        # badhta jaata, bot utna slow hota jaata (aur pymongo sync hai, isliye
        # ek slow query poore bot ka event loop tak block kar deti thi).
        try:
            self.reputation.create_index("user_id")
            self.reputation.create_index("chat_id")
            self.activity.create_index([("chat_id", 1), ("date", 1)])
            self.activity.create_index("date")
            self.activity.create_index([("user_id", 1), ("date", 1)])
            self.withdrawals.create_index("status")
            self.withdrawals.create_index([("user_id", 1), ("status", 1)])
            self.user_index.create_index("username")
            print("✅ MongoDB indexes ensured!")
        except Exception as e:
            print(f"⚠️ Index creation warning: {e}")

    def inc_stat(self, field):
        self.stats_c.update_one({"_id": "global"}, {"$inc": {field: 1}})

    def get_stats(self):
        return self.stats_c.find_one({"_id": "global"}) or {}

    def remember_user(self, user):
        """Har real (non-bot) user ka id + username + first_name yaad rakho.
        Yeh call bahut cheap hai (ek upsert) aur har group message +
        naye member join pe hoti hai — isi index se baad mein /ban, /mute,
        /warn waghera ko sirf @username ya userid se bhi target resolve
        karne diya jaata hai, reply ke bina."""
        if user is None or getattr(user, "is_bot", False):
            return
        try:
            doc = {}
            if getattr(user, "username", None):
                doc["username"] = user.username.lower()
            if getattr(user, "first_name", None):
                doc["first_name"] = user.first_name
            if not doc:
                return
            self.user_index.update_one({"_id": user.id}, {"$set": doc}, upsert=True)
        except Exception:
            pass

    def find_user_by_username(self, username):
        """@username (bina @) se pehle-dekhe hue user ka ID dhoondo."""
        try:
            doc = self.user_index.find_one({"username": username.lower()})
            return doc["_id"] if doc else None
        except Exception:
            return None

    def get_user_info(self, user_id):
        """Seen-user index se ek user ka naam/username nikaalo (display ke liye)."""
        try:
            doc = self.user_index.find_one({"_id": user_id})
            if not doc:
                return None
            return SeenUser(user_id, doc.get("first_name"), doc.get("username"))
        except Exception:
            return None

    def add_group(self, chat_id):
        self.groups.update_one({"_id": chat_id}, {"$setOnInsert": {
            "_id": chat_id,
            "linked_channel": None,
            "rules": None,
            "sticker_delete_min": None,
            "autodelete_min": None,
            "captcha": False,
            "premium": False,       # Owner-granted paid tier
            "allow_member_usernames": False,  # Premium: sirf group-members ke @username allow karo
            "bio_link_guard": "all",      # Premium Bio Guard link check: "off" | "blacklist" | "all"
            "bio_link_domains": DEFAULT_BIO_LINK_DOMAINS.copy(),  # used only when bio_link_guard == "blacklist"
            "bio_blacklist_guard": True,  # Premium Bio Guard: blacklisted-word check on/off
            "bio_username_guard": "off",  # Premium Bio Guard: "off" | "users_only" | "full"
            "warn_durations": None,   # None = default MUTE_TIME use hoga
            "filters": {},            # per-group filter toggles (defaults merged at read time)
            "welcome_enabled": True,
            "welcome_text": None,
        }}, upsert=True)

    def remove_group(self, chat_id):
        self.groups.delete_one({"_id": chat_id})

    def get_group(self, chat_id):
        return self.groups.find_one({"_id": chat_id}) or {}

    def update_group(self, chat_id, data):
        self.groups.update_one({"_id": chat_id}, {"$set": data}, upsert=True)

    # ── Per-group warn → mute/ban durations (admin editable) ──
    def get_warn_durations(self, chat_id):
        g = self.get_group(chat_id)
        custom = g.get("warn_durations")
        if custom and isinstance(custom, dict):
            return {
                1: int(custom.get("1", MUTE_TIME[1])),
                2: int(custom.get("2", MUTE_TIME[2])),
                3: int(custom.get("3", MUTE_TIME[3])),
                4: int(custom.get("4", MUTE_TIME[4])),
            }
        return dict(MUTE_TIME)

    def set_warn_duration(self, chat_id, stage, seconds):
        self.add_group(chat_id)
        g = self.get_group(chat_id)
        custom = g.get("warn_durations") or {}
        if not isinstance(custom, dict):
            custom = {}
        custom[str(stage)] = int(seconds)
        self.update_group(chat_id, {"warn_durations": custom})

    # ── Per-group filter toggles (/settings panel) ────────────
    def get_filters(self, chat_id):
        g = self.get_group(chat_id)
        f = dict(g.get("filters") or {})
        merged = dict(DEFAULT_FILTERS)
        merged.update(f)
        return merged

    def set_filter(self, chat_id, key, value):
        self.add_group(chat_id)
        g = self.get_group(chat_id)
        f = dict(g.get("filters") or {})
        f[key] = bool(value)
        self.update_group(chat_id, {"filters": f})

    def get_total_msg_count(self, chat_id: int, user_id: int) -> int:
        """Group mein is user ke total messages kitne hain (sab dates milakar)."""
        pipeline = [
            {"$match": {"chat_id": chat_id, "user_id": user_id}},
            {"$group": {"_id": None, "total": {"$sum": "$count"}}}
        ]
        result = list(self.activity.aggregate(pipeline))
        return result[0]["total"] if result else 0

    def get_all_groups(self):
        return [g["_id"] for g in self.groups.find({}, {"_id": 1})]

    # ── Global default autodelete (owner sets in DM) ──────────
    def set_global_autodelete(self, minutes):
        """Set default autodelete for ALL groups (owner DM command)."""
        self.stats_c.update_one(
            {"_id": "global"},
            {"$set": {"global_autodelete_min": minutes}},
            upsert=True
        )

    def get_global_autodelete(self):
        doc = self.stats_c.find_one({"_id": "global"})
        return doc.get("global_autodelete_min") if doc else None

    def get_effective_autodelete(self, chat_id):
        """
        Per-group override > global default.
        Returns None if both are unset.
        """
        group = self.get_group(chat_id)
        per_group = group.get("autodelete_min")
        if per_group is not None:
            return per_group          # group admin ne set kiya
        return self.get_global_autodelete()  # owner ka global default

    def set_linked_channel(self, chat_id, channel_id):
        self.update_group(chat_id, {"linked_channel": channel_id})

    def get_linked_channel(self, chat_id):
        g = self.get_group(chat_id)
        return g.get("linked_channel")

    def get_warnings(self, chat_id, user_id):
        k = f"{chat_id}_{user_id}"
        doc = self.users.find_one({"_id": k})
        if not doc:
            return 0
        now = time.time()
        valid = [w for w in doc.get("warns", []) if w.get("exp") is None or w["exp"] > now]
        if len(valid) != len(doc.get("warns", [])):
            if valid:
                self.users.update_one({"_id": k}, {"$set": {"warns": valid, "count": len(valid)}})
            else:
                self.users.delete_one({"_id": k})
        return len(valid)

    def add_warning(self, chat_id, user_id):
        k = f"{chat_id}_{user_id}"
        now = time.time()
        current = self.get_warnings(chat_id, user_id)
        new_count = current + 1
        # Har warning (1-4) ki expiry hoti hai — 4th wali GMUTE_DURATION ke
        # barabar, taaki gmute hatne ke saath hi yeh bhi expire ho jaaye.
        exp = now + WARN_EXP.get(new_count, GMUTE_DURATION)
        warn_entry = {"t": now, "exp": exp}
        self.users.update_one(
            {"_id": k},
            {"$push": {"warns": warn_entry}, "$set": {"count": new_count}},
            upsert=True
        )
        self.inc_stat("warnings")
        return min(new_count, 4)

    def remove_one_warning(self, chat_id, user_id):
        """Sabse purani/ek valid warning hatao (thank-you reward). Returns True if removed."""
        k = f"{chat_id}_{user_id}"
        doc = self.users.find_one({"_id": k})
        if not doc:
            return False
        now = time.time()
        valid = [w for w in doc.get("warns", []) if w.get("exp") is None or w["exp"] > now]
        if not valid:
            self.users.delete_one({"_id": k})
            return False
        valid.pop()  # sabse recent warning hatao
        if valid:
            self.users.update_one({"_id": k}, {"$set": {"warns": valid, "count": len(valid)}})
        else:
            self.users.delete_one({"_id": k})
        return True

    def reset_warnings(self, chat_id, user_id):
        k = f"{chat_id}_{user_id}"
        self.users.delete_one({"_id": k})

    def global_clear_warnings(self, user_id):
        """Saare groups se ek saath user ki warnings hatao."""
        # Underscore-anchored — taaki kisi doosre user ka ID (jo suffix
        # ke roop mein match ho sakta tha) galti se na hat jaaye.
        result = self.users.delete_many({"_id": {"$regex": f"_{re.escape(str(user_id))}$"}})
        return result.deleted_count

    def add_gmute(self, user_id, duration=GMUTE_DURATION):
        """Global mute lagao with expiry timestamp — taaki yeh apne aap hat sake."""
        now = time.time()
        self.gmutes.update_one(
            {"_id": user_id},
            {"$set": {"_id": user_id, "since": now, "until": now + duration}},
            upsert=True
        )
        self.inc_stat("gmutes")

    def is_gmuted(self, user_id):
        """
        Time-aware check. Agar gmute expire ho gaya hai (7 din puray), to:
          - gmute record khud hata do
          - is user ki saari (har group ki) warnings bhi clear kar do,
            taaki agla offense fresh W1 se shuru ho — purani warnings carry na ho.

        NOTE: Purane (legacy) gmute records — jo old buggy code se bane the —
        mein 'until' field hi nahi hota tha, isliye unhe bhi yahan turant
        expire/cleanup kar dete hain (permanent treat NAHI karte), warna woh
        user hamesha "GLOBALLY MUTED" dikhta rahega aur /warnings kabhi sahi
        count nahi dikhayega.
        """
        doc = self.gmutes.find_one({"_id": user_id})
        if not doc:
            return False
        until = doc.get("until")
        if until is None or until <= time.time():
            # Expired (ya legacy record bina 'until') — auto cleanup + fresh start
            self.gmutes.delete_one({"_id": user_id})
            self.global_clear_warnings(user_id)
            return False
        return True

    def remove_gmute(self, user_id):
        """Manual unmute — gmute hatao AND warnings bhi fresh start ke liye clear karo."""
        self.gmutes.delete_one({"_id": user_id})
        self.global_clear_warnings(user_id)

    def get_gmute_remaining(self, user_id):
        """Seconds remaining in current gmute, ya None agar gmuted nahi hai."""
        doc = self.gmutes.find_one({"_id": user_id})
        if not doc:
            return None
        until = doc.get("until")
        if until is None:
            return None
        remaining = until - time.time()
        return max(0, remaining)

    def get_all_gmutes(self):
        return [g["_id"] for g in self.gmutes.find()]

    # ══════════════════════════════════════════════════════════════
    #  GUARDIAN POINTS SYSTEM
    #  10,000 Reputation Points (accepted groups only) → 1 Guardian Coin → ₹1
    #  Min withdrawal: 10 INR (100 Guardian Points)
    #  Daily rep-give cap: SAME target ko max 3x/din (alag logon ko UNLIMITED baar de sakte ho)
    # ══════════════════════════════════════════════════════════════

    # ── Daily rep-give limit (PER giver→target pair, cross-group global) ──
    def get_rep_given_today_to(self, giver_id: int, target_id: int) -> int:
        """Aaj is giver ne ISI target ko kitni baar rep diya (global, cross-group)."""
        date_str = datetime.now().strftime("%Y-%m-%d")
        doc = self.rep_daily.find_one({"_id": f"{giver_id}_{target_id}_{date_str}"})
        return doc.get("count", 0) if doc else 0

    def increment_rep_given_to(self, giver_id: int, target_id: int) -> int:
        """Is giver→target pair ka aaj ka rep-give count +1 karo. Returns new count."""
        date_str = datetime.now().strftime("%Y-%m-%d")
        k = f"{giver_id}_{target_id}_{date_str}"
        result = self.rep_daily.find_one_and_update(
            {"_id": k},
            {"$inc": {"count": 1}, "$set": {"giver_id": giver_id, "target_id": target_id, "date": date_str}},
            upsert=True,
            return_document=True
        )
        return result.get("count", 1) if result else 1

    # ── Reputation (group-wise) ───────────────────────────────────
    def add_reputation(self, chat_id, user_id, amount=REP_PER_THANK, display_name=None, force_convertible=False):
        """
        Group-wise reputation point add karo + guardian wallet resync karo.
        force_convertible=True → ye manually owner ne diya hai (e.g. /reputation
        command se), isliye chahe group accepted ho ya na ho, ye rep hamesha
        Guardian Coin mein convertible rahega.
        """
        k = f"{chat_id}_{user_id}"
        update = {"$inc": {"points": amount}, "$set": {"chat_id": chat_id, "user_id": user_id}}
        if display_name:
            update["$set"]["name"] = display_name
        self.reputation.update_one({"_id": k}, update, upsert=True)
        if force_convertible and not self.is_rep_group_accepted(chat_id):
            self.guardian_pts.update_one(
                {"_id": user_id},
                {"$inc": {"manual_rep": amount}, "$set": {"user_id": user_id}},
                upsert=True
            )
        self._sync_guardian_points(user_id)

    def add_manual_convertible_rep(self, user_id, amount):
        """
        Owner utility: existing rep ko retroactively convertible banao,
        BINA total_rep badhaye (jo pehle se hi reputation collection mein hai).
        """
        self.guardian_pts.update_one(
            {"_id": user_id},
            {"$inc": {"manual_rep": amount}, "$set": {"user_id": user_id}},
            upsert=True
        )
        self._sync_guardian_points(user_id)

    def spend_reputation(self, chat_id, user_id, amount=REP_PER_WARN_REMOVE) -> bool:
        """
        Kisi ek group ka reputation kharch karo (warning maaf karne ke liye).
        Yeh HAR group (accepted ho ya na ho) mein kaam karta hai — reputation
        hamesha warn-se-bachne ke liye valid hota hai, sirf Guardian Coin
        conversion accepted groups tak limited hai.
        Returns True agar kharch ho gaya, False agar balance kam tha.
        """
        k = f"{chat_id}_{user_id}"
        doc = self.reputation.find_one({"_id": k})
        current = doc.get("points", 0) if doc else 0
        if current < amount:
            return False
        self.reputation.update_one({"_id": k}, {"$inc": {"points": -amount}})
        self._sync_guardian_points(user_id)
        return True

    # ── Accepted groups (jinka reputation Guardian Coin mein convert hota hai) ──
    def is_rep_group_accepted(self, chat_id) -> bool:
        return self.accepted_rep_groups.find_one({"_id": chat_id}) is not None

    def get_accepted_rep_groups(self):
        return [g["_id"] for g in self.accepted_rep_groups.find({}, {"_id": 1})]

    def _sync_guardian_points(self, user_id: int):
        """
        Do cheezein calculate karo:
          • total_rep        → SAB groups (accepted + non-accepted) ka total,
                                sirf tier-badge / display ke liye use hota hai
          • convertible_rep  → SIRF accepted groups ka total, isi se
                                Guardian Coin banta hai (10,000 rep = 1 coin)
        """
        accepted_ids = self.get_accepted_rep_groups()

        pipeline_total = [
            {"$match": {"user_id": user_id}},
            {"$group": {"_id": None, "total": {"$sum": "$points"}}}
        ]
        result_total = list(self.reputation.aggregate(pipeline_total))
        total_rep = result_total[0]["total"] if result_total else 0

        if accepted_ids:
            pipeline_conv = [
                {"$match": {"user_id": user_id, "chat_id": {"$in": accepted_ids}}},
                {"$group": {"_id": None, "total": {"$sum": "$points"}}}
            ]
            result_conv = list(self.reputation.aggregate(pipeline_conv))
            convertible_rep = result_conv[0]["total"] if result_conv else 0
        else:
            convertible_rep = 0

        # Manual/owner-granted convertible bucket (independent of group accept-status)
        existing = self.guardian_pts.find_one({"_id": user_id})
        manual_rep = existing.get("manual_rep", 0) if existing else 0
        convertible_rep += manual_rep

        self.guardian_pts.update_one(
            {"_id": user_id},
            {"$set": {
                "user_id": user_id,
                "total_rep": total_rep,
                "convertible_rep": convertible_rep,
            }},
            upsert=True
        )

    def get_reputation(self, chat_id, user_id):
        k = f"{chat_id}_{user_id}"
        doc = self.reputation.find_one({"_id": k})
        return doc.get("points", 0) if doc else 0

    def get_total_reputation(self, user_id: int) -> int:
        """User ka ALL groups mein total lifetime reputation."""
        pipeline = [
            {"$match": {"user_id": user_id}},
            {"$group": {"_id": None, "total": {"$sum": "$points"}}}
        ]
        result = list(self.reputation.aggregate(pipeline))
        return result[0]["total"] if result else 0

    def get_guardian_points(self, user_id: int) -> dict:
        """
        User ka guardian wallet return karo.
        coins = floor(convertible_rep / 10000) − ab tak withdraw kiye gaye coins
        """
        doc = self.guardian_pts.find_one({"_id": user_id})
        total_rep       = doc.get("total_rep", 0) if doc else 0
        convertible_rep = doc.get("convertible_rep", 0) if doc else 0
        withdrawn_coins = doc.get("withdrawn_coins", 0) if doc else 0
        earned_coins    = convertible_rep // REP_PER_GUARDIAN_COIN
        available_coins = max(0, earned_coins - withdrawn_coins)
        return {
            "total_rep": total_rep,
            "convertible_rep": convertible_rep,
            "earned_coins": earned_coins,
            "withdrawn_coins": withdrawn_coins,
            "coins": available_coins,
            # backward-compat key used elsewhere in file
            "guardian_pts": available_coins,
        }

    # ── Withdrawals ─────────────────────────────────────────────
    def create_withdrawal(self, user_id, username, coins, detail):
        req_id = f"{user_id}_{int(time.time()*1000)}"
        self.withdrawals.insert_one({
            "_id": req_id,
            "user_id": user_id,
            "username": username,
            "coins": coins,
            "inr": coins,   # 1 coin = ₹1
            "detail": detail,
            "status": "pending",
            "created_at": time.time(),
        })
        return req_id

    def get_withdrawal(self, req_id):
        return self.withdrawals.find_one({"_id": req_id})

    def get_pending_withdrawal_coins(self, user_id) -> int:
        """User ke sab PENDING requests ka total coins (double-spend rokne ke liye)."""
        pipeline = [
            {"$match": {"user_id": user_id, "status": "pending"}},
            {"$group": {"_id": None, "total": {"$sum": "$coins"}}}
        ]
        result = list(self.withdrawals.aggregate(pipeline))
        return result[0]["total"] if result else 0

    def set_withdrawal_status(self, req_id, status):
        self.withdrawals.update_one({"_id": req_id}, {"$set": {"status": status, "resolved_at": time.time()}})
        if status == "paid":
            doc = self.get_withdrawal(req_id)
            if doc:
                self.guardian_pts.update_one(
                    {"_id": doc["user_id"]},
                    {"$inc": {"withdrawn_coins": doc["coins"]}},
                    upsert=True
                )

    def get_pending_withdrawals(self, limit=20):
        return list(self.withdrawals.find({"status": "pending"}).sort("created_at", 1).limit(limit))

    def get_reputation_top(self, chat_id, limit=10):
        """Reputation ke hisaab se top users (group-wise)."""
        cursor = self.reputation.find({"chat_id": chat_id}).sort("points", -1).limit(limit)
        return list(cursor)

    def get_global_reputation_top(self, limit=10):
        """Sabse zyada total rep wale users (all groups combined)."""
        pipeline = [
            {"$group": {"_id": "$user_id", "total": {"$sum": "$points"},
                        "name": {"$last": "$name"}}},
            {"$sort": {"total": -1}},
            {"$limit": limit}
        ]
        return list(self.reputation.aggregate(pipeline))

    # ── Activity / Message-count Leaderboard ──────────────────────
    # Leaderboard ab REPUTATION se nahi — kitne MESSAGES bheje hain usse decide hota hai.
    # Period buckets: "today", "2weeks" (last 14 din), "month" (last 30 din).
    def track_activity(self, chat_id, user_id, display_name=None):
        """Har message pe call hota hai — aaj ke date-bucket mein count +1."""
        date_str = datetime.now().strftime("%Y-%m-%d")
        k = f"{chat_id}_{user_id}_{date_str}"
        update = {
            "$inc": {"count": 1},
            "$set": {"chat_id": chat_id, "user_id": user_id, "date": date_str}
        }
        if display_name:
            update["$set"]["name"] = display_name
        self.activity.update_one({"_id": k}, update, upsert=True)

    # ── Per-user message log (for /ban & /warn "delete all old messages") ──
    # Telegram ka native ban revoke_messages sirf 48h purane messages delete
    # karta hai — usse aage ke messages delete karne ka bot-level koi bulk
    # API nahi hai, isliye khud ek bounded (max 500) list track karte hain.
    MSG_LOG_CAP = 500

    def log_message_id(self, chat_id, user_id, message_id):
        k = f"{chat_id}_{user_id}"
        self.msg_log.update_one(
            {"_id": k},
            {
                "$push": {"ids": {"$each": [message_id], "$slice": -self.MSG_LOG_CAP}},
                "$set": {"chat_id": chat_id, "user_id": user_id}
            },
            upsert=True
        )

    def pop_message_ids(self, chat_id, user_id):
        """Fetch + clear this user's tracked message_ids for this chat."""
        k = f"{chat_id}_{user_id}"
        doc = self.msg_log.find_one_and_delete({"_id": k})
        return doc.get("ids", []) if doc else []

    def add_immortal(self, chat_id, user_id):
        k = f"{chat_id}_{user_id}"
        self.immortal.update_one({"_id": k}, {"$set": {"chat_id": chat_id, "user_id": user_id}}, upsert=True)

    def remove_immortal(self, chat_id, user_id):
        k = f"{chat_id}_{user_id}"
        self.immortal.delete_one({"_id": k})

    def is_immortal(self, chat_id, user_id):
        k = f"{chat_id}_{user_id}"
        return self.immortal.find_one({"_id": k}) is not None

    def get_immortals(self, chat_id):
        return [doc["user_id"] for doc in self.immortal.find({"chat_id": chat_id})]

    def add_blacklist(self, chat_id, word):
        self.blacklist.update_one(
            {"_id": chat_id},
            {"$addToSet": {"blacklist": word.lower()}},
            upsert=True
        )

    def remove_blacklist(self, chat_id, word):
        self.blacklist.update_one({"_id": chat_id}, {"$pull": {"blacklist": word.lower()}})

    def get_blacklist(self, chat_id):
        doc = self.blacklist.find_one({"_id": chat_id})
        return doc.get("blacklist", []) if doc else []

    def add_whitelist(self, chat_id, word):
        self.blacklist.update_one(
            {"_id": chat_id},
            {"$addToSet": {"whitelist": word.lower()}},
            upsert=True
        )

    def remove_whitelist(self, chat_id, word):
        self.blacklist.update_one({"_id": chat_id}, {"$pull": {"whitelist": word.lower()}})

    def get_whitelist(self, chat_id):
        doc = self.blacklist.find_one({"_id": chat_id})
        return doc.get("whitelist", []) if doc else []

    # ── Global Blacklist (owner only, applies to ALL groups) ──
    def add_gblacklist(self, word):
        self.gblacklist.update_one(
            {"_id": "global"},
            {"$addToSet": {"words": word.lower()}},
            upsert=True
        )

    def remove_gblacklist(self, word):
        self.gblacklist.update_one({"_id": "global"}, {"$pull": {"words": word.lower()}})

    def get_gblacklist(self):
        doc = self.gblacklist.find_one({"_id": "global"})
        return doc.get("words", []) if doc else []

    # ── Bio Words (Premium Bio Guard) — independent from the main
    # /blacklist. None = not customized yet (caller falls back to
    # main blacklist + global blacklist); a list (even empty) means an
    # admin has customized it via /addbioword or /removebioword, and
    # from then on it's fully separate — edits here never touch the
    # main blacklist, and vice versa. ──
    def add_bioword(self, chat_id, word):
        self.blacklist.update_one(
            {"_id": chat_id},
            {"$addToSet": {"bio_words": word.lower()}},
            upsert=True
        )

    def remove_bioword(self, chat_id, word):
        self.blacklist.update_one({"_id": chat_id}, {"$pull": {"bio_words": word.lower()}})

    def set_biowords(self, chat_id, words):
        self.blacklist.update_one(
            {"_id": chat_id},
            {"$set": {"bio_words": [w.lower() for w in words]}},
            upsert=True
        )

    def get_biowords(self, chat_id):
        doc = self.blacklist.find_one({"_id": chat_id})
        if not doc or "bio_words" not in doc:
            return None  # not customized — caller should fall back
        return doc.get("bio_words") or []

    # ── Bio Link Domains (Premium Bio Guard, "Domains Only" mode) ──
    def add_bio_domain(self, chat_id, domain):
        self.groups.update_one(
            {"_id": chat_id},
            {"$addToSet": {"bio_link_domains": domain.lower()}},
            upsert=True
        )

    def remove_bio_domain(self, chat_id, domain):
        self.groups.update_one({"_id": chat_id}, {"$pull": {"bio_link_domains": domain.lower()}})

    # ── Per-group: disable specific GLOBAL blacklist/whitelist words ──
    # (owner ka global word admin ke group par apply NAHI hoga agar disable kiya)
    def disable_gword(self, chat_id, word):
        self.blacklist.update_one({"_id": chat_id}, {"$addToSet": {"disabled_gwords": word.lower()}}, upsert=True)

    def enable_gword(self, chat_id, word):
        self.blacklist.update_one({"_id": chat_id}, {"$pull": {"disabled_gwords": word.lower()}})

    def get_disabled_gwords(self, chat_id):
        doc = self.blacklist.find_one({"_id": chat_id})
        return doc.get("disabled_gwords", []) if doc else []

    def disable_gwhite(self, chat_id, word):
        self.blacklist.update_one({"_id": chat_id}, {"$addToSet": {"disabled_gwhite": word.lower()}}, upsert=True)

    def enable_gwhite(self, chat_id, word):
        self.blacklist.update_one({"_id": chat_id}, {"$pull": {"disabled_gwhite": word.lower()}})

    def get_disabled_gwhite(self, chat_id):
        doc = self.blacklist.find_one({"_id": chat_id})
        return doc.get("disabled_gwhite", []) if doc else []

    # ── Global Whitelist (owner only, exempt in ALL groups) ──
    def add_gwhitelist(self, word):
        self.gblacklist.update_one(
            {"_id": "global"},
            {"$addToSet": {"whitelist": word.lower()}},
            upsert=True
        )

    def remove_gwhitelist(self, word):
        self.gblacklist.update_one({"_id": "global"}, {"$pull": {"whitelist": word.lower()}})

    def get_gwhitelist(self):
        doc = self.gblacklist.find_one({"_id": "global"})
        return doc.get("whitelist", []) if doc else []

    # ── FBan system ──────────────────────────────────────────
    def add_fban(self, user_id, reason="No reason"):
        self.fbans.update_one(
            {"_id": user_id},
            {"$set": {"_id": user_id, "reason": reason}},
            upsert=True
        )

    def remove_fban(self, user_id):
        self.fbans.delete_one({"_id": user_id})

    def is_fbanned(self, user_id):
        return self.fbans.find_one({"_id": user_id}) is not None

    def get_all_fbans(self):
        return [doc["_id"] for doc in self.fbans.find()]

    # ── Powered users (can use /fban) ────────────────────────
    def add_powered(self, user_id):
        self.powered.update_one(
            {"_id": user_id}, {"$set": {"_id": user_id}}, upsert=True
        )

    def remove_powered(self, user_id):
        self.powered.delete_one({"_id": user_id})

    def is_powered(self, user_id):
        return self.powered.find_one({"_id": user_id}) is not None

    # ── Community (per-admin group list) — used by /gban and by the
    # scoped /unmute for non-owner admins. An admin can only add a group
    # they're actually admin/owner of (checked at call site, not here). ──
    def add_to_community(self, admin_id, group_id):
        self.communities.update_one(
            {"_id": admin_id}, {"$addToSet": {"groups": group_id}}, upsert=True
        )

    def remove_from_community(self, admin_id, group_id):
        self.communities.update_one({"_id": admin_id}, {"$pull": {"groups": group_id}})

    def get_community_groups(self, admin_id):
        doc = self.communities.find_one({"_id": admin_id})
        return doc.get("groups", []) if doc else []

    # ── Autodelete Exempt Bots (global) ──────────────────────
    def add_ad_exempt(self, bot_id):
        """Globally exempt a bot/user ID from autodelete."""
        self.ad_exempt.update_one(
            {"_id": bot_id}, {"$set": {"_id": bot_id}}, upsert=True
        )

    def remove_ad_exempt(self, bot_id):
        self.ad_exempt.delete_one({"_id": bot_id})

    def is_ad_exempt(self, bot_id):
        return self.ad_exempt.find_one({"_id": bot_id}) is not None

    def get_all_ad_exempt(self):
        return [doc["_id"] for doc in self.ad_exempt.find()]

    def set_rules(self, chat_id, text):
        self.update_group(chat_id, {"rules": text})

    def get_rules(self, chat_id):
        return self.get_group(chat_id).get("rules")

    # ── Teacher system ────────────────────────────────────────
    def add_teacher(self, chat_id, user_id):
        """Mark a user as teacher in a group (exempt from promo-mute, gets polite warning instead)."""
        k = f"teacher_{chat_id}"
        self.groups.update_one(
            {"_id": chat_id},
            {"$addToSet": {"teachers": user_id}},
            upsert=True
        )

    def remove_teacher(self, chat_id, user_id):
        self.groups.update_one(
            {"_id": chat_id},
            {"$pull": {"teachers": user_id}}
        )

    def is_teacher(self, chat_id, user_id):
        g = self.get_group(chat_id)
        return user_id in g.get("teachers", [])

    def get_teachers(self, chat_id):
        g = self.get_group(chat_id)
        return g.get("teachers", [])

    def get_teacher_promo_count(self, chat_id, user_id):
        """How many times has this teacher done promo in this group?"""
        k = f"tpromo_{chat_id}_{user_id}"
        doc = self.users.find_one({"_id": k})
        return doc.get("count", 0) if doc else 0

    def inc_teacher_promo_count(self, chat_id, user_id):
        k = f"tpromo_{chat_id}_{user_id}"
        self.users.update_one(
            {"_id": k},
            {"$inc": {"count": 1}},
            upsert=True
        )
        return self.get_teacher_promo_count(chat_id, user_id)

    def reset_teacher_promo_count(self, chat_id, user_id):
        k = f"tpromo_{chat_id}_{user_id}"
        self.users.delete_one({"_id": k})

    # ── Premium: Shadow Blacklist (Bio Guard) ──────────────────
    def shadow_blacklist_add(self, chat_id, user_id, reason, matched):
        self.db["shadow_blacklist"].update_one(
            {"_id": f"{chat_id}_{user_id}"},
            {"$set": {
                "chat_id": chat_id, "user_id": user_id,
                "reason": reason, "matched": matched,
                "added_at": time.time(),
            }},
            upsert=True
        )

    def shadow_blacklist_get(self, chat_id, user_id):
        return self.db["shadow_blacklist"].find_one({"_id": f"{chat_id}_{user_id}"})

    def shadow_blacklist_remove(self, chat_id, user_id):
        self.db["shadow_blacklist"].delete_one({"_id": f"{chat_id}_{user_id}"})


db = DB()


# ═══════════════════════════════════════════════════════════
#  COLORED BUTTON SENDER — Bot API direct HTTP (filter.go approach)
#  Standard python-telegram-bot colored buttons support nahi karta.
#  Isliye direct Bot API call karke "style" field pass karte hain.
#  Style values: "primary" (blue), "success" (green), "danger" (red)
# ═══════════════════════════════════════════════════════════

async def send_colored_message(chat_id: int, text: str, keyboard_rows: list, parse_mode: str = "Markdown") -> int:
    """
    Bot API ko seedha call karo colored buttons ke saath.
    keyboard_rows = list of list of dicts:
      {"text": "...", "callback_data": "...", "style": "primary"/"success"/"danger"}
      {"text": "...", "url": "...", "style": "success"}
    Returns message_id on success, 0 on failure.
    """
    if not BOT_TOKEN:
        return 0
    inline_keyboard = []
    for row in keyboard_rows:
        btns = []
        for btn in row:
            b = {"text": btn["text"]}
            if "url" in btn:
                b["url"] = btn["url"]
            elif "callback_data" in btn:
                b["callback_data"] = btn["callback_data"]
            if "style" in btn:
                b["style"] = btn["style"]
            btns.append(b)
        inline_keyboard.append(btns)

    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode,
        "reply_markup": {"inline_keyboard": inline_keyboard}
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                json=payload
            ) as resp:
                data = await resp.json()
                if data.get("ok"):
                    return data["result"]["message_id"]
    except Exception:
        pass
    return 0


async def edit_colored_message(chat_id: int, message_id: int, text: str, keyboard_rows: list, parse_mode: str = "Markdown") -> bool:
    """Edit existing message with colored buttons."""
    if not BOT_TOKEN:
        return False
    inline_keyboard = []
    for row in keyboard_rows:
        btns = []
        for btn in row:
            b = {"text": btn["text"]}
            if "url" in btn:
                b["url"] = btn["url"]
            elif "callback_data" in btn:
                b["callback_data"] = btn["callback_data"]
            if "style" in btn:
                b["style"] = btn["style"]
            btns.append(b)
        inline_keyboard.append(btns)

    payload = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": text,
        "parse_mode": parse_mode,
        "reply_markup": {"inline_keyboard": inline_keyboard}
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText",
                json=payload
            ) as resp:
                data = await resp.json()
                return data.get("ok", False)
    except Exception:
        pass
    return False


def _rows_to_markup(keyboard_rows: list) -> InlineKeyboardMarkup:
    """Colored dict-rows ({'text','callback_data'/'url','style'}) ko plain
    InlineKeyboardMarkup mein convert karta hai — edit_colored_message/
    send_colored_message fail ho jaaye (jaise Bot API colored buttons na
    support kare) to yehi fallback keyboard use hota hai."""
    kb = []
    for row in keyboard_rows:
        line = []
        for btn in row:
            if "url" in btn:
                line.append(InlineKeyboardButton(btn["text"], url=btn["url"]))
            else:
                line.append(InlineKeyboardButton(btn["text"], callback_data=btn.get("callback_data", "cfg_noop")))
        kb.append(line)
    return InlineKeyboardMarkup(kb)


# ═══════════════════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════════════════
async def is_adm(ctx, chat_id, user_id):
    ANON_ADMIN_ID = 1087968824
    if user_id == ANON_ADMIN_ID:
        return True
    if user_id == OWNER_ID:
        return True
    k = f"adm_{chat_id}_{user_id}"
    now = time.time()
    if k in CACHE and now - CACHE[k][1] < 600:
        return CACHE[k][0]
    try:
        m = await ctx.bot.get_chat_member(chat_id, user_id)
        r = m.status in [ChatMember.OWNER, ChatMember.ADMINISTRATOR]
        if len(CACHE) >= MAX_CACHE:
            CACHE.pop(next(iter(CACHE)))
        CACHE[k] = (r, now)
        return r
    except Exception:
        # API fail — fallback: saare admins fetch karke check karo
        try:
            admins = await ctx.bot.get_chat_administrators(chat_id)
            admin_ids = {a.user.id for a in admins}
            r = user_id in admin_ids
            if len(CACHE) >= MAX_CACHE:
                CACHE.pop(next(iter(CACHE)))
            CACHE[k] = (r, now)
            return r
        except Exception:
            # Dono fail — agar pehle se cached hai toh woh use karo
            if k in CACHE:
                return CACHE[k][0]
            # Koi info nahi — doubt mein NON-ADMIN maano (safe side).
            # Pehle "True" tha, jisse API fail hone par har user galti se
            # admin ban jata tha aur saare moderation checks (bio guard,
            # blacklist, edit guard) skip ho jaate the. Moderation ke liye
            # "safe" hamesha "restrict karo", "chhod do" nahi hota.
            return False


def get_sender_id(update: Update) -> int:
    ANON_BOT_ID = 1087968824
    user = update.effective_user
    if user is None:
        sc = getattr(update.message, 'sender_chat', None)
        return sc.id if sc else 0
    if user.id == ANON_BOT_ID:
        sc = getattr(update.message, 'sender_chat', None)
        if sc:
            return sc.id
    return user.id


async def sender_is_admin(ctx, update: Update) -> bool:
    ANON_BOT_ID = 1087968824
    ch   = update.effective_chat
    user = update.effective_user
    if user and user.id == OWNER_ID:
        return True
    if user and user.id == ANON_BOT_ID:
        sc = getattr(update.message, 'sender_chat', None)
        if sc and sc.id == ch.id:
            return True
        return True
    if user is None:
        return False
    return await is_adm(ctx, ch.id, user.id)


async def get_group_bots(ctx, chat_id):
    k = f"bots_{chat_id}"
    now = time.time()
    if k in CACHE and now - CACHE[k][1] < 300:
        return CACHE[k][0]
    try:
        admins = await ctx.bot.get_chat_administrators(chat_id)
        bots = [x.user.username.lower() for x in admins if x.user.is_bot and x.user.username]
        if len(CACHE) >= MAX_CACHE:
            CACHE.pop(next(iter(CACHE)))
        CACHE[k] = (bots, now)
        return bots
    except:
        return []


async def fetch_linked_channel(ctx, chat_id):
    k = f"lc_{chat_id}"
    now = time.time()
    if k in CACHE and now - CACHE[k][1] < 600:
        return CACHE[k][0]
    saved = db.get_linked_channel(chat_id)
    if saved:
        CACHE[k] = (saved, now)
        return saved
    try:
        chat = await ctx.bot.get_chat(chat_id)
        if hasattr(chat, 'linked_chat_id') and chat.linked_chat_id:
            db.set_linked_channel(chat_id, chat.linked_chat_id)
            CACHE[k] = (chat.linked_chat_id, now)
            return chat.linked_chat_id
    except:
        pass
    return None


def md_esc(text: str) -> str:
    """Markdown v1 ke special chars escape karo taaki parse entity error na aaye."""
    # Markdown v1 mein sirf _ * ` [ problematic hain
    for ch in ('_', '*', '`', '['):
        text = text.replace(ch, f'\\{ch}')
    return text


def mv2_esc(text) -> str:
    """
    MarkdownV2 ke SAARE reserved characters escape karo.
    Legacy md_esc() sirf _ * ` [ escape karta hai — MarkdownV2 mein
    isse zyada chars reserved hain (. ! - ( ) = + # | { } > ~ etc).
    User ke naam / free-text jab bhi parse_mode='MarkdownV2' wale
    message mein daalna ho, ISI function se escape karo — warna
    agar naam mein koi bhi special char aaya (bahut common hai:
    period, dash, exclamation...) to Telegram message bhejna FAIL
    ho jaata hai aur (agar try/except mein wrapped hai to) silently
    kuch nahi hota — feature "kaam nahi karta" jaisa dikhta hai.
    """
    if text is None:
        return ""
    text = str(text)
    return re.sub(r'([_*\[\]()~`>#+\-=|{}.!\\])', r'\\\1', text)


def user_name(u, escape: bool = False) -> str:
    """User ka display name return karo. Default escape=False kyunki legacy
    Markdown mode mein backslash-escape render nahi hota, ulta literal
    backslash dikhta hai."""
    try:
        raw = f"@{u.username}" if u.username else u.first_name or str(u.id)
    except Exception:
        raw = "User"
    return md_esc(raw) if escape else raw


def user_mention(u) -> str:
    """Legacy-Markdown mention link — [Name](tg://user?id=...).
    @username plain text sirf tabhi notify karta hai jab user ka koi public
    username ho; jinke paas username nahi hai unhe kabhi notification nahi
    milti. tg://user link hamesha, har user ke liye, real notification
    trigger karti hai — isliye mute/warn/edit-guard jaise "user ko pata
    chalna chahiye" wale messages mein ISKO use karo, user_name() ko nahi."""
    try:
        name = md_esc(u.first_name or (f"@{u.username}" if u.username else str(u.id)))
        return f"[{name}](tg://user?id={u.id})"
    except Exception:
        return "User"


# ═══════════════════════════════════════════════════════════
#  UNIFIED TARGET RESOLUTION — reply / user_id / @username
# ═══════════════════════════════════════════════════════════
# Admin-facing commands (ban, mute, warn, etc.) should ALWAYS accept a
# target in any of these 3 forms, no matter who's using it (normal admin,
# owner, or a "Remain Anonymous" group-admin account):
#   1) /cmd @username
#   2) /cmd <user_id>
#   3) reply to the user's message + /cmd
# This single helper does that resolution consistently everywhere, so a
# command can never silently support only one of the three.
async def resolve_target(update: Update, ctx, usage: str):
    """
    Returns (target_id, target_obj, consumed, error):
      target_id  -> resolved user id, or None if resolution failed
      target_obj -> a User/SeenUser-like object with .id/.first_name/.username
                    (for building names/mentions), or None if we only have
                    a bare numeric id and couldn't look up a profile for it
      consumed   -> how many leading ctx.args were used for the target
                    (0 if resolved via reply, 1 if via id/@username) — so
                    the caller can treat the *rest* of ctx.args as
                    reason/duration/etc.
      error      -> a ready-to-send error/usage message, or None on success

    IMPORTANT: Telegram's Bot API cannot resolve an arbitrary @username or
    userid on its own — it only knows about users the bot has already
    "seen" somewhere (a message, a join event, a DM). So this relies on
    db.user_index (built from every group message via track_bot_reply and
    every join via on_join) as the primary source of truth, with
    ctx.bot.get_chat() only as a best-effort bonus for a nicer name.
    """
    msg = update.message
    if msg.reply_to_message and msg.reply_to_message.from_user:
        ru = msg.reply_to_message.from_user
        if ru.id == ctx.bot.id:
            # Replied to one of the BOT'S OWN cards (e.g. the /warnings
            # status card) — the real target isn't the bot itself. Recover
            # it from an embedded tg://user?id= mention (text_mention
            # entity) if the card included one, instead of wrongly
            # treating the bot as the target (which used to falsely
            # trigger "Admins can't be banned/warned", since the bot
            # itself is an admin in the group).
            entities = list(msg.reply_to_message.entities or []) + \
                       list(msg.reply_to_message.caption_entities or [])
            for ent in entities:
                if ent.type == "text_mention" and ent.user:
                    return ent.user.id, ent.user, 0, None
            # No embedded mention found — fall through to ctx.args/usage
            # below instead of silently targeting the bot.
        else:
            return ru.id, ru, 0, None

    if ctx.args:
        raw = ctx.args[0]

        if raw.startswith('@'):
            uname = raw.lstrip('@')
            uid = db.find_user_by_username(uname)
            if uid:
                info = db.get_user_info(uid) or SeenUser(uid, username=uname)
                return uid, info, 1, None
            # Not in our own index yet — try Telegram directly as a
            # last resort (works occasionally, e.g. if bot has DM'd them).
            try:
                chat_obj = await ctx.bot.get_chat(f"@{uname}")
                return chat_obj.id, chat_obj, 1, None
            except Exception:
                return None, None, 1, (
                    f"❌ Can't find `@{uname}` yet.\n"
                    f"The bot hasn't tracked any message or join from this user "
                    f"in this group — so it can't resolve the @username.\n"
                    f"Fix: *reply* to one of their messages with the command, "
                    f"or use their *numeric user ID* instead."
                )

        try:
            tid = int(raw)
        except ValueError:
            return None, None, 1, f"❌ Invalid user ID or username: `{raw}`"
        # Numeric ID given — pull a display name from our own index if we
        # have one (no Telegram API call needed, so this never fails/hangs).
        info = db.get_user_info(tid)
        return tid, info, 1, None

    return None, None, 0, usage


def target_name(obj, tid, escape=False):
    """Display name for a resolved target — falls back to bare ID if we
    only have a numeric id with no fetched profile."""
    if obj is not None:
        return user_name(obj, escape=escape)
    return f"`{tid}`"


def target_mention(obj, tid):
    """Notifying tg://user mention for a resolved target — falls back to a
    generic link by ID if we only have a numeric id with no fetched profile."""
    if obj is not None:
        return user_mention(obj)
    return f"[User](tg://user?id={tid})"


def is_thank_you_text(text: str) -> bool:
    """Check karo ki message me thank-you wala keyword hai ya nahi (Hindi/English mix)."""
    if not text:
        return False
    clean = text.lower().strip()
    clean = clean.strip(string.punctuation + " ")
    if not clean:
        return False
    # Pura match ya keyword as a standalone word/phrase
    for word in THANK_YOU_WORDS:
        if clean == word:
            return True
        if re.search(r'\b' + re.escape(word) + r'\b', clean):
            return True
    return False


def count_adult_emojis(text):
    return sum(text.count(e) for e in ADULT_EMOJIS)


# Chinese/CJK-ideograph detection — nochinese filter ke liye.
# Common CJK Unified Ideographs block (Chinese hanzi jyada tar isi range mein aate hain).
CHINESE_RE = re.compile(
    r'[\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff]'
)

def has_chinese_text(text):
    """True agar text mein Chinese (Han) characters ho."""
    if not text:
        return False
    return bool(CHINESE_RE.search(text))


def check_link(text):
    for match in URL_RE.findall(text):
        m = match if isinstance(match, str) else (match[0] if match[0] else '')
        if not m or len(m) < 5:
            continue
        if re.match(r'^[\d.]+$', m):
            continue
        if any(ab.lower() in m.lower() for ab in WHITELIST_ABBREVIATIONS):
            continue
        return True
    return False


# ── Bio Guard: domain-blacklist link mode ──
# "blacklist" mode only cares whether a link's DOMAIN is on the group's
# Bio Link Domains list (default: t.me, telegram.me) — e.g. a
# t.me/whatever link trips it, but an instagram.com link doesn't unless
# instagram.com was explicitly added too.
DEFAULT_BIO_LINK_DOMAINS = ["t.me", "telegram.me"]

def extract_domain(url: str) -> str:
    """host-only, lowercased, no scheme/www/path — 'https://www.T.ME/x?y'  -> 't.me'"""
    u = url.strip()
    if not u:
        return ""
    u = re.sub(r'^https?://', '', u, flags=re.I)
    u = re.sub(r'^www\.', '', u, flags=re.I)
    u = u.split('/')[0].split('?')[0].split('#')[0].split(':')[0]
    return u.lower()

def check_link_domain(text: str, domains) -> str | None:
    """Scan text for a URL whose domain matches (or is a subdomain of) one
    of `domains`. Returns the matched domain, or None if nothing hit."""
    dom_set = {d.lower().strip().lstrip('.') for d in (domains or []) if d}
    if not dom_set:
        return None
    for match in URL_RE.findall(text):
        m = match if isinstance(match, str) else (match[0] if match[0] else '')
        if not m or len(m) < 4:
            continue
        if re.match(r'^[\d.]+$', m):
            continue
        host = extract_domain(m)
        if not host:
            continue
        for d in dom_set:
            if host == d or host.endswith('.' + d):
                return d
    return None

def _bio_link_mode(g: dict) -> str:
    """Normalizes bio_link_guard — handles the old boolean values that
    existing groups may still have stored (True meant 'check all links')
    as well as the new 3-state string."""
    v = g.get("bio_link_guard", "all")
    if v is True:
        return "all"
    if v is False:
        return "off"
    if v in ("off", "blacklist", "all"):
        return v
    return "all"


async def check_username(text, wl_words, ctx, chat_id, members_only=False):
    """
    Returns True if text contains a @username that should be blocked.
    Exempt (always):
      - EXEMPT_USERNAMES (admin/owner/request/sbnime)
      - Whitelisted usernames

    members_only=False (default, all groups):
      ANY @username mention is blocked — external @mentions aren't allowed
      here at all.

    members_only=True (Premium only — /settings → 💎 Premium →
    👤 Allow Member Usernames):
      An @mention is allowed if it belongs to an actual member of THIS
      group (not left/kicked/banned). Everyone else's username is still
      blocked, same as before.
    """
    for match in USERNAME_RE.findall(text):
        uname = match.lower()
        # Skip permanently exempt usernames
        if uname in EXEMPT_USERNAMES:
            continue
        # Skip if admin whitelisted this username
        if wl_words and uname in [w.lower() for w in wl_words]:
            continue

        if not members_only:
            return True  # Usernames not allowed at all in this group

        # Premium mode: check if this @username is a member of the group.
        # NOTE: Telegram's getChatMember needs a numeric user_id — it can't
        # take "@username" directly — so we first resolve the username to
        # an ID via our seen-users index (same lookup /ban, /warn etc. use),
        # then check that ID's membership status in THIS group.
        is_member = False
        uid = db.find_user_by_username(uname)
        if uid is not None:
            try:
                member = await ctx.bot.get_chat_member(chat_id, uid)
                # Allow only active members
                if member.status in ("member", "administrator", "creator", "restricted"):
                    is_member = True
            except Exception:
                # Exception = not found in this group (left/kicked/never joined) → outsider
                is_member = False
        # If we've never seen this username before, we have no ID to check —
        # treat as outsider (can't confirm they're a member of this group).

        if not is_member:
            return True  # Block this message

    return False


def build_blacklist_re(words):
    if not words:
        return None
    pattern = r'\b(' + '|'.join(re.escape(w) for w in words) + r')\b'
    return re.compile(pattern, re.I)


def check_flood(chat_id, user_id):
    now = time.time()
    if chat_id not in FLOOD_DATA:
        FLOOD_DATA[chat_id] = {}
    if user_id not in FLOOD_DATA[chat_id]:
        FLOOD_DATA[chat_id][user_id] = []
    FLOOD_DATA[chat_id][user_id] = [t for t in FLOOD_DATA[chat_id][user_id] if now - t < FLOOD_WINDOW]
    FLOOD_DATA[chat_id][user_id].append(now)
    return len(FLOOD_DATA[chat_id][user_id]) > FLOOD_LIMIT


async def do_mute(ctx, chat_id, user_id, seconds=None):
    try:
        perms = ChatPermissions(
            can_send_messages=False, can_send_audios=False, can_send_documents=False,
            can_send_photos=False, can_send_videos=False, can_send_video_notes=False,
            can_send_voice_notes=False, can_send_polls=False, can_send_other_messages=False,
            can_add_web_page_previews=False, can_invite_users=False
        )
        if seconds and seconds > 0:
            until = datetime.now() + timedelta(seconds=max(35, seconds))
            await ctx.bot.restrict_chat_member(chat_id, user_id, perms, until_date=until)
        else:
            await ctx.bot.restrict_chat_member(chat_id, user_id, perms)
        db.inc_stat("mutes")
        return True
    except:
        return False


def format_duration(seconds):
    """Human-friendly duration string for warn/mute messages."""
    seconds = int(seconds)
    if seconds < 60:
        return f"{seconds}s"
    if seconds < 3600:
        return f"{seconds // 60}m"
    if seconds < 86400:
        return f"{seconds // 3600}h"
    if seconds < 604800:
        return f"{seconds // 86400}d"
    weeks = seconds // 604800
    return f"{weeks}w" if weeks > 1 else "1 week"


async def apply_warn_punishment(ctx, chat_id, usr, viol_txt, delete_delay=90):
    """
    The 'normal' escalating warn+mute punishment — same system every regular
    filter violation (link, blacklist, etc.) gets: W1 → 35s, W2 → 1m,
    W3 → 2m, W4 → 1 week — all of it scoped to THIS group only. Bio Guard
    reuses this once a flagged user's shadow-blocked message count crosses
    SHADOW_PUNISH_THRESHOLD, so repeated bio violations are punished exactly
    like a normal violation instead of just being silently deleted forever.

    NOTE: this never touches any group other than `chat_id` — there is no
    automatic "mute everywhere" here anymore. A true cross-group mute is
    only ever done by the owner-only `/gmute` DM command, or by a group
    admin's own `/gban` across the groups in their own community.

    Returns the warning count reached (1-4).
    """
    cnt = db.add_warning(chat_id, usr.id)

    _wd = db.get_warn_durations(chat_id)
    await do_mute(ctx, chat_id, usr.id, _wd[cnt])

    bars = "🟥" * cnt + "⬜" * (4 - cnt)
    mute_str = format_duration(_wd[cnt])
    if cnt == 4:
        next_str = "🔒 Max reached"
    else:
        next_str = f"W{cnt+1} ({format_duration(_wd[cnt+1])})"

    warn_colors = {1: "🟡", 2: "🟠", 3: "🔴", 4: "💀"}
    color = warn_colors.get(cnt, "⚠️")

    # ── Auto-unmute captcha — aasan math sawaal jo galti se mute
    # hue user khud solve karke apna mute + warning hata sake.
    # Group admin ise /settings → Filters se on/off kar sakta hai. ──
    warncaptcha_on = db.get_filters(chat_id).get("warncaptcha", True)
    if warncaptcha_on:
        cap_question, cap_answer, cap_options = generate_captcha()
        MUTE_CAPTCHA_PENDING[f"{chat_id}_{usr.id}"] = {"answer": cap_answer}
        captcha_block = (
            f"\n🔐 Tap the right answer to unmute + clear warnings:\n"
            f"      `{cap_question}`"
        )
        warn_kb = ckb_warn_captcha(chat_id, usr.id, cap_options)
        warn_kb_plain = kb_warn_captcha(chat_id, usr.id, cap_options)
    else:
        captcha_block = ""
        warn_kb = ckb_warn_actions(chat_id, usr.id)
        warn_kb_plain = kb_warn_actions(chat_id, usr.id)

    warn_text = (
        f"*{color} WARNING {cnt}/4*\n"
        f"👤 {user_mention(usr)}\n"
        f"📌 _{viol_txt}_\n"
        f"⏱ Muted: `{mute_str}` • Next: {next_str}\n"
        f"Progress: {bars}"
        f"{captcha_block}"
    )
    if warncaptcha_on:
        asyncio.create_task(_cleanup_mute_captcha(chat_id, usr.id, delete_delay + 5))
    warn_msg_id = await send_colored_message(chat_id, warn_text, warn_kb)
    if warn_msg_id:
        asyncio.create_task(delete_after(ctx, chat_id, warn_msg_id, delete_delay))
    else:
        notice = await ctx.bot.send_message(
            chat_id, warn_text, parse_mode='Markdown',
            reply_markup=warn_kb_plain
        )
        asyncio.create_task(delete_after(ctx, chat_id, notice.message_id, delete_delay))
    return cnt


async def do_unmute(ctx, chat_id, user_id):
    try:
        perms = ChatPermissions(
            can_send_messages=True, can_send_audios=True, can_send_documents=True,
            can_send_photos=True, can_send_videos=True, can_send_video_notes=True,
            can_send_voice_notes=True, can_send_polls=True, can_send_other_messages=True,
            can_add_web_page_previews=True, can_invite_users=True
        )
        await ctx.bot.restrict_chat_member(chat_id, user_id, perms)
        return True
    except:
        return False


async def do_ban(ctx, chat_id, user_id):
    try:
        # revoke_messages=True — Telegram khud is user ke pichhle 48 ghante
        # ke messages delete kar deta hai (platform ki hard limit, isse
        # zyada purane messages ke liye neeche purge_user_messages() dekhein).
        await ctx.bot.ban_chat_member(chat_id, user_id, revoke_messages=True)
        return True
    except:
        return False


async def purge_user_messages(ctx, chat_id, user_id):
    """
    User ke is group mein bheje hue TRACKED purane messages delete karta hai
    (bounded to last MSG_LOG_CAP=500, jitna bhi hamare paas record hai) —
    Telegram ka native revoke_messages sirf 48h cover karta hai, yeh usse
    aage bhi chalta hai. /ban aur /warn dono commands ke saath use hota hai.
    """
    ids = db.pop_message_ids(chat_id, user_id)
    for mid in ids:
        try:
            await ctx.bot.delete_message(chat_id, mid)
        except:
            pass
        await asyncio.sleep(0.05)  # flood-limit se bachne ke liye halka gap


async def do_unban(ctx, chat_id, user_id):
    try:
        await ctx.bot.unban_chat_member(chat_id, user_id)
        return True
    except:
        return False


async def delete_after(ctx, chat_id, msg_id, delay_seconds):
    await asyncio.sleep(delay_seconds)
    try:
        await ctx.bot.delete_message(chat_id, msg_id)
    except:
        pass



async def auto_delete_commands(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Group mein aane wale har command ko 10 min mein delete karo (sirf groups, broadcast nahi)."""
    msg = update.effective_message
    ch  = update.effective_chat
    if not msg or not ch or ch.type == "private":
        return

    # ── nocommands filter: doosre bots ke commands turant delete (non-admins se) ──
    try:
        text = msg.text or ""
        if text.startswith("/") and db.get_filters(ch.id).get("nocommands", False):
            cmd_word = text.split()[0][1:].split("@")[0].lower()
            is_foreign = cmd_word not in OWN_COMMANDS
            if is_foreign and msg.from_user and not await is_adm(ctx, ch.id, msg.from_user.id):
                try:
                    await msg.delete()
                except Exception:
                    pass
                return
    except Exception:
        pass

    asyncio.create_task(delete_after(ctx, ch.id, msg.message_id, 600))

async def global_mute_user(ctx, user_id, display_name=None):
    """4th warning → mute the user in every group silently. No broadcast message
    is sent to any group — the user is just restricted/blocked quietly."""
    db.add_gmute(user_id)
    for gid in db.get_all_groups():
        try:
            await do_mute(ctx, gid, user_id, GMUTE_DURATION)
            await asyncio.sleep(0.1)
        except:
            pass


async def global_unmute_user(ctx, user_id):
    """Warning clear ho ya mute manually hataya jaaye — user ko SAARE
    groups mein ek saath unmute karo aur uska gmute record bhi hata do.
    (Warnings clearing DB-level me instant hai, sirf Telegram-restriction
    hataana har group mein alag se karna padta hai — isliye yeh loop.)"""
    db.remove_gmute(user_id)   # gmute hatao + saare groups ki warnings clear karo
    for gid in db.get_all_groups():
        try:
            await do_unmute(ctx, gid, user_id)
            await asyncio.sleep(0.1)
        except:
            pass


# ═══════════════════════════════════════════════════════════
#  INLINE KEYBOARD BUILDERS
# ═══════════════════════════════════════════════════════════
# ── Menu ownership lock ─────────────────────────────────────
# Group me jab koi /start (ya /help, welcome msg, bot-added msg) chalata hai,
# to sirf USI user ko uske menu ke buttons dabaane dena hai — group ke
# baaki members ko nahi. (chat_id, message_id) -> user_id map karta hai.
MENU_OWNER = {}

# Telegram's "GroupAnonymousBot" pseudo-account id. Used whenever an admin/owner
# sends a message or command with "Remain Anonymous" turned ON.
ANON_ADMIN_ID = 1087968824

def _remember_menu_owner(chat_id, message_id, user_id):
    if message_id is None or user_id is None:
        return
    if len(MENU_OWNER) > 4000:
        MENU_OWNER.clear()
    MENU_OWNER[(chat_id, message_id)] = user_id

def _is_menu_owner(chat_id, message_id, user_id) -> bool:
    owner = MENU_OWNER.get((chat_id, message_id))
    if owner is None:
        # Old/untracked message (from before a restart) — don't block it.
        return True
    if owner == ANON_ADMIN_ID:
        # The panel was opened by an anonymous admin. Telegram always reveals
        # the clicker's REAL user id on a button tap — even for admins who are
        # posting anonymously — so it can never match the recorded owner id
        # here. Only an admin/owner can post anonymously in the first place,
        # so it's safe to allow the click through rather than lock everyone out.
        return True
    return owner == user_id


# ── /settings panel: idle auto-delete ───────────────────────
# Panel (ya uska koi bhi sub-view) agar 1 minute tak use nahi hota
# (koi button/tap/reply nahi aata) to khud-ba-khud delete ho jaata hai,
# taki group mein bekaar ke settings messages padhe na rahein.
PANEL_TIMERS = {}
PANEL_IDLE_SECONDS = 60

# ── Panel ↔ trigger-command linking ─────────────────────────
# Jab bot koi command (jaise /start, /help, /settings) ke jawab mein
# ek panel bhejta hai, uska (chat_id, panel_message_id) → trigger command
# ka message_id yahan store hota hai. Jab bhi panel khud delete hota hai
# (idle-timeout se ya Close button se), uske saath uska trigger command
# wala message bhi turant delete ho jaata hai — taaki group mein na
# panel bacha rahe, na woh /command wala message.
PANEL_TRIGGER = {}

def schedule_panel_autodelete(ctx, chat_id, message_id, delay=PANEL_IDLE_SECONDS, cmd_msg_id=None):
    key = (chat_id, message_id)
    if cmd_msg_id is not None:
        PANEL_TRIGGER[key] = cmd_msg_id
    old = PANEL_TIMERS.get(key)
    if old and not old.done():
        old.cancel()

    async def _job():
        try:
            await asyncio.sleep(delay)
            await ctx.bot.delete_message(chat_id, message_id)
        except Exception:
            pass
        finally:
            PANEL_TIMERS.pop(key, None)
            MENU_OWNER.pop(key, None)
            # Panel ke saath uska trigger command message bhi delete karo.
            trig_id = PANEL_TRIGGER.pop(key, None)
            if trig_id:
                try:
                    await ctx.bot.delete_message(chat_id, trig_id)
                except Exception:
                    pass
            # Panel gaya to uske andar ka pending text-input bhi cancel karo —
            # lekin sirf agar wo isi panel message ka pending input tha
            # (naya /settings session shuru ho chuka ho to usko mat chuo).
            for k, v in list(SETTINGS_PENDING.items()):
                if k[0] == chat_id and v.get("panel_msg_id") == message_id:
                    SETTINGS_PENDING.pop(k, None)

    PANEL_TIMERS[key] = asyncio.create_task(_job())

def cancel_panel_autodelete(chat_id, message_id):
    key = (chat_id, message_id)
    t = PANEL_TIMERS.pop(key, None)
    if t and not t.done():
        t.cancel()

async def _delete_panel_trigger(ctx, chat_id, message_id):
    """Panel ko manually (Close/Dismiss button se) delete karte waqt,
    uska linked trigger command-message bhi turant delete karo."""
    trig_id = PANEL_TRIGGER.pop((chat_id, message_id), None)
    if trig_id:
        try:
            await ctx.bot.delete_message(chat_id, trig_id)
        except Exception:
            pass


def kb_main_menu(is_admin=False):
    """Main menu — Settings & Admin Panel sirf admins/owner ko dikhte hain,
    normal user ko sirf wahi buttons dikhte hain jo vo use kar sakta hai."""
    rows = [
        [
            InlineKeyboardButton("⭐ 𝗠𝘆 𝗣𝗿𝗼𝗳𝗶𝗹𝗲", callback_data="rep:myprofile"),
            InlineKeyboardButton("🏆 𝗥𝗲𝗽 𝗕𝗼𝗮𝗿𝗱", callback_data="menu_repboard"),
        ],
        [
            InlineKeyboardButton("👤 𝗠𝘆 𝗖𝗼𝗺𝗺𝗮𝗻𝗱𝘀", callback_data="menu_user"),
            InlineKeyboardButton("📜 𝗥𝘂𝗹𝗲𝘀", callback_data="show_rules"),
        ],
        [
            InlineKeyboardButton("⚠️ 𝗪𝗮𝗿𝗻 𝗦𝘆𝘀𝘁𝗲𝗺", callback_data="menu_warns"),
        ],
        [
            InlineKeyboardButton("🛡️ 𝗣𝗿𝗼𝘁𝗲𝗰𝘁𝗶𝗼𝗻𝘀", callback_data="menu_protection"),
        ],
    ]
    if is_admin:
        rows[-1].append(InlineKeyboardButton("⚙️ 𝗦𝗲𝘁𝘁𝗶𝗻𝗴𝘀", callback_data="menu_settings"))
        rows.append([InlineKeyboardButton("👮 𝗔𝗱𝗺𝗶𝗻 𝗣𝗮𝗻𝗲𝗹", callback_data="menu_admin")])
    rows.append([InlineKeyboardButton("❌ 𝗖𝗹𝗼𝘀𝗲", callback_data="close_menu")])
    return InlineKeyboardMarkup(rows)

def kb_back():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("◀️ 𝗕𝗮𝗰𝗸 𝘁𝗼 𝗠𝗲𝗻𝘂", callback_data="menu_main")]
    ])

def kb_back_with_help():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("◀️ 𝗕𝗮𝗰𝗸", callback_data="menu_main"),
            InlineKeyboardButton("📜 𝗥𝘂𝗹𝗲𝘀", callback_data="show_rules"),
        ]
    ])

def kb_rules():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📜 𝗩𝗶𝗲𝘄 𝗥𝘂𝗹𝗲𝘀", callback_data="show_rules")],
        [InlineKeyboardButton("🆔 𝗠𝘆 𝗜𝗗", callback_data="show_id")],
    ])

def kb_warn_actions(chat_id, user_id):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔊 𝗨𝗻𝗺𝘂𝘁𝗲", callback_data=f"unmute_{chat_id}_{user_id}"),
            InlineKeyboardButton("🗑️ 𝗗𝗶𝘀𝗺𝗶𝘀𝘀", callback_data=f"dismiss_warn"),
        ]
    ])

def kb_warn_captcha(chat_id, user_id, options):
    """Warning message ke saath attach hone wala self-serve captcha —
    sirf jis user ko warning mili hai wahi ise solve kar sakta hai.
    Solve karte hi mute hatega aur SAARI warnings clear ho jaayengi."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(opt, callback_data=f"wcap_{chat_id}_{user_id}_{opt}") for opt in options[:2]],
        [InlineKeyboardButton(opt, callback_data=f"wcap_{chat_id}_{user_id}_{opt}") for opt in options[2:]],
        [
            InlineKeyboardButton("🔊 𝗨𝗻𝗺𝘂𝘁𝗲 (𝗔𝗱𝗺𝗶𝗻)", callback_data=f"unmute_{chat_id}_{user_id}"),
            InlineKeyboardButton("🗑️ 𝗗𝗶𝘀𝗺𝗶𝘀𝘀", callback_data=f"dismiss_warn"),
        ]
    ])

def kb_unban_button(chat_id, user_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔓 𝗨𝗻𝗯𝗮𝗻", callback_data=f"unban_{chat_id}_{user_id}")]
    ])

def kb_captcha(chat_id, user_id, options):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(opt, callback_data=f"captcha_{chat_id}_{user_id}_{opt}") for opt in options[:2]],
        [InlineKeyboardButton(opt, callback_data=f"captcha_{chat_id}_{user_id}_{opt}") for opt in options[2:]],
    ])

def kb_join_welcome():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📜 𝗚𝗿𝗼𝘂𝗽 𝗥𝘂𝗹𝗲𝘀", callback_data="show_rules"),
            InlineKeyboardButton("🆘 𝗛𝗲𝗹𝗽", callback_data="menu_user"),
        ],
        [
            InlineKeyboardButton("⚠️ 𝗪𝗮𝗿𝗻 𝗦𝘆𝘀𝘁𝗲𝗺", callback_data="menu_warns"),
        ]
    ])

def kb_bot_added():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📋 𝗖𝗼𝗺𝗺𝗮𝗻𝗱𝘀", callback_data="menu_admin"),
            InlineKeyboardButton("⚙️ 𝗦𝗲𝘁𝘂𝗽", callback_data="menu_settings"),
        ],
        [
            InlineKeyboardButton("🛡️ 𝗣𝗿𝗼𝘁𝗲𝗰𝘁𝗶𝗼𝗻𝘀", callback_data="menu_protection"),
        ]
    ])


# ── Colored keyboard row data (for direct Bot API calls) ──────
# Style: "primary"=blue, "success"=green, "danger"=red

def ckb_main_menu(is_admin=False):
    """Main menu colored rows — Settings & Admin Panel sirf admins/owner ko
    dikhte hain, normal user ko sirf wahi buttons dikhte hain jo vo use kar sakta hai."""
    rows = [
        [
            {"text": "⭐ 𝗠𝘆 𝗣𝗿𝗼𝗳𝗶𝗹𝗲",    "callback_data": "rep:myprofile",   "style": "success"},
            {"text": "🏆 𝗥𝗲𝗽 𝗕𝗼𝗮𝗿𝗱",     "callback_data": "menu_repboard",   "style": "success"},
        ],
        [
            {"text": "👤 𝗠𝘆 𝗖𝗼𝗺𝗺𝗮𝗻𝗱𝘀",   "callback_data": "menu_user",       "style": "primary"},
            {"text": "📜 𝗥𝘂𝗹𝗲𝘀",         "callback_data": "show_rules",      "style": "primary"},
        ],
        [
            {"text": "⚠️ 𝗪𝗮𝗿𝗻 𝗦𝘆𝘀𝘁𝗲𝗺",  "callback_data": "menu_warns",      "style": "danger"},
        ],
        [
            {"text": "🛡️ 𝗣𝗿𝗼𝘁𝗲𝗰𝘁𝗶𝗼𝗻𝘀",  "callback_data": "menu_protection", "style": "primary"},
        ],
    ]
    if is_admin:
        rows[-1].append({"text": "⚙️ 𝗦𝗲𝘁𝘁𝗶𝗻𝗴𝘀", "callback_data": "menu_settings", "style": "primary"})
        rows.append([{"text": "👮 𝗔𝗱𝗺𝗶𝗻 𝗣𝗮𝗻𝗲𝗹", "callback_data": "menu_admin", "style": "danger"}])
    rows.append([{"text": "❌ 𝗖𝗹𝗼𝘀𝗲", "callback_data": "close_menu", "style": "danger"}])
    return rows

def ckb_back():
    return [[{"text": "◀️ 𝗕𝗮𝗰𝗸 𝘁𝗼 𝗠𝗲𝗻𝘂", "callback_data": "menu_main", "style": "primary"}]]

def ckb_stats_refresh():
    return [[
        {"text": "🔄 𝗥𝗲𝗳𝗿𝗲𝘀𝗵",  "callback_data": "menu_stats", "style": "primary"},
        {"text": "◀️ 𝗕𝗮𝗰𝗸",     "callback_data": "menu_main",  "style": "primary"},
    ]]

def ckb_repinfo(user_id=0):
    return [[
        {"text": "◀️ 𝗕𝗮𝗰𝗸",     "callback_data": "menu_main",  "style": "primary"},
    ]]

def ckb_warn_actions(chat_id, user_id):
    return [[
        {"text": "🔊 𝗨𝗻𝗺𝘂𝘁𝗲",   "callback_data": f"unmute_{chat_id}_{user_id}", "style": "success"},
        {"text": "🗑️ 𝗗𝗶𝘀𝗺𝗶𝘀𝘀", "callback_data": "dismiss_warn",                "style": "danger"},
    ]]

def ckb_warn_captcha(chat_id, user_id, options):
    """Colored-button version of kb_warn_captcha (send_colored_message ke saath use hoti hai)."""
    return [
        [{"text": opt, "callback_data": f"wcap_{chat_id}_{user_id}_{opt}", "style": "primary"} for opt in options[:2]],
        [{"text": opt, "callback_data": f"wcap_{chat_id}_{user_id}_{opt}", "style": "primary"} for opt in options[2:]],
        [
            {"text": "🔊 𝗨𝗻𝗺𝘂𝘁𝗲 (𝗔𝗱𝗺𝗶𝗻)", "callback_data": f"unmute_{chat_id}_{user_id}", "style": "success"},
            {"text": "🗑️ 𝗗𝗶𝘀𝗺𝗶𝘀𝘀",         "callback_data": "dismiss_warn",                "style": "danger"},
        ]
    ]

def ckb_join_welcome():
    return [
        [
            {"text": "📜 𝗚𝗿𝗼𝘂𝗽 𝗥𝘂𝗹𝗲𝘀", "callback_data": "show_rules", "style": "success"},
            {"text": "🆘 𝗛𝗲𝗹𝗽",        "callback_data": "menu_user",  "style": "primary"},
        ],
        [
            {"text": "⚠️ 𝗪𝗮𝗿𝗻 𝗦𝘆𝘀𝘁𝗲𝗺", "callback_data": "menu_warns", "style": "danger"},
        ]
    ]

def ckb_bot_added():
    return [
        [
            {"text": "📋 𝗖𝗼𝗺𝗺𝗮𝗻𝗱𝘀",     "callback_data": "menu_admin",      "style": "primary"},
            {"text": "⚙️ 𝗦𝗲𝘁𝘂𝗽",        "callback_data": "menu_settings",   "style": "primary"},
        ],
        [
            {"text": "🛡️ 𝗣𝗿𝗼𝘁𝗲𝗰𝘁𝗶𝗼𝗻𝘀", "callback_data": "menu_protection", "style": "success"},
        ]
    ]

def ckb_rep_board(chat_id, user_id):
    return [
        [
            {"text": "🔄 𝗥𝗲𝗳𝗿𝗲𝘀𝗵",       "callback_data": f"rep:board:{chat_id}", "style": "primary"},
            {"text": "⭐ 𝗠𝘆 𝗣𝗿𝗼𝗳𝗶𝗹𝗲",    "callback_data": "rep:myprofile", "style": "success"},
        ],
        [
            {"text": "🌐 𝗚𝗹𝗼𝗯𝗮𝗹 𝗥𝗲𝗳𝗿𝗲𝘀𝗵","callback_data": "rep:global:0",          "style": "primary"},
        ]
    ]

def ckb_start_group(is_admin=False):
    rows = [[
        {"text": "📋 𝗖𝗼𝗺𝗺𝗮𝗻𝗱𝘀", "callback_data": "menu_main",   "style": "primary"},
        {"text": "📜 𝗥𝘂𝗹𝗲𝘀",    "callback_data": "show_rules",  "style": "success"},
    ]]
    if is_admin:
        rows.append([{"text": "⚙️ 𝗦𝗲𝘁𝘁𝗶𝗻𝗴𝘀", "callback_data": "cfg_main", "style": "primary"}])
    return rows


# ═══════════════════════════════════════════════════════════
#  VIOLATION CHECK
# ═══════════════════════════════════════════════════════════
async def check_violations(msg, group_bots, ctx, chat_id):
    """Returns (reason, matched_word). matched_word is only set for 'blacklist' hits,
    so the group can be told exactly which word triggered the action."""
    text = msg.text or msg.caption or ""

    if not msg.from_user:
        return None, None

    filt = db.get_filters(chat_id)

    if filt.get("antiflood", True) and check_flood(chat_id, msg.from_user.id):
        return "flood", None

    # ── New media-type filters (set via /settings → Filters) ──
    if filt.get("nolocations", False) and (msg.location is not None or msg.venue is not None):
        return "location", None

    if filt.get("nocontacts", False) and msg.contact is not None:
        return "contact", None

    if filt.get("novoice", False) and (msg.voice is not None or msg.video_note is not None):
        return "voice", None

    if filt.get("nohashtags", False) and text and "#" in text:
        return "hashtag", None

    if filt.get("nochinese", False) and has_chinese_text(text):
        return "chinese", None

    if filt.get("nopremiumemoji", False) and text and has_premium_emoji(msg):
        return "premium_emoji", None

    if filt.get("noquotes", False) and has_external_quote(msg):
        return "quote", None

    # Everything below this line is part of the "antispam" master filter
    if not filt.get("antispam", True):
        return None, None

    # Hidden link check (text_link entity)
    if filt.get("nolinks", True) and has_hidden_link(msg):
        return "hidden_link", None

    if filt.get("noforwards", True) and (msg.forward_date or msg.forward_from or msg.forward_from_chat):
        if msg.forward_from_chat:
            lc = await fetch_linked_channel(ctx, chat_id)
            if lc and msg.forward_from_chat.id == lc:
                pass
            else:
                return "forward", None
        else:
            return "forward", None

    if count_adult_emojis(text) >= 2:
        return "adult_emoji", None

    wl_words = db.get_whitelist(chat_id)

    if filt.get("blacklist", True):
        bl_words = db.get_blacklist(chat_id)
        if bl_words and text:
            bl_re = build_blacklist_re(bl_words)
            m = bl_re.search(text) if bl_re else None
            if m:
                wl_re = build_blacklist_re(wl_words) if (wl_words and filt.get("whitelist", True)) else None
                if not (wl_re and wl_re.search(text)):
                    return "blacklist", m.group(1)

        # Global blacklist — applies to ALL groups, unless this group disabled that word
        gbl_words = db.get_gblacklist()
        disabled_g = set(db.get_disabled_gwords(chat_id))
        gbl_words = [w for w in gbl_words if w.lower() not in disabled_g]
        if gbl_words and text:
            gbl_re = build_blacklist_re(gbl_words)
            m = gbl_re.search(text) if gbl_re else None
            if m:
                # Check global whitelist before blocking (respect group-level opt-outs too)
                gwl_words = db.get_gwhitelist()
                disabled_gw = set(db.get_disabled_gwhite(chat_id))
                gwl_words = [w for w in gwl_words if w.lower() not in disabled_gw]
                gwl_re = build_blacklist_re(gwl_words) if (gwl_words and filt.get("whitelist", True)) else None
                if not (gwl_re and gwl_re.search(text)):
                    return "blacklist", m.group(1)

    if filt.get("profanity", True):
        default_re = build_blacklist_re(DEFAULT_ADULT_WORDS)
        if default_re and default_re.search(text):
            return "adult_word", None

    # Stylish/fancy font check
    if text and has_stylish_font(text):
        return "stylish_font", None

    if filt.get("nolinks", True) and check_link(text):
        return "url", None

    if '@' in text:
        g_uname = db.get_group(chat_id)
        members_only_uname = (
            bool(g_uname.get("premium", False))
            and bool(g_uname.get("allow_member_usernames", False))
        )
        if await check_username(text, wl_words, ctx, chat_id, members_only=members_only_uname):
            return "username", None

    found_bots = BOT_RE.findall(text)
    for b in found_bots:
        if b.lower() not in group_bots:
            return "bot", None

    return None, None


# ═══════════════════════════════════════════════════════════
#  CAPTCHA
# ═══════════════════════════════════════════════════════════
def generate_captcha():
    a = random.randint(1, 15)
    b = random.randint(1, 15)
    op = random.choice(['+', '-', '*'])
    if op == '+':
        ans = a + b
    elif op == '-':
        ans = abs(a - b)
        a, b = max(a, b), min(a, b)
    else:
        ans = a * b
    question = f"{a} {op} {b} = ?"
    options = {str(ans)}
    while len(options) < 4:
        wrong = ans + random.randint(-5, 5)
        if wrong != ans and wrong >= 0:
            options.add(str(wrong))
    options = list(options)
    random.shuffle(options)
    return question, str(ans), options


async def send_captcha(ctx, chat_id, user_id, user_display):
    question, answer, options = generate_captcha()
    reply_markup = kb_captcha(chat_id, user_id, options)
    await do_mute(ctx, chat_id, user_id)

    msg = await ctx.bot.send_message(
        chat_id,
        f"🔐 *𝗩𝗘𝗥𝗜𝗙𝗜𝗖𝗔𝗧𝗜𝗢𝗡 𝗥𝗘𝗤𝗨𝗜𝗥𝗘𝗗*\n"
        f"{'─'*14}\n\n"
        f"👤 Welcome, {user_display}!\n\n"
        f"🧮 Solve this to unlock the chat:\n\n"
        f"      `{question}`\n\n"
        f"⏱ You have *60 seconds* to answer.\n"
        f"⚠️ A wrong answer means removal from the group.",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

    expire = time.time() + 60
    if chat_id not in CAPTCHA_PENDING:
        CAPTCHA_PENDING[chat_id] = {}
    CAPTCHA_PENDING[chat_id][user_id] = {
        "msg_id": msg.message_id,
        "answer": answer,
        "expire": expire
    }
    asyncio.create_task(captcha_timeout(ctx, chat_id, user_id, msg.message_id, expire))


async def captcha_timeout(ctx, chat_id, user_id, msg_id, expire):
    await asyncio.sleep(62)
    pending = CAPTCHA_PENDING.get(chat_id, {})
    if user_id in pending and pending[user_id]["expire"] <= time.time() + 2:
        try:
            await ctx.bot.ban_chat_member(chat_id, user_id)
            await asyncio.sleep(1)
            await ctx.bot.unban_chat_member(chat_id, user_id)
            await ctx.bot.delete_message(chat_id, msg_id)
            msg = await ctx.bot.send_message(
                chat_id,
                f"⛔ *𝗩𝗲𝗿𝗶𝗳𝗶𝗰𝗮𝘁𝗶𝗼𝗻 𝗙𝗮𝗶𝗹𝗲𝗱*\n\n"
                f"User `{user_id}` was removed for not completing verification in time.",
                parse_mode='Markdown'
            )
            asyncio.create_task(delete_after(ctx, chat_id, msg.message_id, 10))
        except:
            pass
        CAPTCHA_PENDING[chat_id].pop(user_id, None)


async def captcha_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data  = query.data
    parts = data.split("_")
    if len(parts) < 4:
        return

    _, chat_id_s, user_id_s, chosen = parts[0], parts[1], parts[2], parts[3]
    chat_id = int(chat_id_s)
    user_id = int(user_id_s)

    if query.from_user.id != user_id:
        await query.answer("🔒 This verification isn't for you.", show_alert=True)
        return

    pending = CAPTCHA_PENDING.get(chat_id, {}).get(user_id)
    if not pending:
        await query.answer("⏰ This verification has expired.", show_alert=True)
        return

    if chosen == pending["answer"]:
        CAPTCHA_PENDING[chat_id].pop(user_id, None)
        await do_unmute(ctx, chat_id, user_id)
        await query.message.delete()
        msg = await ctx.bot.send_message(
            chat_id,
            f"✅ *𝗩𝗲𝗿𝗶𝗳𝗶𝗰𝗮𝘁𝗶𝗼𝗻 𝗣𝗮𝘀𝘀𝗲𝗱*\n\n"
            f"Welcome to the group — you're all set. 🎉",
            parse_mode='Markdown'
        )
        asyncio.create_task(delete_after(ctx, chat_id, msg.message_id, 15))
        await query.answer("✅ Correct — welcome!")
    else:
        await query.answer("❌ Wrong answer — try again.", show_alert=True)


async def _cleanup_mute_captcha(chat_id, user_id, delay):
    """Warn-message auto-delete hone ke baad stale pending captcha hata do."""
    await asyncio.sleep(delay)
    MUTE_CAPTCHA_PENDING.pop(f"{chat_id}_{user_id}", None)


async def mute_captcha_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Warning/mute ke saath attach captcha ka handler.
    Sahi jawab → us user ka mute turant hatta hai AUR uski saari
    warnings clear ho jaati hain (jaise /resetwarnings chala ho)."""
    query = update.callback_query
    data  = query.data
    parts = data.split("_")
    if len(parts) < 4:
        await query.answer()
        return

    _, chat_id_s, user_id_s, chosen = parts[0], parts[1], parts[2], parts[3]
    try:
        chat_id = int(chat_id_s)
        user_id = int(user_id_s)
    except ValueError:
        await query.answer()
        return

    if query.from_user.id != user_id:
        await query.answer("🔒 This captcha is only for the muted user.", show_alert=True)
        return

    key = f"{chat_id}_{user_id}"
    pending = MUTE_CAPTCHA_PENDING.get(key)
    if not pending:
        await query.answer("⏰ This captcha is no longer valid.", show_alert=True)
        return

    if chosen == pending["answer"]:
        MUTE_CAPTCHA_PENDING.pop(key, None)
        # Answer the callback FIRST — this is what makes Telegram show the
        # "verified" tap instantly instead of waiting for unmute+DB work.
        await query.answer("✅ Verified!")

        # Every warn-mute (W1-W4) is scoped to this one group only now —
        # a real cross-group gmute (owner's /gmute) can't be solved away
        # by a captcha, so this always just unmutes here.
        db.reset_warnings(chat_id, user_id)
        await do_unmute(ctx, chat_id, user_id)
        scope_line = "🔊 Unmuted in this group — you can send messages again."

        success_text = (
            f"✅ *Captcha Verified*\n"
            f"👤 {user_mention(query.from_user)}\n"
            f"{scope_line}\n"
            f"♻️ Warnings cleared."
        )
        try:
            await query.message.edit_text(success_text, parse_mode='Markdown')
        except Exception:
            pass
    else:
        await query.answer("❌ Wrong answer — try again!", show_alert=True)


# ═══════════════════════════════════════════════════════════
#  PREMIUM: Bio Guard — manual "🔄 Recheck" button
# ═══════════════════════════════════════════════════════════
async def bio_recheck_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """User taps '🔄 Recheck My Bio' on a Bio Guard notice. Forces an
    immediate fresh get_chat() + re-scan, bypassing SHADOW_RECHECK_SEC —
    a reliable, explicit alternative to waiting for the next message to
    (maybe) trigger the automatic recheck."""
    query = update.callback_query
    data = query.data
    parts = data.split("_")
    if len(parts) < 3:
        await query.answer()
        return

    try:
        chat_id = int(parts[1])
        user_id = int(parts[2])
    except ValueError:
        await query.answer()
        return

    if query.from_user.id != user_id:
        await query.answer("🔒 Only the person named above can use this button.", show_alert=True)
        return

    key = (chat_id, user_id)
    now = time.time()
    last = BIORECHECK_COOLDOWN.get(key, 0)
    if now - last < BIORECHECK_COOLDOWN_SEC:
        await query.answer("⏳ Give it a couple seconds and try again.", show_alert=True)
        return
    BIORECHECK_COOLDOWN[key] = now

    shadow = db.shadow_blacklist_get(chat_id, user_id)
    if not shadow:
        await query.answer("✅ You're already clear — nothing to recheck!", show_alert=True)
        try:
            await query.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass
        return

    await query.answer("🔍 Rechecking your bio…")

    try:
        full = await ctx.bot.get_chat(user_id)
        bio = getattr(full, "bio", None) or ""
        bio_fetch_ok = True
    except Exception:
        bio = ""
        bio_fetch_ok = False

    if not bio_fetch_ok:
        await query.answer("⚠️ Couldn't fetch your profile right now — try again in a moment.", show_alert=True)
        return

    g_settings = db.get_group(chat_id)
    kind, matched = await bio_violation(bio, chat_id, g_settings, ctx)

    if not kind:
        # Clean — clear shadow status same as the automatic path does.
        db.shadow_blacklist_remove(chat_id, user_id)
        SHADOW_MSG_COUNT.pop(key, None)
        SHADOW_FLOOD.pop(key, None)
        FLAGGED_CHECK_CACHE.pop(key, None)
        try:
            await query.message.edit_text(
                f"✅ {user_mention(query.from_user)}, your bio is clean now — you're all set. 🎉",
                parse_mode='Markdown'
            )
        except Exception:
            try:
                notice = await ctx.bot.send_message(
                    chat_id,
                    f"✅ {user_mention(query.from_user)}, your bio is clean now — you're all set. 🎉",
                    parse_mode='Markdown'
                )
                asyncio.create_task(delete_after(ctx, chat_id, notice.message_id, 20))
            except Exception:
                pass
    else:
        # Still violating — keep the shadow record (and its reason/matched)
        # in sync in case what's left is different from the original hit.
        db.shadow_blacklist_add(chat_id, user_id, kind, matched)
        what = _bio_violation_what(kind, matched, in_bio=True)
        await query.answer(f"❌ Still not clean — {what}. Remove it and tap again.", show_alert=True)


# ═══════════════════════════════════════════════════════════
#  MENU CALLBACK HANDLER
# ═══════════════════════════════════════════════════════════
# ── /start-menu family: idle auto-delete (same as /settings) ──────
# menu_main / show_rules / menu_warns / filter-ke-jaisi koi bhi page —
# jahan bhi user navigate kare — agar owner (jisne panel khola tha)
# 1 minute tak koi bhi button na dabaye, panel khud delete ho jaayega.
# Actual dispatch logic "_menu_callback_dispatch" mein hai (unchanged);
# yeh wrapper sirf har handled click ke baad timer ko (re)start karta hai.
async def menu_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data  = query.data if query else None
    chat  = update.effective_chat

    is_owner_click = True
    if chat and chat.type != "private" and data and not data.startswith(("unmute_", "unban_", "dismiss_warn")):
        is_owner_click = _is_menu_owner(chat.id, query.message.message_id, query.from_user.id)

    await _menu_callback_dispatch(update, ctx)

    # Sirf tab timer (re)start karo jab click asli owner ne kiya ho aur
    # panel abhi bhi khula ho (close/dismiss/warn-actions apni delete-lifecycle
    # khud handle karte hain, unhe idle-timer se chhedna nahi hai).
    if (
        is_owner_click and chat and chat.type != "private" and data
        and data not in ("close_menu", "dismiss_warn")
        and not data.startswith(("unban_", "unmute_"))
    ):
        try:
            schedule_panel_autodelete(ctx, chat.id, query.message.message_id)
        except Exception:
            pass


async def _menu_callback_dispatch(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data  = query.data
    chat  = update.effective_chat

    # 🔒 In groups, personal navigation buttons (menu_*, show_*, close_menu)
    # should only work for the user who ran /start (or help/welcome).
    # unmute_ / unban_ / dismiss_warn are admin-action buttons, so exclude them.
    if chat and chat.type != "private" and not data.startswith(("unmute_", "unban_", "dismiss_warn")):
        if not _is_menu_owner(chat.id, query.message.message_id, query.from_user.id):
            await query.answer(
                "🔒 This menu can only be used by whoever opened it!\n"
                "Open your own menu with /start.",
                show_alert=True
            )
            return

    if data == "menu_main":
        text = (
            f"🛡️ *𝗚𝗨𝗔𝗥𝗗𝗜𝗔𝗡 𝗕𝗢𝗧* — v10.0\n"
            f"_Group Protection Bot_\n"
            f"{'─'*14}\n\n"
            f"_Choose a category below 👇_"
        )
        # Try colored Bot API edit
        chat_id = update.effective_chat.id if update.effective_chat else 0
        is_admin_here = (query.from_user.id == OWNER_ID) or await is_adm(ctx, chat_id, query.from_user.id)
        await query.answer()
        success = await edit_colored_message(chat_id, query.message.message_id, text, ckb_main_menu(is_admin_here))
        if not success:
            await query.edit_message_text(text, reply_markup=kb_main_menu(is_admin_here), parse_mode='Markdown')
        return

    elif data == "menu_user":
        text = (
            f"*👤 YOUR COMMANDS*\n"
            f"{'─'*14}\n\n"
            f"📜 `/rules` — View group rules\n"
            f"⚠️ `/warnings` — Check your warnings\n"
            f"⭐ `/rep` — Guardian Profile Card\n"
            f"🏆 `/repboard` — Group + Global Rep Board\n"
            f"🆔 `/id` — Your Telegram ID\n\n"
            f"{'─'*14}\n"
            f"💎 *𝗥𝗘𝗣𝗨𝗧𝗔𝗧𝗜𝗢𝗡*\n"
            f"_Thank You → +{REP_PER_THANK} Rep | Clear a warning → {REP_PER_WARN_REMOVE} Rep_"
        )
        await query.answer()
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("◀️ 𝗕𝗮𝗰𝗸", callback_data="menu_main"),
                    InlineKeyboardButton("🏆 𝗥𝗲𝗽 𝗕𝗼𝗮𝗿𝗱", callback_data="menu_repboard"),
                ],
                [InlineKeyboardButton("❌ 𝗖𝗹𝗼𝘀𝗲", callback_data="close_menu")],
            ]),
            parse_mode='Markdown'
        )
        return

    elif data == "menu_admin":
        # Only admins / owner can see this panel
        ch_id = update.effective_chat.id if update.effective_chat else 0
        if query.from_user.id != OWNER_ID and not await is_adm(ctx, ch_id, query.from_user.id):
            await query.answer("🔒 Admins only.", show_alert=True)
            return
        text = (
            f"*👮 𝗔𝗗𝗠𝗜𝗡 𝗖𝗢𝗠𝗠𝗔𝗡𝗗𝗦*\n"

            f"{'─'*14}\n\n"
            f"🔇 `/mute [sec]` — Mute _(reply)_\n"
            f"🔊 `/unmute` — Unmute _(reply)_\n"
            f"🔨 `/ban` — Ban _(reply)_\n"
            f"🔓 `/unban <id>` — Unban user\n"
            f"⚠️ `/warn` — Give warning _(reply)_\n"
            f"♻️ `/resetwarnings` — Reset warns _(reply)_\n"
            f"🗑️ `/del` — Delete message _(reply)_\n"
            f"🧹 `/purge` — Bulk delete from reply\n"
            f"🧪 `/testmute` — Test 35s mute _(reply)_\n"
            f"👑 `/immortal <id>` — Grant immunity\n"
            f"💀 `/unimmortal <id>` — Remove immunity\n"
            f"📋 `/immortals` — List immune users\n"
            f"📚 `/addteacher` `/removeteacher` `/teachers`\n\n"
            f"{'─'*14}\n"
            f"🏆 `/repboard`"
        )
        await query.answer()
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("◀️ 𝗕𝗮𝗰𝗸", callback_data="menu_main"),
                    InlineKeyboardButton("⚙️ 𝗦𝗲𝘁𝘁𝗶𝗻𝗴𝘀", callback_data="menu_settings"),
                ],
                [InlineKeyboardButton("❌ 𝗖𝗹𝗼𝘀𝗲", callback_data="close_menu")],
            ]),
            parse_mode='Markdown'
        )
        return

    elif data == "menu_protection":
        text = (
            f"🛡️ *𝗔𝗖𝗧𝗜𝗩𝗘 𝗣𝗥𝗢𝗧𝗘𝗖𝗧𝗜𝗢𝗡𝗦*\n"
            f"{'─'*14}\n\n"
            f"🤖 External bot usernames\n"
            f"👤 External @mentions\n"
            f"   ✅ _@admin, @owner, @request: exempt_\n"
            f"   ✅ _Whitelisted words & members: exempt_\n"
            f"🔗 All links & URLs\n"
            f"🕵️ Hidden hyperlinks (text-link entities)\n"
            f"✍️ Stylish / Unicode fancy fonts\n"
            f"↩️ Forwarded messages\n"
            f"   ✅ _Linked-channel forwards allowed_\n"
            f"🔞 Adult emojis (2+ triggers action)\n"
            f"🚫 Profanity filter — built-in word list\n"
            f"⛔ Custom blacklist words\n"
            f"🌐 Global blacklist (owner-managed)\n"
            f"🌊 Anti-flood system\n"
            f"🎭 Captcha for new members\n"
            f"🗑️ Sticker/GIF auto-delete\n"
            f"⏱️ Message auto-delete timer\n\n"
            f"{'─'*14}\n"
            f"_Every protection runs automatically._"
        )
        await query.answer()
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("◀️ 𝗕𝗮𝗰𝗸", callback_data="menu_main")],
                [InlineKeyboardButton("❌ 𝗖𝗹𝗼𝘀𝗲", callback_data="close_menu")],
            ]),
            parse_mode='Markdown'
        )
        return

    elif data == "menu_settings":
        ch_id = update.effective_chat.id if update.effective_chat else 0
        if query.from_user.id != OWNER_ID and not await is_adm(ctx, ch_id, query.from_user.id):
            await query.answer("🔒 Admins only.", show_alert=True)
            return
        await query.answer()
        _remember_menu_owner(ch_id, query.message.message_id, query.from_user.id)
        await _cfg_edit(query, ch_id, _settings_overview_text(ch_id), kb_settings_main(ch_id))
        return

    elif data == "menu_warns":
        text = (
            f"*⚠️ 𝗪𝗔𝗥𝗡𝗜𝗡𝗚 𝗦𝗬𝗦𝗧𝗘𝗠*\n"

            f"{'─'*14}\n\n"
            f"🟡 *W1* → 35 second mute\n"
            f"   ⏱ _Expires after 6 hours_\n\n"
            f"🟠 *W2* → 60 second mute\n"
            f"   ⏱ _Expires after 16 hours_\n\n"
            f"🔴 *W3* → 120 second mute\n"
            f"   ⏱ _Expires after 27 hours_\n\n"
            f"💀 *W4* → 1 week mute\n"
            f"   📍 _Applied in this group only_\n"
            f"   🔐 _Only an admin can lift it_\n\n"
            f"{'─'*14}\n"
            f"💡 *𝙏𝙞𝙥:* Reply with “thank you” to clear one warning.\n"
            f"_Violations trigger warnings automatically._"
        )
        await query.answer()
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("◀️ 𝗕𝗮𝗰𝗸", callback_data="menu_main"),
                    InlineKeyboardButton("⚠️ 𝗠𝘆 𝗪𝗮𝗿𝗻𝗶𝗻𝗴𝘀", callback_data="show_my_warnings"),
                ],
                [InlineKeyboardButton("❌ 𝗖𝗹𝗼𝘀𝗲", callback_data="close_menu")],
            ]),
            parse_mode='Markdown'
        )
        return

    elif data == "menu_stats":
        s = db.get_stats()
        groups = db.get_all_groups()
        gmutes = db.get_all_gmutes()
        text = (
            f"*📊 BOT STATISTICS*\n"

            f"{'─'*14}\n\n"
            f"👥 Groups Active:     `{len(groups)}`\n"
            f"⚠️ Warnings Given:    `{s.get('warnings', 0)}`\n"
            f"🔇 Mutes Executed:    `{s.get('mutes', 0)}`\n"
            f"📨 Msgs Scanned:      `{s.get('scanned', 0)}`\n"
            f"🗓️ Global Mutes:      `{len(gmutes)}`\n\n"
            f"{'─'*14}\n"
            f"🛡️ Status:  {ICON_ON} *Online & running*\n"
            f"🗄️ Database: {ICON_ON} *Connected*"
        )
        await query.answer()
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("🔄 𝗥𝗲𝗳𝗿𝗲𝘀𝗵", callback_data="menu_stats"),
                    InlineKeyboardButton("◀️ 𝗕𝗮𝗰𝗸", callback_data="menu_main"),
                ],
                [InlineKeyboardButton("❌ 𝗖𝗹𝗼𝘀𝗲", callback_data="close_menu")],
            ]),
            parse_mode='Markdown'
        )
        return

    elif data == "menu_repboard":
        # Actual leaderboard directly — group + global
        ch_id = update.effective_chat.id if update.effective_chat else 0
        medals = ["🥇", "🥈", "🥉"]
        rank_e  = ["4️⃣","5️⃣","6️⃣","7️⃣","8️⃣","9️⃣","🔟"]

        def _lines(entries, key_pts, key_id):
            if not entries:
                return ["  📉 _No data yet!_"]
            out = []
            for i, doc in enumerate(entries[:7]):
                medal = medals[i] if i < 3 else rank_e[i-3]
                name  = md_esc(str(doc.get("name") or doc.get(key_id, "?")))
                pts   = doc.get(key_pts, 0)
                out.append(f"{medal} {name}  —  `{pts}` rep")
            return out

        group_top  = db.get_reputation_top(ch_id, limit=7) if ch_id else []
        global_top = db.get_global_reputation_top(limit=7)
        group_lines  = _lines(group_top,  "points", "user_id")
        global_lines = _lines(global_top, "total",  "_id")

        text = (
            f"*🏆 REPUTATION BOARD*\n"

            f"{'─'*14}\n\n"
            f"🏠 *𝗚𝗥𝗢𝗨𝗣 𝗧𝗢𝗣*\n"
            f"{'┄'*14}\n"
            + "\n".join(group_lines) +
            f"\n\n🌐 *𝗚𝗟𝗢𝗕𝗔𝗟 𝗧𝗢𝗣*\n"
            f"{'┄'*14}\n"
            + "\n".join(global_lines) +
            f"\n\n{'─'*14}\n"
            f"💡 _Reply 'Thank You' to give rep_"
        )
        user_id = query.from_user.id if query.from_user else 0
        await query.answer()
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("🔄 𝗥𝗲𝗳𝗿𝗲𝘀𝗵", callback_data="menu_repboard"),
                    InlineKeyboardButton("⭐ 𝗠𝘆 𝗣𝗿𝗼𝗳𝗶𝗹𝗲", callback_data="rep:myprofile"),
                ],
                [
                    InlineKeyboardButton("📊 𝗚𝗿𝗼𝘂𝗽 𝗥𝗮𝗻𝗸", callback_data=f"rep:board:{ch_id}"),
                    InlineKeyboardButton("🌐 𝗚𝗹𝗼𝗯𝗮𝗹 𝗥𝗮𝗻𝗸", callback_data="rep:global:0"),
                ],
                [
                    InlineKeyboardButton("◀️ 𝗕𝗮𝗰𝗸", callback_data="menu_main"),
                    InlineKeyboardButton("❌ 𝗖𝗹𝗼𝘀𝗲", callback_data="close_menu"),
                ],
            ]),
            parse_mode='Markdown'
        )
        return

    elif data == "menu_repinfo":
        # Keep for backwards compat — redirect to repboard
        ch_id = update.effective_chat.id if update.effective_chat else 0
        await query.answer()
        query.data = "menu_repboard"
        # Re-trigger via same logic
        await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🏆 𝗢𝗽𝗲𝗻 𝗥𝗲𝗽 𝗕𝗼𝗮𝗿𝗱", callback_data="menu_repboard")]
        ]))
        return

    elif data == "menu_premium":
        chat_id = update.effective_chat.id if update.effective_chat else 0
        g = db.get_group(chat_id) if chat_id else {}
        is_prem = g.get("premium", False)
        text = (
            f"*💎 𝗣𝗥𝗘𝗠𝗜𝗨𝗠 𝗣𝗥𝗢𝗧𝗘𝗖𝗧𝗜𝗢𝗡*\n"

            f"{'─'*14}\n\n"
            f"Status: {'🟢 *Active*' if is_prem else '🔴 *Not active in this group*'}\n\n"
            f"{'─'*14}\n"
            f"*𝙒𝙝𝙖𝙩 𝙄𝙩 𝘼𝙙𝙙𝙨:*\n"
            f"  ✏️ *Edit Guard* — rechecks edited messages\n"
            f"       against your filters, not just new ones\n"
            f"  🕵️ *Bio Guard* — scans member bios for links\n"
            f"       or blacklisted words, shadow-blocks them\n"
            f"  👤 *Member Username Guard* — optionally allow only\n"
            f"       this group's own members to send a @username\n\n"
            f"{'─'*14}\n"
            f"_Contact the bot owner to upgrade this group._"
        )
        await query.answer()
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("◀️ 𝗕𝗮𝗰𝗸", callback_data="menu_main")],
                [InlineKeyboardButton("❌ 𝗖𝗹𝗼𝘀𝗲", callback_data="close_menu")],
            ]),
            parse_mode='Markdown'
        )
        return

    elif data == "show_rules":
        chat_id = update.effective_chat.id if update.effective_chat else 0
        custom = db.get_rules(chat_id) if chat_id else None
        if custom:
            rules_text = (
                f"📜 *𝗚𝗥𝗢𝗨𝗣 𝗥𝗨𝗟𝗘𝗦*\n"
                f"{'─'*14}\n\n"
                f"{custom}\n\n"
                f"{'─'*14}\n"
                f"_Follow the rules to avoid punishment._"
            )
        else:
            rules_text = (
                f"📜 *𝗚𝗥𝗢𝗨𝗣 𝗥𝗨𝗟𝗘𝗦*\n"
                f"{'─'*14}\n\n"
                f"🚫 *𝙉𝙊𝙏 𝘼𝙇𝙇𝙊𝙒𝙀𝘿:*\n\n"
                f"  1️⃣  🤖 External bot usernames\n"
                f"  2️⃣  🔗 Links & URLs\n"
                f"  3️⃣  ↩️ Forwarded messages\n"
                f"       ✅ _Linked channel: allowed_\n"
                f"  4️⃣  🔞 Adult emojis (2+)\n"
                f"  5️⃣  🗣️ Abusive language\n"
                f"  6️⃣  ⛔ Blacklisted words\n"
                f"  7️⃣  🌊 Spamming / Flooding\n\n"
                f"{'─'*14}\n\n"
                f"⚠️ *𝙋𝙐𝙉𝙄𝙎𝙃𝙈𝙀𝙉𝙏 𝙎𝘾𝘼𝙇𝙀:*\n"
                f"  • 1st offense → 35s mute\n"
                f"  • 2nd offense → 60s mute\n"
                f"  • 3rd offense → 120s mute\n"
                f"  • 4th offense → 1 WEEK (ALL groups!)\n\n"
                f"{'─'*14}\n"
                f"✅ _Respect the rules & enjoy the group!_"
            )
        await query.answer()
        await query.edit_message_text(
            rules_text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("◀️ 𝗕𝗮𝗰𝗸", callback_data="menu_main")],
                [InlineKeyboardButton("❌ 𝗖𝗹𝗼𝘀𝗲", callback_data="close_menu")],
            ]),
            parse_mode='Markdown'
        )
        return

    elif data == "show_id":
        u = query.from_user
        await query.answer(f"Your ID: {u.id}", show_alert=True)
        return

    elif data == "show_my_warnings":
        usr = query.from_user
        if not usr:
            await query.answer("❌ Could not identify the user!", show_alert=True)
            return
        ch_id = update.effective_chat.id if update.effective_chat else 0
        if not ch_id:
            await query.answer("❌ Use this in a group!", show_alert=True)
            return
        count = db.get_warnings(ch_id, usr.id)
        bars  = "🟥" * count + "⬜" * (4 - count)
        status = {0: "✅ Clean!", 1: "🟡 W1", 2: "🟠 W2", 3: "🔴 W3", 4: "💀 W4"}.get(count, "❓")
        await query.answer(
            f"⚠️ Your Warnings: {count}/4\n{bars}\nStatus: {status}",
            show_alert=True
        )
        return

    elif data.startswith("unban_"):
        parts = data.split("_")
        if len(parts) >= 3:
            try:
                c_id = int(parts[1])
                u_id = int(parts[2])
                if await is_adm(ctx, c_id, query.from_user.id) or query.from_user.id == OWNER_ID:
                    await do_unban(ctx, c_id, u_id)
                    await query.answer("✅ User unbanned!", show_alert=True)
                    await query.message.edit_reply_markup(reply_markup=None)
                else:
                    await query.answer("🔒 Admins only.", show_alert=True)
            except:
                await query.answer("❌ Error!", show_alert=True)
        return

    elif data.startswith("unmute_"):
        # unmute_{chat_id}_{user_id}
        parts = data.split("_")
        if len(parts) >= 3:
            try:
                c_id = int(parts[1])
                u_id = int(parts[2])
                if await is_adm(ctx, c_id, query.from_user.id) or query.from_user.id == OWNER_ID:
                    db.reset_warnings(c_id, u_id)
                    await do_unmute(ctx, c_id, u_id)
                    await query.answer("✅ User unmuted in this group!", show_alert=True)
                    await query.message.edit_reply_markup(reply_markup=None)
                else:
                    await query.answer("🔒 Admins only.", show_alert=True)
            except:
                await query.answer("❌ Error!", show_alert=True)
        return

    elif data == "dismiss_warn":
        if await is_adm(ctx, update.effective_chat.id if update.effective_chat else 0, query.from_user.id) or query.from_user.id == OWNER_ID:
            ch_id = update.effective_chat.id if update.effective_chat else 0
            try:
                await query.message.delete()
            except:
                pass
            await _delete_panel_trigger(ctx, ch_id, query.message.message_id)
        else:
            await query.answer("🔒 Admins only.", show_alert=True)
        return

    elif data == "close_menu":
        cancel_panel_autodelete(chat.id, query.message.message_id)
        try:
            await query.message.delete()
        except:
            await query.answer("✅ Closed!")
        await _delete_panel_trigger(ctx, chat.id, query.message.message_id)
        return

    await query.answer()


# ═══════════════════════════════════════════════════════════
#  COMMANDS
# ═══════════════════════════════════════════════════════════

# ─── /start ─────────────────────────────────────────────────
async def start_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    u  = update.effective_user
    ch = update.effective_chat

    # Group me /start → sirf ek line with button
    if ch.type != "private":
        is_admin_here = (u.id == OWNER_ID) or await is_adm(ctx, ch.id, u.id)
        start_text = (
            f"🛡️ *𝗚𝘂𝗮𝗿𝗱𝗶𝗮𝗻* is online and protecting this group.\n"
            f"_Type /help to see all commands._"
        )
        if is_admin_here:
            start_text += f"\n⚙️ _Admins — open /settings for the control panel._"
        buttons = [
            [
                InlineKeyboardButton("📋 𝗖𝗼𝗺𝗺𝗮𝗻𝗱𝘀", callback_data="menu_main"),
                InlineKeyboardButton("📜 𝗥𝘂𝗹𝗲𝘀", callback_data="show_rules"),
            ]
        ]
        if is_admin_here:
            buttons.append([InlineKeyboardButton("⚙️ 𝗦𝗲𝘁𝘁𝗶𝗻𝗴𝘀", callback_data="cfg_main")])
        msg_id = await send_colored_message(ch.id, start_text, ckb_start_group(is_admin_here))
        if not msg_id:
            sent = await update.message.reply_text(
                start_text,
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(buttons)
            )
            _remember_menu_owner(ch.id, sent.message_id, u.id)
            schedule_panel_autodelete(ctx, ch.id, sent.message_id, cmd_msg_id=update.message.message_id)
        else:
            _remember_menu_owner(ch.id, msg_id, u.id)
            schedule_panel_autodelete(ctx, ch.id, msg_id, cmd_msg_id=update.message.message_id)
        return

    # DM — Owner panel
    if u.id == OWNER_ID:
        text = (
            f"👑 *𝗢𝗪𝗡𝗘𝗥 𝗖𝗢𝗡𝗧𝗥𝗢𝗟 𝗣𝗔𝗡𝗘𝗟*\n"
            f"_v10.0 · MongoDB · AI-Powered_\n"
            f"{'─'*14}\n\n"
            f"🌐 *𝗚𝗟𝗢𝗕𝗔𝗟*\n\n"
            f"  📢 `/broadcast <msg>` — Message every group\n"
            f"  👥 `/groups` — Active group count\n"
            f"  📊 `/stats` — Full bot statistics\n"
            f"  🗓️ `/globalmutes` — View global mutes\n"
            f"  🌐 `/autodelete <min>` — Set global default\n\n"
            f"{'─'*14}\n"
            f"⚡ *𝗠𝗢𝗗𝗘𝗥𝗔𝗧𝗜𝗢𝗡*\n\n"
            f"  💀 `/fban <id> [reason]` — Ban across all groups\n"
            f"  ✅ `/gunban <id>` — Reverse a global ban\n"
            f"  🔇 `/gmute <id>` — Mute across all groups _(DM only)_\n"
            f"  🔊 `/unmute <id>` — Unmute everywhere\n"
            f"  🧹 `/gclearwarn <id>` — Clear all warnings\n"
            f"  ⚡ `/power <id>` — Grant ban authority\n"
            f"  🔻 `/unpower <id>` — Revoke ban authority\n\n"
            f"{'─'*14}\n"
            f"💎 *𝗣𝗥𝗘𝗠𝗜𝗨𝗠*\n\n"
            f"  ✅ `/premium <id> on` — Enable for a group\n"
            f"  🔴 `/premium <id> off` — Disable for a group\n"
            f"  📋 `/premium_list` — List all groups with Premium ON\n\n"
            f"{'─'*14}\n"
            f"🌐 `/gblacklist` · `/gwhitelist` — Global word lists\n"
            f"🤖 `/adexempt` — Auto-delete exemptions\n"
        )
        await update.message.reply_text(
            text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("📊 𝗦𝘁𝗮𝘁𝘀", callback_data="menu_stats"),
                    InlineKeyboardButton("🛡️ 𝗣𝗿𝗼𝘁𝗲𝗰𝘁𝗶𝗼𝗻𝘀", callback_data="menu_protection"),
                ]
            ])
        )
        return

    # DM — Regular user
    text = (
                f"🛡️ *𝗚𝗨𝗔𝗥𝗗𝗜𝗔𝗡 — 𝗚𝗿𝗼𝘂𝗽 𝗣𝗿𝗼𝘁𝗲𝗰𝘁𝗶𝗼𝗻 𝗕𝗼𝘁*\n"
        f"_Security · Moderation · Automation_\n"
        f"{'─'*14}\n\n"
        f"👋 *Hi {md_esc(u.first_name or 'there')}!*\n\n"
        f"I keep groups safe, clean, and spam-free —\n"
        f"around the clock, with zero effort from admins. 🔥\n\n"
        f"{'─'*14}\n"
        f"📱 *𝗬𝗢𝗨𝗥 𝗖𝗢𝗠𝗠𝗔𝗡𝗗𝗦*\n\n"
        f"  📜 `/rules` — View group rules\n"
        f"  ⚠️ `/warnings` — Check your warnings\n"
        f"  ⭐ `/rep` — Your profile card\n"
        f"  🏆 `/repboard` — Reputation ranking\n"
        f"  🆔 `/id` — Your Telegram ID\n\n"
        f"{'─'*14}\n"
        f"💎 *𝗥𝗘𝗣𝗨𝗧𝗔𝗧𝗜𝗢𝗡*\n"
        f"_Say thanks → +{REP_PER_THANK} rep · Clear a warning → {REP_PER_WARN_REMOVE} rep_\n\n"
        f"_Add me to your group and make me admin to get started._"
    )
    await update.message.reply_text(
        text,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("📋 𝗔𝗹𝗹 𝗖𝗼𝗺𝗺𝗮𝗻𝗱𝘀", callback_data="menu_user"),
                InlineKeyboardButton("⚠️ 𝗪𝗮𝗿𝗻 𝗦𝘆𝘀𝘁𝗲𝗺", callback_data="menu_warns"),
            ],
        ])
    )


# ─── /help ──────────────────────────────────────────────────
async def help_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    u  = update.effective_user
    ch = update.effective_chat

    # Check if caller is admin (in group) or owner
    is_owner = u.id == OWNER_ID
    in_group = ch.type != "private"
    caller_is_admin = is_owner or (in_group and await is_adm(ctx, ch.id, u.id))

    # ── User-only help (non-admins) ──────────────────────────
    if not caller_is_admin:
        text = (
            f"*👤 YOUR COMMANDS*\n"

            f"{'─'*14}\n\n"
            f"📜 `/rules` — View group rules\n"
            f"⚠️ `/warnings` — Check your warnings\n"
            f"⭐ `/rep` — Your profile card\n"
            f"🏆 `/repboard` — Reputation leaderboard\n"
            f"🆔 `/id` — Your Telegram ID\n\n"
            f"{'─'*14}\n"
            f"💡 _Say thanks → +{REP_PER_THANK} rep · Clear a warning → {REP_PER_WARN_REMOVE} rep_\n"
            f"_Violations are detected automatically._"
        )
        sent = await update.message.reply_text(
            text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("📜 𝗥𝘂𝗹𝗲𝘀", callback_data="show_rules"),
                    InlineKeyboardButton("⚠️ 𝗪𝗮𝗿𝗻𝘀 𝗜𝗻𝗳𝗼", callback_data="menu_warns"),
                ],
                [
                    InlineKeyboardButton("🛡️ 𝗣𝗿𝗼𝘁𝗲𝗰𝘁𝗶𝗼𝗻𝘀", callback_data="menu_protection"),
                ]
            ])
        )
        _remember_menu_owner(ch.id, sent.message_id, u.id)
        if in_group:
            schedule_panel_autodelete(ctx, ch.id, sent.message_id, cmd_msg_id=update.message.message_id)
        return sent

    # ── Admin / Owner full help ──────────────────────────────
    admin_text = (
        f"*👮 𝗔𝗗𝗠𝗜𝗡 𝗖𝗢𝗠𝗠𝗔𝗡𝗗 𝗣𝗔𝗡𝗘𝗟*\n"

        f"{'─'*14}\n\n"
        f"🔇 `/mute [sec]` — Mute a user _(reply)_\n"
        f"🔊 `/unmute` — Unmute a user _(reply)_\n"
        f"🔨 `/ban [reason]` — Ban a user _(reply)_\n"
        f"🔓 `/unban <id>` — Unban a user\n"
        f"⚠️ `/warn [reason]` — Warn a user _(reply)_\n"
        f"♻️ `/resetwarnings` — Clear warnings _(reply)_\n"
        f"🗑️ `/del` — Delete a message _(reply)_\n"
        f"🧹 `/purge` — Bulk-delete from a reply\n"
        f"🧪 `/testmute` — Test a 35s mute _(reply)_\n"
        f"👑 `/immortal <id>` — Grant immunity\n"
        f"💀 `/unimmortal <id>` — Remove immunity\n"
        f"📋 `/immortals` — List immune users\n\n"
        f"{'─'*14}\n"
        f"⚙️ *𝗦𝗘𝗧𝗧𝗜𝗡𝗚𝗦*\n\n"
        f"🎛️ `/settings` — Open the settings panel\n"
        f"📜 `/setrules <text>` — Set group rules\n"
        f"🔗 `/setlinked` — Set linked channel\n"
        f"🎭 `/captcha on|off` — Toggle captcha\n"
        f"🗑️ `/sticker_delete <min>` — Sticker auto-delete\n"
        f"⏱️ `/autodelete <min>` — Message auto-delete\n"
        f"⛔ `/addblacklist <word>` — Block a word\n"
        f"✅ `/addwhitelist <word>` — Allow a word\n"
        f"📋 `/blacklist` · `/whitelist` — View word lists\n"
        f"📚 `/addteacher` — Grant teacher role\n"
        f"❌ `/removeteacher` — Remove teacher role\n"
        f"📋 `/teachers` — List all teachers\n\n"
        f"{'─'*14}\n"
        f"🌐 *𝗬𝗢𝗨𝗥 𝗖𝗢𝗠𝗠𝗨𝗡𝗜𝗧𝗬*\n\n"
        f"➕ `/addcommunity` — Link this group to your community\n"
        f"➖ `/removecommunity` — Unlink this group\n"
        f"📋 `/mycommunity` — List your community's groups\n"
        f"🔨 `/gban <id> [reason]` — Ban across your community\n"
        f"_`/unmute` (yours) also covers your whole community._\n"
    )

    if is_owner:
        admin_text += (
            f"\n{'─'*14}\n"
            f"👑 *𝗢𝗪𝗡𝗘𝗥 𝗢𝗡𝗟𝗬*\n\n"
            f"🌐 `/autodelete <min>` _(DM)_ — Set global default\n"
            f"💀 `/fban <id>` — Ban across all groups\n"
            f"✅ `/gunban <id>` — Reverse a global ban\n"
            f"🔇 `/gmute <id>` — Mute across all groups _(DM only)_\n"
            f"🧹 `/gclearwarn <id>` — Clear all warnings\n"
            f"⚡ `/power <id>` · `/unpower <id>` — Ban authority\n"
            f"📢 `/broadcast <msg>` — Message every group\n"
            f"👥 `/groups` · `/stats` — Bot statistics\n"
            f"🌐 `/gblacklist` · `/gwhitelist` — Global word lists\n"
            f"🤖 `/adexempt <id>` — Auto-delete exemption\n"
            f"💎 `/premium <id> on|off` — Toggle premium\n"
            f"📋 `/premium_list` — List Premium groups\n"
        )

    admin_text += (
        f"\n{'─'*14}\n"
        f"⚠️ *𝙒𝙖𝙧𝙣𝙞𝙣𝙜 𝙨𝙘𝙖𝙡𝙚:* W1→35s · W2→60s · W3→120s · W4→1 week 🌐"
    )

    sent = await update.message.reply_text(
        admin_text,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🛡️ 𝗣𝗿𝗼𝘁𝗲𝗰𝘁𝗶𝗼𝗻𝘀", callback_data="menu_protection"),
                InlineKeyboardButton("⚙️ 𝗦𝗲𝘁𝘁𝗶𝗻𝗴𝘀", callback_data="menu_settings"),
            ],
            [
                InlineKeyboardButton("⚠️ 𝗪𝗮𝗿𝗻 𝗦𝘆𝘀𝘁𝗲𝗺", callback_data="menu_warns"),
                InlineKeyboardButton("📊 𝗦𝘁𝗮𝘁𝘀", callback_data="menu_stats"),
            ]
        ])
    )
    if in_group:
        _remember_menu_owner(ch.id, sent.message_id, u.id)
        schedule_panel_autodelete(ctx, ch.id, sent.message_id)


# ─── /rule ──────────────────────────────────────────────────
def build_auto_rules_text(chat_id) -> str:
    """/settings → Filters me jo bhi ON hai, unhi se /rules ka 'NOT ALLOWED'
    list banta hai — admin ko kahin do jagah maintain nahi karna padta.
    Warn penalties bhi is group ke actual (custom ho sakti hain) warn
    durations se aate hain, hardcoded nahi."""
    filt = db.get_filters(chat_id)

    lines = [line for key, line in FILTER_RULE_LINES if filt.get(key)]
    if filt.get("antispam", True):
        lines.extend(ANTISPAM_ALWAYS_RULES)

    if lines:
        not_allowed = "🚫 *𝗡𝗢𝗧 𝗔𝗟𝗟𝗢𝗪𝗘𝗗*\n\n" + "\n".join(
            f"  {i}️⃣  {line}" if i <= 9 else f"  {i}.  {line}"
            for i, line in enumerate(lines, start=1)
        )
    else:
        not_allowed = "🚫 *𝗡𝗢𝗧 𝗔𝗟𝗟𝗢𝗪𝗘𝗗*\n\n  _No content filters are currently active in this group._"

    wd = db.get_warn_durations(chat_id)
    penalties = (
        f"⚠️ *𝗣𝗘𝗡𝗔𝗟𝗧𝗜𝗘𝗦*\n"
        f"  🟡 1st → {format_duration(wd[1])} mute\n"
        f"  🟠 2nd → {format_duration(wd[2])} mute\n"
        f"  🔴 3rd → {format_duration(wd[3])} mute\n"
        f"  💀 4th → {format_duration(wd[4])} mute, in this group\n"
    )

    return (
        f"📜 *𝗚𝗥𝗢𝗨𝗣 𝗥𝗨𝗟𝗘𝗦*\n"
        f"{'─'*14}\n\n"
        f"{not_allowed}\n\n"
        f"{'─'*14}\n\n"
        f"{penalties}\n"
        f"{'─'*14}\n"
        f"✅ _Follow the rules and enjoy your stay!_"
    )


async def rule_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    custom = db.get_rules(chat_id)

    if custom:
        text = (
            f"📜 *𝗚𝗥𝗢𝗨𝗣 𝗥𝗨𝗟𝗘𝗦*\n"
            f"{'─'*14}\n\n"
            f"{custom}\n\n"
            f"{'─'*14}\n"
            f"_Please follow the rules to avoid penalties._"
        )
    else:
        text = build_auto_rules_text(chat_id)

    sent = await update.message.reply_text(
        text,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("⚠️ 𝗪𝗮𝗿𝗻 𝗦𝘆𝘀𝘁𝗲𝗺", callback_data="menu_warns")]
        ])
    )
    if update.effective_chat.type != "private" and update.effective_user:
        _remember_menu_owner(update.effective_chat.id, sent.message_id, update.effective_user.id)


# ─── /setrules ───────────────────────────────────────────────
async def setrules_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ch = update.effective_chat
    if ch.type == "private":
        return await update.message.reply_text("⚠️ This command only works in a group.")
    if not await sender_is_admin(ctx, update):
        return await update.message.reply_text("🔒 Admins only.")
    if not ctx.args:
        return await update.message.reply_text(
            "❌ Usage: `/setrules <your rules text>`",
            parse_mode='Markdown'
        )
    rules_text = ' '.join(ctx.args)
    db.set_rules(ch.id, rules_text)
    await update.message.reply_text(
        f"✅ *Custom rules saved!*\n\n"
        f"Use /rule to view them anytime.",
        parse_mode='Markdown'
    )


# ─── /id ────────────────────────────────────────────────────
async def id_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    ch = update.effective_chat
    target = update.message.reply_to_message.from_user if update.message.reply_to_message else u
    text = (
        f"🆔 *𝗨𝘀𝗲𝗿 𝗜𝗻𝗳𝗼𝗿𝗺𝗮𝘁𝗶𝗼𝗻*\n"
        f"{'─'*14}\n\n"
        f"👤 Name: `{target.first_name or ''}`\n"
        f"🔑 ID: `{target.id}`\n"
    )
    if target.username:
        text += f"🔗 Username: @{target.username}\n"
    if ch.type != "private":
        text += f"\n💬 *𝙂𝙧𝙤𝙪𝙥 𝙄𝘿:* `{ch.id}`"
    await update.message.reply_text(text, parse_mode='Markdown')


# ─── /immortal ──────────────────────────────────────────────
async def immortal_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ch = update.effective_chat
    user = update.effective_user
    if ch.type == "private":
        return await update.message.reply_text("⚠️ This command only works in a group.")
    if not await is_adm(ctx, ch.id, user.id) and user.id != OWNER_ID:
        return await update.message.reply_text("🔒 Admins only.")

    tid, tobj, _, err = await resolve_target(
        update, ctx,
        "❌ Usage:\n`/immortal <user_id | @username>`\nor reply to user message with `/immortal`"
    )
    if err:
        return await update.message.reply_text(err, parse_mode='Markdown')

    db.add_immortal(ch.id, tid)
    await update.message.reply_text(
        f"👑 *𝗜𝗠𝗠𝗢𝗥𝗧𝗔𝗟 𝗦𝗧𝗔𝗧𝗨𝗦 𝗚𝗥𝗔𝗡𝗧𝗘𝗗*\n"
        f"{'─'*14}\n\n"
        f"🆔 User: {target_name(tobj, tid)}\n\n"
        f"✅ This user is now *immune* to all rules!\n"
        f"• Links, forwards, any content — allowed\n"
        f"• Bot will never act on their messages\n\n"
        f"Use `/unimmortal {tid}` to revoke.",
        parse_mode='Markdown'
    )


# ─── /unimmortal ────────────────────────────────────────────
async def unimmortal_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ch = update.effective_chat
    user = update.effective_user
    if ch.type == "private":
        return await update.message.reply_text("⚠️ This command only works in a group.")
    if not await is_adm(ctx, ch.id, user.id) and user.id != OWNER_ID:
        return await update.message.reply_text("🔒 Admins only.")

    tid, tobj, _, err = await resolve_target(
        update, ctx,
        "❌ Usage: `/unimmortal <user_id | @username>`\nor reply to user message"
    )
    if err:
        return await update.message.reply_text(err, parse_mode='Markdown')

    db.remove_immortal(ch.id, tid)
    await update.message.reply_text(
        f"✅ Immortal status *removed* for {target_name(tobj, tid)}.\n"
        f"They are now subject to group rules.",
        parse_mode='Markdown'
    )


# ─── /immortals ─────────────────────────────────────────────
async def immortals_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ch = update.effective_chat
    if ch.type == "private":
        return await update.message.reply_text("⚠️ This command only works in a group.")
    if not await sender_is_admin(ctx, update):
        return await update.message.reply_text("🔒 Admins only.")

    immortals = db.get_immortals(ch.id)
    if not immortals:
        return await update.message.reply_text("👑 No immortal users in this group.")

    lines = [f"  • `{uid}`" for uid in immortals]
    await update.message.reply_text(
        f"👑 *𝗜𝗠𝗠𝗢𝗥𝗧𝗔𝗟 𝗨𝗦𝗘𝗥𝗦*\n"
        f"{'─'*14}\n\n"
        + "\n".join(lines) +
        f"\n\n_Total: {len(immortals)} user(s)_",
        parse_mode='Markdown'
    )


# ─── /addblacklist ──────────────────────────────────────────
async def addblacklist_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ch = update.effective_chat
    if ch.type == "private":
        return await update.message.reply_text("⚠️ This command only works in a group.")
    if not await sender_is_admin(ctx, update):
        return await update.message.reply_text("🔒 Admins only.")
    if not ctx.args:
        return await update.message.reply_text(
            "❌ Usage: `/addblacklist <word>`",
            parse_mode='Markdown'
        )
    word = ' '.join(ctx.args).lower().strip()
    db.add_blacklist(ch.id, word)
    await update.message.reply_text(
        f"⛔ *𝘽𝙡𝙖𝙘𝙠𝙡𝙞𝙨𝙩𝙚𝙙:* `{word}`\n\n"
        f"Anyone using this word will be *warned automatically*.",
        parse_mode='Markdown'
    )


# ─── /removeblacklist ───────────────────────────────────────
async def removeblacklist_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ch = update.effective_chat
    if ch.type == "private":
        return await update.message.reply_text("⚠️ This command only works in a group.")
    if not await sender_is_admin(ctx, update):
        return await update.message.reply_text("🔒 Admins only.")
    if not ctx.args:
        return await update.message.reply_text(
            "❌ Usage: `/removeblacklist <word>`",
            parse_mode='Markdown'
        )
    word = ' '.join(ctx.args).lower().strip()
    db.remove_blacklist(ch.id, word)
    await update.message.reply_text(
        f"✅ Removed from blacklist: `{word}`",
        parse_mode='Markdown'
    )


# ─── /blacklist ─────────────────────────────────────────────
async def blacklist_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ch = update.effective_chat
    if ch.type == "private":
        return await update.message.reply_text("⚠️ This command only works in a group.")
    if not await sender_is_admin(ctx, update):
        return await update.message.reply_text("🔒 Admins only.")

    words = db.get_blacklist(ch.id)
    if not words:
        return await update.message.reply_text(
            "⛔ No custom blacklist words set.\n\nUse `/addblacklist <word>` to add.",
            parse_mode='Markdown'
        )
    await update.message.reply_text(
        f"⛔ *𝗕𝗟𝗔𝗖𝗞𝗟𝗜𝗦𝗧𝗘𝗗 𝗪𝗢𝗥𝗗𝗦* ({len(words)})\n"
        f"{'─'*14}\n\n"
        + "\n".join(f"  • `{w}`" for w in words),
        parse_mode='Markdown'
    )


# ═══════════════════════════════════════════════════════════
#  PREMIUM: Bio Guard — Bio Words (independent from /blacklist)
# ═══════════════════════════════════════════════════════════
# ─── /addbioword ──────────────────────────────────────────
async def addbioword_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ch = update.effective_chat
    if ch.type == "private":
        return await update.message.reply_text("⚠️ This command only works in a group.")
    if not await sender_is_admin(ctx, update):
        return await update.message.reply_text("🔒 Admins only.")
    g = db.get_group(ch.id)
    if not bool(g.get("premium", False)):
        return await update.message.reply_text("💎 This is a Premium-only feature. DM @Suhani_TG to get Premium.")
    if not ctx.args:
        return await update.message.reply_text(
            "❌ Usage: `/addbioword <word>`",
            parse_mode='Markdown'
        )
    word = ' '.join(ctx.args).lower().strip()
    if db.get_biowords(ch.id) is None:
        # First customization — fork from the current combined blacklist
        # (group + global) so Bio Words starts out with everything that's
        # already protected. From here on, edits only ever touch this
        # bio-only list — never the main /blacklist.
        db.set_biowords(ch.id, list(set((db.get_blacklist(ch.id) or []) + (db.get_gblacklist() or []))))
    db.add_bioword(ch.id, word)
    await update.message.reply_text(
        f"🕵️ *𝗔𝗱𝗱𝗲𝗱 𝘁𝗼 𝗕𝗶𝗼 𝗪𝗼𝗿𝗱𝘀:* `{word}`\n\n"
        f"_This only affects the Bio Guard check — your main `/blacklist` is unchanged._",
        parse_mode='Markdown'
    )


# ─── /removebioword ───────────────────────────────────────
async def removebioword_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ch = update.effective_chat
    if ch.type == "private":
        return await update.message.reply_text("⚠️ This command only works in a group.")
    if not await sender_is_admin(ctx, update):
        return await update.message.reply_text("🔒 Admins only.")
    g = db.get_group(ch.id)
    if not bool(g.get("premium", False)):
        return await update.message.reply_text("💎 This is a Premium-only feature. DM @Suhani_TG to get Premium.")
    if not ctx.args:
        return await update.message.reply_text(
            "❌ Usage: `/removebioword <word>`",
            parse_mode='Markdown'
        )
    word = ' '.join(ctx.args).lower().strip()
    if db.get_biowords(ch.id) is None:
        # Same fork-first rule — removing a word that only lives in the
        # main /blacklist must NOT touch that main list.
        db.set_biowords(ch.id, list(set((db.get_blacklist(ch.id) or []) + (db.get_gblacklist() or []))))
    db.remove_bioword(ch.id, word)
    await update.message.reply_text(
        f"✅ Removed from Bio Words: `{word}`\n\n"
        f"_Your main `/blacklist` is untouched — this only affects the Bio Guard check._",
        parse_mode='Markdown'
    )


# ─── /biowords ────────────────────────────────────────────
async def biowords_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ch = update.effective_chat
    if ch.type == "private":
        return await update.message.reply_text("⚠️ This command only works in a group.")
    if not await sender_is_admin(ctx, update):
        return await update.message.reply_text("🔒 Admins only.")

    custom = db.get_biowords(ch.id)
    if custom is None:
        words = list(set((db.get_blacklist(ch.id) or []) + (db.get_gblacklist() or [])))
        note = "_Not customized yet — currently mirrors your main `/blacklist` + global blacklist._"
    else:
        words = custom
        note = "_Custom list — independent from your main `/blacklist`._"

    if not words:
        return await update.message.reply_text(
            f"🕵️ No Bio Words set.\n\n{note}\n\nUse `/addbioword <word>` to add one.",
            parse_mode='Markdown'
        )
    await update.message.reply_text(
        f"🕵️ *𝗕𝗜𝗢 𝗪𝗢𝗥𝗗𝗦* ({len(words)})\n{'─'*14}\n\n"
        + "\n".join(f"  • `{w}`" for w in words)
        + f"\n\n{note}",
        parse_mode='Markdown'
    )


# ═══════════════════════════════════════════════════════════
#  PREMIUM: Bio Guard — Bio Link Domains ("Domains Only" mode)
# ═══════════════════════════════════════════════════════════
# ─── /addbiodomain ────────────────────────────────────────
async def addbiodomain_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ch = update.effective_chat
    if ch.type == "private":
        return await update.message.reply_text("⚠️ This command only works in a group.")
    if not await sender_is_admin(ctx, update):
        return await update.message.reply_text("🔒 Admins only.")
    g = db.get_group(ch.id)
    if not bool(g.get("premium", False)):
        return await update.message.reply_text("💎 This is a Premium-only feature. DM @Suhani_TG to get Premium.")
    if not ctx.args:
        return await update.message.reply_text(
            "❌ Usage: `/addbiodomain <domain>` (e.g. `/addbiodomain instagram.com`)",
            parse_mode='Markdown'
        )
    domain = extract_domain(ctx.args[0])
    if not domain:
        return await update.message.reply_text("❌ That doesn't look like a valid domain.")
    if g.get("bio_link_domains") is None:
        db.update_group(ch.id, {"bio_link_domains": DEFAULT_BIO_LINK_DOMAINS.copy()})
    db.add_bio_domain(ch.id, domain)
    await update.message.reply_text(
        f"🌐 *𝗔𝗱𝗱𝗲𝗱 𝘁𝗼 𝗕𝗶𝗼 𝗟𝗶𝗻𝗸 𝗗𝗼𝗺𝗮𝗶𝗻𝘀:* `{domain}`\n\n"
        f"_Only used when Bio Link mode is set to 🟡 Domains Only (see /settings → 💎 Premium)._",
        parse_mode='Markdown'
    )


# ─── /removebiodomain ─────────────────────────────────────
async def removebiodomain_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ch = update.effective_chat
    if ch.type == "private":
        return await update.message.reply_text("⚠️ This command only works in a group.")
    if not await sender_is_admin(ctx, update):
        return await update.message.reply_text("🔒 Admins only.")
    g = db.get_group(ch.id)
    if not bool(g.get("premium", False)):
        return await update.message.reply_text("💎 This is a Premium-only feature. DM @Suhani_TG to get Premium.")
    if not ctx.args:
        return await update.message.reply_text(
            "❌ Usage: `/removebiodomain <domain>`",
            parse_mode='Markdown'
        )
    domain = extract_domain(ctx.args[0])
    if g.get("bio_link_domains") is None:
        # Make sure the field exists first so $pull actually has
        # something to work against for groups still on the defaults.
        db.update_group(ch.id, {"bio_link_domains": DEFAULT_BIO_LINK_DOMAINS.copy()})
    db.remove_bio_domain(ch.id, domain)
    await update.message.reply_text(f"✅ Removed from Bio Link Domains: `{domain}`", parse_mode='Markdown')


# ─── /biodomains ──────────────────────────────────────────
async def biodomains_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ch = update.effective_chat
    if ch.type == "private":
        return await update.message.reply_text("⚠️ This command only works in a group.")
    if not await sender_is_admin(ctx, update):
        return await update.message.reply_text("🔒 Admins only.")

    g = db.get_group(ch.id)
    domains = g.get("bio_link_domains")
    if domains is None:
        domains = DEFAULT_BIO_LINK_DOMAINS

    if not domains:
        return await update.message.reply_text(
            "🌐 No Bio Link domains set.\n\nUse `/addbiodomain <domain>` to add one.",
            parse_mode='Markdown'
        )
    await update.message.reply_text(
        f"🌐 *𝗕𝗜𝗢 𝗟𝗜𝗡𝗞 𝗗𝗢𝗠𝗔𝗜𝗡𝗦* ({len(domains)})\n{'─'*14}\n\n"
        + "\n".join(f"  • `{d}`" for d in domains)
        + f"\n\n_Only used when Bio Link mode is 🟡 Domains Only._",
        parse_mode='Markdown'
    )


# ─── /addwhitelist ──────────────────────────────────────────
async def addwhitelist_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ch = update.effective_chat
    if ch.type == "private":
        return await update.message.reply_text("⚠️ This command only works in a group.")
    if not await sender_is_admin(ctx, update):
        return await update.message.reply_text("🔒 Admins only.")
    if not ctx.args:
        return await update.message.reply_text(
            "❌ Usage: `/addwhitelist <word>`",
            parse_mode='Markdown'
        )
    word = ' '.join(ctx.args).lower().strip()
    db.add_whitelist(ch.id, word)
    await update.message.reply_text(
        f"✅ *𝙒𝙝𝙞𝙩𝙚𝙡𝙞𝙨𝙩𝙚𝙙:* `{word}`\n\n"
        f"This word will bypass blacklist detection.",
        parse_mode='Markdown'
    )


# ─── /removewhitelist ───────────────────────────────────────
async def removewhitelist_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ch = update.effective_chat
    if ch.type == "private":
        return await update.message.reply_text("⚠️ This command only works in a group.")
    if not await sender_is_admin(ctx, update):
        return await update.message.reply_text("🔒 Admins only.")
    if not ctx.args:
        return await update.message.reply_text(
            "❌ Usage: `/removewhitelist <word>`",
            parse_mode='Markdown'
        )
    word = ' '.join(ctx.args).lower().strip()
    db.remove_whitelist(ch.id, word)
    await update.message.reply_text(
        f"✅ Removed from whitelist: `{word}`",
        parse_mode='Markdown'
    )


# ─── /whitelist ─────────────────────────────────────────────
async def whitelist_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ch = update.effective_chat
    if ch.type == "private":
        return await update.message.reply_text("⚠️ This command only works in a group.")
    if not await sender_is_admin(ctx, update):
        return await update.message.reply_text("🔒 Admins only.")

    words = db.get_whitelist(ch.id)
    if not words:
        return await update.message.reply_text(
            "✅ No whitelist words set.",
            parse_mode='Markdown'
        )
    await update.message.reply_text(
        f"✅ *𝗪𝗛𝗜𝗧𝗘𝗟𝗜𝗦𝗧𝗘𝗗 𝗪𝗢𝗥𝗗𝗦* ({len(words)})\n"
        f"{'─'*14}\n\n"
        + "\n".join(f"  • `{w}`" for w in words),
        parse_mode='Markdown'
    )


# ─── /sticker_delete ────────────────────────────────────────
async def sticker_delete_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ch = update.effective_chat
    if ch.type == "private":
        return await update.message.reply_text("⚠️ This command only works in a group.")
    if not await sender_is_admin(ctx, update):
        return await update.message.reply_text("🔒 Admins only.")

    if not ctx.args:
        g = db.get_group(ch.id)
        cur = g.get("sticker_delete_min")
        status = f"{ICON_ON} {cur} min" if cur else f"{ICON_OFF} OFF"
        return await update.message.reply_text(
            f"🗑️ *𝙎𝙩𝙞𝙘𝙠𝙚𝙧 / 𝙂𝙄𝙁 𝘼𝙪𝙩𝙤-𝘿𝙚𝙡𝙚𝙩𝙚*\n"
            f"{'─'*14}\n\n"
            f"Status: {status}\n\n"
            f"Usage: `/sticker_delete 2` → enable (2 min)\n"
            f"Disable: `/sticker_delete 0`",
            parse_mode='Markdown'
        )

    try:
        minutes = int(ctx.args[0].replace('min','').strip())
    except ValueError:
        return await update.message.reply_text(
            "❌ Usage: `/sticker_delete 2`",
            parse_mode='Markdown'
        )

    if minutes <= 0:
        db.update_group(ch.id, {"sticker_delete_min": None})
        await update.message.reply_text(
            f"✅ Sticker auto-delete *disabled*.",
            parse_mode='Markdown'
        )
    else:
        db.update_group(ch.id, {"sticker_delete_min": minutes})
        await update.message.reply_text(
            f"✅ *Sticker / GIF auto-delete enabled!*\n\n"
            f"⏱ Stickers, GIFs & animated emojis\n"
            f"will be deleted after *{minutes} min*.",
            parse_mode='Markdown'
        )


# ─── /autodelete ────────────────────────────────────────────
async def autodelete_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ch   = update.effective_chat
    user = update.effective_user

    # ── DM use — Owner only, sets GLOBAL default ────────────
    if ch.type == "private":
        if user.id != OWNER_ID:
            return await update.message.reply_text("❌ Owner only command in DM!")

        cur_global = db.get_global_autodelete()

        if not ctx.args:
            status = f"🟢 {cur_global} min" if cur_global else "🔴 OFF"
            return await update.message.reply_text(
                f"🌐 *𝙂𝙡𝙤𝙗𝙖𝙡 𝘼𝙪𝙩𝙤-𝘿𝙚𝙡𝙚𝙩𝙚 𝘿𝙚𝙛𝙖𝙪𝙡𝙩*\n"
                f"{'─'*14}\n\n"
                f"Current: {status}\n\n"
                f"Usage: `/autodelete 5` → set default 5 min for ALL groups\n"
                f"Disable: `/autodelete 0`\n\n"
                f"_Group admins can override this per-group._",
                parse_mode='Markdown'
            )

        try:
            minutes = int(ctx.args[0].replace('min', '').strip())
        except ValueError:
            return await update.message.reply_text("❌ Usage: `/autodelete <minutes>`", parse_mode='Markdown')

        if minutes <= 0:
            db.set_global_autodelete(None)
            await update.message.reply_text(
                "✅ *Global auto-delete disabled.*\n\n"
                "_Groups with their own setting will keep it._",
                parse_mode='Markdown'
            )
        else:
            db.set_global_autodelete(minutes)
            await update.message.reply_text(
                f"✅ *Global Auto-Delete Set!*\n\n"
                f"⏱ Default: *{minutes} min* for ALL groups\n"
                f"_Group admins can still override per-group._",
                parse_mode='Markdown'
            )
        return

    # ── Group use — Group admin, sets per-group override ────
    if not await sender_is_admin(ctx, update):
        return await update.message.reply_text("🔒 Admins only.")

    if not ctx.args:
        per_group = db.get_group(ch.id).get("autodelete_min")
        global_val = db.get_global_autodelete()
        effective  = per_group if per_group is not None else global_val

        lines = []
        if per_group is not None:
            lines.append(f"📌 Group setting: *{per_group} min*")
        else:
            lines.append(f"📌 Group setting: _not set_")
        if global_val:
            lines.append(f"🌐 Global default: *{global_val} min*")
        else:
            lines.append(f"🌐 Global default: _OFF_")
        lines.append(f"⚡ *𝘼𝙘𝙩𝙞𝙫𝙚:* {'🟢 ' + str(effective) + ' min' if effective else '🔴 OFF'}")

        return await update.message.reply_text(
            f"🗑️ *Auto-Delete — This Group*\n"
            f"{'─'*14}\n\n"
            + "\n".join(lines) +
            f"\n\nUsage: `/autodelete 5` → override to 5 min\n"
            f"Restore global: `/autodelete reset`",
            parse_mode='Markdown'
        )

    # Special: /autodelete reset → remove per-group override
    if ctx.args[0].lower() == "reset":
        db.update_group(ch.id, {"autodelete_min": None})
        global_val = db.get_global_autodelete()
        await update.message.reply_text(
            f"✅ *Group override removed.*\n\n"
            f"{'🌐 Now using global default: *' + str(global_val) + ' min*' if global_val else '🔴 Auto-delete is OFF (no global default set).'}",
            parse_mode='Markdown'
        )
        return

    try:
        minutes = int(ctx.args[0].replace('min', '').strip())
    except ValueError:
        return await update.message.reply_text("❌ Usage: `/autodelete 5`", parse_mode='Markdown')

    if minutes <= 0:
        db.update_group(ch.id, {"autodelete_min": None})
        global_val = db.get_global_autodelete()
        await update.message.reply_text(
            f"✅ Group auto-delete *override removed*.\n"
            f"{'🌐 Falling back to global default: *' + str(global_val) + ' min*' if global_val else '🔴 Auto-delete is now OFF.'}",
            parse_mode='Markdown'
        )
    else:
        db.update_group(ch.id, {"autodelete_min": minutes})
        await update.message.reply_text(
            f"✅ *Auto-delete set for this group!*\n\n"
            f"⏱ Every message deleted after *{minutes} min*.\n"
            f"_(This overrides the global default.)_",
            parse_mode='Markdown'
        )


# ─── /captcha ───────────────────────────────────────────────
async def captcha_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ch = update.effective_chat
    if ch.type == "private":
        return await update.message.reply_text("⚠️ This command only works in a group.")
    if not await sender_is_admin(ctx, update):
        return await update.message.reply_text("🔒 Admins only.")

    if not ctx.args or ctx.args[0].lower() not in ('on', 'off'):
        g = db.get_group(ch.id)
        status = f"{ICON_ON} ON" if g.get("captcha") else f"{ICON_OFF} OFF"
        return await update.message.reply_text(
            f"🎭 *𝗖𝗮𝗽𝘁𝗰𝗵𝗮 𝗩𝗲𝗿𝗶𝗳𝗶𝗰𝗮𝘁𝗶𝗼𝗻*\n"
            f"{'─'*14}\n\n"
            f"Status: {status}\n\n"
            f"Toggle: `/captcha on` or `/captcha off`",
            parse_mode='Markdown'
        )

    val = ctx.args[0].lower() == 'on'
    db.update_group(ch.id, {"captcha": val})
    state_icon = ICON_ON if val else ICON_OFF
    state_text = "enabled" if val else "disabled"
    await update.message.reply_text(
        f"🎭 Captcha {state_icon} *{state_text}!*\n\n"
        f"{'New members must solve a math question to chat.' if val else 'New members can chat freely.'}",
        parse_mode='Markdown'
    )


# ─── /setlinked ─────────────────────────────────────────────
async def setlinked_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ch = update.effective_chat
    if ch.type == "private":
        return await update.message.reply_text("⚠️ This command only works in a group.")
    if not await sender_is_admin(ctx, update):
        return await update.message.reply_text("🔒 Admins only.")

    try:
        chat = await ctx.bot.get_chat(ch.id)
        if hasattr(chat, 'linked_chat_id') and chat.linked_chat_id:
            db.set_linked_channel(ch.id, chat.linked_chat_id)
            try:
                channel = await ctx.bot.get_chat(chat.linked_chat_id)
                ch_name = channel.title or str(chat.linked_chat_id)
            except:
                ch_name = str(chat.linked_chat_id)
            await update.message.reply_text(
                f"✅ *Linked Channel Set!*\n\n"
                f"📢 {ch_name}\n"
                f"🆔 `{chat.linked_chat_id}`\n\n"
                f"_Forwards from this channel are now allowed._",
                parse_mode='Markdown'
            )
        else:
            if ctx.args:
                try:
                    cid = int(ctx.args[0])
                    db.set_linked_channel(ch.id, cid)
                    await update.message.reply_text(
                        f"✅ Linked channel set: `{cid}`",
                        parse_mode='Markdown'
                    )
                except:
                    await update.message.reply_text("❌ Invalid channel ID!")
            else:
                await update.message.reply_text(
                    "❌ No linked channel found!\n\nUse: `/setlinked -1001234567890`",
                    parse_mode='Markdown'
                )
    except Exception:
        if ctx.args:
            try:
                cid = int(ctx.args[0])
                db.set_linked_channel(ch.id, cid)
                await update.message.reply_text(
                    f"✅ Linked channel set: `{cid}`",
                    parse_mode='Markdown'
                )
            except:
                await update.message.reply_text("❌ Invalid channel ID!")


# ─── /testmute ──────────────────────────────────────────────
async def testmute_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ch = update.effective_chat
    if ch.type == "private": return
    if not await sender_is_admin(ctx, update): return
    tid, tobj, _, err = await resolve_target(
        update, ctx,
        "↩️ Reply to a user, or use `/testmute <user_id | @username>`"
    )
    if err:
        return await update.message.reply_text(err, parse_mode='Markdown')
    if await is_adm(ctx, ch.id, tid):
        return await update.message.reply_text("🔒 Admins can't be muted.")
    if await do_mute(ctx, ch.id, tid, 35):
        await update.message.reply_text(
            f"🧪 *𝗧𝗲𝘀𝘁 𝗠𝘂𝘁𝗲 𝗔𝗽𝗽𝗹𝗶𝗲𝗱*\n\n"
            f"👤 {target_name(tobj, tid)} — muted for *35 seconds*.",
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text("⚠️ Couldn't complete that — check the bot has admin rights.")


# ─── /mute ──────────────────────────────────────────────────
async def mute_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ch = update.effective_chat
    if ch.type == "private": return
    if not await sender_is_admin(ctx, update): return
    tid, tobj, consumed, err = await resolve_target(
        update, ctx,
        "↩️ Reply to a user, or use `/mute <user_id | @username> [seconds]`"
    )
    if err:
        return await update.message.reply_text(err, parse_mode='Markdown')
    if await is_adm(ctx, ch.id, tid):
        return await update.message.reply_text("🔒 Admins can't be muted.")
    sec = 35
    rest_args = ctx.args[consumed:] if ctx.args else []
    if rest_args:
        try:
            sec = max(35, int(rest_args[0]))
        except:
            pass
    if await do_mute(ctx, ch.id, tid, sec):
        await update.message.reply_text(
            f"🔇 *Muted*\n\n"
            f"👤 {target_name(tobj, tid)}\n"
            f"⏱ Duration: *{sec} seconds*",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔊 𝗨𝗻𝗺𝘂𝘁𝗲", callback_data=f"unmute_{ch.id}_{tid}")]
            ])
        )
    else:
        await update.message.reply_text(
            "⚠️ Couldn't mute — make sure the bot is admin here and the "
            "user is actually a member of this group."
        )


# ─── /unmute ────────────────────────────────────────────────
async def unmute_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """
    - Bot OWNER → true global unmute: every group the bot manages.
    - Any other group admin → unmutes in the group they ran it in (if run
      inside a group) PLUS every group in their own /addcommunity list.
      Run from bot DM → only their community groups (no "current group").
    """
    ch  = update.effective_chat
    usr = update.effective_user
    is_owner = bool(usr) and usr.id == OWNER_ID

    if ch.type != "private":
        if not await sender_is_admin(ctx, update):
            return
    elif not is_owner and not db.get_community_groups(usr.id):
        return await update.message.reply_text(
            "🔒 `/unmute` from the bot's DM is only for the bot owner, or "
            "admins who have a community set up — run "
            "`/addcommunity` inside a group first."
        )

    tid, tobj, _, err = await resolve_target(
        update, ctx,
        "↩️ Reply to a user (inside the group), or use `/unmute <user_id | @username>`"
    )
    if err:
        return await update.message.reply_text(err, parse_mode='Markdown')

    if is_owner:
        await global_unmute_user(ctx, tid)
        return await update.message.reply_text(
            f"🔊 *𝗨𝗻𝗺𝘂𝘁𝗲𝗱*\n\n👤 {target_name(tobj, tid)} can send messages again — "
            f"*in all groups* (bot-wide, owner unmute).",
            parse_mode='Markdown'
        )

    groups = set(db.get_community_groups(usr.id))
    current_group = ch.id if ch.type != "private" else None
    if current_group:
        groups.add(current_group)

    if not groups:
        return await update.message.reply_text(
            "📭 No group found to unmute in.\n"
            "Run this inside a group, or set up your community first with `/addcommunity`."
        )

    ok = 0
    for gid in groups:
        try:
            db.reset_warnings(gid, tid)
            if await do_unmute(ctx, gid, tid):
                ok += 1
            await asyncio.sleep(0.1)
        except Exception:
            pass

    if groups == {current_group}:
        scope = "this group"
    else:
        scope = f"`{ok}/{len(groups)}` group(s) — your community"
    await update.message.reply_text(
        f"🔊 *𝗨𝗻𝗺𝘂𝘁𝗲𝗱*\n\n👤 {target_name(tobj, tid)} can send messages again — {scope}.",
        parse_mode='Markdown'
    )


# ─── /ban ───────────────────────────────────────────────────
async def ban_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ch = update.effective_chat
    if ch.type == "private": return
    if not await sender_is_admin(ctx, update): return
    tid, tobj, consumed, err = await resolve_target(
        update, ctx,
        "↩️ Reply to a user, or use `/ban <user_id | @username> [reason]`"
    )
    if err:
        return await update.message.reply_text(err, parse_mode='Markdown')
    if await is_adm(ctx, ch.id, tid):
        return await update.message.reply_text("🔒 Admins can't be banned.")
    rest_args = ctx.args[consumed:] if ctx.args else []
    reason = ' '.join(rest_args) if rest_args else "No reason provided"

    # Reply karke /ban kiya to wahi replied message delete ho jaega —
    # ye 100% reliable hai kyunki bot ko us message ka exact id pata hai.
    if update.message.reply_to_message:
        asyncio.create_task(update.message.reply_to_message.delete())

    if await do_ban(ctx, ch.id, tid):
        await update.message.reply_text(
            f"🔨 *𝗨𝘀𝗲𝗿 𝗕𝗮𝗻𝗻𝗲𝗱*\n"
            f"{'─'*14}\n\n"
            f"👤 {target_name(tobj, tid)}\n"
            f"📋 Reason: _{reason}_",
            parse_mode='Markdown',
            reply_markup=kb_unban_button(ch.id, tid)
        )
    else:
        await update.message.reply_text("⚠️ Couldn't ban — make sure the bot has admin rights.")


# ─── /unban ─────────────────────────────────────────────────
async def unban_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ch = update.effective_chat
    if ch.type == "private": return
    if not await sender_is_admin(ctx, update): return
    tid, tobj, _, err = await resolve_target(
        update, ctx,
        "↩️ Reply to a user, or use `/unban <user_id | @username>`"
    )
    if err:
        return await update.message.reply_text(err, parse_mode='Markdown')
    if await do_unban(ctx, ch.id, tid):
        await update.message.reply_text(
            f"✅ {target_name(tobj, tid)} has been *unbanned*.",
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text("⚠️ Couldn't unban — check the bot has admin rights.")


# ─── /warn ──────────────────────────────────────────────────
async def warn_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ch = update.effective_chat
    if ch.type == "private": return
    if not await sender_is_admin(ctx, update): return
    tid, tobj, consumed, err = await resolve_target(
        update, ctx,
        "↩️ Reply to a user, or use `/warn <user_id | @username> [reason]`"
    )
    if err:
        return await update.message.reply_text(err, parse_mode='Markdown')
    if await is_adm(ctx, ch.id, tid):
        return await update.message.reply_text("🔒 Admins can't be warned.")
    rest_args = ctx.args[consumed:] if ctx.args else []
    reason = ' '.join(rest_args) if rest_args else "Rule violation"

    # Reply karke /warn kiya to wahi replied message delete ho jaega.
    if update.message.reply_to_message:
        asyncio.create_task(update.message.reply_to_message.delete())

    cnt = db.add_warning(ch.id, tid)
    await do_mute(ctx, ch.id, tid, db.get_warn_durations(ch.id)[cnt])

    # Build warning bar
    bars = "🟥" * cnt + "⬜" * (4 - cnt)

    # ── Auto-unmute captcha — target khud solve karke mute + warning hata
    # sake. Group /settings → Filters se yeh feature on/off ho sakta hai. ──
    warncaptcha_on = db.get_filters(ch.id).get("warncaptcha", True)
    if warncaptcha_on:
        cap_question, cap_answer, cap_options = generate_captcha()
        MUTE_CAPTCHA_PENDING[f"{ch.id}_{tid}"] = {"answer": cap_answer}
        captcha_block = (
            f"\n\n🔐 *𝗔𝘂𝘁𝗼-𝗨𝗻𝗺𝘂𝘁𝗲 𝗖𝗮𝗽𝘁𝗰𝗵𝗮*\n"
            f"Tap the right answer below — the mute lifts *instantly*\n"
            f"and *all warnings get cleared* too:\n\n"
            f"      `{cap_question}`"
        )
        warn_kb_plain = kb_warn_captcha(ch.id, tid, cap_options)
    else:
        captcha_block = ""
        warn_kb_plain = kb_warn_actions(ch.id, tid)

    msg = await update.message.reply_text(
        f"⚠️ *𝗪𝗔𝗥𝗡𝗜𝗡𝗚 𝗜𝗦𝗦𝗨𝗘𝗗*\n"
        f"{'─'*14}\n\n"
        f"👤 {target_name(tobj, tid)}\n"
        f"📋 Reason: _{reason}_\n\n"
        f"Progress: {bars} `{cnt}/4`\n\n"
        f"{WARN_MSG[cnt]}"
        f"{captcha_block}",        parse_mode='Markdown',
        reply_markup=warn_kb_plain
    )
    asyncio.create_task(delete_after(ctx, ch.id, msg.message_id, 90))
    if warncaptcha_on:
        asyncio.create_task(_cleanup_mute_captcha(ch.id, tid, 95))


# ─── /warnings ──────────────────────────────────────────────
async def warnings_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ch = update.effective_chat
    if ch.type == "private": return
    # Safe extraction — reply_to_message ho toh uska user, warna khud
    if update.message.reply_to_message and update.message.reply_to_message.from_user:
        tgt = update.message.reply_to_message.from_user
    else:
        tgt = update.effective_user
    if not tgt:
        return await update.message.reply_text("⚠️ Couldn't identify that user (anonymous or channel reply).")
    if db.is_gmuted(tgt.id):
        try:
            msg = await update.message.reply_text(
                f"👤 {user_name(tgt, escape=True)}\n\n"
                f"💀 *𝗚𝗟𝗢𝗕𝗔𝗟𝗟𝗬 𝗠𝗨𝗧𝗘𝗗* — 1-week mute active.",
                parse_mode='Markdown'
            )
        except Exception:
            msg = await update.message.reply_text(
                f"👤 {user_name(tgt, escape=False)}\n\n"
                f"💀 GLOBALLY MUTED — 1-week mute active."
            )
        asyncio.create_task(delete_after(ctx, ch.id, msg.message_id, 600))
        return
    w = db.get_warnings(ch.id, tgt.id)
    bars = "🟥" * w + "⬜" * (4 - w)
    text = (
        f"📊 *𝗪𝗮𝗿𝗻𝗶𝗻𝗴 𝗦𝘁𝗮𝘁𝘂𝘀*\n"
        f"{'─'*14}\n\n"
        f"👤 {user_mention(tgt)}\n"
        f"Count: `{w}/4`\n"
        f"Scale: {bars}"
    )
    try:
        msg = await update.message.reply_text(text, parse_mode='Markdown')
    except Exception:
        # Naam mein koi aisa special character ho sakta hai jo Markdown
        # todta ho — plain text mein fallback taaki reply hamesha aaye,
        # kabhi bhi silently fail na ho.
        msg = await update.message.reply_text(
            f"📊 Warning Status\n{'─'*14}\n\n"
            f"👤 {user_name(tgt, escape=False)}\n"
            f"Count: {w}/4\n"
            f"Scale: {bars}"
        )
    asyncio.create_task(delete_after(ctx, ch.id, msg.message_id, 600))


# ─── /resetwarnings ─────────────────────────────────────────
async def reset_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ANON_ADMIN_ID = 1087968824
    ch = update.effective_chat
    if ch.type == "private":
        return
    if not await sender_is_admin(ctx, update):
        return await update.message.reply_text("🔒 Admins only.")
    tid, tobj, _, err = await resolve_target(
        update, ctx,
        "↩️ Reply to a user, or use `/resetwarnings <user_id | @username>`"
    )
    if err:
        return await update.message.reply_text(err, parse_mode='Markdown')
    if tid == ANON_ADMIN_ID:
        return await update.message.reply_text(
            "⚠️ This is an *anonymous admin* message, so the real user can't be identified.\n"
            "Reply to that user's own (non-anonymous) message and try again, "
            "or use their user ID/@username directly.",
            parse_mode='Markdown'
        )
    db.reset_warnings(ch.id, tid)
    await do_unmute(ctx, ch.id, tid)
    text = f"✅ *𝗪𝗮𝗿𝗻𝗶𝗻𝗴𝘀 𝗿𝗲𝘀𝗲𝘁*\n\n👤 {target_name(tobj, tid, escape=True)} now has 0 warnings — unmuted in this group."
    try:
        await update.message.reply_text(text, parse_mode='Markdown')
    except Exception:
        # Naam mein Markdown-breaking character ho sakta hai — plain text
        # fallback taaki confirmation kabhi bhi silently gayab na ho.
        await update.message.reply_text(
            f"✅ Warnings reset\n\n👤 {target_name(tobj, tid, escape=False)} now has 0 warnings — unmuted in this group."
        )


# ─── /del ───────────────────────────────────────────────────
async def del_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == "private": return
    if not await is_adm(ctx, update.effective_chat.id, update.effective_user.id): return
    if not update.message.reply_to_message: return
    try:
        await update.message.reply_to_message.delete()
        await update.message.delete()
    except:
        pass


# ─── /purge ─────────────────────────────────────────────────
async def purge_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ch = update.effective_chat
    if ch.type == "private": return
    if not await sender_is_admin(ctx, update):
        return await update.message.reply_text("🔒 Admins only.")
    if not update.message.reply_to_message:
        return await update.message.reply_text("↩️ Reply to the message you want to start from.")

    from_msg_id = update.message.reply_to_message.message_id
    to_msg_id   = update.message.message_id
    deleted = 0
    failed  = 0

    ids_to_delete = list(range(from_msg_id, to_msg_id + 1))
    for i in range(0, len(ids_to_delete), 100):
        batch = ids_to_delete[i:i+100]
        for mid in batch:
            try:
                await ctx.bot.delete_message(ch.id, mid)
                deleted += 1
            except:
                failed += 1
        await asyncio.sleep(0.1)

    msg = await ctx.bot.send_message(
        ch.id,
        f"🧹 *𝗣𝘂𝗿𝗴𝗲 𝗖𝗼𝗺𝗽𝗹𝗲𝘁𝗲*\n\n"
        f"🗑️ Deleted: `{deleted}` messages\n"
        f"⚠️ Skipped: `{failed}` messages",
        parse_mode='Markdown'
    )
    asyncio.create_task(delete_after(ctx, ch.id, msg.message_id, 5))


# ─── Owner Commands ──────────────────────────────────────────
async def broadcast_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    reply = update.message.reply_to_message
    args = list(ctx.args) if ctx.args else []

    # Agar aakhri argument ek number hai, use auto-delete minutes maano
    # (dono cases mein chalega: "/broadcast <msg> 30" aur reply karke "/broadcast 30")
    delete_minutes = None
    if args and args[-1].isdigit():
        delete_minutes = int(args[-1])
        args = args[:-1]

    msg_text = ' '.join(args) if args else None

    if not reply and not msg_text:
        return await update.message.reply_text(
            "⚙️ <b>Usage:</b>\n"
            "• <code>/broadcast &lt;message&gt;</code> — sends plain text to all groups\n"
            "• <code>/broadcast &lt;message&gt; 30</code> — same, but auto-deletes after 30 min\n"
            "• Reply to any message (text, photo, video, etc.) with <code>/broadcast</code> — "
            "sends that exact message (as-is) to all groups\n"
            "• Reply with <code>/broadcast 30</code> — same, but auto-deletes after 30 min",
            parse_mode='HTML'
        )

    s = f = 0
    for gid in db.get_all_groups():
        try:
            if reply:
                # Jo bhi message reply kiya gaya hai (text/photo/video/document/etc.)
                # usse hoobahoo copy karke bhejo — koi extra header/footer nahi.
                sent = await ctx.bot.copy_message(
                    chat_id=gid,
                    from_chat_id=update.effective_chat.id,
                    message_id=reply.message_id
                )
            else:
                # Sirf woh text jo diya gaya hai — koi "📢 BROADCAST" wrapper nahi
                sent = await ctx.bot.send_message(gid, msg_text, parse_mode='Markdown')

            if delete_minutes:
                asyncio.create_task(delete_after(ctx, gid, sent.message_id, delete_minutes * 60))

            s += 1
            await asyncio.sleep(0.1)
        except:
            f += 1

    summary = f"📢 *𝗕𝗿𝗼𝗮𝗱𝗰𝗮𝘀𝘁 𝗖𝗼𝗺𝗽𝗹𝗲𝘁𝗲*\n\n✅ Sent: `{s}`\n❌ Failed: `{f}`"
    if delete_minutes:
        summary += f"\n🗑️ Auto-delete in: `{delete_minutes} min` (in every group it was sent to)"
    await update.message.reply_text(summary, parse_mode='Markdown')


GROUPS_PER_PAGE = 25
_groups_list_cache: dict[int, list] = {}   # owner_id -> resolved group rows (in-memory cache for pagination)


async def _resolve_group_full(ctx: ContextTypes.DEFAULT_TYPE, gid: int, me_id: int):
    """
    Ek group ke baare mein poori detail nikalta hai: (title, invite_link, member_count, status)
    status teen values le sakta hai:
      "ok"      → bot is group mein ADMIN/CREATOR hai, sab sahi hai
      "removed" → CONFIRM ho gaya ki bot ab is group ka admin nahi hai
                  (bot ko group se nikala gaya / left / kicked / banned / demote kiya gaya)
                  → caller ise database se hata dega
      "unknown" → Telegram se temporary error aaya (network/timeout/flood-wait)
                  → yeh group SKIP hoga is baar, par database se DELETE NAHI hoga,
                  agli baar /groups chalane par firse try hoga
    """
    # get_chat_member ek hi call kaafi hai — get_chat + get_chat_member_count
    # alag se maangna matlab har group ke liye 3x zyada API calls, jisse
    # bade group count par Telegram flood-control lag jaata hai.
    for attempt in range(2):
        try:
            bot_member = await ctx.bot.get_chat_member(gid, me_id)
            break
        except RetryAfter as e:
            # Flood control — thoda ruk ke ek baar aur try karo, group ko galat se stale mat maano
            await asyncio.sleep(e.retry_after + 0.5)
            continue
        except Forbidden:
            # Bot ko definitely block/kick kiya gaya hai is group se
            return (str(gid), None, None, "removed")
        except BadRequest as e:
            msg = str(e).lower()
            if "chat not found" in msg or "user not found" in msg or "not enough rights" in msg:
                return (str(gid), None, None, "removed")
            return (str(gid), None, None, "unknown")
        except (TimedOut, NetworkError):
            return (str(gid), None, None, "unknown")
        except Exception:
            return (str(gid), None, None, "unknown")
    else:
        return (str(gid), None, None, "unknown")

    if bot_member.status in ("left", "kicked", "banned"):
        return (str(gid), None, None, "removed")
    if bot_member.status not in ("administrator", "creator"):
        # Group mein member to hai par admin nahi — protection features kaam nahi karenge
        return (str(gid), None, None, "removed")

    # Ab title/username/member-count nikalo (bot admin confirm ho chuka hai)
    try:
        chat = await ctx.bot.get_chat(gid)
        title = chat.title or chat.first_name or str(gid)
    except Exception:
        # Admin status confirm hai, sirf naam fetch fail hua — group ko list mein rakho
        title = str(gid)
        chat = None

    members = None
    try:
        members = await ctx.bot.get_chat_member_count(gid)
    except Exception:
        pass

    link = None
    try:
        if chat and chat.username:
            link = f"https://t.me/{chat.username}"
        elif chat and chat.invite_link:
            link = chat.invite_link
    except Exception:
        pass

    return (title, link, members, "ok")


def _build_groups_page(rows: list, page: int):
    total = len(rows)
    total_pages = max(1, (total + GROUPS_PER_PAGE - 1) // GROUPS_PER_PAGE)
    page = max(0, min(page, total_pages - 1))
    start = page * GROUPS_PER_PAGE
    chunk = rows[start:start + GROUPS_PER_PAGE]

    lines = [f"👥 <b>𝗔𝗰𝘁𝗶𝘃𝗲 𝗚𝗿𝗼𝘂𝗽𝘀:</b> {total}  <i>(page {page+1}/{total_pages})</i>\n"]
    for i, (title, link, members) in enumerate(chunk, start=start + 1):
        title_safe = html.escape(title)
        mem_txt = f" — 👤 {members}" if members is not None else ""
        if link:
            lines.append(f"{i}. <a href=\"{html.escape(link)}\">{title_safe}</a>{mem_txt}")
        else:
            lines.append(f"{i}. {title_safe}{mem_txt}")

    buttons = []
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton("◀️ 𝗣𝗿𝗲𝘃", callback_data=f"grppg_{page-1}"))
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton("𝗡𝗲𝘅𝘁 ▶️", callback_data=f"grppg_{page+1}"))
    if nav_row:
        buttons.append(nav_row)

    markup = InlineKeyboardMarkup(buttons) if buttons else None
    return "\n".join(lines), markup


async def groups_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    group_ids = db.get_all_groups()
    if not group_ids:
        return await update.message.reply_text("👥 No groups found.")

    status_msg = await update.message.reply_text(
        f"⏳ Fetching details for {len(group_ids)} groups…"
    )

    me = await ctx.bot.get_me()

    rows = []          # (title, link, members) — sirf confirmed-admin groups
    removed_ids = []   # confirmed removed/non-admin groups
    unknown_count = 0  # temporary errors — in groups ko haath nahi lagaya

    for gid in group_ids:
        title, link, members, status = await _resolve_group_full(ctx, gid, me.id)
        if status == "ok":
            rows.append((title, link, members))
        elif status == "removed":
            removed_ids.append(gid)
        else:
            unknown_count += 1
        await asyncio.sleep(0.15)  # flood-control se bachne ke liye

    if removed_ids:
        for gid in removed_ids:
            db.remove_group(gid)

    _groups_list_cache[update.effective_user.id] = rows

    await status_msg.delete()

    if not rows:
        note = "👥 No groups found where the bot is currently admin."
        if unknown_count:
            note += f"\n⚠️ {unknown_count} group(s) could not be checked right now — try /groups again in a bit."
        return await update.message.reply_text(note)

    text, markup = _build_groups_page(rows, 0)
    footer = []
    if removed_ids:
        footer.append(f"🧹 <i>{len(removed_ids)} group(s) where bot isn't admin were cleaned from database.</i>")
    if unknown_count:
        footer.append(f"⚠️ <i>{unknown_count} group(s) skipped due to a temporary error — re-run /groups to recheck them.</i>")
    if footer:
        text += "\n\n" + "\n".join(footer)

    await update.message.reply_text(text, parse_mode='HTML', disable_web_page_preview=True, reply_markup=markup)


async def groups_page_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if update.effective_user.id != OWNER_ID:
        return await query.answer("🔒 Not for you.", show_alert=True)

    rows = _groups_list_cache.get(update.effective_user.id)
    if not rows:
        return await query.answer("⚠️ List expired — run /groups again.", show_alert=True)

    page = int(query.data.split("_", 1)[1])
    text, markup = _build_groups_page(rows, page)
    await query.answer()
    await query.edit_message_text(text, parse_mode='HTML', disable_web_page_preview=True, reply_markup=markup)


async def regroup_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """
    Owner-only recovery tool: /regroup <chat_id> [chat_id2 ...]
    Kisi purani buggy run mein agar koi valid group database se galti se
    hat gaya tha, to uska chat_id yahan de kar wapas register kiya ja sakta hai —
    bas condition yeh hai ki bot abhi bhi us group mein ADMIN ho.
    """
    if update.effective_user.id != OWNER_ID: return
    if not ctx.args:
        return await update.message.reply_text(
            "⚙️ <b>Usage:</b>\n<code>/regroup -1001234567890 -1009876543210</code>\n\n"
            "Give one or more group chat IDs (space-separated) — "
            "the bot will check whether it's still an admin there, and "
            "re-add it to the database if so.",
            parse_mode='HTML'
        )

    me = await ctx.bot.get_me()
    added, failed = [], []
    for raw in ctx.args:
        try:
            gid = int(raw)
        except ValueError:
            failed.append(f"{raw} (invalid id)")
            continue
        title, link, members, status = await _resolve_group_full(ctx, gid, me.id)
        if status == "ok":
            db.add_group(gid)
            added.append(html.escape(title))
        elif status == "removed":
            failed.append(f"{gid} (bot isn't admin there)")
        else:
            failed.append(f"{gid} (couldn't verify — try again)")
        await asyncio.sleep(0.15)

    lines = []
    if added:
        lines.append("✅ <b>Re-added to database:</b>\n" + "\n".join(f"• {t}" for t in added))
    if failed:
        lines.append("❌ <b>Could not add:</b>\n" + "\n".join(f"• {f}" for f in failed))
    await update.message.reply_text("\n\n".join(lines) or "Nothing to do.", parse_mode='HTML')


GLOBAL_REP_ID = 0  # owner DM se diya gaya reputation isi "virtual group" mein store hota hai


async def reputation_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """
    Owner-only command. Teen tarike se chalti hai:
      1) Bot ki DM se:            /reputation <user_id> <amount>
         → is user ka GLOBAL rep (total_rep mein count hoga, kisi ek
           group se bandha nahi hai, isliye Guardian Coin mein convert
           nahi hota — sirf tier/display ke liye).
      2) Group mein, kisi user ko reply karke: /reputation <amount>
         → usi group ke rep balance mein credit/debit hota hai.
      3) Group mein directly:      /reputation <user_id> <amount>
         → usi group ke rep balance mein credit/debit hota hai.
    Amount negative bhi ho sakta hai (rep kaatne ke liye).
    """
    if update.effective_user.id != OWNER_ID: return
    ch = update.effective_chat
    args = ctx.args

    target_id, amount, chat_id = None, None, None

    if update.message.reply_to_message and args and len(args) >= 1:
        # Group mein reply karke — sirf amount chahiye
        try:
            target_id = update.message.reply_to_message.from_user.id
            amount = int(args[0])
            chat_id = ch.id
        except ValueError:
            pass
    elif args and len(args) >= 2:
        try:
            target_id = int(args[0])
            amount = int(args[1])
            # Private (DM) mein → global rep. Group mein → usi group ka rep.
            chat_id = GLOBAL_REP_ID if (not ch or ch.type == "private") else ch.id
        except ValueError:
            pass

    if target_id is None or amount is None or chat_id is None:
        return await update.message.reply_text(
            "⚙️ *𝙐𝙨𝙖𝙜𝙚:*\n\n"
            "*Via the bot's DM (global rep):*\n"
            "`/reputation <user_id> <amount>`\n\n"
            "*𝙄𝙣 𝙖 𝙜𝙧𝙤𝙪𝙥:*\n"
            "`/reputation <user_id> <amount>`\n"
            "_or by replying to a user:_ `/reputation <amount>`",
            parse_mode='Markdown'
        )

    try:
        target_chat = await ctx.bot.get_chat(target_id)
        name = target_chat.first_name or str(target_id)
    except Exception:
        name = str(target_id)

    db.add_reputation(chat_id, target_id, amount, name, force_convertible=True)
    new_rep = db.get_reputation(chat_id, target_id)
    action = "credited" if amount >= 0 else "deducted"
    is_global = chat_id == GLOBAL_REP_ID
    scope = "🌐 *Global* (given via DM)" if is_global else "in this group"
    await update.message.reply_text(
        f"✅ *𝗥𝗲𝗽𝘂𝘁𝗮𝘁𝗶𝗼𝗻 𝗨𝗽𝗱𝗮𝘁𝗲𝗱*\n"
        f"{'─'*14}\n"
        f"👤 User: `{target_id}`\n"
        f"📈 `{abs(amount)}` points {action} {scope}\n"
        f"📊 New balance: `{new_rep}` rep",
        parse_mode='Markdown'
    )


async def globalmutes_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    mutes = db.get_all_gmutes()
    await update.message.reply_text(
        f"🗓️ *𝙂𝙡𝙤𝙗𝙖𝙡 𝙈𝙪𝙩𝙚𝙨:* `{len(mutes)}`",
        parse_mode='Markdown'
    )


async def unglobalmute_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    if not ctx.args:
        return await update.message.reply_text("ℹ️ Usage: `/unglobalmute <id>`", parse_mode='Markdown')
    try:
        uid = int(ctx.args[0])
        db.remove_gmute(uid)
        await update.message.reply_text(
            f"✅ `{uid}` removed from global mute.",
            parse_mode='Markdown'
        )
    except:
        await update.message.reply_text("⚠️ That doesn't look like a valid ID.")


# ─── /gblacklist ────────────────────────────────────────────
async def gblacklist_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Owner only — add/remove/list global blacklist words (apply to ALL groups)"""
    if update.effective_user.id != OWNER_ID:
        return await update.message.reply_text("🔒 Owner access only.")

    if not ctx.args:
        # Show list
        words = db.get_gblacklist()
        if not words:
            return await update.message.reply_text(
                "📋 *𝗚𝗹𝗼𝗯𝗮𝗹 𝗕𝗹𝗮𝗰𝗸𝗹𝗶𝘀𝘁* is empty.\n\n"
                "Usage:\n"
                "`/gblacklist add <word>` — Add word\n"
                "`/gblacklist remove <word>` — Remove word\n"
                "`/gblacklist list` — Show all words",
                parse_mode='Markdown'
            )
        word_list = "\n".join(f"  • `{w}`" for w in words)
        return await update.message.reply_text(
            f"🌐 *𝗚𝗹𝗼𝗯𝗮𝗹 𝗕𝗹𝗮𝗰𝗸𝗹𝗶𝘀𝘁* ({len(words)} words)\n"
            f"{'─'*14}\n\n"
            f"{word_list}\n\n"
            f"_These words are blocked in ALL groups._",
            parse_mode='Markdown'
        )

    action = ctx.args[0].lower()

    if action == "list":
        words = db.get_gblacklist()
        if not words:
            return await update.message.reply_text("📋 Global blacklist is empty.")
        word_list = "\n".join(f"  • `{w}`" for w in words)
        return await update.message.reply_text(
            f"🌐 *𝗚𝗹𝗼𝗯𝗮𝗹 𝗕𝗹𝗮𝗰𝗸𝗹𝗶𝘀𝘁* ({len(words)} words)\n"
            f"{'─'*14}\n\n"
            f"{word_list}",
            parse_mode='Markdown'
        )

    if action in ("add", "remove") and len(ctx.args) < 2:
        return await update.message.reply_text(
            f"❌ Usage: `/gblacklist {action} <word>`",
            parse_mode='Markdown'
        )

    word = " ".join(ctx.args[1:]).lower().strip()

    if action == "add":
        db.add_gblacklist(word)
        await update.message.reply_text(
            f"✅ *𝗔𝗱𝗱𝗲𝗱 𝘁𝗼 𝗚𝗹𝗼𝗯𝗮𝗹 𝗕𝗹𝗮𝗰𝗸𝗹𝗶𝘀𝘁*\n\n"
            f"🚫 `{word}`\n\n"
            f"_This word is now blocked in ALL your groups._",
            parse_mode='Markdown'
        )

    elif action == "remove":
        db.remove_gblacklist(word)
        await update.message.reply_text(
            f"✅ *𝗥𝗲𝗺𝗼𝘃𝗲𝗱 𝗳𝗿𝗼𝗺 𝗚𝗹𝗼𝗯𝗮𝗹 𝗕𝗹𝗮𝗰𝗸𝗹𝗶𝘀𝘁*\n\n"
            f"🗑️ `{word}`",
            parse_mode='Markdown'
        )

    else:
        await update.message.reply_text(
            "⚠️ Unknown action.\n\n"
            "Usage:\n"
            "`/gblacklist add <word>`\n"
            "`/gblacklist remove <word>`\n"
            "`/gblacklist list`",
            parse_mode='Markdown'
        )


# ─── /gwhitelist ────────────────────────────────────────────
async def gwhitelist_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Owner only — global whitelist, exempt from gblacklist in ALL groups"""
    if update.effective_user.id != OWNER_ID:
        return await update.message.reply_text("🔒 Owner access only.")

    if not ctx.args:
        words = db.get_gwhitelist()
        if not words:
            return await update.message.reply_text(
                "📋 *𝗚𝗹𝗼𝗯𝗮𝗹 𝗪𝗵𝗶𝘁𝗲𝗹𝗶𝘀𝘁* is empty.\n\n"
                "Usage:\n"
                "`/gwhitelist add <word>` — Allow word globally\n"
                "`/gwhitelist remove <word>` — Remove\n"
                "`/gwhitelist list` — Show all",
                parse_mode='Markdown'
            )
        word_list = "\n".join(f"  • `{w}`" for w in words)
        return await update.message.reply_text(
            f"🌐 *𝗚𝗹𝗼𝗯𝗮𝗹 𝗪𝗵𝗶𝘁𝗲𝗹𝗶𝘀𝘁* ({len(words)} words)\n"
            f"{'─'*14}\n\n"
            f"{word_list}\n\n"
            f"_These words are allowed even if in global blacklist._",
            parse_mode='Markdown'
        )

    action = ctx.args[0].lower()

    if action == "list":
        words = db.get_gwhitelist()
        if not words:
            return await update.message.reply_text("📋 Global whitelist is empty.")
        word_list = "\n".join(f"  • `{w}`" for w in words)
        return await update.message.reply_text(
            f"🌐 *𝗚𝗹𝗼𝗯𝗮𝗹 𝗪𝗵𝗶𝘁𝗲𝗹𝗶𝘀𝘁* ({len(words)} words)\n"
            f"{'─'*14}\n\n"
            f"{word_list}",
            parse_mode='Markdown'
        )

    if action in ("add", "remove") and len(ctx.args) < 2:
        return await update.message.reply_text(
            f"❌ Usage: `/gwhitelist {action} <word>`",
            parse_mode='Markdown'
        )

    word = " ".join(ctx.args[1:]).lower().strip()

    if action == "add":
        db.add_gwhitelist(word)
        await update.message.reply_text(
            f"✅ *𝗔𝗱𝗱𝗲𝗱 𝘁𝗼 𝗚𝗹𝗼𝗯𝗮𝗹 𝗪𝗵𝗶𝘁𝗲𝗹𝗶𝘀𝘁*\n\n"
            f"✔️ `{word}`\n\n"
            f"_This word is now allowed in ALL groups._",
            parse_mode='Markdown'
        )
    elif action == "remove":
        db.remove_gwhitelist(word)
        await update.message.reply_text(
            f"✅ *𝗥𝗲𝗺𝗼𝘃𝗲𝗱 𝗳𝗿𝗼𝗺 𝗚𝗹𝗼𝗯𝗮𝗹 𝗪𝗵𝗶𝘁𝗲𝗹𝗶𝘀𝘁*\n\n"
            f"🗑️ `{word}`",
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            "⚠️ Unknown action.\n\n"
            "Usage:\n"
            "`/gwhitelist add <word>`\n"
            "`/gwhitelist remove <word>`\n"
            "`/gwhitelist list`",
            parse_mode='Markdown'
        )


# ─── /power ─────────────────────────────────────────────────
async def power_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Owner only — grant a user fban/gunban power."""
    if update.effective_user.id != OWNER_ID:
        return await update.message.reply_text("🔒 Owner access only.")

    tid, tobj, _, err = await resolve_target(
        update, ctx,
        "❌ Usage: `/power <user_id | @username>` or reply to user"
    )
    if err:
        return await update.message.reply_text(err, parse_mode='Markdown')

    db.add_powered(tid)
    await update.message.reply_text(
        f"⚡ *𝗣𝗼𝘄𝗲𝗿 𝗚𝗿𝗮𝗻𝘁𝗲𝗱*\n"
        f"{'─'*14}\n\n"
        f"🆔 User: {target_name(tobj, tid)} can now use `/fban` and `/gunban`.\n\n"
        f"Use `/unpower {tid}` to revoke.",
        parse_mode='Markdown'
    )


# ─── /unpower ───────────────────────────────────────────────
async def unpower_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Owner only — revoke fban power from a user."""
    if update.effective_user.id != OWNER_ID:
        return await update.message.reply_text("🔒 Owner access only.")

    tid, tobj, _, err = await resolve_target(
        update, ctx,
        "❌ Usage: `/unpower <user_id | @username>` or reply to user"
    )
    if err:
        return await update.message.reply_text(err, parse_mode='Markdown')

    db.remove_powered(tid)
    await update.message.reply_text(
        f"✅ Power *revoked* from {target_name(tobj, tid)}.",
        parse_mode='Markdown'
    )


# ─── /fban ──────────────────────────────────────────────────
async def fban_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """
    Owner or powered user only.
    Bans user from ALL groups silently + deletes all their messages.
    Usage: /fban <user_id | @username> [reason]
    """
    caller = update.effective_user.id
    if caller != OWNER_ID and not db.is_powered(caller):
        return  # silent ignore — no response

    target_id   = None
    target_name = None
    reason_start = 1

    # Resolve target from reply or args
    if update.message.reply_to_message:
        tgt_user = update.message.reply_to_message.from_user
        target_id   = tgt_user.id
        target_name = user_name(tgt_user)
        reason_start = 0  # all args are reason
    elif ctx.args:
        raw = ctx.args[0]
        try:
            target_id = int(raw)
        except ValueError:
            # Username given
            uname = raw.lstrip('@')
            try:
                chat_obj = await ctx.bot.get_chat(f"@{uname}")
                target_id   = chat_obj.id
                target_name = md_esc(chat_obj.first_name or uname)
            except Exception:
                return await update.message.reply_text(
                    f"❌ Cannot find user: `{raw}`",
                    parse_mode='Markdown'
                )
    else:
        return await update.message.reply_text(
            "❌ Usage: `/fban <user_id | @username> [reason]`\n"
            "or reply to user + `/fban [reason]`",
            parse_mode='Markdown'
        )

    # Bot / owner cannot be fbanned
    if target_id == ctx.bot.id or target_id == OWNER_ID:
        return await update.message.reply_text("⚠️ This user can't be banned.")

    reason = ' '.join(ctx.args[reason_start:]) if ctx.args and reason_start < len(ctx.args) else "No reason provided"

    # Save to DB
    db.add_fban(target_id, reason)

    all_groups = db.get_all_groups()
    banned_count  = 0
    deleted_count = 0

    for gid in all_groups:
        # Delete all messages from this user in this group (last 48h limit by Telegram)
        try:
            # We can only delete by scanning recent messages — instead we'll use
            # delete_messages for found message ids stored in context if any.
            # Telegram doesn't expose "delete all msgs by user" API directly,
            # so we ban (which auto-hides nothing) then try ban_chat_member.
            pass
        except Exception:
            pass

        # Ban the user silently
        try:
            await ctx.bot.ban_chat_member(gid, target_id)
            banned_count += 1
        except Exception:
            pass

        await asyncio.sleep(0.05)

    # Confirm silently to the caller only (no group notification)
    confirm_text = (
        f"💀 *𝗚𝗹𝗼𝗯𝗮𝗹 𝗕𝗮𝗻 𝗘𝘅𝗲𝗰𝘂𝘁𝗲𝗱*\n"
        f"{'─'*14}\n\n"
        f"👤 User: `{target_id}`"
        f"{f'  ({target_name})' if target_name else ''}\n"
        f"📋 Reason: _{reason}_\n"
        f"🔨 Banned in: `{banned_count}` groups\n\n"
        f"Use `/gunban {target_id}` to reverse."
    )
    await update.message.reply_text(confirm_text, parse_mode='Markdown')


# ─── /gunban ────────────────────────────────────────────────
async def gunban_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """
    Owner or powered user only.
    Unbans user from ALL groups silently — no group notifications.
    """
    caller = update.effective_user.id
    if caller != OWNER_ID and not db.is_powered(caller):
        return  # silent ignore

    target_id = None

    if update.message.reply_to_message:
        target_id = update.message.reply_to_message.from_user.id
    elif ctx.args:
        raw = ctx.args[0]
        try:
            target_id = int(raw)
        except ValueError:
            uname = raw.lstrip('@')
            try:
                chat_obj = await ctx.bot.get_chat(f"@{uname}")
                target_id = chat_obj.id
            except Exception:
                return await update.message.reply_text(
                    f"❌ Cannot find user: `{raw}`",
                    parse_mode='Markdown'
                )
    else:
        return await update.message.reply_text(
            "❌ Usage: `/gunban <user_id | @username>`",
            parse_mode='Markdown'
        )

    db.remove_fban(target_id)

    all_groups   = db.get_all_groups()
    unbanned_count = 0

    for gid in all_groups:
        try:
            await ctx.bot.unban_chat_member(gid, target_id)
            unbanned_count += 1
        except Exception:
            pass
        await asyncio.sleep(0.05)

    await update.message.reply_text(
        f"✅ *𝗚𝗹𝗼𝗯𝗮𝗹 𝗨𝗻𝗯𝗮𝗻 𝗖𝗼𝗺𝗽𝗹𝗲𝘁𝗲*\n"
        f"{'─'*14}\n\n"
        f"👤 User `{target_id}` unbanned from `{unbanned_count}` groups.\n"
        f"_No notifications were sent to any group._",
        parse_mode='Markdown'
    )


# ═══════════════════════════════════════════════════════════
#  GLOBAL MUTE (owner-only, DM-only) — a true "every group the
#  bot manages" mute, kept completely separate from the normal
#  per-group warn/mute escalation (which never leaves its own group).
# ═══════════════════════════════════════════════════════════
# ─── /gmute ─────────────────────────────────────────────────
async def gmute_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """
    Bot OWNER only, and only from the bot's own DM.
    Mutes a user across EVERY group the bot manages.
    Usage (in bot DM): /gmute <user_id | @username>
    """
    usr = update.effective_user
    ch  = update.effective_chat
    if not usr or usr.id != OWNER_ID:
        return  # silent ignore
    if ch.type != "private":
        return await update.message.reply_text(
            "🔒 `/gmute` only works from the bot's own DM (to save server load)."
        )
    tid, tobj, _, err = await resolve_target(
        update, ctx,
        "❌ Usage: `/gmute <user_id | @username>`"
    )
    if err:
        return await update.message.reply_text(err, parse_mode='Markdown')
    if tid == ctx.bot.id or tid == OWNER_ID:
        return await update.message.reply_text("⚠️ This user can't be muted.")

    await global_mute_user(ctx, tid, target_name(tobj, tid))
    await update.message.reply_text(
        f"💀 *𝗚𝗹𝗼𝗯𝗮𝗹 𝗠𝘂𝘁𝗲 𝗔𝗽𝗽𝗹𝗶𝗲𝗱*\n"
        f"{'─'*14}\n\n"
        f"👤 {target_name(tobj, tid)}\n"
        f"🌐 Muted for *1 week* — across *every group* the bot manages.\n\n"
        f"_Lift it early with `/unmute {tid}` from this DM._",
        parse_mode='Markdown'
    )


# ═══════════════════════════════════════════════════════════
#  COMMUNITY SYSTEM — lets any group admin/owner link their own
#  group(s) together so they can /gban a user across just their
#  own groups (not the entire bot), without needing owner power.
# ═══════════════════════════════════════════════════════════
# ─── /addcommunity ──────────────────────────────────────────
async def addcommunity_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Run inside a group by that group's admin/owner — adds THIS group
    to the caller's own community list."""
    ch  = update.effective_chat
    usr = update.effective_user
    if ch.type == "private":
        return await update.message.reply_text(
            "⚠️ Run this command inside the group you want to add to your community."
        )
    if not await sender_is_admin(ctx, update):
        return await update.message.reply_text("🔒 Only this group's admin/owner can add it to a community.")
    db.add_to_community(usr.id, ch.id)
    n = len(db.get_community_groups(usr.id))
    await update.message.reply_text(
        f"✅ *{md_esc(ch.title or 'This group')}* has been added to your community\\.\n\n"
        f"🌐 Total community groups: `{n}`\n\n"
        f"_`/gban` and non\\-owner `/unmute` will now cover this group too\\._",
        parse_mode='MarkdownV2'
    )


# ─── /removecommunity ───────────────────────────────────────
async def removecommunity_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Run inside a group — removes THIS group from the caller's community."""
    ch  = update.effective_chat
    usr = update.effective_user
    if ch.type == "private":
        return await update.message.reply_text(
            "⚠️ Run this command inside the group you want to remove from your community."
        )
    if not await sender_is_admin(ctx, update):
        return await update.message.reply_text("🔒 Only this group's admin/owner can remove it from a community.")
    db.remove_from_community(usr.id, ch.id)
    await update.message.reply_text(
        f"✅ *{md_esc(ch.title or 'This group')}* has been removed from your community.",
        parse_mode='Markdown'
    )


# ─── /mycommunity ───────────────────────────────────────────
async def mycommunity_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Lists the groups in the caller's own community (works in DM or group)."""
    usr = update.effective_user
    groups = db.get_community_groups(usr.id)
    if not groups:
        return await update.message.reply_text(
            "📭 Your community is empty right now.\n\n"
            "Run `/addcommunity` in any group where you're admin/owner — "
            "that group will be added to your community."
        )
    lines = []
    for gid in groups:
        try:
            chat = await ctx.bot.get_chat(gid)
            lines.append(f"• {chat.title}")
        except Exception:
            lines.append(f"• `{gid}`")
    await update.message.reply_text(
        f"🌐 *𝗬𝗼𝘂𝗿 𝗖𝗼𝗺𝗺𝘂𝗻𝗶𝘁𝘆* — `{len(groups)}` group(s)\n"
        f"{'─'*14}\n\n" + "\n".join(lines) +
        f"\n\n_`/gban` and `/unmute` (when run from DM or any group) will cover all these groups._",
        parse_mode='Markdown'
    )


# ─── /gban ───────────────────────────────────────────────────
async def gban_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """
    Any admin who has built a community via /addcommunity — bans a user
    across ONLY the groups in their own community (not the whole bot).
    Usable from bot DM or from any group.
    """
    usr = update.effective_user
    groups = db.get_community_groups(usr.id)
    if not groups:
        return await update.message.reply_text(
            "📭 You have no groups in your community.\n"
            "First run `/addcommunity` inside your group(s) where you're admin/owner."
        )

    tid, tobj, consumed, err = await resolve_target(
        update, ctx,
        "↩️ Reply to a user (inside the group), or use `/gban <user_id | @username> [reason]`"
    )
    if err:
        return await update.message.reply_text(err, parse_mode='Markdown')
    if tid == ctx.bot.id or tid == OWNER_ID:
        return await update.message.reply_text("⚠️ This user can't be banned.")

    rest_args = ctx.args[consumed:] if ctx.args else []
    reason = ' '.join(rest_args) if rest_args else "No reason provided"

    banned = 0
    for gid in groups:
        try:
            if await is_adm(ctx, gid, tid):
                continue  # community ke kisi group ka admin ban nahi hoga
            if await do_ban(ctx, gid, tid):
                banned += 1
            await asyncio.sleep(0.1)
        except Exception:
            pass

    await update.message.reply_text(
        f"🔨 *𝗖𝗼𝗺𝗺𝘂𝗻𝗶𝘁𝘆 𝗕𝗮𝗻*\n"
        f"{'─'*14}\n\n"
        f"👤 {target_name(tobj, tid)}\n"
        f"📋 Reason: _{reason}_\n"
        f"🌐 Banned from `{banned}/{len(groups)}` community group(s).",
        parse_mode='Markdown'
    )


# ─── /gclearwarn ────────────────────────────────────────────
async def gclearwarn_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """
    Owner + /power users — saare groups se ek saath user ki warnings clear karo.
    Usage: /gclearwarn <user_id | @username>
           Reply to message + /gclearwarn
    """
    caller = update.effective_user.id
    if caller != OWNER_ID and not db.is_powered(caller):
        return await update.message.reply_text("🔒 Owner or authorized users only.")

    target_id = None
    target_name = None

    if update.message.reply_to_message:
        tgt = update.message.reply_to_message.from_user
        target_id = tgt.id
        target_name = user_name(tgt)
    elif ctx.args:
        raw = ctx.args[0]
        try:
            target_id = int(raw)
        except ValueError:
            uname = raw.lstrip('@')
            try:
                chat_obj = await ctx.bot.get_chat(f"@{uname}")
                target_id = chat_obj.id
                target_name = md_esc(chat_obj.first_name or uname)
            except Exception:
                return await update.message.reply_text(
                    f"❌ User not found: `{raw}`", parse_mode='Markdown'
                )
    else:
        return await update.message.reply_text(
            "❌ Usage: `/gclearwarn <user_id | @username>`\n"
            "Or reply to the user's message and type `/gclearwarn`.",
            parse_mode='Markdown'
        )

    deleted = db.global_clear_warnings(target_id)

    await update.message.reply_text(
        f"🧹 *𝗚𝗹𝗼𝗯𝗮𝗹 𝗪𝗮𝗿𝗻𝗶𝗻𝗴𝘀 𝗖𝗹𝗲𝗮𝗿𝗲𝗱*\n"
        f"{'─'*14}\n\n"
        f"👤 User: {target_name or f'`{target_id}`'}\n"
        f"🗑️ Removed: `{deleted}` warning record(s) across all groups\n\n"
        f"_This user now has a fresh start — no warnings._",
        parse_mode='Markdown'
    )


# ─── /addteacher ────────────────────────────────────────────
async def addteacher_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Admin only — mark a user as teacher (special promo handling)."""
    ch = update.effective_chat
    if ch.type == "private":
        return await update.message.reply_text("⚠️ This command only works in a group.")
    if not await sender_is_admin(ctx, update):
        return await update.message.reply_text("🔒 Admins only.")

    target_id = None
    target_name = None

    if update.message.reply_to_message:
        tgt = update.message.reply_to_message.from_user
        target_id = tgt.id
        target_name = user_name(tgt)
    elif ctx.args:
        try:
            target_id = int(ctx.args[0])
        except ValueError:
            uname = ctx.args[0].lstrip('@')
            try:
                chat_obj = await ctx.bot.get_chat(f"@{uname}")
                target_id = chat_obj.id
                target_name = md_esc(uname)
            except Exception:
                return await update.message.reply_text(
                    f"❌ User not found: `{ctx.args[0]}`", parse_mode='Markdown'
                )
    else:
        return await update.message.reply_text(
            "❌ Usage: `/addteacher <id>` or reply to the user's message",
            parse_mode='Markdown'
        )

    db.add_teacher(ch.id, target_id)
    await update.message.reply_text(
        f"📚 *𝗧𝗲𝗮𝗰𝗵𝗲𝗿 𝗔𝗱𝗱𝗲𝗱*\n"
        f"{'─'*14}\n\n"
        f"👤 User: `{target_id}`{f'  ({target_name})' if target_name else ''}\n\n"
        f"🛡️ *𝙎𝙥𝙚𝙘𝙞𝙖𝙡 𝙝𝙖𝙣𝙙𝙡𝙞𝙣𝙜:*\n"
        f"  • 1st promo → just a polite warning, no mute\n"
        f"  • 2nd promo → 🔇 10 min mute\n"
        f"  • 3rd promo → 🔇 40 min mute\n"
        f"  • 4th promo → 🔇 70 min mute _(+30 min added each time)_\n\n"
        f"Use `/removeteacher {target_id}` to remove.",
        parse_mode='Markdown'
    )


# ─── /removeteacher ─────────────────────────────────────────
async def removeteacher_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ch = update.effective_chat
    if ch.type == "private":
        return await update.message.reply_text("⚠️ This command only works in a group.")
    if not await sender_is_admin(ctx, update):
        return await update.message.reply_text("🔒 Admins only.")

    tid, tobj, _, err = await resolve_target(
        update, ctx,
        "ℹ️ Usage: `/removeteacher <user_id | @username>` or reply to user"
    )
    if err:
        return await update.message.reply_text(err, parse_mode='Markdown')

    db.remove_teacher(ch.id, tid)
    db.reset_teacher_promo_count(ch.id, tid)
    await update.message.reply_text(
        f"✅ Teacher status removed for {target_name(tobj, tid)}.\n"
        f"_Their promo count has also been reset._",
        parse_mode='Markdown'
    )


# ─── /teachers ──────────────────────────────────────────────
async def teachers_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ch = update.effective_chat
    if ch.type == "private":
        return await update.message.reply_text("⚠️ This command only works in a group.")
    if not await sender_is_admin(ctx, update):
        return await update.message.reply_text("🔒 Admins only.")

    teachers = db.get_teachers(ch.id)
    if not teachers:
        return await update.message.reply_text(
            "📚 This group has no teachers yet.\n\n"
            "_Use `/addteacher` to add one._",
            parse_mode='Markdown'
        )

    lines = []
    for tid in teachers:
        cnt = db.get_teacher_promo_count(ch.id, tid)
        lines.append(f"  • `{tid}` — promo violations: `{cnt}`")

    await update.message.reply_text(
        f"📚 *𝗧𝗘𝗔𝗖𝗛𝗘𝗥𝗦*\n"
        f"{'─'*14}\n\n"
        + "\n".join(lines) +
        f"\n\n_Total: {len(teachers)} teacher(s)_",
        parse_mode='Markdown'
    )


async def adexempt_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """
    Owner only — globally exempt a bot/channel from autodelete.
    Usage: /adexempt <user_id | @username>
           /adexempt list
    """
    if update.effective_user.id != OWNER_ID:
        return await update.message.reply_text("🔒 Owner access only.")

    if not ctx.args or ctx.args[0].lower() == "list":
        exempts = db.get_all_ad_exempt()
        if not exempts:
            return await update.message.reply_text(
                "📋 *𝗔𝘂𝘁𝗼𝗱𝗲𝗹𝗲𝘁𝗲 𝗘𝘅𝗲𝗺𝗽𝘁 𝗟𝗶𝘀𝘁* is empty.\n\n"
                "Usage: `/adexempt <id | @username>` — add exempt\n"
                "`/unadexempt <id>` — remove exempt\n"
                "`/adexempt list` — show all",
                parse_mode='Markdown'
            )
        lines = "\n".join(f"  • `{eid}`" for eid in exempts)
        return await update.message.reply_text(
            f"🤖 *𝗔𝘂𝘁𝗼𝗱𝗲𝗹𝗲𝘁𝗲 𝗘𝘅𝗲𝗺𝗽𝘁* ({len(exempts)})\n"
            f"{'─'*14}\n\n"
            f"{lines}\n\n"
            f"_These bots/channels are NEVER auto-deleted._",
            parse_mode='Markdown'
        )

    raw = ctx.args[0]
    target_id = None

    # Reply se bhi le sakte ho
    if update.message.reply_to_message:
        r = update.message.reply_to_message
        target_id = r.from_user.id if r.from_user else (r.sender_chat.id if r.sender_chat else None)
    else:
        try:
            target_id = int(raw)
        except ValueError:
            uname = raw.lstrip('@')
            try:
                chat_obj = await ctx.bot.get_chat(f"@{uname}")
                target_id = chat_obj.id
            except Exception:
                return await update.message.reply_text(
                    f"❌ Cannot find: `{raw}`", parse_mode='Markdown'
                )

    if not target_id:
        return await update.message.reply_text("⚠️ Couldn't resolve that ID.")

    db.add_ad_exempt(target_id)
    await update.message.reply_text(
        f"✅ *𝗘𝘅𝗲𝗺𝗽𝘁𝗶𝗼𝗻 𝗔𝗱𝗱𝗲𝗱*\n\n"
        f"🤖 ID `{target_id}` — messages will *never* be auto-deleted.\n"
        f"Use `/unadexempt {target_id}` to remove.",
        parse_mode='Markdown'
    )


# ─── /unadexempt ────────────────────────────────────────────
async def unadexempt_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Owner only — remove autodelete exemption."""
    if update.effective_user.id != OWNER_ID:
        return await update.message.reply_text("🔒 Owner access only.")

    target_id = None

    if update.message.reply_to_message:
        r = update.message.reply_to_message
        target_id = r.from_user.id if r.from_user else (r.sender_chat.id if r.sender_chat else None)
    elif ctx.args:
        try:
            target_id = int(ctx.args[0])
        except ValueError:
            uname = ctx.args[0].lstrip('@')
            try:
                chat_obj = await ctx.bot.get_chat(f"@{uname}")
                target_id = chat_obj.id
            except Exception:
                return await update.message.reply_text(
                    f"❌ Cannot find: `{ctx.args[0]}`", parse_mode='Markdown'
                )
    else:
        return await update.message.reply_text(
            "❌ Usage: `/unadexempt <id>`", parse_mode='Markdown'
        )

    db.remove_ad_exempt(target_id)
    await update.message.reply_text(
        f"✅ Exemption removed for `{target_id}`.\n"
        f"_Their messages will now be auto-deleted normally._",
        parse_mode='Markdown'
    )


# ─── /premium ───────────────────────────────────────────────
async def premium_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """
    Owner only — toggle Premium Protection (Edit Guard + Bio Guard) for a group.
    Use in group: /premium on | /premium off
    Use in DM:    /premium <chat_id> on | /premium <chat_id> off
    """
    if update.effective_user.id != OWNER_ID:
        return await update.message.reply_text("🔒 Owner access only.")

    ch = update.effective_chat
    args = ctx.args

    if ch.type != "private":
        if not args or args[0].lower() not in ("on", "off"):
            return await update.message.reply_text(
                "ℹ️ Usage: `/premium on` or `/premium off`", parse_mode='Markdown'
            )
        target_chat_id = ch.id
        state = args[0].lower() == "on"
    else:
        if len(args) < 2 or args[1].lower() not in ("on", "off"):
            return await update.message.reply_text(
                "ℹ️ Usage: `/premium <group_chat_id> on|off`\n\n"
                "Example:\n`/premium -1001234567890 on`",
                parse_mode='Markdown'
            )
        try:
            target_chat_id = int(args[0])
        except ValueError:
            return await update.message.reply_text("⚠️ That doesn't look like a valid chat ID.")
        state = args[1].lower() == "on"

    db.update_group(target_chat_id, {"premium": state})

    if state:
        await update.message.reply_text(
            f"💎 *𝗣𝗥𝗘𝗠𝗜𝗨𝗠 𝗔𝗖𝗧𝗜𝗩𝗔𝗧𝗘𝗗*\n"
            f"{'─'*14}\n\n"
            f"👥 Group: `{target_chat_id}`\n"
            f"  ✏️ Edit Guard — ON\n"
            f"  🕵️ Bio Guard — ON\n\n"
            f"_To disable: `/premium {target_chat_id} off`_",
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            f"🔴 *𝗣𝗥𝗘𝗠𝗜𝗨𝗠 𝗗𝗘𝗔𝗖𝗧𝗜𝗩𝗔𝗧𝗘𝗗*\n\n"
            f"👥 Group: `{target_chat_id}`\n\n"
            f"_To re-enable: `/premium {target_chat_id} on`_",
            parse_mode='Markdown'
        )


_prem_list_cache: dict[int, list] = {}   # owner_id -> resolved premium group rows (pagination cache)

async def premium_list_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """
    Owner only — sirf woh groups list karo jinme Premium Protection (Edit
    Guard + Bio Guard) ON hai.
    """
    if update.effective_user.id != OWNER_ID:
        return await update.message.reply_text("🔒 Owner access only.")

    all_ids = db.get_all_groups()
    premium_ids = [gid for gid in all_ids if db.get_group(gid).get("premium", False)]

    if not premium_ids:
        return await update.message.reply_text("💎 No groups currently have Premium active.")

    status_msg = await update.message.reply_text(
        f"⏳ Fetching details for {len(premium_ids)} premium group(s)…"
    )

    me = await ctx.bot.get_me()
    rows = []
    for gid in premium_ids:
        title, link, members, status = await _resolve_group_full(ctx, gid, me.id)
        if status == "ok":
            rows.append((title, link, members))
        elif status == "removed":
            # Bot is no longer admin in this group — clear the premium flag
            # too, so it doesn't keep showing up as "premium" for no reason.
            db.update_group(gid, {"premium": False})
        await asyncio.sleep(0.15)

    _prem_list_cache[update.effective_user.id] = rows
    await status_msg.delete()

    if not rows:
        return await update.message.reply_text(
            "💎 No groups currently have Premium active "
            "(the bot was removed from the old premium group(s), so the flag was cleared)."
        )

    text, markup = _build_premium_list_page(rows, 0)
    await update.message.reply_text(text, parse_mode='HTML', disable_web_page_preview=True, reply_markup=markup)


def _build_premium_list_page(rows: list, page: int):
    total = len(rows)
    total_pages = max(1, (total + GROUPS_PER_PAGE - 1) // GROUPS_PER_PAGE)
    page = max(0, min(page, total_pages - 1))
    start = page * GROUPS_PER_PAGE
    chunk = rows[start:start + GROUPS_PER_PAGE]

    lines = [f"💎 <b>𝗣𝗿𝗲𝗺𝗶𝘂𝗺 𝗚𝗿𝗼𝘂𝗽𝘀:</b> {total}  <i>(page {page+1}/{total_pages})</i>\n"]
    for i, (title, link, members) in enumerate(chunk, start=start + 1):
        title_safe = html.escape(title)
        mem_txt = f" — 👤 {members}" if members is not None else ""
        if link:
            lines.append(f"{i}. <a href=\"{html.escape(link)}\">{title_safe}</a>{mem_txt}")
        else:
            lines.append(f"{i}. {title_safe}{mem_txt}")

    buttons = []
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton("◀️ 𝗣𝗿𝗲𝘃", callback_data=f"premlistpg_{page-1}"))
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton("𝗡𝗲𝘅𝘁 ▶️", callback_data=f"premlistpg_{page+1}"))
    if nav_row:
        buttons.append(nav_row)

    markup = InlineKeyboardMarkup(buttons) if buttons else None
    return "\n".join(lines), markup


async def premium_list_page_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if update.effective_user.id != OWNER_ID:
        return await query.answer("🔒 Not for you.", show_alert=True)

    rows = _prem_list_cache.get(update.effective_user.id)
    if not rows:
        return await query.answer("⚠️ List expired — run /premium_list again.", show_alert=True)

    page = int(query.data.split("_", 1)[1])
    text, markup = _build_premium_list_page(rows, page)
    await query.answer()
    await query.edit_message_text(text, parse_mode='HTML', disable_web_page_preview=True, reply_markup=markup)


async def stats_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    s = db.get_stats()
    groups = db.get_all_groups()
    gmutes = db.get_all_gmutes()
    text = (
        f"📊 *𝗕𝗢𝗧 𝗦𝗧𝗔𝗧𝗜𝗦𝗧𝗜𝗖𝗦*\n"
        f"{'═'*14}\n\n"
        f"👥  Groups Active:       `{len(groups)}`\n"
        f"⚠️  Warnings Given:     `{s.get('warnings', 0)}`\n"
        f"🔇  Mutes Executed:     `{s.get('mutes', 0)}`\n"
        f"📨  Messages Scanned:   `{s.get('scanned', 0)}`\n"
        f"🗓️  Global Mutes:       `{len(gmutes)}`\n\n"
        f"{'─'*14}\n"
        f"🛡️ Status:  {ICON_ON} *Online*\n"
        f"🗄️ Database: {ICON_ON} *Connected*"
    )
    await update.message.reply_text(text, parse_mode='Markdown')



# ─── /rep ─── Guardian Points Wallet + Reputation Card ───────
async def rep_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ch = update.effective_chat
    # Works in group + private (private mein sirf own wallet)
    if update.message.reply_to_message and update.message.reply_to_message.from_user:
        tgt = update.message.reply_to_message.from_user
    else:
        tgt = update.effective_user
    if not tgt:
        return await update.message.reply_text("⚠️ Couldn't identify that user.")

    # ── Data fetch ───────────────────────────────────────────
    group_rep   = db.get_reputation(ch.id, tgt.id) if ch.type != "private" else 0
    total_rep   = db.get_total_reputation(tgt.id)

    # Group rank
    if ch.type != "private":
        top_list    = db.get_reputation_top(ch.id, limit=50)
        group_rank  = next((i + 1 for i, d in enumerate(top_list) if d.get("user_id") == tgt.id), None)
    else:
        group_rank = None

    # Global rank (all groups combined)
    global_top  = db.get_global_reputation_top(limit=50)
    global_rank = next((i + 1 for i, d in enumerate(global_top) if d.get("_id") == tgt.id), None)

    # ── Rep tier badge ────────────────────────────────────────
    def rep_tier(pts):
        if pts >= 100000: return "💎 LEGENDARY"
        if pts >= 50000:  return "🔥 ELITE"
        if pts >= 20000:  return "⭐ VETERAN"
        if pts >= 10000:  return "🌟 RISING STAR"
        if pts >= 5000:   return "✨ ACTIVE"
        if pts >= 1000:   return "🌱 NEWCOMER"
        return "🆕 STARTER"

    tier = rep_tier(total_rep)

    rank_group_txt = f"#{group_rank}" if group_rank else "Unranked"
    rank_global_txt = f"#{global_rank}" if global_rank else "Unranked"

    # ── Build reply text (Markdown v1) ─────────────────────────
    name_safe = user_name(tgt, escape=False)

    text = (
        f"⭐ *𝗣𝗥𝗢𝗙𝗜𝗟𝗘 𝗖𝗔𝗥𝗗*\n"
        f"{'─'*14}\n\n"
        f"👤 *{name_safe}*\n"
        f"🏷️ Tier: *{tier}*\n\n"
        f"{'─'*14}\n"
        f"📊 *𝗥𝗘𝗣𝗨𝗧𝗔𝗧𝗜𝗢𝗡*\n"
        f"  🏠 Group Rep:  `{group_rep}` pts  •  Rank `{rank_group_txt}`\n"
        f"  🌐 Total Rep:  `{total_rep}` pts  •  Global `{rank_global_txt}`\n\n"
        f"{'─'*14}\n"
        f"📖 *𝗛𝗢𝗪 𝗜𝗧 𝗪𝗢𝗥𝗞𝗦*\n"
        f"  • Reply “thank you” to someone → +{REP_PER_THANK} rep\n"
        f"  • Max 3 times per day (per person)\n"
        f"  • Clearing 1 warning costs {REP_PER_WARN_REMOVE} rep\n\n"
        f"_/repboard — group + global reputation ranking_"
    )

    # ── Keyboard ──────────────────────────────────────────────
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🏆 𝗥𝗲𝗽 𝗟𝗲𝗮𝗱𝗲𝗿𝗯𝗼𝗮𝗿𝗱", callback_data=f"rep:board:{ch.id}")]
    ])

    msg = await update.message.reply_text(text, parse_mode='Markdown', reply_markup=kb)
    if ch.type != "private":
        _remember_menu_owner(ch.id, msg.message_id, update.effective_user.id)
        asyncio.create_task(delete_after(ctx, ch.id, msg.message_id, 600))


# ─── /repboard ─── Reputation Leaderboard (Group + Global) ────
async def repboard_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ch = update.effective_chat
    if ch.type == "private":
        return await update.message.reply_text(
            "⚠️ This command only works in a group.",
            parse_mode='Markdown'
        )

    medals = ["🥇", "🥈", "🥉"]
    rank_emojis = ["4️⃣","5️⃣","6️⃣","7️⃣","8️⃣","9️⃣","🔟"]

    # ── Group leaderboard ──────────────────────────────────────
    group_top = db.get_reputation_top(ch.id, limit=10)
    # ── Global leaderboard ────────────────────────────────────
    global_top = db.get_global_reputation_top(limit=10)

    def build_board_lines(entries, key_pts="points", key_id="user_id"):
        if not entries:
            return ["  📉 _No data yet._"]
        lines = []
        for i, doc in enumerate(entries):
            medal = medals[i] if i < 3 else (rank_emojis[i-3] if i-3 < len(rank_emojis) else f"`{i+1}.`")
            raw_name = doc.get("name") or str(doc.get(key_id, "?"))
            name = md_esc(str(raw_name))
            pts  = doc.get(key_pts, 0)
            lines.append(f"{medal} {name}  —  `{pts}` rep")
        return lines

    group_lines  = build_board_lines(group_top,  key_pts="points",  key_id="user_id")
    global_lines = build_board_lines(global_top, key_pts="total",   key_id="_id")

    text = (
        f"🏆 *𝗥𝗘𝗣𝗨𝗧𝗔𝗧𝗜𝗢𝗡 𝗕𝗢𝗔𝗥𝗗*\n"

        f"{'─'*14}\n\n"
        f"🏠 *𝗚𝗥𝗢𝗨𝗣 𝗧𝗢𝗣* — {md_esc(getattr(ch, 'title', 'This Group')[:22])}\n"
        f"{'┄'*14}\n"
        + "\n".join(group_lines) +
        f"\n\n"
        f"🌐 *𝗚𝗟𝗢𝗕𝗔𝗟 𝗧𝗢𝗣* — All Groups Combined\n"
        f"{'┄'*14}\n"
        + "\n".join(global_lines) +
        f"\n\n{'─'*14}\n"
        f"💡 _Saying thanks = +{REP_PER_THANK} rep · clearing 1 warning = {REP_PER_WARN_REMOVE} rep_\n"
        f"_Reply “thank you” to give rep — max 3/day per person_"
    )

    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔄 𝗥𝗲𝗳𝗿𝗲𝘀𝗵", callback_data=f"rep:board:{ch.id}"),
            InlineKeyboardButton("⭐ 𝗠𝘆 𝗣𝗿𝗼𝗳𝗶𝗹𝗲", callback_data="rep:myprofile"),
        ],
        [
            InlineKeyboardButton("🌐 𝗚𝗹𝗼𝗯𝗮𝗹 𝗥𝗲𝗳𝗿𝗲𝘀𝗵", callback_data="rep:global:0"),
        ]
    ])

    msg = await update.message.reply_text(text, parse_mode='Markdown', reply_markup=kb)
    asyncio.create_task(delete_after(ctx, ch.id, msg.message_id, 600))


# ─── Reputation callbacks (repboard refresh + wallet + myprofile) ──
async def rep_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat  = update.effective_chat
    if chat and chat.type != "private":
        if not _is_menu_owner(chat.id, query.message.message_id, query.from_user.id):
            await query.answer(
                "🔒 This menu can only be used by whoever opened it!\n"
                "Open your own menu with /start.",
                show_alert=True
            )
            return
    await query.answer()
    medals    = ["🥇", "🥈", "🥉"]
    rank_emojis = ["4️⃣","5️⃣","6️⃣","7️⃣","8️⃣","9️⃣","🔟"]

    def _rep_lines(entries, key_pts, key_id, limit=7):
        if not entries:
            return ["  📉 _No data yet!_"]
        out = []
        for i, doc in enumerate(entries[:limit]):
            medal = medals[i] if i < 3 else (rank_emojis[i-3] if i-3 < len(rank_emojis) else f"`{i+1}.`")
            name  = md_esc(str(doc.get("name") or doc.get(key_id, "?")))
            pts   = doc.get(key_pts, 0)
            out.append(f"{medal} {name}  —  `{pts}` rep")
        return out

    try:
        parts  = query.data.split(":")
        action = parts[1]
        ch_id  = update.effective_chat.id if update.effective_chat else 0

        if action == "myprofile":
            # Caller ka profile — same as /rep command
            usr = query.from_user
            if not usr:
                return
            group_rep   = db.get_reputation(ch_id, usr.id) if ch_id else 0
            total_rep   = db.get_total_reputation(usr.id)

            def rep_tier(p):
                if p >= 100000: return "💎 LEGENDARY"
                if p >= 50000:  return "🔥 ELITE"
                if p >= 20000:  return "⭐ VETERAN"
                if p >= 10000:  return "🌟 RISING STAR"
                if p >= 5000:   return "✨ ACTIVE"
                if p >= 1000:   return "🌱 NEWCOMER"
                return "🆕 STARTER"

            tier = rep_tier(total_rep)
            name_safe = user_name(usr)
            text = (
                f"⭐ *𝗣𝗥𝗢𝗙𝗜𝗟𝗘 𝗖𝗔𝗥𝗗*\n"
                f"{'─'*14}\n\n"
                f"👤 *{name_safe}*\n"
                f"🏷️ Tier: *{tier}*\n\n"
                f"{'─'*14}\n"
                f"📊 *𝗥𝗘𝗣𝗨𝗧𝗔𝗧𝗜𝗢𝗡*\n"
                f"  🏠 Group Rep:  `{group_rep}` pts\n"
                f"  🌐 Total Rep:  `{total_rep}` pts\n\n"
                f"_Reply “thank you” to earn rep · clearing a warning costs {REP_PER_WARN_REMOVE} rep_"
            )
            kb_rows = [
                [
                    InlineKeyboardButton("🏆 𝗥𝗲𝗽 𝗕𝗼𝗮𝗿𝗱",   callback_data="menu_repboard"),
                    InlineKeyboardButton("🌐 𝗚𝗹𝗼𝗯𝗮𝗹 𝗥𝗮𝗻𝗸", callback_data="rep:global:0"),
                ],
                [InlineKeyboardButton("◀️ 𝗕𝗮𝗰𝗸", callback_data="menu_main")],
            ]
            await query.edit_message_text(text, parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(kb_rows))

        elif action == "board":
            chat_id = int(parts[2]) if len(parts) > 2 else ch_id
            group_top  = db.get_reputation_top(chat_id, limit=7)
            global_top = db.get_global_reputation_top(limit=7)
            group_lines  = _rep_lines(group_top,  "points", "user_id")
            global_lines = _rep_lines(global_top, "total",  "_id")
            text = (
                f"*🏆 REPUTATION BOARD*\n"

                f"{'─'*14}\n\n"
                f"🏠 *𝗚𝗥𝗢𝗨𝗣 𝗧𝗢𝗣*\n{'┄'*14}\n"
                + "\n".join(group_lines) +
                f"\n\n🌐 *𝗚𝗟𝗢𝗕𝗔𝗟 𝗧𝗢𝗣*\n{'┄'*14}\n"
                + "\n".join(global_lines)
            )
            await query.edit_message_text(
                text, parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton("🔄 𝗥𝗲𝗳𝗿𝗲𝘀𝗵",       callback_data=f"rep:board:{chat_id}"),
                        InlineKeyboardButton("⭐ 𝗠𝘆 𝗣𝗿𝗼𝗳𝗶𝗹𝗲",    callback_data="rep:myprofile"),
                    ],
                    [
                        InlineKeyboardButton("📊 𝗚𝗿𝗼𝘂𝗽 𝗥𝗮𝗻𝗸",   callback_data=f"rep:board:{chat_id}"),
                        InlineKeyboardButton("🌐 𝗚𝗹𝗼𝗯𝗮𝗹 𝗥𝗮𝗻𝗸",  callback_data="rep:global:0"),
                    ],
                    [InlineKeyboardButton("◀️ 𝗕𝗮𝗰𝗸", callback_data="menu_main")],
                ])
            )

        elif action == "global":
            top = db.get_global_reputation_top(limit=10)
            lines = _rep_lines(top, "total", "_id", limit=10)
            text = (
                f"*🌐 𝗚𝗟𝗢𝗕𝗔𝗟 𝗥𝗘𝗣 𝗕𝗢𝗔𝗥𝗗*\n"

                f"{'─'*14}\n\n"
                f"{'┄'*14}\n"
                + "\n".join(lines) +
                f"\n\n{'─'*14}\n"
                f"_Combined data from all groups_"
            )
            await query.edit_message_text(
                text, parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton("🔄 𝗥𝗲𝗳𝗿𝗲𝘀𝗵",     callback_data="rep:global:0"),
                        InlineKeyboardButton("⭐ 𝗠𝘆 𝗣𝗿𝗼𝗳𝗶𝗹𝗲",  callback_data="rep:myprofile"),
                    ],
                    [
                        InlineKeyboardButton("🏠 𝗚𝗿𝗼𝘂𝗽 𝗥𝗮𝗻𝗸",  callback_data=f"rep:board:{ch_id}"),
                        InlineKeyboardButton("◀️ 𝗕𝗮𝗰𝗸",        callback_data="menu_main"),
                    ],
                ])
            )

    except Exception:
        pass




# ═══════════════════════════════════════════════════════════
#  BOT REPLY TRACKER — Provider bot ne reply kiya? Track karo
# ═══════════════════════════════════════════════════════════
# Structure: {chat_id: {"last_bot_reply_time": float, "replied_to_ids": {msg_id: time}}}
PROVIDER_BOT_REPLIES: dict = {}

async def track_bot_reply(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """
    Jab bhi koi bot (provider) group mein kuch bheje → timestamp note karo.
    """
    msg = update.message
    if not msg or not msg.from_user:
        return

    # ── Seen-users index — HAR group message se sender ko yaad rakho.
    # Yeh alag hai upar wale is_bot check se: humein human users bhi
    # chahiye taaki /ban, /mute, /warn waghera baad mein @username ya
    # userid se bhi resolve ho sakein (sirf reply pe depend na rahe). ──
    db.remember_user(msg.from_user)
    if msg.reply_to_message and msg.reply_to_message.from_user:
        db.remember_user(msg.reply_to_message.from_user)

    # Sirf dusre bots track karo (hamara bot nahi)
    if not msg.from_user.is_bot or msg.from_user.id == ctx.bot.id:
        return

    ch_id = update.effective_chat.id
    now = time.time()

    if ch_id not in PROVIDER_BOT_REPLIES:
        PROVIDER_BOT_REPLIES[ch_id] = {"last_bot_time": 0, "replied_ids": {}}

    # Timestamp update karo — koi bhi bot active tha
    PROVIDER_BOT_REPLIES[ch_id]["last_bot_time"] = now

    # Agar direct reply hai → exact message_id bhi track karo
    if msg.reply_to_message:
        rid = msg.reply_to_message.message_id
        PROVIDER_BOT_REPLIES[ch_id]["replied_ids"][rid] = now

    # Cleanup old replied_ids (2 min se purane)
    PROVIDER_BOT_REPLIES[ch_id]["replied_ids"] = {
        mid: t for mid, t in PROVIDER_BOT_REPLIES[ch_id]["replied_ids"].items()
        if now - t < 120
    }


# ═══════════════════════════════════════════════════════════
#  ACTIVITY TRACKER — Har group message ko count karo
#  (Leaderboard isi data se banta hai — reputation se NAHI)
# ═══════════════════════════════════════════════════════════
async def track_activity_msg(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """
    Har message (text/media/sticker/command — sab) ko count karo, taaki
    /rankings sahi "kitne message bheje" dikha sake.
    Apne alag handler-group mein chalta hai, isliye kisi aur logic
    (warnings/violations/etc.) se conflict nahi karta.
    """
    msg = update.message
    ch  = update.effective_chat
    usr = update.effective_user
    if not msg or not ch or not usr:
        return
    if ch.type == "private":
        return
    if usr.is_bot:
        return
    ANON_BOT_ID = 1087968824
    if usr.id == ANON_BOT_ID:
        return
    db.track_activity(ch.id, usr.id, user_name(usr, escape=False))

    # ── Auto-Reputation: har 100 messages pe 100 rep points ──────
    total_msgs = db.get_total_msg_count(ch.id, usr.id)
    if total_msgs > 0 and total_msgs % 100 == 0:
        db.add_reputation(ch.id, usr.id, REP_PER_THANK, user_name(usr, escape=False))
        new_rep = db.get_reputation(ch.id, usr.id)
        try:
            notice = await ctx.bot.send_message(
                ch.id,
                f"🎉 *{mv2_esc(user_name(usr, escape=False))}* has sent `{total_msgs}` messages in the group\\!\n"
                f"⭐ *\\+{REP_PER_THANK} Reputation Points* auto\\-earn hue\\! Total: `{new_rep}` rep",
                parse_mode='MarkdownV2'
            )
            asyncio.create_task(delete_after(ctx, ch.id, notice.message_id, 30))
        except Exception:
            pass




# ═══════════════════════════════════════════════════════════
#  PREMIUM: Edit Guard — re-check edited messages
# ═══════════════════════════════════════════════════════════
async def on_edited_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """
    Catches messages edited AFTER sending. Some users send a clean message
    first (to slip past normal checks) then edit it into a link, blacklisted
    word, etc. Premium groups get this content re-checked on every edit.
    """
    msg = update.edited_message
    if not msg:
        return

    ch  = update.effective_chat
    usr = update.effective_user
    if not ch or ch.type == "private" or not usr:
        return

    g_settings = db.get_group(ch.id)
    if not g_settings.get("premium", False):
        return

    if await is_adm(ctx, ch.id, usr.id):
        return
    if db.is_immortal(ch.id, usr.id):
        return

    group_bots = await get_group_bots(ctx, ch.id)
    violation, matched_word = await check_violations(msg, group_bots, ctx, ch.id)
    if not violation:
        return

    asyncio.create_task(msg.delete())

    viol_txt = VIOLATION_MSG.get(violation, "Rule violation.")
    if violation == "blacklist" and matched_word:
        viol_txt = f"⛔ Blacklisted word used: `{matched_word}` — please don't repeat this."
    viol_txt = f"✏️ Edited into a violation: {viol_txt}"

    await apply_warn_punishment(ctx, ch.id, usr, viol_txt)


# ═══════════════════════════════════════════════════════════
#  MAIN MESSAGE HANDLER
# ═══════════════════════════════════════════════════════════
async def check_msg(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg: return

    ch  = update.effective_chat
    usr = update.effective_user

    if ch.type == "private": return

    # GroupAnonymousBot — NEVER restrict, it handles linked channel posts
    ANON_BOT_ID = 1087968824
    if usr and usr.id == ANON_BOT_ID:
        return

    db.add_group(ch.id)

    # ── /settings panel: pending text input capture (rules, word add, etc.) ──
    pend_key = (ch.id, usr.id) if usr else None
    if pend_key and pend_key in SETTINGS_PENDING:
        handled = await handle_settings_input(update, ctx, pend_key)
        if handled:
            return

    txt = msg.text or msg.caption or ""
    if txt.startswith('/'): return

    txt_lower = txt.lower().strip()

    # ── Reply karke "thank you/shukriya" type bole to: ──────────
    #    - target ko HAMESHA +100 Reputation Points milte hain (is group mein)
    #    - agar target ke paas active warning hai aur balance ≥100 hai,
    #      to 100 rep apne aap kat ke 1 warning maaf ho jaati hai
    #    - reputation sirf "accepted" group mein Guardian Coin banta hai —
    #      baaki sab groups mein sirf warn-se-bachne ke kaam aata hai
    if (
        msg.reply_to_message
        and msg.reply_to_message.from_user
        and not msg.reply_to_message.from_user.is_bot
        and msg.reply_to_message.from_user.id != usr.id
        and is_thank_you_text(txt_lower)
    ):
        target = msg.reply_to_message.from_user

        # ── Daily 3-rep-give limit PER TARGET (spam-rokne ke liye) ──
        # Ek hi bande ko din mein max 3 baar thanks ka fayda milega, uske baad
        # usi bande ko thanks bolne se kuch nahi hoga — lekin KISI DUSRE bande ko
        # thanks bolna bilkul unlimited hai.
        given_today = db.get_rep_given_today_to(usr.id, target.id)
        if given_today >= 3:
            notice = await msg.reply_text(
                f"💖 {user_name(usr)} ne thank you bola — but\n\n"
                f"⚠️ *You've already thanked this person 3/3 times today!*\n"
                f"Come back tomorrow 😊 — _thanking other members is still unlimited_.",
                parse_mode='Markdown'
            )
            asyncio.create_task(delete_after(ctx, ch.id, notice.message_id, 60))
            return

        current_warns = db.get_warnings(ch.id, target.id)
        new_count = db.increment_rep_given_to(usr.id, target.id)
        db.add_reputation(ch.id, target.id, REP_PER_THANK, user_name(target, escape=False))
        new_rep = db.get_reputation(ch.id, target.id)
        remaining = 3 - new_count

        # ── Agar target ke paas warning hai aur balance sufficient hai → auto-redeem ──
        warn_removed = False
        if current_warns > 0 and new_rep >= REP_PER_WARN_REMOVE:
            if db.spend_reputation(ch.id, target.id, REP_PER_WARN_REMOVE):
                db.remove_one_warning(ch.id, target.id)
                warn_removed = True
                new_rep = db.get_reputation(ch.id, target.id)

        base_msg = (
            f"💖 {mv2_esc(user_name(usr, escape=False))} said thank you to {mv2_esc(user_name(target, escape=False))}\\!\n\n"
            f"⭐ *\\+{REP_PER_THANK} Reputation Points* earned\\!\n"
            f"📊 This group's Rep: `{new_rep}` pts\n"
        )
        if warn_removed:
            base_msg += f"✅ Bonus: a warning was also cleared \\(100 rep deducted\\)\\!\n"
        base_msg += f"🎯 You can still give this person: `{remaining}/3` today\n"
        base_msg += f"\n_Check your rep with \\/rep\\!_"

        notice = await msg.reply_text(base_msg, parse_mode='MarkdownV2')
        asyncio.create_task(delete_after(ctx, ch.id, notice.message_id, 60))
        return

    # ── "Guardian ban" natural language command ──────────────
    # Admin group mein "guardian ban @user" ya "guardian ban userid" likh sakta hai
    if txt_lower.startswith("guardian ban"):
        caller_is_admin = await is_adm(ctx, ch.id, usr.id) or usr.id == OWNER_ID
        if caller_is_admin:
            target_id = None
            target_name = None
            # Reply se target lo
            if msg.reply_to_message and msg.reply_to_message.from_user:
                target_id = msg.reply_to_message.from_user.id
                target_name = user_name(msg.reply_to_message.from_user)
            else:
                # "guardian ban @username" ya "guardian ban 123456"
                parts = txt.split()
                if len(parts) >= 3:
                    raw = parts[2]
                    try:
                        target_id = int(raw)
                    except ValueError:
                        uname = raw.lstrip('@')
                        try:
                            chat_obj = await ctx.bot.get_chat(f"@{uname}")
                            target_id = chat_obj.id
                            target_name = md_esc(uname)
                        except Exception:
                            pass
            if target_id and target_id != ctx.bot.id and target_id != OWNER_ID:
                if not await is_adm(ctx, ch.id, target_id):
                    await do_ban(ctx, ch.id, target_id)
                    try:
                        await msg.delete()
                    except Exception:
                        pass
                    notice = await ctx.bot.send_message(
                        ch.id,
                        f"🔨 *Banned!*\n👤 {target_name or target_id} has been removed.",
                        parse_mode='Markdown'
                    )
                    asyncio.create_task(delete_after(ctx, ch.id, notice.message_id, 15))
            return

    g_settings = db.get_group(ch.id)
    sticker_del_min = g_settings.get("sticker_delete_min")
    autodel_min     = db.get_effective_autodelete(ch.id)

    # ── Admin/Owner check SABSE PEHLE ───────────────────────
    is_admin = await is_adm(ctx, ch.id, usr.id)

    # Admin aur Owner ko koi bhi check nahi lagega
    if is_admin:
        return

    # ── Gmute / Fban check (sirf non-admins ke liye) ────────
    if db.is_gmuted(usr.id):
        asyncio.create_task(msg.delete())
        remaining = db.get_gmute_remaining(usr.id)
        asyncio.create_task(do_mute(ctx, ch.id, usr.id, remaining or GMUTE_DURATION))
        return

    if db.is_fbanned(usr.id):
        asyncio.create_task(msg.delete())
        asyncio.create_task(do_ban(ctx, ch.id, usr.id))
        return

    # ── Autodelete logic ─────────────────────────────────────
    sender_id = usr.id if usr else None
    sender_chat = getattr(msg, 'sender_chat', None)
    if sender_chat:
        sender_id = sender_chat.id

    ad_exempted = sender_id and db.is_ad_exempt(sender_id)

    # Sticker detection — sirf actual sticker/animation, stylish text nahi
    is_sticker_media = bool(msg.sticker or msg.animation)

    if sticker_del_min and is_sticker_media and not ad_exempted:
        asyncio.create_task(delete_after(ctx, ch.id, msg.message_id, sticker_del_min * 60))

    if autodel_min and not ad_exempted:
        asyncio.create_task(delete_after(ctx, ch.id, msg.message_id, autodel_min * 60))

    if db.is_immortal(ch.id, usr.id):
        return

    # ── PREMIUM: Bio Guard ──────────────────────────────────
    if g_settings.get("premium", False):
        shadow_key = (ch.id, usr.id)
        shadow = db.shadow_blacklist_get(ch.id, usr.id)

        if shadow:
            # Already flagged — recheck almost instantly on their next
            # message (not the slow scan), since the bot's own notice
            # promises "send any message to be rechecked".
            last_checked = FLAGGED_CHECK_CACHE.get(shadow_key, 0)
            if time.time() - last_checked >= SHADOW_RECHECK_SEC:
                FLAGGED_CHECK_CACHE[shadow_key] = time.time()
                bio_fetch_ok = True
                try:
                    full = await ctx.bot.get_chat(usr.id)
                    bio = getattr(full, "bio", None) or ""
                except Exception:
                    bio_fetch_ok = False
                    bio = ""
                if bio_fetch_ok:
                    kind, matched = await bio_violation(bio, ch.id, g_settings, ctx)
                    if not kind:
                        # Bio is clean now — clear shadow status and let this message through
                        db.shadow_blacklist_remove(ch.id, usr.id)
                        SHADOW_MSG_COUNT.pop(shadow_key, None)
                        SHADOW_FLOOD.pop(shadow_key, None)
                        FLAGGED_CHECK_CACHE.pop(shadow_key, None)
                        notice = await ctx.bot.send_message(
                            ch.id,
                            f"✅ {user_name(usr)}, your bio is clean now — you're all set. 🎉",
                            parse_mode='Markdown'
                        )
                        asyncio.create_task(delete_after(ctx, ch.id, notice.message_id, 20))
                        shadow = None  # fall through to normal pipeline below
                    else:
                        # Still violating, but WHAT they're violating on may
                        # have changed (e.g. swapped one @username for another,
                        # or fixed the link but the bio still has a blacklisted
                        # word) — refresh the stored record so every notice
                        # after this always reflects the CURRENT bio, never a
                        # stale one from the original hit.
                        db.shadow_blacklist_add(ch.id, usr.id, kind, matched)
                        shadow = db.shadow_blacklist_get(ch.id, usr.id)

        if shadow:
            # Still shadow-blacklisted — let it post, then vanish it
            asyncio.create_task(msg.delete())

            SHADOW_MSG_COUNT[shadow_key] = SHADOW_MSG_COUNT.get(shadow_key, 0) + 1
            hit_count = SHADOW_MSG_COUNT[shadow_key]

            if hit_count >= SHADOW_PUNISH_THRESHOLD:
                # 5th (and every) time they message with a bad bio — switch
                # to the exact same escalating warn/mute punishment a normal
                # link/blacklist violation gets, instead of just deleting
                # the message forever with no real consequence.
                kind = shadow.get("reason")
                matched = shadow.get("matched")
                what = _bio_violation_what(kind, matched, in_bio=True)
                viol_txt = f"⛔ Repeated bio violation — {what}. Remove it to stop getting muted."
                await apply_warn_punishment(ctx, ch.id, usr, viol_txt, delete_delay=90)
                return

            if SHADOW_MSG_COUNT[shadow_key] % 3 == 1:
                kind = shadow.get("reason")
                matched = shadow.get("matched")
                what = _bio_violation_what(kind, matched)
                left = SHADOW_PUNISH_THRESHOLD - hit_count
                notice = await ctx.bot.send_message(
                    ch.id,
                    f"🕵️ *𝗕𝗜𝗢 𝗚𝗨𝗔𝗥𝗗*\n\n"
                    f"👤 {user_mention(usr)}, your profile bio contains {what}.\n"
                    f"Your messages won't be visible until it's removed.\n\n"
                    f"_Remove it, then tap the button below (or send any message) to be rechecked._\n\n"
                    f"⚠️ _{left} more message(s) like this and you'll be muted._",
                    parse_mode='Markdown',
                    reply_markup=_biorecheck_markup(ch.id, usr.id)
                )
                asyncio.create_task(delete_after(ctx, ch.id, notice.message_id, 90))

            # Flood check for shadow-blacklisted user (10 msgs / 60s) — extra
            # safety net in case they spam-flood fast before hitting the
            # SHADOW_PUNISH_THRESHOLD count above
            now = time.time()
            times = [t for t in SHADOW_FLOOD.get(shadow_key, []) if now - t < SHADOW_FLOOD_WINDOW]
            times.append(now)
            SHADOW_FLOOD[shadow_key] = times
            if len(times) > SHADOW_FLOOD_LIMIT:
                cnt = db.add_warning(ch.id, usr.id)
                _wd = db.get_warn_durations(ch.id)
                await do_mute(ctx, ch.id, usr.id, _wd.get(min(cnt, 4), 120))
                SHADOW_FLOOD[shadow_key] = []
            return

        # Not yet shadow-blacklisted — due for a bio check?
        last_checked = CLEAN_CHECK_CACHE.get(shadow_key, 0)
        if time.time() - last_checked >= BIO_RECHECK_SEC:
            CLEAN_CHECK_CACHE[shadow_key] = time.time()
            try:
                full = await ctx.bot.get_chat(usr.id)
                bio = getattr(full, "bio", None) or ""
            except Exception:
                bio = ""

            kind, matched = await bio_violation(bio, ch.id, g_settings, ctx)
            if kind:
                db.shadow_blacklist_add(ch.id, usr.id, kind, matched)
                asyncio.create_task(msg.delete())
                SHADOW_MSG_COUNT[shadow_key] = 1
                what = _bio_violation_what(kind, matched)
                notice = await ctx.bot.send_message(
                    ch.id,
                    f"🕵️ *𝗕𝗜𝗢 𝗚𝗨𝗔𝗥𝗗 𝗧𝗥𝗜𝗚𝗚𝗘𝗥𝗘𝗗*\n\n"
                    f"👤 {user_mention(usr)}, your profile bio contains {what}.\n"
                    f"Your messages won't be visible until it's removed.\n\n"
                    f"_Remove it, then tap the button below (or send any message) to be rechecked._",
                    parse_mode='Markdown',
                    reply_markup=_biorecheck_markup(ch.id, usr.id)
                )
                asyncio.create_task(delete_after(ctx, ch.id, notice.message_id, 90))
                return

    db.inc_stat("scanned")

    group_bots = await get_group_bots(ctx, ch.id)
    violation, matched_word = await check_violations(msg, group_bots, ctx, ch.id)

    if violation:
        asyncio.create_task(msg.delete())

        # ── Admin hai? Sirf message delete karo, koi action nahi ──
        if is_admin:
            return

        # ── Teacher special handling — courtesy notice + escalating mute ──
        if db.is_teacher(ch.id, usr.id):
            promo_count = db.inc_teacher_promo_count(ch.id, usr.id)
            # 1st offense → sirf warning, no mute
            if promo_count == 1:
                notice = await ctx.bot.send_message(
                    ch.id,
                    f"📚 Hi {user_name(usr)},\n\n"
                    f"As a teacher here, you get a courtesy notice instead of a mute 🙏\n"
                    f"But that message still broke a group rule.\n\n"
                    f"⚠️ Please don't repeat this — next time you'll be muted.",
                    parse_mode='Markdown'
                )
                asyncio.create_task(delete_after(ctx, ch.id, notice.message_id, 90))
                return
            else:
                # 2nd offense → 10min, 3rd → 40min, 4th → 70min … +30 min har baar
                base_min = 10
                extra_min = 30 * (promo_count - 2)   # 2nd=0 extra, 3rd=30 extra, 4th=60 extra…
                mute_min = base_min + extra_min
                mute_sec = mute_min * 60
                await do_mute(ctx, ch.id, usr.id, mute_sec)
                notice = await ctx.bot.send_message(
                    ch.id,
                    f"📚 {user_mention(usr)},\n\n"
                    f"A group rule was broken again.\n"
                    f"🔇 Muted for *{mute_min} minutes*.\n\n"
                    f"_(Repeat offense #{promo_count - 1} — mute duration increases each time.)_",
                    parse_mode='Markdown'
                )
                asyncio.create_task(delete_after(ctx, ch.id, notice.message_id, 90))
                return

        viol_txt = VIOLATION_MSG.get(violation, "Rule violation!")
        if violation == "blacklist" and matched_word:
            viol_txt = f"⛔ Blacklisted word used: `{matched_word}` — please don't repeat this."
        # Blacklist-word notices should clear out fast (within 1 min) so the
        # group doesn't stay cluttered with "which word" call-outs.
        warn_delete_delay = 60 if violation == "blacklist" else 90
        await apply_warn_punishment(ctx, ch.id, usr, viol_txt, delete_delay=warn_delete_delay)
        return

    # ── AI REPLY — question/help/confusion ──
    if ai_result["action"] == "REPLY" and ai_result.get("reply"):
        try:
            reply_msg = await msg.reply_text(
                ai_result["reply"],
                parse_mode='Markdown'
            )
            # Auto delete reply after 2 min to keep chat clean
            asyncio.create_task(delete_after(ctx, ch.id, reply_msg.message_id, 120))
        except Exception:
            pass


# ═══════════════════════════════════════════════════════════
#  NEW MEMBER / JOIN / LEAVE EVENTS
# ═══════════════════════════════════════════════════════════
async def on_join(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        if db.get_filters(update.effective_chat.id).get("noevents", False):
            any_real_member = any(m.id != ctx.bot.id for m in update.message.new_chat_members)
            if any_real_member:
                asyncio.create_task(delete_after(ctx, update.effective_chat.id, update.message.message_id, 0))
    except Exception:
        pass
    for member in update.message.new_chat_members:
        db.remember_user(member)  # seen-users index — resolve @username/userid later
        if member.id == ctx.bot.id:
            db.add_group(update.effective_chat.id)
            try:
                chat = await ctx.bot.get_chat(update.effective_chat.id)
                if hasattr(chat, 'linked_chat_id') and chat.linked_chat_id:
                    db.set_linked_channel(update.effective_chat.id, chat.linked_chat_id)
            except:
                pass
            bot_added_text = (
                                f"🛡️ *𝗚𝗨𝗔𝗥𝗗𝗜𝗔𝗡 𝗜𝗦 𝗡𝗢𝗪 𝗔𝗖𝗧𝗜𝗩𝗘*\n"
                f"_v10.0 · AI-Powered Protection_\n"
                f"{'─'*14}\n\n"
                f"⚡ *This group is now protected.*\n\n"
                f"{'─'*14}\n"
                f"📋 *𝙋𝙡𝙚𝙖𝙨𝙚 𝙜𝙧𝙖𝙣𝙩 𝙩𝙝𝙚𝙨𝙚 𝙖𝙙𝙢𝙞𝙣 𝙧𝙞𝙜𝙝𝙩𝙨:*\n"
                f"  ✅ Delete Messages\n"
                f"  ✅ Restrict Members\n"
                f"  ✅ Ban Members\n\n"
                f"{'─'*14}\n"
                f"🛡️ *𝘼𝙘𝙩𝙞𝙫𝙚 𝙗𝙮 𝙙𝙚𝙛𝙖𝙪𝙡𝙩:*\n"
                f"  🤖 External bots & @mentions\n"
                f"  🔗 Links & URLs\n"
                f"  ↩️ Forwarded messages\n"
                f"  🔞 Adult content\n"
                f"  ⛔ Blacklisted words\n"
                f"  🌊 Anti-flood\n"
                f"  🎭 Captcha _(optional)_\n"
                f"  ⏱️ Auto-delete _(optional)_\n\n"
                f"_Type /help to see every command._"
            )
            added_msg_id = await send_colored_message(
                update.effective_chat.id, bot_added_text, ckb_bot_added()
            )
            adder_id = update.effective_user.id if update.effective_user else None
            if not added_msg_id:
                sent = await update.message.reply_text(
                    bot_added_text, parse_mode='Markdown', reply_markup=kb_bot_added()
                )
                _remember_menu_owner(update.effective_chat.id, sent.message_id, adder_id)
            else:
                _remember_menu_owner(update.effective_chat.id, added_msg_id, adder_id)
        elif member.is_bot:
            # ── nobots filter: added by a non-admin → auto-kick spambot ──
            filt = db.get_filters(update.effective_chat.id)
            if filt.get("nobots", True):
                adder = update.effective_user
                adder_is_admin = adder and await is_adm(ctx, update.effective_chat.id, adder.id)
                if not adder_is_admin:
                    try:
                        await do_ban(ctx, update.effective_chat.id, member.id)
                        await ctx.bot.unban_chat_member(update.effective_chat.id, member.id)  # ban→unban = clean kick
                        notice = await update.message.reply_text(
                            f"🛑 *𝗦𝗽𝗮𝗺 𝗯𝗼𝘁 𝗿𝗲𝗺𝗼𝘃𝗲𝗱*\n👤 {user_name(member)} was kicked _(bot filter)_.",
                            parse_mode='Markdown'
                        )
                        asyncio.create_task(delete_after(ctx, update.effective_chat.id, notice.message_id, 20))
                    except Exception:
                        pass
        else:
            g = db.get_group(update.effective_chat.id)
            filt = db.get_filters(update.effective_chat.id)
            if not filt.get("welcome", True):
                pass
            elif g.get("captcha"):
                asyncio.create_task(
                    send_captcha(ctx, update.effective_chat.id, member.id, user_name(member))
                )
            else:
                custom_welcome = g.get("welcome_text")
                welcome_text = custom_welcome.replace("{name}", user_name(member, escape=False)) if custom_welcome else (
                    f"*👋 WELCOME*\n"

                    f"{'─'*14}\n\n"
                    f"Hi {user_name(member)}, glad to have you here! 🎉\n\n"
                    f"{'─'*14}\n"
                    f"📜 Please read the group rules\n"
                    f"⚠️ Violations are detected automatically\n"
                    f"⭐ Earn reputation by being helpful\n\n"
                    f"_Enjoy your stay!_"
                )
                welcome_msg_id = await send_colored_message(
                    update.effective_chat.id, welcome_text, ckb_join_welcome()
                )
                if welcome_msg_id:
                    _remember_menu_owner(update.effective_chat.id, welcome_msg_id, member.id)
                    asyncio.create_task(delete_after(ctx, update.effective_chat.id, welcome_msg_id, 60))
                else:
                    msg = await update.message.reply_text(
                        welcome_text, parse_mode='Markdown', reply_markup=kb_join_welcome()
                    )
                    _remember_menu_owner(update.effective_chat.id, msg.message_id, member.id)
                    asyncio.create_task(delete_after(ctx, update.effective_chat.id, msg.message_id, 60))


async def on_leave(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.message.left_chat_member.id == ctx.bot.id:
        pass
    try:
        if db.get_filters(update.effective_chat.id).get("noevents", False):
            asyncio.create_task(delete_after(ctx, update.effective_chat.id, update.message.message_id, 0))
    except Exception:
        pass


# ═══════════════════════════════════════════════════════════
#  ⚙️  /settings PANEL — Admin/Owner button-based control panel
#  Colored buttons (🟢 success / 🔵 primary / 🔴 danger) — same
#  Bot API "style" trick jo main menu (ckb_main_menu) use karta hai.
#  Agar colored-button API call fail ho jaaye (rare), fallback
#  turant plain grey InlineKeyboardMarkup pe ho jaata hai (_rows_to_markup).
# ═══════════════════════════════════════════════════════════
# (chat_id, user_id) -> {"action": str, "extra": any, "panel_msg_id": int}
SETTINGS_PENDING = {}

def _sec_human(sec):
    sec = int(sec)
    if sec >= 604800:
        return f"{sec // 604800}w"
    if sec >= 86400:
        return f"{sec // 86400}d"
    if sec >= 3600:
        return f"{sec // 3600}h"
    if sec >= 60:
        return f"{sec // 60}m"
    return f"{sec}s"

async def _cfg_is_authorized(ctx, chat_id, user_id) -> bool:
    if user_id == OWNER_ID:
        return True
    return await is_adm(ctx, chat_id, user_id)

async def _cfg_edit(query, chat_id, text, rows, parse_mode='Markdown'):
    """Colored-button edit — Bot API 'style' trick fail ho to turant plain
    grey buttons pe fallback (user ko kabhi error/blank screen nahi dikhta)."""
    ok = await edit_colored_message(chat_id, query.message.message_id, text, rows, parse_mode=parse_mode)
    if not ok:
        await query.edit_message_text(text, parse_mode=parse_mode, reply_markup=_rows_to_markup(rows))

def kb_settings_main(chat_id):
    g = db.get_group(chat_id)
    stk = g.get("sticker_delete_min")
    ad = g.get("autodelete_min")
    captcha_on = bool(g.get("captcha"))
    bl_count = len(db.get_blacklist(chat_id) or [])
    wl_count = len(db.get_whitelist(chat_id) or [])
    prem_on = bool(g.get("premium", False))
    # Order = the flow an admin actually thinks in when setting up a group:
    #  1) What gets enforced (Filters drive /rules automatically, then word lists)
    #  2) What happens on a violation (Warn Durations, Captcha)
    #  3) Cleanup / housekeeping (Sticker & Auto-delete)
    #  4) Extras (Reputation, Premium, Community)
    return [
        [
            {"text": f"🛡️ 𝗙𝗶𝗹𝘁𝗲𝗿𝘀 ({_filters_status_line(chat_id)})", "callback_data": "cfg_filters", "style": "primary"},
            {"text": "📜 𝗥𝘂𝗹𝗲𝘀", "callback_data": "cfg_rules", "style": "primary"},
        ],
        [
            {"text": f"⛔ 𝗕𝗹𝗮𝗰𝗸𝗹𝗶𝘀𝘁 {ICON_ON if bl_count else ICON_OFF}", "callback_data": "cfg_bl",
             "style": "success" if bl_count else "danger"},
            {"text": f"✅ 𝗪𝗵𝗶𝘁𝗲𝗹𝗶𝘀𝘁 {ICON_ON if wl_count else ICON_OFF}", "callback_data": "cfg_wl",
             "style": "success" if wl_count else "danger"},
        ],
        [
            {"text": "⚠️ 𝗪𝗮𝗿𝗻 𝗗𝘂𝗿𝗮𝘁𝗶𝗼𝗻𝘀", "callback_data": "cfg_warndur", "style": "primary"},
            {"text": f"🎭 𝗖𝗮𝗽𝘁𝗰𝗵𝗮 {ICON_ON if captcha_on else ICON_OFF}", "callback_data": "cfg_captcha",
             "style": "success" if captcha_on else "danger"},
        ],
        [
            {"text": f"🗑️ 𝗦𝘁𝗶𝗰𝗸𝗲𝗿 𝗗𝗲𝗹 {ICON_ON if stk else ICON_OFF}", "callback_data": "cfg_stkdel",
             "style": "success" if stk else "danger"},
            {"text": f"⏱️ 𝗔𝘂𝘁𝗼-𝗗𝗲𝗹𝗲𝘁𝗲 {ICON_ON if ad else ICON_OFF}", "callback_data": "cfg_autodel",
             "style": "success" if ad else "danger"},
        ],
        [
            {"text": "🏆 𝗥𝗲𝗽𝘂𝘁𝗮𝘁𝗶𝗼𝗻", "callback_data": "menu_repboard", "style": "primary"},
            {"text": f"💎 𝗣𝗿𝗲𝗺𝗶𝘂𝗺 {ICON_ON if prem_on else ICON_OFF}", "callback_data": "cfg_premium",
             "style": "success" if prem_on else "danger"},
        ],
        [
            {"text": "🌐 𝗖𝗼𝗺𝗺𝘂𝗻𝗶𝘁𝘆", "callback_data": "cfg_community", "style": "primary"},
        ],
        [
            {"text": "◀️ 𝗕𝗮𝗰𝗸", "callback_data": "menu_main", "style": "primary"},
            {"text": "❌ 𝗖𝗹𝗼𝘀𝗲", "callback_data": "close_menu", "style": "danger"},
        ],
    ]

def _settings_overview_text(chat_id):
    """/settings main panel ke liye chhota status overview — admin ko ek nazar mein
    pata chal jaaye ki kya on/off hai, bina har button khole."""
    g = db.get_group(chat_id)
    stk = g.get("sticker_delete_min")
    ad = g.get("autodelete_min")
    captcha_on = bool(g.get("captcha"))
    bl_count = len(db.get_blacklist(chat_id) or [])
    wl_count = len(db.get_whitelist(chat_id) or [])
    prem_on = bool(g.get("premium", False))
    return (
        f"*⚙️ 𝗚𝗥𝗢𝗨𝗣 𝗦𝗘𝗧𝗧𝗜𝗡𝗚𝗦 𝗣𝗔𝗡𝗘𝗟*\n"
        f"{'─'*14}\n\n"
        f"📌 *𝙌𝙪𝙞𝙘𝙠 𝙎𝙩𝙖𝙩𝙪𝙨*\n"
        f"  🛡️ Filters: {_filters_status_line(chat_id)}\n"
        f"  ⛔ Blacklist words: {bl_count}  •  ✅ Whitelist: {wl_count}\n"
        f"  🎭 Captcha: {ICON_ON + ' On' if captcha_on else ICON_OFF + ' Off'}\n"
        f"  🗑️ Sticker auto-del: {ICON_ON + ' ' + _sec_human(stk) if stk else ICON_OFF + ' Off'}\n"
        f"  ⏱️ Msg auto-del: {ICON_ON + ' ' + _sec_human(ad) if ad else ICON_OFF + ' Off'}\n"
        f"  💎 Premium: {ICON_ON + ' Active' if prem_on else ICON_OFF + ' Not active'}\n"
        f"{'─'*14}\n\n"
        f"💡 _/rules updates itself automatically from whatever you turn ON in_ 🛡️ Filters\n"
        f"Tap a button below to view or change a setting 👇\n"
        f"_Admins and the owner only — this panel closes automatically when idle._"
    )

async def settings_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ch = update.effective_chat
    u = update.effective_user
    if ch.type == "private":
        return await update.message.reply_text("⚠️ This command only works in a group.")
    if not await _cfg_is_authorized(ctx, ch.id, u.id):
        return await update.message.reply_text("🔒 This panel is for group admins and the owner only.")
    text = _settings_overview_text(ch.id)
    rows = kb_settings_main(ch.id)
    msg_id = await send_colored_message(ch.id, text, rows, parse_mode='Markdown')
    if not msg_id:
        sent = await update.message.reply_text(text, parse_mode='Markdown', reply_markup=_rows_to_markup(rows))
        msg_id = sent.message_id
    _remember_menu_owner(ch.id, msg_id, u.id)
    schedule_panel_autodelete(ctx, ch.id, msg_id, cmd_msg_id=update.message.message_id)

def rows_back_cfg():
    return [[{"text": "◀️ 𝗕𝗮𝗰𝗸", "callback_data": "cfg_main", "style": "primary"}]]

def kb_back_cfg():
    """Fallback ke liye plain-markup version (legacy call-sites)."""
    return _rows_to_markup(rows_back_cfg())

def kb_filters_grid(chat_id):
    filt = db.get_filters(chat_id)
    rows = []
    for group_label, keys in FILTER_GROUPS:
        rows.append([{"text": f"— {group_label} —", "callback_data": "cfg_noop"}])
        for i in range(0, len(keys), 2):
            row = []
            for k in keys[i:i+2]:
                on = bool(filt.get(k))
                icon = "✅" if on else "▫️"
                row.append({"text": f"{icon} {FILTER_LABELS[k]}", "callback_data": f"cfg_f_{k}",
                            "style": "success" if on else "danger"})
            rows.append(row)
    rows.append([{"text": "◀️ 𝗕𝗮𝗰𝗸", "callback_data": "cfg_main", "style": "primary"}])
    return rows

def _filters_status_line(chat_id):
    """'12/17 ON' jaisi quick summary — filters panel ke header me dikhane ke liye."""
    filt = db.get_filters(chat_id)
    total = len(DEFAULT_FILTERS)
    on = sum(1 for k in DEFAULT_FILTERS if filt.get(k))
    return f"{on}/{total} filters ON"

async def cfg_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE, data: str = None):
    query = update.callback_query
    if data is None:
        data = query.data
    ch = update.effective_chat
    u = query.from_user

    # Authorization checks pehle — agar fail ho, to sirf clicker ko ek
    # popup dikhana hai (query.answer show_alert), group mein KOI message
    # nahi bhejna. Isliye yahan ACK nahi karte jab tak pata na chale ki
    # authorized hai ya nahi (query.answer ek hi baar call ho sakta hai).
    if not _is_menu_owner(ch.id, query.message.message_id, u.id):
        try:
            await query.answer("🔒 This panel belongs to someone else — run your own /settings.", show_alert=True)
        except Exception:
            pass
        return

    if not await _cfg_is_authorized(ctx, ch.id, u.id):
        try:
            await query.answer("🔒 Admins and the owner only.", show_alert=True)
        except Exception:
            pass
        return

    # Authorized — turant ACK karo taaki button ka loading-spinner turant hat jaaye.
    try:
        await query.answer()
    except Exception:
        pass

    try:
        await _cfg_callback_body(update, ctx, data, query, ch, u)
    except Exception:
        # Kabhi bhi (future mein) kisi panel-text mein Markdown parse error
        # ho, to user ko blank/frozen panel ki jagah ek clear error dikhe —
        # silently kuch na hone se yeh behtar hai, taaki bug turant pakda jaaye.
        try:
            await ctx.bot.send_message(
                ch.id, "⚠️ Something went wrong opening that panel — please try again.",
                reply_to_message_id=query.message.message_id
            )
        except Exception:
            pass
    finally:
        # Panel abhi bhi khula hai (close/delete nahi hua) — idle-timer (re)start karo,
        # taaki 1 min tak koi use na kare to khud delete ho jaaye.
        schedule_panel_autodelete(ctx, ch.id, query.message.message_id)


async def _cfg_callback_body(update, ctx, data, query, ch, u):
    # ── Premium ──
    if data == "cfg_premium":
        g = db.get_group(ch.id)
        prem_on = bool(g.get("premium", False))
        uname_on = bool(g.get("allow_member_usernames", False))
        bio_link_mode = _bio_link_mode(g)
        bio_bl_on = bool(g.get("bio_blacklist_guard", True))
        bio_uname_mode = g.get("bio_username_guard", "off")
        text = (
            f"*💎 𝗣𝗥𝗘𝗠𝗜𝗨𝗠 𝗣𝗥𝗢𝗧𝗘𝗖𝗧𝗜𝗢𝗡*\n"
            f"{'─'*14}\n\n"
            f"Status: {'🟢 *Active in this group*' if prem_on else '🔴 *Not active in this group*'}\n\n"
            f"{'─'*14}\n"
            f"*✨ 𝗣𝗿𝗲𝗺𝗶𝘂𝗺 𝗕𝗲𝗻𝗲𝗳𝗶𝘁𝘀:*\n"
            f"  ✏️ *Edit Guard* — if someone edits an old clean message\n"
            f"       into a link or blacklisted word, it's caught instantly\n"
            f"  🕵️ *Bio Guard* — members with a link, blacklisted word, or\n"
            f"       (if enabled) an @username in their profile bio get\n"
            f"       shadow-blocked (their messages silently won't be\n"
            f"       visible to anyone) — each check below is toggleable\n"
            f"  👤 *Member Username Guard* — when ON, only this group's own\n"
            f"       members can mention/send an @username here; sending\n"
            f"       any outsider's @username gets the message deleted\n"
            f"       with a warning issued\n"
            f"  ⚡ Fast detection — bio changes and edits are scanned right away\n\n"
        )
        rows = []
        if prem_on:
            link_mode_label = {
                "off": "🔴 OFF",
                "blacklist": "🟡 Domains Only",
                "all": "🟢 All Links",
            }[bio_link_mode]
            domains = g.get("bio_link_domains")
            if domains is None:
                domains = DEFAULT_BIO_LINK_DOMAINS
            link_mode_desc = {
                "off": "_Links in bios aren't checked at all._",
                "blacklist": f"_Only trips on a link to one of {len(domains)} blacklisted domain(s): "
                             + ", ".join(f"`{d}`" for d in domains)
                             + " — manage with `/addbiodomain`, `/removebiodomain`, `/biodomains`._",
                "all": "_ANY link at all in a bio gets shadow-blocked, regardless of domain._",
            }[bio_link_mode]
            uname_mode_label = {
                "off": "🔴 OFF",
                "users_only": "🟡 Users Only",
                "full": "🟢 Full Block",
            }[bio_uname_mode]
            uname_mode_desc = {
                "off": "_Usernames in bios aren't checked at all._",
                "users_only": "_A plain Telegram user's @username is allowed in bios — but any channel's, group's, or other non-user @username still gets shadow-blocked._",
                "full": "_ANY @username in a bio gets shadow-blocked — no exceptions._",
            }[bio_uname_mode]
            bio_words_custom = db.get_biowords(ch.id)
            bio_words_count = len(bio_words_custom) if bio_words_custom is not None else \
                len(set((db.get_blacklist(ch.id) or []) + (db.get_gblacklist() or [])))
            bio_words_desc = (
                f"_Custom list, independent from `/blacklist`. Manage with the button below, or `/addbioword`, `/removebioword`._"
                if bio_words_custom is not None else
                f"_Mirrors your main `/blacklist` + global blacklist until you customize it below (or with `/addbioword`)._"
            )
            text += (
                f"{'─'*14}\n"
                f"*🕵️ 𝗕𝗶𝗼 𝗚𝘂𝗮𝗿𝗱 𝗖𝗵𝗲𝗰𝗸𝘀:*\n"
                f"🔗 Link check: {link_mode_label}\n"
                f"{link_mode_desc}\n\n"
                f"⛔ Blacklisted word check: {'🟢 ON' if bio_bl_on else '🔴 OFF'}\n"
                f"{bio_words_desc}\n\n"
                f"👤 Username check: {uname_mode_label}\n"
                f"{uname_mode_desc}\n\n"
                f"{'─'*14}\n"
                f"👤 *Allow Member Usernames (in messages):* {'🟢 ON' if uname_on else '🔴 OFF'}\n"
                f"{'_Only this group’s members can send a @username. Everyone else’s @username gets blocked + warned._' if uname_on else '_All @username mentions are currently blocked in this group (default)._'}\n\n"
            )
            rows.append([
                {"text": f"🔗 𝗕𝗶𝗼 𝗟𝗶𝗻𝗸: {link_mode_label}",
                 "callback_data": "cfg_premium_biolink_cycle",
                 "style": "success" if bio_link_mode == "all" else ("primary" if bio_link_mode == "blacklist" else "danger")}
            ])
            if bio_link_mode == "blacklist":
                rows.append([
                    {"text": f"🌐 𝗠𝗮𝗻𝗮𝗴𝗲 𝗗𝗼𝗺𝗮𝗶𝗻𝘀 ({len(domains)})",
                     "callback_data": "cfg_premium_biodomains", "style": "primary"}
                ])
            rows.append([
                {"text": f"⛔ 𝗕𝗶𝗼 𝗪𝗼𝗿𝗱 {ICON_ON if bio_bl_on else ICON_OFF}",
                 "callback_data": "cfg_premium_bioblacklist_toggle",
                 "style": "success" if bio_bl_on else "danger"}
            ])
            rows.append([
                {"text": f"📝 𝗠𝗮𝗻𝗮𝗴𝗲 𝗕𝗶𝗼 𝗪𝗼𝗿𝗱𝘀 ({bio_words_count})",
                 "callback_data": "cfg_premium_biowords", "style": "primary"}
            ])
            rows.append([
                {"text": f"👤 𝗕𝗶𝗼 𝗨𝘀𝗲𝗿𝗻𝗮𝗺𝗲: {uname_mode_label}",
                 "callback_data": "cfg_premium_biouname_cycle",
                 "style": "success" if bio_uname_mode == "full" else ("primary" if bio_uname_mode == "users_only" else "danger")}
            ])
            rows.append([
                {"text": f"👤 𝗠𝗲𝗺𝗯𝗲𝗿 𝗨𝘀𝗲𝗿𝗻𝗮𝗺𝗲𝘀 (𝗺𝘀𝗴𝘀) {ICON_ON if uname_on else ICON_OFF}",
                 "callback_data": "cfg_premium_uname_toggle",
                 "style": "success" if uname_on else "danger"}
            ])
        text += (
            f"{'─'*14}\n"
            f"*💰 𝗣𝗿𝗶𝗰𝗶𝗻𝗴:*\n"
            f"  • Up to 1,000 members — ₹10\n"
            f"  • Up to 10,000 members — ₹49\n"
            f"  • Above 10,000 — +₹5 for every extra 1,000 members\n\n"
            f"{'─'*14}\n"
            f"📩 To get Premium, DM `@Suhani_TG`!"
        )
        rows.append([{"text": "📩 𝗗𝗠 @Suhani_TG", "url": "https://t.me/Suhani_TG"}])
        rows.append([{"text": "◀️ 𝗕𝗮𝗰𝗸", "callback_data": "cfg_main", "style": "primary"}])
        await _cfg_edit(query, ch.id, text, rows)
        return

    if data == "cfg_premium_uname_toggle":
        g = db.get_group(ch.id)
        if not bool(g.get("premium", False)):
            await query.answer("💎 This is a Premium-only feature. DM @Suhani_TG to get Premium.", show_alert=True)
            return
        db.update_group(ch.id, {"allow_member_usernames": not bool(g.get("allow_member_usernames", False))})
        await cfg_callback_reroute(update, ctx, "cfg_premium")
        return

    if data == "cfg_premium_biolink_cycle":
        g = db.get_group(ch.id)
        if not bool(g.get("premium", False)):
            await query.answer("💎 This is a Premium-only feature. DM @Suhani_TG to get Premium.", show_alert=True)
            return
        cur = _bio_link_mode(g)
        nxt = {"off": "blacklist", "blacklist": "all", "all": "off"}.get(cur, "all")
        patch = {"bio_link_guard": nxt}
        if nxt == "blacklist" and g.get("bio_link_domains") is None:
            patch["bio_link_domains"] = DEFAULT_BIO_LINK_DOMAINS.copy()
        db.update_group(ch.id, patch)
        await cfg_callback_reroute(update, ctx, "cfg_premium")
        return

    if data == "cfg_premium_bioblacklist_toggle":
        g = db.get_group(ch.id)
        if not bool(g.get("premium", False)):
            await query.answer("💎 This is a Premium-only feature. DM @Suhani_TG to get Premium.", show_alert=True)
            return
        db.update_group(ch.id, {"bio_blacklist_guard": not bool(g.get("bio_blacklist_guard", True))})
        await cfg_callback_reroute(update, ctx, "cfg_premium")
        return

    if data == "cfg_premium_biouname_cycle":
        g = db.get_group(ch.id)
        if not bool(g.get("premium", False)):
            await query.answer("💎 This is a Premium-only feature. DM @Suhani_TG to get Premium.", show_alert=True)
            return
        cur = g.get("bio_username_guard", "off")
        nxt = {"off": "users_only", "users_only": "full", "full": "off"}.get(cur, "off")
        db.update_group(ch.id, {"bio_username_guard": nxt})
        await cfg_callback_reroute(update, ctx, "cfg_premium")
        return

    # ── Premium Bio Guard: manage Bio Link Domains (add/remove via buttons) ──
    if data == "cfg_premium_biodomains":
        g = db.get_group(ch.id)
        if not bool(g.get("premium", False)):
            await query.answer("💎 This is a Premium-only feature. DM @Suhani_TG to get Premium.", show_alert=True)
            return
        domains = g.get("bio_link_domains")
        if domains is None:
            domains = DEFAULT_BIO_LINK_DOMAINS
        text = (
            f"*🌐 𝗕𝗜𝗢 𝗟𝗜𝗡𝗞 𝗗𝗢𝗠𝗔𝗜𝗡𝗦*\n{'─'*14}\n\n"
            f"Used only when Bio Link mode is 🟡 *Domains Only*. A bio link\n"
            f"trips the guard only if its domain matches one of these:\n\n"
        )
        rows = []
        if domains:
            for i, d in enumerate(domains):
                rows.append([{"text": f"❌ {d}", "callback_data": f"cfg_biodomain_rm_{i}"}])
        else:
            text += "_No domains set — Domains Only mode won't trigger on anything until you add one._\n\n"
        rows.append([{"text": "➕ 𝗔𝗱𝗱 𝗗𝗼𝗺𝗮𝗶𝗻", "callback_data": "cfg_biodomain_add", "style": "success"}])
        rows.append([{"text": "◀️ 𝗕𝗮𝗰𝗸", "callback_data": "cfg_premium", "style": "primary"}])
        await _cfg_edit(query, ch.id, text, rows)
        return

    if data.startswith("cfg_biodomain_rm_"):
        g = db.get_group(ch.id)
        if not bool(g.get("premium", False)):
            await query.answer("💎 This is a Premium-only feature. DM @Suhani_TG to get Premium.", show_alert=True)
            return
        try:
            idx = int(data[len("cfg_biodomain_rm_"):])
        except ValueError:
            await query.answer()
            return
        domains = g.get("bio_link_domains")
        if domains is None:
            domains = DEFAULT_BIO_LINK_DOMAINS
        if 0 <= idx < len(domains):
            removed = domains[idx]
            if g.get("bio_link_domains") is None:
                db.update_group(ch.id, {"bio_link_domains": DEFAULT_BIO_LINK_DOMAINS.copy()})
            db.remove_bio_domain(ch.id, removed)
            await query.answer(f"✅ Removed {removed}")
        await cfg_callback_reroute(update, ctx, "cfg_premium_biodomains")
        return

    if data == "cfg_biodomain_add":
        g = db.get_group(ch.id)
        if not bool(g.get("premium", False)):
            await query.answer("💎 This is a Premium-only feature. DM @Suhani_TG to get Premium.", show_alert=True)
            return
        prompt = await ctx.bot.send_message(
            ch.id,
            f"{BIODOMAIN_ADD_MARKER}\n\nReply to *this* message with the domain to blacklist — e.g. `instagram.com`.",
            parse_mode='Markdown',
            reply_markup=ForceReply(selective=True, input_field_placeholder="e.g. instagram.com")
        )
        asyncio.create_task(delete_after(ctx, ch.id, prompt.message_id, 120))
        return

    # ── Premium Bio Guard: manage Bio Words (add/remove via buttons) ──
    if data == "cfg_premium_biowords":
        g = db.get_group(ch.id)
        if not bool(g.get("premium", False)):
            await query.answer("💎 This is a Premium-only feature. DM @Suhani_TG to get Premium.", show_alert=True)
            return
        custom = db.get_biowords(ch.id)
        if custom is None:
            words = list(set((db.get_blacklist(ch.id) or []) + (db.get_gblacklist() or [])))
            note = "_Not customized yet — currently mirrors your main `/blacklist` + global blacklist. Adding/removing here forks it into its own independent list._"
        else:
            words = custom
            note = "_Custom list — independent from your main `/blacklist`._"
        SHOWN = 15
        text = f"*🕵️ 𝗕𝗜𝗢 𝗪𝗢𝗥𝗗𝗦* ({len(words)})\n{'─'*14}\n\n{note}\n\n"
        rows = []
        if words:
            for i, w in enumerate(words[:SHOWN]):
                rows.append([{"text": f"❌ {w}", "callback_data": f"cfg_bioword_rm_{i}"}])
            if len(words) > SHOWN:
                text += f"_+{len(words) - SHOWN} more — use `/biowords` to see the full list, `/removebioword <word>` to remove any of them._\n\n"
        else:
            text += "_No Bio Words set._\n\n"
        rows.append([{"text": "➕ 𝗔𝗱𝗱 𝗪𝗼𝗿𝗱", "callback_data": "cfg_bioword_add", "style": "success"}])
        rows.append([{"text": "◀️ 𝗕𝗮𝗰𝗸", "callback_data": "cfg_premium", "style": "primary"}])
        await _cfg_edit(query, ch.id, text, rows)
        return

    if data.startswith("cfg_bioword_rm_"):
        g = db.get_group(ch.id)
        if not bool(g.get("premium", False)):
            await query.answer("💎 This is a Premium-only feature. DM @Suhani_TG to get Premium.", show_alert=True)
            return
        try:
            idx = int(data[len("cfg_bioword_rm_"):])
        except ValueError:
            await query.answer()
            return
        custom = db.get_biowords(ch.id)
        words = custom if custom is not None else list(set((db.get_blacklist(ch.id) or []) + (db.get_gblacklist() or [])))
        if 0 <= idx < len(words):
            removed = words[idx]
            if custom is None:
                # First edit — fork from the combined default before removing,
                # so the main /blacklist is never touched.
                db.set_biowords(ch.id, words)
            db.remove_bioword(ch.id, removed)
            await query.answer(f"✅ Removed {removed}")
        await cfg_callback_reroute(update, ctx, "cfg_premium_biowords")
        return

    if data == "cfg_bioword_add":
        g = db.get_group(ch.id)
        if not bool(g.get("premium", False)):
            await query.answer("💎 This is a Premium-only feature. DM @Suhani_TG to get Premium.", show_alert=True)
            return
        prompt = await ctx.bot.send_message(
            ch.id,
            f"{BIOWORD_ADD_MARKER}\n\nReply to *this* message with the word/phrase to add.",
            parse_mode='Markdown',
            reply_markup=ForceReply(selective=True, input_field_placeholder="word or phrase")
        )
        asyncio.create_task(delete_after(ctx, ch.id, prompt.message_id, 120))
        return

    # ── Community ──
    if data == "cfg_community":
        groups = db.get_community_groups(u.id)
        in_community = ch.id in groups
        text = (
            f"*🌐 𝗬𝗢𝗨𝗥 𝗖𝗢𝗠𝗠𝗨𝗡𝗜𝗧𝗬*\n"
            f"{'─'*14}\n\n"
            f"Link groups you admin together, so you can ban a "
            f"troublemaker from *all of them at once* — or unmute "
            f"someone across all of them at once — without needing "
            f"the bot owner.\n\n"
            f"{'─'*14}\n"
            f"This group: {'🟢 *In your community*' if in_community else '🔴 *Not in your community*'}\n"
            f"Total groups in your community: `{len(groups)}`\n"
        )
        rows = [
            [{"text": "➖ 𝗥𝗲𝗺𝗼𝘃𝗲 𝗧𝗵𝗶𝘀 𝗚𝗿𝗼𝘂𝗽" if in_community else "➕ 𝗔𝗱𝗱 𝗧𝗵𝗶𝘀 𝗚𝗿𝗼𝘂𝗽",
              "callback_data": "cfg_community_toggle",
              "style": "danger" if in_community else "success"}],
            [{"text": "📋 𝗟𝗶𝘀𝘁 𝗠𝘆 𝗖𝗼𝗺𝗺𝘂𝗻𝗶𝘁𝘆", "callback_data": "cfg_community_list", "style": "primary"}],
            [{"text": "🔨 𝗕𝗮𝗻 𝗨𝘀𝗲𝗿 𝗳𝗿𝗼𝗺 𝗖𝗼𝗺𝗺𝘂𝗻𝗶𝘁𝘆", "callback_data": "cfg_community_ban", "style": "danger"}],
            [{"text": "◀️ 𝗕𝗮𝗰𝗸", "callback_data": "cfg_main", "style": "primary"}],
        ]
        await _cfg_edit(query, ch.id, text, rows)
        return

    if data == "cfg_community_toggle":
        groups = db.get_community_groups(u.id)
        if ch.id in groups:
            db.remove_from_community(u.id, ch.id)
        else:
            db.add_to_community(u.id, ch.id)
        await cfg_callback_reroute(update, ctx, "cfg_community")
        return

    if data == "cfg_community_list":
        groups = db.get_community_groups(u.id)
        if not groups:
            text = "📭 *Your community is empty right now.*\n\nGo back to this group's settings and tap “➕ Add This Group”."
        else:
            lines = []
            for gid in groups:
                try:
                    chat = await ctx.bot.get_chat(gid)
                    lines.append(f"• {chat.title}")
                except Exception:
                    lines.append(f"• `{gid}`")
            text = (
                f"🌐 *𝗬𝗼𝘂𝗿 𝗖𝗼𝗺𝗺𝘂𝗻𝗶𝘁𝘆* — `{len(groups)}` group(s)\n"
                f"{'─'*14}\n\n" + "\n".join(lines)
            )
        await _cfg_edit(
            query, ch.id, text,
            [[{"text": "◀️ 𝗕𝗮𝗰𝗸", "callback_data": "cfg_community", "style": "primary"}]]
        )
        return

    if data == "cfg_community_ban":
        groups = db.get_community_groups(u.id)
        if not groups:
            await query.answer("📭 First add at least one group to your community.", show_alert=True)
            return
        SETTINGS_PENDING[(ch.id, u.id)] = {"action": "community_ban", "panel_msg_id": query.message.message_id}
        await _cfg_edit(
            query, ch.id,
            f"🔨 *𝗕𝗮𝗻 𝗳𝗿𝗼𝗺 𝗖𝗼𝗺𝗺𝘂𝗻𝗶𝘁𝘆*\n{'─'*14}\n\n"
            f"Type the target's *user ID* or *@username*, with a reason "
            f"if you want — e.g.: `123456789 spamming links`\n\n"
            f"_This will ban them from all `{len(groups)}` group(s) in your community._",
            rows_back_cfg()
        )
        return

    if data == "cfg_main":
        SETTINGS_PENDING.pop((ch.id, u.id), None)
        await _cfg_edit(query, ch.id, _settings_overview_text(ch.id), kb_settings_main(ch.id))
        return

    # ── Rules ──
    if data == "cfg_rules":
        custom_rules = db.get_rules(ch.id)
        if custom_rules:
            body = f"*📜 GROUP RULES*  _(custom)_\n{'─'*14}\n\n{custom_rules}"
            extra_row = [{"text": "♻️ 𝗥𝗲𝘃𝗲𝗿𝘁 𝘁𝗼 𝗔𝘂𝘁𝗼 𝗥𝘂𝗹𝗲𝘀", "callback_data": "cfg_rules_reset", "style": "danger"}]
        else:
            body = (
                f"*📜 GROUP RULES*  _(auto — built from your Filters)_\n{'─'*14}\n\n"
                f"{build_auto_rules_text(ch.id)}\n\n"
                f"_Turn filters on/off from 🛡️ Filters and this list updates automatically._"
            )
            extra_row = None
        rows = [[{"text": "✏️ 𝗦𝗲𝘁 𝗖𝘂𝘀𝘁𝗼𝗺 𝗥𝘂𝗹𝗲𝘀", "callback_data": "cfg_rules_set", "style": "primary"}]]
        if extra_row:
            rows.append(extra_row)
        rows.append([{"text": "◀️ 𝗕𝗮𝗰𝗸", "callback_data": "cfg_main", "style": "primary"}])
        await _cfg_edit(query, ch.id, body, rows)
        return

    if data == "cfg_rules_reset":
        db.set_rules(ch.id, None)
        await query.answer("✅ Reverted to auto rules (built from your active Filters)")
        await cfg_callback_reroute(update, ctx, "cfg_rules")
        return

    if data == "cfg_rules_set":
        SETTINGS_PENDING[(ch.id, u.id)] = {"action": "rules", "panel_msg_id": query.message.message_id}
        await _cfg_edit(query, ch.id, "✏️ *Type and send the new rules* (next message):", rows_back_cfg())
        return

    # ── Sticker auto-delete ──
    if data == "cfg_stkdel":
        g = db.get_group(ch.id)
        stk = g.get("sticker_delete_min")
        await _cfg_edit(
            query, ch.id,
            f"*🗑️ STICKER AUTO-DELETE*\n{'─'*14}\n\n"
            f"Status: {'🟢 ON — ' + str(stk) + ' min' if stk else '🔴 OFF'}\n\n"
            f"_Stickers/GIFs will auto-delete after this duration._",
            [
                [{"text": "🔴 𝗧𝘂𝗿𝗻 𝗢𝗙𝗙" if stk else "🟢 Turn ON", "callback_data": "cfg_stkdel_toggle",
                  "style": "danger" if stk else "success"}],
                [{"text": "✏️ 𝗦𝗲𝘁 𝗠𝗶𝗻𝘂𝘁𝗲𝘀", "callback_data": "cfg_stkdel_set", "style": "primary"}],
                [{"text": "◀️ 𝗕𝗮𝗰𝗸", "callback_data": "cfg_main", "style": "primary"}],
            ]
        )
        return

    if data == "cfg_stkdel_toggle":
        g = db.get_group(ch.id)
        if g.get("sticker_delete_min"):
            db.update_group(ch.id, {"sticker_delete_min": None})
        else:
            db.update_group(ch.id, {"sticker_delete_min": 5})
        await cfg_callback_reroute(update, ctx, "cfg_stkdel")
        return

    if data == "cfg_stkdel_set":
        SETTINGS_PENDING[(ch.id, u.id)] = {"action": "stkdel_min", "panel_msg_id": query.message.message_id}
        await _cfg_edit(
            query, ch.id,
            "✏️ *After how many minutes should stickers/GIFs be deleted?* (send a number, e.g. `5`):",
            rows_back_cfg()
        )
        return

    # ── Auto-delete ──
    if data == "cfg_autodel":
        g = db.get_group(ch.id)
        ad = g.get("autodelete_min")
        await _cfg_edit(
            query, ch.id,
            f"*⏱️ AUTO-DELETE MESSAGES*\n{'─'*14}\n\n"
            f"Status: {'🟢 ON — ' + str(ad) + ' min' if ad else '🔴 OFF'}\n\n"
            f"_Normal messages will auto-delete after this duration._",
            [
                [{"text": "🔴 𝗧𝘂𝗿𝗻 𝗢𝗙𝗙" if ad else "🟢 Turn ON", "callback_data": "cfg_autodel_toggle",
                  "style": "danger" if ad else "success"}],
                [{"text": "✏️ 𝗦𝗲𝘁 𝗠𝗶𝗻𝘂𝘁𝗲𝘀", "callback_data": "cfg_autodel_set", "style": "primary"}],
                [{"text": "◀️ 𝗕𝗮𝗰𝗸", "callback_data": "cfg_main", "style": "primary"}],
            ]
        )
        return

    if data == "cfg_autodel_toggle":
        g = db.get_group(ch.id)
        if g.get("autodelete_min"):
            db.update_group(ch.id, {"autodelete_min": None})
        else:
            db.update_group(ch.id, {"autodelete_min": 10})
        await cfg_callback_reroute(update, ctx, "cfg_autodel")
        return

    if data == "cfg_autodel_set":
        SETTINGS_PENDING[(ch.id, u.id)] = {"action": "autodel_min", "panel_msg_id": query.message.message_id}
        await _cfg_edit(
            query, ch.id,
            "✏️ *After how many minutes should normal messages be deleted?* (send a number, e.g. `10`):",
            rows_back_cfg()
        )
        return

    # ── Warn durations ──
    if data == "cfg_warndur":
        wd = db.get_warn_durations(ch.id)
        await _cfg_edit(
            query, ch.id,
            f"*⚠️ WARN → MUTE DURATIONS*\n{'─'*14}\n\n"
            f"🟡 W1: `{_sec_human(wd[1])}`\n"
            f"🟠 W2: `{_sec_human(wd[2])}`\n"
            f"🔴 W3: `{_sec_human(wd[3])}`\n"
            f"💀 W4: `{_sec_human(wd[4])}` _(global mute)_\n\n"
            f"_Select a stage to edit:_",
            [
                [
                    {"text": "𝗪𝟭 ✏️", "callback_data": "cfg_wd_1", "style": "primary"},
                    {"text": "𝗪𝟮 ✏️", "callback_data": "cfg_wd_2", "style": "primary"},
                ],
                [
                    {"text": "𝗪𝟯 ✏️", "callback_data": "cfg_wd_3", "style": "primary"},
                    {"text": "𝗪𝟰 ✏️", "callback_data": "cfg_wd_4", "style": "primary"},
                ],
                [{"text": "◀️ 𝗕𝗮𝗰𝗸", "callback_data": "cfg_main", "style": "primary"}],
            ]
        )
        return

    if data.startswith("cfg_wd_"):
        stage = int(data.split("_")[-1])
        SETTINGS_PENDING[(ch.id, u.id)] = {"action": "warndur", "extra": stage, "panel_msg_id": query.message.message_id}
        await _cfg_edit(query, ch.id, f"✏️ *Send seconds for W{stage}* (e.g. `60`):", rows_back_cfg())
        return

    # ── Blacklist ──
    if data == "cfg_bl":
        words = db.get_blacklist(ch.id)
        preview = ", ".join(words[:15]) if words else "_(empty)_"
        await _cfg_edit(
            query, ch.id,
            f"*⛔ 𝗚𝗥𝗢𝗨𝗣 𝗕𝗟𝗔𝗖𝗞𝗟𝗜𝗦𝗧*\n{'─'*14}\n\n"
            f"Words: {preview}\n\n"
            f"_You can also disable the owner's global blacklist words for this group._",
            [
                [
                    {"text": "➕ 𝗔𝗱𝗱 𝗪𝗼𝗿𝗱", "callback_data": "cfg_bl_add", "style": "success"},
                    {"text": "➖ 𝗥𝗲𝗺𝗼𝘃𝗲 𝗪𝗼𝗿𝗱", "callback_data": "cfg_bl_rem", "style": "danger"},
                ],
                [{"text": "🌐 𝗚𝗹𝗼𝗯𝗮𝗹 𝗪𝗼𝗿𝗱𝘀 (𝗼𝘄𝗻𝗲𝗿 𝘀𝗲𝘁)", "callback_data": "cfg_bl_g", "style": "primary"}],
                [{"text": "◀️ 𝗕𝗮𝗰𝗸", "callback_data": "cfg_main", "style": "primary"}],
            ]
        )
        return

    if data == "cfg_bl_add":
        SETTINGS_PENDING[(ch.id, u.id)] = {"action": "bl_add", "panel_msg_id": query.message.message_id}
        await _cfg_edit(query, ch.id, "✏️ *Send the word to add to the blacklist:*", rows_back_cfg())
        return

    if data == "cfg_bl_rem":
        SETTINGS_PENDING[(ch.id, u.id)] = {"action": "bl_rem", "panel_msg_id": query.message.message_id}
        await _cfg_edit(query, ch.id, "✏️ *Send the word to remove from the blacklist:*", rows_back_cfg())
        return

    if data == "cfg_bl_g":
        gwords = db.get_gblacklist()
        disabled = set(db.get_disabled_gwords(ch.id))
        if not gwords:
            await _cfg_edit(query, ch.id, "🌐 *Owner hasn't set any global blacklist word yet.*", rows_back_cfg())
            return
        rows = []
        for w in gwords[:20]:
            off = w in disabled
            icon = "🔴 OFF" if off else "🟢 ON"
            rows.append([{"text": f"{icon} — {w}", "callback_data": f"cfg_bl_gt_{w[:45]}",
                          "style": "danger" if off else "success"}])
        rows.append([{"text": "◀️ 𝗕𝗮𝗰𝗸", "callback_data": "cfg_bl", "style": "primary"}])
        await _cfg_edit(
            query, ch.id,
            f"*🌐 GLOBAL BLACKLIST WORDS*\n{'─'*14}\n\n"
            f"_Tap to turn ON/OFF for your group (the global list itself won't change, only your group is affected):_",
            rows
        )
        return

    if data.startswith("cfg_bl_gt_"):
        word = data[len("cfg_bl_gt_"):]
        disabled = set(db.get_disabled_gwords(ch.id))
        if word in disabled:
            db.enable_gword(ch.id, word)
        else:
            db.disable_gword(ch.id, word)
        await cfg_callback_reroute(update, ctx, "cfg_bl_g")
        return

    # ── Whitelist ──
    if data == "cfg_wl":
        words = db.get_whitelist(ch.id)
        preview = ", ".join(words[:15]) if words else "_(empty)_"
        await _cfg_edit(
            query, ch.id,
            f"*✅ 𝗚𝗥𝗢𝗨𝗣 𝗪𝗛𝗜𝗧𝗘𝗟𝗜𝗦𝗧*\n{'─'*14}\n\n"
            f"Words: {preview}\n\n"
            f"_You can also disable the owner's global whitelist words for this group._",
            [
                [
                    {"text": "➕ 𝗔𝗱𝗱 𝗪𝗼𝗿𝗱", "callback_data": "cfg_wl_add", "style": "success"},
                    {"text": "➖ 𝗥𝗲𝗺𝗼𝘃𝗲 𝗪𝗼𝗿𝗱", "callback_data": "cfg_wl_rem", "style": "danger"},
                ],
                [{"text": "🌐 𝗚𝗹𝗼𝗯𝗮𝗹 𝗪𝗼𝗿𝗱𝘀 (𝗼𝘄𝗻𝗲𝗿 𝘀𝗲𝘁)", "callback_data": "cfg_wl_g", "style": "primary"}],
                [{"text": "◀️ 𝗕𝗮𝗰𝗸", "callback_data": "cfg_main", "style": "primary"}],
            ]
        )
        return

    if data == "cfg_wl_add":
        SETTINGS_PENDING[(ch.id, u.id)] = {"action": "wl_add", "panel_msg_id": query.message.message_id}
        await _cfg_edit(query, ch.id, "✏️ *Send the word to add to the whitelist:*", rows_back_cfg())
        return

    if data == "cfg_wl_rem":
        SETTINGS_PENDING[(ch.id, u.id)] = {"action": "wl_rem", "panel_msg_id": query.message.message_id}
        await _cfg_edit(query, ch.id, "✏️ *Send the word to remove from the whitelist:*", rows_back_cfg())
        return

    if data == "cfg_wl_g":
        gwords = db.get_gwhitelist()
        disabled = set(db.get_disabled_gwhite(ch.id))
        if not gwords:
            await _cfg_edit(query, ch.id, "🌐 *Owner hasn't set any global whitelist word yet.*", rows_back_cfg())
            return
        rows = []
        for w in gwords[:20]:
            off = w in disabled
            icon = "🔴 OFF" if off else "🟢 ON"
            rows.append([{"text": f"{icon} — {w}", "callback_data": f"cfg_wl_gt_{w[:45]}",
                          "style": "danger" if off else "success"}])
        rows.append([{"text": "◀️ 𝗕𝗮𝗰𝗸", "callback_data": "cfg_wl", "style": "primary"}])
        await _cfg_edit(
            query, ch.id,
            f"*🌐 GLOBAL WHITELIST WORDS*\n{'─'*14}\n\n"
            f"_Tap to turn ON/OFF for your group:_",
            rows
        )
        return

    if data.startswith("cfg_wl_gt_"):
        word = data[len("cfg_wl_gt_"):]
        disabled = set(db.get_disabled_gwhite(ch.id))
        if word in disabled:
            db.enable_gwhite(ch.id, word)
        else:
            db.disable_gwhite(ch.id, word)
        await cfg_callback_reroute(update, ctx, "cfg_wl_g")
        return

    # ── Filters grid ──
    if data == "cfg_noop":
        return

    if data == "cfg_filters":
        await _cfg_edit(
            query, ch.id,
            f"*🛡️ FILTERS — {_filters_status_line(ch.id)}*\n{'─'*14}\n\n"
            f"✅ = ON     ▫️ = OFF\n"
            f"_Tap any filter — it toggles ON/OFF instantly._\n\n"
            f"📜 _Whatever you turn ON here shows up automatically in /rules._\n"
            f"🌐 _Multi-group ban/unmute? See 🏠 Settings → Community._",
            kb_filters_grid(ch.id)
        )
        return

    if data.startswith("cfg_f_"):
        key = data[len("cfg_f_"):]
        if key in DEFAULT_FILTERS:
            cur = db.get_filters(ch.id).get(key)
            db.set_filter(ch.id, key, not cur)
            state = "🟢 ON" if not cur else "🔴 OFF"
            try:
                await query.answer(f"{FILTER_LABELS.get(key, key)} → {state}")
            except Exception:
                pass
        await _cfg_edit(
            query, ch.id,
            f"*🛡️ FILTERS — {_filters_status_line(ch.id)}*\n{'─'*14}\n\n"
            f"✅ = ON     ▫️ = OFF\n"
            f"_Tap any filter — it toggles ON/OFF instantly._\n\n"
            f"🌐 _Multi-group ban/unmute? See 🏠 Settings → Community._",
            kb_filters_grid(ch.id)
        )
        return

    # ── Captcha ──
    if data == "cfg_captcha":
        g = db.get_group(ch.id)
        on = bool(g.get("captcha"))
        await _cfg_edit(
            query, ch.id,
            f"*🎭 CAPTCHA VERIFICATION*\n{'─'*14}\n\n"
            f"Status: {ICON_ON + ' ON' if on else ICON_OFF + ' OFF'}\n\n"
            f"_New members must solve a math question to chat, until verified._",
            [
                [{"text": f"{ICON_OFF} 𝗧𝘂𝗿𝗻 𝗢𝗙𝗙" if on else f"{ICON_ON} Turn ON", "callback_data": "cfg_captcha_toggle",
                  "style": "danger" if on else "success"}],
                [{"text": "◀️ 𝗕𝗮𝗰𝗸", "callback_data": "cfg_main", "style": "primary"}],
            ]
        )
        return

    if data == "cfg_captcha_toggle":
        g = db.get_group(ch.id)
        db.update_group(ch.id, {"captcha": not bool(g.get("captcha"))})
        await cfg_callback_reroute(update, ctx, "cfg_captcha")
        return


async def cfg_callback_reroute(update, ctx, new_data):
    """Ek hi callback function ke andar dusre 'view' pe re-render karne ke liye."""
    await cfg_callback(update, ctx, data=new_data)


async def handle_settings_input(update: Update, ctx: ContextTypes.DEFAULT_TYPE, key) -> bool:
    """/settings panel se pending text-input (rules/word/number) ko process karta hai."""
    pending = SETTINGS_PENDING.get(key)
    if not pending:
        return False
    ch_id, user_id = key
    msg = update.message
    text = (msg.text or "").strip()
    action = pending["action"]

    if not await _cfg_is_authorized(ctx, ch_id, user_id):
        SETTINGS_PENDING.pop(key, None)
        return False

    def _int_or_none(s):
        try:
            return int(s)
        except Exception:
            return None

    reply = None
    if action == "rules":
        db.set_rules(ch_id, text)
        reply = "✅ *Rules updated.*"
    elif action == "stkdel_min":
        n = _int_or_none(text)
        if n is None or n <= 0:
            reply = "⚠️ Send a valid number (e.g. `5`)."
        else:
            db.update_group(ch_id, {"sticker_delete_min": n})
            reply = f"✅ *Sticker auto-delete set to {n} min.*"
    elif action == "autodel_min":
        n = _int_or_none(text)
        if n is None or n <= 0:
            reply = "⚠️ Send a valid number (e.g. `10`)."
        else:
            db.update_group(ch_id, {"autodelete_min": n})
            reply = f"✅ *Auto-delete set to {n} min.*"
    elif action == "warndur":
        n = _int_or_none(text)
        stage = pending.get("extra")
        if n is None or n <= 0:
            reply = "⚠️ Send a valid number of seconds (e.g. `60`)."
        else:
            db.set_warn_duration(ch_id, stage, n)
            reply = f"✅ *W{stage} duration set to {_sec_human(n)}.*"
    elif action == "bl_add":
        if text:
            db.add_blacklist(ch_id, text.split()[0])
            reply = f"✅ *'{text.split()[0]}' added to the blacklist.*"
    elif action == "bl_rem":
        if text:
            db.remove_blacklist(ch_id, text.split()[0])
            reply = f"✅ *'{text.split()[0]}' removed from the blacklist.*"
    elif action == "wl_add":
        if text:
            db.add_whitelist(ch_id, text.split()[0])
            reply = f"✅ *'{text.split()[0]}' added to the whitelist.*"
    elif action == "wl_rem":
        if text:
            db.remove_whitelist(ch_id, text.split()[0])
            reply = f"✅ *'{text.split()[0]}' removed from the whitelist.*"
    elif action == "community_ban":
        parts = text.split(maxsplit=1)
        raw = parts[0] if parts else ""
        reason = parts[1] if len(parts) > 1 else "No reason provided"
        tid, tobj = None, None
        if raw.startswith('@'):
            uname = raw.lstrip('@')
            uid = db.find_user_by_username(uname)
            if uid:
                tid = uid
                tobj = db.get_user_info(uid) or SeenUser(uid, username=uname)
            else:
                try:
                    chat_obj = await ctx.bot.get_chat(f"@{uname}")
                    tid, tobj = chat_obj.id, chat_obj
                except Exception:
                    tid = None
        elif raw:
            try:
                tid = int(raw)
                tobj = db.get_user_info(tid)
            except ValueError:
                tid = None

        if tid is None:
            reply = f"❌ Can't find `{raw}`. Send a numeric user ID or @username (one the bot has seen before)."
        elif tid == ctx.bot.id or tid == OWNER_ID:
            reply = "⚠️ This user can't be banned."
        else:
            groups = db.get_community_groups(user_id)
            banned = 0
            for gid in groups:
                try:
                    if await is_adm(ctx, gid, tid):
                        continue
                    if await do_ban(ctx, gid, tid):
                        banned += 1
                    await asyncio.sleep(0.1)
                except Exception:
                    pass
            reply = (
                f"🔨 *𝗖𝗼𝗺𝗺𝘂𝗻𝗶𝘁𝘆 𝗕𝗮𝗻 𝗖𝗼𝗺𝗽𝗹𝗲𝘁𝗲*\n\n"
                f"👤 {target_name(tobj, tid)}\n"
                f"📋 Reason: _{reason}_\n"
                f"🌐 Banned from `{banned}/{len(groups)}` community group(s)."
            )

    SETTINGS_PENDING.pop(key, None)
    if reply is None:
        reply = "⚠️ Something went wrong — try /settings again."

    panel_msg_id = pending.get("panel_msg_id")
    back_rows = [[{"text": "◀️ 𝗕𝗮𝗰𝗸 𝘁𝗼 𝗦𝗲𝘁𝘁𝗶𝗻𝗴𝘀", "callback_data": "cfg_main", "style": "primary"}]]

    # Purana "type karke bhejo" prompt ab kaam ka nahi raha — usi message ko edit
    # karke confirmation dikhao, taaki ek fizool message group mein na reh jaaye.
    edited = False
    if panel_msg_id:
        ok = await edit_colored_message(ch_id, panel_msg_id, reply, back_rows, parse_mode='Markdown')
        if not ok:
            try:
                await ctx.bot.edit_message_text(
                    chat_id=ch_id, message_id=panel_msg_id,
                    text=reply, parse_mode='Markdown', reply_markup=_rows_to_markup(back_rows)
                )
                ok = True
            except Exception:
                ok = False
        if ok:
            _remember_menu_owner(ch_id, panel_msg_id, user_id)
            schedule_panel_autodelete(ctx, ch_id, panel_msg_id)
            edited = True

    if not edited:
        msg_id = await send_colored_message(ch_id, reply, back_rows, parse_mode='Markdown')
        if not msg_id:
            sent = await msg.reply_text(reply, parse_mode='Markdown', reply_markup=_rows_to_markup(back_rows))
            msg_id = sent.message_id
        _remember_menu_owner(ch_id, msg_id, user_id)
        schedule_panel_autodelete(ctx, ch_id, msg_id)

    try:
        await msg.delete()
    except Exception:
        pass
    return True


# ═══════════════════════════════════════════════════════════
#  WEB SERVER (Railway health check)
# ═══════════════════════════════════════════════════════════
web_app = Flask(__name__)

@web_app.route('/')
def home():
    return "🛡️ Guardian Bot — Online"

@web_app.route('/health')
def health():
    return "OK"

def run_web():
    port = int(os.environ.get('PORT', 8080))
    web_app.run(host='0.0.0.0', port=port, use_reloader=False)


# ═══════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════
def main():
    print("╔" + "═"*43 + "╗")
    print("║   🛡️  GUARDIAN GROUP PROTECTION BOT v9.0   ║")
    print("╠" + "═"*43 + "╣")
    print("║   ⚡ MongoDB Database Active              ║")
    print("║   👑 Immortal Users System                ║")
    print("║   🎭 Captcha Verification                 ║")
    print("║   🗑️  Sticker/Media Auto-Delete           ║")
    print("║   ⛔ Custom Blacklist/Whitelist           ║")
    print("║   🌊 Anti-Flood Protection                ║")
    print("╚" + "═"*43 + "╝")
    print(f"👑 Owner ID: {OWNER_ID}")
    print(f"🌐 Web Port: {os.environ.get('PORT', 8080)}")
    print("─" * 45)

    app = Application.builder().token(BOT_TOKEN).build()

    # ── Commands ─────────────────────────────────────────────
    app.add_handler(CommandHandler("start",            start_cmd))
    app.add_handler(CommandHandler("help",             help_cmd))
    app.add_handler(CommandHandler("rule",             rule_cmd))
    app.add_handler(CommandHandler("rules",            rule_cmd))
    app.add_handler(CommandHandler("setrules",         setrules_cmd))
    app.add_handler(CommandHandler("id",               id_cmd))
    app.add_handler(CommandHandler("setlinked",        setlinked_cmd))
    app.add_handler(CommandHandler("testmute",         testmute_cmd))
    app.add_handler(CommandHandler("mute",             mute_cmd))
    app.add_handler(CommandHandler("unmute",           unmute_cmd))
    app.add_handler(CommandHandler("ban",              ban_cmd))
    app.add_handler(CommandHandler("unban",            unban_cmd))
    app.add_handler(CommandHandler("warn",             warn_cmd))
    app.add_handler(CommandHandler("warnings",         warnings_cmd))
    app.add_handler(CommandHandler("resetwarnings",    reset_cmd))
    app.add_handler(CommandHandler("rep",              rep_cmd))
    app.add_handler(CommandHandler("repboard",         repboard_cmd))
    # ── Guardian Coin / money reward system: DISABLED (2026-08) ──
    # Reputation ab sirf warnings clear karne ke kaam aata hai, koi
    # paisa/coin conversion nahi hota. Isliye /wallet, /withdraw,
    # /accept_rep, /unaccept_rep, /earn_groups, /makeconvertible
    # commands register nahi kiye ja rahe.
    app.add_handler(CommandHandler("reputation",       reputation_cmd))
    app.add_handler(CommandHandler("del",              del_cmd))
    app.add_handler(CommandHandler("purge",            purge_cmd))
    app.add_handler(CommandHandler("immortal",         immortal_cmd))
    app.add_handler(CommandHandler("unimmortal",       unimmortal_cmd))
    app.add_handler(CommandHandler("immortals",        immortals_cmd))
    app.add_handler(CommandHandler("addblacklist",     addblacklist_cmd))
    app.add_handler(CommandHandler("removeblacklist",  removeblacklist_cmd))
    app.add_handler(CommandHandler("blacklist",        blacklist_cmd))
    app.add_handler(CommandHandler("addbioword",       addbioword_cmd))
    app.add_handler(CommandHandler("removebioword",    removebioword_cmd))
    app.add_handler(CommandHandler("biowords",         biowords_cmd))
    app.add_handler(CommandHandler("addbiodomain",     addbiodomain_cmd))
    app.add_handler(CommandHandler("removebiodomain",  removebiodomain_cmd))
    app.add_handler(CommandHandler("biodomains",       biodomains_cmd))
    app.add_handler(CommandHandler("addwhitelist",     addwhitelist_cmd))
    app.add_handler(CommandHandler("removewhitelist",  removewhitelist_cmd))
    app.add_handler(CommandHandler("whitelist",        whitelist_cmd))
    app.add_handler(CommandHandler("sticker_delete",   sticker_delete_cmd))
    app.add_handler(CommandHandler("autodelete",       autodelete_cmd))
    app.add_handler(CommandHandler("captcha",          captcha_cmd))
    app.add_handler(CommandHandler("broadcast",        broadcast_cmd))
    app.add_handler(CommandHandler("groups",           groups_cmd))
    app.add_handler(CommandHandler("regroup",          regroup_cmd))
    app.add_handler(CommandHandler("globalmutes",      globalmutes_cmd))
    app.add_handler(CommandHandler("unglobalmute",     unglobalmute_cmd))
    app.add_handler(CommandHandler("gblacklist",       gblacklist_cmd))
    app.add_handler(CommandHandler("gwhitelist",       gwhitelist_cmd))
    app.add_handler(CommandHandler("stats",            stats_cmd))
    # /rankings (message-activity leaderboard): DISABLED — isko chalu rakhne
    # ke liye har group ke har message ko scan karna padta tha, jo bade
    # groups mein bot ko slow/busy kar deta tha.
    app.add_handler(CommandHandler("power",            power_cmd))
    app.add_handler(CommandHandler("unpower",          unpower_cmd))
    app.add_handler(CommandHandler("fban",             fban_cmd))
    app.add_handler(CommandHandler("gunban",           gunban_cmd))
    app.add_handler(CommandHandler("gmute",            gmute_cmd))
    app.add_handler(CommandHandler("addcommunity",     addcommunity_cmd))
    app.add_handler(CommandHandler("removecommunity",  removecommunity_cmd))
    app.add_handler(CommandHandler("mycommunity",      mycommunity_cmd))
    app.add_handler(CommandHandler("gban",             gban_cmd))
    app.add_handler(CommandHandler("gclearwarn",       gclearwarn_cmd))
    app.add_handler(CommandHandler("adexempt",         adexempt_cmd))
    app.add_handler(CommandHandler("unadexempt",       unadexempt_cmd))
    app.add_handler(CommandHandler("premium",          premium_cmd))
    app.add_handler(CommandHandler("premium_list",      premium_list_cmd))
    app.add_handler(CommandHandler("addteacher",       addteacher_cmd))
    app.add_handler(CommandHandler("removeteacher",    removeteacher_cmd))
    app.add_handler(CommandHandler("teachers",         teachers_cmd))
    app.add_handler(CommandHandler("settings",         settings_cmd))

    # ── Callback Queries ─────────────────────────────────────
    app.add_handler(CallbackQueryHandler(cfg_callback,        pattern=r"^cfg_"))
    app.add_handler(CallbackQueryHandler(captcha_callback,    pattern=r"^captcha_"))
    app.add_handler(CallbackQueryHandler(mute_captcha_callback, pattern=r"^wcap_"))
    app.add_handler(CallbackQueryHandler(bio_recheck_callback, pattern=r"^biorecheck_"))
    app.add_handler(CallbackQueryHandler(menu_callback,       pattern=r"^(menu_|show_|unmute_|unban_|dismiss_|close_)"))
    app.add_handler(CallbackQueryHandler(rep_callback,        pattern=r"^rep:"))
    app.add_handler(CallbackQueryHandler(groups_page_callback, pattern=r"^grppg_"))
    app.add_handler(CallbackQueryHandler(premium_list_page_callback, pattern=r"^premlistpg_"))
    # rankings_callback (lbd:) aur withdraw_approval_callback (wd:) DISABLED
    # saath saath /rankings aur /withdraw feature ke — neeche dekho.

    # ── Message Handlers ─────────────────────────────────────
    # NOTE: activity tracker (message-count leaderboard) handler yahan se
    # HATA diya gaya hai — yeh pehle group=-1 pe har single group message
    # (commands samet) scan karta tha sirf /rankings leaderboard ke liye,
    # jisse bade groups mein bot busy/slow ho jaata tha. Ab yeh scan hi
    # nahi hota — bot ka load kaafi kam ho gaya hai.
    # Bot reply tracker — group ke saare messages dekho (bots ke replies track karne ke liye)
    app.add_handler(MessageHandler(
        filters.ALL & filters.ChatType.GROUPS,
        track_bot_reply
    ), group=0)
    # ── PREMIUM: Bio Guard — capture reply to "➕ Add Domain/Word" prompt ──
    # Registered in the SAME group (1) as the main message handler, and
    # BEFORE it, so PTB picks this narrowly-filtered handler first for a
    # matching reply and never runs check_msg on it (avoiding the admin's
    # domain/word text getting treated as chat content to moderate).
    app.add_handler(MessageHandler(
        filters.TEXT & filters.ChatType.GROUPS & BIO_ADD_REPLY_FILTER,
        bio_add_reply_handler
    ), group=1)
    # Main message handler
    app.add_handler(MessageHandler(
        filters.ALL & filters.ChatType.GROUPS & ~filters.COMMAND,
        check_msg
    ), group=1)
    # ── Command auto-delete (10 min) — chahe koi bhi command ho, group mein ──
    app.add_handler(MessageHandler(
        filters.COMMAND & filters.ChatType.GROUPS,
        auto_delete_commands
    ), group=2)
    # ── PREMIUM: Edit Guard — re-check messages after they're edited ──
    app.add_handler(MessageHandler(
        filters.UpdateType.EDITED_MESSAGE & filters.ChatType.GROUPS,
        on_edited_message
    ), group=3)
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, on_join))
    app.add_handler(MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER,  on_leave))

    # NOTE: daily_global_winner_job (activity-leaderboard #1 ko free rep dena)
    # DISABLED — yeh /rankings activity-tracking data pe depend karta tha,
    # jo ab scan hi nahi hota.

    print("✅ Bot Started! Polling...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    Thread(target=run_web, daemon=True).start()
    main()
