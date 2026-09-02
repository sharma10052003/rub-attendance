# Phase 2 — Scheduling and Session Lifecycle

> **CI status (2026-09-02): green.** Timetable Slot, Class Session, and Class Session Student
> schemas are proven to sync on a real bench, and `test_generate_sessions` passes for real.
> **Still not CI-covered:** running the generator against a real Semester/Timetable Slot with
> real dates, and the cancel/reschedule flows — those need real data on a real site.

## What's built

Three more doctypes in `apps/rub_attendance`:

- **Timetable Slot** — the recurring weekly pattern (course offering + day of week + time +
  room) that sessions get generated from.
- **Class Session** (submittable) — one document per class meeting, with a real lifecycle:
  `Scheduled → Open → Submitted`, plus `Cancelled` and `Rescheduled` as first-class statuses so
  a class that never happened stays distinguishable from one nobody marked yet. Controller
  methods `cancel_session(reason)` and `reschedule_session(new_date, reason)` — reschedule
  creates a new ad-hoc session and links back via `rescheduled_to`, never overwrites history.
- **Class Session Student** (child table) — the actual attendance rows, one table per session,
  not one document per student per session.

Plus `rub_attendance/setup/generate_sessions.py`: turns a Semester's active Timetable Slots
into Class Session records for every matching weekday between the semester's start and end
date, skipping any date in a given Frappe Holiday List, and never duplicating a session that
already exists for a (course_offering, date) pair — safe to re-run after adding a slot mid-term.

**One security gap deliberately called out, not hidden:** `Class Session`'s doctype-level
permissions grant the `Lecturer` role write access to the whole doctype, because the real
scoping (a lecturer can only touch sessions for offerings they're assigned to) needs the
`get_permission_query_conditions`/`has_permission` hooks that are Phase 4's job. Until then,
`class_session.py`'s `validate()` has a manual guard (`_guard_lecturer_scope`) checking the
current user's `Lecturer` record against the `Course Offering Lecturer` child table — a
stopgap, not a substitute for Phase 4. Kept even after Phase 4 lands, per SPEC.md's rule that
every leak path (API method, `/api/resource`, report view) needs independent guarding.

Same execution caveat as Phase 1: nothing here has run against a real database — no
Python/bench on this machine. Code follows Frappe's conventions correctly; "correct" and
"verified" are still different claims.

## Running it (once Phase 1 is actually installed and passing)

```bash
# 1. Create a Holiday List in Desk (Frappe's built-in doctype) with Sherubtse's
#    academic-calendar holidays for the semester.

# 2. Create Timetable Slot records — no confirmed digital source yet (still
#    the sherubtsett.vercel.app / .fet-file question from phase0/02-data-sources.md),
#    so these are manual entry for the pilot's 2-3 programmes until that's resolved.

# 3. Dry run the generator:
bench --site sherubtse.local execute rub_attendance.setup.generate_sessions.generate_sessions \
    --kwargs "{'semester': 'Autumn 2026', 'holiday_list': 'Sherubtse 2026', 'dry_run': True}"

# 4. Review the report, then run for real:
bench --site sherubtse.local execute rub_attendance.setup.generate_sessions.generate_sessions \
    --kwargs "{'semester': 'Autumn 2026', 'holiday_list': 'Sherubtse 2026', 'dry_run': False}"

# 5. Tests:
bench --site sherubtse.local run-tests --app rub_attendance --module rub_attendance.tests.test_generate_sessions
```

**Update:** the weekday-mapping tests have actually been run locally (no bench) via
[tools/README.md](../tools/README.md)'s portable interpreter — both pass, including the check
that `WEEKDAY_NAMES` actually lines up with Python's `date.weekday()` convention. The generator
itself (the DB-touching part) still needs a real bench to verify.

## What "Phase 2 passes" requires (per SPEC.md's roadmap table)

> "A real week of the real timetable generates correctly, holidays included."

- [ ] At least one real Timetable Slot entered for a real pilot course offering.
- [ ] A real Holiday List entered for the pilot semester.
- [ ] Generator dry-run report reviewed — sessions land on the expected dates, holidays are
      skipped, no unexpected `errors`.
- [ ] Generator run for real, re-run a second time — `sessions_created_count` is 0 on the
      second run, everything shows up in `sessions_skipped_existing` instead.
- [ ] Manually test cancel_session and reschedule_session against one generated session in
      Desk — confirm the cancelled/rescheduled session is never deleted, and reschedule
      produces a linked ad-hoc replacement.
- [ ] Test suite passes.

Still blocked on the same two things as before: a running bench, and the timetable's real
data source (course catalog + lecturer assignments + recurring schedule) — Timetable Slot
entry is manual until that's resolved.
