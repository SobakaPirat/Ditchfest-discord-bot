from types import SimpleNamespace
from unittest.mock import call, patch

import pytest

from src.updaters.maps_updater import (
    fetch_campaign,
    get_new_maps,
    update_maps,
    update_nicknames,
    update_playercounts,
)


def activity(campaign_ids):
    return {"activityList": [{"campaignId": cid} for cid in campaign_ids]}


def campaign(campaign_id, map_uids, name="Campaign"):
    return {
        "publicationTimestamp": 1700000000,
        "name": name,
        "playlist": [{"mapUid": uid} for uid in map_uids],
    }


def map_info(uid, filename="Track.Map.Gbx", map_type="Race"):
    return {
        "mapUid": uid,
        "thumbnailUrl": f"https://thumb/{uid}.png",
        "timestamp": "2024-05-17T12:34:56.000Z",
        "filename": filename,
        "author": f"author_{uid}",
        "authorScore": 100000,
        "goldScore": 110000,
        "silverScore": 120000,
        "bronzeScore": 130000,
        "mapType": map_type,
    }


@pytest.fixture
def db_mock():
    with patch("src.updaters.maps_updater.db") as mock_db:
        yield mock_db


@pytest.fixture
def network():
    with (
        patch("src.updaters.maps_updater.get_campaigns") as mock_get_campaigns,
        patch("src.updaters.maps_updater.get_campaign") as mock_get_campaign,
        patch("src.updaters.maps_updater.get_maps_info") as mock_get_maps_info,
    ):
        yield SimpleNamespace(
            get_campaigns=mock_get_campaigns,
            get_campaign=mock_get_campaign,
            get_maps_info=mock_get_maps_info,
        )


# ------------------------------------------------------------------
# fetch_campaign

def test_fetch_campaign_takes_first_valid_campaign(network):
    network.get_campaigns.return_value = activity([0, 100, 200])
    network.get_campaign.return_value = campaign(100, ["uid_a", "uid_b"])
    network.get_maps_info.return_value = [map_info("uid_a"), map_info("uid_b")]

    result = fetch_campaign()

    network.get_campaigns.assert_called_once_with("0", "DitchFest")
    network.get_campaign.assert_called_once_with(100)
    network.get_maps_info.assert_called_once_with(["uid_a", "uid_b"])
    assert [m["map_uid"] for m in result] == ["uid_a", "uid_b"]


def test_fetch_campaign_all_campaigns_processes_everything(network):
    network.get_campaigns.return_value = activity([0, 100, 200])
    network.get_campaign.side_effect = lambda cid: campaign(cid, [f"uid_{cid}"])
    network.get_maps_info.side_effect = lambda uids: [map_info(u) for u in uids]

    result = fetch_campaign(all_campaigns=True)

    assert [c.args[0] for c in network.get_campaign.call_args_list] == [100, 200]
    assert [m["map_uid"] for m in result] == ["uid_100", "uid_200"]


def test_fetch_campaign_maps_fields(network):
    network.get_campaigns.return_value = activity([100])
    network.get_campaign.return_value = campaign(100, ["uid_a"])
    network.get_maps_info.return_value = [
        map_info("uid_a", filename="My Track.Map.Gbx")
    ]

    result = fetch_campaign()

    assert result == [
        {
            "map_uid": "uid_a",
            "thumbnail": "https://thumb/uid_a.png",
            "date": "2024-05-17",
            "filename": "My Track",
            "author_uid": "author_uid_a",
            "author_time": 100000,
            "gold_time": 110000,
            "silver_time": 120000,
            "bronze_time": 130000,
            "type": "Race",
        }
    ]


def test_fetch_campaign_empty_activity_list(network):
    network.get_campaigns.return_value = activity([])

    assert fetch_campaign() == []
    network.get_campaign.assert_not_called()


def test_fetch_campaign_only_zero_campaign_id(network):
    network.get_campaigns.return_value = activity([0])

    assert fetch_campaign(all_campaigns=True) == []
    network.get_campaign.assert_not_called()


# ------------------------------------------------------------------
# update_maps

def test_update_maps_forwards_all_campaigns_to_fetch(db_mock):
    with patch(
        "src.updaters.maps_updater.fetch_campaign", return_value=[]
    ) as mock_fetch:
        update_maps(all_campaigns=True)

    mock_fetch.assert_called_once_with(True)


def test_update_maps_skips_royal_and_writes_others(db_mock):
    royal = {
        "map_uid": "r1",
        "type": "Royal",
        "author_uid": "author_1",
        "filename": "Royal Track",
    }
    normal = {
        "map_uid": "n1",
        "type": "Race",
        "author_uid": "author_2",
        "filename": "Normal Track",
    }
    with patch(
        "src.updaters.maps_updater.fetch_campaign", return_value=[royal, normal]
    ):
        update_maps()

    db_mock.update_map_info.assert_called_once_with(normal)


def test_update_maps_overrides_author_for_special_map(db_mock):
    special = {
        "map_uid": "QnSv0bKhCNA1WcSKLiSXirMTo87",
        "type": "Race",
        "author_uid": "old_author",
        "filename": "Special Track",
    }
    with patch("src.updaters.maps_updater.fetch_campaign", return_value=[special]):
        update_maps()

    saved = db_mock.update_map_info.call_args.args[0]
    assert saved["author_uid"] == "e10286e7-31dd-4127-bdf2-f092fd4e2887"
    assert saved["map_uid"] == "QnSv0bKhCNA1WcSKLiSXirMTo87"


# ------------------------------------------------------------------
# update_playercounts / update_nicknames

def test_update_playercounts_fetches_and_saves(db_mock):
    db_mock.fetch_maps_uid.return_value = [{"map_uid": "a"}, {"map_uid": "b"}]
    with patch(
        "src.updaters.maps_updater.get_map_playercount", side_effect=[10, 20]
    ) as mock_playercount:
        update_playercounts()

    assert [c.args for c in mock_playercount.call_args_list] == [("a",), ("b",)]
    assert [c.args for c in db_mock.update_maps_playercount.call_args_list] == [
        (10, "a"),
        (20, "b"),
    ]


def test_update_nicknames_fetches_and_saves(db_mock):
    db_mock.fetch_authors_uid.return_value = [
        {"map_author_uid": "u1"},
        {"map_author_uid": "u2"},
    ]
    with patch(
        "src.updaters.maps_updater.ids_to_nicknames",
        return_value={"u1": "Nick1", "u2": "Nick2"},
    ) as mock_nicknames:
        update_nicknames()

    mock_nicknames.assert_called_once_with(["u1", "u2"])
    assert [c.args for c in db_mock.update_author_nicknames.call_args_list] == [
        ("u1", "Nick1"),
        ("u2", "Nick2"),
    ]


# ------------------------------------------------------------------
# get_new_maps

@pytest.fixture
def stages():
    with (
        patch("src.updaters.maps_updater.update_maps") as mock_update_maps,
        patch("src.updaters.maps_updater.update_nicknames") as mock_nicknames,
        patch("src.updaters.maps_updater.update_playercounts") as mock_playercounts,
    ):
        yield SimpleNamespace(
            maps=mock_update_maps,
            nicknames=mock_nicknames,
            playercounts=mock_playercounts,
        )


def test_get_new_maps_existing_populated_db(db_mock, stages):
    db_mock.db_exist.return_value = True
    db_mock.maps_is_empty.return_value = False

    get_new_maps()

    db_mock.create_database.assert_not_called()
    stages.maps.assert_called_once_with(all_campaigns=False)
    stages.nicknames.assert_called_once_with()
    stages.playercounts.assert_called_once_with()


def test_get_new_maps_fresh_db_updates_full_only_once(db_mock, stages):
    db_mock.db_exist.return_value = False

    get_new_maps()

    db_mock.create_database.assert_called_once_with()
    db_mock.maps_is_empty.assert_not_called()
    assert stages.maps.call_args_list == [
        call(all_campaigns=True),
        call(all_campaigns=False),
    ]


def test_get_new_maps_empty_but_existing_db(db_mock, stages):
    db_mock.db_exist.return_value = True
    db_mock.maps_is_empty.return_value = True

    get_new_maps()

    db_mock.create_database.assert_not_called()
    assert stages.maps.call_args_list == [
        call(all_campaigns=True),
        call(all_campaigns=False),
    ]

