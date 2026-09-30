#!/usr/bin/env python3
"""
main.py - Entry point per UniBo Downloader (GUI macOS)
Avvia direttamente l'interfaccia grafica e gestisce le sincronizzazioni programmate in background.
"""

import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))


def main():
    # Supporto per esecuzione sincronizzazione programmata (cron/scheduler) in background
    if len(sys.argv) >= 3 and sys.argv[1] in ("--sync", "--sync-course", "-s"):
        course_query = sys.argv[2]
        from core.downloader import VirtualeDownloader
        downloader = VirtualeDownloader()
        if downloader.init_session():
            if course_query.lower() in ("all", "*", "tutti"):
                downloader.run_all()
            else:
                downloader.scrape_course(course_query)
        sys.exit(0)

    # Avvio predefinito dell'interfaccia grafica
    from gui.app import launch_gui
    launch_gui()


if __name__ == "__main__":
    main()
