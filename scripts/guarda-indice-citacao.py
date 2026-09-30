#!/usr/bin/env python3
"""THE INDEX-CITATION GUARD -- bijection `[N]` <-> frontmatter, and a mandatory gloss.

WHAT IT DEFENDS, and why each state has the colour it has
  The index stopped writing the file name and started citing `[7]`. That makes a class of
  defect ENUMERABLE that already existed and was MUTE: a wrong-but-plausible name in the index
  is invisible to the machine -- `[7]` either resolves or it does not.
  There are these states, and they do not weigh the same:

  FAIL  DUPLICATE id           -- two owners for the same number. Every citation of that number
                                  became ambiguous. Irreversible if someone "fixes" it by
                                  silently picking a side.
  FAIL  `[N]` WITHOUT TARGET   -- the index points at the void. The dead pointer, now
                                  checkable in one pass.
  FAIL  id CITED NOWHERE       -- a memory with a number the index does not cite: it does NOT
                                  LOAD, and nothing flagged it before (the "orphan").
  FAIL  `[N]` WITHOUT GLOSS    -- without it the index decays into blind numbers over time, and
                                  the hash version -- already refused by measurement -- comes
                                  back through the back door. The gloss is the channel that
                                  WORKS: it is what decides to open. The address does no work
                                  until the lookup.
  FAIL  derived TABLE diverges -- the table is a cache; a cache that lies is a defect.
  WARN  memory WITHOUT id      -- safely repairable (it was never cited by number), goes away
                                  with `memoria-id-assign.py`. A warning, not a barrier.
  WARN  line with the full NAME -- pending conversion. The old format, degraded but correct.
                                  Blocking it would block legitimate work.

USAGE
  guarda-indice-citacao.py             runs against the real store (MEM_DIR, default: the
                                       configured memory folder)
  guarda-indice-citacao.py --selftest  proves EACH rule failing on purpose
"""
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from memoria_ids import CITACAO, le_tabela, varre  # noqa: E402
import hipo_config as HC  # noqa: E402

# Floor of the gloss, in USEFUL characters (no punctuation/separator). Not taste: the
# shortest legitimate gloss measured in a real index had 14, and below 10 what is left does
# not answer "why would I open this?" -- it becomes a blind number with decoration.
PISO_GLOSA = 10
# A memory name written in full in the index, in the positions where a pointer lives
# (start of line, after a separator). The same NARROW axis as the memory-index guard: prose
# that mentions a name mid-sentence is not a pending pointer.
_NOME_POS = re.compile(r'(?:^[ \t]*|[-:·][ \t]+)([a-z0-9_][a-z0-9_-]*\.md)\b', re.M)


def glosas(linha):
    """[(N, gloss)] -- the gloss of a citation is the text UP TO the next citation.

    A line lists several sibling memories (`[1] one thing · [2] another`); measuring the whole
    line would give the last citation a free gloss. The partitioning is the same as the
    memory-index guard's, for the same reason."""
    marcas = list(CITACAO.finditer(linha))
    fora = []
    for i, m in enumerate(marcas):
        fim = marcas[i + 1].start() if i + 1 < len(marcas) else len(linha)
        texto = linha[m.end():fim]
        util = re.sub(r'[^0-9A-Za-zÀ-ÿ]', '', texto)
        fora.append((int(m.group(1)), texto.strip(), len(util)))
    return fora


def confere(memdir=None, indice=None, tabela=None):
    """[(colour, message)] -- 'FAIL' or 'WARN'. Empty list = all good."""
    d = Path(memdir) if memdir else Path(os.environ.get(
        "MEM_DIR", HC.MEMORY_DIR))
    idx = Path(indice) if indice else d / "MEMORY.md"
    if not idx.is_file():
        return [("FAIL", f"index {idx} missing -- nothing loads into the context")]

    ids, sem_id, dup = varre(d)
    txt = idx.read_text(encoding="utf-8")
    p = []

    # FAIL 1 · bijection broken on the SOURCE side
    for n in sorted(dup):
        p.append(("FAIL", "id %d has TWO owners: %s -- every citation of [%d] became ambiguous"
                  % (n, ", ".join(x.name for x in dup[n]), n)))

    citados = set()
    for i, linha in enumerate(txt.split("\n"), 1):
        for n, texto, util in glosas(linha):
            citados.add(n)
            # FAIL 2 · citation without target
            if n not in ids:
                p.append(("FAIL", "line %d: [%d] does not resolve -- no memory has that id" % (i, n)))
                continue
            # FAIL 4 · citation without gloss
            if util < PISO_GLOSA:
                p.append(("FAIL", "line %d: [%d] (%s) without gloss -- %d useful characters, floor %d. "
                          "A blind number does not say why to open it."
                          % (i, n, ids[n].stem, util, PISO_GLOSA)))

    # FAIL 3 · a memory with an id the index does not cite: it does not load, and nothing flagged it
    for n in sorted(set(ids) - citados):
        p.append(("FAIL", "memory with id %d is NEVER cited in the index: %s -- it does not load, "
                  "and nothing flags it" % (n, ids[n].stem)))

    # WARN · memory without id -- repairable, goes away with `memoria-id-assign.py`
    if sem_id:
        p.append(("WARN", "%d memory(ies) without id (run memoria-id-assign.py): %s"
                  % (len(sem_id), ", ".join(x.stem for x in sem_id[:5])
                     + (" …" if len(sem_id) > 5 else ""))))

    # WARN · full name in the index -- pending conversion
    vivas = {x.name for x in d.glob("*.md")} - {"MEMORY.md"}
    pend = sorted({r for r in _NOME_POS.findall(txt) if r in vivas})
    if pend:
        p.append(("WARN", "%d pointer(s) still by NAME (pending conversion to [N]): %s"
                  % (len(pend), ", ".join(pend[:5]) + (" …" if len(pend) > 5 else ""))))

    # FAIL 5 · derived table diverging from the source (it is a cache; a cache that lies is a defect)
    tab = le_tabela(tabela)
    if tab:
        fonte = {n: x.stem for n, x in ids.items()}
        if tab != fonte:
            faltam = sorted(set(fonte) - set(tab))
            sobram = sorted(set(tab) - set(fonte))
            trocados = sorted(n for n in set(tab) & set(fonte) if tab[n] != fonte[n])
            p.append(("FAIL", "derived table diverged from the source: %d missing, %d extra, "
                      "%d swapped -- regenerate with memoria-id-assign.py --tabela"
                      % (len(faltam), len(sobram), len(trocados))))
    return p


# ----------------------------- selftest -----------------------------
def selftest():
    """EACH rule proved FAILING on purpose, and the green proved on the clean control.

    A guard that never failed on purpose is decoration, and filtering the output is not
    proving: here the defect is PLANTED in the store and the whole guard runs over it."""
    import shutil
    import tempfile
    falhas, total = [], []

    def chk(ok, nome, detalhe=""):
        print(("  ✓ " if ok else "  ✗ ") + nome + (("  → " + detalhe) if not ok else ""))
        total.append(nome)
        if not ok:
            falhas.append(nome)

    def monta(d, mems, linhas_idx):
        for nome, i in mems:
            fm = ["---", f"name: {nome}"]
            if i is not None:
                fm.append(f"id: {i}")
            fm += [f"description: gloss of {nome}", "---", "", "body"]
            (d / f"{nome}.md").write_text("\n".join(fm) + "\n", encoding="utf-8")
        (d / "MEMORY.md").write_text("\n".join(linhas_idx) + "\n", encoding="utf-8")

    def cores(res):
        return {c for c, _ in res}

    base_mems = [("feedback_um", 1), ("feedback_dois", 2)]
    base_idx = ["Memory Index", "  [1] the first rule that holds · [2] the second rule that holds"]

    casos = [
        # (name, mems, index, expected)
        ("CLEAN CONTROL · an intact store stays GREEN", base_mems, base_idx, "green"),
        ("FAIL · duplicate id",
         [("feedback_um", 1), ("feedback_dois", 2), ("feedback_gemeo", 1)],
         base_idx + ["  [1] I also cite the twin here"], "FAIL"),
        ("FAIL · [N] cited without target",
         base_mems, base_idx + ["  [8] gloss of a memory that does not exist"], "FAIL"),
        ("FAIL · [N] without gloss (blind number)",
         base_mems, ["Memory Index", "  [1] the first rule that holds · [2]"], "FAIL"),
        ("FAIL · memory with an id the index does not cite",
         base_mems + [("feedback_tres", 3)], base_idx, "FAIL"),
        ("WARN · memory without id (repairable, does not block)",
         base_mems + [("feedback_novo", None)],
         base_idx + ["  feedback_novo.md - came in today and has no number yet"], "WARN"),
        ("WARN · pointer still by NAME (pending conversion)",
         base_mems, base_idx + ["  feedback_um.md - the same memory cited by its old name"],
         "WARN"),
    ]

    for nome, mems, idx, espera in casos:
        raiz = Path(tempfile.mkdtemp())
        d = raiz / "mem"
        d.mkdir()
        try:
            monta(d, mems, idx)
            res = confere(d, tabela=raiz / "nao-existe.md")
            c = cores(res)
            if espera == "green":
                ok = not res
            elif espera == "FAIL":
                ok = "FAIL" in c
            else:
                ok = "WARN" in c and "FAIL" not in c
            chk(ok, nome, repr(res[:2]))
        finally:
            shutil.rmtree(raiz, ignore_errors=True)

    # divergent table -- needs a real table, a separate case
    raiz = Path(tempfile.mkdtemp())
    d = raiz / "mem"
    d.mkdir()
    tab = raiz / "tabela.md"
    try:
        monta(d, base_mems, base_idx)
        from memoria_ids import render_tabela
        tab.write_text(render_tabela(d), encoding="utf-8")
        chk(not confere(d, tabela=tab), "CLEAN CONTROL · with a correct table it stays GREEN")
        tab.write_text("| N | file | gloss |\n|---|---|---|\n| 1 | feedback_dois |  |\n",
                       encoding="utf-8")
        r = confere(d, tabela=tab)
        chk(any("derived table diverged" in m for _, m in r), "FAIL · derived table lying",
            repr(r))
    finally:
        shutil.rmtree(raiz, ignore_errors=True)

    # the gloss predicate, both ways, without touching disk
    chk(glosas("  [1] a gloss long enough")[0][2] >= PISO_GLOSA,
        "predicate · a long gloss passes")
    chk(glosas("  [1] · - ")[0][2] < PISO_GLOSA,
        "predicate · punctuation alone does NOT count as a gloss")
    chk([n for n, _, _ in glosas("  [1] aaa · [2] bbb")] == [1, 2],
        "predicate · two citations on the same line are separated")
    chk(glosas("  [[feedback_x]] old link") == [],
        "predicate · a two-bracket `[[link]]` is NOT a numeric citation")
    # the gloss of the LAST citation must not inherit the text of the first
    g = glosas("  [1] a gloss that is really long enough · [2]")
    chk(g[1][2] < PISO_GLOSA, "predicate · the last citation does not inherit the previous gloss")

    print(f"== {len(total) - len(falhas)} of {len(total)} ok · {len(falhas)} failure(s) ==")
    return 1 if falhas else 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        print("SELFTEST -- each rule proved FAILING on purpose:")
        sys.exit(selftest())
    res = confere()
    for cor, msg in res:
        print(f"{cor}|{msg}")
    if not res:
        print("OK index-citation intact: bijection, gloss and table check out")
    sys.exit(1 if any(c == "FAIL" for c, _ in res) else 0)
