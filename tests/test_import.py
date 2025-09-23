"""Test perfpy."""

import perfpy


def test_import() -> None:
    """Test that the app can be imported."""
    assert isinstance(perfpy.__name__, str)
