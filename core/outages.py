import os
import re
import asyncio
import socket
from typing import Union
import numpy as np
from .logger import get_logger

logger = get_logger("Outages")

PIPE_PATH = "/tmp/schedule_pipe"
SOCKET_PATH = "/tmp/schedule.sock"

OBLENERGO_CHAT_ID = 1266403816
BOTLOG_CHAT_ID = 1409418285

def parse_times(times: str, date: str) -> str | None:
    schedule = []
    last_end_time = "00:00"

    on_times = re.findall(
        r"(\d{2}:\d{2})\s*-\s*(\d{2}:\d{2})|з\s*(\d{2}:\d{2})", times
    )

    for match in on_times:
        if match[0] and match[1]:
            start_time, end_time = match[0], match[1]
            if last_end_time < start_time:
                schedule.append(f"{last_end_time}-{start_time}=off")
            schedule.append(f"{start_time}-{end_time}=on")
            last_end_time = end_time
        elif match[2]:
            start_time = match[2]
            if last_end_time < start_time:
                schedule.append(f"{last_end_time}-{start_time}=off")
            schedule.append(f"{start_time}-00:00=on")
            last_end_time = "00:00"

    # if last_end_time < "23:59":
    #     schedule.append(f"{last_end_time}-23:59=off")

    return f"date={date}\n" + "\n".join(schedule)

def parse_outage_image(img: np.ndarray) -> str | None:
    logger.debug(f"Image received for parsing")
    h, w, c = img.shape

    #so, starting points to crop are:
    #Y: 830 is top left of good value
    #how much down? to calculate, by counting where will be not white pixel
    #X: from 870 to 1200 looks good.
    pixels_down = 0
    while img[830+pixels_down, 870][0] > 200:
        pixels_down += 1

    crop_img = img[830:830+pixels_down, 870:1200]

    #step 2, OCR
    import pytesseract
    text = pytesseract.image_to_string(crop_img, lang="ukr")
    if "без обмежень" in text:
      return f"00:00-00:00"
    return text



def parse_outage_message(message: str) -> str | None:
    logger.debug(f"Message received: {message}")

    #was second, now first, i'm just too lazy to rename
    #second_line = message.splitlines()[0] if message.splitlines() else ""
    #logger.debug(f"Second line: {second_line}")

    if "без обмежень" in message:
        return f"00:00-00:00"

    group_2_match = re.search(r"(💡 Група 2.*?)(?=💡|$)", message, re.DOTALL)
    if not group_2_match:
        logger.debug("No 'Група 2' section found.")
        return None

    group_2 = group_2_match.group(1)
    #if "без обмежень" in group_2:
    #    return f"date={date}\n00:00-23:59=on"

    return group_2


async def handle_outage_message(message: Union[str, np.ndarray], date):
    """Parse, log, send to Telegram, and write to Unix socket."""
    from .telegram import TelegramAPI

    logger.info("Received new outage message, parsing...")
    if isinstance(message, str):
        times = parse_outage_message(message)
    elif isinstance(message, np.ndarray):
        times = parse_outage_image(message)
    else:
        logger.warning(f"Unsupported message type: {type(message)}")
        return
    result = parse_times(times, date)

    if not result:
        logger.warning("No valid outage info found in message.")
        return

    logger.info(f"Parsed outage schedule:\n{result}")

    try:
        if not os.path.exists(SOCKET_PATH):
            logger.warning(f"Unix socket not found: {SOCKET_PATH}")
            return

        reader, writer = await asyncio.open_unix_connection(SOCKET_PATH)
        writer.write(result.encode() + b"\n")
        await writer.drain()
        writer.close()
        await writer.wait_closed()

        logger.info(f"Wrote outage schedule to {SOCKET_PATH}")

    except Exception as e:
        logger.error(f"Error writing to socket {SOCKET_PATH}: {e}")
