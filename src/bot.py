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
from src.vk_api_handler import VKAPIHandler, safe_decode, safe_str

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VKinderBot:
    def __init__(self, vk_handler: VKAPIHandler, group_id: int):
        self.vk_handler = vk_handler
        self.group_id = group_id
        self.vk_session = vk_handler.vk_session
        self.api = vk_handler.api
        self.longpoll = vk_handler.longpoll
        self.current_candidates = {}  # {user_id: [candidates]}
        self.current_index = {}  # {user_id: current_index}

    def run(self):
        logger.info("Бот запущен")
        try:
            for event in self.longpoll.listen():
                if event.type == VkBotEventType.MESSAGE_NEW:
                    self.handle_message(event)
        except Exception as e:
            logger.error(f"Ошибка в цикле run: {safe_str(e)}")

    def send_message(self, user_id: int, message: str, keyboard=None, attachments=None):
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
            logger.error(f"Ошибка отправки сообщения: {safe_str(e)}")

    def create_main_keyboard(self):
        try:
            keyboard = VkKeyboard(one_time=False)
            keyboard.add_button('Найти пару', VkKeyboardColor.PRIMARY)
            keyboard.add_button('Избранное', VkKeyboardColor.SECONDARY)
            keyboard.add_line()
            keyboard.add_button('Помощь', VkKeyboardColor.POSITIVE)
            return keyboard
        except Exception as e:
            logger.error(f"Ошибка создания основной клавиатуры: {safe_str(e)}")

    def create_candidate_keyboard(self, candidate_id: int):
        try:
            keyboard = VkKeyboard(inline=True)
            keyboard.add_button('❤️ В избранное', color=VkKeyboardColor.POSITIVE)
            keyboard.add_button('👎 Чёрный список', color=VkKeyboardColor.NEGATIVE)
            keyboard.add_line()
            keyboard.add_button('👍 Лайк фото', color=VkKeyboardColor.PRIMARY)
            keyboard.add_button('👎 Убрать лайк', color=VkKeyboardColor.SECONDARY)
            keyboard.add_button('➡️ Следующий', color=VkKeyboardColor.SECONDARY)
            if os.getenv("DEBUG") == "True":
                keyboard.add_line()
                keyboard.add_button(f'ID: {candidate_id}', color=VkKeyboardColor.SECONDARY)
            return keyboard
        except Exception as e:
            logger.error(f"Ошибка создания клавиатуры кандидата: {safe_str(e)}")

    def handle_start(self, user_id: int):
        try:
            message = (
                "Привет! Я бот VKinder и помогу тебе найти пару.\n"
                "Используй кнопки ниже для управления:\n"
                "• Найти пару - начать поиск\n"
                "• Избранное - просмотреть сохранённые анкеты\n"
                "• Помощь - показать это сообщение"
            )
            self.send_message(user_id, message, self.create_main_keyboard())
        except Exception as e:
            logger.error(f"Ошибка в handle_start: {safe_str(e)}")

    def handle_help(self, user_id: int):
        try:
            self.handle_start(user_id)
        except Exception as e:
            logger.error(f"Ошибка в handle_help: {safe_str(e)}")

    def handle_find_pair(self, user_id: int):
        try:
            with Session() as session:
                blacklist_raw = queries.get_blacklist(session, user_id)
                blacklist = []
                for item in blacklist_raw:
                    if isinstance(item, bytes):
                        decoded_item = safe_decode(item)
                        blacklist.append(decoded_item)
                    else:
                        blacklist.append(str(item))
            vk_user = self.vk_handler.get_user_info(user_id)
            if not vk_user:
                self.send_message(user_id, "Не удалось получить ваши данные")
                return
            candidates = self.vk_handler.find_potential_matches(vk_user)
            candidates = [c for c in candidates if str(c.id) not in blacklist]
            if not candidates:
                self.send_message(user_id, "Не удалось найти подходящих кандидатов")
                return
            self.current_candidates[user_id] = candidates
            self.current_index[user_id] = 0
            self.show_current_candidate(user_id)
        except Exception as e:
            logger.error(f"Search error: {safe_str(e)}")
            self.send_message(user_id, "Произошла ошибка при поиске")

    def handle_show_favorites(self, user_id: int):
        try:
            with Session() as session:
                favorites = get_favorites_for_user(session, user_id)
            if not favorites:
                self.send_message(user_id, "У вас пока нет избранных кандидатов.", self.create_main_keyboard())
                return
            message = "Ваши избранные кандидаты:\\n\\n"
            for fav in favorites:
                message += (
                    f"{fav.first_name} {fav.last_name}\\n"
                    f"Возраст: {fav.age}\\n"
                    f"Город: {fav.city}\\n"
                    f"Ссылка: {fav.url_profile}\\n\\n"
                )
            self.send_message(user_id, message, self.create_favorites_keyboard())
        except Exception as e:
            logger.error(f"Ошибка в handle_show_favorites: {safe_str(e)}")
            self.send_message(user_id, "Ошибка при отображении избранных.", self.create_main_keyboard())

    def handle_add_to_favorites(self, user_id: int):
        try:
            with Session() as session:
                if user_id not in self.current_candidates or user_id not in self.current_index:
                    self.send_message(user_id, "Сначала найдите кандидатов.")
                    return
                index = self.current_index[user_id]
                candidate = self.current_candidates[user_id][index]
                existing = session.query(Favorites).filter(
                    Favorites.user_id == user_id,
                    Favorites.budding_id == candidate.id
                ).first()
                if existing:
                    self.send_message(user_id, "Этот кандидат уже в избранном!")
                    return
                fav = add_favorite(session, user_id, candidate.id)
                session.commit()
                self.send_message(user_id, f"Добавлено в избранное: {candidate.first_name} {candidate.last_name}", self.create_candidate_keyboard(candidate.id))
        except Exception as e:
            logger.error(f"Ошибка в handle_add_to_favorites: {safe_str(e)}")
            self.send_message(user_id, "Ошибка при добавлении в избранное.")



    def handle_message(self, event):
        try:
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
            elif text == '👎 убрать лайк':
                self.handle_unlike_photo(user_id)
            elif text in ['➡️ следующий', 'дальше']:
                self.handle_next_candidate(user_id)
            elif text == 'удалить из избранного':
                self.handle_remove_from_favorites(user_id)
            elif text in ['назад', 'отмена']:
                self.handle_start(user_id)
            else:
                self.send_message(user_id, "Я не понимаю вашу команду. Используйте кнопки или введите 'помощь'.", self.create_main_keyboard())
        except Exception as e:
            logger.error(f"Ошибка в handle_message: {safe_str(e)}")
