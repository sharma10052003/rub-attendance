# Phase 0.4b — Permission Matrix

Roles per SPEC.md: RUB Academic Administrator, College Administrator, HOD, Programme
Coordinator, Lecturer, Student, Registry.

Enforcement mechanism: Frappe User Permissions for `College` (cascading to every doctype that
carries a `college`/`department`/`programme` field via `get_permission_query_conditions` and
`has_permission` hooks) — **not** role-only permissions, because role alone can't express
"HOD of Department X only," and role-only permission checks are exactly the gap that lets a
College-B admin read a College-A student if someone forgets a query filter.

Legend: **F**=full CRUD, **R**=read, **R\***=read own records only, **W**=write/submit,
**A**=approve, **—**=no access. "Aggregate only" means the role sees summary numbers, not the
underlying student-identified rows, without an explicit reason-logged drill-down.

| Doctype | RUB Admin | College Admin | HOD | Programme Coord. | Lecturer | Student | Registry |
|---|---|---|---|---|---|---|---|
| College / Department / Programme / Cohort | R (aggregate) | F (own college) | R (own dept) | R (own programme) | R | — | F |
| Academic Year / Semester | R | F (own college) | R | R | R | R | F |
| Student | R (aggregate; drill-down logged) | R (own college) | R (own dept) | R (own programme) | R (own class rosters only) | R\* (self) | F |
| Lecturer | R (aggregate) | F (own college) | R (own dept) | R (own programme) | R (self) | — | R |
| Course / Course Offering | R | F (own college) | F (own dept) | F (own programme) | R (assigned only) | R (enrolled only) | F |
| Course Enrolment | R (aggregate) | R (own college) | R (own dept) | F (own programme) | R (own offerings) | R\* (self) | F |
| Timetable Slot | R | F (own college) | R | R | R (own) | R (own) | F |
| **Class Session** | R (aggregate) | R (own college) | R (own dept) | R (own programme) | **W (own offerings only, within grace window)** | R\* (own sessions) | R |
| **Class Session Student** (child rows) | R (aggregate; drill-down logged) | R (own college) | R (own dept) | R (own programme) | **W (own offerings only)** | R\* (own row only) | R |
| Excused Absence | R (aggregate) | R | R (own dept, can view reason) | R (own programme) | W (create for own sessions) | R\* (own) | R |
| Attendance Dispute | R (aggregate) | R | **A (assigned reviewer, own dept)** | R (own programme) | R (own sessions, cannot resolve) | **W (create/view own only)** | R |
| Attendance Correction Request | R (aggregate) | R | **A (own dept)** | R (own programme) | W (create for own sessions) | — | R |
| Attendance Policy | R | R | R (propose; needs Registry/Admin to set) | R | R | R | F |
| Attendance Summary | R (aggregate) | R (own college) | R (own dept) | R (own programme) | R (own offerings) | R\* (self) | R |
| Audit Log (individual-record access log) | R (own accesses only — cannot read others' logged accesses without separate audit-admin grant) | — | — | — | — | — | F |

## Rules that apply across every row above

1. **`frappe.get_all` is banned in every whitelisted method that touches Student, Class
   Session, or Class Session Student data.** Only `frappe.get_list` (which applies
   permissions) or an explicit `has_permission` check. A code-review checklist item, not just a
   design note.
2. **University-level roles (RUB Admin) default to aggregate views.** Opening any individual
   student's Class Session Student rows requires a stated reason captured at open-time and
   written to the Audit Log doctype — this is a real logged action, not a comment convention.
3. **Three leak paths tested per doctype in the isolation test suite (Phase 4):** the whitelisted
   API method, `/api/resource/<Doctype>`, and the Query Report engine. A permission rule that
   only guards one of the three is not done.
4. **Lecturer write access is scoped to `Course Offering Lecturer` assignment, not to
   Department/Programme.** A lecturer who isn't assigned to a given Course Offering cannot see
   or mark its sessions, even within their own department.
5. **Student read access is always `R*` (self only), never role-wide `R`.** A student can never
   list another student's attendance through any doctype in this table.

## Explicit test cases for the Phase 4 isolation suite (minimum set)

- College B admin opens a College A student → 403, via API method, `/api/resource`, and report view.
- Lecturer not on a Course Offering's `Course Offering Lecturer` table tries to open its Class Session → 403.
- Student A requests Student B's Attendance Summary or Class Session Student row → 403.
- Programme Coordinator for Programme X tries to write a Class Session belonging to Programme Y → 403.
- RUB Admin reads an individual Class Session Student row without a logged reason → request rejected until a reason is supplied; the reasoned request succeeds and appears in Audit Log.
