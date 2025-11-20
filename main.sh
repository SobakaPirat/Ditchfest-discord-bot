#!/bin/bash
mkdir -p "logs"
main_log="logs/main.log"
updater_log="logs/updater.log"
map_counts=(25 50)

python3 updater.py >> "$updater_log" 2>&1

while true; do
    for count in "${map_counts[@]}"; do
        echo "Время старта: $(date)"
        python3 main.py --maps=$count >> "$main_log" 2>&1
        echo "Проверено $count недавних карт"
    done
    
    echo "Время старта: $(date)"
    python3 main.py >> "$main_log" 2>&1
    echo "Проверены все карты"
done