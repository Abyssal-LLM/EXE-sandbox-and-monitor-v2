"""
Terminal theme for the EXE Sandbox GUI.
This module defines the complete QSS stylesheet that gives the application
its neon-accented, dark terminal aesthetic.

The color palette uses:
- Cyan (#00ffff) for primary elements
- Magenta (#ff00ff) for secondary accents
- Matrix green (#00ff41) for success states
- Deep blacks for backgrounds
"""


# =====================================================
# COLOR PALETTE
# These are the core colors used throughout the theme
# =====================================================

# Primary neon colors
NEON_CYAN = "#00ffff"
NEON_MAGENTA = "#ff00ff"
NEON_GREEN = "#00ff41"
NEON_YELLOW = "#ffff00"
NEON_RED = "#ff0040"
NEON_ORANGE = "#ff8800"

# Background colors (darkest to lightest)
BG_DEEP_BLACK = "#050508"
BG_DARK = "#0a0a12"
BG_PANEL = "#0f0f1a"
BG_WIDGET = "#141422"
BG_INPUT = "#1a1a2e"
BG_HOVER = "#1f1f35"
BG_SELECTED = "#252545"

# Text colors
TEXT_PRIMARY = "#c8c8d0"
TEXT_SECONDARY = "#888898"
TEXT_DIM = "#555568"
TEXT_BRIGHT = "#ffffff"

# Border colors
BORDER_DARK = "#1a1a30"
BORDER_MEDIUM = "#2a2a45"
BORDER_LIGHT = "#3a3a5a"
BORDER_GLOW = "#00ffff40"

# Status colors
SUCCESS = "#00ff41"
WARNING = "#ffff00"
ERROR = "#ff0040"
INFO = "#00ffff"

# Event type colors (for terminal output)
EVENT_FILE = "#00ffff"      # Cyan for file operations
EVENT_REGISTRY = "#ff00ff"  # Magenta for registry operations
EVENT_NETWORK = "#00ff41"   # Green for network operations
EVENT_PROCESS = "#ffff00"   # Yellow for process operations
EVENT_CONSOLE = "#888898"   # Gray for console messages
EVENT_ERROR = "#ff0040"     # Red for errors


# =====================================================
# FONTS
# =====================================================

FONT_FAMILY = "'Cascadia Code', 'Fira Code', 'JetBrains Mono', 'Consolas', monospace"
FONT_FAMILY_UI = "'Segoe UI', 'Inter', sans-serif"
FONT_SIZE_SM = "11px"
FONT_SIZE_MD = "13px"
FONT_SIZE_LG = "15px"
FONT_SIZE_XL = "18px"


# =====================================================
# MAIN STYLESHEET
# This is the complete QSS that defines the entire UI
# =====================================================

MAIN_STYLESHEET = f"""
/* =====================================================
 * GLOBAL STYLES
 * The foundation of the dark theme
 * ===================================================== */

QMainWindow {{
    background-color: {BG_DEEP_BLACK};
    color: {TEXT_PRIMARY};
    border: none;
}}

QWidget {{
    background-color: transparent;
    color: {TEXT_PRIMARY};
    font-family: {FONT_FAMILY_UI};
    font-size: {FONT_SIZE_MD};
}}

/* =====================================================
 * SCROLLBAR STYLES
 * Custom scrollbars with neon accents
 * ===================================================== */

QScrollBar:vertical {{
    background-color: {BG_DARK};
    width: 10px;
    margin: 0;
    border-radius: 5px;
}}

QScrollBar::handle:vertical {{
    background-color: {BORDER_MEDIUM};
    border-radius: 5px;
    min-height: 30px;
}}

QScrollBar::handle:vertical:hover {{
    background-color: {NEON_CYAN};
}}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {{
    height: 0;
    background: none;
}}

QScrollBar:horizontal {{
    background-color: {BG_DARK};
    height: 10px;
    margin: 0;
    border-radius: 5px;
}}

QScrollBar::handle:horizontal {{
    background-color: {BORDER_MEDIUM};
    border-radius: 5px;
    min-width: 30px;
}}

QScrollBar::handle:horizontal:hover {{
    background-color: {NEON_CYAN};
}}

QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal {{
    width: 0;
    background: none;
}}

/* =====================================================
 * BUTTON STYLES
 * Neon-bordered buttons with hover glow effects
 * ===================================================== */

QPushButton {{
    background-color: {BG_WIDGET};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER_MEDIUM};
    border-radius: 6px;
    padding: 8px 16px;
    font-family: {FONT_FAMILY_UI};
    font-size: {FONT_SIZE_MD};
    font-weight: 500;
    min-height: 20px;
}}

QPushButton:hover {{
    background-color: {BG_HOVER};
    border-color: {NEON_CYAN};
    color: {NEON_CYAN};
}}

QPushButton:pressed {{
    background-color: {BG_SELECTED};
    border-color: {NEON_CYAN};
}}

QPushButton:disabled {{
    background-color: {BG_DARK};
    color: {TEXT_DIM};
    border-color: {BORDER_DARK};
}}

/* Primary action button - START */
QPushButton#startButton {{
    background-color: {BG_WIDGET};
    color: {NEON_GREEN};
    border: 2px solid {NEON_GREEN};
    font-weight: bold;
    font-size: {FONT_SIZE_LG};
    padding: 10px 24px;
}}

QPushButton#startButton:hover {{
    background-color: {NEON_GREEN}20;
    border-color: {NEON_GREEN};
    color: {NEON_GREEN};
}}

QPushButton#startButton:pressed {{
    background-color: {NEON_GREEN}40;
}}

/* Danger button - STOP */
QPushButton#stopButton {{
    background-color: {BG_WIDGET};
    color: {NEON_RED};
    border: 2px solid {NEON_RED};
    font-weight: bold;
    font-size: {FONT_SIZE_LG};
    padding: 10px 24px;
}}

QPushButton#stopButton:hover {{
    background-color: {NEON_RED}20;
    border-color: {NEON_RED};
    color: {NEON_RED};
}}

QPushButton#stopButton:pressed {{
    background-color: {NEON_RED}40;
}}

/* =====================================================
 * INPUT STYLES
 * Dark input fields with neon focus states
 * ===================================================== */

QLineEdit {{
    background-color: {BG_INPUT};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER_MEDIUM};
    border-radius: 6px;
    padding: 8px 12px;
    font-family: {FONT_FAMILY};
    font-size: {FONT_SIZE_MD};
    selection-background-color: {NEON_CYAN}40;
}}

QLineEdit:focus {{
    border-color: {NEON_CYAN};
}}

QLineEdit:disabled {{
    background-color: {BG_DARK};
    color: {TEXT_DIM};
}}

QTextEdit, QPlainTextEdit {{
    background-color: {BG_INPUT};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER_MEDIUM};
    border-radius: 6px;
    padding: 8px;
    font-family: {FONT_FAMILY};
    font-size: {FONT_SIZE_SM};
    selection-background-color: {NEON_CYAN}40;
}}

QTextEdit:focus, QPlainTextEdit:focus {{
    border-color: {NEON_CYAN};
}}

/* =====================================================
 * LABEL STYLES
 * ===================================================== */

QLabel {{
    color: {TEXT_PRIMARY};
    background: transparent;
}}

QLabel#titleLabel {{
    color: {NEON_CYAN};
    font-size: {FONT_SIZE_XL};
    font-weight: bold;
    font-family: {FONT_FAMILY};
}}

QLabel#subtitleLabel {{
    color: {TEXT_SECONDARY};
    font-size: {FONT_SIZE_SM};
}}

QLabel#statLabel {{
    color: {TEXT_PRIMARY};
    font-family: {FONT_FAMILY};
    font-size: {FONT_SIZE_SM};
    padding: 4px 8px;
    background-color: {BG_WIDGET};
    border: 1px solid {BORDER_DARK};
    border-radius: 4px;
}}

QLabel#statValue {{
    color: {NEON_CYAN};
    font-family: {FONT_FAMILY};
    font-size: {FONT_SIZE_MD};
    font-weight: bold;
}}

QLabel#eventBadge {{
    color: {TEXT_BRIGHT};
    font-family: {FONT_FAMILY};
    font-size: {FONT_SIZE_SM};
    font-weight: bold;
    padding: 2px 6px;
    border-radius: 3px;
}}

/* =====================================================
 * PANEL STYLES
 * Group boxes and frame containers
 * ===================================================== */

QGroupBox {{
    background-color: {BG_PANEL};
    border: 1px solid {BORDER_DARK};
    border-radius: 8px;
    margin-top: 12px;
    padding: 16px 12px 12px 12px;
    font-size: {FONT_SIZE_MD};
    font-weight: bold;
    color: {TEXT_SECONDARY};
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 16px;
    padding: 0 8px;
    color: {NEON_CYAN};
}}

QFrame {{
    background-color: {BG_PANEL};
    border: 1px solid {BORDER_DARK};
    border-radius: 8px;
}}

QFrame#terminalFrame {{
    background-color: {BG_DEEP_BLACK};
    border: 2px solid {BORDER_MEDIUM};
    border-radius: 8px;
}}

QFrame#statsFrame {{
    background-color: {BG_PANEL};
    border: 1px solid {BORDER_MEDIUM};
    border-radius: 8px;
    padding: 8px;
}}

/* =====================================================
 * TREE VIEW STYLES
 * For the process tree
 * ===================================================== */

QTreeView {{
    background-color: {BG_DEEP_BLACK};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER_MEDIUM};
    border-radius: 6px;
    padding: 4px;
    font-family: {FONT_FAMILY};
    font-size: {FONT_SIZE_SM};
    outline: none;
}}

QTreeView::item {{
    padding: 6px 8px;
    border-radius: 4px;
    min-height: 24px;
}}

QTreeView::item:hover {{
    background-color: {BG_HOVER};
}}

QTreeView::item:selected {{
    background-color: {NEON_CYAN}20;
    color: {NEON_CYAN};
}}

QTreeView::branch {{
    background: transparent;
}}

QTreeView::branch:has-children:closed {{
    border-image: none;
    image: none;
}}

QTreeView::branch:has-children:open {{
    border-image: none;
    image: none;
}}

QHeaderView::section {{
    background-color: {BG_WIDGET};
    color: {TEXT_SECONDARY};
    border: none;
    border-bottom: 1px solid {BORDER_MEDIUM};
    padding: 8px;
    font-weight: bold;
    font-size: {FONT_SIZE_SM};
}}

/* =====================================================
 * TAB WIDGET STYLES
 * ===================================================== */

QTabWidget::pane {{
    background-color: {BG_PANEL};
    border: 1px solid {BORDER_MEDIUM};
    border-radius: 8px;
    margin-top: -1px;
}}

QTabBar::tab {{
    background-color: {BG_WIDGET};
    color: {TEXT_SECONDARY};
    border: 1px solid {BORDER_DARK};
    border-bottom: none;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    padding: 8px 16px;
    margin-right: 2px;
    font-size: {FONT_SIZE_SM};
}}

QTabBar::tab:hover {{
    background-color: {BG_HOVER};
    color: {TEXT_PRIMARY};
}}

QTabBar::tab:selected {{
    background-color: {BG_PANEL};
    color: {NEON_CYAN};
    border-color: {BORDER_MEDIUM};
    border-bottom-color: {BG_PANEL};
}}

/* =====================================================
 * COMBO BOX STYLES
 * ===================================================== */

QComboBox {{
    background-color: {BG_INPUT};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER_MEDIUM};
    border-radius: 6px;
    padding: 6px 12px;
    min-width: 100px;
}}

QComboBox:hover {{
    border-color: {NEON_CYAN};
}}

QComboBox::drop-down {{
    border: none;
    width: 24px;
}}

QComboBox::down-arrow {{
    image: none;
    border: none;
}}

QComboBox QAbstractItemView {{
    background-color: {BG_WIDGET};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER_MEDIUM};
    border-radius: 6px;
    selection-background-color: {NEON_CYAN}30;
    selection-color: {NEON_CYAN};
}}

/* =====================================================
 * SEPARATOR STYLES
 * ===================================================== */

QSplitter::handle {{
    background-color: {BORDER_DARK};
}}

QSplitter::handle:hover {{
    background-color: {NEON_CYAN};
}}

/* =====================================================
 * STATUS BAR STYLES
 * ===================================================== */

QStatusBar {{
    background-color: {BG_DARK};
    color: {TEXT_SECONDARY};
    border-top: 1px solid {BORDER_DARK};
    font-family: {FONT_FAMILY};
    font-size: {FONT_SIZE_SM};
}}

/* =====================================================
 * TOOLTIP STYLES
 * ===================================================== */

QToolTip {{
    background-color: {BG_WIDGET};
    color: {TEXT_PRIMARY};
    border: 1px solid {NEON_CYAN};
    border-radius: 4px;
    padding: 6px;
    font-family: {FONT_FAMILY};
    font-size: {FONT_SIZE_SM};
}}

/* =====================================================
 * MENU STYLES
 * ===================================================== */

QMenuBar {{
    background-color: {BG_DARK};
    color: {TEXT_PRIMARY};
    border-bottom: 1px solid {BORDER_DARK};
}}

QMenuBar::item:selected {{
    background-color: {BG_HOVER};
    color: {NEON_CYAN};
}}

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

QMenu::separator {{
    height: 1px;
    background-color: {BORDER_DARK};
    margin: 4px 8px;
}}

/* =====================================================
 * PROGRESS BAR STYLES
 * ===================================================== */

QProgressBar {{
    background-color: {BG_INPUT};
    border: 1px solid {BORDER_DARK};
    border-radius: 4px;
    text-align: center;
    color: {TEXT_PRIMARY};
    font-family: {FONT_FAMILY};
    font-size: {FONT_SIZE_SM};
}}

QProgressBar::chunk {{
    background-color: {NEON_CYAN};
    border-radius: 3px;
}}

/* =====================================================
 * DROP ZONE STYLES
 * For the EXE loader drag-drop area
 * ===================================================== */

QFrame#dropZone {{
    background-color: {BG_DEEP_BLACK};
    border: 2px dashed {BORDER_MEDIUM};
    border-radius: 12px;
    min-height: 80px;
}}

QFrame#dropZone:hover {{
    border-color: {NEON_CYAN};
    background-color: {NEON_CYAN}08;
}}

QFrame#dropZoneActive {{
    background-color: {NEON_CYAN}10;
    border: 2px dashed {NEON_CYAN};
}}
"""


def get_stylesheet() -> str:
    """
    Get the complete terminal stylesheet.

    Returns:
        The QSS stylesheet string.
    """
    return MAIN_STYLESHEET


def get_event_color(event_type: str) -> str:
    """
    Get the color associated with an event type.

    Parameters:
        event_type: The event type string (FILE, REGISTRY, NETWORK, etc.)

    Returns:
        The hex color string for that event type.
    """
    color_map = {
        "FILE": EVENT_FILE,
        "REGISTRY": EVENT_REGISTRY,
        "NETWORK": EVENT_NETWORK,
        "PROCESS": EVENT_PROCESS,
        "CONSOLE": EVENT_CONSOLE,
        "ERROR": EVENT_ERROR,
    }
    return color_map.get(event_type, TEXT_PRIMARY)
