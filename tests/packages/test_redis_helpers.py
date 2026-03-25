"""Tests for Redis helper functions (no live Redis needed)."""

from database.redis_client import RATE_LIMIT_MAX, RATE_LIMIT_WINDOW, rate_limit_key


class TestRateLimitKey:
    def test_format(self):
        assert rate_limit_key("192.168.1.1") == "rate:192.168.1.1"

    def test_ipv6(self):
        assert rate_limit_key("::1") == "rate:::1"

    def test_empty_ip(self):
        assert rate_limit_key("") == "rate:"


class TestRateLimitConstants:
    def test_window_is_10_minutes(self):
        assert RATE_LIMIT_WINDOW == 600

    def test_max_is_15(self):
        assert RATE_LIMIT_MAX == 15
