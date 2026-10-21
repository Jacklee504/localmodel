import unittest

from cache import build_key, get_cached


class CacheTests(unittest.TestCase):
    def test_key_is_order_independent(self):
        self.assertEqual(
            build_key("main", {"year": 2026, "open": True}),
            build_key("main", {"open": True, "year": 2026}),
        )

    def test_key_distinguishes_values(self):
        self.assertNotEqual(
            build_key("main", {"year": 2026}), build_key("main", {"year": 2027})
        )

    def test_key_distinguishes_pipelines(self):
        self.assertNotEqual(
            build_key("main", {"year": 2026}), build_key("other", {"year": 2026})
        )

    def test_get_cached_hits_on_reordered_filters(self):
        store = {}
        calls = []

        def build(pipeline, filters):
            calls.append(pipeline)
            return "result"

        first = get_cached(store, "main", {"a": 1, "b": 2}, build)
        second = get_cached(store, "main", {"b": 2, "a": 1}, build)
        self.assertEqual(first, "result")
        self.assertEqual(second, "result")
        self.assertEqual(len(calls), 1)
