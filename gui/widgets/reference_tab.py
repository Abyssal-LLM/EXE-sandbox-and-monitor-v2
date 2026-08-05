"""
Reference Database tab widget for the EXE Sandbox.
Provides a searchable, browsable knowledge base that explains every
event type, registry key, file path, network operation, DLL, and
memory operation in plain human language.
"""
from typing import Optional, List

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QLineEdit, QListWidget, QListWidgetItem, QTextEdit,
    QLabel, QFrame, QPushButton, QComboBox, QCheckBox,
    QButtonGroup, QScrollArea,
)
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QFont, QColor, QTextCharFormat, QTextCursor

from gui.theme import (
    NEON_CYAN, NEON_GREEN, NEON_YELLOW, NEON_RED, NEON_MAGENTA, NEON_ORANGE,
    BG_DEEP_BLACK, BG_DARK, BG_PANEL, BG_WIDGET, BG_INPUT, BG_HOVER,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_DIM, BORDER_MEDIUM, BORDER_LIGHT,
    FONT_FAMILY, FONT_FAMILY_UI,
)
from gui.widgets.knowledge_base import (
    KnowledgeBase, KBEntry, EntryCategory, Severity, knowledge_base,
)
from gui.widgets.line_explainer import explain_line, parse_line


class ReferenceTabWidget(QFrame):
    """
    The Reference Database tab — a searchable, browsable knowledge base
    that explains everything the terminal outputs in human language.

    Layout:
    - Top: Search bar + category filter
    - Left: Entry list with category headers
    - Right: Full detail view of selected entry
    - Bottom: Severity indicator + related entries
    """

    entry_selected = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("referenceTab")
        self.kb = knowledge_base
        self.current_entry: Optional[KBEntry] = None
        self.current_category: Optional[EntryCategory] = None

        self._setup_ui()
        self._populate_categories()
        self._populate_entries()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # =====================================================
        # HEADER
        # =====================================================
        header_layout = QHBoxLayout()
        header_layout.setSpacing(12)

        title = QLabel("KNOWLEDGE BASE")
        title.setStyleSheet(f"""
            color: {NEON_CYAN};
            font-family: '{FONT_FAMILY}', monospace;
            font-size: 16px;
            font-weight: bold;
            letter-spacing: 3px;
        """)
        header_layout.addWidget(title)

        subtitle = QLabel(f"// {len(self.kb.entries)} entries")
        subtitle.setStyleSheet(f"""
            color: {TEXT_SECONDARY};
            font-family: '{FONT_FAMILY}', monospace;
            font-size: 11px;
        """)
        self.entry_count_label = subtitle
        header_layout.addWidget(subtitle)
        header_layout.addStretch()

        layout.addLayout(header_layout)

        # =====================================================
        # SEARCH + FILTER BAR
        # =====================================================
        search_frame = QFrame()
        search_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {BG_WIDGET};
                border: 1px solid {BORDER_MEDIUM};
                border-radius: 8px;
                padding: 6px;
            }}
        """)
        search_layout = QHBoxLayout(search_frame)
        search_layout.setContentsMargins(8, 4, 8, 4)
        search_layout.setSpacing(12)

        # Search input
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search the database... (e.g. 'persistence', 'ws2_32', 'port 445')")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {BG_INPUT};
                color: {TEXT_PRIMARY};
                border: 1px solid {BORDER_MEDIUM};
                border-radius: 6px;
                padding: 8px 12px;
                font-family: '{FONT_FAMILY}', monospace;
                font-size: 13px;
                selection-background-color: {NEON_CYAN}40;
            }}
            QLineEdit:focus {{
                border-color: {NEON_CYAN};
            }}
        """)
        search_layout.addWidget(self.search_input)

        # Category filter
        cat_label = QLabel("Category:")
        cat_label.setStyleSheet(f"color: {TEXT_SECONDARY}; font-family: '{FONT_FAMILY_UI}'; font-size: 12px;")
        search_layout.addWidget(cat_label)

        self.category_combo = QComboBox()
        self.category_combo.setMinimumWidth(180)
        self.category_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {BG_INPUT};
                color: {TEXT_PRIMARY};
                border: 1px solid {BORDER_MEDIUM};
                border-radius: 6px;
                padding: 6px 10px;
                font-family: '{FONT_FAMILY_UI}';
                font-size: 12px;
            }}
            QComboBox:hover {{
                border-color: {NEON_CYAN};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 24px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {BG_WIDGET};
                color: {TEXT_PRIMARY};
                border: 1px solid {BORDER_MEDIUM};
                selection-background-color: {NEON_CYAN}30;
            }}
        """)
        search_layout.addWidget(self.category_combo)

        # Severity filter
        sev_label = QLabel("Min severity:")
        sev_label.setStyleSheet(f"color: {TEXT_SECONDARY}; font-family: '{FONT_FAMILY_UI}'; font-size: 12px;")
        search_layout.addWidget(sev_label)

        self.severity_combo = QComboBox()
        self.severity_combo.addItems(["All", "Info", "Low", "Medium", "High", "Critical"])
        self.severity_combo.setMinimumWidth(100)
        self.severity_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {BG_INPUT};
                color: {TEXT_PRIMARY};
                border: 1px solid {BORDER_MEDIUM};
                border-radius: 6px;
                padding: 6px 10px;
                font-family: '{FONT_FAMILY_UI}';
                font-size: 12px;
            }}
            QComboBox:hover {{
                border-color: {NEON_CYAN};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 24px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {BG_WIDGET};
                color: {TEXT_PRIMARY};
                border: 1px solid {BORDER_MEDIUM};
                selection-background-color: {NEON_CYAN}30;
            }}
        """)
        search_layout.addWidget(self.severity_combo)

        layout.addWidget(search_frame)

        # =====================================================
        # MAIN CONTENT SPLITTER
        # =====================================================
        content_splitter = QSplitter(Qt.Horizontal)
        content_splitter.setHandleWidth(4)

        # LEFT: Entry list
        left_frame = QFrame()
        left_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {BG_WIDGET};
                border: 1px solid {BORDER_MEDIUM};
                border-radius: 8px;
            }}
        """)
        left_layout = QVBoxLayout(left_frame)
        left_layout.setContentsMargins(6, 6, 6, 6)
        left_layout.setSpacing(6)

        list_header = QLabel("ENTRIES")
        list_header.setStyleSheet(f"""
            color: {NEON_GREEN};
            font-family: '{FONT_FAMILY}', monospace;
            font-size: 11px;
            font-weight: bold;
            letter-spacing: 2px;
            padding: 4px 8px;
        """)
        left_layout.addWidget(list_header)

        self.entry_list = QListWidget()
        self.entry_list.setStyleSheet(f"""
            QListWidget {{
                background-color: {BG_DEEP_BLACK};
                color: {TEXT_PRIMARY};
                border: 1px solid {BORDER_MEDIUM};
                border-radius: 6px;
                padding: 4px;
                font-family: '{FONT_FAMILY_UI}';
                font-size: 12px;
                outline: none;
            }}
            QListWidget::item {{
                padding: 8px 10px;
                border-radius: 4px;
                margin: 1px 2px;
            }}
            QListWidget::item:hover {{
                background-color: {BG_HOVER};
            }}
            QListWidget::item:selected {{
                background-color: {NEON_CYAN}20;
                color: {NEON_CYAN};
            }}
        """)
        left_layout.addWidget(self.entry_list)

        # Results count
        self.results_label = QLabel("0 results")
        self.results_label.setStyleSheet(f"color: {TEXT_DIM}; font-size: 11px; padding: 2px 8px;")
        left_layout.addWidget(self.results_label)

        content_splitter.addWidget(left_frame)

        # RIGHT: Detail view
        right_frame = QFrame()
        right_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {BG_WIDGET};
                border: 1px solid {BORDER_MEDIUM};
                border-radius: 8px;
            }}
        """)
        right_layout = QVBoxLayout(right_frame)
        right_layout.setContentsMargins(12, 12, 12, 12)
        right_layout.setSpacing(10)

        # Entry title
        self.detail_title = QLabel("Select an entry from the list")
        self.detail_title.setStyleSheet(f"""
            color: {NEON_CYAN};
            font-family: '{FONT_FAMILY}', monospace;
            font-size: 18px;
            font-weight: bold;
            padding: 4px 0px;
        """)
        self.detail_title.setWordWrap(True)
        right_layout.addWidget(self.detail_title)

        # Severity + Category row
        meta_layout = QHBoxLayout()
        meta_layout.setSpacing(12)

        self.severity_badge = QLabel("")
        self.severity_badge.setStyleSheet(f"""
            color: {TEXT_PRIMARY};
            font-family: '{FONT_FAMILY}', monospace;
            font-size: 11px;
            font-weight: bold;
            padding: 3px 10px;
            border-radius: 4px;
            background-color: {BG_INPUT};
            border: 1px solid {BORDER_MEDIUM};
        """)
        meta_layout.addWidget(self.severity_badge)

        self.category_badge = QLabel("")
        self.category_badge.setStyleSheet(f"""
            color: {NEON_MAGENTA};
            font-family: '{FONT_FAMILY}', monospace;
            font-size: 11px;
            padding: 3px 10px;
            border-radius: 4px;
            background-color: {BG_INPUT};
            border: 1px solid {BORDER_MEDIUM};
        """)
        meta_layout.addWidget(self.category_badge)

        meta_layout.addStretch()
        right_layout.addLayout(meta_layout)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet(f"background-color: {BORDER_MEDIUM}; max-height: 1px;")
        right_layout.addWidget(sep)

        # LINE EXPLANATION (shown when a terminal line is clicked)
        self.explanation_frame = QFrame()
        self.explanation_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {NEON_GREEN}08;
                border: 1px solid {NEON_GREEN}40;
                border-radius: 8px;
                padding: 4px;
            }}
        """)
        explanation_layout = QVBoxLayout(self.explanation_frame)
        explanation_layout.setContentsMargins(12, 12, 12, 12)
        explanation_layout.setSpacing(8)

        explanation_header = QLabel("LINE EXPLANATION")
        explanation_header.setStyleSheet(f"""
            color: {NEON_GREEN};
            font-family: '{FONT_FAMILY}', monospace;
            font-size: 11px;
            font-weight: bold;
            letter-spacing: 2px;
        """)
        explanation_layout.addWidget(explanation_header)

        self.explanation_text = QTextEdit()
        self.explanation_text.setReadOnly(True)
        self.explanation_text.setMaximumHeight(120)
        self.explanation_text.setStyleSheet(f"""
            QTextEdit {{
                background-color: {BG_DEEP_BLACK};
                color: {NEON_GREEN};
                border: 1px solid {NEON_GREEN}30;
                border-radius: 6px;
                padding: 10px;
                font-family: '{FONT_FAMILY_UI}';
                font-size: 14px;
                font-weight: bold;
                line-height: 1.4;
            }}
        """)
        explanation_layout.addWidget(self.explanation_text)

        self.explanation_line_raw = QLabel("")
        self.explanation_line_raw.setWordWrap(True)
        self.explanation_line_raw.setStyleSheet(f"""
            QLabel {{
                color: {TEXT_DIM};
                font-family: '{FONT_FAMILY}', monospace;
                font-size: 10px;
                padding: 2px 0px;
            }}
        """)
        explanation_layout.addWidget(self.explanation_line_raw)

        self.explanation_frame.hide()
        right_layout.addWidget(self.explanation_frame)

        # Scrollable detail content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"""
            QScrollArea {{
                background-color: transparent;
                border: none;
            }}
        """)

        detail_container = QWidget()
        detail_container.setStyleSheet("background: transparent;")
        detail_layout = QVBoxLayout(detail_container)
        detail_layout.setContentsMargins(0, 0, 8, 0)
        detail_layout.setSpacing(12)

        # Description section
        detail_layout.addWidget(self._make_section_label("WHAT IS THIS"))
        self.detail_description = QTextEdit()
        self.detail_description.setReadOnly(True)
        self.detail_description.setMaximumHeight(80)
        self.detail_description.setStyleSheet(f"""
            QTextEdit {{
                background-color: {BG_DEEP_BLACK};
                color: {TEXT_PRIMARY};
                border: 1px solid {BORDER_MEDIUM};
                border-radius: 6px;
                padding: 8px;
                font-family: '{FONT_FAMILY_UI}';
                font-size: 13px;
            }}
        """)
        detail_layout.addWidget(self.detail_description)

        # Human explanation
        detail_layout.addWidget(self._make_section_label("IN PLAIN ENGLISH"))
        self.detail_human = QTextEdit()
        self.detail_human.setReadOnly(True)
        self.detail_human.setMaximumHeight(100)
        self.detail_human.setStyleSheet(f"""
            QTextEdit {{
                background-color: {BG_DEEP_BLACK};
                color: {NEON_GREEN};
                border: 1px solid {BORDER_MEDIUM};
                border-radius: 6px;
                padding: 8px;
                font-family: '{FONT_FAMILY_UI}';
                font-size: 13px;
            }}
        """)
        detail_layout.addWidget(self.detail_human)

        # What it means
        detail_layout.addWidget(self._make_section_label("WHAT IT MEANS FOR YOU"))
        self.detail_what = QTextEdit()
        self.detail_what.setReadOnly(True)
        self.detail_what.setMaximumHeight(100)
        self.detail_what.setStyleSheet(f"""
            QTextEdit {{
                background-color: {BG_DEEP_BLACK};
                color: {NEON_YELLOW};
                border: 1px solid {BORDER_MEDIUM};
                border-radius: 6px;
                padding: 8px;
                font-family: '{FONT_FAMILY_UI}';
                font-size: 13px;
            }}
        """)
        detail_layout.addWidget(self.detail_what)

        # Threat context
        detail_layout.addWidget(self._make_section_label("SECURITY CONTEXT"))
        self.detail_threat = QTextEdit()
        self.detail_threat.setReadOnly(True)
        self.detail_threat.setMaximumHeight(100)
        self.detail_threat.setStyleSheet(f"""
            QTextEdit {{
                background-color: {BG_DEEP_BLACK};
                color: {NEON_ORANGE};
                border: 1px solid {BORDER_MEDIUM};
                border-radius: 6px;
                padding: 8px;
                font-family: '{FONT_FAMILY_UI}';
                font-size: 13px;
            }}
        """)
        detail_layout.addWidget(self.detail_threat)

        # Example terminal line
        detail_layout.addWidget(self._make_section_label("EXAMPLE TERMINAL LINE"))
        self.detail_example = QLabel("")
        self.detail_example.setWordWrap(True)
        self.detail_example.setStyleSheet(f"""
            QLabel {{
                background-color: {BG_DEEP_BLACK};
                color: {TEXT_SECONDARY};
                border: 1px solid {BORDER_MEDIUM};
                border-radius: 6px;
                padding: 8px;
                font-family: '{FONT_FAMILY}', monospace;
                font-size: 11px;
            }}
        """)
        detail_layout.addWidget(self.detail_example)

        # Keywords
        detail_layout.addWidget(self._make_section_label("KEYWORDS"))
        self.detail_keywords = QLabel("")
        self.detail_keywords.setWordWrap(True)
        self.detail_keywords.setStyleSheet(f"""
            QLabel {{
                color: {NEON_MAGENTA};
                font-family: '{FONT_FAMILY}', monospace;
                font-size: 11px;
                padding: 4px 0px;
            }}
        """)
        detail_layout.addWidget(self.detail_keywords)

        detail_layout.addStretch()

        scroll.setWidget(detail_container)
        right_layout.addWidget(scroll)

        content_splitter.addWidget(right_frame)

        # Set proportions
        content_splitter.setSizes([320, 580])

        layout.addWidget(content_splitter, 1)

        # =====================================================
        # CONNECTIONS
        # =====================================================
        self.search_input.textChanged.connect(self._on_search_changed)
        self.category_combo.currentIndexChanged.connect(self._on_category_changed)
        self.severity_combo.currentIndexChanged.connect(self._on_severity_changed)
        self.entry_list.currentItemChanged.connect(self._on_entry_selected)

    def _make_section_label(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setStyleSheet(f"""
            color: {TEXT_DIM};
            font-family: '{FONT_FAMILY}', monospace;
            font-size: 10px;
            font-weight: bold;
            letter-spacing: 2px;
            padding: 2px 0px;
        """)
        return label

    def _populate_categories(self) -> None:
        """Fill the category dropdown."""
        self.category_combo.blockSignals(True)
        self.category_combo.clear()
        self.category_combo.addItem("All Categories", None)
        for cat in EntryCategory:
            count = len(self.kb.get_by_category(cat))
            self.category_combo.addItem(f"{cat.value} ({count})", cat)
        self.category_combo.blockSignals(False)

    def _populate_entries(self, entries: Optional[List[KBEntry]] = None) -> None:
        """Fill the entry list."""
        self.entry_list.blockSignals(True)
        self.entry_list.clear()

        if entries is None:
            entries = list(self.kb.entries.values())

        # Group by category
        by_cat = {}
        for entry in entries:
            cat = entry.category
            if cat not in by_cat:
                by_cat[cat] = []
            by_cat[cat].append(entry)

        for cat in EntryCategory:
            if cat not in by_cat:
                continue
            # Category header
            header_item = QListWidgetItem(f"── {cat.value.upper()} ──")
            header_item.setFlags(Qt.NoItemFlags)
            header_item.setForeground(QColor(TEXT_DIM))
            header_item.setFont(QFont(FONT_FAMILY_UI, 11, QFont.Bold))
            self.entry_list.addItem(header_item)

            for entry in sorted(by_cat[cat], key=lambda e: e.title):
                sev_icon = self._severity_icon(entry.severity)
                item = QListWidgetItem(f"  {sev_icon} {entry.title}")
                item.setData(Qt.UserRole, entry.id)
                self.entry_list.addItem(item)

        self.entry_list.blockSignals(False)
        self.results_label.setText(f"{len(entries)} entries")

    def _severity_icon(self, severity: Severity) -> str:
        icons = {
            Severity.INFO: " ",
            Severity.LOW: " ",
            Severity.MEDIUM: " ",
            Severity.HIGH: " ",
            Severity.CRITICAL: " ",
        }
        return icons.get(severity, " ")

    def _severity_color(self, severity: Severity) -> str:
        colors = {
            Severity.INFO: TEXT_SECONDARY,
            Severity.LOW: NEON_GREEN,
            Severity.MEDIUM: NEON_YELLOW,
            Severity.HIGH: NEON_ORANGE,
            Severity.CRITICAL: NEON_RED,
        }
        return colors.get(severity, TEXT_PRIMARY)

    def _filter_entries(self) -> List[KBEntry]:
        """Apply current filters and return matching entries."""
        query = self.search_input.text().lower().strip()
        cat = self.category_combo.currentData()
        sev_idx = self.severity_combo.currentIndex()

        sev_min = [Severity.INFO, Severity.LOW, Severity.MEDIUM, Severity.HIGH, Severity.CRITICAL]
        min_severity = sev_min[sev_idx] if sev_idx < len(sev_min) else Severity.INFO

        results = []
        for entry in self.kb.entries.values():
            # Category filter
            if cat is not None and entry.category != cat:
                continue

            # Severity filter
            if sev_min.index(entry.severity) < sev_min.index(min_severity):
                continue

            # Text search
            if query:
                searchable = (
                    entry.id.lower() + " " +
                    entry.title.lower() + " " +
                    entry.description.lower() + " " +
                    entry.human_explanation.lower() + " " +
                    entry.what_it_means.lower() + " " +
                    " ".join(entry.keywords).lower()
                )
                if query not in searchable:
                    continue

            results.append(entry)

        return results

    @Slot(str)
    def _on_search_changed(self, text: str) -> None:
        self._populate_entries(self._filter_entries())

    @Slot(int)
    def _on_category_changed(self, index: int) -> None:
        self._populate_entries(self._filter_entries())

    @Slot(int)
    def _on_severity_changed(self, index: int) -> None:
        self._populate_entries(self._filter_entries())

    @Slot(QListWidgetItem, QListWidgetItem)
    def _on_entry_selected(self, current: QListWidgetItem, previous: QListWidgetItem) -> None:
        if current is None:
            return
        entry_id = current.data(Qt.UserRole)
        if entry_id is None:
            return

        entry = self.kb.get_by_id(entry_id)
        if entry is None:
            return

        self.current_entry = entry
        self._show_detail(entry)
        self.entry_selected.emit(entry_id)

    def _show_detail(self, entry: KBEntry) -> None:
        """Display the full detail of an entry."""
        self.detail_title.setText(entry.title)

        # Severity badge
        sev_color = self._severity_color(entry.severity)
        self.severity_badge.setText(f"{self._severity_icon(entry.severity)} {entry.severity.value.upper()}")
        self.severity_badge.setStyleSheet(f"""
            color: {sev_color};
            font-family: '{FONT_FAMILY}', monospace;
            font-size: 11px;
            font-weight: bold;
            padding: 3px 10px;
            border-radius: 4px;
            background-color: {sev_color}15;
            border: 1px solid {sev_color}40;
        """)

        # Category badge
        self.category_badge.setText(entry.category.value)

        # Content
        self.detail_description.setPlainText(entry.description)
        self.detail_human.setPlainText(entry.human_explanation)
        self.detail_what.setPlainText(entry.what_it_means)

        if entry.threat_context:
            self.detail_threat.setPlainText(entry.threat_context)
            self.detail_threat.show()
        else:
            self.detail_threat.setPlainText("No specific security concerns for this entry.")
            self.detail_threat.hide()

        if entry.example_terminal_line:
            self.detail_example.setText(entry.example_terminal_line)
            self.detail_example.show()
        else:
            self.detail_example.hide()

        if entry.keywords:
            kw_text = " | ".join(entry.keywords[:15])
            self.detail_keywords.setText(kw_text)
        else:
            self.detail_keywords.setText("")

    def lookup_line(self, line: str) -> None:
        """Parse a terminal line, generate a human explanation, and show related KB entries."""
        # Generate the plain English explanation
        explanation = explain_line(line)

        # Show the explanation prominently in the detail view
        self.explanation_text.setPlainText(explanation)
        self.explanation_line_raw.setText(f"> {line.strip()[:200]}")
        self.explanation_frame.show()

        # Parse the line to find what event type it is
        parsed = parse_line(line)

        # Find related KB entries for additional context
        matches = self.kb.lookup_terminal_line(line)

        # Also try to match by operation name
        if parsed.operation:
            op_lower = parsed.operation.lower()
            for entry in self.kb.entries.values():
                if op_lower in [kw.lower() for kw in entry.keywords]:
                    if entry not in matches:
                        matches.append(entry)

        # Set the title to indicate this is a line explanation
        self.detail_title.setText(f'Explaining: "{line.strip()[:80]}..."')

        # Clear the badges
        self.severity_badge.setText(" EXPLAINED")
        self.severity_badge.setStyleSheet(f"""
            color: {NEON_GREEN};
            font-family: '{FONT_FAMILY}', monospace;
            font-size: 11px;
            font-weight: bold;
            padding: 3px 10px;
            border-radius: 4px;
            background-color: {NEON_GREEN}15;
            border: 1px solid {NEON_GREEN}40;
        """)
        self.category_badge.setText(parsed.event_type or "CONSOLE")

        # Show the explanation in the "IN PLAIN ENGLISH" section
        self.detail_human.setPlainText(explanation)

        # Show the raw parsed data in other sections
        if parsed.event_type:
            self.detail_description.setPlainText(
                f"Event Type: {parsed.event_type}\n"
                f"Process: {parsed.process_name} (PID: {parsed.pid})\n"
                f"Operation: {parsed.operation}"
            )
        else:
            self.detail_description.setPlainText("This is a console/log message from the sandbox itself.")

        # Show related KB entries as context
        if matches:
            context_parts = []
            for m in matches[:3]:
                context_parts.append(f"  - {m.title}: {m.human_explanation[:100]}")
            self.detail_what.setPlainText(
                "Related knowledge base entries:\n" + "\n".join(context_parts)
            )
        else:
            self.detail_what.setPlainText("No additional KB entries match this line.")

        # Clear the search to indicate this was a click-lookup, not a search
        self.search_input.clear()

        # Show related entries in the list
        if matches:
            self._populate_entries(matches[:20])
        else:
            self.entry_list.clear()
            self.results_label.setText("No related entries")

    def lookup_by_id(self, entry_id: str) -> None:
        """Look up an entry by its ID and display it."""
        entry = self.kb.get_by_id(entry_id)
        if entry:
            self.search_input.clear()
            self.category_combo.setCurrentIndex(0)
            self._populate_entries([entry])
            if self.entry_list.count() > 0:
                self.entry_list.setCurrentRow(0)
