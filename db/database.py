import sqlite3
import logging
from pathlib import Path
from dotenv import find_dotenv, load_dotenv, get_key

logger = logging.getLogger(__name__)
dotenv_path = find_dotenv()
load_dotenv(dotenv_path)
DATABASE = get_key(dotenv_path, ("DATABASE"))

class Database:
    def __init__(self):
        self.db_path = DATABASE

    #for updater

    def fetch_authors_uid(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row 
        cursor = conn.cursor()
        cursor.execute("SELECT map_author_uid FROM Maps")
        maps = cursor.fetchall()
        conn.close()
        if maps:
            return [dict(row) for row in maps]
        else:
            logger.warning("Запись не найдена")

    def fetch_maps_uid(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row 
        cursor = conn.cursor()
        cursor.execute("SELECT map_uid FROM Maps")
        maps = cursor.fetchall()
        conn.close()
        if maps:
            return [dict(row) for row in maps]
        else:
            logger.warning("Запись не найдена")

    def update_maps_playercount(self, map_playercount, map_uid):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE Maps SET map_playercount = ? WHERE map_uid = ?', (map_playercount, map_uid))
            conn.commit()
    
    def update_author_nicknames(self, map_author_uid, map_author_name):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE Maps SET map_author_name = ? WHERE map_author_uid = ?', (map_author_name, map_author_uid))
            conn.commit()
    
    def update_map_info(self, map):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO Maps (map_uid, map_name, map_author_uid, map_date, map_thumbnail, map_at, map_gold, map_silver, map_bronze)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (map['map_uid'], map['filename'], map['author_uid'], map['date'], map['thumbnail'], map['author_time'], map['gold_time'], map['silver_time'], map['bronze_time']))
            conn.commit()

    
    #for discord notifier

    def fetch_maps(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row 
        cursor = conn.cursor()
        cursor.execute("SELECT map_uid, map_name, map_thumbnail, map_author_name FROM Maps ORDER BY map_date DESC")
        maps = cursor.fetchall()
        conn.close()
        if maps:
            return [dict(row) for row in maps]
        else:
            logger.warning("Запись не найдена")

    def get_wr(self, map_uid):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('SELECT player_name, player_time, player_timestamp FROM Records WHERE map_uid = ? AND player_place = 1', (map_uid,))
        record = cursor.fetchone()
        conn.close()
        if record:
            return dict(record)
        else:
            return None
    
    def remove_old_records(self, map_uid):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM Records WHERE map_uid = ?', (map_uid,))
        conn.commit()  # Важно сохранить изменения!
        conn.close()

    def update_records(self, map_record, map_uid):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        # Пример обновления нескольких полей
        cursor.execute('''
            INSERT INTO Records (map_uid, player_uid, player_name, player_time, player_timestamp, player_place)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (map_uid, map_record['accountId'], map_record['name'], 
            map_record['score'], map_record['timestamp'], map_record['position']))
        conn.commit()  # Важно сохранить изменения!
        conn.close()

# Глобальный экземпляр
db = Database()