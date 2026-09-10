import logging

import schedule
from dotenv import find_dotenv, get_key, load_dotenv

from src.updaters.maps_updater import get_new_maps
from src.updaters.records_updater import get_new_records
from src.utils.logger_config import setup_logging

setup_logging("logs/updater.log")
logger = logging.getLogger(__name__)
logger.info("Запуск обновления карт и рекордов")

dotenv_path = find_dotenv()
load_dotenv(dotenv_path)
UPDATER_TIME = get_key(dotenv_path, ("UPDATER_TIME"))


def update():
    print("started")
    get_new_maps()
    get_new_records()
    print("finished")


schedule.every().day.at(UPDATER_TIME).do(update)

while True:
    schedule.run_pending()
