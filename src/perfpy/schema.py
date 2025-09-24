"""Holds pydantic models (i.e. schemas) for project."""

from __future__ import annotations

from pydantic import BaseModel


class Command(BaseModel):
    """Represents a single command that will be profiled."""

    #: Name of the command that ends up in the exported reports
    name: str

    #: Command to be run
    command: str


class ProfileCommands(BaseModel):
    """Represents the input JSON file containing the commands that we will profile."""

    commands: list[Command]


class Profile(BaseModel):
    """Represents a single profile after the data has been collected."""

    #: Name of the command that ends up in the exported reports
    name: str

    #: Command object which holds the command and the name we use for it
    command: str

    #: Bytes received
    bytes_recv: int

    #: Bytes sent
    bytes_sent: int

    #: User time (seconds)
    user_time: float

    #: CPU time (seconds)
    cpu_time: float

    #: Total time (nanoseconds)
    total_time: int

    #: Max memory usage (bytes)
    max_memory_usage: int

    #: Return code of process
    return_code: int | None
