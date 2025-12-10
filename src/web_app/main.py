from fastapi import FastAPI, Request, Depends
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

import os

from .routers import topics, courses, menu_items, promotions
from ..config import DB_PATH
from ..data_manager.database import Database

# Инициализация приложения FastAPI
app = FastAPI(title="Админ-панель курсов", description="Веб-интерфейс для управления курсами и темами")

from jinja2 import FileSystemLoader
from pathlib import Path

# Настройка шаблонов с возможностью загрузки из нескольких директорий
template_dirs = [
    "src/web_app/templates",
    "vless-shopbot/src/shop_bot/webhook_server/templates"  # Директория с общими шаблонами
]
loader = FileSystemLoader(template_dirs)
templates = Jinja2Templates(directory="src/web_app/templates", loader=loader)

# Монтирование статических файлов с кэшированием
from .static_files import CachedStaticFiles

app.mount("/static", CachedStaticFiles(directory="src/web_app/static", cache_time=3600), name="static")
app.mount("/courses_img", CachedStaticFiles(directory="src/web_app/static/img/courses", cache_time=3600), name="courses_img")
app.mount("/topics_img", CachedStaticFiles(directory="src/web_app/static/img/topics", cache_time=3600), name="topics_img")

# Подключение роутеров
app.include_router(topics.router, prefix="/topics", tags=["topics"])
app.include_router(courses.router, prefix="/topics", tags=["courses"])
app.include_router(menu_items.router, prefix="/admin", tags=["admin"])
app.include_router(promotions.router, prefix="", tags=["promotions"])
# Роутер catalog больше не используется, так как функциональность интегрирована в menu_items

# Зависимость для получения базы данных
async def get_db():
    db = Database(DB_PATH)
    return db

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    db = await get_db()
    topics_list = await db.get_topics()
    menu_items = await db.get_all_menu_items()
    return templates.TemplateResponse("index.html", {"request": request, "topics": topics_list, "menu_items": menu_items})


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 404:
        return templates.TemplateResponse("404.html", {"request": request}, status_code=404)
    else:
        return templates.TemplateResponse("500.html", {"request": request}, status_code=exc.status_code)


@app.exception_handler(500)
async def internal_error(request: Request, exc):
    return templates.TemplateResponse("500.html", {"request": request}, status_code=500)


# Маршруты для админ-панели акций
