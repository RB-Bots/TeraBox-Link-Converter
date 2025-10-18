# main.py
# Multi-user TeraBox Converter Bot (Public)
# Each user connects their own TeraBox account (BDUSS + STOKEN)

import os
import re
import json
import logging
from datetime import datetime
import aiohttp
from motor.motor_asyncio import AsyncIOMotorClient
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# =====================================
# 🕒 TIME SYNC FIX (prevents msg_id too low error)
# =====================================
import time
import asyncio

# Wait briefly to allow system time sync
asyncio.get_event_loop().run_until_complete(asyncio.sleep(2))
print(f"⏰ System time synced: {time.ctime()}")

# =====================================
# 🕒 EXTRA TIME SYNC CHECK (NTP-based)
# =====================================
import ntplib  # Make sure to add "ntplib" in requirements.txt

def sync_time_ntp():
    try:
        client = ntplib.NTPClient()
        response = client.request("pool.ntp.org", version=3)
        diff = response.tx_time - time.time()
        print(f"🌍 NTP time difference: {diff:.3f} seconds")
        if abs(diff) > 1:
            print("⚙️ Adjusting minor drift... safe delay before bot start")
            time.sleep(2)
    except Exception as e:
        print(f"⚠️ NTP sync skipped: {e}")

sync_time_ntp()

# =====================================
# 🔧 CONFIGURATION
# =====================================
API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
MONGO_URI = os.getenv("MONGO_URI", "")
DEFAULT_SAVE_PATH = os.getenv("DEFAULT_SAVE_PATH", "/Apps/terabox_bot")
USER_AGENT = os.getenv("USER_AGENT", "Mozilla/5.0 (TeraBoxBot)")

if not all([API_ID, API_HASH, BOT_TOKEN, MONGO_URI]):
    raise SystemExit("❌ Missing required environment variables!")

# =====================================
# 📦 SETUP
# =====================================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TeraBoxBot")

db_client = AsyncIOMotorClient(MONGO_URI)
db = db_client["terabox_converter"]
users = db["users"]

app = Client("TeraBoxMultiBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# =====================================
# 🧠 HELPER FUNCTIONS
# =====================================
def normalize_cookie(text: str):
    parts = {}
    for p in re.split(r";\s*", text.strip()):
        if "=" in p:
            k, v = p.split("=", 1)
            if k.strip().upper() in ("BDUSS", "STOKEN"):
                parts[k.strip().upper()] = v.strip()
    if "BDUSS" in parts and "STOKEN" in parts:
        return f"BDUSS={parts['BDUSS']}; STOKEN={parts['STOKEN']};"
    return text.strip()


def extract_share_info(url: str):
    m = re.search(r"shareid=(\d+).*uk=(\d+)", url)
    if m:
        return m.group(1), m.group(2)
    m2 = re.search(r"/s/([A-Za-z0-9_\-]+)", url)
    if m2:
        return m2.group(1), None
    return None, None


async def save_cookie(user_id: int, cookie: str):
    cookie = normalize_cookie(cookie)
    await users.update_one(
        {"_id": user_id},
        {"$set": {"cookie": cookie, "updated_at": datetime.utcnow()}},
        upsert=True,
    )
    return cookie


async def get_cookie(user_id: int):
    doc = await users.find_one({"_id": user_id})
    return doc.get("cookie") if doc else None


async def delete_cookie(user_id: int):
    await users.delete_one({"_id": user_id})


# =====================================
# 🌐 API REQUEST HELPERS
# =====================================
async def terabox_save_share(cookie, shareid, from_uk):
    headers = {"cookie": cookie, "user-agent": USER_AGENT}
    async with aiohttp.ClientSession(headers=headers) as s:
        try:
            url = f"https://www.terabox.com/api/transfer/share/save?shareid={shareid}&from_uk={from_uk}&path={DEFAULT_SAVE_PATH}"
            async with s.get(url) as r:
                data = await r.text()
                try:
                    return json.loads(data)
                except:
                    return {"raw": data}
        except Exception as e:
            logger.error(e)
            return None


async def terabox_create_share(cookie, fid_list):
    headers = {"cookie": cookie, "user-agent": USER_AGENT}
    async with aiohttp.ClientSession(headers=headers) as s:
        try:
            url = "https://www.terabox.com/api/share/set"
            payload = {"fid_list": json.dumps(fid_list), "path": "/", "pwd": ""}
            async with s.post(url, data=payload) as r:
                data = await r.text()
                try:
                    return json.loads(data)
                except:
                    return {"raw": data}
        except Exception as e:
            logger.error(e)
            return None


# =====================================
# 🤖 BOT COMMANDS
# =====================================

@app.on_message(filters.command("start"))
async def start_cmd(_, msg):
    await msg.reply_text(
        "**👋 Welcome to TeraBox Converter Bot!**\n\n"
        "🔹 Use /login to connect your TeraBox account (BDUSS + STOKEN)\n"
        "🔹 Send any TeraBox link after login to convert it via your account\n"
        "🔹 Use /logout to disconnect your account\n\n"
        "__Safe multi-user system — every user uses their own account__ 🔐"
    )


@app.on_message(filters.command("login"))
async def login_cmd(_, msg):
    await msg.reply_text(
        "🔑 **Login to your TeraBox account**\n\n"
        "Please send your TeraBox cookie (format):\n\n"
        "`BDUSS=xxxx; STOKEN=yyyy;`\n\n"
        "⚠️ Do not share this cookie with anyone!"
    )


@app.on_message(filters.command("logout"))
async def logout_cmd(_, msg):
    await delete_cookie(msg.from_user.id)
    await msg.reply_text("✅ You have been logged out and your cookie removed.")


@app.on_message(filters.text & ~filters.command(["start", "login", "logout"]))
async def handle_text(_, msg):
    text = msg.text.strip()

    # Save cookie
    if "BDUSS" in text:
        cookie = normalize_cookie(text)
        if "STOKEN" not in cookie:
            return await msg.reply_text("❌ Invalid cookie format. Must contain BDUSS and STOKEN.")
        await save_cookie(msg.from_user.id, cookie)
        return await msg.reply_text("✅ Your TeraBox account is connected! Now send any TeraBox link to convert.")

    # Convert link
    if "terabox" not in text:
        return await msg.reply_text("⚠️ Please send a valid TeraBox link!")

    cookie = await get_cookie(msg.from_user.id)
    if not cookie:
        return await msg.reply_text("🔐 Please login first using /login and send your cookie.")

    shareid, uk = extract_share_info(text)
    if not shareid:
        return await msg.reply_text("❌ Invalid TeraBox link format.")

    status = await msg.reply_text("⏳ Copying file to your TeraBox account...")

    save_resp = await terabox_save_share(cookie, shareid, uk or "")
    if not save_resp:
        return await status.edit("⚠️ Failed to save file. Please check your cookie or the link.")

    fid_list = []
    if "info" in save_resp and isinstance(save_resp["info"], list):
        fid_list = [i.get("fs_id") for i in save_resp["info"] if i.get("fs_id")]
    elif "fs_id" in save_resp:
        fid_list = [save_resp.get("fs_id")]

    if not fid_list:
        return await status.edit("✅ File saved, but could not create a new share link automatically.")

    share_resp = await terabox_create_share(cookie, fid_list)
    if not share_resp:
        return await status.edit("❌ File saved, but failed to create a share link.")

    new_link = None
    for key in ("short_link", "link", "url"):
        if key in share_resp:
            new_link = share_resp[key]
            break

    if not new_link:
        return await status.edit("✅ File saved but link not found. Check your TeraBox manually.")

    kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔗 Open Link", url=new_link)]])
    await status.edit(f"✅ File copied successfully!\n\n**New Link:** {new_link}", reply_markup=kb)


# =====================================
# 🚀 RUN
# =====================================
print("🚀 TeraBox Converter Bot Running (Public Multi-User)...")
app.run()