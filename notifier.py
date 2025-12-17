import logging
from logging.handlers import RotatingFileHandler

from src.db.database import db
from src.utils.embed_template import post_all_discords
from src.utils.helpers import get_map_records, ids_to_nicknames

handler = RotatingFileHandler(
    filename="logs/notifier.log", maxBytes=1024 * 1024, encoding="utf-8"
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
        map_records = get_map_records(map_uid=map["map_uid"], length=3, offset=0)

        if not map_records:
            logging.info("Нет рекордов на карте")
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
            logging.info(f"Новый wr от {new_wr['name']}")
            # уведомление дискорд
            post_all_discords(
                map=map, map_records=map_records, timestamp=map["map_wr_timestamp"]
            )
            # Запись timestamp в дб
            logging.info("Запись в дб")
            for record in map_records:
                db.update_map_wr_timestamp(
                    timestamp=new_wr["timestamp"], map_uid=map["map_uid"]
                )


if __name__ == "__main__":
    while True:
        logging.info("Цикл начат")
        main()
        logging.info("Цикл закончен")
