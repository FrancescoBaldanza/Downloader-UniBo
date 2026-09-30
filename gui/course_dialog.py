import os
from pathlib import Path
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QComboBox,
    QPushButton,
    QMessageBox,
    QFileDialog,
    QToolTip,
    QFrame,
    QApplication,
)

from core.database import Database, extract_moodle_course_id
from core.downloader import VirtualeDownloader


class CourseDialog(QDialog):
    def __init__(self, parent=None, db: Database = None, course_data=None):
        super().__init__(parent)
        self.db = db or Database()
        self.course_data = course_data  # If editing existing course
        self.is_edit_mode = bool(course_data)
        
        self.setWindowTitle("Modifica Corso" if self.is_edit_mode else "Nuovo Corso — UniBo Downloader")
        if self.is_edit_mode:
            self.setMinimumSize(540, 480)
            self.resize(540, 490)
        else:
            self.setMinimumSize(540, 360)
            self.resize(540, 370)

        self.setModal(True)
        self.txt_name = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)

        # Header
        title = QLabel("Modifica Corso" if self.is_edit_mode else "Definisci Corso")
        title.setStyleSheet("font-size: 19px; font-weight: 700; color: #1D1D1F;")
        
        subtitle_text = (
            "Modifica i dettagli del corso"
            if self.is_edit_mode
            else "Configura i dettagli del corso da sincronizzare da Virtuale"
        )
        subtitle = QLabel(subtitle_text)
        subtitle.setStyleSheet("font-size: 13px; color: #6E6E73;")
        
        layout.addWidget(title)
        layout.addWidget(subtitle)

        # Card
        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 20, 20, 20)
        card_layout.setSpacing(16)

        # 1. Name (Only in Edit Mode)
        if self.is_edit_mode:
            name_box = QVBoxLayout()
            name_box.setSpacing(6)

            name_header = QHBoxLayout()
            name_header.setSpacing(6)
            lbl_name = QLabel("Name:")
            lbl_name.setStyleSheet("font-weight: 600; font-size: 13px; color: #1D1D1F;")
            
            btn_info_name = QPushButton("?")
            btn_info_name.setObjectName("infoButton")
            btn_info_name.setFixedSize(22, 22)
            btn_info_name.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_info_name.setToolTip("Modifica il nome del corso")
            btn_info_name.clicked.connect(lambda: self._show_field_help(
                btn_info_name, "Modifica il nome del corso"
            ))

            name_header.addWidget(lbl_name)
            name_header.addWidget(btn_info_name)
            name_header.addStretch()
            name_box.addLayout(name_header)

            self.txt_name = QLineEdit()
            self.txt_name.setMinimumHeight(34)
            self.txt_name.setPlaceholderText("Es. Basi di Dati, Algoritmi, Fisica...")
            self.txt_name.setText(self.course_data.get("course_name", ""))
            name_box.addWidget(self.txt_name)
            card_layout.addLayout(name_box)

        # 2. Link
        link_box = QVBoxLayout()
        link_box.setSpacing(6)

        link_header = QHBoxLayout()
        link_header.setSpacing(6)
        lbl_link = QLabel("Link:")
        lbl_link.setStyleSheet("font-weight: 600; font-size: 13px; color: #1D1D1F;")

        link_help_text = (
            "Copia il link della pagina Virtuale e incollalo qui. "
            "Dovrebbe iniziare con https://virtuale.unibo.it/course/view.php?id= e continuare con un numero"
        )
        btn_info_link = QPushButton("?")
        btn_info_link.setObjectName("infoButton")
        btn_info_link.setFixedSize(22, 22)
        btn_info_link.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_info_link.setToolTip(link_help_text)
        btn_info_link.clicked.connect(lambda: self._show_field_help(btn_info_link, link_help_text))

        link_header.addWidget(lbl_link)
        link_header.addWidget(btn_info_link)
        link_header.addStretch()
        link_box.addLayout(link_header)

        self.txt_link = QLineEdit()
        self.txt_link.setMinimumHeight(34)
        self.txt_link.setPlaceholderText("https://virtuale.unibo.it/course/view.php?id=83152")
        if self.course_data:
            self.txt_link.setText(self.course_data.get("course_url", ""))
        link_box.addWidget(self.txt_link)
        card_layout.addLayout(link_box)

        # 3. Path
        path_box = QVBoxLayout()
        path_box.setSpacing(6)

        path_header = QHBoxLayout()
        path_header.setSpacing(6)
        lbl_path = QLabel("Path:")
        lbl_path.setStyleSheet("font-weight: 600; font-size: 13px; color: #1D1D1F;")

        path_help_text = "Scegli dove salvare la tua cartella"
        btn_info_path = QPushButton("?")
        btn_info_path.setObjectName("infoButton")
        btn_info_path.setFixedSize(22, 22)
        btn_info_path.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_info_path.setToolTip(path_help_text)
        btn_info_path.clicked.connect(lambda: self._show_field_help(btn_info_path, path_help_text))

        path_header.addWidget(lbl_path)
        path_header.addWidget(btn_info_path)
        path_header.addStretch()
        path_box.addLayout(path_header)

        path_row = QHBoxLayout()
        path_row.setSpacing(8)
        self.combo_path = QComboBox()
        self.combo_path.setEditable(True)
        self.combo_path.setMinimumHeight(34)
        
        # Populate standard default destinations
        home = str(Path.home())
        current_vault = self.db.vault_root
        default_paths = [
            current_vault,
            os.path.join(home, "Desktop", "UniBo"),
            os.path.join(home, "Documents", "UniBo"),
            os.path.join(home, "Downloads", "UniBo"),
        ]
        seen = set()
        unique_paths = []
        for p in default_paths:
            norm = os.path.normpath(p)
            if norm not in seen:
                seen.add(norm)
                unique_paths.append(norm)

        for p in unique_paths:
            self.combo_path.addItem(p)

        self.btn_browse = QPushButton("Sfoglia...")
        self.btn_browse.setMinimumHeight(34)
        self.btn_browse.clicked.connect(self._browse_directory)

        path_row.addWidget(self.combo_path, 1)
        path_row.addWidget(self.btn_browse)
        path_box.addLayout(path_row)
        card_layout.addLayout(path_box)

        layout.addWidget(card)

        # Action Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        button_layout.addStretch()

        self.btn_cancel = QPushButton("Annulla")
        self.btn_cancel.setMinimumHeight(32)
        self.btn_cancel.clicked.connect(self.reject)

        self.btn_save = QPushButton("Salva Corso")
        self.btn_save.setObjectName("primaryButton")
        self.btn_save.setMinimumHeight(32)
        self.btn_save.clicked.connect(self._save_course)

        button_layout.addWidget(self.btn_cancel)
        button_layout.addWidget(self.btn_save)
        layout.addLayout(button_layout)

    def _show_field_help(self, button_widget, text: str):
        pos = button_widget.mapToGlobal(button_widget.rect().bottomRight())
        QToolTip.showText(pos, text, button_widget, button_widget.rect(), 6000)

    def _browse_directory(self):
        current = self.combo_path.currentText().strip() or str(Path.home())
        dir_path = QFileDialog.getExistingDirectory(self, "Seleziona cartella di salvataggio", current)
        if dir_path:
            norm = os.path.normpath(dir_path)
            idx = self.combo_path.findText(norm)
            if idx == -1:
                self.combo_path.insertItem(0, norm)
                self.combo_path.setCurrentIndex(0)
            else:
                self.combo_path.setCurrentIndex(idx)

    def _save_course(self):
        link = self.txt_link.text().strip()
        path_chosen = self.combo_path.currentText().strip()

        if not link:
            QMessageBox.warning(self, "Link Mancante", "Inserisci l'URL o l'ID del corso su Virtuale.")
            self.txt_link.setFocus()
            return

        cid = extract_moodle_course_id(link)
        if not cid:
            QMessageBox.warning(
                self,
                "Link Non Valido",
                "Impossibile trovare un ID corso valido.\nAssicurati che sia del tipo:\nhttps://virtuale.unibo.it/course/view.php?id=12345"
            )
            self.txt_link.setFocus()
            return

        if self.is_edit_mode:
            name = self.txt_name.text().strip() if self.txt_name else ""
            if not name:
                QMessageBox.warning(self, "Nome Mancante", "Inserisci il nome del corso.")
                if self.txt_name:
                    self.txt_name.setFocus()
                return
        else:
            # Nuova inizializzazione: recupera automaticamente il nome predefinito dal corso su Virtuale
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            try:
                default_name = VirtualeDownloader.fetch_course_title(cid)
            finally:
                QApplication.restoreOverrideCursor()
            
            name = default_name or f"Corso {cid}"

        if path_chosen:
            self.db.set_vault_root(path_chosen)

        url = f"https://virtuale.unibo.it/course/view.php?id={cid}"
        self.db.upsert_course(course_id=cid, name=name, url=url, subfolder=name)

        self.accept()
