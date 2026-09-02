"""
Lecturer roll-call API — the backend for the one custom interactive screen
this app has (per SPEC.md architecture: Desk handles everything else).

Implements the contract in phase0/06-api-contract.md:
    get_session(course_offering, date)
    submit(class_session, rows, client_marked_at)
    request_correction(class_session, student, requested_status, reason)

Every method here resolves the caller's Lecturer record from
frappe.session.user and checks Course Offering Lecturer assignment
server-side — never trusts a lecturer/student identity passed by the client.
"""

from datetime import datetime, time, timedelta

import frappe
from frappe.utils import get_datetime, getdate, now_datetime

from rub_attendance.rub_attendance.doctype.attendance_policy.attendance_policy import get_policy


def _current_lecturer():
	lecturer = frappe.db.get_value("Lecturer", {"user": frappe.session.user}, "name")
	if not lecturer:
		frappe.throw("No Lecturer record is linked to your user account", frappe.PermissionError)
	return lecturer


def _assert_lecturer_assigned(course_offering: str, lecturer: str):
	privileged = {"System Manager", "Registry", "HOD", "Programme Coordinator", "College Administrator"}
	if privileged & set(frappe.get_roles()):
		return
	assigned = frappe.db.exists(
		"Course Offering Lecturer", {"parent": course_offering, "lecturer": lecturer}
	)
	if not assigned:
		frappe.throw(
			"You are not assigned to this Course Offering's lecturer list", frappe.PermissionError
		)


def _enrolled_students(course_offering: str):
	rows = frappe.db.get_all(
		"Course Enrolment",
		filters={"course_offering": course_offering, "enrolment_status": "Active"},
		fields=["student"],
	)
	return [r.student for r in rows]


def _grace_window_ends_at(session_doc, policy: dict):
	slot_end = None
	if session_doc.timetable_slot:
		slot_end = frappe.db.get_value("Timetable Slot", session_doc.timetable_slot, "end_time")

	session_end_time = slot_end or time(23, 59, 59)
	session_end = datetime.combine(getdate(session_doc.scheduled_date), session_end_time)
	return session_end + timedelta(hours=policy["grace_window_hours"])


def _programme_for_course_offering(course_offering: str):
	return frappe.db.sql(
		"""
		select p.name
		from `tabCourse Offering` co
		inner join `tabCohort` ch on ch.name = co.cohort
		inner join `tabProgramme` p on p.name = ch.programme
		where co.name = %s
		""",
		course_offering,
	)[0][0]


def _get_or_create_session(course_offering: str, date: str):
	existing = frappe.db.get_value(
		"Class Session",
		{
			"course_offering": course_offering,
			"scheduled_date": date,
			"status": ["not in", ["Cancelled", "Rescheduled"]],
		},
		"name",
	)
	if existing:
		return frappe.get_doc("Class Session", existing)

	slot = frappe.db.get_value(
		"Timetable Slot",
		{"course_offering": course_offering, "is_active": 1},
		"name",
	)

	session = frappe.get_doc(
		{
			"doctype": "Class Session",
			"course_offering": course_offering,
			"scheduled_date": date,
			"timetable_slot": slot,
			"is_adhoc": 0 if slot else 1,
			"status": "Scheduled",
		}
	)

	for student in _enrolled_students(course_offering):
		session.append("students", {"student": student, "status": "Present"})

	session.insert(ignore_permissions=True)
	frappe.db.commit()
	return session


@frappe.whitelist()
def get_session(course_offering: str, date: str):
	lecturer = _current_lecturer()
	_assert_lecturer_assigned(course_offering, lecturer)

	session = _get_or_create_session(course_offering, date)
	policy = get_policy(_programme_for_course_offering(course_offering))

	students = frappe.db.get_all(
		"Student", filters={"name": ["in", [r.student for r in session.students]]},
		fields=["name as student", "student_name"],
	)
	names_by_id = {s.student: s.student_name for s in students}

	return {
		"class_session": session.name,
		"status": session.status,
		"course_offering": course_offering,
		"scheduled_date": str(session.scheduled_date),
		"grace_window_ends_at": str(_grace_window_ends_at(session, policy)),
		"students": [
			{
				"student": row.student,
				"student_name": names_by_id.get(row.student, row.student),
				"status": row.status,
				"marked_at": str(row.marked_at) if row.marked_at else None,
			}
			for row in session.students
		],
	}


@frappe.whitelist()
def submit(class_session: str, rows, client_marked_at: str = None):
	"""rows: list of {student, status} for rows that changed from the
	roster's default (Present). Idempotent — re-submitting the same payload
	upserts, never duplicates or double-counts."""
	if isinstance(rows, str):
		rows = frappe.parse_json(rows)

	session = frappe.get_doc("Class Session", class_session)
	lecturer = _current_lecturer()
	_assert_lecturer_assigned(session.course_offering, lecturer)

	policy = get_policy(_programme_for_course_offering(session.course_offering))
	grace_ends = _grace_window_ends_at(session, policy)
	is_edit_after_submit = session.docstatus == 1

	if is_edit_after_submit and now_datetime() > grace_ends:
		frappe.throw(
			"This session's grace window has passed — use request_correction instead of "
			"editing directly.",
			frappe.ValidationError,
		)

	enrolled = set(_enrolled_students(session.course_offering))
	marked_at = get_datetime(client_marked_at) if client_marked_at else now_datetime()

	by_student = {row.student: row for row in session.students}
	for item in rows:
		student = item.get("student")
		status = item.get("status")
		if student not in enrolled:
			frappe.throw(f"Student {student} is not enrolled in this Course Offering")
		if status not in ("Present", "Absent", "Late", "Excused"):
			frappe.throw(f"Invalid status {status!r} for student {student}")

		row = by_student.get(student)
		if not row:
			row = session.append("students", {"student": student})
			by_student[student] = row
		row.status = status
		row.marked_by = frappe.session.user
		row.marked_at = marked_at
		row.method = "Manual"

	if is_edit_after_submit:
		session.flags.ignore_validate_update_after_submit = True
		session.save(ignore_permissions=False)
	elif session.docstatus == 0:
		session.save(ignore_permissions=False)
		session.submit()

	frappe.db.commit()
	return get_session(session.course_offering, str(session.scheduled_date))


@frappe.whitelist()
def request_correction(class_session: str, student: str, requested_status: str, reason: str):
	session = frappe.get_doc("Class Session", class_session)
	lecturer = _current_lecturer()
	_assert_lecturer_assigned(session.course_offering, lecturer)

	doc = frappe.get_doc(
		{
			"doctype": "Attendance Correction Request",
			"class_session": class_session,
			"student": student,
			"requested_status": requested_status,
			"reason": reason,
		}
	).insert(ignore_permissions=False)
	frappe.db.commit()

	policy = get_policy(_programme_for_course_offering(session.course_offering))
	return {
		"correction_request": doc.name,
		"approval_status": doc.approval_status,
		"requires_approval": policy["correction_requires_approval"],
	}
