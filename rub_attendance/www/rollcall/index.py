import frappe


def get_context(context):
	if frappe.session.user == "Guest":
		frappe.local.flags.redirect_location = "/login?redirect-to=/rollcall"
		raise frappe.Redirect

	lecturer = frappe.db.get_value("Lecturer", {"user": frappe.session.user}, "name")
	if not lecturer:
		context.no_lecturer_record = True
		context.course_offerings = []
		return context

	course_offerings = frappe.db.sql(
		"""
		select co.name, co.course, c.course_title, co.session_type, ch.cohort_label
		from `tabCourse Offering Lecturer` col
		inner join `tabCourse Offering` co on co.name = col.parent
		inner join `tabCourse` c on c.name = co.course
		inner join `tabCohort` ch on ch.name = co.cohort
		where col.lecturer = %s
		order by co.modified desc
		""",
		lecturer,
		as_dict=True,
	)

	context.no_lecturer_record = False
	context.course_offerings = course_offerings
	context.csrf_token = frappe.sessions.get_csrf_token()
	context.no_cache = 1
	return context
