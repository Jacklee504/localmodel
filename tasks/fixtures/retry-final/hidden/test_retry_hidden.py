import unittest
from retry import call_with_retry


class HiddenRetryTests(unittest.TestCase):
    """Edge cases the visible tests do not cover."""

    def test_other_exceptions_are_not_retried(self):
        calls = []

        def request():
            calls.append(1)
            raise KeyError("boom")

        with self.assertRaises(KeyError):
            call_with_retry(request, lambda _: None)
        self.assertEqual(len(calls), 1)

    def test_success_on_first_attempt_does_not_sleep(self):
        delays = []
        self.assertEqual(call_with_retry(lambda: "ok", delays.append), "ok")
        self.assertEqual(delays, [])

    def test_negative_attempts_rejected(self):
        with self.assertRaises(ValueError):
            call_with_retry(lambda: None, lambda _: None, -1)

    def test_single_attempt_never_sleeps(self):
        delays = []

        def request():
            raise TimeoutError()

        with self.assertRaises(TimeoutError):
            call_with_retry(request, delays.append, 1)
        self.assertEqual(delays, [])

    def test_delays_are_one_two_then_stop(self):
        delays = []

        def request():
            raise TimeoutError()

        with self.assertRaises(TimeoutError):
            call_with_retry(request, delays.append, 4)
        self.assertEqual(delays, [1, 2, 4])
