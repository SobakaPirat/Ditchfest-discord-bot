import logging
from logging.handlers import RotatingFileHandler

from src.db.database import db
from src.utils.helpers import id_to_records, ids_to_nicknames

handler = RotatingFileHandler(
    filename="logs/records.log", maxBytes=1024 * 1024, encoding="utf-8", backupCount=2
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[handler],
)

logger = logging.getLogger(__name__)
logger.info("Запуск приложения")


def main() -> None:
    maps_info = db.fetch_maps()
    for map in maps_info:
        logging.info("Карта: " + map["map_name"])
        map_records = id_to_records(map["map_uid"])

        # добавляем ники
        nicknames = ids_to_nicknames([item["accountId"] for item in map_records])
        for record in map_records:
            account_id = record["accountId"]
            if record["accountId"] in nicknames:
                record["name"] = nicknames[account_id]

        if not map_records:
            logging.info("Нет рекордов на карте")
            continue

        logging.info("Запись в дб")
        db.remove_old_records(map["map_uid"])
        for record in map_records:
            db.update_records(record, map["map_uid"])


if __name__ == "__main__":
    main()
