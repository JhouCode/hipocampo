# Front `cpp` — the ruler that comes BEFORE

<!-- when-matches: \.(cpp|hpp|cc)\b|\bc\+\+|\bpointer|\bnullptr|\bsegfault|\bsegmentation|\bheader\b|\bhandler\b|\bstruct\b|\bderef|\bcrash\b -->
<!-- when-touches: \.(cpp|hpp|cc|h)\b|\bnm\s+-C\b|\bgdb\b|\bobjdump\b -->

> Example ruler (mold). The risk here is less a wrong command than a claim about the code that a
> measurement later refutes.

## PREMISES

### 1 · A pointer from the framework needs THREE checks
Null, lifetime (still owned by whom you think), and thread (touched from the thread that owns it).
**Source:** the framework's ownership rules for that object.
**What to do:** write down the three answers before dereferencing.

### 2 · Reading the code is a hypothesis about the crash
**Source:** `docs/mapa/1_CONTRATO.md` (How I measure, rule 2).
**What to do:** reproduce under a debugger or a log line before stating the cause.
