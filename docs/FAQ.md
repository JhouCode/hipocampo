# FAQ — the questions people asked, and where the answer lives

> Every question below was asked in a public thread, most of them more than once, by different
> people. Each answer is short and points to the doc or the code that holds the measurement; **in a
> conflict, that doc wins** — this page is a router, not a second copy. The numbers come from one
> operator's setup (see the README's [known limits](../README.md#known-limits)): Claude Code run from
> `/`, much of the work over ssh.

---

## Did it arrive?

### My hook reports success. Did its text reach the model?
Not necessarily. `hook_success` proves the hook **ran**. Text output above **10,000** UTF-16 units is
saved to disk and the model gets a **2,000**-unit preview, with the record still saying success; the
full file was read back in at most 7 of 210 cases. Keep every injected payload under the cap, and
prove delivery by comparing what the hook emitted with what the transcript recorded.
→ [`CONTEXTO.md` §6](CONTEXTO.md) · threads [#84021](https://github.com/anthropics/claude-code/issues/84021), [#91614](https://github.com/anthropics/claude-code/issues/91614), [#70555](https://github.com/anthropics/claude-code/issues/70555)

### Did my `MEMORY.md` load whole?
Read the `instructions` attachment in the transcript: it lists the index and its content. The caps are
200 lines and 25,000 UTF-16 units, whichever closes first; past them the entry ends in a `> WARNING`
that quotes the first lost line. A canary has two traps: it can be found inside that warning, and on
the first prompt the record is not written yet. `scripts/memory-cap-probe.py` predicts the cut before
it happens.
→ [`CONTEXTO.md` §9 and §11](CONTEXTO.md) · threads [#82056](https://github.com/anthropics/claude-code/issues/82056), [#99403](https://github.com/anthropics/claude-code/issues/99403)

### Why does my `CLAUDE.md` not load?
A nested `CLAUDE.md` loads when something under it is **read with `Read`**: of 196 injections, 126
followed a `Read`, most of the 55 after a `Bash` were re-injections, and a plain `cd` delivered
nothing. An agent that works through Bash rarely pulls it. The way out is to split by guarantee: what must never be missing moves to a distillate printed by
hook (the map), and `CLAUDE.md` becomes a manual.
→ [`CONTEXTO.md` §1 and §2.2](CONTEXTO.md) · [`scripts/mapa-hook.sh`](../scripts/mapa-hook.sh) · thread [#90450](https://github.com/anthropics/claude-code/issues/90450)

### Does Claude Code recall a memory file on its own?
No. In 190 sessions over 61 days, **0** memory files entered the window without the agent opening
them. What makes the agent open one is its **index line**, so the line carries a gloss of what the
memory is about, not just its file name.
→ [`MEMORIA.md` §1.1 and §4](MEMORIA.md) · thread [#82056](https://github.com/anthropics/claude-code/issues/82056)

---

## Compaction

### Can a `PostCompact` hook give context back to the model?
No. After an automatic compaction its output reaches the model by no path (0 attachments in 664
transcripts); on a manual `/compact` it only rides the command's echo, so it seems to work when you
test by hand. Use `SessionStart` with matcher `compact`, under the cap.
→ [`CONTEXTO.md` §7](CONTEXTO.md) · threads [#77832](https://github.com/anthropics/claude-code/issues/77832), [#70555](https://github.com/anthropics/claude-code/issues/70555), [#82017](https://github.com/anthropics/claude-code/issues/82017)

### In what order do the compaction hooks run?
Fixed by the runtime: `SessionStart:compact` first, `PostCompact` after it, and the new boundary is
written to the transcript only after both. So nothing on a compaction event can read the compaction
that just happened; measure by state, on the next touch.
→ [`gatilhos/CANAIS.md` §2](gatilhos/CANAIS.md) · thread [#103442](https://github.com/anthropics/claude-code/issues/103442)

### How do I get back the user turns the summary dropped?
`contexto-medir.py --devolver` on `UserPromptSubmit`: it measures each compaction against the
transcript and returns, on the first prompt after it, the turns that did not survive. On
`SessionStart:compact` it returned 0 of 117; on `UserPromptSubmit`, 117 of 117. For live work, keep a
small state file (the baton) and print a cut of it on `SessionStart:compact`.
→ [`devolver` in `scripts/contexto-medir.py`](../scripts/contexto-medir.py) · [`CONTEXTO.md` §8](CONTEXTO.md) · thread [#103442](https://github.com/anthropics/claude-code/issues/103442)

### What happens to my compaction hooks when a subagent compacts?
`SessionStart:compact` fires for the subagent and its output lands **in the subagent** (81 of 81),
but the payload is the main session's. A hook that consumes state there acts on the main session's
data inside the subagent. Rule: state only on `UserPromptSubmit`, which a subagent never fires (0 of
848 subagent transcripts); on the compaction event, only read-only output.
→ [`CONTEXTO.md` §7](CONTEXTO.md) · thread [#91910](https://github.com/anthropics/claude-code/issues/91910)

### Why does injected context keep growing until the session recompacts?
Re-injection with no ceiling. Here `CLAUDE.md` was 85.8% of everything injected, and 86% of all
injections repeated content the session already had. What bounded it: a budget per source (slices
under the cap, with a guard that fails before one crosses it), a small cut of live state after
compaction, and the full map only on the first turn, the core every N turns after.
→ [`CONTEXTO.md` §2.3 and §6](CONTEXTO.md) · [`scripts/mapa-orcamento-hook.sh`](../scripts/mapa-orcamento-hook.sh) · thread [#103442](https://github.com/anthropics/claude-code/issues/103442)

---

## Memory by trigger

### My index is over the cap. What do I take out?
Each memory goes to the cheapest layer that still gets it there in time: the **index** for what any
session needs; **parking** for a whole project not in use (one command out, one command back, byte
for byte); a **trigger** for a memory tied to a path; the **map** for rules that hold on any path.
Parking two projects took one index from 93.7% to 71.5% of the size cap.
→ [`MEMORIA.md` §5](MEMORIA.md) · [`gatilhos/memoria.md`](gatilhos/memoria.md) · thread [#99403](https://github.com/anthropics/claude-code/issues/99403)

### Why not trigger a memory on `Read` only?
Because most touches are not a `Read`: the shell opens files far more often, and a file edited over
ssh never passes through a local `Read`. The trigger matches `file_path` **and** the Bash command
text. Measured: the injected line (median 172 characters) was enough in at least 97.6% of 495
firings; the body stays on disk.
→ [`gatilhos/CANAIS.md` §5](gatilhos/CANAIS.md) · [`gatilhos/memoria.md`](gatilhos/memoria.md) · thread [#78795](https://github.com/anthropics/claude-code/issues/78795)

### How do I match shell commands without false positives?
Check the command only against the known set of patterns that have a trigger, and judge a write per
piece of the command: in `cp ... && ls .../file`, the `cp` must not make the `ls` a write.
→ [`gatilhos/CANAIS.md` §5](gatilhos/CANAIS.md) · [`escrita_do_item` in `scripts/gatilho.py`](../scripts/gatilho.py) · thread [#78795](https://github.com/anthropics/claude-code/issues/78795)

### What do I do with a warning the agent keeps ignoring?
Escalate by counter, not by hope: warn at the touch (`PostToolUse`), charge at the end of the turn
(`Stop`), and after 3 ignored turns ask before the touch passes (`PreToolUse` with
`permissionDecision: "ask"`). The three steps sit on three events, so one broken channel takes down
one step. A row that keeps reaching the ask is wrong or should become a check.
→ [`gatilhos/CANAIS.md` §1 and §5](gatilhos/CANAIS.md)

---

## Cost and proof

### What does all this cost per request?
Everything resident is paid on **every request**: the index was 1.4 to 2.2% of all input over the
article's window, and anything a hook puts back costs the same way. That is why a trigger injects a
line instead of the body (79 thousand characters over 501 firings, against 1.68 million for the
bodies).
→ [`MEMORIA.md` §5](MEMORIA.md) · [`data/custo_indice.csv`](../data/custo_indice.csv) · [`gatilhos/memoria.md`](gatilhos/memoria.md)

### How do I know a guard actually works?
It has to be seen failing. Every guard here ships with a fixture: green on its control, red on each
named mutant, and the prover runs them all.
→ [`guards/prove-fixture.sh`](../guards/prove-fixture.sh) · [`fixtures/guards/`](../fixtures/guards/) · README, [This repository's own guard](../README.md#this-repositorys-own-guard)
