"""
Minimal stand-in for the `frappe` package, used ONLY to run this project's
pure-function unit tests on a bare Python interpreter, on a machine with no
bench/MariaDB/Redis available (see phase1-6 setup docs).

This is test infrastructure, not application code — it is not part of the
rub_attendance app and must never be shipped or imported by it in a real
bench. Every attribute below is a stub: it exists so `import frappe` and
`class X(Document)` succeed at import time. None of it is called by the
pure functions the test suites actually exercise — if a test starts
calling into one of these stubs for real behavior, that test belongs in a
real bench's `run-tests`, not here.
"""


class PermissionError(Exception):
	pass


class ValidationError(Exception):
	pass


class Redirect(Exception):
	pass


def throw(msg, exc=None):
	raise (exc or ValidationError)(msg)


def whitelist(*args, **kwargs):
	def decorator(fn):
		return fn

	return decorator


def parse_json(value):
	import json

	return json.loads(value) if isinstance(value, str) else value


class _UnimplementedStub:
	"""Any attribute access returns a callable that raises — so a test that
	accidentally exercises real frappe behavior fails loudly and clearly,
	instead of silently doing nothing. `escape` is a real (simplified)
	implementation — real frappe.db.escape is just quote-and-escape, safe to
	reproduce here, and several pure SQL-condition-building functions
	(rub_attendance/permissions.py) call it directly with no other DB access,
	so stubbing it for real lets those functions run under this harness."""

	def escape(self, value, percent=True):
		return "'" + str(value).replace("\\", "\\\\").replace("'", "\\'") + "'"

	def __getattr__(self, name):
		def _unimplemented(*args, **kwargs):
			raise NotImplementedError(
				f"frappe.db.{name} is not implemented in the local test stub — "
				f"this test needs a real bench (see phase*/00-setup-and-verification.md)"
			)

		return _unimplemented


db = _UnimplementedStub()


def get_doc(*args, **kwargs):
	raise NotImplementedError("frappe.get_doc needs a real bench")


def get_list(*args, **kwargs):
	raise NotImplementedError("frappe.get_list needs a real bench")


def get_all(*args, **kwargs):
	raise NotImplementedError("frappe.get_all needs a real bench")


def get_roles(user=None):
	return []


def set_user(user):
	raise NotImplementedError(
		"frappe.set_user needs a real bench with a real database — this test "
		"(test_permission_isolation) is an integration test, not a pure-logic "
		"one; this stub confirms that, it doesn't need fixing"
	)


class _Session:
	user = "test@example.com"


session = _Session()
