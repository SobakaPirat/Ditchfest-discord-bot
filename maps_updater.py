import logging
from logging.handlers import RotatingFileHandler

from dotenv import find_dotenv, get_key, load_dotenv

from src.db.database import db
from src.db.db_to_dropbox import upload_with_direct_link
from src.utils.helpers import (
    get_campaign,
    get_campaigns,
    get_map_playercount,
    get_maps_info,
    ids_to_nicknames,
)

# Set up logging
handler = RotatingFileHandler(
    filename="logs/maps.log", maxBytes=1024 * 1024, encoding="utf-8", backupCount=2
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[handler],
)
logger = logging.getLogger(__name__)
logger.info("Запуск апдейтера")


def fetch_campaign(all_campaigns: bool = False) -> list[dict]:
    logger.info("Собираем кампании")
    df_campaigns = get_campaigns("0", "DitchFest")["activityList"]

    valid_campaigns = [camp for camp in df_campaigns if camp["campaignId"] != 0]
    if not all_campaigns and valid_campaigns:
        valid_campaigns = [valid_campaigns[0]]

    logger.info("Собираем карты")
    campaign_maps = []
    for campaign in valid_campaigns:
        camp = get_campaign(campaign["campaignId"])
        publication_timestamp = camp["publicationTimestamp"]
        campaign_name = camp["name"]
        map_uids = [f"{m['mapUid']}" for m in camp["playlist"]]
        maps_info = get_maps_info(map_uids)
        campaign_maps.extend(
            [
                {
                    "map_uid": item["mapUid"],
                    "thumbnail": item["thumbnailUrl"],
                    "date": item["timestamp"][:10],
                    "filename": item["filename"].replace(".Map.Gbx", ""),
                    "author_uid": item["author"],
                    "author_time": item["authorScore"],
                    "gold_time": item["goldScore"],
                    "silver_time": item["silverScore"],
                    "bronze_time": item["bronzeScore"],
                    "type": item["mapType"],
                }
                for item in maps_info
            ]
        )
    logger.info("Карты взяты")
    return campaign_maps


def update_maps(all_campaigns: bool = False) -> None:
    campaign_maps = fetch_campaign(all_campaigns)
    for map in campaign_maps:
        if "Royal" in map["type"]:
            logger.info(map["filename"] + " Royal skipped")
            continue
        if "QnSv0bKhCNA1WcSKLiSXirMTo87" in map["map_uid"]:
            map["author_uid"] = "e10286e7-31dd-4127-bdf2-f092fd4e2887"
        db.update_map_info(map)
    logger.info("Карты записаны")


def update_playercounts() -> None:
    logger.info("Собираем playercounts")
    for map in db.fetch_maps_uid():
        playercount = get_map_playercount(map["map_uid"])
        db.update_maps_playercount(playercount, map["map_uid"])
    logger.info("Playercounts добавлены")


def update_nicknames() -> None:
    logger.info("Собираем никнеймы")
    authors_uid = db.fetch_authors_uid()
    unique_authors_uid = [item["map_author_uid"] for item in authors_uid]
    author_nicknames = ids_to_nicknames(unique_authors_uid)
    logger.info("Никнеймы получены")
    for uid, nickname in author_nicknames.items():
        db.update_author_nicknames(uid, nickname)
    logger.info("Никнеймы записаны")


def upload_to_dropbox() -> None:
    dotenv_path = find_dotenv()
    load_dotenv(dotenv_path)
    DROPBOX_SAVE = get_key(dotenv_path, ("DROPBOX_SAVE")).lower() == "true"
    if DROPBOX_SAVE:
        url = upload_with_direct_link()
        logger.info(url)


def main() -> None:
    if db.create_database_if_needed():
        update_maps(all_campaigns=True)
    update_maps(all_campaigns=False)
    update_playercounts()
    update_nicknames()
    upload_to_dropbox()
    logger.info("Завершено!")


if __name__ == "__main__":
    main()
