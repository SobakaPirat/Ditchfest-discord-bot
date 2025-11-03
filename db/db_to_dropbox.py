import dropbox
from dotenv import find_dotenv, get_key, load_dotenv

dotenv_path = find_dotenv()
load_dotenv(dotenv_path)
DATABASE = get_key(dotenv_path, ("DATABASE"))
DROPBOX_KEY = get_key(dotenv_path, ("DROPBOX_KEY"))
DROPBOX_SECRET = get_key(dotenv_path, ("DROPBOX_SECRET"))
DROPBOX_TOKEN = get_key(dotenv_path, ("DROPBOX_TOKEN"))
DROPBOX_REFRESH_TOKEN = get_key(dotenv_path, ("DROPBOX_REFRESH_TOKEN"))


def refresh_access_token():
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
        print(f"Auth error: {e}")
        return None


def get_dropbox_client():
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
        print("❌ Оба токена невалидны, требуется новая авторизация")
        return None


def upload_with_direct_link():
    """Загружает и возвращает прямую ссылку для скачивания"""
    dbx = get_dropbox_client()

    if dbx is None:
        print("❌ Не удалось установить соединение с Dropbox")
        return None

    try:
        # Загружаем/обновляем файл
        with open(DATABASE, "rb") as f:
            dbx.files_upload(
                f.read(), "/database.db", mode=dropbox.files.WriteMode.overwrite
            )

        # Получаем публичную ссылку
        shared_link = dbx.sharing_create_shared_link("/database.db")

        # Преобразуем в прямую ссылку для скачивания
        direct_download_url = shared_link.url.replace("dl=0", "dl=1")

        print(f"🔗 Прямая ссылка для скачивания: {direct_download_url}")
        return direct_download_url

    except Exception as e:
        print(f"❌ Ошибка при загрузке файла: {e}")
        return None
