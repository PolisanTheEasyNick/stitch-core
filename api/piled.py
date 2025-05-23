from typing import Optional

from fastapi import APIRouter, Query, Request, HTTPException

from .base import APIModule, get_real_ip
from core.piled import get_current_color, send_color_request
from core.config import IP_WHITELIST

class PiLEDModule(APIModule):
    def register_routes(self, router: APIRouter) -> None:
        @router.get("/piled")
        async def get_color():
            return get_current_color()

        @router.post("/piled")
        async def set_color(
            request: Request,
            hex: Optional[str] = Query(None, description="Hex color string like #ff00aa or ff00aa"),
            red: Optional[int] = Query(None, ge=0, le=255),
            green: Optional[int] = Query(None, ge=0, le=255),
            blue: Optional[int] = Query(None, ge=0, le=255)
        ):
            client_ip = get_real_ip(request)
            if client_ip not in IP_WHITELIST:
                raise HTTPException(status_code=403, detail=f"Forbidden: IP {client_ip} not allowed")

            try:
                if hex:
                    hex_clean = hex.lstrip("#")
                    if len(hex_clean) != 6:
                        return {"status": "error", "reason": "Invalid hex color length"}
                    r = int(hex_clean[0:2], 16)
                    g = int(hex_clean[2:4], 16)
                    b = int(hex_clean[4:6], 16)
                elif red is not None and green is not None and blue is not None:
                    r, g, b = red, green, blue
                else:
                    return {"status": "error", "reason": "Missing color parameters"}

                send_color_request(r, g, b, 3, 50)
                return {
                    "status": "ok",
                    "color": f"{r:02x}{g:02x}{b:02x}",
                    "red": r,
                    "green": g,
                    "blue": b
                }

            except Exception as e:
                return {"status": "error", "reason": str(e)}
