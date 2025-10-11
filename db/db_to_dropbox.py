import dropbox
from dotenv import find_dotenv, load_dotenv, get_key

dotenv_path = find_dotenv()
load_dotenv(dotenv_path)
DATABASE = get_key(dotenv_path, ("DATABASE"))
DROPBOX_TOKEN = get_key(dotenv_path, ("DROPBOX_TOKEN"))

def upload_with_direct_link():
    """Загружает и возвращает прямую ссылку для скачивания"""
    dbx = dropbox.Dropbox(DROPBOX_TOKEN)
    
    # Загружаем/обновляем файл
    with open(DATABASE, 'rb') as f:
        dbx.files_upload(f.read(), '/database.db', mode=dropbox.files.WriteMode.overwrite)
    
    # Получаем публичную ссылку
    shared_link = dbx.sharing_create_shared_link('/database.db')
    
    # Преобразуем в прямую ссылку для скачивания
    direct_download_url = shared_link.url.replace('dl=0', 'dl=1')
    
    print(f"🔗 Прямая ссылка для скачивания: {direct_download_url}")
    return direct_download_url
