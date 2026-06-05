#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════╗
║   🛡️  SUHANI GROUP PROTECTION BOT  v10.0        ║
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
"""

import re, os, asyncio, time, random, string, json
from datetime import datetime, timedelta
from telegram import Update, ChatPermissions, ChatMember, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from threading import Thread
from flask import Flask
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
import aiohttp

# ═══════════════════════════════════════════════════════════
#  CONFIG — Railway Environment Variables
# ═══════════════════════════════════════════════════════════
BOT_TOKEN        = os.environ.get("BOT_TOKEN", "")
OWNER_ID         = int(os.environ.get("OWNER_ID", "0"))
MONGO_URL        = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
AI_API_KEY       = os.environ.get("AI_API_KEY", "")   # optional — AI moderation

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
    "stylish_font": "✍️ Stylish/fancy fonts are NOT allowed in this group!",
    "hidden_link":  "🔗 Hidden links in text are NOT allowed here!",
    "ai_promo":     "🤖 AI detected promotional/spam content!",
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

# Flood control
FLOOD_DATA = {}
FLOOD_LIMIT   = 5
FLOOD_WINDOW  = 8

CACHE     = {}
MAX_CACHE = 100

CAPTCHA_PENDING = {}

# ═══════════════════════════════════════════════════════════
#  AI ENGINE — Groq (llama-3.1-8b-instant)
# ═══════════════════════════════════════════════════════════

AI_COOLDOWN: dict[int, float] = {}
AI_COOLDOWN_SEC = 45   # per-user cooldown seconds

# Per-chat repeat tracker: {chat_id: {user_id: {text: count}}}
REPEAT_TRACKER: dict[int, dict[int, dict[str, int]]] = {}

_AI_SESSION: aiohttp.ClientSession | None = None

async def get_ai_session() -> aiohttp.ClientSession:
    global _AI_SESSION
    if _AI_SESSION is None or _AI_SESSION.closed:
        _AI_SESSION = aiohttp.ClientSession()
    return _AI_SESSION

# ── Popular anime names — AI check se exempt ────────────────
ANIME_NAMES = {
    "naruto","boruto","bleach","onepiece","one piece","dragonball","dragon ball",
    "attackontitan","attack on titan","aot","demonslayer","demon slayer","kimetsu",
    "mha","myheroacademia","my hero academia","jujutsukaisen","jujutsu kaisen","jjk",
    "fullmetal","fullmetal alchemist","fma","tokyoghoul","tokyo ghoul","sao",
    "swordartonline","sword art online","blackclover","black clover","fairytail",
    "fairy tail","hunterxhunter","hunter x hunter","hxh","deathnote","death note",
    "onepunchman","one punch man","opm","rezero","re zero","re:zero","overlord",
    "noragami","vinlandSaga","vinland saga","chainsawman","chainsaw man","csm",
    "spy x family","spyxfamily","bocchi","bocchitherocket","bocchi the rock",
    "bluelock","blue lock","tokyorevengers","tokyo revengers","acecombat",
    "neongenesisevangelion","evangelion","eva","cowboybebop","cowboy bebop",
    "steinsgate","steins gate","steins;gate","gurrenlagann","gurren lagann",
    "madoka","puellamamadoka","codegeass","code geass","kaguya","kaguyasama",
    "shimoneta","oregairu","monogatari","haikyuu","kuroko","kuroko no basket",
    "aonoexorcist","ao no exorcist","blueexorcist","blue exorcist","inuyasha",
    "ranma","drslump","toriko","yu-gi-oh","yugioh","beyblade","digimon",
    "pokemon","pokémon","sailor moon","sailormoon","cardcaptorsakura","cardcaptor",
    "dbs","super","dragonballsuper","dragonballz","dbz","toaru","toarumajutsu",
    "noblesse","tower of god","towerofgod","solo leveling","sololeveling","sl",
    "omniscient reader","omniscientreader","orv","a returners magic","returner",
    "mushokutensei","mushoku tensei","tensura","tenseishitara slime","slime",
    "konosuba","megumin","aqua","darkness","rezero","subaru","emilia","rem","ram",
    "shield hero","shieldhero","tatenoYusha","rising shield hero","rising of the shield hero",
}

def is_anime_message(text: str) -> bool:
    """Return True if message is mainly just an anime name — skip AI check."""
    clean = text.lower().strip()
    # Short message (<=30 chars) containing a known anime name
    if len(clean) <= 30:
        for name in ANIME_NAMES:
            if name in clean:
                return True
    return False

# ── Suhani system prompt ────────────────────────────────────
SUHANI_SYSTEM = """You are Suhani, a friendly Telegram group protection bot.

Your identity:
- Name: Suhani
- Created by: Lucky
- Owner/Partners: @Suhanibots and @sbanime
- You are a group protection bot AND an anime lover
- You speak in Hinglish (Hindi + English mix) naturally, like a desi friend

Your personality:
- Friendly, helpful, slightly playful
- Anime enthusiast — you know and love anime deeply
- You help people who are confused or in trouble
- You keep responses SHORT (2-4 lines max) — this is a chat, not an essay

What you do:
1. MODERATION: Detect if a message is promotional spam
2. ANIME: Answer anime questions enthusiastically
3. HELP: Help users who seem confused or ask questions
4. IDENTITY: Answer questions about who you are

When asked about your AI/technology — NEVER mention Groq, LLaMA, or any AI company. Say you are Suhani, made by Lucky.

Response format — you must ALWAYS respond with JSON only:
{
  "action": "PROMO" | "SAFE" | "REPLY",
  "reply": "your message here (only if action is REPLY, else empty string)"
}

action meanings:
- PROMO: message is promotional/spam/advertising → will be deleted + warned
- SAFE: normal message, ignore it
- REPLY: message needs a response (question, anime topic, help needed, confusion, same anime name repeated)

For REPLY, write in Hinglish, keep it short and friendly."""

async def ai_check(text: str, user_id: int, chat_id: int, username: str = "") -> dict:
    """
    Returns dict: {"action": "PROMO"/"SAFE"/"REPLY", "reply": "..."}
    Uses Groq API (llama-3.1-8b-instant).
    """
    if not AI_API_KEY:
        return {"action": "SAFE", "reply": ""}

    if not text or len(text.strip()) < 3:
        return {"action": "SAFE", "reply": ""}

    # Anime-only message — skip AI entirely
    if is_anime_message(text):
        # But still check repeat
        return {"action": "SAFE", "reply": ""}

    # Cooldown check
    now = time.time()
    last = AI_COOLDOWN.get(user_id, 0)
    if now - last < AI_COOLDOWN_SEC:
        return {"action": "SAFE", "reply": ""}
    AI_COOLDOWN[user_id] = now

    try:
        session = await get_ai_session()
        payload = {
            "model": "llama-3.1-8b-instant",
            "max_tokens": 120,
            "temperature": 0.3,
            "messages": [
                {"role": "system", "content": SUHANI_SYSTEM},
                {"role": "user", "content": text[:600]}
            ],
            "response_format": {"type": "json_object"}
        }
        async with session.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {AI_API_KEY}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=aiohttp.ClientTimeout(total=6)
        ) as resp:
            if resp.status != 200:
                return {"action": "SAFE", "reply": ""}
            data = await resp.json()
            raw = data["choices"][0]["message"]["content"].strip()
            result = json.loads(raw)
            action = result.get("action", "SAFE").upper()
            if action not in ("PROMO", "SAFE", "REPLY"):
                action = "SAFE"
            return {"action": action, "reply": result.get("reply", "")}
    except Exception:
        return {"action": "SAFE", "reply": ""}

# ── Repeat message tracker ───────────────────────────────────
def track_repeat(chat_id: int, user_id: int, text: str) -> int:
    """Returns how many times this user sent same/similar text in this chat."""
    clean = text.lower().strip()[:60]
    if chat_id not in REPEAT_TRACKER:
        REPEAT_TRACKER[chat_id] = {}
    if user_id not in REPEAT_TRACKER[chat_id]:
        REPEAT_TRACKER[chat_id][user_id] = {}
    tracker = REPEAT_TRACKER[chat_id][user_id]
    tracker[clean] = tracker.get(clean, 0) + 1
    # cleanup old keys if too many
    if len(tracker) > 20:
        oldest = list(tracker.keys())[0]
        del tracker[oldest]
    return tracker[clean]

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
        self.gblacklist = self.db["global_blacklist"]
        self.fbans    = self.db["fbans"]          # fban list
        self.powered  = self.db["powered_users"]  # users with /fban power
        self.ad_exempt = self.db["autodel_exempt"] # bots exempt from autodelete

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
            "aimod": True,    # AI moderation default ON (kaam tabhi karega jab API key ho)
        }}, upsert=True)

    def remove_group(self, chat_id):
        self.groups.delete_one({"_id": chat_id})

    def get_group(self, chat_id):
        return self.groups.find_one({"_id": chat_id}) or {}

    def update_group(self, chat_id, data):
        self.groups.update_one({"_id": chat_id}, {"$set": data}, upsert=True)

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

    if not msg.from_user:
        return None

    if check_flood(chat_id, msg.from_user.id):
        return "flood"

    # Hidden link check (text_link entity)
    if has_hidden_link(msg):
        return "hidden_link"

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

    # Global blacklist — applies to ALL groups
    gbl_words = db.get_gblacklist()
    if gbl_words and text:
        gbl_re = build_blacklist_re(gbl_words)
        if gbl_re and gbl_re.search(text):
            # Check global whitelist before blocking
            gwl_words = db.get_gwhitelist()
            gwl_re = build_blacklist_re(gwl_words) if gwl_words else None
            if not (gwl_re and gwl_re.search(text)):
                return "blacklist"

    default_re = build_blacklist_re(DEFAULT_ADULT_WORDS)
    if default_re and default_re.search(text):
        return "adult_word"

    # Stylish/fancy font check
    if text and has_stylish_font(text):
        return "stylish_font"

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
            f"🛡️ *SUHANI BOT v10.0*\n\n"
            f"Choose a category below 👇"
        )
        await query.edit_message_text(text, reply_markup=kb_main_menu(), parse_mode='Markdown')

    elif data == "menu_user":
        text = (
            f"👤 *YOUR COMMANDS*\n"
            f"{'─'*28}\n\n"
            f"📜 `/rules` — View group rules\n"
            f"⚠️ `/warnings` — Check your warnings\n"
            f"🆔 `/id` — Your Telegram ID\n\n"
            f"{'─'*28}\n"
            f"_These commands work for all members._"
        )
        await query.edit_message_text(text, reply_markup=kb_back(), parse_mode='Markdown')

    elif data == "menu_admin":
        # Only admins / owner can see this panel
        ch_id = update.effective_chat.id if update.effective_chat else 0
        if query.from_user.id != OWNER_ID and not await is_adm(ctx, ch_id, query.from_user.id):
            await query.answer("❌ Admins only!", show_alert=True)
            return
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
            f"🕵️ Hidden links inside text (text_link entities)\n"
            f"✍️ Stylish / Unicode fancy fonts\n"
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
    u  = update.effective_user
    ch = update.effective_chat

    # Group me /start → sirf ek line
    if ch.type != "private":
        await update.message.reply_text(
            f"🛡️ *Suhani Bot* is active! Use /help for commands.",
            parse_mode='Markdown'
        )
        return

    # DM — Owner panel
    if u.id == OWNER_ID:
        text = (
            f"╔{'═'*36}╗\n"
            f"║  🛡️  *SUHANI GROUP BOT v10.0*    ║\n"
            f"╚{'═'*36}╝\n\n"
            f"👑 *Owner Panel*\n"
            f"{'─'*30}\n\n"
            f"🌐 `/autodelete <min>` — Global auto-delete default\n"
            f"📢 `/broadcast <msg>` — Message all groups\n"
            f"👥 `/groups` — Active group count\n"
            f"📊 `/stats` — Full bot stats\n"
            f"🗓️ `/globalmutes` — Global mute list\n"
            f"💀 `/fban <id> [reason]` — Global ban\n"
            f"✅ `/gunban <id>` — Global unban\n"
            f"⚡ `/power <id>` — Grant fban power\n"
            f"🔻 `/unpower <id>` — Revoke fban power\n"
            f"🌐 `/gblacklist` — Global blacklist\n"
            f"✅ `/gwhitelist` — Global whitelist\n"
        )
        await update.message.reply_text(text, parse_mode='Markdown')
        return

    # DM — Regular user: sirf unke kaam ki cheezein
    text = (
        f"👋 *Hey {u.first_name}!*\n\n"
        f"I protect Telegram groups. Here's what you can do:\n\n"
        f"{'─'*28}\n"
        f"📜 `/rules` — View group rules\n"
        f"⚠️ `/warnings` — Check your warnings\n"
        f"🆔 `/id` — Your Telegram ID\n"
        f"{'─'*28}\n\n"
        f"_Add me to your group and make me admin to get started!_"
    )
    await update.message.reply_text(text, parse_mode='Markdown')


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
            f"ℹ️ *Commands you can use:*\n"
            f"{'─'*28}\n\n"
            f"📜 `/rules` — View group rules\n"
            f"⚠️ `/warnings` — Check your warnings\n"
            f"🆔 `/id` — Your Telegram ID\n\n"
            f"{'─'*28}\n"
            f"_Violations auto-detected. Stay within rules!_"
        )
        return await update.message.reply_text(text, parse_mode='Markdown')

    # ── Admin / Owner full help ──────────────────────────────
    admin_text = (
        f"👮 *ADMIN COMMANDS*\n"
        f"{'─'*30}\n\n"
        f"🔇 `/mute [sec]` — Mute user (reply)\n"
        f"🔊 `/unmute` — Unmute user (reply)\n"
        f"🔨 `/ban [reason]` — Ban user (reply)\n"
        f"🔓 `/unban <id>` — Unban user\n"
        f"⚠️ `/warn [reason]` — Warn user (reply)\n"
        f"♻️ `/resetwarnings` — Reset warnings (reply)\n"
        f"🗑️ `/del` — Delete message (reply)\n"
        f"🧹 `/purge` — Bulk delete from reply\n"
        f"🧪 `/testmute` — Test 35s mute (reply)\n"
        f"👑 `/immortal <id>` — Grant immunity\n"
        f"💀 `/unimmortal <id>` — Remove immunity\n\n"
        f"⚙️ *SETTINGS*\n"
        f"{'─'*30}\n\n"
        f"📜 `/setrules <text>` — Set rules\n"
        f"🔗 `/setlinked` — Set linked channel\n"
        f"🎭 `/captcha on|off` — Toggle captcha\n"
        f"🗑️ `/sticker_delete <min>` — Sticker auto-del\n"
        f"⏱️ `/autodelete <min>` — Auto-delete messages\n"
        f"   _`/autodelete reset` to restore global default_\n"
        f"⛔ `/addblacklist <word>` — Ban a word\n"
        f"✅ `/addwhitelist <word>` — Whitelist word\n"
        f"📋 `/blacklist` `/whitelist` — View lists\n"
    )

    if is_owner:
        admin_text += (
            f"\n👑 *OWNER ONLY*\n"
            f"{'─'*30}\n\n"
            f"🌐 `/autodelete <min>` _(in DM)_ — Global default\n"
            f"💀 `/fban <id> [reason]` — Global ban all groups\n"
            f"✅ `/gunban <id>` — Global unban\n"
            f"⚡ `/power <id>` — Grant fban power\n"
            f"🔻 `/unpower <id>` — Revoke fban power\n"
            f"📢 `/broadcast <msg>` — Message all groups\n"
            f"👥 `/groups` `/stats` — Bot stats\n"
            f"🌐 `/gblacklist` `/gwhitelist` — Global word lists\n"
            f"🤖 `/adexempt <id>` — Exempt bot from autodelete\n"
            f"❌ `/unadexempt <id>` — Remove exemption\n"
        )

    admin_text += (
        f"\n{'─'*30}\n"
        f"⚠️ *Warn:* W1→35s | W2→60s | W3→120s | W4→1wk all groups"
    )

    await update.message.reply_text(admin_text, parse_mode='Markdown')


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
                f"🌐 *Global Auto-Delete Default*\n"
                f"{'─'*30}\n\n"
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
        return await update.message.reply_text("❌ Admins only!")

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
        lines.append(f"⚡ *Active:* {'🟢 ' + str(effective) + ' min' if effective else '🔴 OFF'}")

        return await update.message.reply_text(
            f"🗑️ *Auto-Delete — This Group*\n"
            f"{'─'*30}\n\n"
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


# ─── /gblacklist ────────────────────────────────────────────
async def gblacklist_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Owner only — add/remove/list global blacklist words (apply to ALL groups)"""
    if update.effective_user.id != OWNER_ID:
        return await update.message.reply_text("❌ Owner only command!")

    if not ctx.args:
        # Show list
        words = db.get_gblacklist()
        if not words:
            return await update.message.reply_text(
                "📋 *Global Blacklist* is empty.\n\n"
                "Usage:\n"
                "`/gblacklist add <word>` — Add word\n"
                "`/gblacklist remove <word>` — Remove word\n"
                "`/gblacklist list` — Show all words",
                parse_mode='Markdown'
            )
        word_list = "\n".join(f"  • `{w}`" for w in words)
        return await update.message.reply_text(
            f"🌐 *Global Blacklist* ({len(words)} words)\n"
            f"{'─'*28}\n\n"
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
            f"🌐 *Global Blacklist* ({len(words)} words)\n"
            f"{'─'*28}\n\n"
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
            f"✅ *Global Blacklist* — Added!\n\n"
            f"🚫 `{word}`\n\n"
            f"_This word is now blocked in ALL your groups._",
            parse_mode='Markdown'
        )

    elif action == "remove":
        db.remove_gblacklist(word)
        await update.message.reply_text(
            f"✅ *Global Blacklist* — Removed!\n\n"
            f"🗑️ `{word}`",
            parse_mode='Markdown'
        )

    else:
        await update.message.reply_text(
            "❌ Unknown action!\n\n"
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
        return await update.message.reply_text("❌ Owner only command!")

    if not ctx.args:
        words = db.get_gwhitelist()
        if not words:
            return await update.message.reply_text(
                "📋 *Global Whitelist* is empty.\n\n"
                "Usage:\n"
                "`/gwhitelist add <word>` — Allow word globally\n"
                "`/gwhitelist remove <word>` — Remove\n"
                "`/gwhitelist list` — Show all",
                parse_mode='Markdown'
            )
        word_list = "\n".join(f"  • `{w}`" for w in words)
        return await update.message.reply_text(
            f"🌐 *Global Whitelist* ({len(words)} words)\n"
            f"{'─'*28}\n\n"
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
            f"🌐 *Global Whitelist* ({len(words)} words)\n"
            f"{'─'*28}\n\n"
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
            f"✅ *Global Whitelist* — Added!\n\n"
            f"✔️ `{word}`\n\n"
            f"_This word is now allowed in ALL groups._",
            parse_mode='Markdown'
        )
    elif action == "remove":
        db.remove_gwhitelist(word)
        await update.message.reply_text(
            f"✅ *Global Whitelist* — Removed!\n\n"
            f"🗑️ `{word}`",
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            "❌ Unknown action!\n\n"
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
        return await update.message.reply_text("❌ Owner only command!")

    target_id = None
    if ctx.args:
        try:
            target_id = int(ctx.args[0])
        except ValueError:
            return await update.message.reply_text(
                "❌ Usage: `/power <user_id>`",
                parse_mode='Markdown'
            )
    elif update.message.reply_to_message:
        target_id = update.message.reply_to_message.from_user.id
    else:
        return await update.message.reply_text(
            "❌ Usage: `/power <user_id>` or reply to user",
            parse_mode='Markdown'
        )

    db.add_powered(target_id)
    await update.message.reply_text(
        f"⚡ *Power Granted!*\n"
        f"{'─'*25}\n\n"
        f"🆔 User `{target_id}` can now use `/fban` and `/gunban`.\n\n"
        f"Use `/unpower {target_id}` to revoke.",
        parse_mode='Markdown'
    )


# ─── /unpower ───────────────────────────────────────────────
async def unpower_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Owner only — revoke fban power from a user."""
    if update.effective_user.id != OWNER_ID:
        return await update.message.reply_text("❌ Owner only command!")

    target_id = None
    if ctx.args:
        try:
            target_id = int(ctx.args[0])
        except ValueError:
            return await update.message.reply_text(
                "❌ Usage: `/unpower <user_id>`",
                parse_mode='Markdown'
            )
    elif update.message.reply_to_message:
        target_id = update.message.reply_to_message.from_user.id
    else:
        return await update.message.reply_text(
            "❌ Usage: `/unpower <user_id>` or reply to user",
            parse_mode='Markdown'
        )

    db.remove_powered(target_id)
    await update.message.reply_text(
        f"✅ Power *revoked* from `{target_id}`.",
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
                target_name = chat_obj.first_name or uname
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
        return await update.message.reply_text("❌ Cannot fban this user!")

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
        f"💀 *FBan Executed!*\n"
        f"{'─'*28}\n\n"
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
        f"✅ *Global Unban Done!*\n"
        f"{'─'*25}\n\n"
        f"👤 User `{target_id}` unbanned from `{unbanned_count}` groups.\n"
        f"_No notifications were sent to any group._",
        parse_mode='Markdown'
    )


# ─── /adexempt ──────────────────────────────────────────────
# ─── /aimod ─────────────────────────────────────────────────
async def aimod_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Admin — toggle AI moderation on/off for this group."""
    ch = update.effective_chat
    if ch.type == "private":
        return await update.message.reply_text("❌ Use in group!")
    if not await sender_is_admin(ctx, update):
        return await update.message.reply_text("❌ Admins only!")

    if not AI_API_KEY:
        return await update.message.reply_text(
            "⚠️ *AI Moderation not configured!*\n\n"
            "Owner needs to set `AI_API_KEY` environment variable on Railway.",
            parse_mode='Markdown'
        )

    if not ctx.args or ctx.args[0].lower() not in ('on', 'off'):
        g = db.get_group(ch.id)
        status = "🟢 ON" if g.get("aimod", True) else "🔴 OFF"
        return await update.message.reply_text(
            f"🤖 *AI Moderation*\n"
            f"{'─'*25}\n\n"
            f"Status: {status}\n\n"
            f"Toggle: `/aimod on` or `/aimod off`\n\n"
            f"_AI detects promotional/spam messages that bypass normal filters._",
            parse_mode='Markdown'
        )

    val = ctx.args[0].lower() == 'on'
    db.update_group(ch.id, {"aimod": val})
    state = "🟢 *enabled*" if val else "🔴 *disabled*"
    await update.message.reply_text(
        f"🤖 AI Moderation {state}!\n\n"
        f"{'_AI will now detect promotions & spam automatically._' if val else '_AI checks are off for this group._'}",
        parse_mode='Markdown'
    )


async def adexempt_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """
    Owner only — globally exempt a bot/channel from autodelete.
    Usage: /adexempt <user_id | @username>
           /adexempt list
    """
    if update.effective_user.id != OWNER_ID:
        return await update.message.reply_text("❌ Owner only command!")

    if not ctx.args or ctx.args[0].lower() == "list":
        exempts = db.get_all_ad_exempt()
        if not exempts:
            return await update.message.reply_text(
                "📋 *Autodelete Exempt List* is empty.\n\n"
                "Usage: `/adexempt <id | @username>` — add exempt\n"
                "`/unadexempt <id>` — remove exempt\n"
                "`/adexempt list` — show all",
                parse_mode='Markdown'
            )
        lines = "\n".join(f"  • `{eid}`" for eid in exempts)
        return await update.message.reply_text(
            f"🤖 *Autodelete Exempt* ({len(exempts)})\n"
            f"{'─'*28}\n\n"
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
        return await update.message.reply_text("❌ Could not resolve ID!")

    db.add_ad_exempt(target_id)
    await update.message.reply_text(
        f"✅ *Autodelete Exempt Added!*\n\n"
        f"🤖 ID `{target_id}` — messages will *never* be auto-deleted.\n"
        f"Use `/unadexempt {target_id}` to remove.",
        parse_mode='Markdown'
    )


# ─── /unadexempt ────────────────────────────────────────────
async def unadexempt_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Owner only — remove autodelete exemption."""
    if update.effective_user.id != OWNER_ID:
        return await update.message.reply_text("❌ Owner only command!")

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

    # GroupAnonymousBot — NEVER restrict, it handles linked channel posts
    ANON_BOT_ID = 1087968824
    if usr and usr.id == ANON_BOT_ID:
        return

    db.add_group(ch.id)

    txt = msg.text or msg.caption or ""
    if txt.startswith('/'): return

    # ── "Suhani ban" natural language command ──────────────
    # Admin group mein "suhani ban @user" ya "suhani ban userid" likh sakta hai
    txt_lower = txt.lower().strip()
    if txt_lower.startswith("suhani ban"):
        caller_is_admin = await is_adm(ctx, ch.id, usr.id) or usr.id == OWNER_ID
        if caller_is_admin:
            target_id = None
            target_name = None
            # Reply se target lo
            if msg.reply_to_message and msg.reply_to_message.from_user:
                target_id = msg.reply_to_message.from_user.id
                target_name = user_name(msg.reply_to_message.from_user)
            else:
                # "suhani ban @username" ya "suhani ban 123456"
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
                            target_name = uname
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
    autodel_min     = db.get_effective_autodelete(ch.id)   # global default ya per-group override

    is_sticker_media = (
        msg.sticker or
        msg.animation or
        (msg.text and any(ord(c) > 127000 for c in txt))
    )

    if db.is_gmuted(usr.id):
        asyncio.create_task(msg.delete())
        asyncio.create_task(do_mute(ctx, ch.id, usr.id, 604800))
        return

    # FBanned user — silently ban and delete message, no notification
    if db.is_fbanned(usr.id):
        asyncio.create_task(msg.delete())
        asyncio.create_task(do_ban(ctx, ch.id, usr.id))
        return

    is_admin = await is_adm(ctx, ch.id, usr.id)

    # ── Autodelete logic ────────────────────────────────────
    # Sender ID resolve karo — normal user ya channel/bot sender_chat
    sender_id = usr.id if usr else None
    sender_chat = getattr(msg, 'sender_chat', None)
    if sender_chat:
        sender_id = sender_chat.id

    # Autodelete exempt check — globally exempted bot/channel IDs
    ad_exempted = sender_id and db.is_ad_exempt(sender_id)

    # Sticker auto-delete: sabpe lagega (admin bhi), sirf exempt nahi
    if sticker_del_min and is_sticker_media and not ad_exempted:
        asyncio.create_task(delete_after(ctx, ch.id, msg.message_id, sticker_del_min * 60))

    # Global/per-group autodelete:
    # - Admin ke messages delete NAHI honge (unka kaam hota hai)
    # - Exempt bots/channels ke messages delete nahi honge
    # - Baaki sab delete honge
    if autodel_min and not is_admin and not ad_exempted:
        asyncio.create_task(delete_after(ctx, ch.id, msg.message_id, autodel_min * 60))

    # Admin ke violations (link/username/etc.) check hote rahenge
    # Sirf is_adm wala early return hata diya — ab admin bhi violation check se guzrega
    if db.is_immortal(ch.id, usr.id):
        return

    db.inc_stat("scanned")

    group_bots = await get_group_bots(ctx, ch.id)
    violation = await check_violations(msg, group_bots, ctx, ch.id)

    # ── AI Engine — sirf tab jab local checks pass ho gaye ──
    txt_for_ai = msg.text or msg.caption or ""
    ai_result = {"action": "SAFE", "reply": ""}

    if not violation and AI_API_KEY and g_settings.get("aimod", True) and not is_admin:
        if txt_for_ai:
            # Repeat tracker — ek hi cheez baar baar likh raha hai?
            repeat_count = track_repeat(ch.id, usr.id, txt_for_ai)

            # Anime name repeat — seedha reply, AI call nahi
            if repeat_count >= 3 and is_anime_message(txt_for_ai):
                anime_name = txt_for_ai.strip()
                ai_result = {
                    "action": "REPLY",
                    "reply": f"Bhai {user_name(usr)}, *{anime_name}* baar baar likhne se kuch nahi hoga 😄 Ye anime available hai toh group mein already pata hoga!"
                }
            else:
                ai_result = await ai_check(txt_for_ai, usr.id, ch.id, getattr(usr, 'username', '') or '')

        if ai_result["action"] == "PROMO":
            violation = "ai_promo"

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
        return

    # ── AI REPLY — question/help/anime/confusion ──
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
    app.add_handler(CommandHandler("gblacklist",       gblacklist_cmd))
    app.add_handler(CommandHandler("gwhitelist",       gwhitelist_cmd))
    app.add_handler(CommandHandler("stats",            stats_cmd))
    app.add_handler(CommandHandler("power",            power_cmd))
    app.add_handler(CommandHandler("unpower",          unpower_cmd))
    app.add_handler(CommandHandler("fban",             fban_cmd))
    app.add_handler(CommandHandler("gunban",           gunban_cmd))
    app.add_handler(CommandHandler("adexempt",         adexempt_cmd))
    app.add_handler(CommandHandler("unadexempt",       unadexempt_cmd))
    app.add_handler(CommandHandler("aimod",            aimod_cmd))

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
