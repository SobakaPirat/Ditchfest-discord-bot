import argparse
import logging

from db.database import db
from utils.embed_template import post_all_discords
from utils.helpers import id_to_records, ids_to_nicknames

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler()],
)

logger = logging.getLogger(__name__)
logger.info("Запуск приложения")

# Сколько карт проверяем для командной строки
parser = argparse.ArgumentParser()
parser.add_argument(
    "--maps", type=int, help="Количество карт для проверки (по умолчанию все)"
)
args = parser.parse_args()
if args.maps:
    logging.info(f"Будет проверено: {args.maps} карт")

maps_info = db.fetch_maps()[: args.maps]
for map in maps_info:
    logging.info("Карта: " + map["map_name"])
    map_records = id_to_records(map["map_uid"])
    nicknames = ids_to_nicknames([item["accountId"] for item in map_records])
    # добавляем ники
    for record in map_records:
        account_id = record["accountId"]
        if record["accountId"] in nicknames:
            record["name"] = nicknames[account_id]

    old_wr = db.get_wr(map["map_uid"])
    if not map_records:
        logging.info("Нет рекордов на карте")
        continue
    new_wr = map_records[0]
    # post_all_discords(map, map_records[:3], old_wr['player_timestamp'])
    if (old_wr is not None) and (new_wr["timestamp"] != old_wr["player_timestamp"]):
        logging.info(f"Новый wr от {new_wr['name']}")
        post_all_discords(map, map_records[:3], old_wr["player_timestamp"])

    logging.info("Запись в дб")
    db.remove_old_records(map["map_uid"])
    for record in map_records:
        db.update_records(record, map["map_uid"])
