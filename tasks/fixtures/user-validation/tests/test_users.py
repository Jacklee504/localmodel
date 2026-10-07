import unittest
from users import create_user, update_user


class UserTests(unittest.TestCase):
    def test_returns(self):
        self.assertEqual(create_user("Ada", 20), ("new", "Ada", 20))
        self.assertEqual(update_user(4, "Ada", 20), (4, "Ada", 20))

    def test_errors(self):
        for call in (lambda: create_user("", 1), lambda: update_user(1, "", 1)):
            with self.assertRaisesRegex(ValueError, "^name required$"):
                call()
        for call in (lambda: create_user("A", -1), lambda: update_user(1, "A", -1)):
            with self.assertRaisesRegex(ValueError, "^age invalid$"):
                call()
