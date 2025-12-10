from fastapi import APIRouter, Depends, Request, File, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import uuid
import os
import logging

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

@router.get("/{topic_id}/courses", response_class=HTMLResponse)
async def get_courses_page(request: Request, topic_id: int, db: Database = Depends(get_db)):
    courses_list = await db.get_courses_by_topic_id(topic_id)
    topic = await db.get_topic_by_id(topic_id)
    if not topic:
        return RedirectResponse(url="/", status_code=303)
    return templates.TemplateResponse("courses.html", {
        "request": request,
        "courses": courses_list,
        "topic": topic,
        "current_topic_id": topic_id
    })
@router.get("/{topic_id}/courses/add", response_class=HTMLResponse)
async def get_add_course_page(request: Request, topic_id: int, db: Database = Depends(get_db)):
    topic = await db.get_topic_by_id(topic_id)
    if not topic:
        return RedirectResponse(url="/", status_code=303)
    return templates.TemplateResponse("add_edit_course.html", {
        "request": request,
        "course": None,
        "topic": topic
    })


@router.post("/{topic_id}/courses/add", response_class=HTMLResponse)
async def add_course(request: Request, topic_id: int, image: UploadFile = File(None), db: Database = Depends(get_db)):
    logging.info(f"Вызов функции add_course роутера с параметрами: topic_id={topic_id}")
    
    form_data = await request.form()
    name = form_data.get("name", "").strip()
    description = form_data.get("description", "").strip()
    price = form_data.get("price", "").strip()
    payment_link = form_data.get("payment_link", "").strip()
    image_path = form_data.get("image_path", "").strip()
    
    # Обработка загрузки изображения
    if image and image.filename:
        # Проверяем, что файл является изображением
        if not image.content_type.startswith("image/"):
            topic = await db.get_topic_by_id(topic_id)
            return templates.TemplateResponse("add_edit_course.html", {
                "request": request,
                "course": None,
                "topic": topic,
                "error": "Файл должен быть изображением"
            })
        
        # Создаем директорию для изображений курсов, если она не существует
        os.makedirs("src/web_app/static/img/courses", exist_ok=True)
        
        # Генерируем уникальное имя файла
        file_extension = os.path.splitext(image.filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = os.path.join("src/web_app/static/img/courses", unique_filename)
        
        # Сохраняем файл
        with open(file_path, "wb") as f:
            f.write(await image.read())
        
        # Формируем относительный путь для сохранения в базе данных
        image_path = f"src/web_app/static/img/courses/{unique_filename}"
    
    # Проверка длины описания
    if len(description) > 1024:
        topic = await db.get_topic_by_id(topic_id)
        return templates.TemplateResponse("add_edit_course.html", {
            "request": request,
            "course": None,
            "topic": topic,
            "error": "Описание не должно превышать 1024 символа"
        })
    
    # Базовая валидация
    if not name or not price:
        topic = await db.get_topic_by_id(topic_id)
        return templates.TemplateResponse("add_edit_course.html", {
            "request": request,
            "course": None,
            "topic": topic,
            "error": "Название и цена не могут быть пустыми"
        })
    
    try:
        price = float(price)
    except ValueError:
        topic = await db.get_topic_by_id(topic_id)
        return templates.TemplateResponse("add_edit_course.html", {
            "request": request,
            "course": None,
            "topic": topic,
            "error": "Цена должна быть числом"
        })
    
    # Логируем передаваемые аргументы
    logging.info(f"Передача аргументов в db.add_course: topic_id={topic_id}, name={name}, description={description}, price={price}, payment_link={payment_link}, image_path={image_path}")
    
    try:
        # Добавляем курс в базу данных
        await db.add_course(topic_id, name, description, price, payment_link, image_path)
        logging.info(f"Курс '{name}' успешно добавлен в базу данных")
    except Exception as e:
        logging.error(f"Ошибка при добавлении курса в базу данных: {e}")
        raise
    
    # Перенаправляем на страницу курсов темы
    return RedirectResponse(url=f"/topics/{topic_id}/courses", status_code=303)

@router.get("/{topic_id}/courses/{course_id}/edit", response_class=HTMLResponse)
async def get_edit_course_page(request: Request, topic_id: int, course_id: int, db: Database = Depends(get_db)):
    course = await db.get_course_by_id(course_id)
    if not course:
        return RedirectResponse(url="/", status_code=303)
    
    # Проверяем, принадлежит ли курс указанной теме
    if course[4] != topic_id:  # topic_id находится в 4-й позиции в кортеже
        return RedirectResponse(url="/", status_code=303)
    
    # Получаем информацию о теме для отображения
    topic = await db.get_topic_by_id(course[4])  # topic_id находится в 4-й позиции в кортеже
    return templates.TemplateResponse("add_edit_course.html", {
        "request": request,
        "course": course,
        "topic": topic
    })

@router.post("/{topic_id}/courses/{course_id}/edit", response_class=HTMLResponse)
async def edit_course(request: Request, topic_id: int, course_id: int, image: UploadFile = File(None), db: Database = Depends(get_db)):
    form_data = await request.form()
    name = form_data.get("name", "").strip()
    description = form_data.get("description", "").strip()
    price = form_data.get("price", "").strip()
    payment_link = form_data.get("payment_link", "").strip()
    # Не берем image_path из формы при редактировании, если загружается новое изображение
    current_course = await db.get_course_by_id(course_id)
    if not current_course or current_course[4] != topic_id:
        return RedirectResponse(url="/", status_code=303)
    current_image_path = current_course[6]  # image_path находится в 6-й позиции в кортеже (id, name, description, price, topic_id, payment_link, image_path)
    
    image_path = current_image_path  # по умолчанию сохраняем старый путь
    
    # Обработка загрузки изображения
    if image and image.filename:
        # Проверяем, что файл является изображением
        if not image.content_type.startswith("image/"):
            course = await db.get_course_by_id(course_id)
            # Проверяем, принадлежит ли курс указанной теме
            if not course or course[4] != topic_id:  # topic_id находится в 4-й позиции в кортеже
                return RedirectResponse(url="/", status_code=303)
            topic = await db.get_topic_by_id(course[4])  # topic_id находится в 4-й позиции в кортеже
            return templates.TemplateResponse("add_edit_course.html", {
                "request": request,
                "course": course,
                "topic": topic,
                "error": "Файл должен быть изображением"
            })
        
        # Создаем директорию для изображений курсов, если она не существует
        os.makedirs("src/web_app/static/img/courses", exist_ok=True)
        
        # Генерируем уникальное имя файла
        file_extension = os.path.splitext(image.filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = os.path.join("src/web_app/static/img/courses", unique_filename)
        
        # Сохраняем файл
        with open(file_path, "wb") as f:
            f.write(await image.read())
        
        # Формируем относительный путь для сохранения в базе данных
        image_path = f"src/web_app/static/img/courses/{unique_filename}"
    
    # Проверка длины описания
    if len(description) > 1024:
        course = await db.get_course_by_id(course_id)
        # Проверяем, принадлежит ли курс указанной теме
        if not course or course[4] != topic_id:  # topic_id находится в 4-й позиции в кортеже
            return RedirectResponse(url="/", status_code=303)
        topic = await db.get_topic_by_id(course[4])  # topic_id находится в 4-й позиции в кортеже
        return templates.TemplateResponse("add_edit_course.html", {
            "request": request,
            "course": course,
            "topic": topic,
            "error": "Описание не должно превышать 1024 символа"
        })
    
    # Базовая валидация
    if not name or not price:
        course = await db.get_course_by_id(course_id)
        # Проверяем, принадлежит ли курс указанной теме
        if not course or course[4] != topic_id:  # topic_id находится в 4-й позиции в кортеже
            return RedirectResponse(url="/", status_code=303)
        topic = await db.get_topic_by_id(course[4])  # topic_id находится в 4-й позиции в кортеже
        return templates.TemplateResponse("add_edit_course.html", {
            "request": request,
            "course": course,
            "topic": topic,
            "error": "Название и цена не могут быть пустыми"
        })
    
    try:
        price = float(price)
    except ValueError:
        course = await db.get_course_by_id(course_id)
        # Проверяем, принадлежит ли курс указанной теме
        if not course or course[4] != topic_id:  # topic_id находится в 4-й позиции в кортеже
            return RedirectResponse(url="/", status_code=303)
        topic = await db.get_topic_by_id(course[4])  # topic_id находится в 4-й позиции в кортеже
        return templates.TemplateResponse("add_edit_course.html", {
            "request": request,
            "course": course,
            "topic": topic,
            "error": "Цена должна быть числом"
        })
    
    # Обновляем курс в базу данных
    await db.update_course(course_id, name, description, price, payment_link, image_path)
    
    # Перенаправляем на страницу курсов темы
    return RedirectResponse(url=f"/topics/{topic_id}/courses", status_code=303)

@router.post("/{topic_id}/courses/{course_id}/delete", response_class=HTMLResponse)
async def delete_course(topic_id: int, course_id: int, db: Database = Depends(get_db)):
    # Получаем курс перед удалением, чтобы проверить принадлежность к теме
    course = await db.get_course_by_id(course_id)
    if not course or course[4] != topic_id:  # topic_id находится в 4-й позиции в кортеже
        return RedirectResponse(url="/", status_code=303)
    
    # Удаляем курс из базы данных
    await db.delete_course(course_id)
    
    # Перенаправляем на страницу курсов темы
    return RedirectResponse(url=f"/topics/{topic_id}/courses", status_code=303)