import logging

import dropbox

from src.utils.config import get_env_key

DROPBOX_KEY = get_env_key("DROPBOX_KEY")
DROPBOX_SECRET = get_env_key("DROPBOX_SECRET")
DROPBOX_TOKEN = get_env_key("DROPBOX_TOKEN")
DROPBOX_REFRESH_TOKEN = get_env_key("DROPBOX_REFRESH_TOKEN")

logger = logging.getLogger(__name__)


def refresh_access_token() -> dropbox.Dropbox:
    try:
        dbx = dropbox.Dropbox(
            app_key=DROPBOX_KEY,
            app_secret=DROPBOX_SECRET,
            oauth2_refresh_token=DROPBOX_REFRESH_TOKEN,
        )
        # Проверяем, что токен работает
        dbx.users_get_current_account()
        return dbx
    except dropbox.exceptions.AuthError as e:
        logger.error(f"Auth error: {e}")
        return None


def get_dropbox_client() -> dropbox.Dropbox:
    """Универсальная функция для получения клиента Dropbox"""
    # Сначала пробуем через refresh token
    dbx = refresh_access_token()
    if dbx is not None:
        return dbx

    # Если не сработало, пробуем прямой токен
    try:
        dbx = dropbox.Dropbox(DROPBOX_TOKEN)
        dbx.users_get_current_account()  # Проверяем валидность
        return dbx
    except dropbox.exceptions.AuthError:
        logger.error("❌ Оба токена невалидны, требуется новая авторизация")
        return None


def upload_with_direct_link() -> str:
    """Экспортирует MariaDB в дамп и загружает его на Dropbox, возвращая прямую ссылку."""
    path = "database/db_backup.sql"

    dbx = get_dropbox_client()
    if dbx is None:
        return None

    try:
        with open(path, "rb") as f:
            dbx.files_upload(
                f.read(), "/db_backup.sql", mode=dropbox.files.WriteMode.overwrite
            )

        shared_link = dbx.sharing_create_shared_link("/db_backup.sql")
        direct_download_url = shared_link.url.replace("dl=0", "dl=1")

        logger.info(f"🔗 Прямая ссылка для скачивания: {direct_download_url}")
        return direct_download_url

    except Exception as e:
        logger.error(f"❌ Ошибка при загрузке файла: {e}")
        return None


def upload_to_dropbox() -> None:
    DROPBOX_SAVE = get_env_key("DROPBOX_SAVE").lower() == "true"
    if DROPBOX_SAVE:
        url = upload_with_direct_link()
        logger.info(url)
