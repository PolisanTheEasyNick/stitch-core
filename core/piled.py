import hmac
import hashlib
import random
import socket
from time import time
import struct

from core.config import PILED_SHARED_SECRET, PILED_ADDRESS, PILED_DEFAULT_COLOR
from .logger import get_logger

logger = get_logger("PiLED-back")

def hmac_sha256(secret, data):
    secret_key = bytes(secret, "utf-8")
    return hmac.new(secret_key, data, hashlib.sha256).digest()


def send_tcp_packet(host, port, data):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect((host, port))
            sock.sendall(data)
            logger.debug(f"Data sent to {host}:{port}")
    except Exception as e:
        logger.debug(f"An error occurred: {e}")


def send_color_request(red, green, blue, duration = 3, steps = 150):
    logger.debug(f"Send color request called with: {red}, {green}, {blue}")
    current_timestamp = int(time())
    nonce = random.getrandbits(64)
    timestamp_bytes = struct.pack(">Q", current_timestamp)
    nonce_bytes = struct.pack(">Q", nonce)
    version = 2
    HEADER = timestamp_bytes + nonce_bytes + struct.pack(">B", version)
    PAYLOAD = bytes([red, green, blue, duration])
    header_with_payload = HEADER + PAYLOAD
    hex_string = " ".join(f"{b:02X}" for b in header_with_payload)
    hmac_result = hmac_sha256(PILED_SHARED_SECRET, header_with_payload)
    hex_string = "".join(f"{b:02X}" for b in hmac_result)
    tcp_package = HEADER + hmac_result + PAYLOAD
    send_tcp_packet(PILED_ADDRESS, 3384, tcp_package)

def get_current_color():
    logger.debug("Get current color called")
    current_timestamp = int(time())
    nonce = random.getrandbits(64)
    timestamp_bytes = struct.pack(">Q", current_timestamp)
    nonce_bytes = struct.pack(">Q", nonce)
    version = 4
    OP = 1  # LED_GET_CURRENT_COLOR
    HEADER = timestamp_bytes + nonce_bytes + struct.pack(">B", version) + struct.pack(">B", OP)

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect((PILED_ADDRESS, 3384))
            sock.sendall(HEADER)
            logger.debug(f"Data sent to {PILED_ADDRESS}:3384")
            response = sock.recv(1024)
            logger.debug(f"Received response: {response.hex()}")

            if len(response) >= 0x35:
                red = response[0x32]
                green = response[0x33]
                blue = response[0x34]
                color = f"{red:02x}{green:02x}{blue:02x}"

                return {
                    "status": "ok",
                    "color": color,
                    "red": red,
                    "green": green,
                    "blue": blue
                }

            else:
                return {"status": "error", "reason": "Incomplete response"}

    except Exception as e:
        logger.error(f"An error occurred: {e}")
        return {"status": "error", "reason": str(e)}

def set_default_color():
    logger.debug("Set default color called")
    color = PILED_DEFAULT_COLOR
    if color.startswith("#"):
        color = color[1:]

    r = int(color[0:2], 16)
    g = int(color[2:4], 16)
    b = int(color[4:6], 16)
    send_color_request(r, g, b, 3, 50)