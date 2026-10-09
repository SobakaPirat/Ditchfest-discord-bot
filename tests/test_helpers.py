from types import SimpleNamespace
from unittest.mock import patch

import pytest
import requests

from src.utils.helpers import (
    REQUEST_TIMEOUT,
    apply_nicknames,
    country_to_flag_iso,
    get_account_name,
    get_campaign,
    get_campaigns,
    get_country,
    get_map_playercount,
    get_map_records,
    get_maps_info,
    get_nadeo_zones,
    get_player_flag,
    id_to_records,
    ids_to_nicknames,
    number_to_time,
    retry_on_error,
    split_list,
)

ENV_KEYS = {
    "NADEO_ACCESS_TOKEN": "nadeo_token",
    "NADEO_LIVESERVICES_ACCESS_TOKEN": "live_token",
    "OAUTH_TOKEN": "oauth_token",
    "USER_AGENT": "test-agent",
    "USER_ID": "my_uid",
}

ZONES = [
    {"zoneId": 100, "parentId": 10, "name": "MapZone"},
    {"zoneId": 10, "parentId": 5, "name": "  Russia "},
    {"zoneId": 5, "parentId": 1, "name": "Continent"},
    {"zoneId": 1, "parentId": 0, "name": "World"},
]


@pytest.fixture(autouse=True)
def sleep_log(monkeypatch):
    """Отключаем реальные sleep (retry_on_error / пагинация) и логируем их."""
    log = []
    monkeypatch.setattr("src.utils.helpers.time.sleep", lambda *args: log.append(args))
    return log


@pytest.fixture
def api():
    """Мокает сетевые вызовы и чтение .env внутри helpers."""
    with (
        patch("src.utils.helpers.check_token_refresh") as mock_refresh,
        patch("src.utils.helpers.requests.get") as mock_get,
        patch(
            "src.utils.helpers.get_env_key", side_effect=lambda key: ENV_KEYS.get(key)
        ),
    ):
        mock_get.return_value.json.return_value = {}
        yield SimpleNamespace(get=mock_get, refresh=mock_refresh)


# ------------------------------------------------------------------
# split_list

def test_split_list_even_chunks():
    assert split_list([1, 2, 3, 4], 2) == [[1, 2], [3, 4]]


def test_split_list_with_remainder():
    assert split_list(list(range(5)), 2) == [[0, 1], [2, 3], [4]]


def test_split_list_empty():
    assert split_list([], 10) == []


def test_split_list_chunk_bigger_than_list():
    assert split_list([1, 2, 3], 10) == [[1, 2, 3]]


# ------------------------------------------------------------------
# number_to_time

@pytest.mark.parametrize(
    ("score", "expected"),
    [
        (-1, "secret"),
        (0, "0.000"),
        (500, "0.500"),
        (1000, "1.000"),
        (59000, "59.000"),
        (60000, "1:00.000"),
        (100000, "1:40.000"),
        (3600000, "1:00:00.000"),
        (3661000, "1:01:01.000"),
    ],
)
def test_number_to_time(score, expected):
    assert number_to_time(score) == expected


# ------------------------------------------------------------------
# get_country

def test_get_country_returns_country_from_parent_chain():
    assert get_country(ZONES, 100) == "russia"


def test_get_country_returns_none_when_chain_too_short():
    short = [
        {"zoneId": 100, "parentId": 10, "name": "MapZone"},
        {"zoneId": 10, "parentId": 1, "name": "Russia"},
    ]
    assert get_country(short, 100) is None


def test_get_country_returns_none_for_unknown_zone():
    assert get_country(ZONES, 999) is None


# ------------------------------------------------------------------
# country_to_flag_iso

def test_country_to_flag_iso_known_countries():
    assert country_to_flag_iso("Russia") == ":flag_ru:"
    assert country_to_flag_iso("Germany") == ":flag_de:"


def test_country_to_flag_iso_unknown_name_returns_globe():
    assert country_to_flag_iso("zzzz not a country zzzz") == ":globe_with_meridians:"


def test_country_to_flag_iso_none_returns_globe():
    assert country_to_flag_iso(None) == ":globe_with_meridians:"


# ------------------------------------------------------------------
# get_player_flag

def test_get_player_flag_returns_flag():
    assert get_player_flag(100, ZONES) == ":flag_ru:"


def test_get_player_flag_unknown_zone_returns_globe():
    assert get_player_flag(999, ZONES) == ":globe_with_meridians:"


def test_get_player_flag_malformed_zones_returns_empty_string():
    assert get_player_flag(100, [{"name": "no zoneId"}]) == ""


# ------------------------------------------------------------------
# retry_on_error

def test_retry_returns_on_first_success(sleep_log):
    calls = []

    @retry_on_error(max_retries=3, delay=1, backoff=2)
    def ok():
        calls.append(1)
        return "done"

    assert ok() == "done"
    assert len(calls) == 1
    assert sleep_log == []


def test_retry_retries_generic_error_then_succeeds(sleep_log):
    attempts = {"count": 0}

    @retry_on_error(max_retries=3, delay=1, backoff=2)
    def flaky():
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise ValueError("boom")
        return "ok"

    assert flaky() == "ok"
    assert attempts["count"] == 3
    assert sleep_log == [(1,), (2,)]


def test_retry_raises_after_max_retries(sleep_log):
    attempts = []

    @retry_on_error(max_retries=3, delay=1, backoff=2)
    def always_fails():
        attempts.append(1)
        raise ValueError("boom")

    with pytest.raises(ValueError, match="boom"):
        always_fails()
    assert len(attempts) == 3
    assert sleep_log == [(1,), (2,)]


def test_retry_raises_after_max_retries_for_ssl_error(sleep_log):
    attempts = []

    @retry_on_error(max_retries=3, delay=1, backoff=2)
    def always_fails():
        attempts.append(1)
        raise requests.exceptions.SSLError("boom")

    with pytest.raises(requests.exceptions.SSLError, match="boom"):
        always_fails()
    assert len(attempts) == 3
    assert sleep_log == [(1,), (2,)]


@pytest.mark.parametrize(
    "exc",
    [
        requests.exceptions.Timeout("timeout"),
        requests.exceptions.ConnectionError("connection"),
        requests.exceptions.SSLError("ssl"),
    ],
)
def test_retry_recovers_from_request_errors(exc, sleep_log):
    attempts = {"count": 0}

    @retry_on_error(max_retries=3, delay=1, backoff=2)
    def flaky():
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise exc
        return "ok"

    assert flaky() == "ok"
    assert attempts["count"] == 2


# ------------------------------------------------------------------
# get_map_records

def test_get_map_records_returns_top(api):
    top = [{"accountId": "a", "score": 1}, {"accountId": "b", "score": 2}]
    api.get.return_value.json.return_value = {"tops": [{"top": top}]}

    result = get_map_records("uid_1", 100, 200)

    assert result == top
    api.refresh.assert_called_once_with()
    url = api.get.call_args.args[0]
    assert url.endswith("map/uid_1/top?length=100&onlyWorld=1&offset=200")
    assert api.get.call_args.kwargs["headers"] == {
        "Authorization": "nadeo_v1 t=live_token",
        "User-Agent": "test-agent",
    }
    assert api.get.call_args.kwargs["timeout"] == REQUEST_TIMEOUT


def test_get_map_records_url_ignores_length_argument(api):
    api.get.return_value.json.return_value = {"tops": [{"top": []}]}
    get_map_records("uid_1", 50, 0)
    # параметр length в URL захардкожен на 100
    assert "length=100" in api.get.call_args.args[0]


# ------------------------------------------------------------------
# get_account_name

def test_get_account_name_builds_url_and_returns_map(api):
    expected = {"uid1": "Player One", "uid2": "Player Two"}
    api.get.return_value.json.return_value = expected

    result = get_account_name(["uid1", "uid2"])

    assert result == expected
    url = api.get.call_args.args[0]
    assert url.startswith("https://api.trackmania.com/api/display-names?")
    assert "&accountId[]=uid1" in url
    assert "&accountId[]=uid2" in url
    assert api.get.call_args.kwargs["headers"] == {
        "Authorization": "Bearer oauth_token",
        "User-Agent": "test-agent",
    }


# ------------------------------------------------------------------
# get_maps_info / get_campaign / get_campaigns / get_nadeo_zones

def test_get_maps_info_joins_map_uids(api):
    expected = [{"uid": "uid1"}, {"uid": "uid2"}]
    api.get.return_value.json.return_value = expected

    assert get_maps_info(["uid1", "uid2"]) == expected
    assert "mapUidList=uid1,uid2" in api.get.call_args.args[0]
    headers = api.get.call_args.kwargs["headers"]
    assert headers["Authorization"] == "nadeo_v1 t=nadeo_token"


def test_get_campaign_returns_campaign(api):
    api.get.return_value.json.return_value = {"campaign": {"id": 5}}

    assert get_campaign(5) == {"id": 5}
    assert api.get.call_args.args[0].endswith("/campaign/5")


def test_get_campaigns_returns_response_with_offset(api):
    expected = {"next": []}
    api.get.return_value.json.return_value = expected

    assert get_campaigns(offset=100, name="Some name") == expected
    url = api.get.call_args.args[0]
    assert "offset=100" in url
    assert "active=true" in url


def test_get_nadeo_zones_returns_zones(api):
    expected = [{"zoneId": 1, "parentId": 0, "name": "World"}]
    api.get.return_value.json.return_value = expected

    assert get_nadeo_zones() == expected
    assert api.get.call_args.args[0].endswith("/zones/")
    api.refresh.assert_called_once_with()


# ------------------------------------------------------------------
# get_map_playercount

def test_get_map_playercount_returns_position(api):
    api.get.return_value.json.return_value = {
        "tops": [{"top": [{"accountId": "someone_else", "position": 42}]}]
    }

    assert get_map_playercount("uid_1") == 42
    url = api.get.call_args.args[0]
    assert "/map/uid_1/surround/1/1?score=1000000000" in url


def test_get_map_playercount_returns_zero_when_user_is_on_top(api):
    api.get.return_value.json.return_value = {
        "tops": [{"top": [{"accountId": "my_uid", "position": 1}]}]
    }

    assert get_map_playercount("uid_1") == 0


# ------------------------------------------------------------------
# id_to_records / ids_to_nicknames

def test_id_to_records_single_page():
    records = [{"score": 1}, {"score": 2}]
    with patch(
        "src.utils.helpers.get_map_records", return_value=records
    ) as mock_fetch:
        assert id_to_records("uid_1") == records
    mock_fetch.assert_called_once_with("uid_1", 100, 0)


def test_id_to_records_paginates_until_short_page():
    page1 = [{"i": i} for i in range(100)]
    page2 = [{"i": i} for i in range(50)]
    with patch(
        "src.utils.helpers.get_map_records", side_effect=[page1, page2]
    ) as mock_fetch:
        result = id_to_records("uid_1")

    assert len(result) == 150
    assert [c.args for c in mock_fetch.call_args_list] == [
        ("uid_1", 100, 0),
        ("uid_1", 100, 100),
    ]


def test_ids_to_nicknames_batches_by_50_and_merges():
    uids = [f"uid{i}" for i in range(120)]

    def fake_account_name(names):
        return {uid: f"name_{uid}" for uid in names}

    with patch(
        "src.utils.helpers.get_account_name", side_effect=fake_account_name
    ) as mock_names:
        result = ids_to_nicknames(uids)

    assert len(result) == 120
    assert result["uid0"] == "name_uid0"
    assert result["uid119"] == "name_uid119"
    assert [len(c.args[0]) for c in mock_names.call_args_list] == [50, 50, 20]


# ------------------------------------------------------------------
# apply_nicknames

def test_apply_nicknames_applies_nicknames_for_each_record():
    records = [{"accountId": "acc1", "name": "raw1"}, {"accountId": "acc2", "name": "raw2"}]
    with patch(
        "src.utils.helpers.ids_to_nicknames",
        return_value={"acc1": "Nick1", "acc2": "Nick2"},
    ) as mock_nicknames:
        result = apply_nicknames(records)

    # ники запрошены один раз по всем аккаунтам
    mock_nicknames.assert_called_once_with(["acc1", "acc2"])
    assert result == [
        {"accountId": "acc1", "name": "Nick1"},
        {"accountId": "acc2", "name": "Nick2"},
    ]


def test_apply_nicknames_keeps_raw_name_without_nickname():
    records = [{"accountId": "acc1", "name": "raw1"}, {"accountId": "acc2", "name": "raw2"}]
    with patch(
        "src.utils.helpers.ids_to_nicknames", return_value={"acc1": "Nick1"}
    ):
        result = apply_nicknames(records)

    assert result[0]["name"] == "Nick1"
    assert result[1]["name"] == "raw2"


def test_apply_nicknames_empty_list():
    with patch("src.utils.helpers.ids_to_nicknames", return_value={}) as mock_nicknames:
        assert apply_nicknames([]) == []
    # пустой список всё равно уходит в ids_to_nicknames (тот вернёт {} без сети)
    mock_nicknames.assert_called_once_with([])


def test_apply_nicknames_same_account_id_repeated():
    records = [
        {"accountId": "acc1", "name": "raw1"},
        {"accountId": "acc1", "name": "raw1"},
    ]
    with patch(
        "src.utils.helpers.ids_to_nicknames", return_value={"acc1": "Nick1"}
    ):
        result = apply_nicknames(records)

    assert [r["name"] for r in result] == ["Nick1", "Nick1"]


def test_apply_nicknames_preserves_other_fields():
    records = [
        {"accountId": "acc1", "name": "raw1", "score": 42000, "position": 1},
        {"accountId": "acc2", "name": "raw2", "score": 43000, "position": 2},
    ]
    with patch(
        "src.utils.helpers.ids_to_nicknames",
        return_value={"acc1": "Nick1", "acc2": "Nick2"},
    ):
        result = apply_nicknames(records)

    assert result == [
        {"accountId": "acc1", "name": "Nick1", "score": 42000, "position": 1},
        {"accountId": "acc2", "name": "Nick2", "score": 43000, "position": 2},
    ]


def test_apply_nicknames_returns_same_list_object():
    records = [{"accountId": "acc1", "name": "raw1"}]
    with patch(
        "src.utils.helpers.ids_to_nicknames", return_value={"acc1": "Nick1"}
    ):
        result = apply_nicknames(records)

    # мутирует на месте и возвращает тот же объект
    assert result is records
    assert records[0]["name"] == "Nick1"


def test_apply_nicknames_without_name_key():
    # запись без ключа name — ник просто добавляется
    records = [{"accountId": "acc1", "score": 42000}]
    with patch(
        "src.utils.helpers.ids_to_nicknames", return_value={"acc1": "Nick1"}
    ):
        result = apply_nicknames(records)

    assert result[0]["name"] == "Nick1"


