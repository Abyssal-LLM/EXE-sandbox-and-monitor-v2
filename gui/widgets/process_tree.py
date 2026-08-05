"""
Process tree widget for the EXE Sandbox.
This displays the live process hierarchy of sandboxed processes.
It updates in real-time showing PID, name, CPU, memory, and thread count.
"""
from typing import Dict, List, Optional

from PySide6.QtWidgets import (
    QTreeView, QVBoxLayout, QWidget, QFrame, QLabel,
    QHBoxLayout, QHeaderView, QMenu,
)
from PySide6.QtCore import Qt, Signal, Slot, QTimer, QModelIndex
from PySide6.QtGui import (
    QStandardItemModel, QStandardItem, QColor, QFont,
    QAction,
)

from gui.theme import (
    NEON_CYAN, NEON_GREEN, NEON_YELLOW, NEON_RED,
    BG_DEEP_BLACK, BG_PANEL, BG_WIDGET,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_DIM,
    BORDER_MEDIUM, FONT_FAMILY,
)


class ProcessTreeWidget(QFrame):
    """
    Widget that displays the live process tree of sandboxed processes.

    Features:
    - Real-time process hierarchy display
    - CPU and memory usage per process
    - Thread count display
    - Visual indicators for process status
    - Right-click context menu for process management

    Signals:
        terminate_requested: Emitted when user wants to terminate a process. Carries PID.
    """

    terminate_requested = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._setup_timer()

        # The process data - keyed by PID
        self.process_data: Dict[int, dict] = {}

        # The model for the tree view
        self.model = QStandardItemModel()
        self.model.setHorizontalHeaderLabels([
            "PID", "Name", "CPU%", "Memory", "Threads", "Status"
        ])

        # Set up the tree view
        self.tree_view.setModel(self.model)
        self.tree_view.header().setStretchLastSection(True)
        self.tree_view.setRootIsDecorated(True)
        self.tree_view.setAlternatingRowColors(False)
        self.tree_view.setSelectionMode(QTreeView.SingleSelection)
        self.tree_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree_view.customContextMenuRequested.connect(self._on_context_menu)

        # Set column widths
        header = self.tree_view.header()
        header.resizeSection(0, 60)   # PID
        header.resizeSection(1, 150)  # Name
        header.resizeSection(2, 60)   # CPU%
        header.resizeSection(3, 80)   # Memory
        header.resizeSection(4, 60)   # Threads
        header.resizeSection(5, 70)   # Status

    def _setup_ui(self) -> None:
        """Set up the process tree UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # Header
        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)

        title = QLabel("PROCESS TREE")
        title.setStyleSheet(f"""
            color: {NEON_YELLOW};
            font-family: '{FONT_FAMILY}', monospace;
            font-size: 12px;
            font-weight: bold;
            letter-spacing: 2px;
        """)
        header_layout.addWidget(title)

        header_layout.addStretch()

        self.process_count_label = QLabel("0 processes")
        self.process_count_label.setStyleSheet(f"""
            color: {TEXT_SECONDARY};
            font-family: '{FONT_FAMILY}', monospace;
            font-size: 11px;
        """)
        header_layout.addWidget(self.process_count_label)

        layout.addLayout(header_layout)

        # Tree view
        self.tree_view = QTreeView()
        self.tree_view.setStyleSheet(f"""
            QTreeView {{
                background-color: {BG_DEEP_BLACK};
                color: {TEXT_PRIMARY};
                border: 1px solid {BORDER_MEDIUM};
                border-radius: 6px;
                padding: 4px;
                font-family: '{FONT_FAMILY}', monospace;
                font-size: 11px;
                outline: none;
            }}
            QTreeView::item {{
                padding: 4px 8px;
                border-radius: 3px;
                min-height: 22px;
            }}
            QTreeView::item:hover {{
                background-color: {NEON_CYAN}10;
            }}
            QTreeView::item:selected {{
                background-color: {NEON_CYAN}20;
                color: {NEON_CYAN};
            }}
            QHeaderView::section {{
                background-color: {BG_WIDGET};
                color: {TEXT_SECONDARY};
                border: none;
                border-bottom: 1px solid {BORDER_MEDIUM};
                padding: 6px;
                font-weight: bold;
                font-size: 11px;
            }}
        """)
        layout.addWidget(self.tree_view)

    def _setup_timer(self) -> None:
        """Set up the timer for periodic updates."""
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self._update_display)
        self.update_timer.start(500)  # Update every 500ms

    def _on_context_menu(self, position) -> None:
        """Handle right-click context menu."""
        index = self.tree_view.indexAt(position)
        if not index.isValid():
            return

        # Get the PID from the selected item
        item = self.model.itemFromIndex(index.sibling(index.row(), 0))
        if item is None:
            return

        pid = item.data()
        if pid is None:
            return

        # Create the context menu
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {BG_WIDGET};
                color: {TEXT_PRIMARY};
                border: 1px solid {BORDER_MEDIUM};
                border-radius: 6px;
                padding: 4px;
            }}
            QMenu::item {{
                padding: 6px 24px;
                border-radius: 4px;
            }}
            QMenu::item:selected {{
                background-color: {NEON_CYAN}20;
                color: {NEON_CYAN};
            }}
        """)

        # Terminate action
        terminate_action = QAction("Terminate Process", self)
        terminate_action.triggered.connect(lambda: self.terminate_requested.emit(pid))
        menu.addAction(terminate_action)

        menu.exec(self.tree_view.viewport().mapToGlobal(position))

    @Slot(list)
    def update_process_tree(self, processes: list) -> None:
        """
        Update the process tree with new data.

        Parameters:
            processes: List of process dictionaries from the sandbox engine.
        """
        self.process_data = {p['pid']: p for p in processes}

    def _update_display(self) -> None:
        """Update the tree view display with current process data."""
        # Clear the existing model
        self.model.removeRows(0, self.model.rowCount())

        # Add each process to the tree
        for pid, proc in self.process_data.items():
            # Create items for each column
            pid_item = QStandardItem(str(pid))
            pid_item.setData(pid)
            pid_item.setTextAlignment(Qt.AlignCenter)

            name_item = QStandardItem(proc.get('name', 'unknown'))

            cpu = proc.get('cpu_percent', 0.0)
            cpu_item = QStandardItem(f"{cpu:.1f}%")
            cpu_item.setTextAlignment(Qt.AlignCenter)
            if cpu > 50:
                cpu_item.setForeground(QColor(NEON_RED))
            elif cpu > 20:
                cpu_item.setForeground(QColor(NEON_YELLOW))
            else:
                cpu_item.setForeground(QColor(NEON_GREEN))

            memory = proc.get('memory_mb', 0.0)
            if memory > 1024:
                mem_text = f"{memory/1024:.1f}GB"
            else:
                mem_text = f"{memory:.0f}MB"
            mem_item = QStandardItem(mem_text)
            mem_item.setTextAlignment(Qt.AlignCenter)

            threads = proc.get('thread_count', 0)
            thread_item = QStandardItem(str(threads))
            thread_item.setTextAlignment(Qt.AlignCenter)

            is_alive = proc.get('is_alive', True)
            status_item = QStandardItem("RUNNING" if is_alive else "EXITED")
            status_item.setTextAlignment(Qt.AlignCenter)
            if is_alive:
                status_item.setForeground(QColor(NEON_GREEN))
            else:
                status_item.setForeground(QColor(NEON_RED))

            # Add the row to the model
            self.model.appendRow([
                pid_item, name_item, cpu_item, mem_item, thread_item, status_item
            ])

        # Update the process count label
        active_count = sum(1 for p in self.process_data.values() if p.get('is_alive', True))
        self.process_count_label.setText(f"{active_count} active / {len(self.process_data)} total")

    def clear(self) -> None:
        """Clear all process data."""
        self.process_data.clear()
        self.model.removeRows(0, self.model.rowCount())
        self.process_count_label.setText("0 processes")
