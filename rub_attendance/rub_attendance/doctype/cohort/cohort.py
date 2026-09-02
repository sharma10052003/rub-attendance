import frappe
from frappe.model.document import Document


class Cohort(Document):
	def validate(self):
		self.section = (self.section or "").strip().upper()

		programme_name = frappe.db.get_value("Programme", self.programme, "programme_code")
		self.cohort_label = f"{programme_name} {self.intake_year} Section {self.section}"

		duplicate = frappe.db.exists(
			"Cohort",
			{
				"programme": self.programme,
				"intake_year": self.intake_year,
				"section": self.section,
				"name": ["!=", self.name],
			},
		)
		if duplicate:
			frappe.throw(f"Cohort {self.cohort_label} already exists")
