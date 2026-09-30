#!/usr/bin/env python3
"""WHAT COMPACTION TAKES AWAY — measured, not estimated.

WHY THIS EXISTS
  Every compaction cuts 92-99% of the context, and nobody knew WHAT was cut. "What do I lose when
the context overflows?" only had opinions for an answer.
  The transcript keeps a `compact_boundary` entry with `compactMetadata` (`preTokens`,
`postTokens`, `cumulativeDroppedTokens`, `preservedMessages.uuids`) and an `isCompactSummary`
message with the whole summary. So the WHOLE history can be measured, not only the next events.

WHAT IT MEASURES, and the unit matters
  Not "how many tokens fell" — `preTokens - postTokens` already says that and teaches nothing. It
is **how many of the USER's turns survived**, because that is the loss that costs: decisions made
in chat evaporate, and it is always the ones that come **after the main subject** of a long message.
  For every user message before the boundary, it looks for a distinctive signature in the summary:
    LITERAL    preserved byte for byte (`preservedMessages.uuids`)
    CITED      the summary carries a recognizable sentence of it
    EVAPORATED nothing of it reached the other side

⚠️ INHERITED vs OWN BOUNDARY
  A session BORN from a compaction has the boundary in its first lines, and the context that was
cut belongs to ANOTHER session. Measuring "0 turns before" there is correct, not a defect — the
script tells the two apart and only counts the loss of the session that produced it.

⚠️ WHAT "EVAPORATED" DOES NOT MEAN
  It measures the passage through the SUMMARY, not total persistence. A turn that evaporated may be
saved in a doc, a backlog or the memory — then it was not lost, it only left the immediate context.
The number says **how much of what the user said depends on it having been written elsewhere**.

🚨 THE FIRST NUMBER WAS WRONG, AND IT WAS THE WINDOW
  The first measurement said 30.5% evaporation. The window walked by POSITION in the file, and the
transcript **re-emits old boundaries** (one boundary can appear 3 times in one transcript). Turns
of one window were compared against the summary of ANOTHER compaction, and almost everything
"evaporated".
  With the window by TIME and turns deduplicated by uuid, the real measurement over 84 compactions
and 1,286 user turns was: **70.5% CITED · 13.5% evaporated · 0.1% literal.**
  It only showed up because the mechanism ran on a real event: in fixtures boundaries do not repeat.

⚠️ "A WHOLE TURN" IS STILL A COARSE UNIT — the loss that matters most is smaller
  The classification judges a message by its longest sentence. A message with 5 subjects counts as
CITED if the summary carried 1, and the other 4 vanish without a number. Measured: **26.5% of the
segments** of long messages judged preserved did not arrive (430 raw; **115 after filtering** paths,
URLs, pasted machine output and pasted chat logs). See `segmentos_uteis`.
  ⚠️ DECLARED RESIDUE: in a real render, 1 of 6 orphans was still a pasted chat line. Tightening
further starts eating the user's prose — stopped here on purpose.

USAGE
  contexto-medir.py --historico        scans every transcript and measures past compactations
  contexto-medir.py --sessao <id>      one session only
  contexto-medir.py --devolver         returns the swallowed turns to the context (UserPromptSubmit /
                                       SessionStart:compact — plain stdout becomes context)
  contexto-medir.py                    HOOK mode — syncs the ledger with the transcript
"""
import json, os, re, sys, glob
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hipo_config as HC

PROJ = Path(os.environ.get("CLAUDE_PROJ", HC.PROJECT_DIR))
LEDGER = Path(os.environ.get("CONTEXTO_LEDGER", str(PROJ / "contexto-compactacoes.jsonl")))
MIN_ASSINATURA = 28          # chars — below this a sentence matches by chance


def texto_de(msg):
    """Extracts the text of a message, whether a string or a list of blocks."""
    c = (msg or {}).get("content")
    if isinstance(c, str):
        return c
    if isinstance(c, list):
        return " ".join(p.get("text", "") for p in c if isinstance(p, dict) and p.get("type") == "text")
    return ""


def e_fala_do_usuario(d):
    """A REAL user message — not a tool_result, not meta, not a hook injection.

    ⚠️ The transcript calls `user` many things the user did not write: tool results,
    system-reminders, the post-compaction continuation text. Counting all of them as "user turns"
    inflates the population and makes the survival rate look better than it is.
    """
    if d.get("type") != "user" or d.get("isMeta") or d.get("isCompactSummary"):
        return False
    c = (d.get("message") or {}).get("content")
    if isinstance(c, list) and any(isinstance(p, dict) and p.get("type") == "tool_result" for p in c):
        return False
    t = texto_de(d.get("message")).strip()
    if not t or len(t) < 3:
        return False
    if t.startswith(("<", "This session is being continued", "Caveat:")):
        return False
    # ⚠️ SYSTEM markers the transcript records as `user` — not user turns. Without this filter,
    # "[Request interrupted by user]" entered the count and inflated the loss with noise.
    if t.strip() in ("[Request interrupted by user]", "[Request interrupted by user for tool use]"):
        return False
    if t.startswith("[Request interrupted"):
        return False
    return True


def assinatura(txt):
    """The most distinctive sentence of the message — the one searched for in the summary.

    Takes the longest stretch without strong punctuation, ignoring the first words (usually "ok",
    "sure", "go ahead"): what identifies the message is the MIDDLE, not the opening.
    """
    # ⚠️ The longest USEFUL one, not the longest. When the user pastes tool output in the middle
    # of a message, that stretch is often the biggest — the signature became the MACHINE's output,
    # which is naturally not in the summary, and the whole message was flagged as evaporated. The
    # filter that serves the orphans serves here, for the same reason.
    uteis = segmentos_uteis(txt)
    if uteis:
        return max(uteis, key=len)
    limpo = re.sub(r"\s+", " ", txt).strip()
    partes = [p.strip() for p in re.split(r"[.!?;\n]", limpo) if len(p.strip()) >= MIN_ASSINATURA]
    return max(partes, key=len) if partes else (limpo if len(limpo) >= MIN_ASSINATURA else None)


def segmentos_uteis(txt):
    """The pieces of a message worth checking one by one.

    ⚠️ BORN FROM A MEASURED BLIND SPOT. `assinatura` judges the message by its LONGEST stretch: in
    a message with 5 subjects, if the summary carries the biggest, it counts as CITED and the other
    4 vanish without entering any number. That is exactly where what the user decides AFTER the
    main subject lives.
      Measured on 247 messages of 3+ segments judged preserved: **26.5% of the segments (430 raw,
    115 after the filters below) did not reach the summary**, with cases of 2% coverage.
      The filter removes citation noise (path, URL, pasted output): it inflates the count, and
    returning it spends the cap on things that are not decisions.
    """
    limpo = re.sub(r"[ \t]+", " ", txt).strip()
    out = []
    for p in re.split(r"[.!?;\n]", limpo):
        p = p.strip()
        if len(p) < MIN_ASSINATURA or "://" in p or p.startswith(("/", "`/", "![", "|")):
            continue
        if len(re.findall(r"[a-zà-ú]{3,}", p.lower())) < 5:
            continue
        # ⚠️ MACHINE OUTPUT THE USER PASTED BACK. Half of the orphans of the first measurement were
        # tool log lines (`[TAG] by kind: 624 236 …`) pasted in for reading. Returning that spends
        # the cap on the tool's own output — and makes the section look like noise, which teaches
        # the reader to skip it entirely. What matters is what the user OBSERVED.
        if re.match(r"^\[[A-Z0-9_-]{3,}\]", p):
            continue
        # ⚠️ CHAT LOG OF ANOTHER PROGRAM pasted in — `[Name]: [Link]`. It passed every filter (long
        # words, few digits, not a path) and came back in a test with REAL data, filling the cap
        # instead of the user's observation. The signal is bracket density: prose rarely has two.
        if len(re.findall(r"\[[^\]]+\]", p)) >= 2:
            continue
        # ⚠️ AND TWO BRACKETS WERE NOT ENOUGH. Rendering a REAL compaction, the orphan section came
        # FLOODED with pasted chat: `[Name]: Hey, do you want to join`, `X says: ...` (3x),
        # `You have invited Y`. One bracket, or none — they passed everything. These three
        # patterns come from the data, not from imagination, and that is why they catch:
        #   `[Name]:` chat line  ·  `X says:` speaker line  ·  `You have/are …` app notification.
        # ⚠️ DECLARED COST: a user sentence in English starting with "You have" would be dropped.
        # Accepted trade-off, written down for whoever touches this.
        if re.match(r"^\[[^\]]+\]\s*:", p) or re.search(r"\bsays:\s", p):
            continue
        if re.match(r"^You (have|are|receive|win|gain|were)\b", p):
            continue
        if sum(c.isdigit() for c in p) / len(p) > 0.12:
            continue
        out.append(p)
    return out


def parecido(assin, resumo_norm):
    """Did the signature reach the summary? Literal match OR overlap of rare words."""
    a = re.sub(r"\s+", " ", assin).lower()
    if a in resumo_norm:
        return True
    palavras = [w for w in re.findall(r"\w{5,}", a)]
    if len(palavras) < 3:
        return False
    achadas = sum(1 for w in palavras if w in resumo_norm)
    return achadas / len(palavras) >= 0.7      # 70% of the long words present


def mede_arquivo(caminho):
    """Returns one measurement per compaction found in the transcript."""
    try:
        linhas = [json.loads(l) for l in open(caminho, encoding="utf-8") if l.strip().startswith("{")]
    except Exception as e:
        return [{"erro": f"{caminho}: {e}"}]
    out = []
    # ⚠️ WINDOW, NOT CUMULATIVE. The original count looked at `linhas[:i]` at each boundary and
    # recounted the SAME turn in every later compaction of the session — a turn that evaporated in
    # the 1st showed up again in the 2nd and 3rd, inflating the loss. Each compaction answers only
    # for what came in AFTER the previous one.
    #
    # 🚨 AND THE WINDOW IS BY TIME, NOT BY POSITION IN THE FILE. The transcript **re-emits old
    # boundaries**, because each summary carries the previous ones. With `anterior` walking by
    # position, a new boundary had a RE-EMISSION of an old one as its "previous", and the window
    # shrank from two hours of conversation to **3 turns**. The same replay would recount old turns
    # if the window were simply stretched backwards.
    # The rule immune to both: DISTINCT boundaries in chronological order, turns DEDUPLICATED by
    # uuid, and each turn falls in the window by its timestamp.
    vistas = {}
    for i, d in enumerate(linhas):
        if d.get("subtype") == "compact_boundary":
            m = d.get("compactMetadata") or {}
            vistas[f'{d.get("timestamp","")[:16]}|{m.get("preTokens",0)}'] = (i, d)
    fronteiras = sorted(vistas.values(), key=lambda t: t[1].get("timestamp", ""))
    todas_falas = {}
    for x in linhas:
        if e_fala_do_usuario(x):
            todas_falas.setdefault(x.get("uuid") or f"sem-uuid-{len(todas_falas)}", x)
    falas_ord = sorted(todas_falas.values(), key=lambda x: x.get("timestamp", ""))

    ts_ant = ""
    for i, d in fronteiras:
        ts = d.get("timestamp", "")
        m = d.get("compactMetadata") or {}
        pres = set((m.get("preservedMessages") or {}).get("uuids") or [])
        # the summary is the next marked message — it is what replaced everything
        resumo = ""
        for x in linhas[i:i + 6]:
            if x.get("isCompactSummary"):
                resumo = texto_de(x.get("message")); break
        # ⚠️ SUMMARY NOT WRITTEN YET = DO NOT MEASURE. At a fresh boundary the summary may not be in
        # the transcript yet; measuring against an empty string would report **100% evaporation**
        # and return turns the summary carried just fine. Without `ts_ant` moving, the window stays
        # intact and the next pass measures it right.
        if not resumo:
            continue
        falas = [x for x in falas_ord if ts_ant < x.get("timestamp", "") <= ts]
        rnorm = re.sub(r"\s+", " ", resumo).lower()

        lit = cit = eva = sem_assin = 0
        evaporadas, orfaos = [], []
        for fx in falas:
            if fx.get("uuid") in pres:
                lit += 1; continue
            txt_fx = texto_de(fx.get("message"))
            a = assinatura(txt_fx)
            if not a:
                sem_assin += 1; continue
            if parecido(a, rnorm):
                cit += 1
                # ⚠️ CITED IS NOT WHOLE. The message passed through its signature, but its other
                # subjects may have been dropped — see `segmentos_uteis`. The orphans are kept to be
                # returned, otherwise the loss that matters most stays without a number.
                segs = segmentos_uteis(txt_fx)
                if len(segs) >= 3:
                    for s in segs:
                        # ⚠️ dedupe: the same line came 3x in a real render. Repeating it spends the
                        # cap and makes the section look like junk — and a section that looks like
                        # junk teaches the reader to skip it, including when it carries a decision.
                        if (not parecido(s, rnorm) and len(orfaos) < 25
                                and s[:400] not in [o["txt"] for o in orfaos]):
                            orfaos.append({"txt": s[:400], "quando": fx.get("timestamp", "")[:16]})
            else:
                eva += 1
                # THE WHOLE TEXT, not the signature: this is what goes back into the next context.
                # The signature is for measuring; returning half would be worse than not returning —
                # an order cut in the middle becomes noise that looks like a decision.
                # ⚠️ BUT A TURN WITH NO PROSE AT ALL DOES NOT GO BACK. A test with real data brought
                # back a whole pasted chat log, eating the cap instead of the user's observation.
                # It still COUNTS as evaporated: the number measures the loss, the return picks
                # what is worth re-emitting, and those are two different things.
                if len(evaporadas) < 40 and segmentos_uteis(txt_fx):
                    evaporadas.append({"txt": texto_de(fx.get("message")).strip()[:1200],
                                       "quando": fx.get("timestamp", "")[:16]})
        out.append({
            "sessao": Path(caminho).stem[:8],
            "quando": d.get("timestamp", "")[:16],
            "trigger": m.get("trigger"),
            # window without our turns = what was cut came from another session (or was counted)
            "herdada": len(falas) == 0,
            "preTokens": m.get("preTokens", 0),
            "postTokens": m.get("postTokens", 0),
            "dropped_acumulado": m.get("cumulativeDroppedTokens", 0),
            "resumo_chars": len(resumo),
            "falas": len(falas), "literais": lit, "citadas": cit,
            "evaporadas": eva, "sem_assinatura": sem_assin,
            "exemplos_evaporados": [e["txt"][:110] if isinstance(e, dict) else e for e in evaporadas],
            "falas_evaporadas": evaporadas,
            # stretches lost INSIDE messages counted as preserved
            "orfaos": orfaos,
            "transcript": str(caminho),
            "devolvida": False,
        })
        ts_ant = ts           # the next window starts at the instant of this boundary
    return out


def relatorio(regs):
    reais = [r for r in regs if not r.get("erro") and not r["herdada"] and r["falas"] > 0]
    print(f"== {len(regs)} compactions in the history · {len(reais)} with measurable own turns ==")
    if not reais:
        # ⚠️ zero here is not "nothing is lost" — it is "could not measure". Always tell them apart.
        print("   BLIND: no compaction with own turns — nothing to conclude")
        return 1
    tf = sum(r["falas"] for r in reais)
    tl = sum(r["literais"] for r in reais)
    tc = sum(r["citadas"] for r in reais)
    te = sum(r["evaporadas"] for r in reais)
    print(f"   user turns in total    : {tf}")
    print(f"     preserved LITERALLY  : {tl:5}  ({100*tl/tf:.1f}%)")
    print(f"     CITED in the summary : {tc:5}  ({100*tc/tf:.1f}%)")
    print(f"     EVAPORATED           : {te:5}  ({100*te/tf:.1f}%)   <- the loss that costs")
    # ⚠️ The loss the number above does NOT see: a message counted as CITED that arrived half-way.
    to = sum(len(r.get("orfaos") or []) for r in reais)
    print(f"   ORPHAN stretches inside 'preserved' messages: {to}"
          f"  ({to/max(len(reais),1):.1f} per compaction)")
    cortes = [100*(1-r["postTokens"]/r["preTokens"]) for r in reais if r["preTokens"]]
    if cortes:
        cortes.sort()
        print(f"   token cut: median {cortes[len(cortes)//2]:.1f}% "
              f"(min {cortes[0]:.1f}% · max {cortes[-1]:.1f}%)")
    print("\n   -- sample of what EVAPORATED (user turns that did not reach the other side) --")
    vistos = 0
    for r in sorted(reais, key=lambda x: -x["evaporadas"]):
        for ex in r["exemplos_evaporados"]:
            print(f"     [{r['quando']}] {ex}")
            vistos += 1
            if vistos >= 12: return 0
    return 0


TETO_DEVOLVER = 4000     # chars — above this, cut and DECLARE the cut
TAIL_BYTES = 3_000_000   # how much of the end of the transcript is enough to find the newest boundary


def chave_de(reg):
    """Identity of a compaction: minute of the boundary + preTokens.

    Works for a ledger record AND for a boundary read from the transcript — it is what lets us ask
    "is this compaction measured already?" without reparsing a 27 MB file.
    """
    return f"{reg.get('quando','')}|{reg.get('preTokens',0)}"


def ultima_chave_do_transcript(tp):
    """Key of the NEWEST boundary of the transcript, reading only the tail. None if there is none.

    ⚠️ Cheap on purpose: this runs on every prompt. The full parse (`mede_arquivo`) only happens
    when this key is unknown to the ledger.
    """
    try:
        tam = os.path.getsize(tp)
        with open(tp, "rb") as f:
            if tam > TAIL_BYTES:
                f.seek(tam - TAIL_BYTES)
                f.readline()                      # drop the line cut in half
            bruto = f.read().decode("utf-8", "replace")
    except Exception:
        return None
    ls = bruto.splitlines()
    achadas = []
    for n, l in enumerate(ls):
        if '"compact_boundary"' not in l:
            continue
        try:
            d = json.loads(l)
        except Exception:
            continue
        if d.get("subtype") != "compact_boundary":
            continue
        m = d.get("compactMetadata") or {}
        achadas.append((n, {"quando": d.get("timestamp", "")[:16],
                            "preTokens": m.get("preTokens", 0)}))
    # ⚠️ THE NEWEST ONE **WITH A SUMMARY**, not simply the newest. Two traps at once:
    #   · `mede_arquivo` refuses to measure a boundary without a summary (it would report 100%
    #     evaporation), so its key never enters the ledger — pointing at it would reparse 27 MB on
    #     every prompt, forever (the cost guard caught this);
    #   · but stopping AT it also blinds the earlier ones, which were measurable and would stay
    #     unsynced (the first version of this shortcut did exactly that and broke 5 checks at once).
    for n, b in reversed(achadas):
        if any('"isCompactSummary":true' in x.replace(" ", "") for x in ls[n:n + 6]):
            return chave_de(b)
    return None


def sincroniza(tp):
    """Makes sure every compaction of the transcript is in the ledger. Returns the number of new ones.

    🚨 WHY THIS EXISTS — the two defects the first REAL event showed:

    1. **The writer measured the WRONG compaction.** At `PostCompact` the new boundary is not yet
       written to the transcript, so `regs[-1]` took the PREVIOUS one. Proven by the tokens: the
       ledger came out with the preTokens of the previous boundary while the one that had just
       happened had a much larger value. A whole turn of user messages was left out.
    2. **The returner lost the race.** `SessionStart:compact` and `PostCompact` fire at the SAME
       instant: the returner read the ledger before the writer created it, exited 0 silently, and
       the mechanism became a no-op exactly on the event it exists for.

    The way out is not ordering hooks (the order is not ours) nor waiting (it would block the start
    of the session): it is making the return **state-driven**. Whoever returns also measures, when
    it can — and the key prevents measuring twice. A boundary not yet written simply enters on the
    next touch, instead of being lost.
    """
    if not tp or not os.path.exists(tp):
        return 0
    try:
        linhas = [json.loads(l) for l in LEDGER.read_text(encoding="utf-8").splitlines() if l.strip()]
    except Exception:
        linhas = []
    conhecidas = {chave_de(r) for r in linhas}
    ch = ultima_chave_do_transcript(tp)
    if not ch or ch in conhecidas:
        return 0                       # nothing new — and the common case does not pay the parse
    # ⚠️ the transcript REPEATS old boundaries (the summary carries the previous ones): the same
    # boundary can appear 3x in a real file. Dedupe INSIDE the batch too, otherwise the first sync
    # is born with a duplicated line in the ledger.
    novas, vistas = [], set(conhecidas)
    for r in mede_arquivo(tp):
        k = chave_de(r)
        if r.get("erro") or k in vistas:
            continue
        vistas.add(k)
        novas.append(r)
    if not novas:
        return 0
    try:
        with LEDGER.open("a") as f:
            for r in novas:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
    except Exception:
        return 0
    return len(novas)


def devolver():
    """SessionStart:compact mode — returns to the context the turns the compaction swallowed.

    WHY THIS EXISTS
      A turn CANNOT be marked as preservable. Measured over 28 compactions, preservation is pure
    RECENCY — a median of 2 messages next to the boundary — and the binary has no
    `preserveFromUuid`/`keepMessages`/`alwaysPreserve`. The 0.1% of literal preservation was not
    wasted capacity: it was its CEILING.
      What can be done is BRING IT BACK. This mode measures the compaction (via `sincroniza`) and
    re-emits the swallowed turns through the channel that already returns the map (PLAIN STDOUT
    becomes context at SessionStart and UserPromptSubmit). Measured cost: a median of 2 turns x 111
    chars = ~56 tokens.
      ⚠️ It no longer depends on `PostCompact`: that one fired BEFORE the new boundary was written
    and measured the PREVIOUS compaction, and also raced this mode. See `sincroniza`.

    ⚠️ THE LINK IS NOT THE session_id — it CHANGES after the compaction, and matching by it would
    lose exactly the case that matters. It matches by `transcript_path`, which is stable — and ONLY
    by it: see the comment on the fallback below.
    """
    try:
        d = json.load(sys.stdin)
    except Exception:
        d = {}
    tp = d.get("transcript_path")
    sincroniza(tp)                    # whoever returns also measures — see `sincroniza`
    try:
        linhas = [json.loads(l) for l in LEDGER.read_text(encoding="utf-8").splitlines() if l.strip()]
    except Exception:
        return 0                      # no ledger, nothing to return — silence, not an error
    cands = [r for r in linhas
             if not r.get("devolvida") and (r.get("falas_evaporadas") or r.get("orfaos"))]
    # 🚨 NO FALLBACK ACROSS SESSIONS. The first version fell back to `or cands` when no record
    # matched this transcript — poison when several sessions are open at the same time: the fallback
    # would hand the turns of ANOTHER conversation here, and consume them (`devolvida=True`) before
    # the owning conversation opened. Losing by silence is bad; returning in the wrong place is
    # worse, because it looks like it worked.
    if tp:
        cands = [r for r in cands if r.get("transcript") == tp]
    if not cands:
        return 0

    # ⚠️ ALL pending ones, oldest to newest — not only the last. If two compactions happen before a
    # return (a session that dies early, a hook that did not run), `cands[-1]` would leave the older
    # one stuck in the ledger forever, marked not-returned and never read. The cap is still the brake.
    usado, mostradas, cortadas = 0, [], 0
    for reg in cands:
        for f in reg["falas_evaporadas"]:
            t = (f.get("txt") if isinstance(f, dict) else str(f)).strip()
            if not t:
                continue
            if usado + len(t) > TETO_DEVOLVER:
                cortadas += 1
                continue
            usado += len(t)
            mostradas.append((f.get("quando", "") if isinstance(f, dict) else "", t))
    # ⚠️ orphans come AFTER, with whatever cap is left: a whole lost turn has priority
    orfaos, orf_cortados = [], 0
    for reg_o in cands:
        for f in reg_o.get("orfaos") or []:
            t = (f.get("txt") or "").strip()
            if not t:
                continue
            if usado + len(t) > TETO_DEVOLVER:
                orf_cortados += 1
                continue
            usado += len(t)
            orfaos.append((f.get("quando", ""), t))
    reg = cands[-1]
    if not mostradas and not orfaos:
        return 0

    pre = max(reg.get("preTokens", 1), 1)
    corte = 100 * (1 - reg.get("postTokens", 0) / pre)
    tot_falas = sum(r.get("falas", 0) for r in cands)
    tot_evap = sum(r.get("evaporadas", 0) for r in cands)
    quando = (reg.get("quando", "?") if len(cands) == 1
              else f"{cands[0].get('quando','?')} … {reg.get('quando','?')} ({len(cands)}x)")
    linhas_out = [
        "<!-- contexto-medir: user turns the compaction SWALLOWED -->",
        "# ⚠️ WHAT YOU TOLD ME AND THE SUMMARY DID NOT CARRY",
        "",
        f"The compaction of {quando} cut {corte:.0f}% of the context. Of your "
        f"{tot_falas} turns in that window, **{tot_evap} did not reach the summary**.",
        "",
        "They are below **verbatim** — a decision of yours is not paraphrased. If one already became",
        "a line in a doc or in memory, it is redundant here, and redundancy costs less than loss.",
        "",
    ]
    if not mostradas:
        linhas_out[3] = (f"The compaction of {quando} cut {corte:.0f}% of the context. No turn "
                         f"of yours was lost whole — but a long message arrived half-way.")
    for quando_f, t in mostradas:
        t1 = t if len(t) <= 600 else t[:600] + " [...]"
        marca = f"**{quando_f}** · " if quando_f else ""
        linhas_out.append(f"- {marca}{t1}")
    if orfaos:
        # ⚠️ THE LOSS THE NUMBER DID NOT SEE: the message passed (its signature is in the
        # summary), but OTHER subjects of it did not. Measured: 26.5% of the segments of long
        # messages judged preserved. It is where what is decided AFTER the main subject lives.
        linhas_out += [
            "",
            "## Stretches of messages the summary carried only HALFWAY",
            "",
            "The message arrived, but these pieces of it did not — they are the secondary",
            "subjects of a long message, historically where a dropped order lives.",
            "",
        ]
        for quando_o, t in orfaos:
            marca = f"**{quando_o}** · " if quando_o else ""
            linhas_out.append(f"- {marca}{t}")
        if orf_cortados:
            linhas_out.append(f"\n*(+{orf_cortados} stretch(es) did not fit under the cap)*")
    if cortadas:
        # ⚠️ never cut silently: what did not fit shows up as a NUMBER
        linhas_out.append("")
        linhas_out.append(f"*(+{cortadas} turn(s) did not fit under the cap of {TETO_DEVOLVER} chars — "
                          f"`contexto-medir.py --historico` shows them all)*")
    print("\n".join(linhas_out))

    # Idempotence: mark ALL that were read in this round. ⚠️ Marking only `cands[-1]` would leave
    # the earlier ones pending forever — they were already emitted, so they would repeat every prompt.
    try:
        for r in cands:
            r["devolvida"] = True
        # ⚠️ PRUNING — the ledger is read ON EVERY PROMPT. Each record can carry 40 turns of 1200
        # chars + 25 orphans of 400: ~58 KB. At the measured pace (8 compactions/day) that projects
        # **42 MB in 90 days** re-read on every message, and the cost would show up as diffuse
        # slowness nobody links to this code. A returned record no longer needs the text: the
        # SERIES (turns/evaporated/orphans/tokens) is what makes the measurement, and it is tiny.
        # The text stays recoverable — `--historico` re-measures from the transcript, the source.
        for r in linhas:
            if r.get("devolvida"):
                r.pop("falas_evaporadas", None)
                r.pop("orfaos", None)
                r.pop("exemplos_evaporados", None)
        LEDGER.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in linhas) + "\n",
                          encoding="utf-8")
    except Exception:
        pass
    return 0


def selftest():
    """Proves the `parecido` predicate — without this, "30% evaporated" is an opinion that looks like a number."""
    ok = ruim = 0
    def checa(nome, cond):
        nonlocal ok, ruim
        print(f"  {'✓' if cond else '✗'} {nome}")
        ok, ruim = (ok+1, ruim) if cond else (ok, ruim+1)

    resumo = ("the user asked to close the export gate and ordered the test battery run on the build host "
              "before promoting the binary to production with the workers loaded").lower()
    # POSITIVE — the turn is in the summary
    checa("positive · turn present in the summary is CITED",
          parecido("ordered the test battery run on the build host before promoting", resumo))
    checa("positive · literal stretch is CITED",
          parecido("close the export gate", resumo))
    # ⚠️ NEGATIVE — without it the predicate "finds" in any summary and the loss becomes 0%
    checa("negative · a turn NOT in the summary evaporates",
          not parecido("the parser lost the cursor in the loop and nobody knew why", resumo))
    checa("negative · loose coinciding words are NOT enough",
          not parecido("user binary production never existed such subject here", resumo))
    # SIGNATURE: a sentence too short matches by chance — it must be rejected at the source
    checa("signature · a too-short sentence is dropped", assinatura("ok sure") is None)
    checa("signature · takes the MIDDLE, not the opening",
          "refactor" in (assinatura("yes: refactor (having a cache is better) no: rewrite module") or ""))
    # POPULATION: a system marker is not a turn
    checa("population · '[Request interrupted by user]' is NOT a user turn",
          not e_fala_do_usuario({"type":"user","message":{"content":"[Request interrupted by user]"}}))
    checa("population · tool_result is NOT a user turn",
          not e_fala_do_usuario({"type":"user","message":{"content":[{"type":"tool_result"}]}}))
    # -- the RETURNER: cap and declared cut ------------------------------------------------------
    import tempfile, os as _os
    with tempfile.TemporaryDirectory() as td:
        led = _os.path.join(td, "l.jsonl")
        falas = [{"txt": "x"*500, "quando": "2026-01-0%d" % (i%9+1)} for i in range(20)]
        reg = {"quando":"t","preTokens":1000,"postTokens":10,"falas":20,"evaporadas":20,
               "falas_evaporadas":falas,"transcript":"/t.jsonl","devolvida":False}
        open(led,"w").write(json.dumps(reg)+"\n")
        globals()["LEDGER"] = Path(led)
        import io, contextlib
        buf = io.StringIO()
        _stdin = sys.stdin; sys.stdin = io.StringIO('{"transcript_path":"/t.jsonl"}')
        with contextlib.redirect_stdout(buf): devolver()
        sys.stdin = _stdin
        out = buf.getvalue()
        checa("returner · respects the char cap", len(out) < TETO_DEVOLVER + 1200)
        # ⚠️ a silent cut is the worst outcome: what did not fit must become a NUMBER
        checa("returner · DECLARES how many turns did not fit", "did not fit under the cap" in out)
        checa("returner · marks as returned (idempotence)",
              json.loads(open(led).readline())["devolvida"] is True)
        buf2 = io.StringIO()
        sys.stdin = io.StringIO('{"transcript_path":"/t.jsonl"}')
        with contextlib.redirect_stdout(buf2): devolver()
        sys.stdin = _stdin
        checa("returner · 2nd call does NOT repeat", buf2.getvalue().strip() == "")

    # -- THE RACE and ATTRIBUTION: the two defects only the first real event showed -------------
    # Checks written AFTER the defect, and proven by removing `sincroniza()` from the returner
    # (without it both light up). A fixture does NOT replace real data — the positive control
    # against a real transcript is `--devolver` on the live session.
    with tempfile.TemporaryDirectory() as td:
        tr = _os.path.join(td, "t.jsonl")
        led2 = _os.path.join(td, "l2.jsonl")

        def fala(txt, ts):
            return {"type": "user", "uuid": ts, "timestamp": ts + ":00.000Z",
                    "message": {"role": "user", "content": txt}}

        def fronteira(ts, pre):
            return {"type": "system", "subtype": "compact_boundary", "timestamp": ts + ":00.000Z",
                    "compactMetadata": {"preTokens": pre, "postTokens": 100, "trigger": "manual",
                                        "preservedMessages": {"uuids": []}}}
        reg_txt_velho = "subject entirely distinct from the first window that never appears there"
        reg_txt_novo = "order from the second window about the trigger dispatcher and the build host"
        linhas_tr = [
            {"type": "assistant", "message": {"role": "assistant", "content": "open"}},
            fala(reg_txt_velho, "2026-01-01T10:00"),
            fronteira("2026-01-01T11:00", 5000),
            {"type": "user", "isCompactSummary": True,
             "message": {"role": "user", "content": "a recap covering some other matter"}},
            fala(reg_txt_novo, "2026-01-01T12:00"),
            # ⚠️ THE RE-EMISSION — this is what the real transcript does, and what shrank the window
            fronteira("2026-01-01T11:00", 5000),
            {"type": "user", "isCompactSummary": True,
             "message": {"role": "user", "content": "a recap covering some other matter"}},
            fronteira("2026-01-01T13:00", 9000),
            {"type": "user", "isCompactSummary": True,
             "message": {"role": "user", "content": "second recap, also about another matter"}},
            # boundary WITHOUT a written summary yet — it cannot be measured (would report 100% loss)
            fala("third window, still open and without any recap at all", "2026-01-01T14:00"),
            fronteira("2026-01-01T15:00", 12000),
        ]
        open(tr, "w").write("\n".join(json.dumps(x) for x in linhas_tr) + "\n")
        globals()["LEDGER"] = Path(led2)

        # ⚠️ THE RACE: a NONEXISTENT ledger (the real state when the returner arrives first).
        # Before the fix this exited 0 silently and the mechanism became a no-op on the event that matters.
        buf3 = io.StringIO()
        sys.stdin = io.StringIO(json.dumps({"transcript_path": tr}))
        with contextlib.redirect_stdout(buf3): devolver()
        sys.stdin = _stdin
        out3 = buf3.getvalue()
        checa("race · returns even with the ledger NOT yet written", reg_txt_novo in out3)
        # ⚠️ ATTRIBUTION: the old writer took `regs[-1]` with the new boundary not yet written and
        # measured the PREVIOUS compaction — a whole turn of user messages was left out.
        # ⚠️ DEFENSIVE READ. The first version of this check did `open(led2)` directly: with the
        # defect re-injected it CRASHED instead of failing, and a traceback kills the whole selftest —
        # the score vanishes and the following checks never run. A check must say "✗", not die.
        def ler_led():
            try:
                return [json.loads(l) for l in open(led2).read().splitlines() if l.strip()]
            except Exception:
                return []
        regs_led = ler_led()
        # ⚠️ proof of attribution is each turn in ITS record, not absence from the output: the
        # output mixes windows on purpose (all pending ones are returned).
        # ⚠️ And the text must be read from a FRESH ledger: `devolver()` above already pruned `led2`
        # (a returned record no longer keeps the text).
        led2b = _os.path.join(td, "l2b.jsonl")
        globals()["LEDGER"] = Path(led2b)
        sincroniza(tr)
        virgem = [json.loads(l) for l in open(led2b).read().splitlines() if l.strip()]
        globals()["LEDGER"] = Path(led2)

        def falas_de(pre):
            r = [x for x in virgem if x.get("preTokens") == pre]
            return " ".join(f["txt"] for f in r[0].get("falas_evaporadas") or []) if r else ""
        checa("attribution · measures the NEW boundary, not the previous one",
              bool(regs_led) and regs_led[-1].get("preTokens") == 9000
              and reg_txt_novo in falas_de(9000) and reg_txt_novo not in falas_de(5000))
        n1 = len(regs_led)
        checa("dedupe · 2nd sync adds no line",
              sincroniza(tr) == 0 and len(ler_led()) == n1)
        # ⚠️ the common case must not pay a 27 MB parse: nothing new => the whole file is not opened
        checa("cost · the tail key matches the ledger's when there is nothing new",
              bool(ler_led()) and ultima_chave_do_transcript(tr) == chave_de(ler_led()[-1]))
        checa("robustness · a nonexistent transcript does not break", sincroniza("/nao/existe.jsonl") == 0)
        # ⚠️ THE RE-EMISSION: with a window by POSITION, the previous boundary of the new one was the
        # copy of the old one and the window shrank to almost nothing. By TIME, the 12:00 turn lands right.
        regs_f = ler_led()
        nova = [r for r in regs_f if r.get("preTokens") == 9000]
        checa("re-emission · window by TIME ignores the re-emitted old boundary",
              len(nova) == 1 and nova[0].get("falas") == 1)
        # ⚠️ a boundary without a written summary does NOT become a record — it would report 100%
        checa("missing summary · a boundary without summary is not measured",
              not [r for r in regs_f if r.get("preTokens") == 12000])
        # ...and the turn stuck in it does not vanish: it enters the window of the next measurement
        checa("missing summary · the turn stays pending, not discarded",
              sum(r.get("falas") or 0 for r in regs_f) == 2)
        # ⚠️ ALL pending ones come out: with `cands[-1]` the older window stayed stuck forever
        checa("pending · returns BOTH windows, not only the last",
              reg_txt_velho in out3 and reg_txt_novo in out3)
        checa("pending · marks both as returned",
              all(r.get("devolvida") for r in ler_led() if r.get("falas_evaporadas")))
        # ⚠️ PRUNING: the ledger is read on every prompt and projected 42 MB in 90 days without this
        checa("pruning · a returned record no longer keeps the text",
              all(not r.get("falas_evaporadas") and not r.get("orfaos")
                  for r in ler_led() if r.get("devolvida")))
        checa("pruning · the measurement SERIES survives the pruning",
              all("falas" in r and "evaporadas" in r and "preTokens" in r for r in ler_led()))
        # 🚨 with several sessions open, returning in the wrong session is worse than not returning.
        # ⚠️ The first version of this check passed GREEN with the defect re-injected: when it ran,
        # the earlier checks had already marked everything returned, so the output was empty with
        # or without the fallback. A check that cannot fail proves nothing — now it plants a NEW
        # pending record, from another conversation, and only then asks.
        outro = _os.path.join(td, "outro.jsonl")
        open(outro, "w").write("{}\n")
        with open(led2, "a") as f:
            f.write(json.dumps({"quando": "2026-01-02T09:00", "preTokens": 4242, "postTokens": 10,
                                "falas": 1, "evaporadas": 1, "transcript": tr, "devolvida": False,
                                "falas_evaporadas": [{"txt": "pending turn of the OTHER chat",
                                                      "quando": "2026-01-02T08:00"}]}) + "\n")
        buf4 = io.StringIO()
        sys.stdin = io.StringIO(json.dumps({"transcript_path": outro}))
        with contextlib.redirect_stdout(buf4): devolver()
        sys.stdin = _stdin
        checa("multi-chat · does NOT return a turn of another conversation", buf4.getvalue().strip() == "")

    # -- ORPHANS: the loss INSIDE a message counted as preserved ----------------------------------
    with tempfile.TemporaryDirectory() as td:
        tr2 = _os.path.join(td, "t2.jsonl")
        led3 = _os.path.join(td, "l3.jsonl")
        principal = "the dashboard has to show the ranking of votes with the total per week"
        sec1 = "the admin part of the app is missing to manage the products sold"
        sec2 = "and the courier must appear with the phone on the delivery view"
        # ⚠️ the fixture noise must SURVIVE the split on '.', otherwise its check cannot fail: the
        # first version used `app.py` and `example.com`, which the split itself destroyed — it
        # passed green with the noise filter REMOVED, the worst kind of check.
        lixo_path = "/srv/work/repo/scripts/some-file-with-a-rather-long-path-name-here"
        lixo_url = "https://example-of-a-rather-long-domain-for-the-test/page/inner"
        # the shape of a real pasted tool log line: bracketed upper-case tag, then counters
        lixo_log = "[WORKER-STAT] by kind direct 624 batch 236 retry 149 heal 0 noop 0 other 5037"
        # ⚠️ THESE THREE HAVE THE SHAPE OF A REAL RENDER. An invented fixture is what let the defect
        # through: the filter demanded 2 brackets and a pasted chat line has 1, or none. A fixture
        # must come from the data, not from an idea of what the data looks like.
        chat1 = "[Marlowe]: Hey Tessaly, can you join my review call on the login page"
        chat2 = "Support Desk Bot says: Need a hand with your order here right now"
        chat3 = "You have invited Brenno to join your team in the chat"
        multi = (f"{principal}. {sec1}. {sec2}. {lixo_path}. {lixo_url}. {lixo_log}. "
                 f"{chat1}. {chat2}. {chat3}")
        curta = "simple single subject message that arrives whole in the turn recap"
        linhas2 = [
            {"type": "assistant", "message": {"role": "assistant", "content": "open"}},
            {"type": "user", "uuid": "u1", "timestamp": "2026-02-01T10:00:00.000Z",
             "message": {"role": "user", "content": multi}},
            {"type": "user", "uuid": "u2", "timestamp": "2026-02-01T10:05:00.000Z",
             "message": {"role": "user", "content": curta}},
            {"type": "system", "subtype": "compact_boundary",
             "timestamp": "2026-02-01T11:00:00.000Z",
             "compactMetadata": {"preTokens": 7000, "postTokens": 100, "trigger": "manual",
                                 "preservedMessages": {"uuids": []}}},
            {"type": "user", "isCompactSummary": True,
             "message": {"role": "user", "content": f"recap: {principal}. And also: {curta}"}},
        ]
        open(tr2, "w").write("\n".join(json.dumps(x) for x in linhas2) + "\n")
        globals()["LEDGER"] = Path(led3)
        sincroniza(tr2)
        r2 = [json.loads(l) for l in open(led3).read().splitlines() if l.strip()][-1]
        orf = " ".join(o["txt"] for o in r2.get("orfaos") or [])
        # POSITIVE — the message passed through its signature, but the secondary subjects did not
        checa("orphan · a CITED message yields the subjects left behind",
              r2["evaporadas"] == 0 and sec1 in orf and sec2 in orf)
        # NEGATIVE — what the summary carried must NOT come back as an orphan (pure noise)
        checa("orphan · the subject that reached the summary does NOT come back", principal not in orf)
        # ⚠️ NOISE: paths and URLs inflated the count and would spend the cap on non-decisions
        checa("orphan · path and URL do not become orphans",
              lixo_path not in orf and lixo_url not in orf)
        # ⚠️ half of the orphans of the first measurement were pasted tool output
        checa("orphan · pasted machine output does not become an orphan",
              "WORKER-STAT" not in orf and "5037" not in orf)
        # ⚠️ and the real render was flooded with pasted chat — 14 of 20 lines
        checa("orphan · a pasted chat log does not become an orphan",
              "Marlowe" not in orf and "Support Desk Bot" not in orf and "Brenno" not in orf)
        # ⚠️ a single-subject message yields no orphan — otherwise every turn would flood
        checa("orphan · a short single-subject message yields no orphan", curta not in orf)
        buf5 = io.StringIO()
        sys.stdin = io.StringIO(json.dumps({"transcript_path": tr2}))
        with contextlib.redirect_stdout(buf5): devolver()
        sys.stdin = _stdin
        checa("orphan · the returner emits the section even with no whole turn lost",
              "HALFWAY" in buf5.getvalue() and sec1 in buf5.getvalue())

    checa("population · a real user text counts",
          e_fala_do_usuario({"type":"user","message":{"content":"go ahead, commit and make section 15 a pointer"}}))
    print(f"== {ok} ok · {ruim} failure(s) ==")
    return 1 if ruim else 0


def main():
    args = sys.argv[1:]
    if "--selftest" in args:
        sys.exit(selftest())
    if "--devolver" in args:
        try:
            sys.exit(devolver())
        except Exception:
            sys.exit(0)      # never disturb the start of the session
    if "--historico" in args or "--sessao" in args:
        alvos = glob.glob(str(PROJ / "*.jsonl"))
        if "--sessao" in args:
            sid = args[args.index("--sessao") + 1]
            alvos = [a for a in alvos if sid in a]
        regs = []
        for a in alvos:
            regs.extend(mede_arquivo(a))
        for r in regs:
            if r.get("erro"):
                print(f"  ⚠️ {r['erro']}")
        sys.exit(relatorio([r for r in regs if not r.get("erro")]))

    # HOOK mode: PostCompact just happened
    try:
        d = json.load(sys.stdin)
    except Exception:
        sys.exit(0)
    tp = d.get("transcript_path")
    if not tp or not os.path.exists(tp):
        sys.exit(0)
    # ⚠️ IT USED TO BE `regs[-1]` STRAIGHT INTO THE LEDGER, wrong in two ways: it took the newest
    # boundary BY POSITION (possibly a re-emission of an old one) and did not dedupe, so running
    # twice duplicated the line. Now it is the same `sincroniza` as the returner — one path, with a
    # key. If the new boundary is not written yet, it does nothing and the first prompt of the next
    # session resolves it.
    sincroniza(tp)
    sys.exit(0)


if __name__ == "__main__":
    main()
