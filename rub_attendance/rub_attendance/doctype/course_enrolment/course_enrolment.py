import frappe
from frappe.model.document import Document


class CourseEnrolment(Document):
	def validate(self):
		if self.enrolment_status == "Active":
			duplicate = frappe.db.exists(
				"Course Enrolment",
				{
					"student": self.student,
					"course_offering": self.course_offering,
					"enrolment_status": "Active",
					"name": ["!=", self.name],
				},
			)
			if duplicate:
				frappe.throw(
					"This student already has an active enrolment in this course offering"
				)
