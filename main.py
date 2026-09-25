#!/usr/bin/env python3
"""
main.py - Entry point per UniBo-Downloader
Fornisce compatibilità diretta con l'interfaccia a comandi `dlub`.
"""

import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

import dlub

if __name__ == "__main__":
    dlub.main()
