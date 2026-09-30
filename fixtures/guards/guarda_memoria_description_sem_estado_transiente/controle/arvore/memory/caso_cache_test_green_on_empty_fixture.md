---
id: 3
name: caso_cache_test_green_on_empty_fixture
description: Case: the cache test that stayed green because its fixture was empty
type: feedback
escopo: ci
regra: feedback_guard_must_fail
---
The cache test asserted "no stale entry" over a fixture with zero entries.

**Why:** zero entries cannot hold a stale one, so the test could not fail.

**How to apply:** the fixture now carries one stale entry in the mutant.
