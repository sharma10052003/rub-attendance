import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime


class AttendanceCorrectionRequest(Document):
	def validate(self):
		if not self.is_new():
			return

		self.requested_by = frappe.session.user
		self.requested_at = now_datetime()

		row = _get_session_student_row(self.class_session, self.student)
		if not row:
			frappe.throw(
				f"Student {self.student} is not on the roster for session {self.class_session}"
			)
		self.original_status = row.status

		if self.original_status == self.requested_status:
			frappe.throw("Requested Status is the same as the current status — nothing to correct")

	@frappe.whitelist()
	def decide(self, approve: bool, note: str = None):
		if self.approval_status != "Pending":
			frappe.throw(f"This request was already {self.approval_status.lower()}")

		department = _get_department_for_class_session(self.class_session)
		hod_user = frappe.db.get_value("Department", department, "hod_user") if department else None

		privileged = {"System Manager", "Registry"}
		is_hod_of_department = hod_user and hod_user == frappe.session.user
		if not (privileged & set(frappe.get_roles())) and not is_hod_of_department:
			frappe.throw(
				"Only the HOD of this session's department (or Registry/System Manager) "
				"may approve or reject a correction request",
				frappe.PermissionError,
			)

		self.approval_status = "Approved" if approve else "Rejected"
		self.approved_by = frappe.session.user
		self.approved_at = now_datetime()
		if note:
			self.add_comment("Comment", note)
		self.save(ignore_permissions=True)

		if approve:
			_apply_correction(self.class_session, self.student, self.requested_status, self.name)

		return self.approval_status


def _get_session_student_row(class_session: str, student: str):
	session = frappe.get_doc("Class Session", class_session)
	for row in session.students:
		if row.student == student:
			return row
	return None


def _get_department_for_class_session(class_session: str):
	return frappe.db.sql(
		"""
		select d.name
		from `tabClass Session` cs
		inner join `tabCourse Offering` co on co.name = cs.course_offering
		inner join `tabCohort` ch on ch.name = co.cohort
		inner join `tabProgramme` p on p.name = ch.programme
		inner join `tabDepartment` d on d.name = p.department
		where cs.name = %s
		""",
		class_session,
	)[0][0]


def _apply_correction(class_session: str, student: str, new_status: str, request_name: str):
	session = frappe.get_doc("Class Session", class_session)
	for row in session.students:
		if row.student == student:
			row.status = new_status
			break
	session.flags.ignore_validate_update_after_submit = True
	session.save(ignore_permissions=True)
	frappe.db.commit()
	session.add_comment(
		"Comment",
		f"Attendance corrected for {student} to {new_status} via approved "
		f"Attendance Correction Request {request_name}",
	)

	from rub_attendance.rub_attendance.doctype.attendance_summary.attendance_summary import (
		rebuild_summary,
	)

	rebuild_summary(student, session.course_offering)
