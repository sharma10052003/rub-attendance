import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime

from rub_attendance.rub_attendance.doctype.attendance_policy.attendance_policy import get_policy


class AttendanceSummary(Document):
	pass


def compute_percentage(counts: dict, sessions_held: int, late_counts_as: str) -> float:
	"""Pure function, kept separate from rebuild_summary so the percentage
	math is testable without a database — see
	rub_attendance/tests/test_attendance_summary.py.

	ASSUMPTION, flagged rather than silently baked in — confirm against the
	real RUB/Sherubtse policy before go-live: Excused sessions are excluded
	from the denominator entirely (they don't count against the student),
	not counted as Absent and not counted as Present. A student with no
	non-excused sessions yet gets 100%, not 0% — an empty record shouldn't
	read as a red flag."""
	excused = counts.get("Excused", 0)
	countable = sessions_held - excused
	if countable <= 0:
		return 100.0
	late_as_present = late_counts_as == "Present"
	effective_present = counts.get("Present", 0) + (counts.get("Late", 0) if late_as_present else 0)
	return effective_present / countable * 100


def rebuild_summary(student: str, course_offering: str):
	"""Recompute one (student, course_offering) summary from submitted Class
	Session rows and upsert it. Called after every Class Session submit and
	every approved Attendance Correction Request — never left to the nightly
	job alone, so the student portal reflects a correction immediately."""
	rows = frappe.db.sql(
		"""
		select css.status
		from `tabClass Session` cs
		inner join `tabClass Session Student` css on css.parent = cs.name
		where cs.course_offering = %s and cs.docstatus = 1 and css.student = %s
		""",
		(course_offering, student),
		as_dict=True,
	)

	counts = {"Present": 0, "Absent": 0, "Late": 0, "Excused": 0}
	for row in rows:
		counts[row.status] = counts.get(row.status, 0) + 1
	sessions_held = len(rows)

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
	percentage = compute_percentage(counts, sessions_held, policy["late_counts_as"])

	existing = frappe.db.get_value(
		"Attendance Summary", {"student": student, "course_offering": course_offering}, "name"
	)
	values = {
		"student": student,
		"course_offering": course_offering,
		"sessions_held": sessions_held,
		"present_count": counts["Present"],
		"absent_count": counts["Absent"],
		"late_count": counts["Late"],
		"excused_count": counts["Excused"],
		"percentage": round(percentage, 2),
		"below_threshold": 1 if percentage < policy["minimum_percentage"] else 0,
		"last_rebuilt_at": now_datetime(),
	}

	if existing:
		doc = frappe.get_doc("Attendance Summary", existing)
		doc.update(values)
		doc.save(ignore_permissions=True)
	else:
		doc = frappe.get_doc({"doctype": "Attendance Summary", **values}).insert(ignore_permissions=True)

	frappe.db.commit()
	return doc.name


def rebuild_all_for_session(class_session: str):
	"""Rebuild the summary for every student on one Class Session — called
	from Class Session's on_submit hook."""
	rows = frappe.db.get_all(
		"Class Session Student", filters={"parent": class_session}, fields=["student"]
	)
	course_offering = frappe.db.get_value("Class Session", class_session, "course_offering")
	for row in rows:
		rebuild_summary(row.student, course_offering)


def rebuild_all():
	"""Scheduled safety net (see hooks.py scheduler_events) — catches any
	summary that drifted from a direct DB fix or a missed hook call. Not the
	primary update path; rebuild_summary/rebuild_all_for_session are."""
	pairs = frappe.db.sql(
		"""
		select distinct cs.course_offering, css.student
		from `tabClass Session` cs
		inner join `tabClass Session Student` css on css.parent = cs.name
		where cs.docstatus = 1
		""",
		as_dict=True,
	)
	for pair in pairs:
		rebuild_summary(pair.student, pair.course_offering)
