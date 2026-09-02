# Phase 6 — Reports and Exports

> **CI status (2026-09-02): green.** All three report JSON/py files load correctly as part of
> the app-wide install/migrate CI now does on every push. **Still not CI-covered:** actually
> running each report with real data and filters, and the CSV/Excel export buttons — those need
> a real site with real records, per the checklist below.

## What's built

Three Frappe **Script Reports** (`is_standard: Yes`, so they load from these `.py` files, not
the database) — per SPEC.md: "Build reports as Frappe Query Reports with CSV and Excel export
— do not hand-build report UIs." CSV/Excel export needed **zero code**: it's a built-in button
on every Frappe report view.

- **Lecturer Course Register** — session-by-session register for one Course Offering: date,
  status, present/absent/late/excused counts, and an "Overdue — Not Yet Marked" flag for any
  past session still stuck in Scheduled/Open. Visible to Lecturer, HOD, Programme Coordinator,
  Registry, System Manager — but row-level scoping (a lecturer only sees offerings they're
  assigned to, an HOD only their department) comes from `frappe.get_list` automatically calling
  Phase 4's `class_session_query_conditions`. Nothing in this report's code does its own
  permission filtering — that's the point of building it on `get_list`.
- **HOD Programme Summary** — every student's percentage per course offering, scoped to the
  caller's department/programme the same way. Tick "Only Below Threshold" for the at-risk list
  SPEC.md asks for — it's the same report, not a second one, since the difference is one filter.
- **Lecturer Submission Rate** — sessions scheduled vs. submitted per lecturer per offering.
  **Deliberately not visible to the Lecturer role**, and not on any dashboard — SPEC.md calls
  this out explicitly as a metric that becomes a "management stick" if it turns into a
  leaderboard lecturers can see about each other. It's a report an HOD pulls, full stop. If this
  is ever extended, keep that restriction — don't add a lecturer-visible version.

## What "student's own record" report is — already done, not duplicated

SPEC.md's third listed report ("student's own record") is `/my-attendance` from Phase 5, not a
Desk report — Student role has no Desk access at all in this app (self-service goes through the
whitelisted API everywhere, consistently, since Phase 1). Building a fourth Query Report for
the same data would just be two paths to maintain for one thing.

## Setup

Nothing beyond having the app installed — reports load automatically since they're
`is_standard: Yes` files under `rub_attendance/rub_attendance/report/`. Access from Desk under
Report or via the "Report" list.

## What "Phase 6 passes" requires (per SPEC.md's roadmap table)

> "The HOD gets the report they actually asked for, in the format they wanted."

This one's condition is literally a conversation, not a checklist — SPEC.md is telling you to
go ask the actual HOD what they need rather than assume these three cover it. Concretely, once
a bench exists:

- [ ] Open each report as the relevant role, confirm the isolation holds (an HOD sees only
      their department, a lecturer only their own offerings).
- [ ] Export one report to CSV and one to Excel from the report view — confirm both open
      cleanly.
- [ ] Show the actual HOD sponsoring the pilot the Programme Summary and Submission Rate
      reports — confirm the columns/filters match what they'd actually pull, and add what's
      missing before calling this phase done. Don't guess further than these three from here
      without that conversation.

Standing blocker, same as every phase: no running bench on this machine.
