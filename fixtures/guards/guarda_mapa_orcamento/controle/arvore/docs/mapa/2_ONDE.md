# 2 · WHERE WE ARE

> **Layer 2 of the map** ([`0_MAPA.md`](0_MAPA.md)). Coordinates of the machines. Loaded whole.
> This is a **table of facts**, not a narrative — it changes when the hardware changes, not when the
> work changes. In a conflict of FACT, the detailed operations doc wins; in a conflict of LAW, layer 1 wins.
>
> *Mold content: two invented hosts. Keep real addresses out of anything you publish.*

---

## The machines

| alias | role | how I get there |
|---|---|---|
| **`build-host`** | **build and test twin** — builds, runs the test suite, rehearses migrations. Disposable by decision | `ssh build-host` |
| **`app-host`** | **production** — web app, worker queue, database. Real users | `ssh app-host` — **only when the owner asks** (layer 1) |
| *(local)* | **the operations machine** — the agent runs here; crons and backups | *it is the local machine* |

## Where things live

| what | `app-host` | `build-host` |
|---|---|---|
| application | `/srv/webapp` | `~/webapp` |
| worker queue | `webapp-worker.service` | same unit, test config |
| database | local PostgreSQL | a disposable copy, refreshed nightly |
| secrets | `/srv/webapp/.env` | a test stub |

> **Paths are discovered, not hard-coded, in scripts.** A hard-coded path that does not exist on a
> host makes a `cd … 2>/dev/null &&` skip its block silently.
