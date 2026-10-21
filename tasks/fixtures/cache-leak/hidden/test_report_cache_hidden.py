import unittest
import report_cache


class HiddenCacheTests(unittest.TestCase):
    """Edge cases the visible tests do not cover."""

    def setUp(self):
        report_cache.cache.clear()

    def test_same_user_same_filters_hits_cache(self):
        calls = []

        def build(user, filters):
            calls.append(user)
            return user

        report_cache.get_report("alice", {"a": 1}, build)
        report_cache.get_report("alice", {"a": 1}, build)
        self.assertEqual(calls, ["alice"])

    def test_different_filter_values_do_not_collide(self):
        calls = []

        def build(user, filters):
            calls.append(filters["a"])
            return filters["a"]

        self.assertEqual(report_cache.get_report("alice", {"a": 1}, build), 1)
        self.assertEqual(report_cache.get_report("alice", {"a": 2}, build), 2)
        self.assertEqual(calls, [1, 2])

    def test_empty_filters_still_isolates_by_user(self):
        calls = []

        def build(user, filters):
            calls.append(user)
            return user

        report_cache.get_report("alice", {}, build)
        report_cache.get_report("bob", {}, build)
        self.assertEqual(calls, ["alice", "bob"])
