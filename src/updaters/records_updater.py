import logging

from src.db.database import db
from src.utils.helpers import apply_nicknames, id_to_records

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

        apply_nicknames(map_records)

        logger.info("Запись в дб")
        db.replace_records(map["map_uid"], map_records)
