# CONTEXTO — the channels, what each one guarantees, and where each thing lives

> **The view of the WHOLE — pieces, regimes, rotation and the role of each — is the umbrella
> [`HIPOCAMPO.md`](HIPOCAMPO.md); this doc owns the CHANNELS.**
>
> The distilled version that loads in every session lives in the map (`docs/mapa/`), in the section
> on *what reaches the agent*; **between the distilled version and this doc, this doc wins** — the
> normal doc × distillate hierarchy the map itself declares.
>
> **Law versus technical fact.** A **law** in conflict → the **map** wins, because it always
> arrives; a **technical fact** in conflict → the **manual** wins, because it has the detail. This is
> not a preference: a source that **does not arrive** cannot arbitrate a conflict, and a revocable law
> in an absent file would have two answers depending on whether someone ran `Read` in that session.
>
> **Why this doc exists:** each piece had its own doc — the memory in [`MEMORIA.md`](MEMORIA.md), the
> map in [`mapa/`](mapa/), the trigger dispatcher in [`gatilhos/`](gatilhos/CANAIS.md), the guards in
> [`guardas/`](guardas/memoria.md). **None of them answered how they compose**, and the question
> nobody had asked was the one that mattered: *of all these things, what is guaranteed to arrive?*

---

## 1 · The three regimes — and the difference is GUARANTEE, not content

| regime | who is here | how it enters | always arrives? |
|---|---|---|---|
| **RESIDENT** | map (layers 1·2·3) · the front-line oracle · `MEMORY.md` | session / tool-call hook · `claudeMd` block | **yes** |
| **PAGED** | the project manual (`CLAUDE.md`) · ~100 docs · ~200 memories | someone has to **fetch** it | **no** |
| **INTERRUPTION** | trigger items + the generated `porta` source · the guards | fires on the path, without being called | yes, **when the path matches** |

In the vocabulary of [`HIPOCAMPO.md`](HIPOCAMPO.md): the window where the three regimes arrive is the
**working memory**; `docs/` + the memory collection are the **cortex**; `MEMORY.md` is the
**hippocampus** (the index, not the content); each individual memory is an **engram**.

> ### The housekeeping law: **law, contract and ruler live in the RESIDENT.** Procedure lives in the paged. What must not be forgotten at the right moment becomes an INTERRUPTION.

---

## 2 · What was MEASURED — 89 transcripts, 144 thousand lines

### 2.1 · The paged regime is barely fetched
| measure | number |
|---|---|
| live memories opened at least once | **95 of 202 (47%)** |
| never opened | **107** |
| sessions that open at least one | 51 of 89 (57%), median **1** |
| memories opened by a fan-out of 11 agents | **0** |
| memories opened by a fresh chat over 125 tool calls | **0** |

⚠️ **The 47% is a FLOOR.** Instrument: [`scripts/memoria-recall.py`](../scripts/memoria-recall.py), and
it has already erred twice in opposite directions (§5).

### 2.2 · `CLAUDE.md` is pulled by `Read` — and `Bash` does not open it
| tool before the injection | of the 196 | of the 64 openings |
|---|---|---|
| **`Read`** | **126** | **49** |
| `Bash` | 55 | 13 |
| `Edit`/`Write` | 8 | 1 |

**Control:** two test sessions ran `cd` into the project folder and received **zero**; of the 55
`Bash`, 40 did not even mention the path — they were **re-injections** in a session that already had
it. In a shell-first session, `CLAUDE.md` **does not exist**.

**Field proof:** two fresh chats (15 and 125 tool calls) solved real tasks without it, obeying the
production rules, permissions, curation and commit conventions — all through the **resident**.

### 2.3 · The volume, and where it goes
| source | total in the sample | per injection | share |
|---|---|---|---|
| `CLAUDE.md` | 16.80 MB / 196× | 87.8 KB | **85.8%** |
| map + oracle | 2.25 MB / 810× | 2.9 KB | 11.5% |
| triggers | 0.52 MB / 302× | 1.8 KB | 2.7% |

Charged per session: **median 133 KB**, mean 247 KB, peak 1,789 KB.
**86% of the injections are repeated content** (955 of 1,112).
The whole memory collection (802 KB) fits **25×** inside what was already charged.

---

## 3 · What each channel is good at — measured, not assumed

- **The resident solves ENTRY, not knowledge.** It knows nothing specific; it guarantees the law
  arrives before the decision. It was the map that held the production rules in two fresh chats.
- **The INDEX is the recall channel — not the `description`.** There is no automatic recall (see
  [`MEMORIA.md`](MEMORIA.md)): a memory's body only enters if the agent opens it, and what makes it
  open is the index line. Proof: a fresh chat opened a memory never read in 89 sessions and named the
  index line as the cause.
- **The collection serves NAMED OPERATIONAL knowledge** (*"the message of the day has a length
  limit"*): things found by noun. **Method and law do not come from it.** Engineering work on code
  does not consult it — three measurements in a row with **zero**.
- **Interruption is the only channel that changes behaviour without the agent remembering.** A ruler
  that loads does not prevent the error: in 4 slips on one day, the rule was on screen, read.

---

## 4 · The instruments, and the question each one answers

| instrument | answers |
|---|---|
| [`memoria-recall.py`](../scripts/memoria-recall.py) | which memories are opened, by whom, when |
| [`oraculo.py --selftest`](../scripts/oraculo.py) | does the front-line ruler fit its ceiling, with backing? |
| [`gatilho.py --selftest`](../scripts/gatilho.py) | are the interruption sources intact? |
| [`contexto-medir.py`](../scripts/contexto-medir.py) | what did the compaction summary drop from the user's turns? |
| [`contexto-consumo.py`](../scripts/contexto-consumo.py) | where the window's volume comes from, and what was billed |
| [`janela-teto.py`](../scripts/janela-teto.py) | is the window past a step (cost = size × remaining turns)? |
| [`memory-cap-probe.py`](../scripts/memory-cap-probe.py) | which `MEMORY.md` cap bites first, and where |
| [`bastao-entrega.py`](../scripts/bastao-entrega.py) | does the compaction hook deliver live state? |
| the guards | **most of them verify FORM** |

🚨 **The gap:** every memory and doc guard verified **form** — intact index, byte-for-byte mirror,
per-line ceiling, pointer that resolves. **None verified whether the claim was TRUE.** A doc saying
the wrong thing passed all of them. A guard that checks truth has to check it against the source the
claim cites.

---

## 5 · Declared blindness

- **13 session openings came after a `Bash`** and what sets them apart is unknown. No mechanism was
  invented.
- **Recall is a FLOOR, and the instrument already erred twice in opposite directions** on the same
  day: it counted as a read a path written **inside a heredoc** (inflated), and did not see `cd` + a
  bare name (blinded). **34%** was published when it was 47%. Only the control told them apart.
- **There is no measure of "was useful"** — only of "was opened". A memory read and not cited does
  not show up.
- **The resident that was NOT used cannot be measured.** The map loads whole in every session; how
  much of it is actually read, no instrument answers.

---

## 6 · The runtime's limits on hook output — measured in transcripts and read in the binary

> 🚨 **A hook's text output has a per-command cap of 10,000 units.** Above it the runtime persists
> the output to disk and puts only a **preview of the first 2,000 units** in the context, wrapped in
> `<persisted-output>` with a `Preview (first 2KB):` marker.

| fact | number | how it was established |
|---|---|---|
| persist threshold | **10,000** UTF-16 units | a text output of 9,586 units arrived whole; one of 10,057 became a preview |
| preview size | **2,000** UTF-16 units (JS `.length`) | measured against real previews in the transcripts |
| preview cut | pulled back to the last `\n` **when it falls after unit 1,000**; otherwise a hard cut | same function; checked against every real preview by `bastao-entrega.py --validar` |
| preview in bytes | median **2,070 B** | includes the 3 B of the `...` the runtime appends — it is not a fixed byte count |
| astral characters | count **2** units each | UTF-16 surrogate pairs |

**Consequence for anything injected by hook:** what must arrive has to sit in the first 2,000 units,
or the whole output has to stay under 10,000. A fixed head at the top of an injected file (2,130 B)
filled the whole preview: in **0 of 72** persisted deliveries did the live state get in. The fix is
the baton's shape — 1 pointer line on top, the live state right after, the rules in a separate file
(§8) — and a cut emitted under the threshold (`bastao-entrega.py --emitir`).

---

## 7 · `PostCompact` is not a channel — `SessionStart:compact` is

> 🚨 **A `PostCompact` hook does NOT deliver context to the model.** To return content after a
> compaction, use `SessionStart:compact`, which injects literally. The writer/returner pair
> (`contexto-medir.py`) already does this — and the choice turned out to be mandatory, not preference.

**The measurement.** A canary in `PostCompact` with an ID generated at firing time (`epoch+PID`), so
that no text written before the event could contain it. Positive control of the EMITTER verified
**before** trusting any silence from it — the step whose absence almost produced a wrong published
number on the first attempt.

| question | answer | population |
|---|---|---|
| does the hook run? | **yes** | 1 real firing, `trigger=manual` |
| does it produce a context attachment? | **no** | `"hookEvent":"PostCompact"` = **0 in 664 transcripts** |
| positive control, same field | `UserPromptSubmit` 52 · `PostToolUse` 44 · `SessionStart` 15 · `Stop` 8 · `PreToolUse` 3 | same sample |
| does stdout reach the model? | **yes, by HITCHHIKING** | `type:"user"` inside `<local-command-stdout>` |

**The mechanism.** The runner returns only `userDisplayMessage`. There is no `newCustomInstructions`
(`PreCompact` has it). But the `/compact` slash command **echoes its own result into the transcript**,
and the transcript is the context — so the text rides along on the command's echo. **No command, no
echo.**

**The inversion that matters:** the field is called `userDisplayMessage`, and the user, looking at the
screen, saw **only** the "conversation compacted" line. No hook line, not even collapsed. The string
"for display to the user" reached the MODEL and did not reach the USER.

### On AUTOMATIC compaction it arrives by NO path

An automatic compaction was forced by filling a chat to the limit (`trigger:"auto"`, `compact_summary`
filled; the raw payload was kept whole, because the event is expensive and does not repeat).

| question | result |
|---|---|
| did the hook RUN on auto? | **yes** |
| marker id in the transcript? | **0** |
| marker text, without the id? | **0** |
| `"hookEvent":"PostCompact"`? | **0** |
| `<local-command-stdout>Compacted`? | **0** — the auto was PURE |
| **positive control** `"hookEvent":"PostToolUse"` | **lights up**, same file, same filter, same search |

**Both halves close:** the manual hitchhike depended on the `/compact` echo; with no command there is
no echo, and there never was an attachment. **On auto, `PostCompact`'s stdout does not reach the
model.** Confirmed later on the baton's own deliveries: on automatic compaction only
`SessionStart:compact` arrived, cut at the preview (**49 of 49**); on the manual `/compact` the whole
baton rode along on the `PostCompact` echo (**23 of 23**).

⚠️ **What does NOT follow:** the hook **fired** on both triggers. A *dispatch* failure reported on
another platform still stands — what was measured here is *propagation*. They are two problems.

Published in [anthropics/claude-code#77832](https://github.com/anthropics/claude-code/issues/77832).

---

## 8 · The baton — the deterministic handoff between contexts

The compaction summary comes from a summarizer we do not control (measured: 97% cut, 8 of 36 user
turns lost). **`docs/mesa/BASTAO.md` is the deterministic anchor**: the live state of the session
(work in flight, pending decisions, fronts, open doors), injected by hook on `SessionStart:compact`.
It is updated at every work event — the post-mortem is the natural ride. `contexto-medir.py` stays as
the net that catches what the summary drops; a manual instruction to `/compact` is reinforcement, not
mechanism.

**Rule 2 of EVAPORATED:** a turn is judged by the user's own segments (without the
`<pasted_content>` blocks) and evaporates only if its signature did not arrive **and** fewer than half
of those segments did; `devolvida` is set only once everything came out (`emitidas` counts it). New
ledger records carry `"regua": 2`; older ones are rule 1 and are not re-measured. The defect and the
numbers are in the header of `scripts/contexto-medir.py`.

**Its shape follows §6:** line 1 is a pointer to [`mesa/BASTAO_REGRAS.md`](mesa/BASTAO_REGRAS.md)
(what the baton is and its rules), line 2 is the `*Updated:` line, then dated entries (`- `), newest
first, then footer sections (`## …`). The hook runs `bastao-entrega.py --emitir docs/mesa/BASTAO.md`,
which emits a cut that always fits under the 10,000-unit threshold: the pointer, the `*Updated:`
line, the newest entries (each up to 600 units), the footer whole up to half the ceiling, and a line
naming what was left out. `bastao-entrega.py --guarda` simulates what the registered hook would
deliver and fails when the delivery carries no live state.

---

## 9 · The index cap warnings are BOTH write-time

> 🚨 **No `MEMORY.md` warning reaches a session that only READS the index.** Both exist, and both
> fire on `PostToolUse:Edit`. A session that does not edit the index is never warned of anything.

```
"...MEMORY.md is 174 lines, approaching the 200-line read limit"   -> PostToolUse:Edit
"...MEMORY.md is 19.6KB, approaching the 24.4KB read limit"        -> PostToolUse:Edit
```

**Population: 664 transcripts, 6 occurrences, one machine.** All arrive as
`attachment: hook_additional_context` — they reach the model's context when they fire.

⚠️ **The name lies: the warning is called `200-line read limit` and the trigger is the WRITE.** Count
on a warning only for whoever **edits** the index — whoever only reads passes the cap seeing nothing.

**The ruler is [`scripts/memory-cap-probe.py`](../scripts/memory-cap-probe.py)** — the three defects of
its v1 are named in its header. ⚠️ It is **arithmetic on the file**: it predicts the cut, it does not
measure it. The documented cap is 25,000 units (a bracket measured in the discussion puts the real
boundary in [24,958, 25,018)) and 200 lines; whichever closes first binds.

Discussion: [anthropics/claude-code#82056](https://github.com/anthropics/claude-code/issues/82056).

---

## 10 · WHAT WE DO NOT HAVE — measured blindness

> This section exists because **an undeclared absence becomes an assumption in the next session**.
> Each line says what was tried and why it failed — not a wish list, an inventory of limits.

### 10.1 · What we could not MEASURE

| we do not have | what was tried | why it failed |
|---|---|---|
| **a headless behavioural arm** | `claude -p` to run probes | the CLI was not authenticated for `-p`; the recorded answer is `<synthetic>`. The only way is an interactive session with a human reading the screen |
| **the second cap string** (`Only part of it was loaded`) | search over **647 transcripts** | **0 occurrences** — the index never really overflowed. When it fires is unknown |
| **a store outside a git repo** | — | the docs say *"outside a git repo, the project root is used instead"*. **Not tested.** Whether two non-repo folders under a common parent share a store is open |
| **semantic duplication between collection and resident** | lexical detector: does the memory's name appear in the map/oracle? | **the positive control did NOT light** — the map distills without citing. It needs semantic comparison |
| **why 119 memories were never opened** | hypothesis: compressing the index degraded recall | **refuted, in the opposite direction**: announced alone, **59.4%** never opened (19/32) against **53.5%** of the compressed ones (46/86). A long description does not protect. **No measured explanation** |
| **"was useful"** | — | there is a measure of *was opened* (48%, a FLOOR). A memory read and not cited does not show up |

### 10.2 · An instrument that proved INVALID — do not reuse

🚨 **Asking the model what it sees is not measurement.** Same index, same setup: asked directly
(*"what are the first and last markers?"*), it answered **`NONE`** — while obeying instructions that
only existed inside that index.

**The self-report did not degrade: it INVERTED.** Any number that depends on asking the model what it
has loaded must be treated as unreliable.

**What works instead:** a behaviour needle — plant an instruction and see whether it is followed, or a
marker with its own ordinal and see whether it is enumerated.

⚠️ **And the marker must be unforgeable in ALL channels, not only the one under test.** One round used
`DELTA`, which occurs twice in an unrelated injected document. It did not corrupt the result — by luck.

### 10.3 · Numbers that are a CEILING, not a count

- **"orphan" memories** — the predicate that finds them is lexical (§10.1), and the map distills
  without citing. The number is a **ceiling**; by how much it is inflated is unknown.
- **command anchors** — the split `99 with / 19 without` was reproduced by two predicates written
  separately, but the first run of the second gave `92/27` by counting a network address as an
  anchor. **What counts as an anchor is a choice, and it moves the number by 8 points.**

### 10.4 · What we do not use as a TOOL, on purpose

- **`.claude/rules/` with `paths:`** is not used: the native trigger only fires on **reading a file**,
  and a session that works through the shell or a database never matches any pattern. `gatilho.py`
  matches against the **whole command** — strictly better. Migrating to the native one would be a
  regression.
