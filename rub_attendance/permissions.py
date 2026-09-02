"""
Phase 4 — permission query conditions and has_permission hooks.

College-level isolation needs NO custom code here: every doctype in this
app carries a direct `college` Link field (per phase0/04-data-model.md's
"every record carries a College link from day one" rule), and Frappe
automatically filters any Link field against a user's "User Permission"
records for that target doctype. So a College Administrator restricted via
one User Permission row on College sees only their college everywhere,
for free. See phase4/00-setup-and-verification.md for how to create that
User Permission record — it's configuration, not code.

What Frappe's native mechanism does NOT do is narrower-than-college scoping
(HOD -> own department, Programme Coordinator -> own programme, Lecturer ->
own assigned offerings), because Student/Cohort/Course Offering/Course
Enrolment/Class Session don't carry a direct Department or Programme
Coordinator field to restrict against. That's what the functions below add.

Every query-condition function has a matching has_permission function,
because a permission query condition only filters LIST/REPORT views — it
does nothing to stop `frappe.get_doc()` or a direct
`/api/resource/<Doctype>/<name>` GET for a single record by name. Both need
guarding independently, per SPEC.md's "three leak paths" rule.
"""

import frappe

# Deliberately does NOT include "RUB Academic Administrator". Per
# phase0/05-permission-matrix.md, that role sees aggregates only — opening
# an individual student's record requires a stated reason, logged (see
# rub_attendance/api/audit.py). None of the doctypes below grant that role
# direct read access at the DocType-permission level either (check the
# .json files) — the only sanctioned path to one student's raw detail is
# the logged whitelisted method, never Desk or /api/resource directly.
GLOBAL_READ_ROLES = {"System Manager", "Registry"}


def _no_restriction():
	return ""


def _roles(user):
	return set(frappe.get_roles(user))


def _has_any(roles, wanted):
	return bool(roles & wanted)


# ---------------------------------------------------------------------------
# Student
# ---------------------------------------------------------------------------


def student_query_conditions(user):
	user = user or frappe.session.user
	if user == "Administrator":
		return _no_restriction()

	roles = _roles(user)
	if _has_any(roles, GLOBAL_READ_ROLES):
		return _no_restriction()
	if "College Administrator" in roles:
		return _no_restriction()  # native User Permission on `college` already scopes this

	if "HOD" in roles:
		return f"""`tabStudent`.cohort in (
			select ch.name from `tabCohort` ch
			inner join `tabProgramme` p on p.name = ch.programme
			inner join `tabDepartment` d on d.name = p.department
			where d.hod_user = {frappe.db.escape(user)}
		)"""

	if "Programme Coordinator" in roles:
		return f"""`tabStudent`.cohort in (
			select ch.name from `tabCohort` ch
			inner join `tabProgramme` p on p.name = ch.programme
			where p.coordinator_user = {frappe.db.escape(user)}
		)"""

	if "Lecturer" in roles:
		return f"""`tabStudent`.name in (
			select ce.student from `tabCourse Enrolment` ce
			inner join `tabCourse Offering` co on co.name = ce.course_offering
			inner join `tabCourse Offering Lecturer` col on col.parent = co.name
			inner join `tabLecturer` l on l.name = col.lecturer
			where l.user = {frappe.db.escape(user)} and ce.enrolment_status = 'Active'
		)"""

	# Student role, or any role with no defined scope: no Desk-level list
	# access. Self-service goes through the whitelisted student portal API
	# (Phase 5), which resolves the caller's own record server-side instead
	# of relying on Desk/report permissions.
	return "1=0"


def student_has_permission(doc, user, permission_type=None):
	user = user or frappe.session.user
	if user == "Administrator":
		return True

	roles = _roles(user)
	if _has_any(roles, GLOBAL_READ_ROLES) or "College Administrator" in roles:
		return True

	if "HOD" in roles:
		return bool(
			frappe.db.sql(
				"""
				select 1 from `tabCohort` ch
				inner join `tabProgramme` p on p.name = ch.programme
				inner join `tabDepartment` d on d.name = p.department
				where ch.name = %s and d.hod_user = %s
				""",
				(doc.cohort, user),
			)
		)

	if "Programme Coordinator" in roles:
		return bool(
			frappe.db.sql(
				"""
				select 1 from `tabCohort` ch
				inner join `tabProgramme` p on p.name = ch.programme
				where ch.name = %s and p.coordinator_user = %s
				""",
				(doc.cohort, user),
			)
		)

	if "Lecturer" in roles:
		return bool(
			frappe.db.sql(
				"""
				select 1 from `tabCourse Enrolment` ce
				inner join `tabCourse Offering` co on co.name = ce.course_offering
				inner join `tabCourse Offering Lecturer` col on col.parent = co.name
				inner join `tabLecturer` l on l.name = col.lecturer
				where ce.student = %s and l.user = %s and ce.enrolment_status = 'Active'
				""",
				(doc.name, user),
			)
		)

	return False


# ---------------------------------------------------------------------------
# Cohort
# ---------------------------------------------------------------------------


def cohort_query_conditions(user):
	user = user or frappe.session.user
	if user == "Administrator":
		return _no_restriction()

	roles = _roles(user)
	if _has_any(roles, GLOBAL_READ_ROLES) or "College Administrator" in roles:
		return _no_restriction()

	if "HOD" in roles:
		return f"""`tabCohort`.programme in (
			select p.name from `tabProgramme` p
			inner join `tabDepartment` d on d.name = p.department
			where d.hod_user = {frappe.db.escape(user)}
		)"""

	if "Programme Coordinator" in roles:
		return f"`tabCohort`.programme in (select name from `tabProgramme` where coordinator_user = {frappe.db.escape(user)})"

	if "Lecturer" in roles:
		return f"""`tabCohort`.name in (
			select co.cohort from `tabCourse Offering` co
			inner join `tabCourse Offering Lecturer` col on col.parent = co.name
			inner join `tabLecturer` l on l.name = col.lecturer
			where l.user = {frappe.db.escape(user)}
		)"""

	return "1=0"


# ---------------------------------------------------------------------------
# Course Offering
# ---------------------------------------------------------------------------


def course_offering_query_conditions(user):
	user = user or frappe.session.user
	if user == "Administrator":
		return _no_restriction()

	roles = _roles(user)
	if _has_any(roles, GLOBAL_READ_ROLES) or "College Administrator" in roles:
		return _no_restriction()

	if "HOD" in roles:
		return f"""`tabCourse Offering`.cohort in (
			select ch.name from `tabCohort` ch
			inner join `tabProgramme` p on p.name = ch.programme
			inner join `tabDepartment` d on d.name = p.department
			where d.hod_user = {frappe.db.escape(user)}
		)"""

	if "Programme Coordinator" in roles:
		return f"""`tabCourse Offering`.cohort in (
			select ch.name from `tabCohort` ch
			inner join `tabProgramme` p on p.name = ch.programme
			where p.coordinator_user = {frappe.db.escape(user)}
		)"""

	if "Lecturer" in roles:
		return f"""`tabCourse Offering`.name in (
			select col.parent from `tabCourse Offering Lecturer` col
			inner join `tabLecturer` l on l.name = col.lecturer
			where l.user = {frappe.db.escape(user)}
		)"""

	return "1=0"


def course_offering_has_permission(doc, user, permission_type=None):
	user = user or frappe.session.user
	if user == "Administrator":
		return True
	roles = _roles(user)
	if _has_any(roles, GLOBAL_READ_ROLES) or "College Administrator" in roles:
		return True
	if "Lecturer" in roles:
		return bool(
			frappe.db.exists(
				"Course Offering Lecturer",
				{"parent": doc.name, "lecturer": frappe.db.get_value("Lecturer", {"user": user}, "name")},
			)
		)
	if "HOD" in roles or "Programme Coordinator" in roles:
		condition_field = "d.hod_user" if "HOD" in roles else "p.coordinator_user"
		return bool(
			frappe.db.sql(
				f"""
				select 1 from `tabCohort` ch
				inner join `tabProgramme` p on p.name = ch.programme
				inner join `tabDepartment` d on d.name = p.department
				where ch.name = %s and {condition_field} = %s
				""",
				(doc.cohort, user),
			)
		)
	return False


# ---------------------------------------------------------------------------
# Attendance Summary
# ---------------------------------------------------------------------------


def attendance_summary_query_conditions(user):
	user = user or frappe.session.user
	if user == "Administrator":
		return _no_restriction()

	roles = _roles(user)
	if _has_any(roles, GLOBAL_READ_ROLES) or "College Administrator" in roles:
		return _no_restriction()
	if "RUB Academic Administrator" in roles:
		return _no_restriction()  # aggregates only — this doctype IS the aggregate, so this is fine

	if "HOD" in roles:
		return f"""`tabAttendance Summary`.course_offering in (
			select co.name from `tabCourse Offering` co
			inner join `tabCohort` ch on ch.name = co.cohort
			inner join `tabProgramme` p on p.name = ch.programme
			inner join `tabDepartment` d on d.name = p.department
			where d.hod_user = {frappe.db.escape(user)}
		)"""

	if "Programme Coordinator" in roles:
		return f"""`tabAttendance Summary`.course_offering in (
			select co.name from `tabCourse Offering` co
			inner join `tabCohort` ch on ch.name = co.cohort
			inner join `tabProgramme` p on p.name = ch.programme
			where p.coordinator_user = {frappe.db.escape(user)}
		)"""

	if "Lecturer" in roles:
		return f"""`tabAttendance Summary`.course_offering in (
			select col.parent from `tabCourse Offering Lecturer` col
			inner join `tabLecturer` l on l.name = col.lecturer
			where l.user = {frappe.db.escape(user)}
		)"""

	# Student role: self-view goes through the whitelisted student portal
	# API (get_my_attendance), which resolves the caller's own Student
	# record server-side — not through Desk/report access to this doctype.
	return "1=0"


# ---------------------------------------------------------------------------
# Course Enrolment
# ---------------------------------------------------------------------------


def course_enrolment_query_conditions(user):
	user = user or frappe.session.user
	if user == "Administrator":
		return _no_restriction()

	roles = _roles(user)
	if _has_any(roles, GLOBAL_READ_ROLES) or "College Administrator" in roles:
		return _no_restriction()

	if "HOD" in roles:
		return f"""`tabCourse Enrolment`.course_offering in (
			select co.name from `tabCourse Offering` co
			inner join `tabCohort` ch on ch.name = co.cohort
			inner join `tabProgramme` p on p.name = ch.programme
			inner join `tabDepartment` d on d.name = p.department
			where d.hod_user = {frappe.db.escape(user)}
		)"""

	if "Programme Coordinator" in roles:
		return f"""`tabCourse Enrolment`.course_offering in (
			select co.name from `tabCourse Offering` co
			inner join `tabCohort` ch on ch.name = co.cohort
			inner join `tabProgramme` p on p.name = ch.programme
			where p.coordinator_user = {frappe.db.escape(user)}
		)"""

	if "Lecturer" in roles:
		return f"""`tabCourse Enrolment`.course_offering in (
			select col.parent from `tabCourse Offering Lecturer` col
			inner join `tabLecturer` l on l.name = col.lecturer
			where l.user = {frappe.db.escape(user)}
		)"""

	return "1=0"


# ---------------------------------------------------------------------------
# Class Session (read-side; write-side already guarded in class_session.py)
# ---------------------------------------------------------------------------


def class_session_query_conditions(user):
	user = user or frappe.session.user
	if user == "Administrator":
		return _no_restriction()

	roles = _roles(user)
	if _has_any(roles, GLOBAL_READ_ROLES) or "College Administrator" in roles:
		return _no_restriction()

	if "HOD" in roles:
		return f"""`tabClass Session`.course_offering in (
			select co.name from `tabCourse Offering` co
			inner join `tabCohort` ch on ch.name = co.cohort
			inner join `tabProgramme` p on p.name = ch.programme
			inner join `tabDepartment` d on d.name = p.department
			where d.hod_user = {frappe.db.escape(user)}
		)"""

	if "Programme Coordinator" in roles:
		return f"""`tabClass Session`.course_offering in (
			select co.name from `tabCourse Offering` co
			inner join `tabCohort` ch on ch.name = co.cohort
			inner join `tabProgramme` p on p.name = ch.programme
			where p.coordinator_user = {frappe.db.escape(user)}
		)"""

	if "Lecturer" in roles:
		return f"""`tabClass Session`.course_offering in (
			select col.parent from `tabCourse Offering Lecturer` col
			inner join `tabLecturer` l on l.name = col.lecturer
			where l.user = {frappe.db.escape(user)}
		)"""

	return "1=0"


def class_session_has_permission(doc, user, permission_type=None):
	user = user or frappe.session.user
	if user == "Administrator":
		return True
	roles = _roles(user)
	if _has_any(roles, GLOBAL_READ_ROLES) or "College Administrator" in roles:
		return True
	if "Lecturer" in roles:
		lecturer = frappe.db.get_value("Lecturer", {"user": user}, "name")
		return bool(
			lecturer
			and frappe.db.exists(
				"Course Offering Lecturer", {"parent": doc.course_offering, "lecturer": lecturer}
			)
		)
	if "HOD" in roles or "Programme Coordinator" in roles:
		condition_field = "d.hod_user" if "HOD" in roles else "p.coordinator_user"
		return bool(
			frappe.db.sql(
				f"""
				select 1 from `tabCourse Offering` co
				inner join `tabCohort` ch on ch.name = co.cohort
				inner join `tabProgramme` p on p.name = ch.programme
				inner join `tabDepartment` d on d.name = p.department
				where co.name = %s and {condition_field} = %s
				""",
				(doc.course_offering, user),
			)
		)
	return False
