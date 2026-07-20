"""Pytest config — auto-skip integration tests unless ``--run-integration`` is
passed, so a bare ``uv run pytest`` runs only the fast, hermetic unit suite."""
import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--run-integration",
        action="store_true",
        default=False,
        help="run integration tests that need a live MinerU engine",
    )


def pytest_collection_modifyitems(config, items):
    if config.getoption("--run-integration"):
        return
    skip = pytest.mark.skip(
        reason="needs a running MinerU engine; pass --run-integration to run"
    )
    for item in items:
        if "integration" in item.keywords:
            item.add_marker(skip)
