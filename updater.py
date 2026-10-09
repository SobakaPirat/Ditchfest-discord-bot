import logging
import re
import time

import schedule

from src.updaters.maps_updater import get_new_maps
from src.updaters.records_updater import get_new_records
from src.utils.config import get_env_key
from src.utils.logger_config import setup_logging

setup_logging("logs/updater.log")
logger = logging.getLogger(__name__)
logger.info("Запуск обновления карт и рекордов")

UPDATER_TIME = get_env_key("UPDATER_TIME")
UPDATER_TIME_PATTERN = re.compile(r"\d{2}:\d{2}(:\d{2})?")


def validate_updater_time(value) -> str:
    """schedule требует строгий HH:MM(:SS) — падаем сразу с понятной ошибкой."""
    if value and UPDATER_TIME_PATTERN.fullmatch(value):
        return value
    raise SystemExit(
        f"UPDATER_TIME={value!r} некорректен: нужен формат HH:MM "
        "(например 04:00) в config/.env"
    )


def update() -> None:
    try:
        get_new_maps()
    except Exception:
        logger.exception("get_new_maps завершился с ошибкой")
    try:
        get_new_records()
    except Exception:
        logger.exception("get_new_records завершился с ошибкой")


schedule.every().day.at(validate_updater_time(UPDATER_TIME)).do(update)


update()
while True:
    schedule.run_pending()
    time.sleep(1)
