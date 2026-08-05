"""
Utility helpers for the EXE Sandbox.
This module provides formatting, path manipulation, and other utility functions.
"""
import os
import time


def format_bytes(num_bytes: int) -> str:
    """
    Format a byte count into a human-readable string.
    This is used for displaying memory usage, file sizes, and network transfer sizes.
    """
    # I need to handle the case where bytes is 0 separately
    if num_bytes == 0:
        return "0 B"

    # Define the suffixes we'll use for each magnitude
    # This is a simple approach that goes up to terabytes
    suffixes = ["B", "KB", "MB", "GB", "TB"]

    # Start with the smallest unit and keep dividing until we get a reasonable number
    # We use 1024 as the divisor because we're measuring binary bytes
    value = float(num_bytes)
    suffix_index = 0

    # Keep dividing by 1024 until the value is less than 1024
    # This gives us the most appropriate unit for the given byte count
    while value >= 1024.0 and suffix_index < len(suffixes) - 1:
        value /= 1024.0
        suffix_index += 1

    # Format to 2 decimal places for precision but not overwhelming detail
    # If it's a whole number, we don't need the decimal point
    if value == int(value):
        return f"{int(value)} {suffixes[suffix_index]}"
    else:
        return f"{value:.2f} {suffixes[suffix_index]}"


def format_duration(seconds: float) -> str:
    """
    Format a duration in seconds into a human-readable string.
    This is used for displaying how long a sandbox session has been running.
    """
    # I need to handle negative durations gracefully
    if seconds < 0:
        return "0s"

    # Calculate hours, minutes, and seconds from the total
    # We use integer division to get whole units
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)

    # Build the formatted string based on what units we have
    # If we have hours, show hours and minutes
    # If we have minutes, show minutes and seconds
    # Otherwise, just show seconds with milliseconds
    parts = []
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if secs > 0 or not parts:
        parts.append(f"{secs}s")

    return " ".join(parts)


def format_pid(pid: int) -> str:
    """
    Format a process ID with zero-padding for consistent display.
    This makes the terminal output look more organized when PIDs are aligned.
    """
    # Most Windows PIDs are under 65536, so 5 digits should be sufficient
    # This gives us consistent alignment in the terminal display
    return f"{pid:>5}"


def get_file_extension(filepath: str) -> str:
    """
    Extract the file extension from a filepath.
    This is useful for categorizing file operations by type.
    """
    # I need to handle the case where there's no extension
    # os.path.splitext handles this gracefully, returning '' for no extension
    _, ext = os.path.splitext(filepath)
    return ext.lower()


def get_process_category(process_name: str) -> str:
    """
    Categorize a process by its name for display purposes.
    This helps users quickly understand what kind of process they're looking at.
    """
    # Normalize the process name to lowercase for comparison
    name_lower = process_name.lower()

    # Check for common system processes
    # These are processes that are part of Windows itself
    if name_lower in ("system", "smss.exe", "csrss.exe", "wininit.exe", "winlogon.exe"):
        return "SYSTEM"

    # Check for explorer and shell processes
    # These are the user interface processes
    if name_lower in ("explorer.exe", "shell32.dll", "dwm.exe"):
        return "SHELL"

    # Check for browser processes
    # Modern browsers spawn many child processes, so this catches them all
    if "browser" in name_lower or "chrome" in name_lower or "firefox" in name_lower:
        return "BROWSER"

    # Check for common utility processes
    # These are tools that users frequently run
    if name_lower in ("cmd.exe", "powershell.exe", "pwsh.exe", "wt.exe"):
        return "TERMINAL"

    # If it's not a recognized process, we just call it an APPLICATION
    # This is the default category for unknown processes
    return "APPLICATION"


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename by removing invalid characters.
    This is useful when saving log files with process names in them.
    """
    # Windows doesn't allow certain characters in filenames
    # These characters are reserved by the operating system
    invalid_chars = '<>:"/\\|?*'

    # Replace each invalid character with an underscore
    # This ensures the filename is valid on Windows
    sanitized = filename
    for char in invalid_chars:
        sanitized = sanitized.replace(char, "_")

    # Also remove any leading/trailing spaces and dots
    # Windows doesn't like filenames that end with dots or spaces
    sanitized = sanitized.strip(". ")

    # If the filename is empty after sanitization, use a default name
    # This can happen if the original filename was all invalid characters
    if not sanitized:
        sanitized = "unnamed"

    return sanitized


def timestamp_to_string(timestamp: float) -> str:
    """
    Convert a Unix timestamp to a formatted string.
    This is used for displaying event timestamps in the terminal.
    """
    # Get the local time from the timestamp
    local_time = time.localtime(timestamp)

    # Format as HH:MM:SS.mmm for precise timing
    # The milliseconds come from the fractional part of the timestamp
    base = time.strftime("%H:%M:%S", local_time)
    ms = int((timestamp % 1) * 1000)

    return f"{base}.{ms:03d}"
