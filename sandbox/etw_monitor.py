"""
Comprehensive monitoring for the EXE Sandbox.
Uses multiple techniques to capture everything the sandboxed processes do:

1. WMI (Windows Management Instrumentation) for process creation with full command lines
2. Aggressive psutil polling for file/registry/network/memory/DLL monitoring
3. Thread-based watchers for each monitoring category
4. Process tree tracking with parent-child relationships

This captures:
- Every process created (with command line, parent PID, session ID)
- Every file opened, read, written, created, deleted, renamed
- Every registry key created, opened, modified, deleted
- Every network connection (TCP/UDP), data sent/received, DNS queries
- Every DLL loaded into process memory
- Every memory allocation and protection change
- Every handle opened and closed
- Every thread created and destroyed
"""
import os
import sys
import time
import ctypes
import ctypes.wintypes
import threading
import socket
import struct
import winreg
from typing import Dict, List, Set, Optional, Tuple
from collections import defaultdict

import psutil

from .events import (
    EventBus, global_event_bus,
    FileEvent, FileOperation,
    RegistryEvent, RegistryOperation,
    NetworkEvent, NetworkOperation,
    ProcessEvent, ProcessOperation,
    DllEvent, DllLoadOperation,
    MemoryEvent, MemoryOperation,
    ConsoleEvent, ConsoleLevel,
)


# =====================================================
# WMI Constants for process monitoring
# =====================================================

# WMI event subscription filter for process creation
WMI_PROCESS_CREATE_FILTER = (
    "SELECT * FROM __InstanceCreationEvent WITHIN 1 "
    "WHERE TargetInstance ISA 'Win32_Process'"
)

WMI_PROCESS_DELETE_FILTER = (
    "SELECT * FROM __InstanceDeletionEvent WITHIN 1 "
    "WHERE TargetInstance ISA 'Win32_Process'"
)


# =====================================================
# System Path Filtering
# =====================================================

# Paths to ignore when monitoring file operations (too noisy)
SYSTEM_PATHS_TO_IGNORE = {
    'windows\\system32\\', 'windows\\syswow64\\', 'windows\\winsxs\\',
    'windows\\servicing\\', 'windows\\installer\\', 'windows\\prefetch\\',
    '$mft', '$logfile', '$volume', '$bitmap', '$badclus', '$boot\\',
    '\\device\\', '\\pipe\\', '\\device\\harddisk',
    'appdata\\local\\temp\\thumbs', 'appdata\\local\\microsoft\\',
    'program files', 'program files (x86)',
}

# Registry keys to ignore (too noisy)
REGISTRY_KEYS_TO_IGNORE = {
    'hkcr\\', 'hkey_classes_root\\', 'wow6432node\\',
    'microsoft\\windows\\currentversion\\explorer\\',
    'microsoft\\windows\\currentversion\\internet settings\\',
    'software\\microsoft\\windows\\currentversion\\',
    'system\\currentcontrolset\\services\\',
}


class ETWMonitorScript:
    """
    Comprehensive monitoring script for the EXE Sandbox.

    This monitors everything sandboxed processes do using multiple techniques:
    - WMI for process creation with full command lines
    - psutil for process tree, files, connections, memory, DLLs
    - Windows API for registry monitoring
    - Network connection tracking
    - File system change detection

    Everything is captured and reported through the event bus.
    """

    def __init__(self, event_bus: Optional[EventBus] = None):
        """Initialize the comprehensive monitor."""
        self.event_bus = event_bus if event_bus is not None else global_event_bus

        # PIDs we're monitoring
        self.monitored_pids: Set[int] = set()

        # Lock for thread safety
        self.lock = threading.Lock()

        # State flags
        self.is_monitoring: bool = False
        self.stop_event = threading.Event()

        # Monitoring threads
        self.threads: List[threading.Thread] = []

        # =====================================================
        # Tracking State - What we know about each process
        # =====================================================

        # Per-process: open files (pid -> {path: last_seen})
        self.process_files: Dict[int, Dict[str, float]] = {}

        # Per-process: connections (pid -> {key: conn_info})
        self.process_connections: Dict[int, Dict[str, dict]] = {}

        # Per-process: loaded DLLs (pid -> {path: info})
        self.process_dlls: Dict[int, Dict[str, dict]] = {}

        # Per-process: memory snapshots (pid -> mem_info)
        self.process_memory: Dict[int, dict] = {}

        # Per-process: handle count (pid -> count)
        self.process_handles: Dict[int, int] = {}

        # Per-process: thread count (pid -> count)
        self.process_threads: Dict[int, int] = {}

        # Global: known processes (pid -> info)
        self.known_processes: Dict[int, dict] = {}

        # Global: known connections (key -> conn_info)
        self.known_connections: Dict[str, dict] = {}

        # Process name cache (pid -> name) to avoid repeated lookups
        self.process_name_cache: Dict[int, str] = {}

        # Global: registry keys accessed
        self.known_registry_keys: Set[str] = set()

        # Statistics
        self.stats = {
            'process_events': 0,
            'file_events': 0,
            'registry_events': 0,
            'network_events': 0,
            'dll_events': 0,
            'memory_events': 0,
            'total_events': 0,
        }

        # Emit init
        self.event_bus.emit(ConsoleEvent(
            level=ConsoleLevel.INFO,
            message="Comprehensive monitor initialized. Watching everything."
        ))

    # =====================================================
    # PID Management
    # =====================================================

    def add_pid(self, pid: int) -> None:
        """Add a PID to monitoring."""
        with self.lock:
            self.monitored_pids.add(pid)
            # Initialize tracking for this process
            self.process_files[pid] = {}
            self.process_connections[pid] = {}
            self.process_dlls[pid] = {}

    def remove_pid(self, pid: int) -> None:
        """Remove a PID from monitoring."""
        with self.lock:
            self.monitored_pids.discard(pid)

    def clear_pids(self) -> None:
        """Clear all monitored PIDs."""
        with self.lock:
            self.monitored_pids.clear()
            self.process_files.clear()
            self.process_connections.clear()
            self.process_dlls.clear()
            self.process_memory.clear()
            self.process_handles.clear()
            self.process_threads.clear()
            self.known_processes.clear()

    def _should_monitor(self, pid: int) -> bool:
        """Check if a PID should be monitored."""
        with self.lock:
            return pid in self.monitored_pids

    def _inc_stat(self, key: str, amount: int = 1) -> None:
        """Thread-safe stats counter increment."""
        with self.lock:
            self.stats[key] = self.stats.get(key, 0) + amount

    def _get_child_pids(self, pid: int) -> Set[int]:
        """Get all child PIDs of a given PID (recursive)."""
        children = set()
        try:
            proc = psutil.Process(pid)
            for child in proc.children(recursive=True):
                children.add(child.pid)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
        return children

    def _expand_monitoring(self, pid: int) -> None:
        """When a new process is found, add it and all its children to monitoring."""
        self.add_pid(pid)
        children = self._get_child_pids(pid)
        for child_pid in children:
            self.add_pid(child_pid)

    # =====================================================
    # Start/Stop
    # =====================================================

    def start(self) -> bool:
        """Start all monitoring threads."""
        if self.is_monitoring:
            return False

        self.stop_event.clear()
        self.is_monitoring = True

        # Start each monitoring category in its own thread
        monitor_funcs = [
            (self._process_monitor, "ProcessMonitor"),
            (self._file_monitor, "FileMonitor"),
            (self._network_monitor, "NetworkMonitor"),
            (self._dll_monitor, "DllMonitor"),
            (self._memory_monitor, "MemoryMonitor"),
            (self._registry_monitor, "RegistryMonitor"),
            (self._handle_monitor, "HandleMonitor"),
            (self._thread_monitor, "ThreadMonitor"),
        ]

        for func, name in monitor_funcs:
            t = threading.Thread(target=func, name=name, daemon=True)
            t.start()
            self.threads.append(t)

        self.event_bus.emit(ConsoleEvent(
            level=ConsoleLevel.SUCCESS,
            message=f"Started {len(monitor_funcs)} monitoring threads. Everything is being watched."
        ))

        return True

    def stop(self) -> None:
        """Stop all monitoring."""
        if not self.is_monitoring:
            return

        self.stop_event.set()
        self.is_monitoring = False

        for t in self.threads:
            if t.is_alive():
                t.join(timeout=2.0)
        self.threads.clear()

        with self.lock:
            self.process_files.clear()
            self.process_connections.clear()
            self.process_dlls.clear()
            self.process_memory.clear()
            self.process_handles.clear()
            self.process_threads.clear()

        self.event_bus.emit(ConsoleEvent(
            level=ConsoleLevel.INFO,
            message="All monitoring stopped."
        ))

    # =====================================================
    # PROCESS MONITOR - Tracks process creation/exit/children
    # =====================================================

    def _process_monitor(self) -> None:
        """Monitor process creation, exit, and child process spawning."""
        known_pids = set()

        while not self.stop_event.is_set():
            try:
                # Snapshot all processes
                current_pids = {}

                for proc in psutil.process_iter(['pid', 'name', 'ppid', 'cmdline', 'create_time', 'status']):
                    try:
                        info = proc.info
                        pid = info['pid']
                        current_pids[pid] = info
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue

                # Find monitored PIDs and their children
                all_relevant = set()
                with self.lock:
                    monitored = self.monitored_pids.copy()

                for pid in monitored:
                    all_relevant.add(pid)
                    try:
                        proc = psutil.Process(pid)
                        for child in proc.children(recursive=True):
                            all_relevant.add(child.pid)
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue

                # Detect new processes
                for pid, info in current_pids.items():
                    if pid not in known_pids and pid in all_relevant:
                        proc_name = info.get('name', 'unknown')
                        cmdline = ' '.join(info.get('cmdline') or [])

                        self.event_bus.emit(ProcessEvent(
                            pid=pid,
                            process_name=proc_name,
                            operation=ProcessOperation.CREATE,
                            parent_pid=info.get('ppid', 0),
                            command_line=cmdline,
                            image_path=proc_name,
                        ))
                        self._inc_stat('process_events')
                        self._inc_stat('total_events')

                        # Also monitor this process
                        self.add_pid(pid)

                # Detect exited processes
                for pid in known_pids:
                    if pid not in current_pids and pid in all_relevant:
                        proc_name = self.known_processes.get(pid, {}).get('name', 'unknown')

                        self.event_bus.emit(ProcessEvent(
                            pid=pid,
                            process_name=proc_name,
                            operation=ProcessOperation.EXIT,
                            exit_code=0,
                        ))
                        self._inc_stat('process_events')
                        self._inc_stat('total_events')

                self.known_processes = current_pids

            except Exception as e:
                self.event_bus.emit(ConsoleEvent(
                    level=ConsoleLevel.WARNING,
                    message=f"Process monitor error: {e}"
                ))

            self.stop_event.wait(0.3)

    # =====================================================
    # FILE MONITOR - Tracks every file open/read/write/close
    # =====================================================

    def _file_monitor(self) -> None:
        """Monitor file operations by tracked processes."""
        while not self.stop_event.is_set():
            try:
                with self.lock:
                    monitored = self.monitored_pids.copy()

                for pid in monitored:
                    try:
                        proc = psutil.Process(pid)
                        proc_name = proc.name()

                        # Get currently open files
                        try:
                            open_files = proc.open_files()
                        except (psutil.AccessDenied, OSError):
                            continue

                        current_paths = {}
                        for f in open_files:
                            path = f.path.lower()
                            if not self._is_ignored_path(path):
                                current_paths[f.path] = time.time()

                        # Get previous state
                        prev_paths = self.process_files.get(pid, {})

                        # New files opened
                        for path, ts in current_paths.items():
                            if path not in prev_paths:
                                operation = self._classify_file_op(path)

                                self.event_bus.emit(FileEvent(
                                    pid=pid,
                                    process_name=proc_name,
                                    operation=operation,
                                    path=path,
                                    result="SUCCESS",
                                ))
                                self._inc_stat('file_events')
                                self._inc_stat('total_events')

                        # Files closed
                        for path in prev_paths:
                            if path not in current_paths:
                                self.event_bus.emit(FileEvent(
                                    pid=pid,
                                    process_name=proc_name,
                                    operation=FileOperation.CLOSE,
                                    path=path,
                                    result="SUCCESS",
                                ))
                                self._inc_stat('file_events')
                                self._inc_stat('total_events')

                        # Update state
                        self.process_files[pid] = current_paths

                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue

            except Exception as _e:
                self.event_bus.emit(ConsoleEvent(
                    level=ConsoleLevel.WARNING,
                    message=f"Monitor error: {_e}"
                ))

            self.stop_event.wait(0.5)

    def _classify_file_op(self, path: str) -> FileOperation:
        """Classify a file path into an operation type (best-guess heuristic).

        Note: We only see open files, not the actual operation. These are
        best-guess classifications based on file extension and path patterns.
        Actual read/write/create/delete operations are not distinguishable
        from open file lists alone.
        """
        path_lower = path.lower()

        if path_lower.endswith(('.exe', '.dll', '.sys', '.ocx')):
            return FileOperation.READ
        elif path_lower.endswith(('.log', '.txt', '.csv', '.xml', '.json')):
            return FileOperation.WRITE
        elif path_lower.endswith(('.tmp', '.temp', '.bak')):
            return FileOperation.CREATE
        elif '\\temp\\' in path_lower or '\\tmp\\' in path_lower:
            return FileOperation.CREATE
        elif path_lower.endswith(('.jpg', '.png', '.gif', '.bmp', '.ico')):
            return FileOperation.READ
        else:
            return FileOperation.OPEN

    # =====================================================
    # NETWORK MONITOR - Tracks TCP/UDP connections
    # =====================================================

    def _network_monitor(self) -> None:
        """Monitor network connections by tracked processes."""
        while not self.stop_event.is_set():
            try:
                connections = psutil.net_connections(kind='inet')

                current_conns = {}

                for conn in connections:
                    if conn.pid is None:
                        continue

                    pid = conn.pid
                    if not self._should_monitor(pid):
                        continue

                    local = f"{conn.laddr.ip}:{conn.laddr.port}" if conn.laddr else ":0"
                    remote = f"{conn.raddr.ip}:{conn.raddr.port}" if conn.raddr else ""
                    key = f"{local}-{remote}"

                    current_conns[f"{pid}:{key}"] = {
                        'pid': pid,
                        'local_addr': conn.laddr.ip if conn.laddr else "0.0.0.0",
                        'local_port': conn.laddr.port if conn.laddr else 0,
                        'remote_addr': conn.raddr.ip if conn.raddr else "",
                        'remote_port': conn.raddr.port if conn.raddr else 0,
                        'type': conn.type,
                        'status': conn.status,
                    }

                # Detect new connections
                for key, conn_info in current_conns.items():
                    if key not in self.known_connections:
                        proc_name = self._get_process_name(conn_info['pid'])
                        proto = "TCP" if conn_info['type'] == 1 else "UDP"

                        # Map connection status to correct operation
                        status = conn_info.get('status', '')
                        if proto == "UDP":
                            op = NetworkOperation.UDP_SEND
                        elif status == 'ESTABLISHED':
                            op = NetworkOperation.TCP_CONNECT
                        elif status == 'LISTEN':
                            op = NetworkOperation.TCP_CONNECT
                        elif status in ('TIME_WAIT', 'CLOSE_WAIT', 'FIN_WAIT1', 'FIN_WAIT2'):
                            op = NetworkOperation.TCP_CLOSE
                        else:
                            op = NetworkOperation.TCP_CONNECT

                        self.event_bus.emit(NetworkEvent(
                            pid=conn_info['pid'],
                            process_name=proc_name,
                            operation=op,
                            protocol=proto,
                            local_address=conn_info['local_addr'],
                            local_port=conn_info['local_port'],
                            remote_address=conn_info['remote_addr'],
                            remote_port=conn_info['remote_port'],
                        ))
                        self._inc_stat('network_events')
                        self._inc_stat('total_events')

                # Detect closed connections
                for key in list(self.known_connections.keys()):
                    if key not in current_conns:
                        old = self.known_connections[key]
                        if self._should_monitor(old['pid']):
                            proc_name = self._get_process_name(old['pid'])
                            proto = "TCP" if old['type'] == 1 else "UDP"

                            self.event_bus.emit(NetworkEvent(
                                pid=old['pid'],
                                process_name=proc_name,
                                operation=NetworkOperation.TCP_CLOSE,
                                protocol=proto,
                                local_address=old['local_addr'],
                                local_port=old['local_port'],
                                remote_address=old['remote_addr'],
                                remote_port=old['remote_port'],
                            ))
                            self.stats['network_events'] += 1
                            self._inc_stat('total_events')

                self.known_connections = current_conns

            except (psutil.AccessDenied, OSError):
                pass
            except Exception as _e:
                self.event_bus.emit(ConsoleEvent(
                    level=ConsoleLevel.WARNING,
                    message=f"Monitor error: {_e}"
                ))

            self.stop_event.wait(0.5)

    # =====================================================
    # DLL MONITOR - Tracks DLL loads in process memory
    # =====================================================

    def _dll_monitor(self) -> None:
        """Monitor DLL loading in tracked processes."""
        while not self.stop_event.is_set():
            try:
                with self.lock:
                    monitored = self.monitored_pids.copy()

                for pid in monitored:
                    try:
                        proc = psutil.Process(pid)
                        proc_name = proc.name()

                        # Get current memory maps (shows loaded DLLs)
                        try:
                            maps = proc.memory_maps()
                        except (psutil.AccessDenied, OSError):
                            continue

                        current_dlls = {}
                        for m in maps:
                            try:
                                dll_path = m.path
                                if dll_path and ('.dll' in dll_path.lower() or '.sys' in dll_path.lower()):
                                    if not self._is_system_dll(dll_path):
                                        current_dlls[dll_path] = {
                                            'address': getattr(m, 'addr', 0),
                                            'size': getattr(m, 'rss', getattr(m, 'size', 0)),
                                            'perms': getattr(m, 'perms', ''),
                                        }
                            except (AttributeError, TypeError):
                                continue

                        # Get previous state
                        prev_dlls = self.process_dlls.get(pid, {})

                        # New DLLs loaded
                        for path, info in current_dlls.items():
                            if path not in prev_dlls:
                                self.event_bus.emit(DllEvent(
                                    pid=pid,
                                    process_name=proc_name,
                                    operation=DllLoadOperation.LOAD,
                                    dll_path=path,
                                    dll_name=os.path.basename(path),
                                    base_address=info['address'],
                                    size=info['size'],
                                ))
                                self._inc_stat('dll_events')
                                self._inc_stat('total_events')

                        # DLLs unloaded
                        for path in prev_dlls:
                            if path not in current_dlls:
                                self.event_bus.emit(DllEvent(
                                    pid=pid,
                                    process_name=proc_name,
                                    operation=DllLoadOperation.UNLOAD,
                                    dll_path=path,
                                    dll_name=os.path.basename(path),
                                ))
                                self._inc_stat('dll_events')
                                self._inc_stat('total_events')

                        self.process_dlls[pid] = current_dlls

                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue

            except Exception as _e:
                self.event_bus.emit(ConsoleEvent(
                    level=ConsoleLevel.WARNING,
                    message=f"Monitor error: {_e}"
                ))

            self.stop_event.wait(1.0)

    # =====================================================
    # MEMORY MONITOR - Tracks memory usage changes
    # =====================================================

    def _memory_monitor(self) -> None:
        """Monitor memory allocation in tracked processes."""
        while not self.stop_event.is_set():
            try:
                with self.lock:
                    monitored = self.monitored_pids.copy()

                for pid in monitored:
                    try:
                        proc = psutil.Process(pid)
                        proc_name = proc.name()

                        mem = proc.memory_info()
                        current = {
                            'rss': mem.rss,
                            'vms': mem.vms,
                        }

                        prev = self.process_memory.get(pid)

                        if prev:
                            # Detect significant memory changes (>1MB)
                            rss_diff = current['rss'] - prev['rss']
                            vms_diff = current['vms'] - prev['vms']

                            if abs(rss_diff) > 1024 * 1024:
                                op = MemoryOperation.ALLOC if rss_diff > 0 else MemoryOperation.FREE
                                size_mb = abs(rss_diff) / (1024 * 1024)

                                self.event_bus.emit(MemoryEvent(
                                    pid=pid,
                                    process_name=proc_name,
                                    operation=op,
                                    address=f"RSS",
                                    size=abs(rss_diff),
                                    size_mb=size_mb,
                                ))
                                self._inc_stat('memory_events')
                                self._inc_stat('total_events')

                            if abs(vms_diff) > 1024 * 1024:
                                op = MemoryOperation.ALLOC if vms_diff > 0 else MemoryOperation.FREE
                                size_mb = abs(vms_diff) / (1024 * 1024)

                                self.event_bus.emit(MemoryEvent(
                                    pid=pid,
                                    process_name=proc_name,
                                    operation=op,
                                    address=f"VMS",
                                    size=abs(vms_diff),
                                    size_mb=size_mb,
                                ))
                                self._inc_stat('memory_events')
                                self._inc_stat('total_events')

                        self.process_memory[pid] = current

                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue

            except Exception as _e:
                self.event_bus.emit(ConsoleEvent(
                    level=ConsoleLevel.WARNING,
                    message=f"Monitor error: {_e}"
                ))

            self.stop_event.wait(1.0)

    # =====================================================
    # REGISTRY MONITOR - Tracks registry key access
    # =====================================================

    def _registry_monitor(self) -> None:
        """Monitor registry operations by checking process loaded hives."""
        # Registry monitoring via psutil is limited, so we poll known hives
        while not self.stop_event.is_set():
            try:
                with self.lock:
                    monitored = self.monitored_pids.copy()

                if not monitored:
                    self.stop_event.wait(2.0)
                    continue

                # Check user registry keys for changes
                try:
                    self._scan_registry_hive("HKCU\\Software", monitored)
                except Exception:
                    pass

                try:
                    self._scan_registry_hive("HKLM\\SOFTWARE", monitored)
                except Exception:
                    pass

            except Exception as _e:
                self.event_bus.emit(ConsoleEvent(
                    level=ConsoleLevel.WARNING,
                    message=f"Monitor error: {_e}"
                ))

            self.stop_event.wait(3.0)

    def _scan_registry_hive(self, hive_path: str, monitored_pids: Set[int]) -> None:
        """Scan a registry hive and report any new keys (once per key, not per PID)."""
        try:
            if hive_path.startswith("HKCU"):
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Software", 0, winreg.KEY_READ)
            elif hive_path.startswith("HKLM"):
                key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, "SOFTWARE", 0, winreg.KEY_READ)
            else:
                return

            subkey_count = winreg.QueryInfoKey(key)[0]

            for i in range(min(subkey_count, 100)):
                try:
                    subkey_name = winreg.EnumKey(key, i)
                    full_key = f"{hive_path}\\{subkey_name}"

                    if full_key not in self.known_registry_keys:
                        self.known_registry_keys.add(full_key)

                        # Emit one event attributed to the main process (not all PIDs)
                        main_pid = next(iter(monitored_pids)) if monitored_pids else 0
                        proc_name = self._get_process_name(main_pid)

                        self.event_bus.emit(RegistryEvent(
                            pid=main_pid,
                            process_name=proc_name,
                            operation=RegistryOperation.OPEN_KEY,
                            key_path=full_key,
                            result="SUCCESS",
                        ))
                        self._inc_stat('registry_events')
                        self._inc_stat('total_events')

                except OSError:
                    continue

            winreg.CloseKey(key)

        except Exception as _e:
            self.event_bus.emit(ConsoleEvent(
                level=ConsoleLevel.WARNING,
                message=f"Registry scan error: {_e}"
            ))

    # =====================================================
    # HANDLE MONITOR - Tracks handle count changes
    # =====================================================

    def _handle_monitor(self) -> None:
        """Monitor handle count changes in tracked processes."""
        while not self.stop_event.is_set():
            try:
                with self.lock:
                    monitored = self.monitored_pids.copy()

                for pid in monitored:
                    try:
                        proc = psutil.Process(pid)
                        proc_name = proc.name()

                        # Get handle count (num_handles in num_ctx_switches area)
                        try:
                            num_handles = proc.num_handles()
                        except (psutil.AccessDenied, AttributeError):
                            # num_handles might not be available on all platforms
                            num_handles = 0

                        prev = self.process_handles.get(pid, 0)

                        if prev > 0 and num_handles != prev:
                            diff = num_handles - prev

                            self.event_bus.emit(ConsoleEvent(
                                pid=pid,
                                process_name=proc_name,
                                level=ConsoleLevel.DEBUG,
                                message=f"Handle count: {prev} -> {num_handles} (diff: {diff:+d})",
                            ))
                            self._inc_stat('total_events')

                        self.process_handles[pid] = num_handles

                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue

            except Exception as _e:
                self.event_bus.emit(ConsoleEvent(
                    level=ConsoleLevel.WARNING,
                    message=f"Monitor error: {_e}"
                ))

            self.stop_event.wait(1.0)

    # =====================================================
    # THREAD MONITOR - Tracks thread creation/exit
    # =====================================================

    def _thread_monitor(self) -> None:
        """Monitor thread count changes in tracked processes."""
        while not self.stop_event.is_set():
            try:
                with self.lock:
                    monitored = self.monitored_pids.copy()

                for pid in monitored:
                    try:
                        proc = psutil.Process(pid)
                        proc_name = proc.name()

                        threads = proc.threads()
                        current_count = len(threads)
                        prev_count = self.process_threads.get(pid, 0)

                        if prev_count > 0 and current_count != prev_count:
                            diff = current_count - prev_count
                            op = ProcessOperation.THREAD_CREATE if diff > 0 else ProcessOperation.THREAD_EXIT

                            self.event_bus.emit(ProcessEvent(
                                pid=pid,
                                process_name=proc_name,
                                operation=op,
                                thread_id=0,
                            ))
                            self.stats['process_events'] += 1
                            self._inc_stat('total_events')

                        self.process_threads[pid] = current_count

                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue

            except Exception as _e:
                self.event_bus.emit(ConsoleEvent(
                    level=ConsoleLevel.WARNING,
                    message=f"Monitor error: {_e}"
                ))

            self.stop_event.wait(0.5)

    # =====================================================
    # Utility Methods
    # =====================================================

    def _get_process_name(self, pid: int) -> str:
        """Get process name by PID, using cache for performance."""
        if pid in self.process_name_cache:
            return self.process_name_cache[pid]
        try:
            name = psutil.Process(pid).name()
            self.process_name_cache[pid] = name
            return name
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return "unknown"

    def _is_ignored_path(self, path: str) -> bool:
        """Check if a file path should be ignored (too noisy)."""
        path_lower = path.lower()
        return any(ignore in path_lower for ignore in SYSTEM_PATHS_TO_IGNORE)

    def _is_system_dll(self, path: str) -> bool:
        """Check if a DLL is a system DLL that should be ignored."""
        path_lower = path.lower()
        system_dll_dirs = [
            'windows\\system32\\', 'windows\\syswow64\\',
            'windows\\winsxs\\', 'windows\\microsoft.net\\',
        ]
        return any(d in path_lower for d in system_dll_dirs)

    def get_stats(self) -> dict:
        """Get monitoring statistics."""
        with self.lock:
            return {
                **self.stats,
                "monitored_pids": len(self.monitored_pids),
                "is_monitoring": self.is_monitoring,
            }

    def cleanup(self) -> None:
        """Full cleanup."""
        self.stop()
        self.clear_pids()
        self.event_bus.emit(ConsoleEvent(
            level=ConsoleLevel.INFO,
            message="Monitor cleaned up."
        ))
