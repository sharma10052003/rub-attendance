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

# Phase 4 will add permission query condition hooks here, per
# phase0/05-permission-matrix.md, once the isolation test suite exists to
# verify them. Not added yet — do not scope-creep Phase 1 into Phase 4.
