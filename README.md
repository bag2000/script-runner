# Restic Python Agent

Легковесный агент на FastAPI для запуска скриптов и хранения истории запусков в SQLite.

## Возможности
- Запуск скриптов через API (`POST /run/{script_name}`).
- Просмотр истории и результатов через SQL-запросы (`GET /db/query`).
- Обогащение JSON-вывода метками времени.

## Установка
1. Подготовьте систему:
```bash
   sudo apt update && sudo apt install python3-venv jq -y
   sudo useradd -r -m -d /opt/restic-agent -s /bin/bash restic-agent
```

2. Разверните код:
```bash
sudo mkdir -p /opt/restic-agent/scripts
sudo cp agent.py /opt/restic-agent/
sudo cp scripts/*.sh /opt/restic-agent/scripts/
sudo cp scripts/config.env.example /opt/restic-agent/scripts/config.env
```

3. Настройте окружение:
```bash
sudo -u restic-agent python3 -m venv /opt/restic-agent/venv
sudo /opt/restic-agent/venv/bin/pip install fastapi uvicorn
```

4. Настройте права sudo:
```bash
echo "restic-agent ALL=(root) NOPASSWD: /opt/restic-agent/scripts/*.sh" | sudo tee /etc/sudoers.d/restic-agent
```

5. Настройка автозапуска (Systemd)
```bash
sudo nano /etc/systemd/system/restic-agent.service
```
Вставить содержимое:
```bash
[Unit]
Description=Restic Python Agent
After=network.target

[Service]
User=restic-agent
Group=restic-agent
WorkingDirectory=/opt/restic-agent
Environment="SERVER_TOKEN=my-super-token"
ExecStart=/opt/restic-agent/venv/bin/uvicorn agent:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

## Настройка
Отредактируйте /opt/restic-agent/scripts/config.env, указав свои доступы к репозиторию.
Установите секретный токен в файле /etc/systemd/system/restic-agent.service в переменной SERVER_TOKEN

## Использование
Запуск скрипта:
```bash
curl -X POST "http://<ip>:8000/run/check_full.sh" -H "x-server-token: <your_token>"
```
Проверка результата:
```bash
curl -s -G "http://<ip>:8000/db/query" \
     -H "x-server-token: <your_token>" \
     --data-urlencode "sql=SELECT stdout FROM jobs WHERE status='success' ORDER BY id DESC LIMIT 1" \
     | jq -r '.[0].stdout | fromjson'
```

