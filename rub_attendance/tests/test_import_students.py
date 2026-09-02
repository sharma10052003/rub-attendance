"""
Tests for the pure parsing/normalization logic in
rub_attendance.setup.import_students — the parts that don't touch the
database, so they can run without a live site.

Run inside a real bench:
    bench --site <site> run-tests --app rub_attendance --module rub_attendance.tests.test_import_students

Or locally with no bench at all — see tools/README.md:
    tools/python312/python.exe -m unittest discover -s rub_attendance/tests -p "test_*.py"
"""

import unittest
from pathlib import Path

from rub_attendance.setup.import_students import (
	identify_programme,
	normalize_email,
	normalize_gender,
	normalize_student_id,
	parse_programme_column,
	parse_roster_identity,
	parse_section,
)


class TestNormalizeStudentId(unittest.TestCase):
	def test_string_with_leading_zero_preserved(self):
		self.assertEqual(normalize_student_id("07260124"), "07260124")

	def test_int_loses_leading_zero_and_gets_repadded(self):
		# This is the real Excel failure mode: a numeric-typed cell drops the
		# leading zero when openpyxl reads it back as a Python int.
		self.assertEqual(normalize_student_id(7260124), "07260124")

	def test_float_from_excel_numeric_cell(self):
		self.assertEqual(normalize_student_id(7260124.0), "07260124")

	def test_none_is_none(self):
		self.assertIsNone(normalize_student_id(None))

	def test_non_numeric_is_none(self):
		self.assertIsNone(normalize_student_id("N/A"))

	def test_blank_is_none(self):
		self.assertIsNone(normalize_student_id("   "))


class TestNormalizeGender(unittest.TestCase):
	def test_single_letter_codes(self):
		self.assertEqual(normalize_gender("F"), "Female")
		self.assertEqual(normalize_gender("m"), "Male")

	def test_full_words_from_admissions_master(self):
		self.assertEqual(normalize_gender("Female"), "Female")
		self.assertEqual(normalize_gender(" Male "), "Male")

	def test_unrecognized_value_is_none_not_guessed(self):
		self.assertIsNone(normalize_gender("Prefer not to say"))

	def test_blank_is_none(self):
		self.assertIsNone(normalize_gender(""))
		self.assertIsNone(normalize_gender(None))


class TestNormalizeEmail(unittest.TestCase):
	def test_real_institutional_format(self):
		self.assertEqual(
			normalize_email("07260124.sherubtse@rub.edu.bt"), "07260124.sherubtse@rub.edu.bt"
		)

	def test_value_without_at_sign_is_none(self):
		# Guards against accidentally reading a non-email column as an email.
		self.assertIsNone(normalize_email("not-an-email"))

	def test_blank_is_none(self):
		self.assertIsNone(normalize_email(""))
		self.assertIsNone(normalize_email(None))


class TestIdentifyProgramme(unittest.TestCase):
	def test_known_fragment_matches(self):
		self.assertEqual(identify_programme("1.BSc in DSDA Section A"), "DSDA")
		self.assertEqual(
			identify_programme("5.BSc in Mathematics Year 1 Sem. I - Autumn 2026"), "MATH"
		)

	def test_unknown_programme_returns_none(self):
		self.assertIsNone(identify_programme("BSc in Underwater Basket Weaving"))


class TestParseProgrammeColumn(unittest.TestCase):
	"""The primary identity path — real values confirmed against the actual
	RUB IMS export (C:\\IMS\\NEW STUDENT UPDATED\\, 2026-09-03), covering all
	seven programmes piloted so far. Two different full-name conventions are
	in use ("Bachelor of X" vs "BSc in X") — both must resolve."""

	def test_all_seven_real_programme_values(self):
		cases = {
			"Bachelor of Data Science and Data Analytics - 2026": "DSDA",
			"Bachelor of Digital Communication and Project Management - 2026": "DCPM",
			"Bachelor of Economics and Political Science - 2026": "EPS",
			"BSc in Mathematics - 2026": "MATH",
			"BSc in Chemistry - 2026": "CHEM",
			"BSc in Physics - 2026": "PHY",
			"BSc in Life Science - 2026": "LFSC",
		}
		for raw_value, expected_code in cases.items():
			with self.subTest(raw_value=raw_value):
				identity, error = parse_programme_column(raw_value)
				self.assertIsNone(error)
				self.assertEqual(identity["programme_code"], expected_code)
				self.assertEqual(identity["intake_year"], 2026)

	def test_missing_year_suffix_is_an_error(self):
		identity, error = parse_programme_column("Bachelor of Data Science and Data Analytics")
		self.assertIsNone(identity)
		self.assertIn("YYYY", error)

	def test_unrecognized_programme_is_an_error_not_a_guess(self):
		identity, error = parse_programme_column("Bachelor of Underwater Basket Weaving - 2026")
		self.assertIsNone(identity)
		self.assertIn("KNOWN_PROGRAMMES", error)

	def test_empty_value_is_an_error(self):
		identity, error = parse_programme_column(None)
		self.assertIsNone(identity)
		self.assertIn("empty", error)


class TestParseSection(unittest.TestCase):
	def test_section_from_filename(self):
		section, notes = parse_section(Path("2.BSc in DSDA Section B.xlsx"))
		self.assertEqual(section, "B")
		self.assertEqual(notes, [])

	def test_no_section_defaults_to_a_with_a_warning(self):
		section, notes = parse_section(Path("5.BSc in Mathematics Year 1 Sem. I - Autumn 2026.xlsx"))
		self.assertEqual(section, "A")
		self.assertEqual(len(notes), 1)


class TestParseRosterIdentity(unittest.TestCase):
	"""The fallback path, used only when a roster has no Programme column —
	the original format this importer was first built against."""

	def test_filename_with_no_year_falls_back_to_title_text(self):
		# Real case from the original format: "1.BSc in DSDA Section A.xlsx"
		# has no year in its filename at all — the year only appears in the
		# sheet's own title string.
		path = Path("1.BSc in DSDA Section A.xlsx")
		identity, notes = parse_roster_identity(
			path, title_text="Bachelor of Data Science and Data Analytics - 2026"
		)
		self.assertIsNotNone(identity)
		self.assertEqual(identity["programme_code"], "DSDA")
		self.assertEqual(identity["intake_year"], 2026)
		self.assertEqual(notes, [])

	def test_filename_with_everything(self):
		path = Path("3.BA in DCPM Year 1 Sem. I - Autumn 2026.xlsx")
		identity, notes = parse_roster_identity(path)
		self.assertEqual(identity["programme_code"], "DCPM")
		self.assertEqual(identity["intake_year"], 2026)
		self.assertEqual(notes, [])

	def test_no_year_anywhere_is_a_hard_error(self):
		path = Path("BSc in DSDA@Section B.xlsx")
		identity, errors = parse_roster_identity(path, title_text="")
		self.assertIsNone(identity)
		self.assertTrue(any("intake year" in e for e in errors))

	def test_unrecognized_programme_is_a_hard_error_not_a_guess(self):
		path = Path("Underwater Basket Weaving Section A - Autumn 2026.xlsx")
		identity, errors = parse_roster_identity(path)
		self.assertIsNone(identity)
		self.assertTrue(any("KNOWN_PROGRAMMES" in e for e in errors))


if __name__ == "__main__":
	unittest.main()
