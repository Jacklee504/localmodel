import unittest

from cache import build_key, get_cached


class HiddenCacheTests(unittest.TestCase):
    def test_nested_filter_values_are_handled(self):
        self.assertEqual(
            build_key("main", {"tags": ["a", "b"]}),
            build_key("main", {"tags": ["a", "b"]}),
        )

    def test_different_nested_values_differ(self):
        self.assertNotEqual(
            build_key("main", {"tags": ["a", "b"]}),
            build_key("main", {"tags": ["b", "a"]}),
        )

    def test_dict_filter_values_are_handled(self):
        self.assertEqual(
            build_key("main", {"opts": {"x": 1}}),
            build_key("main", {"opts": {"x": 1}}),
        )

    def test_list_and_dict_values_are_not_confused(self):
        self.assertNotEqual(
            build_key("main", {"v": [1, 2]}), build_key("main", {"v": {"a": 1}})
        )

    def test_missing_and_empty_filters_differ(self):
        self.assertNotEqual(build_key("main", {}), build_key("main", {"a": 1}))

    def test_cache_hit_for_nested_filters(self):
        store = {}
        calls = []

        def build(pipeline, filters):
            calls.append(1)
            return "x"

        get_cached(store, "main", {"o": {"k": 1}}, build)
        get_cached(store, "main", {"o": {"k": 1}}, build)
        self.assertEqual(len(calls), 1)
