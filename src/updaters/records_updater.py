import logging

from src.db.database import db
from src.utils.helpers import id_to_records, ids_to_nicknames

logger = logging.getLogger(__name__)
logger.info("Запуск апдейтера рекордов")


def get_new_records() -> None:
    maps_info = db.fetch_maps()
    for map in maps_info:
        logger.info("Карта: " + map["map_name"])
        map_records = id_to_records(map["map_uid"])

        if not map_records:
            logger.info("Нет рекордов на карте")
            continue

        # добавляем ники
        nicknames = ids_to_nicknames([item["accountId"] for item in map_records])
        for record in map_records:
            account_id = record["accountId"]
            if record["accountId"] in nicknames:
                record["name"] = nicknames[account_id]

        logger.info("Запись в дб")
        db.replace_records(map["map_uid"], map_records)
