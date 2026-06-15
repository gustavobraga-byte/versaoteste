"""Tests for the jokes module (v0.3 typed version)."""

from __future__ import annotations

import random

import pytest

from pesquisai.jokes import (
    ALL_JOKES,
    JOKES_BY_CATEGORY,
    list_categories,
    next_joke,
    reset_index,
)


class TestNextJoke:
    def test_random_category_returns_from_pool(self, monkeypatch):
        # Force random.choice to return a known element so the test
        # is deterministic.
        monkeypatch.setattr(random, "choice", lambda seq: seq[0])
        result = next_joke("aleatorio")
        assert result == ALL_JOKES[0]

    def test_unknown_category_falls_back_to_random(self, monkeypatch):
        monkeypatch.setattr(random, "choice", lambda seq: seq[-1])
        result = next_joke("categoria-que-nao-existe")
        assert result == ALL_JOKES[-1]

    def test_known_category_round_robin(self):
        reset_index("economia")
        # First call should return index 0 of the economy pool.
        first = next_joke("economia")
        assert first == JOKES_BY_CATEGORY["economia"][0]
        # Second call returns index 1.
        second = next_joke("economia")
        assert second == JOKES_BY_CATEGORY["economia"][1]

    def test_round_robin_wraps_around(self):
        reset_index("economia")
        pool = JOKES_BY_CATEGORY["economia"]
        # Save the start position, then call len(pool) more times and
        # verify we end up back where we started.
        start = next_joke("economia")
        for _ in range(len(pool) - 1):
            next_joke("economia")
        # The next call should be the same joke we started with
        # (because the index wrapped around by len(pool)).
        assert next_joke("economia") == start


class TestListCategories:
    def test_returns_sorted_unique(self):
        cats = list_categories()
        assert cats == sorted(cats)
        assert "economia" in cats
        assert "fisica" in cats
        assert "medicina" in cats

    def test_matches_registry_keys(self):
        cats = list_categories()
        assert set(cats) == set(JOKES_BY_CATEGORY.keys())


class TestResetIndex:
    def test_reset_specific_category(self):
        next_joke("astronomia")
        next_joke("astronomia")
        assert "astronomia" in (reset_index.__globals__["_index"])
        reset_index("astronomia")
        # Hard to assert on a private variable from outside, but
        # the call must not raise.
        assert next_joke("astronomia") == JOKES_BY_CATEGORY["astronomia"][0]

    def test_reset_all(self):
        next_joke("fisica")
        next_joke("quimica")
        reset_index()
        assert next_joke("fisica") == JOKES_BY_CATEGORY["fisica"][0]
