import os
from telethon import TelegramClient, events
from telethon.errors import AboutTooLongError, FloodWaitError, RPCError
from telethon.tl.functions.account import UpdateProfileRequest, UpdateEmojiStatusRequest
from telethon.tl.types import EmojiStatus

import asyncio
import logging
from random import choice
import httpx
from typing import Optional

import re
from io import BytesIO
import numpy as np

from .config import TG_API_KEY, TG_API_HASH
from .quote_manager import get_random_quote
from .emoji_manager import get_random_emoji
from .data_paths import TELEGRAM_SESSION_FILE
from .logger import get_logger

logger = get_logger("Telegram")


class TelegramAPI:
    _client = None
    _telegram_lock = asyncio.Lock()
    _enabled = True

    current_status = None
    current_emoji_status = None

    @classmethod
    async def connect(cls):
        if not TELEGRAM_SESSION_FILE.exists():
            logger.error(f"Telegram session file not found: {TELEGRAM_SESSION_FILE}")
            cls._enabled = False
            return

        async with cls._telegram_lock:
            if cls._client is not None and cls._client.is_connected():
                return

            client = TelegramClient(str(TELEGRAM_SESSION_FILE), TG_API_KEY, TG_API_HASH)
            await client.connect()

            if not await client.is_user_authorized():
                await client.start()

            cls._client = client
            cls._enabled = True
            logger.info("Connected to Telegram")

            await register_outage_listener(cls._client)

    @classmethod
    async def reload_session(cls):
        async with cls._telegram_lock:
            if cls._client is not None:
                try:
                    await cls._client.disconnect()
                except Exception as e:
                    logger.warning(f"Failed to disconnect old Telegram client cleanly: {e}")
            cls._client = None
            cls._enabled = True
            cls.current_status = None
            cls.current_emoji_status = None

        await cls.connect()

    @classmethod
    async def set_status_text(cls, status: str):
        logger.debug(f"Trying to set status text: {status}")
        if not cls._enabled:
            logger.debug("Telegram is disabled due to missing session.")
            return
        if cls._client is None:
            await cls.connect()
        if not cls._enabled:
            return

        async with cls._telegram_lock:
            try:
                if cls.current_status != status:
                    await cls._client(UpdateProfileRequest(about=status))
                    logger.info(f"Updated Telegram profile status: {status}")
                    cls.current_status = status
                else:
                    logger.warning("Status unchanged, skipping update")
            except AboutTooLongError:
                logger.warning("Status message too long.")
            except FloodWaitError as e:
                logger.warning(f"Flood wait: wait {e.seconds} seconds before retrying.")
            except RPCError as e:
                logger.error(f"Telegram RPC error: {e}")

    @classmethod
    async def set_status_emoji(cls, emoji_id: int):
        logger.debug(f"Trying to set status emoji: {emoji_id}")
        if not cls._enabled:
            logger.debug("Telegram is disabled due to missing session.")
            return
        if cls._client is None:
            await cls.connect()
        if not cls._enabled:
            return

        try:
            emoji_id = int(emoji_id)
        except (ValueError, TypeError):
            logger.error(f"Invalid emoji_id passed: {emoji_id}")
            return

        async with cls._telegram_lock:
            try:
                if cls.current_emoji_status == emoji_id:
                    logger.warning("Emoji status unchanged, skipping update")
                    return
                cls.current_emoji_status = emoji_id
                emoji_status = EmojiStatus(document_id=emoji_id)
                await cls._client(UpdateEmojiStatusRequest(emoji_status))
                logger.info(f"Updated emoji status to emoji_id: {emoji_id}")
            except FloodWaitError as e:
                logger.warning(f"Flood wait: wait {e.seconds} seconds before retrying.")
            except RPCError as e:
                logger.error(f"Telegram RPC error: {e}")

    @classmethod
    async def set_default_status(cls):
        await cls.set_status_text(get_random_quote())

    @classmethod
    async def set_default_emoji(cls):
        await cls.set_status_emoji(get_random_emoji())

    @classmethod
    async def send_message(cls, chat_id: int | str, message: str, quiet: bool = False):
        if not cls._enabled:
            logger.error("Telegram is disabled due to missing session.")
            return
        if cls._client is None:
            await cls.connect()
        if not cls._enabled:
            return

        async with cls._telegram_lock:
            try:
                await cls._client.send_message(chat_id, message, silent=quiet)
                logger.info(f"Sent message to {chat_id}: {message} (quiet={quiet})")
            except FloodWaitError as e:
                logger.warning(f"Flood wait: wait {e.seconds} seconds before retrying.")
            except RPCError as e:
                logger.error(f"Telegram RPC error while sending message: {e}")


from .outages import handle_outage_message

from telethon import events
import re
import os
import cv2

async def register_outage_listener(client):
    DATE_REGEX = r"\b\d{2}\.\d{2}\.\d{4}\b"
    CHANNEL_ID = 1266403816

    album_buffer = {}

    def extract_date(text: str):
        if not text: return None
        match = re.search(DATE_REGEX, text)
        return match.group(0) if match else None

    async def download_to_cv2(msg):
        file_bytes = await msg.download_media(file=BytesIO())
        file_bytes.seek(0)
        np_arr = np.frombuffer(file_bytes.read(), np.uint8)
        return cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

    async def process_media_group(group_id):
        for _ in range(20):
            await asyncio.sleep(1.0)

            msgs = album_buffer.get(group_id, [])
            if not msgs:
                continue

            full_text = ""
            photos = []

            for m in msgs:
                t = getattr(m, 'message', '') or getattr(m, 'text', '') or getattr(m, 'raw_text', '')
                if t:
                    full_text = t
                if getattr(m, 'photo', None):
                    photos.append(m)

            date = extract_date(full_text)

            if date:
                album_buffer.pop(group_id, None)

                if "без обмежень" in full_text.lower():
                    await handle_outage_message(full_text, date)
                    return

                if photos:
                    photos.sort(key=lambda x: x.id)
                    first_photo = photos[0]
                    logger.info(f"Extracting outage schedule from FIRST photo for date {date}")
                    image = await download_to_cv2(first_photo)
                    await handle_outage_message(image, date)
                else:
                    logger.info(f"Extracting outage schedule from text for date {date}")
                    await handle_outage_message(full_text, date)
                return

        logger.warning(f"Album/Message {group_id} timed out without finding a valid date text.")
        album_buffer.pop(group_id, None)

    @client.on(events.NewMessage(chats=CHANNEL_ID))
    @client.on(events.MessageEdited(chats=CHANNEL_ID))
    async def on_message_or_edit(event):
        try:
            msg = event.message
            group_id = msg.grouped_id or msg.id

            if group_id not in album_buffer:
                album_buffer[group_id] = [msg]
                asyncio.create_task(process_media_group(group_id))
            else:
                existing = album_buffer[group_id]
                replaced = False
                for i, m in enumerate(existing):
                    if m.id == msg.id:
                        existing[i] = msg
                        replaced = True
                        break
                if not replaced:
                    existing.append(msg)

        except Exception as e:
            logger.error(f"Error buffering outage msg: {e}")
