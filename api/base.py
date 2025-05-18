from abc import ABC, abstractmethod
from fastapi import APIRouter, FastAPI

class APIModule(ABC):
    @abstractmethod
    def register_routes(self, router: APIRouter) -> None:
        """Register the module's API routes to the given router"""
        pass

    def register_websockets(self, app: FastAPI):
        pass

    def register_events(self, app: FastAPI) -> None:
        pass