"""Owner-controlled /rename caption cleaner for Nnlclasses.

/rename                 Start interactive setup
/rename <text>          Save/update text to remove
/rename off             Disable cleaning
/rename status          Show current setting

Settings are stored in MongoDB and survive restarts.
"""
import re
from pyrogram import Client, filters, enums
from pyrogram.types import Message
from config import ADMINS
from database.db import db

settings_col = db.db.rename_settings
WAITING_FOR_TEXT = set()


def is_owner(message: Message) -> bool:
    return bool(message.from_user and message.from_user.id == ADMINS)


async def get_removal_text():
    record = await settings_col.find_one({"_id": "caption_removal_text"})
    return record.get("text", "") if record else ""


async def set_removal_text(value: str):
    await settings_col.update_one(
        {"_id": "caption_removal_text"},
        {"$set": {"text": value}},
        upsert=True,
    )


def clean_caption(caption: str, removal_text: str) -> str:
    if not caption or not removal_text:
        return caption
    cleaned = re.sub(re.escape(removal_text), "", caption, flags=re.IGNORECASE)
    cleaned = "\n".join(line.rstrip() for line in cleaned.splitlines())
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
        await message.reply_text(
            "Send the exact text you want removed from captions.\n"
            "I'll remember it across restarts. Send /cancel to keep the current setting."
        )
        return

    value = parts[1].strip()
    if value.lower() == "status":
        current = await get_removal_text()
        await message.reply_text(f"Current removal text:\n{current}" if current else "No removal text is configured.")
        return
    if value.lower() in {"off", "disable", "none"}:
        await set_removal_text("")
        WAITING_FOR_TEXT.discard(message.from_user.id)
        await message.reply_text("Caption cleaning is disabled.")
        return
    if not value:
        await message.reply_text("Please provide non-empty text.")
        return

    await set_removal_text(value)
    WAITING_FOR_TEXT.discard(message.from_user.id)
    await message.reply_text(f"Saved removal text:\n{value}\n\nThis setting survives bot restarts.")


@Client.on_message(filters.private & filters.command("cancel"), group=-10)
async def cancel_rename(client: Client, message: Message):
    if message.from_user and message.from_user.id in WAITING_FOR_TEXT:
        WAITING_FOR_TEXT.discard(message.from_user.id)
        await message.reply_text("Cancelled. The existing setting was not changed.")


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
    await message.reply_text(f"Saved removal text:\n{value}\n\nThis setting survives bot restarts.")


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


@Client.on_message(
    filters.private & filters.forwarded & (filters.video | filters.document) & filters.caption,
    group=-10,
)
async def clean_forwarded_video_caption(client: Client, message: Message):
    if not is_owner(message):
        return
    if message.document and not (message.document.mime_type or "").lower().startswith("video/"):
        return

    removal_text = await get_removal_text()
    if not removal_text:
        await message.reply_text("No removal text is configured. Use /rename first.")
        return
    original = message.caption or ""
    cleaned = clean_caption(original, removal_text)
    if cleaned == original:
        await message.reply_text("The configured text was not found in this caption.")
        return
    try:
        await client.copy_message(
            chat_id=message.chat.id,
            from_chat_id=message.chat.id,
            message_id=message.id,
            caption=cleaned,
            parse_mode=enums.ParseMode.DISABLED,
        )
        await message.reply_text("Sent a cleaned copy. The original forwarded message is unchanged.")
    except Exception as exc:
        await message.reply_text(f"Couldn't create a cleaned copy. Error: {exc}")
