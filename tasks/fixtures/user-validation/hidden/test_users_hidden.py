import unittest
from users import create_user, update_user


class HiddenUserTests(unittest.TestCase):
    """Edge cases the visible tests do not cover."""

    def test_error_messages_are_exact(self):
        for call, message in (
            (lambda: create_user("", 1), "name required"),
            (lambda: update_user(1, "", 1), "name required"),
            (lambda: create_user("A", -1), "age invalid"),
            (lambda: update_user(1, "A", -1), "age invalid"),
        ):
            with self.assertRaises(ValueError) as caught:
                call()
            self.assertEqual(str(caught.exception), message)

    def test_zero_age_is_valid(self):
        self.assertEqual(create_user("Ada", 0), ("new", "Ada", 0))
        self.assertEqual(update_user(1, "Ada", 0), (1, "Ada", 0))

    def test_save_functions_are_untouched(self):
        import users
        self.assertEqual(users.save_new("A", 1), ("new", "A", 1))
        self.assertEqual(users.save_existing(2, "A", 1), (2, "A", 1))
