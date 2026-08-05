"""
Comprehensive knowledge base for the EXE Sandbox.
Contains hundreds of entries explaining every event type, registry key,
file path, network operation, DLL, memory operation, and process action
in plain human-readable language.

This is the "brain" that makes the terminal output understandable.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum


class EntryCategory(Enum):
    """Categories for knowledge base entries."""
    EVENT_TYPE = "Event Types"
    FILE_OPERATION = "File Operations"
    FILE_PATH = "File Paths"
    REGISTRY_OPERATION = "Registry Operations"
    REGISTRY_KEY = "Registry Keys"
    NETWORK_OPERATION = "Network Operations"
    NETWORK_PROTOCOL = "Network Protocols"
    NETWORK_PORT = "Network Ports"
    PROCESS_OPERATION = "Process Operations"
    DLL_OPERATION = "DLL Operations"
    DLL_NAME = "DLL Names"
    MEMORY_OPERATION = "Memory Operations"
    SYSTEM_CONCEPT = "System Concepts"
    THREAT_INDICATOR = "Threat Indicators"
    GENERAL = "General"


class Severity(Enum):
    """Severity/relevance level of an entry."""
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class KBEntry:
    """A single knowledge base entry."""
    id: str
    title: str
    category: EntryCategory
    description: str
    human_explanation: str
    what_it_means: str
    when_you_see_it: str
    severity: Severity = Severity.INFO
    keywords: List[str] = field(default_factory=list)
    related: List[str] = field(default_factory=list)
    example_terminal_line: str = ""
    threat_context: str = ""


class KnowledgeBase:
    """
    The massive reference database. Contains entries for everything
    the sandbox can output, explained in human language.
    """

    def __init__(self):
        self.entries: Dict[str, KBEntry] = {}
        self._build_database()

    def _add(self, entry: KBEntry) -> None:
        self.entries[entry.id] = entry

    def search(self, query: str) -> List[KBEntry]:
        """Search the database by keyword, title, or description."""
        query_lower = query.lower().strip()
        if not query_lower:
            return list(self.entries.values())

        results = []
        for entry in self.entries.values():
            searchable = (
                entry.id.lower() + " " +
                entry.title.lower() + " " +
                entry.description.lower() + " " +
                entry.human_explanation.lower() + " " +
                entry.what_it_means.lower() + " " +
                " ".join(entry.keywords).lower()
            )
            if query_lower in searchable:
                results.append(entry)
        return results

    def get_by_category(self, category: EntryCategory) -> List[KBEntry]:
        return [e for e in self.entries.values() if e.category == category]

    def get_by_id(self, entry_id: str) -> Optional[KBEntry]:
        return self.entries.get(entry_id)

    def get_all_categories(self) -> List[EntryCategory]:
        seen = set()
        cats = []
        for e in self.entries.values():
            if e.category not in seen:
                seen.add(e.category)
                cats.append(e.category)
        return cats

    def lookup_terminal_line(self, line: str) -> List[KBEntry]:
        """Try to match a terminal line against the database and return relevant entries."""
        line_lower = line.lower()
        matches = []
        for entry in self.entries.values():
            score = 0
            for kw in entry.keywords:
                if kw.lower() in line_lower:
                    score += 2
            if entry.id.lower() in line_lower:
                score += 5
            if score > 0:
                matches.append((score, entry))
        matches.sort(key=lambda x: -x[0])
        return [m[1] for m in matches[:10]]

    # =====================================================
    # DATABASE CONSTRUCTION
    # =====================================================

    def _build_database(self) -> None:
        """Build the entire knowledge base."""
        self._add_event_types()
        self._add_file_operations()
        self._add_file_paths()
        self._add_registry_operations()
        self._add_registry_keys()
        self._add_network_operations()
        self._add_network_protocols()
        self._add_network_ports()
        self._add_process_operations()
        self._add_dll_operations()
        self._add_dll_names()
        self._add_memory_operations()
        self._add_system_concepts()
        self._add_threat_indicators()

    # =====================================================
    # EVENT TYPES
    # =====================================================

    def _add_event_types(self) -> None:
        self._add(KBEntry(
            id="EVT_FILE",
            title="FILE Event",
            category=EntryCategory.EVENT_TYPE,
            description="A file system operation was detected.",
            human_explanation="The sandboxed program opened, read, wrote, created, or deleted a file on your hard drive.",
            what_it_means="Every time the EXE touches a file (config files, logs, temp files, DLLs, data), a FILE event is generated. This shows you exactly what files the program accesses.",
            when_you_see_it="When you see [FILE] in the terminal, the program just performed a file operation.",
            severity=Severity.INFO,
            keywords=["[FILE]", "FILE", "file"],
            example_terminal_line="[12:34:56.789] [FILE] notepad.exe(1234) OPEN: C:\\Users\\test\\document.txt -> SUCCESS",
        ))
        self._add(KBEntry(
            id="EVT_REG",
            title="REG (Registry) Event",
            category=EntryCategory.EVENT_TYPE,
            description="A Windows Registry operation was detected.",
            human_explanation="The sandboxed program read or wrote to the Windows Registry — a central database where Windows and programs store settings.",
            what_it_means="The registry stores configuration, installed software info, startup entries, and more. Programs use it to save settings, check versions, or register themselves. Malware often modifies registry keys for persistence.",
            when_you_see_it="When you see [REG] in the terminal, the program just accessed a registry key.",
            severity=Severity.INFO,
            keywords=["[REG]", "REGISTRY", "registry"],
            example_terminal_line="[12:34:56.789] [REG] myapp.exe(5678) OPEN_KEY: HKCU\\Software\\MyApp -> SUCCESS",
        ))
        self._add(KBEntry(
            id="EVT_NET",
            title="NET (Network) Event",
            category=EntryCategory.EVENT_TYPE,
            description="A network connection or data transfer was detected.",
            human_explanation="The sandboxed program connected to the internet or a local network, or sent/received data.",
            what_it_means="This shows every network connection the program makes — websites it contacts, servers it talks to, data it uploads or downloads. Critical for detecting C2 servers, data exfiltration, or adware.",
            when_you_see_it="When you see [NET] in the terminal, the program just made a network activity.",
            severity=Severity.MEDIUM,
            keywords=["[NET]", "NETWORK", "network", "TCP", "UDP", "DNS"],
            example_terminal_line="[12:34:56.789] [NET] downloader.exe(9012) TCP_CONNECT: 0.0.0.0:49152 -> 142.250.80.46:443",
        ))
        self._add(KBEntry(
            id="EVT_PROC",
            title="PROC (Process) Event",
            category=EntryCategory.EVENT_TYPE,
            description="A process or thread creation/exit was detected.",
            human_explanation="The sandboxed program started a new program (child process) or created/exited a thread.",
            what_it_means="Process events show the program spawning other programs (like cmd.exe, powershell.exe, or other tools). Thread events show internal parallelism. Child processes inherit the sandbox containment.",
            when_you_see_it="When you see [PROC] in the terminal, a process was created, exited, or a thread changed.",
            severity=Severity.INFO,
            keywords=["[PROC]", "PROCESS", "process", "THREAD"],
            example_terminal_line="[12:34:56.789] [PROC] PROCESS_CREATE: cmd.exe(3456) parent=1234 cmd=cmd.exe /c dir",
        ))
        self._add(KBEntry(
            id="EVT_DLL",
            title="DLL Event",
            category=EntryCategory.EVENT_TYPE,
            description="A DLL (Dynamic Link Library) was loaded or unloaded from process memory.",
            human_explanation="The sandboxed program loaded a library of code (DLL) into its memory. DLLs contain reusable functions that programs borrow at runtime.",
            what_it_means="DLLs are shared code libraries. Programs load them to access Windows APIs, graphics, networking, etc. Suspicious DLL loads (like from temp folders) can indicate injection or side-loading attacks.",
            when_you_see_it="When you see [DLL] in the terminal, the program just loaded or unloaded a library.",
            severity=Severity.LOW,
            keywords=["[DLL]", "DLL", "dll", "LOAD", "UNLOAD"],
            example_terminal_line="[12:34:56.789] [DLL] myapp.exe(1234) LOAD: ws2_32.dll -> C:\\Windows\\System32\\ws2_32.dll",
        ))
        self._add(KBEntry(
            id="EVT_MEM",
            title="MEM (Memory) Event",
            category=EntryCategory.EVENT_TYPE,
            description="A memory allocation, free, or protection change was detected.",
            human_explanation="The sandboxed program allocated or freed a chunk of RAM memory, or changed memory protection settings.",
            what_it_means="Memory events show how the program uses RAM. Large allocations may indicate data loading. Protection changes (like making memory executable) can indicate code injection.",
            when_you_see_it="When you see [MEM] in the terminal, the program just changed its memory usage.",
            severity=Severity.LOW,
            keywords=["[MEM]", "MEMORY", "memory", "ALLOC", "FREE", "PROTECT"],
            example_terminal_line="[12:34:56.789] [MEM] myapp.exe(1234) ALLOC: RSS size=2.5MB",
        ))

    # =====================================================
    # FILE OPERATIONS
    # =====================================================

    def _add_file_operations(self) -> None:
        ops = [
            ("FILE_CREATE", "CREATE", "File Created", "A new file was created on disk.",
             "The program just made a brand new file. This could be a config file, log file, cache file, or data file.",
             "Common for first-run programs creating config files, installers creating files, or malware dropping payloads.",
             Severity.INFO),
            ("FILE_OPEN", "OPEN", "File Opened", "An existing file was opened for reading or writing.",
             "The program opened an existing file to read or modify it. The file already existed.",
             "Very common — programs open files to read settings, load data, or write logs.",
             Severity.INFO),
            ("FILE_READ", "READ", "File Read", "Data was read from a file.",
             "The program read the contents of a file. It's pulling data from the file into memory.",
             "Reading config files, documents, DLLs, executables, or any data file.",
             Severity.INFO),
            ("FILE_WRITE", "WRITE", "File Written", "Data was written to a file.",
             "The program wrote data to a file — creating or modifying its contents.",
             "Saving logs, writing config, outputting data, or potentially dropping malicious files.",
             Severity.LOW),
            ("FILE_CLOSE", "CLOSE", "File Closed", "A file handle was closed.",
             "The program finished working with a file and released it.",
             "Normal operation. Files are closed after reading/writing.",
             Severity.INFO),
            ("FILE_DELETE", "DELETE", "File Deleted", "A file was deleted from disk.",
             "The program deleted a file. The file is now gone (or moved to recycle bin).",
             "Malware often deletes logs or evidence. Some programs clean up temp files.",
             Severity.MEDIUM),
            ("FILE_RENAME", "RENAME", "File Renamed", "A file was renamed or moved.",
             "The program changed a file's name or moved it to a different location.",
             "Can be used to hide files or organize data. Some malware renames files to disguise them.",
             Severity.LOW),
        ]
        for fid, badge, title, desc, human, threat, sev in ops:
            self._add(KBEntry(
                id=f"FILE_OP_{fid}",
                title=title,
                category=EntryCategory.FILE_OPERATION,
                description=desc,
                human_explanation=human,
                what_it_means=f"[{badge}] means the program {desc.lower()}",
                when_you_see_it=f"You'll see [FILE] badge with {badge} in the terminal.",
                severity=sev,
                keywords=["FILE", badge, title.lower(), desc.lower()],
                example_terminal_line=f"[12:34:56.789] [FILE] app.exe(1234) {badge}: C:\\path\\file.txt -> SUCCESS",
                threat_context=threat,
            ))

    # =====================================================
    # FILE PATHS
    # =====================================================

    def _add_file_paths(self) -> None:
        paths = [
            ("PATH_WINDOWS_SYSTEM32", "C:\\Windows\\System32\\",
             "Windows System Directory", "The core Windows system folder containing critical OS files.",
             "Contains essential Windows DLLs, drivers, and executables. Programs access this for OS functions.",
             "Normal for most programs. Malware may place files here to blend in.", Severity.INFO),
            ("PATH_WINDOWS_TEMP", "C:\\Windows\\Temp\\",
             "Windows Temp Directory", "The system-wide temporary files folder.",
             "Used by installers, updaters, and services for temporary storage. Often cleaned up automatically.",
             "Frequently used by malware to stage payloads because it's writable and often overlooked.", Severity.MEDIUM),
            ("PATH_USER_TEMP", "AppData\\Local\\Temp\\",
             "User Temp Directory", "The current user's temporary files folder.",
             "Each user has their own temp folder. Programs use it for temporary files, caches, and scratch data.",
             "Very common staging area for malware. Files here are often auto-deleted.", Severity.MEDIUM),
            ("PATH_APPDATA", "AppData\\",
             "AppData Directory", "The user's application data folder where programs store settings and data.",
             "Contains Roaming (synced across PCs), Local (PC-specific), and LocalLow (low privilege) subfolders.",
             "Programs store configs, caches, databases here. Malware uses it for persistence.", Severity.INFO),
            ("PATH_PROGRAM_FILES", "Program Files\\",
             "Program Files Directory", "Where 64-bit programs are installed by default.",
             "The standard installation directory for applications on Windows.",
             "Normal for installed programs. Unexpected files here could be suspicious.", Severity.INFO),
            ("PATH_PROGRAM_FILES_X86", "Program Files (x86)\\",
             "Program Files (x86) Directory", "Where 32-bit programs are installed on 64-bit Windows.",
             "32-bit applications install here on 64-bit Windows systems.",
             "Same as Program Files but for 32-bit apps.", Severity.INFO),
            ("PATH_DESKTOP", "Desktop\\",
             "Desktop Directory", "The user's desktop folder — files here appear on the desktop.",
             "Files placed here show up directly on the Windows desktop for easy access.",
             "Some malware drops files to desktop for visibility. Some installers create shortcuts.", Severity.INFO),
            ("PATH_DOCUMENTS", "Documents\\",
             "Documents Directory", "The user's Documents folder — the default location for personal files.",
             "Standard location for user documents, reports, spreadsheets, etc.",
             "Malware may scan this for sensitive files to steal.", Severity.INFO),
            ("PATH_DOWNLOADS", "Downloads\\",
             "Downloads Directory", "The user's Downloads folder — where browsers save downloaded files.",
             "Files downloaded from the internet land here by default.",
             "Attackers often trick users into running files from Downloads. Common malware entry point.", Severity.MEDIUM),
            ("PATH_STARTUP", "AppData\\Roaming\\Microsoft\\Windows\\Start Menu\\Programs\\Startup\\",
             "Startup Folder", "Programs placed here run automatically when the user logs in.",
             "Windows automatically launches any program in this folder at login. It's a persistence mechanism.",
             "CRITICAL: Malware loves this for persistence. If an unknown program appears here, it will auto-run every boot.", Severity.HIGH),
            ("PATH_REGISTRY_HIVE", "C:\\Windows\\System32\\config\\",
             "Registry Hive Files", "The physical files that store the Windows Registry.",
             "The registry is stored in files on disk. These files are locked while Windows is running.",
             "Direct manipulation of these files is rare and suspicious.", Severity.LOW),
            ("PATH_PREFETCH", "C:\\Windows\\Prefetch\\",
             "Prefetch Directory", "Windows stores program execution traces here for faster loading.",
             "Windows records which programs you run and when, to optimize loading. Files are named PROGRAM.exe-HASH.pf.",
             "Forensic gold mine — shows execution history. Malware sometimes clears prefetch to hide traces.", Severity.LOW),
            ("PATH_RECYCLE_BIN", "C:\\$Recycle.Bin\\",
             "Recycle Bin", "Deleted files are moved here before permanent deletion.",
             "When you delete a file, it goes to the recycle bin. It can be recovered from here.",
             "Malware may delete files from recycle bin to cover tracks.", Severity.LOW),
            ("PATH_DRIVERS", "C:\\Windows\\System32\\drivers\\",
             "Drivers Directory", "Where Windows kernel-mode drivers are stored.",
             "Hardware drivers and kernel extensions live here. They run with highest system privileges.",
             "CRITICAL: Malware dropping .sys files here is a major red flag — it's trying to get kernel access.", Severity.HIGH),
        ]
        for pid, pattern, title, desc, human, threat, sev in paths:
            self._add(KBEntry(
                id=pid,
                title=title,
                category=EntryCategory.FILE_PATH,
                description=desc,
                human_explanation=human,
                what_it_means=f"The path '{pattern}' is {desc.lower()}",
                when_you_see_it=f"You'll see this path pattern in FILE events.",
                severity=sev,
                keywords=[pattern.lower(), title.lower(), pid.lower(), desc.lower()],
                threat_context=threat,
            ))

    # =====================================================
    # REGISTRY OPERATIONS
    # =====================================================

    def _add_registry_operations(self) -> None:
        ops = [
            ("REG_CREATE_KEY", "CREATE_KEY", "Registry Key Created", "A new registry key was created.",
             "The program created a new folder in the registry. This is like creating a new directory in a file system.",
             "Creating keys to store settings is normal. Malware creates keys for persistence or configuration.", Severity.LOW),
            ("REG_OPEN_KEY", "OPEN_KEY", "Registry Key Opened", "An existing registry key was opened for reading.",
             "The program opened a registry key to read its values — like opening a folder to see what's inside.",
             "Very common. Programs read settings, check installations, query system info.", Severity.INFO),
            ("REG_DELETE_KEY", "DELETE_KEY", "Registry Key Deleted", "A registry key was deleted.",
             "The program deleted an entire registry key and all its values.",
             "Unusual for normal programs. Malware may delete security settings or evidence.", Severity.MEDIUM),
            ("REG_SET_VALUE", "SET_VALUE", "Registry Value Set", "A value within a registry key was set or modified.",
             "The program wrote a value (setting) inside a registry key — like saving a configuration option.",
             "Normal for settings. Malware uses this for persistence (Run keys), config, or disabling security.", Severity.LOW),
            ("REG_DELETE_VALUE", "DELETE_VALUE", "Registry Value Deleted", "A specific value within a registry key was deleted.",
             "The program removed a single setting from a registry key.",
             "Can indicate cleaning up settings, or malware removing security configurations.", Severity.MEDIUM),
            ("REG_QUERY_VALUE", "QUERY_VALUE", "Registry Value Queried", "The program read a specific value from a registry key.",
             "The program asked 'what is the value of this setting?' — it's reading a configuration.",
             "Normal for checking settings, versions, installation status.", Severity.INFO),
            ("REG_ENUM_KEY", "ENUM_KEY", "Registry Key Enumerated", "The program listed subkeys within a registry key.",
             "The program is browsing through registry keys to see what's there — like listing subdirectories.",
             "Normal for software enumerating installed components or settings.", Severity.INFO),
        ]
        for fid, badge, title, desc, human, threat, sev in ops:
            self._add(KBEntry(
                id=f"REG_OP_{fid}",
                title=title,
                category=EntryCategory.REGISTRY_OPERATION,
                description=desc,
                human_explanation=human,
                what_it_means=f"[{badge}] means the program {desc.lower()}",
                when_you_see_it=f"You'll see [REG] badge with {badge} in the terminal.",
                severity=sev,
                keywords=["REG", "REGISTRY", badge, title.lower()],
                example_terminal_line=f"[12:34:56.789] [REG] app.exe(1234) {badge}: HKLM\\Software\\MyKey -> SUCCESS",
                threat_context=threat,
            ))

    # =====================================================
    # REGISTRY KEYS
    # =====================================================

    def _add_registry_keys(self) -> None:
        keys = [
            ("REG_RUN", "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run",
             "User Startup Programs", "Programs that automatically start when the current user logs in.",
             "Every program listed here runs at login. It's the most common persistence mechanism on Windows.",
             "CRITICAL: If malware adds itself here, it survives reboots. Check every entry — legitimate ones are usually from installed software.", Severity.CRITICAL,
             ["startup", "autorun", "persistence", "boot"]),
            ("REG_RUN_ONCE", "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\RunOnce",
             "User One-Time Startup", "Programs that run once at next login, then the entry is automatically removed.",
             "Similar to Run but the entry deletes itself after executing once.",
             "Used by installers for first-boot tasks. Malware uses it for one-time payloads.", Severity.HIGH,
             ["startup", "once"]),
            ("REG_RUN_MACHINE", "HKLM\\Software\\Microsoft\\Windows\\CurrentVersion\\Run",
             "Machine-Wide Startup Programs", "Programs that start for ALL users when Windows boots.",
             "Like the user Run key but affects every user on the machine. Requires admin rights to modify.",
             "CRITICAL: System-wide persistence. Very powerful — any program here runs for everyone.", Severity.CRITICAL,
             ["startup", "autorun", "machine"]),
            ("REG_UNINSTALL", "HKLM\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall",
             "Installed Programs Registry", "Windows tracks all installed programs here for Add/Remove Programs.",
             "This is where Windows knows what software is installed on your PC.",
             "Malware may register itself here to appear legitimate, or delete entries to hide.", Severity.LOW,
             ["install", "uninstall", "software"]),
            ("REG_SHELL", "HKLM\\Software\\Microsoft\\Windows NT\\CurrentVersion\\Winlogon",
             "Windows Logon Settings", "Controls what happens at Windows login — shell, userinit, and more.",
             "The 'Shell' value should be 'explorer.exe'. The 'Userinit' value handles login scripts.",
             "CRITICAL: Malware changes 'Shell' to launch itself instead of explorer.exe. Check these values.", Severity.CRITICAL,
             ["logon", "shell", "explorer", "winlogon"]),
            ("REG_FILE_ASSOC", "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\FileExts",
             "File Extension Associations", "Maps file extensions to programs that open them.",
             "When you double-click a .txt file, this registry tells Windows to open Notepad.",
             "Malware may hijack file associations to open malicious programs instead.", Severity.MEDIUM,
             ["association", "extension", "file type"]),
            ("REG_SECURITY", "HKLM\\System\\CurrentControlSet\\Control\\Lsa",
             "Local Security Authority Settings", "Core Windows security configuration — password policies, authentication packages.",
             "Controls how Windows authenticates users, what security packages are loaded, and password policies.",
             "CRITICAL: Modifying LSA settings can disable security features, add rogue authentication, or weaken password policies.", Severity.CRITICAL,
             ["security", "lsa", "authentication", "password"]),
            ("REG_FIREWALL", "HKLM\\System\\CurrentControlSet\\Services\\SharedAccess\\Parameters\\FirewallPolicy",
             "Windows Firewall Settings", "Controls Windows Firewall rules and whether it's enabled.",
             "This is where Windows stores its firewall configuration — what's allowed in/out.",
             "CRITICAL: Malware disables the firewall to allow unrestricted network access.", Severity.CRITICAL,
             ["firewall", "network", "blocking"]),
            ("REG_DEFENDER", "HKLM\\Software\\Microsoft\\Windows Defender",
             "Windows Defender Settings", "Configuration for Windows built-in antivirus.",
             "Windows Defender's settings — real-time protection, exclusions, scan schedules.",
             "CRITICAL: Malware disables Defender or adds exclusions to avoid detection.", Severity.CRITICAL,
             ["antivirus", "defender", "security", "exclusion"]),
            ("REG_SERVICES", "HKLM\\System\\CurrentControlSet\\Services",
             "Windows Services Registry", "Defines all Windows services — drivers, system services, and third-party services.",
             "Every service on your system is registered here with its path, startup type, and configuration.",
             "Malware installs itself as a service for persistence and SYSTEM privileges.", Severity.HIGH,
             ["service", "system", "driver"]),
            ("REG_TCP_IP", "HKLM\\System\\CurrentControlSet\\Services\\Tcpip\\Parameters",
             "TCP/IP Network Settings", "Core Windows networking configuration — DNS, interfaces, routing.",
             "Controls how Windows networking works — DNS servers, IP settings, timeouts.",
             "Malware modifies DNS settings to redirect traffic or adds proxy configurations.", Severity.MEDIUM,
             ["network", "dns", "tcp", "proxy"]),
            ("REG_ENVIRONMENT", "HKLM\\System\\CurrentControlSet\\Control\\Session Manager\\Environment",
             "System Environment Variables", "System-wide PATH and environment variable definitions.",
             "The PATH variable tells Windows where to find executables. Other env vars configure system behavior.",
             "Malware adds its directory to PATH so its executables can be run from anywhere.", Severity.MEDIUM,
             ["path", "environment", "variable"]),
            ("REG_COM", "HKLM\\Software\\Classes\\CLSID",
             "COM Object Registry", "Windows Component Object Model registrations — DLLs and their interfaces.",
             "COM is Windows' component system. DLLs register here so programs can find and use them.",
             "Malware registers malicious COM objects for stealthy persistence and code execution.", Severity.MEDIUM,
             ["com", "class", "dll", "component"]),
            ("REG_BHO", "HKLM\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Browser Helper Objects",
             "Browser Helper Objects", "IE/Edge extensions that run in the browser context.",
             "BHOs are DLLs that load into Internet Explorer/Edge to extend browser functionality.",
             "CRITICAL: Classic malware vector. BHOs can intercept all web traffic, inject ads, steal data.", Severity.CRITICAL,
             ["browser", "bho", "ie", "extension", "web"]),
        ]
        for kid, path, title, desc, human, threat, sev, kws in keys:
            self._add(KBEntry(
                id=kid,
                title=title,
                category=EntryCategory.REGISTRY_KEY,
                description=desc,
                human_explanation=human,
                what_it_means=f"The registry key '{path}' {desc.lower()}",
                when_you_see_it=f"You'll see this key path in REG events.",
                severity=sev,
                keywords=kws + [path.lower(), title.lower(), kid.lower()],
                threat_context=threat,
                example_terminal_line=f"[12:34:56.789] [REG] app.exe(1234) OPEN_KEY: {path} -> SUCCESS",
            ))

    # =====================================================
    # NETWORK OPERATIONS
    # =====================================================

    def _add_network_operations(self) -> None:
        ops = [
            ("NET_TCP_CONNECT", "TCP_CONNECT", "TCP Connection", "A TCP connection was established to a remote server.",
             "The program opened a reliable, ordered connection to a server. This is how most internet traffic works — web browsing, API calls, file transfers.",
             "Any program can connect anywhere. Look for unusual destinations or ports.", Severity.MEDIUM,
             ["connect", "tcp", "connection"]),
            ("NET_TCP_SEND", "TCP_SEND", "TCP Data Sent", "Data was sent over a TCP connection.",
             "The program uploaded or sent data to a server. Could be anything — telemetry, file upload, API request.",
             "Data leaving the system. Check what data and where it's going.", Severity.MEDIUM,
             ["send", "upload", "tcp", "outbound"]),
            ("NET_TCP_RECEIVE", "TCP_RECEIVE", "TCP Data Received", "Data was received over a TCP connection.",
             "The program downloaded data from a server. Could be updates, config, payloads, or responses.",
             "Data entering the system. Malware may download additional payloads.", Severity.MEDIUM,
             ["receive", "download", "tcp", "inbound"]),
            ("NET_TCP_CLOSE", "TCP_CLOSE", "TCP Connection Closed", "A TCP connection was closed.",
             "The program finished a network conversation and closed the connection.",
             "Normal. Connection lifecycle.", Severity.INFO,
             ["close", "disconnect", "tcp"]),
            ("NET_UDP_SEND", "UDP_SEND", "UDP Data Sent", "Data was sent via UDP (connectionless protocol).",
             "The program sent data without establishing a connection first. Faster but unreliable — used for DNS, streaming, gaming.",
             "DNS queries and video streaming use UDP. Unusual UDP to non-standard ports could be suspicious.", Severity.LOW,
             ["send", "udp", "datagram"]),
            ("NET_UDP_RECEIVE", "UDP_RECEIVE", "UDP Data Received", "Data was received via UDP.",
             "The program received a UDP packet. Often a response to a DNS query or streaming data.",
             "Normal for DNS responses. Unusual UDP reception could indicate command-and-control.", Severity.LOW,
             ["receive", "udp", "datagram"]),
            ("NET_DNS_QUERY", "DNS_QUERY", "DNS Query", "The program looked up a domain name to find its IP address.",
             "The program asked 'what is the IP address of example.com?' This is how programs find servers on the internet.",
             "DNS queries reveal what domains the program is contacting. Suspicious domains = suspicious activity.", Severity.MEDIUM,
             ["dns", "domain", "resolve", "lookup", "name"]),
        ]
        for fid, badge, title, desc, human, threat, sev, kws in ops:
            self._add(KBEntry(
                id=f"NET_OP_{fid}",
                title=title,
                category=EntryCategory.NETWORK_OPERATION,
                description=desc,
                human_explanation=human,
                what_it_means=f"[{badge}] means the program {desc.lower()}",
                when_you_see_it=f"You'll see [NET] badge with {badge} in the terminal.",
                severity=sev,
                keywords=kws + ["NET", "NETWORK", badge],
                example_terminal_line=f"[12:34:56.789] [NET] app.exe(1234) {badge}: local -> remote:port",
                threat_context=threat,
            ))

    # =====================================================
    # NETWORK PROTOCOLS
    # =====================================================

    def _add_network_protocols(self) -> None:
        protos = [
            ("PROTO_TCP", "TCP", "Transmission Control Protocol",
             "The reliable, connection-based protocol that powers most internet traffic.",
             "TCP guarantees data arrives in order and without errors. Used for web (HTTP/HTTPS), email, file transfers, and most applications.",
             "Normal for almost all internet activity. The protocol itself isn't suspicious.", Severity.INFO),
            ("PROTO_UDP", "UDP", "User Datagram Protocol",
             "The fast, connectionless protocol used for real-time and DNS traffic.",
             "UDP sends data without checking if it arrived. Used for DNS, video streaming, gaming, VoIP.",
             "DNS uses UDP port 53. Unusual UDP traffic could be tunneling or C2.", Severity.INFO),
            ("PROTO_ICMP", "ICMP", "Internet Control Message Protocol",
             "The protocol used for ping and network diagnostics.",
             "ICMP handles error reporting and diagnostics. 'ping' uses ICMP to check if a host is reachable.",
             "Malware may use ICMP for tunneling data or as a keep-alive signal to C2 servers.", Severity.LOW),
        ]
        for pid, name, title, desc, human, threat, sev in protos:
            self._add(KBEntry(
                id=pid,
                title=title,
                category=EntryCategory.NETWORK_PROTOCOL,
                description=desc,
                human_explanation=human,
                what_it_means=f"Protocol: {name} — {desc}",
                when_you_see_it=f"You'll see {name} in NET events as the protocol.",
                severity=sev,
                keywords=[name.lower(), title.lower(), pid.lower()],
                threat_context=threat,
            ))

    # =====================================================
    # NETWORK PORTS
    # =====================================================

    def _add_network_ports(self) -> None:
        ports = [
            ("PORT_21", 21, "FTP (File Transfer Protocol)",
             "Legacy file transfer protocol. Transmits data including passwords in plain text.",
             "FTP is an old way to transfer files. Everything is sent unencrypted — passwords visible to anyone listening.",
             "Unencrypted FTP is insecure. Malware uses FTP to exfiltrate data. Consider SFTP instead.", Severity.MEDIUM),
            ("PORT_22", 22, "SSH (Secure Shell)",
             "Encrypted remote access and file transfer protocol.",
             "SSH provides secure encrypted access to remote systems. Also used for SFTP file transfers.",
             "Normal for server management. Unexpected SSH connections could indicate unauthorized access.", Severity.LOW),
            ("PORT_23", 23, "Telnet",
             "Unencrypted remote access protocol — extremely insecure.",
             "Telnet sends everything in plain text including passwords. Ancient protocol from the 1970s.",
             "CRITICAL: Telnet is never secure. Any use is suspicious. Used by botnets like Mirai.", Severity.HIGH),
            ("PORT_25", 25, "SMTP (Simple Mail Transfer Protocol)",
             "Protocol for sending email.",
             "SMTP is how email is sent across the internet. Programs use it to send messages.",
             "Malware uses SMTP to send spam or exfiltrate data via email.", Severity.MEDIUM),
            ("PORT_53", 53, "DNS (Domain Name System)",
             "The internet's phone book — translates domain names to IP addresses.",
             "DNS resolves 'google.com' to an IP address. Every internet connection starts with DNS.",
             "DNS tunneling hides data in DNS queries. DNS queries to unusual servers are suspicious.", Severity.MEDIUM),
            ("PORT_80", 80, "HTTP (Hypertext Transfer Protocol)",
             "Standard unencrypted web traffic.",
             "HTTP is how web pages are loaded without encryption. Everything is visible to network observers.",
             "Unencrypted web traffic. If the program downloads executables over HTTP, that's risky.", Severity.LOW),
            ("PORT_443", 443, "HTTPS (HTTP Secure)",
             "Encrypted web traffic — the secure version of HTTP.",
             "HTTPS encrypts web traffic using TLS/SSL. Most modern websites use this.",
             "Normal for most internet activity. Encrypted, so content isn't visible, but destinations are.", Severity.INFO),
            ("PORT_445", 445, "SMB (Server Message Block)",
             "Windows file sharing protocol — used for network drives and printer sharing.",
             "SMB lets Windows computers share files and printers over the network.",
             "CRITICAL: EternalBlue exploit targets SMB. Ransomware (WannaCry) spread via port 445.", Severity.HIGH),
            ("PORT_3389", 3389, "RDP (Remote Desktop Protocol)",
             "Windows remote desktop access — lets you control a PC from another computer.",
             "RDP provides full graphical remote access to a Windows machine. Used for remote administration.",
             "CRITICAL: RDP brute-force attacks are extremely common. If you didn't enable RDP, this is suspicious.", Severity.HIGH),
            ("PORT_8080", 8080, "HTTP Proxy / Alternative HTTP",
             "Common alternative HTTP port, often used for proxies and web servers.",
             "Many web servers and proxies use 8080 as an alternative to port 80.",
             "Common for legitimate proxies. Also used by malware for C2 to avoid blocking common ports.", Severity.LOW),
            ("PORT_3128", 3128, "Squid Proxy",
             "Default port for the Squid proxy server.",
             "Squid is a popular caching proxy. Port 3128 is its default listening port.",
             "May indicate proxy usage. Check if proxy is legitimate.", Severity.LOW),
            ("PORT_9001", 9001, "Tor / Various",
             "Default port for Tor ORPort, also used by various services.",
             "Tor exit nodes and various applications use this port.",
             "High port numbers are often used by Tor or P2P software.", Severity.LOW),
        ]
        for pid, port, title, desc, human, threat, sev in ports:
            self._add(KBEntry(
                id=pid,
                title=f"Port {port} — {title}",
                category=EntryCategory.NETWORK_PORT,
                description=desc,
                human_explanation=human,
                what_it_means=f"Port {port} is used for {title}",
                when_you_see_it=f"You'll see port {port} in NET events.",
                severity=sev,
                keywords=[str(port), title.lower(), pid.lower(), desc.lower()],
                threat_context=threat,
            ))

    # =====================================================
    # PROCESS OPERATIONS
    # =====================================================

    def _add_process_operations(self) -> None:
        ops = [
            ("PROC_CREATE", "CREATE", "Process Created",
             "A new process was spawned by the sandboxed program.",
             "The program just started another program. This could be a child process, helper tool, or system utility.",
             "The command line tells you exactly what was launched. Child processes inherit the sandbox.", Severity.INFO,
             ["create", "spawn", "launch", "child"]),
            ("PROC_EXIT", "EXIT", "Process Exited",
             "A process terminated (either normally or was killed).",
             "A process finished running and was cleaned up. The exit code tells you if it succeeded or failed.",
             "Normal for programs that complete their task. Abnormal exits could indicate crashes or kills.", Severity.INFO,
             ["exit", "terminate", "end", "stop"]),
            ("PROC_THREAD_CREATE", "THREAD_CREATE", "Thread Created",
             "A new thread was created within a process.",
             "The program created a new thread of execution — like a worker that runs in parallel with the main program.",
             "Threads share memory. Multiple threads can do different tasks simultaneously.", Severity.INFO,
             ["thread", "create", "parallel", "worker"]),
            ("PROC_THREAD_EXIT", "THREAD_EXIT", "Thread Exited",
             "A thread within a process was terminated.",
             "A worker thread finished its task and was cleaned up.",
             "Normal thread lifecycle. Many threads being created and destroyed rapidly could be suspicious.", Severity.INFO,
             ["thread", "exit", "terminate"]),
            ("PROC_IMAGE_LOAD", "IMAGE_LOAD", "Image/Module Loaded",
             "An executable or DLL was loaded into process memory.",
             "The program loaded a code module (EXE or DLL) into its address space to use its functions.",
             "Can indicate DLL injection if unexpected modules appear in a process.", Severity.LOW,
             ["image", "load", "module", "inject"]),
        ]
        for fid, badge, title, desc, human, threat, sev, kws in ops:
            self._add(KBEntry(
                id=f"PROC_OP_{fid}",
                title=title,
                category=EntryCategory.PROCESS_OPERATION,
                description=desc,
                human_explanation=human,
                what_it_means=f"[{badge}] means the program {desc.lower()}",
                when_you_see_it=f"You'll see [PROC] badge with {badge} in the terminal.",
                severity=sev,
                keywords=kws + ["PROC", "PROCESS", badge],
                example_terminal_line=f"[12:34:56.789] [PROC] {badge}: proc.exe(1234)",
                threat_context=threat,
            ))

    # =====================================================
    # DLL OPERATIONS
    # =====================================================

    def _add_dll_operations(self) -> None:
        self._add(KBEntry(
            id="DLL_OP_LOAD",
            title="DLL Loaded",
            category=EntryCategory.DLL_OPERATION,
            description="A DLL was loaded into the process's address space.",
            human_explanation="The program loaded a library of shared code (DLL) so it can use its functions. Think of it like checking out a book from a library — the program needs functions that live in this DLL.",
            what_it_means="DLLs contain reusable code. When a program needs to do something (like open a file, show a dialog, or connect to the internet), it loads the DLL that has those functions.",
            when_you_see_it="You'll see [DLL] LOAD when the program first uses a library.",
            severity=Severity.INFO,
            keywords=["DLL", "LOAD", "load", "library"],
            threat_context="Legitimate programs load hundreds of DLLs. Suspicious loads come from unusual paths (temp, downloads) or are known-malicious DLL names.",
        ))
        self._add(KBEntry(
            id="DLL_OP_UNLOAD",
            title="DLL Unloaded",
            category=EntryCategory.DLL_OPERATION,
            description="A DLL was unloaded from the process's address space.",
            human_explanation="The program finished using a library and released it from memory. The DLL's code is no longer available to the program.",
            what_it_means="Programs unload DLLs when they no longer need them, to free memory.",
            when_you_see_it="You'll see [DLL] UNLOAD when the program releases a library.",
            severity=Severity.INFO,
            keywords=["DLL", "UNLOAD", "unload", "release"],
        ))

    # =====================================================
    # DLL NAMES
    # =====================================================

    def _add_dll_names(self) -> None:
        dlls = [
            ("DLL_KERNEL32", "kernel32.dll", "Windows Kernel API",
             "The most fundamental Windows DLL — handles memory, processes, threads, file I/O, and more.",
             "Every Windows program uses kernel32.dll. It's the core interface between your program and the Windows kernel.",
             "Loading kernel32.dll is completely normal. It's loaded by virtually every process.", Severity.INFO),
            ("DLL_NTDLL", "ntdll.dll", "NT Layer DLL",
             "The lowest-level Windows API — interface to the NT kernel. kernel32.dll calls into ntdll.",
             "ntdll.dll is the gateway to the Windows kernel. It's loaded into every process automatically.",
             "Normal. Suspicious if you see direct ntdll calls (unhooking, syscalls).", Severity.INFO),
            ("DLL_USER32", "user32.dll", "Windows User Interface",
             "Handles windows, menus, icons, keyboard input, and other user interface elements.",
             "If a program shows any windows, dialogs, or buttons, it uses user32.dll.",
             "Normal for GUI programs. Console-only programs loading user32 might be hiding a window.", Severity.INFO),
            ("DLL_GDI32", "gdi32.dll", "Graphics Device Interface",
             "Handles drawing graphics, text, and images on screen.",
             "Programs use gdi32.dll for drawing, rendering text, and basic graphics operations.",
             "Normal for any program that draws on screen.", Severity.INFO),
            ("DLL_WS2_32", "ws2_32.dll", "Windows Sockets API",
             "The Windows networking library — handles TCP/UDP connections, DNS, and all network I/O.",
             "ws2_32.dll is how programs talk to the internet. It implements TCP/IP, UDP, and all network protocols.",
             "Any program that uses the internet loads this. Suspicious if loaded by a program that shouldn't need networking.", Severity.LOW),
            ("DLL_ADVAPI32", "advapi32.dll", "Advanced Windows API",
             "Handles registry, security, event logging, and service management.",
             "advapi32.dll provides access to the registry, user accounts, security settings, and Windows services.",
             "Normal for many operations. Heavy registry access through advapi32 is expected.", Severity.INFO),
            ("DLL_SHELL32", "shell32.dll", "Windows Shell API",
             "Handles file operations, shortcuts, drag-and-drop, and shell integration.",
             "shell32.dll provides high-level file operations and Windows shell integration.",
             "Normal for GUI programs that interact with the file system through the shell.", Severity.INFO),
            ("DLL_WININET", "wininet.dll", "Windows Internet API",
             "High-level internet functions — HTTP requests, FTP, cookie management.",
             "wininet.dll provides easy-to-use internet functions. Many programs use it for web requests.",
             "Legitimate for web-connected programs. Malware uses it for HTTP-based C2.", Severity.LOW),
            ("DLL_CRYPT32", "crypt32.dll", "Cryptography API",
             "Windows encryption, decryption, certificate handling, and cryptographic operations.",
             "crypt32.dll handles SSL/TLS certificates, encryption, and digital signatures.",
             "Normal for HTTPS connections. Malware may use it for encrypting stolen data.", Severity.INFO),
            ("DLL_URLMON", "urlmon.dll", "URL Moniker API",
             "Handles URL parsing, MIME type detection, and URL security zones.",
             "urlmon.dll processes URLs and handles internet security zones.",
             "Normal for programs that download files or parse URLs.", Severity.INFO),
            ("DLL_OLE32", "ole32.dll", "OLE/COM Library",
             "Component Object Model (COM) — allows objects to communicate across processes.",
             "OLE32 enables inter-process communication and component sharing through COM.",
             "Normal for many Windows operations. COM hijacking is a persistence technique.", Severity.LOW),
            ("DLL_MSVCR", "msvcr*.dll", "Microsoft C Runtime",
             "The C/C++ runtime library — provides standard C functions like malloc, printf, file I/O.",
             "Almost every C/C++ program needs the MSVC runtime. It provides basic programming functions.",
             "Completely normal. Different versions (msvcr100, msvcr120, vcruntime140) exist.", Severity.INFO),
            ("DLL_PDH", "pdh.dll", "Performance Data Helper",
             "Windows performance monitoring — CPU usage, memory stats, disk I/O counters.",
             "Programs use pdh.dll to check system performance metrics like CPU and memory usage.",
             "Normal for monitoring tools. Unusual for typical applications.", Severity.LOW),
            ("DLL_NSMHTTP", "winhttp.dll", "Windows HTTP Services",
             "Alternative HTTP client library — used for server-to-server communication.",
             "winhttp.dll provides HTTP client functions, often used by services and system components.",
             "Normal for services. Some malware prefers winhttp over wininet.", Severity.LOW),
        ]
        for did, name, title, desc, human, threat, sev in dlls:
            self._add(KBEntry(
                id=did,
                title=f"{name} — {title}",
                category=EntryCategory.DLL_NAME,
                description=desc,
                human_explanation=human,
                what_it_means=f"{name} is {desc.lower()}",
                when_you_see_it=f"You'll see {name} in DLL LOAD events.",
                severity=sev,
                keywords=[name.lower(), title.lower(), did.lower(), desc.lower()],
                threat_context=threat,
            ))

    # =====================================================
    # MEMORY OPERATIONS
    # =====================================================

    def _add_memory_operations(self) -> None:
        ops = [
            ("MEM_ALLOC", "ALLOC", "Memory Allocated",
             "The process allocated a block of RAM memory.",
             "The program asked the operating system for a chunk of RAM to use. It needs space to store data.",
             "Large allocations may indicate loading big files into memory. Many rapid allocations could be a heap spray attack.", Severity.LOW),
            ("MEM_FREE", "FREE", "Memory Freed",
             "The process released a block of RAM back to the system.",
             "The program is done with a chunk of memory and returns it so other programs can use it.",
             "Normal memory management. Programs free memory they no longer need.", Severity.INFO),
            ("MEM_READ", "READ", "Memory Read",
             "The process read data from a memory region.",
             "The program accessed data stored in memory. This is how programs process information.",
             "Normal. Excessive reading of other processes' memory could indicate injection.", Severity.INFO),
            ("MEM_WRITE", "WRITE", "Memory Written",
             "The process wrote data to a memory region.",
             "The program stored data in a memory location. This is how variables and buffers work.",
             "Normal. Writing to another process's memory is suspicious (code injection).", Severity.LOW),
            ("MEM_PROTECT", "PROTECT", "Memory Protection Changed",
             "The protection attributes of a memory region were changed (e.g., made executable).",
             "The program changed the permissions on a memory block — like making readable memory executable.",
             "CRITICAL: Changing memory to EXECUTE (PAGE_EXECUTE_READWRITE) is a classic code injection indicator.", Severity.HIGH),
        ]
        for mid, badge, title, desc, human, threat, sev in ops:
            self._add(KBEntry(
                id=f"MEM_OP_{mid}",
                title=title,
                category=EntryCategory.MEMORY_OPERATION,
                description=desc,
                human_explanation=human,
                what_it_means=f"[{badge}] means the program {desc.lower()}",
                when_you_see_it=f"You'll see [MEM] badge with {badge} in the terminal.",
                severity=sev,
                keywords=["MEM", "MEMORY", badge, title.lower()],
                example_terminal_line=f"[12:34:56.789] [MEM] app.exe(1234) {badge}: RSS size=1.5MB",
                threat_context=threat,
            ))

    # =====================================================
    # SYSTEM CONCEPTS
    # =====================================================

    def _add_system_concepts(self) -> None:
        concepts = [
            ("CONCEPT_JOB_OBJECT", "Windows Job Object",
             "A Windows container that limits what child processes can do — memory, CPU, process count, and more.",
             "Think of a Job Object as a sandbox-within-Windows. It can limit how much memory processes use, how many CPU cycles they get, and even prevent them from creating new processes.",
             "The sandbox uses Job Objects to contain the EXE and all its children. Even if the EXE tries to escape, the Job Object limits what it can do.",
             Severity.INFO, ["job", "object", "containment", "limit"]),
            ("CONCEPT_DETACHED_PROCESS", "Detached Process",
             "A process launched without a console window — invisible to the user by default.",
             "When a process is launched with DETACHED_PROCESS, it doesn't get its own command prompt window. The program runs silently in the background.",
             "The sandbox launches EXEs in detached mode for embedded window embedding — so the EXE's window can be reparented into the sandbox GUI.",
             Severity.INFO, ["detached", "console", "hidden", "background"]),
            ("CONCEPT_SET_PARENT", "SetParent (Window Reparenting)",
             "Changing a window's parent — making another application's window appear inside your GUI.",
             "SetParent is a Windows API that takes an existing window and makes it a child of a different window. The window then appears inside the parent's area.",
             "The sandbox uses this to embed the EXE's GUI inside its own window. The EXE's window becomes part of the sandbox interface.",
             Severity.INFO, ["setparent", "reparent", "embed", "window"]),
            ("CONCEPT_DETOUR", "API Hooking / Detouring",
             "Intercepting function calls to monitor or modify behavior. The sandbox uses this to watch API calls.",
             "Detouring is like putting a tap on a phone line — you can listen to (and sometimes modify) the conversation between a program and the operating system.",
             "This is how the sandbox monitors what the EXE does — it intercepts API calls to log file, registry, network, and process operations.",
             Severity.INFO, ["hook", "detour", "intercept", "monitor", "api"]),
            ("CONCEPT_SANDBOX_MODE", "Sandbox Monitoring Mode",
             "The sandbox observes and logs all activity without blocking anything — a pure monitoring approach.",
             "In Monitor Only mode, the EXE runs normally and can do everything it wants. The sandbox just watches and records everything. Nothing is blocked.",
             "This gives you a complete picture of what the EXE does, without interfering. Useful for analysis before deciding to block operations.",
             Severity.INFO, ["mode", "monitor", "observe", "log"]),
            ("CONCEPT_PROCESS_TREE", "Process Tree",
             "The hierarchy of parent-child process relationships — who spawned whom.",
             "When process A starts process B, B is A's child. The process tree shows this family tree. If the EXE spawns cmd.exe, which spawns powershell.exe, that's a 3-level tree.",
             "The sandbox tracks the full process tree. All child processes are also monitored and contained.",
             Severity.INFO, ["tree", "parent", "child", "hierarchy"]),
            ("CONCEPT_ETW", "Event Tracing for Windows (ETW)",
             "Windows' built-in high-performance event logging system — the foundation of all monitoring.",
             "ETW is Microsoft's kernel-level event system. It's extremely fast and captures events with minimal overhead. The sandbox uses it as one monitoring technique.",
             "ETW can capture process starts, file operations, registry access, network connections, and more — all at kernel level with very low performance impact.",
             Severity.INFO, ["etw", "tracing", "kernel", "event"]),
            ("CONCEPT_PSUTIL", "psutil Library",
             "A Python library for querying system information — processes, memory, CPU, disk, network.",
             "psutil is like a Swiss Army knife for system information. It can list processes, check memory usage, see open files, and monitor network connections.",
             "The sandbox uses psutil to poll process state, detect new connections, track memory usage, and enumerate loaded DLLs.",
             Severity.INFO, ["psutil", "python", "library", "polling"]),
            ("CONCEPT_WMI", "Windows Management Instrumentation (WMI)",
             "Microsoft's framework for accessing system management information — hardware, software, OS settings.",
             "WMI is like a database of everything about your Windows system. Programs can query it to find out about hardware, installed software, running services, etc.",
             "The sandbox uses WMI to detect new process creation events with full command lines.",
             Severity.INFO, ["wmi", "management", "instrumentation"]),
        ]
        for cid, title, desc, human, what, sev, kws in concepts:
            self._add(KBEntry(
                id=cid,
                title=title,
                category=EntryCategory.SYSTEM_CONCEPT,
                description=desc,
                human_explanation=human,
                what_it_means=what,
                when_you_see_it=f"This concept appears in sandbox initialization and operation messages.",
                severity=sev,
                keywords=kws + [title.lower(), cid.lower()],
            ))

    # =====================================================
    # THREAT INDICATORS
    # =====================================================

    def _add_threat_indicators(self) -> None:
        threats = [
            ("THREAT_PERSISTENCE", "Persistence Mechanism Detected",
             "The program is trying to ensure it runs again after a reboot or user login.",
             "Persistence means the program wants to survive a restart. Common techniques: Run keys, Startup folder, Services, Scheduled Tasks, WMI subscriptions.",
             "Legitimate software uses persistence (antivirus, cloud sync). Malware uses it to survive reboots. The key is whether the persistence mechanism is expected for this program.",
             Severity.HIGH, ["persistence", "startup", "autorun", "run key", "service"]),
            ("THREAT_ESCAE", "Sandbox Escape Attempt",
             "The program is trying to break out of the sandbox containment.",
             "The EXE attempted something that the Job Object or sandbox limits should block — like creating processes outside the job, accessing restricted resources, or modifying sandbox settings.",
             "CRITICAL: A sandbox escape attempt means the program is actively trying to bypass your containment. This is a strong malware indicator.",
             Severity.CRITICAL, ["escape", "bypass", "break out", "sandbox"]),
            ("THREAT_PRIVILEGE", "Privilege Escalation",
             "The program is trying to gain higher access rights than it was given.",
             "The program attempted to elevate from user privileges to admin or SYSTEM privileges. This could involve UAC bypass, token manipulation, or exploit code.",
             "CRITICAL: Privilege escalation is almost always malicious. Normal programs don't need SYSTEM access.",
             Severity.CRITICAL, ["privilege", "escalation", "admin", "system", "uac"]),
            ("THREAT_INJECTION", "Code Injection Detected",
             "The program is writing code into another process's memory and executing it.",
             "The program injected its own code into a different process's memory space. The victim process now runs the attacker's code.",
             "CRITICAL: Code injection is a primary malware technique. It hides malicious code inside legitimate processes.",
             Severity.CRITICAL, ["injection", "inject", "writeprocessmemory", "createthread"]),
            ("THREAT_EXFILTRATION", "Data Exfiltration",
             "The program is sending potentially sensitive data to an external server.",
             "The program transmitted data (files, keystrokes, screen captures, documents) to a remote server. This could be stolen data leaving your system.",
             "Look at WHERE the data is going. Cloud storage = possible exfil. Unknown servers = almost certainly exfil.",
             Severity.HIGH, ["exfiltration", "exfil", "upload", "steal", "data"]),
            ("THREAT_RANSOMWARE", "Ransomware Behavior",
             "The program is encrypting files and demanding payment for decryption.",
             "The program is rapidly reading, encrypting, and rewriting files across many directories. This is the hallmark of ransomware.",
             "CRITICAL: If you see mass file encryption (many FILE WRITE events to different directories), disconnect from the network immediately.",
             Severity.CRITICAL, ["ransomware", "encrypt", "crypto", "files"]),
            ("THREAT_KEYLOGGER", "Keylogger Behavior",
             "The program is recording keystrokes to steal passwords and sensitive input.",
             "The program is monitoring keyboard input. This could be through SetWindowsHookEx, GetAsyncKeyState polling, or raw input capture.",
             "CRITICAL: Keyloggers capture passwords, credit card numbers, and private messages.",
             Severity.CRITICAL, ["keylogger", "keyboard", "hook", "keystroke"]),
            ("THREAT_FORMgrab", "Form Grabbing",
             "The program is intercepting web form data before it's encrypted and sent.",
             "The program hooks browser functions to capture form data (usernames, passwords, credit cards) before SSL encryption.",
             "CRITICAL: Form grabbing bypasses HTTPS encryption by stealing data at the browser level.",
             Severity.HIGH, ["form", "grab", "browser", "credential"]),
            ("THREAT_COVER", "Anti-Forensics / Evidence Destruction",
             "The program is trying to hide its tracks by deleting logs, clearing registry, or overwriting files.",
             "The program is deleting event logs, prefetch files, temp files, or registry entries to cover its activity.",
             "Suspicious because legitimate programs rarely need to destroy forensic evidence.",
             Severity.HIGH, ["cover", "delete", "clear", "log", "evidence", "forensic"]),
            ("THREAT_NETWORK_SCAN", "Network Scanning",
             "The program is probing other computers on the network for open ports or vulnerabilities.",
             "The program is connecting to many different IP addresses or ports on the local network, looking for services to attack.",
             "CRITICAL: Network scanning is reconnaissance for lateral movement — the first step in network attacks.",
             Severity.HIGH, ["scan", "recon", "lateral", "network", "probing"]),
            ("THREAT_C2", "Command & Control (C2) Communication",
             "The program is communicating with an attacker's control server.",
             "The program periodically connects to a remote server to receive instructions, download payloads, or send stolen data. C2 servers are the attacker's command center.",
             "Look for periodic network connections to the same IP/domain, especially on high ports or over DNS.",
             Severity.CRITICAL, ["c2", "command", "control", "beacon", "callback"]),
        ]
        for tid, title, desc, human, what, sev, kws in threats:
            self._add(KBEntry(
                id=tid,
                title=title,
                category=EntryCategory.THREAT_INDICATOR,
                description=desc,
                human_explanation=human,
                what_it_means=what,
                when_you_see_it="If multiple events combine to form this pattern, it may indicate malicious activity.",
                severity=sev,
                keywords=kws + [title.lower(), tid.lower()],
                threat_context=what,
            ))


# Global instance
knowledge_base = KnowledgeBase()
