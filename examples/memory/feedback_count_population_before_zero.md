---
name: feedback_count_population_before_zero
id: 2
description: "A zero is only a result when the population it was counted over is known and non-empty; count the population first, then the hits"
metadata:
  node_type: memory
  type: feedback
  escopo: metodo
  prova: 1
---
"0 errors", "0 matches", "0 orphans" read as good news. But a zero has two causes that look
identical in the output: nothing in the population had the property, or the population itself
was empty (wrong directory, broken filter, a query that matched no rows before counting).

**Why:** a counter over an empty set is green by construction. The instrument cannot tell you it
is looking at nothing; only a second number, the size of what it looked at, can.

**How to apply:**
- Every count is reported with its population: "0 of 1,204 requests", never a bare "0".
- If the population is 0, the verdict is "not measured", not "clean".
- Plant one known positive in the population and check that the counter finds it before you
  trust its zero.

Case: [[caso_service_a_zero_errors]]
