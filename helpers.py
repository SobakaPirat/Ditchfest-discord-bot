import logging
import time
from functools import wraps

import pycountry
import requests
from dotenv import find_dotenv, get_key, load_dotenv

from auth.auth import check_token_refresh

logger = logging.getLogger(__name__)


def retry_on_error(max_retries=10, delay=2, backoff=2):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            current_delay = delay

            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    retries += 1
                    if retries >= max_retries:
                        logger.error(
                            f"Функция {func.__name__} не сработала после {max_retries} попыток. Ошибка: {e}"
                        )
                        raise

                    logger.warning(
                        f"Попытка {retries}/{max_retries} не удалась. Ошибка: {e}. Повтор через {current_delay} сек..."
                    )
                    time.sleep(current_delay)
                    current_delay *= backoff

            return None

        return wrapper

    return decorator


@retry_on_error()
def get_map_records(map_uid, offset):
    check_token_refresh()
    dotenv_path = find_dotenv()
    load_dotenv(dotenv_path)
    NADEO_LIVESERVICES_ACCESS_TOKEN = get_key(
        dotenv_path, ("NADEO_LIVESERVICES_ACCESS_TOKEN")
    )
    USER_AGENT = get_key(dotenv_path, ("USER_AGENT"))

    url = f"https://live-services.trackmania.nadeo.live/api/token/leaderboard/group/Personal_Best/map/{map_uid}/top?length=100&onlyWorld=1&offset={offset}"
    headers = {
        "Authorization": "nadeo_v1 t=" + NADEO_LIVESERVICES_ACCESS_TOKEN,
        "User-Agent": USER_AGENT,
    }

    res = requests.get(url, headers=headers)
    res = res.json()
    logger.info(f"Рекорды получены: {map_uid}")
    # time.sleep(0.5)
    return res["tops"][0]["top"]


@retry_on_error()
def get_account_name(uids):
    check_token_refresh()
    dotenv_path = find_dotenv()
    load_dotenv(dotenv_path)
    OAUTH_TOKEN = get_key(dotenv_path, ("OAUTH_TOKEN"))
    USER_AGENT = get_key(dotenv_path, ("USER_AGENT"))

    url = "https://api.trackmania.com/api/display-names?"
    for uid in uids:
        url += "&accountId[]=" + uid
    headers = {"Authorization": f"Bearer {OAUTH_TOKEN}", "User-Agent": USER_AGENT}

    res = requests.get(url, headers=headers)
    res = res.json()
    # time.sleep(0.5)
    return res


def split_list(input_list, chunk_size):
    return [
        input_list[i : i + chunk_size] for i in range(0, len(input_list), chunk_size)
    ]


@retry_on_error()
def id_to_records(map_uid):
    current_records = []
    stop = False
    offset = 0
    while not stop:
        map_records = get_map_records(map_uid, offset)
        current_records.extend(map_records)
        # print(len(map_records))
        if len(map_records) < 100:
            stop = True
        # time.sleep(0.5)
        offset += 100
    logger.info(f"{len(current_records)} Рекордов получено")
    return current_records


def ids_to_nicknames(uids):
    ids_splited = split_list(uids, 50)
    # print(ids_splited)
    current_nicknames = {}
    for ids_list in ids_splited:
        # get_account_name(ids_list)
        current_nicknames.update(get_account_name(ids_list))
    logger.info("Никнеймы получены")
    return current_nicknames


def number_to_time(number):
    if number < 0:
        return "secret"

    seconds, ms = divmod(number, 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)

    if hours:
        return f"{hours}:{minutes:02d}:{seconds:02d}.{ms:03d}"
    if minutes:
        return f"{minutes}:{seconds:02d}.{ms:03d}"
    if seconds:
        return f"{seconds}.{ms:03d}"
    return f"0.{ms:03d}"


@retry_on_error()
def get_maps_info(map_uids):
    check_token_refresh()
    dotenv_path = find_dotenv()
    load_dotenv(dotenv_path)
    NADEO_ACCESS_TOKEN = get_key(dotenv_path, ("NADEO_ACCESS_TOKEN"))
    USER_AGENT = get_key(dotenv_path, ("USER_AGENT"))
    url = f"https://prod.trackmania.core.nadeo.online/maps/?mapUidList={','.join(map_uids)}"

    headers = {
        "Authorization": "nadeo_v1 t=" + NADEO_ACCESS_TOKEN,
        "User-Agent": USER_AGENT,
    }
    res = requests.get(url, headers=headers)
    res = res.json()
    return res


@retry_on_error()
def get_campaign(campaign_id):
    check_token_refresh()
    dotenv_path = find_dotenv()
    load_dotenv(dotenv_path)
    NADEO_LIVESERVICES_ACCESS_TOKEN = get_key(
        dotenv_path, ("NADEO_LIVESERVICES_ACCESS_TOKEN")
    )
    USER_AGENT = get_key(dotenv_path, ("USER_AGENT"))
    url = f"https://live-services.trackmania.nadeo.live/api/token/club/52818/campaign/{campaign_id}"
    headers = {
        "Authorization": "nadeo_v1 t=" + NADEO_LIVESERVICES_ACCESS_TOKEN,
        "User-Agent": USER_AGENT,
    }
    res = requests.get(url, headers=headers)
    res = res.json()
    return res["campaign"]


@retry_on_error()
def get_campaigns(offset, name):
    check_token_refresh()
    dotenv_path = find_dotenv()
    load_dotenv(dotenv_path)
    NADEO_LIVESERVICES_ACCESS_TOKEN = get_key(
        dotenv_path, ("NADEO_LIVESERVICES_ACCESS_TOKEN")
    )
    USER_AGENT = get_key(dotenv_path, ("USER_AGENT"))
    url = f"https://live-services.trackmania.nadeo.live/api/token/club/52818/activity?length=200&offset={offset}&active=true"
    headers = {
        "Authorization": "nadeo_v1 t=" + NADEO_LIVESERVICES_ACCESS_TOKEN,
        "User-Agent": USER_AGENT,
    }
    res = requests.get(url, headers=headers)
    res = res.json()
    return res


@retry_on_error()
def get_map_playercount(map_uid):
    check_token_refresh()
    dotenv_path = find_dotenv()
    load_dotenv(dotenv_path)
    NADEO_LIVESERVICES_ACCESS_TOKEN = get_key(
        dotenv_path, ("NADEO_LIVESERVICES_ACCESS_TOKEN")
    )
    USER_ID = get_key(dotenv_path, ("USER_ID"))
    USER_AGENT = get_key(dotenv_path, ("USER_AGENT"))
    leaderboard_url = (
        "https://live-services.trackmania.nadeo.live/api/token/leaderboard/group/"
    )
    groupUid = "Personal_Best"
    lower = "1"
    upper = "1"
    score = "1000000000"

    # Build url
    complete_url = (
        leaderboard_url
        + groupUid
        + "/map/"
        + map_uid
        + "/surround/"
        + lower
        + "/"
        + upper
        + "?score="
        + score
    )
    # Send get request

    headers = {
        "Authorization": "nadeo_v1 t=" + NADEO_LIVESERVICES_ACCESS_TOKEN,
        "User-Agent": USER_AGENT,
    }

    res = requests.get(complete_url, headers=headers)
    res = res.json()

    scores = res["tops"][0]["top"]
    if scores[0]["accountId"] == USER_ID:
        return 0

    # last score on leaderboard has playercount position
    playercount = scores[0]["position"]

    return playercount


@retry_on_error()
def get_nadeo_zones():
    check_token_refresh()
    dotenv_path = find_dotenv()
    load_dotenv(dotenv_path)
    NADEO_ACCESS_TOKEN = get_key(dotenv_path, ("NADEO_ACCESS_TOKEN"))
    USER_AGENT = get_key(dotenv_path, ("USER_AGENT"))
    url = "https://prod.trackmania.core.nadeo.online/zones/"
    headers = {
        "Authorization": "nadeo_v1 t=" + NADEO_ACCESS_TOKEN,
        "User-Agent": USER_AGENT,
    }
    res = requests.get(url, headers=headers)
    res = res.json()
    logger.info("Зоны надео получены")
    return res


def get_country(data, zone_id):
    current_id = zone_id
    zones = [current_id]

    while True:
        # Ищем элемент с текущим zone_id
        found = None
        for item in data:
            if item["zoneId"] == current_id:
                found = item
                break

        if not found:
            break

        parent_id = found["parentId"]
        zones.append(parent_id)
        current_id = parent_id

    # Если в цепочке меньше 2 элементов, вернуть None
    if len(zones) < 4:
        return None

    # Берём предпоследний parentId
    country_zone = zones[-4]

    # Ищем icon для этого parentId
    for item in data:
        if item["zoneId"] == country_zone:
            logger.info("Страна получена")
            return item["name"].strip().lower()

    return None


def country_to_flag_iso(country_name):
    try:
        # Ищем по официальному названию
        country = pycountry.countries.search_fuzzy(country_name)
        if country:
            logger.info("Страна найдена в iso")
            return f":flag_{country[0].alpha_2.lower()}:"
    except:
        logger.warning("Такой страны нет")
        return ":globe_with_meridians:"


def get_player_flag(zone_id, nadeo_zones):
    try:
        country = get_country(nadeo_zones, zone_id)
        return country_to_flag_iso(country)
    except Exception as e:
        logger.error(f"Флаг не был получен. Ошибка: {e}")
