"""perfpy CLI."""

from __future__ import annotations

from typing import TYPE_CHECKING

import typer
from pydantic import ValidationError
from rich import pretty

from perfpy.profiler import profile
from perfpy.report import report
from perfpy.schema import Profile, ProfileCommands

if TYPE_CHECKING:
    from pathlib import Path

app = typer.Typer()


def parse_json(file: Path) -> ProfileCommands:
    """
    Attempt to parse a JSON file.

    Args:
        file: Path to the JSON file

    Raises
    ------
        pydantic.ValidationError: If parsing fails
    """
    try:
        with file.open("r") as f:
            return ProfileCommands.model_validate_json(f.read())
    except ValidationError as e:
        pretty.pprint(e)
        raise typer.Exit(code=1) from e


FileArg = typer.Argument(
    ...,
    exists=True,
    dir_okay=False,
    readable=True,
    help="Path to the JSON file defining the profiling",
)

OutputArg = typer.Option("report.csv", exists=False, help="Name of the output CSV file")


@app.command()
def main(file: Path = FileArg, output: Path = OutputArg) -> None:
    """Profiles list of commands provided."""
    profile_commands = parse_json(file)

    # Run all provided profiling commands
    profile_measures: list[Profile] = [profile(command) for command in profile_commands.commands]

    # Generate report
    report(profile_measures, output)


if __name__ == "__main__":
    app()
