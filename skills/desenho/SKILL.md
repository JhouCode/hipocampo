---
name: desenho
description: Information skill for the DESK (the session where the operator thinks: brainstorm, drawing board, design decisions). Invoke when opening any brainstorm, drawing board or design decision. It loads the DESIGN (docs/mesa/DESENHO.md, the OPEN items), makes the session declare its MODE before producing anything, and fixes the desk's borders (it thinks, designs and writes briefings; it does NOT operate).
---

# Desenho: the information the desk was missing

The desk is a **session**, not a role played by a sub-agent. What it lacked was information: the
map carries what is CLOSED (law, fact, yardstick) and the index carries the VERDICT, but no channel
carried the DESIGN, meaning what was decided to build and how. Without it, a brainstorm started
out of date. This skill is that channel. The model it assumes: **the desk session thinks and
designs; the worker session operates.** See [`docs/HIPOCAMPO.md`](../../docs/HIPOCAMPO.md),
section 6.

## 1 · The first act: read the OPEN

| read | what | why |
|---|---|---|
| `docs/mesa/DESENHO.md`, **whole** | what was decided to build and how; the state of each drawing board | it is the only surface that carries the OPEN; the map and the index carry only the CLOSED |
| `docs/mesa/BASTAO.md`, whole, if the subject touches work in flight | work state, queue, the operator's orders | reading a truncated baton once made the desk tell the operator that his work had stopped when it had not |
| `docs/HIPOCAMPO.md`, if the subject is the agent's memory | how the memory works: pieces, regimes, who does what | it is the whole; each owner doc has only its own piece |
| `docs/gatilhos/backlog.md`: the rules whose regex matches the FILES the piece will touch, **before writing the piece** | what the operator already revoked on that path | the debt hook fires on the WORKER's touch, after the briefing was approved; a design drawn on top of a revoked rule is caught too late, and the same mechanism repeated three times before this line existed |
| the drawing board the subject cites | the design itself | theorizing without opening the board turned a closed design back into an open hole |

## 2 · Declare the MODE before producing

The operator works in modes: **decide · clarify · theorize · check · test**. Producing in the wrong
mode costs the operator a correction; once, 18 minutes into a session, he had to say *"don't write
anything yet, this is a brainstorm"*. The desk's opening **states in one line which mode it is in**
and what that mode cuts. Brainstorm means the operator reads and annotates; what he did not comment
on he either agrees with or does not see as a problem; no flattery, no pivoting.

## 3 · The borders: the desk thinks, it does NOT operate

- **Building goes through a BRIEFING, verbatim:** the desk writes a self-contained mission (a file
  in `docs/mesa/`, or a hand-off file next to the work) and the WORKER session launches the
  builder and runs the gate. The desk does not re-distill what the worker returns; it reads the
  baton.
- **Validation the desk may launch:** reviewer sub-agents, read-only, to check a design or a
  claim before it becomes a briefing.
- **Reading and measuring are free where the contract allows. Production is not touched from the
  desk.**
- **Map layer 3 changes only by the operator's decision. Memory is written only in the
  post-mortem, with the proof pasted.**
- What the desk writes: drawing boards (proposals, work-in-progress docs), `DESENHO.md`, briefings.
  TRUTH = DOC, ERROR = VERSIONED: the autopsy of the desk's own mistake goes into the commit
  message, never into the living doc.

## 4 · Keep DESENHO.md

Same rule as the baton: **it is the NOW, not a log.** Update it on EVERY design event: board opened
· closed by the operator · in construction · waiting on the operator. One line per board, signed
with the session's short id. The operator's orders, work state and the queue **do not live here**;
they live in the baton. A coverage guard in both directions (a line with no file, a file with no
line) is worker work; until it exists, the question *"is everything here?"* is the desk's at every
opening.

## 5 · How a design line is written

**A design line SETS an order; it does not fill a gap.** The structure (the ladder, the table)
already states things; prose that re-explains what the structure implies is fat. The operator's
literal words live in the header or in the commit, never swelling a cell.

*"Next step"* comes in 3 blocks, and block 2 (*what I need from you*) is always present, even when
empty. Each request in block 2 carries CONTEXT: what the thing is in the operator's words (not an
acronym), why now, what changes with yes and with no, and the desk's recommendation. A bare code
is not something the operator recognizes. And each request says **WHERE** he answers: **here**, in
the desk's window, or in another tool's window, and if so, whether it is **a new conversation** or
**the same one**.
