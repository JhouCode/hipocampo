# THE REVOLVING DOOR — the *paid, swapped* pipeline

> **The requirement:** when a piece of work is concluded — a milestone, the end of a turn, anything —
> the oracle must refresh and things must go to their place before the next one. The best trigger is
> the moment of conclusion, where the commits happen, and it must be automated so it does not depend
> on anyone remembering.
>
> **Sibling doc of** [`CONTEXTO.md`](CONTEXTO.md) (the channels) and [`MEMORIA.md`](MEMORIA.md) (the
> store). The **mechanism** lives here; the contract of each door lives in the door
> ([`mapa/5_COMO_MANTER.md §5`](mapa/5_COMO_MANTER.md), [`oraculo/README.md §5`](oraculo/README.md)).
>
> **The whole — pieces, regimes, rotation and the role of each — is [`HIPOCAMPO.md`](HIPOCAMPO.md).**

---

## 1 · The problem it solves

Five layers had a written revolving door — map, oracle, triggers, memory, the project manual. When
measured, **two were turning**. The map had had 4 written destinations for 11 days and **0 laws** had
left; the oracle had 4 destinations and **0 premises** had left, while one source went from 2,896 to
8,952 B **in one day**.

**Documenting a door is not a door.** Three causes, all measured:

| cause | evidence |
|---|---|
| the guard passes on a tie | the budget check used `-le`: `500 ≤ 500` is green. It **never lit** |
| tightening satisfies the guard without using the door | when a new law entered, nine statements were trimmed and CI went green. Free, silent, indistinguishable from all being well |
| the guard watches the total, and what grows is the existing item | *"what overflows in practice is an existing item **getting fatter**"* |

## 2 · The five stages

```
        SETTLEMENT (the diff says something was paid)
   ┌───────────┼───────────┐
post-commit   stop       working
(committed)  (end turn)  tree dirty
   └───────────┼───────────┘
   E1 DETECT → E2 DERIVE → E3 APPLY│PROPOSE → E4 COLLECT → E5 MEASURE
                                    └──── escalates D1→D2→D3 ────┘
```

**E1 · DETECT** — everything is a diff of the repo, nothing is a feeling. Signals: a new `~~id~~` in
the backlog · a doc moving to `concluido/` · a new guard proven failing · a law gaining `⚙` · a new
feedback memory · a premise leaving a source.

**E2 · DERIVE** — the destination comes from the layer's table, never from intuition. See
[`oraculo/README §5`](oraculo/README.md) and [`mapa/5_COMO_MANTER §5`](mapa/5_COMO_MANTER.md).

**E3 · APPLY or PROPOSE** — the border: **move alone where the predicate decides; propose where
judgement is needed.** The condition of the authorization: *if something leaves or enters, it goes
through a commit, and the commit holds the cause and the timestamp* — **an automatic move without a
cause in the commit is a bug, not a convenience.** A domain cut is always a proposal to the owner.

**E4 · COLLECT** — the debt becomes a row in `docs/gatilhos/porta.md` (generated), delivered by
`gatilho.py`: **D1 warns → D2 collects at end of turn → D3 BLOCKS**. It is born a debt (step `D1`),
not a `RULE`, and **escalates with accumulated rides**. The escalation is what makes this
independent of anyone remembering.

**E5 · MEASURE** — see §4.

## 3 · Why three entries, and not only the commit

`post-commit` only fires if there is a commit, and conclusion does not always become a commit right
away. The first two entries can fail; **the third turns forgetting into blocking**:

| entry | catches the case |
|---|---|
| `post-commit` | the normal one — settlement materialized |
| `stop` (end of turn) | concluded and did not commit |
| escalation D1→D3 | nobody pays: it climbs until it **blocks the tool** |

**Anti-loop, and it has two rules:**

- **`porta.py` closes the loop**: it exits when `HEAD` is already its own commit (prefix `porta:`).
  The hook calls the script **without exporting `PORTA_EM_EXECUCAO`** — that variable is the
  script's handbrake, and in the hook it makes the pipeline exit on its first line: installed,
  green and mute.
- **The brake applies only to the automatic call.** `--seco` and `--selftest` always answer,
  including right after the pipeline ran. And **every early exit says why it exited** — silence
  with `exit 0` is the only answer indistinguishable from "all is well".

## 4 · The death criterion — and it is STATE, never an event count

> **Did the fullest front go down in the window? And did the total go down?**
> If neither gives way for a month with the pipeline installed, **it did not work, and the right
> thing is to REMOVE it** — not to tune it. (A project that is only growing, finishing nothing,
> legitimately does not shrink; the owner reads the answer, the criterion stays the question.)

**Counting events measures DELIVERY when the question is EFFECT.** Measured: **7 commits with the
`porta:` prefix against ~18** that actually reduced a file covered by the door — one of them was
titled *"the revolving door pays in the same commit"* and did not count. And the size series of the
largest front **went up** in the same window: the event scoreboard would say *"working"*, the size
said *"losing"*.

**Two traps of the series, both paid in the field:**

- **Anchor after the source stabilized, never at its birth.** The sources existed from the first
  commit as sketches and were written over the next hours: comparing against that point measures the
  source **being written**, not the door turning. **An anchor less than 24 h from the birth produces
  no verdict**, and the instrument says so instead of going quiet.
- **Peak and total answer different questions.** Anchored after stabilization: peak **−655 B**,
  total **+16%**. The peak answers *"will it overflow?"*; the total, *"is it weighing more?"*. One
  alone lets you declare a false victory.

## 5 · The rule that crosses everything — the name of the number

**Before publishing a number, say the unit and the population out loud, then read the name you
gave it. If the name promises more than that sentence, the NAME is wrong — not the arithmetic.**

On one day four instruments lied, and **all four computations were right**:

| defect | the name said | the measure was |
|---|---|---|
| `rides` read from the wrong field | the ladder counter | a piece of the warning text — the ladder would **never** reach 3 |
| event scoreboard | "the door paid" | commits with a prefix |
| anchor on the sketch | "previous state" | the source being written |
| per-front ceiling | "the oracle ceiling" | the ceiling of **one** front; the whole had none |

This system has **two similar measures** living in the same context — **extracted ruler** (what the
guard collects) and **file bytes** (what the historical series has). Every warning that publishes
bytes **declares which of the two it is**, and `porta.py --selftest` fails any that does not.

## 6 · Commands

```
scripts/porta.py               measures and rewrites the trigger source
scripts/porta.py --seco        measures and prints, writes nothing
scripts/porta.py --selftest    positive and negative controls of every door
scripts/oraculo.py --selftest  budget per front AND aggregate
```

**`docs/gatilhos/porta.md` is GENERATED.** Editing it by hand is work the next run erases; what you
edit is `porta.py`. Only the `~~paid~~` rows survive — they are the proof that the door turned.
