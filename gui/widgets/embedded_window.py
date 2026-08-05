"""
Embedded Window widget for the EXE Sandbox.
Uses Windows API to reparent an external EXE's window into our Qt widget.
"""
import ctypes
import ctypes.wintypes
import time
import threading
from typing import Optional

from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel
from PySide6.QtCore import Qt, QTimer, Signal

from gui.theme import (
    NEON_CYAN, BG_DEEP_BLACK,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_DIM,
    BORDER_MEDIUM, FONT_FAMILY,
)

# Windows API
user32 = ctypes.windll.user32

SetParent = user32.SetParent
MoveWindow = user32.MoveWindow
ShowWindow = user32.ShowWindow
IsWindowVisible = user32.IsWindowVisible
IsIconic = user32.IsIconic
IsWindow = user32.IsWindow
GetWindowThreadProcessId = user32.GetWindowThreadProcessId
GetWindowLongW = user32.GetWindowLongW
SetWindowLongW = user32.SetWindowLongW
GetWindowTextW = user32.GetWindowTextW
GetWindowTextLengthW = user32.GetWindowTextLengthW
EnumWindows = user32.EnumWindows

GWL_STYLE = -16
WS_CHILD = 0x40000000
WS_VISIBLE = 0x10000000
WS_CAPTION = 0x00C00000
WS_THICKFRAME = 0x00040000
WS_MINIMIZEBOX = 0x00020000
WS_MAXIMIZEBOX = 0x00010000


WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)


class EmbeddedWindowWidget(QFrame):
    """
    Embeds an external EXE's window into this Qt widget using SetParent.
    """
    window_embedded = Signal(int)
    window_lost = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.embedded_hwnd: int = 0
        self.embedded_pid: int = 0
        self.is_embedded: bool = False
        self._container_hwnd: int = 0

        self.monitor_timer = QTimer(self)
        self.monitor_timer.timeout.connect(self._check_alive)
        self.monitor_timer.start(500)

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.placeholder = QLabel("No window embedded\nEnable 'EMBED WINDOW' toggle and start a GUI EXE")
        self.placeholder.setAlignment(Qt.AlignCenter)
        self.placeholder.setStyleSheet(f"""
            color: {TEXT_DIM};
            font-family: '{FONT_FAMILY}', monospace;
            font-size: 13px;
            background-color: {BG_DEEP_BLACK};
            border: 2px dashed {BORDER_MEDIUM};
            border-radius: 8px;
            padding: 20px;
        """)
        layout.addWidget(self.placeholder)

    def embed_window_by_pid(self, pid: int, timeout: float = 8.0) -> bool:
        """
        Find and embed the main window of a process.
        Polls for the window to appear within timeout.
        """
        if self.is_embedded:
            self.detach_window()

        self.embedded_pid = pid
        self._container_hwnd = int(self.winId())

        # Poll for the window
        start = time.time()
        while time.time() - start < timeout:
            hwnd = self._find_main_window(pid)
            if hwnd:
                return self._do_embed(hwnd)
            time.sleep(0.3)

        return False

    def _find_main_window(self, pid: int) -> Optional[int]:
        """Find the best visible top-level window for a PID."""
        best = [None]
        best_area = [0]

        # Callback to collect all visible windows for this PID
        def callback(hwnd, lParam):
            wpid = ctypes.c_ulong()
            GetWindowThreadProcessId(hwnd, ctypes.byref(wpid))
            if wpid.value != pid:
                return True  # continue

            if not IsWindowVisible(hwnd):
                return True

            if IsIconic(hwnd):
                return True

            # Get window rect to compute area
            rect = ctypes.wintypes.RECT()
            user32.GetWindowRect(hwnd, ctypes.byref(rect))
            area = (rect.right - rect.left) * (rect.bottom - rect.top)

            if area > best_area[0]:
                best_area[0] = area
                best[0] = hwnd

            return True  # continue

        EnumWindows(WNDENUMPROC(callback), 0)
        return best[0]

    def _do_embed(self, hwnd: int) -> bool:
        """Actually reparent and resize the window."""
        try:
            # Remove popup/caption styles, add child
            style = GetWindowLongW(hwnd, GWL_STYLE)
            style = style & ~(WS_CAPTION | WS_THICKFRAME | WS_MINIMIZEBOX | WS_MAXIMIZEBOX)
            style = style | WS_CHILD | WS_VISIBLE
            SetWindowLongW(hwnd, GWL_STYLE, style)

            # Reparent into our container
            SetParent(hwnd, self._container_hwnd)

            # Resize to fit
            self._resize_embedded()

            # Show it
            ShowWindow(hwnd, 9)  # SW_RESTORE

            self.embedded_hwnd = hwnd
            self.is_embedded = True
            self.placeholder.hide()

            self.window_embedded.emit(self.embedded_pid)
            return True

        except Exception as e:
            print(f"Embed failed: {e}")
            return False

    def detach_window(self):
        """Restore window as top-level."""
        if not self.is_embedded or not self.embedded_hwnd:
            return

        try:
            hwnd = self.embedded_hwnd

            # Restore styles
            style = GetWindowLongW(hwnd, GWL_STYLE)
            style = style & ~WS_CHILD
            style = style | WS_CAPTION | WS_THICKFRAME | WS_VISIBLE
            SetWindowLongW(hwnd, GWL_STYLE, style)

            # Unparent
            SetParent(hwnd, 0)

            # Show normally
            ShowWindow(hwnd, 1)  # SW_SHOWNORMAL

        except Exception:
            pass

        self.embedded_hwnd = 0
        self.embedded_pid = 0
        self.is_embedded = False
        self.placeholder.show()
        self.window_lost.emit()

    def _resize_embedded(self):
        """Resize embedded window to fill container."""
        if self.embedded_hwnd and self._container_hwnd:
            w = self.width()
            h = self.height()
            if w > 0 and h > 0:
                MoveWindow(self.embedded_hwnd, 0, 0, w, h, True)

    def _check_alive(self):
        """Periodically check if embedded window is still alive."""
        if self.is_embedded and self.embedded_hwnd:
            if not IsWindow(self.embedded_hwnd):
                self.embedded_hwnd = 0
                self.embedded_pid = 0
                self.is_embedded = False
                self.placeholder.show()
                self.window_lost.emit()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.is_embedded:
            self._resize_embedded()

    def showEvent(self, event):
        super().showEvent(event)
        if self.is_embedded and self.embedded_hwnd:
            ShowWindow(self.embedded_hwnd, 9)

    def hideEvent(self, event):
        super().hideEvent(event)
        if self.is_embedded and self.embedded_hwnd:
            ShowWindow(self.embedded_hwnd, 0)

    def closeEvent(self, event):
        self.detach_window()
        super().closeEvent(event)

    def cleanup(self):
        self.monitor_timer.stop()
        self.detach_window()
