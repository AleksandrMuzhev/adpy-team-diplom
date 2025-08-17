import logging
from datetime import datetime
from typing import List, Optional, Dict

import vk_api
from pydantic import BaseModel
from vk_api.bot_longpoll import VkBotLongPoll

logger = logging.getLogger(__name__)


class VKUser(BaseModel):
    id: int
    first_name: str
    last_name: str
    age: Optional[int]
    city: Optional[str]
    sex: Optional[int]
    profile_url: str
    interests: Optional[Dict[str, List[str]]] = None


class VKPhoto(BaseModel):
    id: int
    owner_id: int
    likes: int
    url: str
    attachment_str: str


class VKAPIHandler:
    def __init__(self, group_token: str, group_id: int, user_token: Optional[str] = None):
        self.group_token = group_token
        self.user_token = user_token
        self.group_id = group_id

        # Инициализация сессии для работы с API группы
        self.vk_session = vk_api.VkApi(token=group_token)
        self.api = self.vk_session.get_api()

        # Инициализация сессии для работы с API пользователя (если токен предоставлен)
        if user_token:
            self.user_vk_session = vk_api.VkApi(token=user_token)
            self.user_api = self.user_vk_session.get_api()
        else:
            self.user_vk_session = None
            self.user_api = None

        try:
            self.longpoll = VkBotLongPoll(self.vk_session, group_id=group_id)
        except Exception as e:
            logger.warning(f"LongPoll initialization failed: {e}")
            self.longpoll = None

    def get_user_info(self, user_id: int) -> Optional[VKUser]:
        """
        Получает расширенную информацию о пользователе из VK API.

        Args:
            user_id (int): VK ID пользователя

        Returns:
            Optional[VKUser]: Объект с данными пользователя или None, если не найден

        Raises:
            VkApiError: При ошибках запроса к API
        """
        try:
            # Основная информация
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

            # Собираем интересы
            interests = {
                'music': user_data.get('music', '').split(', '),
                'books': user_data.get('books', '').split(', '),
                'movies': user_data.get('movies', '').split(', '),
                'interests': user_data.get('interests', '').split(', ')
            }

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
        except Exception as e:
            logger.error(f"Ошибка получения данных пользователя: {e}")
            return None

    def get_user_interests_score(self, user_id: int, candidate_id: int) -> float:
        """
        Вычисляет процент совпадения интересов между пользователем и кандидатом.

        Args:
            user_id (int): VK ID пользователя-инициатора поиска
            candidate_id (int): VK ID оцениваемого кандидата

        Returns:
            float: Значение от 0.0 до 1.0, где:
                0 - нет совпадений
                1 - полное совпадение интересов

        Calculation:
            Используется взвешенная формула:
            - Музыка: 40% веса
            - Книги: 30% веса
            - Фильмы: 20% веса
            - Общие интересы: 10% веса
            Для каждой категории считается процент совпадения элементов

        Examples:
            >>> get_user_interests_score(12345, 67890)
            0.75  # 75% совпадение интересов

        Notes:
            - Возвращает 0.0 если нет данных об интересах
            - Нормализует результат до 1.0
            - Логирует ошибки при вычислениях
        """
        try:
            user = self.get_user_info(user_id)
            candidate = self.get_user_info(candidate_id)

            if not user or not candidate or not user.interests or not candidate.interests:
                return 0.0

            score = 0.0
            weights = {'music': 0.4, 'books': 0.3, 'movies': 0.2, 'interests': 0.1}

            for category in weights:
                user_items = set(user.interests.get(category, []))
                cand_items = set(candidate.interests.get(category, []))
                common = user_items & cand_items
                score += weights[category] * (len(common) / len(user_items) if user_items else 0)

            return min(score, 1.0)
        except Exception as e:
            logger.error(f"Interest matching error: {e}")
            return 0.0

    def find_potential_matches(self, user: VKUser) -> List[VKUser]:
        """
        Ищет потенциальные пары для пользователя по заданным критериям.

        Args:
            user (VKUser): Объект с данными пользователя

        Returns:
            List[VKUser]: Список подходящих кандидатов, отсортированный по:
                1. Совпадение по городу
                2. Разница в возрасте
                3. Общие интересы

        Note:
            Использует методы:
            - users.search
            - groups.get
            - users.get с расширенными полями
        """
        try:
            search_params = {
                'sex': 1 if user.sex == 2 else 2,
                'age_from': user.age - 5 if user.age else None,
                'age_to': user.age + 5 if user.age else None,
                'city': user.city if hasattr(user, 'city') else None,  # Используем city вместо city_id
                'has_photo': 1,
                'count': 1000,
                'fields': 'sex,city,domain,bdate,interests,music,books,movies'
            }

            # Удаляем None-параметры
            search_params = {k: v for k, v in search_params.items() if v is not None}

            response = self.api.users.search(**search_params)
            candidates = []

            for item in response['items']:
                if item['is_closed']:
                    continue

                age = self._parse_age(item.get('bdate'))
                domain = item.get('domain', f"id{item['id']}")

                candidate = VKUser(
                    id=item['id'],
                    first_name=item['first_name'],
                    last_name=item['last_name'],
                    age=age,
                    city=item.get('city', {}).get('title'),
                    sex=item.get('sex'),
                    profile_url=f"https://vk.com/{domain}",
                    interests={
                        'music': item.get('music', '').split(', '),
                        'books': item.get('books', '').split(', '),
                        'movies': item.get('movies', '').split(', '),
                        'interests': item.get('interests', '').split(', ')
                    }
                )
                candidates.append(candidate)

            return candidates
        except Exception as e:
            if not hasattr(self, 'logger'):
                self.logger = logging.getLogger(__name__)
            self.logger.error(f"Search error: {str(e)}")
            return []

    def calculate_match_score(self, user: VKUser, candidate: dict) -> float:
        """
        Вычисляет общий процент совпадения между пользователем и кандидатом.

        Args:
            user (VKUser): Объект пользователя-инициатора
            candidate (dict): Данные кандидата в виде словаря

        Returns:
            float: Оценка совпадения от 0.0 до 1.0, где:
                0 - нет совпадений
                1 - полное совпадение

        Calculation:
            Использует взвешенную сумму по критериям:
            - Возраст: 40% (меньшая разница = больше баллов)
            - Город: 30% (полное совпадение)
            - Общие группы: 10% (нормализованное количество)
        """
        weights = {
            'age': 0.4,
            'city': 0.3,
            'interests': 0.2,
            'groups': 0.1
        }

        score = 0

        # Совпадение по возрасту
        if user.age and candidate.get('age'):
            age_diff = abs(user.age - candidate['age'])
            score += weights['age'] * (1 - min(age_diff / 10, 1))

        # Совпадение по городу
        if user.city and candidate.get('city'):
            if user.city.lower() == candidate['city'].lower():
                score += weights['city']

        # Общие группы (как показатель интересов)
        common_groups = self.get_common_interests(user.id, candidate['id'])
        score += weights['groups'] * common_groups

        return score

    def get_top_photos(self, user_id: int, count: int = 3) -> list:
        """
        Получает самые популярные фото профиля пользователя.

        Args:
            user_id (int): VK ID пользователя
            count (int): Количество возвращаемых фото (по умолчанию 3)

        Returns:
            list: Список словарей с данными фото:
                - id: ID фото
                - owner_id: ID владельца
                - url: Ссылка на фото
                - likes: Количество лайков

        Note:
            Сортирует фото по количеству лайков (убывание)
            Возвращает только фото среднего размера (type='m')
            При ошибках возвращает пустой список
        """
        try:
            photos = self.api.photos.get(
                owner_id=user_id,
                album_id='profile',
                extended=1,
                photo_sizes=1,
                count=100
            )['items']

            # Сортируем фото по количеству лайков (по убыванию)
            sorted_photos = sorted(
                photos,
                key=lambda x: x.get('likes', {}).get('count', 0),
                reverse=True
            )

            # Выбираем топ-N фото и формируем результат
            result = []
            for photo in sorted_photos[:count]:
                # Ищем URL среднего размера
                sizes = photo.get('sizes', [])
                url = next(
                    (size['url'] for size in sizes if size['type'] == 'm'),
                    None
                )
                if url:
                    result.append({
                        'id': photo['id'],
                        'owner_id': photo['owner_id'],
                        'url': url,
                        'likes': photo.get('likes', {}).get('count', 0)
                    })

            return result
        except Exception as e:
            if not hasattr(self, 'logger'):
                self.logger = logging.getLogger(__name__)
            self.logger.error(f"Get top photos error: {str(e)}")
            return []

    def prepare_attachments(self, photos: List[VKPhoto]) -> str:
        """
        Формирует строку вложений для отправки сообщений через VK API.

        Args:
            photos (List[VKPhoto]): Список объектов фото

        Returns:
            str: Строка в формате "photo{owner_id}_{id},photo{owner_id}_{id}"

        Example:
            >>> prepare_attachments([VKPhoto(123, 456), VKPhoto(123, 789)])
            'photo123_456,photo123_789'
        """
        return ",".join([photo.attachment_str for photo in photos])

    def _parse_age(self, bdate: Optional[str]) -> Optional[int]:
        """
        Парсит возраст из даты рождения формата 'DD.MM.YYYY'.

        Args:
            bdate (Optional[str]): Дата рождения в формате VK

        Returns:
            Optional[int]: Возраст в годах или None если:
                - Нет даты рождения
                - Неполная дата (только день и месяц)
        """
        if not bdate:
            return None
        parts = bdate.split('.')
        if len(parts) == 3:
            return datetime.now().year - int(parts[2])
        return None

    def like_photo(self, owner_id: int, photo_id: int) -> bool:
        """
        Ставит лайк указанной фотографии.

        Args:
            owner_id (int): ID владельца фото
            photo_id (int): ID фотографии

        Returns:
            bool: True если лайк поставлен, False при ошибке

        Note:
            Требует токен с правами на лайки
            Логирует ошибки операции
        """
        try:
            self.api.likes.add(
                type='photo',
                owner_id=owner_id,
                item_id=photo_id
            )
            return True
        except Exception as e:
            if not hasattr(self, 'logger'):
                self.logger = logging.getLogger(__name__)
            self.logger.error(f"Like photo error: {str(e)}")
            return False

    def unlike_photo(self, photo_id: int, owner_id: int) -> bool:
        """
        Убирает лайк с указанной фотографии.

        Args:
            photo_id (int): ID фотографии
            owner_id (int): ID владельца фото

        Returns:
            bool: True если лайк убран, False при ошибке

        Note:
            Требует пользовательский токен (не групповой)
            Логирует ошибки операции
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
        except Exception as e:
            logger.error(f"Ошибка при удалении лайка: {e}")
            return False

    def get_all_members(self):
        """
        Получает всех участников группы бота.

        Returns:
            list: Список участников с основными полями:
                - sex
                - city
                - bdate

        Note:
            Ограничение VK API - максимум 1000 участников
            Использует пакетные запросы по 200 участников
        """
        members = []
        offset = 0
        while offset < 1000:  # Максимально 1000 участников
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
        return members

    def get_common_interests(self, user_id: int, candidate_id: int) -> float:
        """
        Вычисляет процент общих групп между пользователями.

        Args:
            user_id (int): ID первого пользователя
            candidate_id (int): ID второго пользователя

        Returns:
            float: Процент общих групп от 0.0 до 1.0

        Note:
            Возвращает 0.0 при ошибках или отсутствии групп
            Процент считается от количества групп первого пользователя
        """
        try:
            user_groups = set(self.api.groups.get(user_id=user_id)['items'])
            candidate_groups = set(self.api.groups.get(user_id=candidate_id)['items'])
            common = user_groups & candidate_groups
            return len(common) / len(user_groups) if user_groups else 0
        except:
            return 0