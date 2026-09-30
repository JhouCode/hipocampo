#!/usr/bin/env python3
"""BATON · what the compaction hook DELIVERS — simulated with the runtime's rule and measured in the TRANSCRIPT.

WHY IT EXISTS: the `SessionStart:compact` hook used to `cat` `docs/mesa/BASTAO.md` (~100 KB). Above
10,000 units the runtime persists the output to disk and puts only a PREVIEW in the context. The fixed
head of the baton (2,130 B) filled the whole preview: in 0 of 72 persisted deliveries (deduplicated by
uuid) did live state get in. The head moved to `docs/mesa/BASTAO_REGRAS.md` and the top of the baton
kept 1 pointer line.

THIS IS THE ONLY COPY OF THE EMULATION: the baton guard delegates to `--guarda` here, and the DELIVERY
proof reads the transcript with the same functions.

THE RUNTIME RULE, measured: the preview is the first 2,000 UTF-16 units (JS `.length`), pulled
back to the last `\\n` when it falls after unit 1,000. It is not a fixed 2,070 B:
2,070 is the median in bytes, counting the 3 B of the `...` the runtime appends. The persist threshold
was measured in transcripts: a text output of 9,586 units arrived whole, one of 10,057 became a preview.
`--validar` checks the emulation against ALL real previews: if the runtime changes the rule, that is
where it lights up. See docs/CONTEXTO.md.

LIVE STATE: the `*Updated:` line and at least 1 entry (`- `) starting after it, inside what was
delivered. The approved shape adds: at most 1 non-empty line (the pointer) before `*Updated:`.

The `--guarda` starts from the HOOK, not from the path. It reads the `SessionStart` that matches
`compact` in the repository's hooks registration (`settings.example.json` at the root, or the file
named by $BASTAO_SETTINGS, relative to the repo being judged), simulates each `cat` of 1 versioned
file (or the cut of this script) and judges what the runtime would deliver. The placeholder
`<YOUR_FOLDER>` in the commands stands for the root of the repo being judged. An emitter it cannot
simulate (script, pipe) does not count as a delivery: if none is left, it is SEM_EMISSOR (red). The
`PostCompact` does not count: it only rides along on the echo of a manual `/compact`, and automatic
compaction has no echo (see docs/CONTEXTO.md).

What it does NOT read: `…/subagents/` and `tasks/*.output`.

usage: bastao-entrega.py [--desde ISO|commit] [--mostrar]   · real deliveries, and those of the period
       bastao-entrega.py --validar                          · the preview emulation against real previews
       bastao-entrega.py --guarda staged|tree               · the guard verdict (1st line = code)
       bastao-entrega.py --emitir <BASTAO.md>               · the SessionStart:compact HOOK: the cut
       bastao-entrega.py --selftest
  rc 0: every delivery of the period has live state · 1: some does not (or --validar diverged)
  rc 2: no delivery in the period — the delivery proof stays PENDING until the next compaction
"""
import datetime as dt
import glob
import json
import os
import re
import shlex
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hipo_config as HC

RAIZ = os.path.dirname(HC.PROJECT_DIR)
REPO = HC.REPO
LIMIAR, PREVIA = 10000, 2000
MARCA_PREVIA = "Preview (first 2KB):\n"
FONTE = os.environ.get("BASTAO_SETTINGS", "settings.example.json")
PLACEHOLDER = "<YOUR_FOLDER>"


def u16(s):
    return len(s.encode("utf-16-le")) // 2


def previa(s, r=PREVIA):
    """The runtime's preview: the first r UTF-16 units, pulled back to the last \\n if it is past half."""
    if u16(s) <= r:
        return s
    acc, k = 0, len(s)
    for i, ch in enumerate(s):
        w = 2 if ord(ch) > 0xFFFF else 1
        if acc + w > r:
            k = i
            break
        acc += w
    corte = s[:k]
    j = corte.rfind("\n")
    return s[:j] if j >= 0 and u16(corte[:j]) > r * 0.5 else corte


def entregue(s):
    """What the runtime puts in the context for a text hook output: whole, or the preview."""
    return previa(s) if u16(s) > LIMIAR else s


# ── the cut that SessionStart:compact emits ───────────────────────────────────────────────────────
# On AUTOMATIC compaction only SessionStart:compact arrives, cut at the preview; the manual /compact
# receives the whole baton riding along on the PostCompact echo. The cut fits WHOLE under the
# threshold: the *Updated line, the newest entries (each up to CORTE units) and the footer sections
# (## WAITING ON THE USER…) whole, up to half the ceiling. What did not fit is named at the end, with
# the path of the file.
TETO, CORTE = 9500, 600
MARCA_CORTE = " …✂"


def _corta(s, n):
    if u16(s) <= n:
        return s
    acc, k = 0, len(s)
    for i, ch in enumerate(s):
        w = 2 if ord(ch) > 0xFFFF else 1
        if acc + w > n - u16(MARCA_CORTE):
            k = i
            break
        acc += w
    return s[:k].rstrip() + MARCA_CORTE


def recorte(txt, teto=None, corte=CORTE, caminho="docs/mesa/BASTAO.md"):
    """The text the hook delivers at compaction: always <= teto units. Without *Updated it returns the
    whole text (the guard flags it by the live state, not the cut for hiding it)."""
    teto = TETO if teto is None else teto
    L = txt.split("\n")
    ia = next((i for i, l in enumerate(L) if l.startswith("*Updated:")), None)
    if ia is None:
        return txt
    isec = next((i for i in range(ia + 1, len(L)) if L[i].startswith("## ")), len(L))
    entradas = []
    for l in L[ia + 1:isec]:
        if l.startswith("- "):
            entradas.append([l])
        elif entradas and l.strip():
            entradas[-1].append(l)
    entradas = [_corta("\n".join(e), corte) for e in entradas]
    secoes = "\n".join(L[isec:]).strip()
    cabeca = "\n".join(L[:ia + 1])

    def monta(k, sec):
        fora = len(entradas) - k
        nota = (f"> compaction cut: the {k} newest entries, each up to {corte} characters, and the whole"
                f" footer; the whole baton is `{caminho}`")
        corpo = [cabeca, nota, ""] + entradas[:k] + ([""] + [sec] if sec else [])
        if fora:
            corpo += ["", f"> outside this cut: {fora} older entry(ies) — `{caminho}`"]
        return "\n".join(corpo) + "\n"

    # the footer takes at most half the ceiling: the entries are the live state and never lose their place
    sec = secoes if u16(secoes) <= teto // 2 else _corta(secoes, teto // 2)
    k = 0
    while k < len(entradas) and u16(monta(k + 1, sec)) <= teto:
        k += 1
    out = monta(k, sec)
    # the head (pointer and *Updated) has no ceiling of its own: the cut never passes the ceiling, and if
    # the cut eats the live state, the guard flags it by the state
    return out if u16(out) <= teto else _corta(out, teto - 1) + "\n"


def estado_vivo(texto):
    """(has the *Updated: line, number of '- ' entries starting after it) in the DELIVERED text.
    Counts only up to the 1st '## ': the footer lines (## WAITING ON THE USER…) are not entries, and the
    footer enters the cut whole — counting them would make a cut with 0 entries green."""
    linhas = texto.split("\n")
    ia = next((i for i, l in enumerate(linhas) if l.startswith("*Updated:")), None)
    if ia is None:
        return False, 0
    fim = next((i for i in range(ia + 1, len(linhas)) if linhas[i].startswith("## ")), len(linhas))
    return True, sum(1 for l in linhas[ia + 1:fim] if l.startswith("- "))


# ── the guard: the hook decides what arrives ──────────────────────────────────────────────────────
def _casa_compact(m):
    if m in (None, "", "*"):
        return True
    try:
        return re.fullmatch(m, "compact") is not None
    except re.error:
        return "compact" in m.split("|")


def julgar(cfg_txt, ler, ls):
    """-> (code, lines). Codes (protocol tokens, kept verbatim): VERDE · AUSENTE · JSON · SEM_EMISSOR · CABECA · SEM_ESTADO."""
    if cfg_txt is None:
        return "AUSENTE", []
    try:
        cfg = json.loads(cfg_txt)
    except ValueError as e:
        return "JSON", [str(e)]
    cmds = [h.get("command", "") for b in ((cfg.get("hooks") or {}).get("SessionStart") or [])
            if _casa_compact(b.get("matcher")) for h in (b.get("hooks") or []) if h.get("type") == "command"]
    sim, nota = [], []
    versionado = lambda p: [t for t in ls if p == t or p.endswith("/" + t)]
    for c in cmds:
        if re.search(r"[|;&<>$`]", c):
            continue
        try:
            tk = shlex.split(c)
        except ValueError:
            continue
        # the 2 emitters the guard can simulate: `cat <file>` and the cut of this script
        if len(tk) == 2 and tk[0] == "cat":
            forma, alvo = "cat", tk[1]
        elif (len(tk) == 4 and tk[0] in ("python3", "python") and tk[2] == "--emitir"
              and "scripts/bastao-entrega.py" in versionado(tk[1])):
            forma, alvo = "cut", tk[3]
        else:
            continue
        cand = versionado(alvo)
        if not cand:
            nota.append(f"`{c}`: the file is not versioned — nothing to simulate")
            continue
        rel = max(cand, key=len)
        txt = ler(rel)
        if txt is None:
            nota.append(f"`{c}`: {rel} does not exist")
            continue
        L = txt.split("\n")
        ia = next((i for i, l in enumerate(L) if l.startswith("*Updated:")), None)
        emitido = recorte(txt, caminho=rel) if forma == "cut" else txt
        ent = entregue(emitido)
        tem, n = estado_vivo(ent)
        sim.append(dict(rel=rel, forma=forma, u=u16(ent), tem=tem, arq=ia is not None, n=n,
                        inteira=ent == emitido,
                        antes=sum(1 for l in L[:ia] if l.strip()) if ia is not None else None,
                        ini=len(("\n".join(L[:ia]) + "\n").encode()) if ia else 0))
    # the cut exists to arrive WHOLE: if it passed the threshold and became a preview, the cut is broken
    furado = [a for a in sim if a["forma"] == "cut" and not a["inteira"]]
    boa = [a for a in sim if a["tem"] and a["n"] >= 1 and a["antes"] is not None and a["antes"] <= 1
           and a not in furado]
    if boa:
        a = boa[0]
        como = "WHOLE delivery" if a["inteira"] else "delivery"
        return "VERDE", [f"`{a['forma']} {a['rel']}` -> {como} of {a['u']} units; live state from byte {a['ini']}"
                         f" ({a['antes']} line before *Updated); {a['n']} entry(ies) start in the delivery"]
    if furado:
        return "SEM_ESTADO", [f"{a['rel']}: the cut passed the threshold of {LIMIAR} units and became a preview"
                                 f" of {a['u']} — the cut ceiling ({TETO}) did not hold" for a in furado]
    if not sim:
        return "SEM_EMISSOR", [f"{len(cmds)} command(s) in the SessionStart that matches compact; none is a `cat`"
                              " of 1 versioned file" " nor the cut of this script"] + nota
    viva = [a for a in sim if a["tem"] and a["n"] >= 1]
    if viva:
        a = viva[0]
        return "CABECA", [f"{a['rel']}: {a['antes']} non-empty lines before *Updated — the approved shape is 1 (the pointer)"]
    out = []
    for a in sim:
        if not a["arq"]:
            out.append(f"{a['rel']}: has no *Updated: line — the hook emits something that is not the live state")
        elif not a["tem"]:
            out.append(f"{a['rel']}: the delivery ({a['u']} units) ends before *Updated, which starts at byte {a['ini']}")
        else:
            out.append(f"{a['rel']}: the delivery ({a['u']} units) carries *Updated and 0 entries")
    return "SEM_ESTADO", out


def guarda(modo):
    """What the guard runner calls, with cwd = the repo root. staged reads the INDEX; tree reads the disk."""
    def ler(rel):
        if modo == "staged":
            r = subprocess.run(["git", "show", ":" + rel], capture_output=True)
            return r.stdout.decode("utf-8", "replace") if r.returncode == 0 else None
        try:
            with open(rel, encoding="utf-8", errors="replace") as f:
                return f.read()
        except OSError:
            return None
    ls = [t for t in subprocess.run(["git", "ls-files", "-z"], capture_output=True).stdout
          .decode("utf-8", "replace").split("\0") if t]
    cfg = ler(FONTE)
    # the example registration writes the repo root as a placeholder: it stands for the repo being judged
    if cfg is not None:
        cfg = cfg.replace(PLACEHOLDER, json.dumps(os.getcwd())[1:-1])
    cod, linhas = julgar(cfg, ler, ls)
    print(cod)
    for l in linhas:
        print(l)
    return 0


# ── the DELIVERY proof: what entered the context, read in the transcript ───────────────────────────
def recebido(content):
    """What entered the context: the preview, without the runtime's wrapper, or the whole content."""
    if not content.startswith("<persisted-output>"):
        return content, False
    i = content.find(MARCA_PREVIA)
    corpo = content[i + len(MARCA_PREVIA):] if i >= 0 else ""
    for fecho in ("\n...\n</persisted-output>", "\n</persisted-output>"):
        if corpo.endswith(fecho):
            return corpo[: -len(fecho)], True
    return corpo, True


def entregas():
    vistos, out = set(), []
    for p in sorted(glob.glob(f"{RAIZ}/*/*.jsonl")):
        try:
            fh = open(p, encoding="utf-8", errors="replace")
        except OSError:
            continue
        with fh:
            for ln in fh:
                if '"hook_success"' not in ln or "BASTAO.md" not in ln:
                    continue
                try:
                    d = json.loads(ln)
                except ValueError:
                    continue
                a = d.get("attachment") or {}
                if a.get("type") != "hook_success" or "BASTAO.md" not in str(a.get("command", "")):
                    continue
                chave = d.get("uuid") or (d.get("timestamp"), p)
                if chave in vistos:
                    continue
                vistos.add(chave)
                txt, persistida = recebido(a.get("content", "") or "")
                tem, n = estado_vivo(txt)
                out.append(dict(ts=d.get("timestamp", ""), arquivo=os.path.basename(p)[:8], hook=a.get("hookName"),
                                persistida=persistida, texto=txt, stdout=str(a.get("stdout", "")),
                                atualizado=tem, entradas=n))
    out.sort(key=lambda e: e["ts"])
    return out


def instante(desde):
    """ISO (with or without timezone) or commit hash -> UTC datetime."""
    if re.fullmatch(r"[0-9a-f]{7,40}", desde):
        r = subprocess.run(["git", "-C", REPO, "show", "-s", "--format=%cI", desde], capture_output=True, text=True)
        if r.returncode != 0:
            sys.exit(f"unknown commit: {desde}")
        desde = r.stdout.strip()
    t = dt.datetime.fromisoformat(desde.replace("Z", "+00:00"))
    return (t if t.tzinfo else t.replace(tzinfo=dt.timezone.utc)).astimezone(dt.timezone.utc)


def relatorio(desde, mostrar):
    es = entregas()
    per = [e for e in es if e["persistida"]]
    inte = [e for e in es if not e["persistida"]]
    vivo = lambda e: e["atualizado"] and e["entradas"] >= 1
    print(f"deliveries of the baton hook (main transcripts, deduplicated by uuid): {len(es)}"
          f" · events {sorted({str(e['hook']) for e in es})}")
    print(f"  persisted (preview): {len(per)} · with live state: {sum(map(vivo, per))} of {len(per)}")
    print(f"  whole: {len(inte)} · with live state: {sum(map(vivo, inte))} of {len(inte)}")
    if desde is None:
        return 0
    t0 = instante(desde)
    per_ = [e for e in es if dt.datetime.fromisoformat(e["ts"].replace("Z", "+00:00")) > t0]
    ok = sum(map(vivo, per_))
    print(f"since {t0.isoformat(timespec='seconds')} (UTC): {len(per_)} delivery(ies) · with live state: {ok} of {len(per_)}")
    for e in per_:
        print(f"  {e['ts']} {e['arquivo']} {e['hook']} persisted={e['persistida']} delivered={u16(e['texto'])} units"
              f" / {len(e['texto'].encode())} B · *Updated={e['atualizado']} · entries that start={e['entradas']}")
    if not per_:
        print("PENDING: no compaction delivered the baton after the requested instant")
        return 2
    if mostrar:
        print("----- what ENTERED the context in the last delivery -----")
        print(per_[-1]["texto"])
        print("----- end -----")
    return 0 if ok == len(per_) else 1


def validar():
    es = [e for e in entregas() if e["persistida"]]
    ruins = [e for e in es if previa(e["stdout"]) != e["texto"]]
    print(f"preview emulation == real preview: {len(es) - len(ruins)} of {len(es)}")
    for e in ruins[:3]:
        print(f"  DIVERGES {e['ts']} {e['arquivo']}: emulated {u16(previa(e['stdout']))} units, real {u16(e['texto'])} units")
    if not es:
        print("no real preview to compare — the validation did not run")
        return 2
    return 0 if not ruins else 1


# ── selftest: positive AND negative controls of each clause ──────────────────────────────────────
def selftest():
    global TETO
    falhas, total = [], []

    def caso(rotulo, cond):
        total.append(rotulo)
        print(("✓ " if cond else "✗ ") + rotulo)
        if not cond:
            falhas.append(rotulo)

    cab = "> rule\n" * 343                                         # 2,401 units of head alone
    vivo = "*Updated: 2026-01-01 (s1)*\n\n- new entry\n\n"
    corpo = "- old entry " + "x" * 12000 + "\n"
    caso("preview: head on top does not carry *Updated", estado_vivo(entregue(cab + vivo + corpo)) == (False, 0))
    caso("preview: pointer on top carries *Updated and the entries", estado_vivo(entregue("# p\n" + vivo + corpo)) == (True, 2))
    caso("preview: pulls back to \\n when it is past half", previa("a" * 1500 + "\n" + "b" * 900) == "a" * 1500)
    caso("preview: hard cut when the \\n is before half", previa("a" * 10 + "\n" + "b" * 3000) == "a" * 10 + "\n" + "b" * 1989)
    caso("preview: an astral character counts 2 units", u16(previa("🏃" * 1500)) == 2000)
    caso("preview: output up to the threshold arrives whole", entregue(cab + vivo) == cab + vivo)
    env = "<persisted-output>\nOutput too large (99KB). Full output saved to: /x\n\n" + MARCA_PREVIA
    caso("transcript: persisted wrapper comes off whole", recebido(env + "abc\n...\n</persisted-output>") == ("abc", True))
    caso("transcript: whole content is not a preview", recebido("*Updated: x*\n- a") == ("*Updated: x*\n- a", False))
    caso("predicate: an entry BEFORE *Updated does not count", estado_vivo("- before\n*Updated: x*\n") == (True, 0))

    def cfg(compact=("cat /repo/docs/mesa/BASTAO.md",), post=()):
        return json.dumps({"hooks": {
            "SessionStart": [{"matcher": "compact", "hooks": [{"type": "command", "command": c} for c in compact]}],
            "PostCompact": [{"hooks": [{"type": "command", "command": c} for c in post]}]}})
    bom = "# pointer -> [rules](BASTAO_REGRAS.md)\n" + vivo + corpo
    arvore = {"docs/mesa/BASTAO.md": bom, "docs/mesa/BASTAO_REGRAS.md": cab}
    ls = list(arvore)
    j = lambda c, a=arvore: julgar(c, a.get, ls)[0]
    caso("guard: positive control (pointer + live state) -> VERDE", j(cfg()) == "VERDE")
    caso("guard: head back on top -> SEM_ESTADO", j(cfg(), {**arvore, "docs/mesa/BASTAO.md": cab + vivo + corpo}) == "SEM_ESTADO")
    caso("guard: hook emits BASTAO_REGRAS.md with the good baton on disk -> SEM_ESTADO",
         j(cfg(("cat /repo/docs/mesa/BASTAO_REGRAS.md",))) == "SEM_ESTADO")
    caso("guard: the cat only in PostCompact -> SEM_EMISSOR", j(cfg((), ("cat /repo/docs/mesa/BASTAO.md",))) == "SEM_EMISSOR")
    caso("guard: emitter by another script -> SEM_EMISSOR", j(cfg(("python3 /repo/scripts/recorte.py",))) == "SEM_EMISSOR")
    caso("guard: 2 lines before *Updated -> CABECA",
         j(cfg(), {**arvore, "docs/mesa/BASTAO.md": "# pointer\n> a rule that came back\n" + vivo + corpo}) == "CABECA")
    # the cut
    ents = "".join(f"- e{i} " + "y" * 900 + "\n  continuation\n\n" for i in range(40))
    rod = "## WAITING ON THE USER\n- p1\n- p2\n\n## STATE OF THE FRONTS\n- f1\n"
    real = "# pointer\n" + vivo.replace("- new entry\n\n", "") + ents + rod
    r = recorte(real)
    caso("cut: fits whole (<= TETO, under the threshold)", u16(r) <= TETO and entregue(r) == r)
    caso("cut: starts with the pointer and *Updated (1 line before)", r.startswith("# pointer\n*Updated:"))
    caso("cut: the newest entries get in, each cut at CORTE",
         "- e0 " in r and "- e1 " in r and all(u16(b) <= CORTE for b in re.split(r"\n(?=- e\d)|\n\n", r) if b.startswith("- e")))
    caso("cut: an entry's continuation goes with it", "- e0 " + "y" * 10 in r and MARCA_CORTE in r)
    caso("cut: the WAITING ON THE USER footer gets in whole", rod.strip() in r)
    caso("cut: names what was left out", "- e39 " not in r and "outside this cut:" in r)
    caso("cut: a small file comes out whole, without 'outside'", "outside this" not in recorte("# p\n" + vivo + rod)
         and "- new entry" in recorte("# p\n" + vivo + rod))
    caso("cut: without *Updated returns the text (the guard flags it)", recorte(cab) == cab)
    caso("cut: the continuation line of a short entry goes whole",
         "- short\n  short continuation" in recorte("# p\n*Updated: x*\n- short\n  short continuation\n"))
    gig = "# p\n*Updated: x*\n- e\n## WAITING ON THE USER\n- z " + "w" * 20000 + "\n"
    rg = recorte(gig)
    caso("cut: a footer above half the ceiling is cut there, and the entry fits",
         MARCA_CORTE in rg and "\n- e\n" in rg and u16(rg) <= TETO // 2 + 400)
    caso("cut: a giant head does not break the ceiling", u16(recorte("# " + "p" * 12000 + "\n" + vivo)) <= TETO)
    caso("cut: the cut counts an astral character as 2", u16(_corta("🏃" * 400, CORTE)) <= CORTE)
    caso("predicate: a footer '- ' (after the 1st ##) is not an entry", estado_vivo("*Updated: x*\n## P\n- p1") == (True, 0))
    arv2 = {**arvore, "docs/mesa/BASTAO.md": "# pointer\n" + vivo + ents + rod, "scripts/bastao-entrega.py": ""}
    emi = "python3 /repo/scripts/bastao-entrega.py --emitir /repo/docs/mesa/BASTAO.md"
    j2 = lambda c, a=arv2: julgar(c, a.get, list(a))[0]
    caso("guard: positive control of the cut -> VERDE", j2(cfg((emi,))) == "VERDE")
    caso("guard: the cut of a file without state -> SEM_ESTADO",
         j2(cfg((emi.replace("BASTAO.md", "BASTAO_REGRAS.md"),))) == "SEM_ESTADO")
    caso("guard: the cut script not versioned -> SEM_EMISSOR",
         j2(cfg((emi,)), {k: v for k, v in arv2.items() if not k.startswith("scripts/")}) == "SEM_EMISSOR")
    caso("guard: a giant footer does not push the entries out -> VERDE", j2(cfg((emi,)), {**arv2, "docs/mesa/BASTAO.md": gig}) == "VERDE")
    caso("guard: no entries, only the footer with '- ' -> SEM_ESTADO",
         j2(cfg((emi,)), {**arv2, "docs/mesa/BASTAO.md": "# p\n*Updated: x*\n" + rod}) == "SEM_ESTADO")
    caso("guard: the right script with the wrong flag -> SEM_EMISSOR", j2(cfg((emi.replace("--emitir", "--guarda"),))) == "SEM_EMISSOR")
    t0, TETO = TETO, 12000
    try:
        caso("guard: ceiling above the threshold -> the cut becomes a preview -> SEM_ESTADO", j2(cfg((emi,))) == "SEM_ESTADO")
    finally:
        TETO = t0
    caso("guard: no settings -> AUSENTE", j(None) == "AUSENTE")
    caso("guard: broken settings -> JSON", j("{") == "JSON")
    print(f"selftest: {len(total) - len(falhas)} of {len(total)}")
    return 1 if falhas else 0


def emitir(caminho):
    """The hook. Any failure of the cut falls back to the whole file: the hook never emits less than a plain `cat`."""
    try:
        with open(caminho, encoding="utf-8", errors="replace") as f:
            txt = f.read()
    except OSError as e:
        print(f"baton: could not read {caminho}: {e}")
        return 0
    try:
        rel = os.path.relpath(os.path.abspath(caminho), REPO)
        sys.stdout.write(recorte(txt, caminho=rel if not rel.startswith("..") else caminho))
    except Exception:
        sys.stdout.write(txt)
    return 0


def main(argv):
    if "--emitir" in argv:
        i = argv.index("--emitir")
        return emitir(argv[i + 1] if i + 1 < len(argv) else os.path.join(REPO, "docs/mesa/BASTAO.md"))
    if "--selftest" in argv:
        return selftest()
    if "--validar" in argv:
        return validar()
    if "--guarda" in argv:
        i = argv.index("--guarda")
        modo = argv[i + 1] if i + 1 < len(argv) else ""
        if modo not in ("staged", "tree"):
            print("usage: --guarda staged|tree", file=sys.stderr)
            return 2
        return guarda(modo)
    desde = argv[argv.index("--desde") + 1] if "--desde" in argv else None
    return relatorio(desde, "--mostrar" in argv)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
