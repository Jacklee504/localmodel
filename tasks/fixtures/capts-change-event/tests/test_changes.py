import unittest

from changes import (
    detect_added,
    detect_removed,
    detect_renamed,
    detect_modified,
    detect_dependency_changes,
    merge_changes,
    summarise,
)


class ChangeTests(unittest.TestCase):
    def test_added_and_removed(self):
        self.assertEqual(detect_added({"a", "b"}, {"b", "c"}), ["c"])
        self.assertEqual(detect_removed({"a", "b"}, {"b", "c"}), ["a"])

    def test_added_handles_empty(self):
        self.assertEqual(detect_added(set(), {"a"}), ["a"])
        self.assertEqual(detect_added({"a"}, set()), [])

    def test_renamed_uses_hints(self):
        hints = {"old": "new"}
        self.assertEqual(detect_renamed({"old"}, {"new"}, hints), [("old", "new")])

    def test_conflicting_hint_is_ignored(self):
        self.assertEqual(detect_renamed({"old", "new"}, {"new"}, {"old": "new"}), [])

    def test_renamed_needs_both_absent(self):
        self.assertEqual(detect_renamed({"old"}, {"old", "new"}, {"old": "new"}), [])

    def test_modified_compares_definitions(self):
        old = {"a": {"image": "v1"}, "b": {"image": "v1"}}
        new = {"a": {"image": "v2"}, "b": {"image": "v1"}}
        self.assertEqual(detect_modified(old, new), ["a"])

    def test_modified_ignores_key_order(self):
        old = {"a": {"x": 1, "y": 2}}
        new = {"a": {"y": 2, "x": 1}}
        self.assertEqual(detect_modified(old, new), [])

    def test_dependency_changes(self):
        old = {"build": ["compile"], "test": ["build"]}
        new = {"build": [], "test": ["build", "lint"]}
        result = detect_dependency_changes(old, new)
        self.assertIn(("build", "compile", "removed"), result)
        self.assertIn(("test", "lint", "added"), result)

    def test_summarise_includes_zero_counts(self):
        summary = summarise([("a", "added"), ("b", "removed"), ("c", "removed")])
        self.assertEqual(summary["added"], 1)
        self.assertEqual(summary["removed"], 2)
        self.assertEqual(summary["renamed"], 0)

    def test_merge_removes_duplicates(self):
        merged = merge_changes([[("a", "added")], [("a", "added"), ("b", "removed")]])
        self.assertEqual(merged, [("a", "added"), ("b", "removed")])
