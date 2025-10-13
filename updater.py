import logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    datefmt="%Y-%m-%d %H:%M:%S",
                    handlers=[logging.StreamHandler()])
logger = logging.getLogger(__name__)
logger.info("Запуск апдейтера")

from db.database import db
from db.db_to_dropbox import upload_with_direct_link
from helpers import get_maps_info, get_campaigns, get_campaign, get_map_playercount, ids_to_nicknames

#print(get_maps_info(['4W3wiyLZRLLyIMqVIDcFiz7hWm7']))
logger.info("Собираем кампании")
df_campaigns = get_campaigns("0", "DitchFest")['activityList']
logger.info("Собираем карты")
for campaign in df_campaigns[:1]:
    if campaign['campaignId'] != 0:
        camp = get_campaign(campaign['campaignId'])
        publication_timestamp = camp["publicationTimestamp"]
        campaign_name = camp["name"]
        map_uids = [f"{m['mapUid']}" for m in camp["playlist"]]
        maps_info = get_maps_info(map_uids)
        campaign_maps = [
            {   
                'map_uid': item['mapUid'],
                'thumbnail': item['thumbnailUrl'],
                'date': item['timestamp'][:10],
                'filename': item['filename'].replace('.Map.Gbx', ''),
                'author_uid': item['author'],
                'author_time': item['authorScore'],
                'gold_time': item['goldScore'],
                'silver_time': item['silverScore'],
                'bronze_time': item['bronzeScore'],
                'type': item['mapType']
            }
        for item in maps_info
        ]
        logger.info("Карты взяты")
        for map in campaign_maps:
            if 'Royal' in map['type']:
                logger.info(map['filename'] + 'Royal skipped')
                continue
            if 'QnSv0bKhCNA1WcSKLiSXirMTo87' in map['map_uid']:
                map['author_uid'] = 'e10286e7-31dd-4127-bdf2-f092fd4e2887'
            #map['playercount'] = get_map_playercount(map['map_uid'])
            db.update_map_info(map)
        logger.info("Карты записаны")

#playercount
logger.info("Собираем playercounts")
for _map in db.fetch_maps_uid():
    _playercount = get_map_playercount(_map['map_uid'])
    db.update_maps_playercount(_playercount, _map['map_uid'])
    #print(_playercount, _map['map_uid'])
logger.info("Playercounts добавлены")


#nicknames
logger.info("Собираем никнеймы")
authors_uid = db.fetch_authors_uid()
unique_authors_uid = [item['map_author_uid'] for item in authors_uid]
author_nicknames = ids_to_nicknames(unique_authors_uid)
logger.info("Никнеймы получены")

for uid, nickname in author_nicknames.items():
    #print(uid, nickname)
    db.update_author_nicknames(uid, nickname)
logger.info("Никнеймы записаны")

url = upload_with_direct_link()
logger.info(url)






