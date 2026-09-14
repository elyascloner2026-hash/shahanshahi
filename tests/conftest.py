"""
Test fixtures. Sets required env vars BEFORE any project module is
imported (config.py raises at import time if they're missing), and
provides a fresh in-memory Database per test.
"""
import os

os.environ.setdefault("BOT_TOKEN", "test-token-not-real")
os.environ.setdefault("ADMIN_IDS", "1,7224258053")
os.environ.setdefault("CHANNEL_USERNAME", "@ShahanshahiGameBot")
os.environ.setdefault("DATABASE_PATH", ":memory:")
os.environ.setdefault("FIGHT_COOLDOWN", "300")

import pytest

from database import Database


@pytest.fixture
async def test_db():
    database = Database(path=":memory:")
    await database.connect()
    yield database
    await database.close()
