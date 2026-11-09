import logging

from src.db.database import db
from src.utils.embed_template import post_all_discords
from src.utils.helpers import apply_nicknames, get_map_records

logger = logging.getLogger(__name__)

# 0 в map_wr_timestamp = карта проверена, но рекордов ещё не было
NO_RECORDS_TIMESTAMP = 0


def process_map(map: dict) -> None:
    """Сравнивает текущий рекорд карты с сохранённым и уведомляет о новом."""
    logger.info("Карта: " + map["map_name"])
    map_records = get_map_records(map_uid=map["map_uid"], length=3, offset=0)
    saved_timestamp = map["map_wr_timestamp"]

    if not map_records:
        logger.info("Нет рекордов на карте")
        # помечаем пустую карту, чтобы первый рекорд вызвал уведомление
        if saved_timestamp is None:
            db.update_map_wr_timestamp(
                timestamp=NO_RECORDS_TIMESTAMP, map_uid=map["map_uid"]
            )
        return

    new_wr = map_records[0]

    # первое наблюдение — запоминаем baseline без уведомления
    if saved_timestamp is None:
        db.update_map_wr_timestamp(
            timestamp=new_wr["timestamp"], map_uid=map["map_uid"]
        )
        return

    if new_wr["timestamp"] == saved_timestamp:
        return

    apply_nicknames(map_records)
    logger.info(f"Новый wr от {new_wr['name']}")
    # у пустой карты предыдущего рекорда нет
    post_all_discords(
        map=map, map_records=map_records, timestamp=saved_timestamp or None
    )
    db.update_map_wr_timestamp(timestamp=new_wr["timestamp"], map_uid=map["map_uid"])


def process_all_maps() -> None:
    """Проверяет все карты; ошибка одной карты не прерывает остальные."""
    for map in db.fetch_maps():
        try:
            process_map(map)
        except Exception:
            logger.exception(f"Ошибка при обработке карты {map.get('map_uid', '?')}")
