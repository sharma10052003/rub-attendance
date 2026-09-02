"""
HOD's programme summary and at-risk list. Row-level scoping is
rub_attendance.permissions.attendance_summary_query_conditions via
frappe.get_list — an HOD only ever sees their own department's course
offerings here, automatically. Tick "Only Below Threshold" for the
at-risk list; leave it off for the full programme summary.
"""

import frappe


def get_columns():
	return [
		{"fieldname": "student", "label": "Student ID", "fieldtype": "Link", "options": "Student", "width": 110},
		{"fieldname": "student_name", "label": "Student Name", "fieldtype": "Data", "width": 160},
		{"fieldname": "course_title", "label": "Course", "fieldtype": "Data", "width": 180},
		{"fieldname": "sessions_held", "label": "Sessions Held", "fieldtype": "Int", "width": 100},
		{"fieldname": "percentage", "label": "Attendance %", "fieldtype": "Percent", "width": 110},
		{"fieldname": "below_threshold", "label": "Below Threshold", "fieldtype": "Check", "width": 110},
	]


def get_data(filters):
	conditions = {}
	if filters.get("semester"):
		conditions["semester"] = filters["semester"]
	if filters.get("only_below_threshold"):
		conditions["below_threshold"] = 1

	rows = frappe.get_list(
		"Attendance Summary",
		filters=conditions,
		fields=[
			"student",
			"student.student_name as student_name",
			"course_offering",
			"sessions_held",
			"percentage",
			"below_threshold",
		],
		order_by="percentage asc",
	)

	course_titles = {}
	for row in rows:
		if row.course_offering not in course_titles:
			course = frappe.db.get_value("Course Offering", row.course_offering, "course")
			course_titles[row.course_offering] = frappe.db.get_value("Course", course, "course_title")
		row["course_title"] = course_titles[row.course_offering]

	return rows


def execute(filters=None):
	filters = filters or {}
	return get_columns(), get_data(filters)
