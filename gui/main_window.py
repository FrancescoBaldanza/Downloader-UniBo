import os
import subprocess
import threading
from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal, QObject
from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QListWidget,
    QListWidgetItem,
    QStackedWidget,
    QProgressBar,
    QSplitter,
    QFrame,
    QMessageBox,
)

from core.database import Database
from core.downloader import VirtualeDownloader
from gui.course_dialog import CourseDialog
from gui.schedule_widget import ScheduleWidget

class DownloadWorker(QObject):
    finished = pyqtSignal(dict)
    status_updated = pyqtSignal(str)
    progress_updated = pyqtSignal(str, int, int)

    def __init__(self, course_query: str):
        super().__init__()
        self.course_query = course_query

    def run(self):
        try:
            downloader = VirtualeDownloader(
                progress_callback=self._on_progress,
                status_callback=self._on_status,
            )
            if not downloader.init_session():
                self.finished.emit({"success": False, "error": "Impossibile autenticare la sessione."})
                return

            if self.course_query.lower() in ("all", "*"):
                courses = downloader.db.get_courses()
                total_new = 0
                for c in courses:
                    res = downloader.scrape_course(c["course_id"])
                    total_new += res.get("downloaded", 0)
                self.finished.emit({"success": True, "downloaded": total_new, "is_all": True})
            else:
                res = downloader.scrape_course(self.course_query)
                self.finished.emit(res)
        except Exception as e:
            self.finished.emit({"success": False, "error": str(e)})

    def _on_progress(self, filename: str, downloaded_bytes: int, total_bytes: int):
        self.progress_updated.emit(filename, downloaded_bytes, total_bytes)

    def _on_status(self, msg: str):
        self.status_updated.emit(msg)



class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.db = Database()
        self.current_selected_course_id = None
        self.setWindowTitle("UniBo Downloader — macOS")
        self.resize(1020, 680)
        self.setMinimumSize(850, 550)
        self._init_ui()
        self.refresh_courses_list()

    def _init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setHandleWidth(1)

        self.sidebar_widget = self._build_sidebar()
        self.splitter.addWidget(self.sidebar_widget)

        # Content Area
        self.stack = QStackedWidget()
        self.empty_state_page = self._build_empty_state()
        self.course_detail_page = self._build_course_detail()

        self.stack.addWidget(self.empty_state_page)
        self.stack.addWidget(self.course_detail_page)

        self.splitter.addWidget(self.stack)
        self.splitter.setSizes([260, 760])

        main_layout.addWidget(self.splitter)

    def _build_sidebar(self) -> QWidget:
        widget = QWidget()
        widget.setObjectName("sidebar")
        widget.setStyleSheet("background-color: #E8E8ED;")
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(12, 16, 12, 12)
        layout.setSpacing(10)

        header = QHBoxLayout()
        title_lbl = QLabel("I Miei Corsi")
        title_lbl.setStyleSheet("font-size: 15px; font-weight: 700; color: #1D1D1F;")
        header.addWidget(title_lbl)
        header.addStretch()

        btn_add = QPushButton("+")
        btn_add.setObjectName("plusButton")
        btn_add.setFixedSize(26, 26)
        btn_add.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_add.setToolTip("Aggiungi nuovo corso")
        btn_add.clicked.connect(self._open_new_course_dialog)
        header.addWidget(btn_add)
        layout.addLayout(header)

        self.course_list_widget = QListWidget()
        self.course_list_widget.setObjectName("sidebarList")
        self.course_list_widget.currentRowChanged.connect(self._on_course_selected)
        layout.addWidget(self.course_list_widget, 1)

        # Footer
        self.btn_download_all = QPushButton("Sincronizza Tutti")
        self.btn_download_all.setStyleSheet("font-size: 12px; font-weight: 600; padding: 8px;")
        self.btn_download_all.clicked.connect(self._download_all_courses)
        layout.addWidget(self.btn_download_all)

        return widget

    def _build_empty_state(self) -> QWidget:
        page = QFrame()
        page.setObjectName("contentPanel")
        layout = QVBoxLayout(page)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(16)

        title_lbl = QLabel("Nessun Corso Configurato")
        title_lbl.setStyleSheet("font-size: 22px; font-weight: 700; color: #1D1D1F;")
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        desc_lbl = QLabel(
            "Collega il tuo primo insegnamento da Virtuale UniBo\n"
            "per scaricare automaticamente slide, appunti ed esercitazioni."
        )
        desc_lbl.setStyleSheet("font-size: 14px; color: #6E6E73; line-height: 1.4;")
        desc_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        btn_define = QPushButton("Definisci un Corso")
        btn_define.setObjectName("primaryButton")
        btn_define.setStyleSheet("font-size: 14px; font-weight: 600; padding: 10px 24px; border-radius: 8px;")
        btn_define.clicked.connect(self._open_new_course_dialog)

        layout.addStretch()
        layout.addWidget(title_lbl)
        layout.addWidget(desc_lbl)
        layout.addSpacing(10)
        layout.addWidget(btn_define, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addStretch()

        return page

    def _build_course_detail(self) -> QWidget:
        page = QFrame()
        page.setObjectName("contentPanel")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        # 1. TOP HEADER: Course Title + 'Apri Pagina Virtuale' + 'Download' in alto a destra
        top_header = QHBoxLayout()
        top_header.setSpacing(12)

        self.lbl_detail_name = QLabel("Nome Corso")
        self.lbl_detail_name.setStyleSheet("font-size: 20px; font-weight: 700; color: #1D1D1F;")
        top_header.addWidget(self.lbl_detail_name, 1)

        # Tasto a sinistra di Download che manda alla pagina di Virtuale
        self.btn_open_web = QPushButton("Apri Pagina Virtuale")
        self.btn_open_web.setMinimumHeight(32)
        self.btn_open_web.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_open_web.setToolTip("Apri la pagina web di questo corso su Virtuale UniBo")
        self.btn_open_web.clicked.connect(self._open_course_web_page)
        top_header.addWidget(self.btn_open_web)

        # Top Right: Download Button
        self.btn_download = QPushButton("Download")
        self.btn_download.setObjectName("downloadButton")
        self.btn_download.setMinimumHeight(32)
        self.btn_download.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_download.clicked.connect(self._download_current_course)
        top_header.addWidget(self.btn_download)

        layout.addLayout(top_header)

        # Info bar: Path & Finder button
        path_card = QFrame()
        path_card.setObjectName("card")
        path_layout = QHBoxLayout(path_card)
        path_layout.setContentsMargins(12, 8, 12, 8)

        self.lbl_detail_path = QLabel("Cartella locale: /...")
        self.lbl_detail_path.setStyleSheet("font-size: 12px; color: #3A3A3C;")
        path_layout.addWidget(self.lbl_detail_path, 1)

        btn_open_finder = QPushButton("Apri nel Finder")
        btn_open_finder.setStyleSheet("font-size: 11px; padding: 4px 10px;")
        btn_open_finder.clicked.connect(self._open_in_finder)
        path_layout.addWidget(btn_open_finder)

        btn_edit_course = QPushButton("Modifica")
        btn_edit_course.setStyleSheet("font-size: 11px; padding: 4px 10px;")
        btn_edit_course.clicked.connect(self._edit_current_course)
        path_layout.addWidget(btn_edit_course)

        layout.addWidget(path_card)

        # Download Progress & Status bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)

        self.status_msg_lbl = QLabel("")
        self.status_msg_lbl.setStyleSheet("font-size: 12px; font-weight: 600; color: #007AFF;")
        self.status_msg_lbl.hide()
        layout.addWidget(self.status_msg_lbl)

        # 2. CENTER: Sincronizzazione automatica
        self.schedule_widget = ScheduleWidget()
        layout.addWidget(self.schedule_widget)

        # 3. BOTTOM: Spazio bianco pulito
        layout.addStretch()

        return page

    def refresh_courses_list(self):
        courses = self.db.get_courses()
        self.course_list_widget.clear()

        if not courses:
            # Mostra schermata vuota
            self.stack.setCurrentWidget(self.empty_state_page)
            self.btn_download_all.setEnabled(False)
            return

        self.btn_download_all.setEnabled(True)

        for c in courses:
            name = c["course_name"]
            num_files = c.get("total_files", 0)
            item = QListWidgetItem(f"{name} ({num_files})")
            item.setData(Qt.ItemDataRole.UserRole, c["course_id"])
            self.course_list_widget.addItem(item)

        # Seleziona il primo corso o mantiene quello precedentemente attivo
        if self.current_selected_course_id:
            for i in range(self.course_list_widget.count()):
                it = self.course_list_widget.item(i)
                if it.data(Qt.ItemDataRole.UserRole) == self.current_selected_course_id:
                    self.course_list_widget.setCurrentRow(i)
                    return
        self.course_list_widget.setCurrentRow(0)

    def _on_course_selected(self, row: int):
        if row < 0:
            return

        item = self.course_list_widget.item(row)
        if not item:
            return

        course_id = item.data(Qt.ItemDataRole.UserRole)
        self.current_selected_course_id = course_id
        course = self.db.get_course(course_id)

        if not course:
            return

        self.stack.setCurrentWidget(self.course_detail_page)

        name = course["course_name"]
        folder = self.db.get_course_folder(course_id, default_name=name)

        self.lbl_detail_name.setText(name)
        self.lbl_detail_path.setText(f"Cartella locale: {folder}")

        # Aggiorna sincronizzazioni automatiche
        self.schedule_widget.set_course(name)

    def _open_course_web_page(self):
        if not self.current_selected_course_id:
            return
        c = self.db.get_course(self.current_selected_course_id)
        if c and c.get("course_url"):
            subprocess.run(["open", c["course_url"]])

    def _open_in_finder(self):
        if not self.current_selected_course_id:
            return
        c = self.db.get_course(self.current_selected_course_id)
        if c:
            folder = self.db.get_course_folder(self.current_selected_course_id, default_name=c["course_name"])
            os.makedirs(folder, exist_ok=True)
            subprocess.run(["open", folder])

    def _open_new_course_dialog(self):
        dialog = CourseDialog(self, db=self.db)
        if dialog.exec():
            self.refresh_courses_list()

    def _edit_current_course(self):
        if not self.current_selected_course_id:
            return
        c = self.db.get_course(self.current_selected_course_id)
        if not c:
            return
        dialog = CourseDialog(self, db=self.db, course_data=c)
        if dialog.exec():
            self.refresh_courses_list()

    def _set_download_ui_state(self, running: bool, message: str = ""):
        self.btn_download.setEnabled(not running)
        self.btn_download_all.setEnabled(not running)
        if running:
            self.progress_bar.show()
            self.status_msg_lbl.setText(message)
            self.status_msg_lbl.show()
        else:
            self.progress_bar.hide()
            if message:
                self.status_msg_lbl.setText(message)
                self.status_msg_lbl.show()

    def _download_current_course(self):
        if not self.current_selected_course_id:
            return

        self._set_download_ui_state(True, "Avvio sincronizzazione...")

        self.worker = DownloadWorker(self.current_selected_course_id)
        self.worker.status_updated.connect(self._on_download_status)
        self.worker.progress_updated.connect(self._on_download_progress)
        self.worker.finished.connect(self._on_download_finished)
        self.thread = threading.Thread(target=self.worker.run, daemon=True)
        self.thread.start()

    def _download_all_courses(self):
        self._set_download_ui_state(True, "Avvio sincronizzazione di tutti i corsi...")

        self.worker = DownloadWorker("all")
        self.worker.status_updated.connect(self._on_download_status)
        self.worker.progress_updated.connect(self._on_download_progress)
        self.worker.finished.connect(self._on_download_finished)
        self.thread = threading.Thread(target=self.worker.run, daemon=True)
        self.thread.start()

    def _on_download_status(self, msg: str):
        self.status_msg_lbl.setText(msg)

    def _on_download_progress(self, filename: str, downloaded: int, total: int):
        if total > 0:
            percent = min(100, int((downloaded / total) * 100))
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(percent)

            cur_mb = downloaded / (1024 * 1024)
            tot_mb = total / (1024 * 1024)
            if tot_mb >= 1.0:
                size_str = f"{cur_mb:.1f} / {tot_mb:.1f} MB"
            else:
                size_str = f"{downloaded / 1024:.0f} / {total / 1024:.0f} KB"

            self.status_msg_lbl.setText(f"Download: {filename} ({size_str} — {percent}%)")
        else:
            self.progress_bar.setRange(0, 0)
            cur_mb = downloaded / (1024 * 1024)
            if cur_mb >= 1.0:
                size_str = f"{cur_mb:.1f} MB"
            else:
                size_str = f"{downloaded / 1024:.0f} KB"
            self.status_msg_lbl.setText(f"Download: {filename} ({size_str} scaricati...)")

    def _on_download_finished(self, result: dict):
        if result.get("success"):
            new_files = result.get("downloaded", 0)
            msg = f"Sincronizzazione completata! ({new_files} nuovi file scaricati)"
            self._set_download_ui_state(False, msg)
            self.refresh_courses_list()
        else:
            err = result.get("error", "Errore sconosciuto")
            self._set_download_ui_state(False, f"Errore: {err}")
            QMessageBox.critical(self, "Errore Download", f"Si è verificato un errore:\n{err}")

