from __future__ import annotations

import json
import logging
import time
from functools import wraps

import pycountry
import requests

from src.auth.auth import check_token_refresh
from src.db.database import db
from src.utils.config import get_env_key

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = (3.05, 30)

# Зоны меняются редко, а ответ весит ~2 МБ — держим их в кеше неделю.
ZONES_CACHE_TTL_HOURS = 24 * 7
ZONES_CACHE_KEY = "nadeo_zones"
# После неудачного запроса не долбим API какое-то время (флаги берём из кеша).
ZONES_RETRY_COOLDOWN = 10 * 60
ZONES_TIMEOUT = (5, 10)

# Кеш в памяти процесса: список зон и время последней неудачи.
_zones_memo: list[dict] | None = None
_zones_failed_at: float | None = None


def retry_on_error(max_retries=10, delay=2, backoff=2):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            current_delay = delay

            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except requests.exceptions.Timeout:
                    retries += 1
                    logger.warning(
                        f"Таймаут запроса в {func.__name__}. Попытка {retries}/{max_retries}"
                    )
                    if retries >= max_retries:
                        raise
                    time.sleep(current_delay)
                    current_delay *= backoff
                except requests.exceptions.SSLError as e:
                    retries += 1
                    logger.warning(
                        f"SSL ошибка в {func.__name__}: {e}. Попытка {retries}/{max_retries}"
                    )
                    if retries >= max_retries:
                        raise
                    time.sleep(current_delay)
                    current_delay *= backoff
                except requests.exceptions.ConnectionError:
                    retries += 1
                    logger.warning(
                        f"Ошибка соединения в {func.__name__}. Попытка {retries}/{max_retries}"
                    )
                    if retries >= max_retries:
                        raise
                    time.sleep(current_delay)
                    current_delay *= backoff
                except Exception as e:
                    retries += 1
                    if retries >= max_retries:
                        logger.error(
                            f"Функция {func.__name__} не сработала после {max_retries} попыток. Ошибка: {e}"
                        )
                        raise

                    logger.warning(
                        f"Попытка {retries}/{max_retries} не удалась в {func.__name__}. Ошибка: {e}. Повтор через {current_delay} сек..."
                    )
                    time.sleep(current_delay)
                    current_delay *= backoff

            return None

        return wrapper

    return decorator


@retry_on_error()
def get_map_records(map_uid: str, length: int, offset: int) -> list:
    check_token_refresh()
    NADEO_LIVESERVICES_ACCESS_TOKEN = get_env_key("NADEO_LIVESERVICES_ACCESS_TOKEN")
    USER_AGENT = get_env_key("USER_AGENT")

    url = f"https://live-services.trackmania.nadeo.live/api/token/leaderboard/group/Personal_Best/map/{map_uid}/top?length=100&onlyWorld=1&offset={offset}"
    headers = {
        "Authorization": "nadeo_v1 t=" + NADEO_LIVESERVICES_ACCESS_TOKEN,
        "User-Agent": USER_AGENT,
    }

    res = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
    res = res.json()
    logger.info(f"Рекорды получены: {map_uid}")
    # time.sleep(0.5)
    return res["tops"][0]["top"]


@retry_on_error()
def get_account_name(uids: list[str]) -> dict[str, str]:
    check_token_refresh()
    OAUTH_TOKEN = get_env_key("OAUTH_TOKEN")
    USER_AGENT = get_env_key("USER_AGENT")

    url = "https://api.trackmania.com/api/display-names?"
    for uid in uids:
        url += "&accountId[]=" + uid
    headers = {"Authorization": f"Bearer {OAUTH_TOKEN}", "User-Agent": USER_AGENT}

    res = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
    res = res.json()
    # time.sleep(0.5)
    return res


def split_list(input_list: list, chunk_size: int) -> list[list]:
    return [
        input_list[i : i + chunk_size] for i in range(0, len(input_list), chunk_size)
    ]


@retry_on_error()
def id_to_records(map_uid: str) -> list[dict]:
    current_records = []
    stop = False
    offset = 0
    while not stop:
        map_records = get_map_records(map_uid, 100, offset)
        current_records.extend(map_records)
        # print(len(map_records))
        if len(map_records) < 100 or offset >= 9900:
            stop = True
        time.sleep(0.5)
        offset += 100
    logger.info(f"{len(current_records)} Рекордов получено")
    return current_records


def ids_to_nicknames(uids: list[str]) -> dict[str, str]:
    ids_splited = split_list(uids, 50)
    # print(ids_splited)
    current_nicknames = {}
    for ids_list in ids_splited:
        # get_account_name(ids_list)
        current_nicknames.update(get_account_name(ids_list))
    logger.info("Никнеймы получены")
    return current_nicknames


def number_to_time(number: int) -> str:
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
def get_maps_info(map_uids: list[str]) -> dict[str, any]:
    check_token_refresh()
    NADEO_ACCESS_TOKEN = get_env_key("NADEO_ACCESS_TOKEN")
    USER_AGENT = get_env_key("USER_AGENT")
    url = f"https://prod.trackmania.core.nadeo.online/maps/?mapUidList={','.join(map_uids)}"

    headers = {
        "Authorization": "nadeo_v1 t=" + NADEO_ACCESS_TOKEN,
        "User-Agent": USER_AGENT,
    }
    res = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
    res = res.json()
    return res


@retry_on_error()
def get_campaign(campaign_id: int) -> dict:
    check_token_refresh()
    NADEO_LIVESERVICES_ACCESS_TOKEN = get_env_key("NADEO_LIVESERVICES_ACCESS_TOKEN")
    USER_AGENT = get_env_key("USER_AGENT")
    url = f"https://live-services.trackmania.nadeo.live/api/token/club/52818/campaign/{campaign_id}"
    headers = {
        "Authorization": "nadeo_v1 t=" + NADEO_LIVESERVICES_ACCESS_TOKEN,
        "User-Agent": USER_AGENT,
    }
    res = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
    res = res.json()
    return res["campaign"]


@retry_on_error()
def get_campaigns(offset: int, name: str) -> dict:
    check_token_refresh()
    NADEO_LIVESERVICES_ACCESS_TOKEN = get_env_key("NADEO_LIVESERVICES_ACCESS_TOKEN")
    USER_AGENT = get_env_key("USER_AGENT")
    url = f"https://live-services.trackmania.nadeo.live/api/token/club/52818/activity?length=200&offset={offset}&active=true"
    headers = {
        "Authorization": "nadeo_v1 t=" + NADEO_LIVESERVICES_ACCESS_TOKEN,
        "User-Agent": USER_AGENT,
    }
    res = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
    res = res.json()
    return res


@retry_on_error()
def get_map_playercount(map_uid: str) -> int:
    check_token_refresh()
    NADEO_LIVESERVICES_ACCESS_TOKEN = get_env_key("NADEO_LIVESERVICES_ACCESS_TOKEN")
    USER_ID = get_env_key("USER_ID")
    USER_AGENT = get_env_key("USER_AGENT")
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

    res = requests.get(complete_url, headers=headers, timeout=REQUEST_TIMEOUT)
    res = res.json()

    scores = res["tops"][0]["top"]
    if scores[0]["accountId"] == USER_ID:
        return 0

    # last score on leaderboard has playercount position
    playercount = scores[0]["position"]

    return playercount


@retry_on_error(max_retries=2, delay=2, backoff=2)
def _fetch_nadeo_zones() -> list[dict]:
    """Один поход в API за зонами (тяжёлый ответ, поэтому с короткими ретраями)."""
    check_token_refresh()
    NADEO_ACCESS_TOKEN = get_env_key("NADEO_ACCESS_TOKEN")
    USER_AGENT = get_env_key("USER_AGENT")
    url = "https://prod.trackmania.core.nadeo.online/zones/"
    headers = {
        "Authorization": "nadeo_v1 t=" + NADEO_ACCESS_TOKEN,
        "User-Agent": USER_AGENT,
    }
    res = requests.get(url, headers=headers, timeout=ZONES_TIMEOUT)
    res.raise_for_status()
    res = res.json()
    logger.info("Зоны надео получены")
    return res


def _load_zones_cache(*, ignore_ttl: bool = False) -> list[dict] | None:
    """Зоны из БД. None — если записи нет, она битая или устарела."""
    try:
        row = db.get_cache(ZONES_CACHE_KEY)
    except Exception as exc:
        logger.warning(f"Кеш зон не читается: {exc}")
        return None
    if row is None:
        return None

    value, saved_at = row
    try:
        zones = json.loads(value)
    except ValueError as exc:
        logger.warning(f"Кеш зон битый: {exc}")
        return None

    if not isinstance(zones, list) or not zones:
        return None

    if not ignore_ttl:
        age_hours = (time.time() - float(saved_at)) / 3600
        if age_hours > ZONES_CACHE_TTL_HOURS:
            logger.info(f"Кеш зон устарел ({age_hours:.0f} ч) — обновляю")
            return None

    return zones


def _save_zones_cache(zones: list[dict]) -> None:
    """Пишет зоны в БД."""
    try:
        db.set_cache(
            ZONES_CACHE_KEY,
            json.dumps(zones, ensure_ascii=False),
            int(time.time()),
        )
    except Exception as exc:
        logger.warning(f"Кеш зон не сохранился: {exc}")


def _zones_cooldown_active() -> bool:
    return bool(
        _zones_failed_at
        and time.time() - _zones_failed_at < ZONES_RETRY_COOLDOWN
    )


def get_nadeo_zones(force_refresh: bool = False) -> list[dict]:
    """Зоны надео: память → кеш в БД → API.

    Сетевые ошибки не должны ломать отправку уведомления, поэтому при неудаче
    отдаём устаревший кеш, а если его нет — пустой список (флаги не рисуются).
    """
    global _zones_memo, _zones_failed_at

    if _zones_memo is not None and not force_refresh:
        return _zones_memo

    if not force_refresh:
        cached = _load_zones_cache()
        if cached:
            _zones_memo = cached
            return cached

        if _zones_cooldown_active():
            logger.info("Зоны надео: недавняя неудача, запрос пропускаю")
            return _load_zones_cache(ignore_ttl=True) or []

    try:
        zones = _fetch_nadeo_zones()
    except Exception as exc:
        _zones_failed_at = time.time()
        stale = _load_zones_cache(ignore_ttl=True)
        if stale:
            _zones_memo = stale
        logger.warning(
            f"Зоны надео не получены ({exc}); "
            f"флаги: {'из кеша' if stale else 'скрыты'}"
        )
        return stale or []

    _zones_failed_at = None
    _zones_memo = zones
    _save_zones_cache(zones)
    return zones


def get_country(data: list[dict], zone_id: int) -> str | None:
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


def apply_nicknames(records: list[dict]) -> list[dict]:
    nicknames = ids_to_nicknames([item["accountId"] for item in records])
    for record in records:
        account_id = record["accountId"]
        if account_id in nicknames:
            record["name"] = nicknames[account_id]
    return records


def country_to_flag_iso(country_name: str) -> str:
    try:
        # Ищем по официальному названию
        country = pycountry.countries.search_fuzzy(country_name)
        if country:
            logger.info("Страна найдена в iso")
            return f":flag_{country[0].alpha_2.lower()}:"
    except:
        logger.warning("Такой страны нет")
        return ":globe_with_meridians:"


def get_player_flag(zone_id: int, nadeo_zones: list[dict]) -> str:
    try:
        country = get_country(nadeo_zones, zone_id)
        return country_to_flag_iso(country)
    except Exception as e:
        logger.error(f"Флаг не был получен. Ошибка: {e}")
        return ""


# --------------------------------------------------------- флаги через tm.io
# Запасной путь: /zones/ иногда отвечает по 30+ секунд или не отвечает вовсе,
# тогда страну игрока берём напрямую из trackmania.io по его accountId.

TMIO_PLAYER_URL = "https://trackmania.io/api/player/{account_id}"
TMIO_FLAGS_CACHE_TTL_HOURS = 24 * 30
TMIO_FLAGS_CACHE_KEY = "tmio_flags"
TMIO_RETRY_COOLDOWN = 10 * 60
TMIO_TIMEOUT = (5, 10)

_tmio_flags_memo: dict[str, str] = {}
_tmio_flags_loaded = False
_tmio_flags_failed_at: float | None = None


def _load_tmio_flags_cache() -> dict[str, str]:
    """accountId → код страны из прошлых запросов (пусто, если кеш устарел)."""
    try:
        row = db.get_cache(TMIO_FLAGS_CACHE_KEY)
    except Exception as exc:
        logger.warning(f"Кеш флагов не читается: {exc}")
        return {}
    if row is None:
        return {}

    value, saved_at = row
    age_hours = (time.time() - float(saved_at)) / 3600
    if age_hours > TMIO_FLAGS_CACHE_TTL_HOURS:
        return {}

    try:
        flags = json.loads(value)
    except ValueError:
        return {}
    if not isinstance(flags, dict):
        return {}
    return {str(key): str(val) for key, val in flags.items()}


def _save_tmio_flags_cache() -> None:
    try:
        db.set_cache(
            TMIO_FLAGS_CACHE_KEY,
            json.dumps(_tmio_flags_memo, ensure_ascii=False),
            int(time.time()),
        )
    except Exception as exc:
        logger.warning(f"Кеш флагов не сохранился: {exc}")


@retry_on_error(max_retries=1, delay=1, backoff=1)
def _fetch_tmio_flag(account_id: str) -> str:
    """Код страны игрока из trackmania.io ('ARG'); '' — если его там нет."""
    USER_AGENT = get_env_key("USER_AGENT")
    url = TMIO_PLAYER_URL.format(account_id=account_id)
    res = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=TMIO_TIMEOUT)
    res.raise_for_status()
    payload = res.json() or {}

    for zone in (payload.get("zone"), (payload.get("trophies") or {}).get("zone")):
        if isinstance(zone, dict) and zone.get("flag"):
            return str(zone["flag"])
    return ""


def flag_code_to_emoji(code: str) -> str:
    """'ARG' / 'ar' → ':flag_ar:'; регионы и мусор ('WOR') → глобус."""
    code = (code or "").strip().upper()
    if len(code) == 3:
        country = pycountry.countries.get(alpha_3=code)
    elif len(code) == 2:
        country = pycountry.countries.get(alpha_2=code)
    else:
        country = None

    if country is None:
        return ":globe_with_meridians:"
    return f":flag_{country.alpha_2.lower()}:"


def get_flag_by_account(account_id: str) -> str:
    """Флаг по accountId через trackmania.io (память → кеш → API)."""
    global _tmio_flags_loaded, _tmio_flags_failed_at

    account_id = (account_id or "").strip()
    if not account_id:
        return ""

    if not _tmio_flags_loaded:
        _tmio_flags_memo.update(_load_tmio_flags_cache())
        _tmio_flags_loaded = True

    if account_id in _tmio_flags_memo:
        return flag_code_to_emoji(_tmio_flags_memo[account_id])

    if (
        _tmio_flags_failed_at
        and time.time() - _tmio_flags_failed_at < TMIO_RETRY_COOLDOWN
    ):
        return ""

    try:
        code = _fetch_tmio_flag(account_id)
    except Exception as exc:
        _tmio_flags_failed_at = time.time()
        logger.warning(f"Флаг из trackmania.io не получен ({account_id}): {exc}")
        return ""

    _tmio_flags_failed_at = None
    _tmio_flags_memo[account_id] = code
    _save_tmio_flags_cache()
    return flag_code_to_emoji(code)
