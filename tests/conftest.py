"""Shared test fixtures for openclaw-lite test suite."""
from __future__ import annotations

import asyncio
import tempfile
import uuid
from pathlib import Path
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create a session-scoped event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture()
def tmp_db_path(tmp_path: Path) -> Path:
    """Return a temporary SQLite database path."""
    return tmp_path / "test_agent.db"


@pytest.fixture()
def tmp_workspace(tmp_path: Path) -> Path:
    """Return a temporary workspace directory."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    return workspace


@pytest.fixture()
def user_id() -> str:
    """Return a deterministic test user ID."""
    return "test-user-00000000-0000-0000-0000-000000000001"


@pytest.fixture()
def user_id_2() -> str:
    """Return a second deterministic test user ID."""
    return "test-user-00000000-0000-0000-0000-000000000002"


@pytest.fixture()
def session_id() -> str:
    """Return a deterministic test session ID."""
    return "test-session-00000000-0000-0000-0000-000000000001"


@pytest.fixture()
def session_id_2() -> str:
    """Return a second deterministic test session ID."""
    return "test-session-00000000-0000-0000-0000-000000000002"


@pytest.fixture()
def random_user_id() -> str:
    """Return a random user ID."""
    return str(uuid.uuid4())


@pytest.fixture()
def random_session_id() -> str:
    """Return a random session ID."""
    return str(uuid.uuid4())
