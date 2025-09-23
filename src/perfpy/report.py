"""Holds everything we need to generate reports."""

import csv
from collections.abc import Iterable
from pathlib import Path

from perfpy.schema import Profile


def report(profiles: Iterable[Profile], filename: Path) -> None:
    """Generate a CSV report from `Profile` objects."""
    with filename.open("w") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(Profile.model_fields.keys())
        for profile in profiles:
            row = tuple(value for value in profile.model_dump().values())
            writer.writerow(row)
