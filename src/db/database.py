from __future__ import annotations

import logging
import os
import subprocess

import mysql.connector

logger = logging.getLogger(__name__)


class Database:
    def __init__(self) -> None:
        self.host = os.getenv("DB_HOST") or "mariadb"
        self.port = 3306
        self.user = "root"
        self.password = ""
        self.db_name = "database"

    # ------------------------------------------------------------------
    # Соединения

    def get_conn(self):
        """Открывает новое соединение с MariaDB."""
        return mysql.connector.connect(
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password,
            database=self.db_name,
        )

    # ------------------------------------------------------------------
    # Инициализация БД

    def db_exist(self) -> bool:
        """Проверяет, существует ли база данных."""
        conn = mysql.connector.connect(
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password,
        )
        cursor = conn.cursor()
        cursor.execute("SHOW DATABASES LIKE %s", (self.db_name,))
        exists = cursor.fetchone() is not None
        cursor.close()
        conn.close()
        if exists:
            logger.info("Database already exists")
        return exists

    def maps_is_empty(self) -> bool:
        conn = self.get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM Maps")
        count = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        return count == 0

    def create_database(self) -> None:
        # Сначала создаём саму базу данных, если её нет
        conn = mysql.connector.connect(
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password,
        )
        cursor = conn.cursor()
        cursor.execute(
            f"CREATE DATABASE IF NOT EXISTS `{self.db_name}` "
            "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
        )
        conn.commit()
        cursor.close()
        conn.close()

        # Теперь создаём таблицы внутри базы
        conn = self.get_conn()
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Maps (
                map_uid          VARCHAR(64)  PRIMARY KEY,
                map_date         VARCHAR(64),
                map_author_uid   VARCHAR(64),
                map_author_name  VARCHAR(255),
                map_name         VARCHAR(255),
                map_playercount  INT,
                map_thumbnail    VARCHAR(512) UNIQUE,
                map_at           INT,
                map_gold         INT,
                map_silver       INT,
                map_bronze       INT,
                map_wr_timestamp BIGINT
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Records (
                id                INT AUTO_INCREMENT PRIMARY KEY,
                map_uid           VARCHAR(64) NOT NULL,
                player_uid        VARCHAR(64),
                player_name       VARCHAR(255),
                player_time       INT,
                player_timestamp  BIGINT,
                player_place      INT,
                FOREIGN KEY (map_uid) REFERENCES Maps (map_uid) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)

        conn.commit()
        cursor.close()
        conn.close()

    def make_backup() -> None:
        """Создаёт дамп MariaDB через mariadb-dump."""
        path = "database/db_backup.sql"
        try:
            result = subprocess.run(
                [
                    "mariadb-dump",
                    "-h",
                    db.host,
                    "-P",
                    str(db.port),
                    "-u",
                    db.user,
                    f"-p{db.password}",
                    db.db_name,
                ],
                capture_output=True,
                text=True,
            )
        except FileNotFoundError:
            logger.error("mariadb-dump не найден.")

        if result.returncode != 0:
            logger.error(f"Ошибка mariadb-dump: {result.stderr}")

        logger.info(f"Дамп сохранён: {path}")

    # ------------------------------------------------------------------
    # for notifier

    def update_map_wr_timestamp(self, timestamp: int, map_uid: str) -> None:
        conn = self.get_conn()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE Maps SET map_wr_timestamp = %s WHERE map_uid = %s",
            (timestamp, map_uid),
        )
        conn.commit()
        cursor.close()
        conn.close()

    # ------------------------------------------------------------------
    # for updater

    def fetch_authors_uid(self) -> list[dict[str, str]]:
        conn = self.get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT map_author_uid FROM Maps")
        rows = cursor.fetchall()
        cursor.close()
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
        cursor.close()
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
            "UPDATE Maps SET map_playercount = %s WHERE map_uid = %s",
            (map_playercount, map_uid),
        )
        conn.commit()
        cursor.close()
        conn.close()

    def update_author_nicknames(
        self, map_author_uid: str, map_author_name: str
    ) -> None:
        conn = self.get_conn()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE Maps SET map_author_name = %s WHERE map_author_uid = %s",
            (map_author_name, map_author_uid),
        )
        conn.commit()
        cursor.close()
        conn.close()

    def update_map_info(self, map: dict[str, any]) -> None:
        conn = self.get_conn()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO Maps
                (map_uid, map_name, map_author_uid, map_date, map_thumbnail, map_at, map_gold, map_silver, map_bronze)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                map_name = VALUES(map_name),
                map_author_uid = VALUES(map_author_uid),
                map_date = VALUES(map_date),
                map_thumbnail = VALUES(map_thumbnail),
                map_at = VALUES(map_at),
                map_gold = VALUES(map_gold),
                map_silver = VALUES(map_silver),
                map_bronze = VALUES(map_bronze)
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
        cursor.close()
        conn.close()

    # ------------------------------------------------------------------
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
        cursor.close()
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
            WHERE map_uid = %s AND player_place = 1
        """,
            (map_uid,),
        )
        record = cursor.fetchone()
        cursor.close()
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
        cursor.execute("DELETE FROM Records WHERE map_uid = %s", (map_uid,))
        conn.commit()
        cursor.close()
        conn.close()

    def update_records(self, map_record: dict[str, any], map_uid: str) -> None:
        conn = self.get_conn()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO Records
                (map_uid, player_uid, player_name, player_time, player_timestamp, player_place)
            VALUES (%s, %s, %s, %s, %s, %s)
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
        cursor.close()
        conn.close()


db = Database()
