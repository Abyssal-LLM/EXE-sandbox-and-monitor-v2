"""
Statistics panel widget for the EXE Sandbox.
This displays real-time statistics about the sandbox session.
"""
from PySide6.QtWidgets import (
    QFrame, QLabel, QVBoxLayout, QHBoxLayout, QWidget,
)
from PySide6.QtCore import Qt

from gui.theme import (
    NEON_CYAN, NEON_GREEN, NEON_YELLOW, NEON_RED, NEON_MAGENTA,
    BG_DEEP_BLACK, BG_PANEL, BG_WIDGET,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_DIM,
    BORDER_MEDIUM, BORDER_DARK, FONT_FAMILY,
)


class StatsPanelWidget(QFrame):
    """
    Widget that displays real-time sandbox statistics.

    Shows:
    - CPU usage
    - Memory usage
    - Active processes
    - Event counts by type
    - Session duration
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("statsFrame")
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the stats panel UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(16)

        # CPU stat
        cpu_layout = QVBoxLayout()
        cpu_layout.setSpacing(2)
        cpu_title = QLabel("CPU")
        cpu_title.setStyleSheet(f"""
            color: {TEXT_SECONDARY};
            font-family: '{FONT_FAMILY}', monospace;
            font-size: 10px;
            letter-spacing: 1px;
        """)
        cpu_title.setAlignment(Qt.AlignCenter)
        cpu_layout.addWidget(cpu_title)

        self.cpu_value = QLabel("0.0%")
        self.cpu_value.setStyleSheet(f"""
            color: {NEON_GREEN};
            font-family: '{FONT_FAMILY}', monospace;
            font-size: 16px;
            font-weight: bold;
        """)
        self.cpu_value.setAlignment(Qt.AlignCenter)
        cpu_layout.addWidget(self.cpu_value)

        layout.addLayout(cpu_layout)

        # Separator
        sep1 = QFrame()
        sep1.setFrameShape(QFrame.VLine)
        sep1.setStyleSheet(f"color: {BORDER_DARK};")
        layout.addWidget(sep1)

        # Memory stat
        mem_layout = QVBoxLayout()
        mem_layout.setSpacing(2)
        mem_title = QLabel("MEMORY")
        mem_title.setStyleSheet(f"""
            color: {TEXT_SECONDARY};
            font-family: '{FONT_FAMILY}', monospace;
            font-size: 10px;
            letter-spacing: 1px;
        """)
        mem_title.setAlignment(Qt.AlignCenter)
        mem_layout.addWidget(mem_title)

        self.mem_value = QLabel("0 MB")
        self.mem_value.setStyleSheet(f"""
            color: {NEON_CYAN};
            font-family: '{FONT_FAMILY}', monospace;
            font-size: 16px;
            font-weight: bold;
        """)
        self.mem_value.setAlignment(Qt.AlignCenter)
        mem_layout.addWidget(self.mem_value)

        layout.addLayout(mem_layout)

        # Separator
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.VLine)
        sep2.setStyleSheet(f"color: {BORDER_DARK};")
        layout.addWidget(sep2)

        # Processes stat
        proc_layout = QVBoxLayout()
        proc_layout.setSpacing(2)
        proc_title = QLabel("PROCESSES")
        proc_title.setStyleSheet(f"""
            color: {TEXT_SECONDARY};
            font-family: '{FONT_FAMILY}', monospace;
            font-size: 10px;
            letter-spacing: 1px;
        """)
        proc_title.setAlignment(Qt.AlignCenter)
        proc_layout.addWidget(proc_title)

        self.proc_value = QLabel("0")
        self.proc_value.setStyleSheet(f"""
            color: {NEON_YELLOW};
            font-family: '{FONT_FAMILY}', monospace;
            font-size: 16px;
            font-weight: bold;
        """)
        self.proc_value.setAlignment(Qt.AlignCenter)
        proc_layout.addWidget(self.proc_value)

        layout.addLayout(proc_layout)

        # Separator
        sep3 = QFrame()
        sep3.setFrameShape(QFrame.VLine)
        sep3.setStyleSheet(f"color: {BORDER_DARK};")
        layout.addWidget(sep3)

        # Threads stat
        thread_layout = QVBoxLayout()
        thread_layout.setSpacing(2)
        thread_title = QLabel("THREADS")
        thread_title.setStyleSheet(f"""
            color: {TEXT_SECONDARY};
            font-family: '{FONT_FAMILY}', monospace;
            font-size: 10px;
            letter-spacing: 1px;
        """)
        thread_title.setAlignment(Qt.AlignCenter)
        thread_layout.addWidget(thread_title)

        self.thread_value = QLabel("0")
        self.thread_value.setStyleSheet(f"""
            color: {NEON_MAGENTA};
            font-family: '{FONT_FAMILY}', monospace;
            font-size: 16px;
            font-weight: bold;
        """)
        self.thread_value.setAlignment(Qt.AlignCenter)
        thread_layout.addWidget(self.thread_value)

        layout.addLayout(thread_layout)

        # Separator
        sep4 = QFrame()
        sep4.setFrameShape(QFrame.VLine)
        sep4.setStyleSheet(f"color: {BORDER_DARK};")
        layout.addWidget(sep4)

        # Events stat
        event_layout = QVBoxLayout()
        event_layout.setSpacing(2)
        event_title = QLabel("EVENTS")
        event_title.setStyleSheet(f"""
            color: {TEXT_SECONDARY};
            font-family: '{FONT_FAMILY}', monospace;
            font-size: 10px;
            letter-spacing: 1px;
        """)
        event_title.setAlignment(Qt.AlignCenter)
        event_layout.addWidget(event_title)

        self.event_value = QLabel("0")
        self.event_value.setStyleSheet(f"""
            color: {TEXT_PRIMARY};
            font-family: '{FONT_FAMILY}', monospace;
            font-size: 16px;
            font-weight: bold;
        """)
        self.event_value.setAlignment(Qt.AlignCenter)
        event_layout.addWidget(self.event_value)

        layout.addLayout(event_layout)

        # Separator
        sep5 = QFrame()
        sep5.setFrameShape(QFrame.VLine)
        sep5.setStyleSheet(f"color: {BORDER_DARK};")
        layout.addWidget(sep5)

        # Duration stat
        dur_layout = QVBoxLayout()
        dur_layout.setSpacing(2)
        dur_title = QLabel("DURATION")
        dur_title.setStyleSheet(f"""
            color: {TEXT_SECONDARY};
            font-family: '{FONT_FAMILY}', monospace;
            font-size: 10px;
            letter-spacing: 1px;
        """)
        dur_title.setAlignment(Qt.AlignCenter)
        dur_layout.addWidget(dur_title)

        self.dur_value = QLabel("00:00")
        self.dur_value.setStyleSheet(f"""
            color: {TEXT_PRIMARY};
            font-family: '{FONT_FAMILY}', monospace;
            font-size: 16px;
            font-weight: bold;
        """)
        self.dur_value.setAlignment(Qt.AlignCenter)
        dur_layout.addWidget(self.dur_value)

        layout.addLayout(dur_layout)

    def update_stats(self, stats: dict) -> None:
        """
        Update the statistics display.

        Parameters:
            stats: Dictionary containing sandbox statistics.
        """
        # CPU
        cpu = stats.get('cpu_percent', 0.0)
        self.cpu_value.setText(f"{cpu:.1f}%")
        if cpu > 80:
            self.cpu_value.setStyleSheet(f"""
                color: {NEON_RED};
                font-family: '{FONT_FAMILY}', monospace;
                font-size: 16px;
                font-weight: bold;
            """)
        elif cpu > 50:
            self.cpu_value.setStyleSheet(f"""
                color: {NEON_YELLOW};
                font-family: '{FONT_FAMILY}', monospace;
                font-size: 16px;
                font-weight: bold;
            """)
        else:
            self.cpu_value.setStyleSheet(f"""
                color: {NEON_GREEN};
                font-family: '{FONT_FAMILY}', monospace;
                font-size: 16px;
                font-weight: bold;
            """)

        # Memory
        memory = stats.get('memory_mb', 0.0)
        if memory > 1024:
            self.mem_value.setText(f"{memory/1024:.1f} GB")
        else:
            self.mem_value.setText(f"{memory:.0f} MB")

        # Processes
        procs = stats.get('active_processes', 0)
        self.proc_value.setText(str(procs))

        # Threads
        threads = stats.get('threads', 0)
        self.thread_value.setText(str(threads))

        # Events
        events = stats.get('total_events', 0)
        self.event_value.setText(str(events))

        # Duration
        duration = stats.get('session_duration', 0.0)
        minutes = int(duration // 60)
        seconds = int(duration % 60)
        self.dur_value.setText(f"{minutes:02d}:{seconds:02d}")

    def clear(self) -> None:
        """Reset all statistics to zero."""
        self.cpu_value.setText("0.0%")
        self.mem_value.setText("0 MB")
        self.proc_value.setText("0")
        self.thread_value.setText("0")
        self.event_value.setText("0")
        self.dur_value.setText("00:00")
