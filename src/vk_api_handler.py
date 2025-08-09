from datetime import datetime
from typing import List, Optional

import vk_api
from loguru import logger
from pydantic import BaseModel
from vk_api.bot_longpoll import VkBotLongPoll
from vk_api.exceptions import VkApiError


class VKUser(BaseModel):
    id: int
    first_name: str
    last_name: str
    age: Optional[int]
    city: Optional[str]
    sex: Optional[int]
    profile_url: str


class VKPhoto(BaseModel):
    id: int
    owner_id: int
    likes: int
    url: str
    attachment_str: str


class VKAPIHandler:
    def __init__(self, group_token: str, group_id: int):
        self.vk_session = vk_api.VkApi(token=group_token)
        self.api = self.vk_session.get_api()
        self.group_id = group_id

        try:
            self.longpoll = VkBotLongPoll(self.vk_session, group_id=group_id)
        except Exception as e:
            logger.warning(f"LongPoll initialization failed: {e}")
            self.longpoll = None

    def get_user_info(self, user_id: int) -> Optional[VKUser]:
        try:
            response = self.api.users.get(
                user_ids=user_id,
                fields="sex,city,bdate,domain",
                lang="ru"
            )
            if not response:
                return None

            user_data = response[0]
            age = self._parse_age(user_data.get('bdate'))
            domain = user_data.get('domain', f"id{user_id}")

            return VKUser(
                id=user_data['id'],
                first_name=user_data['first_name'],
                last_name=user_data['last_name'],
                age=age,
                city=user_data.get('city', {}).get('title'),
                sex=user_data.get('sex'),
                profile_url=f"https://vk.com/{domain}"
            )
        except Exception as e:
            logger.error(f"Ошибка получения данных: {e}")
            return None

    def find_potential_matches(self, user: VKUser) -> List[VKUser]:
        """Альтернативный поиск через друзей и группы"""
        try:
            # 1. Получаем друзей пользователя
            friends = self.api.friends.get(user_id=user.id, count=100)['items']

            # 2. Получаем друзей друзей
            friends_of_friends = []
            for friend_id in friends[:10]:  # Ограничиваем для скорости
                try:
                    friends_of_friends.extend(
                        self.api.friends.get(user_id=friend_id, count=50)['items']
                    )
                except VkApiError:
                    continue

            # 3. Фильтруем по полу и возрасту
            candidates = []
            for candidate_id in set(friends_of_friends):
                try:
                    candidate = self.api.users.get(
                        user_ids=candidate_id,
                        fields="sex,city,bdate,domain",
                        lang="ru"
                    )[0]

                    if (candidate.get('sex') != user.sex and
                            not candidate.get('is_closed')):
                        domain = candidate.get('domain', f"id{candidate_id}")
                        candidates.append(VKUser(
                            id=candidate['id'],
                            first_name=candidate['first_name'],
                            last_name=candidate['last_name'],
                            age=self._parse_age(candidate.get('bdate')),
                            city=candidate.get('city', {}).get('title'),
                            sex=candidate.get('sex'),
                            profile_url=f"https://vk.com/{domain}"
                        ))
                except Exception:
                    continue

            return candidates[:100]  # Ограничиваем результат

        except Exception as e:
            logger.error(f"Ошибка поиска: {e}")
            return []

    def get_top_photos(self, user_id: int) -> List[VKPhoto]:
        """Получаем фото через токен группы"""
        try:
            # Для группы доступны только фото, где пользователь отмечен
            photos = self.api.photos.getUserPhotos(
                user_id=user_id,
                count=100,
                extended=1
            )['items']

            top_photos = sorted(
                photos,
                key=lambda x: x['likes']['count'],
                reverse=True
            )[:3]

            return [
                VKPhoto(
                    id=photo['id'],
                    owner_id=photo['owner_id'],
                    likes=photo['likes']['count'],
                    url=max(photo['sizes'], key=lambda x: x['height'])['url'],
                    attachment_str=f"photo{photo['owner_id']}_{photo['id']}"
                ) for photo in top_photos
            ]
        except Exception as e:
            logger.error(f"Ошибка загрузки фото: {e}")
            return []

    def prepare_attachments(self, photos: List[VKPhoto]) -> str:
        """Формируем строку attachments для messages.send"""
        return ",".join([photo.attachment_str for photo in photos])

    def _parse_age(self, bdate: Optional[str]) -> Optional[int]:
        """Парсим возраст из даты рождения"""
        if not bdate:
            return None
        parts = bdate.split('.')
        if len(parts) == 3:
            return datetime.now().year - int(parts[2])
        return None
