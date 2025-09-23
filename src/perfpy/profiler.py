"""
Profiles Python processes using `psutil` plus a couple of built-in modules.

NOTICE: this currently only works on Unix-like systems (macOS and Linux)
"""

from __future__ import annotations

import resource
import subprocess
import sys
import time

import psutil

from perfpy.schema import Command, Profile

#: Value used to convert bytes to megabytes
BYTES_TO_MB = 1024 * 1024

#: Value used to convert kilobytes to megabytes
KILOBYTES_TO_MB = 1024


def profile(command: Command) -> Profile:
    """
    Entry point for the profiling script.

    Args:
        command: The command to run

    Raises
    ------
        subprocess.CalledProcessError
    """
    # Gather the network and time statistics before
    net_io_stats_before = psutil.net_io_counters()
    time_before = time.monotonic_ns()

    sub = subprocess.Popen(command.command.split())  # noqa: S603
    sub.wait()

    rusage = resource.getrusage(resource.RUSAGE_CHILDREN)

    # Gather statistics after
    net_io_stats_after = psutil.net_io_counters()
    time_after = time.monotonic_ns()

    bytes_recv = net_io_stats_after.bytes_recv - net_io_stats_before.bytes_recv
    bytes_sent = net_io_stats_after.bytes_sent - net_io_stats_before.bytes_sent

    total_time = round(time_after - time_before, ndigits=2)
    max_mem_convert = BYTES_TO_MB if sys.platform == "darwin" else KILOBYTES_TO_MB
    max_memory_usage = round(rusage.ru_maxrss / max_mem_convert, ndigits=2)

    return Profile(
        name=command.name,
        command=command.command,
        bytes_recv=bytes_recv,
        bytes_sent=bytes_sent,
        user_time=rusage.ru_utime,
        cpu_time=rusage.ru_stime,
        total_time=total_time,
        max_memory_usage=max_memory_usage,
    )
