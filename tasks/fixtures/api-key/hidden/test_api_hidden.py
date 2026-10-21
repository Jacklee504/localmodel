import unittest
from api import put
from store import save


class HiddenApiTests(unittest.TestCase):
    """Edge cases the visible tests do not cover."""

    def test_empty_key_is_rejected_without_writing(self):
        db = {}
        with self.assertRaises(ValueError):
            put(db, "", 1)
        self.assertEqual(db, {})

    def test_non_empty_key_is_written(self):
        db = {}
        self.assertEqual(put(db, "k", 1), {"ok": True})
        self.assertEqual(db, {"k": 1})

    def test_save_still_accepts_empty_keys(self):
        db = {}
        save(db, "", 2)
        self.assertEqual(db, {"": 2})
