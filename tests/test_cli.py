"""Test perfpy CLI."""

import csv
import json
from pathlib import Path

from typer.testing import CliRunner

from perfpy.cli import app

runner = CliRunner()


def test_happy_path_example(tmp_path: Path) -> None:
    """Ensure the example from the README works."""
    to_profile = tmp_path / "to_profile.json"
    report = tmp_path / "report.csv"

    with to_profile.open("w", newline="") as fp:
        json.dump(
            {
                "commands": [
                    {"name": "sysconfig", "command": "python -m sysconfig"},
                    {"name": "zen_of_python", "command": "python -m this"},
                ]
            },
            fp,
        )

    result = runner.invoke(app, [str(to_profile), "--output", str(report)])

    assert result.exit_code == 0
    assert report.exists()

    with report.open("r") as fp:
        csv_reader = csv.DictReader(fp)
        for line in csv_reader:
            assert line.get("name") is not None
            assert line.get("command") is not None
            assert line.get("return_code") == "0"
