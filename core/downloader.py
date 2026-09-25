import hashlib
import html
import os
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import unquote, urlparse

import requests
from bs4 import BeautifulSoup

from core.auth import ensure_valid_session, USER_AGENT
from core.database import Database, extract_moodle_course_id
from integrations.notifications import notify


def sanitize_filename(name: str) -> str:
    if not name:
        return "senza_nome"
    name = html.unescape(name)
    name = unquote(name)
    name = re.sub(r'[\\/*?:"<>|\t\r\n]', "_", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name or "senza_nome"


def clean_section_or_folder_title(title: str, fallback: str = "Generale") -> str:
    if not title:
        return fallback
    title = html.unescape(title)
    title = re.sub(r"\s+", " ", title).strip()
    for noise in [
        r"^Sezione\s*\d*\s*:",
        r"\bFile\b",
        r"\bCartella\b",
        r"\bURL\b",
        r"\bDocumento\b",
        r"\bCaricato il.*$",
        r"\bModificato il.*$",
        r"\bAggiornato il.*$"
    ]:
        title = re.sub(noise, "", title, flags=re.IGNORECASE)
    title = re.sub(r"\s+", " ", title).strip()
    return sanitize_filename(title) or fallback


def parse_filename_from_response(response: requests.Response, fallback_title: str = "") -> str:
    cd = response.headers.get("Content-Disposition", "")
    if cd:
        match_utf8 = re.search(r"filename\*\s*=\s*UTF-8''([^;]+)", cd, re.IGNORECASE)
        if match_utf8:
            return sanitize_filename(unquote(match_utf8.group(1).strip('"\' ')))
        
        match_std = re.search(r'filename\s*=\s*"([^"]+)"', cd, re.IGNORECASE)
        if not match_std:
            match_std = re.search(r"filename\s*=\s*([^; ]+)", cd, re.IGNORECASE)
        if match_std:
            return sanitize_filename(match_std.group(1).strip('"\' '))

    parsed = urlparse(response.url)
    url_filename = os.path.basename(parsed.path)
    if url_filename and "." in url_filename and not url_filename.endswith(".php"):
        return sanitize_filename(url_filename)

    if fallback_title:
        base = sanitize_filename(fallback_title)
        ct = response.headers.get("Content-Type", "").lower()
        ext = ""
        if "pdf" in ct:
            ext = ".pdf"
        elif "zip" in ct:
            ext = ".zip"
        elif "wordprocessingml" in ct or "docx" in ct:
            ext = ".docx"
        elif "presentationml" in ct or "pptx" in ct:
            ext = ".pptx"
        elif "sql" in ct or "text/plain" in ct:
            if not os.path.splitext(base)[1]:
                ext = ".txt"

        if ext and not base.lower().endswith(ext):
            return f"{base}{ext}"
        return base

    return "materiale_senza_nome.bin"


class VirtualeDownloader:
    def __init__(self, db_path: Optional[str] = None, dry_run: bool = False):
        self.db = Database(db_path)
        self.dry_run = dry_run
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})

    def init_session(self) -> bool:
        cookie = ensure_valid_session(gui_fallback=True)
        if not cookie:
            print("[DOWNLOADER] [ERRORE] Impossibile stabilire una sessione Moodle valida.")
            return False
        self.session.cookies.set("MoodleSession", cookie, domain="virtuale.unibo.it")
        return True

    def scrape_course(self, course_id_or_url: str) -> Dict[str, Any]:
        cid_extracted = extract_moodle_course_id(str(course_id_or_url))
        if cid_extracted:
            course_id = cid_extracted
        else:
            db_found = self.db.find_course_by_name_or_id(str(course_id_or_url))
            if db_found:
                course_id = db_found["course_id"]
            else:
                print(f"[DOWNLOADER] [ERRORE] Corso non trovato per '{course_id_or_url}'")
                return {"success": False, "error": "Corso non trovato"}

        course_url = f"https://virtuale.unibo.it/course/view.php?id={course_id}"
        print(f"\n============================================================")
        print(f"[DOWNLOADER] Scansione Corso ID {course_id}...")
        print(f"URL: {course_url}")

        try:
            r = self.session.get(course_url, timeout=30)
            if "login" in r.url.lower():
                print("[DOWNLOADER] Sessione scaduta durante l'accesso al corso. Rinnovo...")
                if not self.init_session():
                    return {"success": False, "error": "Autenticazione fallita"}
                r = self.session.get(course_url, timeout=30)
            r.raise_for_status()
        except requests.RequestException as e:
            print(f"[DOWNLOADER] [ERRORE] Errore durante l'accesso al corso {course_id}: {e}")
            return {"success": False, "error": str(e)}

        soup = BeautifulSoup(r.text, "html.parser")

        h1 = soup.select_one("header h1, .page-header-headings h1, h1.h2, h1")
        course_name = sanitize_filename(h1.get_text(strip=True)) if h1 else f"Corso_{course_id}"

        self.db.upsert_course(course_id, course_name, course_url, subfolder=course_name)
        course_dir = self.db.get_course_folder(course_id, default_name=course_name)
        os.makedirs(course_dir, exist_ok=True)

        print(f"Nome Corso: {course_name}")
        print(f"Cartella File System: {course_dir}")
        print(f"============================================================")

        sections = soup.select("li[id^='section-'], li.section.main, ul.topics > li.section, ul.weeks > li.section, ul.sections > li")
        if not sections:
            sections = soup.find_all("li", class_=re.compile(r"\bsection\b"))
        if not sections:
            sections = [soup]

        stats = {
            "course_id": course_id,
            "course_name": course_name,
            "total_found": 0,
            "downloaded": 0,
            "already_present": 0,
            "errors": 0,
            "new_files": []
        }

        seen_resources_in_run = set()

        for sec_idx, sec in enumerate(sections):
            sec_title_tag = sec.find(["h3", "h4", "span", "div"], class_=re.compile(r"sectionname|section-title"))
            raw_sec_name = sec_title_tag.get_text(strip=True) if sec_title_tag else f"Sezione_{sec_idx}"
            sec_name = clean_section_or_folder_title(raw_sec_name, fallback=f"Sezione_{sec_idx}")

            res_links = sec.find_all("a", href=re.compile(r"/mod/resource/view\.php\?id=\d+"))
            folder_links = sec.find_all("a", href=re.compile(r"/mod/folder/view\.php\?id=\d+"))

            if not res_links and not folder_links:
                continue

            sec_dir = os.path.join(course_dir, sec_name)
            os.makedirs(sec_dir, exist_ok=True)

            print(f"\n[SEZIONE] {sec_name}")

            for link in res_links:
                href = link["href"]
                mod_match = re.search(r"id=(\d+)", href)
                if not mod_match:
                    continue
                mod_id = mod_match.group(1)
                res_unique_id = f"course_{course_id}_resource_{mod_id}"

                if res_unique_id in seen_resources_in_run:
                    continue
                seen_resources_in_run.add(res_unique_id)
                stats["total_found"] += 1

                link_text = clean_section_or_folder_title(link.get_text(separator=" ", strip=True))

                if self.db.is_downloaded(res_unique_id):
                    stats["already_present"] += 1
                    continue

                success, saved_name = self._download_single_resource(
                    url=href,
                    resource_id=res_unique_id,
                    course_id=course_id,
                    course_name=course_name,
                    section_name=sec_name,
                    folder_name=None,
                    link_text=link_text,
                    target_dir=sec_dir,
                )
                if success:
                    stats["downloaded"] += 1
                    stats["new_files"].append(saved_name)
                else:
                    stats["errors"] += 1

            for flink in folder_links:
                fhref = flink["href"]
                f_mod_match = re.search(r"id=(\d+)", fhref)
                if not f_mod_match:
                    continue
                folder_id = f_mod_match.group(1)

                folder_title_text = clean_section_or_folder_title(flink.get_text(separator=" ", strip=True), fallback=f"Cartella_{folder_id}")
                folder_target_dir = os.path.join(sec_dir, folder_title_text)
                os.makedirs(folder_target_dir, exist_ok=True)

                print(f"  [CARTELLA] {folder_title_text}")

                f_found, f_down, f_skip, f_err, f_names = self._process_moodle_folder(
                    folder_url=fhref,
                    folder_id=folder_id,
                    course_id=course_id,
                    course_name=course_name,
                    section_name=sec_name,
                    folder_name=folder_title_text,
                    target_dir=folder_target_dir,
                    seen_set=seen_resources_in_run
                )
                stats["total_found"] += f_found
                stats["downloaded"] += f_down
                stats["already_present"] += f_skip
                stats["errors"] += f_err
                stats["new_files"].extend(f_names)

        self.db.update_course_scanned(course_id)

        print(f"\n" + "-" * 60)
        print(f"Riepilogo '{course_name}':")
        print(f"   - Risorse totali: {stats['total_found']}")
        print(f"   - Gia' archiviate: {stats['already_present']}")
        print(f"   - Nuovi download: {stats['downloaded']}")
        if stats["errors"] > 0:
            print(f"   - Errori:         {stats['errors']}")
        print("-" * 60)

        if stats["downloaded"] > 0:
            notify("UniBo Downloader", f"Scaricati {stats['downloaded']} nuovi file per {course_name}!")

        stats["success"] = True
        return stats

    def _process_moodle_folder(
        self,
        folder_url: str,
        folder_id: str,
        course_id: str,
        course_name: str,
        section_name: str,
        folder_name: str,
        target_dir: str,
        seen_set: set
    ) -> Tuple[int, int, int, int, List[str]]:
        found = 0
        downloaded = 0
        skipped = 0
        errors = 0
        names = []

        try:
            r = self.session.get(folder_url, timeout=30)
            r.raise_for_status()
            soup = BeautifulSoup(r.text, "html.parser")
            
            file_links = soup.find_all("a", href=re.compile(r"/pluginfile\.php/"))
            
            for fl in file_links:
                href = fl["href"]
                raw_name = fl.get_text(strip=True)
                file_title = clean_section_or_folder_title(raw_name)
                
                file_unique_id = f"course_{course_id}_folder_{folder_id}_{sanitize_filename(file_title or os.path.basename(href))}"
                
                if file_unique_id in seen_set:
                    continue
                seen_set.add(file_unique_id)
                found += 1

                if self.db.is_downloaded(file_unique_id):
                    skipped += 1
                    continue

                success, saved_name = self._download_single_resource(
                    url=href,
                    resource_id=file_unique_id,
                    course_id=course_id,
                    course_name=course_name,
                    section_name=section_name,
                    folder_name=folder_name,
                    link_text=file_title,
                    target_dir=target_dir,
                )
                if success:
                    downloaded += 1
                    names.append(saved_name)
                else:
                    errors += 1

        except Exception as e:
            print(f"[DOWNLOADER] [ERRORE] Errore durante l'accesso alla cartella Moodle {folder_name}: {e}")
            errors += 1

        return found, downloaded, skipped, errors, names

    def _download_single_resource(
        self,
        url: str,
        resource_id: str,
        course_id: str,
        course_name: str,
        section_name: str,
        folder_name: Optional[str],
        link_text: str,
        target_dir: str,
    ) -> Tuple[bool, str]:
        disp_title = link_text or "Nuovo elemento"
        print(f"    [DOWNLOAD] '{disp_title}'")

        if self.dry_run:
            print(f"       [DRY-RUN] Simulazione download completata.")
            return True, disp_title

        try:
            head_res = self.session.get(url, allow_redirects=True, stream=True, timeout=30)
            head_res.raise_for_status()

            content_type = head_res.headers.get("Content-Type", "").lower()
            if "text/html" in content_type:
                soup = BeautifulSoup(head_res.text, "html.parser")
                real_file_tag = (
                    soup.find("object", data=re.compile(r"pluginfile\.php"))
                    or soup.find("iframe", src=re.compile(r"pluginfile\.php"))
                    or soup.find("embed", src=re.compile(r"pluginfile\.php"))
                    or soup.find("a", href=re.compile(r"pluginfile\.php"))
                    or soup.find("div", class_="resourcecontent")
                )
                if real_file_tag:
                    real_url = (
                        real_file_tag.get("data")
                        or real_file_tag.get("src")
                        or real_file_tag.get("href")
                    )
                    if real_url:
                        head_res = self.session.get(real_url, allow_redirects=True, stream=True, timeout=30)
                        head_res.raise_for_status()

            filename = parse_filename_from_response(head_res, fallback_title=link_text)
            save_path = os.path.join(target_dir, filename)

            hasher = hashlib.sha256()
            total_bytes = 0
            with open(save_path, "wb") as f:
                for chunk in head_res.iter_content(chunk_size=65536):
                    if chunk:
                        f.write(chunk)
                        hasher.update(chunk)
                        total_bytes += len(chunk)

            hash_hex = hasher.hexdigest()
            file_ext = os.path.splitext(filename)[1].lower() or ".bin"

            if folder_name:
                professor_path = f"{course_name} / {section_name} / {folder_name} / {filename}"
            else:
                professor_path = f"{course_name} / {section_name} / {filename}"

            self.db.record_download({
                "resource_id": resource_id,
                "course_id": course_id,
                "course_name": course_name,
                "section_name": section_name,
                "folder_name": folder_name,
                "filename": filename,
                "local_path": os.path.abspath(save_path),
                "professor_path": professor_path,
                "moodle_url": url,
                "file_type": file_ext,
                "file_size_bytes": total_bytes,
                "sha256": hash_hex,
                "download_datetime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            })

            size_str = f"{total_bytes / (1024 * 1024):.2f} MB" if total_bytes > 1024 * 1024 else f"{total_bytes / 1024:.1f} KB"
            print(f"       [SALVATO] '{filename}' ({size_str}) -> {professor_path}")
            return True, filename

        except requests.RequestException as e:
            print(f"       [ERRORE] Download {url}: {e}")
            return False, ""

    def run_all(self):
        if not self.init_session():
            return

        db_courses = self.db.get_courses()
        if not db_courses:
            print("[DOWNLOADER] [AVVISO] Nessun corso configurato. Usa: dlub -def <Nome> <ID o URL>")
            return

        print(f"\n[DOWNLOADER] Avvio sincronizzazione per {len(db_courses)} corsi...")
        for c in db_courses:
            self.scrape_course(c["course_id"])

        print("\nSincronizzazione completata per tutti i corsi.")
