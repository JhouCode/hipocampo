# MEMORY -- the mechanism, and what it guarantees

> **Memory is ONE of the context channels.** The architecture that contains it -- what always
> arrives, what arrives only if someone looks, what interrupts -- is in [`CONTEXTO.md`](CONTEXTO.md).
> **The whole -- the pieces, the regimes and the role of each -- is in [`HIPOCAMPO.md`](HIPOCAMPO.md)**
> (the umbrella: it points here, it does not duplicate).
>
> **The technical truth of the MECHANISM lives here. The CONTRACTS live in
> [`mapa/5_COMO_MANTER.md`](mapa/5_COMO_MANTER.md)** -- the cascade, the owner of state, and the
> shrink rule. In a conflict about a rule, `5_COMO_MANTER` wins; about the mechanism, this doc.

A working example of everything below is in [`examples/memory/`](../examples/memory/): an index in
the real format, three memories (a method, the case that proves it, and a standalone lesson), and
the derived table in [`INDICE_NUMERICO.md`](INDICE_NUMERICO.md) generated from them.

---

## 1 · What memory IS -- ONE automatic channel, and a second one that depends on the agent

| channel | when it enters | cost | who decides what enters |
|---|---|---|---|
| **`MEMORY.md`** (the index) | **every turn**, in the system prompt | its whole size, against a hard cap | one line per memory, curated by hand |
| **an individual memory** | **only when the agent opens the file** (`Read`/`cat`) | the whole file, every time | **the agent**, deciding from the index line |

In the vocabulary of `HIPOCAMPO.md`: `MEMORY.md` is the **hippocampus** (it keeps the index, not
the content) and each individual memory is an **engram**.

**This is the most important thing in this doc:** an individual memory **does not load by itself,
and nothing loads it for the agent**. Therefore:

- a memory **outside the index** is not less visible -- it is **invisible**, and nothing flags it;
- the index line **is the recall**. It, and only it, makes the agent open the file (opening is the
  **evocation**);
- the **`description:`** is not an entry channel: when it arrives, the whole body came with it. It
  is worth something as **the summary read first** and as the text a search matches -- a wrong claim
  in it is **the wrong summary served as if it were the subject**.

### 1.1 · The proof -- automatic recall does not exist here

Instrument: [`scripts/memoria-recall.py`](../scripts/memoria-recall.py) (it has a `--selftest`
proved failing on injected defects: a glob counted as recall, a `tool_result` counted, a write
counted as a read).

Measured over every session transcript on disk (89 transcripts, 143k lines): of the 25 kinds of
attachment the runtime injects automatically, **zero** are memory recall. About a third of the live
memories had ever been opened at least once; the rest had never been opened at all.

**Horizon of the source:** it covers the sessions still on disk, and today's store is not
yesterday's. That is why the report separates **live** memories from **historical** ones, and why
*"never opened"* does not mean *"useless"*: it means **no measured use**.

**What counts as recall -- and the definition IS the instrument.** Recall is opening **one specific
file**: a `Read` with the `file_path`, or a `Bash` segment naming `memory/<name>.md` in full. It does
**not** count an `ls` of the folder, a `*.md` glob, a write, or the name showing up inside a
`tool_result`. A single `ls memory/` mentions every file and would produce the highest and most
useless number possible.

### 1.2 · The cap -- and its unit

The runtime caps the index at **200 lines** and **25,000 units**. The unit is the **UTF-16 code
unit** (JavaScript's `.length`), not the byte; the comparison is inclusive, and a "KB" label printed
by the runtime is units / 1024. Hook output has its own cap per part (10,000 units).

- Guards that measure **bytes** over-reserve for any non-ASCII text (a few percent in accented
  prose). That is the SAFE direction, so converting to units is accuracy, not urgency.
- **An emoji costs 2 units.** Emoji lives in the BODY of a memory, never in the index line.
- **The binding slack is the SMALLER of the two:** line slack (200 - lines) and unit slack
  (25,000 - units). An index is *line-bound* or *size-bound* depending on which one runs out first,
  and the capacity for new entries is measured against the binding one.

**The capacity arithmetic** (how many more entries fit):

```
marginal cost of one entry  = units of one real, typical entry (citation + gloss + separator)
entries per line            = measured on the file, not assumed (several siblings share a line)
pool by size                = unit slack / marginal cost
pool by lines               = line slack x entries per line
pool                        = min(pool by size, pool by lines)     <- the binding one
```

Use the **marginal** cost of a real entry and the **measured** density, never the average of the
whole file (the header is not an entry). And report the number of the **final state**: a change that
saves units by cutting and then spends some writing new glosses or header lines is measured after
everything it added, not at the instant after the cut.

## 2 · The pieces

| piece | what it does |
|---|---|
| the memory folder (`HIPO_MEMORY_DIR`) | **the source.** Written by the agent, outside the repository |
| [`scripts/memoria_ids.py`](../scripts/memoria_ids.py) | **the id arithmetic**, one module -- the resolver, the assigner and the guard all read from here |
| [`scripts/memoria-id-assign.py`](../scripts/memoria-id-assign.py) | assigns `id: max+1` to a memory without a number; idempotent; a duplicate is RED; `--tabela` regenerates the table |
| [`scripts/memoria-resolve.py`](../scripts/memoria-resolve.py) | `N` -> path. Table first, frontmatter as fallback; a missing id ACCUSES (rc 1, stdout empty) |
| [`scripts/guarda-indice-citacao.py`](../scripts/guarda-indice-citacao.py) | bijection `[N]` <-> frontmatter + mandatory gloss + table vs source. 14 controls in `--selftest` |
| [`scripts/guarda-cascata.py`](../scripts/guarda-cascata.py) | the method <-> case cascade: every `[[link]]` resolves, `prova:` recounts the live cases |
| [`scripts/memoria-estaciona.py`](../scripts/memoria-estaciona.py) | parks / resumes a block of the index (section 5) |
| [`scripts/memoria-espelho.sh`](../scripts/memoria-espelho.sh) | mirrors the source into `memoria/` of a repository, commits **if changed**, pushes only on request (section 6) |
| [`INDICE_NUMERICO.md`](INDICE_NUMERICO.md) | the derived table. **Cache, never source** -- regenerable from the frontmatters |
| the memory-index guard ([`guardas/memoria.md`](guardas/memoria.md)) | index pointers resolve · orphan memory · index cap · the mirror covers the source |

## 3 · The memory file -- frontmatter and body

```
---
name: feedback_count_population_before_zero        <- equals the file name, never changes
id: 2                                               <- born here, assigned by memoria-id-assign.py
description: "A zero is only a result when ..."     <- the SUBJECT, never a transient state
metadata:
  node_type: memory
  type: feedback                                    <- feedback | project | reference | user
  escopo: metodo                                    <- scope: `metodo` (a rule) or a domain
  prova: 1                                          <- a method: how many LIVE cases point back
---
Body: what happened / what holds.

**Why:** the reason, as a failure mode or a measurement.

**How to apply:** what to do differently, concretely.
```

- **`id:` sits at the ROOT of the frontmatter** (column zero), right after `name:`. Inside
  `metadata:` it would be another field, and nothing would read it.
- **`description:` states the subject, never a state that rots** ("X is broken", "waiting for Y").
  It is the summary read first; a stale state in it is a wrong summary served with authority.
- Field names and values of the cascade are parsed literally by `guarda-cascata.py`:

| field | where | meaning |
|---|---|---|
| `escopo: metodo` | the rule | this memory is a method; it must declare `prova:` |
| `prova: N` | the rule | number of LIVE cases whose `regra:` points here; recounted by the guard |
| `prova: fundido` | the rule | the case exists but is still merged in the rule's own body; accepted and COUNTED as debt |
| `escopo: <domain>` | the case | any non-`metodo` value; a file whose name starts with `caso_` is a case |
| `regra: <name>` | the case | the method it proves; must exist |
| `estado: morto` + `motivo:` | either | a dead (revoked) memory; a death without a `motivo:` fails |
| `revogados: M` | the rule | explicit acceptance of M dead cases; without it, any death keeps the guard red |

A method with no live case is **folklore** and fails. A case added without bumping `prova:` fails.
That is the point: **the link carries a POPULATION, not only an address**. An address cannot be
checked; a number is recounted.

## 4 · The index-citation format

**The index line does not write the file name; it cites `[N]`.** The number is born in the `id:` of
the memory's frontmatter; the number -> name table is **derived**. The file name on disk **does not
change** -- `[N]` is an alias on top.

```
Memory Index

  FORMAT: plain text with indentation ... (the header states the rules and the revoked ones)

Method / measurement
  [2] (a zero is a result only with its population; count the denominator first)
  [1] (case: dashboard read 0 errors over 0 log lines after a format change)
```

- plain text with indentation: no markdown, no links, no bold, no emoji;
- a section header is an unindented line; entries are indented under it;
- one line per entry, or several siblings on one line separated by ` · `;
- every citation carries its **gloss**, the text up to the next citation. The gloss answers "why
  would I open this?" -- a directive, not a post-mortem;
- a revoked rule **stays in the header as a dead line**: it is what stops it from being proposed
  again.

**The principle:**

> The capped file pays only for what **works at load time**. The gloss works (it is what decides to
> open). The address does no work until the lookup -- and a lookup is a rare, cheap event. Addresses
> are paged out.

Measured on a real index when the format changed from full file names to citations: **-24.6% of the
units**, and the pool of new entries grew by a third; the regime flipped from size-bound to
line-bound.

**The four rules the mechanism guarantees, each with a guard proved failing:**

1. **An id is never reused, never renumbered once cited.** `max+1` always; a deleted memory takes
   its number to the grave. Reuse is the only irreversible defect here.
2. **A duplicate is RED, never a silent fix.** Two owners for one number make every citation of it
   ambiguous, and picking a side silently is picking the wrong copy with authority.
3. **The gloss is mandatory.** `[N]` without prose on its line FAILS (floor: 10 useful characters).
   Without it the index decays into blind numbers over time.
4. **The table never decides alone.** What it returns is checked against the frontmatter before it
   leaves; a divergent table is discarded and the resolver falls back to the source, WARNING. If
   everything burns, `grep -l '^id: 7$' <memory dir>/*.md` resolves -- one command, zero mechanism.

**Why the table lives in `docs/`, not with the memory:** the memory folder is scanned by guards that
treat every `*.md` other than the index as a memory (no frontmatter, no index entry -> failure), and
the repository's `memoria/` is the target of an `rsync --delete` that erases whatever has no pair in
the source. In `docs/` the table is outside the capped file, outside the store glob and outside the
rsync -- and it is regenerable anyway, so it needs no backup of its own.

### The `[[name]]` links inside memory bodies STAY

Only the index migrated to `[N]`. **The body does not load** -- only the index does, and recall is
manual -- so converting bodies saves **zero** units of the cap. And it costs: in the form `[7]` the
predicates of `guarda-cascata.py` (and of any other `[[name]]` parser) stop matching and every
pointer goes to zero in silence, each selftest still green on its own fixture; in the form `[[7]]`
the cascade fails on all of them at once.

> **The door -- this reopens if, and only if, one of these changes:**
> 1. **bodies start loading by default** (then the address would work at load time and pay for
>    what it costs); **or**
> 2. **the `[[name]]` parsers are retired**, because what the conversion would silence is gone; **or**
> 3. **the other channels (map, oracle, triggers) migrate to `[N]`**: `porta.py` looks for NAMES in
>    them, and would count every body as an orphan, silently -- the migration must re-aim it too.

**The risk that stays, declared:** the index is no longer readable alone. A `MEMORY.md` without its
`memory/` folder becomes glosses without addresses. Mitigation: that scenario does not exist in the
backup design -- the mirror carries index and store together, and the table travels in the repo.

## 5 · Parking a project -- rotating the index

"Park that project, I am working on this one" is a command, not a hand edit. Parking and resuming
are the **active forgetting** of `HIPOCAMPO.md`.

```bash
python3 scripts/memoria-estaciona.py --estaciona billing --bloco "Billing"   # out of load
python3 scripts/memoria-estaciona.py --retoma billing                        # back, byte for byte
python3 scripts/memoria-estaciona.py --lista
```

The block (its unindented header plus the indented lines under it) moves to
`memory/indice_<slug>_estacionado.md` with a new id, and the index keeps the header plus one line:

```
Billing
  [4] PARKED 2026-09-30 · memoria-estaciona.py --retoma billing
```

`--retoma` puts the block back **byte for byte** and deletes the parked file. The memories cited
only inside a parked block are **parked, not orphans**: that clause lives in the memory-index guard
(see [`guardas/memoria.md`](guardas/memoria.md)). `guarda-indice-citacao.py` alone reads only
`MEMORY.md` and will report them as never cited while the block is parked.

If you keep a trigger source for parked projects under `docs/gatilhos/`, its line and the parked
file must move together: the script prints a reminder on every park and resume, because the
trigger's match (which paths belong to the project) cannot be derived from the slug.

**What parking does, measured** (one store, 2026-10-12, `scripts/memoria-recall.py` over 225
transcripts): inside the index, **163 of 280** memories had been opened at least once (58%); of the
176 that left it with parked projects, **at most 8** were opened afterwards (4.5%, a ceiling). A memory
outside the index is invisible, which is the point for a parked project and the reason a memory that
serves only on one path goes to a trigger instead ([`gatilhos/memoria.md`](gatilhos/memoria.md)).
Parking two large projects took the index from **93.7% to 71.5%** of the size cap. That is also a cost
cut: the index is paid on **every request** (1.4 to 2.2% of all input over the article's window,
[`data/custo_indice.csv`](../data/custo_indice.csv)), and so is anything a hook puts back.

## 6 · The mirror -- a backup of the memory

The memory folder lives outside every repository. A rebuild that restores the machine and the hooks
but not this folder rebuilds **the machine that reads the memory, without the memory** -- and a
memory that points to no doc is the only copy of what it says.

`scripts/memoria-espelho.sh` projects the folder into `memoria/` of a repository and commits.

| env | default | meaning |
|---|---|---|
| `MEM_DIR` | `HIPO_MEMORY_DIR` | the source |
| `REPO_DIR` | `HIPO_REPO` | the repository; the mirror is `REPO_DIR/memoria/` |
| `MEM_PUSH` | `0` | `1` pushes after a commit; otherwise the commit stays local |
| `MEM_REMOTE` / `MEM_BRANCH` | the current branch's upstream | what `--status` asks for the offsite state |
| `MEM_LOG` | `HIPO_LOG_DIR/memoria-espelho.cron.log` | the cron log `--status` reads |

The lock is `HIPO_STATE_DIR/memoria-espelho.lock`. A typical cron line:
`47 * * * * bash <repo>/scripts/memoria-espelho.sh >> <log dir>/memoria-espelho.cron.log 2>&1`.

**Design decisions, each with a reason:**

- **`rsync --delete`** -- the mirror is a projection. A memory deleted on purpose leaves the mirror
  too; `git log` keeps the past.
- **`git commit --only memoria/`**, never `add -A` -- another session may be working in the same
  tree, and a plain `git commit` takes the whole index with it. A commit that is blocked unstages
  `memoria/` again, so nothing of it travels in a neighbour's commit.
- **commits only if something changed** -- an hourly empty commit is noise nobody reads.
- **LIMIT control**: a source with fewer than 2 `.md` files **aborts before the `rsync --delete`**.
  Without it, a wrong `MEM_DIR` would erase the mirror and the next commit would erase the backup.
- **git's error reaches the log.** `-m` goes before `--` (after it, git reads the message as paths),
  and stderr is kept: guessing the cause is asking the watchman, not the target.
- **push is opt-in**, and **it pushes only what is its own**: if anything ahead of the upstream is not
  a mirror commit, it commits and holds the push (`push HELD`, the foreign commits named). The mirror
  carries private memory; pushing is a decision about where that goes.
- **`flock`** -- two simultaneous rounds committing the same tree is a guaranteed race.

**Two branches, very different:**

| branch | when | what happens | the log says |
|---|---|---|---|
| **empty** | the source did not change | `rsync`, compare, **leave before the commit** | `no change in the N memories -- nothing to commit` |
| **hot** | a memory was added, changed or deleted | `rsync --delete` -> `git add` -> `commit --only memoria/` (**through the pre-commit guards**) -> push if `MEM_PUSH=1` | `committed: N changed file(s) of M`, then `ok` |

**The empty branch proves nothing about the hot one.** Three clean hourly lines in the log can all be
the empty branch, while the path that matters never ran. Prove the hot branch with a real change, and
prove the push **at the target**: the remote branch's SHA equals the local `HEAD` -- the log says
what the script thought it did; the remote says what arrived.

**Status is not read from a doc; it is asked:** `bash scripts/memoria-espelho.sh --status` answers
four questions, each at its own source, and returns `OK` (0) / `ATTENTION` (1) / `FAIL` (2): is the
cron in the crontab · when it last ran and what it did (**over 90 minutes is a symptom**, it is
hourly) · do source and mirror match in count · **is the offsite up to date**, asking the remote.
`CRONTAB_CMD` makes the "cron is gone" defect injectable for testing.

**Branches that a deployment should expect not to have exercised** until they happen: a failed push
(network, revoked credential), a removal by `rsync --delete` fired by cron, and two rounds contending
for the `flock`. Do not claim them before they are seen.

## 7 · What this mechanism does NOT guarantee -- declared

- **It does not verify that a memory is RIGHT** -- only that it is findable, intact and recoverable.
  Content is judgement, and judgement does not mechanise: attempts to detect a stale state by
  predicate produced mostly false positives. That is why the contracts ask for **declaration**,
  never inference.
- **A memory that is really a doc** (long, full of `file:line` references and code blocks) keeps
  costing only when opened, but it duplicates truth that belongs in `docs/`. It shrinks by
  **carry-over** when touched, not in a bulk rewrite.
- **The mirror is only as private as the repository it commits to.** Audit the store for tokens and
  keys before the first push, and keep `MEM_PUSH` off for any repository you would not publish the
  memory to.
