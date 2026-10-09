"""Persistent default thumbnail commands for Nnlclasses."""
from pyrogram import Client, filters
from pyrogram.types import Message
from config import ADMINS
from TechVJ.thumbnail_utils import clear_thumbnail_file_id, get_thumbnail_file_id, set_thumbnail_file_id

WAITING = set()

def owner(message: Message):
    return bool(message.from_user and message.from_user.id == ADMINS)

@Client.on_message(filters.private & filters.command("setthumb"), group=-10)
async def setthumb(client: Client, message: Message):
    if not owner(message):
        return await message.reply_text("You are not authorized to change the thumbnail.")
    if message.reply_to_message and message.reply_to_message.photo:
        await set_thumbnail_file_id(message.reply_to_message.photo[-1].file_id)
        return await message.reply_text("Default thumbnail saved persistently.")
    WAITING.add(message.from_user.id)
    await message.reply_text("Send the photo to use as the default video thumbnail. It persists across restarts. /cancelthumb cancels.")

@Client.on_message(filters.private & filters.photo, group=-10)
async def receive_photo(client: Client, message: Message):
    user = message.from_user
    if not user or user.id not in WAITING:
        return
    if not owner(message):
        WAITING.discard(user.id)
        return
    await set_thumbnail_file_id(message.photo[-1].file_id)
    WAITING.discard(user.id)
    await message.reply_text("Default thumbnail saved persistently.")

@Client.on_message(filters.private & filters.command("delthumb"), group=-10)
async def delthumb(client: Client, message: Message):
    if not owner(message):
        return await message.reply_text("You are not authorized to change the thumbnail.")
    await clear_thumbnail_file_id()
    WAITING.discard(message.from_user.id)
    await message.reply_text("Default thumbnail removed.")

@Client.on_message(filters.private & filters.command("thumbstatus"), group=-10)
async def thumbstatus(client: Client, message: Message):
    if not owner(message):
        return await message.reply_text("You are not authorized to view this setting.")
    await message.reply_text("A default thumbnail is configured." if await get_thumbnail_file_id() else "No default thumbnail is configured. Use /setthumb.")

@Client.on_message(filters.private & filters.command("cancelthumb"), group=-10)
async def cancelthumb(client: Client, message: Message):
    if message.from_user and message.from_user.id in WAITING:
        WAITING.discard(message.from_user.id)
        await message.reply_text("Thumbnail setup cancelled; the existing thumbnail is unchanged.")
