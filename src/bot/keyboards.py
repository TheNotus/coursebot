from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters.callback_data import CallbackData
from typing import Optional, Union
from pydantic import field_validator
import logging
from ..data_manager.database import Database

logger = logging.getLogger(__name__)

logging.basicConfig(level=logging.INFO)


# Определяем callback data для навигации
class NavigationCallback(CallbackData, prefix="nav"):
    action: str
    topic_id: Optional[str] = None
    course_id: Optional[int] = None
    page: int = 0
    promotion_id: int = 0


def main_menu_reply_keyboard() -> ReplyKeyboardMarkup:
    """
    Клавиатура с одной кнопкой "Главное меню".
    """
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="📚 Главное меню")
            ]
        ],
        resize_keyboard=True,
        one_time_keyboard=False
    )
    return keyboard


from aiogram.utils.keyboard import InlineKeyboardBuilder

def main_menu_inline_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.button(
        text="📚 Купить товары",
        callback_data=NavigationCallback(action="topics", page=0).pack()
    )
    builder.button(
        text="📋 Каталог",
        callback_data=NavigationCallback(action="catalog").pack()
    )
    builder.button(
        text="🎯 Акции",
        callback_data=NavigationCallback(action="promotions").pack()
    )
    builder.button(
        text="🤝 Отзывы",
        callback_data=NavigationCallback(action="reviews").pack()
    )
    builder.button(
        text="ℹ️ О проекте",
        callback_data=NavigationCallback(action="about_project").pack()
    )
    builder.button(
        text="⚙️ Поддержка",
        callback_data=NavigationCallback(action="support").pack()
    )

    builder.adjust(1, 2, 2)

    return builder.as_markup()



def topics_keyboard(topics: list, page: int = 0) -> InlineKeyboardMarkup:
    """
    Клавиатура со списком тем курсов с пагинацией.
    
    :param topics: Список тем из базы данных (id, name, parent_id, image_path)
    :param page: Номер текущей страницы (по умолчанию 0)
    :return: InlineKeyboardMarkup
    """
    PAGE_SIZE = 5
    start_index = page * PAGE_SIZE
    end_index = start_index + PAGE_SIZE
    current_page_topics = topics[start_index:end_index]

    keyboard = []

    # Добавляем кнопки для каждой темы на текущей странице
    for topic_data in current_page_topics:
        topic_id = topic_data[0]
        topic_name = topic_data[1]
        topic_image_path = topic_data[3]
        
        # Проверяем тип данных для topic_id и используем 0 в качестве значения по умолчанию, если это не целое число
        validated_topic_id = topic_id if isinstance(topic_id, int) else 0
        
        # Определяем действие при нажатии на кнопку темы
        # Если у темы есть изображение, показываем детали темы с изображением
        # Если нет изображения или тема является родительской, показываем курсы
        if topic_image_path:
            callback_data = NavigationCallback(action="show_topic_details", topic_id=str(validated_topic_id), page=page)
        else:
            callback_data = NavigationCallback(action="courses", topic_id=str(validated_topic_id), page=page)
        
        keyboard.append([
            InlineKeyboardButton(
                text=topic_name,
                callback_data=callback_data.pack()
            )
        ])

    # Добавляем кнопки "Назад" и "Вперед" для навигации по страницам
    pagination_row = []
    if page > 0:
        pagination_row.append(
            InlineKeyboardButton(
                text="◀️ Предыдущая",
                callback_data=NavigationCallback(action="prev_page_topics", page=page - 1).pack()
            )
        )
    if end_index < len(topics):
        pagination_row.append(
            InlineKeyboardButton(
                text="➡️ Вперед",
                callback_data=NavigationCallback(action="next_page_topics", page=page + 1).pack()
            )
        )
    if pagination_row:
        keyboard.append(pagination_row)

    # Добавляем кнопку "Назад" в главное меню
    keyboard.append([
        InlineKeyboardButton(
            text="🔙 В главное меню",
            callback_data=NavigationCallback(action="show_main_menu").pack()
        )
    ])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def courses_keyboard(courses: list, topic_id: int = None, page: int = 0) -> InlineKeyboardMarkup:
    """
    Клавиатура со списком курсов для выбранной темы с пагинацией.
    
    :param courses: Список курсов из базы данных (id, name, description, price)
    :param topic_id: ID темы, к которой относятся курсы
    :param page: Номер текущей страницы (по умолчанию 0)
    :return: InlineKeyboardMarkup
    """
    PAGE_SIZE = 5
    start_index = page * PAGE_SIZE
    end_index = start_index + PAGE_SIZE
    current_page_courses = courses[start_index:end_index]

    keyboard = []

    # Добавляем кнопки для каждого курса на текущей странице
    for course_id, course_name, _, _ in current_page_courses:
        keyboard.append([
            InlineKeyboardButton(
                text=course_name,
                callback_data=NavigationCallback(action="course", course_id=course_id, page=page).pack()
            )
        ])

    # Добавляем кнопки "Назад" и "Вперед" для навигации по страницам
    pagination_row = []
    if page > 0:
        pagination_row.append(
            InlineKeyboardButton(
                text="◀️ Предыдущая",
                callback_data=NavigationCallback(action="prev_page_courses", topic_id=str(topic_id) if topic_id is not None else None, page=page - 1).pack()
            )
        )
    if end_index < len(courses):
        pagination_row.append(
            InlineKeyboardButton(
                text="➡️ Вперед",
                callback_data=NavigationCallback(action="next_page_courses", topic_id=str(topic_id) if topic_id is not None else None, page=page + 1).pack()
            )
        )
    if pagination_row:
        keyboard.append(pagination_row)

    # Добавляем кнопку "Назад"
    back_callback_data = NavigationCallback(action="show_main_menu") if topic_id is None else NavigationCallback(action="topics", topic_id=str(topic_id) if topic_id is not None else None, page=page)
    back_text = "🔙 В меню" if topic_id is None else "⬅️ Назад к темам"
    keyboard.append([
        InlineKeyboardButton(
            text=back_text,
            callback_data=back_callback_data.pack()
        )
    ])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


async def course_keyboard(course_id: Optional[int], topic_id: int = 0) -> InlineKeyboardMarkup:
    """
    Клавиатура для конкретного курса с кнопками "Оплатить", "Назад" и "Главное меню".
    
    :param course_id: ID курса (может быть None)
    :param topic_id: ID темы, к которой относится курс (опционально)
    :return: InlineKeyboardMarkup
    """
    inline_keyboard = [
        [
            InlineKeyboardButton(
                text="💳 Оплатить",
                callback_data=NavigationCallback(action="payment", course_id=course_id).pack()
            )
        ],
    ]
    
    # Получаем parent_id для текущего topic_id из базы данных
    db = Database()
    parent_id = await db.get_topic_parent_id(topic_id) if topic_id else None
    
    # Формируем back_callback_data в зависимости от наличия parent_id
    if parent_id and parent_id != 0:
        back_callback_data = NavigationCallback(action="topics", topic_id=str(parent_id))
    else:
        back_callback_data = NavigationCallback(action="show_main_menu")
    
    inline_keyboard.append([
        InlineKeyboardButton(
            text="🔙 В меню",
            callback_data=back_callback_data.pack()
        )
    ])
    
    logger.info(f"course_keyboard: topic_id={topic_id}, course_id={course_id}, parent_id={parent_id}")
    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)


def back_to_main_menu_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура с одной кнопкой "Назад в главное меню".
    """
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="🔙 В главное меню",
                callback_data=NavigationCallback(action="show_main_menu").pack()
            )
        ]
    ])
def get_payment_keyboard(payment_url: str) -> InlineKeyboardMarkup:
    """
    Создает инлайн-клавиатуру с одной кнопкой "Оплатить", которая ведет по переданному URL.

    :param payment_url: URL для оплаты.
    :return: InlineKeyboardMarkup
    """
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="💳 Оплатить",
                url=payment_url
            )
        ]
    ])
    return keyboard


def get_promotion_keyboard(course_link: Optional[str]) -> InlineKeyboardMarkup:
    """
    Создает инлайн-клавиатуру для акции, включая кнопку "Перейти к курсу" (если есть ссылка)
    и кнопку "Назад в главное меню".
    """
    buttons = []
    if course_link and course_link.strip():
        buttons.append([
            InlineKeyboardButton(
                text="➡️ Перейти к курсу",
                url=course_link
            )
        ])
    
    buttons.append([
        InlineKeyboardButton(
            text="🔙 В главное меню",
            callback_data=NavigationCallback(action="show_main_menu").pack()
        )
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def promotions_list_keyboard(promotions: list) -> InlineKeyboardBuilder:
    """
    Создает инлайн-клавиатуру со списком акций.
    """
    builder = InlineKeyboardBuilder()
    
    for promotion in promotions:
        promo_id, name, _, _, _, _, _, _, _, _ = promotion # Разбираем кортеж акции (теперь 10 полей)
        builder.row(
            InlineKeyboardButton(
                text=name,
                callback_data=NavigationCallback(action="show_promotion_details", promotion_id=promo_id).pack()
            )
        )
    
    builder.row(
        InlineKeyboardButton(
            text="🔙 В главное меню",
            callback_data=NavigationCallback(action="show_main_menu").pack()
        )
    )
    
    return builder
