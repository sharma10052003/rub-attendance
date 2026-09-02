# Phase 4 — Permission Isolation and Test Suite

> **CI status (2026-09-02): green — including the integration suite.**
> `test_permission_isolation` now runs against a real database on every push and passes. It
> took five real, distinct bug fixes to get there (see the CI commit history from
> `d5ed777` back to `9cdaa70`): a `before_install` ordering fix so custom roles exist before
> permission sync, a missing `"name"` field in the role fixtures, a missing `Semester` in the
> test's own fixture setup, and — the one an actual test caught, not review — **College
> Administrator was missing from 15 doctypes' permissions** where the matrix below calls for
> it, discovered because `test_college_admin_cannot_see_other_college_student` failed for real.
> Two of the four originally-written test assertions also encoded a wrong assumption about
> Frappe's API (`frappe.get_doc()` doesn't check permissions by itself) and were corrected.
> **Still not CI-covered:** the two other leak paths SPEC.md asks for — `/api/resource` over
> HTTP and Report View — the suite exercises the same underlying permission-check code path via
> Python, which is strong evidence but not identical to an actual HTTP request.

## The key finding: college-level isolation is (almost) free

Every doctype in this app carries a direct `college` Link field — a deliberate Phase 0 design
decision. Frappe automatically filters any Link field against a logged-in user's **User
Permission** records for that target doctype, with no custom code required. So a College
Administrator with one User Permission row (`allow: College, for_value: <their college>`) is
already scoped to their college everywhere, for every doctype, automatically. Setting that up
is a configuration step, not a code change:

```
Desk > User Permission > New
  User: <the college admin's account>
  Allow: College
  For Value: <their College record>
```

## What actually needed custom code

Department/programme/lecturer-assignment scoping — Frappe's native mechanism can't derive
"HOD of which department" or "which offerings is this lecturer assigned to" on its own, since
Student/Course Offering/Class Session don't carry a direct Department field. `rub_attendance/permissions.py`
adds `get_permission_query_conditions` (filters list/report views) and `has_permission`
(guards direct single-record access — the leak path a query condition alone doesn't cover) for
Student, Cohort, Course Offering, Course Enrolment, and Class Session, wired into
[hooks.py](../apps/rub_attendance/rub_attendance/hooks.py).

Two small fields were added retroactively to make this possible: `Department.hod_user` (Phase 3)
and `Programme.coordinator_user` (this phase) — Phase 1's original doctypes had no way to
express "who is the HOD" or "who is the coordinator," which the permission matrix always
required.

## RUB Academic Administrator: the fairness fix from SPEC.md A4

No doctype in this app grants that role direct read on `Student` — check any `.json`
permissions block, it's not there. The only way to see one student's raw record is
`rub_attendance.api.audit.view_student_record(student, reason)`, which requires a non-empty
reason and writes an **Audit Log** entry (`accessed_by`, `student`, `reason`, `accessed_at`)
before returning the record. Audit Log itself can't be deleted even by System Manager
(`delete: 0` in its DocType permissions) — the log has to stay honest.

## Test suite

`rub_attendance/tests/test_permission_isolation.py` — a `FrappeTestCase` covering the minimum
set from phase0/05-permission-matrix.md: cross-college, cross-department, unassigned-lecturer,
student-self, and RUB-Admin-drill-down cases. **Needs a real site to run** — it creates real
Users, a User Permission record, and impersonates each one via `frappe.set_user()`. Same
execution caveat as every phase so far: written correctly against Frappe's test conventions,
not yet run against a database.

```bash
bench --site sherubtse.local run-tests --app rub_attendance --module rub_attendance.tests.test_permission_isolation
```

## What "Phase 4 passes" requires (per SPEC.md's roadmap table)

> "All isolation tests pass in CI, including via `/api/resource` and report view."

- [ ] Test suite above passes.
- [ ] Manually repeat at least one case through `/api/resource/Student/<name>` directly (not
      just the Python API) — log in as the cross-college College Administrator in a browser
      and hit that URL, confirm 403. The test suite exercises `frappe.get_doc()` and
      `frappe.get_list()`, which share the permission-check code path with `/api/resource`, but
      an actual HTTP request is the real proof SPEC.md asks for.
- [ ] Manually repeat one case through Report View (Desk > Student > Report View, logged in
      as the HOD-of-a-different-department account) — confirm the other department's students
      don't appear.
- [ ] Wire CI (even a minimal GitHub Actions workflow running `bench run-tests`) so this suite
      runs automatically — not done yet, needs a real bench/site to build against.

Still blocked on the same root cause as every phase: no running bench on this machine to
actually execute any of the above.
