# RUB Attendance System — Master Prompt (Sherubtse College Pilot)

Source: pasted by user on 2026-09-02. This is the authoritative spec for the project.
Part A (reality check / rationale) is kept for context; Part B (master prompt) is what
implementation work follows. Development proceeds one phase at a time per the Output
Rules below — do not jump ahead to later phases without an explicit go-ahead.

---

# PART A — REALITY CHECK

## A1. The blocking architectural error

> "Strapi = Presentation / Content / API layer … Build Student Portal, Lecturer Portal, HOD Portal, College Portal, RUB Portal in Strapi."

**Strapi cannot do this.** Strapi is a headless CMS. It gives you three things: an admin panel for *content editors*, a REST/GraphQL API over *its own* database, and a plugin system. It has no user-facing rendering layer. There is no way to build a student attendance dashboard "in Strapi" — you would need a frontend application to consume Strapi's API, and the prompt bans every frontend framework in its second paragraph.

So the prompt, as written, describes a system that cannot be built. An AI given this prompt will not tell you that. It will generate confident Strapi content-type definitions and controller stubs that look like progress and lead nowhere.

There is a second problem underneath it. Strapi needs its own database, its own deployment, its own authentication, its own upgrade cycle. For one person to run that *alongside* Frappe, in order to serve announcements and FAQs — which Frappe's built-in Web Page and Blog Post doctypes already do — is a straight loss. It also contradicts the prompt's own Rule 11 ("keep the system simple enough for university ICT staff to maintain").

**Resolution used in Part B:** Frappe owns the entire attendance system, including its user interfaces. Frappe Desk handles admin, HOD and coordinator screens for free. One custom mobile-friendly page handles the lecturer roll-call, which is the only screen where UX genuinely matters. A simple server-rendered portal page handles the student self-view. Your existing Strapi + Astro build keeps doing the college website and touches no attendance data, no student data and no authentication. The boundary is stated explicitly so it does not erode later.

## A2. Rebuilding what already exists

The prompt says "create a Student DocType", "create a Course", and so on, from zero. Before doing that, two existing systems need a decided answer, not an unconsidered one:

- **`frappe/education`** is an open-source Frappe app with Student, Program, Course, Instructor, Course Schedule and Student Attendance doctypes already built. It has roughly 126 open issues and a variable maintenance history, so extending it is not automatically the right call — but "we evaluated it and chose greenfield because X" is a defensible position and "we never looked" is not.
- **Your Moodle VLE** already holds real students, real logins and real course enrolments, and `mod_attendance` already does sessions, registers, exports and rotating-QR self-marking. It will not give you RUB-wide hierarchy or official-record status, and its enrolment is not the registry's enrolment — but if it closes 60–70% of the need for zero build effort, that reshapes the whole project.

Part B makes this a Phase 0 decision with a written answer.

## A3. What breaks in actual Bhutanese conditions

The original prompt has no mention of any of these, and each one has killed attendance systems elsewhere.

**Connectivity and power.** Lecture halls and labs with weak or no Wi-Fi, and load-shedding. If the lecturer cannot reach the server at 9:00, attendance does not get taken, and the data is then *worse* than the paper register it replaced — because it is silently incomplete rather than visibly missing. The roll-call screen must hold its state locally and sync when the network returns, and there must be a submission grace window measured in hours, not minutes.

**Student devices.** QR-only marking excludes any student without a working smartphone and data. Manual lecturer marking must be the default path and must always work standalone; QR is an accelerator layered on top, never a replacement.

**Timetables do not hold still.** Classes get swapped, merged across sections, cancelled, moved for guest lectures, made up on Saturdays, and suspended for exam weeks and national holidays. A rigid Timetable → Class Session generator will fight the college calendar every single week until lecturers stop using it. Session cancellation, rescheduling and ad-hoc sessions must be first-class operations, and the Frappe Holiday List must be wired in from the start.

**Where the data comes from is the actual project.** The original prompt puts IMS integration at Phase 10, which means Phases 1–9 depend on somebody hand-entering thousands of students, courses, offerings and enrolments — and re-entering them every add/drop period. That will not happen accurately. Data ingestion belongs in Phase 1: CSV/Excel importers with validation, dry-run mode, and idempotent upsert keyed on student ID so re-running never duplicates. The first real conversation is with whoever owns the current enrolment spreadsheets, before a single doctype is written.

**Scale is misjudged in both directions.** The prompt worries about "thousands of students scanning simultaneously." Actual arithmetic for Sherubtse: roughly 13,500 sessions per semester, about 540,000 attendance rows per semester, around 1.1 million per year — and about 6.5 million per year if all ten RUB colleges eventually run on it. MariaDB on one well-specced VM handles that comfortably. The peak write burst is around 0.3 writes/second for a single class, under 7 writes/second even if twenty classes all scan at the top of the same hour. That is nothing. So: do not build for imaginary scale, no microservices, no queue infrastructure. But *do* index properly and *do* precompute attendance percentages into a summary table, because the thing that will actually be slow is a dashboard scanning a million raw rows to render a percentage.

**A one-person team.** This is the largest risk in the project and the original prompt does not acknowledge it at all. A system that touches exam eligibility for 2,450 students, maintained by one person, has a bus factor of one. Part B makes a named backup maintainer and a tested restore procedure hard prerequisites for go-live, and pushes hosting toward Frappe Cloud so that backups, upgrades and monitoring are not also your job.

## A4. Where the original prompt is ethically wrong

**QR anti-abuse is dishonest about what it can do.** Section 18 lists token rotation, rate limiting and server-side validation as if they solve proxy attendance. They do not. A student photographs a rotating QR and sends it over WhatsApp in about four seconds; rotation shortens the window, it does not close it. Real-world evidence: Moodle's `mod_attendance` rotating-QR feature has a long tail of open bug reports from institutions trying exactly this. The controls that actually work are the lecturer in the room, occasional random spot-checks of three names, and binding one device per student account. Writing "prevents duplicate attendance" into a spec creates false confidence that later gets used to justify accusing a student.

**The surveillance list should not be a roadmap.** Geofencing, campus Wi-Fi validation, IP validation, device fingerprinting, RFID, NFC and biometrics are listed as "optional future protection." That phrasing is how surveillance arrives: a future maintainer reads it as approved-in-principle. These collect location and biometric data on students, they are all spoofable by exactly the students motivated to spoof them, and they generate false negatives that punish the honest — a student sitting by a window on cellular data gets marked absent. Part B moves them to an explicit **out of scope** list requiring a written justification and student consultation before anyone reopens the question.

**Students have no way to challenge the record.** The original prompt has an Attendance Correction Request that only a *lecturer* can raise. But attendance gates exam eligibility. A student wrongly marked absent has, in this design, no route into the system at all — they must find the lecturer and persuade them to file. That is the single most important fairness defect in the document. Part B adds a student-initiated dispute with a defined response time and a human appeal route.

**The correction workflow is too heavy to survive.** `Draft → Submitted → Under Review → Approved/Rejected` for every correction means a lecturer who taps the wrong row and notices thirty seconds later must file paperwork. HODs will drown, and people will route around the system by keeping a private spreadsheet. A 24-hour self-correction window that is fully logged, with the approval workflow applying only beyond that window, gets you the audit trail without the friction.

**"Lecturer Submission Rate" as a headline metric is a management stick.** Put it in an operational report a HOD can pull, not on a dashboard leaderboard. Attendance systems that feel like staff surveillance get quiet non-cooperation, and lecturer non-cooperation is what actually kills these projects.

**Excused absence needs to be real, not a status value.** Students miss class for illness, bereavement, funerals, religious observance, and travel from remote dzongkhags. If marking someone "Excused" is harder than marking them "Absent," everyone gets marked absent and the 80% threshold starts punishing circumstance. This needs an easy path and a documented policy.

**No automated punishment, ever.** The system flags. A human decides. Nothing in the software should bar a student from an exam.

**Legal position.** No comprehensive personal-data protection statute in Bhutan comparable to GDPR or India's DPDP Act was found; the Information, Communications and Media Act 2018 carries limited provisions and the RMA's 2021 data privacy guidelines are financial-sector scoped. Verify this with RUB's legal office rather than relying on this reading. But the absence of a statute is not the absence of an obligation — it means RUB must set its own policy, and there should be a written privacy notice, a named data controller, a stated retention period and an access-logging rule in place before the first real student record is loaded.

**Also: `RUB Super Administrator → sees everything`** means one account can see every student's daily movements across ten colleges. Default that role to aggregates, require a stated reason for opening an individual record, and log every such access.

## A5. Process problem: twelve design documents before any running code

The original prompt ends by requiring twelve architecture artifacts before implementation. The instinct is right; the execution guarantees two hundred pages of plausible LLM prose that nobody reads and that has never met the actual data. Part B cuts this to three short documents and requires a Frappe instance running with real Sherubtse enrolment data in the first fortnight, because that is where the surprises are.

## A6. Missing model realities

The original data model does not accommodate: students repeating a module, a course taught by two lecturers, tutorials and labs with different rosters than the lecture, cross-college or distance students, a lecturer teaching at two colleges, students transferring mid-semester, or term rollover. Part B lists these as cases the model must be tested against before it is frozen.

---

# PART B — REVISED MASTER PROMPT

*Everything below this line is the operative prompt for implementation work.*

---

## MASTER PROMPT — SHERUBTSE COLLEGE ATTENDANCE SYSTEM (Frappe)

### Role

Act as a senior Frappe Framework developer and university information-systems specialist who has deployed systems in low-resource, intermittent-connectivity environments and who has seen attendance projects fail. The job is not to produce an impressive architecture. The job is to produce something one person can build, run and be responsible for, that lecturers will actually use, and that treats students fairly.

Be direct about what will not work. If a request is a bad idea, say so before building it.

### The real constraints — do not design around these, design *for* them

1. **One maintainer.** The system is built and run largely alone, with AI assistance. Every feature added is a feature maintained forever. Bias hard toward less.
2. **Frappe only.** Frappe Framework (v15 or v16) is the entire attendance system, including its user interfaces. No Strapi, no Astro, no Next.js, no React, no Laravel, no Django, no separate backend, no microservices.
3. **An existing Strapi + Astro build serves the college website.** It stays exactly where it is. It handles announcements, news, FAQ and public pages. It receives **no** attendance data, **no** student data and **no** authentication responsibility. State this boundary in any document produced so it does not erode.
4. **Intermittent connectivity and power.** Lecture halls with weak Wi-Fi, occasional load-shedding.
5. **Not every student has a usable smartphone.** Lecturer-marked attendance is the default and must work standalone.
6. **Attendance is an academic record** that influences exam eligibility. Errors have consequences for students.
7. **Pilot scope is small on purpose:** two or three programmes in one department at Sherubtse College, for one semester. Not the college. Not RUB.

### Phase 0 — Decisions before any code (produce these first, keep each under two pages)

Do not write a doctype until these are answered in writing.

**0.1 — Build-vs-reuse decision.** Assess `frappe/education` (existing Student, Program, Course, Course Schedule, Student Attendance doctypes; ~126 open issues; variable maintenance) and Moodle's `mod_attendance` (already running on the VLE with real logins, real enrolments, sessions, registers, exports, rotating-QR self-marking). For each, state what it gives free, what it cannot do, and the migration/maintenance cost. Then recommend one of: extend `frappe/education`, build a greenfield Frappe app, or use Moodle and build only what it lacks. Argue it. Do not default to greenfield because it is more fun to build.

**0.2 — Data source reality.** List every field the system needs and, for each, name where it comes from today: which registry spreadsheet, which IMS screen, which person. Flag every field with no current source — those are the ones that will be empty forever. If a field has no source and no owner, remove it from the model.

**0.3 — Written pilot agreement.** Draft a one-page agreement for the HOD and registry covering: which programmes are in the pilot; that the paper/existing register runs in parallel for the entire pilot semester; that **no student's exam eligibility is determined by this system in year one**; who is the named backup maintainer if the primary maintainer is unavailable; and what happens to the data if the pilot is stopped.

**0.4 — Three design documents only.** A data model with relationships; a permission matrix by role and doctype including field-level restrictions; an API/interface contract for the lecturer roll-call and student self-view. Nothing else. No twelve-artifact package.

Then get a Frappe instance running with **real Sherubtse enrolment data** before building any feature. The surprises are in the data.

### Architecture

```
Frappe (single custom app: rub_attendance)
├── Frappe Desk          → admin, coordinator, HOD screens (use as-is, build nothing custom)
├── One Frappe UI page   → lecturer roll-call, mobile-first, offline-capable
├── Portal page (Jinja)  → student self-view, read-only + dispute form
└── Query Reports        → all reporting and exports

Strapi + Astro (existing, separate) → college website only. No attendance data. No student data.
```

Rules: Frappe Desk is the admin UI — do not rebuild it. Build exactly one custom interactive screen (roll-call), because that is the only place UX determines adoption. Everything else is Desk views, list views, Query Reports and one Jinja portal page.

### Data model

Build the entities in the original hierarchy — University, College, Department, Programme, Cohort, Academic Year, Semester, Student, Staff, Course, Course Offering, Course Enrolment, Timetable, Class Session — with every record carrying a **College** link from day one. Multi-college support in year one is a *data model property*, not a feature set: do not build college-comparison dashboards for a single-college pilot.

Then add what the original design was missing:

- **Attendance storage:** one **Class Session** document per class, submittable, containing a child table of student rows (student, status, marked_by, marked_at, method, remark). Do **not** create one standalone document per student per session — at roughly 1.1 million rows a year for Sherubtse alone that is unmanageable in Desk and pointless. Index the child table on student, course_offering and date.
- **Attendance Summary:** a precomputed aggregate per (student, course_offering, semester) refreshed by a scheduled job. All dashboards and threshold checks read this, never raw rows.
- **Frappe Holiday List** wired to the academic calendar, so session generation skips national holidays and college closures.
- **Session lifecycle including failure paths:** Scheduled → Open → Submitted, plus **Cancelled** (with reason) and **Rescheduled**, plus the ability to create an **ad-hoc session** that was never on the timetable. A session that never happened must be distinguishable from a session where nobody was marked.
- **Excused Absence** as a real record with reason and optional evidence, not just a status value — and make marking it no harder than marking Absent.
- **Attendance Dispute** raised *by the student*, with a defined response time and escalation to a named human.
- **Attendance Correction Request** for lecturer-initiated changes *outside* the grace window.
- **Attendance Policy** as configurable records (minimum percentage, late threshold, grace window length, whether corrections need approval), scoped by programme so different programmes can differ.

**Test the model against these before freezing it:** a student repeating a module; a course taught by two lecturers; a lab or tutorial whose roster differs from the lecture; a student transferring mid-semester; a lecturer teaching at two colleges; two sections merged for one session; semester rollover.

**Data minimisation:** do not store CID unless the IMS join is proven to require it. If it is required, restrict it with field-level permissions to the registry role only.

### Attendance capture

Default and only method in v1: **the lecturer marks the register.**

The roll-call screen must:

- open in under three seconds on a mid-range Android phone over 3G;
- default every student to Present, so the lecturer taps only the exceptions;
- show a running count (Present / Absent / Late / Excused) before submission;
- **hold state locally and survive losing the network mid-class**, syncing when connectivity returns, with a clearly visible unsynced indicator;
- allow submission up to a configurable grace window (start at 24 hours) after the session.

After submission: the lecturer may still edit within 24 hours, fully logged, no approval needed. Beyond 24 hours: a correction request with approval. This is the trade-off that keeps the audit trail without making the system so annoying people abandon it.

### QR attendance — deferred, and described honestly

**Do not build QR in v1.** Revisit only after one full pilot semester of manual marking has succeeded.

When documenting it later, state this plainly and do not soften it:

> Rotating QR codes do not prevent proxy attendance. A student can photograph a code and send it to an absent classmate in a few seconds; token rotation shortens that window but does not close it. Moodle's `mod_attendance` rotating-QR feature has a substantial history of real-world defect reports from institutions attempting exactly this. QR reduces the time a lecturer spends calling names. It is not evidence of presence, and the lecturer remains accountable for the accuracy of the register.

If QR is built later, the controls that are actually worth implementing, in order: server-side validation bound to one open session; one scan per student per session; authenticated student session required; enrolment verified server-side; short token lifetime; and **one-device binding per student account** with an admin reset path — cheap, effective against mass sharing, and collects no location data. Pair it with an occasional random verbal spot-check of three names, which is more effective than any of the technical controls.

### Explicitly out of scope — requires written justification and student consultation to reopen

Geofencing. Campus Wi-Fi validation. IP-based location checks. Device fingerprinting beyond a single opaque device identifier. RFID. NFC. Biometrics. Facial recognition. Photo capture at marking.

These collect location or biometric data on students, are all defeatable by the students most motivated to defeat them, and produce false negatives that punish honest students. They are not a roadmap. Do not list them as "future enhancements."

### Permissions

Roles: RUB Academic Administrator, College Administrator, HOD, Programme Coordinator, Lecturer, Student, Registry.

- College isolation via Frappe User Permissions; department and programme cascades via `get_permission_query_conditions` and `has_permission` hooks per doctype.
- **Every whitelisted API method must use `frappe.get_list` or an explicit permission check. `frappe.get_all` bypasses permissions entirely** — treat any use of it in a whitelisted method as a security defect.
- Remember the separate leak paths: `/api/resource`, report view, and the query report engine each need testing independently.
- University-level roles see **aggregates by default**. Opening an individual student's record requires a stated reason and is written to the audit log.
- Write an automated test suite for isolation and run it in CI. At minimum: College B admin reading a College A student returns 403; a lecturer reading a course they are not assigned to returns 403; a student reading another student's attendance returns 403; the same three attempted through `/api/resource` and through report view.

### Student rights — build these, do not treat them as documentation

1. A student can see their own attendance in near-real-time, per course, with the date and status of every session.
2. A student can **raise a dispute** on any specific session directly in the system, with a defined response time and a named human who handles it.
3. Threshold warnings are informational. **The system never bars anyone from anything.** It flags; a human decides.
4. A privacy notice is shown at first login: what is collected, who can see it, how long it is kept, how to dispute, who to contact.
5. A stated retention period and a defined deletion or archival step at graduation.
6. Every access to an individual student's record above lecturer level is logged.

### Reporting and performance

All dashboards and threshold checks read the Attendance Summary table, never raw session rows. Build reports as Frappe Query Reports with CSV and Excel export — do not hand-build report UIs. Reports needed for the pilot: student's own record; lecturer's course register and missing submissions; HOD's programme summary and at-risk list.

Lecturer submission rate is an operational report a HOD can pull. It is **not** a dashboard leaderboard. Attendance systems that feel like staff surveillance get quiet non-cooperation, and lecturer non-cooperation is what actually kills them.

Do not build college-comparison or RUB-wide dashboards until a second college is genuinely running on the system.

### Operations — for a single maintainer

- **Recommend Frappe Cloud over self-hosting**, with the cost comparison. Backups, upgrades, monitoring and security patching stop being the maintainer's job. If self-hosting is chosen anyway, specify automated nightly backups to off-site storage, a monitored restore test, and a documented upgrade procedure.
- **A restore from backup must be performed and documented before go-live.** An untested backup is not a backup.
- Everything in git, including doctype fixtures. A second person must be able to stand up the system from the repository.
- A named backup maintainer identified in writing before real data is loaded.
- Separate staging and production. Never test on production.
- **The paper register stays available all pilot semester**, and nobody is asked to double-enter into both systems as a requirement.

### Roadmap — sequential, each phase must pass its check before the next begins

| Phase | Deliverable | Passes when |
|---|---|---|
| 0 | Decisions, data sources, pilot agreement, 3 design docs | HOD and registry have signed the pilot agreement |
| 1 | Core doctypes + CSV importers (validation, dry-run, idempotent upsert) | Real Sherubtse enrolment data loads clean and re-runs without duplicating |
| 2 | Timetable, holiday list, session generation, cancel/reschedule/ad-hoc | A real week of the real timetable generates correctly, holidays included |
| 3 | Roll-call screen with offline capability and grace-window edits | A lecturer marks a real class on their own phone, in the room, with Wi-Fi disabled |
| 4 | Permissions and isolation test suite | All isolation tests pass in CI, including via `/api/resource` and report view |
| 5 | Student self-view, dispute flow, summary aggregation | A student finds an error and successfully disputes it end to end |
| 6 | Reports and exports | The HOD gets the report they actually asked for, in the format they wanted |
| 7 | One-semester pilot, 2–3 programmes, paper running in parallel | End-of-semester figures reconcile with the paper register |

Only after a successful pilot semester: QR, notifications, additional colleges, IMS integration.

### Output rules

- **One phase at a time.** Do not generate the whole system. Stop at the end of each phase and wait.
- Working, runnable code. Include the `bench` commands to install and migrate. No placeholder functions, no `# TODO: implement`, no invented API surfaces.
- Include tests with each phase, especially permission tests.
- If a fact about RUB is unknown — grading rules, the real attendance threshold, semester dates, how the registry currently stores enrolment — **ask, or mark it clearly as an assumption to verify.** Do not invent university policy.
- If a requirement is wrong, unworkable or unethical, say so before implementing it.
- Prefer removing a feature over adding a configuration option for it.

### Development rules

1. Frappe is the whole system. Strapi stays on the website.
2. Never duplicate attendance data outside Frappe.
3. Never trust the frontend: validate every college, student, course, session and status server-side.
4. Never hard-code attendance policy.
5. Never allow silent modification of a historical record — log every change with who, what, when, before, after and why.
6. Never let the system automatically penalise a student.
7. Manual marking always works standalone; QR is only ever an accelerator.
8. Do not collect location or biometric data.
9. Do not build for imagined scale. Build indexes and one summary table; skip the microservices.
10. Use Frappe's native capabilities — Desk, Query Reports, Holiday List, User Permissions, Version history, scheduled jobs — rather than rebuilding them.
11. Every feature added is a feature one person maintains forever. When in doubt, leave it out.
12. Design so a second college is a data question, not a rewrite — but do not build second-college features until there is a second college.

---

## Sources

- [Colleges under RUB – Royal University of Bhutan](https://www.rub.edu.bt/index.php/colleges/)
- [frappe/education – GitHub](https://github.com/frappe/education)
- [Moodle Plugins directory: Attendance (mod_attendance)](https://moodle.org/plugins/mod_attendance)
- [Rotating QR code defect reports – danmarsden/moodle-mod_attendance issues](https://github.com/danmarsden/moodle-mod_attendance/issues/746)
- [Attendance Security and QR Codes – Moodle.org forum](https://moodle.org/mod/forum/discuss.php?d=451905)
- [Guidelines on Data Privacy and Data Protection 2021 – Royal Monetary Authority of Bhutan](https://www.rma.org.bt/media/Laws_By_Laws/Guidelines%20on%20Data%20Privacy%20and%20Data%20Protection%202021.pdf)
- [Digital Privacy: Issues and Challenges in Bhutan – Khamsum Kinley](https://kkinley.com/digital-privacy-issues-and-challenges-in-bhutan/)
