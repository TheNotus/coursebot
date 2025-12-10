import aiosqlite
import logging
from typing import List, Tuple, Optional
from datetime import date, datetime
from ..config import DB_PATH


class Database:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path

    async def init_db(self):
        """Инициализация базы данных и создание таблиц"""
        async with aiosqlite.connect(self.db_path) as db:
            # Создание таблицы users
            await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER NOT NULL UNIQUE,
                username TEXT,
                registration_date DATETIME NOT NULL
            );
            """)

            # Создание таблицы course_topics
            await db.execute("""
            CREATE TABLE IF NOT EXISTS course_topics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                parent_id INTEGER,
                image_path TEXT,
                FOREIGN KEY (parent_id) REFERENCES course_topics (id) ON DELETE CASCADE
            );
            """)

            # Создание таблицы courses
            await db.execute("""
            CREATE TABLE IF NOT EXISTS courses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic_id INTEGER,
                name TEXT NOT NULL,
                description TEXT,
                price REAL NOT NULL CHECK (price >= 0),
                payment_link TEXT,
                image_path TEXT,
                FOREIGN KEY (topic_id) REFERENCES course_topics (id) ON DELETE CASCADE
            );
            """)

            # Создание таблицы purchases
            await db.execute("""
            CREATE TABLE IF NOT EXISTS purchases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                course_id INTEGER NOT NULL,
                purchase_date DATETIME NOT NULL,
                amount REAL NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                FOREIGN KEY (course_id) REFERENCES courses (id) ON DELETE CASCADE
            );
            """)

            # Создание таблицы menu_items
            await db.execute("""
            CREATE TABLE IF NOT EXISTS menu_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT NOT NULL UNIQUE,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                image_path TEXT,
                url_link TEXT DEFAULT ''
            );
            """)
            
            # Создание таблицы promotions
            await db.execute("""
            CREATE TABLE IF NOT EXISTS promotions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                course_link TEXT NOT NULL,
                discounted_price REAL,
                start_date TEXT,
                end_date TEXT,
                image_path TEXT,
                is_period_enabled INTEGER DEFAULT 1,
                is_price_enabled INTEGER DEFAULT 1
            );
            """)
            
            # Создание индексов
            await db.execute("CREATE INDEX IF NOT EXISTS idx_courses_topic_id ON courses (topic_id);")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_purchases_user_id ON purchases (user_id);")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_purchases_course_id ON purchases (course_id);")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_promotions_start_date ON promotions (start_date);")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_promotions_end_date ON promotions (end_date);")
            
            await db.commit()
            logging.info("База данных инициализирована")
            
            # Добавление тестовых данных
            await self._add_sample_data(db)
            
            # Добавление начальных данных для пунктов меню
            await self._add_menu_items_data(db)

    async def _add_sample_data(self, db):
        """Добавление тестовых данных в базу данных"""
        # Проверяем, есть ли уже данные в таблицах
        async with db.execute('SELECT COUNT(*) FROM course_topics') as cursor:
            topics_count = await cursor.fetchone()
        
        if topics_count[0] == 0:
            # Добавляем тестовые темы
            topics_data = [
                ("Программирование", None),
                ("Дизайн", None),
                ("Маркетинг", None),
                ("Бизнес", None)
            ]
            
            await db.executemany('''
                INSERT INTO course_topics (name, image_path) VALUES (?, ?)
            ''', topics_data)
            
            # Добавляем тестовые курсы
            courses_data = [
                # Курсы по программированию (topic_id = 1)
                (1, "Python для начинающих", "Основы программирования на Python", 2990.0),
                (1, "JavaScript продвинутый", "Современные фреймворки и библиотеки", 4990.0),
                (1, "Разработка на Go", "Создание высоконагруженных приложений", 5990.0),
                
                # Курсы по дизайну (topic_id = 2)
                (2, "Основы графического дизайна", "Цвет, композиция, типографика", 390.0),
                (2, "UI/UX дизайн", "Создание интерфейсов и пользовательских путей", 690.0),
                
                # Курсы по маркетингу (topic_id = 3)
                (3, "Контекстная реклама", "Google Ads и Яндекс.Директ", 4490.0),
                (3, "SMM-стратегия", "Продвижение в социальных сетях", 3990.0),
                
                # Курсы по бизнесу (topic_id = 4)
                (4, "Основы предпринимательства", "От идеи до запуска бизнеса", 5490.0),
                (4, "Финансовый менеджмент", "Управление финансами компании", 4990.0)
            ]
            
            await db.executemany('''
                INSERT INTO courses (topic_id, name, description, price) VALUES (?, ?, ?, ?)
            ''', courses_data)
            
            await db.commit()
            logging.info("Тестовые данные добавлены в базу данных")

    async def _add_menu_items_data(self, db):
        """Добавление начальных данных для пунктов меню"""
        # Проверяем, есть ли уже данные в таблице menu_items
        async with db.execute('SELECT COUNT(*) FROM menu_items') as cursor:
            menu_items_count = await cursor.fetchone()
        
        if menu_items_count[0] == 0:
            # Добавляем начальные пункты меню, используя INSERT OR IGNORE
            menu_items_data = [
                ('about_project', 'О проекте', 'Информация о нашем проекте и миссии', None),
                ('promotions', 'Акции', 'Действующие акции и скидки на курсы', None),
                ('reviews', 'Отзывы', 'Отзывы наших учеников', None),
                ('support', 'Поддержка', 'Контакты для связи и поддержки', None),
                ('catalog', 'Каталог', 'https://example.com', None) # Добавляем каталог как отдельный пункт
            ]
            
            await db.executemany('''
                INSERT OR IGNORE INTO menu_items (key, title, content, image_path) VALUES (?, ?, ?, ?)
            ''', menu_items_data)
            
            await db.commit()
            logging.info("Начальные данные для пунктов меню добавлены в базу данных")

    async def add_user(self, user_id: int, username: str, first_name: str, last_name: str):
        """Добавление пользователя в базу данных"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Используем full name, так как в таблице только поле username
                full_name = f"{first_name} {last_name}".strip() if first_name or last_name else None
                registration_date = datetime.now().isoformat()
                
                await db.execute("""
                INSERT OR REPLACE INTO users (telegram_id, username, registration_date)
                VALUES (?, ?, ?)
                """, (user_id, username or full_name, registration_date))
                await db.commit()
                logging.info(f"Пользователь {user_id} добавлен/обновлен в базе данных")
        except Exception as e:
            logging.error(f"Ошибка при добавлении пользователя: {e}")

    async def get_user(self, user_id: int) -> Optional[Tuple]:
        """Получение информации о пользователе"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute("SELECT * FROM users WHERE telegram_id = ?", (user_id,)) as cursor:
                    return await cursor.fetchone()
        except Exception as e:
            logging.error(f"Ошибка при получении пользователя: {e}")
            return None

    async def get_topics(self) -> List[Tuple]:
        """Получение всех тем (адаптируем под существующую структуру)"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute("SELECT id, name, parent_id, image_path FROM course_topics") as cursor:
                    return await cursor.fetchall()
        except Exception as e:
            logging.error(f"Ошибка при получении тем: {e}")
            return []

    async def get_topic_by_id(self, topic_id: int) -> Optional[Tuple]:
        """Получение темы по ID (адаптируем под существующую структуру)"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute("SELECT id, name, parent_id, image_path FROM course_topics WHERE id = ?", (topic_id,)) as cursor:
                    return await cursor.fetchone()
        except Exception as e:
            logging.error(f"Ошибка при получении темы: {e}")
            return None

    async def get_topic_parent_id(self, topic_id: int) -> Optional[int]:
        """Получение parent_id для темы по ID"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute("SELECT parent_id FROM course_topics WHERE id = ?", (topic_id,)) as cursor:
                    result = await cursor.fetchone()
                    return result[0] if result else None
        except Exception as e:
            logging.error(f"Ошибка при получении parent_id темы: {e}")
            return None

    async def add_topic(self, name: str, image_path: str = None) -> bool:
        """Добавление новой темы"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("INSERT INTO course_topics (name, image_path) VALUES (?, ?)", (name, image_path))
                await db.commit()
                logging.info(f"Тема '{name}' добавлена в базу данных")
                return True
        except Exception as e:
            logging.error(f"Ошибка при добавлении темы: {e}")
            return False

    async def update_topic(self, topic_id: int, name: str, image_path: str = None) -> bool:
        """Обновление темы"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("UPDATE course_topics SET name = ?, image_path = ? WHERE id = ?", (name, image_path, topic_id))
                await db.commit()
                logging.info(f"Тема с ID {topic_id} обновлена в базе данных")
                return True
        except Exception as e:
            logging.error(f"Ошибка при обновлении темы: {e}")
            return False

    async def delete_topic(self, topic_id: int) -> bool:
        """Удаление темы"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("DELETE FROM course_topics WHERE id = ?", (topic_id,))
                await db.commit()
                logging.info(f"Тема с ID {topic_id} удалена из базы данных")
                return True
        except Exception as e:
            logging.error(f"Ошибка при удалении темы: {e}")
            return False

    async def get_courses_by_topic(self, topic_id: int) -> List[Tuple]:
        """Получение всех курсов для темы (адаптируем под существующую структуру)"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute("""
                    SELECT id, name, description, price
                    FROM courses
                    WHERE topic_id = ?
                """, (topic_id,)) as cursor:
                    return await cursor.fetchall()
        except Exception as e:
            logging.error(f"Ошибка при получении курсов: {e}")
            return []

    async def get_course_by_id(self, course_id: int) -> Optional[Tuple]:
        """Получение курса по ID (адаптируем под существующую структуру)"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Возвращаем все поля, но обрабатываем только нужные в обработчике
                async with db.execute("""
                    SELECT id, name, description, price, topic_id, payment_link, image_path
                    FROM courses
                    WHERE id = ?
                """, (course_id,)) as cursor:
                    return await cursor.fetchone()
        except Exception as e:
            logging.error(f"Ошибка при получении курса: {e}")
            return None

    async def add_course(self, topic_id: int, name: str, description: str, price: float, payment_link: str = "", image_path: str = "") -> bool:
        """Добавление нового курса"""
        logging.info(f"Вызов функции add_course базы данных с параметрами: topic_id={topic_id}, name={name}, description={description}, price={price}, payment_link={payment_link}, image_path={image_path}")
        
        try:
            async with aiosqlite.connect(self.db_path) as db:
                query = """
                    INSERT INTO courses (topic_id, name, description, price, payment_link, image_path)
                    VALUES (?, ?, ?, ?, ?, ?)
                """
                params = (topic_id, name, description, price, payment_link, image_path)
                
                logging.info(f"Выполнение SQL-запроса: {query} с параметрами: {params}")
                
                await db.execute(query, params)
                logging.info("SQL-запрос успешно выполнен")
                
                await db.commit()
                logging.info("Транзакция успешно зафиксирована в базе данных")
                
                return True
        except Exception as e:
            logging.error(f"Ошибка при добавлении курса: {e}")
            return False

    async def update_course(self, course_id: int, name: str, description: str, price: float, payment_link: str = "", image_path: str = "") -> bool:
        """Обновление курса"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    UPDATE courses
                    SET name = ?, description = ?, price = ?, payment_link = ?, image_path = ?
                    WHERE id = ?
                """, (name, description, price, payment_link, image_path, course_id))
                await db.commit()
                logging.info(f"Курс с ID {course_id} обновлен в базе данных")
                return True
        except Exception as e:
            logging.error(f"Ошибка при обновлении курса: {e}")
            return False

    async def delete_course(self, course_id: int) -> bool:
        """Удаление курса"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("DELETE FROM courses WHERE id = ?", (course_id,))
                await db.commit()
                logging.info(f"Курс с ID {course_id} удален из базы данных")
                return True
        except Exception as e:
            logging.error(f"Ошибка при удалении курса: {e}")
            return False

    async def get_courses_by_topic_id(self, topic_id: int) -> List[Tuple]:
        """Получение всех курсов для темы по ID темы"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute("""
                    SELECT id, name, description, price, image_path
                    FROM courses
                    WHERE topic_id = ?
                """, (topic_id,)) as cursor:
                    return await cursor.fetchall()
        except Exception as e:
            logging.error(f"Ошибка при получении курсов для темы: {e}")
            return []

    async def add_purchase(self, user_id: int, course_id: int, amount: float):
        """Добавление информации о покупке в базу данных"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                purchase_date = datetime.now().isoformat()
                
                await db.execute("""
                INSERT INTO purchases (user_id, course_id, purchase_date, amount)
                VALUES (?, ?, ?, ?)
                """, (user_id, course_id, purchase_date, amount))
                await db.commit()
                logging.info(f"Покупка добавлена в базу данных: user_id={user_id}, course_id={course_id}, amount={amount}")
        except Exception as e:
            logging.error(f"Ошибка при добавлении покупки: {e}")

    async def get_purchase(self, user_id: int, course_id: int) -> Optional[Tuple]:
        """Получение информации о покупке курса пользователем"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute("""
                    SELECT id, user_id, course_id, purchase_date, amount
                    FROM purchases
                    WHERE user_id = ? AND course_id = ?
                """, (user_id, course_id)) as cursor:
                    return await cursor.fetchone()
        except Exception as e:
            logging.error(f"Ошибка при получении покупки: {e}")
            return None

    async def add_menu_item(self, key: str, title: str, content: str, image_path: str = None, url_link: str = None) -> bool:
        """Добавление нового пункта меню"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT INTO menu_items (key, title, content, image_path, url_link)
                    VALUES (?, ?, ?, ?, ?)
                """, (key, title, content, image_path, url_link))
                await db.commit()
                logging.info(f"Пункт меню с ключом '{key}' добавлен в базу данных")
                return True
        except Exception as e:
            logging.error(f"Ошибка при добавлении пункта меню: {e}")
            return False

    async def get_menu_item(self, key: str) -> Optional[Tuple]:
        """Получение пункта меню по ключу"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute("""
                    SELECT id, key, title, content, image_path, url_link
                    FROM menu_items
                    WHERE key = ?
                """, (key,)) as cursor:
                    return await cursor.fetchone()
        except Exception as e:
            logging.error(f"Ошибка при получении пункта меню: {e}")
            return None

    async def get_all_menu_items(self) -> List[Tuple]:
        """Получение всех пунктов меню"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute("""
                    SELECT id, key, title, content, image_path, url_link
                    FROM menu_items
                """) as cursor:
                    return await cursor.fetchall()
        except Exception as e:
            logging.error(f"Ошибка при получении всех пунктов меню: {e}")
            return []

    async def update_menu_item_content(self, key: str, content: str, url_link: str = None) -> bool:
        """Обновление содержимого пункта меню и, опционально, ссылки"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                if url_link is not None:
                    await db.execute("""
                        UPDATE menu_items
                        SET content = ?, url_link = ?
                        WHERE key = ?
                    """, (content, url_link, key))
                else:
                    await db.execute("""
                        UPDATE menu_items
                        SET content = ?
                        WHERE key = ?
                    """, (content, key))
                await db.commit()
                logging.info(f"Содержимое пункта меню с ключом '{key}' обновлено в базе данных")
                return True
        except Exception as e:
            logging.error(f"Ошибка при обновлении содержимого пункта меню: {e}")
            return False

    async def update_menu_item(self, key: str, title: str, content: str, image_path: str = None, url_link: str = None) -> bool:
        """Обновление пункта меню (название, содержимое, изображение и ссылка)"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                print(f"DEBUG: Executing UPDATE query for key='{key}', title='{title}', content='{content[:50]}...', image_path='{image_path}', url_link='{url_link}'")
                if url_link is not None:
                    await db.execute("""
                        UPDATE menu_items
                        SET title = ?, content = ?, image_path = ?, url_link = ?
                        WHERE key = ?
                    """, (title, content, image_path, url_link, key))
                else:
                    await db.execute("""
                        UPDATE menu_items
                        SET title = ?, content = ?, image_path = ?
                        WHERE key = ?
                    """, (title, content, image_path, key))
                await db.commit()
                print(f"DEBUG: Transaction committed for key='{key}'")
                logging.info(f"Пункт меню с ключом '{key}' обновлен в базе данных")
                return True
        except Exception as e:
            logging.error(f"Ошибка при обновлении пункта меню: {e}")
            return False

    async def delete_menu_item(self, key: str) -> bool:
        """Удаление пункта меню"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("DELETE FROM menu_items WHERE key = ?", (key,))
                await db.commit()
                logging.info(f"Пункт меню с ключом '{key}' удален из базы данных")
                return True
        except Exception as e:
            logging.error(f"Ошибка при удалении пункта меню: {e}")
            return False
# Старые методы для работы с catalog_link в таблице settings удалены.
# Теперь catalog - это обычный пункт меню с ключом 'catalog'.

    async def add_promotion(self, name: str, description: str, course_link: str, discounted_price: Optional[float], start_date: Optional[str], end_date: Optional[str], image_path: str = None, is_period_enabled: bool = True, is_price_enabled: bool = True) -> bool:
        """Добавление новой акции"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Преобразуем булевы значения в int, проверяя на None
                period_enabled_int = 1 if is_period_enabled else 0
                price_enabled_int = 1 if is_price_enabled else 0
                
                await db.execute("""
                    INSERT INTO promotions (name, description, course_link, discounted_price, start_date, end_date, image_path, is_period_enabled, is_price_enabled)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    name,
                    description,
                    course_link,
                    discounted_price,
                    start_date,
                    end_date,
                    image_path,
                    period_enabled_int,
                    price_enabled_int
                ))
                await db.commit()
                logging.info(f"Акция '{name}' добавлена в базу данных")
                return True
        except Exception as e:
            logging.error(f"Ошибка при добавлении акции: {e}")
            return False
        
    async def get_promotion_by_id(self, promotion_id: int) -> Optional[Tuple]:
        """Получение акции по ID"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute("""
                    SELECT id, name, description, course_link, discounted_price, start_date, end_date, image_path, is_period_enabled, is_price_enabled
                    FROM promotions
                    WHERE id = ?
                """, (promotion_id,)) as cursor:
                    return await cursor.fetchone()
        except Exception as e:
            logging.error(f"Ошибка при получении акции: {e}")
            return None

    async def get_all_promotions(self) -> List[Tuple]:
        """Получение всех акций"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute("""
                    SELECT id, name, description, course_link, discounted_price, start_date, end_date, image_path, is_period_enabled, is_price_enabled
                    FROM promotions
                """) as cursor:
                    return await cursor.fetchall()
        except Exception as e:
            logging.error(f"Ошибка при получении всех акций: {e}")
            return []

    async def update_promotion(self, promotion_id: int, name: str, description: str, course_link: str, discounted_price: Optional[float], start_date: Optional[str], end_date: Optional[str], is_period_enabled: bool = True, is_price_enabled: bool = True, image_path: str = None) -> bool:
        """Обновление акции"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Преобразуем булевы значения в int, проверяя на None
                period_enabled_int = 1 if is_period_enabled else 0
                price_enabled_int = 1 if is_price_enabled else 0
                
                await db.execute("""
                    UPDATE promotions
                    SET name = ?, description = ?, course_link = ?, discounted_price = ?, start_date = ?, end_date = ?, is_period_enabled = ?, is_price_enabled = ?, image_path = ?
                    WHERE id = ?
                """, (
                    name,
                    description,
                    course_link,
                    discounted_price,
                    start_date,
                    end_date,
                    period_enabled_int,
                    price_enabled_int,
                    image_path,
                    promotion_id
                ))
                await db.commit()
                logging.info(f"Акция с ID {promotion_id} обновлена в базе данных")
                return True
        except Exception as e:
            logging.error(f"Ошибка при обновлении акции: {e}")
            return False
        
    async def delete_promotion(self, promotion_id: int) -> bool:
        """Удаление акции"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("DELETE FROM promotions WHERE id = ?", (promotion_id,))
                await db.commit()
                logging.info(f"Акция с ID {promotion_id} удалена из базы данных")
                return True
        except Exception as e:
            logging.error(f"Ошибка при удалении акции: {e}")
            return False

    async def get_all_active_promotions(self):
        """
        Извлекает все акции из базы данных без фильтрации.
        """
        query = """
            SELECT id, name, description, course_link, discounted_price, start_date, end_date, image_path, is_period_enabled, is_price_enabled
            FROM promotions
        """
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(query)
            promotions = await cursor.fetchall()
            return promotions

    async def get_all_courses(self) -> List[Tuple]:
        """Получение всех курсов"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute("""
                    SELECT id, name, description, price, topic_id, payment_link, image_path
                    FROM courses
                """) as cursor:
                    return await cursor.fetchall()
        except Exception as e:
            logging.error(f"Ошибка при получении всех курсов: {e}")
            return []
