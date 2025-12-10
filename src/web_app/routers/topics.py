from fastapi import APIRouter, Depends, Request, UploadFile, File
import aiofiles
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import uuid
import os

from ...data_manager.database import Database
from ...config import DB_PATH

# Инициализация роутера
router = APIRouter()

# Шаблоны
templates = Jinja2Templates(directory="src/web_app/templates")

# Зависимость для получения базы данных
async def get_db():
    db = Database(DB_PATH)
    return db

@router.get("/", response_class=HTMLResponse)
async def get_topics_page(request: Request, db: Database = Depends(get_db)):
    topics_list = await db.get_topics()
    return templates.TemplateResponse("index.html", {"request": request, "topics": topics_list})


@router.get("/add", response_class=HTMLResponse)
async def get_add_topic_page(request: Request):
    return templates.TemplateResponse("add_edit_topic.html", {"request": request, "topic": None})


@router.post("/add", response_class=HTMLResponse)
async def add_topic(request: Request, image: UploadFile = File(None), db: Database = Depends(get_db)):
    print("Начало обработки POST запроса для добавления темы")
    form_data = await request.form()
    topic_name = form_data.get("name", "").strip()
    print(f"Получено имя темы: '{topic_name}'")
    print(f"Получен объект изображения: {image}")
    if image and hasattr(image, 'filename'):
        print(f"Имя файла изображения: '{image.filename}'")
        print(f"Тип содержимого изображения: '{image.content_type}'")
        if hasattr(image, 'size'):
            print(f"Размер изображения: {image.size} байт")
        else:
            print("Размер изображения не определен напрямую, пытаемся получить из содержимого...")
            # Проверяем содержимое файла
            try:
                content = await image.read()
                print(f"Прочитано байт из файла: {len(content)}")
                await image.seek(0)  # Возвращаем указатель в начало для дальнейшей обработки
            except Exception as e:
                print(f"Ошибка при чтении содержимого файла: {e}")
    else:
        print("Объект изображения отсутствует или не является UploadFile")
    
    # Обработка загрузки изображения
    image_path = None
    if image and image.filename:
        print(f"Получено изображение: {image.filename}, тип: {image.content_type}")
        # Проверяем, что файл не пустой
        try:
            content = await image.read()
            if len(content) == 0:
                print("Предупреждение: файл изображения пустой")
            else:
                print(f"Файл изображения содержит {len(content)} байт данных")
                # Генерируем уникальное имя файла
                file_extension = os.path.splitext(image.filename)[1]
                unique_filename = str(uuid.uuid4()) + file_extension
                file_path = f"src/web_app/static/img/topics/{unique_filename}"
                
                # Создаем директорию, если она не существует
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                
                # Сохраняем файл асинхронно
                async with aiofiles.open(file_path, "wb") as buffer:
                    await buffer.write(content)
                print(f"Изображение сохранено по пути: {file_path}")
                
                # Формируем путь для базы данных (URL-путь)
                image_path = f"/topics_img/{unique_filename}"
            await image.seek(0)  # Возвращаем указатель в начало на всякий случай
        except Exception as e:
            print(f"Ошибка при обработке файла изображения: {e}")
    else:
        print("Изображение не было загружено")
    
    # Проверка длины названия темы
    if len(topic_name) > 100:
        # Возвращаем страницу с ошибкой
        return templates.TemplateResponse("add_edit_topic.html", {
            "request": request,
            "topic": None,
            "error": "Название темы не должно превышать 100 символов"
        })
    
    if not topic_name:
        # Возвращаем страницу с ошибкой
        return templates.TemplateResponse("add_edit_topic.html", {
            "request": request,
            "topic": None,
            "error": "Название темы не может быть пустым"
        })
    
    # Добавляем тему в базу данных
    await db.add_topic(topic_name, image_path)
    
    # Перенаправляем на главную страницу
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/", status_code=303)


@router.get("/edit/{topic_id}", response_class=HTMLResponse)
async def get_edit_topic_page(request: Request, topic_id: int, db: Database = Depends(get_db)):
    topic = await db.get_topic_by_id(topic_id)
    if not topic:
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/", status_code=303)
    
    return templates.TemplateResponse("add_edit_topic.html", {"request": request, "topic": topic})


@router.post("/edit/{topic_id}", response_class=HTMLResponse)
async def edit_topic(request: Request, topic_id: int, image: UploadFile = File(None), db: Database = Depends(get_db)):
    print(f"Начало обработки POST запроса для редактирования темы с ID: {topic_id}")
    form_data = await request.form()
    topic_name = form_data.get("name", "").strip()
    print(f"Получено имя темы: '{topic_name}'")
    print(f"Получен объект изображения: {image}")
    if image and hasattr(image, 'filename'):
        print(f"Имя файла изображения: '{image.filename}'")
        print(f"Тип содержимого изображения: '{image.content_type}'")
        if hasattr(image, 'size'):
            print(f"Размер изображения: {image.size} байт")
        else:
            print("Размер изображения не определен напрямую, пытаемся получить из содержимого...")
            # Проверяем содержимое файла
            try:
                content = await image.read()
                print(f"Прочитано байт из файла: {len(content)}")
                await image.seek(0)  # Возвращаем указатель в начало для дальнейшей обработки
            except Exception as e:
                print(f"Ошибка при чтении содержимого файла: {e}")
    else:
        print("Объект изображения отсутствует или не является UploadFile")
    
    # Получаем текущую тему для проверки
    topic = await db.get_topic_by_id(topic_id)
    if not topic:
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/", status_code=303)
    
    # Обработка загрузки изображения
    image_path = topic[3]  # Используем текущий путь к изображению по умолчанию
    if image and image.filename:
        print(f"Получено изображение: {image.filename}, тип: {image.content_type}")
        # Проверяем, что файл не пустой
        try:
            content = await image.read()
            if len(content) == 0:
                print("Предупреждение: файл изображения пустой")
            else:
                print(f"Файл изображения содержит {len(content)} байт данных")
                # Генерируем уникальное имя файла
                file_extension = os.path.splitext(image.filename)[1]
                unique_filename = str(uuid.uuid4()) + file_extension
                file_path = f"src/web_app/static/img/topics/{unique_filename}"
                
                # Создаем директорию, если она не существует
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                
                # Сохраняем файл асинхронно
                async with aiofiles.open(file_path, "wb") as buffer:
                    await buffer.write(content)
                print(f"Изображение сохранено по пути: {file_path}")
                
                # Формируем путь для базы данных (URL-путь)
                image_path = f"/topics_img/{unique_filename}"
            await image.seek(0)  # Возвращаем указатель в начало на всякий случай
        except Exception as e:
            print(f"Ошибка при обработке файла изображения: {e}")
    elif image and not image.filename:
        # Если передан пустой файл, сбрасываем изображение
        image_path = None
    else:
        print("Изображение не было загружено или не было изменено")
    
    # Проверка длины названия темы
    if len(topic_name) > 100:
        # Возвращаем страницу с ошибкой
        return templates.TemplateResponse("add_edit_topic.html", {
            "request": request,
            "topic": topic,
            "error": "Название темы не должно превышать 100 символов"
        })
    
    if not topic_name:
        # Возвращаем страницу с ошибкой
        return templates.TemplateResponse("add_edit_topic.html", {
            "request": request,
            "topic": topic,
            "error": "Название темы не может быть пустым"
        })
    
    # Обновляем тему в базе данных
    await db.update_topic(topic_id, topic_name, image_path)
    
    # Перенаправляем на главную страницу
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/", status_code=303)


@router.post("/delete/{topic_id}", response_class=HTMLResponse)
async def delete_topic(topic_id: int, db: Database = Depends(get_db)):
    # Удаляем тему из базы данных
    await db.delete_topic(topic_id)
    
    # Перенаправляем на главную страницу
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/", status_code=303)