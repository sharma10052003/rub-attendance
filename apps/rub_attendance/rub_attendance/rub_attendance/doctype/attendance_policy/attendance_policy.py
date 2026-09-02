import frappe
from frappe.model.document import Document


class AttendancePolicy(Document):
	def validate(self):
		duplicate = frappe.db.exists(
			"Attendance Policy",
			{"programme": self.programme, "name": ["!=", self.name]},
		)
		if duplicate:
			label = self.programme or "the college-wide default"
			frappe.throw(f"An Attendance Policy already exists for {label}")


def get_policy(programme: str = None) -> dict:
	"""Resolve the effective policy for a programme: a programme-specific row
	if one exists, else the blank/default row. Callers must never hard-code
	minimum_percentage, grace_window_hours, or correction_requires_approval —
	always come through here."""
	policy_name = None
	if programme:
		policy_name = frappe.db.get_value("Attendance Policy", {"programme": programme})
	if not policy_name:
		policy_name = frappe.db.get_value("Attendance Policy", {"programme": ["is", "not set"]})

	if not policy_name:
		frappe.throw(
			"No Attendance Policy is configured (neither a programme-specific row nor a "
			"college-wide default). Create one in Desk before using attendance features — "
			"this is a deliberate hard stop, not a silent hard-coded fallback."
		)

	doc = frappe.get_doc("Attendance Policy", policy_name)
	return {
		"policy": doc.name,
		"minimum_percentage": doc.minimum_percentage,
		"late_counts_as": doc.late_counts_as,
		"grace_window_hours": doc.grace_window_hours,
		"correction_requires_approval": bool(doc.correction_requires_approval),
	}
