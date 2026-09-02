# Local verification tools (no bench/WSL/Docker required)

This machine has no Python, WSL, or Docker, and Frappe's `bench` CLI needs Linux. That blocked
*any* real verification of the app through Phase 6 — everything was "written correctly against
Frappe's conventions" but never actually run. This directory closes part of that gap: it lets
the app's pure-logic code and every module's import-time correctness be checked for real, on
this machine, without a database or web server.

**What this does NOT replace:** a real bench. Anything that touches the database, permissions
at runtime, or the actual Frappe framework (doctype validation hooks executing, permission
query conditions running against real data, the isolation test suite in
`test_permission_isolation.py`) still needs Phase 1's setup (Frappe Cloud or WSL). This is a
smoke test and a pure-function test runner, not a substitute for that.

## What's here

- `python312/` — a portable, embeddable Python 3.12 interpreter (official python.org
  distribution, no installer, no admin rights needed) with `pip` bootstrapped and `openpyxl`
  installed. **Gitignored — never commit this**, it's a ~15 MB third-party binary blob with no
  place in a source repo.
- `stubs/frappe/` — a minimal fake `frappe` package (throw, whitelist, a stub `db` object, a
  stub `Document` base class, `frappe.utils` date helpers). It exists ONLY so `import frappe`
  and `class X(Document):` succeed at import time on a bare interpreter. Every stubbed function
  that would need real behavior raises `NotImplementedError` with a message pointing back here
  — so a test that accidentally depends on real Frappe behavior fails loudly, not silently.
  **This is test infrastructure, not application code** — it must never be imported by the real
  app or shipped anywhere near a real bench.

## How it was set up (for reference / rebuilding)

```bash
curl -sL -o tools/python-embed.zip "https://www.python.org/ftp/python/3.12.7/python-3.12.7-embed-amd64.zip"
unzip -q tools/python-embed.zip -d tools/python312
sed -i 's/#import site/import site/' tools/python312/python312._pth
curl -sL -o tools/get-pip.py "https://bootstrap.pypa.io/get-pip.py"
tools/python312/python.exe tools/get-pip.py --no-warn-script-location
tools/python312/python.exe -m pip install openpyxl --quiet
```

Then two extra lines were appended to `tools/python312/python312._pth` (the embeddable
distribution's `PYTHONPATH` environment variable is ignored by design — this file is the only
way to extend `sys.path` for it):

```
../stubs
../../apps/rub_attendance
```

## Running the tests

```bash
tools/python312/python.exe -m unittest discover -s apps/rub_attendance/rub_attendance/tests -p "test_*.py" -v
```

As of the last run: **23 of 24 tests pass for real** (not reviewed-and-assumed — actually
executed). The one that doesn't (`test_permission_isolation`) is expected to fail here: it's an
integration test that creates real Users and impersonates them, and correctly hits a
`NotImplementedError` from the `frappe.set_user` stub — that's the stub confirming it needs a
real bench, not a bug to chase down here.

## Smoke-testing every module for import-time errors

This goes further than the test suite — it attempts to import every single `.py` file in the
app (doctype controllers, API modules, permission hooks, reports, setup scripts) and reports
any `SyntaxError`, bad import, or `NameError` at module load time:

```bash
tools/python312/python.exe -c "
import importlib, pathlib
root = pathlib.Path('apps/rub_attendance/rub_attendance')
failures = []
for pyfile in sorted(root.rglob('*.py')):
    rel = pyfile.relative_to('apps/rub_attendance')
    parts = list(rel.with_suffix('').parts)
    if parts[-1] == '__init__':
        parts = parts[:-1]
    if not parts:
        continue
    try:
        importlib.import_module('.'.join(parts))
    except Exception as e:
        failures.append((parts, type(e).__name__, str(e)))
print(f'{len(failures)} failures')
for f in failures: print(f)
"
```

Last run: **all 69 files imported cleanly.** This does not prove the code is correct — it
proves there are no syntax errors, no typos in cross-module references, and every class/function
referenced at import time actually exists where it's expected. That's a real, meaningful floor
that nothing before this had verified.
