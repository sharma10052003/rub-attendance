"""
Tests for the pure percentage math in attendance_summary.compute_percentage
— no database required.

Run inside a bench:
    bench --site <site> run-tests --app rub_attendance --module rub_attendance.tests.test_attendance_summary

Not runnable on this machine — no Python/bench installed here (see chat).
"""

import unittest

from rub_attendance.rub_attendance.doctype.attendance_summary.attendance_summary import (
	compute_percentage,
)


class TestComputePercentage(unittest.TestCase):
	def test_no_sessions_is_zero_not_divide_by_zero(self):
		self.assertEqual(compute_percentage({}, 0, "Absent"), 0.0)

	def test_all_present(self):
		counts = {"Present": 10, "Absent": 0, "Late": 0, "Excused": 0}
		self.assertEqual(compute_percentage(counts, 10, "Absent"), 100.0)

	def test_late_counts_as_absent_by_default_policy(self):
		counts = {"Present": 7, "Absent": 1, "Late": 2, "Excused": 0}
		self.assertEqual(compute_percentage(counts, 10, "Absent"), 70.0)

	def test_late_counts_as_present_when_policy_says_so(self):
		counts = {"Present": 7, "Absent": 1, "Late": 2, "Excused": 0}
		self.assertEqual(compute_percentage(counts, 10, "Present"), 90.0)

	def test_excused_is_excluded_from_the_denominator(self):
		# Excused sessions don't count against the student at all — neither
		# present nor absent. Of 10 sessions with 5 excused, only the other
		# 5 are counted, and the student was present for all of them.
		counts = {"Present": 5, "Absent": 0, "Late": 0, "Excused": 5}
		self.assertEqual(compute_percentage(counts, 10, "Absent"), 100.0)

	def test_all_sessions_excused_is_100_not_0(self):
		# An empty record (nothing countable yet) should never read as a
		# red flag — 0% would look like the student never showed up.
		counts = {"Present": 0, "Absent": 0, "Late": 0, "Excused": 3}
		self.assertEqual(compute_percentage(counts, 3, "Absent"), 100.0)


if __name__ == "__main__":
	unittest.main()
