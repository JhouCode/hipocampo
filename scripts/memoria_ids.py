#!/usr/bin/env python3
"""THE ID ARITHMETIC -- one module, because a second copy of the arithmetic is a second truth.

WHAT THIS MODULE IS
  Reading the frontmatter of the memories and deriving the `number -> path` table.
  It decides NOTHING: `memoria-id-assign.py` assigns, `memoria-resolve.py` resolves,
  the guard runner refuses. All three read from here.

THE LAW OF THE NUMBER (design: docs/MEMORIA.md)
  1. The number is BORN in the file (`id: N` in the frontmatter). The table is a regenerable CACHE.
     If the table and the whole mechanism burn, `grep -l 'id: 7' memory/*.md` resolves.
  2. An id is NEVER reused and NEVER renumbered once cited. `max+1`, always --
     the hole left by a deleted memory STAYS a hole, on purpose.
  3. The file name does NOT change. The number is an ALIAS on top, not a replacement.
  4. A duplicate id is RED, never a silent fix: two files with the same number mean someone
     renumbered or copied, and guessing which one wins is silently picking the wrong copy.
"""
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hipo_config as HC  # noqa: E402

MEMDIR = Path(os.environ.get("MEM_DIR", HC.MEMORY_DIR))
TABELA = Path(os.environ.get("MEM_TABELA", os.path.join(HC.REPO, "docs/INDICE_NUMERICO.md")))

# `id:` at the ROOT level of the frontmatter. The `^` anchor with MULTILINE is not enough:
# `metadata:` has indented children, and an `  id: 3` in there would be another field. Column zero.
_ID = re.compile(r"^id:[ \t]*(\d+)[ \t]*$", re.M)
_NAME = re.compile(r"^name:[ \t]*(\S+)[ \t]*$", re.M)
# the citation in the index: `[7]`. It does not match `[[link]]` (two brackets) nor `[a]`.
CITACAO = re.compile(r"(?<!\[)\[(\d+)\](?!\])")


def frontmatter(texto):
    """The block between the first pair of `---`. Returns '' if the file has none.

    Slicing the WHOLE file looking for `id:` would match an `id: 5` written in prose in the
    body. The frontmatter has a start and an end; the search respects both."""
    if not texto.startswith("---\n"):
        return ""
    fim = texto.find("\n---", 3)
    return texto[4:fim] if fim > 0 else ""


def memorias(memdir=None):
    """Every memory file of the store. The INDEX is not a memory and stays out."""
    d = Path(memdir) if memdir else MEMDIR
    return sorted(p for p in d.glob("*.md") if p.name != "MEMORY.md")


def varre(memdir=None):
    """(ids, sem_id, duplicados) read from disk -- the SOURCE, never the table.

    ids       : {N: Path}          -- the ones that have a number
    sem_id    : [Path]             -- store pending assignment (repairable)
    duplicados: {N: [Path, Path...]} -- RED: two owners for the same number
    """
    ids, sem_id, todos = {}, [], {}
    for p in memorias(memdir):
        m = _ID.search(frontmatter(p.read_text(encoding="utf-8", errors="replace")))
        if not m:
            sem_id.append(p)
            continue
        n = int(m.group(1))
        todos.setdefault(n, []).append(p)
    for n, ps in todos.items():
        ids[n] = ps[0]
    dup = {n: ps for n, ps in todos.items() if len(ps) > 1}
    return ids, sem_id, dup


def proximo(ids):
    """`max+1`. Never fills a hole -- reusing an id is the only irreversible defect."""
    return (max(ids) + 1) if ids else 1


def glosas_do_indice(memdir=None):
    """{N: gloss} -- the gloss the INDEX shows, not the body's `description`.

    The choice of source was decided by a guard, not by taste. A first version of this table
    copied the whole `description`, and the guard that keeps first-person error narratives out
    of `docs/` refused it: a memory's `description` may legitimately carry a post-mortem in the
    first person, which in the BODY is the content and inside `docs/` is forbidden prose.
    Truncating would not fix it: sometimes the post-mortem is the first clause.
      The index gloss does not have that problem by construction: it already passes the index
    line-length cap and answers "why would I open this?", which is a directive, not a
    post-mortem. And it is the SAME gloss that works at load time -- the table stops having text
    of its own that ages by itself."""
    d = Path(memdir) if memdir else MEMDIR
    idx = d / "MEMORY.md"
    if not idx.is_file():
        return {}
    fora = {}
    for linha in idx.read_text(encoding="utf-8").split("\n"):
        marcas = list(CITACAO.finditer(linha))
        for i, m in enumerate(marcas):
            fim = marcas[i + 1].start() if i + 1 < len(marcas) else len(linha)
            fora[int(m.group(1))] = linha[m.end():fim].strip(" -·\t")
    return fora


def render_tabela(memdir=None):
    """The derived table, as TEXT. Deterministic: same input, same bytes.

    It is a CACHE. It lives OUTSIDE `MEMORY.md` (it must not pay load) and OUTSIDE the memory
    directory (there every `*.md` that is not the index is treated as a memory by the store
    guards -- a cache file inside would make each of them fail for the wrong reason). It lives
    OUTSIDE the repo's `memoria/` mirror too: that directory is the target of an
    `rsync --delete` (memoria-espelho.sh) and a file with no pair in the source is DELETED.
    """
    ids, sem_id, dup = varre(memdir)
    gl = glosas_do_indice(memdir)
    out = [
        "# Numeric index of the memory -- DERIVED TABLE (cache, not source)",
        "",
        "**This is generated, not written.** The source is the `id:` in the frontmatter of each",
        "memory; this table is a regenerable cache (`scripts/memoria-id-assign.py --tabela`).",
        "A divergence between the two is a DEFECT OF THE TABLE, and the bijection guard refuses it.",
        "If this file burns: `grep -l 'id: N' <memory dir>/*.md`.",
        "",
        f"Population: {len(ids)} with id · {len(sem_id)} without id · {len(dup)} duplicate(s).",
        "",
        "| N | file | gloss |",
        "|---|------|-------|",
    ]
    for n in sorted(ids):
        p = ids[n]
        g = gl.get(n, "").replace("|", "\\|")
        out.append(f"| {n} | {p.stem} | {g} |")
    if sem_id:
        out += ["", "## Without id (pending assignment)", ""]
        out += [f"- {p.stem}" for p in sem_id]
    if dup:
        out += ["", "## DUPLICATE IDS -- the table above is LYING", ""]
        for n in sorted(dup):
            out.append(f"- `{n}`: " + ", ".join(p.stem for p in dup[n]))
    return "\n".join(out) + "\n"


def le_tabela(caminho=None):
    """{N: name} read from the table. A missing cache returns {} -- and the caller HAS to
    know the difference between 'empty cache' and 'empty store' (the resolver does: it falls
    back to the source and SAYS it fell back)."""
    c = Path(caminho) if caminho else TABELA
    if not c.is_file():
        return {}
    fora = {}
    for l in c.read_text(encoding="utf-8").split("\n"):
        m = re.match(r"\|\s*(\d+)\s*\|\s*(\S+)\s*\|", l)
        if m:
            fora[int(m.group(1))] = m.group(2)
    return fora
