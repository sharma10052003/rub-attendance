"""
Exercises the SQL-condition-building functions in rub_attendance.permissions
directly — these were never actually run before (test_permission_isolation.py
needs a real bench and a real database; these functions are pure string
building plus one frappe.db.escape call, so they can run under the local
stub in tools/ — see tools/README.md).

This does NOT prove the SQL is correct against a real schema (only a real
bench can prove that) — it proves each role gets the KIND of condition it's
supposed to (fully open, scoped-with-the-right-table-and-column, or locked
out), and that no role/doctype combination raises an exception or returns
something structurally wrong (e.g. an empty string where a lockout was
expected, which would silently grant everyone access).

Run inside a real bench:
    bench --site <site> run-tests --app rub_attendance --module rub_attendance.tests.test_permissions_query_conditions

Or locally with no bench at all — see tools/README.md:
    tools/python312/python.exe -m unittest discover -s rub_attendance/tests -p "test_*.py"
"""

import unittest
from contextlib import contextmanager

import rub_attendance.permissions as permissions


@contextmanager
def roles_as(role_list):
	original = permissions.frappe.get_roles
	permissions.frappe.get_roles = lambda user=None: list(role_list)
	try:
		yield
	finally:
		permissions.frappe.get_roles = original


UNRESTRICTED_ROLE_SETS = [
	["System Manager"],
	["Registry"],
	["College Administrator"],
]

NO_ACCESS_ROLE_SETS = [
	[],
	["Student"],
	["Some Unrelated Role"],
]

# (function, scoping-role -> substring expected in the generated SQL)
SCOPED_FUNCTIONS = [
	(permissions.student_query_conditions, "HOD", "hod_user"),
	(permissions.student_query_conditions, "Programme Coordinator", "coordinator_user"),
	(permissions.student_query_conditions, "Lecturer", "tabLecturer"),
	(permissions.cohort_query_conditions, "HOD", "hod_user"),
	(permissions.cohort_query_conditions, "Programme Coordinator", "coordinator_user"),
	(permissions.cohort_query_conditions, "Lecturer", "tabLecturer"),
	(permissions.course_offering_query_conditions, "HOD", "hod_user"),
	(permissions.course_offering_query_conditions, "Programme Coordinator", "coordinator_user"),
	(permissions.course_offering_query_conditions, "Lecturer", "tabLecturer"),
	(permissions.course_enrolment_query_conditions, "HOD", "hod_user"),
	(permissions.course_enrolment_query_conditions, "Programme Coordinator", "coordinator_user"),
	(permissions.course_enrolment_query_conditions, "Lecturer", "tabLecturer"),
	(permissions.class_session_query_conditions, "HOD", "hod_user"),
	(permissions.class_session_query_conditions, "Programme Coordinator", "coordinator_user"),
	(permissions.class_session_query_conditions, "Lecturer", "tabLecturer"),
	(permissions.attendance_summary_query_conditions, "HOD", "hod_user"),
	(permissions.attendance_summary_query_conditions, "Programme Coordinator", "coordinator_user"),
	(permissions.attendance_summary_query_conditions, "Lecturer", "tabLecturer"),
]

ALL_QUERY_CONDITION_FUNCTIONS = [
	permissions.student_query_conditions,
	permissions.cohort_query_conditions,
	permissions.course_offering_query_conditions,
	permissions.course_enrolment_query_conditions,
	permissions.class_session_query_conditions,
	permissions.attendance_summary_query_conditions,
]


class TestAdministratorAlwaysUnrestricted(unittest.TestCase):
	def test_administrator_user_bypasses_regardless_of_roles(self):
		for fn in ALL_QUERY_CONDITION_FUNCTIONS:
			with self.subTest(fn=fn.__name__):
				with roles_as([]):
					self.assertEqual(fn("Administrator"), "")


class TestUnrestrictedRoles(unittest.TestCase):
	def test_global_roles_get_no_condition(self):
		for fn in ALL_QUERY_CONDITION_FUNCTIONS:
			for role_set in UNRESTRICTED_ROLE_SETS:
				with self.subTest(fn=fn.__name__, roles=role_set):
					with roles_as(role_set):
						self.assertEqual(fn("someone@example.test"), "")


class TestRubAcademicAdministratorIsNotGlobal(unittest.TestCase):
	"""The one deliberate exception: RUB Academic Administrator must NOT get
	unrestricted access to Student/Cohort/Course Offering/Course Enrolment/
	Class Session — only to Attendance Summary (the aggregate). See
	phase4/00-setup-and-verification.md and SPEC.md A4."""

	def test_locked_out_of_row_level_doctypes(self):
		row_level_fns = [
			permissions.student_query_conditions,
			permissions.cohort_query_conditions,
			permissions.course_offering_query_conditions,
			permissions.course_enrolment_query_conditions,
			permissions.class_session_query_conditions,
		]
		for fn in row_level_fns:
			with self.subTest(fn=fn.__name__):
				with roles_as(["RUB Academic Administrator"]):
					self.assertEqual(fn("rub-admin@example.test"), "1=0")

	def test_unrestricted_on_the_aggregate_doctype(self):
		with roles_as(["RUB Academic Administrator"]):
			self.assertEqual(
				permissions.attendance_summary_query_conditions("rub-admin@example.test"), ""
			)


class TestNoAccessRoles(unittest.TestCase):
	def test_roles_with_no_defined_scope_are_locked_out(self):
		for fn in ALL_QUERY_CONDITION_FUNCTIONS:
			for role_set in NO_ACCESS_ROLE_SETS:
				with self.subTest(fn=fn.__name__, roles=role_set):
					with roles_as(role_set):
						self.assertEqual(fn("someone@example.test"), "1=0")


class TestScopedRolesReferenceTheRightColumn(unittest.TestCase):
	def test_scoped_condition_mentions_the_right_scoping_column_and_the_user(self):
		user = "scoped-user@example.test"
		for fn, role, expected_substring in SCOPED_FUNCTIONS:
			with self.subTest(fn=fn.__name__, role=role):
				with roles_as([role]):
					condition = fn(user)
				self.assertIn(expected_substring, condition)
				self.assertIn(user, condition)
				self.assertNotEqual(condition.strip(), "")
				self.assertNotEqual(condition.strip(), "1=0")


if __name__ == "__main__":
	unittest.main()
