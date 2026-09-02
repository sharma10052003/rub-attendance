# Phase 1 — Setup, Running the Import, and What "Passes" Means

> **CI status (2026-09-02): green.** [`.github/workflows/ci.yml`](../.github/workflows/ci.yml)
> now installs this app on a real Frappe bench (MariaDB + Redis, GitHub-hosted) and runs
> `test_import_students` for real — not just reviewed. The doctype schemas (College through
> Course Enrolment) are proven to sync cleanly. **Still not CI-covered:** actually running
> `import_rosters` against the real `Student Data 2026/` spreadsheets — that needs a site with
> real data, per the checklist below.

## What's built

`apps/rub_attendance/` — a complete Frappe custom app: 12 doctypes (College, Department,
Programme, Academic Year, Semester, Cohort, Student, Lecturer, Course, Course Offering,
Course Offering Lecturer, Course Enrolment) plus the 7 roles from SPEC.md, plus a student
roster importer (`rub_attendance/setup/import_students.py`) with dry-run mode, idempotent
upsert, and pure-function tests.

**This machine has no Python, WSL, or Docker** — `bench` (Frappe's CLI) cannot run natively on
Windows, so nothing above has been executed or tested against a real database yet. The code is
written correctly against Frappe's actual doctype/controller conventions, but "written
correctly" and "verified running" are different claims — don't take Phase 1 as done until
you've actually run it, per one of the two paths below.

## Path A — Frappe Cloud (recommended; SPEC.md's own preference for a one-person maintainer)

No local bench install at all. Frappe Cloud builds and hosts the site from a git repo.

1. Push `apps/rub_attendance` to a git repo (GitHub/GitLab — private is fine).
2. Frappe Cloud → New Bench → attach that repo as a custom app → New Site → install
   `rub_attendance` on it.
3. Use the site's **Console** (or their bench-in-browser SSH) to run the importer commands
   below.
4. Backups, upgrades, and monitoring are handled by Frappe Cloud from day one — this directly
   satisfies the SPEC.md operations requirement for a single maintainer.

## Path B — Local dev via WSL (if you want a local dev/staging environment too)

```bash
wsl --install
# after reboot, inside the WSL Ubuntu shell:
sudo apt update && sudo apt install -y python3-dev python3-pip python3-venv mariadb-server redis-server
pip install frappe-bench
bench init rub-bench --frappe-branch version-15
cd rub-bench
bench new-site sherubtse.local
# copy or symlink apps/rub_attendance from this Windows folder into rub-bench/apps/rub_attendance
bench get-app file:///mnt/c/Users/MATRIKA/Desktop/attendence\ system/apps/rub_attendance
bench --site sherubtse.local install-app rub_attendance
bench --site sherubtse.local migrate
```

## Before importing any real students

The importer deliberately will not create Programme/Department/College records — that's a
judgment call for a person. In Desk (or via `bench console`), create in this order:

1. One **College** record for Sherubtse.
2. **Department** record(s) — you'll need to tell me (or fill in yourself) which department
   owns DSDA, DCPM, EPS, Mathematics, Chemistry, Physics, and Life Science. I don't have this
   mapping and won't guess it.
3. One **Programme** per programme, with `programme_code` matching `KNOWN_PROGRAMMES` in
   `import_students.py` (`DSDA`, `DCPM`, `EPS`, `MATH`, `CHEM`, `PHY`, `LFSC`).

## Running the import

```bash
# Dry run first — writes nothing, just reports what it would do.
bench --site sherubtse.local execute rub_attendance.setup.import_students.import_rosters \
    --kwargs "{'source_dir': '/mnt/c/Users/MATRIKA/Desktop/Student Data 2026', 'dry_run': True}"

# Read the report. Fix any file in files_skipped or row in row_errors — most
# commonly a missing Programme record, or a filename the parser can't read
# (KNOWN_PROGRAMMES doesn't recognize it, or no year found anywhere).

# Once the dry-run report looks right:
bench --site sherubtse.local execute rub_attendance.setup.import_students.import_rosters \
    --kwargs "{'source_dir': '/mnt/c/Users/MATRIKA/Desktop/Student Data 2026', 'dry_run': False}"

# Re-run any time — it's an upsert keyed on student_id, never duplicates.
```

Run it against both `Student Data 2026/` and `New Student Data/2026 batch/` — they're
overlapping/parallel folders per phase0/02-data-sources.md, and re-running is safe.

## Running the tests

```bash
bench --site sherubtse.local run-tests --app rub_attendance --module rub_attendance.tests.test_import_students
```

**Update:** these have now actually been run — not just reviewed — using a portable Python
interpreter and a stub `frappe` package (no bench needed for pure-logic tests; see
[tools/README.md](../tools/README.md)). All pass, including the two real Excel gotchas this
suite exists to catch (leading-zero student IDs, filename-vs-title-text year fallback). The
`bench run-tests` command above is still the one to run once a real site exists — it's the
authoritative version — but this is no longer untested code.

These cover the parsing/normalization logic only (programme identification, student ID
zero-padding, gender normalization, the filename-vs-title-text fallback) — no database
required. They do **not** cover the doctype layer (validate() hooks, uniqueness checks) —
that needs a real site and is worth adding once Phase 1 is actually running, before Phase 2
starts.

## What "Phase 1 passes" actually requires (per SPEC.md's roadmap table)

> "Real Sherubtse enrolment data loads clean and re-runs without duplicating."

Concretely, before calling Phase 1 done:

- [ ] Bench running somewhere real (Frappe Cloud or WSL) with `rub_attendance` installed.
- [ ] College, Department(s), Programme(s) created by a person, department mapping confirmed.
- [ ] Dry-run report against `Student Data 2026/` reviewed — zero unexplained `files_skipped`.
- [ ] Real import run once — student count matches the roster files' actual row counts.
- [ ] Real import run a **second time** — `students_created_count` is 0 the second time,
      `students_updated_count` reflects only genuine changes, no duplicate Student records.
- [ ] Same two-run check against `New Student Data/2026 batch/`.
- [ ] Pytest/bench test suite passes.

I can't check any of these boxes myself without a running bench — this is the part that needs
you (or a WSL/Frappe Cloud session I can drive once one exists).
