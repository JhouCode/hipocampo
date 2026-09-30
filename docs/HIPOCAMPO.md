# HIPOCAMPO: the agent's memory, its pieces, and who does what

> **Umbrella doc.** It defines the model and names the pieces; **the detail of each piece lives in
> the doc that owns it**, and when the two disagree, the owner wins. Nothing here is a second
> source: this is the **map of sources**.
>
> **Maintenance:** a new piece, a dead piece, or a role that changed means one line here, pointing
> to the owner doc. Numbers and state do not live here; they live in the owner
> ([`mapa/5_COMO_MANTER.md`](mapa/5_COMO_MANTER.md)).

---

## 0 · In one sentence, for someone from outside

> **In 1953 a surgeon removed the hippocampus of Henry Molaison, the patient known as H.M.** He
> kept his intelligence, his skills, everything he knew from before, and his working memory. He
> lost one thing: the ability to **form new memories**. Every conversation started from zero.
> **A language model session is H.M.** This system is a prosthesis for the missing organ: **the
> agent does not remember; the hippocampus delivers.**

The brain's hippocampus **does not store the content**. It stores the **index** and does the
**consolidation**: today's episode becomes a durable trace in the cortex, largely during sleep, and
remembering is a **cue** reactivating the index so the cortex can rebuild the pattern (the
hippocampal indexing theory, Teyler & DiScenna 1986, one theory among others, not a settled fact).
That is the design here: the index (`MEMORY.md`) points, the cortex (`docs/` plus the memory store)
holds, the post-mortem consolidates, the trigger is the cue. Section 8 has the vocabulary.

**In engineering terms, the same design is called virtual memory**: a small, expensive window (the
working memory), a much larger address space (the cortex), **resident** pages, pages **paged in**
on demand, **interrupts** that fire along the path, and **swap** for what leaves the load and comes
back by command. Both readings say the same thing. The design work was deciding **what lives in
which regime**, and that decision was measured, not argued.

**Where the analogy STOPS, stated up front:** real consolidation is automatic and happens during
sleep; ours is **manual, in the post-mortem**. The mirror job only projects, it does not rewrite.
And real recall is transparent; ours **is not**: a paged memory only enters if the agent opens it
(sections 1 and 7). The name describes the design; it does not claim the automatic part exists.

## 1 · The problem it solves: three measured facts

| fact | where the proof is |
|---|---|
| **There is no automatic memory recall in the measured installation.** A memory file enters the context only if the agent opens it, and what makes the agent open it is its line in the index | [`MEMORIA.md`](MEMORIA.md): 89 transcripts, 0 injected recalls |
| **Compaction loses what matters.** The summarizer is not ours: a 97% cut, and 8 of the operator's 36 messages lost in one real event | [`CONTEXTO.md`](CONTEXTO.md), the baton section |
| **A loaded rule does not become action; only an interrupt changes behavior.** In 4 slips on the same day, the rule had been read and was on screen | [`CONTEXTO.md`](CONTEXTO.md) |

Without the system, every session redoes the onboarding, every compaction erases the work in
flight, and every new project starts from zero. With it, **the onboarding is built once and tied to
the right regime**.

## 2 · The principles: four, each with an owner doc

1. **The repository is the truth; the runtime and the memory are projections.** If it is not in the
   repository, it does not survive the next disaster. -> [`MEMORIA.md`](MEMORIA.md)
2. **Memory holds VERDICT + POINTER, never the detail.** Technical truth lives in `docs/`; when they
   disagree, the doc wins. -> [`mapa/5_COMO_MANTER.md`](mapa/5_COMO_MANTER.md)
3. **Law lives in the resident regime; technical fact lives in the manual.** A source that does not
   arrive cannot arbitrate a conflict. -> [`CONTEXTO.md`](CONTEXTO.md)
4. **Only what works at load time pays for the load.** The gloss works (it decides whether to open);
   the address does not (lookup is rare and cheap). That is why the index cites `[N]` + gloss and
   pages the file name out. -> [`MEMORIA.md`](MEMORIA.md)

## 3 · The three regimes: the spine of the system

| regime | what lives here | how it arrives | guarantee | budget |
|---|---|---|---|---|
| **RESIDENT** | the map (layers 1, 2, 3) · the front's oracle · `MEMORY.md` (the index) · the baton and the design (the desk) | session hook, touch hook, the runtime's memory block | **always arrives** | measured ceiling and a revolving door |
| **PAGED** | `CLAUDE.md` · `docs/` · the memory store (one fact per file) | someone has to **fetch** it (`Read` / `cat`) | **does not arrive by itself** | whatever the subject needs |
| **INTERRUPT** | path triggers · pre-touch guards · ceiling warnings | fires along the path without being called | **arrives when the path matches** | one sentence + a pointer |

> **The filing rule:** law, contract and yardstick live in the RESIDENT regime. Procedure lives in
> the PAGED regime. What must not be forgotten at the right moment becomes an INTERRUPT. Owner doc:
> [`CONTEXTO.md`](CONTEXTO.md).

## 4 · The pieces: what each one does, who delivers it, where the detail lives

### 4.1 · Resident: what arrives before the first decision

| piece | what it is | delivered by | owner doc |
|---|---|---|---|
| **Map, layer 1** `1_CONTRATO` | WHO WE ARE: method, authorizations, vetoes, how the operator tests | `scripts/mapa-hook.sh` on `UserPromptSubmit` (whole on turn 1, the core every `CADA_N` turns) and on `SessionStart:compact` | [`mapa/0_MAPA.md`](mapa/0_MAPA.md) |
| **Map, layer 2** `2_ONDE` | WHERE WE ARE: machines, ports, paths, databases | same | same |
| **Map, layer 3** `3_DECIDIDO` | WHAT HAS BEEN DECIDED: product law, one line per decision, with state and a proof glyph | same | [`mapa/5_COMO_MANTER.md`](mapa/5_COMO_MANTER.md) |
| **Map, layer 4** `4_FRENTES` | WHAT WE ARE DOING: the index of the fronts | **not loaded**: a door to each front's README | same |
| **The front's oracle** | the front's yardstick (per area plus a common part), injected BEFORE the building starts | `scripts/oraculo.py` on `UserPromptSubmit` and on touch | [`oraculo/README.md`](oraculo/README.md) |
| **`MEMORY.md`, the index** | one line per memory: `[N]` + gloss; **it is the only recall channel** | the runtime's memory block, every turn | [`MEMORIA.md`](MEMORIA.md) |
| **Baton** `mesa/BASTAO.md` | live state of the desk (work in flight, the operator's open items, the queue): the deterministic hand-off between contexts | on `SessionStart:compact`, a CUT (`scripts/bastao-entrega.py --emitir`, at most 9,500 units, so it arrives whole: the `*Updated` line, the newest entries at 600 units each, the footer) · and on `PostCompact` a `cat`, which arrives WHOLE only by riding the echo of a manual `/compact` and not at all on automatic compaction (measured: manual 23 of 23, automatic 0 of 49) | [`mesa/BASTAO_REGRAS.md`](mesa/BASTAO_REGRAS.md) |
| **Design** `mesa/DESENHO.md` | the OPEN: what was decided to build and where the drawing board is | the `desenho` skill, when the desk opens | [`skills/desenho/SKILL.md`](../skills/desenho/SKILL.md) |
| **Neighbors** | what is dirty in the working tree and is not this session's | `scripts/vizinhos-hook.py` on the session's first read | the script's header |

### 4.2 · Paged: what exists and waits to be opened

| piece | what it is | how it enters | owner doc |
|---|---|---|---|
| **Individual memory** | one fact per file, frontmatter with `id:` and `description:`; types `user` / `feedback` / `project` / `reference` | only if opened; the index line decides | [`MEMORIA.md`](MEMORIA.md) |
| **`CLAUDE.md`** | reference manual (technical fact) | `Read`; `Bash` does **not** pull it | [`CONTEXTO.md`](CONTEXTO.md) |
| **`docs/`** | the technical truth | opening it | the doc itself |
| **`INDICE_NUMERICO.md`** | table `[N]` -> file name; **a derived cache, never a source** | `scripts/memoria-resolve.py N` | [`INDICE_NUMERICO.md`](INDICE_NUMERICO.md) · [`MEMORIA.md`](MEMORIA.md) |

### 4.3 · Interrupt: what calls without being called

| piece | what it does | event | owner doc |
|---|---|---|---|
| **Dispatcher** `scripts/gatilho.py` | matches the **whole command** against the sources and warns (`PostToolUse`), charges (`Stop`) or blocks (`PreToolUse`) | the 3 events | [`gatilhos/CANAIS.md`](gatilhos/CANAIS.md) |
| Source `backlog` | a debt item with a door, charged on touch | touch | [`gatilhos/backlog.md`](gatilhos/backlog.md) |
| Source `memoria` | **cold memory called by the path**: "is there a memory that answers exactly this file?" | touch | [`gatilhos/memoria.md`](gatilhos/memoria.md) |
| Source `porta` (generated) | the state of the revolving doors (tare, target, orphans) | touch | [`PORTA.md`](PORTA.md) |
| Source `estacionado` | warns that a project's index block is out of the load, and how to bring it back | touch on a path of that project | [`gatilhos/estacionado.md`](gatilhos/estacionado.md) |
| Sources `duplicado` · `dependencia` · `promocao` | writing rules, dependencies between works, promotion | touch | `docs/gatilhos/` |
| **`scripts/guarda-ja-existe.py`** | when a rule is written, asks "does this already exist?" against the index and layers 1 and 3 (warns; lexical) | `PostToolUse` | the script's header |
| **`scripts/guarda-crase.py`** | blocks a backtick inside a heredoc | `PreToolUse:Bash` | the script's header |
| **`scripts/horizonte.py`** · **`scripts/janela-teto.py`** · **`scripts/mapa-orcamento-hook.sh`** | warnings about the horizon, the window ceiling and the map's budget | `PostToolUse` | the scripts' headers |
| **`scripts/memory-cap-probe.py`** | arithmetic of the index cap (lines and UTF-16 units) | `SessionStart` | [`CONTEXTO.md`](CONTEXTO.md) |

A guard that blocks touching production was part of the reference installation; it is
lab-specific and not included.

### 4.4 · Durability and integrity: what makes the system survive itself

| piece | what it does | owner doc |
|---|---|---|
| **Mirror** `scripts/memoria-espelho.sh` + an hourly cron job (`47 * * * *`) | projects the source (the runtime's `memory/` folder for the project) into `memoria/` in the repository, commits if it changed, pushes. It is the **only backup** of the memory | [`MEMORIA.md`](MEMORIA.md) |
| **Commit guards** `guards/memory-guards.sh`, proven by `guards/prove-fixture.sh` | integrity of **form**: the index is whole, `[N]` and the frontmatter form a bijection, the gloss is mandatory, the rule/case cascade is not silent, the baton delivers live state. **They do not judge truth**. The full CI battery of the reference installation is lab-specific and not included | [`guardas/memoria.md`](guardas/memoria.md) |
| **Revolving door** | for something to enter the resident regime, something leaves; the tare blocks at commit, the target pushes | [`PORTA.md`](PORTA.md) |
| **`scripts/contexto-medir.py`** | measures what each compaction lost and hands back what it fished out | [`CONTEXTO.md`](CONTEXTO.md) · [`gatilhos/CANAIS.md`](gatilhos/CANAIS.md) |
| **`scripts/memoria-recall.py`** | measures which memories are actually opened (the instrument that proved automatic recall does not exist) | [`MEMORIA.md`](MEMORIA.md) |

### 4.5 · Swap: rotating between projects

| piece | what it does | owner doc |
|---|---|---|
| **`scripts/memoria-estaciona.py --estaciona / --retoma / --lista`** | takes a block out of the loaded index (into `memory/indice_<slug>_estacionado.md`) and puts it back byte for byte; the operator's order is a **command**, not a hand edit | [`MEMORIA.md`](MEMORIA.md) |
| **`guarda_memoria_indice_integro`** | treats a memory cited in a parked block as parked, not orphaned | [`guardas/memoria.md`](guardas/memoria.md) |
| Source `estacionado` | the cherry-pick: warns on touch that the project's index is not loaded | [`gatilhos/estacionado.md`](gatilhos/estacionado.md) |

## 5 · How to switch projects without redoing the onboarding

Rotation works because **each kind of knowledge lives in a different regime**, and only one of
them changes when the project changes:

| kind of knowledge | where it lives | does it change when the project changes? |
|---|---|---|
| **Method** (how work is done, what is authorized, how the operator tests, how things are measured) | map layer 1 · the oracle's common part · `feedback` memories | **no**: this is the onboarding, paid ONCE |
| **Machines** (hosts, ports, paths) | layer 2 | only when the hardware changes |
| **Product law** | layer 3 (one block per product) | grows; never erased (a revoked line stays) |
| **The front's yardstick** | the front's oracle | arrives **on touch**: whoever edits C++ gets the C++ yardstick |
| **Named operational knowledge** of the project | its index block + `project` memories | **park / resume** by command |
| **Cold memory of a path** | the `memoria` trigger source | arrives **on touch** of the right file |
| **Work in flight** | baton + design | crosses compaction; disappears when the work closes |

**"Build it once and tie it to the context of the area"** is, as a mechanism, the **post-mortem of
every work** (map layer 1): 4 questions at closing. What did the work PROVE that changes the method
(-> memory, only the delta, with the proof pasted) · which memory did it CONFIRM / CONTRADICT / KILL
· what is technical truth (-> doc) · what is NOT worth a memory. And **tying** means choosing the
step of the cascade ([`mapa/5_COMO_MANTER.md`](mapa/5_COMO_MANTER.md)): guard -> hook/oracle -> doc
-> index. **The index is the most expensive step** (it loads every turn), so it comes last.

## 6 · Who does what

| who | what it does in the system | what it does NOT do |
|---|---|---|
| **The operator** (the human) | **originates** method law (layer 1) and product law (layer 3); decides domain cuts, what enters the oracle, what gets parked and resumed; gives the test gate; reads the screen when the instrument is blind | does not edit the index by hand (that is a command) |
| **The desk session** (the session that thinks, designs and writes briefings) | thinks, designs, writes the briefing; keeps the **baton** and the **design**; runs the post-mortem and writes **memory with the proof pasted**; operates the revolving door for what is its own | does not operate the work; does not re-distill what the worker returns (it reads the baton); does not invent method rules |
| **The worker session** (the one that operates) | operates, runs the gate, launches sub-agents; closes with a `## MEMORY CANDIDATES` section (at most 3) | does not design; builds only from a verbatim briefing |
| **The runtime** (the Claude Code hooks) | **delivery**: it is the only thing that guarantees arrival; each event has a measured contract (who accepts `additionalContext`, a ceiling of 10,000 units per command, order not guaranteed) | is not a channel on `PostCompact`; does not warn someone who only reads the index |
| **The commit guards** | integrity of form on every commit, proven failing | do not judge whether a statement is true |
| **The mirror job** | durability: the memory survives the loss of the machine | does not validate content |
| **git** | the chain of trust and the history of what was revoked | is not re-implemented |

## 7 · What the system does NOT guarantee, stated, with the doc that measures it

- **That a memory is CORRECT.** Only that it can be found, is whole and can be recovered; content
  is judgement, and two attempts to mechanize it gave false positives -> [`MEMORIA.md`](MEMORIA.md).
- **That a memory that was read was USEFUL.** The only measure is "it was opened" (floor: 47%) ->
  [`CONTEXTO.md`](CONTEXTO.md).
- **That the loaded resident text was READ.** No instrument answers this -> same.
- **That silence from `guarda-ja-existe.py` certifies something is new.** The predicate is lexical,
  and the map distills without citing -> the script's header.
- **That the slices arrive in the order they were registered.** That is why each one labels itself
  *"part N of M"* -> [`mapa/0_MAPA.md`](mapa/0_MAPA.md).

## 8 · Vocabulary: the brain names the pieces

**The convention:** each piece of the system takes the name of the movement it performs in the
brain. It is not a figure of speech; it is the same division of labor, and the clinical case of
section 0 is what shows it. Sources: Semon 1904 (*engram*); Scoville & Milner 1957 (H.M.); Tulving
1983 (*ecphory*, the cue finds the trace); Teyler & DiScenna 1986 (hippocampal index); Nader 2000
(reconsolidation).

| brain | movement | the piece here | owner doc |
|---|---|---|---|
| **working memory** (prefrontal) | hold the now; small, expensive, gone when attention moves | the **context window**, with a measured ceiling | [`CONTEXTO.md`](CONTEXTO.md) |
| **cortex** | store long-term content, spread out | **`docs/` + the memory store**: the truth | [`MEMORIA.md`](MEMORIA.md) |
| **hippocampus** | store the **index**, not the content | **`MEMORY.md`**: `[N]` + gloss pointing into the cortex | [`MEMORIA.md`](MEMORIA.md) · [`INDICE_NUMERICO.md`](INDICE_NUMERICO.md) |
| **engram** | the physical trace of one memory | the **individual memory** (one fact per file, `id:` in the frontmatter) | [`MEMORIA.md`](MEMORIA.md) |
| **encoding** | the episode becomes a trace | the **post-mortem**: 4 questions at closing, the memory is born with the proof pasted | [`mapa/1_CONTRATO.md`](mapa/1_CONTRATO.md) |
| **consolidation** (during sleep) | from episode to cortex, with nobody in the room | the **mirror job** and the **revolving door**: projection and cleanup outside the turn | [`MEMORIA.md`](MEMORIA.md) · [`PORTA.md`](PORTA.md) |
| **cue -> ecphory** | the cue finds the trace and the content comes back | the **path trigger**: a cold memory lit when the right file is touched | [`gatilhos/memoria.md`](gatilhos/memoria.md) |
| **recall** | bring it into the present | **opening the file** from its index line: manual, and that is the stated blind spot | [`MEMORIA.md`](MEMORIA.md) |
| **reconsolidation** | a recalled memory becomes unstable and is rewritten | **rotation on touch**: CONFIRMED / CONTRADICTED / KILLED | [`mapa/1_CONTRATO.md`](mapa/1_CONTRATO.md) |
| **extinction** | inhibits without erasing; the original trace remains | the **REVOKED line with its reason**: the tombstone is the asset | [`mapa/5_COMO_MANTER.md`](mapa/5_COMO_MANTER.md) |
| **active forgetting** | take out of the load what does not serve now | **park / resume** and the **purge** | [`MEMORIA.md`](MEMORIA.md) |
| **reflex** | a response before thought | the **pre-touch guards** that block (`scripts/guarda-crase.py`) | the script's header |
| **priming** | the right context before the decision | the **map** and the **front's oracle**, injected before building | [`mapa/0_MAPA.md`](mapa/0_MAPA.md) · [`oraculo/README.md`](oraculo/README.md) |
| **saved across a context switch** | what survives an interruption | the desk's **baton** and **design**, which cross compaction | [`mesa/BASTAO.md`](mesa/BASTAO.md) |

**The engineering terms for the same design**, to explain it to someone in 5 minutes:

| term | in one line |
|---|---|
| **resident / paged / interrupt** | the 3 regimes: always arrives · arrives if fetched · arrives when the path matches |
| **map** | the 4-layer digest that arrives on turn 1: who we are · where we are · what was decided · what we are doing |
| **oracle** | the front's yardstick, injected before building, on touch |
| **trigger** | an interrupt by path: one sentence + a pointer, on `PostToolUse` / `Stop` / `PreToolUse` |
| **guard** | a commit-time predicate, proven failing before it counts; it checks form |
| **index `[N]` + gloss** | the line that makes the agent open a memory; the number is born in the frontmatter, the gloss is mandatory |
| **revolving door** | for something to enter the resident regime, something leaves; the tare blocks, the target pushes |
| **baton / design** | the desk's NOW (work in flight / what was decided to build); crosses compaction |
| **park / resume** | swap of a project's index block, by command |
| **post-mortem** | the 4 questions at the closing of every work; it is where memory is born, with proof |
| **cascade** | the order for deciding where something lives: guard -> hook -> doc -> index |

---

## 9 · Who points here

**Declared population: 13 surfaces.** Each one owns a piece and carries, in its header or in its
section, one line that points back to this doc. The state (how many point back today) **does not
live here**: measure it with the command at the end of this section.

| # | surface | where the back-pointer lives |
|---|---|---|
| 1 | [`MEMORIA.md`](MEMORIA.md) | header |
| 2 | [`CONTEXTO.md`](CONTEXTO.md) | header |
| 3 | [`PORTA.md`](PORTA.md) | header |
| 4 | [`mapa/0_MAPA.md`](mapa/0_MAPA.md) | how the map relates to the rest |
| 5 | [`mapa/1_CONTRATO.md`](mapa/1_CONTRATO.md) | what reaches the agent (resident, slice 1) |
| 6 | [`mapa/5_COMO_MANTER.md`](mapa/5_COMO_MANTER.md) | the cascade |
| 7 | [`gatilhos/CANAIS.md`](gatilhos/CANAIS.md) | header |
| 8 | [`gatilhos/memoria.md`](gatilhos/memoria.md) | header |
| 9 | [`gatilhos/estacionado.md`](gatilhos/estacionado.md) | header |
| 10 | [`oraculo/README.md`](oraculo/README.md) | header |
| 11 | [`guardas/memoria.md`](guardas/memoria.md) | header |
| 12 | [`mesa/BASTAO_REGRAS.md`](mesa/BASTAO_REGRAS.md) | the baton's fixed head, **never** a dated entry |
| 13 | [`skills/desenho/SKILL.md`](../skills/desenho/SKILL.md) | section 1, the first act |

**Outside the population, on purpose** (this doc points to them; they do not point back):
[`INDICE_NUMERICO.md`](INDICE_NUMERICO.md) is **derived** and never edited by hand ·
[`gatilhos/backlog.md`](gatilhos/backlog.md) is a data source, cited by a source line, not the owner
of a piece · [`mesa/DESENHO.md`](mesa/DESENHO.md) and [`mesa/BASTAO.md`](mesa/BASTAO.md) are state,
and their dated entries would cite this doc and make the proof green by construction.

**How to measure it** (from the repository root; the baton's head lives in `BASTAO_REGRAS.md`, and
that is where it is measured):

```bash
for f in docs/{MEMORIA,CONTEXTO,PORTA}.md docs/mapa/{0_MAPA,1_CONTRATO,5_COMO_MANTER}.md \
         docs/gatilhos/{CANAIS,memoria,estacionado}.md docs/oraculo/README.md docs/guardas/memoria.md \
         docs/mesa/BASTAO_REGRAS.md skills/desenho/SKILL.md; do
  grep -q HIPOCAMPO "$f" || echo "MISSING: $f"; done
```
