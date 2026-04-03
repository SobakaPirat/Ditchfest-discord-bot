#!/bin/bash

while true; do
    current_hour=$(date +%H)
    current_minute=$(date +%M)
    
    # Если сейчас 5:00
    if [ "$current_hour" = "05" ] && [ "$current_minute" = "00" ]; then
        python maps_updater.py
        python records_updater.py
        # Ждем 1 минуту чтобы не выполнить дважды в одну минуту
        sleep 60
    else
        # Ждем 1 минуту и проверяем снова
        sleep 60
    fi
done