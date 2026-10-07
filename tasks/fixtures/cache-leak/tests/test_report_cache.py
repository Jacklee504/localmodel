import unittest
import report_cache


class CacheTests(unittest.TestCase):
    def setUp(self):
        report_cache.cache.clear()

    def test_user_isolation_and_filter_order(self):
        calls = []
        def build(user, filters):
            calls.append(user)
            return user
        self.assertEqual(report_cache.get_report("alice", {"year": 2026, "open": True}, build), "alice")
        self.assertEqual(report_cache.get_report("bob", {"open": True, "year": 2026}, build), "bob")
        self.assertEqual(report_cache.get_report("alice", {"open": True, "year": 2026}, build), "alice")
        self.assertEqual(calls, ["alice", "bob"])
