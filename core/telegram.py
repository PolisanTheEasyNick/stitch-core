import os
from telethon import TelegramClient
from telethon.errors import AboutTooLongError, FloodWaitError, RPCError
from telethon.tl.functions.account import UpdateProfileRequest, UpdateEmojiStatusRequest
from telethon.tl.types import EmojiStatus

import asyncio
import logging
from random import choice
import httpx
from typing import Optional

from .config import TG_API_KEY, TG_API_HASH
from .quote_manager import get_random_quote
from .emoji_manager import get_random_emoji
from .logger import get_logger
from .enums import ActivityType

logger = get_logger("Telegram")

SESSION_PATH = "/data/Stitch.session"

class TelegramAPI:
    _client = None
    _telegram_lock = asyncio.Lock()
    _enabled = True  # New flag

    current_status = None
    current_emoji_status = None

    @classmethod
    async def connect(cls):
        if not os.path.exists(SESSION_PATH):
            logger.error(f"Telegram session file not found: {SESSION_PATH}")
            cls._enabled = False
            return

        async with cls._telegram_lock:
            if cls._client is not None and cls._client.is_connected():
                return

            client = TelegramClient(SESSION_PATH, TG_API_KEY, TG_API_HASH)

            if not client.is_connected():
                await client.connect()

            retries = 10
            while not client.is_connected() and retries > 0:
                await asyncio.sleep(0.5)
                retries -= 1

            if not await client.is_user_authorized():
                await client.start()

            cls._client = client
            logger.info("Connected to Telegram")

    @classmethod
    async def set_status_text(cls, status: str):
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
    async def send_message(cls, chat_id: int | str, message: str):
        if not cls._enabled:
            logger.error("Telegram is disabled due to missing session.")
            return
        if cls._client is None:
            await cls.connect()
        if not cls._enabled:
            return

        async with cls._telegram_lock:
            try:
                await cls._client.send_message(chat_id, message)
                logger.info(f"Sent message to {chat_id}: {message}")
            except FloodWaitError as e:
                logger.warning(f"Flood wait: wait {e.seconds} seconds before retrying.")
            except RPCError as e:
                logger.error(f"Telegram RPC error while sending message: {e}")

