<!-- THE DESK'S DESIGN: the resident of the OPEN. Read when the `desenho` skill is invoked. Rule: it is the NOW, not a log. -->
# THE DESIGN: what was decided to build, and how (state of the drawing boards)

> **What it is:** the resident of the OPEN. The map carries what is CLOSED (law, fact, yardstick)
> and the index carries the VERDICT; no channel carried the DESIGN (what was decided to build and
> how), so brainstorms started out of date. This file is that channel, loaded by
> [`skills/desenho/SKILL.md`](../../skills/desenho/SKILL.md).
> **Maintenance rule (same as the baton):** the desk updates it on EVERY design event: board
> opened · closed by the operator · in construction · waiting on the operator. One line per board,
> signed with the session's short id. Dead state leaves immediately. **The operator's orders, work
> state and the queue do NOT live here**; they live in [`BASTAO.md`](BASTAO.md). What lives here is
> what was DESIGNED and where the design is.
> **Life test:** a coverage guard in both directions (a line with no file · a file with no line).
> If the guard is green and the file is wrong after a few weeks, this file dies.

*Updated: 2026-01-15 17:40 -- the time comes from `date`, never from memory*

<!-- MOLD: the sections below are invented examples. One section per product or area; one line per
board. Line form:  - `path/to/board.md` -- **STATE (date)**: what was decided, in one sentence ·
door: what reopens it  <signature> -->

## THE SYSTEM ITSELF (memory and tooling)
- `_proposals/INDEX_CEILING_WARNING.md` -- **OPEN**: warn at 80% of the index ceiling, not at 100%; the number of lines is the unit shown · door: the measurement of how fast the index grows per week `a1`
- `mesa/BRIEFING_BATON_CUT.md` -- **CLOSED (2026-01-12): built and proven on a real compaction**: the compaction hook emits a cut under the preview threshold, so it arrives whole `a1`
- `HIPOCAMPO.md` -- **CLOSED (2026-01-10)**: the umbrella doc; every owner doc points back to it `b7`

## WEB APP (example product)
- `web-app/andamento/CHECKOUT_RETRY.md` -- **IN CONSTRUCTION**: a failed payment retries once after 30 s, then shows the error; the worker has the briefing · door: the gate on the test environment `b7`
- `web-app/andamento/SEARCH_RANKING.md` -- **WAITING ON THE OPERATOR**: two rankings drawn, the choice is a product decision · door: his pick between A and B `a1`

**Reference: not design, but what the design consults**
- `web-app/andamento/USAGE_EXPORT.md` -- **REFERENCE**: one month of anonymized usage counts, input for the ranking board `b7`

## SERVICE-A (example service)
- `service-a/README.md` -- the design lives in that repository, not here (pointer only) `a1`
