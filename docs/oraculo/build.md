# Front `build` — the ruler that comes BEFORE

<!-- when-matches: \b(build|builds|compil\w+|recompil\w+|cmake|ninja|make install|\-j\d+|promot\w+|binar\w+)\b -->
<!-- when-touches: \bcmake\b|\bmake\b|\bninja\b|CMakeCache|\s\-j\d+|Built target -->

> Example ruler (mold). A front touched rarely has the highest error rate: there is no repetition
> to fix the procedure, and every error costs a whole build.

## PREMISES

### 1 · Build on the build host, never on production
**Source:** `docs/mapa/1_CONTRATO.md` (What I do NOT do without the owner) + `docs/mapa/2_ONDE.md`.
**What to do:** check the host name as the first command of any build.

### 2 · A green build over an OLD binary proves nothing
The install step can silently skip a target and leave the previous binary in place.
**Source:** the build system's own output (`Built target` lines).
**What to do:** compare the checksum of the installed binary with the one just built.
