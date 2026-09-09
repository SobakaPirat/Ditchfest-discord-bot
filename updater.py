import logging

from src.utils.logger_config import setup_logging

setup_logging("logs/test.log")
logger = logging.getLogger(__name__)
logger.info("Запуск приложения")
