❯ cat -pp scripts/reset_agent.sh
#!/bin/bash

# Путь к базе
DB_FILE="/opt/restic-agent/agent.db"

# Удаляем базу
if [ -f "$DB_FILE" ]; then
    rm "$DB_FILE"
fi

# Перезапуск сервиса через systemd (это безопасно делать из-под sudo)
systemctl restart restic-agent
