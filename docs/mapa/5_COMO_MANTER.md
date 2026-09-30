# 5 · HOW TO KEEP THE MAP

> **The maintenance rule of the 4 layers** ([`0_MAPA.md`](0_MAPA.md)). It was written before the
> first commit of the map, because a map without a maintenance rule is an orphan doc with a pretty
> index: an earlier "read this before deciding" doc was born with the same intent and rotted — it
> depended on someone opening it.
>
> **This page is a process rule, not a loadable fact — it does NOT count against the budget of
> layers 1–3.** The rule below is the real one; only the examples are generic.

---

## 1. Where each thing goes

| it happened | goes to | how |
|---|---|---|
| the owner decided something **about the product** | [`3_DECIDIDO`](3_DECIDIDO.md) | new row, `✅ IN FORCE`, with **owner and date** — and the **mechanism glyph** (§1.1) |
| a decision **fell** | [`3_DECIDIDO`](3_DECIDIDO.md) | becomes `🔻 REVOKED` **with the reason in the body**, dead statement in `~~strikethrough~~` — never deleted |
| the owner **postponed** something | [`3_DECIDIDO`](3_DECIDIDO.md) | `🕓 POSTPONED` + a `**TRIGGER:**` row right below — **mandatory** |
| a machine, port, path or database changed | [`2_ONDE`](2_ONDE.md) | edit **in place**. It is a table: no history, no revocation |
| the owner corrected me **on method** | [`1_CONTRATO`](1_CONTRATO.md) | new row. **Only the owner originates** — the agent does not invent method rules |
| the owner **authorized** something for good | [`1_CONTRATO`](1_CONTRATO.md) | the *"What is ALREADY AUTHORIZED"* table. A forgotten authorization becomes daily friction |
| a front changed phase | [`4_FRENTES`](4_FRENTES.md) | move the folder (`andamento/`→`concluido/`) **and** adjust the row |
| a bug or a pending measurement | the debt backlog (`docs/gatilhos/`) | **it is not a decision** — it does not enter layer 3 |

## 1.1 The missing question: *"what proves this is still true?"*

A law's contract had three questions: *what was decided* · *by whom and when* · *where is the proof
of the decision*. The fourth is the only one that ages: **what proves this is still true?** The
first three talk about the past, and the past does not change. The fourth talks about now. The
failure it prevents: a law loaded in every session, stating the opposite of the world, with no
instrument able to disagree.

**Every `✅ IN FORCE` row answers the fourth with a glyph:**

| glyph | meaning | what the row must carry |
|---|---|---|
| **`⚙`** | a **CI guard** fails on its own, on every commit | the **guard name** in the proof column |
| **`🔔`** | nothing verifies, but a **trigger** fires when the area is touched | the id of the backlog item |
| **`🕳`** | **NO MECHANISM** — nothing runs by itself | nothing. It is the honest answer, not a failure |

**`🕳` is the most valuable of the three.** It fixes nothing — it stops hiding. A law that declares
itself unverified stops presenting itself as measured truth. A `🕳` on a law whose object does not
exist yet is expected; the dangerous `🕳` is on a law whose object is already in production.

A guard should fail an `IN FORCE` row without a glyph, and a `⚙` whose guard name does not exist —
otherwise the mark becomes the lie it came to kill.

## 1.2 The CASCADE — where each thing lives, in order

**Stop at the first step that fits.**

1. **What is the authority?** A behaviour policy only holds anchored in the code or the data. A rule
   justified by something that no longer exists **fails or re-anchors on the source**.
2. **Is there a reproducible predicate + a positive control?** → a **CI guard**, proven failing —
   **and then it LEAVES the ruler**. This is the step that closes the cycle.
3. **Is there an identifiable touch before the decision?** → a **hook/oracle**: one sentence and a
   pointer, never the whole ruler.
4. **Is there a procedure, context or parameter?** → a **doc**, where technical truth lives.
5. **`MEMORY.md`** → only **verdict + pointer**, one line. Never the detail.

> An item can sit in **more than one layer** — with **a single source of truth**. The guard
> enforces, the doc explains, the index points; only one of them **defines** it.

Step 5 is the most expensive of the system, which is why it is last: the index loads on **every
turn**; the map once per session; a doc only when opened. The whole is in
[`docs/HIPOCAMPO.md`](../HIPOCAMPO.md).

### How to write a row in layer 3

```
| id | state | the decision, in one sentence | who, when | where the proof is |
```

- **One sentence.** If it does not fit, the proof lives in a layer-4 doc and the link goes in the
  last column. The **first `**bold**` span** of the decision is what the periodic reminder carries.
- **State**: `IN FORCE` · `REVOKED` (with the reason in the body and the dead statement in
  `~~strikethrough~~`) · `POSTPONED` (**requires a trigger** row).
- **IDs** are a letter and a number (`P1`, `P2`…). A guard reads rows whose first column matches
  `^[A-Z]\d+$`.
- **Mechanism** — the glyph next to the state (§1.1).

## 1.3 The OWNER of a state

**Outside the owner of a state, CITE and POINT — do not assert state.** Each family of ids has one
file that asserts its state (laws: `3_DECIDIDO.md`; debts: the backlog; phases: the folder). When a
citation needs the state, it comes **dated** — *"on 2026-02-01 it was X"* — because a dated statement
ages without lying; a standing one does not.

## 2. A new project — the 4 acts

None is optional. A project that enters without all four is invisible to the map.

1. **One row in [`4_FRENTES`](4_FRENTES.md)** — name · entry door · **when to open**.
2. **A folder `docs/<project>/`** with `proposta/` · `andamento/` · `concluido/` + a `README.md` door.
3. **Each product decision the owner brings becomes a row in layer 3**, with owner and date.
4. **Each new machine, port or path becomes a row in layer 2.**

> **Layer 1 is NOT touched by a new project.** A project does not change method.

## 3. WHEN to write — the rule that attacks forgetting

> **An owner decision becomes a row BEFORE I start executing. Not after.**

Decisions evaporate when they sit in the middle or at the end of a long message about something
else — and they vanish exactly while the main subject is being executed. Recording after executing
records **what survived my attention**, which is precisely the filter that caused the losses.
**In practice:** read the whole message → extract the items → write the rows → **only then** work.

## 4. What NOT to do

- **Do not create `MAP_v2`, `3_DECIDIDO_new`, `MAP_REVIEW`.** Final state, edited in place; git
  keeps the history.
- **Do not delete a revoked row.** The dead row is the asset.
- **Do not postpone without a trigger.** Postponing without a trigger is forgetting with a date.
- **Do not duplicate technical truth in the map.** The map distills and **points**.
- **Do not let layer 4 leak into layers 1–3.** A row that needs a paragraph is layer 4 with a link.

## 5. THE REVOLVING DOOR — how the map does not expire

**The scarce resource is not bytes.** Slicing absorbs size. What does not scale is the session
starting with the agent reading 5, 6 blocks of map before working. So the limit is **in slices**
(`MAX_FATIAS` in `scripts/mapa-hook.sh`), and `--selftest` always says how much is left **in laws**:

```
· BUDGET: 6 laws in force at ~220 B each; +30 fit before slice 4 is needed
```

> **The budget in laws is optimistic — the cut breaks first, and it breaks in BYTES.** Slicing
> breaks at block boundaries, not at the ceiling, so growing an existing row by ~100 B can add a
> slice while the budget still says "+8 laws". And the symptom is **silent**: the hooks are
> registered for `--parte 1..N`, so slice N+1 **does not arrive** and nothing complains unless the
> registration guard runs. **Before adding text to a law, run
> `bash scripts/mapa-hook.sh --selftest`** and read the number of slices, not of laws.

### When the alarm rings: for something to enter, something leaves — and "leaving" has a destination

| # | what leaves | to where | why |
|---|---|---|---|
| 1 | **a rule that became executable** | 1 pointer line to the guard | the guard already enforces it; the whole text in the map is redundancy that costs turns |
| 2 | **a REVOKED law** | a `3_REVOGADAS.md` created on the first move (not loaded) | still the asset that prevents re-proposing — but consultation, not reminder |
| 3 | **laws of a finished project** | go with the project to `concluido/` | a closed project's law does not rule new work |
| 4 | **prose of a mature law** | the detail goes to the doc; the statement stays | the highest leverage: the reminder already carries only the bold statement |

**"Raising the ceiling" is not a destination.**

### What NEVER leaves

Granted authorizations · vetoes · laws in force of a live project. If the budget tightens and only
that is left, **the problem is not the map** — it is too many live projects at once, and that
conversation is with the owner, not with the file.

## 6. Guards — the rule becoming an executable check

A rule without a guard is decoration, and this page **does not fail by itself**. The checks that
make it bite (each must be proven failing before it counts):

| # | check |
|---|---|
| 1 | `POSTPONED` without a `**TRIGGER:**` row right below → fail |
| 2 | `REVOKED` without a `Reason` in the row → fail |
| 3 | initial load above `MAX_FATIAS` slices → fail. It does not count bytes: it calls the hook's own `--selftest`, so there is one computation of the budget, not two |
| 4 | a broken relative link in the map → fail |
| 5 | an odd number of backticks in a statement (the law reaches the context cut in half) → fail |
| 6 | an `IN FORCE` law without a §1.1 glyph, or a `⚙` naming a guard that does not exist → fail |

Two design decisions for whoever touches them: **scope is only the `3_DECIDIDO` table** (lines that
start with `|`) — scanning the whole map would match this very page, which quotes the words the
guard looks for; and **they do not look at the diff** — they scan the whole file in every mode,
because a guard that only scans what was touched lets a deleted file pass green.
