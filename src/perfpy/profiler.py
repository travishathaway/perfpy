"""
Profiles Python processes using `psutil` plus a couple of built-in modules.

NOTICE: this currently only works on Unix-like systems (macOS and Linux)
"""

from __future__ import annotations

import contextlib
import shlex
import subprocess
import time

import psutil

from perfpy.schema import Command, Profile

#: Value used to convert bytes to megabytes
BYTES_TO_MB = 1024 * 1024

#: Value used to convert kilobytes to megabytes
KILOBYTES_TO_MB = 1024

#: Type alias for psutil namedtuple
Pcputimes = psutil._common.pcputimes  # noqa: SLF001  (private psutil type)


def _start_process(command: list[str]) -> subprocess.Popen:
    """Start the subprocess and return the Popen handle."""
    return subprocess.Popen(command)  # noqa: S603


def _wrap_psutil(pid: int) -> psutil.Process | None:
    """Return a psutil.Process if it exists, else None (process exited immediately)."""
    try:
        return psutil.Process(pid)
    except psutil.NoSuchProcess:
        return None


def _sum_rss_bytes(proc: psutil.Process, *, include_children: bool) -> int:
    """Return current RSS in bytes for proc (and optionally its children)."""
    rss = 0
    with contextlib.suppress(psutil.NoSuchProcess, psutil.AccessDenied):
        rss += proc.memory_info().rss
        if include_children:
            for child in proc.children(recursive=True):
                with contextlib.suppress(psutil.NoSuchProcess, psutil.AccessDenied):
                    rss += child.memory_info().rss
    return rss


def _cpu_times(proc: psutil.Process) -> Pcputimes:
    """Return current cpu_times for proc, or zeroed values if unavailable."""
    with contextlib.suppress(psutil.NoSuchProcess, psutil.AccessDenied):
        return proc.cpu_times()
    return Pcputimes(0.0, 0.0, 0.0, 0.0)


def _is_better_cpu_times(a: Pcputimes, b: Pcputimes) -> bool:
    """Return True if a has greater (user+system) than b."""
    return (a.user + a.system) > (b.user + b.system)


def _timed_out(start: float, timeout: float | None) -> bool:
    return timeout is not None and (time.time() - start) > timeout


def _kill_tree(proc: psutil.Process) -> None:
    """Best-effort kill of proc and all of its children."""
    with contextlib.suppress(psutil.NoSuchProcess, psutil.AccessDenied):
        for child in proc.children(recursive=True):
            with contextlib.suppress(psutil.NoSuchProcess, psutil.AccessDenied):
                child.kill()
    with contextlib.suppress(psutil.NoSuchProcess, psutil.AccessDenied):
        proc.kill()


def _reap(p: subprocess.Popen, timeout: float = 5.0) -> None:
    """Ensure the subprocess is fully reaped."""
    try:
        p.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        p.kill()
        p.wait()


def _zero_cpu() -> Pcputimes:
    return Pcputimes(0.0, 0.0, 0.0, 0.0)


def run_and_monitor(
    command: list[str],
    interval: float = 0.5,
    *,
    include_children: bool = True,
    timeout: float | None = None,
) -> tuple[int, int, Pcputimes]:
    """
    Start a process, poll until it completes, and monitor RSS memory usage.

    Args:
        command: Command to run (argv list).
        interval: Seconds between polls.
        include_children: Sum RSS of child processes too.
        timeout: Kill the process if it runs longer than this (seconds).

    Returns
    -------
        (return_code, peak_rss_bytes, peak_cpu_times)
    """
    # Normalize command (allowing callers to pass a shell string would be easy: shlex.split)
    proc = _start_process(command)
    ps_proc = _wrap_psutil(proc.pid)

    if ps_proc is None:
        # The process exited immediately.
        rc = proc.wait()
        return rc, 0, _zero_cpu()

    start = time.time()
    peak_rss = 0
    peak_cpu = _zero_cpu()

    try:
        while True:
            rc = proc.poll()

            # Sample current metrics
            current_rss = _sum_rss_bytes(ps_proc, include_children)
            current_cpu = _cpu_times(ps_proc)

            # Update peaks
            peak_rss = max(peak_rss, current_rss)
            if _is_better_cpu_times(current_cpu, peak_cpu):
                peak_cpu = current_cpu

            # Exit conditions
            if rc is not None:
                break

            if _timed_out(start, timeout):
                _kill_tree(ps_proc)
                proc.wait()
                break

            time.sleep(interval)
    finally:
        _reap(proc)

    return proc.returncode, peak_rss, peak_cpu


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

    command_parts = shlex.split(command.command)
    return_code, peak_rss, cpu_times = run_and_monitor(command_parts)

    # Gather statistics after
    net_io_stats_after = psutil.net_io_counters()
    time_after = time.monotonic_ns()

    bytes_recv = net_io_stats_after.bytes_recv - net_io_stats_before.bytes_recv
    bytes_sent = net_io_stats_after.bytes_sent - net_io_stats_before.bytes_sent

    total_time = round(time_after - time_before, ndigits=2)

    return Profile(
        name=command.name,
        command=command.command,
        bytes_recv=bytes_recv,
        bytes_sent=bytes_sent,
        user_time=cpu_times.user,
        cpu_time=cpu_times.system,
        total_time=total_time,
        max_memory_usage=peak_rss,
        return_code=return_code,
    )
