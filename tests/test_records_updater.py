from types import SimpleNamespace
from unittest.mock import patch

import pytest

from src.updaters.records_updater import get_new_records

MAPS = [
    {"map_uid": "uid_a", "map_name": "Map A"},
    {"map_uid": "uid_b", "map_name": "Map B"},
]


def make_records(*account_ids):
    return [
        {
            "accountId": acc_id,
            "name": f"raw_{acc_id}",
            "score": 100000,
            "position": i + 1,
        }
        for i, acc_id in enumerate(account_ids)
    ]


@pytest.fixture
def env():
    with (
        patch("src.updaters.records_updater.db") as mock_db,
        patch("src.updaters.records_updater.id_to_records") as mock_id_to_records,
        patch("src.utils.helpers.ids_to_nicknames") as mock_ids_to_nicknames,
    ):
        yield SimpleNamespace(
            db=mock_db,
            id_to_records=mock_id_to_records,
            ids_to_nicknames=mock_ids_to_nicknames,
        )


# ------------------------------------------------------------------
# get_new_records

def test_get_new_records_rewrites_records_with_nicknames(env):
    env.db.fetch_maps.return_value = [MAPS[0]]
    map_records = make_records("acc1", "acc2")
    env.id_to_records.return_value = map_records
    env.ids_to_nicknames.return_value = {"acc1": "Nick1", "acc2": "Nick2"}

    get_new_records()

    env.id_to_records.assert_called_once_with("uid_a")
    env.ids_to_nicknames.assert_called_once_with(["acc1", "acc2"])
    env.db.replace_records.assert_called_once_with("uid_a", map_records)
    assert map_records[0]["name"] == "Nick1"
    assert map_records[1]["name"] == "Nick2"


def test_get_new_records_keeps_raw_name_without_nickname(env):
    env.db.fetch_maps.return_value = [MAPS[0]]
    map_records = make_records("acc1", "acc2")
    env.id_to_records.return_value = map_records
    env.ids_to_nicknames.return_value = {"acc1": "Nick1"}

    get_new_records()

    assert map_records[0]["name"] == "Nick1"
    assert map_records[1]["name"] == "raw_acc2"


def test_get_new_records_skips_map_without_records(env):
    env.db.fetch_maps.return_value = [MAPS[0]]
    env.id_to_records.return_value = []
    env.ids_to_nicknames.return_value = {}

    get_new_records()

    env.ids_to_nicknames.assert_not_called()
    env.db.replace_records.assert_not_called()


def test_get_new_records_processes_each_map(env):
    env.db.fetch_maps.return_value = MAPS
    env.id_to_records.side_effect = [
        make_records("acc1"),
        make_records("acc2", "acc3"),
    ]
    env.ids_to_nicknames.side_effect = lambda uids: {u: f"nick_{u}" for u in uids}

    get_new_records()

    assert [c.args for c in env.id_to_records.call_args_list] == [
        ("uid_a",),
        ("uid_b",),
    ]
    assert [c.args[0] for c in env.db.replace_records.call_args_list] == [
        "uid_a",
        "uid_b",
    ]
    assert env.db.replace_records.call_count == 2


def test_get_new_records_uses_single_transactional_replace(env):
    env.db.fetch_maps.return_value = [MAPS[0]]
    env.id_to_records.return_value = make_records("acc1", "acc2")
    env.ids_to_nicknames.return_value = {}

    get_new_records()

    env.db.replace_records.assert_called_once()
    env.db.remove_old_records.assert_not_called()
    env.db.update_records.assert_not_called()
