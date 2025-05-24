import importlib
import pkgutil

from fastapi import FastAPI, APIRouter
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware


from api.base import APIModule
from core.config import HOSTNAME

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

    @app.get("/services/status")
    async def get_services_status():
        return [
            {"name": "spotify", "last_update": "2025-05-18T12:34:56", "alive": True},
            {"name": "weather", "last_update": "2025-05-18T12:30:00", "alive": False},
        ]

    @app.get("/", response_class=HTMLResponse)
    async def list_routes():
        exclude_paths = {"/openapi.json", "/docs", "/docs/oauth2-redirect", "/redoc", "/"}
        unique_paths = set()

        for route in app.routes:
            if hasattr(route, "path"):
                path = route.path
                if path not in exclude_paths and "{" not in path:
                    unique_paths.add(path)
        links = [f'<li><a href="{path}">{path}</a></li>' for path in sorted(unique_paths)]
        links_html = "\n".join(links)
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Available Routes</title>
            <style>
                body {{ font-family: monospace; background: #1e1e1e; color: #eee; padding: 20px; }}
                a {{ color: #4fc3f7; text-decoration: none; }}
                a:hover {{ text-decoration: underline; }}
            </style>
        </head>
        <body>
            <h1>Available Routes</h1>
            <ul>
                {links_html}
            </ul>
        </body>
        </html>
        """
        return HTMLResponse(content=html_content)

    app.add_middleware(
        CORSMiddleware,
        #allow_origins=[HOSTNAME],
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    return app



app = create_app()
