from PyQt6.QtCore import Qt, QTime
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTimeEdit,
    QComboBox,
    QScrollArea,
    QFrame,
    QMessageBox,
)

from core.scheduler import (
    ScheduleItem,
    get_course_schedules,
    setup_cron_schedule,
    remove_cron_schedule,
)


class ScheduleItemCard(QFrame):
    def __init__(self, course_name: str, item: ScheduleItem, on_delete_callback, parent=None):
        super().__init__(parent)
        self.course_name = course_name
        self.item = item
        self.on_delete_callback = on_delete_callback
        self.setObjectName("alarmCard")
        self._init_ui()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(12)

        # [Download] Tag in verde
        lbl_tag = QLabel("[Download]")
        lbl_tag.setStyleSheet("font-size: 12px; font-weight: 700; color: #34C759;")
        layout.addWidget(lbl_tag)

        # Time and Frequency Info
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)

        time_lbl = QLabel(self.item.time_str)
        time_lbl.setStyleSheet("font-size: 16px; font-weight: 700; color: #1D1D1F;")

        desc_lbl = QLabel(self.item.days_summary)
        desc_lbl.setStyleSheet("font-size: 12px; color: #6E6E73;")

        info_layout.addWidget(time_lbl)
        info_layout.addWidget(desc_lbl)
        layout.addLayout(info_layout, 1)

        # Status badge
        badge = QLabel("ATTIVA")
        badge.setStyleSheet(
            "background-color: #E8F5E9; color: #2E7D32; font-size: 10px; font-weight: 700; "
            "padding: 3px 8px; border-radius: 6px;"
        )
        layout.addWidget(badge)

        # Delete button: tutto rosso con scritta bianca
        btn_del = QPushButton("Rimuovi")
        btn_del.setObjectName("dangerButton")
        btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_del.clicked.connect(lambda: self.on_delete_callback(self.item.time_str, self.item.frequency_type))
        layout.addWidget(btn_del)


class ScheduleWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_course_name = ""
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # Title
        header_layout = QHBoxLayout()
        title_box = QVBoxLayout()
        title_box.setSpacing(2)

        title = QLabel("Sincronizzazione automatica")
        title.setStyleSheet("font-size: 16px; font-weight: 700; color: #1D1D1F;")

        subtitle = QLabel("Pianifica i momenti in cui verificare e scaricare nuovi materiali da Virtuale")
        subtitle.setStyleSheet("font-size: 12px; color: #6E6E73;")

        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        header_layout.addLayout(title_box)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        # Add New Schedule Bar
        add_bar = QFrame()
        add_bar.setObjectName("card")
        add_outer_layout = QVBoxLayout(add_bar)
        add_outer_layout.setContentsMargins(14, 12, 14, 12)
        add_outer_layout.setSpacing(10)

        # Time
        top_row = QHBoxLayout()
        top_row.setSpacing(10)

        lbl_time = QLabel("Orario:")
        lbl_time.setStyleSheet("font-weight: 600; font-size: 12px; color: #3A3A3C;")
        top_row.addWidget(lbl_time)

        self.time_edit = QTimeEdit()
        self.time_edit.setDisplayFormat("HH:mm")
        self.time_edit.setTime(QTime(8, 0))
        self.time_edit.setMinimumHeight(32)
        self.time_edit.setStyleSheet("font-size: 14px; font-weight: 600; min-width: 85px;")
        top_row.addWidget(self.time_edit)

        lbl_freq = QLabel("Frequenza:")
        lbl_freq.setStyleSheet("font-weight: 600; font-size: 12px; color: #3A3A3C;")
        top_row.addWidget(lbl_freq)

        self.combo_freq = QComboBox()
        self.combo_freq.setMinimumHeight(32)
        self.combo_freq.addItem("Tutti i giorni", "everyday")
        self.combo_freq.addItem("Una sola volta", "once")
        self.combo_freq.addItem("Giorni specifici...", "custom")
        self.combo_freq.currentIndexChanged.connect(self._on_freq_changed)
        top_row.addWidget(self.combo_freq)

        self.btn_add = QPushButton("+ Aggiungi")
        self.btn_add.setObjectName("primaryButton")
        self.btn_add.setMinimumHeight(32)
        self.btn_add.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_add.clicked.connect(self._add_schedule)
        top_row.addWidget(self.btn_add)

        top_row.addStretch()
        add_outer_layout.addLayout(top_row)

        # Weekdays Selector Row
        self.days_container = QWidget()
        days_layout = QHBoxLayout(self.days_container)
        days_layout.setContentsMargins(0, 4, 0, 0)
        days_layout.setSpacing(6)

        lbl_days = QLabel("Seleziona giorni:")
        lbl_days.setStyleSheet("font-size: 12px; font-weight: 500; color: #6E6E73;")
        days_layout.addWidget(lbl_days)

        self.day_buttons = []
        days_defs = [
            (1, "Lun"),
            (2, "Mar"),
            (3, "Mer"),
            (4, "Gio"),
            (5, "Ven"),
            (6, "Sab"),
            (7, "Dom"),
        ]
        for day_num, day_label in days_defs:
            btn = QPushButton(day_label)
            btn.setObjectName("dayChip")
            btn.setCheckable(True)
            btn.setChecked(day_num <= 5)  # Default: Mon-Fri selected
            btn.setProperty("day_num", day_num)
            days_layout.addWidget(btn)
            self.day_buttons.append(btn)

        days_layout.addStretch()
        self.days_container.hide()
        add_outer_layout.addWidget(self.days_container)

        layout.addWidget(add_bar)

        # Scroll area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setStyleSheet("background: transparent;")

        self.schedules_container = QWidget()
        self.schedules_container.setStyleSheet("background: transparent;")
        self.schedules_layout = QVBoxLayout(self.schedules_container)
        self.schedules_layout.setContentsMargins(0, 4, 0, 4)
        self.schedules_layout.setSpacing(8)
        self.schedules_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.scroll_area.setWidget(self.schedules_container)
        layout.addWidget(self.scroll_area, 1)

    def _on_freq_changed(self, index: int):
        freq_data = self.combo_freq.currentData()
        if freq_data == "custom":
            self.days_container.show()
        else:
            self.days_container.hide()

    def set_course(self, course_name: str):
        self.current_course_name = course_name
        self.refresh_schedules()

    def refresh_schedules(self):
        while self.schedules_layout.count():
            item = self.schedules_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not self.current_course_name:
            empty_lbl = QLabel("Nessun corso selezionato.")
            empty_lbl.setStyleSheet("color: #8E8E93; font-style: italic;")
            self.schedules_layout.addWidget(empty_lbl)
            return

        schedules = get_course_schedules(self.current_course_name)
        if not schedules:
            no_items = QLabel("Nessuna sincronizzazione automatica configurata per questo corso.")
            no_items.setStyleSheet("color: #8E8E93; font-size: 12px; padding: 12px 0;")
            self.schedules_layout.addWidget(no_items)
            return

        for s in schedules:
            card = ScheduleItemCard(self.current_course_name, s, self._delete_schedule)
            self.schedules_layout.addWidget(card)

    def _add_schedule(self):
        if not self.current_course_name:
            QMessageBox.warning(self, "Attenzione", "Seleziona prima un corso.")
            return

        time_str = self.time_edit.time().toString("HH:mm")
        freq_type = self.combo_freq.currentData()

        selected_days = []
        if freq_type == "custom":
            selected_days = [btn.property("day_num") for btn in self.day_buttons if btn.isChecked()]
            if not selected_days:
                QMessageBox.warning(self, "Giorni mancanti", "Seleziona almeno un giorno della settimana.")
                return

        success = setup_cron_schedule(
            course_query=self.current_course_name,
            time_str=time_str,
            frequency_type=freq_type,
            selected_days=selected_days,
        )
        if success:
            self.refresh_schedules()
        else:
            QMessageBox.critical(self, "Errore", f"Impossibile pianificare la sincronizzazione alle {time_str}.")

    def _delete_schedule(self, time_str: str, freq_type: str):
        if not self.current_course_name:
            return

        success = remove_cron_schedule(
            course_query=self.current_course_name,
            time_str=time_str,
            frequency=freq_type if freq_type == "once" else None,
        )
        if success:
            self.refresh_schedules()
        else:
            QMessageBox.critical(self, "Errore", f"Impossibile rimuovere la sincronizzazione delle {time_str}.")
