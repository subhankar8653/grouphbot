#!/usr/bin/env python3
"""
🛡️ ANTI-BOT + ANTI-SPAM PROTECTION - v7.2
⚡ Optimized for low resources
🔗 Advanced Link Detection
✅ Linked Channel Forwards Allowed
"""

import re, json, os, asyncio
from datetime import datetime, timedelta
from telegram import Update, ChatPermissions, ChatMember
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from threading import Thread
from flask import Flask

# ═══════════════ CONFIG ═══════════════
BOT_TOKEN = ""
OWNER_ID = 
DATA_FILE = "data.json"

# Warning messages
WARN_MSG = {
    1: "🚫 **Warning 1/4**\n\nRule violation detected!\n⏱️ Muted: 35s",
    2: "😤 **Warning 2/4**\n\nStop breaking rules!\n⏱️ Muted: 60s",
    3: "🔴 **Warning 3/4 - LAST CHANCE!**\n\nNext = 1 WEEK mute in ALL groups!\n⏱️ Muted: 120s",
    4: "💀 **GLOBAL MUTE!**\n\n🗓️ 1 WEEK mute in ALL groups!\n🔐 Only admin can unmute!"
}

# Violation type messages
VIOLATION_MSG = {
    "bot": "🤖 External bot username not allowed!",
    "url": "🔗 Links/URLs not allowed!",
    "forward": "↩️ Forwarded messages not allowed!",
    "adult_emoji": "🔞 Adult emojis not allowed!",
    "adult_word": "🚫 Inappropriate language not allowed!"
}

MUTE_TIME = {1: 35, 2: 60, 3: 120, 4: 604800}
WARN_EXP = {1: 21600, 2: 57600, 3: 97200, 4: 432000}

# ═══════════════ DETECTION PATTERNS ═══════════════

# Bot username pattern
BOT_RE = re.compile(r'@(\w{5,}bot)\b', re.I)

# 🔗 ADVANCED URL/LINK DETECTION
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

# 🔞 Adult Emojis - Only these are NOT allowed (2+ = violation)
ADULT_EMOJIS = [
    '🍑', '🍆', '💦', '🔞', '👅', '💋', '🍒', '🍌', '🥒', '🌶️',
    '👙', '🩲', '🩱', '🫦', '🥵', '🤤'
]
 
 # 🚫 Bad words - Adult/Bad words (Hindi + English)
ADULT_WORDS = [
     #English
    'sex', 'xxx', 'porn', 'nude', 'naked', 'boob', 'dick', 'pussy', 'cock',
    'fuck', 'fucking', 'fucker', 'bitch', 'whore', 'slut', 'ass', 'asshole',
    'horny', 'sexy', 'hot girl', 'hot boy', 'dating', 'hookup', 'one night',
    'onlyfans', 'webcam', 'adult', '18+', 'nsfw', 'xvideo', 'xnxx', 'xhamster',
    'pornhub', 'brazzers', 'blowjob', 'handjob', 'orgasm', 'cum', 'suck',
    'strip', 'stripper', 'escort', 'call girl', 'massage', 'body massage',  'nut',

# Hindi/Hinglish

    'chut', 'lund', 'loda', 'lauda', 'gaand', 'gand', 'chod', 'chuda',
    'madarchod', 'behenchod', 'bhenchod', 'bhosd', 'bhosdike', 'chud',
    'randi', 'raand', 'hijra', 'kutiya', 
    'muth', 'hilana', 'pelna', 'chodna', 'chudai', 'chudwa',
    'dalla', 'dalal', 'maal', 'badan', 'jism', 'nanga', 'nangi',
    'kapde utaro', 
]

BAD_WORDS_RE = re.compile(
    r'\b(' + '|'.join(re.escape(word) for word in ADULT_WORDS) + r')\b',
    re.I
)

# ✅ WHITELIST for links
WHITELIST = ['Mr.', 'Mrs.', 'Dr.', 'Sr.', 'Jr.', 'a.m.', 'p.m.', 'A.M.', 'P.M.', 'e.g.', 'i.e.', 'etc.']

# Light cache
CACHE = {}
MAX_CACHE = 50

# ═══════════════ DATABASE ═══════════════
class DB:
    def __init__(self):
        self.d = {"u": {}, "g": [], "m": [], "s": [0,0,0,0], "lc": {}}
        # lc = linked channels {group_id: channel_id}
        self._c = 0
        self.load()
    
    def load(self):
        try:
            if os.path.exists(DATA_FILE):
                with open(DATA_FILE) as f:
                    self.d = json.load(f)
        except: pass
    
    def save(self):
        self._c += 1
        if self._c >= 15:
            try:
                with open(DATA_FILE, 'w') as f:
                    json.dump(self.d, f)
                self._c = 0
            except: pass
    
    def get_w(self, c, u):
        k = f"{c}_{u}"
        self._clean(k)
        return self.d["u"].get(k, {}).get("c", 0)
    
    def add_w(self, c, u):
        k = f"{c}_{u}"
        self._clean(k)
        if k not in self.d["u"]:
            self.d["u"][k] = {"c": 0, "w": []}
        self.d["u"][k]["c"] += 1
        cnt = self.d["u"][k]["c"]
        exp = WARN_EXP.get(min(cnt, 4))
        now = datetime.now().timestamp()
        self.d["u"][k]["w"].append({"t": now, "e": now + exp if exp else None})
        self.d["s"][0] += 1
        self.save()
        return min(cnt, 4)
    
    def _clean(self, k):
        if k not in self.d["u"]: return
        now = datetime.now().timestamp()
        a = [w for w in self.d["u"][k].get("w", []) if w.get("e") is None or w["e"] > now]
        if not a:
            del self.d["u"][k]
        else:
            self.d["u"][k]["w"] = a
            self.d["u"][k]["c"] = len(a)
    
    def reset_w(self, c, u):
        k = f"{c}_{u}"
        if k in self.d["u"]:
            del self.d["u"][k]
            self.save()
    
    def add_gm(self, u):
        if u not in self.d["m"]:
            self.d["m"].append(u)
            self.d["s"][3] += 1
            self.save()
    
    def is_gm(self, u): return u in self.d["m"]
    
    def rm_gm(self, u):
        if u in self.d["m"]:
            self.d["m"].remove(u)
            self.save()
    
    def add_g(self, c):
        if c not in self.d["g"]:
            self.d["g"].append(c)
            self.save()
    
    def rm_g(self, c):
        if c in self.d["g"]:
            self.d["g"].remove(c)
            self.save()
    
    def set_linked_channel(self, group_id, channel_id):
        if "lc" not in self.d:
            self.d["lc"] = {}
        self.d["lc"][str(group_id)] = channel_id
        self.save()
    
    def get_linked_channel(self, group_id):
        if "lc" not in self.d:
            return None
        return self.d["lc"].get(str(group_id))

db = DB()

# ═══════════════ HELPERS ═══════════════
async def is_adm(ctx, c, u):
    k = f"{c}_{u}"
    now = datetime.now().timestamp()
    if k in CACHE and now - CACHE[k][1] < 300:
        return CACHE[k][0]
    try:
        m = await ctx.bot.get_chat_member(c, u)
        r = m.status in [ChatMember.OWNER, ChatMember.ADMINISTRATOR]
        if len(CACHE) >= MAX_CACHE:
            CACHE.pop(next(iter(CACHE)))
        CACHE[k] = (r, now)
        return r
    except: return False

async def get_bots(ctx, c):
    k = f"b_{c}"
    now = datetime.now().timestamp()
    if k in CACHE and now - CACHE[k][1] < 300:
        return CACHE[k][0]
    try:
        a = await ctx.bot.get_chat_administrators(c)
        b = [x.user.username.lower() for x in a if x.user.is_bot and x.user.username]
        if len(CACHE) >= MAX_CACHE:
            CACHE.pop(next(iter(CACHE)))
        CACHE[k] = (b, now)
        return b
    except: return []

async def get_linked_channel(ctx, chat_id):
    """Get linked channel ID for a group"""
    k = f"lc_{chat_id}"
    now = datetime.now().timestamp()
    
    # Check cache first
    if k in CACHE and now - CACHE[k][1] < 600:
        return CACHE[k][0]
    
    # Check database
    saved = db.get_linked_channel(chat_id)
    if saved:
        CACHE[k] = (saved, now)
        return saved
    
    # Try to get from Telegram API
    try:
        chat = await ctx.bot.get_chat(chat_id)
        if hasattr(chat, 'linked_chat_id') and chat.linked_chat_id:
            db.set_linked_channel(chat_id, chat.linked_chat_id)
            CACHE[k] = (chat.linked_chat_id, now)
            return chat.linked_chat_id
    except:
        pass
    
    return None

def name(u):
    try:
        return f"@{u.username}" if u.username else u.first_name or str(u.id)
    except: return "User"

def count_adult_emojis(text):
    count = 0
    for emoji in ADULT_EMOJIS:
        count += text.count(emoji)
    return count

def is_whitelisted(text):
    text_lower = text.lower()
    for w in WHITELIST:
        if w.lower() in text_lower:
            return True
    return False

def check_link(text):
    matches = URL_RE.findall(text)
    for match in matches:
        matched_text = match if isinstance(match, str) else match[0] if match[0] else ''
        if is_whitelisted(matched_text):
            continue
        if len(matched_text) < 5:
            continue
        if re.match(r'^[\d.]+$', matched_text):
            continue
        return True
    return False

async def check_violations(msg, gbots, ctx, chat_id):
    """Check all violations and return type"""
    text = msg.text or msg.caption or ""
    
    # 1. Check forwarded message (with linked channel exception)
    if msg.forward_date or msg.forward_from or msg.forward_from_chat:
        # Check if forwarded from linked channel
        if msg.forward_from_chat:
            linked_channel = await get_linked_channel(ctx, chat_id)
            if linked_channel and msg.forward_from_chat.id == linked_channel:
                # Allowed - forwarded from linked channel
                pass
            else:
                return "forward"
        else:
            # Forwarded from user
            return "forward"
    
    # 2. Check adult emojis (2+ = violation)
    if count_adult_emojis(text) >= 2:
        return "adult_emoji"
    
    # 3. Check adult/bad words
    if BAD_WORDS_RE.search(text):
        return "adult_word"
    
    # 4. Check URLs/Links
    if check_link(text):
        return "url"
    
    # 5. Check external bot usernames
    found_bots = BOT_RE.findall(text)
    for bot in found_bots:
        if bot.lower() not in gbots:
            return "bot"
    
    return None

async def mute(ctx, c, u, d=None):
    try:
        p = ChatPermissions(
            can_send_messages=False, can_send_audios=False, can_send_documents=False,
            can_send_photos=False, can_send_videos=False, can_send_video_notes=False,
            can_send_voice_notes=False, can_send_polls=False, can_send_other_messages=False,
            can_add_web_page_previews=False, can_invite_users=False
        )
        if d and d > 0:
            await ctx.bot.restrict_chat_member(c, u, p, until_date=datetime.now() + timedelta(seconds=max(35,d)))
        else:
            await ctx.bot.restrict_chat_member(c, u, p)
        db.d["s"][1] += 1
        return True
    except: return False

async def unmute(ctx, c, u):
    try:
        p = ChatPermissions(
            can_send_messages=True, can_send_audios=True, can_send_documents=True,
            can_send_photos=True, can_send_videos=True, can_send_video_notes=True,
            can_send_voice_notes=True, can_send_polls=True, can_send_other_messages=True,
            can_add_web_page_previews=True, can_invite_users=True
        )
        await ctx.bot.restrict_chat_member(c, u, p)
        return True
    except: return False

async def del_msg(ctx, c, m, delay=60):
    await asyncio.sleep(delay)
    try: await ctx.bot.delete_message(c, m)
    except: pass

async def global_mute(ctx, u, un=None):
    db.add_gm(u)
    for g in db.d["g"]:
        try:
            await mute(ctx, g, u, 604800)
            await ctx.bot.send_message(g, f"👤 {un or u}\n\n{WARN_MSG[4]}", parse_mode='Markdown')
            await asyncio.sleep(0.1)
        except: pass

# ═══════════════ COMMANDS ═══════════════
async def start_cmd(u, c):
    if u.effective_chat.type != "private":
        return await u.message.reply_text("🤖 Bot Active! /help")
    
    if u.effective_user.id == OWNER_ID:
        t = """🛡️ ANTI-BOT + ANTI-SPAM BOT
👑 Owner Panel

━━━━━━━━━━━━━━━━━━━━━

📋 Commands:

👤 User:
/warnings - Check warnings
/help - Help menu
/rule - Group rules

👮 Admin:
/mute [sec] - Mute user (reply)
/unmute - Unmute user (reply)
/warn - Give warning (reply)
/resetwarnings - Reset (reply)
/del - Delete message (reply)
/testmute - Test 35s mute (reply)
/setlinked - Set linked channel

👑 Owner:
/broadcast <msg> - Broadcast
/groups - Groups list
/stats - Statistics
/globalmutes - Global mutes
/unglobalmute <id> - Remove mute

━━━━━━━━━━━━━━━━━━━━━

⚠️ Warning System:
• W1 → 35s (6hr expire)
• W2 → 60s (16hr expire)
• W3 → 120s (27hr expire)
• W4 → 1 week (All Groups)

🛡️ Protection:
• 🤖 External bots
• 🔗 ALL Links
• ↩️ Forwards (except linked channel)
• 🔞 Adult emojis (2+)
• 🚫 Bad words"""
    else:
        t = """🛡️ ANTI-BOT + ANTI-SPAM BOT

━━━━━━━━━━━━━━━━━━━━━

📋 Commands:

👤 User:
/warnings - Check warnings
/help - Help menu
/rule - Group rules

👮 Admin:
/mute [sec] - Mute user (reply)
/unmute - Unmute user (reply)
/warn - Give warning (reply)
/resetwarnings - Reset (reply)
/del - Delete message (reply)
/testmute - Test 35s mute (reply)
/setlinked - Set linked channel

━━━━━━━━━━━━━━━━━━━━━

⚠️ Warning System:
• W1 → 35s
• W2 → 60s
• W3 → 120s
• W4 → 1 week"""
    await u.message.reply_text(t)

async def help_cmd(u, c):
    if u.effective_user.id == OWNER_ID:
        t = """📚 **Owner Help**

👤 /warnings /rule
👮 /mute /unmute /warn /resetwarnings /del /testmute /setlinked
👑 /broadcast /groups /stats /globalmutes /unglobalmute

🛡️ **Auto Detection:**
• External bot usernames
• ALL types of links
• Forwarded messages (except linked channel)
• Adult emojis (2+)
• Bad words (Hindi)"""
    else:
        t = """📚 **Help**

👤 /warnings /rule
👮 /mute /unmute /warn /resetwarnings /del /testmute /setlinked

⚠️ W1→35s | W2→60s | W3→120s | W4→1 Week"""
    await u.message.reply_text(t, parse_mode='Markdown')

async def rule_cmd(u, c):
    t = """📜 **GROUP RULES**

━━━━━━━━━━━━━━━━━━━━━

🚫 **NOT ALLOWED:**

1️⃣ 🤖 External bot usernames

2️⃣ 🔗 ALL Links/URLs

3️⃣ ↩️ Forwarded Messages
   ✅ Linked channel forwards allowed

4️⃣ 🔞 Adult Emojis (2+)
   🍑🍆💦👅💋 etc.

5️⃣ 🗣️ Bad Language
   Hindi abusive words

━━━━━━━━━━━━━━━━━━━━━

⚠️ **PUNISHMENT:**

• 1st Violation → 35s mute
• 2nd Violation → 60s mute
• 3rd Violation → 120s mute
• 4th Violation → 1 WEEK (ALL GROUPS)

━━━━━━━━━━━━━━━━━━━━━

✅ Follow rules & enjoy!"""
    await u.message.reply_text(t, parse_mode='Markdown')

async def setlinked_cmd(u, c):
    """Set linked channel for the group"""
    ch = u.effective_chat
    if ch.type == "private": 
        return await u.message.reply_text("❌ Use in group!")
    
    if not await is_adm(c, ch.id, u.effective_user.id): 
        return await u.message.reply_text("❌ Admins only!")
    
    # Try to auto-detect linked channel
    try:
        chat = await c.bot.get_chat(ch.id)
        if hasattr(chat, 'linked_chat_id') and chat.linked_chat_id:
            db.set_linked_channel(ch.id, chat.linked_chat_id)
            
            # Get channel name
            try:
                channel = await c.bot.get_chat(chat.linked_chat_id)
                channel_name = channel.title or channel.username or str(chat.linked_chat_id)
            except:
                channel_name = str(chat.linked_chat_id)
            
            await u.message.reply_text(
                f"✅ **Linked Channel Set!**\n\n"
                f"📢 Channel: {channel_name}\n"
                f"🆔 ID: `{chat.linked_chat_id}`\n\n"
                f"✅ Forwards from this channel are now allowed!",
                parse_mode='Markdown'
            )
        else:
            await u.message.reply_text(
                "❌ **No linked channel found!**\n\n"
                "📌 First link a channel to this group from Telegram settings.\n\n"
                "Or use: `/setlinked <channel_id>`",
                parse_mode='Markdown'
            )
    except Exception as e:
        # Manual set
        if c.args:
            try:
                channel_id = int(c.args[0])
                db.set_linked_channel(ch.id, channel_id)
                await u.message.reply_text(f"✅ Linked channel set: `{channel_id}`", parse_mode='Markdown')
            except:
                await u.message.reply_text("❌ Invalid channel ID!")
        else:
            await u.message.reply_text(
                "❌ **Could not detect linked channel!**\n\n"
                "Use: `/setlinked <channel_id>`\n"
                "Example: `/setlinked -1001234567890`",
                parse_mode='Markdown'
            )

async def testmute_cmd(u, c):
    ch = u.effective_chat
    if ch.type == "private": return
    if not await is_adm(c, ch.id, u.effective_user.id): return
    if not u.message.reply_to_message: return await u.message.reply_text("❌ Reply to user!")
    tg = u.message.reply_to_message.from_user
    if await is_adm(c, ch.id, tg.id): return await u.message.reply_text("❌ Can't mute admin!")
    if await mute(c, ch.id, tg.id, 35):
        await u.message.reply_text(f"✅ {name(tg)} muted 35s")
    else:
        await u.message.reply_text("❌ Failed! Make bot admin!")

async def mute_cmd(u, c):
    ch = u.effective_chat
    if ch.type == "private": return
    if not await is_adm(c, ch.id, u.effective_user.id): return
    if not u.message.reply_to_message: return await u.message.reply_text("❌ Reply! `/mute 60`", parse_mode='Markdown')
    tg = u.message.reply_to_message.from_user
    if await is_adm(c, ch.id, tg.id): return await u.message.reply_text("❌ Can't mute admin!")
    d = 35
    if c.args:
        try: d = max(35, int(c.args[0]))
        except: pass
    if await mute(c, ch.id, tg.id, d):
        await u.message.reply_text(f"🔇 {name(tg)} muted {d}s")

async def unmute_cmd(u, c):
    ch = u.effective_chat
    if ch.type == "private": return
    if not await is_adm(c, ch.id, u.effective_user.id): return
    if not u.message.reply_to_message: return
    tg = u.message.reply_to_message.from_user
    db.rm_gm(tg.id)
    if await unmute(c, ch.id, tg.id):
        db.reset_w(ch.id, tg.id)
        await u.message.reply_text(f"🔊 {name(tg)} unmuted!")

async def warn_cmd(u, c):
    ch = u.effective_chat
    if ch.type == "private": return
    if not await is_adm(c, ch.id, u.effective_user.id): return
    if not u.message.reply_to_message: return
    tg = u.message.reply_to_message.from_user
    if await is_adm(c, ch.id, tg.id): return
    cnt = db.add_w(ch.id, tg.id)
    if cnt >= 4:
        await global_mute(c, tg.id, name(tg))
        return
    await mute(c, ch.id, tg.id, MUTE_TIME[cnt])
    s = await u.message.reply_text(f"👤 {name(tg)}\n\n{WARN_MSG[cnt]}", parse_mode='Markdown')
    asyncio.create_task(del_msg(c, ch.id, s.message_id, 90))

async def warnings_cmd(u, c):
    ch = u.effective_chat
    if ch.type == "private": return
    tg = u.message.reply_to_message.from_user if u.message.reply_to_message else u.effective_user
    if db.is_gm(tg.id):
        return await u.message.reply_text(f"👤 {name(tg)}\n\n🗓️ **GLOBALLY MUTED** (1 week)", parse_mode='Markdown')
    w = db.get_w(ch.id, tg.id)
    bar = "🟥" * w + "⬜" * (4 - w)
    await u.message.reply_text(f"👤 {name(tg)}\n📊 **{w}/4**\n{bar}", parse_mode='Markdown')

async def reset_cmd(u, c):
    ch = u.effective_chat
    if ch.type == "private": return
    if not await is_adm(c, ch.id, u.effective_user.id): return
    if not u.message.reply_to_message: return
    tg = u.message.reply_to_message.from_user
    db.reset_w(ch.id, tg.id)
    await u.message.reply_text(f"✅ {name(tg)} reset!")

async def del_cmd(u, c):
    if u.effective_chat.type == "private": return
    if not await is_adm(c, u.effective_chat.id, u.effective_user.id): return
    if not u.message.reply_to_message: return
    try:
        await u.message.reply_to_message.delete()
        await u.message.delete()
    except: pass

# Owner commands
async def broadcast_cmd(u, c):
    if u.effective_user.id != OWNER_ID: return
    if not c.args: return await u.message.reply_text("❌ /broadcast <msg>")
    msg = ' '.join(c.args)
    s = f = 0
    for g in db.d["g"]:
        try:
            await c.bot.send_message(g, f"📢 {msg}")
            s += 1
            await asyncio.sleep(0.1)
        except: f += 1
    await u.message.reply_text(f"✅ {s} | ❌ {f}")

async def groups_cmd(u, c):
    if u.effective_user.id == OWNER_ID:
        await u.message.reply_text(f"📋 Groups: {len(db.d['g'])}")

async def globalmutes_cmd(u, c):
    if u.effective_user.id == OWNER_ID:
        await u.message.reply_text(f"🗓️ Global Mutes: {len(db.d['m'])}")

async def unglobalmute_cmd(u, c):
    if u.effective_user.id != OWNER_ID: return
    if not c.args: return await u.message.reply_text("❌ /unglobalmute <id>")
    try:
        uid = int(c.args[0])
        db.rm_gm(uid)
        await u.message.reply_text(f"✅ {uid} unmuted!")
    except: await u.message.reply_text("❌ Invalid ID!")

async def stats_cmd(u, c):
    if u.effective_user.id != OWNER_ID: return
    s = db.d["s"]
    lc_count = len(db.d.get("lc", {}))
    t = f"""📊 **BOT STATISTICS**

👥 Groups: {len(db.d['g'])}
📢 Linked Channels: {lc_count}
⚠️ Warnings: {s[0]}
🔇 Mutes: {s[1]}
📨 Scanned: {s[2]}
🗓️ Global Mutes: {s[3]}

🛡️ Status: Active"""
    await u.message.reply_text(t, parse_mode='Markdown')

# ═══════════════ MAIN HANDLER ═══════════════
async def check_msg(u, c):
    msg = u.message
    if not msg: return
    
    ch = u.effective_chat
    usr = u.effective_user
    
    if ch.type == "private": return
    
    # Add group
    if ch.id not in db.d["g"]:
        db.d["g"].append(ch.id)
    
    # Global mute check
    if db.is_gm(usr.id):
        asyncio.create_task(msg.delete())
        asyncio.create_task(mute(c, ch.id, usr.id, 604800))
        return
    
    # Skip commands
    txt = msg.text or msg.caption or ""
    if txt.startswith('/'): return
    
    # Admin check
    if await is_adm(c, ch.id, usr.id): return
    
    db.d["s"][2] += 1
    
    # Get group bots
    gbots = await get_bots(c, ch.id)
    
    # Check all violations (now async for linked channel check)
    violation = await check_violations(msg, gbots, c, ch.id)
    
    if violation:
        asyncio.create_task(msg.delete())
        
        cnt = db.add_w(ch.id, usr.id)
        
        if cnt >= 4:
            await global_mute(c, usr.id, name(usr))
            return
        
        await mute(c, ch.id, usr.id, MUTE_TIME[cnt])
        
        violation_text = VIOLATION_MSG.get(violation, "Rule violation!")
        s = await c.bot.send_message(
            ch.id, 
            f"👤 {name(usr)}\n\n{violation_text}\n\n{WARN_MSG[cnt]}", 
            parse_mode='Markdown'
        )
        asyncio.create_task(del_msg(c, ch.id, s.message_id, 90))

# ═══════════════ EVENTS ═══════════════
async def on_join(u, c):
    for m in u.message.new_chat_members:
        if m.id == c.bot.id:
            db.add_g(u.effective_chat.id)
            
            # Try to auto-detect linked channel
            try:
                chat = await c.bot.get_chat(u.effective_chat.id)
                if hasattr(chat, 'linked_chat_id') and chat.linked_chat_id:
                    db.set_linked_channel(u.effective_chat.id, chat.linked_chat_id)
            except: pass
            
            await u.message.reply_text(
                "🛡️ **Bot Active!**\n\n"
                "⚠️ Make admin with Delete & Restrict!\n\n"
                "🛡️ **Protection:**\n"
                "• 🤖 External bots\n"
                "• 🔗 ALL Links\n"
                "• ↩️ Forwards (except linked channel)\n"
                "• 🔞 Adult content\n\n"
                "📜 /rule for rules!\n"
                "📢 /setlinked to set linked channel",
                parse_mode='Markdown'
            )

async def on_leave(u, c):
    if u.message.left_chat_member.id == c.bot.id:
        db.rm_g(u.effective_chat.id)

# ═══════════════ WEB SERVER (for Render) ═══════════════
web_app = Flask(__name__)

@web_app.route('/')
def home():
    return "🛡️ Suhani Bot is running!"

@web_app.route('/health')
def health():
    return "OK"

def run_web():
    port = int(os.environ.get('PORT', 10000))
    web_app.run(host='0.0.0.0', port=port)

# ═══════════════ MAIN ═══════════════
def main():
    print("🛡️ Anti-Bot + Anti-Spam v7.2")
    print("⚡ Optimized for low resources")
    print("🔗 Advanced Link Detection")
    print("✅ Linked Channel Forwards Allowed")
    print("━" * 40)
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Commands
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("rule", rule_cmd))
    app.add_handler(CommandHandler("rules", rule_cmd))
    app.add_handler(CommandHandler("setlinked", setlinked_cmd))
    app.add_handler(CommandHandler("testmute", testmute_cmd))
    app.add_handler(CommandHandler("mute", mute_cmd))
    app.add_handler(CommandHandler("unmute", unmute_cmd))
    app.add_handler(CommandHandler("warn", warn_cmd))
    app.add_handler(CommandHandler("warnings", warnings_cmd))
    app.add_handler(CommandHandler("resetwarnings", reset_cmd))
    app.add_handler(CommandHandler("del", del_cmd))
    app.add_handler(CommandHandler("broadcast", broadcast_cmd))
    app.add_handler(CommandHandler("groups", groups_cmd))
    app.add_handler(CommandHandler("globalmutes", globalmutes_cmd))
    app.add_handler(CommandHandler("unglobalmute", unglobalmute_cmd))
    app.add_handler(CommandHandler("stats", stats_cmd))
    
    # Handlers
    app.add_handler(MessageHandler(filters.ALL & filters.ChatType.GROUPS & ~filters.COMMAND, check_msg))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, on_join))
    app.add_handler(MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER, on_leave))
    
    print("✅ Started!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    # Start web server in background thread (for Render)
    Thread(target=run_web, daemon=True).start()
    # Start bot
    main()
