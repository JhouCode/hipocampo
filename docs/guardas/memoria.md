# GUARDS · memory

> The **history** of the guards in this family, in plain text: why each one exists, what it refuses
> to block, the defect that created it, and how it was proven failing. The predicates live in
> `guards/memory-guards.sh`; each guard is proven by `guards/prove-fixture.sh` over
> `fixtures/guards/<guard>/{controle,mutante-N}/`, where the control must come out green and every
> mutant red. **The heading `## <function name>` is an address: do not rename it.**
>
> **The whole of the memory these guards defend (pieces, regimes, rotation, who does what) is
> [`HIPOCAMPO.md`](../HIPOCAMPO.md).**
>
> What is NOT here, on purpose: the warning for whoever will **edit** a predicate. That one stays
> next to the line in the bash file, because that is the path that protects; a distant doc does not.
>
> **Not included:** the reference installation also had a guard that checked a divergence ledger
> (a decided divergence must touch the file it names). The ledger is lab-specific, so that guard
> is not shipped.

## guarda_memoria_indice_integro

**What it protects.** `MEMORY.md` is the ONLY point of the memory store that can fail in silence.
**An individual memory does not load into the context; only the index does.** So a memory without
a line in the index is not "less visible"; it is **invisible**, and nothing reports it: the file is
there, intact, and is never read again.

On its first run it found **1 orphaned memory** (a file outside the index) and **1 index pointer
that did not resolve**, the latter written hours earlier with a relative path counted from the
wrong folder. Both defects are the same disease in two directions: the index and the disk
diverging with nobody asking.

And the index has **no turn budget**, unlike the map. Here the scarce resource is the BYTE, not the
turn: the map loads once per session, the index loads **on every turn**. That is why the budget is
in bytes and the message says how much is left **in lines**, the unit in which the index grows.

**When the index became `[N]` citations, this guard would have gone blind in TWO opposite
directions.** The WIDE axis (orphan) would have reported every memory at once and blocked every
commit; the NARROW axis (dead pointer) and the 80-byte per-line ceiling would have come out
**silently green**, which is worse: a guard green on the wrong axis says "all is well" with
authority. The block now resolves `[N]` -> file name through `scripts/memoria_ids.py`, and **a
missing resolver is a FAILURE, never green**: without it the guard cannot resolve any citation, and
"I found no pointer" would become "there is no pointer".

**Proven failing, 4 of 4 plus a positive control:** `[9999]` with no target lights *dead
citation*; a 105-byte entry lights the *per-line ceiling*; a deleted citation turns the memory into
an *orphan*; a nonexistent `MEM_IDS` lights *missing resolver*. Two defects of the guard itself
fell in those proofs: a `NameError` (which this guard's anti-blindness correctly turned into
"predicate DIED without a verdict") and a `\b` placed after `]`, where there is no word boundary,
which kept the 80-byte ceiling silent even with the predicate "fixed".

**The PARKED clause.** An index block taken out of the load lives in
`memory/indice_<slug>_estacionado.md`, moved by `scripts/memoria-estaciona.py`. A memory cited
**there** is not an orphan: it is parked, out of the load by decision, and still opens with
`scripts/memoria-resolve.py N`. A dead citation in a parked block is a FAILURE like one in the
index. **Why it had to exist:** one project's block of about 970 bytes stayed in every session,
because taking it out of the index made this guard block the mirror. **Proven failing, 3 of 3, on
a copy of the store (`MEM_DIR`):** a memory with no citation -> ORPHAN; the same memory cited only
in an `indice_t_estacionado.md` -> leaves the list; `[9999]` in the parked block -> *dead citation
in a PARKED index*. The script's control pair: `memoria-estaciona.py --selftest` (park -> resume ->
`MEMORY.md` byte for byte).

## guarda_memoria_description_sem_estado_transiente

**What it protects.** The `description:` is the SUMMARY read first inside the file, and it is what
a search matches. A wrong statement there is not a wrong detail; it is **the wrong summary served as
if it were the subject**.

**The defect that created it.** A memory's description said the change was *"in pre-production,
waiting for validation, committed locally without push"* while its body said *"in production since
a given date, pushed"*. The summary served the wrong state, and the body, which was right, was
never read.

**A correction it carries.** The guard once claimed the description "is the recall key, the only
thing that reaches the context when the memory is recalled". That is false in the measured
installation: there is no automatic recall (89 transcripts, 143,133 lines, 25 attachment types,
zero of them memory; `scripts/memoria-recall.py`). When the description arrives, the body came with
it. The guard survives for the reason above, not for the one it used to state.

**What it refuses to block.** It does NOT ban state, and the distinction was measured: **19
descriptions stated a state, most of them TERMINAL** (*in production*, *resolved*, *live*).
Terminal state does not rot backwards. What rots is **TRANSIENT** state: *pending*, *waiting*, *in
progress*, *in pre-production*. There were **3 of 187**, and all 3 were rewritten. The rule: the
description says the SUBJECT of the memory (what it holds, and why one would open it); the STATE
lives in the body, dated, where a new line goes in chronological order.

## guarda_memoria_nao_afirma_lei_morta

**What it protects.** Measured: **45 of the 112 pointers in `MEMORY.md` restated a law that the
map already delivers whole.** Trimming them was proposed and the measurement killed the proposal:
it would have saved **364 tokens** (1.9% of the resume load), and the duplicated fragment is exactly
what IDENTIFIES the memory. Removing the hook buys recall blindness for small change.

So the duplication STAYS, and the risk changes shape: when a law is revoked or postponed in the
map (`docs/mapa/3_DECIDIDO.md`), the memory's hook keeps stating the opposite, and the header of
`MEMORY.md` itself says *"when they disagree, the DOC wins"*. But nobody notices the conflict: both
sentences arrive in the same context, both look true, and the older one is read first (the memory
enters the system prompt; the map arrives after it).

**What it refuses to block.** It does NOT report duplication; duplicating a law that is still in
force is accepted and measured. It reports only the dangerous case: a memory stating what the map
already killed. Today that count is ZERO, and the zero is the point: the guard exists for the day a
line falls.

## guarda_memoria_cascata

**What it protects.** Each memory is split into two pieces: the **rule** (`escopo: metodo`, stands
on its own, without a single domain word) and the **case** (`escopo: <domain>`, the dated
measurement that proves it), linked by a pointer. The risk is not the number of files; it is the
**cascade going SILENT**: the method surviving alone while claiming a proof that already died, or
the case becoming an orphan with no rule.

**That is why the link carries a POPULATION (`prova: N`), not just an address.** A bare
`[[link]]` cannot be falsified; a number can be recounted. Measured on its first run, breaking it
on purpose: deleting a case lights the count plus a dead pointer; **adding a third case without
changing the number also lights it**, and that is the case no address would catch. Gaining proof
in silence is as silent as losing it.

**Life cycle.** A case is **immutable** (a measurement taken on a given day is what it was); a
method is **mutable**. Revoking a case forces a change to the method: the count only counts LIVE
cases, so the death does not go unnoticed downstream. The acceptance field (`revogados: M`) exists
because a red that never clears is what makes someone turn the guard off: after checking, it goes
quiet; if a second case dies, it wakes up.

**It delegates** to `scripts/guarda-cascata.py` instead of recounting in bash: a new guard that
re-implements a count that already exists creates a **second truth**.

## guarda_memoria_bastao_entrega_estado_vivo

**The defect that created it.** The compaction hook ran `cat` on
[`mesa/BASTAO.md`](../mesa/BASTAO.md), a file of about 100 KB. Above 10,000 units the runtime
writes the output to disk and puts only a preview of the first 2,000 UTF-16 units into the
context. The baton's fixed head grew from 805 bytes to 1,961 and then to 2,130, and from then on it
filled the whole preview: of the 72 deliveries persisted in the transcripts (fork copies excluded),
not one carried a line of live state. Nothing went red, because the hook "worked": `hook_success`
on all of them. The head moved to [`mesa/BASTAO_REGRAS.md`](../mesa/BASTAO_REGRAS.md), and the top
of the baton kept a single pointer line.

**The predicate.** The guard delegates to `scripts/bastao-entrega.py --guarda` (the emulation lives
in one place only). The script reads the `SessionStart` entry whose matcher is `compact` in the
project's hook settings (`settings.json`), simulates each `cat` of one versioned file with the
runtime's rule, and judges the text that would be DELIVERED. Green only with the `*Updated:`
line and at least one entry (`- `) inside the delivery, and at most one non-empty line before
`*Updated:`, which is the approved form. Each red names its cause: a delivery with no live
state; the head growing back with the state still inside it; a `SessionStart:compact` with no
emitter the script knows how to simulate.

**Why it starts from the hook and not from the path.** A guard that read `docs/mesa/BASTAO.md`
directly would stay green with the hook emitting something else, or with the `cat` outside
`SessionStart`. Mutant 2 of the fixtures is exactly that: a good baton on disk and the hook emitting
`BASTAO_REGRAS.md`, and the guard lights. An emitter it cannot simulate (a script, a cut, a pipe)
comes out red: whoever changes the emitter teaches the simulation to the script in the same commit.

**The hook now emits a CUT, and the guard simulates it.** The `SessionStart:compact` hook changed
from `cat` to `python3 .../scripts/bastao-entrega.py --emitir .../BASTAO.md`: the pointer, the
`*Updated:` line, the newest entries cut to 600 units each, and the footer whole, with a ceiling
of 9,500, below the threshold, so it arrives WHOLE. The guard recognizes that emitter (the
versioned script, with `--emitir` and one file) and runs the SAME cut function over the committed
file. A new red: a cut that exceeds the threshold and becomes a preview (a ceiling that did not
hold). The script's selftest covers the cut and the emitter, with mutants.

**What it refuses to block.** `PostCompact`: its `cat` arrives whole only by riding the echo of a
manual `/compact`, and does not arrive on automatic compaction ([`CONTEXTO.md`](../CONTEXTO.md);
measured: manual 23 of 23, automatic 0 of 49), so the guard neither counts on it nor requires it to
exist. And the rest of the baton: it does not measure what falls past the preview.

**The runtime's rule is borrowed, so it has a validator.** The emulation (2,000 UTF-16 units,
pulled back to the last `\n` when that newline is past unit 1,000, as measured on the runtime
version in use) reproduces 72 of 72 real previews. Deliberately wrong, it reproduces 0 of 72
(without the pull-back) and 20 of 72 (2,070 instead of 2,000). If a new runtime version changes
the rule, what lights is `python3 scripts/bastao-entrega.py --validar`, and only if someone runs
it: that is declared debt, not coverage.

**Proven failing.** On the baton file with the head at the top, over the working tree: *"the
delivery (1989 units) ends before \*Updated, which starts at byte 2130"*. After the change:
green, live state from byte 128. Fixtures in
`fixtures/guards/guarda_memoria_bastao_entrega_estado_vivo/`: a green control and 4 red mutants
(the head put back at the top · the hook emitting `BASTAO_REGRAS.md` · the `cat` only on
`PostCompact` · one line of the head back above `*Updated`).

**The guard simulates; DELIVERY is proven in the transcript.** A hook's success status proves
emission, not delivery. The command is `python3 scripts/bastao-entrega.py --desde <commit>
--mostrar`: rc 0 with live state in every compaction after the commit, rc 2 while none has
happened yet.

**The mirror is optional, and the guard says so.** In `guarda_memoria_indice_integro`, a mirror folder that is absent and NOT configured is a yellow warning ("no mirror configured -- the memory folder has NO backup"); configured (`MEM_ESPELHO` set, or files under the mirror path tracked in git, which `scripts/memoria-espelho.sh` leaves after its first run) and absent is a red failure. Fixture: `fixtures/guards/guarda_memoria_indice_integro/mutante-4`.
