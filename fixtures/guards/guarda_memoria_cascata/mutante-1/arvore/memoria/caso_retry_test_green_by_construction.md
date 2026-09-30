---
id: 6
name: caso_retry_test_green_by_construction
description: Case: the retry test that could not fail because the queue was mocked away
type: feedback
escopo: ci
regra: feedback_guard_must_fail
---
The retry test mocked the queue, so the retry cap was never exercised.

**Why:** a mocked dependency cannot break the rule under test.

**How to apply:** the mutant now removes the cap and the test goes red.
