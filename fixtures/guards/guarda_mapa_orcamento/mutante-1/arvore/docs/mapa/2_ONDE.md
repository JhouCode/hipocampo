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


## Service area 01 (grown without anything leaving)

- queue `jobs-01-01`: owned by service-a, drained by the nightly worker; retries go to `jobs-01-01-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-01-02`: owned by service-a, drained by the nightly worker; retries go to `jobs-01-02-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-01-03`: owned by service-a, drained by the nightly worker; retries go to `jobs-01-03-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-01-04`: owned by service-a, drained by the nightly worker; retries go to `jobs-01-04-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-01-05`: owned by service-a, drained by the nightly worker; retries go to `jobs-01-05-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-01-06`: owned by service-a, drained by the nightly worker; retries go to `jobs-01-06-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-01-07`: owned by service-a, drained by the nightly worker; retries go to `jobs-01-07-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-01-08`: owned by service-a, drained by the nightly worker; retries go to `jobs-01-08-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-01-09`: owned by service-a, drained by the nightly worker; retries go to `jobs-01-09-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-01-10`: owned by service-a, drained by the nightly worker; retries go to `jobs-01-10-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-01-11`: owned by service-a, drained by the nightly worker; retries go to `jobs-01-11-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-01-12`: owned by service-a, drained by the nightly worker; retries go to `jobs-01-12-dead` and the on-call runbook is in docs/runbook.md

## Service area 02 (grown without anything leaving)

- queue `jobs-02-01`: owned by service-a, drained by the nightly worker; retries go to `jobs-02-01-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-02-02`: owned by service-a, drained by the nightly worker; retries go to `jobs-02-02-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-02-03`: owned by service-a, drained by the nightly worker; retries go to `jobs-02-03-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-02-04`: owned by service-a, drained by the nightly worker; retries go to `jobs-02-04-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-02-05`: owned by service-a, drained by the nightly worker; retries go to `jobs-02-05-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-02-06`: owned by service-a, drained by the nightly worker; retries go to `jobs-02-06-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-02-07`: owned by service-a, drained by the nightly worker; retries go to `jobs-02-07-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-02-08`: owned by service-a, drained by the nightly worker; retries go to `jobs-02-08-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-02-09`: owned by service-a, drained by the nightly worker; retries go to `jobs-02-09-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-02-10`: owned by service-a, drained by the nightly worker; retries go to `jobs-02-10-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-02-11`: owned by service-a, drained by the nightly worker; retries go to `jobs-02-11-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-02-12`: owned by service-a, drained by the nightly worker; retries go to `jobs-02-12-dead` and the on-call runbook is in docs/runbook.md

## Service area 03 (grown without anything leaving)

- queue `jobs-03-01`: owned by service-a, drained by the nightly worker; retries go to `jobs-03-01-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-03-02`: owned by service-a, drained by the nightly worker; retries go to `jobs-03-02-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-03-03`: owned by service-a, drained by the nightly worker; retries go to `jobs-03-03-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-03-04`: owned by service-a, drained by the nightly worker; retries go to `jobs-03-04-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-03-05`: owned by service-a, drained by the nightly worker; retries go to `jobs-03-05-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-03-06`: owned by service-a, drained by the nightly worker; retries go to `jobs-03-06-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-03-07`: owned by service-a, drained by the nightly worker; retries go to `jobs-03-07-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-03-08`: owned by service-a, drained by the nightly worker; retries go to `jobs-03-08-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-03-09`: owned by service-a, drained by the nightly worker; retries go to `jobs-03-09-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-03-10`: owned by service-a, drained by the nightly worker; retries go to `jobs-03-10-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-03-11`: owned by service-a, drained by the nightly worker; retries go to `jobs-03-11-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-03-12`: owned by service-a, drained by the nightly worker; retries go to `jobs-03-12-dead` and the on-call runbook is in docs/runbook.md

## Service area 04 (grown without anything leaving)

- queue `jobs-04-01`: owned by service-a, drained by the nightly worker; retries go to `jobs-04-01-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-04-02`: owned by service-a, drained by the nightly worker; retries go to `jobs-04-02-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-04-03`: owned by service-a, drained by the nightly worker; retries go to `jobs-04-03-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-04-04`: owned by service-a, drained by the nightly worker; retries go to `jobs-04-04-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-04-05`: owned by service-a, drained by the nightly worker; retries go to `jobs-04-05-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-04-06`: owned by service-a, drained by the nightly worker; retries go to `jobs-04-06-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-04-07`: owned by service-a, drained by the nightly worker; retries go to `jobs-04-07-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-04-08`: owned by service-a, drained by the nightly worker; retries go to `jobs-04-08-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-04-09`: owned by service-a, drained by the nightly worker; retries go to `jobs-04-09-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-04-10`: owned by service-a, drained by the nightly worker; retries go to `jobs-04-10-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-04-11`: owned by service-a, drained by the nightly worker; retries go to `jobs-04-11-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-04-12`: owned by service-a, drained by the nightly worker; retries go to `jobs-04-12-dead` and the on-call runbook is in docs/runbook.md

## Service area 05 (grown without anything leaving)

- queue `jobs-05-01`: owned by service-a, drained by the nightly worker; retries go to `jobs-05-01-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-05-02`: owned by service-a, drained by the nightly worker; retries go to `jobs-05-02-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-05-03`: owned by service-a, drained by the nightly worker; retries go to `jobs-05-03-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-05-04`: owned by service-a, drained by the nightly worker; retries go to `jobs-05-04-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-05-05`: owned by service-a, drained by the nightly worker; retries go to `jobs-05-05-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-05-06`: owned by service-a, drained by the nightly worker; retries go to `jobs-05-06-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-05-07`: owned by service-a, drained by the nightly worker; retries go to `jobs-05-07-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-05-08`: owned by service-a, drained by the nightly worker; retries go to `jobs-05-08-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-05-09`: owned by service-a, drained by the nightly worker; retries go to `jobs-05-09-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-05-10`: owned by service-a, drained by the nightly worker; retries go to `jobs-05-10-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-05-11`: owned by service-a, drained by the nightly worker; retries go to `jobs-05-11-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-05-12`: owned by service-a, drained by the nightly worker; retries go to `jobs-05-12-dead` and the on-call runbook is in docs/runbook.md

## Service area 06 (grown without anything leaving)

- queue `jobs-06-01`: owned by service-a, drained by the nightly worker; retries go to `jobs-06-01-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-06-02`: owned by service-a, drained by the nightly worker; retries go to `jobs-06-02-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-06-03`: owned by service-a, drained by the nightly worker; retries go to `jobs-06-03-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-06-04`: owned by service-a, drained by the nightly worker; retries go to `jobs-06-04-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-06-05`: owned by service-a, drained by the nightly worker; retries go to `jobs-06-05-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-06-06`: owned by service-a, drained by the nightly worker; retries go to `jobs-06-06-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-06-07`: owned by service-a, drained by the nightly worker; retries go to `jobs-06-07-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-06-08`: owned by service-a, drained by the nightly worker; retries go to `jobs-06-08-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-06-09`: owned by service-a, drained by the nightly worker; retries go to `jobs-06-09-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-06-10`: owned by service-a, drained by the nightly worker; retries go to `jobs-06-10-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-06-11`: owned by service-a, drained by the nightly worker; retries go to `jobs-06-11-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-06-12`: owned by service-a, drained by the nightly worker; retries go to `jobs-06-12-dead` and the on-call runbook is in docs/runbook.md

## Service area 07 (grown without anything leaving)

- queue `jobs-07-01`: owned by service-a, drained by the nightly worker; retries go to `jobs-07-01-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-07-02`: owned by service-a, drained by the nightly worker; retries go to `jobs-07-02-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-07-03`: owned by service-a, drained by the nightly worker; retries go to `jobs-07-03-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-07-04`: owned by service-a, drained by the nightly worker; retries go to `jobs-07-04-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-07-05`: owned by service-a, drained by the nightly worker; retries go to `jobs-07-05-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-07-06`: owned by service-a, drained by the nightly worker; retries go to `jobs-07-06-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-07-07`: owned by service-a, drained by the nightly worker; retries go to `jobs-07-07-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-07-08`: owned by service-a, drained by the nightly worker; retries go to `jobs-07-08-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-07-09`: owned by service-a, drained by the nightly worker; retries go to `jobs-07-09-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-07-10`: owned by service-a, drained by the nightly worker; retries go to `jobs-07-10-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-07-11`: owned by service-a, drained by the nightly worker; retries go to `jobs-07-11-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-07-12`: owned by service-a, drained by the nightly worker; retries go to `jobs-07-12-dead` and the on-call runbook is in docs/runbook.md

## Service area 08 (grown without anything leaving)

- queue `jobs-08-01`: owned by service-a, drained by the nightly worker; retries go to `jobs-08-01-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-08-02`: owned by service-a, drained by the nightly worker; retries go to `jobs-08-02-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-08-03`: owned by service-a, drained by the nightly worker; retries go to `jobs-08-03-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-08-04`: owned by service-a, drained by the nightly worker; retries go to `jobs-08-04-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-08-05`: owned by service-a, drained by the nightly worker; retries go to `jobs-08-05-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-08-06`: owned by service-a, drained by the nightly worker; retries go to `jobs-08-06-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-08-07`: owned by service-a, drained by the nightly worker; retries go to `jobs-08-07-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-08-08`: owned by service-a, drained by the nightly worker; retries go to `jobs-08-08-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-08-09`: owned by service-a, drained by the nightly worker; retries go to `jobs-08-09-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-08-10`: owned by service-a, drained by the nightly worker; retries go to `jobs-08-10-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-08-11`: owned by service-a, drained by the nightly worker; retries go to `jobs-08-11-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-08-12`: owned by service-a, drained by the nightly worker; retries go to `jobs-08-12-dead` and the on-call runbook is in docs/runbook.md

## Service area 09 (grown without anything leaving)

- queue `jobs-09-01`: owned by service-a, drained by the nightly worker; retries go to `jobs-09-01-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-09-02`: owned by service-a, drained by the nightly worker; retries go to `jobs-09-02-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-09-03`: owned by service-a, drained by the nightly worker; retries go to `jobs-09-03-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-09-04`: owned by service-a, drained by the nightly worker; retries go to `jobs-09-04-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-09-05`: owned by service-a, drained by the nightly worker; retries go to `jobs-09-05-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-09-06`: owned by service-a, drained by the nightly worker; retries go to `jobs-09-06-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-09-07`: owned by service-a, drained by the nightly worker; retries go to `jobs-09-07-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-09-08`: owned by service-a, drained by the nightly worker; retries go to `jobs-09-08-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-09-09`: owned by service-a, drained by the nightly worker; retries go to `jobs-09-09-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-09-10`: owned by service-a, drained by the nightly worker; retries go to `jobs-09-10-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-09-11`: owned by service-a, drained by the nightly worker; retries go to `jobs-09-11-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-09-12`: owned by service-a, drained by the nightly worker; retries go to `jobs-09-12-dead` and the on-call runbook is in docs/runbook.md

## Service area 10 (grown without anything leaving)

- queue `jobs-10-01`: owned by service-a, drained by the nightly worker; retries go to `jobs-10-01-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-10-02`: owned by service-a, drained by the nightly worker; retries go to `jobs-10-02-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-10-03`: owned by service-a, drained by the nightly worker; retries go to `jobs-10-03-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-10-04`: owned by service-a, drained by the nightly worker; retries go to `jobs-10-04-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-10-05`: owned by service-a, drained by the nightly worker; retries go to `jobs-10-05-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-10-06`: owned by service-a, drained by the nightly worker; retries go to `jobs-10-06-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-10-07`: owned by service-a, drained by the nightly worker; retries go to `jobs-10-07-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-10-08`: owned by service-a, drained by the nightly worker; retries go to `jobs-10-08-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-10-09`: owned by service-a, drained by the nightly worker; retries go to `jobs-10-09-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-10-10`: owned by service-a, drained by the nightly worker; retries go to `jobs-10-10-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-10-11`: owned by service-a, drained by the nightly worker; retries go to `jobs-10-11-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-10-12`: owned by service-a, drained by the nightly worker; retries go to `jobs-10-12-dead` and the on-call runbook is in docs/runbook.md

## Service area 11 (grown without anything leaving)

- queue `jobs-11-01`: owned by service-a, drained by the nightly worker; retries go to `jobs-11-01-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-11-02`: owned by service-a, drained by the nightly worker; retries go to `jobs-11-02-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-11-03`: owned by service-a, drained by the nightly worker; retries go to `jobs-11-03-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-11-04`: owned by service-a, drained by the nightly worker; retries go to `jobs-11-04-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-11-05`: owned by service-a, drained by the nightly worker; retries go to `jobs-11-05-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-11-06`: owned by service-a, drained by the nightly worker; retries go to `jobs-11-06-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-11-07`: owned by service-a, drained by the nightly worker; retries go to `jobs-11-07-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-11-08`: owned by service-a, drained by the nightly worker; retries go to `jobs-11-08-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-11-09`: owned by service-a, drained by the nightly worker; retries go to `jobs-11-09-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-11-10`: owned by service-a, drained by the nightly worker; retries go to `jobs-11-10-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-11-11`: owned by service-a, drained by the nightly worker; retries go to `jobs-11-11-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-11-12`: owned by service-a, drained by the nightly worker; retries go to `jobs-11-12-dead` and the on-call runbook is in docs/runbook.md

## Service area 12 (grown without anything leaving)

- queue `jobs-12-01`: owned by service-a, drained by the nightly worker; retries go to `jobs-12-01-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-12-02`: owned by service-a, drained by the nightly worker; retries go to `jobs-12-02-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-12-03`: owned by service-a, drained by the nightly worker; retries go to `jobs-12-03-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-12-04`: owned by service-a, drained by the nightly worker; retries go to `jobs-12-04-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-12-05`: owned by service-a, drained by the nightly worker; retries go to `jobs-12-05-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-12-06`: owned by service-a, drained by the nightly worker; retries go to `jobs-12-06-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-12-07`: owned by service-a, drained by the nightly worker; retries go to `jobs-12-07-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-12-08`: owned by service-a, drained by the nightly worker; retries go to `jobs-12-08-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-12-09`: owned by service-a, drained by the nightly worker; retries go to `jobs-12-09-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-12-10`: owned by service-a, drained by the nightly worker; retries go to `jobs-12-10-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-12-11`: owned by service-a, drained by the nightly worker; retries go to `jobs-12-11-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-12-12`: owned by service-a, drained by the nightly worker; retries go to `jobs-12-12-dead` and the on-call runbook is in docs/runbook.md

## Service area 13 (grown without anything leaving)

- queue `jobs-13-01`: owned by service-a, drained by the nightly worker; retries go to `jobs-13-01-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-13-02`: owned by service-a, drained by the nightly worker; retries go to `jobs-13-02-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-13-03`: owned by service-a, drained by the nightly worker; retries go to `jobs-13-03-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-13-04`: owned by service-a, drained by the nightly worker; retries go to `jobs-13-04-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-13-05`: owned by service-a, drained by the nightly worker; retries go to `jobs-13-05-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-13-06`: owned by service-a, drained by the nightly worker; retries go to `jobs-13-06-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-13-07`: owned by service-a, drained by the nightly worker; retries go to `jobs-13-07-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-13-08`: owned by service-a, drained by the nightly worker; retries go to `jobs-13-08-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-13-09`: owned by service-a, drained by the nightly worker; retries go to `jobs-13-09-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-13-10`: owned by service-a, drained by the nightly worker; retries go to `jobs-13-10-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-13-11`: owned by service-a, drained by the nightly worker; retries go to `jobs-13-11-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-13-12`: owned by service-a, drained by the nightly worker; retries go to `jobs-13-12-dead` and the on-call runbook is in docs/runbook.md

## Service area 14 (grown without anything leaving)

- queue `jobs-14-01`: owned by service-a, drained by the nightly worker; retries go to `jobs-14-01-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-14-02`: owned by service-a, drained by the nightly worker; retries go to `jobs-14-02-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-14-03`: owned by service-a, drained by the nightly worker; retries go to `jobs-14-03-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-14-04`: owned by service-a, drained by the nightly worker; retries go to `jobs-14-04-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-14-05`: owned by service-a, drained by the nightly worker; retries go to `jobs-14-05-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-14-06`: owned by service-a, drained by the nightly worker; retries go to `jobs-14-06-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-14-07`: owned by service-a, drained by the nightly worker; retries go to `jobs-14-07-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-14-08`: owned by service-a, drained by the nightly worker; retries go to `jobs-14-08-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-14-09`: owned by service-a, drained by the nightly worker; retries go to `jobs-14-09-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-14-10`: owned by service-a, drained by the nightly worker; retries go to `jobs-14-10-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-14-11`: owned by service-a, drained by the nightly worker; retries go to `jobs-14-11-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-14-12`: owned by service-a, drained by the nightly worker; retries go to `jobs-14-12-dead` and the on-call runbook is in docs/runbook.md

## Service area 15 (grown without anything leaving)

- queue `jobs-15-01`: owned by service-a, drained by the nightly worker; retries go to `jobs-15-01-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-15-02`: owned by service-a, drained by the nightly worker; retries go to `jobs-15-02-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-15-03`: owned by service-a, drained by the nightly worker; retries go to `jobs-15-03-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-15-04`: owned by service-a, drained by the nightly worker; retries go to `jobs-15-04-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-15-05`: owned by service-a, drained by the nightly worker; retries go to `jobs-15-05-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-15-06`: owned by service-a, drained by the nightly worker; retries go to `jobs-15-06-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-15-07`: owned by service-a, drained by the nightly worker; retries go to `jobs-15-07-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-15-08`: owned by service-a, drained by the nightly worker; retries go to `jobs-15-08-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-15-09`: owned by service-a, drained by the nightly worker; retries go to `jobs-15-09-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-15-10`: owned by service-a, drained by the nightly worker; retries go to `jobs-15-10-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-15-11`: owned by service-a, drained by the nightly worker; retries go to `jobs-15-11-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-15-12`: owned by service-a, drained by the nightly worker; retries go to `jobs-15-12-dead` and the on-call runbook is in docs/runbook.md

## Service area 16 (grown without anything leaving)

- queue `jobs-16-01`: owned by service-a, drained by the nightly worker; retries go to `jobs-16-01-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-16-02`: owned by service-a, drained by the nightly worker; retries go to `jobs-16-02-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-16-03`: owned by service-a, drained by the nightly worker; retries go to `jobs-16-03-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-16-04`: owned by service-a, drained by the nightly worker; retries go to `jobs-16-04-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-16-05`: owned by service-a, drained by the nightly worker; retries go to `jobs-16-05-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-16-06`: owned by service-a, drained by the nightly worker; retries go to `jobs-16-06-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-16-07`: owned by service-a, drained by the nightly worker; retries go to `jobs-16-07-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-16-08`: owned by service-a, drained by the nightly worker; retries go to `jobs-16-08-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-16-09`: owned by service-a, drained by the nightly worker; retries go to `jobs-16-09-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-16-10`: owned by service-a, drained by the nightly worker; retries go to `jobs-16-10-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-16-11`: owned by service-a, drained by the nightly worker; retries go to `jobs-16-11-dead` and the on-call runbook is in docs/runbook.md
- queue `jobs-16-12`: owned by service-a, drained by the nightly worker; retries go to `jobs-16-12-dead` and the on-call runbook is in docs/runbook.md
