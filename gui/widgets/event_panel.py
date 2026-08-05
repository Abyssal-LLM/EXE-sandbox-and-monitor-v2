"""
Event detail panel shown in KB mode.
Displays the clicked terminal line and its AI-generated explanation.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit,
    QFrame, QPushButton, QApplication,
)
from PySide6.QtCore import Qt, Signal

from gui.theme import (
    NEON_CYAN, NEON_GREEN, NEON_MAGENTA, NEON_YELLOW, NEON_RED,
    BG_DEEP_BLACK, BG_DARK, BG_PANEL, BG_INPUT,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_DIM, BORDER_MEDIUM, FONT_FAMILY,
)


class EventPanel(QWidget):
    """
    Right-side panel that shows:
      - The selected terminal log line
      - The AI model's human-readable explanation

    Shown only when KB mode is active.
    """

    close_requested = Signal()

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
        inner.setContentsMargins(12, 10, 12, 12)
        inner.setSpacing(10)

        # --- Header ---
        header = QHBoxLayout()
        header.setSpacing(8)

        title = QLabel("EVENT")
        title.setStyleSheet(f"""
            color: {NEON_MAGENTA};
            font-family: '{FONT_FAMILY}', monospace;
            font-size: 12px;
            font-weight: bold;
            letter-spacing: 2px;
        """)
        header.addWidget(title)

        header.addStretch()

        close_btn = QPushButton("X")
        close_btn.setFixedSize(22, 22)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {TEXT_SECONDARY};
                border: 1px solid {BORDER_MEDIUM};
                border-radius: 4px;
                font-family: '{FONT_FAMILY}', monospace;
                font-size: 10px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                color: {NEON_RED};
                border-color: {NEON_RED};
            }}
        """)
        close_btn.clicked.connect(self.close_requested.emit)
        header.addWidget(close_btn)

        inner.addLayout(header)

        # --- Raw log line ---
        raw_label = QLabel("LOG LINE")
        raw_label.setStyleSheet(f"""
            color: {TEXT_SECONDARY};
            font-family: '{FONT_FAMILY}', monospace;
            font-size: 10px;
            letter-spacing: 1px;
        """)
        inner.addWidget(raw_label)

        self.raw_text = QTextEdit()
        self.raw_text.setReadOnly(True)
        self.raw_text.setMaximumHeight(80)
        self.raw_text.setStyleSheet(f"""
            QTextEdit {{
                background-color: {BG_DEEP_BLACK};
                color: {NEON_GREEN};
                border: 1px solid {BORDER_MEDIUM};
                border-radius: 6px;
                padding: 8px;
                font-family: '{FONT_FAMILY}', monospace;
                font-size: 11px;
            }}
        """)
        inner.addWidget(self.raw_text)

        # --- Separator ---
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet(f"background-color: {BORDER_MEDIUM}; max-height: 1px;")
        inner.addWidget(sep)

        # --- AI Explanation ---
        ai_label = QLabel("AI EXPLANATION")
        ai_label.setStyleSheet(f"""
            color: {NEON_MAGENTA};
            font-family: '{FONT_FAMILY}', monospace;
            font-size: 10px;
            letter-spacing: 1px;
        """)
        inner.addWidget(ai_label)

        self.explanation_text = QTextEdit()
        self.explanation_text.setReadOnly(True)
        self.explanation_text.setStyleSheet(f"""
            QTextEdit {{
                background-color: {BG_DARK};
                color: {TEXT_PRIMARY};
                border: 1px solid {NEON_MAGENTA}40;
                border-radius: 6px;
                padding: 10px;
                font-family: '{FONT_FAMILY}', monospace;
                font-size: 12px;
            }}
        """)
        inner.addWidget(self.explanation_text)

        # --- Copy button ---
        btn_bar = QHBoxLayout()
        btn_bar.addStretch()

        copy_btn = QPushButton("COPY EXPLANATION")
        copy_btn.setCursor(Qt.PointingHandCursor)
        copy_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {BG_INPUT};
                color: {NEON_MAGENTA};
                border: 1px solid {NEON_MAGENTA}60;
                border-radius: 6px;
                font-family: '{FONT_FAMILY}', monospace;
                font-size: 10px;
                font-weight: bold;
                padding: 6px 16px;
                letter-spacing: 1px;
            }}
            QPushButton:hover {{
                background-color: {NEON_MAGENTA}20;
                border-color: {NEON_MAGENTA};
            }}
        """)
        copy_btn.clicked.connect(self._copy_explanation)
        btn_bar.addWidget(copy_btn)

        inner.addLayout(btn_bar)

        layout.addWidget(container)

    def set_raw(self, text: str) -> None:
        """Set the raw log line."""
        self.raw_text.setPlainText(text)

    def set_explanation(self, text: str) -> None:
        """Set the AI explanation."""
        self.explanation_text.setPlainText(text)

    def show_event(self, raw_line: str, explanation: str) -> None:
        """Set both fields at once."""
        self.raw_text.setPlainText(raw_line)
        self.explanation_text.setPlainText(explanation)

    def show_hint(self) -> None:
        """Show initial hint when KB mode opens but no line selected yet."""
        self.raw_text.setPlainText("")
        self.explanation_text.setPlainText("Click any terminal line to see an AI explanation.\nPress Esc or click X to exit KB mode.")

    def _copy_explanation(self) -> None:
        clipboard = QApplication.clipboard()
        if clipboard:
            clipboard.setText(self.explanation_text.toPlainText())
