# The rules of the baton

> **The fixed head of [`BASTAO.md`](BASTAO.md), moved here whole.** The compaction hook puts in the
> context only the preview of the first 2,000 units of the baton, and this head (2,130 B) filled the
> whole preview: in 0 of 72 persisted deliveries (counted without fork copies) did live state get in.
> The top of the baton kept 1 pointer line to this file (see [`../CONTEXTO.md`](../CONTEXTO.md) §6).
> **Below the rule is the text of the head**: the rules did not change, only their place. Where it
> says "this file" or "arrives by hook", the subject is `BASTAO.md`.

---

<!-- THE BATON — arrives by hook at every COMPACTION (SessionStart:compact). -->
# 🏃 THE BATON — the live state of the working session

> **What it is:** the handoff between contexts. The compaction summary comes from a summarizer we do
> not control (measured: 97% cut, 8 of 36 user turns lost); this file is the DETERMINISTIC anchor —
> what the session cannot lose crosses over here. It is the **save point of the context switch** of
> [`HIPOCAMPO.md`](../HIPOCAMPO.md) — the whole of the agent's memory: pieces, regimes, rotation and
> the role of each.
> **Maintenance rule:** the session updates this file at EVERY work event (launched a worker, work
> closed, a decision became pending on the user) — the post-mortem is the natural ride. Dead state
> leaves at once; this is NOT a log, it is the NOW. `contexto-medir.py` keeps fishing for lost turns —
> the baton does not replace it, it anchors the rest.
>
> **SIGNATURE:** every entry carries who wrote it — a stable session nickname at the end of the line,
> backed by a transcript id in a session registry (a route name is cache; a route is resolved when
> sending). Doubt about an entry → the transcript of the signed id, without asking anyone for a hash.
> The chain of trust is GIT ITSELF (not re-implemented); commits carry a trailer
> `Session: <nickname>`. Strong authorship (GPG) stays as a door — only if the threat model changes.
> **Commit race between sessions:** the git lock protects — whoever loses the race gets
> `cannot lock ref`, and the rule is to CHECK `HEAD` against the working tree before committing again
> (another session may have swept your files into its commit). Never re-commit blindly; never remove
> someone else's lock.
> **Two namespaces, both numeric, never crossed:** `[N]` = MEMORY · a session nickname = SESSION.
> Brackets never sign a session; a session nickname never cites a memory — chance can produce the same
> number in both, and it is the glyph that separates them.
>
> **SHAPE (what the compaction guard checks):** line 1 is the pointer to this file; line 2 is
> `*Updated: <date> <time> — the time comes from \`date\`, never estimated*`; then the entries, one
> per line starting with `- `, NEWEST FIRST; then the footer sections (`## …`). At most 1 non-empty
> line before `*Updated:`. The hook emits a cut (`bastao-entrega.py --emitir`) that always fits under
> the runtime's 10,000-unit threshold; `bastao-entrega.py --guarda` fails when what the hook would
> deliver carries no `*Updated:` line with at least 1 entry after it.
