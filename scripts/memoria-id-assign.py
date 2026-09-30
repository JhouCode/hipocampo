#!/usr/bin/env python3
"""ASSIGNS the `id:` of the frontmatter -- on the write path AND as a late repair.

WHY IT MAY RUN LATE, and this is not a patch
  The objection was a good one: with numbers, every memory write starts depending on a
  mechanism, and a mechanism that fails silently would give birth to a memory without an id
  plus an orphan line in the index. The answer comes from the DESIGN, not from discipline:

    a memory without an id was NEVER cited by number -- you cannot cite a number that does not exist.

  So assigning late is ALWAYS safe: the invariant ("never renumber once cited") cannot be
  violated by a file nobody cited. The failure mode is a self-healing delay, not corruption.
  The irreversible one (reusing an id) stays forbidden. And the degraded write is the old
  format: the mechanism failed -> the index line goes in with the full file name, which is
  exactly what was done before numbers. There is no failure mode worse than the present.

WHAT IT DOES NOT DO, ON PURPOSE
  · it does not renumber anything that already has an id;
  · it does not fill a hole (a deleted memory takes its number to the grave);
  · it does not "fix" a duplicate: a duplicate is RED and it exits != 0 writing NOTHING.
    Choosing which of the two owners wins is choosing the wrong copy in silence.

USAGE
  memoria-id-assign.py              assigns an id to whoever lacks one + regenerates the table
  memoria-id-assign.py --dry-run    says what it would do, does not write
  memoria-id-assign.py --tabela     only regenerates the derived table
  memoria-id-assign.py --selftest   proves the controls, positive AND negative
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from memoria_ids import (  # noqa: E402
    TABELA, _ID, _NAME, frontmatter, proximo, render_tabela, varre,
)


def insere_id(texto, n):
    """Writes `id: N` at the root level of the frontmatter, right after `name:`.

    THE POSITION IS SEMANTIC, not aesthetic: the frontmatter has `metadata:` with INDENTED
    children at the end. Appending at the end of the block would push the `id` inside
    `metadata`, and `_ID` (column zero) would stop finding it -- the file would carry an id
    nobody reads, which is worse than no id, because it looks done."""
    if not texto.startswith("---\n"):
        raise ValueError("no frontmatter")
    fim = texto.find("\n---", 3)
    if fim < 0:
        raise ValueError("frontmatter does not close")
    bloco = texto[4:fim]
    if _ID.search(bloco):
        return texto                              # already has one: untouched
    linhas = bloco.split("\n")
    pos = 0
    for i, l in enumerate(linhas):
        if _NAME.match(l):
            pos = i + 1
            break
    linhas.insert(pos, f"id: {n}")
    return "---\n" + "\n".join(linhas) + texto[fim:]


def rodada(memdir=None, seco=False, tabela=None):
    """(assigned, already_had, duplicates). A duplicate ABORTS before any write."""
    ids, sem_id, dup = varre(memdir)
    if dup:
        return None, len(ids), dup
    atribuidos = []
    n = proximo(ids)
    for p in sorted(sem_id):                       # stable order: same input, same ids
        if not seco:
            t = p.read_text(encoding="utf-8")
            p.write_text(insere_id(t, n), encoding="utf-8")
        atribuidos.append((n, p.stem))
        n += 1
    if not seco:
        alvo = Path(tabela) if tabela else TABELA
        alvo.parent.mkdir(parents=True, exist_ok=True)
        alvo.write_text(render_tabela(memdir), encoding="utf-8")
    return atribuidos, len(ids), {}


# ----------------------------- selftest -----------------------------
def _fixture(d, arquivos):
    """arquivos: {name: id_or_None}"""
    for nome, i in arquivos.items():
        fm = ["---", f"name: {nome}"]
        if i is not None:
            fm.append(f"id: {i}")
        fm += ["description: test gloss here", "metadata:", "  type: feedback", "---", "", "body"]
        (d / f"{nome}.md").write_text("\n".join(fm) + "\n", encoding="utf-8")


def selftest():
    import shutil
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
    # the table OUTSIDE the memory directory -- and this selftest is the proof that the
    # decision is not aesthetic: with the table inside `d`, `varre()` treats it as a memory
    # without frontmatter and the next round blows up. It is the same collision it would
    # cause in every store guard that globs `*.md` minus `MEMORY.md`.
    tab = raiz / "tabela.md"
    try:
        # POSITIVE · a virgin store gets 1..3, in stable order
        _fixture(d, {"feedback_a": None, "feedback_b": None, "feedback_c": None})
        at, ja, dup = rodada(d, tabela=tab)
        chk(dup == {} and [n for n, _ in at] == [1, 2, 3], "positive · a virgin store receives 1,2,3")
        chk([nm for _, nm in at] == ["feedback_a", "feedback_b", "feedback_c"],
            "positive · the order is stable (alphabetical), not the filesystem's")

        # IDEMPOTENCE · running again changes NOTHING
        antes = {p.name: p.read_text() for p in d.glob("*.md")}
        at2, _, _ = rodada(d, tabela=tab)
        depois = {p.name: p.read_text() for p in d.glob("*.md")}
        chk(at2 == [] and antes == depois, "idempotent · the 2nd round neither assigns nor rewrites")

        # POSITIVE · a new memory enters with max+1
        _fixture(d, {"feedback_d": None})
        at3, _, _ = rodada(d, tabela=tab)
        chk(at3 == [(4, "feedback_d")], "positive · a new memory receives max+1")

        # INVARIANT · a hole is NOT filled
        (d / "feedback_b.md").unlink()
        _fixture(d, {"feedback_e": None})
        at4, _, _ = rodada(d, tabela=tab)
        chk(at4 == [(5, "feedback_e")], "invariant · the id of a deleted memory (2) is NOT reused")

        # INVARIANT · an existing id is never renumbered
        txt = (d / "feedback_a.md").read_text()
        chk("id: 1" in txt, "invariant · whoever already had an id keeps the SAME one")

        # NEGATIVE · a duplicate ABORTS and writes nothing
        _fixture(d, {"feedback_gemeo": 1})          # collides with feedback_a
        _fixture(d, {"feedback_f": None})           # and there is legitimate pending work
        antes = {p.name: p.read_text() for p in d.glob("*.md")}
        at5, _, dup5 = rodada(d, tabela=tab)
        depois = {p.name: p.read_text() for p in d.glob("*.md")}
        chk(at5 is None and 1 in dup5, "NEGATIVE · a duplicate id returns RED, does not fix")
        chk(antes == depois, "NEGATIVE · with a duplicate present, ZERO files are touched")
        (d / "feedback_gemeo.md").unlink()

        # NEGATIVE · the `id` must not land inside `metadata:`
        t = (d / "feedback_a.md").read_text()
        fm = frontmatter(t)
        pos_id = fm.index("id: 1")
        pos_meta = fm.index("metadata:")
        chk(pos_id < pos_meta, "NEGATIVE · the id stays at ROOT level, before `metadata:`")

        # DETERMINISM of the table · generating twice gives the same bytes
        a = render_tabela(d)
        b = render_tabela(d)
        chk(a == b, "table · deterministic (same input, same bytes)")

        # ABSENCE CONTROL · a file without frontmatter is not silently swallowed
        (d / "feedback_cru.md").write_text("no frontmatter at all\n", encoding="utf-8")
        try:
            insere_id("no frontmatter at all\n", 9)
            ok = False
        except ValueError:
            ok = True
        chk(ok, "absence · a file without frontmatter raises, does not write crooked")
    finally:
        shutil.rmtree(raiz, ignore_errors=True)

    print(f"== {len(total) - len(falhas)} of {len(total)} ok · {len(falhas)} failure(s) ==")
    return 1 if falhas else 0


if __name__ == "__main__":
    argv = sys.argv[1:]
    if "-h" in argv or "--help" in argv:
        print((__doc__ or "").strip())
        sys.exit(0)
    if "--selftest" in argv:
        print("SELFTEST -- id assignment, positive AND negative controls:")
        sys.exit(selftest())

    if "--tabela" in argv:
        ids, sem, dup = varre()
        TABELA.parent.mkdir(parents=True, exist_ok=True)
        TABELA.write_text(render_tabela(), encoding="utf-8")
        print(f"table: {TABELA} · {len(ids)} with id · {len(sem)} without id · {len(dup)} duplicate(s)")
        sys.exit(1 if dup else 0)

    seco = "--dry-run" in argv
    at, ja, dup = rodada(seco=seco)
    if at is None:
        print("DUPLICATE IDS -- nothing was written. Decide BY HAND which file keeps the number:")
        for n in sorted(dup):
            print(f"   id {n}: " + ", ".join(str(p) for p in dup[n]))
        sys.exit(2)
    print(f"{'(dry) ' if seco else ''}{len(at)} assigned · {ja} already had an id")
    for n, nome in at:
        print(f"   {n} -> {nome}")
    sys.exit(0)
