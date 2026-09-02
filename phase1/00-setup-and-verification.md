# Phase 1 — Setup, Running the Import, and What "Passes" Means

> **CI status (2026-09-02): green.** [`.github/workflows/ci.yml`](../.github/workflows/ci.yml)
> now installs this app on a real Frappe bench (MariaDB + Redis, GitHub-hosted) and runs
> `test_import_students` for real — not just reviewed. The doctype schemas (College through
> Course Enrolment) are proven to sync cleanly. **Still not CI-covered:** actually running
> `import_rosters` against the real `Student Data 2026/` spreadsheets — that needs a site with
> real data, per the checklist below.

## What's built

`rub_attendance/` (repo root) — a complete Frappe custom app: 12 doctypes (College, Department,
Programme, Academic Year, Semester, Cohort, Student, Lecturer, Course, Course Offering,
Course Offering Lecturer, Course Enrolment) plus the 7 roles from SPEC.md, plus a student
roster importer (`rub_attendance/setup/import_students.py`) with dry-run mode, idempotent
upsert, and pure-function tests. **This app lives at the repo root on purpose** — it used to be
nested under `apps/rub_attendance/`, moved out specifically because Frappe Cloud and
`bench get-app` both expect to find `pyproject.toml` and the app package directly at the
repository root when adding a custom app from a git URL.

**Update:** this is no longer untested. [`.github/workflows/ci.yml`](../.github/workflows/ci.yml)
installs this app on a real Frappe bench (MariaDB + Redis, GitHub-hosted) on every push and it's
green — see the CI status note at the top of this doc. What CI does *not* prove is that it works
on **your** deployment target with **your** real data — that's what the two paths below are for.

## Path A — Frappe Cloud (recommended; SPEC.md's own preference for a one-person maintainer)

No local bench install at all. Frappe Cloud builds and hosts the site from this same git repo.

1. Sign up at [frappecloud.com](https://frappecloud.com) (a free trial is available) — this step
   needs a human, nobody else can do it for you.
2. Frappe Cloud → New Bench → Add App → **Custom App** → paste this repo's URL
   (`https://github.com/sharma10052003/rub-attendance`), branch `master`. It should detect
   `rub_attendance` automatically since `pyproject.toml` is right at the repo root now.
3. New Site → install `rub_attendance` on it.
4. Use the site's **Console** (or their bench-in-browser SSH) to run the importer commands
   below.
5. Backups, upgrades, and monitoring are handled by Frappe Cloud from day one — this directly
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
# clone this repo (or copy it from the Windows filesystem) so its root is the app:
git clone https://github.com/sharma10052003/rub-attendance.git /tmp/rub-attendance
cp -r /tmp/rub-attendance apps/rub_attendance
./env/bin/pip install -e apps/rub_attendance
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
