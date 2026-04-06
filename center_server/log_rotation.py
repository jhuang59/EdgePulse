#!/usr/bin/env python3
"""
Log Rotation Utilities for EdgePulse Center Server
Provides automatic rotation of JSONL log files to prevent unbounded growth.
"""

import os
import gzip
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional
import threading
import fcntl

# Default rotation settings
DEFAULT_MAX_SIZE_MB = 100  # Rotate when file exceeds this size
DEFAULT_MAX_FILES = 10     # Keep this many rotated files
DEFAULT_COMPRESS = True    # Compress rotated files


class LogRotator:
    """
    Handles log file rotation with optional compression.
    Thread-safe with file locking.
    """

    def __init__(
        self,
        log_file: Path,
        max_size_mb: int = DEFAULT_MAX_SIZE_MB,
        max_files: int = DEFAULT_MAX_FILES,
        compress: bool = DEFAULT_COMPRESS
    ):
        self.log_file = Path(log_file)
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.max_files = max_files
        self.compress = compress
        self.lock = threading.Lock()

    def should_rotate(self) -> bool:
        """Check if the log file should be rotated."""
        if not self.log_file.exists():
            return False
        return self.log_file.stat().st_size >= self.max_size_bytes

    def rotate(self) -> Optional[Path]:
        """
        Rotate the log file if it exceeds the size limit.
        Returns the path to the rotated file, or None if no rotation occurred.
        """
        with self.lock:
            if not self.should_rotate():
                return None

            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            rotated_name = f"{self.log_file.stem}_{timestamp}{self.log_file.suffix}"
            rotated_path = self.log_file.parent / rotated_name

            # Rename current log file
            shutil.move(str(self.log_file), str(rotated_path))

            # Compress if enabled
            if self.compress:
                compressed_path = Path(str(rotated_path) + '.gz')
                with open(rotated_path, 'rb') as f_in:
                    with gzip.open(compressed_path, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                os.remove(rotated_path)
                rotated_path = compressed_path

            # Clean up old rotated files
            self._cleanup_old_files()

            print(f"[LogRotation] Rotated {self.log_file.name} -> {rotated_path.name}")
            return rotated_path

    def _cleanup_old_files(self):
        """Remove rotated files beyond max_files limit."""
        pattern = f"{self.log_file.stem}_*"
        rotated_files = sorted(
            self.log_file.parent.glob(pattern),
            key=lambda f: f.stat().st_mtime,
            reverse=True
        )

        # Keep only max_files
        for old_file in rotated_files[self.max_files:]:
            try:
                os.remove(old_file)
                print(f"[LogRotation] Cleaned up old file: {old_file.name}")
            except Exception as e:
                print(f"[LogRotation] Error cleaning up {old_file.name}: {e}")

    def write_with_rotation(self, line: str) -> None:
        """
        Write a line to the log file, rotating first if necessary.
        Thread-safe operation.
        """
        with self.lock:
            # Check and rotate if needed (without holding lock twice)
            if self.log_file.exists() and self.log_file.stat().st_size >= self.max_size_bytes:
                self._rotate_internal()

            # Write the line
            with open(self.log_file, 'a') as f:
                f.write(line if line.endswith('\n') else line + '\n')

    def _rotate_internal(self):
        """Internal rotation without acquiring lock (called from write_with_rotation)."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        rotated_name = f"{self.log_file.stem}_{timestamp}{self.log_file.suffix}"
        rotated_path = self.log_file.parent / rotated_name

        shutil.move(str(self.log_file), str(rotated_path))

        if self.compress:
            compressed_path = Path(str(rotated_path) + '.gz')
            with open(rotated_path, 'rb') as f_in:
                with gzip.open(compressed_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            os.remove(rotated_path)

        self._cleanup_old_files()


class AtomicFileWriter:
    """
    Provides atomic file operations with file locking.
    Prevents race conditions when multiple processes access the same file.
    """

    def __init__(self, file_path: Path):
        self.file_path = Path(file_path)
        self.lock_file = Path(str(file_path) + '.lock')

    def read_json(self, default=None):
        """Read JSON file with shared lock."""
        if not self.file_path.exists():
            return default if default is not None else {}

        try:
            with open(self.lock_file, 'w') as lock_fd:
                fcntl.flock(lock_fd.fileno(), fcntl.LOCK_SH)
                try:
                    with open(self.file_path, 'r') as f:
                        return json.load(f)
                finally:
                    fcntl.flock(lock_fd.fileno(), fcntl.LOCK_UN)
        except Exception as e:
            print(f"[AtomicFileWriter] Error reading {self.file_path}: {e}")
            return default if default is not None else {}

    def write_json(self, data, indent=2):
        """Write JSON file with exclusive lock."""
        self.file_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(self.lock_file, 'w') as lock_fd:
                fcntl.flock(lock_fd.fileno(), fcntl.LOCK_EX)
                try:
                    with open(self.file_path, 'w') as f:
                        json.dump(data, f, indent=indent)
                finally:
                    fcntl.flock(lock_fd.fileno(), fcntl.LOCK_UN)
        except Exception as e:
            print(f"[AtomicFileWriter] Error writing {self.file_path}: {e}")
            raise

    def update_json(self, update_fn):
        """
        Atomically read, update, and write JSON file.
        update_fn receives current data and should return updated data.
        """
        self.file_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(self.lock_file, 'w') as lock_fd:
                fcntl.flock(lock_fd.fileno(), fcntl.LOCK_EX)
                try:
                    # Read current data
                    if self.file_path.exists():
                        with open(self.file_path, 'r') as f:
                            data = json.load(f)
                    else:
                        data = {}

                    # Apply update
                    updated_data = update_fn(data)

                    # Write back
                    with open(self.file_path, 'w') as f:
                        json.dump(updated_data, f, indent=2)

                    return updated_data
                finally:
                    fcntl.flock(lock_fd.fileno(), fcntl.LOCK_UN)
        except Exception as e:
            print(f"[AtomicFileWriter] Error updating {self.file_path}: {e}")
            raise


# Import json here for AtomicFileWriter
import json


# Singleton rotators for the main log files
_rotators = {}


def get_rotator(log_file: Path, **kwargs) -> LogRotator:
    """Get or create a LogRotator for the given file."""
    key = str(log_file)
    if key not in _rotators:
        _rotators[key] = LogRotator(log_file, **kwargs)
    return _rotators[key]
