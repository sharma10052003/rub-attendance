import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime


class ExcusedAbsence(Document):
	def validate(self):
		if self.is_new():
			self.recorded_by = frappe.session.user
			self.recorded_at = now_datetime()
