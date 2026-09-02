# Phase 5 — Student Self-View, Disputes, Summary Aggregation

## What's built

- **Attendance Summary** — the precomputed aggregate every dashboard/report/threshold-check
  reads (never raw session rows, per SPEC.md's performance rule). Rebuilt directly from
  `Class Session.on_submit` and from an approved `Attendance Correction Request`, with a nightly
  scheduled job (`scheduler_events["daily"]` in hooks.py) as a safety net for anything those two
  miss — not the primary update path.
- **One policy call worth flagging, not hiding:** `compute_percentage` (the pure function behind
  the aggregate — see `rub_attendance/tests/test_attendance_summary.py`) excludes Excused
  sessions from the denominator entirely — they neither count as present nor drag the
  percentage down, and a student with only excused sessions so far reads as 100%, not 0%. This
  is a genuine policy judgment call, not something SPEC.md pinned down explicitly. **Confirm it
  matches RUB/Sherubtse's actual attendance policy before go-live** — if excused absences are
  meant to still count against the denominator (just flagged differently), this needs to change.
- **Excused Absence** — the "why" behind a row marked Excused; marking Excused itself stays as
  easy as marking Absent in `/rollcall` (nothing gates the mark on this record existing first).
- **Attendance Dispute** — student-raised, auto-assigned to the session's department HOD via
  `Department.hod_user`, with a `resolve()` method restricted to that HOD (or Registry/System
  Manager). This is SPEC.md's single biggest fairness fix over the original design: the
  original spec only let a *lecturer* raise a correction, leaving a student with no route in at
  all if wrongly marked.
- **`rub_attendance/api/student_portal.py`** — `get_my_attendance`, `get_my_sessions`,
  `raise_dispute`, `get_dispute_status`. Every method resolves the caller's own Student record
  from `frappe.session.user` via `Student.user` — never trusts a student ID from the client.
- **`/my-attendance`** — the student self-view portal page (Jinja + vanilla JS, same
  no-build-step approach as `/rollcall`): per-course percentage cards, a below-threshold banner
  that explicitly says this is informational only, drill-down to individual sessions, and a
  dispute form per session.
- Added `attendance_summary_query_conditions` to Phase 4's permission hooks, and Attendance
  Summary read access for `RUB Academic Administrator` — this doctype *is* the aggregate, so
  giving that role unrestricted read here is correct, unlike raw `Student` access.

## The open question this phase surfaces: student login provisioning

`Student.user` links a Student record to a Frappe User account, and everything in
`student_portal.py` depends on that link existing. Per your answer in Phase 0, RUB issues
institutional email/credentials — but I don't know the exact domain or issuance process, so
**account creation is manual for the pilot**: Registry creates a User (Desk > User > New) with
the student's institutional email and links it via `Student.user`. This does not scale past a
small pilot by hand, but building an automated bulk-invite flow means guessing at a real
provisioning process I don't have confirmed details for — worth revisiting once the pilot's
2-3 programmes are confirmed and someone can hand over the actual email format/issuance
mechanism.

## What "Phase 5 passes" requires (per SPEC.md's roadmap table)

> "A student finds an error and successfully disputes it end to end."

- [ ] At least one Student record has `user` linked to a real logged-in-capable User account.
- [ ] A Class Session has been submitted (Phase 3) with at least one student marked incorrectly
      on purpose, for testing.
- [ ] `Attendance Summary` reflects it — open `/my-attendance` as that student, confirm the
      percentage and counts match what was actually marked.
- [ ] Student clicks into the session, taps Dispute, submits a claim — confirm an
      `Attendance Dispute` record appears in Desk, `assigned_to` is correctly the department's
      HOD.
- [ ] Log in as that HOD, call `resolve()` (via Desk or console) approving the claim — confirm
      `get_dispute_status` reflects Resolved when the student checks back.
- [ ] Separately: get an `Attendance Correction Request` approved (Phase 3 flow) and confirm
      `Attendance Summary` updates immediately, not just after the nightly job.
- [ ] Test suite passes: `bench --site <site> run-tests --app rub_attendance --module rub_attendance.tests.test_attendance_summary`

Same standing blocker as every phase: no running bench on this machine to actually execute any
of the above.

## What's still not built (deliberately — not this phase's scope)

Phase 6 (reports/exports) and Phase 7 (the actual pilot semester) per SPEC.md's roadmap. Also
still open from earlier phases: the real course/timetable data source, and a running bench
environment (Frappe Cloud or WSL) to install any of this on.
