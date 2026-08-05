"""
Control bar widget for the EXE Sandbox.
This provides the main control buttons (Start, Stop, Clear, Export)
and the session status indicator.
"""
from PySide6.QtWidgets import (
    QFrame, QPushButton, QHBoxLayout, QLabel, QWidget,
)
from PySide6.QtCore import Qt, Signal

from gui.theme import (
    NEON_CYAN, NEON_GREEN, NEON_RED, NEON_YELLOW,
    BG_DEEP_BLACK, BG_PANEL, BG_WIDGET,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_DIM,
    BORDER_MEDIUM, BORDER_DARK, FONT_FAMILY,
)


class ControlBarWidget(QFrame):
    """
    Control bar with Start, Stop, Clear, and Export buttons.

    Signals:
        start_clicked: Emitted when Start is clicked.
        stop_clicked: Emitted when Stop is clicked.
        clear_clicked: Emitted when Clear is clicked.
        export_clicked: Emitted when Export is clicked.
    """

    start_clicked = Signal()
    stop_clicked = Signal()
    clear_clicked = Signal()
    export_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._setup_connections()

        # Current state
        self.is_running = False

    def _setup_ui(self) -> None:
        """Set up the control bar UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(12)

        # START button
        self.start_button = QPushButton("START SANDBOX")
        self.start_button.setObjectName("startButton")
        self.start_button.setMinimumWidth(150)
        self.start_button.setMinimumHeight(40)
        self.start_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {BG_WIDGET};
                color: {NEON_GREEN};
                border: 2px solid {NEON_GREEN};
                border-radius: 8px;
                font-family: '{FONT_FAMILY}', monospace;
                font-size: 14px;
                font-weight: bold;
                letter-spacing: 1px;
                padding: 8px 20px;
            }}
            QPushButton:hover {{
                background-color: {NEON_GREEN}15;
                border-color: {NEON_GREEN};
            }}
            QPushButton:pressed {{
                background-color: {NEON_GREEN}30;
            }}
            QPushButton:disabled {{
                background-color: {BG_DEEP_BLACK};
                color: {TEXT_DIM};
                border-color: {BORDER_MEDIUM};
            }}
        """)
        layout.addWidget(self.start_button)

        # STOP button
        self.stop_button = QPushButton("STOP")
        self.stop_button.setObjectName("stopButton")
        self.stop_button.setMinimumWidth(100)
        self.stop_button.setMinimumHeight(40)
        self.stop_button.setEnabled(False)
        self.stop_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {BG_WIDGET};
                color: {NEON_RED};
                border: 2px solid {NEON_RED};
                border-radius: 8px;
                font-family: '{FONT_FAMILY}', monospace;
                font-size: 14px;
                font-weight: bold;
                letter-spacing: 1px;
                padding: 8px 20px;
            }}
            QPushButton:hover {{
                background-color: {NEON_RED}15;
                border-color: {NEON_RED};
            }}
            QPushButton:pressed {{
                background-color: {NEON_RED}30;
            }}
            QPushButton:disabled {{
                background-color: {BG_DEEP_BLACK};
                color: {TEXT_DIM};
                border-color: {BORDER_MEDIUM};
            }}
        """)
        layout.addWidget(self.stop_button)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.VLine)
        sep.setStyleSheet(f"color: {BORDER_MEDIUM};")
        layout.addWidget(sep)

        # CLEAR button
        self.clear_button = QPushButton("CLEAR")
        self.clear_button.setMinimumWidth(80)
        self.clear_button.setMinimumHeight(40)
        self.clear_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {BG_WIDGET};
                color: {TEXT_SECONDARY};
                border: 1px solid {BORDER_MEDIUM};
                border-radius: 8px;
                font-family: '{FONT_FAMILY}', monospace;
                font-size: 12px;
                font-weight: bold;
                padding: 8px 16px;
            }}
            QPushButton:hover {{
                background-color: {BG_WIDGET};
                color: {TEXT_PRIMARY};
                border-color: {NEON_CYAN};
            }}
        """)
        layout.addWidget(self.clear_button)

        # EXPORT button
        self.export_button = QPushButton("EXPORT LOG")
        self.export_button.setMinimumWidth(100)
        self.export_button.setMinimumHeight(40)
        self.export_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {BG_WIDGET};
                color: {TEXT_SECONDARY};
                border: 1px solid {BORDER_MEDIUM};
                border-radius: 8px;
                font-family: '{FONT_FAMILY}', monospace;
                font-size: 12px;
                font-weight: bold;
                padding: 8px 16px;
            }}
            QPushButton:hover {{
                background-color: {BG_WIDGET};
                color: {TEXT_PRIMARY};
                border-color: {NEON_CYAN};
            }}
        """)
        layout.addWidget(self.export_button)

        layout.addStretch()

        # Status indicator
        self.status_frame = QFrame()
        self.status_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {BG_DEEP_BLACK};
                border: 1px solid {BORDER_DARK};
                border-radius: 20px;
                padding: 4px 12px;
            }}
        """)
        status_layout = QHBoxLayout(self.status_frame)
        status_layout.setContentsMargins(8, 4, 12, 4)
        status_layout.setSpacing(6)

        # Status dot
        self.status_dot = QLabel()
        self.status_dot.setFixedSize(10, 10)
        self.status_dot.setStyleSheet(f"""
            background-color: {TEXT_DIM};
            border-radius: 5px;
            border: none;
        """)
        status_layout.addWidget(self.status_dot)

        self.status_text = QLabel("IDLE")
        self.status_text.setStyleSheet(f"""
            color: {TEXT_SECONDARY};
            font-family: '{FONT_FAMILY}', monospace;
            font-size: 11px;
            font-weight: bold;
            letter-spacing: 1px;
        """)
        status_layout.addWidget(self.status_text)

        layout.addWidget(self.status_frame)

    def _setup_connections(self) -> None:
        """Set up signal-slot connections."""
        self.start_button.clicked.connect(self._on_start_clicked)
        self.stop_button.clicked.connect(self._on_stop_clicked)
        self.clear_button.clicked.connect(self._on_clear_clicked)
        self.export_button.clicked.connect(self._on_export_clicked)

    def _on_start_clicked(self) -> None:
        """Handle start button click."""
        self.set_running(True)
        self.start_clicked.emit()

    def _on_stop_clicked(self) -> None:
        """Handle stop button click."""
        self.set_running(False)
        self.stop_clicked.emit()

    def _on_clear_clicked(self) -> None:
        """Handle clear button click."""
        self.clear_clicked.emit()

    def _on_export_clicked(self) -> None:
        """Handle export button click."""
        self.export_clicked.emit()

    def set_running(self, running: bool) -> None:
        """
        Update the control bar state based on whether sandbox is running.

        Parameters:
            running: True if sandbox is running, False otherwise.
        """
        self.is_running = running

        if running:
            self.start_button.setEnabled(False)
            self.stop_button.setEnabled(True)

            self.status_dot.setStyleSheet(f"""
                background-color: {NEON_GREEN};
                border-radius: 5px;
                border: none;
            """)
            self.status_text.setText("RUNNING")
            self.status_text.setStyleSheet(f"""
                color: {NEON_GREEN};
                font-family: '{FONT_FAMILY}', monospace;
                font-size: 11px;
                font-weight: bold;
                letter-spacing: 1px;
            """)
        else:
            self.start_button.setEnabled(True)
            self.stop_button.setEnabled(False)

            self.status_dot.setStyleSheet(f"""
                background-color: {TEXT_DIM};
                border-radius: 5px;
                border: none;
            """)
            self.status_text.setText("IDLE")
            self.status_text.setStyleSheet(f"""
                color: {TEXT_SECONDARY};
                font-family: '{FONT_FAMILY}', monospace;
                font-size: 11px;
                font-weight: bold;
                letter-spacing: 1px;
            """)
