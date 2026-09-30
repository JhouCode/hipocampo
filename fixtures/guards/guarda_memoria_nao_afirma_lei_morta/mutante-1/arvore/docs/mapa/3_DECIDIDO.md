# 3 · WHAT WAS ALREADY DECIDED

> **Layer 3** ([`0_MAPA.md`](0_MAPA.md)): **product** law, decided and out of discussion — one row
> per decision, and it can be revoked. Layer 1 ([`1_CONTRATO.md`](1_CONTRATO.md)) is the other kind:
> *method*, valid in any project.
>
> **Every row is born `IN FORCE`; when it falls it becomes `REVOKED` — never deleted, and the REASON
> stays.** A postponed row is `POSTPONED` and carries a `**TRIGGER:**` row right below it.
> The dead row is the asset: it is what stops re-proposing what was already rejected.
>
> How to write a row (format, states, glyphs): [`5_COMO_MANTER §1.2`](5_COMO_MANTER.md).
> *Mold content: an invented small web app with a worker queue.*

---

## The web app

| # | state | decision | who, when | proof |
|---|---|---|---|---|
| P1 | ✅ IN FORCE ⚙ | **A job is retried at most three times, then it goes to the dead-letter queue.** Retrying forever hides a poison message behind a busy worker | owner, 2026-01-12 | guard `queue_retry_cap` |
| P2 | ✅ IN FORCE ⚙ | **Every schema change ships with its down migration.** A migration that cannot be undone is a one-way door | owner, 2026-01-15 | guard `migration_has_down` |
| P3 | ✅ IN FORCE 🔔 | **User-facing text is bilingual.** Internal logs and reasoning stay in one language | owner, 2026-01-20 | backlog item that fires when a template is touched |
| P4 | ✅ IN FORCE 🕳 | **The worker never sends e-mail directly; it enqueues it.** One sender, one rate limit | owner, 2026-02-02 | no mechanism yet |
| P5 | ✅ IN FORCE 🕳 | **Public changelogs carry no infrastructure numbers.** Versions and features only | owner, 2026-02-05 | no mechanism yet |
| P6 | ✅ IN FORCE 🕳 | **Uploads above 10 MB are rejected at the edge, not in the app.** The app never buffers what it will refuse | owner, 2026-02-09 | no mechanism yet |
| P7 | 🔻 REVOKED | ~~**Jobs run in strict FIFO order.**~~ Reason: a single slow tenant blocked every other tenant for hours; replaced by per-tenant fair queues (P1 still caps retries) | owner, 2026-01-12 · revoked 2026-02-20 | incident note in the operations doc |
| P8 | 🕓 POSTPONED | **Move the worker queue to a managed service.** Not now: the self-hosted queue costs less than one hour a month to run | owner, 2026-02-22 | cost note |
| | | **TRIGGER:** when queue upkeep passes four hours in a month, or the app gets a second region. | | |
