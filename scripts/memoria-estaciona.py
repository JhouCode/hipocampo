#!/usr/bin/env python3
"""PARKS / RESUMES a block of `MEMORY.md` -- project rotation, mechanised.

WHY IT EXISTS
  "Put project X aside" used to be done by hand: the block was COPIED into a memory
  (`indice_<slug>_estacionado.md`) and the original STAYED in the index, still loading in every
  session of a project that was not on the table (measured: about 1 KB per session). Not by
  carelessness -- the memory-index guard refuses as ORPHAN every memory that `MEMORY.md` does
  not cite, so removing the block by hand blocks the mirror's commit. Parking without a
  mechanism was impossible. The request that created it: "park that project, I am going to
  work on this one" should be a command, not a hand edit.

WHAT IT DOES
  --estaciona <slug> --bloco "<start of the header>"
      moves the block (unindented header + indented lines) from `MEMORY.md` to
      `memory/indice_<slug>_estacionado.md` and leaves in its place the header + ONE line:
          <header, as it was>
            [id] PARKED <date> · memoria-estaciona.py --retoma <slug>
      If the file already exists, the frontmatter (id, name) is preserved and only the body is
      rewritten with the CURRENT block of the index -- the index is the truth, the copy a projection.
  --retoma <slug>
      the inverse, byte for byte: the block goes back in place of the stub and the parked file
      is removed (the mirror versions it; `git log` keeps what it was).
  --lista            what is parked today
  --selftest         park -> resume -> empty diff; and the negatives (ambiguous block, missing
                     slug, file without marker) exit != 0

WHAT IT DOES NOT DO
  It does not decide what to park -- that is the user's call, in the conversation. It does not
  touch any guard: the clause that makes a memory cited in `indice_*_estacionado.md` NOT an
  orphan lives in the memory-index guard (docs/guardas/memoria.md), proved failing there.
  It does not commit.

THE CHERRY-PICK
  A trigger source for parked projects (docs/gatilhos/) can warn, when a command touches a path
  of the parked project, that its index is not loaded and how to resume it. When the user
  declares "I am working on X", the order is one command: `--retoma X`.
"""
import datetime
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from memoria_ids import MEMDIR, varre, proximo  # noqa: E402

MARCADOR = "<!-- bloco -->"
STUB_RE = re.compile(r"^  \[(\d+)\] PARKED (\d{4}-\d{2}-\d{2}) · memoria-estaciona\.py --retoma ([a-z0-9_-]+)$")

#   THE TRIGGER REMINDER -- it exists because the trigger source PROMISES to stay paired with the
# parked file and nobody pairs it.
#
#   A trigger source for parked projects (docs/gatilhos/estacionado.md, if you keep one) says:
# "an item enters when a block is parked and leaves when it is resumed -- the line and the file
# move together". This script moves the block and does NOT touch it. Measured: a project was
# resumed and its trigger line stayed alive, firing for two hours a warning that told the agent
# to open a file `--retoma` had already deleted -- and claiming the project on the table was aside.
#
#   IT CANNOT BE FULLY AUTOMATED, which is why this is a REMINDER and not a fix: the `when it
# matches` column is a domain regex (which paths "belong to project X") and cannot be derived
# from the slug. What can be guaranteed is that nobody leaves here without knowing the other side
# is missing.
COBRANCA_GATILHO = (
    "\n   THE OTHER SIDE IS MISSING: fix `docs/gatilhos/estacionado.md` in the SAME change --"
    "\n      parked -> NEW line (with the project's `when it matches`) · resumed -> the line becomes a TOMBSTONE."
    "\n      The source promises that the line and the file move together; you keep that promise."
)


def memdir():
    return Path(os.environ.get("MEM_DIR", str(MEMDIR)))


def arquivo(slug, d):
    return d / f"indice_{slug}_estacionado.md"


def blocos(linhas):
    """[(start, end)] -- header = non-empty unindented line; the block runs up to the next one."""
    cabecas = [i for i, l in enumerate(linhas) if l and not l[0].isspace()]
    out = []
    for k, i in enumerate(cabecas):
        fim = cabecas[k + 1] if k + 1 < len(cabecas) else len(linhas)
        out.append((i, fim))
    return out


def separa_cauda(bloco):
    """Empty lines at the end of the block are index spacing, not content: they stay in the index."""
    n = len(bloco)
    while n > 0 and bloco[n - 1].strip() == "":
        n -= 1
    return bloco[:n], bloco[n:]


def estaciona(slug, comeco, d, hoje=None):
    hoje = hoje or datetime.date.today().isoformat()
    idx = d / "MEMORY.md"
    linhas = idx.read_text(encoding="utf-8").split("\n")
    alvos = [(i, f) for i, f in blocos(linhas) if linhas[i].startswith(comeco)]
    if len(alvos) != 1:
        return 2, f"block '{comeco}': {len(alvos)} header(s) match -- must be exactly 1"
    i, f = alvos[0]
    corpo, cauda = separa_cauda(linhas[i:f])
    if len(corpo) < 2:
        return 2, f"block '{linhas[i]}' has no indented line -- nothing to park"
    if STUB_RE.match(corpo[1] if len(corpo) > 1 else ""):
        return 2, f"block '{linhas[i]}' is ALREADY parked"
    arq = arquivo(slug, d)
    if arq.exists():
        texto = arq.read_text(encoding="utf-8")
        partes = texto.split("\n---\n", 1)
        if len(partes) != 2 or not texto.startswith("---\n"):
            return 2, f"{arq.name} exists and has no frontmatter -- not overwriting"
        fm = partes[0] + "\n---\n"
        m = re.search(r"^id:\s*(\d+)$", fm, re.M)
        if not m:
            return 2, f"{arq.name} exists and has no `id:` -- not overwriting"
        n = int(m.group(1))
    else:
        ids, _, dup = varre(d)
        if dup:
            return 2, f"duplicate ids in the store ({sorted(dup)}) -- resolve before creating a new memory"
        n = proximo(ids)
        cab = corpo[0].replace('"', "'")
        fm = (
            "---\n"
            f"name: indice_{slug}_estacionado\n"
            f"id: {n}\n"
            f'description: "Index block \'{cab[:60]}\' PARKED on {hoje} on request; '
            f'returns to MEMORY.md with memoria-estaciona.py --retoma {slug}"\n'
            "metadata:\n  node_type: indice\n  type: reference\n---\n"
        )
    corpo_txt = "\n".join(corpo) + "\n"
    arq.write_text(
        fm
        + f"\nPARKED on {hoje} on request -- the whole `MEMORY.md` block, byte for byte.\n"
        f"Returns with `python3 scripts/memoria-estaciona.py --retoma {slug}`. A memory cited here is not\n"
        "an orphan (memory-index guard clause): it is out of load, and opens with `memoria-resolve.py N` as always.\n\n"
        f"{MARCADOR}\n{corpo_txt}",
        encoding="utf-8",
    )
    stub = [corpo[0], f"  [{n}] PARKED {hoje} · memoria-estaciona.py --retoma {slug}"]
    novo = linhas[:i] + stub + cauda + linhas[f:]
    idx.write_text("\n".join(novo), encoding="utf-8")
    antes, depois = len("\n".join(linhas).encode()), len("\n".join(novo).encode())
    return 0, (f"parked '{corpo[0][:50]}' -> {arq.name} [{n}] · index {antes} -> {depois} B (-{antes - depois})"
               + COBRANCA_GATILHO)


def retoma(slug, d):
    idx = d / "MEMORY.md"
    arq = arquivo(slug, d)
    if not arq.exists():
        return 2, f"nothing parked as '{slug}' ({arq.name} does not exist)"
    texto = arq.read_text(encoding="utf-8")
    if f"\n{MARCADOR}\n" not in texto:
        return 2, f"{arq.name} lacks the marker {MARCADOR} -- it was not parked by this script; resume by hand"
    bloco = texto.split(f"\n{MARCADOR}\n", 1)[1].rstrip("\n").split("\n")
    linhas = idx.read_text(encoding="utf-8").split("\n")
    pos = [i for i, l in enumerate(linhas) if STUB_RE.match(l) and STUB_RE.match(l).group(3) == slug]
    if len(pos) != 1:
        return 2, f"stub of '{slug}' in MEMORY.md: {len(pos)} found, expected 1"
    i = pos[0]
    if i == 0 or linhas[i - 1] != bloco[0]:
        return 2, f"the header above the stub ('{linhas[i-1][:40]}') does not match the block's ('{bloco[0][:40]}')"
    novo = linhas[: i - 1] + bloco + linhas[i + 1:]
    idx.write_text("\n".join(novo), encoding="utf-8")
    arq.unlink()
    return 0, (f"resumed '{bloco[0][:50]}' ({len(bloco)} lines) · {arq.name} removed"
               + COBRANCA_GATILHO)


def lista(d):
    out = []
    for arq in sorted(d.glob("indice_*_estacionado.md")):
        t = arq.read_text(encoding="utf-8")
        m = re.search(r"PARKED on (\S+)", t)
        cab = t.split(f"\n{MARCADOR}\n", 1)[1].split("\n", 1)[0] if MARCADOR in t else "(no marker -- by hand)"
        out.append(f"{arq.name:45s} {m.group(1) if m else '?':10s} {cab[:60]}")
    return 0, "\n".join(out) if out else "nothing parked"


def selftest():
    ok = True

    def checa(nome, cond):
        nonlocal ok
        print(("  ✓ " if cond else "  ✗ ") + nome)
        ok = ok and cond

    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        for n, nome in ((1, "feedback_a"), (2, "feedback_b"), (3, "project_c")):
            (d / f"{nome}.md").write_text(f"---\nname: {nome}\nid: {n}\ndescription: x\nmetadata:\n  type: feedback\n---\ncorpo\n")
        original = (
            "Memory Index\n  opening line here\n\nBlock A\n  [1] (a) · [2] (b)\n\n"
            "Block B -- what leaves\n  [3] (c)\n  second line\n  third line, long enough for the block to weigh more than the stub\n\nBlock C\n  end\n"
        )
        (d / "MEMORY.md").write_text(original)
        rc, msg = estaciona("b", "Block B", d, hoje="2026-09-02")
        checa("park exits 0", rc == 0)
        idx = (d / "MEMORY.md").read_text()
        checa("the index shrank", len(idx) < len(original))
        checa("the stub has 2 lines and cites the new id [4]", "Block B -- what leaves\n  [4] PARKED 2026-09-02 · memoria-estaciona.py --retoma b\n\nBlock C" in idx)
        checa("the stub fits in 80 B", all(len(l.encode()) <= 80 for l in idx.split("\n") if "PARKED" in l))
        arq = d / "indice_b_estacionado.md"
        checa("the parked file was born with id 4 and the marker", arq.exists() and "id: 4\n" in arq.read_text() and MARCADOR in arq.read_text())
        checa("the whole block is in the file", "  [3] (c)\n  second line\n  third line" in arq.read_text())
        rc2, _ = estaciona("b", "Block B", d)
        checa("parking the same block again exits != 0", rc2 != 0)
        rc3, _ = estaciona("x", "Block", d)
        checa("an ambiguous header (3 match) exits != 0", rc3 != 0)
        rc4, _ = retoma("nao-existe", d)
        checa("resuming a missing slug exits != 0", rc4 != 0)
        (d / "indice_manual_estacionado.md").write_text("---\nname: indice_manual_estacionado\nid: 9\ndescription: x\n---\nno marker\n")
        rc5, _ = retoma("manual", d)
        checa("a file without the marker exits != 0", rc5 != 0)
        rc6, msg6 = retoma("b", d)
        checa("resume exits 0", rc6 == 0)
        checa("MEMORY.md came back BYTE FOR BYTE", (d / "MEMORY.md").read_text() == original)
        checa("the parked file is gone", not arq.exists())
        # pre-existing file (a block copied by hand before): frontmatter preserved, body rewritten
        (d / "indice_b_estacionado.md").write_text("---\nname: indice_b_estacionado\nid: 7\ndescription: stale\nmetadata:\n  type: reference\n---\n\nstale body\n")
        rc7, _ = estaciona("b", "Block B", d, hoje="2026-09-02")
        t7 = (d / "indice_b_estacionado.md").read_text()
        checa("pre-existing file: id 7 preserved, body rewritten with the block", rc7 == 0 and "id: 7\n" in t7 and "stale body" not in t7 and "[3] (c)" in t7)
        checa("the stub cites the preserved id [7]", "[7] PARKED" in (d / "MEMORY.md").read_text())
        rc8, _ = retoma("b", d)
        checa("resuming the pre-existing one comes back byte for byte", rc8 == 0 and (d / "MEMORY.md").read_text() == original)
    print("SELFTEST", "OK" if ok else "FAILED")
    return 0 if ok else 1


def main(argv):
    d = memdir()
    if "--selftest" in argv:
        return selftest()
    if "--lista" in argv:
        rc, msg = lista(d)
    elif "--estaciona" in argv:
        slug = argv[argv.index("--estaciona") + 1]
        if "--bloco" not in argv:
            print("--estaciona needs --bloco \"<start of the header>\"", file=sys.stderr)
            return 2
        rc, msg = estaciona(slug, argv[argv.index("--bloco") + 1], d)
    elif "--retoma" in argv:
        rc, msg = retoma(argv[argv.index("--retoma") + 1], d)
    else:
        print(__doc__)
        return 2
    print(msg, file=sys.stderr if rc else sys.stdout)
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
