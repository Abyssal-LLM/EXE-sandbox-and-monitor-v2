"""
Clickable log snapshot for KB mode.
Displays terminal history as a list of individually clickable lines.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QListWidget, QListWidgetItem, QFrame, QLabel,
    QHBoxLayout, QAbstractItemView, QPushButton,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from gui.theme import (
    NEON_CYAN, NEON_GREEN, NEON_MAGENTA, NEON_YELLOW, NEON_RED,
    BG_DEEP_BLACK, BG_DARK, BG_PANEL, BG_INPUT, BG_HOVER, BG_SELECTED,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_DIM, BORDER_MEDIUM, FONT_FAMILY,
)


class LogSnapshotWidget(QWidget):
    """
    A list of terminal log lines, each one clickable.
    Populated from event history when KB mode opens.
    New events are appended in real-time.
    """

    line_clicked = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        container = QFrame()
        container.setStyleSheet(f"""
            QFrame {{
                background-color: {BG_PANEL};
                border: 1px solid {BORDER_MEDIUM};
                border-radius: 8px;
            }}
        """)
        inner = QVBoxLayout(container)
        inner.setContentsMargins(8, 8, 8, 8)
        inner.setSpacing(6)

        header = QHBoxLayout()
        header.setSpacing(8)
        title = QLabel("LOG SNAPSHOT")
        title.setStyleSheet(f"""
            color: {NEON_CYAN};
            font-family: '{FONT_FAMILY}', monospace;
            font-size: 12px;
            font-weight: bold;
            letter-spacing: 2px;
        """)
        header.addWidget(title)
        header.addStretch()

        self.update_toggle = QPushButton("UPDATE")
        self.update_toggle.setCheckable(True)
        self.update_toggle.setChecked(False)
        self.update_toggle.setFixedWidth(70)
        self.update_toggle.setCursor(Qt.PointingHandCursor)
        self.update_toggle.setToolTip("Toggle live updates — when OFF, snapshot is frozen")
        self.update_toggle.setStyleSheet(f"""
            QPushButton {{
                background-color: {BG_DEEP_BLACK};
                color: {TEXT_SECONDARY};
                border: 1px solid {BORDER_MEDIUM};
                border-radius: 4px;
                font-family: '{FONT_FAMILY}', monospace;
                font-size: 9px;
                font-weight: bold;
                letter-spacing: 1px;
                padding: 2px 6px;
            }}
            QPushButton:hover {{ border-color: {NEON_GREEN}; color: {NEON_GREEN}; }}
            QPushButton:checked {{ background-color: {NEON_GREEN}20; color: {NEON_GREEN}; border-color: {NEON_GREEN}; }}
        """)
        header.addWidget(self.update_toggle)

        self.line_count = QLabel("0 lines")
        self.line_count.setStyleSheet(f"""
            color: {TEXT_SECONDARY};
            font-family: '{FONT_FAMILY}', monospace;
            font-size: 10px;
        """)
        header.addWidget(self.line_count)
        inner.addLayout(header)

        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QAbstractItemView.NoSelection)
        self.list_widget.setSpacing(1)
        self.list_widget.setStyleSheet(f"""
            QListWidget {{
                background-color: {BG_DEEP_BLACK};
                border: 1px solid {BORDER_MEDIUM};
                border-radius: 6px;
                padding: 4px;
                font-family: '{FONT_FAMILY}', monospace;
                font-size: 11px;
                outline: none;
            }}
            QListWidget::item {{
                padding: 4px 8px;
                border-radius: 3px;
                color: {TEXT_PRIMARY};
            }}
            QListWidget::item:hover {{
                background-color: {BG_HOVER};
                color: {NEON_CYAN};
            }}
            QListWidget::item:pressed {{
                background-color: {BG_SELECTED};
                color: {NEON_MAGENTA};
            }}
        """)
        self.list_widget.itemClicked.connect(self._on_item_clicked)
        inner.addWidget(self.list_widget)

        layout.addWidget(container)

    def load_lines(self, lines: list) -> None:
        """Load a list of log line strings into the snapshot."""
        self.list_widget.clear()
        for line in lines:
            if line.strip():
                self._add_item(line)
        self._update_count()

    def append_line(self, line: str) -> None:
        """Append a single new log line — only if UPDATE is checked."""
        if not self.update_toggle.isChecked():
            return
        if line.strip():
            self._add_item(line)
            self.list_widget.scrollToBottom()
            self._update_count()

    def _add_item(self, text: str) -> None:
        item = QListWidgetItem(text)
        item.setFont(QFont(FONT_FAMILY, 11))
        item.setToolTip(text)
        self.list_widget.addItem(item)

    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        text = item.text()
        if text.strip():
            self.line_clicked.emit(text)

    def _update_count(self) -> None:
        count = self.list_widget.count()
        self.line_count.setText(f"{count} lines")
