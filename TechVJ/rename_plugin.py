"""Persistent caption cleaner for forwarded videos. See upload instructions."""
import asyncio
import re
from pyrogram import Client, filters, enums
from pyrogram.types import Message
from config import ADMINS
from database.db import db

settings_col = db.db.rename_settings
WAITING_FOR_TEXT = set()
BATCH_LOCKS = {}

def is_owner(message: Message) -> bool:
    user = message.from_user
    if not user:
        return False
    admins = ADMINS if isinstance(ADMINS, (list, tuple, set)) else [ADMINS]
    try:
        return int(user.id) in {int(x) for x in admins}
    except (TypeError, ValueError):
        return False

def get_batch_lock(user_id: int) -> asyncio.Lock:
    if user_id not in BATCH_LOCKS:
        BATCH_LOCKS[user_id] = asyncio.Lock()
    return BATCH_LOCKS[user_id]

async def get_removal_text() -> str:
    record = await settings_col.find_one({"_id": "caption_removal_text"})
    return record.get("text", "") if record else ""

async def set_removal_text(value: str) -> None:
    await settings_col.update_one({"_id": "caption_removal_text"}, {"$set": {"text": value}}, upsert=True)

def clean_caption(caption: str, removal_text: str) -> str:
    if not caption or not removal_text:
        return caption
    needle = removal_text.strip().casefold()
    kept = [line for line in caption.splitlines() if needle not in line.casefold()]
    cleaned = "\n".join(kept)
    cleaned = re.sub(r"\n[ \t]*\n(?:[ \t]*\n)+", "\n\n", cleaned)
    return cleaned.strip()

@Client.on_message(filters.private & filters.command("rename"), group=-10)
async def rename_command(client: Client, message: Message):
    if not is_owner(message):
        await message.reply_text("You are not authorized to change this setting.")
        return
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) == 1:
        WAITING_FOR_TEXT.add(message.from_user.id)
        await message.reply_text("Which text should I remove from video captions? Send the exact text or line in your next message. I'll remember it in the database. Send /cancel to keep the current rule.")
        return
    value = parts[1].strip()
    if value.lower() == "status":
        current = await get_removal_text()
        await message.reply_text(f"Current removal text:\n{current}" if current else "No removal text is configured. Use /rename to set it.")
        return
    if value.lower() in {"off", "disable", "none"}:
        await set_removal_text("")
        WAITING_FOR_TEXT.discard(message.from_user.id)
        await message.reply_text("Caption cleaning is disabled.")
        return
    await set_removal_text(value)
    WAITING_FOR_TEXT.discard(message.from_user.id)
    await message.reply_text(f"Saved removal text:\n{value}\n\nNow forward videos to me. I'll clean captions one at a time.")

@Client.on_message(filters.private & filters.command("cancel"), group=-10)
async def cancel_rename(client: Client, message: Message):
    user = message.from_user
    if user and user.id in WAITING_FOR_TEXT:
        WAITING_FOR_TEXT.discard(user.id)
        await message.reply_text("Setup cancelled. The previous saved rule is unchanged.")

@Client.on_message(filters.private & filters.text & ~filters.command(["rename", "cancel"]), group=-10)
async def receive_removal_text(client: Client, message: Message):
    user = message.from_user
    if not user or user.id not in WAITING_FOR_TEXT:
        return
    if not is_owner(message):
        WAITING_FOR_TEXT.discard(user.id)
        return
    value = (message.text or "").strip()
    if not value:
        await message.reply_text("Please send non-empty text, or /cancel.")
        return
    await set_removal_text(value)
    WAITING_FOR_TEXT.discard(user.id)
    await message.reply_text(f"Saved removal text:\n{value}\n\nNow forward videos to me. I'll clean captions one at a time.")

@Client.on_message(filters.channel & filters.caption, group=-10)
async def clean_new_channel_caption(client: Client, message: Message):
    removal_text = await get_removal_text()
    if not removal_text:
        return
    original = message.caption or ""
    cleaned = clean_caption(original, removal_text)
    if cleaned == original:
        return
    try:
        await message.edit_caption(caption=cleaned, parse_mode=enums.ParseMode.DISABLED)
        print(f"Cleaned caption on channel post {message.id}")
    except Exception as exc:
        print(f"Could not edit channel post {message.id}: {exc}")

@Client.on_message(filters.private & filters.forwarded & (filters.video | filters.document), group=-10)
async def clean_forwarded_video_caption(client: Client, message: Message):
    if not is_owner(message):
        return
    if message.document and not (message.document.mime_type or "").lower().startswith("video/"):
        return
    if not message.video and not message.document:
        return
    original = message.caption or ""
    if not original:
        await message.reply_text("This video has no caption to clean.")
        return
    removal_text = await get_removal_text()
    if not removal_text:
        await message.reply_text("No removal text is configured. Use /rename first.")
        return
    cleaned = clean_caption(original, removal_text)
    if cleaned == original:
        await message.reply_text("The saved text was not found in this caption; nothing was changed.")
        return
    if not cleaned:
        await message.reply_text("Removing that text would leave an empty caption. The video was not copied.")
        return
    async with get_batch_lock(message.from_user.id):
        status = await message.reply_text("Queued for caption cleaning…")
        try:
            await status.edit_text("Processing video…")
            await client.copy_message(chat_id=message.chat.id, from_chat_id=message.chat.id, message_id=message.id, caption=cleaned, parse_mode=enums.ParseMode.DISABLED)
            await status.edit_text("Done. Cleaned copy sent; the original is unchanged.")
        except Exception as exc:
            await status.edit_text(f"Couldn't create the cleaned copy: {exc}")
