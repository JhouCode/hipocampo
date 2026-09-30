# THE ORACLE — the entry contract of the area rulers

> **What it is:** the ruler of an area (a "front"), injected **before** the work starts, not
> checked after. Engine: [`scripts/oraculo.py`](../../scripts/oraculo.py); one source file per
> front in this directory. The idea behind it: *checking is an expensive proof, and it becomes cheap
> when you KNOW how the thing was built.*
>
> **This file is the explicit contract of the format.** Without it, whoever feeds a source derives
> the format by imitation — and guessing a format is how two sources start to diverge.
>
> The files next to this one are a **mold**: the format is real, the rules are generic examples.
> The whole system is described in [`docs/HIPOCAMPO.md`](../HIPOCAMPO.md).

---

## 0 · How it works

Two channels, because one does not reach:

| channel | hook | matches | declared in the source as |
|---|---|---|---|
| **A** | `UserPromptSubmit` | the owner's TEXT, when it names the front | `<!-- when-matches: REGEX -->` |
| **B** | `PostToolUse` | the agent's COMMAND or edited path, on the FIRST touch of the front | `<!-- when-touches: REGEX -->` |

Text alone misses most of the work: people describe a SYMPTOM, and the front only appears when the
agent opens a file. Channel B is `PostToolUse` and not `PreToolUse` because `PreToolUse` has no
`additionalContext` (it is a channel to BLOCK, not to speak — see `docs/gatilhos/CANAIS.md`). So the
ruler arrives **after the first command of the front**, and that is declared, not hidden.

Channel B looks at what a command TOUCHES, never at what it MENTIONS: heredoc bodies and tokens with
regex metacharacters (search patterns) are dropped before matching.

**What keeps it from flooding the context:**

1. **At most 2 fronts per prompt.** A request that matches four is a conversation about the project.
2. **Once per session PER FRONT** (a marker in `~/.cache/oraculo/`).
3. **Silence when nothing matches.**
4. **A byte ceiling per source and an aggregate ceiling** (§5).

`_comum.md` is not a front (the `_` keeps it out of matching): it goes out once per session, with
the first ruler, and holds what is valid in ANY front.

## 1 · What a PREMISE is — the filter

> **What repeats in ANY work goes in. The specific defect of one piece of code does not.**

**Quick test:** if the sentence only makes sense citing a specific file of today's work, it is a
review. If it would survive the file being deleted, it is a ruler.

## 2 · Measure before inserting

A premise without measurement is folklore, and folklore injected in every session carries authority
without carrying proof. Every new premise needs at least one of: **a dated case that happened**;
**a number with a declared population** (`N of M`); **proof that the instrument sees** (it failed on
purpose before). Reading code is not enough: read-only produces a hypothesis.

## 3 · The FORMAT — two kinds of item

| kind | what it is | mandatory ballast |
|---|---|---|
| **LESSON** | born from a defect that cost work | `Measured …:` with **number and population** |
| **PROCEDURE** | how things are done here; there was no defect | `**Source:**` + a pointer to whoever rules it |

**An item with neither is a GUESS**, and `oraculo.py --selftest` fails it. The kind is **declared,
not inferred**: predicates that tried to guess "does this have evidence?" disagreed with each other
and with inspection in both directions. A guard that judges does not converge; a guard that checks a
FORMAT does.

```markdown
### N · Imperative title that already states the rule
<the MECHANISM: why it happens, in one or two sentences>
Measured on YYYY-MM-DD: <the real case, with number and population>   ← LESSON
**Source:** `docs/some-doc.md §2`                                     ← PROCEDURE (one of the two, never zero)
**What to do:** <the concrete action, imperative>
```

- The source file must contain `<!-- when-matches: … -->`, `<!-- when-touches: … -->` and a
  `## PREMISES` section (the engine parses these three anchors).
- **SEQUENTIAL numbering**; `7.1` only exists to deepen `7` and comes right after it.
- **Link to the law, do not copy it.** If the rule is already a law of the map, point to it. In a
  conflict, the map wins.

## 4 · Where a premise goes

| the premise holds… | goes to |
|---|---|
| only when compiling/promoting | `build.md` |
| only when touching compiled code | `cpp.md` |
| only when touching a database | `db.md` |
| only when writing a script/guard/hook | `scripts.md` |
| **in any front** | `_comum.md` |

The axis is the MECHANISM of the defect, not the front. If a premise fits three sources, it belongs
to `_comum.md`.

**When a premise is WRONG, rewrite it; do not append a correction.** A rule injected before work
with an erratum below it costs the decision: in a long window the erratum can fall to compaction
while the original claim stays. Wrong (never true) → leaves, git keeps it. Revoked (was true, stopped
being) → stays with the reason. Error as lesson → stays as a dated case.

## 5 · THE REVOLVING DOOR — for something to enter, something leaves

The ceiling is **`TETO_BYTES` per source** and **`TETO_AGREGADO` for the sum** (all fronts plus
`_comum`), both in `oraculo.py`. The per-front ceiling is blind to the whole: every front can grow to
its ceiling with CI green, and what reaches a session is the SUM of the fronts that light up. The
aggregate ceiling is frozen at a measured value (the tare) — zero slack on purpose, so every addition
weighs. `ALVO_AGREGADO` does not block; it says where the door must push.

**Past the ceiling the answer is NOT raising the number.** A premise leaves by one of these:

1. **Became a CI GUARD** — the best destination: the machine enforces it now.
2. **Became a LAW of the map** — if what is left is a product decision.
3. **Became a FRONT DOC** — detail that only matters inside that work.
4. **SHRANK** — part of it is already stated by a resident source with the same force; that part
   leaves, **citing the resident text verbatim**. Without the citation it stays.

What stays in its place depends on WHY it left: the object no longer exists → nothing, git is
enough; an owner's judgement → a tombstone with the owner's dated sentence; a measured condition →
a tombstone with the TRIGGER that reopens it. **When in doubt, tombstone** — keeping wrongly costs a
line; deleting wrongly costs the decision being re-proposed.

`scripts/porta.py` watches these ceilings and raises the debt (see [`docs/PORTA.md`](../PORTA.md)).

## 6 · Before committing

```bash
python3 scripts/oraculo.py --selftest
```

It checks: every source has both channels and `## PREMISES`, the budget per source and aggregate,
the ordering and the ballast of every premise, `_comum` not becoming a front, idempotence, and the
2-front ceiling per prompt — plus positive and negative matching cases.
