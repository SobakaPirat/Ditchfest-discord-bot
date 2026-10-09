from types import SimpleNamespace
from unittest.mock import patch

import pytest

from src.utils.embed_template import post_all_discords, post_record

WEBHOOK_URL = "https://discord.com/api/webhooks/1/test"
TIMESTAMP = 1690000000

MAP = {
    "map_name": "Test Map",
    "map_uid": "uid_1",
    "map_author_name": "Author",
    "map_thumbnail": "https://thumb.example/map.png",
}

ZONES = [{"zoneId": 100, "parentId": 10, "name": "World"}]


def make_records(scores=(100000, 100500, 101000)):
    return [
        {"name": f"Player{i + 1}", "score": score, "zoneId": 100 + i}
        for i, score in enumerate(scores)
    ]


def get_field(embed, name):
    for field in embed.fields:
        if field["name"] == name:
            return field
    return None


@pytest.fixture
def no_sleep(monkeypatch):
    """Отключаем sleep: post_record обёрнут в retry_on_error (retries со sleep 2s+)."""
    monkeypatch.setattr("src.utils.helpers.time.sleep", lambda *args, **kwargs: None)


@pytest.fixture
def post(no_sleep):
    """Хелпер: прогоняет post_record с моками и возвращает результат."""

    def _post(map=None, records=None, timestamp=None):
        with (
            patch("src.utils.embed_template.DiscordWebhook") as mock_webhook_cls,
            patch(
                "src.utils.embed_template.get_nadeo_zones", return_value=ZONES
            ) as mock_zones,
            patch(
                "src.utils.embed_template.get_player_flag", return_value=":flag_ru:"
            ) as mock_flag,
        ):
            post_record(
                WEBHOOK_URL,
                MAP if map is None else map,
                timestamp,
                make_records() if records is None else records,
            )

        webhook = mock_webhook_cls.return_value
        webhook.add_embed.assert_called_once()
        return SimpleNamespace(
            embed=webhook.add_embed.call_args[0][0],
            webhook=webhook,
            webhook_cls=mock_webhook_cls,
            flag=mock_flag,
            zones=mock_zones,
        )

    return _post


# ------------------------------------------------------------------
# post_record: webhook

def test_post_record_creates_webhook_and_executes(post):
    result = post()
    result.webhook_cls.assert_called_once_with(url=WEBHOOK_URL, timeout=5)
    result.webhook.execute.assert_called_once()


# ------------------------------------------------------------------
# post_record: embed

def test_embed_header(post):
    embed = post().embed
    assert embed.title == "Test Map"
    assert embed.url == "https://trackmania.io/#/leaderboard/uid_1"
    assert embed.description == (
        "Author\n\n:checkered_flag: New World Record!"
    )
    assert embed.color == 0xFFE500


def test_embed_timestamp_is_moscow_time(post):
    assert post().embed.timestamp.endswith("+03:00")


def test_record_holder_field_lists_top_3(post):
    result = post()
    field = get_field(result.embed, "Record Holder")
    assert field["value"] == (
        ":first_place: :flag_ru: Player1\n"
        ":second_place: :flag_ru: Player2\n"
        ":third_place: :flag_ru: Player3\n"
    )
    assert field["inline"] is True
    assert [c.args for c in result.flag.call_args_list] == [
        (100, ZONES),
        (101, ZONES),
        (102, ZONES),
    ]
    result.zones.assert_called_once_with()


def test_time_field_shows_gaps_between_places(post):
    field = get_field(post().embed, "Time")
    assert field["value"] == (
        "1:40.000\n"
        "1:40.500 (+0.500)\n"
        "1:41.000 (+1.000)\n"
    )
    assert field["inline"] is True


def test_negative_score_shows_secret_instead_of_time(post):
    records = make_records(scores=(-1, -2, -3))
    field = get_field(post(records=records).embed, "Time")
    assert field["value"] == "-# Secret\n" * 3
    assert field["inline"] is True


def test_negative_score_with_fewer_records_shows_secret(post):
    records = make_records(scores=(-1, -2))
    field = get_field(post(records=records).embed, "Time")
    assert field["value"] == "-# Secret\n" * 2


def test_fewer_than_three_records(post):
    result = post(records=make_records()[:2])
    holder = get_field(result.embed, "Record Holder")
    assert holder["value"] == (
        ":first_place: :flag_ru: Player1\n"
        ":second_place: :flag_ru: Player2\n"
    )
    time_field = get_field(result.embed, "Time")
    assert time_field["value"] == "1:40.000\n1:40.500 (+0.500)\n"
    assert result.flag.call_count == 2


def test_timestamp_field_added(post):
    field = get_field(post(timestamp=TIMESTAMP).embed, "")
    assert field["value"] == (
        f"The previous world record has been set <t:{TIMESTAMP}:R>"
    )
    assert field["inline"] is False


def test_no_timestamp_field_when_timestamp_is_none(post):
    assert get_field(post(timestamp=None).embed, "") is None


def test_thumbnail_and_footer(post):
    embed = post().embed
    assert embed.thumbnail["url"] == MAP["map_thumbnail"]
    assert embed.footer["text"] == "by Soba"
    assert embed.footer["icon_url"].startswith("https://")


# ------------------------------------------------------------------
# post_all_discords

def test_post_all_discords_passes_webhook_url_from_env():
    records = make_records()
    with (
        patch(
            "src.utils.embed_template.get_env_key", return_value=WEBHOOK_URL
        ) as mock_get_env,
        patch("src.utils.embed_template.post_record") as mock_post_record,
    ):
        post_all_discords(MAP, records, TIMESTAMP)

    mock_get_env.assert_called_once_with("WEBHOOKS_URL")
    mock_post_record.assert_called_once_with(WEBHOOK_URL, MAP, TIMESTAMP, records)


def test_post_all_discords_defaults_timestamp_to_none():
    records = make_records()
    with (
        patch("src.utils.embed_template.get_env_key", return_value=WEBHOOK_URL),
        patch("src.utils.embed_template.post_record") as mock_post_record,
    ):
        post_all_discords(MAP, records)

    mock_post_record.assert_called_once_with(WEBHOOK_URL, MAP, None, records)
