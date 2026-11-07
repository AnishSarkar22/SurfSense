"""The install feed end to end, over a real socket: the in-process transport
waits for a response to finish, and this one never does."""

import json
from collections.abc import AsyncIterator

import pytest
from httpx import AsyncClient

from api.main import create_app
from tests.integration.serving_app import serving_app

pytestmark = pytest.mark.integration


@pytest.fixture
async def base_url(data_dir: object) -> AsyncIterator[str]:
    """A migrated app on a free port; data_dir points it at this test's DB."""
    async with serving_app(create_app()) as base:
        yield base


async def test_the_feed_opens_with_every_job(base_url: str) -> None:
    """Its first frame is the whole list, so a screen that connects late or
    reconnects needs nothing it missed."""
    async with (
        AsyncClient(base_url=base_url, timeout=5) as client,
        client.stream("GET", "/llm/installs/events") as reply,
    ):
        assert reply.headers["content-type"].startswith("application/x-ndjson")
        first = await anext(reply.aiter_lines())

    assert json.loads(first) == {"jobs": []}
