#!/usr/bin/env python3
"""RESOLVES `N` -> path of the memory. And when it does not resolve, it ACCUSES.

THE HIERARCHY OF SOURCES, and it is the whole design
  1. The derived TABLE (`docs/INDICE_NUMERICO.md`) -- cache, fast.
  2. The SOURCE (the `id:` in the frontmatter) -- whenever the table fails, and whenever
     `--fonte` is asked for.
  The table never decides alone: what it returns is CHECKED against the file before it
  leaves. A cache that answers without checking is the fallback silently picking the old copy.

WHAT IT NEVER DOES
  Return empty with rc=0. A missing id exits != 0 and names the number it did not find:
  a green silence is indistinguishable from "all is well", and an empty
  `$(memoria-resolve.py 999)` inside a `Read` would become an error without a cause.

USAGE
  memoria-resolve.py 7              absolute path (rc=0) or error (rc=1)
  memoria-resolve.py 7 --nome       only the name (no path, no .md)
  memoria-resolve.py --fonte 7      ignores the table, goes straight to the frontmatter
  memoria-resolve.py --selftest     positive, negative and fallback controls
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from memoria_ids import MEMDIR, le_tabela, varre  # noqa: E402


def resolve(n, memdir=None, tabela=None, so_fonte=False):
    """(Path|None, source_used, warning). `warning` is text for STDERR, never stdout."""
    d = Path(memdir) if memdir else MEMDIR
    aviso = ""
    if not so_fonte:
        tab = le_tabela(tabela)
        nome = tab.get(n)
        if nome:
            p = d / f"{nome}.md"
            # CHECKS against the disk before answering: the table is a cache, and a divergent
            # cache is a defect of the table -- not a reason to lie.
            ids, _, _ = varre(d)
            if ids.get(n) == p:
                return p, "tabela", ""
            aviso = (f"the table says {n} is '{nome}', but the frontmatter does NOT confirm it -- "
                     f"fell back to the source. Regenerate: memoria-id-assign.py --tabela")
        elif tab:
            aviso = f"id {n} is not in the table -- fell back to the source (stale table?)"
        else:
            aviso = "table missing or empty -- resolving from the source"
    ids, _, dup = varre(d)
    if n in dup:
        return None, "fonte", (f"id {n} has TWO owners: "
                               + ", ".join(p.name for p in dup[n]))
    p = ids.get(n)
    return (p, "fonte", aviso) if p else (None, "fonte", aviso)


# ----------------------------- selftest -----------------------------
def selftest():
    import shutil
    import subprocess
    import tempfile
    falhas, total = [], []

    def chk(ok, nome):
        print(("  ✓ " if ok else "  ✗ ") + nome)
        total.append(nome)
        if not ok:
            falhas.append(nome)

    raiz = Path(tempfile.mkdtemp())
    d = raiz / "mem"
    d.mkdir()
    tab = raiz / "tabela.md"
    try:
        for nome, i in (("feedback_um", 1), ("feedback_dois", 2), ("project_tres", 3)):
            (d / f"{nome}.md").write_text(
                f"---\nname: {nome}\nid: {i}\ndescription: gloss of {nome}\n---\n\nbody\n",
                encoding="utf-8")
        from memoria_ids import render_tabela
        tab.write_text(render_tabela(d), encoding="utf-8")

        # POSITIVE CONTROL -- a known id resolves, through the table
        p, fonte, av = resolve(2, d, tab)
        chk(p is not None and p.stem == "feedback_dois" and fonte == "tabela",
            "POSITIVE · a known id resolves through the table")

        # NEGATIVE CONTROL -- a missing id ACCUSES, it does not return a green empty
        p, fonte, av = resolve(999, d, tab)
        chk(p is None, "NEGATIVE · a missing id returns None (never an empty path)")

        # and the negative holds AT THE MOUTH, not only in the function: the process rc must be != 0
        eu = str(Path(__file__).resolve())
        import os
        env = dict(os.environ, MEM_DIR=str(d), MEM_TABELA=str(tab))
        r_ok = subprocess.run([sys.executable, eu, "2"], capture_output=True, text=True, env=env)
        r_no = subprocess.run([sys.executable, eu, "999"], capture_output=True, text=True, env=env)
        chk(r_ok.returncode == 0 and "feedback_dois" in r_ok.stdout,
            "POSITIVE · at the mouth: rc=0 and the path on stdout")
        chk(r_no.returncode != 0 and r_no.stdout.strip() == "" and "999" in r_no.stderr,
            "NEGATIVE · at the mouth: rc!=0, EMPTY stdout, the number named on stderr")

        # FALLBACK -- burned table, the source answers the same (and warns)
        tab.unlink()
        p, fonte, av = resolve(3, d, tab)
        chk(p is not None and p.stem == "project_tres" and fonte == "fonte" and av,
            "FALLBACK · without the table, the frontmatter resolves -- and the warning is printed")

        # FALLBACK · a LYING table is not obeyed
        tab.write_text("| N | file | gloss |\n|---|---|---|\n| 1 | project_tres |  |\n",
                       encoding="utf-8")
        p, fonte, av = resolve(1, d, tab)
        chk(p is not None and p.stem == "feedback_um" and fonte == "fonte",
            "FALLBACK · a divergent table is DISCARDED, the frontmatter wins")

        # DUPLICATE -- two owners: refuses, does not pick
        (d / "feedback_gemeo.md").write_text(
            "---\nname: feedback_gemeo\nid: 1\ndescription: x\n---\n\nc\n", encoding="utf-8")
        p, fonte, av = resolve(1, d, None, so_fonte=True)
        chk(p is None and "TWO owners" in av,
            "NEGATIVE · an id with two owners REFUSES (does not silently pick a copy)")
    finally:
        shutil.rmtree(raiz, ignore_errors=True)

    print(f"== {len(total) - len(falhas)} of {len(total)} ok · {len(falhas)} failure(s) ==")
    return 1 if falhas else 0


if __name__ == "__main__":
    argv = sys.argv[1:]
    if "--selftest" in argv:
        print("SELFTEST -- resolver: positive, negative, fallback and duplicate:")
        sys.exit(selftest())

    nums = [a for a in argv if a.isdigit()]
    if not nums:
        print("usage: memoria-resolve.py <N> [--nome] [--fonte]", file=sys.stderr)
        sys.exit(2)
    n = int(nums[0])
    p, fonte, aviso = resolve(n, so_fonte="--fonte" in argv)
    if aviso:
        print(f"[memoria-resolve] {aviso}", file=sys.stderr)
    if p is None:
        print(f"id {n} DOES NOT EXIST in the store ({MEMDIR}). "
              f"Check: grep -l '^id: {n}$' {MEMDIR}/*.md", file=sys.stderr)
        sys.exit(1)
    print(p.stem if "--nome" in argv else str(p))
