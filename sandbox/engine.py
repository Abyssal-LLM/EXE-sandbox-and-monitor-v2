"""
The main sandbox engine that orchestrates process management and monitoring.
This is the brain that ties everything together - it manages the lifecycle
of the sandbox, coordinates between the process manager and ETW monitor,
and provides a clean API for the GUI to interact with.
"""
import os
import sys
import time
import threading
from typing import Optional

from .events import (
    EventBus, global_event_bus,
    ConsoleEvent, ConsoleLevel,
)
from .process_manager import ProcessManagerScript
from .etw_monitor import ETWMonitorScript


class SandboxEngineScript:
    """
    The main sandbox engine that ties together process management and monitoring.

    This class provides a high-level API for:
    1. Starting and stopping the sandbox
    2. Launching EXEs in the sandbox
    3. Monitoring what the EXE does
    4. Getting statistics and status information

    Think of this as the conductor of the orchestra - it tells the process
    manager and ETW monitor what to do and when to do it.
    """

    def __init__(self, event_bus: Optional[EventBus] = None):
        """
        Initialize the SandboxEngineScript.

        Parameters:
            event_bus: The event bus to use for communication. If None, uses global.
        """
        # Store the event bus - this is how all components communicate
        self.event_bus = event_bus if event_bus is not None else global_event_bus

        # Create the process manager - this handles launching and containing EXEs
        self.process_manager = ProcessManagerScript(self.event_bus)

        # Create the ETW monitor - this watches what the EXE does
        self.etw_monitor = ETWMonitorScript(self.event_bus)

        # Whether the sandbox is currently running
        self.is_running: bool = False

        # The currently loaded EXE path
        self.current_exe_path: str = ""

        # The start time of the current session
        self.session_start_time: float = 0.0

        # The stop time of the last session (for duration after stop)
        self._session_stop_time: float = 0.0

        # Emit an initialization message
        self.event_bus.emit(ConsoleEvent(
            level=ConsoleLevel.INFO,
            message="SandboxEngineScript initialized. Ready to sandbox EXEs."
        ))

    def load_exe(self, exe_path: str) -> bool:
        """
        Load an EXE into the sandbox (but don't run it yet).

        This validates the EXE exists and stores the path for later use.

        Parameters:
            exe_path: Full path to the EXE to load.

        Returns:
            True if the EXE was loaded successfully, False otherwise.
        """
        # First, check if the file exists
        if not os.path.exists(exe_path):
            self.event_bus.emit(ConsoleEvent(
                level=ConsoleLevel.ERROR,
                message=f"EXE not found: {exe_path}"
            ))
            return False

        # Check if it's actually an EXE file
        if not exe_path.lower().endswith('.exe'):
            self.event_bus.emit(ConsoleEvent(
                level=ConsoleLevel.WARNING,
                message=f"File does not appear to be an EXE: {exe_path}"
            ))

        # Store the EXE path
        self.current_exe_path = exe_path

        # Emit a success message
        exe_name = os.path.basename(exe_path)
        self.event_bus.emit(ConsoleEvent(
            level=ConsoleLevel.SUCCESS,
            message=f"EXE loaded: {exe_name}"
        ))

        return True

    def start(self, args: str = "", working_dir: str = "", embedded: bool = False) -> bool:
        """
        Start the sandbox and launch the loaded EXE.

        This method:
        1. Creates a Job Object for containment
        2. Launches the EXE as a sandboxed process
        3. Starts monitoring the process

        Parameters:
            args: Command-line arguments to pass to the EXE.
            working_dir: Working directory for the process.
            embedded: If True, launch without a new console for window embedding.

        Returns:
            True if the sandbox started successfully, False otherwise.
        """
        # Check if we have an EXE loaded
        if not self.current_exe_path:
            self.event_bus.emit(ConsoleEvent(
                level=ConsoleLevel.ERROR,
                message="No EXE loaded. Use load_exe() first."
            ))
            return False

        # Check if the sandbox is already running
        if self.is_running:
            self.event_bus.emit(ConsoleEvent(
                level=ConsoleLevel.WARNING,
                message="Sandbox is already running. Stop it first."
            ))
            return False

        # Record the session start time
        self.session_start_time = time.time()

        # Launch the EXE in the sandbox
        # When embedded=True, we don't create a new console so the window can be reparented
        create_console = not embedded
        success = self.process_manager.launch_sandboxed(
            self.current_exe_path, args, working_dir, create_console=create_console
        )

        if success:
            # Start monitoring
            self.etw_monitor.start()

            # Add the main process PID to monitoring
            self.etw_monitor.add_pid(self.process_manager.main_pid)

            # Set the running flag
            self.is_running = True

            self.event_bus.emit(ConsoleEvent(
                level=ConsoleLevel.SUCCESS,
                message=f"Sandbox started! Monitoring {self.process_manager.main_pid}"
            ))

            return True
        else:
            self.event_bus.emit(ConsoleEvent(
                level=ConsoleLevel.ERROR,
                message="Failed to start sandbox."
            ))
            return False

    def stop(self) -> None:
        """
        Stop the sandbox and terminate all sandboxed processes.

        This method:
        1. Stops all monitoring
        2. Terminates all sandboxed processes
        3. Cleans up resources
        """
        if not self.is_running:
            return

        self.event_bus.emit(ConsoleEvent(
            level=ConsoleLevel.INFO,
            message="Stopping sandbox..."
        ))

        # Stop monitoring first
        self.etw_monitor.stop()

        # Terminate all processes
        self.process_manager.terminate_all()

        # Clear monitoring state
        self.etw_monitor.clear_pids()

        # Update state
        self.is_running = False
        self._session_stop_time = time.time()

        # Calculate session duration
        duration = time.time() - self.session_start_time if self.session_start_time > 0 else 0

        self.event_bus.emit(ConsoleEvent(
            level=ConsoleLevel.INFO,
            message=f"Sandbox stopped. Session duration: {duration:.1f}s"
        ))

    def get_stats(self) -> dict:
        """
        Get comprehensive sandbox statistics.

        Returns:
            Dictionary containing process, monitoring, and session stats.
        """
        process_stats = self.process_manager.get_stats()
        monitor_stats = self.etw_monitor.get_stats()

        # Calculate session duration
        duration = 0.0
        if self.session_start_time > 0:
            if self.is_running:
                duration = time.time() - self.session_start_time
            elif self._session_stop_time > 0:
                duration = self._session_stop_time - self.session_start_time

        return {
            "is_running": self.is_running,
            "exe_path": self.current_exe_path,
            "session_duration": duration,
            "process": process_stats,
            "monitor": monitor_stats,
        }

    def get_process_tree(self) -> list:
        """
        Get the current process tree hierarchy.
        Merges process_manager data with ETW-detected child processes.

        Returns:
            List of process dictionaries with parent-child relationships.
        """
        import psutil

        # Get main process from process_manager
        tree = self.process_manager.get_process_tree()
        known_pids = {p['pid'] for p in tree}

        # Include child processes detected by ETW monitor
        etw_pids = self.etw_monitor.monitored_pids.copy()
        for pid in etw_pids - known_pids:
            try:
                proc = psutil.Process(pid)
                mem_info = proc.memory_info()
                tree.append({
                    "pid": pid,
                    "name": proc.name(),
                    "cpu_percent": proc.cpu_percent(interval=0),
                    "memory_mb": mem_info.rss / (1024 * 1024),
                    "thread_count": proc.num_threads(),
                    "is_alive": True,
                    "children": [],
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        return tree

    def cleanup(self) -> None:
        """
        Full cleanup of the SandboxEngineScript.
        This should be called when the application is shutting down.
        """
        self.stop()
        self.process_manager.cleanup()
        self.etw_monitor.cleanup()

        self.event_bus.emit(ConsoleEvent(
            level=ConsoleLevel.INFO,
            message="SandboxEngineScript cleaned up."
        ))

