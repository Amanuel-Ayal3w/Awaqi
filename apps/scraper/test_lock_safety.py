"""
Targeted lock-safety checks for scraper distributed lock behavior.

This test script validates:
1) lock acquisition returns an owner token
2) second acquisition fails while lock is held
3) stale owner cannot release another owner's lock
4) only current owner can refresh lock TTL
"""

from __future__ import annotations

import asyncio
from unittest.mock import patch

from scraper.main import _acquire_lock, _refresh_lock, _release_lock


class FakeRedis:
    def __init__(self) -> None:
        self.store: dict[str, str] = {}

    async def set(self, key: str, value: str, nx: bool = False, ex: int | None = None):
        del ex  # TTL behavior is not needed for this unit check.
        if nx and key in self.store:
            return None
        self.store[key] = value
        return True

    async def eval(self, script: str, numkeys: int, key: str, *args):
        del numkeys
        token = str(args[0]) if args else ""
        current = self.store.get(key)

        if "return redis.call(\"del\"" in script:
            if current == token:
                del self.store[key]
                return 1
            return 0

        if "return redis.call(\"expire\"" in script:
            return 1 if current == token else 0

        return 0


async def main() -> None:
    fake_redis = FakeRedis()

    with patch("scraper.main.redis_client", fake_redis):
        owner_token = await _acquire_lock()
        assert owner_token is not None, "Expected lock acquisition to succeed"

        second_token = await _acquire_lock()
        assert second_token is None, "Expected second lock acquisition to fail"

        # Simulate ownership change by replacing lock value.
        fake_redis.store["scraper:running"] = "new-owner-token"
        await _release_lock(owner_token)
        assert (
            fake_redis.store.get("scraper:running") == "new-owner-token"
        ), "Stale owner must not release new owner's lock"

        refreshed_stale = await _refresh_lock(owner_token)
        assert not refreshed_stale, "Stale owner must not refresh lock TTL"

        refreshed_current = await _refresh_lock("new-owner-token")
        assert refreshed_current, "Current owner should refresh lock TTL"

    print("lock-safety-tests-passed")


if __name__ == "__main__":
    asyncio.run(main())
