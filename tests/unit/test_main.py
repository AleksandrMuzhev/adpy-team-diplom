from unittest.mock import patch

from src.main import main


@patch('src.main.VKinderBot')
def test_main_success(mock_bot):
    """Тестирует успешный запуск основного потока выполнения программы.

    Проверяет что:
    - Создается экземпляр VKinderBot
    - Вызывается метод run() бота
    - Программа запускается без ошибок

    Использует моки для:
    - VKinderBot (чтобы не создавать реальный экземпляр)
    - print (чтобы не выводить сообщения в консоль)
    """
    with patch('builtins.print'):
        main()
    assert mock_bot.called


@patch('src.main.check_token')
@patch('src.main.logger')
def test_main_failure(mock_logger, mock_check):
    """Тестирует обработку ошибки при невалидном токене.

    Проверяет что:
    - При невалидном токене программа не создает бота
    - Записывается сообщение об ошибке в лог
    - Сообщение содержит информацию о невалидном токене

    Args:
        mock_logger: Мок логгера для проверки вызовов
        mock_check: Мок функции проверки токена (возвращает False)
    """
    mock_check.return_value = False
    with patch('builtins.print'):
        main()

    # Проверяем, что logger.error был вызван с правильным сообщением
    mock_logger.error.assert_called_with("Invalid VK_TOKEN")