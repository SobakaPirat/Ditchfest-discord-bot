from discord_webhook import DiscordWebhook, DiscordEmbed
from helpers import number_to_time, retry_on_error
from datetime import datetime, timedelta, timezone
from dotenv import find_dotenv, load_dotenv, set_key, get_key
import time
import logging

logger = logging.getLogger(__name__)

@retry_on_error()
def post_record(webhook_url, map, timestamp, map_records):
    moscow_time = timezone(timedelta(hours=3))

    # difference = [number_to_time(map_records[1]['score'] - map_records[0]['score']), number_to_time(map_records[2]['score'] - map_records[0]['score'])]
    
    webhook = DiscordWebhook(url=webhook_url,timeout=5)

    embed = DiscordEmbed(title=map['map_name'],
                        url=f"https://trackmania.io/#/leaderboard/{map['map_uid']}",
                        description=":checkered_flag: Новый рекорд!",
                        color=0xffe500,
                        timestamp=datetime.now(tz=moscow_time))

    #embed.set_author(name=map['map_author_name'])

    medals = [":first_place:", ":second_place:", ":third_place:"]
    nicknames_discord = ""
    for place in range(min(3, len(map_records))):
        nicknames_discord += f"{medals[place]} {map_records[place]['name']}\n"
    embed.add_embed_field(name="Рекордсмены",
                    value=nicknames_discord,
                    inline=True)
    
    if map_records[0]['score'] < 0:
        time_text = "-# Secret\n" * min(3, len(map_records))
    else:
        time_text = ""
        for place in range(min(3, len(map_records))):
            if place == 0:
                time_text += f"{number_to_time(map_records[place]['score'])}\n"
            else:
                time_text += f"{number_to_time(map_records[place]['score'])} (+{number_to_time(map_records[place]['score'] - map_records[0]['score'])})\n"
        embed.add_embed_field(name="Время",
                        value=time_text,
                        inline=True)
        
    if timestamp is not None:
        embed.add_embed_field(name="",
                        value=f"Прошлый рекорд был поставлен <t:{timestamp}:R>",
                        inline=False)

    embed.set_thumbnail(url=map['map_thumbnail'])

    embed.set_footer(text="by Soba",
                    icon_url="https://images2.imgbox.com/2f/41/jhWjD3hp_o.png")

    # Добавляем Embed в Webhook
    webhook.add_embed(embed)

    # Отправляем
    webhook.execute()
    logger.info("Сообщение отправлено!")

def post_all_discords(map, map_records, timestamp):
    dotenv_path = find_dotenv()
    load_dotenv(dotenv_path)
    WEBHOOKS_URL = get_key(dotenv_path, ("WEBHOOKS_URL"))
    post_record(WEBHOOKS_URL, map, timestamp, map_records)

