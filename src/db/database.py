import logging
import os

import dataset
from dotenv import find_dotenv, get_key, load_dotenv
from sqlalchemy import text

logger = logging.getLogger(__name__)
dotenv_path = find_dotenv()
load_dotenv(dotenv_path)
DATABASE = get_key(dotenv_path, ("DATABASE"))


class Database:
    def __init__(self) -> None:
        self.db_path = DATABASE
        self.db = dataset.connect(f"sqlite:///{self.db_path}")

    def get_conn(self):
        return self.db.engine.connect()

    def create_database_if_needed(self):
        if not os.path.exists(self.db_path):
            logger.info("Creating database...")
            self.create_database()
            logger.info("Database created.")
            return True
        else:
            logger.info("Database already exists.")
            return False

    def create_database(self) -> None:
        conn = self.get_conn()
        conn.execute(
            text(
                """
            CREATE TABLE IF NOT EXISTS Maps (
                map_uid         TEXT    PRIMARY KEY    UNIQUE,
                map_date        TEXT,
                map_author_uid  TEXT,
                map_author_name TEXT,
                map_name        TEXT,
                map_playercount INTEGER,
                map_thumbnail   TEXT    UNIQUE,
                map_at          INTEGER,
                map_gold        INTEGER,
                map_silver      INTEGER,
                map_bronze      INTEGER
            )
            """
            )
        )
        conn.execute(
            text(
                """
            CREATE TABLE IF NOT EXISTS Records (
                map_uid          TEXT    NOT NULL    REFERENCES Maps (map_uid) ON DELETE CASCADE,
                player_uid       TEXT,
                player_name      TEXT,
                player_time      INTEGER,
                player_timestamp INTEGER,
                player_place     INTEGER
            )
            """
            )
        )
        conn.close()

    # for notifier

    def update_map_wr_timestamp(self, timestamp: int, map_uid: str) -> None:
        conn = self.get_conn()
        conn.execute(
            text("UPDATE Maps SET map_wr_timestamp = :wr WHERE map_uid = :uid"),
            {"wr": timestamp, "uid": map_uid},
        )
        conn.close()

    # for updater

    def fetch_authors_uid(self) -> list[dict[str, str]]:
        conn = self.get_conn()
        res = conn.execute(text("SELECT map_author_uid FROM Maps"))
        rows = res.fetchall()
        conn.close()
        if rows:
            return [dict(row) for row in rows]
        else:
            logger.warning("Запись не найдена")
            return []

    def fetch_maps_uid(self) -> list[dict[str, str]]:
        conn = self.get_conn()
        res = conn.execute(text("SELECT map_uid FROM Maps"))
        rows = res.fetchall()
        conn.close()
        if rows:
            return [dict(row) for row in rows]
        else:
            logger.warning("Запись не найдена")
            return []

    def update_maps_playercount(self, map_playercount: int, map_uid: str) -> None:
        conn = self.get_conn()
        conn.execute(
            text("UPDATE Maps SET map_playercount = :pc WHERE map_uid = :uid"),
            {"pc": map_playercount, "uid": map_uid},
        )
        conn.close()

    def update_author_nicknames(
        self, map_author_uid: str, map_author_name: str
    ) -> None:
        conn = self.get_conn()
        conn.execute(
            text("UPDATE Maps SET map_author_name = :name WHERE map_author_uid = :uid"),
            {"name": map_author_name, "uid": map_author_uid},
        )
        conn.close()

    def update_map_info(self, map: dict[str, any]) -> None:
        conn = self.get_conn()
        conn.execute(
            text(
                """
            INSERT OR REPLACE INTO Maps (map_uid, map_name, map_author_uid, map_date, map_thumbnail, map_at, map_gold, map_silver, map_bronze)
            VALUES (:map_uid, :map_name, :author_uid, :date, :thumbnail, :at, :gold, :silver, :bronze)
            """
            ),
            {
                "map_uid": map["map_uid"],
                "map_name": map["filename"],
                "author_uid": map["author_uid"],
                "date": map["date"],
                "thumbnail": map["thumbnail"],
                "at": map["author_time"],
                "gold": map["gold_time"],
                "silver": map["silver_time"],
                "bronze": map["bronze_time"],
            },
        )
        conn.close()

    # for discord notifier

    def fetch_maps(self) -> list[dict[str, str]]:
        conn = self.get_conn()
        res = conn.execute(
            text(
                "SELECT map_uid, map_name, map_thumbnail, map_author_name, map_wr_timestamp FROM Maps ORDER BY map_date DESC"
            )
        )
        rows = res.fetchall()
        conn.close()
        if rows:
            return [dict(row) for row in rows]
        else:
            logger.warning("Карты не найдены. Запустите updater.py для сбора карт.")
            return []

    def get_wr(self, map_uid: str) -> dict[str, int] | None:
        conn = self.get_conn()
        res = conn.execute(
            text(
                "SELECT player_name, player_time, player_timestamp FROM Records WHERE map_uid = :uid AND player_place = 1"
            ),
            {"uid": map_uid},
        )
        record = res.fetchone()
        conn.close()
        if record:
            return dict(record)
        else:
            return None

    def remove_old_records(self, map_uid: str) -> None:
        conn = self.get_conn()
        conn.execute(text("DELETE FROM Records WHERE map_uid = :uid"), {"uid": map_uid})
        conn.close()

    def update_records(self, map_record: dict[str, any], map_uid: str) -> None:
        conn = self.get_conn()
        conn.execute(
            text(
                """
            INSERT INTO Records (map_uid, player_uid, player_name, player_time, player_timestamp, player_place)
            VALUES (:map_uid, :player_uid, :player_name, :player_time, :player_timestamp, :player_place)
            """
            ),
            {
                "map_uid": map_uid,
                "player_uid": map_record["accountId"],
                "player_name": map_record["name"],
                "player_time": map_record["score"],
                "player_timestamp": map_record["timestamp"],
                "player_place": map_record["position"],
            },
        )
        conn.close()


db = Database()
