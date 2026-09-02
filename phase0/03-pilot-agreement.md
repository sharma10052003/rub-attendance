# Phase 0.3 — Pilot Agreement (Draft — needs HOD/registry sign-off)

**This is a draft for you to review, edit, and take to the HOD and registry. It is not yet
agreed by anyone but you. Fields in brackets need a name or a decision before this is sent.**

---

## RUB Attendance System — Pilot Agreement

**Prepared by:** [your name], ICT/ITSU, Sherubtse College
**Date:** [date sent for sign-off]
**Pilot semester:** [Autumn 2026 / Spring 2027 — pick one]

### 1. Scope

The pilot covers the following programmes and sections only:

- [Programme 1, e.g. "BSc in Data Science and Data Analytics, Year 1, Sections A & B"]
- [Programme 2 — optional]

No other programme, department, or college is included. This is not a Sherubtse-wide or
RUB-wide rollout.

### 2. What runs in parallel

The existing paper/manual attendance register **continues to be used as the official record
for the entire pilot semester**, without exception. The digital system is being tested
alongside it, not replacing it yet. Lecturers are not required to keep two full attendance
processes in perfect sync — the paper register is authoritative; the digital one is under
evaluation.

### 3. What this system does not do (in year one)

- **No student's exam eligibility is determined by this system during the pilot.** The 80%
  (or whatever the actual policy threshold is — [confirm the real number with the registry])
  attendance requirement continues to be assessed from the paper register only.
- The system will surface attendance percentages and low-attendance flags for visibility, but
  these are informational. A human (HOD/coordinator) makes any eligibility decision, using the
  existing process.

### 4. Data

- Student names, student IDs, and class attendance records for the pilot programmes/sections
  will be stored in the system.
- [Confirm: will CID be stored? Default position per SPEC.md is *no*, unless there's a proven
  need — flag this explicitly so the HOD knows it's being deliberately excluded.]
- Data is not shared with or visible to the college's public website, Moodle, or any other
  system — this is a standalone application.
- A named person (see §6) is the point of contact for any student who wants to know what's
  recorded about them or wants it corrected/removed.

### 5. If the pilot is stopped

If the pilot is discontinued for any reason, [default proposal: attendance data collected
during the pilot is retained for one semester after the pilot ends in case of dispute, then
archived or deleted — confirm the actual retention decision with the registry] and no
follow-on decision (grading, eligibility, disciplinary) will be based on incomplete pilot data.

### 6. Roles

| Role | Name | Responsibility |
|---|---|---|
| Primary maintainer | [you] | Builds and runs the system, first point of contact for lecturers/students |
| **Named backup maintainer** | **[MUST be filled before go-live per SPEC.md — who covers this if you're unavailable?]** | Can access backups, restart the system, and hand off support if the primary maintainer is unreachable |
| HOD sponsor | [name] | Approves pilot scope, receives reports, makes any eligibility calls |
| Registry contact | [name] | Confirms enrolment data, handles disputes escalated beyond the maintainer |

### 7. Sign-off

- HOD: ______________________ Date: __________
- Registry: ______________________ Date: __________
- ICT/Primary maintainer: ______________________ Date: __________

---

**Note to self (not part of the document sent for sign-off):** §6's backup-maintainer row is a
hard blocker per SPEC.md — "a named backup maintainer identified in writing before real data is
loaded." Do not load real student data into a running instance until that name is filled in.
