# Source `dependencia` -- what has to change TOGETHER

> The second front of the dispatcher, **written without touching a line of `scripts/gatilho.py`**
> -- that is the test of the contract: if a new front needed code in the engine, the contract
> would be wrong.
>
> The `backlog` asks *"what can I pay on the way?"*; this source asks **"what breaks silently if I
> change only one side?"**. Every row here is a pair that already diverged, or that only has not
> diverged yet because nobody touched it.
>
> **Every item here is a `RULE`, not a debt.** A rule does not die when obeyed: it holds again on
> the next touch. So it **always warns and never blocks**, and the `rides` column is a metric: a
> high number says *"this rule lives on my path -- worth automating"*, not *"time to block"*. The
> column contract is in [`backlog.md`](backlog.md).
>
> **Small source on purpose.** The selftest marks `🟡 BLIND SOURCE` under 5 items, and the warning
> is honest: a small population here means the dependencies were not surveyed yet, not that they
> do not exist.

| id | when it matches | what to say | NEXT STEP | step | rides |
|---|---|---|---|---|---|
| DEP-01 | `(^\|/)db/schema\.sql$` | The schema and the migrations are two sides of one fact: editing the schema without a migration makes a fresh install differ from an upgraded one | Write the matching file under `db/migrations/` in the same commit, and run the migration test on an empty database | RULE | 0 |
| DEP-02 | `(^\|/)config/[^/]+\.conf$` | What runs is the copy on the host; `config/` is the versioned mirror | Apply the change on both sides in the same batch, or the drift check flags it and a restore brings back the wrong version | RULE | 0 |

## Population -- DERIVED (`gatilho.py --selftest`)

A dependency is a pair of paths, so a path trigger covers it well. How many items there are, the
parser counts; writing the number here would only create a second truth that ages silently.
