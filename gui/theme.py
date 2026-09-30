MACOS_STYLE = """
QMainWindow, QDialog {
    background-color: #ECECEE;
}

QWidget {
    font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", "Helvetica Neue", Arial, sans-serif;
    color: #1D1D1F;
    font-size: 13px;
}

/* Sidebar in stile Impostazioni Apple / Package Explorer */
QListWidget#sidebarList {
    background-color: #E2E2E7;
    border: none;
    border-right: 1px solid #D2D2D7;
    outline: none;
    padding: 8px 6px;
}

QListWidget#sidebarList::item {
    padding: 8px 12px;
    border-radius: 8px;
    margin-bottom: 2px;
    font-size: 13px;
    font-weight: 500;
    color: #1D1D1F;
}

QListWidget#sidebarList::item:hover {
    background-color: #D8D8DE;
}

QListWidget#sidebarList::item:selected {
    background-color: #007AFF;
    color: #FFFFFF;
}

/* Header & Panels */
QFrame#contentPanel {
    background-color: #F7F7F9;
    border: none;
}

QFrame#card {
    background-color: #FFFFFF;
    border: 1px solid #D5D5DC;
    border-radius: 12px;
}

QFrame#alarmCard {
    background-color: #FFFFFF;
    border: 1px solid #E5E5EA;
    border-radius: 10px;
}

/* Bottoni in stile macOS */
QPushButton {
    background-color: #FFFFFF;
    border: 1px solid #C6C6C8;
    border-radius: 7px;
    padding: 5px 14px;
    min-height: 24px;
    font-size: 13px;
    font-weight: 500;
    color: #1D1D1F;
}

QPushButton:hover {
    background-color: #F2F2F7;
    border-color: #B5B5BA;
}

QPushButton:pressed {
    background-color: #E5E5EA;
}

QPushButton#plusButton {
    background-color: #FFFFFF;
    color: #007AFF;
    border: 1px solid #C6C6C8;
    border-radius: 13px;
    font-size: 16px;
    font-weight: 600;
    min-width: 26px;
    max-width: 26px;
    min-height: 26px;
    max-height: 26px;
    padding: 0px;
    text-align: center;
}

QPushButton#plusButton:hover {
    background-color: #007AFF;
    color: #FFFFFF;
    border-color: #007AFF;
}

QPushButton#primaryButton {
    background-color: #007AFF;
    color: #FFFFFF;
    border: 1px solid #0062CC;
    font-weight: 600;
    padding: 6px 16px;
}

QPushButton#primaryButton:hover {
    background-color: #0069D9;
}

QPushButton#primaryButton:pressed {
    background-color: #0051A8;
}

QPushButton#downloadButton {
    background-color: #34C759;
    color: #FFFFFF;
    border: 1px solid #28A745;
    font-weight: 600;
    font-size: 13px;
    padding: 6px 16px;
    border-radius: 8px;
    min-height: 24px;
}

QPushButton#downloadButton:hover {
    background-color: #2DB84D;
}

QPushButton#downloadButton:pressed {
    background-color: #24963E;
}

QPushButton#downloadButton:disabled {
    background-color: #A3E6B5;
    border-color: #A3E6B5;
    color: #FFFFFF;
}

/* Bottone Rimuovi: tutto rosso solido con testo bianco */
QPushButton#dangerButton {
    background-color: #FF3B30;
    color: #FFFFFF;
    border: 1px solid #D70015;
    border-radius: 6px;
    font-size: 12px;
    font-weight: 600;
    padding: 4px 12px;
    min-height: 22px;
}

QPushButton#dangerButton:hover {
    background-color: #D70015;
    border-color: #B5000F;
}

QPushButton#dangerButton:pressed {
    background-color: #A3000C;
}

QPushButton#infoButton {
    background-color: #E5E5EA;
    color: #007AFF;
    border: 1px solid #D1D1D6;
    border-radius: 11px;
    font-weight: 700;
    font-size: 12px;
    min-width: 22px;
    max-width: 22px;
    min-height: 22px;
    max-height: 22px;
    padding: 0px;
}

QPushButton#infoButton:hover {
    background-color: #007AFF;
    color: #FFFFFF;
    border-color: #007AFF;
}

/* Input Fields & ComboBox */
QLineEdit {
    background-color: #FFFFFF;
    color: #1D1D1F;
    border: 1px solid #C6C6C8;
    border-radius: 7px;
    padding: 6px 10px;
    font-size: 13px;
    min-height: 24px;
    selection-background-color: #007AFF;
}

QLineEdit:focus {
    border: 2px solid #007AFF;
    padding: 5px 9px;
}

QComboBox {
    background-color: #FFFFFF;
    color: #1D1D1F;
    border: 1px solid #C6C6C8;
    border-radius: 7px;
    padding: 6px 28px 6px 10px;
    font-size: 13px;
    min-height: 24px;
    selection-background-color: #007AFF;
}

QComboBox:focus {
    border: 2px solid #007AFF;
    padding: 5px 27px 5px 9px;
}

QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 22px;
    border: none;
}

QComboBox QAbstractItemView {
    background-color: #FFFFFF;
    color: #1D1D1F;
    border: 1px solid #D5D5DC;
    border-radius: 6px;
    padding: 4px;
    selection-background-color: #007AFF;
    selection-color: #FFFFFF;
}

QTimeEdit {
    background-color: #FFFFFF;
    color: #1D1D1F;
    border: 1px solid #C6C6C8;
    border-radius: 7px;
    padding: 5px 8px;
    font-size: 13px;
    min-height: 24px;
}

QTimeEdit:focus {
    border: 2px solid #007AFF;
    padding: 4px 7px;
}

/* Day check box / chip buttons */
QPushButton#dayChip {
    background-color: #F2F2F7;
    color: #1D1D1F;
    border: 1px solid #D1D1D6;
    border-radius: 6px;
    padding: 3px 6px;
    font-size: 11px;
    font-weight: 500;
    min-width: 28px;
    max-width: 32px;
    min-height: 22px;
}

QPushButton#dayChip:checked {
    background-color: #007AFF;
    color: #FFFFFF;
    border-color: #0062CC;
    font-weight: 600;
}

/* Progress bar */
QProgressBar {
    background-color: #E5E5EA;
    border: 1px solid #C6C6C8;
    border-radius: 7px;
    height: 16px;
    min-height: 16px;
    max-height: 16px;
    text-align: center;
    font-size: 11px;
    font-weight: 600;
    color: #1D1D1F;
}

QProgressBar::chunk {
    background-color: #34C759;
    border-radius: 6px;
}


/* Tooltips */
QToolTip {
    background-color: #1D1D1F;
    color: #FFFFFF;
    border: 1px solid #3A3A3C;
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 12px;
}
"""
