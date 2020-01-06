
import unittest
import re

class RegexTest(unittest.TestCase):

    def setUp(self):
        self._regex = re.compile('create run cafe=(?P<cafeid>[0-9]+) time=(?P<time>(\d{4})-(\d{2})-(\d{2}) (\d{2}):(\d{2})) pickup=(?P<pickup>.*)')

    def test_create_run_correct_syntax(self):
        match = self._regex.match("create run cafe=1 time=2020-01-04 07:30 pickup=ABS Building")
        print(match.groupdict())

if __name__ == "__main__":
    unittest.main()