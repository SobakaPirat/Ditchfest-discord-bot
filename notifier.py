import logging

from src.utils.logger_config import setup_logging

setup_logging("logs/notifier.log")
logger = logging.getLogger(__name__)
logger.info("Запуск уведомлений")


from src.db.database import db
from src.utils.embed_template import post_all_discords
from src.utils.helpers import get_map_records, ids_to_nicknames


def main() -> None:
    maps_info = db.fetch_maps()
    for map in maps_info:
        logger.info("Карта: " + map["map_name"])
        map_records = get_map_records(map_uid=map["map_uid"], length=3, offset=0)

        if not map_records:
            logger.info("Нет рекордов на карте")
            continue
        new_wr = map_records[0]

        if (map["map_wr_timestamp"] is not None) and (
            new_wr["timestamp"] != map["map_wr_timestamp"]
        ):
            # добавляем ники
            nicknames = ids_to_nicknames([item["accountId"] for item in map_records])
            for record in map_records:
                account_id = record["accountId"]
                if account_id in nicknames:
                    record["name"] = nicknames[account_id]
            logger.info(f"Новый wr от {new_wr['name']}")
            # уведомление дискорд
            post_all_discords(
                map=map, map_records=map_records, timestamp=map["map_wr_timestamp"]
            )

        if new_wr["timestamp"] != map["map_wr_timestamp"]:
            # Запись timestamp в дб
            logger.info("Запись в дб")
            for record in map_records:
                db.update_map_wr_timestamp(
                    timestamp=new_wr["timestamp"], map_uid=map["map_uid"]
                )


if __name__ == "__main__":
    while True:
        logger.info("Цикл начат")
        main()
        logger.info("Цикл закончен")
