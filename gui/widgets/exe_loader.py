"""
EXE loader widget for the EXE Sandbox.
This provides a drag-and-drop zone for loading EXEs into the sandbox.
It also includes a file browser button and command-line arguments input.
"""
import os
from typing import Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QFileDialog, QSizePolicy,
)
from PySide6.QtCore import Qt, Signal, QUrl
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QFont

from gui.theme import (
    NEON_CYAN, NEON_GREEN, BG_DEEP_BLACK, BG_PANEL, BG_WIDGET,
    BG_INPUT, TEXT_PRIMARY, TEXT_SECONDARY, TEXT_DIM,
    BORDER_MEDIUM, BORDER_DARK, FONT_FAMILY,
)


class ExeLoaderWidget(QFrame):
    """
    Widget for loading EXEs into the sandbox.

    Features:
    - Drag-and-drop zone for EXE files
    - File browser button
    - Command-line arguments input
    - Working directory selector
    - Visual feedback for drag operations

    Signals:
        exe_loaded: Emitted when an EXE is loaded. Carries the file path.
        exe_cleared: Emitted when the loaded EXE is cleared.
    """

    exe_loaded = Signal(str)
    exe_cleared = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("dropZone")
        self.setAcceptDrops(True)
        self._setup_ui()
        self._setup_connections()

        # The currently loaded EXE path
        self.current_exe_path: str = ""

    def _setup_ui(self) -> None:
        """Set up the loader UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Title row
        title_row = QHBoxLayout()
        title_row.setSpacing(8)

        title_label = QLabel("SANDBOX TARGET")
        title_label.setObjectName("titleLabel")
        title_label.setStyleSheet(f"""
            color: {NEON_CYAN};
            font-family: '{FONT_FAMILY}', monospace;
            font-size: 14px;
            font-weight: bold;
            letter-spacing: 2px;
        """)
        title_row.addWidget(title_label)

        title_row.addStretch()

        # Status indicator
        self.status_label = QLabel("NO EXE LOADED")
        self.status_label.setStyleSheet(f"""
            color: {TEXT_DIM};
            font-family: '{FONT_FAMILY}', monospace;
            font-size: 11px;
            padding: 4px 8px;
            background-color: {BG_DEEP_BLACK};
            border: 1px solid {BORDER_DARK};
            border-radius: 4px;
        """)
        title_row.addWidget(self.status_label)

        layout.addLayout(title_row)

        # Drop zone area
        self.drop_zone = QFrame()
        self.drop_zone.setObjectName("dropZone")
        self.drop_zone.setMinimumHeight(80)
        self.drop_zone.setStyleSheet(f"""
            QFrame {{
                background-color: {BG_DEEP_BLACK};
                border: 2px dashed {BORDER_MEDIUM};
                border-radius: 12px;
            }}
            QFrame:hover {{
                border-color: {NEON_CYAN};
                background-color: {NEON_CYAN}08;
            }}
        """)

        drop_layout = QVBoxLayout(self.drop_zone)
        drop_layout.setContentsMargins(16, 12, 16, 12)
        drop_layout.setAlignment(Qt.AlignCenter)

        # Drop icon/text
        self.drop_label = QLabel("Drag & Drop .exe here")
        self.drop_label.setAlignment(Qt.AlignCenter)
        self.drop_label.setStyleSheet(f"""
            color: {TEXT_SECONDARY};
            font-family: '{FONT_FAMILY}', monospace;
            font-size: 13px;
        """)
        drop_layout.addWidget(self.drop_label)

        self.file_path_label = QLabel("")
        self.file_path_label.setAlignment(Qt.AlignCenter)
        self.file_path_label.setStyleSheet(f"""
            color: {NEON_GREEN};
            font-family: '{FONT_FAMILY}', monospace;
            font-size: 12px;
        """)
        self.file_path_label.hide()
        drop_layout.addWidget(self.file_path_label)

        layout.addWidget(self.drop_zone)

        # Controls row
        controls_row = QHBoxLayout()
        controls_row.setSpacing(8)

        # Browse button
        self.browse_button = QPushButton("Browse...")
        self.browse_button.setFixedWidth(100)
        controls_row.addWidget(self.browse_button)

        # Clear button
        self.clear_button = QPushButton("Clear")
        self.clear_button.setFixedWidth(80)
        self.clear_button.setEnabled(False)
        controls_row.addWidget(self.clear_button)

        controls_row.addStretch()

        # Command-line arguments
        args_label = QLabel("Args:")
        args_label.setStyleSheet(f"color: {TEXT_SECONDARY}; font-family: '{FONT_FAMILY}', monospace;")
        controls_row.addWidget(args_label)

        self.args_input = QLineEdit()
        self.args_input.setPlaceholderText("Command-line arguments...")
        self.args_input.setMinimumWidth(200)
        controls_row.addWidget(self.args_input)

        layout.addLayout(controls_row)

        # Working directory row
        dir_row = QHBoxLayout()
        dir_row.setSpacing(8)

        dir_label = QLabel("Work Dir:")
        dir_label.setStyleSheet(f"color: {TEXT_SECONDARY}; font-family: '{FONT_FAMILY}', monospace;")
        dir_row.addWidget(dir_label)

        self.workdir_input = QLineEdit()
        self.workdir_input.setPlaceholderText("Working directory (uses EXE directory if empty)...")
        dir_row.addWidget(self.workdir_input)

        self.workdir_button = QPushButton("...")
        self.workdir_button.setFixedWidth(30)
        dir_row.addWidget(self.workdir_button)

        layout.addLayout(dir_row)

    def _setup_connections(self) -> None:
        """Set up signal-slot connections."""
        self.browse_button.clicked.connect(self._on_browse_clicked)
        self.clear_button.clicked.connect(self._on_clear_clicked)
        self.workdir_button.clicked.connect(self._on_workdir_browse)

    def _on_browse_clicked(self) -> None:
        """Handle browse button click - open file dialog."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select EXE to Sandbox",
            "",
            "Executables (*.exe);;All Files (*.*)"
        )

        if file_path:
            self._load_exe(file_path)

    def _on_clear_clicked(self) -> None:
        """Handle clear button click - clear the loaded EXE."""
        self._clear_exe()

    def _on_workdir_browse(self) -> None:
        """Handle working directory browse button click."""
        dir_path = QFileDialog.getExistingDirectory(
            self,
            "Select Working Directory"
        )

        if dir_path:
            self.workdir_input.setText(dir_path)

    def _load_exe(self, file_path: str) -> None:
        """
        Load an EXE file.

        Parameters:
            file_path: Full path to the EXE file.
        """
        if not file_path.lower().endswith('.exe'):
            self.status_label.setText("NOT AN EXE")
            self.status_label.setStyleSheet(f"""
                color: {NEON_GREEN};
                font-family: '{FONT_FAMILY}', monospace;
                font-size: 11px;
                padding: 4px 8px;
                background-color: {BG_DEEP_BLACK};
                border: 1px solid {BORDER_DARK};
                border-radius: 4px;
            """)
            return

        self.current_exe_path = file_path
        exe_name = os.path.basename(file_path)

        # Update the UI
        self.drop_label.setText(exe_name)
        self.file_path_label.setText(file_path)
        self.file_path_label.show()

        self.status_label.setText("LOADED")
        self.status_label.setStyleSheet(f"""
            color: {NEON_GREEN};
            font-family: '{FONT_FAMILY}', monospace;
            font-size: 11px;
            padding: 4px 8px;
            background-color: {BG_DEEP_BLACK};
            border: 1px solid {NEON_GREEN}40;
            border-radius: 4px;
        """)

        self.clear_button.setEnabled(True)

        # Update the drop zone style
        self.drop_zone.setStyleSheet(f"""
            QFrame {{
                background-color: {NEON_GREEN}08;
                border: 2px solid {NEON_GREEN}40;
                border-radius: 12px;
            }}
        """)

        # Emit the signal
        self.exe_loaded.emit(file_path)

    def _clear_exe(self) -> None:
        """Clear the loaded EXE."""
        self.current_exe_path = ""

        # Reset the UI
        self.drop_label.setText("Drag & Drop .exe here")
        self.file_path_label.setText("")
        self.file_path_label.hide()

        self.status_label.setText("NO EXE LOADED")
        self.status_label.setStyleSheet(f"""
            color: {TEXT_DIM};
            font-family: '{FONT_FAMILY}', monospace;
            font-size: 11px;
            padding: 4px 8px;
            background-color: {BG_DEEP_BLACK};
            border: 1px solid {BORDER_DARK};
            border-radius: 4px;
        """)

        self.clear_button.setEnabled(False)

        # Reset the drop zone style
        self.drop_zone.setStyleSheet(f"""
            QFrame {{
                background-color: {BG_DEEP_BLACK};
                border: 2px dashed {BORDER_MEDIUM};
                border-radius: 12px;
            }}
            QFrame:hover {{
                border-color: {NEON_CYAN};
                background-color: {NEON_CYAN}08;
            }}
        """)

        # Emit the signal
        self.exe_cleared.emit()

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        """Handle drag enter events."""
        if event.mimeData().hasUrls():
            # Check if any of the URLs point to an EXE file
            for url in event.mimeData().urls():
                if url.toLocalFile().lower().endswith('.exe'):
                    event.acceptProposedAction()

                    # Highlight the drop zone
                    self.drop_zone.setStyleSheet(f"""
                        QFrame {{
                            background-color: {NEON_CYAN}10;
                            border: 2px dashed {NEON_CYAN};
                            border-radius: 12px;
                        }}
                    """)
                    return

        event.ignore()

    def dragLeaveEvent(self, event) -> None:
        """Handle drag leave events."""
        # Reset the drop zone style
        self.drop_zone.setStyleSheet(f"""
            QFrame {{
                background-color: {BG_DEEP_BLACK};
                border: 2px dashed {BORDER_MEDIUM};
                border-radius: 12px;
            }}
            QFrame:hover {{
                border-color: {NEON_CYAN};
                background-color: {NEON_CYAN}08;
            }}
        """)

    def dropEvent(self, event: QDropEvent) -> None:
        """Handle drop events."""
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if file_path.lower().endswith('.exe'):
                self._load_exe(file_path)
                event.acceptProposedAction()
                return

        event.ignore()

    def get_exe_path(self) -> str:
        """
        Get the currently loaded EXE path.

        Returns:
            The full path to the loaded EXE, or empty string if none loaded.
        """
        return self.current_exe_path

    def get_args(self) -> str:
        """
        Get the command-line arguments.

        Returns:
            The arguments string.
        """
        return self.args_input.text()

    def get_workdir(self) -> str:
        """
        Get the working directory.

        Returns:
            The working directory path, or empty string if not set.
        """
        return self.workdir_input.text()
