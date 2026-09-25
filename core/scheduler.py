import os
import re
import subprocess
import sys
from pathlib import Path


def parse_schedule_time(time_str: str) -> str:
    time_str = time_str.strip()
    match = re.match(r"^([01]?\d|2[0-3]):([0-5]\d)$", time_str)
    if not match:
        raise ValueError(f"Formato orario non valido: '{time_str}'. Utilizzare il formato HH:MM (es. '08:00').")
    hour = int(match.group(1))
    minute = int(match.group(2))
    return f"{minute} {hour} * * *"


def setup_cron_schedule(course_query: str, time_str: str) -> bool:
    try:
        cron_expr = parse_schedule_time(time_str)
    except ValueError as e:
        print(f"[ERRORE] {e}")
        return False

    project_root = Path(__file__).resolve().parent.parent
    py_bin = sys.executable
    log_file = project_root / "cron.log"
    
    cmd_str = f'{py_bin} -m dlub -get "{course_query}" >> "{log_file}" 2>&1'
    marker = f"# UNIBO_DOWNLOADER_{course_query.upper().replace(' ', '_')}"
    cron_line = f"{cron_expr} {cmd_str} {marker}"

    print(f"Pianificazione giornaliera alle {time_str} -> {cron_expr}")

    try:
        proc = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
        current_cron = proc.stdout if proc.returncode == 0 else ""

        lines = [line for line in current_cron.splitlines() if marker not in line and line.strip()]
        lines.append(cron_line)
        new_cron = "\n".join(lines) + "\n"

        set_proc = subprocess.run(["crontab", "-"], input=new_cron, text=True, capture_output=True)
        if set_proc.returncode == 0:
            print(f"Pianificazione registrata con successo in crontab.")
            print(f"   Orario: ogni giorno alle {time_str}")
            print(f"   Log: {log_file}")
            return True
        else:
            print(f"[ERRORE] Crontab: {set_proc.stderr}")
            return False
    except Exception as e:
        print(f"[ERRORE] Impossibile configurare crontab: {e}")
        return False
