from __future__ import annotations

import logging
import os
import sqlite3

logger = logging.getLogger(__name__)


class Database:
    def __init__(self) -> None:
        self.db_path = "database/database.db"

    def get_conn(self):
        return sqlite3.connect(self.db_path)

    def db_exist(self):
        if not os.path.exists(self.db_path):
            return False
        else:
            logger.info("Database already exists")
            return True

    def maps_is_empty(self):
        conn = self.get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM Maps")
        count = cursor.fetchone()[0]
        return count == 0

    def create_database(self) -> None:
        os.makedirs("database", exist_ok=True)
        conn = self.get_conn()
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Maps (
                map_uid          TEXT    PRIMARY KEY    UNIQUE,
                map_date         TEXT,
                map_author_uid   TEXT,
                map_author_name  TEXT,
                map_name         TEXT,
                map_playercount  INTEGER,
                map_thumbnail    TEXT    UNIQUE,
                map_at           INTEGER,
                map_gold         INTEGER,
                map_silver       INTEGER,
                map_bronze       INTEGER,
                map_wr_timestamp INTEGER
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Records (
                map_uid          TEXT    NOT NULL    REFERENCES Maps (map_uid) ON DELETE CASCADE,
                player_uid       TEXT,
                player_name      TEXT,
                player_time      INTEGER,
                player_timestamp INTEGER,
                player_place     INTEGER
            )
        """)

        conn.commit()
        conn.close()

    # for notifier

    def update_map_wr_timestamp(self, timestamp: int, map_uid: str) -> None:
        conn = self.get_conn()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE Maps SET map_wr_timestamp = ? WHERE map_uid = ?",
            (timestamp, map_uid),
        )
        conn.commit()
        conn.close()

    # for updater

    def fetch_authors_uid(self) -> list[dict[str, str]]:
        conn = self.get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT map_author_uid FROM Maps")
        rows = cursor.fetchall()
        conn.close()
        if rows:
            return [{"map_author_uid": row[0]} for row in rows]
        else:
            logger.warning("Запись не найдена")
            return []

    def fetch_maps_uid(self) -> list[dict[str, str]]:
        conn = self.get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT map_uid FROM Maps")
        rows = cursor.fetchall()
        conn.close()
        if rows:
            return [{"map_uid": row[0]} for row in rows]
        else:
            logger.warning("Запись не найдена")
            return []

    def update_maps_playercount(self, map_playercount: int, map_uid: str) -> None:
        conn = self.get_conn()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE Maps SET map_playercount = ? WHERE map_uid = ?",
            (map_playercount, map_uid),
        )
        conn.commit()
        conn.close()

    def update_author_nicknames(
        self, map_author_uid: str, map_author_name: str
    ) -> None:
        conn = self.get_conn()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE Maps SET map_author_name = ? WHERE map_author_uid = ?",
            (map_author_name, map_author_uid),
        )
        conn.commit()
        conn.close()

    def update_map_info(self, map: dict[str, any]) -> None:
        conn = self.get_conn()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO Maps (map_uid, map_name, map_author_uid, map_date, map_thumbnail, map_at, map_gold, map_silver, map_bronze)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                map["map_uid"],
                map["filename"],
                map["author_uid"],
                map["date"],
                map["thumbnail"],
                map["author_time"],
                map["gold_time"],
                map["silver_time"],
                map["bronze_time"],
            ),
        )
        conn.commit()
        conn.close()

    # for discord notifier

    def fetch_maps(self) -> list[dict[str, str]]:
        conn = self.get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT map_uid, map_name, map_thumbnail, map_author_name, map_wr_timestamp 
            FROM Maps 
            ORDER BY map_date DESC
        """)
        rows = cursor.fetchall()
        conn.close()
        if rows:
            return [
                {
                    "map_uid": row[0],
                    "map_name": row[1],
                    "map_thumbnail": row[2],
                    "map_author_name": row[3],
                    "map_wr_timestamp": row[4],
                }
                for row in rows
            ]
        else:
            logger.warning("Карты не найдены. Запустите updater.py для сбора карт.")
            return []

    def get_wr(self, map_uid: str) -> dict[str, int] | None:
        conn = self.get_conn()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT player_name, player_time, player_timestamp 
            FROM Records 
            WHERE map_uid = ? AND player_place = 1
        """,
            (map_uid,),
        )
        record = cursor.fetchone()
        conn.close()
        if record:
            return {
                "player_name": record[0],
                "player_time": record[1],
                "player_timestamp": record[2],
            }
        else:
            return None

    def remove_old_records(self, map_uid: str) -> None:
        conn = self.get_conn()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Records WHERE map_uid = ?", (map_uid,))
        conn.commit()
        conn.close()

    def update_records(self, map_record: dict[str, any], map_uid: str) -> None:
        conn = self.get_conn()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO Records (map_uid, player_uid, player_name, player_time, player_timestamp, player_place)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
            (
                map_uid,
                map_record["accountId"],
                map_record["name"],
                map_record["score"],
                map_record["timestamp"],
                map_record["position"],
            ),
        )
        conn.commit()
        conn.close()


db = Database()
