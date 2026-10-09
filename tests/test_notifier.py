from types import SimpleNamespace
from unittest.mock import patch

import pytest

from notifier import main, process_map


def make_map(map_uid="uid_a", map_name="Map A", wr_timestamp=111):
    return {
        "map_uid": map_uid,
        "map_name": map_name,
        "map_wr_timestamp": wr_timestamp,
    }


def make_records(*account_ids, timestamp=222):
    return [
        {
            "accountId": acc_id,
            "name": f"raw_{acc_id}",
            "score": 100000,
            "position": i + 1,
            "timestamp": timestamp,
        }
        for i, acc_id in enumerate(account_ids)
    ]


@pytest.fixture
def env():
    with (
        patch("notifier.db") as mock_db,
        patch("notifier.get_map_records") as mock_get_map_records,
        patch("notifier.ids_to_nicknames") as mock_ids_to_nicknames,
        patch("notifier.post_all_discords") as mock_post_all_discords,
    ):
        yield SimpleNamespace(
            db=mock_db,
            get_map_records=mock_get_map_records,
            ids_to_nicknames=mock_ids_to_nicknames,
            post_all_discords=mock_post_all_discords,
        )


# ------------------------------------------------------------------
# process_map


def test_process_map_without_records_does_nothing(env):
    env.get_map_records.return_value = []

    process_map(make_map())

    env.get_map_records.assert_called_once_with(
        map_uid="uid_a", length=3, offset=0
    )
    env.ids_to_nicknames.assert_not_called()
    env.post_all_discords.assert_not_called()
    env.db.update_map_wr_timestamp.assert_not_called()


def test_process_map_same_timestamp_does_nothing(env):
    env.get_map_records.return_value = make_records("acc1")

    process_map(make_map(wr_timestamp=222))

    env.ids_to_nicknames.assert_not_called()
    env.post_all_discords.assert_not_called()
    env.db.update_map_wr_timestamp.assert_not_called()


def test_process_map_new_wr_notifies_and_saves_timestamp(env):
    map = make_map(wr_timestamp=111)
    map_records = make_records("acc1", "acc2")
    env.get_map_records.return_value = map_records
    env.ids_to_nicknames.return_value = {"acc1": "Nick1", "acc2": "Nick2"}

    process_map(map)

    env.ids_to_nicknames.assert_called_once_with(["acc1", "acc2"])
    assert map_records[0]["name"] == "Nick1"
    assert map_records[1]["name"] == "Nick2"
    env.post_all_discords.assert_called_once_with(
        map=map, map_records=map_records, timestamp=111
    )
    env.db.update_map_wr_timestamp.assert_called_once_with(
        timestamp=222, map_uid="uid_a"
    )


def test_process_map_keeps_raw_name_without_nickname(env):
    map_records = make_records("acc1", "acc2")
    env.get_map_records.return_value = map_records
    env.ids_to_nicknames.return_value = {"acc1": "Nick1"}

    process_map(make_map())

    assert map_records[0]["name"] == "Nick1"
    assert map_records[1]["name"] == "raw_acc2"


def test_process_map_first_wr_updates_db_without_notification(env):
    env.get_map_records.return_value = make_records("acc1")

    process_map(make_map(wr_timestamp=None))

    env.ids_to_nicknames.assert_not_called()
    env.post_all_discords.assert_not_called()
    env.db.update_map_wr_timestamp.assert_called_once_with(
        timestamp=222, map_uid="uid_a"
    )


# ------------------------------------------------------------------
# main


def test_main_processes_all_maps(env):
    env.db.fetch_maps.return_value = [
        make_map(map_uid="uid_a", wr_timestamp=111),
        make_map(map_uid="uid_b", wr_timestamp=111),
    ]
    env.get_map_records.side_effect = [
        make_records("acc1"),
        make_records("acc2"),
    ]

    main()

    assert [c.kwargs for c in env.get_map_records.call_args_list] == [
        {"map_uid": "uid_a", "length": 3, "offset": 0},
        {"map_uid": "uid_b", "length": 3, "offset": 0},
    ]
    assert [
        c.kwargs for c in env.db.update_map_wr_timestamp.call_args_list
    ] == [
        {"timestamp": 222, "map_uid": "uid_a"},
        {"timestamp": 222, "map_uid": "uid_b"},
    ]


def test_main_continues_after_map_error(env):
    env.db.fetch_maps.return_value = [
        make_map(map_uid="uid_a"),
        make_map(map_uid="uid_b"),
    ]
    env.get_map_records.side_effect = [
        Exception("boom"),
        make_records("acc2"),
    ]

    main()

    assert [
        c.kwargs["map_uid"]
        for c in env.db.update_map_wr_timestamp.call_args_list
    ] == ["uid_b"]
