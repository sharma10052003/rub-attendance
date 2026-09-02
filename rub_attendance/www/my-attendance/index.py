import frappe


def get_context(context):
	if frappe.session.user == "Guest":
		frappe.local.flags.redirect_location = "/login?redirect-to=/my-attendance"
		raise frappe.Redirect

	student = frappe.db.get_value("Student", {"user": frappe.session.user}, ["name", "student_name"], as_dict=True)
	context.no_student_record = student is None
	context.student = student
	context.csrf_token = frappe.sessions.get_csrf_token()
	context.no_cache = 1
	return context
