import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime


class ClassSession(Document):
	def validate(self):
		self._guard_lecturer_scope()
		self._prevent_duplicate_active_session()

	def _guard_lecturer_scope(self):
		"""Belt-and-suspenders check ahead of the real permission-query-condition
		hooks landing in Phase 4 (see hooks.py). Without this, any user with the
		bare Lecturer role could write a Class Session for a course they are not
		assigned to, because the doctype-level permission grants Lecturer write
		access to the whole doctype — the fine-grained scoping isn't wired up
		yet. Do not remove this once Phase 4 lands; it becomes a second layer,
		not a replacement — SPEC.md requires every leak path to be independently
		guarded."""
		roles = frappe.get_roles()
		privileged = {"System Manager", "Registry", "HOD", "Programme Coordinator", "College Administrator"}
		if privileged & set(roles):
			return
		if "Lecturer" not in roles:
			return

		lecturer = frappe.db.get_value("Lecturer", {"user": frappe.session.user}, "name")
		if not lecturer:
			frappe.throw("No Lecturer record is linked to your user account", frappe.PermissionError)

		assigned = frappe.db.exists(
			"Course Offering Lecturer",
			{"parent": self.course_offering, "lecturer": lecturer},
		)
		if not assigned:
			frappe.throw(
				"You are not assigned to this Course Offering's lecturer list",
				frappe.PermissionError,
			)

	def _prevent_duplicate_active_session(self):
		if self.is_adhoc:
			return
		duplicate = frappe.db.exists(
			"Class Session",
			{
				"course_offering": self.course_offering,
				"scheduled_date": self.scheduled_date,
				"status": ["not in", ["Cancelled", "Rescheduled"]],
				"name": ["!=", self.name],
			},
		)
		if duplicate:
			frappe.throw(
				f"A session for this Course Offering already exists on {self.scheduled_date} "
				f"({duplicate}). Cancel or reschedule it instead of creating a second one."
			)

	def on_submit(self):
		if self.status in ("Cancelled", "Rescheduled"):
			frappe.throw(f"Cannot submit a session that is {self.status}")
		self.status = "Submitted"
		if not self.submitted_by:
			self.submitted_by = frappe.session.user
		if not self.submitted_at:
			self.submitted_at = now_datetime()

	@frappe.whitelist()
	def cancel_session(self, reason: str):
		"""A cancelled session is a real, visible record — distinguishable from
		a session nobody got around to marking. Never delete a Class Session
		to represent a class that didn't happen."""
		if self.docstatus == 1:
			frappe.throw("Cannot cancel a session that has already been submitted")
		if not reason or not reason.strip():
			frappe.throw("A cancellation reason is required")
		self.status = "Cancelled"
		self.cancellation_reason = reason.strip()
		self.save(ignore_permissions=False)

	@frappe.whitelist()
	def reschedule_session(self, new_date: str, reason: str, new_timetable_slot: str = None):
		"""Marks this session Rescheduled and creates a new ad-hoc session on
		new_date carrying the same course_offering and roster expectations.
		The original stays in place, pointed at the replacement via
		rescheduled_to — both records remain queryable, nothing is overwritten."""
		if self.docstatus == 1:
			frappe.throw("Cannot reschedule a session that has already been submitted")
		if not reason or not reason.strip():
			frappe.throw("A reschedule reason is required")

		new_session = frappe.get_doc(
			{
				"doctype": "Class Session",
				"course_offering": self.course_offering,
				"scheduled_date": new_date,
				"timetable_slot": new_timetable_slot or self.timetable_slot,
				"is_adhoc": 1,
				"status": "Scheduled",
			}
		).insert(ignore_permissions=False)

		self.status = "Rescheduled"
		self.cancellation_reason = reason.strip()
		self.rescheduled_to = new_session.name
		self.save(ignore_permissions=False)

		return new_session.name
