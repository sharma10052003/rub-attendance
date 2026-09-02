import frappe
from frappe.model.document import Document


class TimetableSlot(Document):
	def validate(self):
		if self.start_time and self.end_time and self.start_time >= self.end_time:
			frappe.throw("Start Time must be before End Time")
