import frappe
from frappe.model.document import Document


class Department(Document):
	def validate(self):
		duplicate = frappe.db.exists(
			"Department",
			{
				"college": self.college,
				"department_code": self.department_code,
				"name": ["!=", self.name],
			},
		)
		if duplicate:
			frappe.throw(
				f"Department code {self.department_code} already exists for this college"
			)
