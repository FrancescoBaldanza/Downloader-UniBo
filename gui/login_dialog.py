import os
import threading
from PyQt6.QtCore import Qt, pyqtSignal, QObject
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QProgressBar,
    QMessageBox,
    QFrame,
)

from core.auth import (
    get_current_moodle_session,
    verify_moodle_session,
    set_unibo_credentials,
    get_fresh_moodle_session,
    load_env_file,
)


class LoginWorker(QObject):
    finished = pyqtSignal(bool, str)
    status_update = pyqtSignal(str)

    def __init__(self, email: str, password: str, headless: bool = True):
        super().__init__()
        self.email = email
        self.password = password
        self.headless = headless

    def run(self):
        try:
            self.status_update.emit("Salvataggio credenziali...")
            set_unibo_credentials(self.email, self.password)

            self.status_update.emit("Verifica sessione Virtuale UniBo...")
            cookie = get_fresh_moodle_session(headless=self.headless)
            if cookie and verify_moodle_session(cookie):
                self.finished.emit(True, "Accesso riuscito e sessione Moodle collegata!")
            else:
                self.finished.emit(False, "Impossibile autenticare su Virtuale UniBo. Verifica email e password.")
        except Exception as e:
            self.finished.emit(False, f"Errore durante l'accesso: {e}")


class LoginDialog(QDialog):
    login_successful = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("UniBo Downloader — Accesso Virtuale")
        self.setMinimumSize(460, 440)
        self.resize(460, 450)
        self.setModal(True)
        load_env_file()
        self._init_ui()
        self._check_existing_session()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(16)

        # Header Icon & Titles
        header_layout = QVBoxLayout()
        header_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.setSpacing(6)

        title_lbl = QLabel("UniBo Downloader")
        title_lbl.setStyleSheet("font-size: 22px; font-weight: 700; color: #1D1D1F;")
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        subtitle_lbl = QLabel("Accedi con le tue credenziali d'Ateneo per iniziare")
        subtitle_lbl.setStyleSheet("font-size: 13px; color: #6E6E73;")
        subtitle_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        header_layout.addWidget(title_lbl)
        header_layout.addWidget(subtitle_lbl)
        layout.addLayout(header_layout)

        layout.addSpacing(8)

        # Card
        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(18, 18, 18, 18)
        card_layout.setSpacing(14)

        # Email
        lbl_email = QLabel("Email Istituzionale (@studio.unibo.it):")
        lbl_email.setStyleSheet("font-weight: 600; font-size: 12px; color: #3A3A3C;")
        self.txt_email = QLineEdit()
        self.txt_email.setMinimumHeight(34)
        self.txt_email.setPlaceholderText("nome.cognome@studio.unibo.it")
        self.txt_email.setText(os.getenv("UNIBO_EMAIL", ""))
        card_layout.addWidget(lbl_email)
        card_layout.addWidget(self.txt_email)

        # Password
        lbl_pwd = QLabel("Password UniBo:")
        lbl_pwd.setStyleSheet("font-weight: 600; font-size: 12px; color: #3A3A3C;")
        self.txt_pwd = QLineEdit()
        self.txt_pwd.setMinimumHeight(34)
        self.txt_pwd.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_pwd.setPlaceholderText("••••••••••••")
        self.txt_pwd.setText(os.getenv("UNIBO_PASSWORD", ""))
        card_layout.addWidget(lbl_pwd)
        card_layout.addWidget(self.txt_pwd)

        layout.addWidget(card)

        # Status & Progress
        self.status_lbl = QLabel("")
        self.status_lbl.setStyleSheet("font-size: 12px; font-weight: 500; color: #007AFF;")
        self.status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_lbl)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # indeterminate
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        self.btn_login_browser = QPushButton("Login con Finestra")
        self.btn_login_browser.setMinimumHeight(34)
        self.btn_login_browser.setToolTip("Apri browser visibile per 2FA o Microsoft Authenticator")
        self.btn_login_browser.clicked.connect(lambda: self._start_login(headless=False))

        self.btn_login = QPushButton("Accedi")
        self.btn_login.setObjectName("primaryButton")
        self.btn_login.setMinimumHeight(34)
        self.btn_login.clicked.connect(lambda: self._start_login(headless=True))

        btn_layout.addWidget(self.btn_login_browser)
        btn_layout.addWidget(self.btn_login)
        layout.addLayout(btn_layout)

    def _check_existing_session(self):
        cookie = get_current_moodle_session()
        if cookie:
            self.status_lbl.setText("Verifica sessione salvata...")
            self.progress_bar.show()
            self._set_inputs_enabled(False)

            def verify():
                valid = verify_moodle_session(cookie)
                self.progress_bar.hide()
                self._set_inputs_enabled(True)
                if valid:
                    self.status_lbl.setText("Collegamento attivo!")
                    self.login_successful.emit()
                    self.accept()
                else:
                    self.status_lbl.setText("Sessione scaduta. Inserisci le credenziali.")

            threading.Thread(target=verify, daemon=True).start()

    def _set_inputs_enabled(self, enabled: bool):
        self.txt_email.setEnabled(enabled)
        self.txt_pwd.setEnabled(enabled)
        self.btn_login.setEnabled(enabled)
        self.btn_login_browser.setEnabled(enabled)

    def _start_login(self, headless: bool = True):
        email = self.txt_email.text().strip()
        pwd = self.txt_pwd.text().strip()

        if not email or not pwd:
            QMessageBox.warning(self, "Campi obbligatori", "Inserisci sia l'email UniBo che la password.")
            return

        self._set_inputs_enabled(False)
        self.progress_bar.show()
        self.status_lbl.setText("Connessione a Virtuale in corso...")

        self.worker = LoginWorker(email, pwd, headless=headless)
        self.worker_thread = threading.Thread(target=self._run_worker, daemon=True)
        self.worker.status_update.connect(self.status_lbl.setText)
        self.worker.finished.connect(self._on_login_finished)
        self.worker_thread.start()

    def _run_worker(self):
        self.worker.run()

    def _on_login_finished(self, success: bool, message: str):
        self.progress_bar.hide()
        self._set_inputs_enabled(True)
        if success:
            self.status_lbl.setText(message)
            self.login_successful.emit()
            self.accept()
        else:
            self.status_lbl.setText(message)
            QMessageBox.critical(self, "Errore di Autenticazione", message)

