# Phase 0.4c — API / Interface Contract

Two consumer-facing surfaces only, per SPEC.md architecture: the lecturer roll-call (a Frappe
UI page) and the student self-view (a Jinja portal page). Everything else is Frappe Desk —
no separate API contract needed for Desk, permissions handle it.

All endpoints are Frappe whitelisted methods (`@frappe.whitelist()`), called via
`frappe.call`. All of them use `frappe.get_list`/explicit `has_permission` checks — never
`frappe.get_all` — per the permission matrix rule.

## Lecturer roll-call screen

### `rub_attendance.api.rollcall.get_session(course_offering, date)`
Returns the Class Session for a given offering+date, creating it from the Timetable Slot if it
doesn't exist yet and the date is valid (not a holiday, within term dates). Returns:
```json
{
  "class_session": "CS-2026-00042",
  "status": "Open",
  "course_offering": "...",
  "scheduled_date": "2026-09-02",
  "grace_window_ends_at": "2026-09-03T09:00:00",
  "students": [
    {"student": "07260124", "student_name": "Chhimi Om Doya", "status": "Present", "marked_at": null}
  ]
}
```
Every student defaults to `Present` in the response — the lecturer only has to touch exceptions,
per SPEC.md's roll-call requirement.

### `rub_attendance.api.rollcall.submit(class_session, rows, client_marked_at)`
`rows` = array of `{student, status}` for only the rows that changed from the default (Present).
`client_marked_at` is the device's local timestamp, sent so a session marked offline and synced
later still records when it actually happened, not when the network came back.
Idempotent: calling it twice with the same payload does not double-count or error — it's an
upsert against the child table, not an append.
Server validates: session isn't already past the grace window (else routes to Correction
Request instead of a direct write), caller is in `Course Offering Lecturer` for this offering,
every `student` in `rows` is actually enrolled in this offering.
Returns the same shape as `get_session`, now with `status: "Submitted"`.

### Offline behavior (client-side, not a server endpoint)
The roll-call page caches `get_session`'s response in local storage/IndexedDB on load. Taps
update local state immediately and queue a pending `submit` call. A visible "N changes not yet
synced" indicator shows until `submit` succeeds. On reconnect, queued submits fire in order.
This is a client requirement captured here because it constrains the API shape above
(idempotent submit, client-supplied timestamp) — there's no separate server endpoint for it.

### `rub_attendance.api.rollcall.request_correction(class_session, student, requested_status, reason)`
Used once the grace window has passed. Creates an `Attendance Correction Request`, does not
change the Class Session Student row until an HOD approves it.

## Student self-view portal page

### `rub_attendance.api.student_portal.get_my_attendance(course_offering=None, semester=None)`
Returns the calling user's own `Attendance Summary` rows (filtered if params given), each with
a drill-down list of individual `Class Session Student` rows — but only the student's own,
enforced server-side by resolving `frappe.session.user` to a `Student` record, never trusting
a `student` parameter from the client.
```json
{
  "summary": [
    {"course_offering": "...", "course_title": "...", "percentage": 82.1,
     "sessions_held": 22, "present": 18, "absent": 2, "late": 1, "excused": 1}
  ]
}
```
Threshold flags (below `Attendance Policy.minimum_percentage`) are included as an informational
`"below_threshold": true` field — **the API never returns or implies any eligibility decision**,
per SPEC.md's "system flags, human decides" rule.

### `rub_attendance.api.student_portal.raise_dispute(class_session, claim)`
Creates an `Attendance Dispute` for the calling student against one of their own
`Class Session Student` rows. Server verifies the row actually belongs to the caller before
creating it. Returns the dispute's tracking ID and the HOD/reviewer's expected response-time
policy (pulled from `Attendance Policy`, not hard-coded).

### `rub_attendance.api.student_portal.get_dispute_status(dispute)`
Read-only status check on a dispute the student raised. 403 if the dispute doesn't belong to
the caller.

## What is explicitly not part of this contract

- No QR endpoints — QR is deferred past the pilot per SPEC.md.
- No geofencing/device-fingerprint/location fields anywhere in any payload — out of scope per
  SPEC.md, and not something to leave a placeholder field for.
- No bulk cross-student query available to the Lecturer or Student roles through this API —
  cross-student views are Desk/Query Report territory, gated by the permission matrix, not this
  API surface.
