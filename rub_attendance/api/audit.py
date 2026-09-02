"""
The one sanctioned path for a university-level role to see one student's
individual record. Per phase0/05-permission-matrix.md: "University-level
roles see aggregates by default. Opening any individual student's record
requires a stated reason and is written to the audit log." No doctype in
this app grants RUB Academic Administrator direct read on Student — this
is the only door, and it's logged every time it's used.
"""

import frappe
from frappe.utils import now_datetime

ALLOWED_ROLES = {"RUB Academic Administrator", "System Manager"}


@frappe.whitelist()
def view_student_record(student: str, reason: str):
	if not (ALLOWED_ROLES & set(frappe.get_roles())):
		frappe.throw("Not permitted", frappe.PermissionError)
	if not reason or not reason.strip():
		frappe.throw("A reason is required to open an individual student record")

	frappe.get_doc(
		{
			"doctype": "Audit Log",
			"accessed_by": frappe.session.user,
			"student": student,
			"reason": reason.strip(),
			"accessed_at": now_datetime(),
		}
	).insert(ignore_permissions=True)
	frappe.db.commit()

	return frappe.get_doc("Student", student).as_dict()
