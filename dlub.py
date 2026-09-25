import getpass
import os
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from core.auth import (
    get_current_moodle_session,
    get_fresh_moodle_session,
    set_unibo_credentials,
    verify_moodle_session,
    load_env_file,
)
from core.database import Database
from core.downloader import VirtualeDownloader
from core.scheduler import setup_cron_schedule


def print_banner():
    print("=" * 65)
    print("UniBo-Downloader (dlub)")
    print("=" * 65)


def cmd_init(args):
    print_banner()
    email = ""
    password = ""
    
    if len(args) >= 2:
        email = args[0].strip()
        password = args[1].strip()
    elif len(args) == 1:
        email = args[0].strip()
        password = getpass.getpass("Inserisci Password UniBo: ").strip()
    else:
        email = input("Inserisci Email Istituzionale UniBo (@studio.unibo.it): ").strip()
        password = getpass.getpass("Inserisci Password UniBo: ").strip()

    if not email or not password:
        print("[ERRORE] Email e Password sono obbligatorie.")
        return

    set_unibo_credentials(email, password)
    print("[AUTH] Credenziali salvate in .env (permessi 0600).")

    print("\n[AUTH] Verifica credenziali e connessione a Virtuale...")
    cookie = get_fresh_moodle_session(headless=True)
    if cookie and verify_moodle_session(cookie):
        print("[AUTH] Autenticazione completata con successo. Sessione Moodle attiva.")
    else:
        print("[AUTH] [AVVISO] Impossibile verificare la sessione automaticamente. Tentativo con interfaccia visuale...")
        cookie = get_fresh_moodle_session(headless=False)
        if cookie and verify_moodle_session(cookie):
            print("[AUTH] Autenticazione completata con successo.")
        else:
            print("[AUTH] [ERRORE] Autenticazione fallita. Verifica le credenziali inserite.")


def cmd_dir(args):
    print_banner()
    db = Database()
    
    if args:
        target_dir = args[0].strip()
    else:
        print(f"Cartella corrente dei corsi: {db.vault_root}")
        ans = input("Inserisci il nuovo percorso della cartella: ").strip()
        if not ans:
            print("Operazione annullata.")
            return
        target_dir = ans

    resolved = db.set_vault_root(target_dir)
    print(f"Cartella di destinazione impostata su:")
    print(f"   {resolved}")


def cmd_def(args):
    print_banner()
    db = Database()

    if len(args) >= 2:
        course_name = args[0].strip()
        course_link = args[1].strip()
    elif len(args) == 1:
        course_name = args[0].strip()
        course_link = input(f"Inserisci il Link o ID per il corso '{course_name}': ").strip()
    else:
        course_name = input("Inserisci il Nome del corso (es. 'Fisica Generale' o 'Basi di Dati'): ").strip()
        course_link = input("Inserisci il Link o ID del corso (es. 'https://virtuale.unibo.it/course/view.php?id=83152'): ").strip()

    if not course_name or not course_link:
        print("[ERRORE] Nome del corso e Link/ID sono entrambi obbligatori.")
        return

    success, cid, msg = db.define_course(course_name, course_link)
    if success:
        folder = db.get_course_folder(cid, default_name=course_name)
        print(f"[OK] {msg}")
        print(f"Cartella locale: {folder}")
        print(f"Comando di download: dlub -get \"{course_name}\"")
    else:
        print(f"[ERRORE] {msg}")


def cmd_get(args):
    db = Database()
    course_query = args[0].strip() if args else ""
    if not course_query:
        courses = db.get_courses()
        if courses:
            print("Corsi configurati disponibili:")
            for c in courses:
                print(f"  - [{c['course_id']}] {c['course_name']}")
            ans = input("\nInserisci Nome, ID o premi Invio per scaricarli tutti: ").strip()
            course_query = ans or "all"
        else:
            course_query = input("Inserisci Nome, ID o URL del corso su Virtuale: ").strip()

    if not course_query:
        print("[ERRORE] Nessun corso specificato.")
        return

    downloader = VirtualeDownloader()
    if not downloader.init_session():
        return

    if course_query.lower() in ("all", "*", "tutti"):
        downloader.run_all()
    else:
        downloader.scrape_course(course_query)


def cmd_schedule(args):
    print_banner()
    if len(args) < 2:
        print("Uso: dlub -schedule \"Nome Corso / ID\" <HH:MM>")
        print("Esempio: dlub -schedule \"Basi di Dati\" \"08:00\"")
        return

    course_query = args[0].strip()
    time_str = args[1].strip()
    setup_cron_schedule(course_query, time_str)


def cmd_list(args):
    print_banner()
    db = Database()
    
    courses = db.get_courses()
    stats = db.get_stats()

    print(f"\nCARTELLA RADICE: {db.vault_root}")
    print(f"STATISTICHE DATABASE (SQLite: {db.db_path}):")
    print(f"   - Corsi registrati: {stats['total_courses']}")
    print(f"   - File scaricati:   {stats['total_files']} ({stats['total_size_mb']} MB)")
    if stats['type_distribution']:
        types_str = ", ".join(f"{k}: {v}" for k, v in stats['type_distribution'].items())
        print(f"   - Distribuzione tipi: {types_str}")
    print("-" * 65)

    if not courses:
        print("Nessun corso ancora registrato nel database locale.")
        print("Usa 'dlub -def <Nome> <Link/ID>' per definire un corso,")
        print("oppure 'dlub -get <ID o Link>' per scaricarlo direttamente.")
        return

    print("\nCORSI CONFIGURATI:")
    for c in courses:
        cid = c["course_id"]
        cname = c["course_name"]
        last_s = c.get("last_scanned") or "Mai"
        total = c.get("total_files", 0)
        folder = db.get_course_folder(cid, default_name=cname)
        print(f"[{cid}] {cname}")
        print(f"   Cartella locale: {folder}")
        print(f"   File salvati:    {total} | Ultima scansione: {last_s}")
        print()


def cmd_doctor(args):
    print_banner()
    db = Database()
    load_env_file()

    print("DIAGNOSTICA UNIBO-DOWNLOADER:")
    print("-" * 65)

    py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    print(f" Python:             {py_ver}")

    v_root = db.vault_root
    exists = "PRESENTE" if os.path.exists(v_root) else "DA CREARE"
    print(f" Cartella Vault:     {v_root} ({exists})")

    print(f" SQLite Database:    {db.db_path}")

    cookie = get_current_moodle_session()
    if cookie:
        masked = cookie[:6] + "..." + cookie[-4:]
        if verify_moodle_session(cookie):
            print(f" Sessione Moodle:    ATTIVA ({masked})")
        else:
            print(f" Sessione Moodle:    SCADUTA ({masked}) - verra' rinnovata al prossimo get")
    else:
        print(f" Sessione Moodle:    NON CONFIGURATA (esegui: dlub -init)")

    email = os.getenv("UNIBO_EMAIL", "")
    pwd = os.getenv("UNIBO_PASSWORD", "")
    if email and pwd:
        print(f" Credenziali UniBo:  CONFIGURATE ({email})")
    else:
        print(f" Credenziali UniBo:  NON PRESENTI IN .env")

    courses = db.get_courses()
    print(f" Corsi registrati:   {len(courses)}")
    print("=" * 65)


def main():
    argv = sys.argv[1:]
    if not argv:
        print_banner()
        print("Uso:")
        print('  dlub -init "EMAIL" "PASSWORD"     Configura credenziali UniBo')
        print('  dlub -dir "PERCORSO"              Imposta cartella radice dei corsi')
        print('  dlub -def "NOME CORSO" "LINK/ID"  Definisce e associa un corso')
        print('  dlub -get "NOME O ID CORSO"       Scarica materiali del corso')
        print('  dlub -schedule "CORSO" "HH:MM"    Pianifica sincronizzazione giornaliera')
        print('  dlub -list                        Mostra corsi e statistiche')
        print('  dlub -doctor                      Verifica integrita\' sistema')
        print()
        sys.exit(0)

    first_arg = argv[0].lower().lstrip("-")
    remaining = argv[1:]

    if first_arg in ("init", "setup"):
        cmd_init(remaining)
    elif first_arg in ("dir", "folder", "vault", "set-dir"):
        cmd_dir(remaining)
    elif first_arg in ("def", "define", "add", "add-course"):
        cmd_def(remaining)
    elif first_arg in ("get", "run", "download", "scrape"):
        cmd_get(remaining)
    elif first_arg in ("schedule", "cron"):
        cmd_schedule(remaining)
    elif first_arg in ("list", "ls", "courses"):
        cmd_list(remaining)
    elif first_arg in ("doctor", "check", "status"):
        cmd_doctor(remaining)
    elif first_arg in ("h", "help"):
        main([])
    else:
        cmd_get(argv)


if __name__ == "__main__":
    main()
