# DitchFest Discord Bot

Бот для сбора информации о рекордах на картах клубной кампании
**DitchFest** в игре TrackMania. При появлении нового мирового рекорда бот автоматически
отправляет оформленное уведомление (embed) в канал Discord через вебхук.

Бот состоит из двух независимых воркеров:

| Воркер         | Что делает                                                                                              |
| -------------- | ------------------------------------------------------------------------------------------------------- |
| `updater.py`   | По расписанию собирает карты кампании, рекорды, никнеймы игроков через API TrackMania/Nadeo и записывает всё в базу данных. |
| `notifier.py`  | В цикле проверяет карты на наличие нового мирового рекорда и публикует уведомление в Discord.            |

---

## Технологии

- **Python 3.13**
- **[uv](https://docs.astral.sh/uv/)** — менеджер зависимостей и виртуального окружения
- **MariaDB** — база данных (драйвер `mysql-connector-python`)
- **[discord-webhook](https://pypi.org/project/discord-webhook/)** — отправка уведомлений в Discord
- **TrackMania / Nadeo API** — источник данных о картах и рекордах
- **schedule** — планировщик ежедневного обновления
- **Docker / Docker Compose** — контейнеризованный запуск

---

## Структура проекта

```
.
├── updater.py              # Точка входа: сбор карт и рекордов по расписанию
├── notifier.py             # Точка входа: проверка WR и отправка в Discord
├── src/
│   ├── auth/auth.py        # Аутентификация Ubisoft → Nadeo (core + live services) + OAuth
│   ├── db/database.py      # Работа с MariaDB (создание и работа с БД, таблицы Maps/Records)
│   ├── updaters/           # Логика обновления карт и рекордов
│   └── utils/              # Конфиг, HTTP-хелперы, шаблоны Discord-embed, логирование
├── config/
│   ├── .env_template       # Шаблон переменных окружения (скопируйте в .env)
│   └── .env                # Ваши секреты (в git не попадает)
├── logs/                   # Файлы логов (updater.log, notifier.log) — создаётся автоматически
├── database/               # Данные MariaDB при запуске через Docker (том)
├── tests/                  # Тесты (pytest)
├── docker/
│   ├── dockerfile          # Сборка образа ditch-bot
│   └── docker-compose.yml  # Сервисы db, df-updater, df-notifier
├── pyproject.toml          # Зависимости проекта
└── uv.lock                 # Фиксированные версии зависимостей
```

---

## Предварительные требования

Перед запуском подготовьте данные:

1. **Сервисный аккаунт Ubisoft** — зарегистрируйте сервисный аккаунт на
   [trackmania.com/player/service-account](https://www.trackmania.com/player/service-account)
   (нужны `UBI_LOGIN` и `UBI_PASSWORD`).
2. **Приложение TrackMania API** — создайте приложение на
   [api.trackmania.com](https://api.trackmania.com/) и получите `CLIENT_ID` и `CLIENT_SECRET`.
3. **Discord Webhook** — в нужном канале вашего сервера: *Edit channel → Integrations → Webhooks* → скопируйте URL.
4. **USER_ID** — ID вашего аккаунта на [trackmania.io](https://trackmania.io/)
   (используется для подсчёта количества рекордов карт).
5. **MariaDB** — для локального запуска нужен работающий сервер MariaDB/MySQL
   (пользователь `root` без пароля, порт `3306`).

---

## Настройка `.env`

Все секреты и настройки хранятся в файле `config/.env`. Скопируйте шаблон:

```bash
cp config/.env_template config/.env
```

Заполните значения:

```ini
# Ubisoft / сервисный аккаунт
UBI_LOGIN = ""              # Сервисный логин (trackmania.com/player/service-account)
UBI_PASSWORD = ""           # Сервисный пароль
USER_AGENT = ""             # Имя вашего приложения и контакты
CLIENT_ID = ""              # Application Identifier (api.trackmania.com)
CLIENT_SECRET = ""          # Application Secret (api.trackmania.com)

USER_ID = ""               # ID вашего аккаунта с trackmania.io

WEBHOOKS_URL = ""          # URL Discord-вебхука (Edit channel -> Integrations -> Webhooks)

UPDATER_TIME = "04:00"     # Время ежедневного обновления карт и рекордов (формат HH:MM)

# Хост базы данных:
#   - для локального запуска:      DB_HOST = "127.0.0.1"
#   - для запуска в Docker:        DB_HOST = "mariadb"
DB_HOST = "127.0.0.1"
```

> **Важно:** файл `config/.env` добавлен в `.gitignore` и не должен попадать в репозиторий.

---

## Локальный запуск

### 1. Установите `uv`

```bash
# Linux / macOS
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Требуется **Python 3.13** (версия зафиксирована в `.python-version`).
При необходимости `uv` скачает и установит подходящую версию автоматически.

### 2. Установите зависимости

Из корня проекта:

```bash
uv sync
```

Команда создаст виртуальное окружение `.venv` и установит все зависимости из `uv.lock`.
Для установки вместе с dev-зависимостями (нужны для тестов):

```bash
uv sync --all-groups
```

### 3. Подготовьте базу данных

Убедитесь, что локальный MariaDB/MySQL запущен и доступен как `127.0.0.1:3306`
с пользователем `root` без пароля. База данных `database` и таблицы `Maps`/`Records`
будут созданы автоматически при первом запуске `updater.py`.

### 4. Настройте `.env`

Скопируйте шаблон и заполните (см. раздел выше). Для локального запуска
установите `DB_HOST = "127.0.0.1"`.

### 5. Запустите воркеры

В двух отдельных терминалах из корня проекта:

```bash
# Терминал 1 — сбор карт и рекордов по расписанию
uv run updater.py

# Терминал 2 — проверка рекордов и отправка в Discord
uv run notifier.py
```

Оба процесса работают непрерывно (бесконечный цикл). Для остановки нажмите `Ctrl+C`.

---

## Запуск через Docker Compose

Самый простой способ поднять всё окружение (бот + база данных) — использовать
`docker/docker-compose.yml`. Compose поднимает три сервиса:

| Сервис        | Образ         | Назначение                                                       |
| ------------- | ------------- | ---------------------------------------------------------------- |
| `db`          | `mariadb`     | База данных (том `../database`, порт `3306`).                    |
| `df-updater`  | `ditch-bot`   | Сбор карт и рекордов.                                            |
| `df-notifier` | `ditch-bot`   | Проверка WR и отправка уведомлений в Discord.                    |

### 1. Настройте `.env` для Docker

```bash
cp config/.env_template config/.env
```

Укажите хост базы данных так, как его видит контейнер:

```ini
DB_HOST = "mariadb"
```

### 2. Соберите и запустите

Из **корня проекта** (compose-файл лежит в `docker/`, пути к томам внутри него
относительные — `../logs`, `../database`, `../config`, `context: ..` — поэтому
запускать можно прямо из корня):

```bash
docker compose -f docker/docker-compose.yml up -d
```

> **Примечание:** при первом старте `df-updater` ждёт инициализации БД (~50 c),
> а `df-notifier` дополнительно выжидает ~20 минут, чтобы база успела наполниться
> картами. Это заложено в `docker-compose.yml` (`sleep`).

---

## Логи

Файлы логов создаются автоматически в каталоге `logs/` с ротацией
(макс. 1 МБ, до 2 архивных копий — см. `src/utils/logger_config.py`):

- `logs/updater.log` — работа сборщика карт и рекордов;
- `logs/notifier.log` — работа отправщика уведомлений в Discord.

При запуске через Docker каталог `logs/` смонтирован как том, поэтому логи
доступны на хосте. Посмотреть их можно так:

```bash
# из корня проекта
tail -f logs/updater.log
tail -f logs/notifier.log
```

---

## Запуск тестов

Тесты написаны на **pytest** и входят в dev-группу зависимостей:

```bash
# Убедитесь, что dev-зависимости установлены
uv sync --all-groups

# Запуск всех тестов
uv run pytest
```

---

## Как это работает (кратко)

1. **Аутентификация.** `src/auth/auth.py` получает токены Nadeo (Core и Live
   Services) и OAuth через сервисный аккаунт Ubisoft и сохраняет их в `config/.env`.
2. **Обновление карт** (`updater.py` → `src/updaters/maps_updater.py`): по
   расписанию `UPDATER_TIME` загружаются карты кампании DitchFest, их авторы,
   медали, превью и количество прохождений, после чего данные пишутся в таблицу `Maps`.
3. **Обновление рекордов** (`updater.py` → `src/updaters/records_updater.py`):
   для каждой карты загружается топ мировых рекордов и записывается в таблицу `Records`.
4. **Уведомления** (`notifier.py` → `src/utils/embed_template.py`): при появлении
   нового мирового рекорда формируется Discord-embed с автором карты, топ-3
   игроками, их временем и флагами стран, и отправляется на `WEBHOOKS_URL`.

---



