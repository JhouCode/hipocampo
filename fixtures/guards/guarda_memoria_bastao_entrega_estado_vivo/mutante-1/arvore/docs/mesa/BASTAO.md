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
*Updated: 2026-01-20 17:05 UTC — the time comes from `date`, never estimated (s3)*
- ✅ **(2026-01-20 17:00) Export endpoint of service-a: step 1 recorded.** The worker agent ran the change on staging and the gate confirmed it; the evidence is in `logs/export-01.log`. What is left is written in the proposal, and the next step waits for the load test numbers before anything touches production. (s1)
- 🔄 **(2026-01-20 16:07) Reports table migration: step 2 recorded.** The worker agent ran the change on staging and the gate confirmed it; the evidence is in `logs/reports-02.log`. What is left is written in the proposal, and the next step waits for the load test numbers before anything touches production. (s2)
- ⏸️ **(2026-01-20 15:14) Cache layer of the web app: step 3 recorded.** The worker agent ran the change on staging and the gate confirmed it; the evidence is in `logs/cache-03.log`. What is left is written in the proposal, and the next step waits for the load test numbers before anything touches production. (s3)
- ✅ **(2026-01-19 14:21) Nightly job schedule: step 4 recorded.** The worker agent ran the change on staging and the gate confirmed it; the evidence is in `logs/nightly-04.log`. What is left is written in the proposal, and the next step waits for the load test numbers before anything touches production. (s1)
- 🔄 **(2026-01-19 13:28) Queue consumer retries: step 5 recorded.** The worker agent ran the change on staging and the gate confirmed it; the evidence is in `logs/queue-05.log`. What is left is written in the proposal, and the next step waits for the load test numbers before anything touches production. (s2)
- ⏸️ **(2026-01-19 12:35) Search index rebuild: step 6 recorded.** The worker agent ran the change on staging and the gate confirmed it; the evidence is in `logs/search-06.log`. What is left is written in the proposal, and the next step waits for the load test numbers before anything touches production. (s3)
- ✅ **(2026-01-18 11:42) Login rate limit: step 7 recorded.** The worker agent ran the change on staging and the gate confirmed it; the evidence is in `logs/login-07.log`. What is left is written in the proposal, and the next step waits for the load test numbers before anything touches production. (s1)
- 🔄 **(2026-01-18 10:49) Billing webhook signature: step 8 recorded.** The worker agent ran the change on staging and the gate confirmed it; the evidence is in `logs/billing-08.log`. What is left is written in the proposal, and the next step waits for the load test numbers before anything touches production. (s2)
- ⏸️ **(2026-01-18 09:56) Dashboard chart colors: step 9 recorded.** The worker agent ran the change on staging and the gate confirmed it; the evidence is in `logs/dashboard-09.log`. What is left is written in the proposal, and the next step waits for the load test numbers before anything touches production. (s3)
- ✅ **(2026-01-17 17:03) Log rotation policy: step 10 recorded.** The worker agent ran the change on staging and the gate confirmed it; the evidence is in `logs/log-10.log`. What is left is written in the proposal, and the next step waits for the load test numbers before anything touches production. (s1)
- 🔄 **(2026-01-17 16:10) Backup restore drill: step 11 recorded.** The worker agent ran the change on staging and the gate confirmed it; the evidence is in `logs/backup-11.log`. What is left is written in the proposal, and the next step waits for the load test numbers before anything touches production. (s2)
- ⏸️ **(2026-01-17 15:17) Feature flag cleanup: step 12 recorded.** The worker agent ran the change on staging and the gate confirmed it; the evidence is in `logs/feature-12.log`. What is left is written in the proposal, and the next step waits for the load test numbers before anything touches production. (s3)
- ✅ **(2026-01-16 14:24) Export endpoint of service-a: step 13 recorded.** The worker agent ran the change on staging and the gate confirmed it; the evidence is in `logs/export-13.log`. What is left is written in the proposal, and the next step waits for the load test numbers before anything touches production. (s1)
- 🔄 **(2026-01-16 13:31) Reports table migration: step 14 recorded.** The worker agent ran the change on staging and the gate confirmed it; the evidence is in `logs/reports-14.log`. What is left is written in the proposal, and the next step waits for the load test numbers before anything touches production. (s2)
- ⏸️ **(2026-01-16 12:38) Cache layer of the web app: step 15 recorded.** The worker agent ran the change on staging and the gate confirmed it; the evidence is in `logs/cache-15.log`. What is left is written in the proposal, and the next step waits for the load test numbers before anything touches production. (s3)
- ✅ **(2026-01-15 11:45) Nightly job schedule: step 16 recorded.** The worker agent ran the change on staging and the gate confirmed it; the evidence is in `logs/nightly-16.log`. What is left is written in the proposal, and the next step waits for the load test numbers before anything touches production. (s1)
- 🔄 **(2026-01-15 10:52) Queue consumer retries: step 17 recorded.** The worker agent ran the change on staging and the gate confirmed it; the evidence is in `logs/queue-17.log`. What is left is written in the proposal, and the next step waits for the load test numbers before anything touches production. (s2)
- ⏸️ **(2026-01-15 09:59) Search index rebuild: step 18 recorded.** The worker agent ran the change on staging and the gate confirmed it; the evidence is in `logs/search-18.log`. What is left is written in the proposal, and the next step waits for the load test numbers before anything touches production. (s3)
- ✅ **(2026-01-14 17:06) Login rate limit: step 19 recorded.** The worker agent ran the change on staging and the gate confirmed it; the evidence is in `logs/login-19.log`. What is left is written in the proposal, and the next step waits for the load test numbers before anything touches production. (s1)
- 🔄 **(2026-01-14 16:13) Billing webhook signature: step 20 recorded.** The worker agent ran the change on staging and the gate confirmed it; the evidence is in `logs/billing-20.log`. What is left is written in the proposal, and the next step waits for the load test numbers before anything touches production. (s2)
- ⏸️ **(2026-01-14 15:20) Dashboard chart colors: step 21 recorded.** The worker agent ran the change on staging and the gate confirmed it; the evidence is in `logs/dashboard-21.log`. What is left is written in the proposal, and the next step waits for the load test numbers before anything touches production. (s3)
- ✅ **(2026-01-13 14:27) Log rotation policy: step 22 recorded.** The worker agent ran the change on staging and the gate confirmed it; the evidence is in `logs/log-22.log`. What is left is written in the proposal, and the next step waits for the load test numbers before anything touches production. (s1)
- 🔄 **(2026-01-13 13:34) Backup restore drill: step 23 recorded.** The worker agent ran the change on staging and the gate confirmed it; the evidence is in `logs/backup-23.log`. What is left is written in the proposal, and the next step waits for the load test numbers before anything touches production. (s2)
- ⏸️ **(2026-01-13 12:41) Feature flag cleanup: step 24 recorded.** The worker agent ran the change on staging and the gate confirmed it; the evidence is in `logs/feature-24.log`. What is left is written in the proposal, and the next step waits for the load test numbers before anything touches production. (s3)
- ✅ **(2026-01-12 11:48) Export endpoint of service-a: step 25 recorded.** The worker agent ran the change on staging and the gate confirmed it; the evidence is in `logs/export-25.log`. What is left is written in the proposal, and the next step waits for the load test numbers before anything touches production. (s1)
- 🔄 **(2026-01-12 10:55) Reports table migration: step 26 recorded.** The worker agent ran the change on staging and the gate confirmed it; the evidence is in `logs/reports-26.log`. What is left is written in the proposal, and the next step waits for the load test numbers before anything touches production. (s2)
- ⏸️ **(2026-01-12 09:02) Cache layer of the web app: step 27 recorded.** The worker agent ran the change on staging and the gate confirmed it; the evidence is in `logs/cache-27.log`. What is left is written in the proposal, and the next step waits for the load test numbers before anything touches production. (s3)
- ✅ **(2026-01-11 17:09) Nightly job schedule: step 28 recorded.** The worker agent ran the change on staging and the gate confirmed it; the evidence is in `logs/nightly-28.log`. What is left is written in the proposal, and the next step waits for the load test numbers before anything touches production. (s1)
- 🔄 **(2026-01-11 16:16) Queue consumer retries: step 29 recorded.** The worker agent ran the change on staging and the gate confirmed it; the evidence is in `logs/queue-29.log`. What is left is written in the proposal, and the next step waits for the load test numbers before anything touches production. (s2)
- ⏸️ **(2026-01-11 15:23) Search index rebuild: step 30 recorded.** The worker agent ran the change on staging and the gate confirmed it; the evidence is in `logs/search-30.log`. What is left is written in the proposal, and the next step waits for the load test numbers before anything touches production. (s3)
- ✅ **(2026-01-10 14:30) Login rate limit: step 31 recorded.** The worker agent ran the change on staging and the gate confirmed it; the evidence is in `logs/login-31.log`. What is left is written in the proposal, and the next step waits for the load test numbers before anything touches production. (s1)
- 🔄 **(2026-01-10 13:37) Billing webhook signature: step 32 recorded.** The worker agent ran the change on staging and the gate confirmed it; the evidence is in `logs/billing-32.log`. What is left is written in the proposal, and the next step waits for the load test numbers before anything touches production. (s2)
- ⏸️ **(2026-01-10 12:44) Dashboard chart colors: step 33 recorded.** The worker agent ran the change on staging and the gate confirmed it; the evidence is in `logs/dashboard-33.log`. What is left is written in the proposal, and the next step waits for the load test numbers before anything touches production. (s3)
- ✅ **(2026-01-09 11:51) Log rotation policy: step 34 recorded.** The worker agent ran the change on staging and the gate confirmed it; the evidence is in `logs/log-34.log`. What is left is written in the proposal, and the next step waits for the load test numbers before anything touches production. (s1)

## WAITING ON THE USER (do not chase — the user knows)
- Choose between keeping the nightly job or moving it to the queue.

## STATE OF THE FRONTS (1 line each)
- service-a: export closed · migration running · cache parked.

## OPEN DOORS (trigger written, do not chase)
- If the queue grows past 1,000 items, reopen the cache proposal.
