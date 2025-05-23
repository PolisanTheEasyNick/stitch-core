from abc import ABC, abstractmethod
from fastapi import APIRouter, FastAPI, Request

def get_real_ip(request: Request) -> str:
    x_forwarded_for = request.headers.get("x-forwarded-for")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.client.host

class APIModule(ABC):
    @abstractmethod
    def register_routes(self, router: APIRouter) -> None:
        """Register the module's API routes to the given router"""
        pass

    def register_websockets(self, app: FastAPI):
        pass

    def register_events(self, app: FastAPI) -> None:
        pass