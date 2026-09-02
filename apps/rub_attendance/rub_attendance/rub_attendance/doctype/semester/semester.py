import frappe
from frappe.model.document import Document


class Semester(Document):
	def validate(self):
		if self.start_date and self.end_date and self.start_date >= self.end_date:
			frappe.throw("Start Date must be before End Date")

		if self.is_current:
			frappe.db.set_value(
				"Semester",
				{"is_current": 1, "name": ["!=", self.name]},
				"is_current",
				0,
			)
