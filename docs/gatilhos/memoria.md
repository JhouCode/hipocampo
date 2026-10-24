# Source `memoria` -- the cold memory that only serves on one specific path

> The fifth front of the dispatcher, **written without touching a line of `scripts/gatilho.py`**.
> The whole -- pieces, regimes and the role of each -- is in [`../HIPOCAMPO.md`](../HIPOCAMPO.md).
>
> The question of this source: **"is there a memory that answers exactly the file being opened
> now?"** (the cue finds the trace).
>
> **THE PROBLEM IT SOLVES.** There is no automatic recall of memory files: if the agent does not
> open a file, it never enters the context, and the only channel that makes it happen is the index
> line, read at the right moment. `scripts/memoria-recall.py` measures it: which memories were ever
> opened, and which never were. Many of the never-opened ones are not junk -- they are correct,
> specific operational knowledge that only serves when one path is touched, and nobody called them
> at that moment. This source is that call.
>
> **Every item here is a `RULE`** -- there is nothing to "pay". It always warns, never blocks, and
> `rides` measures whether the memory is really on the path. **A high ride count here is a sign of
> promotion**: a cold memory that lights every week deserves its index line back.
>
> **MEASURED** (one store, 2026-08-14 to 2026-10-13): the source fired **501** times across 211
> sessions (once per memory per session; 37 memories had a trigger). The full memory was opened in
> the same session in **at most 12 of 495** firings (2.4%, a ceiling) -- the line was enough, which is
> the design working. The injected line has a median of **172** characters; the memory body, 2,275.
> Over the 501 firings the lines came to 79 thousand characters; the bodies would have been 1.68
> million. Three patterns accounted for half the firings: the promotion signal. And the count proves
> the hook **emitted**, not that the model read it.
>
> **What does NOT go here:** a method memory (it holds on any path -- that belongs to the map) and a
> memory whose trigger is an EVENT, not a file. An item without a real `when it matches` would be
> documentation dressed as a trigger, and the parser would accept it silently.

| id | when it matches | what to say | NEXT STEP | step | rides |
|---|---|---|---|---|---|
| MEM-01 | `(^\|/)nginx/[^/]+\.conf$` | A `reload` keeps the old workers alive until their connections close -- a config test that passes is not the new config serving yet | Open `memory/reference_nginx_reload_drains.md` before editing, and check the served header after the reload, not only `nginx -t` | RULE | 0 |
| MEM-02 | `\bcrontab\b` | The cron environment has no login PATH -- a job that works in the shell fails silently at night | Open `memory/feedback_cron_has_no_path.md` and write absolute paths in the new line | RULE | 0 |

## Population -- DERIVED (`gatilho.py --selftest`)
How many items there are, and how many are covered, the parser counts.
