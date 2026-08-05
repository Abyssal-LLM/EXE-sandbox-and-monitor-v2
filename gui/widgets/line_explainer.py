"""
Parses terminal log lines and generates human-readable explanations.
This is the brain that turns raw log output into plain English.
"""
import re
from dataclasses import dataclass, field
from typing import Optional, Dict, List


@dataclass
class ParsedLine:
    """Structured data extracted from a terminal log line."""
    raw: str = ""
    timestamp: str = ""
    event_type: str = ""
    process_name: str = ""
    pid: str = ""
    operation: str = ""
    detail_key: str = ""
    detail_value: str = ""
    result: str = ""
    extra: Dict[str, str] = field(default_factory=dict)


# Regex patterns for each event type
PATTERNS = {
    "FILE": re.compile(
        r'\[(\d{2}:\d{2}:\d{2}\.\d{3})\]\s*\[FILE\]\s*'
        r'(\S+?)\((\d+)\)\s+'
        r'(\w+):\s*(.+?)\s*->\s*(\S+)'
    ),
    "REG": re.compile(
        r'\[(\d{2}:\d{2}:\d{2}\.\d{3})\]\s*\[REG\]\s*'
        r'(\S+?)\((\d+)\)\s+'
        r'(\w+):\s*(\S+?)(?:\s+value=(\S+))?\s*->\s*(\S+)'
    ),
    "NET": re.compile(
        r'\[(\d{2}:\d{2}:\d{2}\.\d{3})\]\s*\[NET\]\s*'
        r'(\S+?)\((\d+)\)\s+'
        r'(\w+):\s*(.+)'
    ),
    "PROC": re.compile(
        r'\[(\d{2}:\d{2}:\d{2}\.\d{3})\]\s*\[PROC\]\s*'
        r'(\w+):\s*'
        r'(\S+?)\((\d+)\)'
        r'(.*)$'
    ),
    "DLL": re.compile(
        r'\[(\d{2}:\d{2}:\d{2}\.\d{3})\]\s*\[DLL\]\s*'
        r'(\S+?)\((\d+)\)\s+'
        r'(\w+):\s*(\S+)\s*->\s*(.+)'
    ),
    "MEM": re.compile(
        r'\[(\d{2}:\d{2}:\d{2}\.\d{3})\]\s*\[MEM\]\s*'
        r'(\S+?)\((\d+)\)\s+'
        r'(\w+):\s*(\S+)\s+size=(\S+)'
    ),
}


def parse_line(line: str) -> ParsedLine:
    """Parse a terminal log line into structured data."""
    result = ParsedLine(raw=line)

    for event_type, pattern in PATTERNS.items():
        m = pattern.search(line)
        if not m:
            continue

        result.event_type = event_type
        result.timestamp = m.group(1)

        if event_type == "FILE":
            result.process_name = m.group(2)
            result.pid = m.group(3)
            result.operation = m.group(4)
            result.detail_key = m.group(5).strip()
            result.result = m.group(6)

        elif event_type == "REG":
            result.process_name = m.group(2)
            result.pid = m.group(3)
            result.operation = m.group(4)
            result.detail_key = m.group(5)
            if m.group(6):
                result.extra["value_name"] = m.group(6)
            result.result = m.group(7)

        elif event_type == "NET":
            result.process_name = m.group(2)
            result.pid = m.group(3)
            result.operation = m.group(4)
            raw_detail = m.group(5).strip()
            _parse_net_detail(result, raw_detail)

        elif event_type == "PROC":
            result.operation = m.group(2)
            result.process_name = m.group(3)
            result.pid = m.group(4)
            rest = m.group(5) or ""
            # Extract key=value pairs from the rest
            parent_m = re.search(r'parent=(\d+)', rest)
            if parent_m:
                result.extra["parent_pid"] = parent_m.group(1)
            cmd_m = re.search(r'cmd=(.*)', rest)
            if cmd_m:
                result.extra["cmdline"] = cmd_m.group(1).strip()
            exit_m = re.search(r'exit_code=(\d+)', rest)
            if exit_m:
                result.extra["exit_code"] = exit_m.group(1)
            thread_m = re.search(r'thread=(\d+)', rest)
            if thread_m:
                result.extra["thread_id"] = thread_m.group(1)

        elif event_type == "DLL":
            result.process_name = m.group(2)
            result.pid = m.group(3)
            result.operation = m.group(4)
            result.detail_key = m.group(5)
            result.detail_value = m.group(6).strip()

        elif event_type == "MEM":
            result.process_name = m.group(2)
            result.pid = m.group(3)
            result.operation = m.group(4)
            result.detail_key = m.group(5)
            result.extra["size"] = m.group(6)

    return result


def _parse_net_detail(result: ParsedLine, raw: str) -> None:
    """Parse the network detail portion of a NET line."""
    # DNS_QUERY: domain
    if result.operation == "DNS_QUERY":
        result.detail_key = raw
        return

    # TCP_CONNECT / TCP_CLOSE: local -> remote  OR  local:port -> remote:port
    if " -> " in raw:
        parts = raw.split(" -> ", 1)
        result.detail_key = parts[0].strip()
        result.detail_value = parts[1].strip()
    else:
        result.detail_key = raw


def explain_line(line: str) -> str:
    """Parse a terminal line and return a human-readable explanation."""
    parsed = parse_line(line)

    if not parsed.event_type:
        return _explain_console_or_unknown(line)

    explainer = {
        "FILE": _explain_file,
        "REG": _explain_reg,
        "NET": _explain_net,
        "PROC": _explain_proc,
        "DLL": _explain_dll,
        "MEM": _explain_mem,
    }.get(parsed.event_type)

    if explainer:
        return explainer(parsed)
    return _explain_console_or_unknown(line)


# =====================================================
# FILE EXPLANATIONS
# =====================================================

def _explain_file(p: ParsedLine) -> str:
    proc = p.process_name or "the program"
    op = p.operation.upper()
    path = p.detail_key or "a file"
    fname = _filename(path)

    op_text = {
        "CREATE": f'created a new file called "{fname}"',
        "OPEN": f'opened the file "{fname}"',
        "READ": f'read data from "{fname}"',
        "WRITE": f'wrote data to "{fname}"',
        "CLOSE": f'closed the file "{fname}"',
        "DELETE": f'deleted the file "{fname}"',
        "RENAME": f'renamed the file "{fname}"',
    }.get(op, f'performed {op} on "{fname}"')

    where = _describe_location(path)
    result = f'The program "{proc}" {op_text}'
    if where:
        result += f" {where}"
    result += "."
    return result


# =====================================================
# REGISTRY EXPLANATIONS
# =====================================================

def _explain_reg(p: ParsedLine) -> str:
    proc = p.process_name or "the program"
    op = p.operation.upper()
    key = p.detail_key or "a registry key"
    val = p.extra.get("value_name", "")
    friendly_key = _friendly_registry_key(key)

    op_text = {
        "CREATE_KEY": f'created a new registry key "{friendly_key}"',
        "OPEN_KEY": f'opened the registry key "{friendly_key}"',
        "DELETE_KEY": f'deleted the registry key "{friendly_key}"',
        "SET_VALUE": f'set a value in "{friendly_key}"',
        "DELETE_VALUE": f'removed a value from "{friendly_key}"',
        "QUERY_VALUE": f'read a value from "{friendly_key}"',
        "ENUM_KEY": f'browsed subkeys inside "{friendly_key}"',
    }.get(op, f'performed {op} on "{friendly_key}"')

    if val:
        op_text += f' (value: "{val}")'

    result = f'The program "{proc}" {op_text}'
    context = _registry_context(key)
    if context:
        result += f". {context}"
    result += "."
    return result


# =====================================================
# NETWORK EXPLANATIONS
# =====================================================

def _explain_net(p: ParsedLine) -> str:
    proc = p.process_name or "the program"
    op = p.operation.upper()

    if op == "DNS_QUERY":
        domain = p.detail_key or "a domain"
        return (
            f'The program "{proc}" looked up the internet address '
            f'"{domain}" to find its server.'
        )

    if op == "TCP_CONNECT":
        remote = p.detail_value or "a remote server"
        remote_clean = remote.rstrip(":0").rstrip(":")
        return (
            f'The program "{proc}" opened a network connection '
            f'to {remote_clean}.'
        )

    if op == "TCP_CLOSE":
        remote = p.detail_value or "a remote server"
        remote_clean = remote.rstrip(":0").rstrip(":")
        return (
            f'The program "{proc}" closed its connection to {remote_clean}.'
        )

    if "SEND" in op:
        remote = p.detail_value or "a remote server"
        remote_clean = remote.rstrip(":0").rstrip(":")
        return (
            f'The program "{proc}" sent data over the network '
            f'to {remote_clean}.'
        )

    if "RECEIVE" in op:
        remote = p.detail_value or "a remote server"
        remote_clean = remote.rstrip(":0").rstrip(":")
        return (
            f'The program "{proc}" received data from {remote_clean}.'
        )

    return f'The program "{proc}" performed a network operation ({op}).'


# =====================================================
# PROCESS EXPLANATIONS
# =====================================================

def _explain_proc(p: ParsedLine) -> str:
    proc = p.process_name or "the program"
    op = p.operation.upper()

    if op == "CREATE" or op == "PROCESS_CREATE":
        child = proc
        cmdline = p.extra.get("cmdline", "")
        parent = p.extra.get("parent_pid", "")
        parts = [f'A new process "{child}" was started']
        if cmdline:
            parts.append(f'running "{cmdline}"')
        if parent:
            parts.append(f'(by parent process {parent})')
        return " ".join(parts) + "."

    if op == "EXIT" or op == "PROCESS_EXIT":
        code = p.extra.get("exit_code", "?")
        return (
            f'The program "{proc}" finished running and exited '
            f'(exit code {code}).'
        )

    if op == "THREAD_CREATE":
        tid = p.extra.get("thread_id", "?")
        return (
            f'The program "{proc}" created a new thread of execution '
            f'(thread {tid}).'
        )

    if op == "THREAD_EXIT":
        tid = p.extra.get("thread_id", "?")
        return (
            f'The program "{proc}" terminated a thread (thread {tid}).'
        )

    return f'The program "{proc}" performed a process operation ({op}).'


# =====================================================
# DLL EXPLANATIONS
# =====================================================

def _explain_dll(p: ParsedLine) -> str:
    proc = p.process_name or "the program"
    op = p.operation.upper()
    dll_name = p.detail_key or "a DLL"
    dll_path = p.detail_value or ""

    friendly_dll = _friendly_dll_name(dll_name)
    where = _describe_dll_location(dll_path)

    if op == "LOAD":
        result = f'The program "{proc}" loaded the library "{dll_name}"'
        if friendly_dll:
            result += f" ({friendly_dll})"
        if where:
            result += f" {where}"
        result += "."
        return result

    if op == "UNLOAD":
        return (
            f'The program "{proc}" unloaded the library "{dll_name}" '
            f'from memory.'
        )

    return f'The program "{proc}" performed a DLL operation ({op}) on "{dll_name}".'


# =====================================================
# MEMORY EXPLANATIONS
# =====================================================

def _explain_mem(p: ParsedLine) -> str:
    proc = p.process_name or "the program"
    op = p.operation.upper()
    addr = p.detail_key or "memory"
    size = p.extra.get("size", "")

    op_text = {
        "ALLOC": "allocated",
        "FREE": "released",
        "READ": "read from",
        "WRITE": "wrote to",
        "PROTECT": "changed the protection on",
    }.get(op, f"performed {op} on")

    result = f'The program "{proc}" {op_text} a block of memory'
    if addr and addr not in ("RSS", "VMS", "HANDLES"):
        result += f" at address {addr}"
    if size:
        result += f" (size: {size})"
    result += "."
    return result


# =====================================================
# CONSOLE / UNKNOWN
# =====================================================

def _explain_console_or_unknown(line: str) -> str:
    """Handle console messages and unrecognized lines."""
    # Check for console patterns like [INFO], [WARN], [ERR], [OK]
    m = re.search(r'\[(INFO|WARN|ERR|OK|DBG)\]\s*(.*)', line)
    if m:
        level = m.group(1)
        msg = m.group(2)
        level_desc = {
            "INFO": "informational message",
            "WARN": "warning",
            "ERR": "error message",
            "OK": "success message",
            "DBG": "debug message",
        }.get(level, "message")
        return f'The sandbox emitted a {level_desc}: "{msg}"'

    return f'This line contains: "{line.strip()[:120]}"'


# =====================================================
# HELPER FUNCTIONS
# =====================================================

def _filename(path: str) -> str:
    """Extract filename from a full path."""
    if not path:
        return "unknown file"
    path = path.replace("\\", "/")
    parts = path.rsplit("/", 1)
    return parts[-1] if len(parts) > 1 else path


def _describe_location(path: str) -> str:
    """Describe where a file is located in human terms."""
    p = path.lower()
    if "\\temp\\" in p or "\\tmp\\" in p or "_MEI" in p:
        return "in a temporary folder"
    if "appdata\\local" in p:
        return "in the local app data folder"
    if "appdata\\roaming" in p:
        return "in the roaming app data folder"
    if "appdata" in p:
        return "in the app data folder"
    if "desktop" in p:
        return "on the desktop"
    if "downloads" in p:
        return "in the downloads folder"
    if "documents" in p:
        return "in the documents folder"
    if "windows\\system32" in p:
        return "in the Windows system directory"
    if "windows" in p:
        return "in the Windows directory"
    if "program files" in p:
        return "in the program files directory"
    return ""


def _friendly_registry_key(key: str) -> str:
    """Make a registry key path more readable."""
    replacements = {
        "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run": "User Startup Programs (Run key)",
        "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\RunOnce": "User One-Time Startup (RunOnce key)",
        "HKLM\\Software\\Microsoft\\Windows\\CurrentVersion\\Run": "Machine-Wide Startup Programs",
        "HKLM\\System\\CurrentControlSet\\Control\\Lsa": "Windows Security (LSA) settings",
        "HKLM\\System\\CurrentControlSet\\Services": "Windows Services configuration",
    }
    for pattern, friendly in replacements.items():
        if key.lower().startswith(pattern.lower()):
            return friendly
    return key


def _registry_context(key: str) -> str:
    """Provide security context for known registry keys."""
    k = key.lower()
    if "\\currentversion\\run" in k:
        return "WARNING: This key makes programs auto-start at login. Verify the entry is legitimate."
    if "\\lsa" in k:
        return "SECURITY: This controls Windows authentication. Changes here can weaken system security."
    if "\\services" in k:
        return "This defines a Windows service. Services run with high privileges."
    if "\\defender" in k:
        return "SECURITY: This controls Windows Defender. Modifications may disable antivirus protection."
    if "\\firewall" in k:
        return "SECURITY: This controls the Windows Firewall. Changes may open network access."
    return ""


def _friendly_dll_name(dll: str) -> str:
    """Explain what a DLL is for."""
    dll_lower = dll.lower()
    descriptions = {
        "kernel32.dll": "core Windows functions (memory, processes, files)",
        "ntdll.dll": "low-level Windows kernel interface",
        "user32.dll": "windows, menus, and user interface",
        "gdi32.dll": "graphics and screen drawing",
        "ws2_32.dll": "network/internet connections",
        "advapi32.dll": "registry, security, and services",
        "shell32.dll": "file operations and Windows shell",
        "wininet.dll": "internet/HTTP requests",
        "crypt32.dll": "encryption and certificates",
        "ole32.dll": "COM inter-process communication",
        "urlmon.dll": "URL handling and internet security",
        "msvcr": "C/C++ runtime (standard programming functions)",
        "pdh.dll": "performance monitoring (CPU, memory stats)",
        "winhttp.dll": "HTTP client for server communication",
    }
    for pattern, desc in descriptions.items():
        if pattern in dll_lower:
            return desc
    return ""


def _describe_dll_location(path: str) -> str:
    """Describe where a DLL was loaded from."""
    p = path.lower()
    if "\\temp\\" in p or "_mei" in p:
        return "from a temporary folder (created by the app's installer)"
    if "windows\\system32" in p:
        return "from the Windows system directory"
    if "windows\\syswow64" in p:
        return "from the Windows 32-bit compatibility directory"
    if "appdata" in p:
        return "from the app data folder"
    if "program files" in p:
        return "from the program files directory"
    if "downloads" in p:
        return "from the downloads folder"
    return ""
