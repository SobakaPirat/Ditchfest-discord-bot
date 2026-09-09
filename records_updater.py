import logging

from src.utils.logger_config import setup_logging

setup_logging("logs/records.log")
logger = logging.getLogger(__name__)
logger.info("Запуск апдейтера рекордов")


from src.db.database import db
from src.utils.helpers import id_to_records, ids_to_nicknames


def main() -> None:
    maps_info = db.fetch_maps()
    for map in maps_info:
        logger.info("Карта: " + map["map_name"])
        map_records = id_to_records(map["map_uid"])

        # добавляем ники
        nicknames = ids_to_nicknames([item["accountId"] for item in map_records])
        for record in map_records:
            account_id = record["accountId"]
            if record["accountId"] in nicknames:
                record["name"] = nicknames[account_id]

        if not map_records:
            logger.info("Нет рекордов на карте")
            continue

        logger.info("Запись в дб")
        db.remove_old_records(map["map_uid"])
        for record in map_records:
            db.update_records(record, map["map_uid"])


if __name__ == "__main__":
    main()
