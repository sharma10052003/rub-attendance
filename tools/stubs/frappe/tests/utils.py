import unittest


class FrappeTestCase(unittest.TestCase):
	"""Stub — real isolation tests need a real bench/database and will fail
	loudly here via the frappe.db stub's NotImplementedError, which is
	correct: this file exists so the module IMPORTS cleanly for local
	syntax/logic sanity, not so the isolation suite passes without a DB."""

	pass
