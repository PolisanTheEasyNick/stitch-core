from typing import Optional

from fastapi import APIRouter, Query, Request, HTTPException
from pydantic import BaseModel, Field, conint

from .base import APIModule, get_real_ip
from core.piled import get_current_color, send_color_request, update_default_color, get_default_color
from core.config import IP_WHITELIST
from core.logger import get_logger

from .activity import activity_data

logger = get_logger("PiLED")

class ColorRequest(BaseModel):
    hex: Optional[str] = Field(None, description="Hex color string like #ff00aa or ff00aa")
    red: Optional[conint(ge=0, le=255)] = None
    green: Optional[conint(ge=0, le=255)] = None
    blue: Optional[conint(ge=0, le=255)] = None

class DefaultColorRequest(BaseModel):
    color: str

class PiLEDModule(APIModule):
    def register_routes(self, router: APIRouter) -> None:

        @router.get("/piled")
        async def get_color():
            logger.debug("GET on /piled")
            return get_current_color()

        @router.post("/piled")
        async def set_color(request: Request, body: ColorRequest):
            logger.debug(f"POST on /piled, body: {body.dict()}")
            client_ip = get_real_ip(request)
            if client_ip not in IP_WHITELIST:
                logger.warning(f"POST on /piled from non-whitelisted IP: {client_ip}")
                raise HTTPException(status_code=403, detail=f"Forbidden: IP {client_ip} not allowed")

            if activity_data["is_someone_at_room"]:
                logger.warning("PiLED POST called, but no one in room. Ignoring request.")
                raise HTTPException(
                    status_code=403,
                    detail="Action forbidden: no one in room"
                )

            try:
                if body.hex:
                    logger.debug("hex detected")
                    hex_clean = body.hex.lstrip("#")
                    if len(hex_clean) != 6:
                        raise HTTPException(status_code=400, detail="Invalid hex color length")
                    r = int(hex_clean[0:2], 16)
                    g = int(hex_clean[2:4], 16)
                    b = int(hex_clean[4:6], 16)
                elif body.red is not None and body.green is not None and body.blue is not None:
                    logger.debug("rgb detected")
                    r, g, b = body.red, body.green, body.blue
                else:
                    logger.debug(f"nothing detected. body: {body.dict()}")
                    raise HTTPException(status_code=400, detail="Missing color parameters")

                send_color_request(r, g, b, 3, 50)
                logger.debug(f"Set color r: {r}, g: {g}, b: {b}")
                return {
                    "status": "ok",
                    "color": f"{r:02x}{g:02x}{b:02x}",
                    "red": r,
                    "green": g,
                    "blue": b
                }

            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @router.get("/piled/default")
        async def get_def_color():
            return {"color": get_default_color()}

        @router.post("/piled/default")
        async def set_def_color(request: Request, body: DefaultColorRequest):
            client_ip = get_real_ip(request)
            if client_ip not in IP_WHITELIST:
                logger.warning(f"POST on /piled/default from non-whitelisted IP: {client_ip}")
                raise HTTPException(status_code=403, detail=f"Forbidden: IP {client_ip} not allowed")
            
            update_default_color(body.color)
            return {"status": "ok", "new_default": body.color}