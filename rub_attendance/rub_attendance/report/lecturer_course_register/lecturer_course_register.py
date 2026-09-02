"""
A lecturer's own course register: every session in a Course Offering, its
attendance counts, and whether it's overdue for marking. Also usable by
HOD/Programme Coordinator/Registry/System Manager for any offering they
have permission to see — row-level scoping comes from
rub_attendance.permissions.class_session_query_conditions via
frappe.get_list, not from anything in this file, so the same isolation
rules from Phase 4 apply here automatically.
"""

import frappe
from frappe.utils import getdate, nowdate


def get_columns():
	return [
		{"fieldname": "scheduled_date", "label": "Date", "fieldtype": "Date", "width": 100},
		{"fieldname": "status", "label": "Status", "fieldtype": "Data", "width": 100},
		{"fieldname": "present_count", "label": "Present", "fieldtype": "Int", "width": 80},
		{"fieldname": "absent_count", "label": "Absent", "fieldtype": "Int", "width": 80},
		{"fieldname": "late_count", "label": "Late", "fieldtype": "Int", "width": 80},
		{"fieldname": "excused_count", "label": "Excused", "fieldtype": "Int", "width": 80},
		{"fieldname": "submitted_at", "label": "Submitted At", "fieldtype": "Datetime", "width": 160},
		{"fieldname": "overdue", "label": "Overdue — Not Yet Marked", "fieldtype": "Data", "width": 180},
		{"fieldname": "class_session", "label": "Session", "fieldtype": "Link", "options": "Class Session", "width": 120},
	]


def get_data(filters):
	conditions = {}
	if filters.get("course_offering"):
		conditions["course_offering"] = filters["course_offering"]
	if filters.get("from_date") and filters.get("to_date"):
		conditions["scheduled_date"] = ["between", [filters["from_date"], filters["to_date"]]]
	elif filters.get("from_date"):
		conditions["scheduled_date"] = [">=", filters["from_date"]]
	elif filters.get("to_date"):
		conditions["scheduled_date"] = ["<=", filters["to_date"]]

	sessions = frappe.get_list(
		"Class Session",
		filters=conditions,
		fields=["name", "scheduled_date", "status", "submitted_at"],
		order_by="scheduled_date desc",
	)

	today = getdate(nowdate())
	rows = []
	for session in sessions:
		counts = frappe.db.get_all(
			"Class Session Student",
			filters={"parent": session.name},
			fields=["status", "count(name) as n"],
			group_by="status",
		)
		by_status = {c.status: c.n for c in counts}

		overdue = ""
		if session.status in ("Scheduled", "Open") and getdate(session.scheduled_date) < today:
			overdue = "Yes — past date, still not submitted"

		rows.append(
			{
				"class_session": session.name,
				"scheduled_date": session.scheduled_date,
				"status": session.status,
				"present_count": by_status.get("Present", 0),
				"absent_count": by_status.get("Absent", 0),
				"late_count": by_status.get("Late", 0),
				"excused_count": by_status.get("Excused", 0),
				"submitted_at": session.submitted_at,
				"overdue": overdue,
			}
		)
	return rows


def execute(filters=None):
	filters = filters or {}
	if not filters.get("course_offering"):
		frappe.msgprint("Pick a Course Offering to see its register.")
		return get_columns(), []
	return get_columns(), get_data(filters)
