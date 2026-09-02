"""
before_install runs before doctype/permission sync during `bench install-app`
(and before `bench migrate` re-syncs an already-installed app). Our custom
roles (HOD, Registry, RUB Academic Administrator, etc.) are declared as
fixtures in hooks.py, but fixtures import happens AFTER doctype sync in
Frappe's install sequence — and doctype sync is exactly where each
doctype's `permissions` list gets written as DocPerm rows, each with a
`role` Link field. A Role that doesn't exist yet fails that Link's
validation. Creating the roles here, before sync_for runs, closes that gap
— this is a known ordering issue with custom roles in doctype JSON
permissions, not specific to this app.

Kept idempotent (frappe.db.exists check) so it's harmless on `bench
migrate` re-runs and doesn't fight the fixtures import that still runs
afterward and keeps these in sync with hooks.py's fixture list.
"""

import frappe

CUSTOM_ROLES = [
	{"role_name": "RUB Academic Administrator", "desk_access": 1},
	{"role_name": "College Administrator", "desk_access": 1},
	{"role_name": "HOD", "desk_access": 1},
	{"role_name": "Programme Coordinator", "desk_access": 1},
	{"role_name": "Lecturer", "desk_access": 1},
	{"role_name": "Student", "desk_access": 0},
	{"role_name": "Registry", "desk_access": 1},
]


def before_install():
	for role in CUSTOM_ROLES:
		if not frappe.db.exists("Role", role["role_name"]):
			frappe.get_doc({"doctype": "Role", **role}).insert(ignore_permissions=True)
	frappe.db.commit()
