# Front `scripts` — the ruler that comes BEFORE

<!-- when-matches: \bscript\b|\bguard\w*|\bguards?\b|selftest|self-test|\bhook\w*\b|\bbash\b|\bshell\b|\bpython3?\b|\.sh\b|\.py\b|\bcron\b|\bbattery\b|\bautomat\w+|\bdry-?run\b -->
<!-- when-touches: \.(sh|py)\b|\bbash\s|\bpython3?\s|--selftest|\bguards/|\bcrontab\b -->

> Example ruler (mold). The risk in this front is rarely the command itself: it is **the green guard
> that proves nothing**.

## PREMISES

### 1 · A guard must FAIL on purpose before it counts
Inject the defect and watch the guard light up; "proven failing" only counts if it ran. A guard that
DIES (exception) is not a guard that fails — a crash looks like a test failure, not a verdict.
**Source:** `docs/mapa/1_CONTRATO.md` (How I measure, rule 3).
**What to do:** keep one positive and one negative case per guard in its selftest.

### 2 · A selftest has TWO halves, and the second matters more
Cases that **must light** prove it sees; cases that **must pass** prove it is not too wide — a
blocking hook that stops legitimate work is switched off by the third time. Report `N of M`.
**Source:** `docs/mapa/1_CONTRATO.md` (the 3 controls).

### 3 · A fixture hides the plumbing
Measured in the reference deployment: 7 of 7 synthetic cases green, and the 1st real transcript
broke on SIGPIPE under `pipefail` (a `tac | grep -m1` on a big file). Fixtures rarely reproduce a
repeated source, a half-written file, or two processes racing.
**What to do:** add one case with REAL volume; call a number measured only on fixtures PROVISIONAL.

### 4 · What already answers on failure takes no fallback
`grep -c` prints `0` AND exits 1, so `grep -c … || echo 0` prints `0` twice.
**Source:** the command's own manual page.
**What to do:** before appending `|| <fallback>`, check what the command already writes on its error
branch.
