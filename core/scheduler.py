"""
scheduler.py - Gestore delle pianificazioni e sincronizzazioni automatiche (cron)
Supporta:
- Esecuzione giornaliera ("Tutti i giorni")
- Esecuzione singola ("Una sola volta", cancellata dopo l'esecuzione)
- Giorni specifici della settimana (es. "Lun, Mer, Ven")
"""

import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

DAY_NAMES = {
    1: "Lun",
    2: "Mar",
    3: "Mer",
    4: "Gio",
    5: "Ven",
    6: "Sab",
    7: "Dom",
    0: "Dom",
}


@dataclass
class ScheduleItem:
    time_str: str
    frequency_type: str  # "everyday", "once", "custom"
    days_summary: str    # "Tutti i giorni", "Una sola volta", "Lun, Mer, Ven"
    cron_raw_line: str
    marker: str


def parse_schedule_time(time_str: str) -> tuple[int, int]:
    time_str = time_str.strip()
    match = re.match(r"^([01]?\d|2[0-3]):([0-5]\d)$", time_str)
    if not match:
        raise ValueError(f"Formato orario non valido: '{time_str}'. Utilizzare il formato HH:MM (es. '08:00').")
    hour = int(match.group(1))
    minute = int(match.group(2))
    return hour, minute


def format_days_label(days: List[int]) -> str:
    if not days or set(days) == {1, 2, 3, 4, 5, 6, 7} or set(days) == {1, 2, 3, 4, 5, 6, 0}:
        return "Tutti i giorni"
    if set(days) == {1, 2, 3, 4, 5}:
        return "Lun - Ven"
    if set(days) == {6, 7} or set(days) == {6, 0}:
        return "Fine settimana (Sab, Dom)"
    
    sorted_unique = sorted(set(d if d != 0 else 7 for d in days))
    return ", ".join(DAY_NAMES.get(d, str(d)) for d in sorted_unique)


def get_course_schedules(course_query: str) -> List[ScheduleItem]:
    """Ritorna la lista degli oggetti ScheduleItem configurati in crontab per il corso."""
    try:
        proc = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
        if proc.returncode != 0:
            return []

        clean_q = course_query.upper().replace(" ", "_")
        marker_prefix = f"# UNIBO_DOWNLOADER_{clean_q}"
        schedules: List[ScheduleItem] = []

        for line in proc.stdout.splitlines():
            if marker_prefix in line:
                parts = line.split()
                if len(parts) >= 5:
                    minute_s = parts[0]
                    hour_s = parts[1]
                    day_of_week = parts[4]

                    if minute_s.isdigit() and hour_s.isdigit():
                        time_str = f"{int(hour_s):02d}:{int(minute_s):02d}"
                        
                        freq_type = "everyday"
                        days_summary = "Tutti i giorni"

                        if "_ONCE" in line or "ONCE" in line:
                            freq_type = "once"
                            days_summary = "Una sola volta"
                        elif day_of_week != "*":
                            freq_type = "custom"
                            try:
                                day_ints = [int(d) for d in day_of_week.split(",") if d.isdigit()]
                                days_summary = format_days_label(day_ints)
                            except Exception:
                                days_summary = f"Giorni: {day_of_week}"

                        marker = [p for p in parts if p.startswith("#")][0] if "#" in line else marker_prefix
                        schedules.append(
                            ScheduleItem(
                                time_str=time_str,
                                frequency_type=freq_type,
                                days_summary=days_summary,
                                cron_raw_line=line,
                                marker=marker,
                            )
                        )
        return schedules
    except Exception:
        return []


def remove_cron_schedule(course_query: str, time_str: Optional[str] = None, frequency: Optional[str] = None) -> bool:
    """Rimuove una specifica pianificazione o tutte le pianificazioni per un corso."""
    clean_q = course_query.upper().replace(" ", "_")
    marker_prefix = f"# UNIBO_DOWNLOADER_{clean_q}"
    try:
        proc = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
        if proc.returncode != 0:
            return True

        current_cron = proc.stdout
        lines = []

        target_time_tuple = None
        if time_str:
            try:
                target_time_tuple = parse_schedule_time(time_str)
            except ValueError:
                pass

        for line in current_cron.splitlines():
            if marker_prefix in line:
                if target_time_tuple:
                    parts = line.split()
                    if len(parts) >= 2 and parts[0].isdigit() and parts[1].isdigit():
                        l_min = int(parts[0])
                        l_hr = int(parts[1])
                        if l_hr == target_time_tuple[0] and l_min == target_time_tuple[1]:
                            if frequency and frequency.upper() not in line:
                                lines.append(line)
                                continue
                            # Corrispondenza trovata: salta (rimuove)
                            continue
                # Se non specificato time_str, rimuove tutte le occorrenze del corso
                continue
            elif line.strip():
                lines.append(line)

        new_cron = "\n".join(lines) + ("\n" if lines else "")
        set_proc = subprocess.run(["crontab", "-"], input=new_cron, text=True, capture_output=True)
        return set_proc.returncode == 0
    except Exception:
        return False


def setup_cron_schedule(
    course_query: str,
    time_str: str,
    frequency_type: str = "everyday",
    selected_days: Optional[List[int]] = None,
) -> bool:
    """
    Registra una nuova pianificazione in crontab.
    frequency_type: 'everyday', 'once', 'custom'
    selected_days: lista di interi 1..7 (1=Lun, 7=Dom) per frequency_type='custom'
    """
    try:
        hour, minute = parse_schedule_time(time_str)
    except ValueError as e:
        print(f"[ERRORE] {e}")
        return False

    project_root = Path(__file__).resolve().parent.parent
    py_bin = sys.executable
    log_file = project_root / "cron.log"
    clean_q = course_query.upper().replace(" ", "_")

    main_script = project_root / "main.py"

    if frequency_type == "once":
        cron_expr = f"{minute} {hour} * * *"
        marker = f"# UNIBO_DOWNLOADER_{clean_q}_{hour:02d}{minute:02d}_ONCE"
        # Script one-shot che dopo il download rimuove se stesso da crontab
        cleanup_py = (
            f'{py_bin} -c "from core.scheduler import remove_cron_schedule; '
            f'remove_cron_schedule(\'{course_query}\', \'{time_str}\', \'ONCE\')"'
        )
        cmd_str = f'{py_bin} "{main_script}" --sync "{course_query}" >> "{log_file}" 2>&1; {cleanup_py}'
    elif frequency_type == "custom" and selected_days:
        day_str = ",".join(str(d if d != 7 else 0) for d in sorted(set(selected_days)))
        cron_expr = f"{minute} {hour} * * {day_str}"
        marker = f"# UNIBO_DOWNLOADER_{clean_q}_{hour:02d}{minute:02d}_DAYS_{day_str.replace(',', '_')}"
        cmd_str = f'{py_bin} "{main_script}" --sync "{course_query}" >> "{log_file}" 2>&1'
    else:
        cron_expr = f"{minute} {hour} * * *"
        marker = f"# UNIBO_DOWNLOADER_{clean_q}_{hour:02d}{minute:02d}_EVERYDAY"
        cmd_str = f'{py_bin} "{main_script}" --sync "{course_query}" >> "{log_file}" 2>&1'

    cron_line = f"{cron_expr} {cmd_str} {marker}"

    try:
        proc = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
        current_cron = proc.stdout if proc.returncode == 0 else ""

        # Rimuove le linee preesistenti con lo stesso marker per non duplicarle
        lines = [line for line in current_cron.splitlines() if marker not in line and line.strip()]
        lines.append(cron_line)
        new_cron = "\n".join(lines) + "\n"

        set_proc = subprocess.run(["crontab", "-"], input=new_cron, text=True, capture_output=True)
        if set_proc.returncode == 0:
            print(f"Pianificazione registrata con successo in crontab ({frequency_type}).")
            return True
        else:
            print(f"[ERRORE] Crontab: {set_proc.stderr}")
            return False
    except Exception as e:
        print(f"[ERRORE] Impossibile configurare crontab: {e}")
        return False
