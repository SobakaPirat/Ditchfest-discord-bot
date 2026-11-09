import logging
import time

from src.utils.logger_config import setup_logging

setup_logging("logs/notifier.log")
logger = logging.getLogger(__name__)
logger.info("Запуск уведомлений")


from src.notifiers.records_notifier import process_all_maps


def main() -> None:
    process_all_maps()


if __name__ == "__main__":
    while True:
        logger.info("Цикл начат")
        main()
        logger.info("Цикл закончен")
        time.sleep(2)
