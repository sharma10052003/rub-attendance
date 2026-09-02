"""
Student self-view / dispute API, per phase0/06-api-contract.md. Every
method resolves the caller's own Student record from frappe.session.user —
never trusts a `student` parameter from the client. A Student's User
account is linked via Student.user (set by Registry once the student's
institutional login exists — see phase5/00-setup-and-verification.md for
why that provisioning step is manual for the pilot).
"""

import frappe

from rub_attendance.rub_attendance.doctype.attendance_policy.attendance_policy import get_policy


def _current_student():
	student = frappe.db.get_value("Student", {"user": frappe.session.user}, "name")
	if not student:
		frappe.throw(
			"No Student record is linked to your account. Ask Registry to link it.",
			frappe.PermissionError,
		)
	return student


@frappe.whitelist()
def get_my_attendance(course_offering: str = None, semester: str = None):
	student = _current_student()

	filters = {"student": student}
	if course_offering:
		filters["course_offering"] = course_offering
	if semester:
		filters["semester"] = semester

	rows = frappe.get_list(
		"Attendance Summary",
		filters=filters,
		fields=[
			"course_offering",
			"semester",
			"sessions_held",
			"present_count",
			"absent_count",
			"late_count",
			"excused_count",
			"percentage",
			"below_threshold",
		],
		ignore_permissions=True,  # scope is already student-owned via _current_student()
	)

	course_titles = {}
	for row in rows:
		if row.course_offering not in course_titles:
			course_titles[row.course_offering] = frappe.db.get_value(
				"Course",
				frappe.db.get_value("Course Offering", row.course_offering, "course"),
				"course_title",
			)
		row["course_title"] = course_titles[row.course_offering]

	return {"summary": rows}


@frappe.whitelist()
def get_my_sessions(course_offering: str):
	"""Drill-down list backing a summary row: every session's date and this
	student's status for it, so a student can see exactly which date they
	want to dispute."""
	student = _current_student()

	if not frappe.db.exists("Course Enrolment", {"student": student, "course_offering": course_offering}):
		frappe.throw("You are not enrolled in this Course Offering", frappe.PermissionError)

	rows = frappe.db.sql(
		"""
		select cs.name as class_session, cs.scheduled_date, css.status
		from `tabClass Session` cs
		inner join `tabClass Session Student` css on css.parent = cs.name
		where cs.course_offering = %s and cs.docstatus = 1 and css.student = %s
		order by cs.scheduled_date
		""",
		(course_offering, student),
		as_dict=True,
	)
	return {"sessions": rows}


@frappe.whitelist()
def raise_dispute(class_session: str, claim: str):
	student = _current_student()

	if not frappe.db.exists("Class Session Student", {"parent": class_session, "student": student}):
		frappe.throw("You have no attendance row on this session", frappe.PermissionError)

	existing_open = frappe.db.exists(
		"Attendance Dispute",
		{"class_session": class_session, "student": student, "status": ["!=", "Resolved"]},
	)
	if existing_open:
		frappe.throw("You already have an open dispute for this session")

	doc = frappe.get_doc(
		{
			"doctype": "Attendance Dispute",
			"student": student,
			"class_session": class_session,
			"claim": claim,
		}
	).insert(ignore_permissions=True)
	frappe.db.commit()

	course_offering = frappe.db.get_value("Class Session", class_session, "course_offering")
	programme = frappe.db.sql(
		"""
		select p.name from `tabCourse Offering` co
		inner join `tabCohort` ch on ch.name = co.cohort
		inner join `tabProgramme` p on p.name = ch.programme
		where co.name = %s
		""",
		course_offering,
	)
	policy = get_policy(programme[0][0] if programme else None)

	return {
		"dispute": doc.name,
		"status": doc.status,
		"assigned_to": doc.assigned_to,
		"note": (
			"A department HOD will review this."
			if doc.assigned_to
			else "No HOD is configured for this department yet — Registry has been asked to assign one."
		),
	}


@frappe.whitelist()
def get_dispute_status(dispute: str):
	student = _current_student()
	doc = frappe.get_doc("Attendance Dispute", dispute)
	if doc.student != student:
		frappe.throw("Not permitted", frappe.PermissionError)
	return {
		"dispute": doc.name,
		"status": doc.status,
		"resolution_note": doc.resolution_note,
		"resolved_at": str(doc.resolved_at) if doc.resolved_at else None,
	}
