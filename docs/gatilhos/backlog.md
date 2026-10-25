# Source `backlog` -- debts paid as a free ride

> **The pilot source of the dispatcher** (`scripts/gatilho.py`). An opportunistic backlog ("when
> you touch X, also do Y") that lives in a document nobody opens at the right moment is mute. Here
> a hook reads it at the moment of the touch.
>
> **The contract -- six columns, always these, in this order:**
>
> | column | what it is |
> |---|---|
> | `id` | stable. `~~id~~` = **paid**; the row stays in the table as proof that the trigger worked |
> | `when it matches` | **a regex between backticks**, matched against the file path OR the command text. `—` = uncovered, **declared** |
> | `what to say` | one sentence. It goes into the agent's context at the touch -- long here is noise there |
> | `NEXT STEP` | **mandatory** (10+ characters). It is what keeps the warning from pulling the agent out of its plan of action |
> | `step` | **the KIND of item.** `D1` = debt: dies when paid and escalates by the counter. `RULE` = permanent: always warns and **never blocks**. A debt may carry a **wait marker** after the kind (`D1 ⏸DEBT-02`, see below) |
> | `rides` | missed rides. For a debt, **`>= 3` promotes it to D3 (BLOCK) by itself**. For a rule it is only a metric |
>
> **DEBT and RULE are not the same thing, and confusing them breaks the ladder.** A debt comes due:
> at some point it has to hurt, and D3 is that point. A rule does not come due -- *"check the
> projection before editing"* holds every time, forever. If a rule accumulated like a debt, every
> rule would reach 3 and block everything **even while it is always obeyed**, because the Stop
> step only knows that it warned, there was a write and the turn closed; it does not know whether
> the debt was paid.
>
> **A debt that WAITS for something else does not add rides.** A ride is only a missed *opportunity
> to pay*, and a debt whose next step depends on another item, on a run, on a piece of work or on
> the owner's decision has no such opportunity: charging it measures "I touched the file", and
> pushes it to D3 over something nobody could pay. (Measured on a real backlog: 7 of the 12 items
> that sat in D3 were in this state.) The wait is declared **in the `step` column**, after the kind:
>
> | marker | waits for | stays open |
> |---|---|---|
> | `D1 ⏸DEBT-02` | another item, from any source (the id as in the `id` column) | while that item exists and is not struck through (`~~`) |
> | `D1 ⏸dele 2026-09-30` | a decision of the owner's (`dele` is the literal token of the grammar, Portuguese for "his") | until someone removes the marker by hand |
> | `D1 ⏸evento 2026-09-30` | a run, a piece of work, a fact of the world (`evento` = "event") | until someone removes the marker by hand |
>
> The date is the day the wait was declared. **WHAT is awaited stays in the `NEXT STEP`**: the marker
> is for the machine, the sentence is for people. While the wait is **open**, D1 still warns (the
> warning says `⏸ waiting …`), **D2 does not add**, **D3 does not block**, and the old rides stay
> in the cell, frozen. When the target item is struck through the wait **closes**: everything counts
> again, and D1 says once that the wait closed (remove the marker). Defects are **red** in
> `gatilho.py --selftest`: `⏸<id>` with no such item in any source, a marker outside the grammar, or
> a `RULE` carrying a wait (it does not escalate anyway); a defective marker counts as a *closed*
> wait, so a typo never disarms D3 silently. A `dele`/`evento` wait older than 21 days is **yellow**
> (printed, not failed): a wait nobody revisits becomes a tombstone. A source that is generated
> (`porta.md`) keeps the marker across regenerations.
>
> **Do not fake coverage.** An item whose trigger is an event (*"next release"*, *"next DR
> drill"*) is born with `—` and enters the count of uncovered items. Inventing a weak regex for it
> would leave the source green and blind.
>
> **The ladder, measured by the counter and not by anyone's memory:**
> D1 WARN on `PostToolUse` (once per session) -> D2 CHARGE on `Stop` (a warned item that was
> WRITTEN and not paid gets `rides + 1`, in this file) -> D3 BLOCK on `PreToolUse` (a debt with
> `rides >= 3` asks for a decision before the write passes). Reads warn; only writes are charged
> and blocked -- except a debt with an open wait, which is neither charged nor blocked. "Write" is
> judged per item and per command segment: a heredoc body is data, not a command, and a
> redirection counts only when its *destination* is the item (`bash run-checks.sh > log` runs the
> item and writes the log). The channels are in [`CANAIS.md`](CANAIS.md).

| id | when it matches | what to say | NEXT STEP | step | rides |
|---|---|---|---|---|---|
| DEBT-01 | `scripts/deploy\.sh$` | The deploy script still hard-codes the service port instead of reading it from `config/app.env` | While the file is open: replace the literal with `${APP_PORT}` read from `config/app.env`, and run `scripts/deploy.sh --dry-run` once | D1 | 0 |
| DEBT-02 | — | The next release must rotate the API signing key, which is older than one year | On the release checklist: generate the new key, publish both for one day, then drop the old one | D1 | 0 |
| RULE-01 | `(^\|/)\.env\.example$` | Every key added to `.env.example` must also exist in the secrets vault, or a fresh deploy starts with an empty value | Add the same key to the vault in the same change, and say in the commit body that both sides moved | RULE | 0 |
| ~~DEBT-00~~ | `templates/.*\.html$` | PAID -- inline handlers moved to `static/js/`, the CSP no longer needs `unsafe-inline` for scripts | -- | -- | 0 |

## Population -- DERIVED, never written by hand

**Who counts is `python3 scripts/gatilho.py --selftest`**, which derives everything from the table:
active, paid, covered by `when it matches`, and the split by source. A population number written
by hand in prose does not recompute, and it ages silently while the table right under it is right.

An item **by event** is born with `when it matches: —` **declared**, never blank: the `—` is what
separates *"uncovered on purpose"* from *"forgot to fill in"*, and it is what the selftest counts.
