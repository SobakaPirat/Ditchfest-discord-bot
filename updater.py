import logging

import schedule

from src.updaters.maps_updater import get_new_maps
from src.updaters.records_updater import get_new_records
from src.utils.config import get_env_key
from src.utils.logger_config import setup_logging

setup_logging("logs/updater.log")
logger = logging.getLogger(__name__)
logger.info("Запуск обновления карт и рекордов")

UPDATER_TIME = get_env_key("UPDATER_TIME")


def update():
    get_new_maps()
    open("database/.ready", "w").close()  # для docker-compose
    get_new_records()


schedule.every().day.at(UPDATER_TIME).do(update)


update()
while True:
    schedule.run_pending()
