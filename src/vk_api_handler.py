import logging
from datetime import datetime
from typing import List, Optional, Dict

import vk_api
from vk_api.bot_longpoll import VkBotLongPoll
from vk_api.exceptions import ApiError

from pydantic import BaseModel


logger = logging.getLogger(__name__)


def safe_decode(data):
    """
    Безопасно декодирует байты в строку.

    Пытается декодировать данные сначала в 'utf-8', затем в 'cp1251' с заменой ошибок.
    Если не удаётся, возвращает str(data).

    Args:
        data (bytes): данные для декодирования.

    Returns:
        str: декодированная строка.
    """
    try:
        return data.decode('utf-8')
    except (UnicodeDecodeError, AttributeError):
        try:
            return data.decode('cp1251', errors='replace')
        except Exception:
            return str(data)


def safe_str(obj):
    """
    Безопасно приводит объект к строке.

    В случае UnicodeDecodeError кодирует в 'cp1251' и декодирует обратно.

    Args:
        obj: объект для преобразования в строку.

    Returns:
        str: строковое представление объекта.
    """
    try:
        return str(obj)
    except UnicodeDecodeError:
        return str(obj).encode('cp1251', errors='replace').decode('cp1251')


class VKUser(BaseModel):
    """
    Модель пользователя ВК.

    Attributes:
        id (int): ID пользователя.
        first_name (str): имя пользователя.
        last_name (str): фамилия пользователя.
        age (Optional[int]): возраст пользователя.
        city (Optional[str]): город пользователя.
        sex (Optional[int]): пол пользователя.
        profile_url (str): URL профиля ВК.
        interests (Optional[Dict[str, List[str]]]): интересы пользователя.
    """
    id: int
    first_name: str
    last_name: str
    age: Optional[int]
    city: Optional[str]
    sex: Optional[int]
    profile_url: str
    interests: Optional[Dict[str, List[str]]] = None


class VKPhoto(BaseModel):
    """
    Модель фотографии пользователя ВК.

    Attributes:
        id (int): ID фотографии.
        owner_id (int): ID владельца фотографии.
        likes (int): количество лайков.
        url (str): ссылка на фотографию.
        attachment_str (str): строка-вложение для сообщения ВК.
    """
    id: int
    owner_id: int
    likes: int
    url: str
    attachment_str: str


class VKAPIHandler:
    """
    Класс для взаимодействия с VK API.

    Использует токены группы и пользователя для доступа к методам API ВК.

    Attributes:
        group_token (str): токен группы.
        group_id (int): ID группы.
        user_token (Optional[str]): токен пользователя, если есть.
    """

    def __init__(self, group_token: str, group_id: int, user_token: Optional[str] = None):
        """
        Инициализация VKAPIHandler.

        Создает сессии для группы и (опционально) пользователя, а также объект longpoll.

        Args:
            group_token (str): токен группы ВК.
            group_id (int): идентификатор группы ВК.
            user_token (Optional[str]): токен пользователя ВК.
        """
        self.group_token = group_token
        self.user_token = user_token
        self.group_id = group_id

        self.vk_session = vk_api.VkApi(token=group_token)
        self.api = self.vk_session.get_api()

        if user_token:
            self.user_vk_session = vk_api.VkApi(token=user_token)
            self.user_api = self.user_vk_session.get_api()
        else:
            self.user_vk_session = None
            self.user_api = None

        try:
            self.longpoll = VkBotLongPoll(self.vk_session, group_id=group_id)
        except Exception as e:
            logger.warning(f"LongPoll initialization failed: {safe_str(e)}")
            self.longpoll = None

    def get_user_info(self, user_id: int) -> Optional[VKUser]:
        """
        Получает информацию о пользователе ВК по его ID.

        Args:
            user_id (int): ID пользователя.

        Returns:
            Optional[VKUser]: объект VKUser с данными пользователя или None при ошибке.
        """
        try:
            response = self.api.users.get(
                user_ids=user_id,
                fields="sex,city,bdate,domain,interests,music,books,movies",
                lang="ru"
            )
            if not response:
                return None

            user_data = response[0]
            age = self._parse_age(user_data.get('bdate'))
            domain = user_data.get('domain', f"id{user_id}")

            interests = {
                'music': safe_decode(user_data.get('music', '').encode()) if isinstance(user_data.get('music', ''), str) else safe_decode(user_data.get('music', b'')),
                'books': safe_decode(user_data.get('books', '').encode()) if isinstance(user_data.get('books', ''), str) else safe_decode(user_data.get('books', b'')),
                'movies': safe_decode(user_data.get('movies', '').encode()) if isinstance(user_data.get('movies', ''), str) else safe_decode(user_data.get('movies', b'')),
                'interests': safe_decode(user_data.get('interests', '').encode()) if isinstance(user_data.get('interests', ''), str) else safe_decode(user_data.get('interests', b''))
            }
            for k in interests:
                interests[k] = interests[k].split(', ') if interests[k] else []

            return VKUser(
                id=user_data['id'],
                first_name=user_data['first_name'],
                last_name=user_data['last_name'],
                age=age,
                city=user_data.get('city', {}).get('title'),
                sex=user_data.get('sex'),
                profile_url=f"https://vk.com/{domain}",
                interests=interests
            )
        except ApiError as e:
            if e.code == 14:
                captcha_sid = e.error.get('captcha_sid')
                captcha_img = e.error.get('captcha_img')
                logger.error(f"Captcha required for user {user_id}: SID={captcha_sid} IMG={captcha_img}")
            else:
                logger.error(f"VK API error при получении данных пользователя {user_id}: {safe_str(e)}")
            return None
        except Exception as e:
            logger.error(f"Ошибка получения данных пользователя {user_id}: {safe_str(e)}")
            return None

    def find_potential_matches(self, user: VKUser) -> List[VKUser]:
        """
        Поиск потенциальных совпадений для данного пользователя.

        Args:
            user (VKUser): исходный пользователь.

        Returns:
            List[VKUser]: список подходящих кандидатов.
        """
        try:
            search_params = {
                'sex': 1 if user.sex == 2 else 2,
                'age_from': user.age - 5 if user.age else None,
                'age_to': user.age + 5 if user.age else None,
                'city': user.city if hasattr(user, 'city') else None,
                'has_photo': 1,
                'count': 1000,
                'fields': 'sex,city,domain,bdate,interests,music,books,movies'
            }
            search_params = {k: v for k, v in search_params.items() if v is not None}

            response = self.api.users.search(**search_params)

            candidates = []
            for item in response.get('items', []):
                if item.get('is_closed'):
                    continue

                age = self._parse_age(item.get('bdate'))
                domain = item.get('domain', f"id{item['id']}")

                interests = {
                    'music': safe_decode(item.get('music', '').encode()) if isinstance(item.get('music', ''), str) else safe_decode(item.get('music', b'')),
                    'books': safe_decode(item.get('books', '').encode()) if isinstance(item.get('books', ''), str) else safe_decode(item.get('books', b'')),
                    'movies': safe_decode(item.get('movies', '').encode()) if isinstance(item.get('movies', ''), str) else safe_decode(item.get('movies', b'')),
                    'interests': safe_decode(item.get('interests', '').encode()) if isinstance(item.get('interests', ''), str) else safe_decode(item.get('interests', b''))
                }
                for k in interests:
                    interests[k] = interests[k].split(', ') if interests[k] else []

                candidate = VKUser(
                    id=item['id'],
                    first_name=item['first_name'],
                    last_name=item['last_name'],
                    age=age,
                    city=item.get('city', {}).get('title'),
                    sex=item.get('sex'),
                    profile_url=f"https://vk.com/{domain}",
                    interests=interests
                )
                candidates.append(candidate)
            return candidates
        except ApiError as e:
            if e.code == 14:
                captcha_sid = e.error.get('captcha_sid')
                captcha_img = e.error.get('captcha_img')
                logger.error(f"Captcha required during search: SID={captcha_sid} IMG={captcha_img}")
            else:
                logger.error(f"VK API error during search: {safe_str(e)}")
            return []
        except Exception as e:
            logger.error(f"Search error: {safe_str(e)}")
            return []

    def _parse_age(self, bdate: Optional[str]) -> Optional[int]:
        """
        Парсит дату рождения пользователя и вычисляет возраст.

        Args:
            bdate (Optional[str]): дата рождения в формате 'DD.MM.YYYY'.

        Returns:
            Optional[int]: возраст пользователя или None, если не удалось вычислить.
        """
        if not bdate:
            return None
        parts = bdate.split('.')
        if len(parts) == 3:
            try:
                return datetime.now().year - int(parts[2])
            except ValueError:
                return None
        return None

    def like_photo(self, owner_id: int, photo_id: int) -> bool:
        """
        Поставить лайк фото.

        Args:
            owner_id (int): ID владельца фото.
            photo_id (int): ID фото.

        Returns:
            bool: True, если успешно, иначе False.
        """
        try:
            self.api.likes.add(
                type='photo',
                owner_id=owner_id,
                item_id=photo_id
            )
            return True
        except ApiError as e:
            if e.code == 14:
                captcha_sid = e.error.get('captcha_sid')
                captcha_img = e.error.get('captcha_img')
                logger.error(f"Captcha required during like_photo: SID={captcha_sid} IMG={captcha_img}")
            else:
                logger.error(f"VK API error during like_photo: {e}")
            return False
        except Exception as e:
            logger.error(f"Like photo error: {e}")
            return False

    def unlike_photo(self, photo_id: int, owner_id: int) -> bool:
        """
        Убрать лайк с фото.

        Args:
            photo_id (int): ID фото.
            owner_id (int): ID владельца фото.

        Returns:
            bool: True, если успешно, иначе False.
        """
        if not self.user_api:
            return False
        try:
            self.user_api.likes.delete(
                type='photo',
                owner_id=owner_id,
                item_id=photo_id
            )
            return True
        except ApiError as e:
            if e.code == 14:
                captcha_sid = e.error.get('captcha_sid')
                captcha_img = e.error.get('captcha_img')
                logger.error(f"Captcha required during unlike_photo: SID={captcha_sid} IMG={captcha_img}")
            else:
                logger.error(f"VK API error during unlike_photo: {e}")
            return False
        except Exception as e:
            logger.error(f"Unlike photo error: {e}")
            return False

    def get_all_members(self):
        """
        Получить список всех участников группы до 1000 человек.

        Returns:
            list: список словарей с данными участников.
        """
        members = []
        offset = 0
        while offset < 1000:
            try:
                batch = self.api.groups.getMembers(
                    group_id=self.group_id,
                    fields='sex,city,bdate',
                    offset=offset,
                    count=200
                )['items']
                if not batch:
                    break
                members.extend(batch)
                offset += len(batch)
            except ApiError as e:
                if e.code == 14:
                    captcha_sid = e.error.get('captcha_sid')
                    captcha_img = e.error.get('captcha_img')
                    logger.error(f"Captcha required during get_all_members: SID={captcha_sid} IMG={captcha_img}")
                else:
                    logger.error(f"VK API error during get_all_members: {e}")
                break
            except Exception as e:
                logger.error(f"Error during get_all_members: {e}")
                break
        return members

    def get_common_interests(self, user_id: int, candidate_id: int) -> float:
        """
        Вычисляет долю общих групп (интересов) между двумя пользователями ВК.

        Args:
            user_id (int): ID первого пользователя.
            candidate_id (int): ID второго пользователя.

        Returns:
            float: доля общих групп, число от 0 до 1.
        """
        try:
            user_groups = set(self.api.groups.get(user_id=user_id)['items'])
            candidate_groups = set(self.api.groups.get(user_id=candidate_id)['items'])
            common = user_groups & candidate_groups
            return len(common) / len(user_groups) if user_groups else 0
        except ApiError as e:
            if e.code == 14:
                captcha_sid = e.error.get('captcha_sid')
                captcha_img = e.error.get('captcha_img')
                logger.error(f"Captcha required during get_common_interests: SID={captcha_sid} IMG={captcha_img}")
            else:
                logger.error(f"VK API error during get_common_interests: {e}")
            return 0
        except Exception as e:
            logger.error(f"Error during get_common_interests: {e}")
            return 0
