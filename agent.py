import subprocess, os, json, sqlite3, time, asyncio
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, Header, HTTPException, BackgroundTasks
import os

app = FastAPI(title="Restic Script-Based Agent")

# --- КОНФИГУРАЦИЯ ---
#API_TOKEN = "my-secret-token"
API_TOKEN = os.getenv("SERVER_TOKEN", "fallback-secret-token")
DB_PATH = "agent.db"
# Папка, где лежат твои .sh скрипты
SCRIPTS_DIR = Path(__file__).parent / "scripts"
# Очередь, чтобы restic не запускался одновременно (если скрипты работают с одним репо)
restic_lock = asyncio.Lock()

# --- БД ФУНКЦИИ (без изменений) ---
def db_execute(sql: str, params: tuple = ()):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(sql, params)
    conn.commit()
    last_id = cursor.lastrowid
    conn.close()
    return last_id

async def execute_script_task(job_id: int, script_path: str, script_name: str):
    async with restic_lock:
        db_execute("UPDATE jobs SET status='processing' WHERE id=?", (job_id,))

        start_ts = time.time()
        # Запускаем bash. Вся магия с systemd-run и restic теперь ВНУТРИ .sh файла
        proc = await asyncio.create_subprocess_exec(
            "sudo", script_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        stdout, stderr = await proc.communicate()
        out_str = stdout.decode(errors='ignore')
        err_str = stderr.decode(errors='ignore')
        duration = round(time.time() - start_ts, 2)
        status = "success" if proc.returncode == 0 else "error"

        # Попытка найти JSON в выводе для динамических таблиц (опционально)
        # Если скрипт выводит JSON от restic, мы можем его выцепить
        if proc.returncode == 0:
            try:
                # Ищем последнюю строку, похожую на JSON объект
                for line in reversed(out_str.strip().split('\n')):
                    if line.strip().startswith('{') and line.strip().endswith('}'):
                        # Тут можно вызвать твою функцию save_to_dynamic_db,
                        # если заранее знать имя таблицы (например, по имени скрипта)
                        # save_to_dynamic_db(f"results_{script_name.split('.')[0]}", json.loads(line))
                        break
            except: pass

        db_execute(
            "UPDATE jobs SET status=?, stdout=?, stderr=?, exit_code=?, duration=? WHERE id=?",
            (status, out_str, err_str, proc.returncode, duration, job_id)
        )

# --- API ENDPOINTS ---

@app.on_event("startup")
def startup():
    # Создаем папку для скриптов, если её нет
    SCRIPTS_DIR.mkdir(exist_ok=True)
    db_execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            command TEXT,
            status TEXT,
            start_time TEXT,
            duration REAL,
            stdout TEXT,
            stderr TEXT,
            exit_code INTEGER
        )
    """)

@app.post("/run/{script_name}")
async def run_script(script_name: str, background_tasks: BackgroundTasks, x_server_token: str = Header(None)):
    if x_server_token != API_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid token")

    # Безопасность: защищаемся от ../ в имени файла
    safe_name = os.path.basename(script_name)
    script_path = SCRIPTS_DIR / safe_name

    if not script_path.exists():
        raise HTTPException(status_code=404, detail=f"Script {safe_name} not found in {SCRIPTS_DIR}")

    job_id = db_execute(
        "INSERT INTO jobs (command, status, start_time) VALUES (?, ?, ?)",
        (safe_name, "queued", time.strftime("%Y-%m-%d %H:%M:%S"))
    )

    background_tasks.add_task(execute_script_task, job_id, str(script_path), safe_name)
    return {"job_id": job_id, "status": "queued", "script": safe_name}

@app.get("/db/query")
async def query_db(sql: str, x_server_token: str = Header(None)):
    if x_server_token != API_TOKEN: raise HTTPException(status_code=403)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    try:
        cursor.execute(sql)
        rows = cursor.fetchall()
        return [dict(r) for r in rows]
    except Exception as e:
        return {"error": str(e)}
    finally:
        conn.close()
