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


class HiddenChangeTests(unittest.TestCase):
    def test_added_and_removed_are_sorted(self):
        self.assertEqual(detect_added(set(), {"c", "a", "b"}), ["a", "b", "c"])
        self.assertEqual(detect_removed({"c", "a", "b"}, set()), ["a", "b", "c"])

    def test_renames_are_sorted_by_old_name(self):
        hints = {"z_old": "z_new", "a_old": "a_new"}
        result = detect_renamed({"a_old", "z_old"}, {"a_new", "z_new"}, hints)
        self.assertEqual(result, [("a_old", "a_new"), ("z_old", "z_new")])

    def test_rename_with_no_hint_is_not_reported(self):
        self.assertEqual(detect_renamed({"old"}, {"new"}, {}), [])

    def test_modified_detects_value_change(self):
        self.assertEqual(detect_modified({"a": {"v": 1}}, {"a": {"v": 2}}), ["a"])

    def test_modified_detects_added_key(self):
        self.assertEqual(detect_modified({"a": {"v": 1}}, {"a": {"v": 1, "w": 2}}), ["a"])

    def test_modified_detects_removed_key(self):
        self.assertEqual(detect_modified({"a": {"v": 1, "w": 2}}, {"a": {"v": 1}}), ["a"])

    def test_dependency_changes_are_sorted(self):
        old = {"b": ["x", "y"], "a": []}
        new = {"a": ["z"], "b": ["x"]}
        result = detect_dependency_changes(old, new)
        self.assertEqual(result, sorted(result))
        self.assertIn(("b", "y", "removed"), result)
        self.assertIn(("a", "z", "added"), result)

    def test_summarise_counts_each_kind(self):
        summary = summarise([
            ("a", "added"), ("b", "added"), ("c", "removed"),
            ("d", "renamed"), ("e", "modified"),
            ("f", "dependency_added"), ("g", "dependency_removed"),
        ])
        self.assertEqual(summary["added"], 2)
        self.assertEqual(summary["removed"], 1)
        self.assertEqual(summary["renamed"], 1)
        self.assertEqual(summary["modified"], 1)
        self.assertEqual(summary["dependency_added"], 1)
        self.assertEqual(summary["dependency_removed"], 1)

    def test_merge_of_empty_lists(self):
        self.assertEqual(merge_changes([]), [])

    def test_merge_keeps_distinct_entries(self):
        merged = merge_changes([[("a", "added")], [("b", "removed")]])
        self.assertEqual(len(merged), 2)
