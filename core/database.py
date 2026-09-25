import os
import re
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DB_PATH = DATA_DIR / "unibo_downloader.db"
ENV_PATH = PROJECT_ROOT / ".env"


def secure_file(path: Path | str):
    try:
        p = Path(path)
        if p.exists():
            os.chmod(p, 0o600)
    except OSError:
        pass


def resolve_path(p: str) -> str:
    expanded = os.path.expanduser(p)
    if os.path.isabs(expanded):
        return os.path.normpath(expanded)
    return os.path.normpath(str(PROJECT_ROOT / expanded))


def extract_moodle_course_id(link_or_id: str) -> Optional[str]:
    link_or_id = str(link_or_id).strip()
    match_url = re.search(r"[?&]id=(\d+)", link_or_id)
    if match_url:
        return match_url.group(1)
    if link_or_id.isdigit():
        return link_or_id
    match_digits = re.search(r"\b(\d{4,8})\b", link_or_id)
    if match_digits:
        return match_digits.group(1)
    return None


class Database:
    def __init__(self, db_path: Optional[str] = None):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.db_path = str(db_path) if db_path else str(DB_PATH)
        self._init_db()
        secure_file(self.db_path)

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=15.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS courses (
                    course_id TEXT PRIMARY KEY,
                    course_name TEXT NOT NULL,
                    course_url TEXT NOT NULL,
                    subfolder TEXT,
                    last_scanned TEXT,
                    total_files INTEGER DEFAULT 0
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS downloads (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    resource_id TEXT UNIQUE NOT NULL,
                    course_id TEXT NOT NULL,
                    course_name TEXT NOT NULL,
                    section_name TEXT NOT NULL,
                    folder_name TEXT,
                    filename TEXT NOT NULL,
                    local_path TEXT NOT NULL,
                    professor_path TEXT NOT NULL,
                    moodle_url TEXT NOT NULL,
                    file_type TEXT NOT NULL,
                    file_size_bytes INTEGER NOT NULL,
                    sha256 TEXT,
                    download_datetime TEXT NOT NULL,
                    FOREIGN KEY (course_id) REFERENCES courses(course_id)
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_downloads_resource_id ON downloads(resource_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_downloads_course_id ON downloads(course_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_downloads_sha256 ON downloads(sha256)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_downloads_datetime ON downloads(download_datetime)")
            conn.commit()

    def get_setting(self, key: str, default: str = "") -> str:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM settings WHERE key = ? LIMIT 1", (key,))
            row = cursor.fetchone()
            return row["value"] if row else default

    def set_setting(self, key: str, value: str):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO settings (key, value) VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """, (key, value))
            conn.commit()
            secure_file(self.db_path)

    @property
    def vault_root(self) -> str:
        return resolve_path(self.get_setting("vault_root", "~/Desktop/UniBo"))

    def set_vault_root(self, path_str: str) -> str:
        resolved = resolve_path(path_str.strip())
        os.makedirs(resolved, exist_ok=True)
        self.set_setting("vault_root", path_str.strip())
        return resolved

    def get_course_folder(self, course_id: str, default_name: str = "") -> str:
        c = self.get_course(course_id)
        if c:
            sub = c.get("subfolder") or c.get("course_name") or str(course_id)
            return os.path.join(self.vault_root, sub)
        name = default_name or f"Corso_{course_id}"
        return os.path.join(self.vault_root, name)

    def define_course(self, name: str, link_or_id: str) -> Tuple[bool, str, str]:
        name = name.strip()
        if not name:
            return False, "", "Il nome del corso non puo' essere vuoto."

        course_id = extract_moodle_course_id(link_or_id)
        if not course_id:
            return False, "", f"Impossibile estrarre un ID corso Moodle valido da '{link_or_id}'."

        url = f"https://virtuale.unibo.it/course/view.php?id={course_id}"
        self.upsert_course(course_id=course_id, name=name, url=url, subfolder=name)
        return True, course_id, f"Corso '{name}' (ID: {course_id}) registrato con URL: {url}"

    def is_downloaded(self, resource_id: str) -> bool:
        if not resource_id:
            return False
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM downloads WHERE resource_id = ? LIMIT 1", (resource_id,))
            return cursor.fetchone() is not None

    def record_download(self, data: Dict[str, Any]):
        dt = data.get("download_datetime") or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO downloads (
                    resource_id, course_id, course_name, section_name, folder_name,
                    filename, local_path, professor_path, moodle_url, file_type,
                    file_size_bytes, sha256, download_datetime
                ) VALUES (
                    ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?,
                    ?, ?, ?
                )
                ON CONFLICT(resource_id) DO UPDATE SET
                    filename = excluded.filename,
                    local_path = excluded.local_path,
                    professor_path = excluded.professor_path,
                    file_size_bytes = excluded.file_size_bytes,
                    sha256 = excluded.sha256,
                    download_datetime = excluded.download_datetime
            """, (
                data["resource_id"],
                data.get("course_id", ""),
                data.get("course_name", ""),
                data.get("section_name", "Generale"),
                data.get("folder_name"),
                data["filename"],
                data["local_path"],
                data.get("professor_path", ""),
                data.get("moodle_url", ""),
                data.get("file_type", ""),
                data.get("file_size_bytes", 0),
                data.get("sha256", ""),
                dt
            ))

            if data.get("course_id"):
                cursor.execute("""
                    UPDATE courses 
                    SET total_files = (SELECT COUNT(*) FROM downloads WHERE course_id = ?)
                    WHERE course_id = ?
                """, (data["course_id"], data["course_id"]))

            conn.commit()
            secure_file(self.db_path)

    def upsert_course(self, course_id: str, name: str, url: str, subfolder: str = ""):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO courses (course_id, course_name, course_url, subfolder)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(course_id) DO UPDATE SET
                    course_name = excluded.course_name,
                    course_url = excluded.course_url,
                    subfolder = COALESCE(NULLIF(excluded.subfolder, ''), courses.subfolder)
            """, (str(course_id), name, url, subfolder or name))
            conn.commit()
            secure_file(self.db_path)

    def update_course_scanned(self, course_id: str):
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE courses 
                SET last_scanned = ?,
                    total_files = (SELECT COUNT(*) FROM downloads WHERE course_id = ?)
                WHERE course_id = ?
            """, (now_str, str(course_id), str(course_id)))
            conn.commit()

    def get_courses(self) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM courses ORDER BY course_name ASC")
            return [dict(row) for row in cursor.fetchall()]

    def get_course(self, course_id: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM courses WHERE course_id = ? LIMIT 1", (str(course_id),))
            row = cursor.fetchone()
            return dict(row) if row else None

    def find_course_by_name_or_id(self, query: str) -> Optional[Dict[str, Any]]:
        query = query.strip()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM courses WHERE course_id = ? LIMIT 1", (query,))
            row = cursor.fetchone()
            if row:
                return dict(row)

            cursor.execute("SELECT * FROM courses WHERE course_url LIKE ? LIMIT 1", (f"%{query}%",))
            row = cursor.fetchone()
            if row:
                return dict(row)

            cursor.execute("SELECT * FROM courses WHERE LOWER(course_name) LIKE LOWER(?) LIMIT 1", (f"%{query}%",))
            row = cursor.fetchone()
            if row:
                return dict(row)

            return None

    def get_downloads_for_course(self, course_id: str) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM downloads 
                WHERE course_id = ? 
                ORDER BY section_name ASC, folder_name ASC, filename ASC
            """, (str(course_id),))
            return [dict(row) for row in cursor.fetchall()]

    def get_stats(self) -> Dict[str, Any]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM downloads")
            total_files = cursor.fetchone()[0]

            cursor.execute("SELECT COALESCE(SUM(file_size_bytes), 0) FROM downloads")
            total_bytes = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM courses")
            total_courses = cursor.fetchone()[0]

            cursor.execute("""
                SELECT file_type, COUNT(*) as count 
                FROM downloads 
                GROUP BY file_type 
                ORDER BY count DESC
            """)
            type_distribution = {row["file_type"]: row["count"] for row in cursor.fetchall()}

            return {
                "total_files": total_files,
                "total_size_mb": round(total_bytes / (1024 * 1024), 2),
                "total_courses": total_courses,
                "type_distribution": type_distribution
            }
