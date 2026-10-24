# Hook-to-context channels -- what is a CHANNEL and what is only a BELL

> The foundation of the trigger dispatcher (`scripts/gatilho.py`). **Everything here was measured
> against the Claude Code runtime and against real events**, not read from the documentation --
> the public documentation was wrong about this subject more than once. In a conflict, **what is
> measured here wins**, and each cell says how to reproduce it. Re-measure after a runtime update:
> a channel is a property of the version you run.
>
> **The whole -- pieces, regimes and the role of each -- is [`../HIPOCAMPO.md`](../HIPOCAMPO.md)**;
> these channels are its **interruption** regime.

---

## 1 · Who accepts `additionalContext` -- the authoritative list

The runtime's validator **rejects** a `hookSpecificOutput` outside the contract and, when it
rejects, **prints the whole schema**. That is how this table was born: it is not a reading of the
docs, it is the validator speaking. To reproduce, make a hook return an invalid
`hookSpecificOutput` for the event and read the error.

| event | accepts `additionalContext`? | note from the schema itself |
|---|---|---|
| `UserPromptSubmit` | ✅ **required** | the channel the map hook (`mapa-hook.sh`) uses |
| `PostToolUse` | ✅ optional | **the public docs said it did not exist -- it does.** It arrives clean, labelled *"hook additional context"* |
| `PostToolBatch` | ✅ optional | an event the public docs did not list |
| `Stop` / `SubagentStop` | ✅ optional | *"Feedback for the model; **the conversation continues so the model can act on it**"* |
| `PreToolUse` | ❌ | has `permissionDecision` + `updatedInput` (a channel to **block**, not to speak) |
| **`PreCompact`** | ❌ | **rejected**, and the error shows on the user's screen at every compaction |
| **`PostCompact`** | ❌ | not in the schema |

Root fields any event accepts: `continue`, `suppressOutput`, `stopReason`, `decision`, `reason`,
`systemMessage`, `terminalSequence`, `permissionDecision`.

### What this decides in the dispatcher

| step | event | why |
|---|---|---|
| **D1 · WARN** | `PostToolUse` | speaks at the moment of the touch, without interrupting |
| **D2 · CHARGE** | `Stop` | the schema guarantees that **the conversation continues** -- it is a charge with a chance to pay in the same turn, not a farewell note |
| **D3 · BLOCK** | `PreToolUse` | `permissionDecision` is the only channel that stops the touch |

The three steps fall on **three different events**: a channel that breaks in an update takes down
one step, not the ladder.

`scripts/janela-teto.py` speaks through D1 too (`PostToolUse`, `hookSpecificOutput` envelope).
It also counts the session's **own** touches since the last compaction: a subagent's touch arrives
with the parent's `session_id` and `transcript_path`, and only `agent_id`/`agent_type` tell them
apart (measured on the real stdin).

---

## 2 · What each compaction event DELIVERS (real stdin, not the docs)

```jsonc
// PreCompact
{"session_id":"…","transcript_path":"<HIPO_PROJECT_DIR>/<session>.jsonl",
 "cwd":"…","prompt_id":"…","hook_event_name":"PreCompact",
 "trigger":"manual","custom_instructions":null}

// PostCompact -- about 19,000 chars in a real event
{"session_id":"…","transcript_path":"…","cwd":"…","prompt_id":"…",
 "hook_event_name":"PostCompact","trigger":"manual",
 "compact_summary":"<the WHOLE summary>"}
```

`session_id`, `transcript_path`, `cwd` and `prompt_id` were **not in the public docs**, and they
are what makes `PostCompact` useful: with the summary in hand and the transcript on disk, you can
measure **what fell out** at each compaction -- by machine, without depending on anyone's reading.

**Verdict:** `PreCompact` is a **bell**, not a channel -- it tells *when* and *with which
transcript*. `PostCompact` is a **measuring instrument**, and the best one there is.

### But `PostCompact` fires TOO EARLY to measure on its own

On the first real event, `PostCompact` recorded the **previous** compaction, not the one that had
just happened: when it runs, the new `compact_boundary` **has not been written to the transcript
yet**. Proved by the token counts -- the boundary it read carried the pre-compaction size of the
earlier compaction, not of this one. And `SessionStart:compact` fired **in the same second, before
it**, so a hook that gives the summary back read the ledger before the writer had created it.

**The order is fixed, and it is the runtime's.** Read in the Claude Code bundle (2.1.292, reported in
[anthropics/claude-code#103442](https://github.com/anthropics/claude-code/issues/103442); checked again
in 2.1.304): on the manual and the reactive paths the restore bundle, where `SessionStart:compact`
runs, is awaited **first**; `PostCompact` runs after it; the new boundary is written to the transcript
only after both. So at `SessionStart:compact` the compaction that just happened does not exist in the
transcript yet: a returner of swallowed turns placed there returned **0 of 117**, and on
`UserPromptSubmit` **117 of 117** (2026-08-14 to 2026-10-20).

**Two consequences that hold for any hook of this family:**

| trap | rule |
|---|---|
| the transcript **is not ready** when the compaction hook runs | do not measure on the event; measure **by state**, when the data exists |
| the compaction hooks run in an order **you do not set** | neither may depend on the file the other writes |

That is why `contexto-medir.py` became **state-driven**: whoever gives the summary back also
measures, and a key (`boundary minute | preTokens`) prevents measuring twice. A boundary without
a recorded summary **is not measured** -- it would measure 100% evaporation against an empty
string.

---

## 3 · CONTAMINATED CODE WORD -- the failure mode of every channel probe

> **A marker is only a marker if it is improbable IN THE CHANNEL AND ABSENT FROM THE
> CONVERSATION.** Talking about the marker contaminates it: a marker the transcript already
> contains measures the **conversation**, not the channel -- and returns green for an injection
> that **never happened**.

Measured: a probe looked for a random code word in the `PreCompact` summary, and the predicate
said **True** while the injection had been **rejected by the validator**. Every occurrence was of
the kind *"I created the probe with code word X"* -- the word had become a topic, and the summary
carried it on its own.

**And the three classic controls do not catch this:** positive (summary with the word), negative
(summary without it) and absence (field missing) all pass. **The missing control is *"could the
word be there for another reason?"***

---

## 4 · Frontiers -- what is still unmeasured

- **`custom_instructions` of `PreCompact` is INPUT**, coming from the user's `/compact <text>`.
  There is no hook channel to influence the summary; if that is wanted, the user types it.
- **`systemMessage`** exists in the root schema and **was not tested** -- the hypothesis is that it
  goes to the user's screen, not to the model's context. Without a measurement, it is not claimed.
- The events `PostToolBatch`, `UserPromptExpansion`, `StopFailure`, `SubagentStart`,
  `InstructionsLoaded` and others **exist in the runtime** (about 27 in total) and **were never
  exercised** here.

---

## 5 · Matching a touch -- the command text, judged per piece

The dispatcher matches each source row's pattern against `file_path` (Edit/Write) **or the Bash
command text** (`alvo_do_hook` in `scripts/gatilho.py`). A `Read`-only matcher misses most of the
touches: here the agent read through the shell far more than through `Read` (1,253 `Read` calls
against at least 3,151 shell commands that open a file, 30 days), and a file edited over ssh never
passes through a local `Read` at all. Each row carries its own pattern, so the command is checked
against a small known set, not scanned for anything path-shaped.

**The trap: a compound command contaminates.** Measured in the pilot: `cp ...crontab... && ls -l
.../backup.sh` charged the backup item as a **write**, because the `cp` made the whole command a write
and the `ls` only mentioned the path. The fix (`escrita_do_item`): split the command into the pieces
that run separately (`;` `&&` `||` `|` newline), and judge the write **per item, in the piece that
matched**. Bash is a read by default: erring low lets one warning pass, erring high blocks a read.

**An ignored warning is a measurement.** Each row counts the turns that touched it without acting
(`rides`); at 3 the touch asks before it passes (D3). A row that keeps reaching the ask is either
wrong or should become a check.

Discussion: [anthropics/claude-code#78795](https://github.com/anthropics/claude-code/issues/78795).

