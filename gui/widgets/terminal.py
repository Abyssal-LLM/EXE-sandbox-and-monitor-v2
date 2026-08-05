"""
Scrolling terminal widget for the EXE Sandbox.
This displays all monitoring events in real-time with color-coded output.
It's the main monitoring interface where users see everything the sandbox captures.
"""
from PySide6.QtWidgets import (
    QPlainTextEdit, QVBoxLayout, QHBoxLayout, QWidget,
    QLineEdit, QPushButton, QLabel, QFrame, QCheckBox,
    QMenu,
)
from PySide6.QtCore import Qt, Signal, Slot, QRegularExpression, QEvent
from PySide6.QtGui import (
    QTextCharFormat, QColor, QTextCursor, QFont,
    QSyntaxHighlighter,
)

from gui.theme import (
    NEON_CYAN, NEON_GREEN, NEON_YELLOW, NEON_RED, NEON_MAGENTA,
    BG_DEEP_BLACK, BG_PANEL, BG_INPUT, TEXT_PRIMARY, TEXT_SECONDARY,
    TEXT_DIM, BORDER_MEDIUM, FONT_FAMILY,
    EVENT_FILE, EVENT_REGISTRY, EVENT_NETWORK, EVENT_PROCESS, EVENT_CONSOLE,
)


class TerminalHighlighter(QSyntaxHighlighter):
    """
    Syntax highlighter for the terminal output.
    This colors different parts of each log line based on event type.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        # Define the highlighting rules
        self.rules = []

        # Timestamp pattern - gray color
        timestamp_format = QTextCharFormat()
        timestamp_format.setForeground(QColor(TEXT_SECONDARY))
        self.rules.append((
            QRegularExpression(r'\[\d{2}:\d{2}:\d{2}\.\d{3}\]'),
            timestamp_format
        ))

        # Event type badges - colored by type
        for badge, color in [
            ("FILE", EVENT_FILE),
            ("REGISTRY", EVENT_REGISTRY),
            ("NETWORK", EVENT_NETWORK),
            ("PROCESS", EVENT_PROCESS),
            ("DLL", "#ff8800"),
            ("MEM", "#8888ff"),
        ]:
            fmt = QTextCharFormat()
            fmt.setForeground(QColor(color))
            fmt.setFontWeight(QFont.Bold)
            self.rules.append((
                QRegularExpression(rf'\[{badge}\]'),
                fmt
            ))

        # Console level badges
        for level, color in [
            ("INFO", NEON_CYAN),
            ("WARN", NEON_YELLOW),
            ("ERR", NEON_RED),
            ("DBG", TEXT_DIM),
            ("OK", NEON_GREEN),
        ]:
            fmt = QTextCharFormat()
            fmt.setForeground(QColor(color))
            fmt.setFontWeight(QFont.Bold)
            self.rules.append((
                QRegularExpression(rf'\[{level}\]'),
                fmt
            ))

        # PID pattern - yellow
        pid_format = QTextCharFormat()
        pid_format.setForeground(QColor(NEON_YELLOW))
        self.rules.append((
            QRegularExpression(r'\(\d+\)'),
            pid_format
        ))

        # File paths - cyan
        path_format = QTextCharFormat()
        path_format.setForeground(QColor(NEON_CYAN))
        self.rules.append((
            QRegularExpression(r'[A-Z]:\\[^\s]+'),
            path_format
        ))

        # Registry keys - magenta
        reg_format = QTextCharFormat()
        reg_format.setForeground(QColor(NEON_MAGENTA))
        self.rules.append((
            QRegularExpression(r'HK[A-Z]+\\[^\s]+'),
            reg_format
        ))

        # IP addresses - green
        ip_format = QTextCharFormat()
        ip_format.setForeground(QColor(NEON_GREEN))
        self.rules.append((
            QRegularExpression(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d+'),
            ip_format
        ))

        # Success indicators
        success_format = QTextCharFormat()
        success_format.setForeground(QColor(NEON_GREEN))
        self.rules.append((
            QRegularExpression(r'-> SUCCESS'),
            success_format
        ))

        # Error indicators
        error_format = QTextCharFormat()
        error_format.setForeground(QColor(NEON_RED))
        self.rules.append((
            QRegularExpression(r'-> FAIL|-> ERROR|Error:'),
            error_format
        ))

    def highlightBlock(self, text: str) -> None:
        """Apply highlighting to a block of text."""
        for pattern, fmt in self.rules:
            match_iter = pattern.globalMatch(text)
            while match_iter.hasNext():
                match = match_iter.next()
                self.setFormat(match.capturedStart(), match.capturedLength(), fmt)


class TerminalWidget(QFrame):
    """
    The main terminal widget that displays monitoring output.

    This widget features:
    - Real-time scrolling log output
    - Syntax highlighting by event type
    - Auto-scroll with manual override
    - Filter bar for searching and filtering events
    - Maximum line limit to prevent memory issues
    - Export functionality for logs

    Signals:
        export_requested: Emitted when the user wants to export the log.
        log_received: Internal signal for thread-safe log delivery.
    """

    export_requested = Signal()
    log_received = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("terminalFrame")

        # Maximum number of lines to keep in the terminal
        # This prevents memory issues with long-running sandboxes
        self.max_lines: int = 10000

        # Whether auto-scroll is enabled
        self.auto_scroll: bool = True

        # The filter text - only lines containing this will be shown
        self.filter_text: str = ""

        # Event type filters - which event types to show
        self.show_file_events: bool = True
        self.show_registry_events: bool = True
        self.show_network_events: bool = True
        self.show_process_events: bool = True
        self.show_dll_events: bool = True
        self.show_mem_events: bool = True
        self.show_console_events: bool = True

        self._setup_ui()
        self._setup_connections()

    def _setup_ui(self) -> None:
        """Set up the terminal UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # Filter bar at the top
        filter_frame = QFrame()
        filter_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {BG_PANEL};
                border: 1px solid {BORDER_MEDIUM};
                border-radius: 6px;
                padding: 4px;
            }}
        """)
        filter_layout = QHBoxLayout(filter_frame)
        filter_layout.setContentsMargins(8, 4, 8, 4)
        filter_layout.setSpacing(8)

        # Search/filter input
        self.filter_input = QLineEdit()
        self.filter_input.setPlaceholderText("Filter events...")
        self.filter_input.setClearButtonEnabled(True)
        filter_layout.addWidget(self.filter_input)

        # Event type filter checkboxes
        self.file_filter = QCheckBox("FILE")
        self.file_filter.setChecked(True)
        self.file_filter.setStyleSheet(f"QCheckBox {{ color: {EVENT_FILE}; }}")
        filter_layout.addWidget(self.file_filter)

        self.registry_filter = QCheckBox("REG")
        self.registry_filter.setChecked(True)
        self.registry_filter.setStyleSheet(f"QCheckBox {{ color: {EVENT_REGISTRY}; }}")
        filter_layout.addWidget(self.registry_filter)

        self.network_filter = QCheckBox("NET")
        self.network_filter.setChecked(True)
        self.network_filter.setStyleSheet(f"QCheckBox {{ color: {EVENT_NETWORK}; }}")
        filter_layout.addWidget(self.network_filter)

        self.process_filter = QCheckBox("PROC")
        self.process_filter.setChecked(True)
        self.process_filter.setStyleSheet(f"QCheckBox {{ color: {EVENT_PROCESS}; }}")
        filter_layout.addWidget(self.process_filter)

        self.dll_filter = QCheckBox("DLL")
        self.dll_filter.setChecked(True)
        self.dll_filter.setStyleSheet("QCheckBox { color: #ff8800; }")
        filter_layout.addWidget(self.dll_filter)

        self.mem_filter = QCheckBox("MEM")
        self.mem_filter.setChecked(True)
        self.mem_filter.setStyleSheet("QCheckBox { color: #8888ff; }")
        filter_layout.addWidget(self.mem_filter)

        self.console_filter = QCheckBox("CONSOLE")
        self.console_filter.setChecked(True)
        self.console_filter.setStyleSheet(f"QCheckBox {{ color: {EVENT_CONSOLE}; }}")
        filter_layout.addWidget(self.console_filter)

        layout.addWidget(filter_frame)

        # The main terminal output area
        self.terminal_output = QPlainTextEdit()
        self.terminal_output.setReadOnly(True)
        self.terminal_output.setMaximumBlockCount(self.max_lines)
        self.terminal_output.setStyleSheet(f"""
            QPlainTextEdit {{
                background-color: {BG_DEEP_BLACK};
                color: {TEXT_PRIMARY};
                border: 1px solid {BORDER_MEDIUM};
                border-radius: 6px;
                padding: 8px;
                font-family: '{FONT_FAMILY}', monospace;
                font-size: 12px;
                selection-background-color: {NEON_CYAN}40;
            }}
        """)

        # Set up the syntax highlighter
        self.highlighter = TerminalHighlighter(self.terminal_output.document())

        layout.addWidget(self.terminal_output)

        # Bottom bar with controls
        bottom_frame = QFrame()
        bottom_layout = QHBoxLayout(bottom_frame)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.setSpacing(8)

        # Auto-scroll checkbox
        self.auto_scroll_checkbox = QCheckBox("Auto-scroll")
        self.auto_scroll_checkbox.setChecked(True)
        bottom_layout.addWidget(self.auto_scroll_checkbox)

        # Line count label
        self.line_count_label = QLabel("0 lines")
        self.line_count_label.setStyleSheet(f"color: {TEXT_SECONDARY};")
        bottom_layout.addWidget(self.line_count_label)

        bottom_layout.addStretch()

        # Clear button
        self.clear_button = QPushButton("Clear")
        self.clear_button.setFixedWidth(80)
        bottom_layout.addWidget(self.clear_button)

        # Export button
        self.export_button = QPushButton("Export")
        self.export_button.setFixedWidth(80)
        bottom_layout.addWidget(self.export_button)

        layout.addWidget(bottom_frame)

    def _setup_connections(self) -> None:
        """Set up signal-slot connections."""
        # Thread-safe log delivery signal
        self.log_received.connect(self._do_append_log)

        # Auto-scroll checkbox
        self.auto_scroll_checkbox.stateChanged.connect(self._on_auto_scroll_changed)

        # Filter input
        self.filter_input.textChanged.connect(self._on_filter_changed)

        # Event type filters
        self.file_filter.stateChanged.connect(self._on_filter_changed)
        self.registry_filter.stateChanged.connect(self._on_filter_changed)
        self.network_filter.stateChanged.connect(self._on_filter_changed)
        self.process_filter.stateChanged.connect(self._on_filter_changed)
        self.dll_filter.stateChanged.connect(self._on_filter_changed)
        self.mem_filter.stateChanged.connect(self._on_filter_changed)
        self.console_filter.stateChanged.connect(self._on_filter_changed)

        # Buttons
        self.clear_button.clicked.connect(self.clear)
        self.export_button.clicked.connect(self.export_requested.emit)

        # Install event filter on terminal output for click-to-explain
        self.terminal_output.installEventFilter(self)

    def _copy_line(self, line: str) -> None:
        """Copy a line to clipboard."""
        from PySide6.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        if clipboard:
            clipboard.setText(line)

    def _show_custom_context_menu(self, global_pos) -> None:
        """Build and show the custom context menu with Explain + Copy + Select All."""
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: #1a1a2e;
                color: #c8c8d0;
                border: 1px solid #2a2a45;
                border-radius: 6px;
                padding: 4px;
            }}
            QMenu::item {{
                padding: 6px 24px;
                border-radius: 4px;
            }}
            QMenu::item:selected {{
                background-color: #ff00ff20;
                color: #ff00ff;
            }}
        """)

        # Get the line under the current cursor
        cursor = self.terminal_output.textCursor()
        cursor.select(QTextCursor.LineUnderCursor)
        selected_line = cursor.selectedText()

        copy_action = menu.addAction("Copy Line")
        copy_action.triggered.connect(lambda: self._copy_line(selected_line))

        select_all_action = menu.addAction("Select All")
        select_all_action.triggered.connect(self.terminal_output.selectAll)

        menu.exec(global_pos)

    def eventFilter(self, obj, event) -> bool:
        """Handle right-click context menu on the terminal output."""
        if obj == self.terminal_output:
            if event.type() == QEvent.ContextMenu:
                self._show_custom_context_menu(event.globalPos())
                return True

        return super().eventFilter(obj, event)

    def _on_auto_scroll_changed(self, state: int) -> None:
        """Handle auto-scroll checkbox change."""
        self.auto_scroll = state == Qt.Checked.value

    def _on_filter_changed(self) -> None:
        """Handle filter changes."""
        self.filter_text = self.filter_input.text().lower()
        self.show_file_events = self.file_filter.isChecked()
        self.show_registry_events = self.registry_filter.isChecked()
        self.show_network_events = self.network_filter.isChecked()
        self.show_process_events = self.process_filter.isChecked()
        self.show_dll_events = self.dll_filter.isChecked()
        self.show_mem_events = self.mem_filter.isChecked()
        self.show_console_events = self.console_filter.isChecked()

    def _should_show_line(self, line: str) -> bool:
        """
        Determine if a line should be shown based on current filters.

        Parameters:
            line: The log line to check.

        Returns:
            True if the line should be displayed, False otherwise.
        """
        # Check text filter
        if self.filter_text and self.filter_text not in line.lower():
            return False

        # Check event type filters - match the actual badges used in events
        if not self.show_file_events and "[FILE]" in line:
            return False
        if not self.show_registry_events and ("[REG]" in line or "[REGISTRY]" in line):
            return False
        if not self.show_network_events and ("[NET]" in line or "[NETWORK]" in line):
            return False
        if not self.show_process_events and ("[PROC]" in line or "[PROCESS]" in line):
            return False
        if not self.show_dll_events and "[DLL]" in line:
            return False
        if not self.show_mem_events and ("[MEM]" in line or "[MEMORY]" in line):
            return False

        # Check console event filters - match level badges used in ConsoleEvent
        if not self.show_console_events:
            for badge in ["[INFO]", "[WARN]", "[ERR", "[ OK", "[DBG"]:
                if badge in line:
                    return False
                if badge in line:
                    return False

        return True

    @Slot(str)
    def append_log(self, message: str) -> None:
        """
        Thread-safe log append. Emits a signal that delivers on the main thread.
        Can be called from ANY thread safely.
        """
        self.log_received.emit(message)

    def _do_append_log(self, message: str) -> None:
        """
        Actually append a log message to the terminal.
        This runs on the main thread via the signal.
        """
        if self._should_show_line(message):
            self.terminal_output.appendPlainText(message)

            # Update line count
            line_count = self.terminal_output.blockCount()
            self.line_count_label.setText(f"{line_count} lines")

            # Auto-scroll to bottom if enabled
            if self.auto_scroll:
                scrollbar = self.terminal_output.verticalScrollBar()
                scrollbar.setValue(scrollbar.maximum())

    def clear(self) -> None:
        """Clear all terminal output."""
        self.terminal_output.clear()
        self.line_count_label.setText("0 lines")

    def get_log_text(self) -> str:
        """
        Get all the terminal output as a single string.

        Returns:
            The complete log text.
        """
        return self.terminal_output.toPlainText()

    def set_font_size(self, size: int) -> None:
        """
        Set the terminal font size.

        Parameters:
            size: The font size in pixels.
        """
        self.terminal_output.setStyleSheet(f"""
            QPlainTextEdit {{
                background-color: {BG_DEEP_BLACK};
                color: {TEXT_PRIMARY};
                border: 1px solid {BORDER_MEDIUM};
                border-radius: 6px;
                padding: 8px;
                font-family: '{FONT_FAMILY}', monospace;
                font-size: {size}px;
                selection-background-color: {NEON_CYAN}40;
            }}
        """)
