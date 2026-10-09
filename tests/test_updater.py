from types import SimpleNamespace
from unittest.mock import patch

import pytest

from updater import main, update, validate_updater_time


@pytest.fixture
def stages():
    with (
        patch("updater.get_new_maps") as mock_get_new_maps,
        patch("updater.get_new_records") as mock_get_new_records,
    ):
        yield SimpleNamespace(
            get_new_maps=mock_get_new_maps,
            get_new_records=mock_get_new_records,
        )


# ------------------------------------------------------------------
# validate_updater_time


@pytest.mark.parametrize("value", ["04:00", "23:59", "04:00:00", "23:59:59"])
def test_validate_updater_time_accepts_hhmm_and_hhmmss(value):
    assert validate_updater_time(value) == value


@pytest.mark.parametrize("value", ["4:00", "0400", "04:00:0", "", None, "abc"])
def test_validate_updater_time_rejects_invalid(value):
    with pytest.raises(SystemExit):
        validate_updater_time(value)


# ------------------------------------------------------------------
# update


def test_update_runs_both_stages(stages):
    update()

    stages.get_new_maps.assert_called_once_with()
    stages.get_new_records.assert_called_once_with()


def test_update_survives_maps_error(stages):
    stages.get_new_maps.side_effect = Exception("maps boom")

    update()

    stages.get_new_records.assert_called_once_with()


def test_update_survives_records_error(stages):
    stages.get_new_records.side_effect = Exception("records boom")

    update()

    stages.get_new_maps.assert_called_once_with()


# ------------------------------------------------------------------
# main


def test_main_schedules_daily_job_and_updates(stages):
    with (
        patch("updater.UPDATER_TIME", "04:00"),
        patch("updater.schedule") as mock_schedule,
        patch("updater.time") as mock_time,
    ):
        mock_time.sleep.side_effect = [None, KeyboardInterrupt]
        with pytest.raises(KeyboardInterrupt):
            main()

    mock_schedule.every().day.at.assert_called_once_with("04:00")
    mock_schedule.every().day.at.return_value.do.assert_called_once_with(update)
    assert mock_schedule.run_pending.call_count >= 1
    stages.get_new_maps.assert_called_once_with()
    stages.get_new_records.assert_called_once_with()
