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

import re, os, asyncio, time, random, string, json, html
from datetime import datetime, timedelta, time as dtime
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
#  SUHANI COIN / REPUTATION ECONOMY — CONFIG
#  • Har "Thank You" = 100 Reputation Points
#  • 1 warning maaf karne ka cost = 100 Reputation Points
#  • 10,000 Reputation Points = 1 Suhani Coin = ₹1
#  • Suhani Coin sirf "accepted" groups ke reputation se banta hai.
#    Non-accepted group ka reputation SIRF warning maaf karne ke
#    kaam aata hai, coin mein convert nahi hota.
#  • Min withdrawal = 10 Suhani Coins (₹10)
# ═══════════════════════════════════════════════════════════
REP_PER_THANK        = 100      # 1 thank you = 100 rep points
REP_PER_WARN_REMOVE  = 100      # 1 warning maaf = 100 rep points
REP_PER_SUHANI_COIN  = 10000    # 10,000 rep = 1 Suhani Coin (₹1)
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
SUHANI_SYSTEM = """You are Suhani, a friendly Telegram group protection bot for an anime Hindi dub group.

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
2. ANIME_SEARCH: User wrote an anime name (to search/request it) — provider bot handles actual search
3. ANIME_NOT_FOUND: Provider bot did NOT reply → anime not available yet
4. HELP: Help users who seem confused or ask questions
5. IDENTITY: Answer questions about who you are

When asked about your AI/technology — NEVER mention Groq, LLaMA, or any AI company. Say you are Suhani, made by Lucky.

IMPORTANT CONTEXT about this group:
- This is a Hindi dubbed anime group
- Users type anime names to search/get them
- A provider bot searches and replies with the anime if available
- If provider bot did NOT reply → that anime is NOT available yet in Hindi dub
- When anime is not found, ALWAYS suggest 2-3 similar anime they might like instead
- Common typos happen — if you recognize a misspelled anime, mention the correct name

Response format — you must ALWAYS respond with JSON only:
{
  "action": "PROMO" | "SAFE" | "REPLY" | "ANIME_NOT_FOUND",
  "reply": "your message here (only if action is REPLY or ANIME_NOT_FOUND, else empty string)",
  "anime_name": "exact anime name user was searching (only if action is ANIME_NOT_FOUND, else empty string)"
}

action meanings:
- PROMO: message is promotional/spam/advertising → will be deleted + warned
- SAFE: normal message or conversation, ignore it
- REPLY: message needs a response (question, help needed, confusion, anime discussion)
- ANIME_NOT_FOUND: user searched an anime but provider bot didn't find it → tell them nicely + suggest similar

For ANIME_NOT_FOUND reply example:
"Yaar, 'The Brilliant Healer's New Life in the Shadows' abhi Hindi mein available nahi hai 😅 Jald add karenge! Tab tak 'Eminence in Shadow' ya 'Overlord' try karo — same vibes hai! 🔥"

For REPLY with typo correction example:
"Bhai, 'Narato' nahi, 'Naruto' likho 😄 Provider se maango!"

For REPLY, write in Hinglish, keep it short and friendly.
For SAFE — normal conversations between users, greetings, reactions — DO NOT interfere."""

async def ai_check(text: str, user_id: int, chat_id: int, username: str = "",
                   reply_context: str = "", bypass_cooldown: bool = False) -> dict:
    """
    Returns dict: {"action": "PROMO"/"SAFE"/"REPLY", "reply": "..."}
    Uses Groq API (llama-3.1-8b-instant).
    reply_context: bot ka previous message (agar user ne reply kiya ho)
    bypass_cooldown: True karo jab user bot ke reply pe message kare
    """
    if not AI_API_KEY:
        return {"action": "SAFE", "reply": ""}

    if not text or len(text.strip()) < 3:
        return {"action": "SAFE", "reply": ""}

    # Anime-only message — skip AI entirely
    if is_anime_message(text):
        # But still check repeat
        return {"action": "SAFE", "reply": ""}

    # Cooldown check — bypass karo agar bot ke reply pe message hai
    now = time.time()
    if not bypass_cooldown:
        last = AI_COOLDOWN.get(user_id, 0)
        if now - last < AI_COOLDOWN_SEC:
            return {"action": "SAFE", "reply": ""}
    AI_COOLDOWN[user_id] = now

    try:
        session = await get_ai_session()

        # Context-aware message — agar bot ke reply pe hai
        if reply_context:
            user_content = (
                f"[Context: User is replying to your previous message: \"{reply_context}\"]\n"
                f"User's reply: {text[:500]}"
            )
        else:
            user_content = text[:600]

        payload = {
            "model": "llama-3.1-8b-instant",
            "max_tokens": 150,
            "temperature": 0.3,
            "messages": [
                {"role": "system", "content": SUHANI_SYSTEM},
                {"role": "user", "content": user_content}
            ]
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
            # Groq sometimes wraps JSON in ```json ... ``` markdown
            raw = re.sub(r'^```(?:json)?\s*', '', raw)
            raw = re.sub(r'\s*```$', '', raw)
            raw = raw.strip()
            # Extract first JSON object if extra text present
            json_match = re.search(r'\{.*\}', raw, re.DOTALL)
            if json_match:
                raw = json_match.group(0)
            result = json.loads(raw)
            action = result.get("action", "SAFE").upper()
            if action not in ("PROMO", "SAFE", "REPLY", "ANIME_NOT_FOUND"):
                action = "SAFE"
            return {
                "action": action,
                "reply": result.get("reply", ""),
                "anime_name": result.get("anime_name", "")
            }
    except Exception:
        return {"action": "SAFE", "reply": "", "anime_name": ""}

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
        self.reputation = self.db["reputation"]   # group-wise reputation points (SEPARATE from leaderboard)
        self.activity  = self.db["activity"]      # daily message-count tracking (leaderboard source)
        self.suhani_pts = self.db["suhani_points"]   # global suhani points wallet per user
        self.rep_daily  = self.db["rep_daily_limit"] # daily rep-give tracking (3/day cap)
        self.accepted_rep_groups = self.db["accepted_rep_groups"]  # groups jinka rep Suhani Coin mein convert hota hai
        self.withdrawals = self.db["withdrawals"]    # Suhani Coin withdrawal requests
        self.daily_winners = self.db["daily_winners"] # daily #1 global-ranking auto-reward log

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
            "aimod": False,       # Default OFF — owner /aiapprove se enable karega
            "ai_approved": False, # Owner approval required
        }}, upsert=True)

    def remove_group(self, chat_id):
        self.groups.delete_one({"_id": chat_id})

    def get_group(self, chat_id):
        return self.groups.find_one({"_id": chat_id}) or {}

    def update_group(self, chat_id, data):
        self.groups.update_one({"_id": chat_id}, {"$set": data}, upsert=True)

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
    #  SUHANI POINTS SYSTEM
    #  10,000 Reputation Points (accepted groups only) → 1 Suhani Coin → ₹1
    #  Min withdrawal: 10 INR (100 Suhani Points)
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
    def add_reputation(self, chat_id, user_id, amount=REP_PER_THANK, display_name=None):
        """Group-wise reputation point add karo + suhani wallet resync karo."""
        k = f"{chat_id}_{user_id}"
        update = {"$inc": {"points": amount}, "$set": {"chat_id": chat_id, "user_id": user_id}}
        if display_name:
            update["$set"]["name"] = display_name
        self.reputation.update_one({"_id": k}, update, upsert=True)
        self._sync_suhani_points(user_id)

    def spend_reputation(self, chat_id, user_id, amount=REP_PER_WARN_REMOVE) -> bool:
        """
        Kisi ek group ka reputation kharch karo (warning maaf karne ke liye).
        Yeh HAR group (accepted ho ya na ho) mein kaam karta hai — reputation
        hamesha warn-se-bachne ke liye valid hota hai, sirf Suhani Coin
        conversion accepted groups tak limited hai.
        Returns True agar kharch ho gaya, False agar balance kam tha.
        """
        k = f"{chat_id}_{user_id}"
        doc = self.reputation.find_one({"_id": k})
        current = doc.get("points", 0) if doc else 0
        if current < amount:
            return False
        self.reputation.update_one({"_id": k}, {"$inc": {"points": -amount}})
        self._sync_suhani_points(user_id)
        return True

    # ── Accepted groups (jinka reputation Suhani Coin mein convert hota hai) ──
    def accept_rep_group(self, chat_id, title=None, link=None):
        update = {"$set": {"_id": chat_id, "accepted_at": time.time()}}
        if title:
            update["$set"]["title"] = title
        if link:
            update["$set"]["link"] = link
        self.accepted_rep_groups.update_one({"_id": chat_id}, update, upsert=True)

    def unaccept_rep_group(self, chat_id):
        self.accepted_rep_groups.delete_one({"_id": chat_id})

    def is_rep_group_accepted(self, chat_id) -> bool:
        return self.accepted_rep_groups.find_one({"_id": chat_id}) is not None

    def get_accepted_rep_groups(self):
        return [g["_id"] for g in self.accepted_rep_groups.find({}, {"_id": 1})]

    def get_accepted_rep_groups_full(self):
        """Poori detail (title + invite link) ke saath accepted groups — /earn_groups ke liye."""
        return list(self.accepted_rep_groups.find({}))

    def _sync_suhani_points(self, user_id: int):
        """
        Do cheezein calculate karo:
          • total_rep        → SAB groups (accepted + non-accepted) ka total,
                                sirf tier-badge / display ke liye use hota hai
          • convertible_rep  → SIRF accepted groups ka total, isi se
                                Suhani Coin banta hai (10,000 rep = 1 coin)
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

        self.suhani_pts.update_one(
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

    def get_suhani_points(self, user_id: int) -> dict:
        """
        User ka suhani wallet return karo.
        coins = floor(convertible_rep / 10000) − ab tak withdraw kiye gaye coins
        """
        doc = self.suhani_pts.find_one({"_id": user_id})
        total_rep       = doc.get("total_rep", 0) if doc else 0
        convertible_rep = doc.get("convertible_rep", 0) if doc else 0
        withdrawn_coins = doc.get("withdrawn_coins", 0) if doc else 0
        earned_coins    = convertible_rep // REP_PER_SUHANI_COIN
        available_coins = max(0, earned_coins - withdrawn_coins)
        return {
            "total_rep": total_rep,
            "convertible_rep": convertible_rep,
            "earned_coins": earned_coins,
            "withdrawn_coins": withdrawn_coins,
            "coins": available_coins,
            # backward-compat key used elsewhere in file
            "suhani_pts": available_coins,
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
                self.suhani_pts.update_one(
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

    @staticmethod
    def _activity_date_filter(period):
        """period: 'today' | '2weeks' | 'month' → mongo date-string filter banata hai."""
        now = datetime.now()
        if period == "today":
            return {"date": now.strftime("%Y-%m-%d")}
        elif period == "2weeks":
            cutoff = (now - timedelta(days=14)).strftime("%Y-%m-%d")
            return {"date": {"$gte": cutoff}}
        else:  # "month"
            cutoff = (now - timedelta(days=30)).strftime("%Y-%m-%d")
            return {"date": {"$gte": cutoff}}

    def get_activity_leaderboard(self, chat_id, period="today", limit=10):
        """Group ke andar top message-senders, given period ke liye."""
        match = {"chat_id": chat_id}
        match.update(self._activity_date_filter(period))
        pipeline = [
            {"$match": match},
            {"$group": {
                "_id": "$user_id",
                "total": {"$sum": "$count"},
                "name": {"$last": "$name"},
            }},
            {"$sort": {"total": -1}},
            {"$limit": limit},
        ]
        return list(self.activity.aggregate(pipeline))

    def get_global_activity_leaderboard(self, period="today", limit=10):
        """Saare groups mile ke top message-senders, given period ke liye."""
        match = {}
        match.update(self._activity_date_filter(period))
        pipeline = [
            {"$match": match},
            {"$group": {
                "_id": "$user_id",
                "total": {"$sum": "$count"},
                "name": {"$last": "$name"},
            }},
            {"$sort": {"total": -1}},
            {"$limit": limit},
        ]
        return list(self.activity.aggregate(pipeline))

    # ── Daily #1 global-ranking auto-reward ─────────────────────────
    def get_global_activity_top_for_date(self, date_str, limit=1):
        """EXACT date (YYYY-MM-DD) ke liye global (saare groups) top message-senders."""
        pipeline = [
            {"$match": {"date": date_str}},
            {"$group": {
                "_id": "$user_id",
                "total": {"$sum": "$count"},
                "name": {"$last": "$name"},
            }},
            {"$sort": {"total": -1}},
            {"$limit": limit},
        ]
        return list(self.activity.aggregate(pipeline))

    def get_most_active_group_for_user_on_date(self, user_id, date_str):
        """Us din user sabse zyada kis group mein active tha — wahi group rep credit ke liye use hota hai."""
        cursor = self.activity.find(
            {"user_id": user_id, "date": date_str}
        ).sort("count", -1).limit(1)
        doc = next(cursor, None)
        return doc.get("chat_id") if doc else None

    def was_daily_winner_awarded(self, date_str) -> bool:
        return self.daily_winners.find_one({"_id": date_str}) is not None

    def mark_daily_winner_awarded(self, date_str, user_id, chat_id):
        self.daily_winners.update_one(
            {"_id": date_str},
            {"$set": {"user_id": user_id, "chat_id": chat_id, "awarded_at": time.time()}},
            upsert=True
        )

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

    # ── Missing Anime tracker ─────────────────────────────────
    def log_missing_anime(self, anime_name: str, chat_id: int):
        """Log a missing anime — increment request count."""
        clean = anime_name.strip().lower()[:120]
        self.db["missing_anime"].update_one(
            {"_id": clean},
            {
                "$inc": {"count": 1},
                "$set": {"display_name": anime_name.strip()},
                "$addToSet": {"groups": chat_id},
                "$setOnInsert": {"first_seen": time.time()}
            },
            upsert=True
        )

    def get_missing_anime_list(self, limit=30):
        """Get top requested missing anime sorted by count."""
        return list(
            self.db["missing_anime"].find().sort("count", -1).limit(limit)
        )

    def clear_missing_anime(self, anime_name: str = None):
        """Clear one or all missing anime entries."""
        if anime_name:
            self.db["missing_anime"].delete_one({"_id": anime_name.strip().lower()})
        else:
            self.db["missing_anime"].delete_many({})


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
            # Koi info nahi — doubt mein admin maano (safe side)
            return True


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


def user_name(u, escape: bool = False) -> str:
    """User ka display name return karo. Default escape=False kyunki legacy
    Markdown mode mein backslash-escape render nahi hota, ulta literal
    backslash dikhta hai."""
    try:
        raw = f"@{u.username}" if u.username else u.first_name or str(u.id)
    except Exception:
        raw = "User"
    return md_esc(raw) if escape else raw


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



async def auto_delete_commands(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Group mein aane wale har command ko 10 min mein delete karo (sirf groups, broadcast nahi)."""
    msg = update.effective_message
    ch  = update.effective_chat
    if not msg or not ch or ch.type == "private":
        return
    asyncio.create_task(delete_after(ctx, ch.id, msg.message_id, 600))

async def global_mute_user(ctx, user_id, display_name=None):
    db.add_gmute(user_id)
    for gid in db.get_all_groups():
        try:
            await do_mute(ctx, gid, user_id, GMUTE_DURATION)
            notice = await ctx.bot.send_message(
                gid,
                f"╔{'═'*30}╗\n"
                f"║   💀  GLOBAL MUTE EXECUTED   ║\n"
                f"╚{'═'*30}╝\n\n"
                f"👤 *{display_name or user_id}*\n\n"
                f"🌐 Muted in *ALL* groups\n"
                f"🗓️ Duration: *1 WEEK*\n"
                f"🔐 Only admin can unmute manually\n\n"
                f"_{'─'*30}_\n"
                f"_{WARN_MSG[4]}_",
                parse_mode='Markdown'
            )
            asyncio.create_task(delete_after(ctx, gid, notice.message_id, 600))
            await asyncio.sleep(0.1)
        except:
            pass


# ═══════════════════════════════════════════════════════════
#  INLINE KEYBOARD BUILDERS
# ═══════════════════════════════════════════════════════════
def kb_main_menu():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("👤 My Commands", callback_data="menu_user"),
            InlineKeyboardButton("👮 Admin Panel", callback_data="menu_admin"),
        ],
        [
            InlineKeyboardButton("🛡️ Protections", callback_data="menu_protection"),
            InlineKeyboardButton("⚙️ Settings", callback_data="menu_settings"),
        ],
        [
            InlineKeyboardButton("⚠️ Warn System", callback_data="menu_warns"),
            InlineKeyboardButton("📜 Rules", callback_data="show_rules"),
        ],
        [
            InlineKeyboardButton("🏆 Rep Board", callback_data="menu_repboard"),
            InlineKeyboardButton("⭐ My Profile", callback_data="rep:myprofile"),
        ],
        [
            InlineKeyboardButton("📊 Rankings", callback_data="menu_rankings"),
        ],
        [InlineKeyboardButton("❌ Close", callback_data="close_menu")],
    ])

def kb_back():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("◀️ Back to Menu", callback_data="menu_main")]
    ])

def kb_back_with_help():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("◀️ Back", callback_data="menu_main"),
            InlineKeyboardButton("📜 Rules", callback_data="show_rules"),
        ]
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
            InlineKeyboardButton("📜 Group Rules", callback_data="show_rules"),
            InlineKeyboardButton("🆘 Help", callback_data="menu_user"),
        ],
        [
            InlineKeyboardButton("⚠️ Warn System", callback_data="menu_warns"),
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


# ── Colored keyboard row data (for direct Bot API calls) ──────
# Style: "primary"=blue, "success"=green, "danger"=red

def ckb_main_menu():
    """Main menu colored rows."""
    return [
        [
            {"text": "👤 My Commands",   "callback_data": "menu_user",       "style": "primary"},
            {"text": "👮 Admin Panel",   "callback_data": "menu_admin",      "style": "primary"},
        ],
        [
            {"text": "🛡️ Protections",  "callback_data": "menu_protection", "style": "success"},
            {"text": "⚙️ Settings",     "callback_data": "menu_settings",   "style": "primary"},
        ],
        [
            {"text": "⚠️ Warn System",  "callback_data": "menu_warns",      "style": "danger"},
            {"text": "📜 Rules",         "callback_data": "show_rules",      "style": "primary"},
        ],
        [
            {"text": "🏆 Rep Board",     "callback_data": "menu_repboard",   "style": "success"},
            {"text": "⭐ My Profile",    "callback_data": "rep:myprofile",   "style": "success"},
        ],
        [
            {"text": "📊 Rankings",      "callback_data": "menu_rankings",   "style": "success"},
        ],
        [{"text": "❌ Close",            "callback_data": "close_menu",       "style": "danger"}],
    ]

def ckb_back():
    return [[{"text": "◀️ Back to Menu", "callback_data": "menu_main", "style": "primary"}]]

def ckb_stats_refresh():
    return [[
        {"text": "🔄 Refresh",  "callback_data": "menu_stats", "style": "primary"},
        {"text": "◀️ Back",     "callback_data": "menu_main",  "style": "primary"},
    ]]

def ckb_repinfo(user_id=0):
    return [[
        {"text": "◀️ Back",     "callback_data": "menu_main",  "style": "primary"},
        {"text": "💸 Withdraw", "callback_data": f"rep:wdinfo:{user_id}", "style": "success"},
    ]]

def ckb_warn_actions(chat_id, user_id):
    return [[
        {"text": "🔊 Unmute",   "callback_data": f"unmute_{chat_id}_{user_id}", "style": "success"},
        {"text": "🗑️ Dismiss", "callback_data": "dismiss_warn",                "style": "danger"},
    ]]

def ckb_join_welcome():
    return [
        [
            {"text": "📜 Group Rules", "callback_data": "show_rules", "style": "success"},
            {"text": "🆘 Help",        "callback_data": "menu_user",  "style": "primary"},
        ],
        [
            {"text": "⚠️ Warn System", "callback_data": "menu_warns", "style": "danger"},
        ]
    ]

def ckb_bot_added():
    return [
        [
            {"text": "📋 Commands",     "callback_data": "menu_admin",      "style": "primary"},
            {"text": "⚙️ Setup",        "callback_data": "menu_settings",   "style": "primary"},
        ],
        [
            {"text": "🛡️ Protections", "callback_data": "menu_protection", "style": "success"},
        ]
    ]

def ckb_rep_board(chat_id, user_id):
    return [
        [
            {"text": "🔄 Refresh",       "callback_data": f"rep:board:{chat_id}", "style": "primary"},
            {"text": "⭐ My Profile",    "callback_data": f"rep:wallet:{user_id}", "style": "success"},
        ],
        [
            {"text": "🌐 Global Refresh","callback_data": "rep:global:0",          "style": "primary"},
            {"text": "💸 Withdraw",      "callback_data": f"rep:wdinfo:{user_id}", "style": "success"},
        ]
    ]

def ckb_start_group():
    return [[
        {"text": "📋 Commands", "callback_data": "menu_main",   "style": "primary"},
        {"text": "📜 Rules",    "callback_data": "show_rules",  "style": "success"},
    ]]


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
            f"╔{'═'*34}╗\n"
            f"║   🛡️  SUHANI BOT v10.0        ║\n"
            f"╠{'═'*34}╣\n"
            f"║      Group Protection Bot      ║\n"
            f"╚{'═'*34}╝\n\n"
            f"_Choose a category below 👇_"
        )
        # Try colored Bot API edit
        chat_id = update.effective_chat.id if update.effective_chat else 0
        await query.answer()
        success = await edit_colored_message(chat_id, query.message.message_id, text, ckb_main_menu())
        if not success:
            await query.edit_message_text(text, reply_markup=kb_main_menu(), parse_mode='Markdown')
        return

    elif data == "menu_user":
        text = (
            f"╔{'═'*32}╗\n"
            f"║   👤  YOUR COMMANDS          ║\n"
            f"╚{'═'*32}╝\n\n"
            f"{'─'*32}\n\n"
            f"📜 `/rules` — View group rules\n"
            f"⚠️ `/warnings` — Check your warnings\n"
            f"⭐ `/rep` — Suhani Profile Card \\& Wallet\n"
            f"💰 `/wallet` — Suhani Points \\& INR value\n"
            f"🏆 `/repboard` — Group + Global Rep Board\n"
            f"📊 `/rankings` — Group \\& Global message-activity rank\n"
            f"💰 `/earn_groups` — Groups jaha msg karke paisa kamao\n"
            f"🆔 `/id` — Your Telegram ID\n\n"
            f"{'─'*32}\n"
            f"💎 *REWARD SYSTEM*\n"
            f"_Thank You → +100 Rep | Warn maaf → 100 Rep_\n"
            f"_10,000 Rep (accepted group) → 1 Suhani Coin → ₹1_\n"
            f"_Active raho → Auto earn! 🔥_\n"
            f"_Min withdrawal: ₹10 → `/withdraw`_"
        )
        await query.answer()
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("◀️ Back", callback_data="menu_main"),
                    InlineKeyboardButton("🏆 Rep Board", callback_data="menu_repboard"),
                ],
                [InlineKeyboardButton("❌ Close", callback_data="close_menu")],
            ]),
            parse_mode='Markdown'
        )
        return

    elif data == "menu_admin":
        # Only admins / owner can see this panel
        ch_id = update.effective_chat.id if update.effective_chat else 0
        if query.from_user.id != OWNER_ID and not await is_adm(ctx, ch_id, query.from_user.id):
            await query.answer("❌ Admins only!", show_alert=True)
            return
        text = (
            f"╔{'═'*32}╗\n"
            f"║   👮  ADMIN COMMANDS         ║\n"
            f"╚{'═'*32}╝\n\n"
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
            f"{'─'*32}\n"
            f"📊 `/rankings` • `/repboard`"
        )
        await query.answer()
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("◀️ Back", callback_data="menu_main"),
                    InlineKeyboardButton("⚙️ Settings", callback_data="menu_settings"),
                ],
                [InlineKeyboardButton("❌ Close", callback_data="close_menu")],
            ]),
            parse_mode='Markdown'
        )
        return

    elif data == "menu_protection":
        text = (
            f"╚{'═'*32}╝\n\n"
            f"🤖 External bot usernames\n"
            f"👤 External @mentions\n"
            f"   ✅ _@admin @owner @request: exempt_\n"
            f"   ✅ _Whitelisted & members: exempt_\n"
            f"🔗 All Links & URLs\n"
            f"🕵️ Hidden hyperlinks (text_link entities)\n"
            f"✍️ Stylish / Unicode fancy fonts\n"
            f"↩️ Forwarded messages\n"
            f"   ✅ _Linked channel forwards: allowed_\n"
            f"🔞 Adult emojis (2+ triggers action)\n"
            f"🚫 Bad words — Hindi + English built-in\n"
            f"⛔ Custom blacklist words\n"
            f"🌐 Global blacklist (owner sets)\n"
            f"🌊 Anti-Flood system\n"
            f"🎭 Captcha for new members\n"
            f"🗑️ Sticker/GIF auto-delete\n"
            f"⏱️ Message auto-delete timer\n\n"
            f"{'─'*32}\n"
            f"_All protections are automatic!_"
        )
        await query.answer()
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("◀️ Back", callback_data="menu_main")],
                [InlineKeyboardButton("❌ Close", callback_data="close_menu")],
            ]),
            parse_mode='Markdown'
        )
        return

    elif data == "menu_settings":
        text = (
            f"╔{'═'*32}╗\n"
            f"║   ⚙️  GROUP SETTINGS         ║\n"
            f"╚{'═'*32}╝\n\n"
            f"🔗 `/setlinked` — Set linked channel\n"
            f"📜 `/setrules <text>` — Set group rules\n"
            f"🎭 `/captcha on|off` — Toggle captcha\n"
            f"⛔ `/addblacklist <word>` — Ban a word\n"
            f"✅ `/addwhitelist <word>` — Whitelist word\n"
            f"📋 `/blacklist` • `/whitelist` — View lists\n"
            f"🗑️ `/sticker_delete <min>` — Sticker auto-del\n"
            f"⏱️ `/autodelete <min>` — Auto-delete msgs\n"
            f"   _`/autodelete reset` → restore global default_\n"
            f"🤖 `/aimod on|off` — AI moderation toggle\n\n"
            f"{'─'*32}\n"
            f"💡 _Settings apply only to this group_"
        )
        await query.answer()
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("◀️ Back", callback_data="menu_main")],
                [InlineKeyboardButton("❌ Close", callback_data="close_menu")],
            ]),
            parse_mode='Markdown'
        )
        return

    elif data == "menu_warns":
        text = (
            f"╔{'═'*32}╗\n"
            f"║   ⚠️  WARNING SYSTEM         ║\n"
            f"╚{'═'*32}╝\n\n"
            f"🟡 *W1* → Muted 35 seconds\n"
            f"   ⏱ _Expires in 6 hours_\n\n"
            f"🟠 *W2* → Muted 60 seconds\n"
            f"   ⏱ _Expires in 16 hours_\n\n"
            f"🔴 *W3* → Muted 120 seconds\n"
            f"   ⏱ _Expires in 27 hours_\n\n"
            f"💀 *W4* → 1 WEEK BAN\n"
            f"   🌐 _Applied in ALL groups!_\n"
            f"   🔐 _Admin must manually unmute_\n\n"
            f"{'─'*32}\n"
            f"💡 *Tip:* Reply *Thank You* to remove 1 warning!\n"
            f"_Violations auto-trigger warnings_"
        )
        await query.answer()
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("◀️ Back", callback_data="menu_main"),
                    InlineKeyboardButton("⚠️ My Warnings", callback_data="show_my_warnings"),
                ],
                [InlineKeyboardButton("❌ Close", callback_data="close_menu")],
            ]),
            parse_mode='Markdown'
        )
        return

    elif data == "menu_stats":
        s = db.get_stats()
        groups = db.get_all_groups()
        gmutes = db.get_all_gmutes()
        text = (
            f"╔{'═'*32}╗\n"
            f"║   📊  BOT STATISTICS         ║\n"
            f"╚{'═'*32}╝\n\n"
            f"👥 Groups Active:     `{len(groups)}`\n"
            f"⚠️ Warnings Given:    `{s.get('warnings', 0)}`\n"
            f"🔇 Mutes Executed:    `{s.get('mutes', 0)}`\n"
            f"📨 Msgs Scanned:      `{s.get('scanned', 0)}`\n"
            f"🗓️ Global Mutes:      `{len(gmutes)}`\n\n"
            f"{'─'*32}\n"
            f"🛡️ Status:  {ICON_ON} *Active & Running*\n"
            f"🗄️ Database: {ICON_ON} *MongoDB Connected*\n"
            f"🤖 AI Engine: {'🟢 Active' if AI_API_KEY else '🔴 Not Configured'}"
        )
        await query.answer()
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("🔄 Refresh", callback_data="menu_stats"),
                    InlineKeyboardButton("◀️ Back", callback_data="menu_main"),
                ],
                [InlineKeyboardButton("❌ Close", callback_data="close_menu")],
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
                return ["  📉 _Abhi koi data nahi!_"]
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
            f"╔{'═'*32}╗\n"
            f"║   🏆  REPUTATION BOARD       ║\n"
            f"╚{'═'*32}╝\n\n"
            f"🏠 *GROUP TOP*\n"
            f"{'┄'*32}\n"
            + "\n".join(group_lines) +
            f"\n\n🌐 *GLOBAL TOP*\n"
            f"{'┄'*32}\n"
            + "\n".join(global_lines) +
            f"\n\n{'─'*32}\n"
            f"💡 _Reply 'Thank You' → +1 Rep_\n"
            f"_Active raho → Auto earn! 🔥_"
        )
        user_id = query.from_user.id if query.from_user else 0
        await query.answer()
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("🔄 Refresh", callback_data="menu_repboard"),
                    InlineKeyboardButton("⭐ My Profile", callback_data="rep:myprofile"),
                ],
                [
                    InlineKeyboardButton("📊 Group Rank", callback_data=f"rep:board:{ch_id}"),
                    InlineKeyboardButton("🌐 Global Rank", callback_data="rep:global:0"),
                ],
                [
                    InlineKeyboardButton("◀️ Back", callback_data="menu_main"),
                    InlineKeyboardButton("❌ Close", callback_data="close_menu"),
                ],
            ]),
            parse_mode='Markdown'
        )
        return

    elif data == "menu_rankings":
        # /rankings ka main-menu version — Group/Global + period buttons ke saath
        ch = update.effective_chat
        origin_id = ch.id if ch and ch.type != "private" else 0
        scope = "g" if origin_id else "a"
        if scope == "g":
            entries = db.get_activity_leaderboard(origin_id, period="today", limit=10)
            text = build_lb_text(entries, "today", "GROUP RANKINGS")
        else:
            entries = db.get_global_activity_leaderboard(period="today", limit=10)
            text = build_lb_text(entries, "today", "GLOBAL RANKINGS")
        kb_rows = list(build_rankings_keyboard(scope, origin_id, "today").inline_keyboard)
        kb_rows.append([
            InlineKeyboardButton("◀️ Back", callback_data="menu_main"),
            InlineKeyboardButton("❌ Close", callback_data="close_menu"),
        ])
        await query.answer()
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(kb_rows),
            parse_mode='HTML',
            disable_web_page_preview=True
        )
        return

    elif data == "menu_repinfo":
        # Keep for backwards compat — redirect to repboard
        ch_id = update.effective_chat.id if update.effective_chat else 0
        await query.answer()
        query.data = "menu_repboard"
        # Re-trigger via same logic
        await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🏆 Open Rep Board", callback_data="menu_repboard")]
        ]))
        return

    elif data == "menu_ai":
        text = (
            f"╔{'═'*32}╗\n"
            f"║   🤖  AI MODERATION          ║\n"
            f"╚{'═'*32}╝\n\n"
            f"AI Engine: {'🟢 *Suhani AI — Active*' if AI_API_KEY else '🔴 *Not Configured*'}\n\n"
            f"{'─'*32}\n"
            f"*What AI Does:*\n"
            f"  🚨 Detects promo/spam content\n"
            f"  🎌 Knows anime names (search assist)\n"
            f"  💬 Replies in Hinglish when needed\n"
            f"  📋 Logs missing anime requests\n\n"
            f"*Owner Commands:*\n"
            f"  `/aiapprove` — Approve group\n"
            f"  `/airevoke` — Revoke AI\n"
            f"  `/aigroups` — List approved\n"
            f"  `/missinganime` — Missing requests\n\n"
            f"*Admin Command:*\n"
            f"  `/aimod on|off` — Toggle AI\n\n"
            f"{'─'*32}\n"
            f"_AI requires owner approval per group_"
        )
        await query.answer()
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("◀️ Back", callback_data="menu_main")],
                [InlineKeyboardButton("❌ Close", callback_data="close_menu")],
            ]),
            parse_mode='Markdown'
        )
        return

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
        await query.edit_message_text(
            rules_text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("◀️ Back", callback_data="menu_main")],
                [InlineKeyboardButton("❌ Close", callback_data="close_menu")],
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
            await query.answer("❌ User identify nahi hua!", show_alert=True)
            return
        ch_id = update.effective_chat.id if update.effective_chat else 0
        if not ch_id:
            await query.answer("❌ Group mein use karo!", show_alert=True)
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

    elif data == "close_menu":
        try:
            await query.message.delete()
        except:
            await query.answer("✅ Closed!")
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
        start_text = (
            f"🛡️ *Suhani Bot* is active & protecting this group!\n"
            f"_Use /help for all commands._"
        )
        msg_id = await send_colored_message(ch.id, start_text, ckb_start_group())
        if not msg_id:
            await update.message.reply_text(
                start_text,
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton("📋 Commands", callback_data="menu_main"),
                        InlineKeyboardButton("📜 Rules", callback_data="show_rules"),
                    ]
                ])
            )
        return

    # DM — Owner panel
    if u.id == OWNER_ID:
        text = (
            f"╔{'═'*38}╗\n"
            f"║  👑  SUHANI BOT — OWNER PANEL   ║\n"
            f"╠{'═'*38}╣\n"
            f"║  v10.0  •  MongoDB  •  AI-Powered   ║\n"
            f"╚{'═'*38}╝\n\n"
            f"{'─'*38}\n"
            f"🌐 *GLOBAL CONTROLS*\n\n"
            f"  📢 `/broadcast <msg>` — All groups\n"
            f"  👥 `/groups` — Active group count\n"
            f"  📊 `/stats` — Full bot stats\n"
            f"  🗓️ `/globalmutes` — Global mute list\n"
            f"  🌐 `/autodelete <min>` — Global default\n\n"
            f"{'─'*38}\n"
            f"⚡ *MODERATION*\n\n"
            f"  💀 `/fban <id> [reason]` — Global ban\n"
            f"  ✅ `/gunban <id>` — Global unban\n"
            f"  🧹 `/gclearwarn <id>` — Clear all warns\n"
            f"  ⚡ `/power <id>` — Grant fban power\n"
            f"  🔻 `/unpower <id>` — Revoke power\n\n"
            f"{'─'*38}\n"
            f"🤖 *AI CONTROLS*\n\n"
            f"  ✅ `/aiapprove <id>` — Approve group\n"
            f"  🔴 `/airevoke <id>` — Revoke AI\n"
            f"  📋 `/aigroups` — AI approved list\n"
            f"  🎌 `/missinganime` — Missing requests\n\n"
            f"{'─'*38}\n"
            f"🪙 *SUHANI COIN CONTROLS*\n\n"
            f"  ✅ `/Accept_rep <group_id>` — Group ka rep coin-convertible banao\n"
            f"  🔒 `/Unaccept_rep <group_id>` — Coin-convertible hatao\n"
            f"  👥 `/earn_groups` — Members ke liye accepted groups ki link-list\n"
            f"  💸 Withdrawals — approve/reject buttons DM mein aate hain\n\n"
            f"{'─'*38}\n"
            f"🌐 `/gblacklist` • `/gwhitelist` — Global word lists\n"
            f"🤖 `/adexempt` — Autodelete exemptions\n"
        )
        await update.message.reply_text(
            text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("📊 Stats", callback_data="menu_stats"),
                    InlineKeyboardButton("🛡️ Protections", callback_data="menu_protection"),
                ]
            ])
        )
        return

    # DM — Regular user
    text = (
        f"╔{'═'*34}╗\n"
        f"║   🛡️  SUHANI PROTECTION BOT    ║\n"
        f"╠{'═'*34}╣\n"
        f"║      Group Protection Bot      ║\n"
        f"╚{'═'*34}╝\n\n"
        f"👋 *Hey {md_esc(u.first_name or 'there')}!*\n\n"
        f"Main groups ko protect karta hoon aur anime community\n"
        f"ko safe aur spam-free rakhta hoon! 🔥\n\n"
        f"{'─'*34}\n"
        f"📱 *YOUR COMMANDS*\n\n"
        f"  📜 `/rules` — Group ke rules dekho\n"
        f"  ⚠️ `/warnings` — Apni warnings check karo\n"
        f"  ⭐ `/rep` — Suhani Profile Card & Wallet\n"
        f"  💰 `/wallet` — Suhani Points & INR\n"
        f"  🏆 `/repboard` — Reputation Ranking\n"
        f"  📊 `/rankings` — Message activity rank (Group & Global)\n"
        f"  💰 `/earn_groups` — Groups jaha msg karke paisa kamao\n"
        f"  🆔 `/id` — Apna Telegram ID\n\n"
        f"{'─'*34}\n"
        f"💎 *REWARD SYSTEM*\n"
        f"_Thank You → +100 Rep | Warn maaf → 100 Rep_\n"
        f"_10,000 Rep (accepted group) → 1 Coin → ₹1_\n"
        f"_Min ₹10 withdrawal → `/withdraw`_\n\n"
        f"_Add me to your group & make me admin!_"
    )
    await update.message.reply_text(
        text,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("📋 All Commands", callback_data="menu_user"),
                InlineKeyboardButton("⚠️ Warn System", callback_data="menu_warns"),
            ],
            [
                InlineKeyboardButton("💸 Withdraw Info", callback_data=f"rep:wdinfo:{update.effective_user.id}"),
            ]
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
            f"╔{'═'*32}╗\n"
            f"║   👤  YOUR COMMANDS & INFO    ║\n"
            f"╚{'═'*32}╝\n\n"
            f"{'─'*32}\n"
            f"📜 `/rules` — View group rules\n"
            f"⚠️ `/warnings` — Check your warnings\n"
            f"⭐ `/rep` — Suhani Profile Card & Wallet\n"
            f"💰 `/wallet` — Suhani Points & INR value\n"
            f"🏆 `/repboard` — Reputation Leaderboard\n"
            f"📊 `/rankings` — Message activity rank (Group & Global)\n"
            f"💰 `/earn_groups` — Groups jaha msg karke paisa kamao\n"
            f"🆔 `/id` — Your Telegram ID\n\n"
            f"{'─'*32}\n"
            f"💡 _Thank You → +100 Rep | 10,000 Rep → 1 Coin → ₹1_\n"
            f"_Min ₹10 withdraw → `/withdraw` | Violations auto-detected!_"
        )
        return await update.message.reply_text(
            text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("📜 Rules", callback_data="show_rules"),
                    InlineKeyboardButton("⚠️ Warns Info", callback_data="menu_warns"),
                ],
                [
                    InlineKeyboardButton("🛡️ Protections", callback_data="menu_protection"),
                ]
            ])
        )

    # ── Admin / Owner full help ──────────────────────────────
    admin_text = (
        f"╔{'═'*34}╗\n"
        f"║   👮  ADMIN COMMANDS PANEL    ║\n"
        f"╚{'═'*34}╝\n\n"
        f"🔇 `/mute [sec]` — Mute user _(reply)_\n"
        f"🔊 `/unmute` — Unmute user _(reply)_\n"
        f"🔨 `/ban [reason]` — Ban user _(reply)_\n"
        f"🔓 `/unban <id>` — Unban user\n"
        f"⚠️ `/warn [reason]` — Warn user _(reply)_\n"
        f"♻️ `/resetwarnings` — Reset warnings _(reply)_\n"
        f"🗑️ `/del` — Delete message _(reply)_\n"
        f"🧹 `/purge` — Bulk delete from reply\n"
        f"🧪 `/testmute` — Test 35s mute _(reply)_\n"
        f"👑 `/immortal <id>` — Grant immunity\n"
        f"💀 `/unimmortal <id>` — Remove immunity\n"
        f"📋 `/immortals` — List immune users\n\n"
        f"{'─'*34}\n"
        f"⚙️ *SETTINGS*\n\n"
        f"📜 `/setrules <text>` — Set rules\n"
        f"🔗 `/setlinked` — Set linked channel\n"
        f"🎭 `/captcha on|off` — Toggle captcha\n"
        f"🗑️ `/sticker_delete <min>` — Sticker auto-del\n"
        f"⏱️ `/autodelete <min>` — Auto-delete msgs\n"
        f"⛔ `/addblacklist <word>` — Ban a word\n"
        f"✅ `/addwhitelist <word>` — Whitelist word\n"
        f"📋 `/blacklist` • `/whitelist` — View lists\n"
        f"📚 `/addteacher` — Mark user as teacher\n"
        f"❌ `/removeteacher` — Remove teacher\n"
        f"📋 `/teachers` — List all teachers\n"
    )

    if is_owner:
        admin_text += (
            f"\n{'─'*34}\n"
            f"👑 *OWNER ONLY*\n\n"
            f"🌐 `/autodelete <min>` _(DM)_ — Global default\n"
            f"💀 `/fban <id>` — Global ban all groups\n"
            f"✅ `/gunban <id>` — Global unban\n"
            f"🧹 `/gclearwarn <id>` — Clear all warns\n"
            f"⚡ `/power <id>` • `/unpower <id>` — Fban perms\n"
            f"📢 `/broadcast <msg>` — Message all groups\n"
            f"👥 `/groups` • `/stats` — Bot stats\n"
            f"🌐 `/gblacklist` • `/gwhitelist` — Global lists\n"
            f"🤖 `/adexempt <id>` — Autodelete exempt\n"
            f"🤖 `/aiapprove` • `/airevoke` • `/aigroups`\n"
            f"🎌 `/missinganime` — Missing anime requests\n"
        )

    admin_text += (
        f"\n{'─'*34}\n"
        f"⚠️ *Warn Scale:* W1→35s | W2→60s | W3→120s | W4→1wk 🌐"
    )

    await update.message.reply_text(
        admin_text,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🛡️ Protections", callback_data="menu_protection"),
                InlineKeyboardButton("⚙️ Settings", callback_data="menu_settings"),
            ],
            [
                InlineKeyboardButton("⚠️ Warn System", callback_data="menu_warns"),
                InlineKeyboardButton("📊 Stats", callback_data="menu_stats"),
            ]
        ])
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
    # Safe extraction — reply_to_message ho toh uska user, warna khud
    if update.message.reply_to_message and update.message.reply_to_message.from_user:
        tgt = update.message.reply_to_message.from_user
    else:
        tgt = update.effective_user
    if not tgt:
        return await update.message.reply_text("❌ Could not identify user (anonymous/channel reply).")
    if db.is_gmuted(tgt.id):
        msg = await update.message.reply_text(
            f"👤 {user_name(tgt)}\n\n"
            f"💀 *GLOBALLY MUTED* — 1 week ban active.",
            parse_mode='Markdown'
        )
        asyncio.create_task(delete_after(ctx, ch.id, msg.message_id, 600))
        return
    w = db.get_warnings(ch.id, tgt.id)
    bars = "🟥" * w + "⬜" * (4 - w)
    msg = await update.message.reply_text(
        f"📊 *Warning Status*\n"
        f"{'─'*20}\n\n"
        f"👤 {user_name(tgt)}\n"
        f"Count: `{w}/4`\n"
        f"Scale: {bars}",
        parse_mode='Markdown'
    )
    asyncio.create_task(delete_after(ctx, ch.id, msg.message_id, 600))


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
    group_ids = db.get_all_groups()
    if not group_ids:
        return await update.message.reply_text("👥 Koi group nahi mila.")

    status_msg = await update.message.reply_text(
        f"⏳ {len(group_ids)} groups ki details fetch ho rahi hain..."
    )

    lines = [f"👥 <b>Active Groups:</b> {len(group_ids)}\n"]
    for i, gid in enumerate(group_ids, 1):
        title, link = await _resolve_group_link(ctx, gid)
        title_safe = html.escape(title)
        if link:
            lines.append(f"{i}. <a href=\"{html.escape(link)}\">{title_safe}</a>")
        else:
            lines.append(f"{i}. {title_safe}")

    text = "\n".join(lines)
    # Telegram message limit ~4096 chars — split into chunks agar zyada groups hain
    chunks = [text[j:j+4000] for j in range(0, len(text), 4000)]
    await status_msg.delete()
    for chunk in chunks:
        await update.message.reply_text(chunk, parse_mode='HTML', disable_web_page_preview=True)


# ─── Helper: accepted group ka title/public-link nikaalo (aur missing ho to backfill karo) ──
async def _resolve_group_link(ctx: ContextTypes.DEFAULT_TYPE, gid: int):
    """Live Telegram se group ka title + public link fetch karta hai."""
    title, link = str(gid), None
    try:
        chat = await ctx.bot.get_chat(gid)
        title = chat.title or str(gid)
        if chat.username:
            link = f"https://t.me/{chat.username}"
        else:
            try:
                link = await ctx.bot.export_chat_invite_link(gid)
            except Exception:
                link = None
    except Exception:
        pass
    return title, link


async def _accepted_groups_with_links(ctx: ContextTypes.DEFAULT_TYPE):
    """
    Sab accepted groups laata hai. Jin groups ka title/link pehle se DB mein
    save nahi hai (purane /Accept_rep se add kiye gaye — feature ke pehle),
    unke liye live fetch karke DB mein backfill (save) kar deta hai, taaki
    dobara /Accept_rep chalane ki zaroorat na pade.
    """
    groups = db.get_accepted_rep_groups_full()
    result = []
    for g in groups:
        gid = g["_id"]
        title, link = g.get("title"), g.get("link")
        if not link:
            fetched_title, fetched_link = await _resolve_group_link(ctx, gid)
            title = fetched_title or title
            if fetched_link:
                link = fetched_link
            # Backfill DB taaki agli baar live-fetch na karna pade
            if title or link:
                db.accept_rep_group(gid, title=title, link=link)
        result.append({"_id": gid, "title": title or str(gid), "link": link})
    return result


# ─── /reputation ─── Owner-only: kisi bhi user ko manually rep do/kaato ────
async def reputation_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """
    Usage: /reputation <user_id> <amount>   (group mein chalao — usi group mein credit hota hai)
    Ya kisi user ko reply karke: /reputation <amount>
    Amount negative bhi ho sakta hai (rep kaatne ke liye).
    """
    if update.effective_user.id != OWNER_ID: return
    ch = update.effective_chat
    args = ctx.args

    target_id, amount = None, None
    if update.message.reply_to_message and args and len(args) >= 1:
        try:
            target_id = update.message.reply_to_message.from_user.id
            amount = int(args[0])
        except ValueError:
            pass
    elif args and len(args) >= 2:
        try:
            target_id = int(args[0])
            amount = int(args[1])
        except ValueError:
            pass

    if target_id is None or amount is None:
        return await update.message.reply_text(
            "⚙️ *Usage:*\n"
            "`/reputation <user_id> <amount>`\n"
            "_ya kisi user ko reply karke:_ `/reputation <amount>`\n\n"
            "_Group mein chalao — usi group ke rep balance mein credit\\/debit hoga._",
            parse_mode='Markdown'
        )
    if not ch or ch.type == "private":
        return await update.message.reply_text(
            "❌ Ise kisi group mein chalao (jis group ka rep balance update karna hai).",
            parse_mode='Markdown'
        )

    try:
        target_chat = await ctx.bot.get_chat(target_id)
        name = target_chat.first_name or str(target_id)
    except Exception:
        name = str(target_id)

    db.add_reputation(ch.id, target_id, amount, name)
    new_rep = db.get_reputation(ch.id, target_id)
    action = "diye gaye" if amount >= 0 else "kaate gaye"
    await update.message.reply_text(
        f"✅ `{abs(amount)}` reputation points user `{target_id}` ko {action} is group mein.\n"
        f"📊 Naya balance: `{new_rep}` rep",
        parse_mode='Markdown'
    )


# ─── /Accept_rep ─── Owner-only: group ka reputation Suhani Coin ke liye accept karo ──
async def accept_rep_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    if not ctx.args:
        groups = await _accepted_groups_with_links(ctx)
        if not groups:
            lines = "  <i>Koi group accepted nahi hai</i>"
        else:
            out = []
            for g in groups:
                title = html.escape(g["title"])
                link  = g.get("link")
                if link:
                    out.append(f"  • <a href=\"{html.escape(link)}\">{title}</a>  (<code>{g['_id']}</code>)")
                else:
                    out.append(f"  • {title}  (<code>{g['_id']}</code>) — ⚠️ link nahi mila")
            lines = "\n".join(out)
        return await update.message.reply_text(
            f"⚙️ <b>Usage:</b> <code>/Accept_rep &lt;group_id&gt;</code>\n\n"
            f"✅ <b>Accepted Groups</b> (Suhani Coin convertible):\n{lines}\n\n"
            f"👥 Members yeh list <code>/earn_groups</code> se dekh sakte hain.",
            parse_mode='HTML', disable_web_page_preview=True
        )
    try:
        gid = int(ctx.args[0])
    except ValueError:
        return await update.message.reply_text("❌ Group ID number mein do!")

    # Group ka title aur public/invite link fetch karo, taaki members
    # ko /earn_groups mein ek clickable link dikh sake.
    title, link = await _resolve_group_link(ctx, gid)

    db.accept_rep_group(gid, title=title, link=link)
    link_note = f"\n🔗 Link: {html.escape(link)}" if link else \
        "\n⚠️ Invite link nahi mil paya — bot ko is group mein admin (invite-link permission ke saath) banao."
    await update.message.reply_text(
        f"✅ Group <code>{gid}</code> (<b>{html.escape(title)}</b>) ab <b>accepted</b> hai!\n"
        f"Ab is group ka reputation Suhani Coin (₹) mein convert ho sakta hai."
        + link_note,
        parse_mode='HTML'
    )


# ─── /earn_groups ─── Public: accepted groups ki list, link ke saath ────
async def earn_groups_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """
    Sabhi 'accepted' groups (jinka reputation Suhani Coin/₹ mein convert hota hai)
    unke clickable invite link ke saath dikhata hai — taaki members ko pata chale
    konse group mein message karke paisa kama sakte hain.
    """
    groups = await _accepted_groups_with_links(ctx)
    if not groups:
        return await update.message.reply_text(
            "📉 <i>Abhi koi group Suhani Coin ke liye accepted nahi hai.</i>",
            parse_mode='HTML'
        )
    lines = []
    for i, g in enumerate(groups, 1):
        title = html.escape(g["title"])
        link  = g.get("link")
        if link:
            lines.append(f"{i}. <a href=\"{html.escape(link)}\">{title}</a>")
        else:
            lines.append(f"{i}. {title} — ⚠️ link jald aayega")
    text = (
        f"💰 <b>EARN GROUPS</b>\n"
        f"<i>Inme active rehke Suhani Coin (₹) kamao</i>\n"
        f"{'─'*28}\n\n" + "\n".join(lines) +
        f"\n\n💡 <i>Thank You reply se rep milta hai • 10,000 rep = ₹1</i>"
    )
    await update.message.reply_text(text, parse_mode='HTML', disable_web_page_preview=True)


# ─── /Unaccept_rep ─── Owner-only: group ka reputation coin-convertible band karo ──
async def unaccept_rep_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    if not ctx.args:
        return await update.message.reply_text("⚙️ *Usage:* `/Unaccept_rep <group_id>`", parse_mode='Markdown')
    try:
        gid = int(ctx.args[0])
    except ValueError:
        return await update.message.reply_text("❌ Group ID number mein do!")
    db.unaccept_rep_group(gid)
    await update.message.reply_text(
        f"🔒 Group `{gid}` ab *not accepted* hai.\n"
        f"Is group ka reputation ab sirf warn maaf karne ke kaam aayega, coin nahi banega.",
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


# ─── /gclearwarn ────────────────────────────────────────────
async def gclearwarn_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """
    Owner + /power users — saare groups se ek saath user ki warnings clear karo.
    Usage: /gclearwarn <user_id | @username>
           Reply to message + /gclearwarn
    """
    caller = update.effective_user.id
    if caller != OWNER_ID and not db.is_powered(caller):
        return await update.message.reply_text("❌ Owner ya powered user hi yeh command use kar sakte hain!")

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
                    f"❌ User nahi mila: `{raw}`", parse_mode='Markdown'
                )
    else:
        return await update.message.reply_text(
            "❌ Usage: `/gclearwarn <user_id | @username>`\n"
            "Ya user ke message pe reply karke `/gclearwarn` likho.",
            parse_mode='Markdown'
        )

    deleted = db.global_clear_warnings(target_id)

    await update.message.reply_text(
        f"🧹 *Global Warnings Cleared!*\n"
        f"{'─'*28}\n\n"
        f"👤 User: {target_name or f'`{target_id}`'}\n"
        f"🗑️ Removed: `{deleted}` warning record(s) across all groups\n\n"
        f"_Ab yeh user fresh start se hai — koi warning nahi._",
        parse_mode='Markdown'
    )


# ─── /adexempt ──────────────────────────────────────────────
# ─── /aimod ─────────────────────────────────────────────────
async def aimod_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Admin — toggle AI moderation on/off for this group (only if owner approved)."""
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

    g = db.get_group(ch.id)
    # Check owner approval
    if not g.get("ai_approved", False):
        return await update.message.reply_text(
            "⚠️ *Is group ke liye AI approved nahi hai!*\n\n"
            "_Bot owner se `/aiapprove` karwao pehle._",
            parse_mode='Markdown'
        )

    if not ctx.args or ctx.args[0].lower() not in ('on', 'off'):
        status = "🟢 ON" if g.get("aimod", False) else "🔴 OFF"
        return await update.message.reply_text(
            f"🤖 *AI Moderation*\n"
            f"{'─'*25}\n\n"
            f"Status: {status}\n"
            f"Owner Approved: ✅\n\n"
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


# ─── /missinganime ──────────────────────────────────────────
async def missinganime_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """
    Owner only — missing anime list dekhna aur clear karna.
    /missinganime          → top 30 list
    /missinganime clear    → sab clear
    /missinganime clear <name> → ek entry clear
    """
    if update.effective_user.id != OWNER_ID:
        return

    args = ctx.args or []

    # Clear command
    if args and args[0].lower() == "clear":
        if len(args) > 1:
            name = ' '.join(args[1:])
            db.clear_missing_anime(name)
            return await update.message.reply_text(
                f"✅ `{name}` missing list se remove kar diya!",
                parse_mode='Markdown'
            )
        else:
            db.clear_missing_anime()
            return await update.message.reply_text("✅ Puri missing anime list clear kar di!")

    # Show list
    missing = db.get_missing_anime_list(30)
    if not missing:
        return await update.message.reply_text(
            "📋 *Missing Anime List khali hai!*\n\n"
            "_Koi anime abhi missing report nahi hua._",
            parse_mode='Markdown'
        )

    lines = []
    for i, doc in enumerate(missing, 1):
        name = doc.get("display_name", doc["_id"])
        count = doc.get("count", 1)
        lines.append(f"  {i}. `{name}` — {count}x request")

    text = (
        f"📋 *Missing Anime Requests*\n"
        f"{'─'*30}\n\n"
        + "\n".join(lines) +
        f"\n\n{'─'*30}\n"
        f"_Total: {len(missing)} anime_\n"
        f"Use `/missinganime clear` to reset list."
    )
    await update.message.reply_text(text, parse_mode='Markdown')


# ─── /aiapprove ─────────────────────────────────────────────
async def aiapprove_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """
    Owner only — approve a group to use AI moderation.
    Use in group: /aiapprove        → approves current group
    Use in DM:    /aiapprove <id>   → approves that group by chat_id
    """
    if update.effective_user.id != OWNER_ID:
        return  # silent ignore

    ch = update.effective_chat

    # ── DM mein use kiya ──────────────────────────────────────
    if ch.type == "private":
        if not ctx.args:
            return await update.message.reply_text(
                "❌ *DM mein chat ID dena zaroori hai!*\n\n"
                "Usage: `/aiapprove <group_chat_id>`\n\n"
                "Example:\n"
                "`/aiapprove -1001234567890`\n\n"
                "_Group ka ID pane ke liye group mein `/id` use karo._",
                parse_mode='Markdown'
            )
        try:
            target_chat_id = int(ctx.args[0])
        except ValueError:
            return await update.message.reply_text(
                f"❌ Invalid ID: `{ctx.args[0]}`\n\n"
                f"_Sirf number dalo, jaise `-1001234567890`_",
                parse_mode='Markdown'
            )
    else:
        # ── Group mein use kiya ───────────────────────────────
        target_chat_id = ch.id

    # DB mein save karo
    try:
        db.groups.update_one(
            {"_id": target_chat_id},
            {"$set": {"ai_approved": True, "aimod": True}},
            upsert=True
        )
        await update.message.reply_text(
            f"✅ *AI Approved!*\n"
            f"{'─'*28}\n\n"
            f"🤖 Group `{target_chat_id}` ke liye:\n"
            f"  • AI Approved: ✅\n"
            f"  • AI Status: 🟢 ON\n\n"
            f"_Group admin `/aimod on/off` se control kar sakte hain._\n"
            f"_Revoke karna ho toh: `/airevoke {target_chat_id}`_",
            parse_mode='Markdown'
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Error: `{e}`", parse_mode='Markdown')


# ─── /airevoke ──────────────────────────────────────────────
async def airevoke_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """
    Owner only — revoke AI approval from a group.
    Use in group: /airevoke
    Use in DM:    /airevoke <chat_id>
    """
    if update.effective_user.id != OWNER_ID:
        return  # silent ignore

    ch = update.effective_chat

    if ch.type == "private":
        if not ctx.args:
            return await update.message.reply_text(
                "❌ *DM mein chat ID dena zaroori hai!*\n\n"
                "Usage: `/airevoke <group_chat_id>`\n\n"
                "Example:\n"
                "`/airevoke -1001234567890`\n\n"
                "_Approved groups dekhne ke liye `/aigroups` use karo._",
                parse_mode='Markdown'
            )
        try:
            target_chat_id = int(ctx.args[0])
        except ValueError:
            return await update.message.reply_text(
                f"❌ Invalid ID: `{ctx.args[0]}`\n\n"
                f"_Sirf number dalo, jaise `-1001234567890`_",
                parse_mode='Markdown'
            )
    else:
        target_chat_id = ch.id

    try:
        db.groups.update_one(
            {"_id": target_chat_id},
            {"$set": {"ai_approved": False, "aimod": False}},
            upsert=True
        )
        await update.message.reply_text(
            f"🔴 *AI Revoked!*\n"
            f"{'─'*28}\n\n"
            f"Group `{target_chat_id}` ke liye:\n"
            f"  • AI Approved: ❌\n"
            f"  • AI Status: 🔴 OFF\n\n"
            f"_AI wahan kaam nahi karega._\n"
            f"_Wapas enable karna ho: `/aiapprove {target_chat_id}`_",
            parse_mode='Markdown'
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Error: `{e}`", parse_mode='Markdown')


# ─── /aigroups ──────────────────────────────────────────────
async def aigroups_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Owner only — list all AI-approved groups."""
    if update.effective_user.id != OWNER_ID:
        return

    all_groups = db.get_all_groups()
    approved = []
    for gid in all_groups:
        g = db.get_group(gid)
        if g.get("ai_approved", False):
            status = "🟢 ON" if g.get("aimod", False) else "🟡 Approved/OFF"
            approved.append(f"  • `{gid}` — {status}")

    if not approved:
        return await update.message.reply_text(
            "📋 *AI Approved Groups: 0*\n\n"
            "_Kisi bhi group ko approve nahi kiya gaya abhi._\n"
            "Use `/aiapprove` in a group or `/aiapprove <chat_id>` in DM.",
            parse_mode='Markdown'
        )

    await update.message.reply_text(
        f"🤖 *AI Approved Groups* ({len(approved)})\n"
        f"{'─'*30}\n\n"
        + "\n".join(approved) +
        f"\n\n_Use `/airevoke <chat_id>` to remove._",
        parse_mode='Markdown'
    )


# ─── /addteacher ────────────────────────────────────────────
async def addteacher_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Admin only — mark a user as teacher (special promo handling)."""
    ch = update.effective_chat
    if ch.type == "private":
        return await update.message.reply_text("❌ Use in group!")
    if not await sender_is_admin(ctx, update):
        return await update.message.reply_text("❌ Admins only!")

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
                    f"❌ User nahi mila: `{ctx.args[0]}`", parse_mode='Markdown'
                )
    else:
        return await update.message.reply_text(
            "❌ Usage: `/addteacher <id>` ya reply karo user ke message pe",
            parse_mode='Markdown'
        )

    db.add_teacher(ch.id, target_id)
    await update.message.reply_text(
        f"📚 *Teacher Added!*\n"
        f"{'─'*28}\n\n"
        f"👤 User: `{target_id}`{f'  ({target_name})' if target_name else ''}\n\n"
        f"🛡️ *Special handling:*\n"
        f"  • 1st promo → sirf polite warning, no mute\n"
        f"  • 2nd promo → 🔇 10 min mute\n"
        f"  • 3rd promo → 🔇 40 min mute\n"
        f"  • 4th promo → 🔇 70 min mute _(+30 min har baar badhega)_\n\n"
        f"Use `/removeteacher {target_id}` to remove.",
        parse_mode='Markdown'
    )


# ─── /removeteacher ─────────────────────────────────────────
async def removeteacher_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ch = update.effective_chat
    if ch.type == "private":
        return await update.message.reply_text("❌ Use in group!")
    if not await sender_is_admin(ctx, update):
        return await update.message.reply_text("❌ Admins only!")

    target_id = None
    if update.message.reply_to_message:
        target_id = update.message.reply_to_message.from_user.id
    elif ctx.args:
        try:
            target_id = int(ctx.args[0])
        except ValueError:
            return await update.message.reply_text("❌ Invalid ID!")
    else:
        return await update.message.reply_text(
            "❌ Usage: `/removeteacher <id>`", parse_mode='Markdown'
        )

    db.remove_teacher(ch.id, target_id)
    db.reset_teacher_promo_count(ch.id, target_id)
    await update.message.reply_text(
        f"✅ Teacher status removed for `{target_id}`.\n"
        f"_Unka promo count bhi reset ho gaya._",
        parse_mode='Markdown'
    )


# ─── /teachers ──────────────────────────────────────────────
async def teachers_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ch = update.effective_chat
    if ch.type == "private":
        return await update.message.reply_text("❌ Use in group!")
    if not await sender_is_admin(ctx, update):
        return await update.message.reply_text("❌ Admins only!")

    teachers = db.get_teachers(ch.id)
    if not teachers:
        return await update.message.reply_text(
            "📚 Is group mein koi teacher nahi hai abhi.\n\n"
            "_Use `/addteacher` to add one._",
            parse_mode='Markdown'
        )

    lines = []
    for tid in teachers:
        cnt = db.get_teacher_promo_count(ch.id, tid)
        lines.append(f"  • `{tid}` — promo violations: `{cnt}`")

    await update.message.reply_text(
        f"📚 *TEACHERS LIST*\n"
        f"{'─'*28}\n\n"
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
#  /rankings — Message-count based (Today / 2 Weeks / Month)
#  Group + Global dono ek hi command mein, button se switch hota hai.
#  NOTE: Yeh REPUTATION se ALAG hai — sirf "kitne message bheje"
#  ke hisaab se ranking hoti hai.
#
#  Names ab tg://user?id=<id> link ke roop mein clickable hain —
#  isse @username na hone par bhi profile khulta hai, aur usernames
#  mein underscore (_) hone par koi backslash/parsing bug nahi aata
#  (HTML parse_mode + html.escape use hota hai, Markdown escaping nahi).
# ═══════════════════════════════════════════════════════════
LB_PERIOD_LABEL = {"today": "📅 Today", "2weeks": "🗓 Last 2 Weeks", "month": "📆 Last Month"}
LB_PERIOD_ORDER = ["today", "2weeks", "month"]

def build_rankings_keyboard(scope, chat_id, active_period):
    """
    scope: 'g' (group) ya 'a' (all/global).
    chat_id: origin GROUP chat id (0 agar command private mein aur koi group context nahi hai) —
             yeh hamesha group id rehta hai, scope switch karne par bhi, taaki "Group" button
             wapas usi group ki ranking dikha sake.
    """
    scope_row = []
    if chat_id:
        label_g = "• 👥 Group •" if scope == "g" else "👥 Group"
        scope_row.append(InlineKeyboardButton(label_g, callback_data=f"lbd:g:{active_period}:{chat_id}"))
    label_a = "• 🌐 Global •" if scope == "a" else "🌐 Global"
    scope_row.append(InlineKeyboardButton(label_a, callback_data=f"lbd:a:{active_period}:{chat_id}"))

    period_row = []
    for p in LB_PERIOD_ORDER:
        label = LB_PERIOD_LABEL[p]
        if p == active_period:
            label = f"• {label} •"
        period_row.append(InlineKeyboardButton(label, callback_data=f"lbd:{scope}:{p}:{chat_id}"))

    return InlineKeyboardMarkup([scope_row, period_row])

def build_lb_text(entries, period, scope_title):
    period_label = LB_PERIOD_LABEL[period]
    if not entries:
        return (
            f"🏆 <b>{html.escape(scope_title)}</b>\n"
            f"<i>{html.escape(period_label)}</i>\n"
            f"{'─'*28}\n\n"
            f"📉 Is period mein koi message activity nahi mili!"
        )
    medals = ["🥇", "🥈", "🥉"]
    lines = []
    for i, entry in enumerate(entries):
        rank = medals[i] if i < 3 else f"<code>{i+1}.</code>"
        uid = entry.get("_id")
        raw_name = entry.get("name") or str(uid)
        # Purane data mein pehle se md_esc() se escape hoke backslash "\_" jaisa
        # literally save ho chuka ho sakta hai (old bug) — usko yahin clean karo,
        # taaki naya message aane ka wait kiye bina bhi turant sahi dikhe.
        # Real Telegram username/name mein backslash kabhi valid nahi hota,
        # isliye ise hata dena hamesha safe hai.
        clean_name = str(raw_name).replace('\\', '')
        name_esc = html.escape(clean_name)
        # tg://user link — hamesha clickable, chahe @username ho ya na ho
        name_html = f'<a href="tg://user?id={uid}">{name_esc}</a>' if uid else name_esc
        total = entry.get("total", 0)
        lines.append(f"{rank} {name_html} — <b>{total}</b> messages")
    return (
        f"🏆 <b>{html.escape(scope_title)}</b>\n"
        f"<i>{html.escape(period_label)}</i>\n"
        f"{'─'*28}\n\n" + "\n".join(lines)
    )


# ─── /rankings ─── Group + Global message-activity ranking, button se toggle ──
async def rankings_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ch = update.effective_chat
    origin_id = ch.id if ch.type != "private" else 0
    scope = "g" if origin_id else "a"
    try:
        if scope == "g":
            entries = db.get_activity_leaderboard(origin_id, period="today", limit=10)
            text = build_lb_text(entries, "today", "GROUP RANKINGS")
        else:
            entries = db.get_global_activity_leaderboard(period="today", limit=10)
            text = build_lb_text(entries, "today", "GLOBAL RANKINGS")
        kb = build_rankings_keyboard(scope, origin_id, "today")
        msg = await update.message.reply_text(text, parse_mode='HTML', reply_markup=kb, disable_web_page_preview=True)
        if origin_id:
            asyncio.create_task(delete_after(ctx, origin_id, msg.message_id, 600))
    except Exception as e:
        await update.message.reply_text(f"❌ Rankings load nahi hui: <code>{html.escape(str(e))}</code>", parse_mode='HTML')


# ─── /rankings button callback — scope (Group/Global) aur period switch ───
async def rankings_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    try:
        _, scope, period, chat_id_str = query.data.split(":")
        chat_id = int(chat_id_str)
    except Exception:
        return

    if period not in LB_PERIOD_LABEL:
        return

    try:
        if scope == "g" and chat_id:
            entries = db.get_activity_leaderboard(chat_id, period=period, limit=10)
            text = build_lb_text(entries, period, "GROUP RANKINGS")
        else:
            scope = "a"
            entries = db.get_global_activity_leaderboard(period=period, limit=10)
            text = build_lb_text(entries, period, "GLOBAL RANKINGS")
        kb = build_rankings_keyboard(scope, chat_id, period)

        await query.edit_message_text(text, parse_mode='HTML', reply_markup=kb, disable_web_page_preview=True)
    except Exception:
        pass


# ═══════════════════════════════════════════════════════════
#  DAILY GLOBAL #1 AUTO-REWARD
#  Har din (server-time midnight ke thodi der baad) chalta hai —
#  PICHLE poore din ka GLOBAL (sab groups milaake) #1 message-sender
#  ko 1000 Reputation Points FREE mein milte hain, uske sabse active
#  group mein credit hoke (taaki warn-maafi/Suhani-Coin dono kaam karein
#  agar wo group accepted hai).
# ═══════════════════════════════════════════════════════════
DAILY_WINNER_REWARD = 1000

async def daily_global_winner_job(ctx: ContextTypes.DEFAULT_TYPE):
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

    # Idempotency — agar bot restart hoke job dobara chal jaye to dobara na de
    if db.was_daily_winner_awarded(yesterday):
        return

    top = db.get_global_activity_top_for_date(yesterday, limit=1)
    if not top:
        return

    winner = top[0]
    user_id = winner.get("_id")
    if not user_id:
        return

    win_chat_id = db.get_most_active_group_for_user_on_date(user_id, yesterday)
    if not win_chat_id:
        return

    name = winner.get("name") or str(user_id)
    db.add_reputation(win_chat_id, user_id, DAILY_WINNER_REWARD, name)
    db.mark_daily_winner_awarded(yesterday, user_id, win_chat_id)

    total_msgs = winner.get("total", 0)
    announce = (
        f"🏆 <b>DAILY GLOBAL #1!</b>\n\n"
        f'🎉 <a href="tg://user?id={user_id}">{html.escape(str(name))}</a> ne kal '
        f"({html.escape(yesterday)}) sabse zyada <b>{total_msgs}</b> messages bheje "
        f"— sabhi groups milaake!\n\n"
        f"⭐ Reward: <b>+{DAILY_WINNER_REWARD} Reputation Points</b> (free!) 🎁"
    )
    # Winner ke sabse active group mein announce karo
    try:
        await ctx.bot.send_message(win_chat_id, announce, parse_mode='HTML')
    except Exception:
        pass
    # Owner ko bhi log bhej do
    try:
        if OWNER_ID:
            await ctx.bot.send_message(
                OWNER_ID,
                f"🏆 Daily Global Winner ({html.escape(yesterday)}): "
                f'<a href="tg://user?id={user_id}">{html.escape(str(name))}</a> '
                f"(id <code>{user_id}</code>) ko group <code>{win_chat_id}</code> mein "
                f"+{DAILY_WINNER_REWARD} free rep mila!",
                parse_mode='HTML'
            )
    except Exception:
        pass


# ─── /withdraw ─── Suhani Coin withdrawal request ───────────
async def withdraw_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """
    Usage: /withdraw <coins> <upi_id/detail>
    User apna Suhani Coin withdrawal request bhejta hai — owner ko notify
    hota hai approve/reject buttons ke saath. Coins tabhi minus hote hain
    (via withdrawn_coins ledger) jab owner APPROVE kare — reject par kuch
    nahi katega, user dobara request kar sakta hai.
    """
    usr = update.effective_user
    if not usr:
        return
    if not ctx.args or len(ctx.args) < 2:
        wallet = db.get_suhani_points(usr.id)
        return await update.message.reply_text(
            f"⚙️ *Usage:* `/withdraw <coins> <UPI ID / payment detail>`\n\n"
            f"🪙 Available Coins: `{wallet['coins']}` (₹{wallet['coins']})\n"
            f"Min withdrawal: `{MIN_WITHDRAW_COINS}` coins (₹{MIN_WITHDRAW_COINS})\n\n"
            f"_Example:_ `/withdraw 10 rahul@upi`",
            parse_mode='Markdown'
        )
    try:
        req_coins = int(ctx.args[0])
    except ValueError:
        return await update.message.reply_text("❌ Coins ek number hona chahiye! Example: `/withdraw 10 rahul@upi`", parse_mode='Markdown')

    detail = ' '.join(ctx.args[1:]).strip()
    if req_coins < MIN_WITHDRAW_COINS:
        return await update.message.reply_text(
            f"❌ Min withdrawal `{MIN_WITHDRAW_COINS}` coins hai (₹{MIN_WITHDRAW_COINS}).",
            parse_mode='Markdown'
        )

    wallet = db.get_suhani_points(usr.id)
    pending_already = db.get_pending_withdrawal_coins(usr.id)
    if req_coins + pending_already > wallet["coins"]:
        return await update.message.reply_text(
            f"❌ Insufficient balance!\n"
            f"🪙 Available: `{wallet['coins']}`  •  Already pending: `{pending_already}`",
            parse_mode='Markdown'
        )

    req_id = db.create_withdrawal(usr.id, user_name(usr, escape=False), req_coins, detail)
    await update.message.reply_text(
        f"✅ *Withdrawal Request Submitted\\!*\n\n"
        f"🪙 Coins: `{req_coins}` \\(₹{req_coins}\\)\n"
        f"💳 Detail: `{md_esc(detail)}`\n"
        f"🆔 Request ID: `{req_id}`\n\n"
        f"_Owner review karega aur payment jaldi bhej dega\\._",
        parse_mode='MarkdownV2'
    )

    # ── Owner ko notify karo, approve/reject buttons ke saath ──
    try:
        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ Approve & Paid", callback_data=f"wd:approve:{req_id}"),
            InlineKeyboardButton("❌ Reject",          callback_data=f"wd:reject:{req_id}"),
        ]])
        await ctx.bot.send_message(
            OWNER_ID,
            f"💸 *NEW WITHDRAWAL REQUEST*\n{'─'*26}\n\n"
            f"👤 User: {user_name(usr)} \\(`{usr.id}`\\)\n"
            f"🪙 Coins: `{req_coins}` \\(₹{req_coins}\\)\n"
            f"💳 Detail: `{md_esc(detail)}`\n"
            f"🆔 ID: `{req_id}`",
            parse_mode='MarkdownV2',
            reply_markup=kb
        )
    except Exception:
        pass


async def withdraw_approval_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Owner-only: withdrawal request ko approve (paid) ya reject karo."""
    query = update.callback_query
    if not query or not query.from_user or query.from_user.id != OWNER_ID:
        return await query.answer("❌ Sirf owner isse use kar sakta hai!", show_alert=True)
    await query.answer()
    try:
        _, action, req_id = query.data.split(":", 2)
    except ValueError:
        return
    req = db.get_withdrawal(req_id)
    if not req:
        return await query.edit_message_text("❌ Request nahi mili \\(shayad already resolved\\)\\.", parse_mode='MarkdownV2')
    if req.get("status") != "pending":
        return await query.edit_message_text(f"ℹ️ Yeh request already `{req['status']}` hai\\.", parse_mode='MarkdownV2')

    if action == "approve":
        db.set_withdrawal_status(req_id, "paid")
        await query.edit_message_text(
            f"✅ *PAID* — `{req['coins']}` coins \\(₹{req['coins']}\\) settle ho gaye\\.\n"
            f"👤 User ID: `{req['user_id']}`",
            parse_mode='MarkdownV2'
        )
        try:
            await ctx.bot.send_message(
                req["user_id"],
                f"✅ *Aapki withdrawal approve ho gayi\\!*\n\n"
                f"🪙 Coins: `{req['coins']}` \\(₹{req['coins']}\\) bhej diye gaye hain\\.",
                parse_mode='MarkdownV2'
            )
        except Exception:
            pass
    elif action == "reject":
        db.set_withdrawal_status(req_id, "rejected")
        await query.edit_message_text(
            f"❌ *REJECTED* — `{req['coins']}` coins ka request reject kiya gaya\\.\n"
            f"👤 User ID: `{req['user_id']}`",
            parse_mode='MarkdownV2'
        )
        try:
            await ctx.bot.send_message(
                req["user_id"],
                f"❌ *Aapki withdrawal request reject ho gayi\\.*\n\n"
                f"Coins wapas balance mein available hain, dobara request kar sakte ho\\.",
                parse_mode='MarkdownV2'
            )
        except Exception:
            pass


# ─── /rep ─── Suhani Points Wallet + Reputation Card ───────
async def rep_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ch = update.effective_chat
    # Works in group + private (private mein sirf own wallet)
    if update.message.reply_to_message and update.message.reply_to_message.from_user:
        tgt = update.message.reply_to_message.from_user
    else:
        tgt = update.effective_user
    if not tgt:
        return await update.message.reply_text("❌ User identify nahi hua!")

    # ── Data fetch ───────────────────────────────────────────
    group_rep   = db.get_reputation(ch.id, tgt.id) if ch.type != "private" else 0
    total_rep   = db.get_total_reputation(tgt.id)
    wallet      = db.get_suhani_points(tgt.id)
    coins       = wallet["coins"]
    is_accepted = db.is_rep_group_accepted(ch.id) if ch.type != "private" else False

    # Group rank
    if ch.type != "private":
        top_list    = db.get_reputation_top(ch.id, limit=50)
        group_rank  = next((i + 1 for i, d in enumerate(top_list) if d.get("user_id") == tgt.id), None)
    else:
        group_rank = None

    # Global rank (all groups combined)
    global_top  = db.get_global_reputation_top(limit=50)
    global_rank = next((i + 1 for i, d in enumerate(global_top) if d.get("_id") == tgt.id), None)

    # ── Progress bar toward next Suhani Coin (10,000 rep, convertible groups only) ──
    progress   = wallet["convertible_rep"] % REP_PER_SUHANI_COIN
    bar_filled = progress // (REP_PER_SUHANI_COIN // 10)
    bar_empty  = 10 - bar_filled
    prog_bar   = "█" * bar_filled + "░" * bar_empty
    pts_needed = REP_PER_SUHANI_COIN - progress

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

    # ── Min withdrawal check ──────────────────────────────────
    can_withdraw = coins >= MIN_WITHDRAW_COINS

    rank_group_txt = f"#{group_rank}" if group_rank else "Unranked"
    rank_global_txt = f"#{global_rank}" if global_rank else "Unranked"

    # ── Build reply text (Markdown v1) ─────────────────────────
    name_safe = user_name(tgt, escape=False)
    accepted_line = "✅ Yeh group Suhani Coin ke liye *accepted* hai" if is_accepted else \
                    ("🔒 Yeh group accepted nahi hai — rep sirf warn maaf karne ke kaam aayega" if ch.type != "private" else "")

    text = (
        f"╔══════════════════════════╗\n"
        f"║  ⭐  SUHANI PROFILE CARD  ║\n"
        f"╚══════════════════════════╝\n\n"
        f"👤 *{name_safe}*\n"
        f"🏷️ Tier: *{tier}*\n\n"
        f"{'─'*28}\n"
        f"📊 *REPUTATION*\n"
        f"  🏠 Group Rep:  `{group_rep}` pts  •  Rank `{rank_group_txt}`\n"
        f"  🌐 Total Rep:  `{total_rep}` pts  •  Global `{rank_global_txt}`\n"
        f"  💠 Convertible Rep: `{wallet['convertible_rep']}` pts\n"
        + (f"  {accepted_line}\n" if accepted_line else "") +
        f"\n⚡ *Next Suhani Coin*\n"
        f"  [{prog_bar}] `{progress}/{REP_PER_SUHANI_COIN}`\n"
        f"  _{pts_needed} more convertible rep → +1 Suhani Coin_\n\n"
        f"{'─'*28}\n"
        f"💰 *SUHANI WALLET*\n"
        f"  🪙 Suhani Coins: `{coins}`\n"
        f"  💵 INR Value:    `₹{coins}`\n"
        f"  {'✅ Withdrawal available!' if can_withdraw else f'🔒 Min {MIN_WITHDRAW_COINS} coins needed  •  {max(0,MIN_WITHDRAW_COINS-coins)} more remaining'}\n\n"
        f"{'─'*28}\n"
        f"📖 *HOW IT WORKS*\n"
        f"  • Reply kisi ko *Thank You* → +{REP_PER_THANK} Rep\n"
        f"  • 3 baar max de sakte ho daily\n"
        f"  • 1 warning maaf = {REP_PER_WARN_REMOVE} rep (auto-deduct)\n"
        f"  • {REP_PER_SUHANI_COIN} Convertible Rep = 1 Suhani Coin = ₹1\n"
        f"  • Min ₹{MIN_WITHDRAW_COINS} withdrawal • /withdraw se request karo\n\n"
        f"{'─'*28}\n"
        f"💸 *WITHDRAW* → `/withdraw` command use karo\n"
        f"_/repboard — Group reputation ranking_"
    )

    # ── Keyboard ──────────────────────────────────────────────
    kb_rows = [
        [InlineKeyboardButton("🏆 Rep Leaderboard", callback_data=f"rep:board:{ch.id}"),
         InlineKeyboardButton("💰 My Wallet", callback_data=f"rep:wallet:{tgt.id}")]
    ]
    if can_withdraw:
        kb_rows.append([InlineKeyboardButton(
            "💸 Request Withdrawal", callback_data=f"rep:wdinfo:{tgt.id}"
        )])
    kb = InlineKeyboardMarkup(kb_rows)

    msg = await update.message.reply_text(text, parse_mode='Markdown', reply_markup=kb)
    if ch.type != "private":
        asyncio.create_task(delete_after(ctx, ch.id, msg.message_id, 600))


# ─── /wallet ─── Suhani Points wallet (DM + group) ───────────
async def wallet_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    usr = update.effective_user
    ch  = update.effective_chat
    if not usr:
        return
    total_rep  = db.get_total_reputation(usr.id)
    wallet     = db.get_suhani_points(usr.id)
    coins      = wallet["coins"]
    progress   = wallet["convertible_rep"] % REP_PER_SUHANI_COIN
    bar_filled = progress // (REP_PER_SUHANI_COIN // 10)
    prog_bar   = "█" * bar_filled + "░" * (10 - bar_filled)
    can_withdraw = coins >= MIN_WITHDRAW_COINS

    text = (
        f"╔═══════════════════════╗\n"
        f"║  💰  SUHANI WALLET     ║\n"
        f"╚═══════════════════════╝\n\n"
        f"👤 *{user_name(usr)}*\n\n"
        f"{'─'*26}\n"
        f"🪙 Suhani Coins:   `{coins}`\n"
        f"🌐 Total Rep:      `{total_rep} pts`\n"
        f"💠 Convertible Rep: `{wallet['convertible_rep']} pts`\n"
        f"💵 INR Value:      `₹{coins}`\n\n"
        f"⚡ *Next Coin*\n"
        f"  [{prog_bar}] `{progress}/{REP_PER_SUHANI_COIN} rep`\n\n"
        f"{'─'*26}\n"
        f"📋 *CONVERSION RATES*\n"
        f"  {REP_PER_SUHANI_COIN} Convertible Rep  →  1 Suhani Coin\n"
        f"  1 Coin  →  ₹1\n"
        f"  Min: {MIN_WITHDRAW_COINS} Coins = ₹{MIN_WITHDRAW_COINS} withdrawal\n\n"
        f"{'─'*26}\n"
        f"ℹ️ _Sirf accepted groups ka rep hi coin banta hai._\n"
        f"{'✅ *Withdrawal Ready!*' if can_withdraw else f'🔒 Need `{max(0,MIN_WITHDRAW_COINS-coins)}` more Coins'}\n"
        f"💸 Withdraw → `/withdraw` command use karo"
    )
    kb_rows = [[InlineKeyboardButton("🏆 Rep Board", callback_data="rep:board:0")]]
    if can_withdraw:
        kb_rows[0].insert(0, InlineKeyboardButton("✅ Request Withdrawal", callback_data=f"rep:wdinfo:{usr.id}"))
    kb = InlineKeyboardMarkup(kb_rows)
    msg = await update.message.reply_text(text, parse_mode='Markdown', reply_markup=kb)
    if ch.type != "private":
        asyncio.create_task(delete_after(ctx, ch.id, msg.message_id, 300))


# ─── /repboard ─── Reputation Leaderboard (Group + Global) ────
async def repboard_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ch = update.effective_chat
    if ch.type == "private":
        return await update.message.reply_text(
            "❌ Ise group mein use karo!",
            parse_mode='Markdown'
        )

    medals = ["🥇", "🥈", "🥉"]
    rank_emojis = ["4️⃣","5️⃣","6️⃣","7️⃣","8️⃣","9️⃣","🔟"]

    is_accepted = db.is_rep_group_accepted(ch.id)

    # ── Group leaderboard ──────────────────────────────────────
    group_top = db.get_reputation_top(ch.id, limit=10)
    # ── Global leaderboard ────────────────────────────────────
    global_top = db.get_global_reputation_top(limit=10)

    def build_board_lines(entries, key_pts="points", key_id="user_id"):
        if not entries:
            return ["  📉 _Koi data nahi mila!_"]
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

    accepted_note = "✅ *Accepted* — is group ka rep Suhani Coin mein convert hota hai" if is_accepted \
        else "🔒 *Not Accepted* — is group ka rep sirf warn maaf karne ke kaam aayega"

    text = (
        f"╔{'═'*34}╗\n"
        f"║   🏆  SUHANI REPUTATION BOARD   ║\n"
        f"╚{'═'*34}╝\n\n"
        f"🏠 *GROUP TOP* — {md_esc(getattr(ch, 'title', 'This Group')[:22])}\n"
        f"{accepted_note}\n"
        f"{'┄'*34}\n"
        + "\n".join(group_lines) +
        f"\n\n"
        f"🌐 *GLOBAL TOP* — All Groups Combined\n"
        f"{'┄'*34}\n"
        + "\n".join(global_lines) +
        f"\n\n{'─'*34}\n"
        f"💡 _Thank You = +{REP_PER_THANK} rep  •  1 warn maaf = {REP_PER_WARN_REMOVE} rep_\n"
        f"💡 _{REP_PER_SUHANI_COIN} convertible rep = 1 Suhani Coin = ₹1_\n"
        f"_Reply *Thank You* to give rep  •  Max 3/day per person_"
    )

    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔄 Refresh", callback_data=f"rep:board:{ch.id}"),
            InlineKeyboardButton("⭐ My Profile", callback_data=f"rep:wallet:{update.effective_user.id}"),
        ],
        [
            InlineKeyboardButton("🌐 Global Refresh", callback_data="rep:global:0"),
            InlineKeyboardButton("💸 Withdraw", callback_data=f"rep:wdinfo:{update.effective_user.id}"),
        ]
    ])

    msg = await update.message.reply_text(text, parse_mode='Markdown', reply_markup=kb)
    asyncio.create_task(delete_after(ctx, ch.id, msg.message_id, 600))


# ─── Reputation callbacks (repboard refresh + wallet + myprofile) ──
async def rep_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    medals    = ["🥇", "🥈", "🥉"]
    rank_emojis = ["4️⃣","5️⃣","6️⃣","7️⃣","8️⃣","9️⃣","🔟"]

    def _rep_lines(entries, key_pts, key_id, limit=7):
        if not entries:
            return ["  📉 _Abhi koi data nahi!_"]
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
            wallet      = db.get_suhani_points(usr.id)
            coins       = wallet["coins"]
            progress    = wallet["convertible_rep"] % REP_PER_SUHANI_COIN
            prog_bar    = "█" * (progress // (REP_PER_SUHANI_COIN // 10)) + "░" * (10 - progress // (REP_PER_SUHANI_COIN // 10))
            pts_needed  = REP_PER_SUHANI_COIN - progress
            can_wd      = coins >= MIN_WITHDRAW_COINS

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
                f"╔══════════════════════════╗\n"
                f"║  ⭐  SUHANI PROFILE CARD  ║\n"
                f"╚══════════════════════════╝\n\n"
                f"👤 *{name_safe}*\n"
                f"🏷️ Tier: *{tier}*\n\n"
                f"{'─'*28}\n"
                f"📊 *REPUTATION*\n"
                f"  🏠 Group Rep:  `{group_rep}` pts\n"
                f"  🌐 Total Rep:  `{total_rep}` pts\n"
                f"  💠 Convertible: `{wallet['convertible_rep']}` pts\n\n"
                f"⚡ *Next Suhani Coin*\n"
                f"  [{prog_bar}] `{progress}/{REP_PER_SUHANI_COIN}`\n"
                f"  _{pts_needed} more convertible rep → +1 Coin_\n\n"
                f"{'─'*28}\n"
                f"💰 *WALLET*\n"
                f"  🪙 Suhani Coins: `{coins}`\n"
                f"  💵 INR Value:    `₹{coins}`\n"
                f"  {'✅ Withdrawal ready!' if can_wd else f'🔒 Need {max(0,MIN_WITHDRAW_COINS-coins)} more Coins'}"
            )
            kb_rows = [
                [
                    InlineKeyboardButton("🏆 Rep Board",   callback_data="menu_repboard"),
                    InlineKeyboardButton("🌐 Global Rank", callback_data="rep:global:0"),
                ],
                [InlineKeyboardButton("◀️ Back", callback_data="menu_main")],
            ]
            if can_wd:
                kb_rows.insert(1, [InlineKeyboardButton("💸 Withdraw", callback_data=f"rep:wdinfo:{usr.id}")])
            await query.edit_message_text(text, parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(kb_rows))

        elif action == "board":
            chat_id = int(parts[2]) if len(parts) > 2 else ch_id
            is_accepted = db.is_rep_group_accepted(chat_id)
            group_top  = db.get_reputation_top(chat_id, limit=7)
            global_top = db.get_global_reputation_top(limit=7)
            group_lines  = _rep_lines(group_top,  "points", "user_id")
            global_lines = _rep_lines(global_top, "total",  "_id")
            accepted_note = "✅ Accepted group (Coin-convertible)" if is_accepted else "🔒 Not accepted (warn-only rep)"
            text = (
                f"╔{'═'*32}╗\n"
                f"║   🏆  REPUTATION BOARD       ║\n"
                f"╚{'═'*32}╝\n\n"
                f"{accepted_note}\n\n"
                f"🏠 *GROUP TOP*\n{'┄'*32}\n"
                + "\n".join(group_lines) +
                f"\n\n🌐 *GLOBAL TOP*\n{'┄'*32}\n"
                + "\n".join(global_lines) +
                f"\n\n{'─'*32}\n"
                f"_{REP_PER_SUHANI_COIN} convertible rep = 1 Coin = ₹1_"
            )
            await query.edit_message_text(
                text, parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton("🔄 Refresh",       callback_data=f"rep:board:{chat_id}"),
                        InlineKeyboardButton("⭐ My Profile",    callback_data="rep:myprofile"),
                    ],
                    [
                        InlineKeyboardButton("📊 Group Rank",   callback_data=f"rep:board:{chat_id}"),
                        InlineKeyboardButton("🌐 Global Rank",  callback_data="rep:global:0"),
                    ],
                    [InlineKeyboardButton("◀️ Back", callback_data="menu_main")],
                ])
            )

        elif action == "global":
            top = db.get_global_reputation_top(limit=10)
            lines = _rep_lines(top, "total", "_id", limit=10)
            text = (
                f"╔{'═'*32}╗\n"
                f"║   🌐  GLOBAL REP BOARD       ║\n"
                f"╚{'═'*32}╝\n\n"
                f"{'┄'*32}\n"
                + "\n".join(lines) +
                f"\n\n{'─'*32}\n"
                f"_Sab groups ka combined data_\n"
                f"_Coin sirf accepted groups ke rep se banta hai_"
            )
            await query.edit_message_text(
                text, parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton("🔄 Refresh",     callback_data="rep:global:0"),
                        InlineKeyboardButton("⭐ My Profile",  callback_data="rep:myprofile"),
                    ],
                    [
                        InlineKeyboardButton("🏠 Group Rank",  callback_data=f"rep:board:{ch_id}"),
                        InlineKeyboardButton("◀️ Back",        callback_data="menu_main"),
                    ],
                ])
            )

        elif action == "wallet":
            user_id    = int(parts[2]) if len(parts) > 2 else (query.from_user.id if query.from_user else 0)
            total_rep  = db.get_total_reputation(user_id)
            wallet     = db.get_suhani_points(user_id)
            coins      = wallet["coins"]
            progress   = wallet["convertible_rep"] % REP_PER_SUHANI_COIN
            prog_bar   = "█" * (progress // (REP_PER_SUHANI_COIN // 10)) + "░" * (10 - progress // (REP_PER_SUHANI_COIN // 10))
            can_wd     = coins >= MIN_WITHDRAW_COINS
            text = (
                f"💰 *SUHANI WALLET*\n{'─'*26}\n\n"
                f"🪙 Coins: `{coins}`\n"
                f"🌐 Total Rep: `{total_rep} pts`\n"
                f"💠 Convertible Rep: `{wallet['convertible_rep']} pts`\n"
                f"💵 Value: `₹{coins}`\n\n"
                f"[{prog_bar}] `{progress}/{REP_PER_SUHANI_COIN}`\n\n"
                f"{'✅ Withdrawal ready!' if can_wd else f'🔒 {max(0,MIN_WITHDRAW_COINS-coins)} Coins needed'}"
            )
            kb_rows = [[InlineKeyboardButton("◀️ Back", callback_data="rep:myprofile")]]
            if can_wd:
                kb_rows.insert(0, [InlineKeyboardButton("💸 Withdraw", callback_data=f"rep:wdinfo:{user_id}")])
            await query.edit_message_text(text, parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(kb_rows))

        elif action == "wdinfo":
            # Withdrawal info — /withdraw command ka pointer
            usr_id = int(parts[2]) if len(parts) > 2 else (query.from_user.id if query.from_user else 0)
            if query.from_user and query.from_user.id != usr_id:
                return
            wallet = db.get_suhani_points(usr_id)
            coins  = wallet["coins"]
            text = (
                f"💸 *WITHDRAWAL REQUEST*\n{'─'*26}\n\n"
                f"🪙 Available Coins: `{coins}` (₹{coins})\n\n"
                f"Withdraw karne ke liye DM mein ye bhejo:\n"
                f"`/withdraw <amount> <UPI ID>`\n\n"
                f"_Example:_ `/withdraw {min(coins, MIN_WITHDRAW_COINS)} name@upi`\n\n"
                f"Min withdrawal: `{MIN_WITHDRAW_COINS}` coins (₹{MIN_WITHDRAW_COINS})"
            )
            await query.edit_message_text(text, parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Back", callback_data="rep:myprofile")]]))

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
    _delayed_ai_check mein yeh timestamp use hoga.
    """
    msg = update.message
    if not msg or not msg.from_user:
        return
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
                f"🎉 *{user_name(usr)}* ne group mein `{total_msgs}` messages complete kiye\\!\n"
                f"⭐ *\\+{REP_PER_THANK} Reputation Points* auto\\-earn hue\\! Total: `{new_rep}` rep",
                parse_mode='MarkdownV2'
            )
            asyncio.create_task(delete_after(ctx, ch.id, notice.message_id, 30))
        except Exception:
            pass


async def _delayed_ai_check(ctx, msg, ch, usr, txt_for_ai, is_reply_to_bot, g_settings):
    """
    Background task — user ka message aane ke baad wait karo,
    phir check karo ki provider bot ne kuch bheja ya nahi.
    """
    msg_time = time.time()  # Note karo kab message aaya
    await asyncio.sleep(5.0)

    # Check 1: Exact message_id pe reply aaya?
    exact_replied = (
        ch.id in PROVIDER_BOT_REPLIES and
        msg.message_id in PROVIDER_BOT_REPLIES[ch.id].get("replied_ids", {})
    )

    # Check 2: Hamare message ke BAAD kisi bot ne kuch bheja?
    # (Provider bot ka reply reply_to_message ke bina bhi aa sakta hai)
    last_bot_time = PROVIDER_BOT_REPLIES.get(ch.id, {}).get("last_bot_time", 0)
    bot_replied_after = last_bot_time > msg_time

    if exact_replied or bot_replied_after:
        # Provider bot active tha — AI chup rahe
        return

    # Provider ne reply nahi kiya — AI check karo
    reply_context = ""
    if is_reply_to_bot and msg.reply_to_message and msg.reply_to_message.text:
        reply_context = msg.reply_to_message.text[:300]

    ai_result = await ai_check(
        txt_for_ai, usr.id, ch.id,
        getattr(usr, 'username', '') or '',
        reply_context=reply_context,
        bypass_cooldown=is_reply_to_bot
    )

    # ANIME_NOT_FOUND
    if ai_result["action"] == "ANIME_NOT_FOUND" and ai_result.get("reply"):
        anime_name = ai_result.get("anime_name") or txt_for_ai.strip()
        db.log_missing_anime(anime_name, ch.id)
        try:
            reply_msg = await msg.reply_text(ai_result["reply"], parse_mode='Markdown')
            asyncio.create_task(delete_after(ctx, ch.id, reply_msg.message_id, 120))
        except Exception:
            pass
        try:
            group_name = getattr(ch, 'title', str(ch.id))
            await ctx.bot.send_message(
                OWNER_ID,
                f"📋 *Missing Anime Request!*\n{'─'*28}\n\n"
                f"🎌 Anime: `{anime_name}`\n"
                f"👤 User: {user_name(usr)}\n"
                f"💬 Group: {group_name} (`{ch.id}`)\n\n"
                f"_User ne search kiya lekin available nahi tha._",
                parse_mode='Markdown'
            )
        except Exception:
            pass
        return

    # REPLY
    if ai_result["action"] == "REPLY" and ai_result.get("reply"):
        try:
            reply_msg = await msg.reply_text(ai_result["reply"], parse_mode='Markdown')
            asyncio.create_task(delete_after(ctx, ch.id, reply_msg.message_id, 90))
        except Exception:
            pass


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

    txt_lower = txt.lower().strip()

    # ── Reply karke "thank you/shukriya" type bole to: ──────────
    #    - target ko HAMESHA +100 Reputation Points milte hain (is group mein)
    #    - agar target ke paas active warning hai aur balance ≥100 hai,
    #      to 100 rep apne aap kat ke 1 warning maaf ho jaati hai
    #    - reputation sirf "accepted" group mein Suhani Coin banta hai —
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
                f"⚠️ *Isi bande ko aaj 3/3 baar thanks bol chuke ho!*\n"
                f"Kal phir dena 😊 — _dusre members ko thanks bolna abhi bhi unlimited hai_.",
                parse_mode='Markdown'
            )
            asyncio.create_task(delete_after(ctx, ch.id, notice.message_id, 60))
            return

        current_warns = db.get_warnings(ch.id, target.id)
        new_count = db.increment_rep_given_to(usr.id, target.id)
        db.add_reputation(ch.id, target.id, REP_PER_THANK, user_name(target, escape=False))
        new_rep = db.get_reputation(ch.id, target.id)
        remaining = 3 - new_count
        is_accepted = db.is_rep_group_accepted(ch.id)

        # ── Agar target ke paas warning hai aur balance sufficient hai → auto-redeem ──
        warn_removed = False
        if current_warns > 0 and new_rep >= REP_PER_WARN_REMOVE:
            if db.spend_reputation(ch.id, target.id, REP_PER_WARN_REMOVE):
                db.remove_one_warning(ch.id, target.id)
                warn_removed = True
                new_rep = db.get_reputation(ch.id, target.id)

        wallet = db.get_suhani_points(target.id)

        # ── Milestone: naya Suhani Coin ban gaya kya? (sirf accepted group) ──
        milestone_txt = ""
        if is_accepted and wallet["convertible_rep"] % REP_PER_SUHANI_COIN < REP_PER_THANK and wallet["coins"] > 0:
            milestone_txt = (
                f"\n\n🎉 *MILESTONE\\!* Naya Suhani Coin ban gaya\\!\n"
                f"💰 Wallet: `{wallet['coins']}` Suhani Coin \\= ₹`{wallet['coins']}`"
            )

        base_msg = (
            f"💖 {user_name(usr)} ne {user_name(target)} ko thank you bola\\!\n\n"
            f"⭐ *\\+{REP_PER_THANK} Reputation Points* mil gaye\\!\n"
            f"📊 Is group ka Rep: `{new_rep}` pts\n"
        )
        if warn_removed:
            base_msg += f"✅ Bonus: ek warning bhi maaf ho gayi \\(100 rep kat gaye\\)\\!\n"
        base_msg += f"🎯 Isi bande ko aaj aur de sakte ho: `{remaining}/3`\n"
        if not is_accepted:
            base_msg += f"_ℹ️ Yeh group Suhani Coin ke liye accepted nahi hai — rep sirf warn maaf karne ke kaam aayega\\._\n"
        base_msg += f"{milestone_txt}\n\n_\\/rep karke apna wallet dekho\\!_"

        notice = await msg.reply_text(base_msg, parse_mode='MarkdownV2')
        asyncio.create_task(delete_after(ctx, ch.id, notice.message_id, 60))
        return

    # ── "Suhani ban" natural language command ──────────────
    # Admin group mein "suhani ban @user" ya "suhani ban userid" likh sakta hai
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

    db.inc_stat("scanned")

    group_bots = await get_group_bots(ctx, ch.id)
    violation = await check_violations(msg, group_bots, ctx, ch.id)

    # ── AI Engine — sirf tab jab local checks pass ho gaye ──
    txt_for_ai = msg.text or msg.caption or ""
    ai_result = {"action": "SAFE", "reply": ""}

    if not violation and AI_API_KEY and g_settings.get("ai_approved", False) and g_settings.get("aimod", False) and not is_admin:
        if txt_for_ai:
            # ── Fix 1: Agar user kisi HUMAN ke message pe reply kar raha hai → AI skip ──
            # Do members baat kar rahe hain — AI bich mein na ghuse
            is_reply_to_human = (
                msg.reply_to_message and
                msg.reply_to_message.from_user and
                not msg.reply_to_message.from_user.is_bot
            )
            if is_reply_to_human:
                # Sirf AI reply skip — violation check already upar ho chuka hai
                pass
            else:
                # Repeat tracker — ek hi cheez baar baar likh raha hai?
                repeat_count = track_repeat(ch.id, usr.id, txt_for_ai)

                # Check if user replied to bot's message — cooldown bypass
                is_reply_to_bot = (
                    msg.reply_to_message and
                    msg.reply_to_message.from_user and
                    msg.reply_to_message.from_user.id == ctx.bot.id
                )

                # Anime name repeat — seedha reply, AI call nahi
                if repeat_count >= 3 and is_anime_message(txt_for_ai):
                    anime_name = txt_for_ai.strip()
                    ai_result = {
                        "action": "REPLY",
                        "reply": f"Bhai {user_name(usr)}, *{anime_name}* baar baar likhne se kuch nahi hoga 😄 Ye anime available hai toh group mein already pata hoga!"
                    }
                else:
                    # Provider bot ka update process hone ke liye background task mein bhejo
                    asyncio.create_task(
                        _delayed_ai_check(
                            ctx, msg, ch, usr, txt_for_ai,
                            is_reply_to_bot, g_settings
                        )
                    )
                    # Yahan se return — AI result baad mein process hoga
                    return

        if ai_result["action"] == "PROMO":
            violation = "ai_promo"

    # ── ANIME_NOT_FOUND → group reply + owner DM ──────────────
    if ai_result["action"] == "ANIME_NOT_FOUND" and ai_result.get("reply"):
        anime_name = ai_result.get("anime_name") or txt_for_ai.strip()
        # DB mein log karo
        db.log_missing_anime(anime_name, ch.id)
        # Group mein reply do
        try:
            reply_msg = await msg.reply_text(
                ai_result["reply"],
                parse_mode='Markdown'
            )
            asyncio.create_task(delete_after(ctx, ch.id, reply_msg.message_id, 120))
        except Exception:
            pass
        # Owner ko DM bhejo
        try:
            group_name = getattr(ch, 'title', str(ch.id))
            await ctx.bot.send_message(
                OWNER_ID,
                f"📋 *Missing Anime Request!*\n"
                f"{'─'*28}\n\n"
                f"🎌 Anime: `{anime_name}`\n"
                f"👤 User: {user_name(usr)}\n"
                f"💬 Group: {group_name} (`{ch.id}`)\n\n"
                f"_User ne search kiya lekin available nahi tha._",
                parse_mode='Markdown'
            )
        except Exception:
            pass
        return

    if violation:
        asyncio.create_task(msg.delete())

        # ── Admin hai? Sirf message delete karo, koi action nahi ──
        if is_admin:
            return

        # ── Teacher special handling ──────────────────────────
        if violation == "ai_promo" and db.is_teacher(ch.id, usr.id):
            promo_count = db.inc_teacher_promo_count(ch.id, usr.id)
            # 1st offense → sirf warning, no mute
            if promo_count == 1:
                notice = await ctx.bot.send_message(
                    ch.id,
                    f"📚 {user_name(usr)} bhai/didi,\n\n"
                    f"Aap ek teacher ho, toh aapki izzat karte hain 🙏\n"
                    f"Lekin *promotional content* is group mein allowed nahi hai.\n\n"
                    f"⚠️ Aage se ऐसा mat karna — agla baar mute hoga!",
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
                    f"📚 {user_name(usr)},\n\n"
                    f"Promotion rule dobara tod di! 😤\n"
                    f"🔇 *{mute_min} minutes* ke liye mute kar diya gaya hai.\n\n"
                    f"_(Yeh {promo_count - 1}th repeat offense hai — mute duration bar bar badhega!)_",
                    parse_mode='Markdown'
                )
                asyncio.create_task(delete_after(ctx, ch.id, notice.message_id, 90))
                return

        cnt = db.add_warning(ch.id, usr.id)

        if cnt >= 4:
            await global_mute_user(ctx, usr.id, user_name(usr))
            return

        await do_mute(ctx, ch.id, usr.id, MUTE_TIME[cnt])
        viol_txt = VIOLATION_MSG.get(violation, "Rule violation!")
        bars = "🟥" * cnt + "⬜" * (4 - cnt)
        mute_sec = MUTE_TIME[cnt]
        mute_str = f"{mute_sec}s" if mute_sec < 3600 else "1 week"
        next_str = "💀 1 week ban 🌐" if cnt == 3 else f"W{cnt+1}"

        warn_colors = {1: "🟡", 2: "🟠", 3: "🔴", 4: "💀"}
        color = warn_colors.get(cnt, "⚠️")

        warn_text = (
            f"╔{'═'*28}╗\n"
            f"║  {color} WARNING {cnt}/4 — ACTION TAKEN  ║\n"
            f"╚{'═'*28}╝\n\n"
            f"👤 *{user_name(usr)}*\n"
            f"📌 _{viol_txt}_\n\n"
            f"⏱ Muted: `{mute_str}` • Next: {next_str}\n"
            f"{'─'*28}\n"
            f"Progress: {bars} `{cnt}/4`"
        )
        warn_msg_id = await send_colored_message(ch.id, warn_text, ckb_warn_actions(ch.id, usr.id))
        if warn_msg_id:
            asyncio.create_task(delete_after(ctx, ch.id, warn_msg_id, 90))
        else:
            notice = await ctx.bot.send_message(
                ch.id, warn_text, parse_mode='Markdown',
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
            bot_added_text = (
                f"╔{'═'*36}╗\n"
                f"║  🛡️  SUHANI BOT — ACTIVATED!    ║\n"
                f"╠{'═'*36}╣\n"
                f"║   v10.0  •  AI-Powered Guard     ║\n"
                f"╚{'═'*36}╝\n\n"
                f"⚡ *Protection is now ACTIVE!*\n\n"
                f"{'─'*36}\n"
                f"📋 *Give me these admin rights:*\n"
                f"  ✅ Delete Messages\n"
                f"  ✅ Restrict Members\n"
                f"  ✅ Ban Members\n\n"
                f"{'─'*36}\n"
                f"🛡️ *Auto-Protection Enabled:*\n"
                f"  🤖 External bots & @mentions\n"
                f"  🔗 Links & URLs\n"
                f"  ↩️ Forwarded messages\n"
                f"  🔞 Adult content\n"
                f"  ⛔ Blacklist words\n"
                f"  🌊 Anti-Flood\n"
                f"  🎭 Captcha _(optional)_\n"
                f"  ⏱️ Auto-delete _(optional)_\n\n"
                f"_Use /help to see all commands!_"
            )
            added_msg_id = await send_colored_message(
                update.effective_chat.id, bot_added_text, ckb_bot_added()
            )
            if not added_msg_id:
                await update.message.reply_text(
                    bot_added_text, parse_mode='Markdown', reply_markup=kb_bot_added()
                )
        else:
            g = db.get_group(update.effective_chat.id)
            if g.get("captcha"):
                asyncio.create_task(
                    send_captcha(ctx, update.effective_chat.id, member.id, user_name(member))
                )
            else:
                welcome_text = (
                    f"╔{'═'*30}╗\n"
                    f"║   👋  WELCOME!              ║\n"
                    f"╚{'═'*30}╝\n\n"
                    f"Hey {user_name(member)}, glad to have you here! 🎉\n\n"
                    f"{'─'*30}\n"
                    f"📜 Please read the group rules\n"
                    f"⚠️ Violations are auto-detected\n"
                    f"⭐ Earn rep by being helpful!\n\n"
                    f"_Enjoy the community!_ 🔥"
                )
                welcome_msg_id = await send_colored_message(
                    update.effective_chat.id, welcome_text, ckb_join_welcome()
                )
                if welcome_msg_id:
                    asyncio.create_task(delete_after(ctx, update.effective_chat.id, welcome_msg_id, 60))
                else:
                    msg = await update.message.reply_text(
                        welcome_text, parse_mode='Markdown', reply_markup=kb_join_welcome()
                    )
                    asyncio.create_task(delete_after(ctx, update.effective_chat.id, msg.message_id, 60))


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
    app.add_handler(CommandHandler("rep",              rep_cmd))
    app.add_handler(CommandHandler("wallet",           wallet_cmd))
    app.add_handler(CommandHandler("repboard",         repboard_cmd))
    app.add_handler(CommandHandler("withdraw",         withdraw_cmd))
    app.add_handler(CommandHandler("Accept_rep",       accept_rep_cmd))
    app.add_handler(CommandHandler("accept_rep",       accept_rep_cmd))
    app.add_handler(CommandHandler("Unaccept_rep",     unaccept_rep_cmd))
    app.add_handler(CommandHandler("unaccept_rep",     unaccept_rep_cmd))
    app.add_handler(CommandHandler("earn_groups",      earn_groups_cmd))
    app.add_handler(CommandHandler("earngroups",       earn_groups_cmd))
    app.add_handler(CommandHandler("reputation",       reputation_cmd))
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
    app.add_handler(CommandHandler("rankings",          rankings_cmd))
    app.add_handler(CommandHandler("power",            power_cmd))
    app.add_handler(CommandHandler("unpower",          unpower_cmd))
    app.add_handler(CommandHandler("fban",             fban_cmd))
    app.add_handler(CommandHandler("gunban",           gunban_cmd))
    app.add_handler(CommandHandler("gclearwarn",       gclearwarn_cmd))
    app.add_handler(CommandHandler("adexempt",         adexempt_cmd))
    app.add_handler(CommandHandler("unadexempt",       unadexempt_cmd))
    app.add_handler(CommandHandler("aimod",            aimod_cmd))
    app.add_handler(CommandHandler("aiapprove",        aiapprove_cmd))
    app.add_handler(CommandHandler("airevoke",         airevoke_cmd))
    app.add_handler(CommandHandler("aigroups",         aigroups_cmd))
    app.add_handler(CommandHandler("missinganime",     missinganime_cmd))
    app.add_handler(CommandHandler("addteacher",       addteacher_cmd))
    app.add_handler(CommandHandler("removeteacher",    removeteacher_cmd))
    app.add_handler(CommandHandler("teachers",         teachers_cmd))

    # ── Callback Queries ─────────────────────────────────────
    app.add_handler(CallbackQueryHandler(captcha_callback,    pattern=r"^captcha_"))
    app.add_handler(CallbackQueryHandler(menu_callback,       pattern=r"^(menu_|show_|unmute_|unban_|dismiss_|close_)"))
    app.add_handler(CallbackQueryHandler(rankings_callback, pattern=r"^lbd:"))
    app.add_handler(CallbackQueryHandler(rep_callback,        pattern=r"^rep:"))
    app.add_handler(CallbackQueryHandler(withdraw_approval_callback, pattern=r"^wd:"))

    # ── Message Handlers ─────────────────────────────────────
    # Activity tracker (message-count leaderboard) — apna ALAG group (-1),
    # taaki yeh COMMANDS samet har message ko count kare, bina kisi
    # doosre handler (commands/check_msg/auto-delete) se conflict kiye.
    app.add_handler(MessageHandler(
        filters.ALL & filters.ChatType.GROUPS,
        track_activity_msg
    ), group=-1)
    # Bot reply tracker — group ke saare messages dekho (bots ke replies track karne ke liye)
    app.add_handler(MessageHandler(
        filters.ALL & filters.ChatType.GROUPS,
        track_bot_reply
    ), group=0)
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
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, on_join))
    app.add_handler(MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER,  on_leave))

    # ── Daily job: global #1 message-sender ko 1000 free rep (pichle din ka) ──
    if app.job_queue:
        app.job_queue.run_daily(daily_global_winner_job, time=dtime(hour=0, minute=5))
    else:
        print("⚠️ job_queue unavailable — 'python-telegram-bot[job-queue]' install karo daily reward ke liye.")

    print("✅ Bot Started! Polling...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    Thread(target=run_web, daemon=True).start()
    main()
