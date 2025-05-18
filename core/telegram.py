from telethon import TelegramClient
from telethon.errors import AboutTooLongError, FloodWaitError, RPCError
from telethon.tl.functions.account import UpdateProfileRequest, UpdateEmojiStatusRequest
from telethon.tl.types import EmojiStatus

import asyncio
import logging
from random import choice

from .config import TG_API_KEY, TG_API_HASH
from .quote_manager import load_quotes

logger = logging.getLogger(__name__)

class TelegramAPI:
    _client = None
    _telegram_lock = asyncio.Lock()

    current_status = None

    @classmethod
    async def connect(cls):
        async with cls._telegram_lock:
            if cls._client is not None and cls._client.is_connected():
                return

            client = TelegramClient("/data/Stitch.session", TG_API_KEY, TG_API_HASH)

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
        if cls._client is None:
            await cls.connect()
        async with cls._telegram_lock:
            try:
                if cls.current_status != status:
                    await cls._client(UpdateProfileRequest(about=status))
                    logger.info(f"Updated Telegram profile status: {status}")
                    cls.current_status = status
            except AboutTooLongError:
                logger.warning("Status message too long.")
            except FloodWaitError as e:
                logger.warning(f"Flood wait: wait {e.seconds} seconds before retrying.")
            except RPCError as e:
                logger.error(f"Telegram RPC error: {e}")

    @classmethod
    async def set_status_emoji(cls, emoji_id: int):
        if cls._client is None:
            await cls.connect()
        async with cls._telegram_lock:
            try:
                emoji_status = EmojiStatus(document_id=emoji_id)
                await cls._client(UpdateEmojiStatusRequest(emoji_status))
                logger.info(f"Updated emoji status to emoji_id: {emoji_id}")
            except FloodWaitError as e:
                logger.warning(f"Flood wait: wait {e.seconds} seconds before retrying.")
            except RPCError as e:
                logger.error(f"Telegram RPC error: {e}")

    @classmethod
    async def set_default_status(cls):
        quote = choice(load_quotes()).strip()
        await cls.set_status_text(quote)
