# 0 · THE MAP

> **This is a MOLD.** The structure, the section anchors and the table formats are the real ones:
> `scripts/mapa-hook.sh` and `scripts/porta.py` parse them. The content describes an invented
> project (*a small web app with a worker queue*) so every anchor exists and the selftests have
> something to measure. Replace the content; keep the anchors, or change them together with the
> scripts.
>
> **The order is the hierarchy:** who we are → where we are → what was already decided → what we
> are doing.

---

## The 4 layers

| # | layer | what it answers | nature | loaded? |
|---|---|---|---|---|
| **1** | [`1_CONTRATO.md`](1_CONTRATO.md) | **WHO WE ARE** — *method* rules: who decides, what is already authorized, how work is done | almost immutable | ✅ whole |
| **2** | [`2_ONDE.md`](2_ONDE.md) | **WHERE WE ARE** — machines, ports, paths, databases | changes with the hardware | ✅ whole |
| **3** | [`3_DECIDIDO.md`](3_DECIDIDO.md) | **WHAT WAS ALREADY DECIDED** — *product* law, one row per decision, with a state | changes by pivot | ✅ whole |
| **4** | [`4_FRENTES.md`](4_FRENTES.md) | **WHAT WE ARE DOING** — current work | changes every week | ❌ index + trigger |
| — | [`5_COMO_MANTER.md`](5_COMO_MANTER.md) | **how the map is kept** — where each thing goes, how a project is born, what is never deleted | process | ❌ read when writing |

### Why 1–3 load and 4 does not

The first three are **state facts**. A state fact competes with nothing: either it is loaded and the
agent knows it, or it is not. Layer 4 is **work state** — it grows every week, and loading more of it
does not help: a behaviour rule loaded next to a task competes with the task and loses.

> **Budget: the initial load fits in a fixed number of SLICES** (`MAX_FATIAS` in the hook). The
> runtime truncates a single hook output above ~10,000 characters, so the map arrives in slices of up
> to 9,500 B, all in the first turn. Past the slice budget it is time for the REVOLVING DOOR
> ([`5_COMO_MANTER §5`](5_COMO_MANTER.md)): for something to enter, something leaves.
> `bash scripts/mapa-hook.sh --selftest` always says how much room is left, **in laws**.

### The border between 1 and 3

**Method × product.** *"Production changes go through staging first"* is layer 1 — it holds in any
project. *"Jobs are retried at most three times"* is layer 3 — it holds in this product and can be
revoked tomorrow.

### Only layer 3 has state

The others are corrected in place. Layer 3 has **history**: a decision that falls becomes `REVOKED`
**with the reason**, and is never deleted. The dead row is the asset — it is what stops someone from
re-proposing what was already rejected.

---

## How the map relates to the rest

- **Technical truth stays in the docs.** In a conflict of FACT, the detailed doc wins; in a conflict
  of LAW, the map wins (it is the one that always arrives).
- **The map does not replace docs; it solves *entry*.** The problem is rarely a wrong doc; it is not
  opening it at the right moment. This one is loaded by a hook.
- **The map is ONE channel, not the system.** The whole is in [`docs/HIPOCAMPO.md`](../HIPOCAMPO.md)
  and the channels in [`docs/CONTEXTO.md`](../CONTEXTO.md).
