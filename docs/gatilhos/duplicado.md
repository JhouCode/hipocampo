# Source `duplicado` -- does this already exist under another name?

> The third front of the dispatcher, also **without a new line in `scripts/gatilho.py`**.
>
> The cheapest question of all, and the one most often skipped: *"before writing this, is there
> already a piece that does the same?"*. The cost of getting it wrong is not extra code -- it is
> **two truths diverging on their own**.
>
> **Every item here is a `RULE`** -- always warns, never blocks, and the counter is a metric.
>
> **THE LIMIT OF THIS SOURCE:** every item matches on the **target of the touch** (the path or the
> command), never on the **content written**. It cannot catch a rule rewritten in prose inside a
> memory or a map layer. That gap is served by `scripts/guarda-ja-existe.py`, which compares
> **content** against the rule surfaces. The two live together and ask different questions.

| id | when it matches | what to say | NEXT STEP | step | rides |
|---|---|---|---|---|---|
| DUP-01 | `scripts/.*(notify\|alert).*\.(sh\|py)$` | There is already one notifier, `scripts/notify.sh`, with retry and rate limit -- a second one would drift from it | Call `scripts/notify.sh` from the new script instead of writing another sender; extend it if a channel is missing | RULE | 0 |
| DUP-02 | `(projects/.*/memory/.*\.md\|docs/(mapa\|oraculo)/.*\.md)` | Writing a rule: the question "does this already exist?" now runs by itself on the path -- `guarda-ja-existe.py` compares the new text against the memory index and map layers 1 and 3 | Read the blocks it cites BEFORE closing the write; what already exists is cited, not rewritten -- save only the delta | RULE | 0 |

## Population -- DERIVED (`gatilho.py --selftest`)

Every item here came from a duplication ALREADY KNOWN -- none from a sweep. That is the honest
limit of this source: the parser counts the items, but no instrument says *"nobody swept for new
duplicates"*.
