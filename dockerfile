FROM python:3.12-slim

# Устанавливаем зависимости
RUN apt-get update && apt-get install -y \
    cron \
    && rm -rf /var/lib/apt/lists/*

# Рабочая директория
WORKDIR /app

# Копируем файлы
COPY updater.py .
COPY main.py .
COPY main.sh .
COPY requirements.txt .
COPY auth ./auth/
COPY db ./db/
COPY utils ./utils/

# Устанавливаем Python зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Делаем скрипт исполняемым
RUN chmod +x main.sh

# Добавляем задание в crontab
RUN echo "0 5 * * * cd /app && python3 updater.py >> updater.log 2>&1" | crontab -

# Запускаем основной скрипт
CMD ["./main.sh"]