from unittest.mock import MagicMock, patch

import pytest

from src.db.database import Database


@pytest.fixture
def mock_db():
    with patch("src.db.database.mysql.connector") as mock_connector:
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connector.connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        yield Database(), mock_connector, mock_conn, mock_cursor


def test_init_sets_default_attributes():
    db = Database()
    assert db.host == "127.0.0.1"
    assert db.port == 3306
    assert db.user == "root"
    assert db.password == ""
    assert db.db_name == "database"


def test_get_conn_returns_connection(mock_db):
    db, _, mock_conn, _ = mock_db
    result = db.get_conn()
    assert result is mock_conn


def test_db_exist_returns_true(mock_db):
    db, mock_connector, mock_conn, mock_cursor = mock_db
    mock_cursor.fetchone.return_value = ("database",)
    assert db.db_exist() is True


def test_db_exist_returns_false(mock_db):
    db, mock_connector, mock_conn, mock_cursor = mock_db
    mock_cursor.fetchone.return_value = None
    assert db.db_exist() is False


def test_db_exist_closes_resources(mock_db):
    db, _, mock_conn, mock_cursor = mock_db
    db.db_exist()
    mock_cursor.close.assert_called_once()
    mock_conn.close.assert_called_once()


def test_maps_is_empty_returns_true(mock_db):
    db, _, mock_conn, mock_cursor = mock_db
    mock_cursor.fetchone.return_value = (0,)
    assert db.maps_is_empty() is True


def test_maps_is_empty_returns_false(mock_db):
    db, _, mock_conn, mock_cursor = mock_db
    mock_cursor.fetchone.return_value = (5,)
    assert db.maps_is_empty() is False


def test_maps_is_empty_closes_resources(mock_db):
    db, _, mock_conn, mock_cursor = mock_db
    db.maps_is_empty()
    mock_cursor.close.assert_called_once()
    mock_conn.close.assert_called_once()


def test_create_database_creates_db_and_tables(mock_db):
    db, mock_connector, mock_conn, mock_cursor = mock_db
    db.create_database()
    mock_connector.connect.assert_called()
    assert mock_cursor.execute.call_count >= 2


def test_create_database_closes_resources(mock_db):
    db, _, mock_conn, mock_cursor = mock_db
    db.create_database()
    mock_cursor.close.assert_called()
    mock_conn.close.assert_called()


def test_update_map_wr_timestamp(mock_db):
    db, _, mock_conn, mock_cursor = mock_db
    db.update_map_wr_timestamp(12345, "map_uid_1")
    mock_cursor.execute.assert_called_once_with(
        "UPDATE Maps SET map_wr_timestamp = %s WHERE map_uid = %s",
        (12345, "map_uid_1"),
    )
    mock_conn.commit.assert_called_once()


def test_fetch_authors_uid_returns_list(mock_db):
    db, _, mock_conn, mock_cursor = mock_db
    mock_cursor.fetchall.return_value = [("author1",), ("author2",)]
    result = db.fetch_authors_uid()
    assert result == [{"map_author_uid": "author1"}, {"map_author_uid": "author2"}]


def test_fetch_authors_uid_returns_empty(mock_db):
    db, _, mock_conn, mock_cursor = mock_db
    mock_cursor.fetchall.return_value = []
    result = db.fetch_authors_uid()
    assert result == []


def test_fetch_maps_uid_returns_list(mock_db):
    db, _, mock_conn, mock_cursor = mock_db
    mock_cursor.fetchall.return_value = [("map1",), ("map2",)]
    result = db.fetch_maps_uid()
    assert result == [{"map_uid": "map1"}, {"map_uid": "map2"}]


def test_fetch_maps_uid_returns_empty(mock_db):
    db, _, mock_conn, mock_cursor = mock_db
    mock_cursor.fetchall.return_value = []
    result = db.fetch_maps_uid()
    assert result == []


def test_update_maps_playercount(mock_db):
    db, _, mock_conn, mock_cursor = mock_db
    db.update_maps_playercount(100, "map_uid_1")
    mock_cursor.execute.assert_called_once_with(
        "UPDATE Maps SET map_playercount = %s WHERE map_uid = %s",
        (100, "map_uid_1"),
    )
    mock_conn.commit.assert_called_once()


def test_update_author_nicknames(mock_db):
    db, _, mock_conn, mock_cursor = mock_db
    db.update_author_nicknames("author1", "Player One")
    mock_cursor.execute.assert_called_once_with(
        "UPDATE Maps SET map_author_name = %s WHERE map_author_uid = %s",
        ("Player One", "author1"),
    )
    mock_conn.commit.assert_called_once()


def test_update_map_info(mock_db):
    db, _, mock_conn, mock_cursor = mock_db
    map_data = {
        "map_uid": "uid1",
        "filename": "map_name",
        "author_uid": "author1",
        "date": "2024-01-01",
        "thumbnail": "thumb.png",
        "author_time": 100,
        "gold_time": 90,
        "silver_time": 95,
        "bronze_time": 105,
    }
    db.update_map_info(map_data)
    mock_cursor.execute.assert_called_once()
    mock_conn.commit.assert_called_once()


def test_fetch_maps_returns_list(mock_db):
    db, _, mock_conn, mock_cursor = mock_db
    mock_cursor.fetchall.return_value = [
        ("uid1", "Map1", "thumb.png", "Author1", 12345)
    ]
    result = db.fetch_maps()
    assert len(result) == 1
    assert result[0]["map_uid"] == "uid1"
    assert result[0]["map_name"] == "Map1"


def test_fetch_maps_returns_empty(mock_db):
    db, _, mock_conn, mock_cursor = mock_db
    mock_cursor.fetchall.return_value = []
    result = db.fetch_maps()
    assert result == []


def test_get_wr_returns_record(mock_db):
    db, _, mock_conn, mock_cursor = mock_db
    mock_cursor.fetchone.return_value = ("Player1", 99, 1234567890)
    result = db.get_wr("uid1")
    assert result["player_name"] == "Player1"
    assert result["player_time"] == 99
    assert result["player_timestamp"] == 1234567890


def test_get_wr_returns_none(mock_db):
    db, _, mock_conn, mock_cursor = mock_db
    mock_cursor.fetchone.return_value = None
    result = db.get_wr("uid1")
    assert result is None


def test_remove_old_records(mock_db):
    db, _, mock_conn, mock_cursor = mock_db
    db.remove_old_records("uid1")
    mock_cursor.execute.assert_called_once_with(
        "DELETE FROM Records WHERE map_uid = %s", ("uid1",)
    )
    mock_conn.commit.assert_called_once()


def test_update_records(mock_db):
    db, _, mock_conn, mock_cursor = mock_db
    record = {
        "accountId": "acc1",
        "name": "Player1",
        "score": 99,
        "timestamp": 1234567890,
        "position": 1,
    }
    db.update_records(record, "uid1")
    mock_cursor.execute.assert_called_once()
    mock_conn.commit.assert_called_once()


def test_db_instance_is_created():
    from src.db.database import db
    assert isinstance(db, Database)
