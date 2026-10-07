import unittest
from api import put
from store import save


class ApiTests(unittest.TestCase):
    def test_reject_before_write(self):
        db = {}
        with self.assertRaises(ValueError):
            put(db, "", 1)
        self.assertEqual(db, {})

    def test_direct_save_unchanged(self):
        db = {}
        save(db, "", 2)
        self.assertEqual(db, {"": 2})
