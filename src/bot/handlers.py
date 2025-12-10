
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.filters import CommandStart
from aiogram.fsm.state import State, StatesGroup
import logging
import os

logger = logging.getLogger(__name__)

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

from aiogram import Bot

from .keyboards import (
    main_menu_inline_keyboard,
    topics_keyboard,
    courses_keyboard,
    course_keyboard,
    NavigationCallback,
    main_menu_reply_keyboard,
    back_to_main_menu_keyboard,
    get_payment_keyboard,
    get_promotion_keyboard,
    promotions_list_keyboard
)

from src.config import PAYMENT_PROVIDER_TOKEN

# Создаем роутер
router = Router()

# Определяем FSM для пользователя (если потребуется в будущем)
class UserState(StatesGroup):
    choosing_topic = State()
    choosing_course = State()
    viewing_course = State()

# Вспомогательные функции для безопасного редактирования сообщений
async def safe_edit_text(bot, message, text, **kwargs):
    """
    Безопасное редактирование текста сообщения с проверкой на пустой текст.
    """
    stripped_text = text.strip() if text else ""
    if not stripped_text:
        # Если текст пустой или содержит только пробелы, удаляем сообщение и отправляем новое
        await message.delete()
        await bot.send_message(chat_id=message.chat.id, text="Произошла ошибка: невозможно отредактировать сообщение с пустым текстом.", **kwargs)
        return
    try:
        await message.edit_text(text=stripped_text, **kwargs)
    except Exception:
        # Если не удалось отредактировать текст (например, в случае фото с подписью), пробуем другой подход
        if hasattr(message, 'caption') and message.caption is not None:
            # Если сообщение содержит медиафайл с подписью, пробуем отредактировать подпись
            try:
                await message.edit_caption(caption=stripped_text, **kwargs)
            except Exception:
                # Если и это не получилось, удаляем сообщение и отправляем новое
                await message.delete()
                await bot.send_message(chat_id=message.chat.id, text=stripped_text, **kwargs)
        else:
            # Если обычное текстовое сообщение не отредактировалось, удаляем и отправляем новое
            await message.delete()
            await bot.send_message(chat_id=message.chat.id, text=stripped_text, **kwargs)

async def safe_edit_caption(bot, message, caption, **kwargs):
    """
    Безопасное редактирование подписи к сообщению с проверкой на пустую подпись.
    """
    stripped_caption = caption.strip() if caption else ""
    if not stripped_caption:
        # Если подпись пустая или содержит только пробелы, удаляем сообщение и отправляем новое
        await message.delete()
        await bot.send_message(chat_id=message.chat.id, text="Произошла ошибка: невозможно отредактировать сообщение с пустой подписью.", **kwargs)
        return
    try:
        await message.edit_caption(caption=stripped_caption, **kwargs)
    except Exception as e:
        # Если не удалось отредактировать подпись, пробуем отправить новое сообщение
        await message.delete()
        # Если в kwargs есть photo, отправляем фото с подписью, иначе просто текст
        if 'photo' in kwargs:
            photo = kwargs.pop('photo')
            await bot.send_photo(chat_id=message.chat.id, photo=photo, caption=stripped_caption, **kwargs)
        else:
            await bot.send_message(chat_id=message.chat.id, text=stripped_caption, **kwargs)


async def send_main_menu(chat_id, bot, send_photo=True):
    """
    Вспомогательная функция для отправки главного меню.
    
    :param chat_id: ID чата, в который нужно отправить меню
    :param bot: Объект бота
    :param send_photo: Флаг, указывающий, нужно ли отправлять фото
    """
    main_menu_text = "📚 Главное меню\n\nВыберите действие:"

    if send_photo:
        photo_path = "src/bot/media/start.png"
        if os.path.exists(photo_path):
            await bot.send_photo(
                chat_id=chat_id,
                photo=FSInputFile(photo_path),
                caption=main_menu_text,
                reply_markup=main_menu_inline_keyboard()
            )
        else:
            # Если фото не найдено, отправляем только текст
            await bot.send_message(
                chat_id=chat_id,
                text=main_menu_text,
                reply_markup=main_menu_inline_keyboard()
            )
    else:
        # Отправляем только текст
        await bot.send_message(
            chat_id=chat_id,
            text=main_menu_text,
            reply_markup=main_menu_inline_keyboard()
        )


async def send_main_menu_editable(message, bot, send_photo=False):
    """
    Вспомогательная функция для отправки или редактирования главного меню.
    Если send_photo=True, удаляет старое сообщение и отправляет новое с фото.
    Если send_photo=False, пытается отредактировать текст текущего сообщения.
    
    :param message: Объект сообщения, которое нужно отредактировать или удалить
    :param bot: Объект бота
    :param send_photo: Флаг, указывающий, нужно ли отправлять фото
    """
    main_menu_text = "📚 Главное меню\nВыберите действие:"

    if send_photo:
        # Удаляем старое сообщение и отправляем новое с фото
        await message.delete()
        photo_path = "src/bot/media/start.png"
        if os.path.exists(photo_path):
            await bot.send_photo(
                chat_id=message.chat.id,
                photo=FSInputFile(photo_path),
                caption=main_menu_text,
                reply_markup=main_menu_inline_keyboard()
            )
        else:
            # Если фото не найдено, отправляем только текст
            await bot.send_message(
                chat_id=message.chat.id,
                text=main_menu_text,
                reply_markup=main_menu_inline_keyboard()
            )
    else:
        # Редактируем текст текущего сообщения
        # Проверяем, есть ли текст для редактирования
        stripped_text = main_menu_text.strip() if main_menu_text else ""
        if not stripped_text:
            await message.delete()
            await bot.send_message(
                chat_id=message.chat.id,
                text="Произошла ошибка при отображении главного меню.",
                reply_markup=main_menu_inline_keyboard()
            )
        else:
            await safe_edit_text(
                bot,
                message,
                text=stripped_text,
                reply_markup=main_menu_inline_keyboard()
            )


@router.message(CommandStart())
async def start_handler(message: Message, bot: Bot):
    """
    Обработчик команды /start.
    Приветствует пользователя, регистрирует его в БД (если новый) и отправляет главное меню.
    """
    # Используем объект базы данных, прикрепленный к боту
    db = bot.db
    
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name

    # Регистрируем пользователя в БД
    await db.add_user(user_id, username, first_name, last_name)

    # Отправляем главное меню с фото
    await send_main_menu(message.chat.id, bot, send_photo=True)


@router.message(F.text == "📚Главное меню")
async def show_main_menu_message(message: Message, bot: Bot):
    """
    Обработчик для показа главного меню по нажатию кнопки "Главное меню".
    """
    # Отправляем главное меню без фото
    await send_main_menu(message.chat.id, bot, send_photo=False)


@router.callback_query(NavigationCallback.filter(F.action == "show_main_menu"))
async def show_main_menu_callback(callback: CallbackQuery, callback_data: NavigationCallback, bot: Bot):
    """
    Обработчик для показа главного меню по нажатию кнопки "Назад в главное меню".
    """
    # Проверяем, является ли текущее сообщение сообщением с фото
    # Если да, то удаляем его и отправляем новое с фото
    # Если нет, то редактируем текст
    if callback.message.photo:
        # Это сообщение с фото, удаляем его и отправляем новое с фото
        await callback.message.delete()
        await send_main_menu(callback.message.chat.id, bot, send_photo=True)
    else:
        # Это сообщение с текстом, редактируем его
        await send_main_menu_editable(callback.message, bot, send_photo=False)
    await callback.answer()


@router.callback_query(NavigationCallback.filter(F.action == "main_menu"))
async def main_menu_handler(callback: CallbackQuery, callback_data: NavigationCallback, bot: Bot):
    """
    Обработчик для возврата в главное меню по нажатию кнопки "Назад в главное меню".
    """
    # Проверяем, является ли текущее сообщение сообщением с фото
    # Если да, то удаляем его и отправляем новое с фото
    # Если нет, то редактируем текст
    if callback.message.photo:
        # Это сообщение с фото, удаляем его и отправляем новое с фото
        await callback.message.delete()
        await send_main_menu(callback.message.chat.id, bot, send_photo=True)
    else:
        # Это сообщение с текстом, редактируем его
        await send_main_menu_editable(callback.message, bot, send_photo=False)
    
    await callback.answer()



@router.callback_query(NavigationCallback.filter(F.action == "about_project"))
async def about_project_handler(callback: CallbackQuery, callback_data: NavigationCallback, bot: Bot):
    """
    Обработчик для показа информации о проекте.
    """
    # Используем объект базы данных, прикрепленный к боту
    db = bot.db
    
    # Получаем контент из базы данных
    menu_item = await db.get_menu_item('about_project')
    if menu_item:
        content = menu_item[3] # индекс 3 соответствует полю content
        image_path = menu_item[4] # индекс 4 соответствует полю image_path
    else:
        content = "Информация о проекте временно недоступна."
        image_path = None
    
    # Удаляем старое сообщение
    await callback.message.delete()
    
    # Создаем клавиатуру с кнопкой "Назад в главное меню" с новым callback_data
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    
    keyboard_builder = InlineKeyboardBuilder()
    
    # Добавляем кнопку "Назад в главное меню" с новым callback_data
    keyboard_builder.row(InlineKeyboardButton(
        text="🔙 В главное меню",
        callback_data=NavigationCallback(action="main_menu").pack()
    ))
    
    # Проверяем наличие изображения и отправляем его, если оно есть
    if image_path and os.path.exists(image_path):
        # Отправляем новое сообщение с фото
        await bot.send_photo(
            chat_id=callback.message.chat.id,
            photo=FSInputFile(image_path),
            caption=content,
            reply_markup=keyboard_builder.as_markup(),
            parse_mode="HTML"
        )
    else:
        # Если изображение не указано или не существует, отправляем только текст
        await bot.send_message(
            chat_id=callback.message.chat.id,
            text=content,
            reply_markup=keyboard_builder.as_markup(),
            parse_mode="HTML"
        )
    
    await callback.answer()


@router.callback_query(NavigationCallback.filter(F.action == "promotions"))
async def promotions_handler(callback: CallbackQuery, callback_data: NavigationCallback, bot: Bot):
    """
    Обработчик для показа списка акций.
    """
    db = bot.db
    
    promotions = await db.get_all_active_promotions()
    
    await callback.message.delete()
    
    if not promotions:
        await bot.send_message(
            chat_id=callback.message.chat.id,
            text="К сожалению, в данный момент активных акций нет.",
            reply_markup=back_to_main_menu_keyboard(),
            parse_mode="HTML"
        )
    else:
        # Создаем клавиатуру с акциями
        keyboard = promotions_list_keyboard(promotions)
        
        await bot.send_message(
            chat_id=callback.message.chat.id,
            text="Выберите акцию:",
            reply_markup=keyboard.as_markup(),
            parse_mode="HTML"
        )
            
    await callback.answer()


@router.callback_query(NavigationCallback.filter(F.action == "show_promotion_details"))
async def show_promotion_details_handler(callback: CallbackQuery, callback_data: NavigationCallback, bot: Bot):
    """
    Обработчик для показа деталей выбранной акции.
    """
    db = bot.db
    promotion_id = callback_data.promotion_id
    
    promotion = await db.get_promotion_by_id(promotion_id)
    
    await callback.message.delete()

    if not promotion:
        await bot.send_message(
            chat_id=callback.message.chat.id,
            text="К сожалению, акция не найдена или неактивна.",
            reply_markup=back_to_main_menu_keyboard(),
            parse_mode="HTML"
        )
        await callback.answer()
        return

    promo_id, name, description, course_link, discounted_price, start_date_str, end_date_str, image_path, is_period_enabled, is_price_enabled = promotion
     
    # Форматирование дат с обработкой None значений
    import datetime
    if start_date_str is None:
        start_date = "Дата не указана"
    else:
        start_date = datetime.datetime.strptime(start_date_str, '%Y-%m-%d').strftime('%d.%m.%Y')
    
    if end_date_str is None:
        end_date = "Дата не указана"
    else:
        end_date = datetime.datetime.strptime(end_date_str, '%Y-%m-%d').strftime('%d.%m.%Y')

    promo_text = f"✨ <b>{name}</b>\n\n{description}\n\n"
    
    # Добавляем цену со скидкой, если она включена и не равна None
    if is_price_enabled and discounted_price is not None:
        promo_text += f"💰 Цена по акции: {discounted_price} руб.\n"
    
    # Добавляем период действия, если он включен и даты не равны None
    if is_period_enabled and start_date_str is not None and end_date_str is not None:
        promo_text += f"🗓️ Период действия: с {start_date} по {end_date}"
    
    # Убираем лишний символ новой строки в конце, если он есть
    promo_text = promo_text.rstrip('\n')
    
    reply_markup = get_promotion_keyboard(course_link)
    
    if image_path and os.path.exists(image_path):
        await bot.send_photo(
            chat_id=callback.message.chat.id,
            photo=FSInputFile(image_path),
            caption=promo_text,
            reply_markup=reply_markup,
            parse_mode="HTML"
        )
    else:
        await bot.send_message(
            chat_id=callback.message.chat.id,
            text=promo_text,
            reply_markup=reply_markup,
            parse_mode="HTML"
        )
        
    await callback.answer()


@router.callback_query(NavigationCallback.filter(F.action == "reviews"))
async def reviews_handler(callback: CallbackQuery, callback_data: NavigationCallback, bot: Bot):
    """
    Обработчик для показа информации об отзывах.
    """
    # Используем объект базы данных, прикрепленный к боту
    db = bot.db
    
    # Получаем контент из базы данных
    menu_item = await db.get_menu_item('reviews')
    if menu_item:
        content = menu_item[3] # индекс 3 соответствует полю content
        image_path = menu_item[4] # индекс 4 соответствует полю image_path
        url_link = menu_item[5] # индекс 5 соответствует полю url_link
    else:
        content = "Информация об отзывах временно недоступна."
        image_path = None
        url_link = None
    
    # Удаляем старое сообщение
    await callback.message.delete()
    
    # Создаем клавиатуру с URL-кнопкой "Перейти к отзывам" и кнопкой "Назад в главное меню"
    from aiogram.types import InlineKeyboardButton
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    
    keyboard_builder = InlineKeyboardBuilder()
    
    # Добавляем кнопку с ссылкой на отзывы, если она есть
    if url_link:
        keyboard_builder.row(InlineKeyboardButton(text="Перейти к отзывам", url=url_link))
    
    # Добавляем кнопку "Назад в главное меню"
    keyboard_builder.row(InlineKeyboardButton(
        text="🔙 В главное меню",
        callback_data=NavigationCallback(action="show_main_menu").pack()
    ))
    
    # Проверяем наличие изображения и отправляем его, если оно есть
    if image_path and os.path.exists(image_path):
        # Отправляем новое сообщение с фото
        await bot.send_photo(
            chat_id=callback.message.chat.id,
            photo=FSInputFile(image_path),
            caption=content,
            reply_markup=keyboard_builder.as_markup(),
            parse_mode="HTML"
        )
    else:
        # Если изображение не указано или не существует, отправляем только текст
        await bot.send_message(
            chat_id=callback.message.chat.id,
            text=content,
            reply_markup=keyboard_builder.as_markup(),
            parse_mode="HTML"
        )
    
    await callback.answer()


@router.callback_query(NavigationCallback.filter(F.action == "support"))
async def support_handler(callback: CallbackQuery, callback_data: NavigationCallback, bot: Bot):
    """
    Обработчик для показа информации о поддержке.
    """
    # Используем объект базы данных, прикрепленный к боту
    db = bot.db
    
    # Получаем контент из базы данных
    menu_item = await db.get_menu_item('support')
    if menu_item:
        content = menu_item[3] # индекс 3 соответствует полю content
        image_path = menu_item[4] # индекс 4 соответствует полю image_path
    else:
        content = "Информация о поддержке временно недоступна."
        image_path = None
    
    # Удаляем старое сообщение
    await callback.message.delete()
    
    # Создаем клавиатуру с кнопкой "Назад в главное меню"
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    
    keyboard_builder = InlineKeyboardBuilder()
    
    # Добавляем кнопку "Назад в главное меню"
    keyboard_builder.row(InlineKeyboardButton(
        text="🔙 В главное меню",
        callback_data=NavigationCallback(action="main_menu").pack()
    ))
    
    # Проверяем наличие изображения и отправляем его, если оно есть
    if image_path and os.path.exists(image_path):
        # Отправляем новое сообщение с фото
        await bot.send_photo(
            chat_id=callback.message.chat.id,
            photo=FSInputFile(image_path),
            caption=content,
            reply_markup=keyboard_builder.as_markup(),
            parse_mode="HTML"
        )
    else:
        # Если изображение не указано или не существует, отправляем только текст
        await bot.send_message(
            chat_id=callback.message.chat.id,
            text=content,
            reply_markup=keyboard_builder.as_markup(),
            parse_mode="HTML"
        )
    
    await callback.answer()


@router.callback_query(NavigationCallback.filter(F.action == "catalog"))
async def catalog_handler(callback: CallbackQuery, callback_data: NavigationCallback, bot: Bot):
    """
    Обработчик для показа ссылки на каталог.
    """
    # Используем объект базы данных, прикрепленный к боту
    db = bot.db
    
    # Получаем контент (текст) и ссылку (url_link) из пункта меню 'catalog'
    menu_item = await db.get_menu_item('catalog')
    if menu_item:
        content = menu_item[3] # индекс 3 соответствует полю content (текст)
        url_link = menu_item[5] # индекс 5 соответствует полю url_link
        image_path = menu_item[4] # индекс 4 соответствует полю image_path
    else:
        content = "Ссылка на каталог временно недоступна." # значение по умолчанию
        url_link = "https://example.com" # значение по умолчанию
        image_path = None
    
    # Удаляем старое сообщение
    await callback.message.delete()
    
    # Создаем клавиатуру с URL-кнопкой "Перейти в каталог" и кнопкой "Назад в главное меню"
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="🌐 Перейти в каталог",
                url=url_link # Используем url_link как URL
            )
        ],
        [
            InlineKeyboardButton(
                text="🔙 В главное меню",
                callback_data=NavigationCallback(action="main_menu").pack()
            )
        ]
    ])
    
    # Проверяем наличие изображения и отправляем его, если оно есть
    if image_path and os.path.exists(image_path):
        # Отправляем новое сообщение с фото
        await bot.send_photo(
            chat_id=callback.message.chat.id,
            photo=FSInputFile(image_path),
            caption=content, # Используем content как текст
            reply_markup=keyboard # Используем новую клавиатуру
        )
    else:
        # Если изображение не указано или не существует, отправляем только текст
        await bot.send_message(
            chat_id=callback.message.chat.id,
            text=content, # Используем content как текст
            reply_markup=keyboard # Используем новую клавиатуру
        )
    
    await callback.answer()


@router.callback_query(NavigationCallback.filter(F.action == "topics"))
async def show_topics(callback: CallbackQuery, callback_data: NavigationCallback, bot: Bot):
    """
    Обработчик для показа списка тем курсов.
    """
    # Используем объект базы данных, прикрепленный к боту
    db = bot.db
    
    # Получаем список тем из БД
    topics = await db.get_topics()
    
    page = callback_data.page

    # Определяем путь к изображению
    photo_path = "src/bot/media/topics.png"

    # Удаляем старое сообщение
    await callback.message.delete()

    if not topics:
        await bot.send_message(
            chat_id=callback.message.chat.id,
            text="К сожалению, пока нет доступных тем курсов.",
            reply_markup=main_menu_inline_keyboard()
        )
        await callback.answer()
        return

    # Если изображение существует, отправляем его вместе с подписью и клавиатурой
    if os.path.exists(photo_path):
        await bot.send_photo(
            chat_id=callback.message.chat.id,
            photo=FSInputFile(photo_path),
            caption="Здесь представлен список всех наших когда-либо созданных цифровых продуктов, мы разбили на категории для удобства. Выбирайте что вам по душе:",
            reply_markup=topics_keyboard(topics, page),
            parse_mode="HTML"
        )
    else:
        # Иначе отправляем только текст
        await bot.send_message(
            chat_id=callback.message.chat.id,
            text="Здесь представлен список всех наших когда-либо созданных цифровых продуктов, мы разбили на категории для удобства. Выбирайте что вам по душе:",
            reply_markup=topics_keyboard(topics, page),
            parse_mode="HTML"
        )
    await callback.answer()


@router.callback_query(NavigationCallback.filter(F.action == "show_topic_details"))
async def show_topic_details(callback: CallbackQuery, callback_data: NavigationCallback, bot: Bot):
    """
    Обработчик для показа детальной информации о теме, включая изображение.
    """
    # Используем объект базы данных, прикрепленный к боту
    db = bot.db
    
    topic_id = callback_data.topic_id
    
    # Получаем информацию о теме из БД
    topic = await db.get_topic_by_id(topic_id)
    
    if not topic:
        message_text = "К сожалению, информация о теме недоступна."
        # Проверяем, есть ли текст для редактирования
        stripped_text = message_text.strip() if message_text else ""
        if not stripped_text:
            await callback.message.delete()
            await bot.send_message(
                chat_id=callback.message.chat.id,
                text="Произошла ошибка при отображении информации о теме."
            )
        else:
            await safe_edit_text(bot, callback.message, text=stripped_text)
        await callback.answer()
        return

    # Извлекаем данные темы (id, name, parent_id, image_path)
    topic_id, topic_name, parent_id, image_path = topic

    # Формируем сообщение с информацией о теме
    topic_info = f"📚 <b>{topic_name}</b>\n\nВыберите курс в этой теме:"

    # Проверяем наличие изображения и отправляем его, если оно есть
    if image_path:
        # Используем FSInputFile для отправки изображения
        from aiogram.types import FSInputFile
        import os
        
        # Добавляем логирование для отладки проблемы с изображениями
        logging.info(f"Topic Image Path from DB: {image_path}")
        logging.info(f"Current Working Directory: {os.getcwd()}")
        
        # Формируем путь к файлу изображения
        # Если image_path - это URL-путь (как в веб-приложении), преобразуем его в путь к файлу
        if image_path.startswith('/topics_img/'):
            # Это URL-путь к изображению темы, преобразуем в локальный путь
            # Предполагаем, что изображения тем хранятся в src/web_app/static/img/topics/
            file_path = os.path.join(os.getcwd(), 'src', 'web_app', 'static', 'img', 'topics', os.path.basename(image_path))
        else:
            # Используем путь как есть
            file_path = os.path.join(os.getcwd(), image_path) if not os.path.isabs(image_path) else image_path
        
        # Формируем путь к файлу изображения
        # Если image_path - это URL-путь (как в веб-приложении), преобразуем его в путь к файлу
        if image_path.startswith('/topics_img/'):
            # Это URL-путь к изображению темы, преобразуем в локальный путь
            # Предполагаем, что изображения тем хранятся в src/web_app/static/img/topics/
            file_path = os.path.join(os.getcwd(), 'src', 'web_app', 'static', 'img', 'topics', os.path.basename(image_path))
        else:
            # Используем путь как есть
            file_path = os.path.join(os.getcwd(), image_path) if not os.path.isabs(image_path) else image_path
        
        logging.info(f"Formed File Path: {file_path}")
        logging.info(f"File Exists: {os.path.exists(file_path)}")
        
        if os.path.exists(file_path):
            # Удаляем старое сообщение и отправляем новое с фото
            await callback.message.delete()
            await bot.send_photo(
                chat_id=callback.message.chat.id,
                photo=FSInputFile(file_path),
                caption=topic_info,
                reply_markup=courses_keyboard(await db.get_courses_by_topic(topic_id), topic_id=topic_id, page=0),
                parse_mode="HTML"
            )
        else:
            # Если файл не найден, отправляем только текст
            # Проверяем, есть ли текст для редактирования
            stripped_text = topic_info.strip() if topic_info else ""
            if not stripped_text:
                await callback.message.delete()
                await bot.send_message(
                    chat_id=callback.message.chat.id,
                    text="Произошла ошибка при отображении информации о теме.",
                    reply_markup=courses_keyboard(await db.get_courses_by_topic(topic_id), topic_id=topic_id, page=0),
                    parse_mode="HTML"
                )
            else:
                await safe_edit_text(
                    bot,
                    callback.message,
                    text=stripped_text,
                    reply_markup=courses_keyboard(await db.get_courses_by_topic(topic_id), topic_id=topic_id, page=0),
                    parse_mode="HTML"
                )
    else:
        # Если изображение не указано, отправляем только текст
        # Проверяем, есть ли текст для редактирования
        stripped_text = topic_info.strip() if topic_info else ""
        if not stripped_text:
            await callback.message.delete()
            await bot.send_message(
                chat_id=callback.message.chat.id,
                text="Произошла ошибка при отображении информации о теме.",
                reply_markup=courses_keyboard(await db.get_courses_by_topic(topic_id), topic_id=topic_id, page=0),
                parse_mode="HTML"
            )
        else:
            await safe_edit_text(
                bot,
                callback.message,
                text=stripped_text,
                reply_markup=courses_keyboard(await db.get_courses_by_topic(topic_id), topic_id=topic_id, page=0),
                parse_mode="HTML"
            )

    await callback.answer()


@router.callback_query(NavigationCallback.filter(F.action == "prev_page_topics"))
async def show_prev_page_topics(callback: CallbackQuery, callback_data: NavigationCallback, bot: Bot):
    """
    Обработчик для показа предыдущей страницы списка тем курсов.
    """
    # Используем объект базы данных, прикрепленный к боту
    db = bot.db
    
    # Получаем список тем из БД
    topics = await db.get_topics()
    
    page = callback_data.page

    if not topics:
        message_text = "К сожалению, пока нет доступных тем курсов."
        # Проверяем, есть ли текст для редактирования
        stripped_text = message_text.strip() if message_text else ""
        if not stripped_text:
            await callback.message.delete()
            await bot.send_message(
                chat_id=callback.message.chat.id,
                text="Произошла ошибка при отображении тем."
            )
        else:
            await safe_edit_text(bot, callback.message, text=stripped_text)
        await callback.answer()
        return

    message_text = "Здесь представлен список всех наших когда-либо созданных цифровых продуктов, мы разбили на категории для удобства. Выбирайте что вам по душе:"
    # Проверяем, есть ли текст для редактирования
    stripped_text = message_text.strip() if message_text else ""
    if not stripped_text:
        await callback.message.delete()
        await bot.send_message(
            chat_id=callback.message.chat.id,
            text="Произошла ошибка при отображении тем.",
            reply_markup=topics_keyboard(topics, page)
        )
    else:
        await safe_edit_text(
            bot,
            callback.message,
            text=stripped_text,
            reply_markup=topics_keyboard(topics, page)
        )
    await callback.answer()


@router.callback_query(NavigationCallback.filter(F.action == "next_page_topics"))
async def show_next_page_topics(callback: CallbackQuery, callback_data: NavigationCallback, bot: Bot):
    """
    Обработчик для показа следующей страницы списка тем курсов.
    """
    # Используем объект базы данных, прикрепленный к боту
    db = bot.db
    
    # Получаем список тем из БД
    topics = await db.get_topics()
    
    page = callback_data.page

    if not topics:
        message_text = "К сожалению, пока нет доступных тем курсов."
        # Проверяем, есть ли текст для редактирования
        stripped_text = message_text.strip() if message_text else ""
        if not stripped_text:
            await callback.message.delete()
            await bot.send_message(
                chat_id=callback.message.chat.id,
                text="Произошла ошибка при отображении тем."
            )
        else:
            await safe_edit_text(bot, callback.message, text=stripped_text)
        await callback.answer()
        return

    message_text = "Здесь представлен список всех наших когда-либо созданных цифровых продуктов, мы разбили на категории для удобства. Выбирайте что вам по душе:"
    # Проверяем, есть ли текст для редактирования
    stripped_text = message_text.strip() if message_text else ""
    if not stripped_text:
        await callback.message.delete()
        await bot.send_message(
            chat_id=callback.message.chat.id,
            text="Произошла ошибка при отображении тем.",
            reply_markup=topics_keyboard(topics, page)
        )
    else:
        await safe_edit_text(
            bot,
            callback.message,
            text=stripped_text,
            reply_markup=topics_keyboard(topics, page)
        )
    await callback.answer()


@router.callback_query(NavigationCallback.filter(F.action == "courses"))
async def show_courses(callback: CallbackQuery, callback_data: NavigationCallback, bot: Bot):
    """
    Обработчик для показа списка курсов в выбранной теме.
    """
    # Используем объект базы данных, прикрепленный к боту
    db = bot.db
    
    # Преобразуем topic_id из строки в целое число с обработкой ошибок
    topic_id = None
    logger.info(f"show_courses: callback_data.topic_id={callback_data.topic_id}")
    if callback_data.topic_id is not None:
        try:
            topic_id = int(callback_data.topic_id)
            logger.info(f"show_courses: parsed topic_id={topic_id}")
        except ValueError:
            logger.error(f"show_courses: Failed to parse topic_id='{callback_data.topic_id}'")
            message_text = "Некорректный идентификатор темы."
            # Проверяем, есть ли текст для редактирования
            stripped_text = message_text.strip() if message_text else ""
            if not stripped_text:
                await callback.message.delete()
                await bot.send_message(
                    chat_id=callback.message.chat.id,
                    text="Произошла ошибка при обработке запроса."
                )
            else:
                await safe_edit_text(bot, callback.message, text=stripped_text)
            await callback.answer()
            return

    page = callback_data.page

    if topic_id is None:
        message_text = "Не указана тема для отображения курсов."
        # Проверяем, есть ли текст для редактирования
        stripped_text = message_text.strip() if message_text else ""
        if not stripped_text:
            await callback.message.delete()
            await bot.send_message(
                chat_id=callback.message.chat.id,
                text="Произошла ошибка при обработке запроса."
            )
        else:
            await safe_edit_text(bot, callback.message, text=stripped_text)
        await callback.answer()
        return
      
    # Получаем список курсов для выбранной темы
    courses = await db.get_courses_by_topic(topic_id)
    logger.info(f"show_courses: courses for topic_id={topic_id}: {len(courses) if courses else 0} courses found")

    if not courses:
        message_text = "К сожалению, в этой теме пока нет курсов."
        # Проверяем, есть ли текст для редактирования
        stripped_text = message_text.strip() if message_text else ""
        if not stripped_text:
            await callback.message.delete()
            await bot.send_message(
                chat_id=callback.message.chat.id,
                text="Произошла ошибка при отображении курсов."
            )
        else:
            await safe_edit_text(bot, callback.message, text=stripped_text)
        await callback.answer()
        return

    # Получаем название темы для отображения
    topic = await db.get_topic_by_id(topic_id)
    topic_name = (topic[1] if topic and topic[1] else "Неизвестная тема").strip()
    if not topic_name:
        topic_name = "Неизвестная тема"

    message_text = f"Товары в теме '{topic_name}':"
    keyboard = courses_keyboard(courses, topic_id=topic_id, page=page)

    # Проверяем, что текст не пустой перед редактированием
    # Проверяем, есть ли текст для редактирования
    stripped_text = message_text.strip() if message_text else ""
    if not stripped_text:
        # Если текст пустой, отправляем новое сообщение вместо редактирования
        await callback.message.delete()
        await bot.send_message(
            chat_id=callback.message.chat.id,
            text="Произошла ошибка при отображении курсов.",
            reply_markup=keyboard
        )
    else:
        await safe_edit_text(
            bot,
            callback.message,
            text=stripped_text,
            reply_markup=keyboard
        )
    await callback.answer()


@router.callback_query(NavigationCallback.filter(F.action == "prev_page_courses"))
async def show_prev_page_courses(callback: CallbackQuery, callback_data: NavigationCallback, bot: Bot):
    """
    Обработчик для показа предыдущей страницы списка курсов.
    """
    # Используем объект базы данных, прикрепленный к боту
    db = bot.db
    
    # Преобразуем topic_id из строки в целое число с обработкой ошибок
    topic_id = None
    if callback_data.topic_id is not None:
        try:
            topic_id = int(callback_data.topic_id)
        except ValueError:
            message_text = "Некорректный идентификатор темы."
            # Проверяем, есть ли текст для редактирования
            stripped_text = message_text.strip() if message_text else ""
            if not stripped_text:
                await callback.message.delete()
                await bot.send_message(
                    chat_id=callback.message.chat.id,
                    text="Произошла ошибка при обработке запроса."
                )
            else:
                await safe_edit_text(bot, callback.message, text=stripped_text)
            await callback.answer()
            return

    page = callback_data.page

    if topic_id is None:
        message_text = "Не указана тема для отображения курсов."
        # Проверяем, есть ли текст для редактирования
        stripped_text = message_text.strip() if message_text else ""
        if not stripped_text:
            await callback.message.delete()
            await bot.send_message(
                chat_id=callback.message.chat.id,
                text="Произошла ошибка при обработке запроса."
            )
        else:
            await safe_edit_text(bot, callback.message, text=stripped_text)
        await callback.answer()
        return
      
    # Получаем список курсов для выбранной темы
    courses = await db.get_courses_by_topic(topic_id)

    if not courses:
        message_text = "К сожалению, в этой теме пока нет курсов."
        # Проверяем, есть ли текст для редактирования
        stripped_text = message_text.strip() if message_text else ""
        if not stripped_text:
            await callback.message.delete()
            await bot.send_message(
                chat_id=callback.message.chat.id,
                text="Произошла ошибка при отображении курсов."
            )
        else:
            await safe_edit_text(bot, callback.message, text=stripped_text)
        await callback.answer()
        return

    # Получаем название темы для отображения
    topic = await db.get_topic_by_id(topic_id)
    topic_name = (topic[1] if topic and topic[1] else "Неизвестная тема").strip()
    if not topic_name:
        topic_name = "Неизвестная тема"

    message_text = f"Товары в теме '{topic_name}':"
    keyboard = courses_keyboard(courses, topic_id=topic_id, page=page)

    # Проверяем, что текст не пустой перед редактированием
    # Проверяем, есть ли текст для редактирования
    stripped_text = message_text.strip() if message_text else ""
    if not stripped_text:
        # Если текст пустой, отправляем новое сообщение вместо редактирования
        await callback.message.delete()
        await bot.send_message(
            chat_id=callback.message.chat.id,
            text="Произошла ошибка при отображении курсов.",
            reply_markup=keyboard
        )
    else:
        await safe_edit_text(
            bot,
            callback.message,
            text=stripped_text,
            reply_markup=keyboard
        )
    await callback.answer()


@router.callback_query(NavigationCallback.filter(F.action == "next_page_courses"))
async def show_next_page_courses(callback: CallbackQuery, callback_data: NavigationCallback, bot: Bot):
    """
    Обработчик для показа следующей страницы списка курсов.
    """
    # Используем объект базы данных, прикрепленный к боту
    db = bot.db
    
    # Преобразуем topic_id из строки в целое число с обработкой ошибок
    topic_id = None
    if callback_data.topic_id is not None:
        try:
            topic_id = int(callback_data.topic_id)
        except ValueError:
            message_text = "Некорректный идентификатор темы."
            # Проверяем, есть ли текст для редактирования
            stripped_text = message_text.strip() if message_text else ""
            if not stripped_text:
                await callback.message.delete()
                await bot.send_message(
                    chat_id=callback.message.chat.id,
                    text="Произошла ошибка при обработке запроса."
                )
            else:
                await safe_edit_text(bot, callback.message, text=stripped_text)
            await callback.answer()
            return

    page = callback_data.page

    if topic_id is None:
        message_text = "Не указана тема для отображения курсов."
        # Проверяем, есть ли текст для редактирования
        stripped_text = message_text.strip() if message_text else ""
        if not stripped_text:
            await callback.message.delete()
            await bot.send_message(
                chat_id=callback.message.chat.id,
                text="Произошла ошибка при обработке запроса."
            )
        else:
            await safe_edit_text(bot, callback.message, text=stripped_text)
        await callback.answer()
        return
      
    # Получаем список курсов для выбранной темы
    courses = await db.get_courses_by_topic(topic_id)

    if not courses:
        message_text = "К сожалению, в этой теме пока нет курсов."
        # Проверяем, есть ли текст для редактирования
        stripped_text = message_text.strip() if message_text else ""
        if not stripped_text:
            await callback.message.delete()
            await bot.send_message(
                chat_id=callback.message.chat.id,
                text="Произошла ошибка при отображении курсов."
            )
        else:
            await safe_edit_text(bot, callback.message, text=stripped_text)
        await callback.answer()
        return

    # Получаем название темы для отображения
    topic = await db.get_topic_by_id(topic_id)
    topic_name = (topic[1] if topic and topic[1] else "Неизвестная тема").strip()
    if not topic_name:
        topic_name = "Неизвестная тема"

    message_text = f"Товары в теме '{topic_name}':"
    keyboard = courses_keyboard(courses, topic_id=topic_id, page=page)
    
    # Проверяем, есть ли текст для редактирования
    stripped_text = message_text.strip() if message_text else ""
    if not stripped_text:
        # Если текст пустой или содержит только пробелы, удаляем сообщение и отправляем новое
        await callback.message.delete()
        await bot.send_message(
            chat_id=callback.message.chat.id,
            text="Произошла ошибка при отображении курсов (пустой текст).",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    else:
        if callback.message.photo:
            await safe_edit_caption(
                bot,
                callback.message,
                caption=stripped_text,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
        else:
            await safe_edit_text(
                bot,
                callback.message,
                text=stripped_text,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
    await callback.answer()


@router.callback_query(NavigationCallback.filter(F.action == "course"))
async def show_course_details(callback: CallbackQuery, callback_data: NavigationCallback, bot: Bot):
    """
    Обработчик для показа детальной информации о курсе.
    """
    # Используем объект базы данных, прикрепленный к боту
    db = bot.db
    
    course_id = callback_data.course_id
    
    # Получаем информацию о курсе из БД
    course = await db.get_course_by_id(course_id)
    
    if not course:
        message_text = "К сожалению, информация о курсе недоступна."
        # Проверяем, есть ли текст для редактирования
        stripped_text = message_text.strip() if message_text else ""
        if not stripped_text:
            await callback.message.delete()
            await bot.send_message(
                chat_id=callback.message.chat.id,
                text="Произошла ошибка при отображении информации о курсе."
            )
        else:
            await safe_edit_text(bot, callback.message, text=stripped_text)
        await callback.answer()
        return

    # Извлекаем данные курса (id, name, description, price, topic_id, payment_link, image_path)
    course_details = await db.get_course_by_id(course_id)
    if not course_details:
        message_text = "К сожалению, информация о курсе недоступна."
        # Проверяем, есть ли текст для редактирования
        stripped_text = message_text.strip() if message_text else ""
        if not stripped_text:
            await callback.message.delete()
            await bot.send_message(
                chat_id=callback.message.chat.id,
                text="Произошла ошибка при отображении информации о курсе."
            )
        else:
            await safe_edit_text(bot, callback.message, text=stripped_text)
        await callback.answer()
        return

    course_id, course_name, description, price, topic_id_str, payment_link, image_path = course_details

    # Преобразуем topic_id из строки в целое число с обработкой ошибок
    topic_id = None
    if topic_id_str is not None:
        try:
            topic_id = int(topic_id_str)
        except ValueError:
            topic_id = 0  # значение по умолчанию в случае ошибки

    # Формируем сообщение с информацией о курсе
    course_info = (
        f"📚 <b>{course_name}</b>\n\n"
        f"{description}\n\n"
        f"<b>Цена:</b> {price} руб."
    )

    # Проверяем наличие payment_link и создаем соответствующую клавиатуру
    if payment_link:
        reply_markup = get_payment_keyboard(payment_link)
    else:
        reply_markup = await course_keyboard(course_id, topic_id)

    # Проверяем наличие изображения и отправляем его, если оно есть
    if image_path:
        # Используем FSInputFile для отправки изображения
        from aiogram.types import FSInputFile
        # Убедимся, что путь к изображению корректен
        import os
        
        # Добавляем логирование для отладки проблемы с изображениями
        logging.info(f"Course Image Path from DB: {image_path}")
        logging.info(f"Current Working Directory: {os.getcwd()}")
        
        # Путь к файлу изображения
        file_path = os.path.join(os.getcwd(), image_path)
        logging.info(f"Formed File Path: {file_path}")
        logging.info(f"File Exists: {os.path.exists(file_path)}")
        
        if os.path.exists(file_path):
            # Отправляем фото с информацией о курсе
            await callback.message.delete()  # Удаляем старое сообщение
            await bot.send_photo(
                chat_id=callback.message.chat.id,
                photo=FSInputFile(file_path),
                caption=course_info,
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
        else:
            # Если файл не найден, отправляем только текст
            # Проверяем, есть ли текст для редактирования
            stripped_text = course_info.strip() if course_info else ""
            if not stripped_text:
                await callback.message.delete()
                await bot.send_message(
                    chat_id=callback.message.chat.id,
                    text="Произошла ошибка при отображении информации о курсе.",
                    reply_markup=reply_markup,
                    parse_mode="HTML"
                )
            else:
                await safe_edit_text(
                    bot,
                    callback.message,
                    text=stripped_text,
                    reply_markup=reply_markup,
                    parse_mode="HTML"
                )
    else:
        # Если изображение не указано, отправляем только текст
        # Проверяем, есть ли текст для редактирования
        stripped_text = course_info.strip() if course_info else ""
        if not stripped_text:
            await callback.message.delete()
            await bot.send_message(
                chat_id=callback.message.chat.id,
                text="Произошла ошибка при отображении информации о курсе.",
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
        else:
            await safe_edit_text(
                bot,
                callback.message,
                text=stripped_text,
                reply_markup=reply_markup,
                parse_mode="HTML"
            )

    await callback.answer()


@router.callback_query(NavigationCallback.filter(F.action == "payment"))
async def handle_payment(callback: CallbackQuery, callback_data: NavigationCallback, bot: Bot):
    """
    Обработчик для кнопки "Оплатить".
    Проверяет, куплен ли курс пользователем. Если куплен, отправляет ссылку на курс.
    Если не куплен, запускает процесс оплаты.
    """
    # Используем объект базы данных, прикрепленный к боту
    db = bot.db
    
    user_id = callback.from_user.id
    course_id = callback_data.course_id
    
    # Получаем информацию о курсе из БД
    course_details = await db.get_course_by_id(course_id)
    
    if not course_details:
        message_text = "К сожалению, информация о курсе недоступна."
        # Проверяем, есть ли текст для редактирования
        stripped_text = message_text.strip() if message_text else ""
        if not stripped_text:
            await callback.message.delete()
            await bot.send_message(
                chat_id=callback.message.chat.id,
                text="Произошла ошибка при отображении информации о курсе."
            )
        else:
            await safe_edit_text(bot, callback.message, text=stripped_text)
        await callback.answer()
        return

    course_id, course_name, description, price, payment_link, topic_id_str, image_path = course_details

    # Проверяем, есть ли валидная ссылка на оплату
    if not payment_link or not isinstance(payment_link, str) or not payment_link.startswith('http'):
        message_text = "К сожалению, ссылка на оплату сейчас недоступна. Пожалуйста, свяжитесь с администратором."
        # Проверяем, есть ли текст для редактирования
        stripped_text = message_text.strip() if message_text else ""
        if not stripped_text:
            await callback.message.delete()
            await bot.send_message(
                chat_id=callback.message.chat.id,
                text="Произошла ошибка при обработке оплаты.",
                reply_markup=back_to_main_menu_keyboard()
            )
        else:
            await safe_edit_text(
                bot,
                callback.message,
                text=stripped_text,
                reply_markup=back_to_main_menu_keyboard()
            )
        await callback.answer()
        return

    # Преобразуем topic_id из строки в целое число с обработкой ошибок
    topic_id = None
    if topic_id_str is not None:
        try:
            topic_id = int(topic_id_str)
        except ValueError:
            topic_id = 0 # значение по умолчанию в случае ошибки

    # Проверяем, куплен ли курс пользователем
    purchase = await db.get_purchase(user_id, course_id)
    
    if purchase:
        # Курс уже куплен, отправляем сообщение об успешной покупке
        # Ссылки course_link и external_link больше не используются
        message_text = f"Спасибо за покупку курса '{course_name}'!\n\nДоступ к курсу открыт."
        # Проверяем, есть ли текст для редактирования
        stripped_text = message_text.strip() if message_text else ""
        if not stripped_text:
            await callback.message.delete()
            await bot.send_message(
                chat_id=callback.message.chat.id,
                text="Произошла ошибка при подтверждении оплаты.",
                reply_markup=back_to_main_menu_keyboard()
            )
        else:
            await safe_edit_text(
                bot,
                callback.message,
                text=stripped_text,
                reply_markup=back_to_main_menu_keyboard()
            )
    else:
        # Курс не куплен, запускаем процесс оплаты
        # Получаем ссылку на оплату из настроек
        if payment_link:
            # Формируем сообщение о покупке
            message_text = f"Курс '{course_name}' доступен для покупки за {price} руб."
            
            # Проверяем наличие изображения и отправляем его, если оно есть
            if image_path:
                # Используем FSInputFile для отправки изображения
                from aiogram.types import FSInputFile
                # Убедимся, что путь к изображению корректен
                import os
                
                # Добавляем логирование для отладки проблемы с изображениями
                logging.info(f"Payment Course Image Path from DB: {image_path}")
                logging.info(f"Current Working Directory: {os.getcwd()}")
                
                # Путь к файлу изображения
                file_path = os.path.join(os.getcwd(), image_path)
                logging.info(f"Formed File Path: {file_path}")
                logging.info(f"File Exists: {os.path.exists(file_path)}")
                
                if os.path.exists(file_path):
                    # Отправляем фото с информацией о курсе и клавиатурой оплаты
                    await callback.message.delete()  # Удаляем старое сообщение
                    await bot.send_photo(
                        chat_id=callback.message.chat.id,
                        photo=FSInputFile(file_path),
                        caption=message_text,
                        reply_markup=get_payment_keyboard(payment_link),
                        parse_mode="HTML"
                    )
                else:
                    # Если файл не найден, отправляем только текст
                    # Проверяем, есть ли текст для редактирования
                    stripped_text = message_text.strip() if message_text else ""
                    if not stripped_text:
                        await callback.message.delete()
                        await bot.send_message(
                            chat_id=callback.message.chat.id,
                            text="Произошла ошибка при отображении информации о курсе.",
                            reply_markup=get_payment_keyboard(payment_link)
                        )
                    else:
                        await safe_edit_text(
                            bot,
                            callback.message,
                            text=stripped_text,
                            reply_markup=get_payment_keyboard(payment_link)
                        )
            else:
                # Если изображение не указано, отправляем только текст
                # Проверяем, есть ли текст для редактирования
                stripped_text = message_text.strip() if message_text else ""
                if not stripped_text:
                    await callback.message.delete()
                    await bot.send_message(
                        chat_id=callback.message.chat.id,
                        text="Произошла ошибка при отображении информации о курсе.",
                        reply_markup=get_payment_keyboard(payment_link)
                    )
                else:
                    await safe_edit_text(
                        bot,
                        callback.message,
                        text=stripped_text,
                        reply_markup=get_payment_keyboard(payment_link)
                    )
        else:
            # Ссылка на оплату не найдена в настройках
            message_text = (
                f"Курс '{course_name}' доступен для покупки за {price} руб., "
                f"но ссылка на оплату временно недоступна. Обратитесь к администратору."
            )
            # Проверяем, есть ли текст для редактирования
            stripped_text = message_text.strip() if message_text else ""
            if not stripped_text:
                await callback.message.delete()
                await bot.send_message(
                    chat_id=callback.message.chat.id,
                    text="Произошла ошибка при обработке оплаты.",
                    reply_markup=back_to_main_menu_keyboard()
                )
            else:
                await safe_edit_text(
                    bot,
                    callback.message,
                    text=stripped_text,
                    reply_markup=back_to_main_menu_keyboard()
                )
    
    await callback.answer()
