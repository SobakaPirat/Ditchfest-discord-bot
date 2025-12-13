#!/bin/bash
map_counts=(25 50)

python3 updater.py

while true; do
    for count in "${map_counts[@]}"; do
        echo "Время старта: $(date)"
        python3 main.py --maps=$count
        echo "Проверено $count недавних карт"
    done
    
    echo "Время старта: $(date)"
    python3 main.py
    echo "Проверены все карты"
done