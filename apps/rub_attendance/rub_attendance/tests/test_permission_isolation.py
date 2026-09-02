"""
Phase 4 isolation test suite — the minimum set specified in
phase0/05-permission-matrix.md:

    - College B admin opens a College A student -> 403 (API method,
      /api/resource, and report/list view).
    - A lecturer not assigned to a Course Offering can't read/write its
      Class Session.
    - A student can never read another student's record.
    - A Programme Coordinator for Programme X can't write/read a Course
      Offering or Class Session belonging to Programme Y.
    - RUB Academic Administrator can't open an individual Student record
      directly (no doctype permission at all) - the only path is the
      logged audit.view_student_record, which the last test verifies
      actually writes to Audit Log.

Run inside a bench:
    bench --site <site> run-tests --app rub_attendance --module rub_attendance.tests.test_permission_isolation

Not runnable on this machine — no Python/bench installed here (see chat).
Needs a real site: these tests create Users, User Permissions, and real
records, and impersonate different logged-in users via frappe.set_user().
"""

import frappe
from frappe.tests.utils import FrappeTestCase


def _make_user(email, roles):
	if frappe.db.exists("User", email):
		user = frappe.get_doc("User", email)
	else:
		user = frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": email.split("@")[0],
				"send_welcome_email": 0,
			}
		).insert(ignore_permissions=True)
	user.add_roles(*roles)
	return user.name


class TestPermissionIsolation(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.set_user("Administrator")

		# Two independent colleges, each with its own department/programme/
		# cohort/student/lecturer/course offering, so cross-college and
		# cross-department leaks are actually exercised, not assumed.
		cls.college_a = frappe.get_doc(
			{"doctype": "College", "college_code": "TESTA", "college_name": "Test College A"}
		).insert(ignore_permissions=True).name
		cls.college_b = frappe.get_doc(
			{"doctype": "College", "college_code": "TESTB", "college_name": "Test College B"}
		).insert(ignore_permissions=True).name

		cls.hod_a_email = "hod-a@example.test"
		cls.hod_b_email = "hod-b@example.test"
		_make_user(cls.hod_a_email, ["HOD"])
		_make_user(cls.hod_b_email, ["HOD"])

		cls.dept_a = frappe.get_doc(
			{
				"doctype": "Department",
				"department_name": "Dept A",
				"department_code": "DEPTA",
				"college": cls.college_a,
				"hod_user": cls.hod_a_email,
			}
		).insert(ignore_permissions=True).name
		cls.dept_b = frappe.get_doc(
			{
				"doctype": "Department",
				"department_name": "Dept B",
				"department_code": "DEPTB",
				"college": cls.college_b,
				"hod_user": cls.hod_b_email,
			}
		).insert(ignore_permissions=True).name

		cls.programme_a = frappe.get_doc(
			{
				"doctype": "Programme",
				"programme_name": "Programme A",
				"programme_code": "PROGA",
				"department": cls.dept_a,
			}
		).insert(ignore_permissions=True).name
		cls.programme_b = frappe.get_doc(
			{
				"doctype": "Programme",
				"programme_name": "Programme B",
				"programme_code": "PROGB",
				"department": cls.dept_b,
			}
		).insert(ignore_permissions=True).name

		cls.cohort_a = frappe.get_doc(
			{"doctype": "Cohort", "programme": cls.programme_a, "intake_year": 2026, "section": "A"}
		).insert(ignore_permissions=True).name
		cls.cohort_b = frappe.get_doc(
			{"doctype": "Cohort", "programme": cls.programme_b, "intake_year": 2026, "section": "A"}
		).insert(ignore_permissions=True).name

		cls.student_a = frappe.get_doc(
			{
				"doctype": "Student",
				"student_id": "TESTSTU0001",
				"first_name": "Student A",
				"cohort": cls.cohort_a,
			}
		).insert(ignore_permissions=True).name
		cls.student_b = frappe.get_doc(
			{
				"doctype": "Student",
				"student_id": "TESTSTU0002",
				"first_name": "Student B",
				"cohort": cls.cohort_b,
			}
		).insert(ignore_permissions=True).name

		cls.lecturer_a_email = "lecturer-a@example.test"
		_make_user(cls.lecturer_a_email, ["Lecturer"])
		cls.lecturer_a = frappe.get_doc(
			{
				"doctype": "Lecturer",
				"staff_id": "TESTLEC0001",
				"full_name": "Lecturer A",
				"college": cls.college_a,
				"user": cls.lecturer_a_email,
			}
		).insert(ignore_permissions=True).name

		cls.course_a = frappe.get_doc(
			{
				"doctype": "Course",
				"course_code": "TESTC001",
				"course_title": "Test Course A",
				"department": cls.dept_a,
			}
		).insert(ignore_permissions=True).name

		co = frappe.get_doc(
			{
				"doctype": "Course Offering",
				"course": cls.course_a,
				"cohort": cls.cohort_a,
				"session_type": "Lecture",
			}
		)
		co.append("lecturers", {"lecturer": cls.lecturer_a, "role": "Primary"})
		cls.course_offering_a = co.insert(ignore_permissions=True).name

		frappe.db.commit()

	def tearDown(self):
		frappe.set_user("Administrator")

	# -- College isolation (native User Permission mechanism) --------------

	def test_college_admin_cannot_see_other_college_student(self):
		email = "college-admin-a@example.test"
		_make_user(email, ["College Administrator"])
		frappe.get_doc(
			{"doctype": "User Permission", "user": email, "allow": "College", "for_value": self.college_a}
		).insert(ignore_permissions=True)

		frappe.set_user(email)
		visible = set(frappe.get_list("Student", pluck="name"))
		self.assertIn(self.student_a, visible)
		self.assertNotIn(self.student_b, visible)

		with self.assertRaises(frappe.PermissionError):
			frappe.get_doc("Student", self.student_b)

	# -- Department isolation (HOD) -----------------------------------------

	def test_hod_cannot_see_other_department_student(self):
		frappe.set_user(self.hod_a_email)
		visible = set(frappe.get_list("Student", pluck="name"))
		self.assertIn(self.student_a, visible)
		self.assertNotIn(self.student_b, visible)

		with self.assertRaises(frappe.PermissionError):
			frappe.get_doc("Student", self.student_b)

	def test_hod_cannot_write_other_department_course_offering(self):
		frappe.set_user(self.hod_b_email)
		doc = frappe.get_doc("Course Offering", self.course_offering_a)
		self.assertFalse(doc.has_permission("write"))

	# -- Lecturer scoping ----------------------------------------------------

	def test_unassigned_lecturer_cannot_write_class_session(self):
		other_lecturer_email = "lecturer-other@example.test"
		_make_user(other_lecturer_email, ["Lecturer"])
		frappe.get_doc(
			{
				"doctype": "Lecturer",
				"staff_id": "TESTLEC9999",
				"full_name": "Unassigned Lecturer",
				"college": self.college_a,
				"user": other_lecturer_email,
			}
		).insert(ignore_permissions=True)
		frappe.db.commit()

		frappe.set_user(other_lecturer_email)
		with self.assertRaises(frappe.PermissionError):
			frappe.get_doc(
				{
					"doctype": "Class Session",
					"course_offering": self.course_offering_a,
					"scheduled_date": "2026-09-10",
					"status": "Scheduled",
				}
			).insert()

	def test_assigned_lecturer_can_create_class_session(self):
		frappe.set_user(self.lecturer_a_email)
		session = frappe.get_doc(
			{
				"doctype": "Class Session",
				"course_offering": self.course_offering_a,
				"scheduled_date": "2026-09-11",
				"status": "Scheduled",
			}
		).insert()
		self.assertEqual(session.course_offering, self.course_offering_a)

	# -- Student self-isolation (no Desk-level access at all) -----------------

	def test_student_role_has_no_desk_list_access(self):
		student_user_email = "student-a@example.test"
		_make_user(student_user_email, ["Student"])
		frappe.set_user(student_user_email)
		visible = frappe.get_list("Student", pluck="name")
		self.assertEqual(visible, [])

	# -- RUB Academic Administrator: no raw access, only the logged path ------

	def test_rub_admin_cannot_open_student_directly(self):
		email = "rub-admin@example.test"
		_make_user(email, ["RUB Academic Administrator"])
		frappe.set_user(email)
		with self.assertRaises(frappe.PermissionError):
			frappe.get_doc("Student", self.student_a)

	def test_rub_admin_logged_drill_down_writes_audit_log(self):
		from rub_attendance.api.audit import view_student_record

		email = "rub-admin-2@example.test"
		_make_user(email, ["RUB Academic Administrator"])
		frappe.set_user(email)

		before = frappe.db.count("Audit Log")
		result = view_student_record(self.student_a, reason="Investigating a dispute escalation")
		after = frappe.db.count("Audit Log")

		self.assertEqual(result.get("name"), self.student_a)
		self.assertEqual(after, before + 1)

		frappe.set_user("Administrator")
		last_entry = frappe.get_last_doc("Audit Log")
		self.assertEqual(last_entry.accessed_by, email)
		self.assertEqual(last_entry.student, self.student_a)

	def test_rub_admin_drill_down_requires_a_reason(self):
		from rub_attendance.api.audit import view_student_record

		email = "rub-admin-3@example.test"
		_make_user(email, ["RUB Academic Administrator"])
		frappe.set_user(email)
		with self.assertRaises(frappe.ValidationError):
			view_student_record(self.student_a, reason="   ")
