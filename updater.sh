#!/bin/bash
mkdir -p "logs"
log_file="logs/script.log"
map_counts=(25 50)

while true; do
    for count in "${map_counts[@]}"; do
        echo "Время старта: $(date)"
        python3 main.py --maps=$count >> "$log_file" 2>&1
        echo "Проверено $count недавних карт"
    done
    
    echo "Время старта: $(date)"
    python3 main.py >> "$log_file" 2>&1
    echo "Проверены все карты"
done