#!/usr/bin/env python3
"""contexto-consumo.py — WHERE what fills the window comes from, and what was BILLED.

Born to answer "what is bloating me?". It corrected a wrong number (see --selftest, defect D1):
measuring the `toolUseResult` field measures the LOCAL RECORD (2.7x bigger), not what reaches the
window. What reaches the window is `content`.

RULE: the window is paid on EVERY request. Cost of an item = size x remaining requests.
That is why FIXED overhead (enters at the opening, never leaves) is the most expensive per byte.

  --fontes [N]   where the volume comes from, over the N most recent sessions
  --cobrado [N]  tokens actually billed (real usage) per session
  --ranking      the most expensive sessions on disk
  --cauda        the tail of large results, classified by purpose
  --prova-corte [--base CHARS] [--prefixos P1,P2]
                 did a cut of the skill listing take? (only a NEW session answers)
                 --base      listing size before the cut, in chars (env CORTE_BASE). Default:
                             the OLDEST listing among the 20 most recent sessions of YOUR store,
                             so keep one session from before the cut in that window, or pass it.
                 --prefixos  comma-separated name prefixes of the entries you removed, e.g. the
                             skills of one plugin (env CORTE_PREFIXOS). Default: none -- the
                             verdict then rests on the size delta alone.
  --selftest     positive/negative controls (injected defects)
"""
import json, os, sys, glob, re, statistics
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hipo_config as HC

DIR = HC.PROJECT_DIR

def linhas(a):
    try:
        with open(a, errors="replace") as fh:
            for l in fh: yield l
    except OSError: return

def conteudo_attach(at):
    r"""The REAL content that enters the window.

    ⚠️ `nested_memory` carries a dict {path, type, content} — serializing the dict and measuring
    the JSON inflates ~4x (each \n becomes 2 chars, each accent becomes \uXXXX). That is how a
    "CLAUDE.md = 9.4% of the cost" got published when the real figure was 4.6%. Always measure the
    inner field."""
    c = at.get("content")
    if isinstance(c, dict):
        c = c.get("content", "")
    if isinstance(c, list):
        c = " ".join(str(x.get("content") or x.get("text", "")) if isinstance(x, dict) else str(x) for x in c)
    if isinstance(c, str) and c:
        return c
    alt = at.get("systemPrompt") or at.get("skills") or at.get("tools") or at.get("agents") or ""
    return alt if isinstance(alt, str) else json.dumps(alt, ensure_ascii=False)

def txt_result(x):
    """What REACHES the window. NEVER use d['toolUseResult'] here (defect D1)."""
    cc = x.get("content")
    if isinstance(cc, str): return cc
    if isinstance(cc, list): return " ".join(y.get("text","") for y in cc if isinstance(y, dict))
    return ""

def sessoes(n=None):
    a = sorted(glob.glob(os.path.join(DIR, "*.jsonl")), key=os.path.getmtime, reverse=True)
    return a[:n] if n else a

def subagentes(sid):
    """A subagent does NOT live in the parent's .jsonl: it lives in <sid>/subagents/agent-*.jsonl.
    Scanning only the top-level `*.jsonl` loses 15.7% of the cost (measured)."""
    return glob.glob(os.path.join(DIR, sid, "subagents", "*.jsonl"))

ABERTURA = {"prompt_snapshot","skill_listing","instructions","deferred_tools_record",
            "deferred_tools_delta","agent_listing_delta","mcp_instructions_delta",
            "session_context","model","date","auto_mode","command_permissions"}

def fontes(n):
    por = defaultdict(int); cnt = defaultdict(int); total = 0; nres = 0
    arqs = sessoes(n)
    for a in arqs:
        tm = {}
        for line in linhas(a):
            try: d = json.loads(line)
            except Exception: continue
            t = d.get("type")
            if t == "attachment":
                at = d.get("attachment") or {}
                ty = at.get("type","?")
                rot = ("ABERTURA/" if ty in ABERTURA else "") + ty
                if ty.startswith("hook"): rot += "/" + str(at.get("hookName"))
                c = len(conteudo_attach(at)); total += c
                por[rot] += c; cnt[rot] += 1
            elif t == "assistant":
                for x in (d.get("message") or {}).get("content") or []:
                    if isinstance(x, dict):
                        if x.get("type") == "tool_use": tm[x.get("id")] = x.get("name")
                        v = len(x.get("text","") or x.get("thinking","") or "")
                        total += v; por["assistant writing"] += v
                cnt["assistant writing"] += 1
            elif t == "user":
                c = (d.get("message") or {}).get("content")
                if isinstance(c, str):
                    total += len(c); por["user turn"] += len(c); cnt["user turn"] += 1
                elif isinstance(c, list):
                    for x in c:
                        if not isinstance(x, dict): continue
                        if x.get("type") == "tool_result":
                            s = txt_result(x); total += len(s); nres += 1
                            por["output: " + str(tm.get(x.get("tool_use_id"),"?"))] += len(s)
                            cnt["output: " + str(tm.get(x.get("tool_use_id"),"?"))] += 1
                        elif x.get("type") == "text":
                            total += len(x.get("text","")); por["user turn"] += len(x.get("text","")); cnt["user turn"] += 1
    print(f"POPULATION: {len(arqs)} transcripts · {total/1e6:.1f}M chars · {nres} results")
    for k, v in sorted(por.items(), key=lambda x: -x[1])[:22]:
        print(f"  {100*v/max(total,1):6.2f}%  {v/1e6:7.2f}M  n={cnt[k]:<6} {k}")
    return total

def usage_de(a):
    reqs = 0; tin = 0; jan = []
    for line in linhas(a):
        if '"usage"' not in line: continue
        try: d = json.loads(line)
        except Exception: continue
        if d.get("type") != "assistant": continue
        u = (d.get("message") or {}).get("usage") or {}
        v = u.get("input_tokens",0)+u.get("cache_read_input_tokens",0)+u.get("cache_creation_input_tokens",0)
        if v: reqs += 1; tin += v; jan.append(v)
    return reqs, tin, jan

def ranking(n=15):
    res = []
    for a in sessoes():
        sid = os.path.basename(a)[:-6]
        rp, cp, jp = usage_de(a)
        rs = cs = ns = 0
        for sub in subagentes(sid):
            r, t, _ = usage_de(sub)
            if t: ns += 1; rs += r; cs += t
        if cp + cs:
            res.append((cp+cs, cp, cs, rp, rs, ns, statistics.median(jp) if jp else 0, sid[:8]))
    res.sort(reverse=True)
    if not res:   # empty store: say so, never divide by a zero total
        print(f"POPULATION: 0 sessions with usage in {DIR} -- no transcript yet, nothing to rank")
        return
    tot = sum(x[0] for x in res)
    tot_sub = sum(x[2] for x in res)
    print(f"POPULATION: {len(res)} sessions · {tot/1e9:.2f}B input tokens "
          f"(subagents: {tot_sub/1e9:.2f}B = {100*tot_sub/max(tot,1):.1f}%)")
    print(f"{'total':>9} {'%':>5} {'parent':>9} {'subs':>9} {'reqs':>7} {'n subs':>7}  session")
    for t, cp, cs, rp, rs, ns, m, sid in res[:n]:
        print(f"{t/1e6:>8.0f}M {100*t/tot:>4.1f}% {cp/1e6:>8.0f}M {cs/1e6:>8.0f}M {rp:>7} {ns:>7}  {sid}")
    com = [x for x in res if x[2] > 0]
    if com:
        print(f"\nwith subagent: {len(com)} of {len(res)} sessions · {100*sum(x[0] for x in com)/tot:.1f}% of the cost"
              f" · inside them the subagent is {100*sum(x[2] for x in com)/sum(x[0] for x in com):.1f}%")
    longas = [x for x in res if x[3] > 500]
    print(f">500 requests in the parent: {len(longas)} of {len(res)} = {100*sum(x[0] for x in longas)/tot:.1f}% of the cost")

BUSCA_CEGA = re.compile(r'\b(journalctl|access_log|dmesg|tail -f|gdb|bt full|core\.|\.log\b|crash)', re.I)
RECORTE    = re.compile(r'\b(grep -c|wc -l|\| *head|\| *tail|awk|jq |uniq -c|SELECT COUNT)', re.I)

def cauda(thresh=20000, top=10):
    custos = sorted(((usage_de(a)[1], a) for a in sessoes()), reverse=True)[:top]
    alvo = [a for _, a in custos]
    cls = defaultdict(lambda: [0,0]); nres = 0; ch_tot = 0
    for a in alvo:
        tm = {}
        for line in linhas(a):
            try: d = json.loads(line)
            except Exception: continue
            if d.get("type") == "assistant":
                for x in (d.get("message") or {}).get("content") or []:
                    if isinstance(x, dict) and x.get("type") == "tool_use":
                        tm[x.get("id")] = (x.get("name"), x.get("input") or {})
            elif d.get("type") == "user":
                for x in (d.get("message") or {}).get("content") or []:
                    if not isinstance(x, dict) or x.get("type") != "tool_result": continue
                    s = txt_result(x); nres += 1; ch_tot += len(s)
                    if len(s) < thresh: continue
                    nome, inp = tm.get(x.get("tool_use_id"), ("?", {}))
                    cmd = str(inp.get("command") or inp.get("file_path") or "")
                    k = (f"[{nome}]" if nome != "Bash" else
                         "blind search (log/crash) LEGITIMATE" if BUSCA_CEGA.search(cmd) else
                         "defined question WITH a cut" if RECORTE.search(cmd) else
                         "defined question WITHOUT a cut = FAT")
                    cls[k][0] += 1; cls[k][1] += len(s)
    soma = sum(v[1] for v in cls.values())
    print(f"POPULATION: {len(alvo)} most expensive sessions · {nres} results · {ch_tot/1e6:.1f}M chars")
    print(f"TAIL >={thresh}: {sum(v[0] for v in cls.values())} results = {100*soma/max(ch_tot,1):.1f}% of the volume")
    for k, (n, b) in sorted(cls.items(), key=lambda x: -x[1][1]):
        print(f"  {b/1e6:>6.2f}M {100*b/max(soma,1):>5.1f}%  n={n:<4} {k}")

def selftest():
    """Injected defects. Each one MUST be caught."""
    ok = 0; n = 0; pulados = 0
    # D1 (the real defect): measuring the local record instead of what is delivered
    n += 1
    x = {"type":"tool_result","content":"12345"}
    d_local = {"toolUseResult":"1"*500, "message":{"content":[x]}}
    if len(txt_result(x)) == 5 and len(txt_result(x)) != len(d_local["toolUseResult"]):
        ok += 1; print("  OK  D1 local record (toolUseResult) does NOT count as window")
    else: print("  FAILED D1")
    # D2: an attachment with content=None must fall back to the alternative field, not become zero
    n += 1
    if len(conteudo_attach({"type":"prompt_snapshot","content":None,"systemPrompt":["abc"]})) > 3:
        ok += 1; print("  OK  D2 attachment without 'content' is measured by the alternative field")
    else: print("  FAILED D2 (hook/system prompt would vanish from the count)")
    # D3 NEGATIVE control: a command with a cut must NOT be classified as fat
    n += 1
    pos = bool(RECORTE.search("grep -c foo x.txt | head -5"))          # has a cut   -> matches
    neg = bool(RECORTE.search("cat /srv/work/repo/CLAUDE.md"))          # no cut      -> does NOT match
    neg2 = bool(BUSCA_CEGA.search("ls -la /etc"))                       # not a log   -> does NOT match
    if pos and not neg and not neg2:
        ok += 1; print("  OK  D3 predicate matches a cut (+) and refuses raw cat (-) and ls (-)")
    else: print(f"  FAILED D3 (pos={pos} neg={neg} neg2={neg2}) — a wide predicate finds anywhere")
    # D4: a subagent lives in <sid>/subagents/, outside the top-level glob
    #   It needs REAL subagent transcripts. A store that never ran a subagent (a fresh install) has
    # none, and zero is not a failure of the code -- it is an absent population. So it is SKIPPED and
    # counted apart, never green: "skipped" says out loud that the case did not run.
    n += 1
    topo = set(glob.glob(os.path.join(DIR, "*.jsonl")))
    subs = glob.glob(os.path.join(DIR, "*", "subagents", "*.jsonl"))
    if subs and not (set(subs) & topo):
        print(f"  OK  D4 sees {len(subs)} subagent transcript(s), which the top-level glob does NOT catch")
        ok += 1
    elif not subs:
        pulados += 1
        print(f"  SKIP D4 — skipped: needs subagent transcripts in {DIR}/<session>/subagents/ "
              "(none found: either there are none yet, or the path is wrong)")
    else: print("  FAILED D4")
    n += 1
    real = "line1\nline2 with accents üñß\n" * 40
    inflado = len(json.dumps({"path": "/x", "type": "Project", "content": real}, ensure_ascii=False))
    medido = len(conteudo_attach({"type": "nested_memory",
                                  "content": {"path": "/x", "type": "Project", "content": real}}))
    if medido == len(real) and medido < inflado:
        ok += 1; print(f"  OK  D5 nested_memory measured by the inner field ({medido}), not by the dict ({inflado})")
    else:
        print(f"  FAILED D5 — measured {medido}, expected {len(real)}; the serialized dict inflates to {inflado}")
    print(f"\n{ok} of {n - pulados} assertions ({pulados} skipped)")
    return 0 if ok == n - pulados else 1

def prova_corte(base=None, prefixos=None):
    """Did the cut of the skill listing take? Only a NEW session answers: the listing enters at the opening.

    The baseline and the prefixes belong to the READER's store, never to the one this was born on:
    `base` (chars of the listing before the cut) defaults to the OLDEST listing found; `prefixos`
    (name prefixes of the removed entries) defaults to none."""
    import datetime
    achados = []
    pref = [x for x in (prefixos or []) if x]
    rx_pref = (re.compile(r'^\s*-\s*(' + "|".join(re.escape(x) for x in pref) + ')', re.M)
               if pref else None)
    for a in sessoes(20):
        for line in linhas(a):
            if '"skill_listing"' not in line: continue
            try: d = json.loads(line)
            except Exception: continue
            at = d.get("attachment") or {}
            if at.get("type") != "skill_listing": continue
            c = conteudo_attach(at)
            pm = len(rx_pref.findall(c)) if rx_pref else 0
            achados.append((d.get("timestamp",""), os.path.basename(a)[:8], len(c), pm))
    achados.sort(reverse=True)
    if not achados:
        print("ZERO listings found — the instrument found nothing, this proves nothing"); return 2
    rot = ("/".join(pref) if pref else "(no prefix)")[:12]
    print(f"{'when (UTC)':21} {'session':9} {'chars':>7} {rot:>12}")
    for ts, sid, n, pm in achados[:6]:
        print(f"{ts[:19]:21} {sid:9} {n:>7} {pm if pref else '-':>12}")
    ts, sid, n, pm = achados[0]
    if base is None:
        # the reader's own baseline: the OLDEST listing of the window, before the cut if one is there
        _, bsid, BASE_CHARS, BASE_PM = achados[-1]
        if len(achados) < 2:
            print("\nONE listing only -- no baseline to compare against; pass --base CHARS "
                  "(the listing size before the cut)")
            return 2
        print(f"\nbaseline: the oldest listing in the window ({bsid}, {BASE_CHARS} chars) -- "
              "pass --base to fix it")
    else:
        BASE_CHARS, BASE_PM = base, None
    delta = BASE_CHARS - n
    print()
    if delta <= 0:
        print(f"DID NOT TAKE: the most recent listing ({sid}, {ts[:19]}) has {n} chars — nothing left.")
        return 1
    # verdict by DELTA, not by absolute zero: a plugin still enabled is a PARTIAL cut, not a failure
    if not pref:
        estado = "by size only (no --prefixos: the removed entries were not counted)"
    else:
        estado = "COMPLETE" if pm == 0 else f"PARTIAL ({pm} entry(ies) of a plugin still enabled)"
    print(f"TOOK / {estado} · session {sid} ({ts[:19]})")
    print(f"  listing: {BASE_CHARS} -> {n} chars  ({-100*delta/BASE_CHARS:+.1f}%)")
    if pref:
        print(f"  {'/'.join(pref)} entries: {'?' if BASE_PM is None else BASE_PM} -> {pm}")
    print(f"  measured gain: ~{delta/3.6:.0f} tokens PER REQUEST")
    return 0

if __name__ == "__main__":
    a = sys.argv[1] if len(sys.argv) > 1 else "--fontes"
    if a == "--prova-corte":
        def _opt(flag, env):
            v = os.environ.get(env)
            if flag in sys.argv[2:]:
                i = sys.argv.index(flag)
                v = sys.argv[i + 1] if i + 1 < len(sys.argv) else None
            return v
        _b = _opt("--base", "CORTE_BASE")
        _p = _opt("--prefixos", "CORTE_PREFIXOS")
        sys.exit(prova_corte(int(_b) if _b else None, _p.split(",") if _p else None))
    arg = int(sys.argv[2]) if len(sys.argv) > 2 else None
    if a == "--selftest": sys.exit(selftest())
    elif a == "--cobrado" or a == "--ranking": ranking(arg or 15)
    elif a == "--cauda": cauda(top=arg or 10)
    else: fontes(arg or 30)
