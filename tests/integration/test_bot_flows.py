from unittest.mock import MagicMock


# python -m pytest ./tests/integration/test_bot_flows.py -k test_full_flow
def test_full_flow(bot):
    """
    Тестирует полный цикл работы бота: от поиска до взаимодействия с кандидатом.

    Arrange:
        - Настраиваем моки для возврата тестового пользователя и кандидата
    Act:
        - Вызываем handle_find_pair
    Assert:
        - Проверяем, что кандидаты были сохранены в current_candidates
    """
    bot.vk_handler.get_user_info.return_value = MagicMock(city="Moscow", age=25)
    bot.vk_handler.find_potential_matches.return_value = [MagicMock(id=123)]
    bot.handle_find_pair(123)
    assert bot.current_candidates.get(123) is not None
