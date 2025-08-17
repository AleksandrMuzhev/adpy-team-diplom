import logging
import os

import vk_api
from dotenv import load_dotenv
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from vk_api.utils import get_random_id

from src.db import queries
from src.db.db_session import Session
from src.db.queries import (
    add_favorite, remove_favorite, get_favorites_for_user
)
from src.db.vkinder_models import Favorites
from src.vk_api_handler import VKAPIHandler

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class VKinderBot:
    def __init__(self, group_token: str, group_id: int):
        self.vk_session = vk_api.VkApi(token=group_token)
        self.api = self.vk_session.get_api()
        self.longpoll = VkBotLongPoll(self.vk_session, group_id=group_id)
        self.vk_handler = VKAPIHandler(group_token, group_id)
        self.current_candidates = {}  # {user_id: [candidates]}
        self.current_index = {}  # {user_id: current_index}

    def send_message(self, user_id: int, message: str, keyboard=None, attachments=None):
        """
        Отправляет сообщение пользователю через VK API.

        Args:
            user_id (int): ID пользователя-получателя
            message (str): Текст сообщения
            keyboard (VkKeyboard, optional): Объект клавиатуры для прикрепления
            attachments (str, optional): Вложения к сообщению (фото, документы)

        Note:
            Логирует ошибки при отправке сообщения
        """
        params = {
            'user_id': user_id,
            'message': message,
            'random_id': get_random_id(),
        }
        if keyboard:
            params['keyboard'] = keyboard.get_keyboard()
        if attachments:
            params['attachment'] = attachments

        try:
            self.api.messages.send(**params)
        except Exception as e:
            logger.error(f"Ошибка отправки сообщения: {e}")

    def create_main_keyboard(self):
        """
        Создает основную клавиатуру бота с главными командами.

        Returns:
            VkKeyboard: Объект клавиатуры с кнопками:
                - Найти пару
                - Избранное
                - Помощь
        """
        keyboard = VkKeyboard(one_time=False)
        keyboard.add_button('Найти пару', VkKeyboardColor.PRIMARY)
        keyboard.add_button('Избранное', VkKeyboardColor.SECONDARY)
        keyboard.add_line()
        keyboard.add_button('Помощь', VkKeyboardColor.POSITIVE)
        return keyboard

    def create_candidate_keyboard(self, candidate_id: int):
        """
        Создает интерактивную клавиатуру для взаимодействия с кандидатом.

        Args:
            candidate_id (int): ID текущего кандидата (для отладки)

        Returns:
            VkKeyboard: Объект клавиатуры с кнопками:
                - В избранное
                - В черный список
                - Лайк фото
                - Следующий кандидат
        """
        keyboard = VkKeyboard(inline=True)

        # Первая строка
        keyboard.add_button('❤️ В избранное', color=VkKeyboardColor.POSITIVE)
        keyboard.add_button('👎 Чёрный список', color=VkKeyboardColor.NEGATIVE)

        # Вторая строка
        keyboard.add_line()
        keyboard.add_button('👍 Лайк фото', color=VkKeyboardColor.PRIMARY)
        keyboard.add_button('➡️ Следующий', color=VkKeyboardColor.SECONDARY)

        # Третья строка (только для теста)
        if os.getenv("DEBUG") == "True":
            keyboard.add_line()
            keyboard.add_button(f'ID: {candidate_id}', color=VkKeyboardColor.SECONDARY)

        return keyboard

    def handle_start(self, user_id: int):
        """
        Обрабатывает команду /start, отправляя приветственное сообщение.

        Args:
            user_id (int): ID пользователя, запустившего бота
        """
        message = (
            "Привет! Я бот VKinder и помогу тебе найти пару.\n"
            "Используй кнопки ниже для управления:\n"
            "• Найти пару - начать поиск\n"
            "• Избранное - просмотреть сохранённые анкеты\n"
            "• Помощь - показать это сообщение"
        )
        self.send_message(user_id, message, self.create_main_keyboard())

    def handle_help(self, user_id: int):
        """
        Обрабатывает запрос помощи, перенаправляя на handle_start.

        Args:
            user_id (int): ID пользователя, запросившего помощь
        """
        self.handle_start(user_id)

    def handle_find_pair(self, user_id: int):
        """
        Обрабатывает команду поиска партнера. Основной рабочий поток:
        1. Получает данные пользователя
        2. Ищет кандидатов через VK API
        3. Фильтрует по черному списку
        4. Сохраняет в текущую сессию
        5. Показывает первого кандидата

        Args:
            user_id (int): VK ID пользователя, инициировавшего поиск

        Side effects:
            - Обновляет self.current_candidates
            - Обновляет self.current_index
            - Отправляет сообщения пользователю
        """
        try:
            # Получаем черный список из БД
            with Session() as session:
                blacklist = queries.get_blacklist(session, user_id)  # Используем queries

            vk_user = self.vk_handler.get_user_info(user_id)
            if not vk_user:
                self.send_message(user_id, "Не удалось получить ваши данные")
                return

            candidates = self.vk_handler.find_potential_matches(vk_user)

            # Фильтруем кандидатов по черному списку
            candidates = [c for c in candidates if c.id not in blacklist]

            if not candidates:
                self.send_message(user_id, "Не удалось найти подходящих кандидатов")
                return

            self.current_candidates[user_id] = candidates
            self.current_index[user_id] = 0
            self.show_current_candidate(user_id)

        except Exception as e:
            logger.error(f"Search error: {e}")
            self.send_message(user_id, "Произошла ошибка при поиске")

    def show_current_candidate(self, user_id: int):
        """
        Отображает текущего кандидата с фото и интерактивной клавиатурой.

        Args:
            user_id (int): VK ID пользователя

        Workflow:
            1. Проверяет наличие кандидатов
            2. Получает топ-3 фото
            3. Формирует сообщение с:
               - Основной информацией
               - Процентом совпадения
               - Ссылкой на профиль
            4. Отправляет сообщение с клавиатурой

        Note:
            Использует методы:
            - get_top_photos
            - prepare_attachments
            - calculate_match_score
        """
        try:
            # Проверка наличия кандидатов
            if user_id not in self.current_candidates or user_id not in self.current_index:
                self.send_message(user_id, "Начните поиск заново.", self.create_main_keyboard())
                return

            index = self.current_index[user_id]
            candidates = self.current_candidates[user_id]

            if index >= len(candidates):
                self.send_message(user_id, "Больше нет кандидатов. Начните новый поиск.", self.create_main_keyboard())
                return

            candidate = candidates[index]

            # Получаем фото (аватарки + фото с отметками)
            photos = self.vk_handler.get_top_photos(candidate.id)
            attachments = self.vk_handler.prepare_attachments(photos) if photos else None

            # Сохраняем кандидата в БД
            db_candidate = {
                "budding_id": candidate.id,
                "first_name": candidate.first_name,
                "last_name": candidate.last_name,
                "gender": "male" if candidate.sex == 2 else "female",
                "age": candidate.age,
                "url_profile": candidate.profile_url,
                "city": candidate.city
            }

            with Session() as session:
                # Проверяем чёрный список
                blacklist = queries.get_blacklist(session, user_id)
                if candidate.id in blacklist:
                    self.current_index[user_id] += 1
                    return self.show_current_candidate(user_id)

                # Сохраняем кандидата
                budding = queries.add_budding(session, db_candidate)

                # Сохраняем фото
                for i, photo in enumerate(photos):
                    queries.add_budding_photo(session, {
                        "budding_id": budding.budding_id,
                        "photo_vk": photo.attachment_str,
                        "likes_count": photo.likes,
                        "rank_photo": i + 1
                    })

            # Вычисляем совпадение по группам
            common_groups = self.get_common_groups(user_id, candidate.id)

            # Формируем сообщение с рейтингом совпадения
            match_score = self.calculate_match_score(user_id, candidate.id, common_groups)
            message = (
                f"👤 {candidate.first_name} {candidate.last_name}\n"
                f"🎂 Возраст: {candidate.age or 'не указан'}\n"
                f"🏙️ Город: {candidate.city or 'не указан'}\n"
                f"👥 Общие группы: {common_groups}\n"
                f"🔗 Профиль: {candidate.profile_url}\n"
                f"💘 Совпадение: {match_score:.0%}"
            )

            # Отправляем сообщение с клавиатурой
            self.send_message(
                user_id,
                message,
                keyboard=self.create_candidate_keyboard(candidate.id),
                attachments=attachments
            )

        except Exception as e:
            logger.error(f"Show candidate error: {e}")
            self.send_message(user_id, "Ошибка при загрузке анкеты", self.create_main_keyboard())

    def get_common_groups(self, user_id: int, candidate_id: int) -> int:
        """
        Возвращает количество общих групп между пользователем и кандидатом.

        Args:
            user_id (int): ID пользователя
            candidate_id (int): ID кандидата

        Returns:
            int: Количество общих групп (0 в случае ошибки)
        """
        try:
            # Получаем группы пользователя
            user_groups = set(self.vk_handler.api.groups.get(user_id=user_id)['items'])
            # Получаем группы кандидата
            candidate_groups = set(self.vk_handler.api.groups.get(user_id=candidate_id)['items'])
            # Возвращаем количество общих групп
            return len(user_groups & candidate_groups)
        except Exception as e:
            logger.error(f"Error getting common groups: {e}")
            return 0

    def calculate_match_score(self, user_id: int, candidate_id: int, common_groups: int) -> float:
        """
        Вычисляет процент совпадения между пользователем и кандидатом.

        Args:
            user_id (int): ID пользователя
            candidate_id (int): ID кандидата
            common_groups (int): Количество общих групп

        Returns:
            float: Процент совпадения (0.0-1.0)
        """
        with Session() as session:
            user = queries.get_user_by_id(session, user_id)
            candidate = queries.get_budding_by_id(session, candidate_id)

            if not user or not candidate:
                return 0.0

            score = 0.0
            weights = {'age': 0.4, 'city': 0.3, 'groups': 0.3}

            # Совпадение по возрасту
            if user.age and candidate.age:
                age_diff = min(abs(user.age - candidate.age), 10)
                score += weights['age'] * (1 - age_diff / 10)

            # Совпадение по городу
            if user.city and candidate.city and user.city.lower() == candidate.city.lower():
                score += weights['city']

            # Общие группы
            score += weights['groups'] * min(common_groups / 10, 1.0)  # Нормализуем до 1.0

            return min(score, 1.0)  # Ограничиваем 100%

    def handle_next_candidate(self, user_id: int):
        """
        Переключает на следующего кандидата в списке.

        Args:
            user_id (int): ID пользователя

        Note:
            Обновляет current_index и показывает нового кандидата
        """
        if user_id in self.current_index:
            self.current_index[user_id] += 1
            self.show_current_candidate(user_id)

    def handle_add_to_favorites(self, user_id: int):
        """
        Добавляет текущего кандидата в список избранного пользователя.

        Args:
            user_id (int): VK ID пользователя, выполняющего действие

        Workflow:
            1. Проверяет наличие активного кандидата
            2. Проверяет, не добавлен ли кандидат уже в избранное
            3. Создает запись в таблице Favorites
            4. Отправляет подтверждение пользователю

        Raises:
            Exception: Логирует ошибки при работе с БД

        Side Effects:
            - Добавляет запись в таблицу Favorites
            - Отправляет сообщения пользователю
            - Логирует ошибки в журнал

        Example:
            >>> bot.handle_add_to_favorites(123456)
            [Сообщение пользователю: "Добавлено в избранное: Иван Петров"]
        """
        try:
            with Session() as session:
                if user_id not in self.current_candidates or user_id not in self.current_index:
                    self.send_message(user_id, "Сначала найдите кандидатов.")
                    return

                index = self.current_index[user_id]
                candidate = self.current_candidates[user_id][index]

                # Проверяем, есть ли уже в избранном
                existing = session.query(Favorites).filter(
                    Favorites.user_id == user_id,
                    Favorites.budding_id == candidate.id
                ).first()

                if existing:
                    self.send_message(user_id, "Этот кандидат уже в избранном!")
                    return

                # Добавляем в избранное
                fav = add_favorite(session, user_id, candidate.id)
                session.commit()

                self.send_message(
                    user_id,
                    f"Добавлено в избранное: {candidate.first_name} {candidate.last_name}",
                    self.create_candidate_keyboard(candidate.id)
                )

        except Exception as e:
            logger.error(f"Favorite add error: {e}")
            self.send_message(user_id, "Ошибка при добавлении в избранное.")

    def handle_show_favorites(self, user_id: int):
        """
        Показывает список избранных кандидатов пользователя.

        Args:
            user_id (int): ID пользователя

        Workflow:
            1. Получает список избранного из БД
            2. Форматирует сообщение с данными кандидатов
            3. Отправляет сообщение с клавиатурой управления

        Note:
            Если избранных нет, отправляет соответствующее сообщение
        """
        with Session() as session:
            favorites = get_favorites_for_user(session, user_id)

        if not favorites:
            self.send_message(user_id, "У вас пока нет избранных кандидатов.", self.create_main_keyboard())
            return

        message = "Ваши избранные кандидаты:\n\n"
        for fav in favorites:
            message += (
                f"{fav.first_name} {fav.last_name}\n"
                f"Возраст: {fav.age}\n"
                f"Город: {fav.city}\n"
                f"Ссылка: {fav.url_profile}\n\n"
            )

        self.send_message(user_id, message, self.create_favorites_keyboard())

    def handle_remove_from_favorites(self, user_id: int):
        """
        Обрабатывает удаление кандидата из избранного.

        В текущей реализации удаляет последнего просмотренного кандидата.

        Args:
            user_id (int): ID пользователя, инициировавшего удаление

        Workflow:
            1. Проверяет наличие текущего кандидата
            2. Удаляет связь пользователь-кандидат из таблицы Favorites
            3. Отправляет уведомление о результате

        Note:
            В будущих версиях планируется добавить:
            - Выбор конкретного кандидата для удаления
            - Подтверждение перед удалением
        """
        if user_id in self.current_candidates and user_id in self.current_index:
            index = self.current_index[user_id]
            candidate = self.current_candidates[user_id][index]

            with Session() as session:
                removed = remove_favorite(session, user_id, candidate.id)

            if removed:
                self.send_message(user_id, "Удалено из избранного.", self.create_main_keyboard())
            else:
                self.send_message(user_id, "Не удалось удалить из избранного.", self.create_main_keyboard())

    def run(self):
        """
        Основной цикл работы бота.

        Запускает бесконечный цикл прослушивания событий от VK LongPoll API.

        Workflow:
            1. Инициализирует прослушивание событий
            2. Для каждого нового сообщения (MESSAGE_NEW):
               - Перенаправляет на handle_message
            3. Логирует запуск бота

        Note:
            Работает до принудительной остановки.
            Обрабатывает только события типа MESSAGE_NEW.
        """
        logger.info("Бот запущен")
        for event in self.longpoll.listen():
            if event.type == VkBotEventType.MESSAGE_NEW:
                self.handle_message(event)

    def create_favorites_keyboard(self):
        """
        Создает клавиатуру для управления избранными кандидатами.

        Returns:
            VkKeyboard: Клавиатура с кнопками:
                - Удалить из избранного
                - Назад (в главное меню)
        """
        keyboard = VkKeyboard(one_time=False)
        keyboard.add_button('Удалить из избранного', VkKeyboardColor.NEGATIVE)
        keyboard.add_button('Назад', VkKeyboardColor.SECONDARY)
        return keyboard

    def handle_message(self, event):
        """
        Основной обработчик входящих сообщений от пользователей.

        Определяет тип команды и перенаправляет на соответствующий обработчик.
        Поддерживает как текстовые команды, так команды от интерактивных кнопок.

        Args:
            event (VkBotMessageEvent): Объект события входящего сообщения

        Обрабатываемые команды:
            - Стартовые команды: ['привет', 'начать', 'старт']
            - Помощь: ['помощь', 'help']
            - Поиск пар: ['найти пару', 'поиск']
            - Избранное: ['избранное', 'favorites']
            - Действия с кандидатами (из интерактивных кнопок):
                ❤️ В избранное
                👎 Чёрный список
                👍 Лайк фото
                ➡️ Следующий
            - Управление избранным: 'удалить из избранного'
            - Навигация: ['назад', 'отмена']

        Note:
            Для нераспознанных команд отправляет подсказку о помощи.
            Все команды обрабатываются в нижнем регистре.
        """
        user_id = event.obj.message['from_id']
        text = event.obj.message['text'].lower()

        if text in ['привет', 'начать', 'старт']:
            self.handle_start(user_id)
        elif text in ['помощь', 'help']:
            self.handle_help(user_id)
        elif text in ['найти пару', 'поиск']:
            self.handle_find_pair(user_id)
        elif text in ['избранное', 'favorites']:
            self.handle_show_favorites(user_id)
        elif text == '❤️ в избранное':
            self.handle_add_to_favorites(user_id)
        elif text == '👎 чёрный список':
            self.handle_blacklist(user_id)
        elif text == '👍 лайк фото':
            self.handle_like_photo(user_id)
        elif text in ['➡️ следующий', 'дальше']:
            self.handle_next_candidate(user_id)
        elif text == 'удалить из избранного':
            self.handle_remove_from_favorites(user_id)
        elif text in ['назад', 'отмена']:
            self.handle_start(user_id)
        else:
            self.send_message(
                user_id,
                "Я не понимаю вашу команду. Используйте кнопки или введите 'помощь'.",
                self.create_main_keyboard()
            )

    def handle_blacklist(self, user_id: int):
        """
        Добавляет текущего кандидата в черный список пользователя.

        Warning:
            После добавления кандидат больше не будет появляться в поиске,
            но останется в БД для статистики.

        Side effects:
            - Обновляет таблицу Blacklist
            - Отправляет уведомление пользователю
        """
        if user_id not in self.current_candidates:
            return

        candidate = self.current_candidates[user_id][self.current_index[user_id]]
        with Session() as session:
            queries.add_to_blacklist(session, user_id, candidate.id)
        self.send_message(user_id, f"Пользователь {candidate.first_name} добавлен в чёрный список")

    def handle_like_photo(self, user_id: int):
        """
        Обрабатывает запрос на лайк фото текущего кандидата.

        Args:
            user_id (int): ID пользователя, отправившего запрос

        Workflow:
            1. Проверяет наличие текущего кандидата
            2. Получает топ фото кандидата
            3. Ставит лайк первому фото
            4. Отправляет уведомление о результате

        Note:
            В случае ошибки отправляет сообщение об ошибке
        """
        if user_id not in self.current_candidates or user_id not in self.current_index:
            self.send_message(user_id, "Сначала найдите кандидатов.")
            return

        index = self.current_index[user_id]
        candidate = self.current_candidates[user_id][index]

        # Получаем фото текущего кандидата
        with Session() as session:
            photos = queries.get_top_photos_for_budding(session, candidate.id)
            if not photos:
                self.send_message(user_id, "Нет доступных фото для лайка.")
                return

            # Лайкаем первое фото (можно добавить выбор)
            photo = photos[0]
            if self.vk_handler.like_photo(photo.photo_id, photo.budding_id):
                self.send_message(user_id, "Лайк поставлен!", self.create_candidate_keyboard(candidate.id))
            else:
                self.send_message(user_id, "Не удалось поставить лайк.")
