from fastapi import APIRouter, Depends, Request, File, UploadFile, HTTPException, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import uuid
import os
from pydantic import BaseModel, Field, validator, ValidationError
from typing import Optional
import datetime
from typing_extensions import Annotated

from ...data_manager.database import Database
from ...config import DB_PATH

# Инициализация роутера
router = APIRouter()

# Шаблоны
templates = Jinja2Templates(directory="src/web_app/templates")

# Pydantic модели для акций
class PromotionBase(BaseModel):
    name: str = Field(..., min_length=1)
    description: Optional[str] = None
    course_link: str = Field(..., min_length=1)  # Изменили на course_link
    discounted_price: Optional[float] = Field(None, ge=0.0) # Сделали необязательным
    start_date: Optional[datetime.date] = None # Сделали необязательным
    end_date: Optional[datetime.date] = None  # Сделали необязательным
    is_period_enabled: Optional[bool] = False
    is_price_enabled: Optional[bool] = False
    image_path: Optional[str] = None

    @validator('discounted_price', pre=True)
    def parse_price_field(cls, v):
        if v is None or v == "" or v == "null":
            return None
        if isinstance(v, (int, float)):
            return float(v)
        if isinstance(v, str):
            try:
                return float(v)
            except ValueError:
                raise ValueError("Цена должна быть числом.")
        return v

    @validator('image_path', pre=True)
    def set_empty_string_to_none(cls, v):
        if v == "":
            return None
        return v

    @validator('start_date', 'end_date', pre=True)
    def parse_date_fields(cls, v):
        if v is None or v == "" or v == "null":
            return None
        if isinstance(v, datetime.date):
            return v
        if isinstance(v, str):
            try:
                return datetime.datetime.strptime(v, '%Y-%m-%d').date()
            except ValueError:
                raise ValueError("Неверный формат даты. Ожидается YYYY-MM-DD.")
        raise ValueError("Дата должна быть строкой в формате YYYY-MM-DD или объектом даты.")

class PromotionCreate(PromotionBase):
    pass

class PromotionUpdate(PromotionBase):
    name: Optional[str] = None
    course_link: Optional[str] = Field(None, min_length=1)
    # Поля уже определены в базовом классе как Optional, поэтому не нужно повторять

class PromotionInDB(PromotionBase):
    id: int

# Зависимость для получения базы данных
async def get_db():
    db = Database(DB_PATH)
    return db

@router.get("/promotions/add", response_class=HTMLResponse)
async def get_add_promotion_page(request: Request, db: Database = Depends(get_db)):
    return templates.TemplateResponse("add_edit_promotion.html", {
        "request": request,
        "promotion": None,
        "courses": []  # Удалили список курсов, так как теперь используется course_link
    })

@router.post("/promotions/add", response_class=HTMLResponse)
async def add_promotion(
    request: Request,
    name: Annotated[str, Form()],
    course_link: Annotated[str, Form()],
    discounted_price: Annotated[Optional[float], Form()] = None,
    start_date: Annotated[Optional[str], Form()] = None, # Сделали необязательным
    end_date: Annotated[Optional[str], Form()] = None,   # Сделали необязательным
    is_period_enabled: Annotated[Optional[bool], Form()] = False,
    is_price_enabled: Annotated[Optional[bool], Form()] = False,
    description: Annotated[Optional[str], Form()] = None,
    image: UploadFile = File(None),
    db: Database = Depends(get_db)
):
    image_path = None
    if image and image.filename:
        if not image.content_type.startswith("image/"):
            return templates.TemplateResponse("add_edit_promotion.html", {
                "request": request,
                "promotion": None,
                "error": "Файл должен быть изображением"
            })
        os.makedirs("src/web_app/static/img/promotions", exist_ok=True)
        file_extension = os.path.splitext(image.filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = os.path.join("src/web_app/static/img/promotions", unique_filename)
        with open(file_path, "wb") as f:
            f.write(await image.read())
        image_path = f"src/web_app/static/img/promotions/{unique_filename}"

    try:
        # Обработка значений в зависимости от состояния чекбоксов
        processed_discounted_price = discounted_price if is_price_enabled else None
        processed_start_date = start_date if is_period_enabled else None
        processed_end_date = end_date if is_period_enabled else None

        # Преобразуем булевы значения, проверяя на None
        period_enabled_bool = bool(is_period_enabled) if is_period_enabled is not None else False
        price_enabled_bool = bool(is_price_enabled) if is_price_enabled is not None else False
        
        # Убедимся, что поля даты и цены равны None, если соответствующие чекбоксы не отмечены
        if not period_enabled_bool:
            processed_start_date = None
            processed_end_date = None
        if not price_enabled_bool:
            processed_discounted_price = None

        promotion_data = PromotionCreate(
            name=name,
            description=description,
            course_link=course_link,
            discounted_price=processed_discounted_price,
            start_date=processed_start_date,
            end_date=processed_end_date,
            is_period_enabled=period_enabled_bool,
            is_price_enabled=price_enabled_bool,
            image_path=image_path
        )
        await db.add_promotion(
            promotion_data.name,
            promotion_data.description,
            promotion_data.course_link,
            promotion_data.discounted_price,
            promotion_data.start_date,
            promotion_data.end_date,
            promotion_data.is_period_enabled,
            promotion_data.is_price_enabled,
            promotion_data.image_path
        )
        return RedirectResponse(url="/promotions", status_code=303)
    except ValidationError as e:
        # Обработка ошибок валидации
        errors = e.errors()
        error_messages = []
        for error in errors:
            loc = error["loc"][0] if error["loc"] else "Общая ошибка"
            msg = error["msg"]
            error_messages.append(f"Поле '{loc}': {msg}")
        
        # Подготовка данных для повторного отображения формы
        # Здесь можно заполнить поля формы данными, которые пользователь уже ввел
        # Для простоты пока просто выводим ошибки
        return templates.TemplateResponse("add_edit_promotion.html", {
            "request": request,
            "promotion": {
                "name": name,
                "description": description,
                "course_link": course_link,
                "discounted_price": discounted_price,
                "start_date": start_date,
                "end_date": end_date,
                "image_path": image_path
            },
            "error": "Произошли ошибки валидации: " + "; ".join(error_messages)
        })
    except Exception as e:
        return templates.TemplateResponse("add_edit_promotion.html", {
            "request": request,
            "promotion": None,
            "error": f"Неизвестная ошибка: {e}"
        })

@router.get("/promotions", response_class=HTMLResponse)
async def get_promotions_page(request: Request, db: Database = Depends(get_db)):
    promotions_list = await db.get_all_promotions()
    # Теперь в promotions_list course_link вместо course_id
    promotions_with_course_info = []
    for promotion in promotions_list:
        promotion_id, name, description, course_link, discounted_price, start_date, end_date, image_path, is_period_enabled, is_price_enabled = promotion
        promotions_with_course_info.append({
            'id': promotion_id,
            'name': name,
            'description': description,
            'course_link': course_link,  # Теперь используем course_link
            'discounted_price': discounted_price,
            'start_date': start_date,
            'end_date': end_date,
            'is_period_enabled': is_period_enabled,
            'is_price_enabled': is_price_enabled,
            'image_path': image_path
        })
    return templates.TemplateResponse("promotions.html", {
        "request": request,
        "promotions": promotions_with_course_info
    })

@router.post("/promotions/{promotion_id}/edit", response_class=HTMLResponse)
async def edit_promotion(
    request: Request,
    promotion_id: int,
    name: Annotated[str, Form()],
    course_link: Annotated[str, Form()],
    discounted_price: Annotated[Optional[float], Form()] = None,
    start_date: Annotated[Optional[str], Form()] = None,  # Сделали необязательным
    end_date: Annotated[Optional[str], Form()] = None,   # Сделали необязательным
    is_period_enabled: Annotated[Optional[bool], Form()] = False,
    is_price_enabled: Annotated[Optional[bool], Form()] = False,
    description: Annotated[Optional[str], Form()] = None,
    image: UploadFile = File(None),
    db: Database = Depends(get_db)
):
    # Получаем текущую акцию для получения текущего image_path и других данных
    current_promotion = await db.get_promotion_by_id(promotion_id)
    if not current_promotion:
        return RedirectResponse(url="/", status_code=303)
    
    current_image_path = current_promotion[7]  # image_path находится в 7-й позиции в кортеже (id, name, description, course_link, discounted_price, start_date, end_date, image_path, is_period_enabled, is_price_enabled)
    image_path = current_image_path  # по умолчанию сохраняем старый путь
    
    # Обработка загрузки изображения
    if image and image.filename:
        if not image.content_type.startswith("image/"):
            # Получаем текущую акцию для отображения ошибки
            current_promotion = await db.get_promotion_by_id(promotion_id)
            if not current_promotion:
                return RedirectResponse(url="/", status_code=303)
            promotion_dict = {
                'id': current_promotion[0],
                'name': current_promotion[1],
                'description': current_promotion[2],
                'course_link': current_promotion[3],  # Исправлено: course_link вместо course_id
                'discounted_price': current_promotion[4],
                'start_date': current_promotion[5],
                'end_date': current_promotion[6],
                'is_period_enabled': current_promotion[8],
                'is_price_enabled': current_promotion[9],
                'image_path': current_promotion[7]
            }
            return templates.TemplateResponse("add_edit_promotion.html", {
                "request": request,
                "promotion": promotion_dict,
                "error": "Файл должен быть изображением"
            })
        
        # Создаем директорию для изображений акций, если она не существует
        os.makedirs("src/web_app/static/img/promotions", exist_ok=True)
        
        # Генерируем уникальное имя файла
        file_extension = os.path.splitext(image.filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = os.path.join("src/web_app/static/img/promotions", unique_filename)
        
        # Сохраняем файл
        with open(file_path, "wb") as f:
            f.write(await image.read())
        
        # Формируем относительный путь для сохранения в базе данных
        image_path = f"src/web_app/static/img/promotions/{unique_filename}"

    try:
        # Обработка значений в зависимости от состояния чекбоксов
        processed_discounted_price = discounted_price if is_price_enabled else None
        processed_start_date = start_date if is_period_enabled else None
        processed_end_date = end_date if is_period_enabled else None

        # Преобразуем булевы значения, проверяя на None
        period_enabled_bool = bool(is_period_enabled) if is_period_enabled is not None else False
        price_enabled_bool = bool(is_price_enabled) if is_price_enabled is not None else False
        
        # Убедимся, что поля даты и цены равны None, если соответствующие чекбоксы не отмечены
        if not period_enabled_bool:
            processed_start_date = None
            processed_end_date = None
        if not price_enabled_bool:
            processed_discounted_price = None

        # Создаем объект PromotionUpdate из полученных параметров формы
        promotion_data = PromotionUpdate(
            name=name,
            description=description,
            course_link=course_link,
            discounted_price=processed_discounted_price,
            start_date=processed_start_date,
            end_date=processed_end_date,
            is_period_enabled=period_enabled_bool,
            is_price_enabled=price_enabled_bool,
            image_path=image_path
        )
        # Используем значения из объекта валидации, если они предоставлены, иначе используем текущие значения
        name = promotion_data.name if promotion_data.name is not None else current_promotion[1]
        description = promotion_data.description if promotion_data.description is not None else current_promotion[2]
        course_link = promotion_data.course_link if promotion_data.course_link is not None else current_promotion[3]
        discounted_price = promotion_data.discounted_price if promotion_data.discounted_price is not None else current_promotion[4]
        start_date = promotion_data.start_date if promotion_data.start_date is not None else current_promotion[5]
        end_date = promotion_data.end_date if promotion_data.end_date is not None else current_promotion[6]
        is_period_enabled = promotion_data.is_period_enabled if promotion_data.is_period_enabled is not None else current_promotion[8]
        is_price_enabled = promotion_data.is_price_enabled if promotion_data.is_price_enabled is not None else current_promotion[9]
        image_path = promotion_data.image_path if promotion_data.image_path is not None else current_promotion[7]
        await db.update_promotion(
            promotion_id,
            name,
            description,
            course_link,
            discounted_price,
            start_date,
            end_date,
            is_period_enabled,
            is_price_enabled,
            image_path
        )
        return RedirectResponse(url="/promotions", status_code=303)
    except ValidationError as e:
        # Обработка ошибок валидации
        errors = e.errors()
        error_messages = []
        for error in errors:
            loc = error["loc"][0] if error["loc"] else "Общая ошибка"
            msg = error["msg"]
            error_messages.append(f"Поле '{loc}': {msg}")
        
        # Подготовка данных для повторного отображения формы
        return templates.TemplateResponse("add_edit_promotion.html", {
            "request": request,
            "promotion": {
                "id": promotion_id,
                "name": name,
                "description": description,
                "course_link": course_link,
                "discounted_price": discounted_price,
                "start_date": start_date,
                "end_date": end_date,
                "image_path": image_path
            },
            "error": "Произошли ошибки валидации: " + "; ".join(error_messages)
        })
    except Exception as e:
        current_promotion = await db.get_promotion_by_id(promotion_id)
        if not current_promotion:
            return RedirectResponse(url="/", status_code=303)
        promotion_dict = {
            'id': current_promotion[0],
            'name': current_promotion[1],
            'description': current_promotion[2],
            'course_link': current_promotion[3],  # Исправлено: course_link вместо course_id
            'discounted_price': current_promotion[4],
            'start_date': current_promotion[5],
            'end_date': current_promotion[6],
            'is_period_enabled': current_promotion[8],
            'is_price_enabled': current_promotion[9],
            'image_path': current_promotion[7]
        }
        return templates.TemplateResponse("add_edit_promotion.html", {
            "request": request,
            "promotion": promotion_dict,
            "error": f"Неизвестная ошибка: {e}"
        })

@router.get("/promotions/{promotion_id}/edit", response_class=HTMLResponse)
async def get_edit_promotion_page(request: Request, promotion_id: int, db: Database = Depends(get_db)):
    promotion = await db.get_promotion_by_id(promotion_id)
    if not promotion:
        return RedirectResponse(url="/", status_code=303)
    
    # Преобразуем данные в словарь для передачи в шаблон
    # Важно: порядок полей в кортеже должен соответствовать порядку в SELECT запросе в database.py
    # Запрос: SELECT id, name, description, course_link, discounted_price, start_date, end_date, image_path, is_period_enabled, is_price_enabled
    promotion_dict = {
        'id': promotion[0],
        'name': promotion[1],
        'description': promotion[2],
        'course_link': promotion[3],  # Изменили на course_link
        'discounted_price': promotion[4],
        'start_date': promotion[5],
        'end_date': promotion[6],
        'image_path': promotion[7],  # Исправлено: теперь это индекс 7
        'is_period_enabled': promotion[8],
        'is_price_enabled': promotion[9]
    }

    # Удалили список всех курсов для выбора, так как теперь используется course_link
    return templates.TemplateResponse("add_edit_promotion.html", {
        "request": request,
        "promotion": promotion_dict,
        "courses": []  # Удалили список курсов
    })

@router.get("/promotions/{promotion_id}", response_class=HTMLResponse)
async def get_promotion_page(request: Request, promotion_id: int, db: Database = Depends(get_db)):
    promotion = await db.get_promotion_by_id(promotion_id)
    if not promotion:
        return RedirectResponse(url="/", status_code=303)
    
    # Преобразуем данные в словарь для передачи в шаблон
    # Важно: порядок полей в кортеже должен соответствовать порядку в SELECT запросе в database.py
    # Запрос: SELECT id, name, description, course_link, discounted_price, start_date, end_date, image_path, is_period_enabled, is_price_enabled
    promotion_dict = {
        'id': promotion[0],
        'name': promotion[1],
        'description': promotion[2],
        'course_link': promotion[3],  # Изменили на course_link
        'discounted_price': promotion[4],
        'start_date': promotion[5],
        'end_date': promotion[6],
        'image_path': promotion[7],  # Исправлено: теперь это индекс 7
        'is_period_enabled': promotion[8],
        'is_price_enabled': promotion[9]
    }
    return templates.TemplateResponse("add_edit_promotion.html", {
        "request": request,
        "promotion": promotion_dict
    })

@router.post("/promotions/{promotion_id}/delete", response_class=HTMLResponse)
async def delete_promotion(promotion_id: int, db: Database = Depends(get_db)):
    # Получаем акцию перед удалением
    promotion = await db.get_promotion_by_id(promotion_id)
    if not promotion:
        return RedirectResponse(url="/", status_code=303)
    
    # Удаляем акцию из базы данных
    await db.delete_promotion(promotion_id)
    
    # Перенаправляем на страницу акций
    return RedirectResponse(url="/promotions", status_code=303)

# API endpoints
@router.get("/api/promotions", response_model=list[PromotionInDB])
async def get_promotions_api(db: Database = Depends(get_db)):
    promotions_list = await db.get_all_promotions()
    # Преобразуем полученные данные в формат Pydantic-моделей
    promotions = [
        PromotionInDB(
            id=promotion[0],
            name=promotion[1],
            description=promotion[2],
            course_link=promotion[3],  # Изменили на course_link
            discounted_price=promotion[4],
            start_date=promotion[5],
            end_date=promotion[6],
            is_period_enabled=promotion[8],
            is_price_enabled=promotion[9],
            image_path=promotion[7]
        )
        for promotion in promotions_list
    ]
    return promotions

@router.get("/api/promotions/{promotion_id}", response_model=PromotionInDB)
async def get_promotion_api(promotion_id: int, db: Database = Depends(get_db)):
    promotion = await db.get_promotion_by_id(promotion_id)
    if not promotion:
        raise HTTPException(status_code=404, detail="Акция не найдена")
    
    # Преобразуем данные в формат Pydantic-модели
    promotion_model = PromotionInDB(
        id=promotion[0],
        name=promotion[1],
        description=promotion[2],
        course_link=promotion[3],  # Изменили на course_link
        discounted_price=promotion[4],
        start_date=promotion[5],
        end_date=promotion[6],
        is_period_enabled=promotion[8],
        is_price_enabled=promotion[9],
        image_path=promotion[7]
    )
    return promotion_model

@router.post("/api/promotions", response_model=PromotionInDB)
async def create_promotion_api(
    name: Annotated[str, Form()],
    course_link: Annotated[str, Form()],
    discounted_price: Annotated[Optional[float], Form()] = None,
    start_date: Annotated[Optional[str], Form()] = None,
    end_date: Annotated[Optional[str], Form()] = None,
    is_period_enabled: Annotated[Optional[bool], Form()] = False,
    is_price_enabled: Annotated[Optional[bool], Form()] = False,
    description: Annotated[Optional[str], Form()] = None,
    image: UploadFile = File(None),
    db: Database = Depends(get_db)
):
    image_path = None
    if image and image.filename:
        if not image.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="Файл должен быть изображением")
        
        os.makedirs("src/web_app/static/img/promotions", exist_ok=True)
        file_extension = os.path.splitext(image.filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = os.path.join("src/web_app/static/img/promotions", unique_filename)
        
        with open(file_path, "wb") as f:
            f.write(await image.read())
        
        image_path = f"src/web_app/static/img/promotions/{unique_filename}"
    
    try:
        # Обработка значений в зависимости от состояния чекбоксов
        processed_discounted_price = discounted_price if is_price_enabled else None
        processed_start_date = start_date if is_period_enabled else None
        processed_end_date = end_date if is_period_enabled else None

        # Преобразуем булевы значения, проверяя на None
        period_enabled_bool = bool(is_period_enabled) if is_period_enabled is not None else False
        price_enabled_bool = bool(is_price_enabled) if is_price_enabled is not None else False
        
        # Убедимся, что поля даты и цены равны None, если соответствующие чекбоксы не отмечены
        if not period_enabled_bool:
            processed_start_date = None
            processed_end_date = None
        if not price_enabled_bool:
            processed_discounted_price = None

        promotion_data = PromotionCreate(
            name=name,
            description=description,
            course_link=course_link,
            discounted_price=processed_discounted_price,
            start_date=processed_start_date,
            end_date=processed_end_date,
            is_period_enabled=period_enabled_bool,
            is_price_enabled=price_enabled_bool,
            image_path=image_path
        )
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=e.errors())

    success = await db.add_promotion(
        promotion_data.name,
        promotion_data.description,
        promotion_data.course_link,
        promotion_data.discounted_price,
        promotion_data.start_date,
        promotion_data.end_date,
        promotion_data.is_period_enabled,
        promotion_data.is_price_enabled,
        promotion_data.image_path
    )
    if not success:
        raise HTTPException(status_code=500, detail="Ошибка при создании акции")
    
    all_promotions = await db.get_all_promotions()
    if not all_promotions:
        raise HTTPException(status_code=500, detail="Ошибка при создании акции")
    
    created_promotion = all_promotions[-1]
    
    promotion_model = PromotionInDB(
        id=created_promotion[0],
        name=created_promotion[1],
        description=created_promotion[2],
        course_link=created_promotion[3],
        discounted_price=created_promotion[4],
        start_date=created_promotion[5],
        end_date=created_promotion[6],
        is_period_enabled=created_promotion[8],
        is_price_enabled=created_promotion[9],
        image_path=created_promotion[7]
    )
    return promotion_model

@router.put("/api/promotions/{promotion_id}", response_model=PromotionInDB)
async def update_promotion_api(
    promotion_id: int,
    name: Annotated[Optional[str], Form()] = None,
    course_link: Annotated[Optional[str], Form()] = None,
    discounted_price: Annotated[Optional[float], Form()] = None,
    start_date: Annotated[Optional[str], Form()] = None,
    end_date: Annotated[Optional[str], Form()] = None,
    is_period_enabled: Annotated[Optional[bool], Form()] = None,
    is_price_enabled: Annotated[Optional[bool], Form()] = None,
    description: Annotated[Optional[str], Form()] = None,
    image: UploadFile = File(None),
    db: Database = Depends(get_db)
):
    # Получаем текущую акцию
    current_promotion = await db.get_promotion_by_id(promotion_id)
    if not current_promotion:
        raise HTTPException(status_code=404, detail="Акция не найдена")
    
    # Обработка загрузки изображения
    current_image_path = current_promotion[7]  # текущий путь к изображению
    image_path = current_image_path  # по умолчанию сохраняем старый путь
    
    if image and image.filename:
        if not image.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="Файл должен быть изображением")
        
        # Удаляем старое изображение, если оно существует и не является стандартным
        if current_image_path and os.path.exists(current_image_path):
            os.remove(current_image_path)
        
        os.makedirs("src/web_app/static/img/promotions", exist_ok=True)
        file_extension = os.path.splitext(image.filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = os.path.join("src/web_app/static/img/promotions", unique_filename)
        
        with open(file_path, "wb") as f:
            f.write(await image.read())
        
        image_path = f"src/web_app/static/img/promotions/{unique_filename}"
    
    # Используем значения из формы, если они предоставлены, иначе используем текущие значения
    name = name if name is not None else current_promotion[1]
    description = description if description is not None else current_promotion[2]
    course_link = course_link if course_link is not None else current_promotion[3]
    discounted_price = discounted_price if discounted_price is not None else current_promotion[4]
    start_date = start_date if start_date is not None else current_promotion[5]
    end_date = end_date if end_date is not None else current_promotion[6]
    # Если параметры не были переданы (остались None), используем текущие значения из базы данных
    is_period_enabled = is_period_enabled if is_period_enabled is not None else current_promotion[8]
    is_price_enabled = is_price_enabled if is_price_enabled is not None else current_promotion[9]
    image_path = image_path if image_path != current_promotion[7] else current_promotion[7]  # Обновляем путь к изображению только если было загружено новое
    
    try:
        # Создаем объект PromotionUpdate для валидации данных
        promotion_data = PromotionUpdate(
            name=name,
            description=description,
            course_link=course_link,
            discounted_price=discounted_price,
            start_date=start_date,
            end_date=end_date,
            is_period_enabled=is_period_enabled,
            is_price_enabled=is_price_enabled,
            image_path=image_path
        )
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=e.errors())
    
    # Обновляем акцию в базу данных
    success = await db.update_promotion(
        promotion_id,
        promotion_data.name,
        promotion_data.description,
        promotion_data.course_link,
        promotion_data.discounted_price,
        promotion_data.start_date,
        promotion_data.end_date,
        promotion_data.is_period_enabled,
        promotion_data.is_price_enabled,
        promotion_data.image_path
    )
    if not success:
        raise HTTPException(status_code=500, detail="Ошибка при обновлении акции")
    
    # Получаем обновленную акцию
    updated_promotion = await db.get_promotion_by_id(promotion_id)
    if not updated_promotion:
        raise HTTPException(status_code=500, detail="Ошибка при обновлении акции")
    
    # Преобразуем данные в формат Pydantic-модели
    promotion_model = PromotionInDB(
        id=updated_promotion[0],
        name=updated_promotion[1],
        description=updated_promotion[2],
        course_link=updated_promotion[3],
        discounted_price=updated_promotion[4],
        start_date=updated_promotion[5],
        end_date=updated_promotion[6],
        is_period_enabled=updated_promotion[8],
        is_price_enabled=updated_promotion[9],
        image_path=updated_promotion[7]
    )
    return promotion_model

@router.delete("/api/promotions/{promotion_id}")
async def delete_promotion_api(promotion_id: int, db: Database = Depends(get_db)):
    # 1. Проверить, существует ли акция
    promotion = await db.get_promotion_by_id(promotion_id)
    if not promotion:
        raise HTTPException(status_code=404, detail="Акция не найдена")

    # 2. Удалить файл изображения, если он есть
    image_path = promotion[7] # Индекс image_path
    if image_path and os.path.exists(image_path):
        try:
            os.remove(image_path)
        except OSError as e:
            # Логировать ошибку, но продолжить, т.к. удаление из БД важнее
            print(f"Error deleting file {image_path}: {e}")

    # 3. Удалить акцию из базы данных
    success = await db.delete_promotion(promotion_id)
    if not success:
        raise HTTPException(status_code=500, detail="Ошибка при удалении акции из базы данных")

    # 4. Вернуть успешный ответ
    return {"message": "Акция успешно удалена"}


# Новый роут для получения списка курсов
@router.get("/api/courses", response_model=list[dict])
async def get_courses_api(db: Database = Depends(get_db)):
    """Получение списка всех курсов для выбора при создании акции"""
    courses_list = await db.get_all_courses()  # Предполагаем, что такая функция есть в Database
    courses = [
        {
            "id": course[0],  # id находится в индексе 0
            "name": course[1],  # name находится в индексе 1
            "price": course[3]  # price находится в индексе 3
        }
        for course in courses_list
    ]
    return courses