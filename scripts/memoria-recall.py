#!/usr/bin/env python3
"""THE RECALL -- how many times each memory was REALLY opened, and which never were.

WHY THIS EXISTS
  You can know how many memories exist, their size and the link graph between them, and still know
  ZERO about which ones are USED. Some have no incoming link -- they arrive only through their
  `description` -- and without an instrument nothing says whether any of them is already dead. A
  store with no evidence of use only grows: the cut becomes a guess.

WHAT COUNTS AS RECALL -- and why the definition is the instrument
  Recall is OPENING ONE SPECIFIC FILE. It is not `ls memory/`, not `wc -c *.md`, not writing to it,
  and not the name showing up in a command's output. A single `ls` of the directory mentions every
  memory and would produce one "recall" for each -- the highest and most useless number possible.
    That is why the extraction runs over `tool_use` (what the agent asked for), never over
  `tool_result` (what the world returned), and requires the path `memory/<name>.md` spelled out in
  the segment.

WHAT IT DOES NOT REIMPLEMENT
  `e_escrita` and `segmentos` come from `gatilho.py`. That module already paid three pilot findings
  on this same distinction (reading is not writing; a write in one segment does not contaminate the
  read in another). A second copy of the rule = a second truth.

POPULATION -- read before quoting any number from here
  The transcripts cover the sessions that exist ON DISK, and today's memory store is not
  yesterday's: a purge kills memories that were read a lot before it. So the output always
  separates `live` (the file exists now) from `historical` (the name was cited, the file no longer
  exists), and declares the horizon of the transcripts.

PATHS
  The memory folder is HIPO_MEMORY_DIR and the transcript store is the folder that holds
  HIPO_PROJECT_DIR (every project store next to it, as Claude Code lays them out); both come from
  `hipo_config`. The `cd <memory dir> && cat <bare name>` matcher is built from the last three
  components of the memory folder (`projects/<slug>/memory`), so it follows your project's slug.

USAGE
  memoria-recall.py                report
  memoria-recall.py --nunca        only the live memories with zero recall
  memoria-recall.py --json         raw data
  memoria-recall.py --selftest     proves the predicates, with a positive AND a negative control
"""
import json, os, re, sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gatilho import e_escrita, segmentos  # noqa: E402  -- the rule lives there, not here
import hipo_config as HC  # noqa: E402

MEMORIA = Path(HC.MEMORY_DIR)
PROJETOS = Path(HC.PROJECT_DIR).parent
# requires the directory spelled out: `memory/<name>.md`. A glob (`*.md`) does not match, on purpose.
_PATH = re.compile(r"memory/([a-z_0-9]+)\.md")
_TOOL_ARQ = ("Read", "Write", "Edit", "NotebookEdit")
# `projects/<slug>/memory` -- the tail of the memory folder, so the matcher follows the user's slug.
_SUFIXO = "/".join(MEMORIA.parts[-3:])
_DIR = re.compile(r'(?:cd|ls|cat|grep|sed)\s[^\n]*' + re.escape(_SUFIXO) + r'\b')
_NU = re.compile(r'\b([a-z_0-9]+)\.md\b')


def _sem_heredoc(cmd):
    """The EXECUTABLE segments, without heredoc bodies.

    MEASURED DEFECT, and it inflated a number about to be published. `segmentos()` splits on
    newlines; a `cat > target.md <<'EOF' ... EOF` turns each LINE OF THE CONTENT into a "segment"
    with no redirection -- so writing `memory/x.md` INSIDE a file was counted as a READ of x. That
    is how the memories cited in a trigger source showed up as "opened" when none had been: the
    recall rate jumped by four points on text the agent itself wrote.
      File content is not a command. The heredoc body leaves before any classification.
    """
    fora, dentro, delim = [], False, None
    for l in cmd.split("\n"):
        if dentro:
            if l.strip() == delim:
                dentro = False
            continue
        m = re.search(r"<<-?\s*'?\"?([A-Za-z_][A-Za-z0-9_]*)'?\"?", l)
        if m:
            dentro, delim = True, m.group(1)
            fora.append(l)          # the `cat > target` line is still a command
            continue
        fora.append(l)
    return [s for s in segmentos("\n".join(fora)) if s.strip()]


def vivas():
    return {p.stem for p in MEMORIA.glob("*.md") if p.name != "MEMORY.md"}


def toques(linha):
    """Returns the `tool_use` blocks of one transcript line, in the shape gatilho.py understands."""
    try:
        r = json.loads(linha)
    except Exception:
        return None  # None != [] -- an unreadable line is a DEFECT, not an absence
    msg = r.get("message") or {}
    conteudo = msg.get("content")
    if not isinstance(conteudo, list):
        return []
    fora = []
    for b in conteudo:
        if isinstance(b, dict) and b.get("type") == "tool_use":
            fora.append({"tool_name": b.get("name") or "", "tool_input": b.get("input") or {}})
    return fora


def alvos(d):
    """(name, write) for each memory that THIS touch really opened."""
    nome = d["tool_name"]
    ent = d["tool_input"]
    if nome in _TOOL_ARQ:
        m = _PATH.search(str(ent.get("file_path") or ""))
        return [(m.group(1), nome != "Read")] if m else []
    if nome != "Bash":
        return []
    cmd = str(ent.get("command") or "")
    fora = []
    for seg in _sem_heredoc(cmd):
        for m in _PATH.finditer(seg):
            # the write belongs to the SEGMENT -- `cat a.md && sed -i b.md` reads a and writes b
            fora.append((m.group(1), e_escrita({"tool_name": "Bash", "tool_input": {"command": seg}})))
    # `cd <memory dir> && cat <bare name>` -- the path is gone, the read still exists
    if _DIR.search(cmd):
        vistos = {n for n, _ in fora}
        for seg in _sem_heredoc(cmd):
            for m in _NU.finditer(seg):
                n = m.group(1)
                if n != "MEMORY" and n not in vistos and (MEMORIA / (n + ".md")).is_file():
                    fora.append((n, e_escrita({"tool_name": "Bash", "tool_input": {"command": seg}})))
                    vistos.add(n)
    return fora


def varre(raiz=PROJETOS):
    leitura, escrita = defaultdict(int), defaultdict(int)
    sessoes, ultimo = defaultdict(set), {}
    n_linhas = n_ilegiveis = n_arq = 0
    for jl in sorted(raiz.glob("*/*.jsonl")):
        n_arq += 1
        sid = jl.stem
        ts = datetime.fromtimestamp(jl.stat().st_mtime, timezone.utc).date().isoformat()
        for linha in jl.open(errors="replace"):
            n_linhas += 1
            ts_use = toques(linha)
            if ts_use is None:
                n_ilegiveis += 1
                continue
            for d in ts_use:
                for nome, escreveu in alvos(d):
                    if escreveu:
                        escrita[nome] += 1
                    else:
                        leitura[nome] += 1
                        sessoes[nome].add(sid)
                        ultimo[nome] = max(ultimo.get(nome, ""), ts)
    return dict(leitura=dict(leitura), escrita=dict(escrita),
                sessoes={k: len(v) for k, v in sessoes.items()}, ultimo=ultimo,
                _pop=dict(arquivos=n_arq, linhas=n_linhas, ilegiveis=n_ilegiveis))


def relatorio(dados, so_nunca=False):
    v = vivas()
    if not v:   # empty store: say so, never divide by a zero population
        return (f"RECALL · no memory yet in {MEMORIA} -- nothing to measure "
                f"({dados['_pop']['arquivos']} transcript(s) scanned)")
    lei, ses, ult = dados["leitura"], dados["sessoes"], dados["ultimo"]
    lidas = {k for k in lei if k in v}
    nunca = sorted(v - lidas)
    hist = sorted((k for k in lei if k not in v), key=lambda k: -lei[k])
    p = dados["_pop"]
    out = []
    out.append(f"HORIZON · {p['arquivos']} transcripts, {p['linhas']:,} lines, "
               f"{p['ilegiveis']} unreadable · live store: {len(v)}")
    if p["ilegiveis"]:
        out.append(f"⚠️  {p['ilegiveis']} unreadable lines -- the number below is a FLOOR, not a total")
    out.append("")
    out.append(f"RECALL · {len(lidas)} of {len(v)} live memories were opened at least once "
               f"({100*len(lidas)/len(v):.0f}%) · {len(nunca)} NEVER")
    if hist:
        out.append(f"HISTORICAL · {len(hist)} names read that no longer exist in the store "
                   f"(top: {hist[0]} ×{lei[hist[0]]})")
    if so_nunca:
        out.append("")
        out.append("-- never opened --")
        out += [f"  {n}" for n in nunca]
        return "\n".join(out)
    out.append("")
    out.append("-- most opened (live) --")
    for k in sorted(lidas, key=lambda k: -lei[k])[:15]:
        out.append(f"  {lei[k]:4d}× in {ses[k]:3d} sessions · last {ult[k]} · {k}")
    out.append("")
    out.append(f"-- never opened: {len(nunca)} --")
    for n in nunca[:20]:
        out.append(f"  {n}")
    if len(nunca) > 20:
        out.append(f"  ... and {len(nunca)-20} more (use --nunca)")
    return "\n".join(out)


# --------------------------- selftest ---------------------------
def _t(ok, nome, falhas, precisa=None):
    """One assertion. `precisa` names a population the case needs and this store does not have
    (a fresh install has no memories and no transcripts): the case is SKIPPED and counted apart --
    never green, because a case that did not run proves nothing."""
    _t.n += 1
    if precisa:
        _t.pulados += 1
        print("  - skipped: needs " + precisa + " · " + nome)
        return
    print(("  ✓ " if ok else "  ✗ ") + nome)
    if not ok:
        falhas.append(nome)


def selftest():
    f = []
    _t.n = _t.pulados = 0
    # populations the field cases need; when absent, those cases are skipped, not failed
    _perfil = (MEMORIA / "user_profile.md").is_file()
    _sem_perfil = None if _perfil else "user_profile.md in " + str(MEMORIA)
    def toque(name, **inp):
        return {"tool_name": name, "tool_input": inp}
    m = "~/.claude/" + _SUFIXO      # the memory folder as a command spells it

    # POSITIVE CONTROL -- what HAS to light up
    _t(alvos(toque("Read", file_path=str(MEMORIA / "user_profile.md"))) == [("user_profile", False)],
       "positive · Read of the file is recall", f)
    _t(alvos(toque("Bash", command=f"cat {m}/user_profile.md")) == [("user_profile", False)],
       "positive · cat of the file is recall", f)
    # NEGATIVE CONTROL -- what must NOT light up
    _t(alvos(toque("Bash", command=f"ls {m}/")) == [],
       "negative · ls of the directory is NOT recall", f)
    _t(alvos(toque("Bash", command=f"wc -c {m}/*.md")) == [],
       "negative · glob *.md is NOT recall", f)
    _t(alvos(toque("Bash", command=f"grep -c x {HC.REPO}/docs/MEMORIA.md")) == [],
       "negative · a doc outside memory/ does NOT count", f)
    _t(alvos(toque("Grep", pattern="x", path=str(MEMORIA))) == [],
       "negative · a tool without file_path does NOT count", f)
    # a write is not recall
    _t(alvos(toque("Write", file_path=str(MEMORIA / "user_profile.md"))) == [("user_profile", True)],
       "write · Write counts as a write, not a read", f)
    _t(alvos(toque("Bash", command=f"sed -i s/a/b/ {m}/user_profile.md")) == [("user_profile", True)],
       "write · sed -i counts as a write", f)
    # the gatilho.py finding: a write in one segment does not contaminate the read in another
    r = alvos(toque("Bash", command=f"cat {m}/a_um.md && sed -i s/x/y/ {m}/b_dois.md"))
    _t(r == [("a_um", False), ("b_dois", True)], "per-segment · reads one and writes another in the same command", f)
    # THE TWO MEASURED DEFECTS -- each with its own assertion
    her = "cat > docs/gatilhos/memoria.md <<'MDEOF'\n| MEM-1 | open `memory/user_profile.md` first |\nMDEOF"
    _t(alvos(toque("Bash", command=her)) == [],
       "defect 1 · a path cited INSIDE a heredoc is content, not a read", f)
    #   The bare-name read is confirmed against the DISK (`is_file()`), so this positive case needs
    # the file to exist; the negatives below do not.
    _t(alvos(toque("Bash", command=f"cd {m} && cat user_profile.md")) == [("user_profile", False)],
       "defect 2 · `cd` into the directory + bare name IS a read", f, _sem_perfil)
    _t(alvos(toque("Bash", command=f"cd {m} && ls")) == [],
       "defect 2 · negative · `cd` without citing a file is still not recall", f)
    _t(alvos(toque("Bash", command="cd /tmp && cat user_profile.md")) == [],
       "defect 2 · negative · a bare name OUTSIDE the memory directory does not count", f)
    _t(alvos(toque("Bash", command=f"cd {m} && cat MEMORY.md")) == [],
       "defect 2 · negative · the INDEX is not a memory recall", f)
    # tool_result never gets in
    _t(toques(json.dumps({"message": {"content": [
        {"type": "tool_result", "content": "memory/user_profile.md"}]}})) == [],
       "negative · tool_result is ignored", f)
    # an unreadable line is reported, not dropped silently
    _t(toques("{this is not json") is None, "defect · an unreadable line returns None (not [])", f)
    # the source exists
    #   A MISSING folder is an absent population (skipped, and the path is printed so a wrong path is
    # visible); an EXISTING folder with no memory is what this control exists to catch.
    _t(len(vivas()) > 0, "absence control · the memory store is not empty", f,
       None if MEMORIA.is_dir() else "the memory folder " + str(MEMORIA) + " (absent)")
    # FIELD positive control: running on the real base, the top has to exist
    d = varre()
    _sem_tr = None if d["_pop"]["arquivos"] else "session transcripts under " + str(PROJETOS)
    _t(d["_pop"]["arquivos"] > 0, "field · found transcripts", f, _sem_tr)
    _t(sum(d["leitura"].values()) > 0, "field · found at least one real recall", f, _sem_tr)
    #   Over zero recalls `all()` is True by construction -- that is a skip, not a pass.
    _t(all(re.fullmatch(r"[a-z_0-9]+", k) for k in d["leitura"]), "field · every extracted name is a valid slug", f,
       None if d["leitura"] else "at least one recall in the transcripts")
    print(f"== {_t.n - _t.pulados - len(f)} ok · {len(f)} failure(s) · {_t.pulados} skipped (of {_t.n}) ==")
    return 1 if f else 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    dados = varre()
    if "--json" in sys.argv:
        print(json.dumps(dados, ensure_ascii=False, indent=1, default=str))
    else:
        print(relatorio(dados, so_nunca="--nunca" in sys.argv))
