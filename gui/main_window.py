"""
Main window for the EXE Sandbox application.
This ties together all the widgets and the sandbox engine into a cohesive GUI.
"""
import os
import time
import threading

import psutil

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QSplitter, QFrame, QLabel, QFileDialog, QMessageBox,
    QApplication, QPushButton,
)
from PySide6.QtCore import Qt, Slot, QTimer, QThread, Signal

from gui.theme import (
    NEON_CYAN, NEON_GREEN, NEON_YELLOW, NEON_MAGENTA,
    BG_DEEP_BLACK, BG_DARK, BG_PANEL,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_DIM,
    BORDER_MEDIUM, FONT_FAMILY, get_stylesheet,
)
from sandbox.engine import SandboxEngineScript
from gui.widgets.exe_loader import ExeLoaderWidget
from gui.widgets.terminal import TerminalWidget
from gui.widgets.process_tree import ProcessTreeWidget
from gui.widgets.stats_panel import StatsPanelWidget
from gui.widgets.control_bar import ControlBarWidget
from gui.widgets.embedded_window import EmbeddedWindowWidget
from gui.widgets.event_panel import EventPanel
from gui.widgets.log_snapshot import LogSnapshotWidget
from sandbox.model_explainer import ModelExplainer


class SandboxWorker(QThread):
    stats_updated = Signal(dict)

    def __init__(self, engine: SandboxEngineScript, parent=None):
        super().__init__(parent)
        self.engine = engine
        self._running = False

    def run(self):
        self._running = True
        while self._running:
            if self.engine.is_running:
                stats = self.engine.get_stats()
                stats['total_events'] = len(self.engine.event_bus.get_history())
                self.stats_updated.emit(stats)
            time.sleep(0.5)

    def stop(self):
        self._running = False


class MainWindow(QMainWindow):

    # Thread-safe signals: background threads emit these, slots run on main thread
    _explanation_ready = Signal(str, str)   # (raw_line, explanation)
    _model_status = Signal(bool, str)       # (success, error_message)

    def __init__(self):
        super().__init__()

        self.engine = SandboxEngineScript()
        self.model_explainer = ModelExplainer()

        # Debounce state for click-to-explain
        self._explanation_pending = False
        self._pending_line = ""
        self._last_clicked_line = ""  # for auto-retry after model loads

        # Save embed state across KB mode
        self._embed_was_checked = False

        self.engine.event_bus.subscribe(self._on_event_received)

        self._setup_ui()
        self._setup_connections()

        self.worker = SandboxWorker(self.engine)
        self.worker.stats_updated.connect(self._on_stats_updated)
        self.worker.start()

        self._load_model_async()

    def _setup_ui(self) -> None:
        self.setWindowTitle("EXE SANDBOX AND MONITOR v2")
        self.setMinimumSize(1200, 800)
        self.resize(1400, 900)
        self.setStyleSheet(get_stylesheet())

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(12)

        # --- Title bar ---
        title_layout = QHBoxLayout()
        title_layout.setSpacing(12)

        title_label = QLabel("EXE SANDBOX")
        title_label.setObjectName("titleLabel")
        title_label.setStyleSheet(f"""
            color: {NEON_CYAN};
            font-family: '{FONT_FAMILY}', monospace;
            font-size: 24px;
            font-weight: bold;
            letter-spacing: 3px;
        """)
        title_layout.addWidget(title_label)

        subtitle_label = QLabel("// MONITORING EDITION")
        subtitle_label.setStyleSheet(f"""
            color: {TEXT_SECONDARY};
            font-family: '{FONT_FAMILY}', monospace;
            font-size: 11px;
            letter-spacing: 1px;
        """)
        title_layout.addWidget(subtitle_label)

        title_layout.addStretch()
        main_layout.addLayout(title_layout)

        # --- EXE Loader (hidden in KB mode) ---
        self.exe_loader = ExeLoaderWidget()
        main_layout.addWidget(self.exe_loader)

        # --- Control bar (hidden in KB mode) ---
        self.control_bar = ControlBarWidget()
        main_layout.addWidget(self.control_bar)

        # --- Main content splitter ---
        content_splitter = QSplitter(Qt.Horizontal)
        content_splitter.setHandleWidth(4)

        # Left - Process tree
        left_panel = QFrame()
        left_panel.setStyleSheet(f"""
            QFrame {{
                background-color: {BG_PANEL};
                border: 1px solid {BORDER_MEDIUM};
                border-radius: 8px;
            }}
        """)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(8, 8, 8, 8)
        left_layout.setSpacing(8)
        self.process_tree = ProcessTreeWidget()
        left_layout.addWidget(self.process_tree)
        content_splitter.addWidget(left_panel)

        # Right - Terminal + controls
        right_panel = QFrame()
        right_panel.setStyleSheet(f"""
            QFrame {{
                background-color: {BG_PANEL};
                border: 1px solid {BORDER_MEDIUM};
                border-radius: 8px;
            }}
        """)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(8, 8, 8, 8)
        right_layout.setSpacing(8)

        # Terminal header
        terminal_header = QHBoxLayout()
        terminal_title = QLabel("MONITORING TERMINAL")
        terminal_title.setStyleSheet(f"""
            color: {NEON_GREEN};
            font-family: '{FONT_FAMILY}', monospace;
            font-size: 12px;
            font-weight: bold;
            letter-spacing: 2px;
        """)
        terminal_header.addWidget(terminal_title)
        terminal_header.addStretch()

        self.embed_toggle = QPushButton("EMBED WINDOW")
        self.embed_toggle.setFixedWidth(120)
        self.embed_toggle.setCheckable(True)
        self.embed_toggle.setStyleSheet(f"""
            QPushButton {{
                background-color: {BG_DEEP_BLACK};
                color: {NEON_CYAN};
                border: 1px solid {NEON_CYAN};
                border-radius: 6px;
                font-family: '{FONT_FAMILY}', monospace;
                font-size: 11px;
                font-weight: bold;
                padding: 4px 8px;
            }}
            QPushButton:hover {{ background-color: {NEON_CYAN}15; }}
            QPushButton:checked {{ background-color: {NEON_CYAN}30; color: {NEON_CYAN}; }}
        """)
        self.embed_toggle.clicked.connect(self._on_embed_toggle)
        terminal_header.addWidget(self.embed_toggle)

        self.kb_toggle = QPushButton("KB")
        self.kb_toggle.setFixedWidth(40)
        self.kb_toggle.setCheckable(True)
        self.kb_toggle.setToolTip("Toggle KB mode — click terminal lines for AI explanation")
        self.kb_toggle.setStyleSheet(f"""
            QPushButton {{
                background-color: {BG_DEEP_BLACK};
                color: {NEON_MAGENTA};
                border: 1px solid {NEON_MAGENTA};
                border-radius: 6px;
                font-family: '{FONT_FAMILY}', monospace;
                font-size: 11px;
                font-weight: bold;
                padding: 4px 8px;
            }}
            QPushButton:hover {{ background-color: {NEON_MAGENTA}15; }}
            QPushButton:checked {{ background-color: {NEON_MAGENTA}30; color: {NEON_MAGENTA}; }}
        """)
        self.kb_toggle.clicked.connect(self._on_kb_toggle)
        terminal_header.addWidget(self.kb_toggle)

        self.event_count_label = QLabel("0 events")
        self.event_count_label.setStyleSheet(f"""
            color: {TEXT_SECONDARY};
            font-family: '{FONT_FAMILY}', monospace;
            font-size: 11px;
        """)
        terminal_header.addWidget(self.event_count_label)

        right_layout.addLayout(terminal_header)

        # Embedded window (hidden by default)
        self.embedded_window = EmbeddedWindowWidget()
        self.embedded_window.setMinimumHeight(200)
        self.embedded_window.hide()
        right_layout.addWidget(self.embedded_window)

        # Terminal
        self.terminal = TerminalWidget()
        right_layout.addWidget(self.terminal)

        # Log snapshot (hidden, shown in KB mode instead of terminal)
        self.log_snapshot = LogSnapshotWidget()
        self.log_snapshot.hide()
        right_layout.addWidget(self.log_snapshot)

        content_splitter.addWidget(right_panel)
        content_splitter.setSizes([350, 900])

        main_layout.addWidget(content_splitter, 1)

        # --- Event panel (hidden by default, inserted into splitter in KB mode) ---
        self.event_panel = EventPanel()
        self.event_panel.hide()
        self._content_splitter = content_splitter

        # Stats panel (hidden in KB mode)
        self.stats_panel = StatsPanelWidget()
        main_layout.addWidget(self.stats_panel)

        # Status bar
        self.statusBar().showMessage("Ready")
        self.statusBar().setStyleSheet(f"""
            QStatusBar {{
                background-color: {BG_DARK};
                color: {TEXT_SECONDARY};
                border-top: 1px solid {BORDER_MEDIUM};
                font-family: '{FONT_FAMILY}', monospace;
                font-size: 11px;
            }}
        """)

    def _setup_connections(self) -> None:
        self.exe_loader.exe_loaded.connect(self._on_exe_loaded)
        self.exe_loader.exe_cleared.connect(self._on_exe_cleared)
        self.control_bar.start_clicked.connect(self._on_start_clicked)
        self.control_bar.stop_clicked.connect(self._on_stop_clicked)
        self.control_bar.clear_clicked.connect(self._on_clear_clicked)
        self.control_bar.export_clicked.connect(self._on_export_clicked)
        self.terminal.export_requested.connect(self._on_export_clicked)
        self.process_tree.terminate_requested.connect(self._on_terminate_requested)
        self.embedded_window.window_lost.connect(self._on_embedded_window_lost)
        self.event_panel.close_requested.connect(self._on_event_panel_close)
        self.log_snapshot.line_clicked.connect(self._on_explain_requested)
        # Thread-safe signals from background threads
        self._explanation_ready.connect(self._on_explanation_ready)
        self._model_status.connect(self._on_model_status)

    # ---- Sandbox control handlers (unchanged) ----

    @Slot(str)
    def _on_exe_loaded(self, exe_path: str) -> None:
        self.engine.load_exe(exe_path)
        self.statusBar().showMessage(f"Loaded: {os.path.basename(exe_path)}")

    @Slot()
    def _on_exe_cleared(self) -> None:
        if self.engine.is_running:
            self.engine.stop()
            self.control_bar.set_running(False)
        self.statusBar().showMessage("Ready")

    @Slot()
    def _on_start_clicked(self) -> None:
        exe_path = self.exe_loader.get_exe_path()
        if not exe_path:
            QMessageBox.warning(self, "No EXE Loaded",
                                "Please load an EXE file before starting the sandbox.")
            return
        args = self.exe_loader.get_args()
        workdir = self.exe_loader.get_workdir()
        embedded = self.embed_toggle.isChecked()
        success = self.engine.start(args, workdir, embedded=embedded)
        if success:
            self.statusBar().showMessage("Sandbox running")
            if embedded:
                QTimer.singleShot(1000, self._try_embed_window)
        else:
            self.control_bar.set_running(False)
            QMessageBox.critical(self, "Failed to Start",
                                 "Failed to start the sandbox. Check the terminal for details.")

    def _try_embed_window(self) -> None:
        if not self.engine.is_running:
            return
        pid = self.engine.process_manager.main_pid
        if pid > 0:
            success = self.embedded_window.embed_window_by_pid(pid, timeout=5.0)
            if success:
                self.terminal.append_log(f"[SANDBOX] Window embedded for PID {pid}")
            else:
                self.terminal.append_log(
                    f"[SANDBOX] Could not find window for PID {pid} - process may be console-only")

    @Slot()
    def _on_stop_clicked(self) -> None:
        if self.embedded_window.is_embedded:
            self.embedded_window.detach_window()
        self.engine.stop()
        self.control_bar.set_running(False)
        self.statusBar().showMessage("Sandbox stopped")

    @Slot()
    def _on_embed_toggle(self) -> None:
        if self.embed_toggle.isChecked():
            self.embedded_window.show()
            self.terminal.setMaximumHeight(250)
            self.statusBar().showMessage("Embedded mode enabled")
        else:
            if self.embedded_window.is_embedded:
                self.embedded_window.detach_window()
            self.embedded_window.hide()
            self.terminal.setMaximumHeight(16777215)
            self.statusBar().showMessage("Monitor mode")

    @Slot()
    def _on_clear_clicked(self) -> None:
        self.terminal.clear()
        self.process_tree.clear()
        self.stats_panel.clear()
        self.engine.event_bus.clear_history()
        self.statusBar().showMessage("Cleared")

    @Slot()
    def _on_export_clicked(self) -> None:
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Log",
            f"sandbox_log_{int(time.time())}.txt",
            "Text Files (*.txt);;All Files (*.*)")
        if file_path:
            try:
                log_text = self.terminal.get_log_text()
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(log_text)
                self.statusBar().showMessage(f"Log exported to: {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Export Failed",
                                     f"Failed to export log: {e}")

    # ---- KB mode ----

    @Slot()
    def _on_kb_toggle(self) -> None:
        if self.kb_toggle.isChecked():
            self._enter_kb_mode()
        else:
            self._exit_kb_mode()

    def _enter_kb_mode(self) -> None:
        """Switch to focused KB mode: show log snapshot + event panel, hide controls."""

        # Save embed state before hiding
        self._embed_was_checked = self.embed_toggle.isChecked()

        # Hide sandbox control widgets
        self.exe_loader.hide()
        self.control_bar.hide()
        self.embed_toggle.hide()
        self.embedded_window.hide()
        self.stats_panel.hide()

        # Populate snapshot from current terminal history
        log_text = self.terminal.get_log_text()
        lines = [l for l in log_text.split("\n") if l.strip()]
        self.log_snapshot.load_lines(lines)

        # Show snapshot instead of terminal
        self.terminal.hide()
        self.log_snapshot.show()

        # Insert event panel as a third section in the splitter
        if self.event_panel.parent() is not None:
            self.event_panel.setParent(None)
        self._content_splitter.addWidget(self.event_panel)
        self.event_panel.show()
        self.event_panel.show_hint()
        self._content_splitter.setSizes([300, 500, 500])

        # Reset terminal height
        self.terminal.setMaximumHeight(16777215)

        self.statusBar().showMessage("KB mode — click any log line for AI explanation")

    def _exit_kb_mode(self) -> None:
        """Restore normal mode: show all controls, hide event panel and snapshot."""

        # Hide event panel and snapshot, show terminal
        self.event_panel.hide()
        self.log_snapshot.hide()
        self.terminal.show()
        self._content_splitter.setSizes([350, 900])

        # Restore sandbox control widgets
        self.exe_loader.show()
        self.control_bar.show()
        self.stats_panel.show()

        # Restore embed state
        if self._embed_was_checked:
            self.embed_toggle.setChecked(True)
            self.embedded_window.show()
        else:
            self.embed_toggle.setChecked(False)

        self.terminal.setMaximumHeight(16777215)
        self.statusBar().showMessage("KB mode off")

    @Slot()
    def _on_event_panel_close(self) -> None:
        """Close button on event panel — exit KB mode."""
        self.kb_toggle.setChecked(False)
        self._exit_kb_mode()

    def keyPressEvent(self, event) -> None:
        """Escape exits KB mode."""
        if event.key() == Qt.Key_Escape and self.kb_toggle.isChecked():
            self.kb_toggle.setChecked(False)
            self._exit_kb_mode()
            return
        super().keyPressEvent(event)

    # ---- Explain (click on terminal line) ----

    @Slot(str)
    def _on_explain_requested(self, line: str) -> None:
        """Handle click on a log snapshot line — show AI explanation."""
        if not line.strip():
            return

        self.event_panel.show_event(line, "Generating explanation...")

        # Check if model is ready
        if not self.model_explainer.is_loaded:
            if self.model_explainer.is_loading:
                self.event_panel.show_event(line, "Model loading — click this line again when ready")
            else:
                err = self.model_explainer.load_error or "unknown error"
                self.event_panel.show_event(line, f"AI model failed to load: {err}")
            self._last_clicked_line = line
            return

        self._last_clicked_line = ""

        # Debounce: if already running, just update the pending line
        if self._explanation_pending:
            self._pending_line = line
            return

        self._explanation_pending = True
        self._pending_line = ""

        def _run():
            explanation = self.model_explainer.explain(line)
            self._explanation_ready.emit(line, explanation)

        thread = threading.Thread(target=_run, daemon=True)
        thread.start()

    @Slot(str, str)
    def _on_explanation_ready(self, line: str, explanation: str) -> None:
        """Called on the main thread when the model finishes explaining."""
        self._explanation_pending = False

        # If a newer click arrived while we were running, use that line instead
        if self._pending_line:
            pending = self._pending_line
            self._pending_line = ""
            self.event_panel.show_event(pending, "Generating explanation...")
            self._explanation_pending = True
            def _run():
                exp = self.model_explainer.explain(pending)
                self._explanation_ready.emit(pending, exp)
            thread = threading.Thread(target=_run, daemon=True)
            thread.start()
            return

        self.event_panel.show_event(line, explanation)

    # ---- Other handlers ----

    @Slot(int)
    def _on_terminate_requested(self, pid: int) -> None:
        try:
            proc = psutil.Process(pid)
            proc.terminate()
            self.terminal.append_log(f"[SANDBOX] Terminated process: {proc.name()}({pid})")
        except Exception as e:
            self.terminal.append_log(f"[SANDBOX] Failed to terminate PID {pid}: {e}")

    @Slot()
    def _on_embedded_window_lost(self) -> None:
        self.terminal.append_log("[SANDBOX] Embedded window closed")

    def _on_event_received(self, event) -> None:
        log_line = event.to_log_string()
        self.terminal.append_log(log_line)
        # Also append to snapshot if KB mode is active
        if self.kb_toggle.isChecked():
            self.log_snapshot.append_line(log_line)

    @Slot(dict)
    def _on_stats_updated(self, stats: dict) -> None:
        # Flatten nested stats for the stats panel
        flat_stats = {
            **stats.get('process', {}),
            **stats.get('monitor', {}),
            'session_duration': stats.get('session_duration', 0.0),
            'is_running': stats.get('is_running', False),
            'total_events': stats.get('total_events', 0),
        }
        self.stats_panel.update_stats(flat_stats)
        process_tree = self.engine.get_process_tree()
        self.process_tree.update_process_tree(process_tree)
        event_count = flat_stats.get('total_events', 0)
        self.event_count_label.setText(f"{event_count} events")

    def _load_model_async(self) -> None:
        self.statusBar().showMessage("Loading AI model...")

        def _load():
            success = self.model_explainer.load()
            err = self.model_explainer.load_error or ""
            self._model_status.emit(success, err)

        thread = threading.Thread(target=_load, daemon=True)
        thread.start()

    @Slot(bool, str)
    def _on_model_status(self, success: bool, error: str) -> None:
        """Called on the main thread when model load finishes."""
        if success:
            self.statusBar().showMessage("AI model ready")
            # Auto-retry: if user clicked a line while model was loading, explain it now
            if self._last_clicked_line and self.kb_toggle.isChecked():
                line = self._last_clicked_line
                self._last_clicked_line = ""
                self.event_panel.show_event(line, "Generating explanation...")
                self._explanation_pending = True
                def _run():
                    exp = self.model_explainer.explain(line)
                    self._explanation_ready.emit(line, exp)
                thread = threading.Thread(target=_run, daemon=True)
                thread.start()
        else:
            self.statusBar().showMessage(f"Model load failed: {error}")

    def closeEvent(self, event) -> None:
        self.worker.stop()
        self.worker.wait(1000)
        self.engine.event_bus.unsubscribe(self._on_event_received)
        self.engine.cleanup()
        event.accept()
