---
id: 2
name: feedback_guard_must_fail
description: A guard is trusted only after it was seen failing on a named mutant
type: feedback
escopo: metodo
prova: 1
---
Every new guard ships with a control that is green and a mutant that is red.

**Why:** a guard that was never seen red may be green by construction.

**How to apply:** add the fixture in fixtures/guards/ in the same change as the guard.
