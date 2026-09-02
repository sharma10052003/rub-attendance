# Phase 0.1 — Build vs. Reuse Decision

**Status:** decided. **Decision: build a new, narrow custom app (`rub_attendance`) on plain Frappe. Do not install `frappe/education`.**

Moodle was ruled out separately — this project is being built standalone in its own folder,
with no dependency on the college website stack or any VLE. So this was a two-way call:
extend `frappe/education`, or build greenfield.

## What `frappe/education` actually is (checked against the live repo, 2026-09-02)

- Active: 620 stars, 424 forks, **143 open issues**, last push today. Not abandoned.
- It ships `Student`, `Program`, `Course`, `Instructor`, `Course Schedule`, `Student Group`,
  and `Student Attendance`, plus a large amount unrelated to attendance: Fees and Fee
  Schedules, Guardians and Siblings, Hostel, Transportation, Assessment/Exams, LMS/Content,
  Certification. All of that installs and shows up in Desk whether it's used or not.
- I pulled the actual doctype JSON for the two doctypes that matter most:

**`Student Attendance`** — fields: `student`, `course_schedule`, `student_group`, `date`,
`status` (Present/Absent/Leave), `leave_application`, `amended_from`. `is_submittable: true`,
naming series `EDU-ATT-.YYYY.-`.

This is **one document per student per date** — exactly the pattern [SPEC.md](../SPEC.md)
rules out ("Do not create one standalone document per student per session — at roughly 1.1
million rows a year for Sherubtse alone that is unmanageable in Desk and pointless"). It also
has no `marked_by`, no `method` (manual/QR), no grace-window semantics, and only three
statuses — no `Late`, no `Excused` as a distinct first-class concept. Using it as-is means
either rebuilding the exact anti-pattern the spec forbids, or forking/heavily patching a doctype
that ships inside someone else's app (fragile across upgrades).

**`Student`** — 40+ fields: name parts, guardians, siblings, hostel/customer linkage, address,
exit records. No `CID`, no `Scholarship Type`, no `Programme` link directly on it (those live on
`Program Enrollment` in the education app's model) — so the real Sherubtse admission data (see
[02-data-sources.md](02-data-sources.md)) doesn't map onto it cleanly either; it would still need
a full import-mapping layer, just against a bigger, less-transparent target schema.

## Trade-off

| | Extend `frappe/education` | Greenfield `rub_attendance` |
|---|---|---|
| Free registry doctypes (Student, Program, Course, Instructor) | Yes | Build these (small: ~4 doctypes) |
| Attendance capture model | Wrong shape — must be replaced or forked anyway | Built to spec from the start (Class Session + child table) |
| Extra surface area to maintain (Fees, Hostel, Transport, LMS, Assessment, Guardians/Siblings) | ~15+ unrelated doctypes installed and visible in Desk | None |
| Upgrade risk | Tied to upstream's release cadence and its 143 open issues | Fully owned, upgrades on our schedule |
| Time to first working pilot | Faster registry setup, offset by fighting the attendance doctype | Slightly more upfront doctype work, no fighting later |
| Fit with "one maintainer, bias toward less" (SPEC.md rule 11) | Poor — inherits a large app's entire footprint for ~4 doctypes worth of value | Good — every doctype in the app is one we chose |

## Decision and rationale

Build greenfield. The two doctypes `frappe/education` would actually save us building
(`Student`, `Program`/`Course`) are small — a handful of fields each — and the one doctype that
matters most for this project, attendance capture, is built the wrong way in that app and would
need replacing regardless. Installing the rest of `frappe/education` to get four simple doctypes
means a one-person maintainer inherits fees, hostel, transport, LMS and assessment machinery
that will never be used here, plus that app's own bug backlog, for a system whose core design
principle is "every feature added is a feature maintained forever."

This is a **narrow, deliberate rejection**, not a default to greenfield-because-it's-more-fun:
the registry doctypes we'd reuse are cheap to build ourselves, and the one part that's expensive
to build (a correct, session-based, offline-capable attendance model) is not something
`frappe/education` provides anyway.

**Revisit this if:** the pilot succeeds and Sherubtse (or RUB) later wants a full SIS — fees,
hostel, transport, exams — in which case adopting `frappe/education` for *those* modules and
keeping `rub_attendance` as a satellite app that links to its `Student`/`Program` doctypes
becomes worth reconsidering. Do not reopen it for the attendance pilot itself.

## What we build (Phase 1 scope, per SPEC.md hierarchy)

Minimal registry doctypes only: `College`, `Department`, `Programme`, `Academic Year`,
`Semester`, `Student`, `Staff`/Lecturer, `Course`, `Course Offering`, `Course Enrolment`,
`Class Session` (with child table `Class Session Student`). No Fees, no Hostel, no Guardians,
no Assessment — none of that is in scope for an attendance pilot.
