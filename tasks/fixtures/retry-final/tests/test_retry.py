import unittest
from retry import call_with_retry


class RetryTests(unittest.TestCase):
    def test_exhaustion(self):
        delays = []
        def request():
            raise TimeoutError("timed out")
        with self.assertRaisesRegex(TimeoutError, "timed out"):
            call_with_retry(request, delays.append)
        self.assertEqual(delays, [1, 2])

    def test_eventual_success(self):
        calls = []
        def request():
            calls.append(1)
            if len(calls) < 2:
                raise TimeoutError()
            return "ok"
        self.assertEqual(call_with_retry(request, lambda _: None), "ok")
        self.assertEqual(len(calls), 2)

    def test_invalid_attempts(self):
        with self.assertRaises(ValueError):
            call_with_retry(lambda: None, lambda _: None, 0)
