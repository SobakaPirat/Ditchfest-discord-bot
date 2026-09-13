import logging

import schedule

from src.db.database import Database
from src.db.db_to_dropbox import upload_to_dropbox
from src.utils.logger_config import setup_logging

setup_logging("logs/backup.log")
logger = logging.getLogger(__name__)
logger.info("Запуск бекапа")

db = Database()


def update():
    db.make_backup()
    upload_to_dropbox()


schedule.every(12).hours.do(update)

while True:
    schedule.run_pending()
