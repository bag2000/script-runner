#!/bin/bash
set -e

APP_DIR="/opt/restic-agent"

# Добавляем папку в исключения (на всякий случай для текущего пользователя)
git config --global --add safe.directory "$APP_DIR"

echo "Updating code from Git..."

# 1. Меняем владельца временно на того, кто запускает скрипт
sudo chown -R $USER "$APP_DIR"

# 2. Обновляем
cd "$APP_DIR"
git pull origin main

# 3. Возвращаем правильных владельцев
# Агенту — всё, кроме скриптов
sudo chown -R restic-agent:restic-agent "$APP_DIR"
# Скриптам — root (чтобы sudoers был в безопасности)
sudo chown -R root:root "$APP_DIR/scripts"

# 4. Перезагрузка сервиса
sudo systemctl restart restic-agent.service

echo "Done!"
