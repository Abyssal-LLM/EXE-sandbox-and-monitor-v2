"""
Event system for the EXE Sandbox.
This module defines all event types that can occur during sandboxed execution.
Each event carries metadata about what happened, when, and which process caused it.
"""
import time
import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, List, Optional


class EventType(Enum):
    """Enumeration of all possible event types the sandbox can capture."""
    FILE = "FILE"
    REGISTRY = "REGISTRY"
    NETWORK = "NETWORK"
    PROCESS = "PROCESS"
    DLL = "DLL"
    MEMORY = "MEMORY"
    CONSOLE = "CONSOLE"
    ERROR = "ERROR"
    UNKNOWN = "UNKNOWN"


class FileOperation(Enum):
    """Types of file operations that can be detected."""
    CREATE = "CREATE"
    OPEN = "OPEN"
    READ = "READ"
    WRITE = "WRITE"
    CLOSE = "CLOSE"
    DELETE = "DELETE"
    RENAME = "RENAME"
    DIRECTORY_CREATE = "DIR_CREATE"
    DIRECTORY_REMOVE = "DIR_REMOVE"
    QUERY_INFO = "QUERY_INFO"
    SET_INFO = "SET_INFO"
    UNKNOWN = "UNKNOWN"


class RegistryOperation(Enum):
    """Types of registry operations that can be detected."""
    CREATE_KEY = "CREATE_KEY"
    OPEN_KEY = "OPEN_KEY"
    DELETE_KEY = "DELETE_KEY"
    SET_VALUE = "SET_VALUE"
    DELETE_VALUE = "DELETE_VALUE"
    QUERY_VALUE = "QUERY_VALUE"
    ENUM_KEY = "ENUM_KEY"
    UNKNOWN = "UNKNOWN"


class NetworkOperation(Enum):
    """Types of network operations that can be detected."""
    TCP_CONNECT = "TCP_CONNECT"
    TCP_SEND = "TCP_SEND"
    TCP_RECEIVE = "TCP_RECEIVE"
    TCP_CLOSE = "TCP_CLOSE"
    UDP_SEND = "UDP_SEND"
    UDP_RECEIVE = "UDP_RECEIVE"
    DNS_QUERY = "DNS_QUERY"
    UNKNOWN = "UNKNOWN"


class ProcessOperation(Enum):
    """Types of process operations that can be detected."""
    CREATE = "CREATE"
    EXIT = "EXIT"
    IMAGE_LOAD = "IMAGE_LOAD"
    THREAD_CREATE = "THREAD_CREATE"
    THREAD_EXIT = "THREAD_EXIT"
    UNKNOWN = "UNKNOWN"


class ConsoleLevel(Enum):
    """Log levels for console output messages."""
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    DEBUG = "DEBUG"
    SUCCESS = "SUCCESS"


@dataclass
class SandboxEvent:
    """
    Base event class for all sandbox events.
    Every event carries a timestamp, event type, and optional process info.
    """
    timestamp: float = field(default_factory=time.time)
    event_type: EventType = EventType.UNKNOWN
    pid: int = 0
    process_name: str = ""

    def to_log_string(self) -> str:
        """Convert this event to a formatted log string for terminal display."""
        time_str = time.strftime("%H:%M:%S", time.localtime(self.timestamp))
        ms = int((self.timestamp % 1) * 1000)
        return f"[{time_str}.{ms:03d}]"

    def format_header(self) -> str:
        """Format the event header with type badge and process info."""
        type_badge = f"[{self.event_type.value}]"
        proc_info = f"{self.process_name}({self.pid})" if self.pid > 0 else "SYSTEM"
        return f"{self.to_log_string()} {type_badge:<12} {proc_info}"


@dataclass
class FileEvent(SandboxEvent):
    """Event representing a file system operation."""
    operation: FileOperation = FileOperation.UNKNOWN
    path: str = ""
    result: str = "SUCCESS"
    size: int = 0

    def __post_init__(self):
        self.event_type = EventType.FILE

    def to_log_string(self) -> str:
        base = super().to_log_string()
        return f"{base} [FILE] {self.process_name}({self.pid}) {self.operation.value}: {self.path} -> {self.result}"


@dataclass
class RegistryEvent(SandboxEvent):
    """Event representing a registry operation."""
    operation: RegistryOperation = RegistryOperation.UNKNOWN
    key_path: str = ""
    value_name: str = ""
    value_data: str = ""
    result: str = "SUCCESS"

    def __post_init__(self):
        self.event_type = EventType.REGISTRY

    def to_log_string(self) -> str:
        base = super().to_log_string()
        value_info = f" value={self.value_name}" if self.value_name else ""
        return f"{base} [REG] {self.process_name}({self.pid}) {self.operation.value}: {self.key_path}{value_info} -> {self.result}"


@dataclass
class NetworkEvent(SandboxEvent):
    """Event representing a network operation."""
    operation: NetworkOperation = NetworkOperation.UNKNOWN
    protocol: str = "TCP"
    local_address: str = ""
    local_port: int = 0
    remote_address: str = ""
    remote_port: int = 0
    bytes_sent: int = 0
    bytes_received: int = 0
    result: str = "SUCCESS"

    def __post_init__(self):
        self.event_type = EventType.NETWORK

    def to_log_string(self) -> str:
        base = super().to_log_string()
        if self.operation == NetworkOperation.DNS_QUERY:
            return f"{base} [NET] {self.process_name}({self.pid}) DNS_QUERY: {self.remote_address}"
        elif self.operation in (NetworkOperation.TCP_CONNECT,):
            return f"{base} [NET] {self.process_name}({self.pid}) {self.operation.value}: {self.local_address}:{self.local_port} -> {self.remote_address}:{self.remote_port}"
        elif self.operation in (NetworkOperation.TCP_SEND, NetworkOperation.UDP_SEND):
            return f"{base} [NET] {self.process_name}({self.pid}) {self.operation.value}: {self.bytes_sent} bytes -> {self.remote_address}:{self.remote_port}"
        elif self.operation in (NetworkOperation.TCP_RECEIVE, NetworkOperation.UDP_RECEIVE):
            return f"{base} [NET] {self.process_name}({self.pid}) {self.operation.value}: {self.bytes_received} bytes <- {self.remote_address}:{self.remote_port}"
        else:
            return f"{base} [NET] {self.process_name}({self.pid}) {self.operation.value}: {self.protocol} {self.remote_address}:{self.remote_port}"


@dataclass
class ProcessEvent(SandboxEvent):
    """Event representing a process/thread operation."""
    operation: ProcessOperation = ProcessOperation.UNKNOWN
    parent_pid: int = 0
    command_line: str = ""
    image_path: str = ""
    exit_code: int = 0
    thread_id: int = 0

    def __post_init__(self):
        self.event_type = EventType.PROCESS

    def to_log_string(self) -> str:
        base = super().to_log_string()
        if self.operation == ProcessOperation.CREATE:
            return f"{base} [PROC] PROCESS_CREATE: {self.process_name}({self.pid}) parent={self.parent_pid} cmd={self.command_line}"
        elif self.operation == ProcessOperation.EXIT:
            return f"{base} [PROC] PROCESS_EXIT: {self.process_name}({self.pid}) exit_code={self.exit_code}"
        elif self.operation == ProcessOperation.THREAD_CREATE:
            return f"{base} [PROC] THREAD_CREATE: {self.process_name}({self.pid}) thread={self.thread_id}"
        elif self.operation == ProcessOperation.THREAD_EXIT:
            return f"{base} [PROC] THREAD_EXIT: {self.process_name}({self.pid}) thread={self.thread_id}"
        elif self.operation == ProcessOperation.IMAGE_LOAD:
            return f"{base} [PROC] IMAGE_LOAD: {self.process_name}({self.pid}) -> {self.image_path}"
        else:
            return f"{base} [PROC] {self.operation.value}: {self.process_name}({self.pid})"


@dataclass
class ConsoleEvent(SandboxEvent):
    """Event representing a console/log message from the sandbox itself."""
    level: ConsoleLevel = ConsoleLevel.INFO
    message: str = ""

    def __post_init__(self):
        self.event_type = EventType.CONSOLE

    def to_log_string(self) -> str:
        base = super().to_log_string()
        level_names = {
            ConsoleLevel.INFO: "INFO",
            ConsoleLevel.WARNING: "WARN",
            ConsoleLevel.ERROR: "ERR ",
            ConsoleLevel.DEBUG: "DBG ",
            ConsoleLevel.SUCCESS: " OK ",
        }
        level_str = level_names.get(self.level, "INFO")
        return f"{base} [{level_str}] {self.message}"


class DllLoadOperation(Enum):
    """Types of DLL operations that can be detected."""
    LOAD = "LOAD"
    UNLOAD = "UNLOAD"
    UNKNOWN = "UNKNOWN"


@dataclass
class DllEvent(SandboxEvent):
    """Event representing a DLL/library load operation."""
    operation: DllLoadOperation = DllLoadOperation.UNKNOWN
    dll_path: str = ""
    dll_name: str = ""
    base_address: str = ""
    size: int = 0

    def __post_init__(self):
        self.event_type = EventType.DLL

    def to_log_string(self) -> str:
        base = super().to_log_string()
        return f"{base} [DLL] {self.process_name}({self.pid}) {self.operation.value}: {self.dll_name} -> {self.dll_path}"


class MemoryOperation(Enum):
    """Types of memory operations that can be detected."""
    ALLOC = "ALLOC"
    FREE = "FREE"
    READ = "READ"
    WRITE = "WRITE"
    PROTECT = "PROTECT"
    UNKNOWN = "UNKNOWN"


@dataclass
class MemoryEvent(SandboxEvent):
    """Event representing a memory operation."""
    operation: MemoryOperation = MemoryOperation.UNKNOWN
    address: str = ""
    size: int = 0
    size_mb: float = 0.0
    protection: str = ""
    result: str = "SUCCESS"

    def __post_init__(self):
        self.event_type = EventType.MEMORY

    def to_log_string(self) -> str:
        base = super().to_log_string()
        size_str = f"{self.size_mb:.1f}MB" if self.size_mb > 0 else f"{self.size}B"
        return f"{base} [MEM] {self.process_name}({self.pid}) {self.operation.value}: {self.address} size={size_str}"


class EventBus:
    """
    Thread-safe event bus that routes events to registered callbacks.
    This is the central nervous system of the sandbox - all events flow through here.
    """
    def __init__(self):
        self._lock = threading.Lock()
        self._callbacks: List[Callable[[SandboxEvent], None]] = []
        self._event_history: List[SandboxEvent] = []
        self._max_history: int = 10000

    def subscribe(self, callback: Callable[[SandboxEvent], None]) -> None:
        """Register a callback to receive events."""
        with self._lock:
            self._callbacks.append(callback)

    def unsubscribe(self, callback: Callable[[SandboxEvent], None]) -> None:
        """Unregister a callback from receiving events."""
        with self._lock:
            if callback in self._callbacks:
                self._callbacks.remove(callback)

    def emit(self, event: SandboxEvent) -> None:
        """
        Emit an event to all registered callbacks.
        This is thread-safe and can be called from any thread.
        """
        with self._lock:
            self._event_history.append(event)
            if len(self._event_history) > self._max_history:
                self._event_history = self._event_history[-self._max_history:]
            callbacks_copy = list(self._callbacks)

        for callback in callbacks_copy:
            try:
                callback(event)
            except Exception as e:
                try:
                    print(f"[EventBus] Error in callback: {e}")
                except OSError:
                    pass

    def get_history(self, event_type: Optional[EventType] = None, limit: int = 1000) -> List[SandboxEvent]:
        """Retrieve event history, optionally filtered by type."""
        with self._lock:
            if event_type is not None:
                filtered = [e for e in self._event_history if e.event_type == event_type]
                return filtered[-limit:]
            return list(self._event_history[-limit:])

    def clear_history(self) -> None:
        """Clear all event history."""
        with self._lock:
            self._event_history.clear()

    def get_stats(self) -> dict:
        """Get event statistics by type."""
        with self._lock:
            stats = {}
            for event_type in EventType:
                stats[event_type.value] = sum(1 for e in self._event_history if e.event_type == event_type)
            stats["TOTAL"] = len(self._event_history)
            return stats


# Global event bus instance - the single source of truth for all sandbox events
# Every component that needs to emit or listen to events uses this instance
global_event_bus = EventBus()
