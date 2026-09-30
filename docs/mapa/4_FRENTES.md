# 4 · WHAT WE ARE DOING

> **Layer 4 of the map** ([`0_MAPA.md`](0_MAPA.md)). Current work. **This layer is NOT loaded** —
> what the others carry is a pointer to *this page*: the index and the **trigger** of each front.
> The content enters when the subject asks for it.
>
> **No state is written on this page.** A status typed by hand into a table rots without anyone
> noticing; numbers come from a generated block or from `git log`. This page keeps what does not
> rot: the entry door and *when to open*.
>
> *Mold content: an invented small web app with a worker queue.*

---

## Live fronts

| front | entry door | **when to open** |
|---|---|---|
| **Web app** | `docs/webapp/README.md` | any change to routes, templates, sessions |
| **Worker queue** | `docs/queue/README.md` | retries, dead letters, a job that "never finishes" |
| **Database** | `docs/db/README.md` | a migration, a slow query, a backup restore |
| **CI guards** | `docs/guardas/memoria.md` | when writing, editing or doubting a guard |
| **Oracle — the area ruler** | [`docs/oraculo/README.md`](../oraculo/README.md) | when opening any build, cpp, db or scripts work |
| **The map itself** | [`0_MAPA.md`](0_MAPA.md) | when writing or moving any doc |

## How a front changes phase

Docs of a live project live in `docs/<project>/{proposta,andamento,concluido}/`. Finishing a phase
**moves the doc** (`andamento/` → `concluido/`) and adjusts the row above. A stamp saying "done" on
a doc that stayed in `andamento/` is the lie this rule prevents.
