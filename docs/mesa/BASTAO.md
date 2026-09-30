# 🏃 THE BATON — live state of the working session · what it is and its rules live in [`BASTAO_REGRAS.md`](BASTAO_REGRAS.md)
*Updated: 2026-01-15 18:05 UTC — the time comes from `date`, never estimated (s2)*
- ✅ **(2026-01-15 18:05) The export endpoint of service-a is closed — commit `a1b2c3d`.** Worker gate: 6 of 6 checks confirmed, 0 blocking. The retry cap stayed at 3 (the user's call, verbatim: *"three is enough"*). Next: nothing on this front. (s2)
- 🔄 **(2026-01-15 16:40) Migration of the reports table in flight** — a worker agent runs it on the staging database; ETA ~20 min; the result lands in `logs/migration-0115.log`. Check the log first when resuming, not the worker. (s2)
- ⏸️ **(2026-01-14 11:10) The cache layer of the web app is parked** until the load test numbers exist; the proposal is in `docs/proposals/cache.md`. (s1)

## WAITING ON THE USER (do not chase — the user knows)
- Choose between keeping the nightly job or moving it to the queue (options written in the proposal).

## STATE OF THE FRONTS (1 line each)
- service-a: export closed · migration running · cache parked.

## OPEN DOORS (trigger written, do not chase)
- If the queue grows past 1,000 items, reopen the cache proposal.
