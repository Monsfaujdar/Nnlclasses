import os
import asyncio
import re
import pyrogram
from pyrogram import Client, filters, enums
from pyrogram.errors import FloodWait, UserIsBlocked, InputUserDeactivated, UserAlreadyParticipant, InviteHashExpired, UsernameNotOccupied
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
from config import API_ID, API_HASH, ERROR_MESSAGE, LOGIN_SYSTEM, STRING_SESSION, CHANNEL_ID, WAITING_TIME
from database.db import db
from TechVJ.strings import HELP_TXT
from bot import TechVJUser


class batch_temp(object):
    IS_BATCH = {}


async def downstatus(client, statusfile, message, chat):
    while not os.path.exists(statusfile):
        await asyncio.sleep(3)
    while os.path.exists(statusfile):
        with open(statusfile, "r") as f:
            txt = f.read()
        try:
            await client.edit_message_text(chat, message.id, f"**Downloaded:** **{txt}**")
            await asyncio.sleep(10)
        except Exception:
            await asyncio.sleep(5)


async def upstatus(client, statusfile, message, chat):
    while not os.path.exists(statusfile):
        await asyncio.sleep(3)
    while os.path.exists(statusfile):
        with open(statusfile, "r") as f:
            txt = f.read()
        try:
            await client.edit_message_text(chat, message.id, f"**Uploaded:** **{txt}**")
            await asyncio.sleep(10)
        except Exception:
            await asyncio.sleep(5)


def progress(current, total, message, type):
    with open(f"{message.id}{type}status.txt", "w") as f:
        f.write(f"{current * 100 / total:.1f}%")


@Client.on_message(filters.command(["start"]))
async def send_start(client: Client, message: Message):
    if not await db.is_user_exist(message.from_user.id):
        await db.add_user(message.from_user.id, message.from_user.first_name)
    await client.send_message(
        chat_id=message.chat.id,
        text=f"<b>👋 Hi {message.from_user.mention}, I am Save Restricted Content Bot, I can send you restricted content by its post link.\n\nFor downloading restricted content /login first.\n\nKnow how to use bot by - /help</b>",
        reply_to_message_id=message.id
    )


@Client.on_message(filters.command(["help"]))
async def send_help(client: Client, message: Message):
    await client.send_message(chat_id=message.chat.id, text=HELP_TXT)


@Client.on_message(filters.command(["cancel"]))
async def send_cancel(client: Client, message: Message):
    batch_temp.IS_BATCH[message.from_user.id] = True
    await client.send_message(chat_id=message.chat.id, text="**Batch Successfully Cancelled.**")


@Client.on_message(filters.text & filters.private)
async def save(client: Client, message: Message):
    text = message.text or ""
    if ("https://t.me/+" in text or "https://t.me/joinchat/" in text) and LOGIN_SYSTEM == False:
        if TechVJUser is None:
            await client.send_message(message.chat.id, "String Session is not Set", reply_to_message_id=message.id)
            return
        try:
            await TechVJUser.join_chat(text)
            await client.send_message(message.chat.id, "Chat Joined", reply_to_message_id=message.id)
        except UserAlreadyParticipant:
            await client.send_message(message.chat.id, "Chat already Joined", reply_to_message_id=message.id)
        except InviteHashExpired:
            await client.send_message(message.chat.id, "Invalid Link", reply_to_message_id=message.id)
        except Exception as e:
            await client.send_message(message.chat.id, f"Error : {e}", reply_to_message_id=message.id)
        return

    if "https://t.me/" not in text:
        return
    if batch_temp.IS_BATCH.get(message.from_user.id) == False:
        return await message.reply_text("**One Task Is Already Processing. Wait For Complete It. If You Want To Cancel This Task Then Use - /cancel**")

    links = list(dict.fromkeys(re.findall(r"https://t\.me/[^\s]+", text)))
    if not links:
        return

    if LOGIN_SYSTEM == True:
        user_data = await db.get_session(message.from_user.id)
        if user_data is None:
            await message.reply("**For Downloading Restricted Content You Have To /login First.**")
            return
        api_id = int(await db.get_api_id(message.from_user.id))
        api_hash = await db.get_api_hash(message.from_user.id)
        try:
            acc = Client("saverestricted", session_string=user_data, api_hash=api_hash, api_id=api_id)
            await acc.connect()
        except Exception:
            return await message.reply("**Your Login Session Expired. So /logout First Then Login Again By - /login**")
    else:
        if TechVJUser is None:
            await client.send_message(message.chat.id, "**String Session is not Set**", reply_to_message_id=message.id)
            return
        acc = TechVJUser

    batch_temp.IS_BATCH[message.from_user.id] = False
    try:
        for index, link in enumerate(links, 1):
            if batch_temp.IS_BATCH.get(message.from_user.id):
                break
            datas = link.split("/")
            try:
                parts = datas[-1].split("?")[0].split("-")
                from_id = int(parts[0])
                to_id = int(parts[1]) if len(parts) > 1 else from_id
            except (ValueError, IndexError):
                if ERROR_MESSAGE:
                    await client.send_message(message.chat.id, f"**Invalid Telegram link skipped:** {link}", reply_to_message_id=message.id)
                continue

            for msgid in range(from_id, to_id + 1):
                if batch_temp.IS_BATCH.get(message.from_user.id):
                    break
                try:
                    if "https://t.me/c/" in link:
                        await handle_private(client, acc, message, int("-100" + datas[4]), msgid)
                    elif "https://t.me/b/" in link:
                        await handle_private(client, acc, message, datas[4], msgid)
                    else:
                        username = datas[3]
                        msg = await client.get_messages(username, msgid)
                        try:
                            await client.copy_message(message.chat.id, msg.chat.id, msg.id, reply_to_message_id=message.id)
                        except Exception:
                            await handle_private(client, acc, message, username, msgid)
                except Exception as e:
                    if ERROR_MESSAGE:
                        await client.send_message(message.chat.id, f"Error processing link {link} (message {msgid}): {e}", reply_to_message_id=message.id)
                if not batch_temp.IS_BATCH.get(message.from_user.id):
                    await asyncio.sleep(WAITING_TIME)
            if not batch_temp.IS_BATCH.get(message.from_user.id):
                try:
                    await client.send_message(message.chat.id, f"**Queue:** {index}/{len(links)} completed.", reply_to_message_id=message.id)
                except Exception:
                    pass
    finally:
        if LOGIN_SYSTEM == True:
            try:
                await acc.disconnect()
            except Exception:
                pass
        batch_temp.IS_BATCH[message.from_user.id] = True


async def handle_private(client: Client, acc, message: Message, chatid, msgid: int):
    msg: Message = await acc.get_messages(chatid, msgid)
    if msg.empty:
        return
    msg_type = get_message_type(msg)
    if not msg_type:
        return
    try:
        chat = int(CHANNEL_ID) if CHANNEL_ID else message.chat.id
    except (ValueError, TypeError):
        chat = message.chat.id
    if batch_temp.IS_BATCH.get(message.from_user.id):
        return
    reply_id = message.id if chat == message.chat.id else None

    if msg_type == "Text":
        try:
            await client.send_message(chat, msg.text, entities=msg.entities, reply_to_message_id=reply_id, parse_mode=enums.ParseMode.HTML)
        except Exception as e:
            if ERROR_MESSAGE:
                await client.send_message(message.chat.id, f"Error: {e}", reply_to_message_id=message.id, parse_mode=enums.ParseMode.HTML)
        return

    smsg = await client.send_message(message.chat.id, "**Downloading**", reply_to_message_id=message.id)
    downfile = f"{message.id}downstatus.txt"
    upfile = f"{message.id}upstatus.txt"
    try:
        asyncio.create_task(downstatus(client, downfile, smsg, message.chat.id))
        file = await acc.download_media(msg, progress=progress, progress_args=[message, "down"])
        if os.path.exists(downfile):
            os.remove(downfile)
    except Exception as e:
        if ERROR_MESSAGE:
            await client.send_message(message.chat.id, f"Error: {e}", reply_to_message_id=reply_id, parse_mode=enums.ParseMode.HTML)
        await smsg.delete()
        return

    if batch_temp.IS_BATCH.get(message.from_user.id):
        if os.path.exists(file):
            os.remove(file)
        return
    asyncio.create_task(upstatus(client, upfile, smsg, message.chat.id))
    caption = msg.caption or None
    ph_path = None
    try:
        if msg_type == "Document":
            try:
                ph_path = await acc.download_media(msg.document.thumbs[0].file_id)
            except Exception:
                pass
            await client.send_document(chat, file, thumb=ph_path, caption=caption, reply_to_message_id=reply_id, parse_mode=enums.ParseMode.HTML, progress=progress, progress_args=[message, "up"])
        elif msg_type == "Video":
            try:
                ph_path = await acc.download_media(msg.video.thumbs[0].file_id)
            except Exception:
                pass
            await client.send_video(chat, file, duration=msg.video.duration, width=msg.video.width, height=msg.video.height, thumb=ph_path, caption=caption, reply_to_message_id=reply_id, parse_mode=enums.ParseMode.HTML, progress=progress, progress_args=[message, "up"])
        elif msg_type == "Animation":
            await client.send_animation(chat, file, reply_to_message_id=reply_id, parse_mode=enums.ParseMode.HTML)
        elif msg_type == "Sticker":
            await client.send_sticker(chat, file, reply_to_message_id=reply_id, parse_mode=enums.ParseMode.HTML)
        elif msg_type == "Voice":
            await client.send_voice(chat, file, caption=caption, caption_entities=msg.caption_entities, reply_to_message_id=reply_id, parse_mode=enums.ParseMode.HTML, progress=progress, progress_args=[message, "up"])
        elif msg_type == "Audio":
            try:
                ph_path = await acc.download_media(msg.audio.thumbs[0].file_id)
            except Exception:
                pass
            await client.send_audio(chat, file, thumb=ph_path, caption=caption, reply_to_message_id=reply_id, parse_mode=enums.ParseMode.HTML, progress=progress, progress_args=[message, "up"])
        elif msg_type == "Photo":
            await client.send_photo(chat, file, caption=caption, reply_to_message_id=reply_id, parse_mode=enums.ParseMode.HTML)
    except Exception as e:
        if ERROR_MESSAGE:
            await client.send_message(message.chat.id, f"Error: {e}", reply_to_message_id=reply_id, parse_mode=enums.ParseMode.HTML)
    finally:
        if ph_path and os.path.exists(ph_path):
            os.remove(ph_path)
        if os.path.exists(upfile):
            os.remove(upfile)
        if os.path.exists(file):
            os.remove(file)
        try:
            await client.delete_messages(message.chat.id, [smsg.id])
        except Exception:
            pass


def get_message_type(msg: pyrogram.types.messages_and_media.message.Message):
    for attr, name in (
        ("document", "Document"), ("video", "Video"), ("animation", "Animation"),
        ("sticker", "Sticker"), ("voice", "Voice"), ("audio", "Audio"),
        ("photo", "Photo"), ("text", "Text")
    ):
        try:
            getattr(msg, attr).file_id if attr != "text" else msg.text
            return name
        except Exception:
            pass
    return None
