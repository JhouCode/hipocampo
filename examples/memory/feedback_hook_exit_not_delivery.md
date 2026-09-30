---
name: feedback_hook_exit_not_delivery
id: 3
description: "A hook that exits 0 proves the hook RAN, not that its text reached the model; delivery is proved by the text showing up in the transcript"
metadata:
  node_type: memory
  type: feedback
  escopo: tooling
---
A hook that prints context and exits 0 is logged as a success by the runtime. That success is
about the PROCESS: it started, it wrote to stdout, it returned 0. It says nothing about whether
the text was injected, truncated, or dropped on the way to the model.

**Why:** an output over the per-hook size cap, a wrong JSON shape, or a hook event that does not
accept additional context all end the same way: exit 0, green in the log, and nothing delivered.
The emitter's log cannot see the receiver.

**How to apply:**
- Prove a new hook by finding a unique marker of its output in the session transcript, not by
  reading its own exit code or log line.
- Measure the output size against the cap in the same units the runtime uses before trusting it.
- A hook whose only evidence is "hook_success" is unproved; say so instead of calling it working.
