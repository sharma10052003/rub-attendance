import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime


class AttendanceDispute(Document):
	def validate(self):
		if not self.is_new():
			return

		row_exists = frappe.db.exists(
			"Class Session Student", {"parent": self.class_session, "student": self.student}
		)
		if not row_exists:
			frappe.throw(
				f"Student {self.student} has no attendance row on session {self.class_session} "
				f"— nothing to dispute"
			)

		self.status = "Open"
		self.raised_at = now_datetime()
		if not self.assigned_to:
			self.assigned_to = _department_hod(self.class_session)

	@frappe.whitelist()
	def resolve(self, resolution_note: str, new_status: str = "Resolved"):
		if self.status == "Resolved":
			frappe.throw("This dispute is already resolved")
		if new_status not in ("Under Review", "Resolved"):
			frappe.throw(f"Invalid status {new_status!r}")

		privileged = {"System Manager", "Registry"}
		is_assigned_reviewer = self.assigned_to and self.assigned_to == frappe.session.user
		if not (privileged & set(frappe.get_roles())) and not is_assigned_reviewer:
			frappe.throw(
				"Only the assigned reviewer (or Registry/System Manager) may act on this dispute",
				frappe.PermissionError,
			)

		self.status = new_status
		if not resolution_note or not resolution_note.strip():
			frappe.throw("A resolution note is required")
		self.resolution_note = resolution_note.strip()
		if new_status == "Resolved":
			self.resolved_at = now_datetime()
		self.save(ignore_permissions=True)
		frappe.db.commit()
		return self.status


def _department_hod(class_session: str):
	rows = frappe.db.sql(
		"""
		select d.hod_user
		from `tabClass Session` cs
		inner join `tabCourse Offering` co on co.name = cs.course_offering
		inner join `tabCohort` ch on ch.name = co.cohort
		inner join `tabProgramme` p on p.name = ch.programme
		inner join `tabDepartment` d on d.name = p.department
		where cs.name = %s
		""",
		class_session,
	)
	return rows[0][0] if rows and rows[0][0] else None
