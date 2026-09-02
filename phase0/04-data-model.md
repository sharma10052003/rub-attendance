# Phase 0.4a — Data Model

App name: `rub_attendance`. Every doctype below carries a `college` Link field from day one
(SPEC.md: "Multi-college support in year one is a data model property, not a feature set").
Pilot loads exactly one College record (Sherubtse).

## Registry hierarchy

```
College
  └─ Department
       └─ Programme (e.g. "BSc in Data Science and Data Analytics")
Academic Year (e.g. "2026")
  └─ Semester (e.g. "Autumn 2026", "Spring 2026")
Cohort  — a Programme + intake year + section, e.g. "DSDA 2026 Section A"
          (this is what the roster spreadsheet titles actually encode — see 02-data-sources.md)
```

| Doctype | Key fields | Notes |
|---|---|---|
| **College** | college_name | One row for the pilot. |
| **Department** | department_name, college (Link) | |
| **Programme** | programme_name, department (Link), programme_code | e.g. DSDA, DCPM, EPS |
| **Academic Year** | year_name (e.g. "2026") | |
| **Semester** | semester_name, academic_year (Link), term (Autumn/Spring), start_date, end_date | Drives Holiday List scoping and session generation windows. |
| **Cohort** | programme (Link), intake_year, section (A/B/…) | Matches the roster-file granularity directly — this is the entity the importer upserts against per spreadsheet. |

## People

| Doctype | Key fields | Notes |
|---|---|---|
| **Student** | student_id (natural key, the 8-digit number), first_name, last_name, gender, cohort (Link), user (Link to Frappe User), institutional_email, status (Active/Transferred/Withdrawn/Graduated) | `student_id` is the idempotent-upsert key per SPEC.md Phase 1 requirement. CID **not stored** in v1 — no proven need yet (see 02-data-sources.md); revisit only if an IMS join later requires it, and if so restrict it to the Registry role via field-level permission. |
| **Lecturer** | staff_id, full_name, user (Link), college (Link) | A Lecturer can be linked to course offerings across colleges (SPEC.md model-reality case: "a lecturer teaching at two colleges"). |

## Academic offering

| Doctype | Key fields | Notes |
|---|---|---|
| **Course** | course_code, course_title, department (Link) | The catalog — currently has **no confirmed digital source** (02-data-sources.md); first Phase 1 task is getting this list, likely from the timetable `.fet` source or manual entry. |
| **Course Offering** | course (Link), semester (Link), cohort (Link), session_type (Lecture/Tutorial/Lab) | Session type exists explicitly so a lab/tutorial can have a different roster than its parent lecture (SPEC.md model-reality case). |
| **Course Offering Lecturer** (child table on Course Offering) | lecturer (Link), role (Primary/Co-teaching) | A table, not a single Link, so two lecturers can co-teach one offering (SPEC.md model-reality case). |
| **Course Enrolment** | student (Link), course_offering (Link), enrolment_status (Active/Dropped/Transferred), start_date, end_date | Row per student per offering. Supports mid-semester transfer and repeat-a-module cases: a repeating student gets a *new* Course Enrolment row against the new semester's offering, never a mutated old one. |

## Scheduling

| Doctype | Key fields | Notes |
|---|---|---|
| **Timetable Slot** | course_offering (Link), day_of_week, start_time, end_time, room | Recurring weekly pattern — the template `Class Session` records are generated from. |
| **Class Session** | course_offering (Link), scheduled_date, timetable_slot (Link, nullable), status (Scheduled/Open/Submitted/Cancelled/Rescheduled), cancellation_reason, rescheduled_to (Link, self), is_adhoc (Check), submitted_by, submitted_at | `is_submittable`. `timetable_slot` is nullable specifically so an ad-hoc session (SPEC.md requirement) can exist without ever having been on the recurring timetable. Cancelled/Rescheduled are real statuses, not deletions — a session that never happened must stay distinguishable from one nobody marked (SPEC.md requirement). |
| **Class Session Student** (child table on Class Session) | student (Link), status (Present/Absent/Late/Excused), marked_by (Link User), marked_at (Datetime), method (Manual/QR — QR unused until Phase 8+) | **This is the entire attendance record.** One Class Session document holds every student's row for that class — not one document per student per session. Indexed on `student`, and the parent's `course_offering`/`scheduled_date` cover the summary-rebuild query. |

## Exceptions and disputes

| Doctype | Key fields | Notes |
|---|---|---|
| **Excused Absence** | student (Link), class_session (Link), reason, evidence (Attach, optional), recorded_by | A real record, not just a status value on the child row — the child row's status still shows `Excused`, this doctype holds the *why*, per SPEC.md's fairness requirement. |
| **Attendance Dispute** | student (Link, the raiser), class_session (Link), claim, status (Open/Under Review/Resolved), assigned_to (Link User), resolution_note, raised_at, resolved_at | Student-initiated. This is the doctype SPEC.md calls the single most important fairness fix over the original design. |
| **Attendance Correction Request** | class_session (Link), requested_by (lecturer), original_status, requested_status, reason, approval_status (Pending/Approved/Rejected), approved_by | Only used for edits **outside** the 24-hour grace window — inside the window, the lecturer edits the Class Session Student row directly and it's captured by Frappe's built-in version history, no separate doctype needed. |

## Policy and aggregation

| Doctype | Key fields | Notes |
|---|---|---|
| **Attendance Policy** | programme (Link, nullable = applies to all), minimum_percentage, late_counts_as, grace_window_hours, correction_requires_approval | Scoped by programme so different programmes can set different thresholds, per SPEC.md. Never hard-coded in code. |
| **Attendance Summary** | student (Link), course_offering (Link), semester (Link), sessions_held, present_count, absent_count, late_count, excused_count, percentage | Rebuilt by a scheduled job after every Class Session submission/correction. **Every dashboard, report, and threshold check reads this table — never raw Class Session Student rows.** This is the table that keeps the pilot fast at Sherubtse's real volume (~540k attendance rows/semester). |

## Model-reality test cases (per SPEC.md — verified against this model before freezing)

| Case | How the model handles it |
|---|---|
| Student repeats a module | New `Course Enrolment` row against the new semester's `Course Offering`; old enrolment stays `Dropped`/completed, its `Attendance Summary` row is untouched history. |
| Course taught by two lecturers | `Course Offering Lecturer` child table, not a single Link. |
| Lab/tutorial has a different roster than the lecture | Separate `Course Offering` rows per `session_type`, each with its own `Course Enrolment` rows. |
| Student transfers mid-semester | `Course Enrolment.enrolment_status = Transferred` with `end_date` set; new enrolment created at the destination `Cohort`/`Course Offering`. Historical `Class Session Student` rows before the transfer date are untouched. |
| Lecturer teaches at two colleges | `Lecturer.college` is the lecturer's home college; `Course Offering Lecturer` links can cross colleges since it's a separate table, not a same-college-only field. |
| Two sections merged for one session | One `Class Session` can be linked from two `Course Offering`s only if we allow `Class Session.course_offering` to be... **open question, not yet resolved** — current model assumes one offering per session. If merged-section sessions turn out to be common at Sherubtse, this needs a join table (`Class Session` ↔ multiple `Course Offering`s) rather than a single Link. Flagging rather than guessing. |
| Semester rollover | `Semester` and `Academic Year` are just new records; nothing about the model requires closing out the old one, so historical summaries stay queryable indefinitely. |

**Open item to confirm before freezing:** the merged-sections case above. Everything else is
covered.
