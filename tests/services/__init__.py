"""Services-layer tests subpackage.

Module-scope fixtures (see tests/seed_fixtures.py `seeded_user`) need this
subpackage marker so each test module has its own isolated scope; without
the `__init__.py`, pytest would flatten discovery and share fixture state
across unrelated service tests.
"""
