"""
An operational report a HOD/Programme Coordinator can pull to see whether
sessions are being marked on time — deliberately NOT available to the
Lecturer role and NOT surfaced on any dashboard. SPEC.md is explicit about
why: "Lecturer Submission Rate as a headline metric is a management stick
... put it in an operational report a HOD can pull, not on a dashboard
leaderboard." Keep it that way if this report is ever extended — do not
add a Lecturer-visible version of this data.
"""

import frappe


def get_columns():
	return [
		{"fieldname": "lecturer", "label": "Lecturer", "fieldtype": "Link", "options": "Lecturer", "width": 130},
		{"fieldname": "lecturer_name", "label": "Name", "fieldtype": "Data", "width": 150},
		{"fieldname": "course_offering", "label": "Course Offering", "fieldtype": "Link", "options": "Course Offering", "width": 130},
		{"fieldname": "course_title", "label": "Course", "fieldtype": "Data", "width": 160},
		{"fieldname": "sessions_scheduled", "label": "Sessions Scheduled", "fieldtype": "Int", "width": 130},
		{"fieldname": "sessions_submitted", "label": "Sessions Submitted", "fieldtype": "Int", "width": 130},
		{"fieldname": "submission_rate", "label": "Submission Rate %", "fieldtype": "Percent", "width": 130},
	]


def get_data(filters):
	offering_conditions = {}
	if filters.get("semester"):
		offering_conditions["semester"] = filters["semester"]

	# frappe.get_list on Course Offering already applies Phase 4's isolation
	# (an HOD only sees their own department's offerings, etc).
	offerings = frappe.get_list(
		"Course Offering",
		filters=offering_conditions,
		fields=["name", "course"],
	)

	rows = []
	for offering in offerings:
		course_title = frappe.db.get_value("Course", offering.course, "course_title")
		lecturers = frappe.db.get_all(
			"Course Offering Lecturer", filters={"parent": offering.name}, fields=["lecturer"]
		)

		session_conditions = {"course_offering": offering.name, "status": ["!=", "Cancelled"]}
		if filters.get("from_date") and filters.get("to_date"):
			session_conditions["scheduled_date"] = ["between", [filters["from_date"], filters["to_date"]]]

		total = frappe.db.count("Class Session", session_conditions)
		submitted = frappe.db.count("Class Session", {**session_conditions, "status": "Submitted"})
		rate = round(submitted / total * 100, 1) if total else 0.0

		for l in lecturers:
			lecturer_name = frappe.db.get_value("Lecturer", l.lecturer, "full_name")
			rows.append(
				{
					"lecturer": l.lecturer,
					"lecturer_name": lecturer_name,
					"course_offering": offering.name,
					"course_title": course_title,
					"sessions_scheduled": total,
					"sessions_submitted": submitted,
					"submission_rate": rate,
				}
			)

	rows.sort(key=lambda r: r["submission_rate"])
	return rows


def execute(filters=None):
	filters = filters or {}
	return get_columns(), get_data(filters)
