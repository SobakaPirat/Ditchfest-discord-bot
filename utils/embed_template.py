import logging
from datetime import datetime, timedelta, timezone

from discord_webhook import DiscordEmbed, DiscordWebhook
from dotenv import find_dotenv, get_key, load_dotenv

from utils.helpers import (
    get_nadeo_zones,
    get_player_flag,
    number_to_time,
    retry_on_error,
)

logger = logging.getLogger(__name__)


@retry_on_error()
def post_record(
    webhook_url: str, map: dict, timestamp: int, map_records: list[dict]
) -> None:
    moscow_time = timezone(timedelta(hours=3))

    webhook = DiscordWebhook(url=webhook_url, timeout=5)

    embed = DiscordEmbed(
        title=map["map_name"],
        url=f"https://trackmania.io/#/leaderboard/{map['map_uid']}",
        description=f"{map['map_author_name']}\n\n:checkered_flag: New World Record!",
        color=0xFFE500,
        timestamp=datetime.now(tz=moscow_time),
    )

    # embed.set_author(name=map['map_author_name'])

    medals = [":first_place:", ":second_place:", ":third_place:"]
    nadeo_zones = get_nadeo_zones()
    nicknames_discord = ""
    for place in range(min(3, len(map_records))):
        nicknames_discord += f"{medals[place]} {get_player_flag(map_records[place]['zoneId'], nadeo_zones)} {map_records[place]['name']}\n"
    embed.add_embed_field(name="Record Holder", value=nicknames_discord, inline=True)

    if map_records[0]["score"] < 0:
        time_text = "-# Secret\n" * min(3, len(map_records))
    else:
        time_text = ""
        for place in range(min(3, len(map_records))):
            if place == 0:
                time_text += f"{number_to_time(map_records[place]['score'])}\n"
            else:
                time_text += f"{number_to_time(map_records[place]['score'])} (+{number_to_time(map_records[place]['score'] - map_records[0]['score'])})\n"
        embed.add_embed_field(name="Time", value=time_text, inline=True)

    if timestamp is not None:
        embed.add_embed_field(
            name="",
            value=f"The previous world record has been set <t:{timestamp}:R>",
            inline=False,
        )

    embed.set_thumbnail(url=map["map_thumbnail"])

    embed.set_footer(
        text="by Soba",
        icon_url="https://download.dashmap.live/e10286e7-31dd-4127-bdf2-f092fd4e2887/df_short.png",
    )

    # Добавляем Embed в Webhook
    webhook.add_embed(embed)

    # Отправляем
    webhook.execute()
    logger.info("Сообщение отправлено!")


def post_all_discords(
    map: dict[str, any], map_records: list[dict[str, any]], timestamp: int = None
) -> None:
    dotenv_path = find_dotenv()
    load_dotenv(dotenv_path)
    WEBHOOKS_URL = get_key(dotenv_path, ("WEBHOOKS_URL"))
    post_record(WEBHOOKS_URL, map, timestamp, map_records)
