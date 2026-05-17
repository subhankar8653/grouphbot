#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════╗
║   🛡️  SUHANI GROUP PROTECTION BOT  v9.0         ║
║   ⚡  MongoDB Persistent Database                ║
║   🔗  Advanced Link Detection                    ║
║   ✅  Linked Channel Forwards Allowed            ║
║   👑  Immortal Users System                      ║
║   🗑️  Sticker/Media Auto Delete                 ║
║   📝  Custom Blacklist & Whitelist               ║
║   🌊  Anti-Flood / Anti-Raid                     ║
║   🎭  Captcha Verification                       ║
╚══════════════════════════════════════════════════╝
"""

import re, os, asyncio, time, random, string
from datetime import datetime, timedelta
from telegram import Update, ChatPermissions, ChatMember, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from threading import Thread
from flask import Flask
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

# ═══════════════════════════════════════════════════════════
#  CONFIG — Railway Environment Variables
# ═══════════════════════════════════════════════════════════
BOT_TOKEN   = os.environ.get("BOT_TOKEN", "")
OWNER_ID    = int(os.environ.get("OWNER_ID", "0"))
MONGO_URL   = os.environ.get("MONGO_URL", "mongodb://localhost:27017")

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
        "╔══ ⚠️ WARNING 1 / 4 ══╗\n"
        "║\n"
        "║  Rule violation detected!\n"
        "║  ⏱ Muted for **35 seconds**\n"
        "║\n"
        "╚══ Be careful! ══════════╝"
    ),
    2: (
        "╔══ 😤 WARNING 2 / 4 ══╗\n"
        "║\n"
        "║  Stop breaking the rules!\n"
        "║  ⏱ Muted for **60 seconds**\n"
        "║\n"
        "╚══ Last chances left: 2 ═╝"
    ),
    3: (
        "╔══ 🔴 WARNING 3 / 4 ══╗\n"
        "║\n"
        "║  ⚡ LAST CHANCE!\n"
        "║  Next = 1 WEEK mute in ALL groups!\n"
        "║  ⏱ Muted for **120 seconds**\n"
        "║\n"
        "╚══ Final Warning! ════════╝"
    ),
    4: (
        "╔══ 💀 GLOBAL MUTE ════╗\n"
        "║\n"
        "║  🗓 **1 WEEK** ban — ALL Groups!\n"
        "║  🔐 Only admin can unmute.\n"
        "║\n"
        "╚══ You crossed the line. ═╝"
    ),
}

VIOLATION_MSG = {
    "bot":          "🤖 External bot username detected!",
    "url":          "🔗 Links/URLs are not allowed here!",
    "username":     "👤 External usernames (@mentions) are not allowed here!",
    "forward":      "↩️ Forwarded messages not allowed!",
    "adult_emoji":  "🔞 Adult emojis are strictly banned!",
    "adult_word":   "🚫 Inappropriate language detected!",
    "blacklist":    "⛔ Blacklisted word used!",
    "flood":        "🌊 Slow down! Anti-flood triggered!",
}

# Usernames that are always exempt from @mention filtering
EXEMPT_USERNAMES = {"admin", "owner", "request", "sbnime"}

MUTE_TIME  = {1: 35, 2: 60, 3: 120, 4: 604800}
WARN_EXP   = {1: 21600, 2: 57600, 3: 97200, 4: None}

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

# Flood control
FLOOD_DATA = {}
FLOOD_LIMIT   = 5
FLOOD_WINDOW  = 8

CACHE     = {}
MAX_CACHE = 100

CAPTCHA_PENDING = {}

# ═══════════════════════════════════════════════════════════
#  MONGODB DATABASE
# ═══════════════════════════════════════════════════════════
class DB:
    def __init__(self):
        try:
            self.client = MongoClient(MONGO_URL, serverSelectionTimeoutMS=5000)
            self.client.admin.command('ping')
            self.db = self.client["suhanigroupbot"]
            print("✅ MongoDB Connected!")
        except ConnectionFailure as e:
            raise RuntimeError(f"❌ MongoDB connection failed: {e}")

        self.users    = self.db["users"]
        self.groups   = self.db["groups"]
        self.gmutes   = self.db["gmutes"]
        self.stats_c  = self.db["stats"]
        self.immortal = self.db["immortal"]
        self.blacklist= self.db["blacklist"]

        if not self.stats_c.find_one({"_id": "global"}):
            self.stats_c.insert_one({"_id": "global", "warnings": 0, "mutes": 0, "scanned": 0, "gmutes": 0})

    def inc_stat(self, field):
        self.stats_c.update_one({"_id": "global"}, {"$inc": {field: 1}})

    def get_stats(self):
        return self.stats_c.find_one({"_id": "global"}) or {}

    def add_group(self, chat_id):
        self.groups.update_one({"_id": chat_id}, {"$setOnInsert": {
            "_id": chat_id,
            "linked_channel": None,
            "rules": None,
            "sticker_delete_min": None,
            "autodelete_min": None,
            "captcha": False,
        }}, upsert=True)

    def remove_group(self, chat_id):
        self.groups.delete_one({"_id": chat_id})

    def get_group(self, chat_id):
        return self.groups.find_one({"_id": chat_id}) or {}

    def update_group(self, chat_id, data):
        self.groups.update_one({"_id": chat_id}, {"$set": data}, upsert=True)

    def get_all_groups(self):
        return [g["_id"] for g in self.groups.find({}, {"_id": 1})]

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
        exp = None if new_count >= 4 else now + WARN_EXP.get(new_count, 21600)
        warn_entry = {"t": now, "exp": exp}
        self.users.update_one(
            {"_id": k},
            {"$push": {"warns": warn_entry}, "$set": {"count": new_count}},
            upsert=True
        )
        self.inc_stat("warnings")
        return min(new_count, 4)

    def reset_warnings(self, chat_id, user_id):
        k = f"{chat_id}_{user_id}"
        self.users.delete_one({"_id": k})

    def add_gmute(self, user_id):
        self.gmutes.update_one({"_id": user_id}, {"$set": {"_id": user_id}}, upsert=True)
        self.inc_stat("gmutes")

    def is_gmuted(self, user_id):
        return self.gmutes.find_one({"_id": user_id}) is not None

    def remove_gmute(self, user_id):
        self.gmutes.delete_one({"_id": user_id})

    def get_all_gmutes(self):
        return [g["_id"] for g in self.gmutes.find()]

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

    def set_rules(self, chat_id, text):
        self.update_group(chat_id, {"rules": text})

    def get_rules(self, chat_id):
        return self.get_group(chat_id).get("rules")


db = DB()


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
    if k in CACHE and now - CACHE[k][1] < 300:
        return CACHE[k][0]
    try:
        m = await ctx.bot.get_chat_member(chat_id, user_id)
        r = m.status in [ChatMember.OWNER, ChatMember.ADMINISTRATOR]
        if len(CACHE) >= MAX_CACHE:
            CACHE.pop(next(iter(CACHE)))
        CACHE[k] = (r, now)
        return r
    except:
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


def user_name(u):
    try:
        return f"@{u.username}" if u.username else u.first_name or str(u.id)
    except:
        return "User"


def count_adult_emojis(text):
    return sum(text.count(e) for e in ADULT_EMOJIS)


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


async def check_username(text, wl_words, ctx, chat_id):
    """
    Returns True if text contains a @username that should be blocked.
    Exempt:
      - EXEMPT_USERNAMES (admin/owner/request/sbnime)
      - Whitelisted usernames
      - Users who are actual members of this group (not left/kicked/banned)
    """
    for match in USERNAME_RE.findall(text):
        uname = match.lower()
        # Skip permanently exempt usernames
        if uname in EXEMPT_USERNAMES:
            continue
        # Skip if admin whitelisted this username
        if wl_words and uname in [w.lower() for w in wl_words]:
            continue

        # Check if this @username is a member of the group
        is_member = False
        try:
            member = await ctx.bot.get_chat_member(chat_id, f"@{uname}")
            # Allow only active members
            if member.status in ("member", "administrator", "creator", "restricted"):
                is_member = True
        except Exception:
            # Exception = user not found in group → treat as outsider
            is_member = False

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
        await ctx.bot.ban_chat_member(chat_id, user_id)
        return True
    except:
        return False


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


async def global_mute_user(ctx, user_id, display_name=None):
    db.add_gmute(user_id)
    for gid in db.get_all_groups():
        try:
            await do_mute(ctx, gid, user_id, 604800)
            await ctx.bot.send_message(
                gid,
                f"👤 {display_name or user_id}\n\n{WARN_MSG[4]}",
                parse_mode='Markdown'
            )
            await asyncio.sleep(0.1)
        except:
            pass


# ═══════════════════════════════════════════════════════════
#  INLINE KEYBOARD BUILDERS
# ═══════════════════════════════════════════════════════════
def kb_main_menu():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("👤 User Cmds", callback_data="menu_user"),
            InlineKeyboardButton("👮 Admin Cmds", callback_data="menu_admin"),
        ],
        [
            InlineKeyboardButton("🛡️ Protections", callback_data="menu_protection"),
            InlineKeyboardButton("⚙️ Settings", callback_data="menu_settings"),
        ],
        [
            InlineKeyboardButton("⚠️ Warn System", callback_data="menu_warns"),
            InlineKeyboardButton("📊 Stats", callback_data="menu_stats"),
        ],
    ])

def kb_back():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("◀️ Back to Menu", callback_data="menu_main")]
    ])

def kb_rules():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📜 View Rules", callback_data="show_rules")],
        [InlineKeyboardButton("🆔 My ID", callback_data="show_id")],
    ])

def kb_warn_actions(chat_id, user_id):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔊 Unmute", callback_data=f"unmute_{chat_id}_{user_id}"),
            InlineKeyboardButton("🗑️ Dismiss", callback_data=f"dismiss_warn"),
        ]
    ])

def kb_unban_button(chat_id, user_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔓 Unban", callback_data=f"unban_{chat_id}_{user_id}")]
    ])

def kb_captcha(chat_id, user_id, options):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(opt, callback_data=f"captcha_{chat_id}_{user_id}_{opt}") for opt in options[:2]],
        [InlineKeyboardButton(opt, callback_data=f"captcha_{chat_id}_{user_id}_{opt}") for opt in options[2:]],
    ])

def kb_join_welcome():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📜 Rules", callback_data="show_rules"),
            InlineKeyboardButton("🆘 Help", callback_data="menu_user"),
        ]
    ])

def kb_bot_added():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📋 Commands", callback_data="menu_admin"),
            InlineKeyboardButton("⚙️ Setup", callback_data="menu_settings"),
        ],
        [
            InlineKeyboardButton("🛡️ Protections", callback_data="menu_protection"),
        ]
    ])


# ═══════════════════════════════════════════════════════════
#  VIOLATION CHECK
# ═══════════════════════════════════════════════════════════
async def check_violations(msg, group_bots, ctx, chat_id):
    text = msg.text or msg.caption or ""

    if check_flood(chat_id, msg.from_user.id):
        return "flood"

    if msg.forward_date or msg.forward_from or msg.forward_from_chat:
        if msg.forward_from_chat:
            lc = await fetch_linked_channel(ctx, chat_id)
            if lc and msg.forward_from_chat.id == lc:
                pass
            else:
                return "forward"
        else:
            return "forward"

    if count_adult_emojis(text) >= 2:
        return "adult_emoji"

    bl_words = db.get_blacklist(chat_id)
    wl_words  = db.get_whitelist(chat_id)
    if bl_words and text:
        bl_re = build_blacklist_re(bl_words)
        if bl_re and bl_re.search(text):
            wl_re = build_blacklist_re(wl_words) if wl_words else None
            if not (wl_re and wl_re.search(text)):
                return "blacklist"

    default_re = build_blacklist_re(DEFAULT_ADULT_WORDS)
    if default_re and default_re.search(text):
        return "adult_word"

    if check_link(text):
        return "url"

    if await check_username(text, wl_words, ctx, chat_id):
        return "username"

    found_bots = BOT_RE.findall(text)
    for b in found_bots:
        if b.lower() not in group_bots:
            return "bot"

    return None


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
        f"🔐 *VERIFICATION REQUIRED*\n"
        f"{'─' * 30}\n\n"
        f"👤 Welcome, {user_display}!\n\n"
        f"🧮 Solve this to join the chat:\n"
        f"┌─────────────────┐\n"
        f"│  `{question}`       │\n"
        f"└─────────────────┘\n\n"
        f"⏱ You have **60 seconds** to answer!\n"
        f"❌ Wrong answer = kick!",
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
                f"⛔ *Captcha Failed*\n\n"
                f"User `{user_id}` was kicked for not completing verification!",
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
        await query.answer("❌ This captcha is not for you!", show_alert=True)
        return

    pending = CAPTCHA_PENDING.get(chat_id, {}).get(user_id)
    if not pending:
        await query.answer("⏰ Captcha expired!", show_alert=True)
        return

    if chosen == pending["answer"]:
        CAPTCHA_PENDING[chat_id].pop(user_id, None)
        await do_unmute(ctx, chat_id, user_id)
        await query.message.delete()
        msg = await ctx.bot.send_message(
            chat_id,
            f"✅ *Verification Passed!*\n\n"
            f"Welcome to the group! You can now chat freely. 🎉",
            parse_mode='Markdown'
        )
        asyncio.create_task(delete_after(ctx, chat_id, msg.message_id, 15))
        await query.answer("✅ Correct! Welcome!")
    else:
        await query.answer("❌ Wrong answer! Try again.", show_alert=True)


# ═══════════════════════════════════════════════════════════
#  MENU CALLBACK HANDLER
# ═══════════════════════════════════════════════════════════
async def menu_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data  = query.data

    if data == "menu_main":
        text = (
            f"╔{'═'*38}╗\n"
            f"║  🛡️  *SUHANI BOT v9.0*  ⚡  ║\n"
            f"║  {'─'*36}  ║\n"
            f"║  Premium Group Protection System  ║\n"
            f"╚{'═'*38}╝\n\n"
            f"Choose a category below 👇"
        )
        await query.edit_message_text(text, reply_markup=kb_main_menu(), parse_mode='Markdown')

    elif data == "menu_user":
        text = (
            f"👤 *USER COMMANDS*\n"
            f"{'─'*30}\n\n"
            f"📌 `/warnings` — Check your warnings\n"
            f"📌 `/help` — Show help menu\n"
            f"📌 `/rule` — View group rules\n"
            f"📌 `/id` — Your Telegram ID\n\n"
            f"{'─'*30}\n"
            f"_These commands work for all members._"
        )
        await query.edit_message_text(text, reply_markup=kb_back(), parse_mode='Markdown')

    elif data == "menu_admin":
        text = (
            f"👮 *ADMIN COMMANDS*\n"
            f"{'─'*30}\n\n"
            f"🔇 `/mute [sec]` — Mute a user\n"
            f"🔊 `/unmute` — Unmute a user\n"
            f"🔨 `/ban` — Ban a user\n"
            f"🔓 `/unban <id>` — Unban a user\n"
            f"⚠️ `/warn` — Give a warning\n"
            f"♻️ `/resetwarnings` — Reset warnings\n"
            f"🗑️ `/del` — Delete replied message\n"
            f"🧹 `/purge` — Bulk delete messages\n"
            f"🧪 `/testmute` — Test 35s mute\n"
            f"👑 `/immortal <id>` — Grant immunity\n"
            f"💀 `/unimmortal <id>` — Remove immunity\n"
            f"📋 `/immortals` — List immune users\n"
        )
        await query.edit_message_text(text, reply_markup=kb_back(), parse_mode='Markdown')

    elif data == "menu_protection":
        text = (
            f"🛡️ *AUTO PROTECTIONS*\n"
            f"{'─'*30}\n\n"
            f"🤖 External bot usernames\n"
            f"👤 External @mentions (usernames)\n"
            f"   ✅ _@admin @owner @request @sbnime: exempt_\n"
            f"   ✅ _Whitelisted usernames: exempt_\n"
            f"🔗 All Links & URLs\n"
            f"↩️ Forwarded messages\n"
            f"   ✅ _(Linked channel: allowed)_\n"
            f"🔞 Adult emojis (2+ triggers)\n"
            f"🚫 Bad words — Hindi + English\n"
            f"⛔ Custom blacklist words\n"
            f"🌊 Anti-Flood system\n"
            f"🎭 Captcha for new members\n"
            f"🗑️ Sticker/GIF auto-delete\n"
        )
        await query.edit_message_text(text, reply_markup=kb_back(), parse_mode='Markdown')

    elif data == "menu_settings":
        text = (
            f"⚙️ *GROUP SETTINGS*\n"
            f"{'─'*30}\n\n"
            f"🔗 `/setlinked` — Set linked channel\n"
            f"📜 `/setrules <text>` — Set group rules\n"
            f"⛔ `/addblacklist <word>` — Add banned word\n"
            f"✅ `/addwhitelist <word>` — Whitelist word\n"
            f"📋 `/blacklist` — Show banned words\n"
            f"📋 `/whitelist` — Show allowed words\n"
            f"🗑️ `/sticker_delete <min>` — Sticker auto-del\n"
            f"⏱️ `/autodelete <min>` — Auto-delete all\n"
            f"🎭 `/captcha on|off` — Toggle captcha\n"
        )
        await query.edit_message_text(text, reply_markup=kb_back(), parse_mode='Markdown')

    elif data == "menu_warns":
        text = (
            f"⚠️ *WARNING SYSTEM*\n"
            f"{'─'*30}\n\n"
            f"🟡 *W1* → 35s mute\n"
            f"   ⏱ Expires in 6 hours\n\n"
            f"🟠 *W2* → 60s mute\n"
            f"   ⏱ Expires in 16 hours\n\n"
            f"🔴 *W3* → 120s mute\n"
            f"   ⏱ Expires in 27 hours\n\n"
            f"💀 *W4* → 1 WEEK ban\n"
            f"   🌐 Applied in ALL groups!\n"
            f"   🔐 Admin must manually unmute.\n"
        )
        await query.edit_message_text(text, reply_markup=kb_back(), parse_mode='Markdown')

    elif data == "menu_stats":
        s = db.get_stats()
        groups = db.get_all_groups()
        gmutes = db.get_all_gmutes()
        text = (
            f"📊 *BOT STATISTICS*\n"
            f"{'─'*30}\n\n"
            f"👥 Groups Active: `{len(groups)}`\n"
            f"⚠️ Warnings Given: `{s.get('warnings', 0)}`\n"
            f"🔇 Mutes Executed: `{s.get('mutes', 0)}`\n"
            f"📨 Messages Scanned: `{s.get('scanned', 0)}`\n"
            f"🗓️ Global Mutes: `{len(gmutes)}`\n\n"
            f"{'─'*30}\n"
            f"🛡️ Status: {ICON_ON} *Active*\n"
            f"🗄️ Database: {ICON_ON} *MongoDB*"
        )
        await query.edit_message_text(text, reply_markup=kb_back(), parse_mode='Markdown')

    elif data == "show_rules":
        chat_id = update.effective_chat.id if update.effective_chat else 0
        custom = db.get_rules(chat_id) if chat_id else None
        if custom:
            rules_text = (
                f"📜 *GROUP RULES*\n"
                f"{'─'*30}\n\n"
                f"{custom}\n\n"
                f"{'─'*30}\n"
                f"_Follow the rules to avoid punishment._"
            )
        else:
            rules_text = (
                f"📜 *GROUP RULES*\n"
                f"{'─'*30}\n\n"
                f"🚫 *NOT ALLOWED:*\n\n"
                f"  1️⃣  🤖 External bot usernames\n"
                f"  2️⃣  🔗 Links & URLs\n"
                f"  3️⃣  ↩️ Forwarded messages\n"
                f"       ✅ _Linked channel: allowed_\n"
                f"  4️⃣  🔞 Adult emojis (2+)\n"
                f"  5️⃣  🗣️ Abusive language\n"
                f"  6️⃣  ⛔ Blacklisted words\n"
                f"  7️⃣  🌊 Spamming / Flooding\n\n"
                f"{'─'*30}\n\n"
                f"⚠️ *PUNISHMENT SCALE:*\n"
                f"  • 1st offense → 35s mute\n"
                f"  • 2nd offense → 60s mute\n"
                f"  • 3rd offense → 120s mute\n"
                f"  • 4th offense → 1 WEEK (ALL groups!)\n\n"
                f"{'─'*30}\n"
                f"✅ _Respect the rules & enjoy the group!_"
            )
        await query.answer()
        await query.message.reply_text(rules_text, parse_mode='Markdown')
        return

    elif data == "show_id":
        u = query.from_user
        await query.answer(f"Your ID: {u.id}", show_alert=True)
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
                    await query.answer("❌ Admins only!", show_alert=True)
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
                    await do_unmute(ctx, c_id, u_id)
                    await query.answer("✅ User unmuted!", show_alert=True)
                    await query.message.edit_reply_markup(reply_markup=None)
                else:
                    await query.answer("❌ Admins only!", show_alert=True)
            except:
                await query.answer("❌ Error!", show_alert=True)
        return

    elif data == "dismiss_warn":
        if await is_adm(ctx, update.effective_chat.id if update.effective_chat else 0, query.from_user.id) or query.from_user.id == OWNER_ID:
            try:
                await query.message.delete()
            except:
                pass
        else:
            await query.answer("❌ Admins only!", show_alert=True)
        return

    await query.answer()


# ═══════════════════════════════════════════════════════════
#  COMMANDS
# ═══════════════════════════════════════════════════════════

# ─── /start ─────────────────────────────────────────────────
async def start_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    if update.effective_chat.type != "private":
        msg = await update.message.reply_text(
            f"🛡️ *Suhani Bot* is active in this group!\n"
            f"Use /help to see all commands.",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📋 Commands", callback_data="menu_admin"),
                 InlineKeyboardButton("🛡️ Protections", callback_data="menu_protection")]
            ])
        )
        return

    is_owner = u.id == OWNER_ID
    owner_badge = f"\n👑 *Owner Panel*\n`/broadcast` `/groups` `/stats` `/globalmutes`\n" if is_owner else ""

    text = (
        f"╔{'═'*38}╗\n"
        f"║  🛡️  *SUHANI GROUP BOT v9.0*      ║\n"
        f"╠{'═'*38}╣\n"
        f"║  ⚡ MongoDB  •  Anti-Flood         ║\n"
        f"║  🔗 Link Guard  •  👑 Immortal     ║\n"
        f"║  🎭 Captcha  •  🗑️ Auto Delete    ║\n"
        f"╚{'═'*38}╝\n\n"
        f"Hey {u.first_name}! 👋\n"
        f"I'm your *premium group protection bot*.\n\n"
        f"Select a category to explore commands 👇"
        f"{owner_badge}"
    )

    await update.message.reply_text(
        text,
        reply_markup=kb_main_menu(),
        parse_mode='Markdown'
    )


# ─── /help ──────────────────────────────────────────────────
async def help_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    is_group = update.effective_chat.type != "private"

    text = (
        f"🛡️ *SUHANI BOT — HELP MENU*\n"
        f"{'─'*35}\n\n"
        f"👤 *User Commands:*\n"
        f"  `/help` — This menu\n"
        f"  `/rules` — View group rules\n"
        f"  `/warnings` — Check your warnings\n"
        f"  `/id` — Your Telegram ID\n\n"
        f"👮 *Admin Commands:*\n"
        f"  `/mute [sec]` — Mute a user (reply)\n"
        f"  `/unmute` — Unmute a user (reply)\n"
        f"  `/ban [reason]` — Ban a user (reply)\n"
        f"  `/unban <id>` — Unban a user\n"
        f"  `/warn [reason]` — Warn a user (reply)\n"
        f"  `/resetwarnings` — Reset user warnings (reply)\n"
        f"  `/del` — Delete a message (reply)\n"
        f"  `/purge` — Bulk delete from message (reply)\n"
        f"  `/testmute` — Test 35s mute (reply)\n\n"
        f"👑 *Immortal System:*\n"
        f"  `/immortal <id>` — Grant rule immunity\n"
        f"  `/unimmortal <id>` — Remove immunity\n"
        f"  `/immortals` — List immune users\n\n"
        f"⚙️ *Group Settings:*\n"
        f"  `/setrules <text>` — Set custom rules\n"
        f"  `/setlinked` — Set linked channel\n"
        f"  `/captcha on|off` — Toggle captcha\n"
        f"  `/sticker_delete <min>` — Sticker auto-delete\n"
        f"  `/autodelete <min>` — Auto-delete all messages\n\n"
        f"⛔ *Blacklist / Whitelist:*\n"
        f"  `/addblacklist <word>` — Ban a word\n"
        f"  `/removeblacklist <word>` — Remove ban\n"
        f"  `/blacklist` — Show banned words\n"
        f"  `/addwhitelist <word>` — Whitelist a word\n"
        f"  `/removewhitelist <word>` — Remove whitelist\n"
        f"  `/whitelist` — Show whitelisted words\n\n"
        f"{'─'*35}\n"
        f"⚠️ *Warn Scale:* W1→35s | W2→60s | W3→120s | W4→1wk global\n"
        f"🛡️ *Auto-protection always ON for non-admins*"
    )

    await update.message.reply_text(
        text,
        parse_mode='Markdown',
        reply_markup=kb_main_menu()
    )


# ─── /rule ──────────────────────────────────────────────────
async def rule_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    custom = db.get_rules(chat_id)

    if custom:
        text = (
            f"📜 *GROUP RULES*\n"
            f"{'─'*30}\n\n"
            f"{custom}\n\n"
            f"{'─'*30}\n"
            f"_Follow the rules to avoid punishment._"
        )
    else:
        text = (
            f"📜 *GROUP RULES*\n"
            f"{'─'*30}\n\n"
            f"🚫 *NOT ALLOWED:*\n\n"
            f"  1️⃣  🤖 External bot usernames\n"
            f"  2️⃣  🔗 Links & URLs\n"
            f"  3️⃣  ↩️ Forwarded messages\n"
            f"       ✅ _Linked channel: allowed_\n"
            f"  4️⃣  🔞 Adult emojis (2+)\n"
            f"  5️⃣  🗣️ Abusive language\n"
            f"  6️⃣  ⛔ Blacklisted words\n"
            f"  7️⃣  🌊 Spamming / Flooding\n\n"
            f"{'─'*30}\n\n"
            f"⚠️ *PUNISHMENTS:*\n"
            f"  🟡 1st → 35 sec mute\n"
            f"  🟠 2nd → 60 sec mute\n"
            f"  🔴 3rd → 120 sec mute\n"
            f"  💀 4th → 1 WEEK (ALL groups!)\n\n"
            f"{'─'*30}\n"
            f"✅ _Respect the rules & enjoy!_"
        )

    await update.message.reply_text(
        text,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("⚠️ Warn System", callback_data="menu_warns")]
        ])
    )


# ─── /setrules ───────────────────────────────────────────────
async def setrules_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ch = update.effective_chat
    if ch.type == "private":
        return await update.message.reply_text("❌ Use in group!")
    if not await sender_is_admin(ctx, update):
        return await update.message.reply_text("❌ Admins only!")
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
        f"🆔 *User Information*\n"
        f"{'─'*25}\n\n"
        f"👤 Name: `{target.first_name or ''}`\n"
        f"🔑 ID: `{target.id}`\n"
    )
    if target.username:
        text += f"🔗 Username: @{target.username}\n"
    if ch.type != "private":
        text += f"\n💬 *Group ID:* `{ch.id}`"
    await update.message.reply_text(text, parse_mode='Markdown')


# ─── /immortal ──────────────────────────────────────────────
async def immortal_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ch = update.effective_chat
    user = update.effective_user
    if ch.type == "private":
        return await update.message.reply_text("❌ Use in group!")
    if not await is_adm(ctx, ch.id, user.id) and user.id != OWNER_ID:
        return await update.message.reply_text("❌ Admins only!")

    target_id = None
    target_name = None

    if ctx.args:
        try:
            target_id = int(ctx.args[0])
        except ValueError:
            return await update.message.reply_text(
                "❌ Invalid user ID!\nUsage: `/immortal 1234567890`",
                parse_mode='Markdown'
            )
    elif update.message.reply_to_message:
        target_id = update.message.reply_to_message.from_user.id
        target_name = user_name(update.message.reply_to_message.from_user)
    else:
        return await update.message.reply_text(
            "❌ Usage:\n`/immortal <user_id>`\nor reply to user message with `/immortal`",
            parse_mode='Markdown'
        )

    db.add_immortal(ch.id, target_id)
    await update.message.reply_text(
        f"👑 *IMMORTAL STATUS GRANTED*\n"
        f"{'─'*30}\n\n"
        f"🆔 User: `{target_id}`"
        f"{f'  ({target_name})' if target_name else ''}\n\n"
        f"✅ This user is now *immune* to all rules!\n"
        f"• Links, forwards, any content — allowed\n"
        f"• Bot will never act on their messages\n\n"
        f"Use `/unimmortal {target_id}` to revoke.",
        parse_mode='Markdown'
    )


# ─── /unimmortal ────────────────────────────────────────────
async def unimmortal_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ch = update.effective_chat
    user = update.effective_user
    if ch.type == "private":
        return await update.message.reply_text("❌ Use in group!")
    if not await is_adm(ctx, ch.id, user.id) and user.id != OWNER_ID:
        return await update.message.reply_text("❌ Admins only!")

    target_id = None
    if ctx.args:
        try:
            target_id = int(ctx.args[0])
        except ValueError:
            return await update.message.reply_text("❌ Invalid user ID!")
    elif update.message.reply_to_message:
        target_id = update.message.reply_to_message.from_user.id
    else:
        return await update.message.reply_text(
            "❌ Usage: `/unimmortal <user_id>`",
            parse_mode='Markdown'
        )

    db.remove_immortal(ch.id, target_id)
    await update.message.reply_text(
        f"✅ Immortal status *removed* for `{target_id}`.\n"
        f"They are now subject to group rules.",
        parse_mode='Markdown'
    )


# ─── /immortals ─────────────────────────────────────────────
async def immortals_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ch = update.effective_chat
    if ch.type == "private":
        return await update.message.reply_text("❌ Use in group!")
    if not await sender_is_admin(ctx, update):
        return await update.message.reply_text("❌ Admins only!")

    immortals = db.get_immortals(ch.id)
    if not immortals:
        return await update.message.reply_text("👑 No immortal users in this group.")

    lines = [f"  • `{uid}`" for uid in immortals]
    await update.message.reply_text(
        f"👑 *IMMORTAL USERS*\n"
        f"{'─'*25}\n\n"
        + "\n".join(lines) +
        f"\n\n_Total: {len(immortals)} user(s)_",
        parse_mode='Markdown'
    )


# ─── /addblacklist ──────────────────────────────────────────
async def addblacklist_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ch = update.effective_chat
    if ch.type == "private":
        return await update.message.reply_text("❌ Use in group!")
    if not await sender_is_admin(ctx, update):
        return await update.message.reply_text("❌ Admins only!")
    if not ctx.args:
        return await update.message.reply_text(
            "❌ Usage: `/addblacklist <word>`",
            parse_mode='Markdown'
        )
    word = ' '.join(ctx.args).lower().strip()
    db.add_blacklist(ch.id, word)
    await update.message.reply_text(
        f"⛔ *Blacklisted:* `{word}`\n\n"
        f"Anyone using this word will be *warned automatically*.",
        parse_mode='Markdown'
    )


# ─── /removeblacklist ───────────────────────────────────────
async def removeblacklist_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ch = update.effective_chat
    if ch.type == "private":
        return await update.message.reply_text("❌ Use in group!")
    if not await sender_is_admin(ctx, update):
        return await update.message.reply_text("❌ Admins only!")
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
        return await update.message.reply_text("❌ Use in group!")
    if not await sender_is_admin(ctx, update):
        return await update.message.reply_text("❌ Admins only!")

    words = db.get_blacklist(ch.id)
    if not words:
        return await update.message.reply_text(
            "⛔ No custom blacklist words set.\n\nUse `/addblacklist <word>` to add.",
            parse_mode='Markdown'
        )
    await update.message.reply_text(
        f"⛔ *BLACKLISTED WORDS* ({len(words)})\n"
        f"{'─'*25}\n\n"
        + "\n".join(f"  • `{w}`" for w in words),
        parse_mode='Markdown'
    )


# ─── /addwhitelist ──────────────────────────────────────────
async def addwhitelist_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ch = update.effective_chat
    if ch.type == "private":
        return await update.message.reply_text("❌ Use in group!")
    if not await sender_is_admin(ctx, update):
        return await update.message.reply_text("❌ Admins only!")
    if not ctx.args:
        return await update.message.reply_text(
            "❌ Usage: `/addwhitelist <word>`",
            parse_mode='Markdown'
        )
    word = ' '.join(ctx.args).lower().strip()
    db.add_whitelist(ch.id, word)
    await update.message.reply_text(
        f"✅ *Whitelisted:* `{word}`\n\n"
        f"This word will bypass blacklist detection.",
        parse_mode='Markdown'
    )


# ─── /removewhitelist ───────────────────────────────────────
async def removewhitelist_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ch = update.effective_chat
    if ch.type == "private":
        return await update.message.reply_text("❌ Use in group!")
    if not await sender_is_admin(ctx, update):
        return await update.message.reply_text("❌ Admins only!")
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
        return await update.message.reply_text("❌ Use in group!")
    if not await sender_is_admin(ctx, update):
        return await update.message.reply_text("❌ Admins only!")

    words = db.get_whitelist(ch.id)
    if not words:
        return await update.message.reply_text(
            "✅ No whitelist words set.",
            parse_mode='Markdown'
        )
    await update.message.reply_text(
        f"✅ *WHITELISTED WORDS* ({len(words)})\n"
        f"{'─'*25}\n\n"
        + "\n".join(f"  • `{w}`" for w in words),
        parse_mode='Markdown'
    )


# ─── /sticker_delete ────────────────────────────────────────
async def sticker_delete_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ch = update.effective_chat
    if ch.type == "private":
        return await update.message.reply_text("❌ Use in group!")
    if not await sender_is_admin(ctx, update):
        return await update.message.reply_text("❌ Admins only!")

    if not ctx.args:
        g = db.get_group(ch.id)
        cur = g.get("sticker_delete_min")
        status = f"{ICON_ON} {cur} min" if cur else f"{ICON_OFF} OFF"
        return await update.message.reply_text(
            f"🗑️ *Sticker / GIF Auto-Delete*\n"
            f"{'─'*30}\n\n"
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
    ch = update.effective_chat
    if ch.type == "private":
        return await update.message.reply_text("❌ Use in group!")
    if not await sender_is_admin(ctx, update):
        return await update.message.reply_text("❌ Admins only!")

    if not ctx.args:
        g = db.get_group(ch.id)
        cur = g.get("autodelete_min")
        status = f"{ICON_ON} {cur} min" if cur else f"{ICON_OFF} OFF"
        return await update.message.reply_text(
            f"🗑️ *Auto-Delete ALL Messages*\n"
            f"{'─'*30}\n\n"
            f"Status: {status}\n\n"
            f"Usage: `/autodelete 5` → enable (5 min)\n"
            f"Disable: `/autodelete 0`\n\n"
            f"⚠️ This deletes EVERY message!",
            parse_mode='Markdown'
        )

    try:
        minutes = int(ctx.args[0].replace('min','').strip())
    except ValueError:
        return await update.message.reply_text(
            "❌ Usage: `/autodelete 5`",
            parse_mode='Markdown'
        )

    if minutes <= 0:
        db.update_group(ch.id, {"autodelete_min": None})
        await update.message.reply_text(
            f"✅ Auto-delete *disabled*.",
            parse_mode='Markdown'
        )
    else:
        db.update_group(ch.id, {"autodelete_min": minutes})
        await update.message.reply_text(
            f"✅ *Auto-delete ALL messages enabled!*\n\n"
            f"⏱ Every message will be deleted after *{minutes} min*.\n"
            f"⚠️ This keeps the group completely clean!",
            parse_mode='Markdown'
        )


# ─── /captcha ───────────────────────────────────────────────
async def captcha_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ch = update.effective_chat
    if ch.type == "private":
        return await update.message.reply_text("❌ Use in group!")
    if not await sender_is_admin(ctx, update):
        return await update.message.reply_text("❌ Admins only!")

    if not ctx.args or ctx.args[0].lower() not in ('on', 'off'):
        g = db.get_group(ch.id)
        status = f"{ICON_ON} ON" if g.get("captcha") else f"{ICON_OFF} OFF"
        return await update.message.reply_text(
            f"🎭 *Captcha Verification*\n"
            f"{'─'*25}\n\n"
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
        return await update.message.reply_text("❌ Use in group!")
    if not await sender_is_admin(ctx, update):
        return await update.message.reply_text("❌ Admins only!")

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
    if not update.message.reply_to_message:
        return await update.message.reply_text("❌ Reply to a user!")
    tgt = update.message.reply_to_message.from_user
    if await is_adm(ctx, ch.id, tgt.id):
        return await update.message.reply_text("❌ Can't mute an admin!")
    if await do_mute(ctx, ch.id, tgt.id, 35):
        await update.message.reply_text(
            f"🧪 *Test Mute Applied*\n\n"
            f"👤 {user_name(tgt)} — muted for *35 seconds*.",
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text("❌ Failed! Make sure bot has admin rights.")


# ─── /mute ──────────────────────────────────────────────────
async def mute_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ch = update.effective_chat
    if ch.type == "private": return
    if not await sender_is_admin(ctx, update): return
    if not update.message.reply_to_message:
        return await update.message.reply_text(
            "❌ Reply to a user!\nUsage: `/mute 60`",
            parse_mode='Markdown'
        )
    tgt = update.message.reply_to_message.from_user
    if await is_adm(ctx, ch.id, tgt.id):
        return await update.message.reply_text("❌ Can't mute an admin!")
    sec = 35
    if ctx.args:
        try:
            sec = max(35, int(ctx.args[0]))
        except:
            pass
    if await do_mute(ctx, ch.id, tgt.id, sec):
        await update.message.reply_text(
            f"🔇 *Muted!*\n\n"
            f"👤 {user_name(tgt)}\n"
            f"⏱ Duration: *{sec} seconds*",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔊 Unmute", callback_data=f"unmute_{ch.id}_{tgt.id}")]
            ])
        )


# ─── /unmute ────────────────────────────────────────────────
async def unmute_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ch = update.effective_chat
    if ch.type == "private": return
    if not await sender_is_admin(ctx, update): return
    if not update.message.reply_to_message: return
    tgt = update.message.reply_to_message.from_user
    db.remove_gmute(tgt.id)
    if await do_unmute(ctx, ch.id, tgt.id):
        db.reset_warnings(ch.id, tgt.id)
        await update.message.reply_text(
            f"🔊 *Unmuted!*\n\n👤 {user_name(tgt)} can now send messages.",
            parse_mode='Markdown'
        )


# ─── /ban ───────────────────────────────────────────────────
async def ban_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ch = update.effective_chat
    if ch.type == "private": return
    if not await sender_is_admin(ctx, update): return
    if not update.message.reply_to_message:
        return await update.message.reply_text("❌ Reply to a user to ban!")
    tgt = update.message.reply_to_message.from_user
    if await is_adm(ctx, ch.id, tgt.id):
        return await update.message.reply_text("❌ Can't ban an admin!")
    reason = ' '.join(ctx.args) if ctx.args else "No reason provided"
    if await do_ban(ctx, ch.id, tgt.id):
        await update.message.reply_text(
            f"🔨 *User Banned!*\n"
            f"{'─'*25}\n\n"
            f"👤 {user_name(tgt)}\n"
            f"📋 Reason: _{reason}_",
            parse_mode='Markdown',
            reply_markup=kb_unban_button(ch.id, tgt.id)
        )
    else:
        await update.message.reply_text("❌ Failed to ban. Make bot an admin!")


# ─── /unban ─────────────────────────────────────────────────
async def unban_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ch = update.effective_chat
    if ch.type == "private": return
    if not await sender_is_admin(ctx, update): return
    target_id = None
    if ctx.args:
        try:
            target_id = int(ctx.args[0])
        except:
            return await update.message.reply_text(
                "❌ Usage: `/unban <user_id>`",
                parse_mode='Markdown'
            )
    elif update.message.reply_to_message:
        target_id = update.message.reply_to_message.from_user.id
    else:
        return await update.message.reply_text("❌ Reply to user or provide user ID!")
    if await do_unban(ctx, ch.id, target_id):
        await update.message.reply_text(
            f"✅ `{target_id}` has been *unbanned!*",
            parse_mode='Markdown'
        )


# ─── /warn ──────────────────────────────────────────────────
async def warn_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ch = update.effective_chat
    if ch.type == "private": return
    if not await sender_is_admin(ctx, update): return
    if not update.message.reply_to_message: return
    tgt = update.message.reply_to_message.from_user
    if await is_adm(ctx, ch.id, tgt.id): return
    reason = ' '.join(ctx.args) if ctx.args else "Rule violation"
    cnt = db.add_warning(ch.id, tgt.id)
    if cnt >= 4:
        await global_mute_user(ctx, tgt.id, user_name(tgt))
        return
    await do_mute(ctx, ch.id, tgt.id, MUTE_TIME[cnt])

    # Build warning bar
    bars = "🟥" * cnt + "⬜" * (4 - cnt)
    msg = await update.message.reply_text(
        f"⚠️ *WARNING ISSUED*\n"
        f"{'─'*25}\n\n"
        f"👤 {user_name(tgt)}\n"
        f"📋 Reason: _{reason}_\n\n"
        f"Progress: {bars} `{cnt}/4`\n\n"
        f"{WARN_MSG[cnt]}",
        parse_mode='Markdown',
        reply_markup=kb_warn_actions(ch.id, tgt.id)
    )
    asyncio.create_task(delete_after(ctx, ch.id, msg.message_id, 90))


# ─── /warnings ──────────────────────────────────────────────
async def warnings_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ch = update.effective_chat
    if ch.type == "private": return
    tgt = update.message.reply_to_message.from_user if update.message.reply_to_message else update.effective_user
    if db.is_gmuted(tgt.id):
        return await update.message.reply_text(
            f"👤 {user_name(tgt)}\n\n"
            f"💀 *GLOBALLY MUTED* — 1 week ban active.",
            parse_mode='Markdown'
        )
    w = db.get_warnings(ch.id, tgt.id)
    bars = "🟥" * w + "⬜" * (4 - w)
    await update.message.reply_text(
        f"📊 *Warning Status*\n"
        f"{'─'*20}\n\n"
        f"👤 {user_name(tgt)}\n"
        f"Count: `{w}/4`\n"
        f"Scale: {bars}",
        parse_mode='Markdown'
    )


# ─── /resetwarnings ─────────────────────────────────────────
async def reset_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ch = update.effective_chat
    if ch.type == "private": return
    if not await sender_is_admin(ctx, update): return
    if not update.message.reply_to_message: return
    tgt = update.message.reply_to_message.from_user
    db.reset_warnings(ch.id, tgt.id)
    await update.message.reply_text(
        f"✅ *Warnings reset!*\n\n👤 {user_name(tgt)} now has 0 warnings.",
        parse_mode='Markdown'
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
        return await update.message.reply_text("❌ Admins only!")
    if not update.message.reply_to_message:
        return await update.message.reply_text("❌ Reply to the starting message!")

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
        f"🧹 *Purge Complete!*\n\n"
        f"🗑️ Deleted: `{deleted}` messages\n"
        f"⚠️ Skipped: `{failed}` messages",
        parse_mode='Markdown'
    )
    asyncio.create_task(delete_after(ctx, ch.id, msg.message_id, 5))


# ─── Owner Commands ──────────────────────────────────────────
async def broadcast_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    if not ctx.args:
        return await update.message.reply_text("❌ /broadcast <msg>")
    msg_text = ' '.join(ctx.args)
    s = f = 0
    for gid in db.get_all_groups():
        try:
            await ctx.bot.send_message(
                gid,
                f"📢 *BROADCAST*\n{'─'*20}\n\n{msg_text}",
                parse_mode='Markdown'
            )
            s += 1
            await asyncio.sleep(0.1)
        except:
            f += 1
    await update.message.reply_text(
        f"📢 *Broadcast Complete!*\n\n"
        f"✅ Sent: `{s}`\n❌ Failed: `{f}`",
        parse_mode='Markdown'
    )


async def groups_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    groups = db.get_all_groups()
    await update.message.reply_text(
        f"👥 *Active Groups:* `{len(groups)}`",
        parse_mode='Markdown'
    )


async def globalmutes_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    mutes = db.get_all_gmutes()
    await update.message.reply_text(
        f"🗓️ *Global Mutes:* `{len(mutes)}`",
        parse_mode='Markdown'
    )


async def unglobalmute_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    if not ctx.args:
        return await update.message.reply_text("❌ /unglobalmute <id>")
    try:
        uid = int(ctx.args[0])
        db.remove_gmute(uid)
        await update.message.reply_text(
            f"✅ `{uid}` removed from global mute!",
            parse_mode='Markdown'
        )
    except:
        await update.message.reply_text("❌ Invalid ID!")


async def stats_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    s = db.get_stats()
    groups = db.get_all_groups()
    gmutes = db.get_all_gmutes()
    text = (
        f"📊 *BOT STATISTICS*\n"
        f"{'═'*30}\n\n"
        f"👥  Groups Active:       `{len(groups)}`\n"
        f"⚠️  Warnings Given:     `{s.get('warnings', 0)}`\n"
        f"🔇  Mutes Executed:     `{s.get('mutes', 0)}`\n"
        f"📨  Messages Scanned:   `{s.get('scanned', 0)}`\n"
        f"🗓️  Global Mutes:       `{len(gmutes)}`\n\n"
        f"{'─'*30}\n"
        f"🛡️ Status:  {ICON_ON} *Active*\n"
        f"🗄️ Database: {ICON_ON} *MongoDB Connected*"
    )
    await update.message.reply_text(text, parse_mode='Markdown')


# ═══════════════════════════════════════════════════════════
#  MAIN MESSAGE HANDLER
# ═══════════════════════════════════════════════════════════
async def check_msg(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg: return

    ch  = update.effective_chat
    usr = update.effective_user

    if ch.type == "private": return

    db.add_group(ch.id)

    txt = msg.text or msg.caption or ""
    if txt.startswith('/'): return

    g_settings = db.get_group(ch.id)
    sticker_del_min = g_settings.get("sticker_delete_min")
    autodel_min     = g_settings.get("autodelete_min")

    is_sticker_media = (
        msg.sticker or
        msg.animation or
        (msg.text and any(ord(c) > 127000 for c in txt))
    )

    if db.is_gmuted(usr.id):
        asyncio.create_task(msg.delete())
        asyncio.create_task(do_mute(ctx, ch.id, usr.id, 604800))
        return

    is_admin = await is_adm(ctx, ch.id, usr.id)

    # Sticker auto-delete: admin pe bhi lagega
    if sticker_del_min and is_sticker_media:
        asyncio.create_task(delete_after(ctx, ch.id, msg.message_id, sticker_del_min * 60))

    # Global autodelete: admin ke NORMAL messages pe nahi lagega
    if autodel_min and not is_admin:
        asyncio.create_task(delete_after(ctx, ch.id, msg.message_id, autodel_min * 60))

    # Admin ke violations (link/username/etc.) check hote rahenge
    # Sirf is_adm wala early return hata diya — ab admin bhi violation check se guzrega
    if db.is_immortal(ch.id, usr.id):
        return

    db.inc_stat("scanned")

    group_bots = await get_group_bots(ctx, ch.id)
    violation = await check_violations(msg, group_bots, ctx, ch.id)

    if violation:
        asyncio.create_task(msg.delete())
        cnt = db.add_warning(ch.id, usr.id)

        if cnt >= 4:
            await global_mute_user(ctx, usr.id, user_name(usr))
            return

        await do_mute(ctx, ch.id, usr.id, MUTE_TIME[cnt])
        viol_txt = VIOLATION_MSG.get(violation, "Rule violation!")
        bars = "🟥" * cnt + "⬜" * (4 - cnt)
        mute_sec = MUTE_TIME[cnt]
        mute_str = f"{mute_sec}s" if mute_sec < 3600 else "1 week"
        next_str = "1 week ban 🌐" if cnt == 3 else f"W{cnt+1}"

        notice = await ctx.bot.send_message(
            ch.id,
            f"🚨 *{user_name(usr)}* warned! `(W{cnt}/4)`\n"
            f"📌 {viol_txt}\n"
            f"⏱ Muted `{mute_str}` • Next = {next_str}\n\n"
            f"Progress: {bars} `{cnt}/4`",
            parse_mode='Markdown',
            reply_markup=kb_warn_actions(ch.id, usr.id)
        )
        asyncio.create_task(delete_after(ctx, ch.id, notice.message_id, 90))


# ═══════════════════════════════════════════════════════════
#  NEW MEMBER / JOIN / LEAVE EVENTS
# ═══════════════════════════════════════════════════════════
async def on_join(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    for member in update.message.new_chat_members:
        if member.id == ctx.bot.id:
            db.add_group(update.effective_chat.id)
            try:
                chat = await ctx.bot.get_chat(update.effective_chat.id)
                if hasattr(chat, 'linked_chat_id') and chat.linked_chat_id:
                    db.set_linked_channel(update.effective_chat.id, chat.linked_chat_id)
            except:
                pass
            await update.message.reply_text(
                f"╔{'═'*38}╗\n"
                f"║  🛡️  *SUHANI BOT ACTIVATED!*      ║\n"
                f"╚{'═'*38}╝\n\n"
                f"⚡ I'm now protecting this group!\n\n"
                f"📋 *Please give me admin rights with:*\n"
                f"  • Delete Messages\n"
                f"  • Restrict Members\n\n"
                f"{'─'*38}\n\n"
                f"🛡️ *Auto Protection Active:*\n"
                f"  🤖 External bots\n"
                f"  🔗 ALL Links & URLs\n"
                f"  ↩️ Forwarded messages\n"
                f"  🔞 Adult content\n"
                f"  ⛔ Blacklist words\n"
                f"  🌊 Anti-Flood\n"
                f"  🎭 Captcha _(optional)_\n\n"
                f"Use /help to see all commands!",
                parse_mode='Markdown',
                reply_markup=kb_bot_added()
            )
        else:
            g = db.get_group(update.effective_chat.id)
            if g.get("captcha"):
                asyncio.create_task(
                    send_captcha(ctx, update.effective_chat.id, member.id, user_name(member))
                )
            else:
                msg = await update.message.reply_text(
                    f"👋 *Welcome!*\n\n"
                    f"Hey {user_name(member)}, glad to have you here!\n"
                    f"Please read the group rules below. 👇",
                    parse_mode='Markdown',
                    reply_markup=kb_join_welcome()
                )
                asyncio.create_task(
                    delete_after(ctx, update.effective_chat.id, msg.message_id, 30)
                )


async def on_leave(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.message.left_chat_member.id == ctx.bot.id:
        pass


# ═══════════════════════════════════════════════════════════
#  WEB SERVER (Railway health check)
# ═══════════════════════════════════════════════════════════
web_app = Flask(__name__)

@web_app.route('/')
def home():
    return "🛡️ Suhani Bot v9.0 — Active!"

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
    print("║   🛡️  SUHANI GROUP PROTECTION BOT v9.0   ║")
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
    app.add_handler(CommandHandler("del",              del_cmd))
    app.add_handler(CommandHandler("purge",            purge_cmd))
    app.add_handler(CommandHandler("immortal",         immortal_cmd))
    app.add_handler(CommandHandler("unimmortal",       unimmortal_cmd))
    app.add_handler(CommandHandler("immortals",        immortals_cmd))
    app.add_handler(CommandHandler("addblacklist",     addblacklist_cmd))
    app.add_handler(CommandHandler("removeblacklist",  removeblacklist_cmd))
    app.add_handler(CommandHandler("blacklist",        blacklist_cmd))
    app.add_handler(CommandHandler("addwhitelist",     addwhitelist_cmd))
    app.add_handler(CommandHandler("removewhitelist",  removewhitelist_cmd))
    app.add_handler(CommandHandler("whitelist",        whitelist_cmd))
    app.add_handler(CommandHandler("sticker_delete",   sticker_delete_cmd))
    app.add_handler(CommandHandler("autodelete",       autodelete_cmd))
    app.add_handler(CommandHandler("captcha",          captcha_cmd))
    app.add_handler(CommandHandler("broadcast",        broadcast_cmd))
    app.add_handler(CommandHandler("groups",           groups_cmd))
    app.add_handler(CommandHandler("globalmutes",      globalmutes_cmd))
    app.add_handler(CommandHandler("unglobalmute",     unglobalmute_cmd))
    app.add_handler(CommandHandler("stats",            stats_cmd))

    # ── Callback Queries ─────────────────────────────────────
    app.add_handler(CallbackQueryHandler(captcha_callback, pattern=r"^captcha_"))
    app.add_handler(CallbackQueryHandler(menu_callback,    pattern=r"^(menu_|show_|unmute_|unban_|dismiss_)"))

    # ── Message Handlers ─────────────────────────────────────
    app.add_handler(MessageHandler(
        filters.ALL & filters.ChatType.GROUPS & ~filters.COMMAND,
        check_msg
    ))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, on_join))
    app.add_handler(MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER,  on_leave))

    print("✅ Bot Started! Polling...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    Thread(target=run_web, daemon=True).start()
    main()
