# Source `estacionado` -- a project out of load, and the warning that it exists

> A block of the memory index that the owner asked to "put aside" leaves the load (active
> forgetting) through `scripts/memoria-estaciona.py` and lives in
> `memory/indice_<slug>_estacionado.md`. This source is the cherry-pick: on the first touch of a
> path of the parked project, it warns that its index is not loaded and how to resume it. **When
> the owner says "I am going to work on X", the order is one command:**
> `python3 scripts/memoria-estaciona.py --retoma X`.
>
> **Every item here is a `RULE`**, not a debt. It warns once per session and never blocks. An item
> enters when a block is parked and leaves when it is resumed -- the row and the file move together.
> `memoria-estaciona.py` does NOT write this file (a `when it matches` is a domain regex and cannot
> be invented by a script); it reminds you at the end of each park/resume to add or remove the row.
> A source that promises to be paired and has nobody pairing it lies in the most expensive
> direction: it claims the project is put aside.

| id | when it matches | what to say | NEXT STEP | step | rides |
|---|---|---|---|---|---|
| PARK-01 | `(service-b/\|legacy-importer)` | Project **service-b** is PARKED: its index block (state of the work, open decisions) is NOT loaded, so decisions about it are being made without it | Open `memory/indice_service-b_estacionado.md` before deciding anything here; if the owner is resuming the work, run `python3 scripts/memoria-estaciona.py --retoma service-b` and delete this row | RULE | 0 |
