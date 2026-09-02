"""
Tests for the pure logic in rub_attendance.setup.generate_sessions — mainly
the weekday-name mapping, since a bug there would silently generate every
session on the wrong day of the week and be easy to miss in a quick look at
the output.

Run inside a real bench:
    bench --site <site> run-tests --app rub_attendance --module rub_attendance.tests.test_generate_sessions

Or locally with no bench at all — see tools/README.md:
    tools/python312/python.exe -m unittest discover -s apps/rub_attendance/rub_attendance/tests -p "test_*.py"
"""

import datetime
import unittest

from rub_attendance.setup.generate_sessions import WEEKDAY_NAMES


class TestWeekdayNames(unittest.TestCase):
	def test_matches_python_date_weekday_convention(self):
		# date.weekday(): Monday=0 .. Sunday=6. If this drifts, every
		# generated session lands on the wrong day.
		known_monday = datetime.date(2026, 9, 7)
		self.assertEqual(known_monday.weekday(), 0)
		self.assertEqual(WEEKDAY_NAMES[known_monday.weekday()], "Monday")

		known_sunday = datetime.date(2026, 9, 13)
		self.assertEqual(known_sunday.weekday(), 6)
		self.assertEqual(WEEKDAY_NAMES[known_sunday.weekday()], "Sunday")

	def test_has_exactly_seven_days(self):
		self.assertEqual(len(WEEKDAY_NAMES), 7)
		self.assertEqual(len(set(WEEKDAY_NAMES)), 7)


if __name__ == "__main__":
	unittest.main()
