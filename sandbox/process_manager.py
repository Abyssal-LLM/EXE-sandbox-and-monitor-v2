"""
Process management for the EXE Sandbox.
This module handles launching, monitoring, and terminating sandboxed processes.
It uses Windows Job Objects for containment and psutil for process tree tracking.
"""
import os
import sys
import time
import ctypes
import ctypes.wintypes
import threading
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

import psutil

from .events import (
    EventBus, global_event_bus,
    ProcessEvent, ProcessOperation,
    ConsoleEvent, ConsoleLevel,
)


# Windows API constants for Job Objects
# These are the values I need to configure the Job Object correctly
# I found these in the Windows SDK headers and documentation
JOB_OBJECT_EXTENDED_LIMIT_INFORMATION = 9
JOB_OBJECT_LIMIT_JOB_MEMORY = 0x00000800
JOB_OBJECT_LIMIT_PROCESS_MEMORY = 0x00000100
JOB_OBJECT_LIMIT_ACTIVE_PROCESS = 0x00000008
JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000
JOB_OBJECT_LIMIT_JOB_TIME = 0x00000004

# Process creation flags
CREATE_SUSPENDED = 0x00000004
CREATE_NEW_CONSOLE = 0x00000010
CREATE_BREAKAWAY_FROM_JOB = 0x01000000
EXTENDED_STARTUPINFO_PRESENT = 0x00080000
DETACHED_PROCESS = 0x00000008
INHERIT_PARENT_AFFINITY = 0x00010000

# Handle constants
JOB_OBJECT_ALL_ACCESS = 0x001F001F
PROCESS_ALL_ACCESS = 0x001FFFFF


class IO_COUNTERS(ctypes.Structure):
    """
    Structure for I/O counters in the Job Object.
    This tracks how many read/write operations the processes in the job have performed.
    """
    _fields_ = [
        ("ReadOperationCount", ctypes.c_uint64),
        ("WriteOperationCount", ctypes.c_uint64),
        ("OtherOperationCount", ctypes.c_uint64),
        ("ReadTransferCount", ctypes.c_uint64),
        ("WriteTransferCount", ctypes.c_uint64),
        ("OtherTransferCount", ctypes.c_uint64),
    ]


class JOBOBJECT_BASIC_LIMIT_INFORMATION(ctypes.Structure):
    """
    Basic limit information for a Job Object.
    This contains the fundamental resource limits we can impose on processes.
    Affinity is ULONG_PTR (pointer-sized), so we use c_size_t.
    """
    _fields_ = [
        ("PerProcessUserTimeLimit", ctypes.c_int64),
        ("PerJobUserTimeLimit", ctypes.c_int64),
        ("LimitFlags", ctypes.c_uint32),
        ("_pad1", ctypes.c_uint32),
        ("MinimumWorkingSetSize", ctypes.c_size_t),
        ("MaximumWorkingSetSize", ctypes.c_size_t),
        ("ActiveProcessLimit", ctypes.c_uint32),
        ("_pad2", ctypes.c_uint32),
        ("Affinity", ctypes.c_size_t),
        ("PriorityClass", ctypes.c_uint32),
        ("SchedulingClass", ctypes.c_uint32),
    ]


class JOBOBJECT_EXTENDED_LIMIT_INFORMATION(ctypes.Structure):
    """
    Extended limit information for a Job Object.
    This provides more granular control over memory and process limits.
    """
    _fields_ = [
        ("BasicLimitInformation", JOBOBJECT_BASIC_LIMIT_INFORMATION),
        ("IoInfo", IO_COUNTERS),
        ("ProcessMemoryLimit", ctypes.c_size_t),
        ("JobMemoryLimit", ctypes.c_size_t),
        ("PeakProcessMemoryUsed", ctypes.c_size_t),
        ("PeakJobMemoryUsed", ctypes.c_size_t),
    ]


class STARTUPINFOW(ctypes.Structure):
    """
    Startup information structure for process creation.
    This defines the initial state of the new process's window and I/O handles.
    """
    _fields_ = [
        ("cb", ctypes.c_uint32),
        ("lpReserved", ctypes.c_wchar_p),
        ("lpDesktop", ctypes.c_wchar_p),
        ("lpTitle", ctypes.c_wchar_p),
        ("dwX", ctypes.c_uint32),
        ("dwY", ctypes.c_uint32),
        ("dwXSize", ctypes.c_uint32),
        ("dwYSize", ctypes.c_uint32),
        ("dwXCountChars", ctypes.c_uint32),
        ("dwYCountChars", ctypes.c_uint32),
        ("dwFillAttribute", ctypes.c_uint32),
        ("dwFlags", ctypes.c_uint32),
        ("wShowWindow", ctypes.c_uint16),
        ("cbReserved2", ctypes.c_uint16),
        ("lpReserved2", ctypes.c_void_p),
        ("hStdInput", ctypes.c_void_p),
        ("hStdOutput", ctypes.c_void_p),
        ("hStdError", ctypes.c_void_p),
    ]


class PROCESS_INFORMATION(ctypes.Structure):
    """
    Structure that receives information about the new process.
    After CreateProcessW returns, this contains the process and thread handles and IDs.
    """
    _fields_ = [
        ("hProcess", ctypes.c_void_p),
        ("hThread", ctypes.c_void_p),
        ("dwProcessId", ctypes.c_uint32),
        ("dwThreadId", ctypes.c_uint32),
    ]


@dataclass
class SandboxedProcess:
    """
    Represents a single sandboxed process and its metadata.
    This is what we track for each process we launch in the sandbox.
    """
    pid: int
    name: str
    exe_path: str
    command_line: str
    start_time: float
    process_handle: ctypes.c_void_p
    thread_handle: ctypes.c_void_p
    psutil_process: Optional[psutil.Process] = None
    is_alive: bool = True
    cpu_percent: float = 0.0
    memory_mb: float = 0.0
    thread_count: int = 0


class ProcessManagerScript:
    """
    The main process manager for the sandbox.
    This handles creating, monitoring, and destroying sandboxed processes.

    This class is responsible for:
    1. Creating Windows Job Objects with resource limits
    2. Launching EXEs as child processes within the Job Object
    3. Tracking the process tree via psutil
    4. Providing real-time statistics for each process
    5. Clean shutdown of all sandboxed processes
    """

    def __init__(self, event_bus: Optional[EventBus] = None):
        """
        Initialize the ProcessManagerScript.

        Parameters:
            event_bus: The event bus to emit events to. If None, uses the global event bus.
        """
        # Store the event bus reference - we'll use this to emit process events
        self.event_bus = event_bus if event_bus is not None else global_event_bus

        # The Job Object handle - this is the kernel object that contains our processes
        # It needs to be created before we can launch any sandboxed processes
        self.job_handle: Optional[ctypes.c_void_p] = None

        # Dictionary of sandboxed processes, keyed by PID
        # This allows us to quickly look up process information
        self.processes: Dict[int, SandboxedProcess] = {}

        # Lock for thread-safe access to the processes dictionary
        # This is important because the monitoring thread and GUI thread both access this
        self.lock = threading.Lock()

        # The main EXE path we're sandboxing
        self.main_exe_path: str = ""

        # The main process PID - this is the root of our process tree
        self.main_pid: int = 0

        # Whether the sandbox is currently running
        self.is_running: bool = False

        # Statistics tracking
        self.total_cpu_usage: float = 0.0
        self.total_memory_mb: float = 0.0
        self.total_threads: int = 0

        # Configuration parameters - these control the Job Object limits
        # I'm setting reasonable defaults that allow most EXEs to run
        self.max_memory_mb: int = 2048  # 2GB total memory limit
        self.max_processes: int = 32    # Maximum concurrent processes
        self.max_cpu_percent: int = 80  # CPU usage cap (0-100)

        # The monitoring timer - this updates process stats periodically
        self.monitor_timer: Optional[threading.Timer] = None
        self.monitor_interval: float = 0.5  # Update every 500ms

        # Emit an initialization message
        self.event_bus.emit(ConsoleEvent(
            level=ConsoleLevel.INFO,
            message="ProcessManagerScript initialized. Ready to sandbox EXEs."
        ))

    def create_job_object(self) -> bool:
        """
        Create and configure the Windows Job Object for process containment.

        The Job Object is a kernel-level object that groups processes and enforces
        resource limits. When the Job Object handle is closed, all processes in
        the job are terminated by the kernel - this ensures clean shutdown.

        Returns:
            True if the Job Object was created successfully, False otherwise.
        """
        # First, I need to close any existing Job Object
        # This is important because we can only have one active sandbox at a time
        if self.job_handle is not None:
            self.close_job_object()

        # Create the Job Object using the Windows API
        # The first parameter is the security attributes (None for default)
        # The second parameter is the name (None for unnamed - which is what we want)
        self.job_handle = ctypes.windll.kernel32.CreateJobObjectW(None, None)

        # Check if the Job Object was created successfully
        if self.job_handle is None:
            self.event_bus.emit(ConsoleEvent(
                level=ConsoleLevel.ERROR,
                message="Failed to create Job Object. Error: " + str(ctypes.GetLastError())
            ))
            return False

        # Now I need to configure the limits for the Job Object
        # I'll use the extended limit information structure for maximum flexibility
        info = JOBOBJECT_EXTENDED_LIMIT_INFORMATION()

        # Set the limit flags - these tell Windows what limits we're enforcing
        # I'm combining multiple flags to get the containment behavior we want
        info.BasicLimitInformation.LimitFlags = (
            JOB_OBJECT_LIMIT_JOB_MEMORY |      # Enable job memory limit
            JOB_OBJECT_LIMIT_PROCESS_MEMORY |   # Enable per-process memory limit
            JOB_OBJECT_LIMIT_ACTIVE_PROCESS |   # Enable process count limit
            JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE  # Kill all processes when handle closes
        )

        # Set the memory limits - these are in bytes
        # The job memory limit is the total for all processes combined
        # The process memory limit is per individual process
        info.JobMemoryLimit = self.max_memory_mb * 1024 * 1024
        info.ProcessMemoryLimit = self.max_memory_mb * 1024 * 1024

        # Set the maximum number of concurrent processes
        # This prevents fork bombs and runaway process creation
        info.BasicLimitInformation.ActiveProcessLimit = self.max_processes

        # Apply the configuration to the Job Object using SetInformationJobObject
        # This is the critical call that actually sets the limits
        result = ctypes.windll.kernel32.SetInformationJobObject(
            self.job_handle,
            JOB_OBJECT_EXTENDED_LIMIT_INFORMATION,
            ctypes.byref(info),
            ctypes.sizeof(info)
        )

        # Check if the configuration was applied successfully
        if result == 0:
            self.event_bus.emit(ConsoleEvent(
                level=ConsoleLevel.ERROR,
                message="Failed to configure Job Object limits. Error: " + str(ctypes.GetLastError())
            ))
            self.close_job_object()
            return False

        # Emit a success message so the user knows the sandbox is ready
        self.event_bus.emit(ConsoleEvent(
            level=ConsoleLevel.SUCCESS,
            message=f"Job Object created. Memory limit: {self.max_memory_mb}MB, Max processes: {self.max_processes}"
        ))

        return True

    def close_job_object(self) -> None:
        """
        Close the Job Object handle.
        This will terminate all processes in the job (if KILL_ON_JOB_CLOSE is set).
        """
        if self.job_handle is not None:
            ctypes.windll.kernel32.CloseHandle(self.job_handle)
            self.job_handle = None

    def launch_sandboxed(self, exe_path: str, args: str = "", working_dir: str = "", create_console: bool = True) -> bool:
        """
        Launch an EXE in the sandbox.

        This method:
        1. Creates a Job Object (if not already created)
        2. Creates the process in a suspended state
        3. Assigns the process to the Job Object
        4. Resumes the process

        Parameters:
            exe_path: Full path to the EXE to launch
            args: Command-line arguments to pass to the EXE
            working_dir: Working directory for the process (uses EXE directory if empty)
            create_console: If True, create a new console window. Set to False for embedding.

        Returns:
            True if the process was launched successfully, False otherwise.
        """
        # Validate the EXE path exists before we try to launch it
        # This prevents confusing error messages later
        if not os.path.exists(exe_path):
            self.event_bus.emit(ConsoleEvent(
                level=ConsoleLevel.ERROR,
                message=f"EXE not found: {exe_path}"
            ))
            return False

        # Store the main EXE path for reference
        self.main_exe_path = exe_path

        # If no working directory was specified, use the EXE's directory
        # This is the standard behavior for most applications
        if not working_dir:
            working_dir = os.path.dirname(exe_path)

        # Create the Job Object if we don't have one yet
        # This needs to happen before we create the process
        if self.job_handle is None:
            if not self.create_job_object():
                return False

        # Build the full command line
        # The format is: "exe_path" args
        # We quote the exe path in case it contains spaces
        full_command = f'"{exe_path}"'
        if args:
            full_command += f" {args}"

        # Set up the startup information structure
        # This defines how the new process's window and I/O handles are configured
        startup_info = STARTUPINFOW()
        startup_info.cb = ctypes.sizeof(STARTUPINFOW)
        startup_info.dwFlags = 0  # No special flags for now

        # The process information structure will receive the new process's handles and IDs
        process_info = PROCESS_INFORMATION()

        # Create the process in a SUSPENDED state
        # We do this so we can assign it to the Job Object before it starts executing
        # If we don't suspend first, the process might finish before we can contain it
        creation_flags = CREATE_SUSPENDED
        if create_console:
            creation_flags |= CREATE_NEW_CONSOLE
        else:
            # For embedded mode: detach from console but still allow window creation
            creation_flags |= DETACHED_PROCESS

        result = ctypes.windll.kernel32.CreateProcessW(
            None,                           # Application name (None = use command line)
            full_command,                   # Command line
            None,                           # Process security attributes
            None,                           # Thread security attributes
            False,                          # Inherit handles
            creation_flags,                 # Creation flags
            None,                           # Environment (inherit parent)
            working_dir,                    # Working directory
            ctypes.byref(startup_info),     # Startup information
            ctypes.byref(process_info)      # Process information (receives handles)
        )

        # Check if the process was created successfully
        if result == 0:
            error_code = ctypes.GetLastError()
            self.event_bus.emit(ConsoleEvent(
                level=ConsoleLevel.ERROR,
                message=f"Failed to create process. Error: {error_code}"
            ))
            return False

        # Now we need to assign the process to our Job Object
        # This is the critical step that contains the process
        assign_result = ctypes.windll.kernel32.AssignProcessToJobObject(
            self.job_handle,
            process_info.hProcess
        )

        # If assignment fails, we need to terminate the process and clean up
        # Otherwise it would run outside our sandbox
        if assign_result == 0:
            self.event_bus.emit(ConsoleEvent(
                level=ConsoleLevel.ERROR,
                message="Failed to assign process to Job Object. Terminating."
            ))
            ctypes.windll.kernel32.TerminateProcess(process_info.hProcess, 1)
            ctypes.windll.kernel32.CloseHandle(process_info.hProcess)
            ctypes.windll.kernel32.CloseHandle(process_info.hThread)
            return False

        # Now that the process is assigned to the job, we can resume it
        # This starts the actual execution of the EXE
        resume_result = ctypes.windll.kernel32.ResumeThread(process_info.hThread)

        # Check if the thread was resumed successfully
        if resume_result == -1:
            self.event_bus.emit(ConsoleEvent(
                level=ConsoleLevel.ERROR,
                message="Failed to resume process thread. Error: " + str(ctypes.GetLastError())
            ))
            ctypes.windll.kernel32.TerminateProcess(process_info.hProcess, 1)
            ctypes.windll.kernel32.CloseHandle(process_info.hProcess)
            ctypes.windll.kernel32.CloseHandle(process_info.hThread)
            return False

        # Try to get a psutil Process object for monitoring
        # This gives us access to CPU usage, memory, and other stats
        try:
            psutil_proc = psutil.Process(process_info.dwProcessId)
        except psutil.NoSuchProcess:
            psutil_proc = None

        # Create a SandboxedProcess object to track this process
        proc_name = os.path.basename(exe_path)
        sandboxed_proc = SandboxedProcess(
            pid=process_info.dwProcessId,
            name=proc_name,
            exe_path=exe_path,
            command_line=full_command,
            start_time=time.time(),
            process_handle=process_info.hProcess,
            thread_handle=process_info.hThread,
            psutil_process=psutil_proc,
            is_alive=True,
        )

        # Add the process to our tracking dictionary
        with self.lock:
            self.processes[process_info.dwProcessId] = sandboxed_proc

        # If this is the main EXE (not a child process), store its PID
        if self.main_pid == 0:
            self.main_pid = process_info.dwProcessId
            self.is_running = True
            # Start the monitoring timer to update process stats
            self.start_monitoring()

        # Emit a process creation event so the GUI knows about the new process
        self.event_bus.emit(ProcessEvent(
            pid=process_info.dwProcessId,
            process_name=proc_name,
            operation=ProcessOperation.CREATE,
            parent_pid=process_info.dwProcessId if self.main_pid == process_info.dwProcessId else self.main_pid,
            command_line=full_command,
            image_path=exe_path,
        ))

        # Also emit a console message for visibility
        self.event_bus.emit(ConsoleEvent(
            level=ConsoleLevel.SUCCESS,
            message=f"Launched: {proc_name} (PID: {process_info.dwProcessId})"
        ))

        return True

    def start_monitoring(self) -> None:
        """
        Start the periodic monitoring of sandboxed processes.
        This updates CPU usage, memory, and thread counts for each process.
        """
        # If monitoring is already running, don't start another timer
        if self.monitor_timer is not None:
            return

        # Create a daemon thread timer that calls _monitor_loop
        # Daemon threads are automatically killed when the main program exits
        self.monitor_timer = threading.Timer(self.monitor_interval, self._monitor_loop)
        self.monitor_timer.daemon = True
        self.monitor_timer.start()

    def _monitor_loop(self) -> None:
        """
        The main monitoring loop that updates process statistics.
        This runs periodically and updates the stats for all sandboxed processes.
        """
        # If the sandbox isn't running, stop monitoring
        if not self.is_running:
            return

        try:
            # Update stats for each process
            self._update_process_stats()

            # Check if any processes have died
            self._check_process_status()
        except Exception as e:
            # Don't let monitoring errors crash the application
            self.event_bus.emit(ConsoleEvent(
                level=ConsoleLevel.WARNING,
                message=f"Monitor loop error: {e}"
            ))

        # Schedule the next monitoring cycle
        # We use a new Timer each time to avoid accumulation issues
        if self.is_running:
            self.monitor_timer = threading.Timer(self.monitor_interval, self._monitor_loop)
            self.monitor_timer.daemon = True
            self.monitor_timer.start()

    def _update_process_stats(self) -> None:
        """
        Update CPU and memory statistics for all sandboxed processes.
        This is called periodically by the monitoring loop.
        """
        total_cpu = 0.0
        total_memory = 0.0
        total_threads = 0

        with self.lock:
            for pid, proc in self.processes.items():
                if not proc.is_alive:
                    continue

                # Try to get updated stats from psutil
                if proc.psutil_process is not None:
                    try:
                        # Get CPU usage - this is the percentage of CPU time
                        # The interval parameter controls how long we sample
                        proc.cpu_percent = proc.psutil_process.cpu_percent(interval=0)

                        # Get memory usage in bytes and convert to MB
                        mem_info = proc.psutil_process.memory_info()
                        proc.memory_mb = mem_info.rss / (1024 * 1024)

                        # Get the number of threads
                        proc.thread_count = proc.psutil_process.num_threads()

                        # Accumulate totals
                        total_cpu += proc.cpu_percent
                        total_memory += proc.memory_mb
                        total_threads += proc.thread_count

                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        # Process might have died or we don't have permission
                        proc.is_alive = False

        # Update the aggregate statistics
        self.total_cpu_usage = total_cpu
        self.total_memory_mb = total_memory
        self.total_threads = total_threads

    def _check_process_status(self) -> None:
        """
        Check if any sandboxed processes have exited.
        This emits exit events for processes that have died.
        """
        with self.lock:
            for pid, proc in list(self.processes.items()):
                if not proc.is_alive:
                    continue

                try:
                    if proc.psutil_process is not None:
                        # Check if the process is still running
                        if not proc.psutil_process.is_running():
                            # Process has exited
                            proc.is_alive = False

                            # Try to get the exit code
                            try:
                                exit_code = proc.psutil_process.exitcode
                            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess, ValueError):
                                exit_code = -1

                            # Emit an exit event
                            self.event_bus.emit(ProcessEvent(
                                pid=pid,
                                process_name=proc.name,
                                operation=ProcessOperation.EXIT,
                                exit_code=exit_code,
                            ))

                            self.event_bus.emit(ConsoleEvent(
                                level=ConsoleLevel.INFO,
                                message=f"Process exited: {proc.name}({pid}) exit_code={exit_code}"
                            ))
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    # Process is gone, mark as dead
                    proc.is_alive = False

    def get_process_tree(self) -> List[dict]:
        """
        Get the current process tree hierarchy.
        This returns a list of process dictionaries with parent-child relationships.

        Returns:
            List of dictionaries containing process information.
        """
        tree = []

        with self.lock:
            for pid, proc in self.processes.items():
                # Build the process info dictionary
                proc_info = {
                    "pid": pid,
                    "name": proc.name,
                    "cpu_percent": proc.cpu_percent,
                    "memory_mb": proc.memory_mb,
                    "thread_count": proc.thread_count,
                    "is_alive": proc.is_alive,
                    "children": [],
                }

                # Find children of this process
                for child_pid, child_proc in self.processes.items():
                    if child_pid != pid and child_proc.psutil_process is not None:
                        try:
                            if child_proc.psutil_process.ppid() == pid:
                                proc_info["children"].append(child_pid)
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            pass

                tree.append(proc_info)

        return tree

    def terminate_all(self) -> None:
        """
        Terminate all sandboxed processes.
        This is the clean shutdown method that ensures all processes are killed.
        """
        self.is_running = False

        # Stop the monitoring timer
        if self.monitor_timer is not None:
            self.monitor_timer.cancel()
            self.monitor_timer = None

        # Close the Job Object - this kills all processes if KILL_ON_JOB_CLOSE is set
        self.close_job_object()

        # Also explicitly terminate any remaining processes
        with self.lock:
            for pid, proc in self.processes.items():
                if proc.is_alive:
                    try:
                        if proc.psutil_process is not None:
                            proc.psutil_process.terminate()
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass

            # Clear the process list
            self.processes.clear()
            self.main_pid = 0

        self.event_bus.emit(ConsoleEvent(
            level=ConsoleLevel.INFO,
            message="All sandboxed processes terminated."
        ))

    def get_stats(self) -> dict:
        """
        Get current sandbox statistics.

        Returns:
            Dictionary containing CPU, memory, and process counts.
        """
        with self.lock:
            active_count = sum(1 for p in self.processes.values() if p.is_alive)
            total_count = len(self.processes)

        return {
            "cpu_percent": self.total_cpu_usage,
            "memory_mb": self.total_memory_mb,
            "threads": self.total_threads,
            "active_processes": active_count,
            "total_processes": total_count,
            "is_running": self.is_running,
        }

    def cleanup(self) -> None:
        """
        Full cleanup of the ProcessManagerScript.
        This should be called when the application is shutting down.
        """
        self.terminate_all()
        self.event_bus.emit(ConsoleEvent(
            level=ConsoleLevel.INFO,
            message="ProcessManagerScript cleaned up."
        ))
