"""Smoke test to verify environment and packaging setup."""

import impactlab


def test_package_import() -> None:
    assert impactlab.__name__ == "impactlab"
