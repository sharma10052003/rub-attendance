"""
Phase 2 session generator — turns a Semester's Timetable Slots into Class
Session records, skipping holidays and never duplicating a session that
already exists for a given (course_offering, date).

Usage, from a real Frappe bench:

    # Dry run first — reports what would be created, writes nothing.
    bench --site <site> execute rub_attendance.setup.generate_sessions.generate_sessions \
        --kwargs "{'semester': 'Autumn 2026', 'holiday_list': 'Sherubtse 2026', 'dry_run': True}"

    bench --site <site> execute rub_attendance.setup.generate_sessions.generate_sessions \
        --kwargs "{'semester': 'Autumn 2026', 'holiday_list': 'Sherubtse 2026', 'dry_run': False}"

Safe to re-run at any point in the semester — e.g. after adding a new
Timetable Slot mid-term — because it only ever creates a session for a
(course_offering, date) pair that doesn't already have one. It never touches
an existing Class Session, so a lecturer's edits, cancellations, or
reschedules already recorded are never overwritten by a re-run.

holiday_list is optional. Without one, no dates are skipped — every matching
weekday in the semester gets a session, including public holidays. Wire in a
real Holiday List (Frappe's built-in doctype: Setup > Holiday List) before
running this for real, per SPEC.md's requirement that the academic calendar
drive generation, not just the day-of-week pattern.
"""

from dataclasses import dataclass, field
from datetime import timedelta

import frappe

WEEKDAY_NAMES = [
	"Monday",
	"Tuesday",
	"Wednesday",
	"Thursday",
	"Friday",
	"Saturday",
	"Sunday",
]


@dataclass
class SessionGenerationReport:
	dry_run: bool = True
	semester: str = ""
	holiday_list: str = None
	sessions_created: list = field(default_factory=list)
	sessions_skipped_existing: list = field(default_factory=list)
	dates_skipped_holiday: list = field(default_factory=list)
	errors: list = field(default_factory=list)

	def as_dict(self):
		return {
			"dry_run": self.dry_run,
			"semester": self.semester,
			"holiday_list": self.holiday_list,
			"sessions_created_count": len(self.sessions_created),
			"sessions_created": self.sessions_created,
			"sessions_skipped_existing_count": len(self.sessions_skipped_existing),
			"dates_skipped_holiday_count": len(self.dates_skipped_holiday),
			"errors": self.errors,
		}


def get_holiday_dates(holiday_list: str) -> set:
	if not holiday_list:
		return set()
	if not frappe.db.exists("Holiday List", holiday_list):
		frappe.throw(f"Holiday List {holiday_list!r} does not exist")
	rows = frappe.db.get_all(
		"Holiday", filters={"parent": holiday_list}, fields=["holiday_date"]
	)
	return {row.holiday_date for row in rows}


def get_timetable_slots_for_semester(semester: str):
	return frappe.db.sql(
		"""
		select ts.name, ts.course_offering, ts.day_of_week
		from `tabTimetable Slot` ts
		inner join `tabCourse Offering` co on co.name = ts.course_offering
		where co.semester = %s and ts.is_active = 1
		""",
		semester,
		as_dict=True,
	)


def generate_sessions(semester: str, holiday_list: str = None, dry_run: bool = True) -> dict:
	report = SessionGenerationReport(dry_run=dry_run, semester=semester, holiday_list=holiday_list)

	semester_doc = frappe.get_doc("Semester", semester)
	if not semester_doc.start_date or not semester_doc.end_date:
		frappe.throw(f"Semester {semester} has no start_date/end_date set")

	holidays = get_holiday_dates(holiday_list)
	slots = get_timetable_slots_for_semester(semester)

	if not slots:
		report.errors.append(
			f"No active Timetable Slot rows found for any Course Offering in semester "
			f"{semester!r}. Nothing to generate."
		)
		return report.as_dict()

	slots_by_weekday = {}
	for slot in slots:
		slots_by_weekday.setdefault(slot.day_of_week, []).append(slot)

	current_date = semester_doc.start_date
	while current_date <= semester_doc.end_date:
		weekday_name = WEEKDAY_NAMES[current_date.weekday()]

		if current_date in holidays:
			if weekday_name in slots_by_weekday:
				report.dates_skipped_holiday.append(str(current_date))
			current_date += timedelta(days=1)
			continue

		for slot in slots_by_weekday.get(weekday_name, []):
			_generate_one_session(slot, current_date, dry_run, report)

		current_date += timedelta(days=1)

	return report.as_dict()


def _generate_one_session(slot, session_date, dry_run: bool, report: SessionGenerationReport):
	existing = frappe.db.exists(
		"Class Session",
		{
			"course_offering": slot.course_offering,
			"scheduled_date": session_date,
			"status": ["not in", ["Cancelled", "Rescheduled"]],
		},
	)
	if existing:
		report.sessions_skipped_existing.append(existing)
		return

	if dry_run:
		report.sessions_created.append(
			f"{slot.course_offering} on {session_date} (would be created, slot {slot.name})"
		)
		return

	try:
		doc = frappe.get_doc(
			{
				"doctype": "Class Session",
				"course_offering": slot.course_offering,
				"scheduled_date": session_date,
				"timetable_slot": slot.name,
				"status": "Scheduled",
				"is_adhoc": 0,
			}
		).insert(ignore_permissions=True)
		frappe.db.commit()
		report.sessions_created.append(doc.name)
	except Exception as e:
		frappe.db.rollback()
		report.errors.append(
			f"{slot.course_offering} on {session_date}: {e}"
		)


@frappe.whitelist()
def generate_sessions_api(semester: str, holiday_list: str = None, dry_run: bool = True):
	"""Whitelisted wrapper for a future Desk button. Restricted to the same
	roles that can write Course Offering/Timetable Slot records."""
	allowed = {"System Manager", "Registry", "College Administrator"}
	if not allowed & set(frappe.get_roles()):
		frappe.throw("Not permitted", frappe.PermissionError)
	if isinstance(dry_run, str):
		dry_run = dry_run.lower() not in ("false", "0", "")
	return generate_sessions(semester, holiday_list=holiday_list, dry_run=dry_run)
