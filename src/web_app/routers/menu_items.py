from fastapi import APIRouter, Request, Form, Depends, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from ...config import DB_PATH
from ...data_manager.database import Database
import os
import uuid

# Зависимость для получения базы данных
async def get_db():
    db = Database(DB_PATH)
    return db

router = APIRouter()
templates = Jinja2Templates(directory="src/web_app/templates")


@router.get("/menu_items", response_class=HTMLResponse)
async def get_menu_items(request: Request, db: Database = Depends(get_db)):
    menu_items = await db.get_all_menu_items()
    print(f"DEBUG: Raw data from database: {menu_items}")
    # Преобразуем список кортежей в список словарей
    menu_items_dicts = [
        {
            "id": item[0],
            "key": item[1],
            "title": item[2],
            "content": item[3],
            "image_path": item[4]
        }
        for item in menu_items
    ]
    
    print(f"DEBUG: Transformed data to pass to template: {menu_items_dicts}")
    return templates.TemplateResponse("menu_items.html", {"request": request, "menu_items": menu_items_dicts})


@router.get("/menu_items/edit/{key}", response_class=HTMLResponse)
async def get_edit_menu_item(request: Request, key: str, db: Database = Depends(get_db)):
    menu_item = await db.get_menu_item(key)
    if not menu_item:
        return RedirectResponse(url="/admin/menu_items")
    return templates.TemplateResponse("edit_menu_item.html", {
        "request": request,
        "key": key,
        "title": menu_item[2], # индекс 2 соответствует полю title
        "content": menu_item[3], # индекс 3 соответствует полю content
        "image_path": menu_item[4], # индекс 4 соответствует полю image_path
        "url_link": menu_item[5] # индекс 5 соответствует полю url_link
    })


@router.post("/menu_items/edit/{key}", response_class=HTMLResponse)
async def post_edit_menu_item(
    request: Request,
    key: str,
    title: str = Form(...),
    content: str = Form(...),
    url_link: str = Form(""),  # Добавляем поле для ссылки
    image: UploadFile = None,
    db: Database = Depends(get_db)
):
    print(f"DEBUG: Received POST request to edit menu item '{key}'. Title length: {len(title)}, Content length: {len(content)}, URL Link: {url_link}")
    
    # Проверка длины содержания
    if len(content) > 1024:
        # Возвращаем пользователя на страницу редактирования с ошибкой
        # Получаем текущий пункт меню для отображения актуального image_path и url_link
        current_menu_item = await db.get_menu_item(key)
        current_image_path = current_menu_item[4] if current_menu_item else None
        current_url_link = current_menu_item[5] if current_menu_item and len(current_menu_item) > 5 else "" # Индекс 5 для url_link
        
        print(f"DEBUG: Content too long, returning error template for key '{key}'")
        return templates.TemplateResponse("edit_menu_item.html", {
            "request": request,
            "key": key,
            "title": title,
            "content": content,
            "image_path": current_image_path,
            "url_link": current_url_link, # Передаем текущую ссылку в шаблон
            "error": "Содержание не должно превышать 1024 символа"
        })
    
    # Проверка на валидность URL для пункта меню "catalog"
    if key == "catalog":
        from urllib.parse import urlparse
        parsed_url = urlparse(url_link)
        if not (parsed_url.scheme and parsed_url.netloc):
            # Возвращаем пользователя на страницу редактирования с ошибкой
            current_menu_item = await db.get_menu_item(key)
            current_image_path = current_menu_item[4] if current_menu_item else None
            current_url_link = current_menu_item[5] if current_menu_item and len(current_menu_item) > 5 else "" # Индекс 5 для url_link
            
            print(f"DEBUG: Invalid URL, returning error template for key '{key}'")
            return templates.TemplateResponse("edit_menu_item.html", {
                "request": request,
                "key": key,
                "title": title,
                "content": content,
                "image_path": current_image_path,
                "url_link": current_url_link, # Передаем текущую ссылку в шаблон
                "error": "Ссылка должна быть действительным URL-адресом"
            })
    
    # Создаем директорию для изображений меню, если она не существует
    menu_images_dir = "src/web_app/static/img/menu_items"
    os.makedirs(menu_images_dir, exist_ok=True)
    
    # Обрабатываем загрузку изображения
    image_path = None
    if image and image.filename:
        # Генерируем уникальное имя файла
        ext = os.path.splitext(image.filename)[1]
        unique_filename = f"{uuid.uuid4()}{ext}"
        image_path = os.path.join(menu_images_dir, unique_filename)
        
        # Сохраняем файл
        with open(image_path, "wb") as buffer:
            buffer.write(await image.read())
        
        # Формируем относительный путь для сохранения в базу данных
        image_path = f"src/web_app/static/img/menu_items/{unique_filename}"
    else:
        # Если новое изображение не загружено, получаем текущий путь к изображению из базы данных
        current_item = await db.get_menu_item(key)
        if current_item:
            image_path = current_item[4]  # индекс 4 соответствует полю image_path
        print(f"DEBUG: No new image uploaded, using existing image_path: {image_path}")
    
    # Логирование перед обновлением
    print(f"DEBUG: Updating menu item '{key}' with title='{title}', content='{content[:50]}...', image_path='{image_path}', url_link='{url_link}'")
    success = await db.update_menu_item(key, title, content, image_path, url_link) # Передаем url_link в update_menu_item
    if success:
        print(f"DEBUG: Menu item '{key}' updated successfully")
    else:
        print(f"ERROR: Failed to update menu item '{key}' in database")
    return RedirectResponse(url="/admin/menu_items", status_code=303)