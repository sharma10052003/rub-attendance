# Phase 0.2 — Data Source Reality

Based on direct inspection of files already on this machine (not assumptions):

- `Desktop\Student Data 2026\` — 11 spreadsheets, one per programme/section, e.g.
  `1.BSc in DSDA Section A.xlsx`, `3.BA in DCPM Year 1 Sem. I - Autumn 2026.xlsx`, plus
  `New admission with student numbers.xlsx` (a combined admissions master).
- `Desktop\New Student Data\2025 batch\` and `\2026 batch\` — same shape, organized by intake
  year.

These are **real 2026 Sherubtse enrolment rosters**, not samples. Columns actually observed:

## Fields with a known source today

| Field | Source file/column | Notes |
|---|---|---|
| Student ID | `Std. No.` / bare 8-digit values (e.g. `07260124`) in the section rosters | Looks like the RUB-wide student number. Treat as the natural key for upsert. |
| Full name | `Name` (section rosters) / `First Name` (admissions master) | Section rosters have one combined name field; admissions master splits it. These two files are not the same schema — reconciling them is Phase 1 work. |
| Gender | `Gender` column, values `F`/`M` in rosters, `Female`/`Male` in admissions master | Two different value encodings for the same field — normalize on import. |
| Programme | Encoded in the **filename and a sheet title string**, e.g. `"BSc in DSDA - Year 1 Sem. I -Section A - Autumn 2026"` | Not a clean column — it's a composite of Programme + Year + Semester + Section + Academic Term baked into one string. The importer must parse this, not just read a "Programme" cell. |
| Section (A/B) | Same composite string / filename | Same caveat. |
| Scholarship type | `Scholarship Type` (admissions master): Leadership Scholarship / Government Scholarship / Self Funding; `Scholarship` (section rosters, values like `Self`) | Present but not required for attendance — noted for completeness, not part of the attendance data model. |
| CID / Identification | `Identification Type`, `CID`, `CID/Passport Number/Document Card` columns exist in admissions master | **Header exists; did not verify populated values are present for every row.** If sparsely filled, do not make it a required field — see SPEC.md's data-minimisation rule: don't store CID unless an IMS join proves it's required. |
| Old Student ID / re-admission flag | `Old Student ID`, `Is Existing Student` (admissions master) | Relevant for repeat/transfer students (a case SPEC.md explicitly says to test the model against). |

## Fields the attendance system needs that have **no source found yet**

These are the ones that will be empty forever unless someone names where they come from —
per SPEC.md: "If a field has no source and no owner, remove it from the model" until answered.

- **Course catalog** (course codes/titles, credit hours, which courses belong to which
  programme/semester) — the files found are *student rosters per programme+section*, not a
  *course list*. No course-to-programme mapping exists in what's on disk.
- **Course offering ↔ lecturer assignment** — no file names an instructor for any course.
- **Timetable** (day/time/room per course offering) — not present in any file inspected.
- **Student email / login identity** — no email or username column seen in either the section
  rosters or the admissions master. This matters because Frappe's `Student` doctype needs
  something to link to a `User` for portal login (student self-view, disputes). **Open
  question, needs an owner:** does RUB IMS issue institutional emails, or do we mint
  `<student_id>@placeholder>` accounts?
- **Academic Year / Semester as structured records** — currently only exists baked into sheet
  title strings ("Autumn 2026", "Spring 2026", "Year 1 Sem. I").
- **Department / HOD assignment** — not present in the files found.

## What this means for Phase 1

1. The importer's first and hardest job is **parsing the composite title string** into
   Programme / Year / Semester / Section / Term — this is not a simple column-mapped CSV
   upsert, it needs a small parsing step with validation and a dry-run report showing what it
   parsed, before touching the database.
2. Course catalog, offerings, lecturer assignments and timetable have **no digital source at
   all** right now. Before Phase 1 can load anything beyond students, someone needs to name who
   owns this data — almost certainly a conversation with the HOD/registry about how courses,
   sections and lecturer assignments are currently recorded (even if it's just another
   spreadsheet not yet in this folder, or something that only exists in the IMS/AIMS system).
3. Two schemas for the "same" student data already disagree (section rosters vs. admissions
   master: different name-splitting, different gender encoding). The importer needs to treat
   these as two separate source formats, not one.

**Update (resolved 2026-09-02):**

- **Course/timetable source:** https://sherubtsett.vercel.app/ — a live timetable viewer for
  Sherubtse showing programme/group views, instructor schedules, and room bookings by
  day/time. Its view naming ("days_vertical") matches the output convention of **FET (Free
  Timetabling Software)**, a common open-source scheduler — which strongly suggests the actual
  source of truth is a `.fet` file (XML) maintained by whoever builds the timetable each
  semester, and this site is a static HTML export of it. **Action for Phase 1:** before writing
  an HTML scraper against the published site (fragile, breaks if the export template changes),
  ask whoever maintains the timetable whether the underlying `.fet`/XML file (or its CSV export)
  can be shared directly — that's a far more stable and complete import source than scraping
  rendered HTML. If it's genuinely not obtainable, scraping the four view types (programme,
  group, instructor, room) is the fallback.
- **Student login identity:** RUB issues institutional email/credentials. Student portal
  accounts will be created against institutional email as the login identity — confirm the
  exact domain/format (e.g. `student_id@rub.edu.bt` or similar) before Phase 1's importer writes
  `User` records.
