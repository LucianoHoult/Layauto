"""v2 pipeline orchestration boundary.

This module is reserved for the Stage 1-6 orchestration described in
``docs/architecture.md``. It should wire public APIs from importers,
annotation, state, planning, constraints, transactions, derive, export,
and validation without owning domain logic or mutating exported artifacts.
"""
