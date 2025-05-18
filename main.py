import importlib
import pkgutil
from fastapi import FastAPI, APIRouter
from api.base import APIModule

def load_modules() -> list[APIModule]:
    modules = []
    for finder, name, _ in pkgutil.iter_modules(["api"]):
        if name == "base":
            continue

        full_name = f"api.{name}"
        module = importlib.import_module(full_name)

        for attr in dir(module):
            obj = getattr(module, attr)
            if isinstance(obj, type) and issubclass(obj, APIModule) and obj is not APIModule:
                instance = obj()
                modules.append(instance)
    return modules

def create_app() -> FastAPI:
    app = FastAPI()
    main_router = APIRouter()

    for module in load_modules():
        module.register_routes(main_router)
        module.register_websockets(main_router)
        module.register_events(app)

    app.include_router(main_router)
    return app

app = create_app()
