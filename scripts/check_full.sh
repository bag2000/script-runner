#!/bin/bash
# Остановить выполнение при любой ошибке
set -e

# Загружаем переменные окружения
source "$(dirname "$0")/config.env"

# Запускаем restic в изолированном scope. Вывод сохраняем в переменную RESULT, 
# чтобы не выводить "мусор" от systemd-run в итоговый лог агента.
RESULT=$(systemd-run --scope -q -p CPUQuota=200% -p MemoryLimit=1G -- restic check --read-data --json)

# Добавляем в JSON метку времени и выводим в stdout для базы данных агента
echo "$RESULT" | jq --arg d "$(date '+%Y-%m-%d %H:%M:%S')" '. + {agent_executed_at: $d}'

