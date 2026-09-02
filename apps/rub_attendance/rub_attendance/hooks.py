app_name = "rub_attendance"
app_title = "RUB Attendance"
app_publisher = "Sherubtse College ICT"
app_description = "Standalone attendance system for the RUB Sherubtse College pilot"
app_email = "claude3.sherubtse@rub.edu.bt"
app_license = "mit"

# Roles, once created via the Desk UI or migrated in from fixtures, are kept in sync here.
fixtures = [
	{"doctype": "Role", "filters": [["role_name", "in", [
		"RUB Academic Administrator",
		"College Administrator",
		"HOD",
		"Programme Coordinator",
		"Lecturer",
		"Student",
		"Registry",
	]]]},
]

# College-level isolation needs no entry here — every doctype carries a
# direct `college` Link field, so Frappe's native User Permission mechanism
# filters it automatically. These hooks add the narrower-than-college
# scoping (department/programme/lecturer-assignment) that Frappe can't
# derive on its own. See rub_attendance/permissions.py and
# phase0/05-permission-matrix.md.
permission_query_conditions = {
	"Student": "rub_attendance.permissions.student_query_conditions",
	"Cohort": "rub_attendance.permissions.cohort_query_conditions",
	"Course Offering": "rub_attendance.permissions.course_offering_query_conditions",
	"Course Enrolment": "rub_attendance.permissions.course_enrolment_query_conditions",
	"Class Session": "rub_attendance.permissions.class_session_query_conditions",
	"Attendance Summary": "rub_attendance.permissions.attendance_summary_query_conditions",
}

has_permission = {
	"Student": "rub_attendance.permissions.student_has_permission",
	"Course Offering": "rub_attendance.permissions.course_offering_has_permission",
	"Class Session": "rub_attendance.permissions.class_session_has_permission",
}

# Safety-net rebuild — the primary update path is rebuild_summary/
# rebuild_all_for_session called directly from Class Session's on_submit
# and Attendance Correction Request's approval (see those files). This
# nightly run only catches drift from something those two missed.
scheduler_events = {
	"daily": [
		"rub_attendance.rub_attendance.doctype.attendance_summary.attendance_summary.rebuild_all",
	],
}
