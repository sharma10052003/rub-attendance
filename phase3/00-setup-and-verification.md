# Phase 3 — Lecturer Roll-Call Screen

## What's built

- **Attendance Policy** doctype — `minimum_percentage`, `late_counts_as`, `grace_window_hours`,
  `correction_requires_approval`, scoped by Programme (blank = college-wide default). Every
  place that needs a policy number reads `attendance_policy.get_policy(programme)`, which
  **hard-throws** if no policy is configured rather than silently falling back to a hard-coded
  number — deliberate, per SPEC.md's "never hard-code attendance policy" rule.
- **Attendance Correction Request** doctype, with a `decide(approve, note)` method scoped to the
  HOD of the session's department (via a new `Department.hod_user` field — added retroactively;
  Phase 1's Department doctype was missing a way to express who the HOD actually is).
- **`rub_attendance/api/rollcall.py`** — `get_session`, `submit`, `request_correction`, matching
  phase0/06-api-contract.md. `get_session` creates the Class Session on first open (pre-filling
  the roster from active Course Enrolment, defaulting everyone to Present) if Phase 2's
  generator hasn't already created one for that date. `submit` is idempotent and grace-window
  aware: inside the window it allows direct edits to an already-submitted session (logged via
  Frappe's version history), outside it the caller must use `request_correction` instead.
- **`/rollcall`** — the one custom interactive page, a single-file server-rendered Jinja + vanilla
  JS page (no build step, no framework — consistent with SPEC.md's "Frappe only" rule). Large
  tap targets, defaults every student to Present, running Present/Absent/Late/Excused counts,
  and an offline queue: a failed submit is saved to `localStorage` and retried automatically on
  the `online` event or when the user taps "Sync now" — the lecturer's marks are never lost to
  a dead connection mid-class.

## What I could not verify, and why

No browser-against-a-live-site test happened — there's no running bench (same constraint as
every phase so far). The JS is plain, dependency-free, and uses only `fetch`/`localStorage`,
which are safe assumptions for "a mid-range Android phone over 3G" (SPEC.md's target device),
but **you should open `/rollcall` on an actual phone once a site exists** before trusting it in
a real classroom — this is exactly the kind of thing that needs the "make the feature not exist
until you've held it" rule from your own project's Bash/Frontend guidance in spirit: I have not
looked at this page render, and neither has anyone else yet.

## Setup

```bash
# 1. Create at least one Attendance Policy record (Desk) — leave Programme
#    blank for a college-wide default, or scope one per programme.

# 2. Link each Lecturer record's `user` field to that person's actual User
#    account — /rollcall resolves "who is this" from frappe.session.user via
#    the Lecturer doctype, not from a URL parameter.
```

Then just visit `/rollcall` while logged in as a lecturer. No bench command needed beyond having
the app installed and migrated (`bench --site <site> migrate` after Phase 1/2's `install-app`).

## What "Phase 3 passes" requires (per SPEC.md's roadmap table)

> "A lecturer marks a real class on their own phone, in the room, with Wi-Fi disabled."

- [ ] A real Lecturer, Course Offering, and enrolled Students exist (Phases 1–2 actually run).
- [ ] Open `/rollcall` on an Android phone, pick the class, load it with Wi-Fi **on** first.
- [ ] Turn Wi-Fi **off**, mark a few students Absent/Late, tap Submit — confirm the
      "not yet synced" banner appears and nothing is lost (reload the page while still offline;
      the marks should still be there from `localStorage`).
- [ ] Turn Wi-Fi back on — confirm it auto-syncs within a few seconds, or tap "Sync now".
- [ ] Re-open the same class after submission, edit one student's status within the grace
      window — confirm it saves without needing a Correction Request.
- [ ] Manually set a session's `scheduled_date` far in the past (or shrink
      `grace_window_hours` to 0 for a test) and confirm editing a submitted session now
      requires `request_correction` instead of a direct edit.

Still open from earlier phases: no running bench, and Timetable Slot data is still manual entry
pending the course/timetable source question from phase0/02-data-sources.md.
