import frappe
from frappe.model.document import Document


class Student(Document):
	def validate(self):
		self.student_id = (self.student_id or "").strip()
		self.first_name = (self.first_name or "").strip()
		self.last_name = (self.last_name or "").strip()
		self.student_name = f"{self.first_name} {self.last_name}".strip()
