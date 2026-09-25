import os
import signal
import subprocess
import time
from pathlib import Path
from subprocess import CalledProcessError
from typing import Optional

from core.database import secure_file, ENV_PATH
from integrations.notifications import notify

BROWSER_PROFILE_DIR = os.path.expanduser("~/.unibo_playwright_profile")
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)


def load_env_file():
    if not ENV_PATH.exists():
        return
    try:
        from dotenv import load_dotenv
        load_dotenv(dotenv_path=ENV_PATH)
    except ImportError:
        with open(ENV_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, val = line.split("=", 1)
                key, val = key.strip(), val.strip()
                if val.startswith('"') and val.endswith('"'):
                    val = val[1:-1]
                elif val.startswith("'") and val.endswith("'"):
                    val = val[1:-1]
                os.environ.setdefault(key, val)
    secure_file(ENV_PATH)


load_env_file()


def cleanup_residual_browsers():
    my_pid = os.getpid()
    profile = BROWSER_PROFILE_DIR
    try:
        out = subprocess.check_output(["ps", "aux"]).decode("utf-8", errors="ignore")
        killed = 0
        for line in out.splitlines():
            if (
                ("Chromium.app" in line or "chrome-mac" in line or profile in line or "ms-playwright" in line)
                and "python" not in line.lower()
            ):
                parts = line.split()
                if len(parts) > 1:
                    try:
                        pid = int(parts[1])
                        if pid != my_pid:
                            os.kill(pid, signal.SIGTERM)
                            killed += 1
                    except (ValueError, ProcessLookupError):
                        pass
        if killed > 0:
            time.sleep(0.5)
    except CalledProcessError:
        pass


def set_unibo_credentials(email: str, password: str, moodle_session: Optional[str] = None):
    existing_env = {}
    if ENV_PATH.exists():
        try:
            with open(ENV_PATH, "r", encoding="utf-8") as f:
                for line in f:
                    if "=" in line and not line.strip().startswith("#"):
                        k, v = line.strip().split("=", 1)
                        existing_env[k.strip()] = v.strip()
        except OSError:
            pass

    if email:
        existing_env["UNIBO_EMAIL"] = email.strip()
    if password:
        existing_env["UNIBO_PASSWORD"] = password.strip()
    if moodle_session:
        existing_env["MOODLE_SESSION"] = moodle_session.strip()

    with open(ENV_PATH, "w", encoding="utf-8") as f:
        for k, v in existing_env.items():
            f.write(f"{k}={v}\n")

    secure_file(ENV_PATH)
    load_env_file()


def save_moodle_cookie(cookie: str):
    if not cookie:
        return

    existing_env = {}
    if ENV_PATH.exists():
        try:
            with open(ENV_PATH, "r", encoding="utf-8") as f:
                for line in f:
                    if "=" in line and not line.strip().startswith("#"):
                        k, v = line.strip().split("=", 1)
                        existing_env[k.strip()] = v.strip()
        except OSError:
            pass

    existing_env["MOODLE_SESSION"] = cookie.strip()
    with open(ENV_PATH, "w", encoding="utf-8") as f:
        for k, v in existing_env.items():
            f.write(f"{k}={v}\n")

    secure_file(ENV_PATH)
    os.environ["MOODLE_SESSION"] = cookie.strip()
    load_env_file()


def get_current_moodle_session() -> str:
    load_env_file()
    return os.getenv("MOODLE_SESSION", "").strip()


def verify_moodle_session(cookie: Optional[str] = None) -> bool:
    import requests

    c = cookie or get_current_moodle_session()
    if not c:
        return False

    session = requests.Session()
    session.cookies.set("MoodleSession", c, domain="virtuale.unibo.it")
    session.headers.update({"User-Agent": USER_AGENT})

    for attempt in range(1, 4):
        try:
            r = session.get("https://virtuale.unibo.it/my/", allow_redirects=True, timeout=12)
            if "login" not in r.url.lower() and r.status_code == 200:
                return True
            return False
        except requests.exceptions.RequestException:
            if attempt < 3:
                time.sleep(1.5 * attempt)
            else:
                return False
    return False


def get_fresh_moodle_session(headless: bool = True) -> str:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[AUTH] Playwright non e' installato. Per il login automatico esegui:")
        print("   pip install playwright && playwright install chromium")
        return ""

    email = os.getenv("UNIBO_EMAIL", "").strip()
    password = os.getenv("UNIBO_PASSWORD", "").strip()

    if not email or not password:
        print("[AUTH] Credenziali UniBo mancanti. Inseriscile con: dlub -init <EMAIL> <PASSWORD>")
        return ""

    os.makedirs(BROWSER_PROFILE_DIR, exist_ok=True)
    moodle_cookie = ""

    with sync_playwright() as p:
        print(f"[AUTH] Avvio browser (headless={headless})...")
        try:
            context = p.chromium.launch_persistent_context(
                user_data_dir=BROWSER_PROFILE_DIR,
                headless=headless,
                viewport={"width": 1280, "height": 800},
                args=["--disable-blink-features=AutomationControlled"],
            )
        except Exception as launch_err:
            print(f"[AUTH] [ERRORE] Impossibile avviare il browser con il profilo: {launch_err}")
            cleanup_residual_browsers()
            return ""

        page = context.new_page()

        try:
            print("[AUTH] Apertura portale Virtuale UniBo...")
            page.goto("https://virtuale.unibo.it/login/index.php", wait_until="domcontentloaded", timeout=30000)
            time.sleep(2)

            if "virtuale.unibo.it" in page.url and "/login/" not in page.url and "idp.unibo.it" not in page.url:
                print("[AUTH] Sessione gia' attiva su Virtuale.")
            else:
                btn_unibo = page.locator(".idp.btnUnibo").first
                if btn_unibo.is_visible():
                    print("[AUTH] Selezione modalita' 'Entra con UNIBO'...")
                    try:
                        with page.expect_navigation(timeout=10000):
                            page.evaluate("HRD.selection('AD AUTHORITY')")
                    except Exception:
                        btn_unibo.click()
                    page.wait_for_load_state("domcontentloaded")
                    time.sleep(1)

                if page.locator("#userNameInput").is_visible():
                    print("[AUTH] Autenticazione credenziali d'Ateneo...")
                    page.locator("#userNameInput").fill(email)
                    page.locator("#passwordInput").fill(password)
                    if page.locator("#kmsiInput").is_visible():
                        try:
                            page.locator("#kmsiInput").check()
                        except Exception:
                            pass
                    page.locator("#submitButton").click()
                    time.sleep(2)

                elif page.locator("#emailInput").is_visible():
                    page.locator("#emailInput").fill(email)
                    if page.locator("#HomeRealmByEmail").is_visible():
                        page.locator("#HomeRealmByEmail").click()
                    else:
                        page.keyboard.press("Enter")
                    time.sleep(2)

                if "login.microsoftonline.com" in page.url:
                    print("[AUTH] Accesso Microsoft Identity...")
                    if page.locator('input[type="email"]').is_visible():
                        page.locator('input[type="email"]').fill(email)
                        page.locator('input[type="submit"], #idSIButton9').click()
                        time.sleep(2)

                    if page.locator('input[type="password"]').is_visible():
                        page.locator('input[type="password"]').fill(password)
                        page.locator('input[type="submit"], #idSIButton9').click()
                        time.sleep(3)

                    if "login.microsoftonline.com" in page.url and (
                        page.locator("#idDiv_SAOTCAS_Title").is_visible()
                        or "approva" in page.content().lower()
                        or "autenticazione" in page.content().lower()
                    ):
                        print("\n[AUTH] Richiesta 2FA inviata. Approva la notifica su Microsoft Authenticator...")
                        notify("Virtuale Unibo", "Conferma la notifica su Microsoft Authenticator")
                        page.wait_for_url(lambda u: "virtuale.unibo.it" in u or "kmsi" in u.lower(), timeout=90000)

                    if page.locator('#KmsiCheckboxField, input[name="DontShowAgain"]').is_visible():
                        try:
                            page.locator('#KmsiCheckboxField, input[name="DontShowAgain"]').check()
                        except Exception:
                            pass
                    if page.locator("#idSIButton9").is_visible():
                        page.locator("#idSIButton9").click()
                        time.sleep(2)

                page.wait_for_url(
                    lambda u: "virtuale.unibo.it" in u and "login" not in u and "auth" not in u,
                    timeout=45000,
                )

            cookies = context.cookies("https://virtuale.unibo.it")
            for c in cookies:
                if c.get("name") == "MoodleSession":
                    moodle_cookie = c.get("value")
                    break

            if moodle_cookie:
                if verify_moodle_session(moodle_cookie):
                    print("[AUTH] Login verificato con successo. Cookie MoodleSession attivo.")
                    save_moodle_cookie(moodle_cookie)
                else:
                    print("[AUTH] [ERRORE] Cookie estratto ma non valido all'interrogazione HTTP.")
                    moodle_cookie = ""
            else:
                print("[AUTH] [ERRORE] Cookie MoodleSession non trovato nei cookie del browser.")

        except Exception as e:
            print(f"[AUTH] [ERRORE] Errore durante l'autenticazione: {e}")
        finally:
            try:
                for pg in context.pages:
                    try:
                        pg.close()
                    except Exception:
                        pass
                context.close()
            except Exception:
                pass

    cleanup_residual_browsers()
    return moodle_cookie


def ensure_valid_session(gui_fallback: bool = True) -> str:
    current_cookie = get_current_moodle_session()
    if current_cookie and verify_moodle_session(current_cookie):
        return current_cookie

    print("[AUTH] Sessione Moodle scaduta o non presente. Tentativo rinnovo automatico...")
    new_cookie = get_fresh_moodle_session(headless=True)
    if new_cookie:
        return new_cookie

    if gui_fallback:
        print("\n[AUTH] Login in corso con interfaccia visuale...")
        notify("UniBo Downloader", "E' richiesto il login su Virtuale.")
        new_cookie = get_fresh_moodle_session(headless=False)
        if new_cookie:
            return new_cookie

    return ""
