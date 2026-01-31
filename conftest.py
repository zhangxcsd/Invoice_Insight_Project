from __future__ import annotations

import pytest


@pytest.fixture(scope="session")
def config():
    """Provide the repository config object for tests expecting a `config` fixture."""

    from config_manager import get_config

    return get_config()
