#!/usr/bin/env python3
"""
🛡️ SUHANI GROUP PROTECTION BOT - v8.0
⚡ MongoDB Persistent Database
🔗 Advanced Link Detection
✅ Linked Channel Forwards Allowed
👑 Immortal Users System
🗑️ Sticker/Media Auto Delete
📝 Custom Blacklist & Whitelist Words
🌊 Anti-Flood / Anti-Raid
🎭 Captcha Verification
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
#  WARNING MESSAGES
# ═══════════════════════════════════════════════════════════
WARN_MSG = {
    1: "🚫 **Warning 1/4**\n\nRule violation detected!\n⏱️ Muted: 35s",
    2: "😤 **Warning 2/4**\n\nStop breaking rules!\n⏱️ Muted: 60s",
    3: "🔴 **Warning 3/4 - LAST CHANCE!**\n\nNext = 1 WEEK mute in ALL groups!\n⏱️ Muted: 120s",
    4: "💀 **GLOBAL MUTE!**\n\n🗓️ 1 WEEK mute in ALL groups!\n🔐 Only admin can unmute!"
}

VIOLATION_MSG = {
    "bot":          "🤖 External bot username not allowed!",
    "url":          "🔗 Links/URLs not allowed!",
    "forward":      "↩️ Forwarded messages not allowed!",
    "adult_emoji":  "🔞 Adult emojis not allowed!",
    "adult_word":   "🚫 Inappropriate language not allowed!",
    "blacklist":    "⛔ Blacklisted word detected!",
    "flood":        "🌊 Slow down! Too many messages!",
}

MUTE_TIME  = {1: 35, 2: 60, 3: 120, 4: 604800}
WARN_EXP   = {1: 21600, 2: 57600, 3: 97200, 4: None}

# ═══════════════════════════════════════════════════════════
#  DETECTION PATTERNS
# ═══════════════════════════════════════════════════════════
BOT_RE = re.compile(r'@(\w{5,}bot)\b', re.I)

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

# Flood control: {chat_id: {user_id: [timestamps]}}
FLOOD_DATA = {}
FLOOD_LIMIT   = 5   # messages
FLOOD_WINDOW  = 8   # seconds

# Cache
CACHE     = {}
MAX_CACHE = 100

# Pending captchas: {chat_id: {user_id: {"msg_id": int, "answer": str, "expire": float}}}
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

        # Collections
        self.users    = self.db["users"]       # warnings per user per group
        self.groups   = self.db["groups"]      # group settings
        self.gmutes   = self.db["gmutes"]      # globally muted users
        self.stats_c  = self.db["stats"]       # global stats
        self.immortal = self.db["immortal"]    # immortal users per group
        self.blacklist= self.db["blacklist"]   # blacklist/whitelist per group

        # Ensure stats doc exists
        if not self.stats_c.find_one({"_id": "global"}):
            self.stats_c.insert_one({"_id": "global", "warnings": 0, "mutes": 0, "scanned": 0, "gmutes": 0})

    # ── Stats ────────────────────────────────────────────────
    def inc_stat(self, field):
        self.stats_c.update_one({"_id": "global"}, {"$inc": {field: 1}})

    def get_stats(self):
        return self.stats_c.find_one({"_id": "global"}) or {}

    # ── Groups ───────────────────────────────────────────────
    def add_group(self, chat_id):
        self.groups.update_one({"_id": chat_id}, {"$setOnInsert": {
            "_id": chat_id,
            "linked_channel": None,
            "rules": None,
            "sticker_delete_min": None,   # minutes, None = disabled
            "autodelete_min": None,        # minutes, None = disabled
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

    # ── Linked Channel ───────────────────────────────────────
    def set_linked_channel(self, chat_id, channel_id):
        self.update_group(chat_id, {"linked_channel": channel_id})

    def get_linked_channel(self, chat_id):
        g = self.get_group(chat_id)
        return g.get("linked_channel")

    # ── Warnings ─────────────────────────────────────────────
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
        # First clean expired
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

    # ── Global Mutes ─────────────────────────────────────────
    def add_gmute(self, user_id):
        self.gmutes.update_one({"_id": user_id}, {"$set": {"_id": user_id}}, upsert=True)
        self.inc_stat("gmutes")

    def is_gmuted(self, user_id):
        return self.gmutes.find_one({"_id": user_id}) is not None

    def remove_gmute(self, user_id):
        self.gmutes.delete_one({"_id": user_id})

    def get_all_gmutes(self):
        return [g["_id"] for g in self.gmutes.find()]

    # ── Immortal Users ───────────────────────────────────────
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

    # ── Blacklist / Whitelist ─────────────────────────────────
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

    # ── Custom Rules ─────────────────────────────────────────
    def set_rules(self, chat_id, text):
        self.update_group(chat_id, {"rules": text})

    def get_rules(self, chat_id):
        return self.get_group(chat_id).get("rules")


db = DB()


# ═══════════════════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════════════════
async def is_adm(ctx, chat_id, user_id):
    # 1677858391 = Telegram's "Group Anonymous Bot" ID (used when admin posts as channel)
    # Also check if sender_chat matches the group itself (anonymous admin)
    ANON_ADMIN_ID = 1087968824  # GroupAnonymousBot — Telegram ka official anonymous admin bot
    if user_id == ANON_ADMIN_ID:
        return True

    # OWNER_ID always admin
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
    """Jab channel se anonymously command aaye tab real sender detect karo."""
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
    """
    Unified admin check — channel se post karne par bhi kaam karta hai.
    GroupAnonymousBot (1087968824) = Telegram ka anonymous admin bot
    """
    ANON_BOT_ID = 1087968824
    ch   = update.effective_chat
    user = update.effective_user

    # Owner always passes
    if user and user.id == OWNER_ID:
        return True

    # GroupAnonymousBot = admin ne 'Send as group' choose kiya hai
    if user and user.id == ANON_BOT_ID:
        sc = getattr(update.message, 'sender_chat', None)
        # Agar sender_chat group hi hai toh confirmed admin
        if sc and sc.id == ch.id:
            return True
        # Channel post wala case — check linked channel
        return True  # GroupAnonymousBot = always admin in that group

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
    # Clean old
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
#  VIOLATION CHECK
# ═══════════════════════════════════════════════════════════
async def check_violations(msg, group_bots, ctx, chat_id):
    text = msg.text or msg.caption or ""

    # 1. Flood
    if check_flood(chat_id, msg.from_user.id):
        return "flood"

    # 2. Forwarded message (linked channel exception)
    if msg.forward_date or msg.forward_from or msg.forward_from_chat:
        if msg.forward_from_chat:
            lc = await fetch_linked_channel(ctx, chat_id)
            if lc and msg.forward_from_chat.id == lc:
                pass  # allowed
            else:
                return "forward"
        else:
            return "forward"

    # 3. Adult emojis (2+)
    if count_adult_emojis(text) >= 2:
        return "adult_emoji"

    # 4. Custom blacklist words (per group)
    bl_words = db.get_blacklist(chat_id)
    wl_words  = db.get_whitelist(chat_id)
    if bl_words and text:
        bl_re = build_blacklist_re(bl_words)
        if bl_re and bl_re.search(text):
            # check whitelist override
            wl_re = build_blacklist_re(wl_words) if wl_words else None
            if not (wl_re and wl_re.search(text)):
                return "blacklist"

    # 5. Default adult/bad words
    default_re = build_blacklist_re(DEFAULT_ADULT_WORDS)
    if default_re and default_re.search(text):
        return "adult_word"

    # 6. URLs/Links
    if check_link(text):
        return "url"

    # 7. External bot usernames
    found_bots = BOT_RE.findall(text)
    for b in found_bots:
        if b.lower() not in group_bots:
            return "bot"

    return None


# ═══════════════════════════════════════════════════════════
#  CAPTCHA
# ═══════════════════════════════════════════════════════════
def generate_captcha():
    """Simple math captcha"""
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
    # Generate wrong options
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
    keyboard = [
        [InlineKeyboardButton(opt, callback_data=f"captcha_{chat_id}_{user_id}_{opt}") for opt in options[:2]],
        [InlineKeyboardButton(opt, callback_data=f"captcha_{chat_id}_{user_id}_{opt}") for opt in options[2:]],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Mute until captcha solved
    await do_mute(ctx, chat_id, user_id)

    msg = await ctx.bot.send_message(
        chat_id,
        f"👋 Welcome {user_display}!\n\n"
        f"🔐 **Solve to verify you're human:**\n\n"
        f"🧮 `{question}`\n\n"
        f"⏱️ You have 60 seconds!",
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

    # Auto-kick after 60s if not solved
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
            await ctx.bot.send_message(
                chat_id,
                f"🚫 User {user_id} was kicked for failing captcha!",
                parse_mode='Markdown'
            )
        except:
            pass
        CAPTCHA_PENDING[chat_id].pop(user_id, None)


async def captcha_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data  = query.data  # captcha_{chat_id}_{user_id}_{answer}
    parts = data.split("_")
    if len(parts) < 4:
        return

    _, chat_id_s, user_id_s, chosen = parts[0], parts[1], parts[2], parts[3]
    chat_id = int(chat_id_s)
    user_id = int(user_id_s)

    # Only the correct user can answer
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
        await ctx.bot.send_message(
            chat_id,
            f"✅ Welcome! Captcha solved successfully! You can now chat.",
        )
        await query.answer("✅ Correct!")
    else:
        await query.answer("❌ Wrong answer! Try again.", show_alert=True)


# ═══════════════════════════════════════════════════════════
#  COMMANDS
# ═══════════════════════════════════════════════════════════

# ─── /start ─────────────────────────────────────────────────
async def start_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    if update.effective_chat.type != "private":
        return await update.message.reply_text("🤖 Bot Active! /help")

    is_owner = u.id == OWNER_ID
    owner_section = """
👑 Owner Only:
/broadcast <msg> — Broadcast to all groups
/groups — Total groups count
/stats — Bot statistics
/globalmutes — Global mute list count
/unglobalmute <id> — Remove global mute
""" if is_owner else ""

    text = f"""🛡️ **SUHANI GROUP PROTECTION BOT v8.0**

━━━━━━━━━━━━━━━━━━━━━

📋 **Commands:**

👤 User:
/warnings — Check warnings
/help — Help menu
/rule — Group rules
/id — Your Telegram ID

👮 Admin:
/mute [sec] — Mute user (reply)
/unmute — Unmute user (reply)
/ban — Ban user (reply)
/unban — Unban user (reply)
/warn — Give warning (reply)
/resetwarnings — Reset warnings (reply)
/del — Delete message (reply)
/purge — Delete messages from reply to now
/testmute — Test 35s mute (reply)
/setlinked — Set linked channel
/setrules <text> — Set custom group rules
/immortal <user_id> — Make user immune to rules
/unimmortal <user_id> — Remove immortal status
/immortals — List immortal users
/addblacklist <word> — Add blacklist word
/removeblacklist <word> — Remove blacklist word
/blacklist — Show blacklist words
/addwhitelist <word> — Add whitelist word
/removewhitelist <word> — Remove whitelist
/whitelist — Show whitelist
/sticker_delete <min> — Auto delete stickers/GIF/emoji (0 = off)
/autodelete <min> — Auto delete ALL messages (0 = off)
/captcha on|off — Toggle captcha for new members
{owner_section}
━━━━━━━━━━━━━━━━━━━━━

⚠️ **Warning System:**
• W1 → 35s mute (6h expire)
• W2 → 60s mute (16h expire)
• W3 → 120s mute (27h expire)
• W4 → 1 week (ALL Groups)

🛡️ **Auto Protection:**
• 🤖 External bot usernames
• 🔗 ALL Links/URLs
• ↩️ Forwards (except linked channel)
• 🔞 Adult emojis (2+)
• 🚫 Bad words (Hindi + English)
• ⛔ Custom blacklist words
• 🌊 Anti-Flood protection
• 🎭 Captcha verification (optional)
• 🗑️ Sticker/GIF auto-delete (optional)"""

    await update.message.reply_text(text, parse_mode='Markdown')


# ─── /help ──────────────────────────────────────────────────
async def help_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await start_cmd(update, ctx)


# ─── /rule ──────────────────────────────────────────────────
async def rule_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    custom = db.get_rules(chat_id)
    if custom:
        await update.message.reply_text(
            f"📜 **GROUP RULES**\n\n{custom}",
            parse_mode='Markdown'
        )
        return

    text = """📜 **GROUP RULES**

━━━━━━━━━━━━━━━━━━━━━

🚫 **NOT ALLOWED:**

1️⃣ 🤖 External bot usernames
2️⃣ 🔗 ALL Links/URLs
3️⃣ ↩️ Forwarded Messages
   ✅ Linked channel forwards allowed
4️⃣ 🔞 Adult Emojis (2+)
5️⃣ 🗣️ Bad Language
6️⃣ ⛔ Blacklisted words
7️⃣ 🌊 Flooding / Spamming

━━━━━━━━━━━━━━━━━━━━━

⚠️ **PUNISHMENT:**
• 1st → 35s mute
• 2nd → 60s mute
• 3rd → 120s mute
• 4th → 1 WEEK (ALL GROUPS)

━━━━━━━━━━━━━━━━━━━━━

✅ Follow rules & enjoy!"""
    await update.message.reply_text(text, parse_mode='Markdown')


# ─── /setrules ───────────────────────────────────────────────
async def setrules_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ch = update.effective_chat
    if ch.type == "private":
        return await update.message.reply_text("❌ Use in group!")
    if not await sender_is_admin(ctx, update):
        return await update.message.reply_text("❌ Admins only!")
    if not ctx.args:
        return await update.message.reply_text("❌ Usage: `/setrules <your rules text>`", parse_mode='Markdown')
    rules_text = ' '.join(ctx.args)
    db.set_rules(ch.id, rules_text)
    await update.message.reply_text("✅ **Custom rules saved!**\n\nUse /rule to view.", parse_mode='Markdown')


# ─── /id ────────────────────────────────────────────────────
async def id_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    ch = update.effective_chat
    target = update.message.reply_to_message.from_user if update.message.reply_to_message else u
    text = f"👤 **User Info**\n\n🆔 ID: `{target.id}`\n👤 Name: {target.first_name or ''}"
    if target.username:
        text += f"\n🔗 Username: @{target.username}"
    if ch.type != "private":
        text += f"\n\n💬 **Group ID:** `{ch.id}`"
    await update.message.reply_text(text, parse_mode='Markdown')


# ─── /immortal ──────────────────────────────────────────────
async def immortal_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ch = update.effective_chat
    user = update.effective_user
    if ch.type == "private":
        return await update.message.reply_text("❌ Use in group!")
    if not await is_adm(ctx, ch.id, user.id) and user.id != OWNER_ID:
        return await update.message.reply_text("❌ Admins only!")

    # Get target user_id from args or reply
    target_id = None
    target_name = None

    if ctx.args:
        try:
            target_id = int(ctx.args[0])
        except ValueError:
            return await update.message.reply_text("❌ Invalid user ID!\nUsage: `/immortal 1234567890`", parse_mode='Markdown')
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
        f"👑 **IMMORTAL STATUS GRANTED!**\n\n"
        f"🆔 User: `{target_id}`{f' ({target_name})' if target_name else ''}\n\n"
        f"✅ This user is now exempt from ALL group rules!\n"
        f"• Can send links, forwards, any content\n"
        f"• Bot will never act on their messages\n\n"
        f"Use `/unimmortal {target_id}` to remove.",
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
        return await update.message.reply_text("❌ Usage: `/unimmortal <user_id>`", parse_mode='Markdown')

    db.remove_immortal(ch.id, target_id)
    await update.message.reply_text(
        f"✅ Immortal status removed for `{target_id}`.",
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

    lines = [f"• `{uid}`" for uid in immortals]
    await update.message.reply_text(
        f"👑 **Immortal Users ({len(immortals)}):**\n\n" + "\n".join(lines),
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
        return await update.message.reply_text("❌ Usage: `/addblacklist <word>`", parse_mode='Markdown')

    word = ' '.join(ctx.args).lower().strip()
    db.add_blacklist(ch.id, word)
    await update.message.reply_text(
        f"⛔ **Blacklisted:** `{word}`\n\nAnyone using this word will be warned!",
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
        return await update.message.reply_text("❌ Usage: `/removeblacklist <word>`", parse_mode='Markdown')

    word = ' '.join(ctx.args).lower().strip()
    db.remove_blacklist(ch.id, word)
    await update.message.reply_text(f"✅ Removed from blacklist: `{word}`", parse_mode='Markdown')


# ─── /blacklist ─────────────────────────────────────────────
async def blacklist_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ch = update.effective_chat
    if ch.type == "private":
        return await update.message.reply_text("❌ Use in group!")
    if not await sender_is_admin(ctx, update):
        return await update.message.reply_text("❌ Admins only!")

    words = db.get_blacklist(ch.id)
    if not words:
        return await update.message.reply_text("⛔ No custom blacklist words set.\n\nUse `/addblacklist <word>` to add.", parse_mode='Markdown')
    await update.message.reply_text(
        f"⛔ **Blacklisted Words ({len(words)}):**\n\n" + "\n".join(f"• `{w}`" for w in words),
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
        return await update.message.reply_text("❌ Usage: `/addwhitelist <word>`", parse_mode='Markdown')

    word = ' '.join(ctx.args).lower().strip()
    db.add_whitelist(ch.id, word)
    await update.message.reply_text(
        f"✅ **Whitelisted:** `{word}`\n\nThis word will bypass blacklist detection.",
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
        return await update.message.reply_text("❌ Usage: `/removewhitelist <word>`", parse_mode='Markdown')

    word = ' '.join(ctx.args).lower().strip()
    db.remove_whitelist(ch.id, word)
    await update.message.reply_text(f"✅ Removed from whitelist: `{word}`", parse_mode='Markdown')


# ─── /whitelist ─────────────────────────────────────────────
async def whitelist_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ch = update.effective_chat
    if ch.type == "private":
        return await update.message.reply_text("❌ Use in group!")
    if not await sender_is_admin(ctx, update):
        return await update.message.reply_text("❌ Admins only!")

    words = db.get_whitelist(ch.id)
    if not words:
        return await update.message.reply_text("✅ No whitelist words set.", parse_mode='Markdown')
    await update.message.reply_text(
        f"✅ **Whitelisted Words ({len(words)}):**\n\n" + "\n".join(f"• `{w}`" for w in words),
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
        status = f"{cur} min" if cur else "OFF"
        return await update.message.reply_text(
            f"🗑️ **Sticker/GIF/Emoji Auto-Delete**\n\n"
            f"Current: **{status}**\n\n"
            f"Usage: `/sticker_delete 2` (2 min)\n"
            f"To disable: `/sticker_delete 0`",
            parse_mode='Markdown'
        )

    try:
        minutes = int(ctx.args[0].replace('min','').strip())
    except ValueError:
        return await update.message.reply_text("❌ Usage: `/sticker_delete 2`", parse_mode='Markdown')

    if minutes <= 0:
        db.update_group(ch.id, {"sticker_delete_min": None})
        await update.message.reply_text("✅ Sticker auto-delete **disabled**.", parse_mode='Markdown')
    else:
        db.update_group(ch.id, {"sticker_delete_min": minutes})
        await update.message.reply_text(
            f"✅ **Sticker/GIF/Emoji auto-delete enabled!**\n\n"
            f"⏱️ Stickers, GIFs, animated emojis will be deleted after **{minutes} min**.",
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
        status = f"{cur} min" if cur else "OFF"
        return await update.message.reply_text(
            f"🗑️ **Auto-Delete ALL Messages**\n\n"
            f"Current: **{status}**\n\n"
            f"Usage: `/autodelete 5` (5 min)\n"
            f"To disable: `/autodelete 0`\n\n"
            f"⚠️ This deletes EVERY message after the set time!",
            parse_mode='Markdown'
        )

    try:
        minutes = int(ctx.args[0].replace('min','').strip())
    except ValueError:
        return await update.message.reply_text("❌ Usage: `/autodelete 5`", parse_mode='Markdown')

    if minutes <= 0:
        db.update_group(ch.id, {"autodelete_min": None})
        await update.message.reply_text("✅ Auto-delete ALL messages **disabled**.", parse_mode='Markdown')
    else:
        db.update_group(ch.id, {"autodelete_min": minutes})
        await update.message.reply_text(
            f"✅ **Auto-delete ALL messages enabled!**\n\n"
            f"⏱️ Every message in this group will be deleted after **{minutes} min**.\n\n"
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
        status = "ON ✅" if g.get("captcha") else "OFF ❌"
        return await update.message.reply_text(
            f"🎭 **Captcha Verification**\n\nCurrent: **{status}**\n\nUsage: `/captcha on` or `/captcha off`",
            parse_mode='Markdown'
        )

    val = ctx.args[0].lower() == 'on'
    db.update_group(ch.id, {"captcha": val})
    state = "enabled ✅" if val else "disabled ❌"
    await update.message.reply_text(
        f"🎭 Captcha verification **{state}**!\n\n"
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
                f"✅ **Linked Channel Set!**\n\n📢 {ch_name}\n🆔 `{chat.linked_chat_id}`",
                parse_mode='Markdown'
            )
        else:
            # Manual set
            if ctx.args:
                try:
                    cid = int(ctx.args[0])
                    db.set_linked_channel(ch.id, cid)
                    await update.message.reply_text(f"✅ Linked channel set: `{cid}`", parse_mode='Markdown')
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
                await update.message.reply_text(f"✅ Linked channel set: `{cid}`", parse_mode='Markdown')
            except:
                await update.message.reply_text("❌ Invalid channel ID!")


# ─── /testmute ──────────────────────────────────────────────
async def testmute_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ch = update.effective_chat
    if ch.type == "private": return
    if not await sender_is_admin(ctx, update): return
    if not update.message.reply_to_message:
        return await update.message.reply_text("❌ Reply to user!")
    tgt = update.message.reply_to_message.from_user
    if await is_adm(ctx, ch.id, tgt.id):
        return await update.message.reply_text("❌ Can't mute admin!")
    if await do_mute(ctx, ch.id, tgt.id, 35):
        await update.message.reply_text(f"✅ {user_name(tgt)} muted 35s (test)")
    else:
        await update.message.reply_text("❌ Failed! Make bot admin!")


# ─── /mute ──────────────────────────────────────────────────
async def mute_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ch = update.effective_chat
    if ch.type == "private": return
    if not await sender_is_admin(ctx, update): return
    if not update.message.reply_to_message:
        return await update.message.reply_text("❌ Reply to user! `/mute 60`", parse_mode='Markdown')
    tgt = update.message.reply_to_message.from_user
    if await is_adm(ctx, ch.id, tgt.id):
        return await update.message.reply_text("❌ Can't mute admin!")
    sec = 35
    if ctx.args:
        try:
            sec = max(35, int(ctx.args[0]))
        except:
            pass
    if await do_mute(ctx, ch.id, tgt.id, sec):
        await update.message.reply_text(f"🔇 {user_name(tgt)} muted for {sec}s")


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
        await update.message.reply_text(f"🔊 {user_name(tgt)} unmuted!")


# ─── /ban ───────────────────────────────────────────────────
async def ban_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ch = update.effective_chat
    if ch.type == "private": return
    if not await sender_is_admin(ctx, update): return
    if not update.message.reply_to_message:
        return await update.message.reply_text("❌ Reply to user to ban!")
    tgt = update.message.reply_to_message.from_user
    if await is_adm(ctx, ch.id, tgt.id):
        return await update.message.reply_text("❌ Can't ban admin!")
    reason = ' '.join(ctx.args) if ctx.args else "No reason given"
    if await do_ban(ctx, ch.id, tgt.id):
        await update.message.reply_text(
            f"🔨 **{user_name(tgt)} has been banned!**\n📋 Reason: {reason}",
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text("❌ Failed to ban. Make bot admin!")


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
            return await update.message.reply_text("❌ Usage: `/unban <user_id>`", parse_mode='Markdown')
    elif update.message.reply_to_message:
        target_id = update.message.reply_to_message.from_user.id
    else:
        return await update.message.reply_text("❌ Reply to user or give user ID!")
    if await do_unban(ctx, ch.id, target_id):
        await update.message.reply_text(f"✅ `{target_id}` has been unbanned!", parse_mode='Markdown')


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
    msg = await update.message.reply_text(
        f"👤 {user_name(tgt)}\n\n📋 Reason: {reason}\n\n{WARN_MSG[cnt]}",
        parse_mode='Markdown'
    )
    asyncio.create_task(delete_after(ctx, ch.id, msg.message_id, 90))


# ─── /warnings ──────────────────────────────────────────────
async def warnings_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ch = update.effective_chat
    if ch.type == "private": return
    tgt = update.message.reply_to_message.from_user if update.message.reply_to_message else update.effective_user
    if db.is_gmuted(tgt.id):
        return await update.message.reply_text(
            f"👤 {user_name(tgt)}\n\n🗓️ **GLOBALLY MUTED** (1 week)",
            parse_mode='Markdown'
        )
    w = db.get_warnings(ch.id, tgt.id)
    bar = "🟥" * w + "⬜" * (4 - w)
    await update.message.reply_text(
        f"👤 {user_name(tgt)}\n📊 **{w}/4 warnings**\n{bar}",
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
    await update.message.reply_text(f"✅ {user_name(tgt)} warnings reset!")


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
        return await update.message.reply_text("❌ Reply to the message from where you want to start purge!")

    from_msg_id = update.message.reply_to_message.message_id
    to_msg_id   = update.message.message_id
    deleted = 0
    failed  = 0

    # Delete in batches
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

    msg = await ctx.bot.send_message(ch.id, f"🗑️ Purged **{deleted}** messages!", parse_mode='Markdown')
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
            await ctx.bot.send_message(gid, f"📢 {msg_text}")
            s += 1
            await asyncio.sleep(0.1)
        except:
            f += 1
    await update.message.reply_text(f"✅ Sent: {s} | ❌ Failed: {f}")


async def groups_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    groups = db.get_all_groups()
    await update.message.reply_text(f"📋 Total Groups: **{len(groups)}**", parse_mode='Markdown')


async def globalmutes_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    mutes = db.get_all_gmutes()
    await update.message.reply_text(f"🗓️ Global Mutes: **{len(mutes)}**", parse_mode='Markdown')


async def unglobalmute_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    if not ctx.args:
        return await update.message.reply_text("❌ /unglobalmute <id>")
    try:
        uid = int(ctx.args[0])
        db.remove_gmute(uid)
        await update.message.reply_text(f"✅ `{uid}` removed from global mute!", parse_mode='Markdown')
    except:
        await update.message.reply_text("❌ Invalid ID!")


async def stats_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    s = db.get_stats()
    groups = db.get_all_groups()
    gmutes = db.get_all_gmutes()
    text = f"""📊 **BOT STATISTICS**

👥 Groups: {len(groups)}
⚠️ Warnings Given: {s.get('warnings', 0)}
🔇 Mutes Done: {s.get('mutes', 0)}
📨 Messages Scanned: {s.get('scanned', 0)}
🗓️ Global Mutes: {len(gmutes)}

🛡️ Status: Active ✅
🗄️ Database: MongoDB ✅"""
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

    # Register group
    db.add_group(ch.id)

    # Skip commands
    txt = msg.text or msg.caption or ""
    if txt.startswith('/'): return

    # ── Sticker / GIF / Animated Emoji auto-delete ──────────
    g_settings = db.get_group(ch.id)
    sticker_del_min = g_settings.get("sticker_delete_min")
    autodel_min     = g_settings.get("autodelete_min")

    is_sticker_media = (
        msg.sticker or
        msg.animation or
        (msg.text and any(ord(c) > 127000 for c in txt))  # animated emoji range
    )

    if sticker_del_min and is_sticker_media:
        asyncio.create_task(delete_after(ctx, ch.id, msg.message_id, sticker_del_min * 60))

    # ── Auto-delete ALL messages ─────────────────────────────
    if autodel_min:
        asyncio.create_task(delete_after(ctx, ch.id, msg.message_id, autodel_min * 60))

    # ── Global mute check ────────────────────────────────────
    if db.is_gmuted(usr.id):
        asyncio.create_task(msg.delete())
        asyncio.create_task(do_mute(ctx, ch.id, usr.id, 604800))
        return

    # ── Admin bypass ─────────────────────────────────────────
    if await is_adm(ctx, ch.id, usr.id):
        return

    # ── Immortal user bypass ─────────────────────────────────
    if db.is_immortal(ch.id, usr.id):
        return

    db.inc_stat("scanned")

    # ── Get group bots ───────────────────────────────────────
    group_bots = await get_group_bots(ctx, ch.id)

    # ── Check violations ─────────────────────────────────────
    violation = await check_violations(msg, group_bots, ctx, ch.id)

    if violation:
        asyncio.create_task(msg.delete())
        cnt = db.add_warning(ch.id, usr.id)

        if cnt >= 4:
            await global_mute_user(ctx, usr.id, user_name(usr))
            return

        await do_mute(ctx, ch.id, usr.id, MUTE_TIME[cnt])
        viol_txt = VIOLATION_MSG.get(violation, "Rule violation!")
        notice = await ctx.bot.send_message(
            ch.id,
            f"👤 {user_name(usr)}\n\n{viol_txt}\n\n{WARN_MSG[cnt]}",
            parse_mode='Markdown'
        )
        asyncio.create_task(delete_after(ctx, ch.id, notice.message_id, 90))


# ═══════════════════════════════════════════════════════════
#  NEW MEMBER / JOIN / LEAVE EVENTS
# ═══════════════════════════════════════════════════════════
async def on_join(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    for member in update.message.new_chat_members:
        if member.id == ctx.bot.id:
            # Bot added to group
            db.add_group(update.effective_chat.id)
            try:
                chat = await ctx.bot.get_chat(update.effective_chat.id)
                if hasattr(chat, 'linked_chat_id') and chat.linked_chat_id:
                    db.set_linked_channel(update.effective_chat.id, chat.linked_chat_id)
            except:
                pass
            await update.message.reply_text(
                "🛡️ **Suhani Bot Active!**\n\n"
                "⚠️ Make me admin with Delete & Restrict permissions!\n\n"
                "🛡️ **Protection:**\n"
                "• 🤖 External bots\n"
                "• 🔗 ALL Links\n"
                "• ↩️ Forwards (except linked channel)\n"
                "• 🔞 Adult content\n"
                "• ⛔ Blacklist words\n"
                "• 🌊 Anti-flood\n"
                "• 🎭 Captcha (optional)\n\n"
                "📜 /rule | 🆔 /id | 📚 /help",
                parse_mode='Markdown'
            )
        else:
            # New human member
            g = db.get_group(update.effective_chat.id)
            if g.get("captcha"):
                asyncio.create_task(
                    send_captcha(ctx, update.effective_chat.id, member.id, user_name(member))
                )
            else:
                msg = await update.message.reply_text(
                    f"👋 Welcome {user_name(member)}!\n\n📜 Please read /rule"
                )
                asyncio.create_task(delete_after(ctx, update.effective_chat.id, msg.message_id, 30))


async def on_leave(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.message.left_chat_member.id == ctx.bot.id:
        # Remove group from DB
        pass  # Keep group data, just in case bot re-added


# ═══════════════════════════════════════════════════════════
#  WEB SERVER (Railway health check)
# ═══════════════════════════════════════════════════════════
web_app = Flask(__name__)

@web_app.route('/')
def home():
    return "🛡️ Suhani Bot v8.0 is running!"

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
    print("🛡️ Suhani Group Protection Bot v8.0")
    print("⚡ MongoDB Database")
    print("👑 Immortal Users System")
    print("🎭 Captcha Verification")
    print("🗑️ Sticker/Media Auto-Delete")
    print("⛔ Custom Blacklist/Whitelist")
    print("🌊 Anti-Flood Protection")
    print("━" * 45)
    print(f"👑 Owner ID: {OWNER_ID}")
    print(f"🌐 Web Port: {os.environ.get('PORT', 8080)}")
    print("━" * 45)

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

    # ── Message Handlers ─────────────────────────────────────
    app.add_handler(MessageHandler(
        filters.ALL & filters.ChatType.GROUPS & ~filters.COMMAND,
        check_msg
    ))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, on_join))
    app.add_handler(MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER,  on_leave))

    print("✅ Bot Started!")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    Thread(target=run_web, daemon=True).start()
    main()
