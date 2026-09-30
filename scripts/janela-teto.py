#!/usr/bin/env python3
"""JANELA-TETO — warns when the context window passes a step.

WHY IT EXISTS (measured over 136 sessions / 40.04 billion input tokens).
The window is re-sent on EVERY request, so cost = size x remaining turns (see docs/CONTEXTO.md).
A long session ALREADY compacts itself — the largest in the sample did so 13 times — but only way
up: the window climbs to ~620 K and drops to 59 K.

  Simulated over the real curve of that session (the model reproduces the measured cost within 0.6%):

    ceiling ~620 K (default) -> 3,205 M tokens   |   ceiling 300 K -> 1,511 M   (47%)
    ceiling 400 K            -> 1,929 M (60%)    |   ceiling 200 K -> 1,090 M   (34%)

  **Compacting at 300 K instead of 620 K cuts the cost in half.** Unless a ceiling is set (see
  `teto_configurado`), the auto-compact threshold is the harness's own, so an early compaction has
  to be PROVOKED, and nobody watches the number: that is why it goes to 620 K. This hook watches.

WHAT IT IS NOT: a read brake. Cutting reads was measured and dropped — the tail of large results
is 4.7% of the volume, and cutting reads collides with reading logs in full. Nothing is cut here:
it warns that the history became expensive.

CONTRACT
  · runs on `PostToolUse`, never blocks (exit 0 always, even on error)
  · reads only the END of the transcript (50 MB transcripts exist; reading all of it on every tool
    call would slow the session down)
  · warns once PER STEP: a warning repeated on every call becomes ignored decoration
  · a drop of the window (compaction) re-arms the steps

THE COUNTER OF OWN TOOL CALLS.
Measured over 28 compaction cycles: a cycle holds ~130 own tool calls whatever the project, and the
median result of a call is < 1 KB — **what fills the window is the LOOP in the session, not the heavy
call**. The loop belongs to an agent (build AND gate). This counter lights up when the session
starts operating what it should delegate.
  · +1 per hook call, ONLY on an OWN call. Measured on the real stdin: the `PostToolUse` of a
    subagent arrives with the PARENT's `session_id` and `transcript_path`, and what tells it apart
    is `agent_id`/`agent_type` being present. The `isSidechain` of the parent's tail does NOT work:
    the subagent writes to `<sid>/subagents/agent-<id>.jsonl`, not to the parent's transcript.
  · own re-arm: the window DROPPED (`v < 0.7 x the window of the previous call`). The window steps
    do not work as a trigger — 1.15x/1.40x/1.75x of the ceiling never drop in normal operation.
  · warns once at 60 and once at 100; state written on EVERY call, atomically and under a lock,
    because parallel tool calls of the same message fire the hook at the same time
"""
import fcntl
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hipo_config as HC

def teto_configurado():
    """The auto-compact ceiling, read from where it REALLY lives.

    `/autocompact <tokens>` writes `autoCompactWindow` into the user settings (100k-1M), and
    `CLAUDE_CODE_AUTO_COMPACT_WINDOW` takes precedence over it. It was once claimed that this was
    NOT configurable — after searching only settings.json and .claude.json, where the key is only
    born when someone uses the command. Reading it here instead of hard-coding a number: if the
    ceiling changes, this hook follows by itself."""
    env = os.environ.get("CLAUDE_CODE_AUTO_COMPACT_WINDOW")
    if env and env.strip().isdigit():
        return int(env)
    try:
        with open(HC.SETTINGS) as fh:
            v = json.load(fh).get("autoCompactWindow")
        if isinstance(v, int) and v > 0:
            return v
    except (OSError, ValueError):
        pass
    return None


def degraus():
    """Steps DERIVED from the ceiling: the hook guards the mechanism, it does not replace it.

    With auto-compact configured, the window should not pass the ceiling. If it passed with room
    to spare, the mechanism did NOT fire — and then the warning is a finding, not a reminder.
    Without a configured ceiling, auto-compact only acts way up (~620 K measured), and the steps go
    back to being reminders."""
    manual = os.environ.get("JANELA_DEGRAUS")
    if manual:
        return [int(x) for x in manual.split(",")]
    t = teto_configurado()
    if t:
        return [int(t * f) for f in (1.15, 1.40, 1.75)]
    return [260000, 360000, 460000]


DEGRAUS = degraus()
ESTADO_DIR = os.environ.get("JANELA_ESTADO", os.path.join(HC.STATE_DIR, "janela-teto"))
CAUDA = 512 * 1024          # how much of the end of the transcript to read
TOQUES_DEGRAUS = (60, 100)  # ~half and ~3/4 of a measured cycle (~130 own calls)
QUEDA = 0.7                 # compaction cuts ~75% (~350 K -> ~86 K); below this, re-arm


def transcript_de(dados):
    p = dados.get("transcript_path")
    if p and os.path.exists(p):
        return p
    sid = dados.get("session_id")
    if not sid:
        return None
    for base in (HC.PROJECT_DIR,):
        c = os.path.join(base, sid + ".jsonl")
        if os.path.exists(c):
            return c
    return None


def janela_atual(caminho):
    """Last usage of the file. Reads only the tail — the start does not matter and can be 50 MB."""
    try:
        tam = os.path.getsize(caminho)
        with open(caminho, "rb") as fh:
            if tam > CAUDA:
                fh.seek(tam - CAUDA)
                fh.readline()          # drop the line cut in half
            bloco = fh.read().decode("utf-8", "replace")
    except OSError:
        return None
    for linha in reversed(bloco.splitlines()):
        if '"usage"' not in linha:
            continue
        try:
            d = json.loads(linha)
        except ValueError:
            continue
        if d.get("type") != "assistant" or d.get("isSidechain"):
            continue
        u = (d.get("message") or {}).get("usage") or {}
        v = (u.get("input_tokens", 0) + u.get("cache_read_input_tokens", 0)
             + u.get("cache_creation_input_tokens", 0))
        if v:
            return v
    return None


def degrau_de(v):
    """The highest step already crossed, or 0."""
    alcancados = [d for d in DEGRAUS if v >= d]
    return max(alcancados) if alcancados else 0


def le_estado(sid):
    try:
        with open(os.path.join(ESTADO_DIR, sid + ".json")) as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def grava_estado(sid, d):
    """Atomic (tmp + os.replace): several sessions and subagents write at the same time, and the
    write happens on EVERY call — a reader must never catch the file half-written."""
    try:
        os.makedirs(ESTADO_DIR, exist_ok=True)
        tmp = os.path.join(ESTADO_DIR, ".%s.%d.tmp" % (sid, os.getpid()))
        with open(tmp, "w") as fh:
            json.dump(d, fh)
        os.replace(tmp, os.path.join(ESTADO_DIR, sid + ".json"))
    except OSError:
        pass


def trava():
    """Single lock of the state directory for the read-modify-write. Parallel calls of the same
    message fire the hook together: without a lock, two read 59 and both write 60 — a lost
    increment. If the lock fails, go on without it (a hook that breaks the session is worse than a
    hook that stays silent)."""
    try:
        os.makedirs(ESTADO_DIR, exist_ok=True)
        fh = open(os.path.join(ESTADO_DIR, ".trava"), "w")
        fcntl.flock(fh, fcntl.LOCK_EX)
        return fh
    except OSError:
        return None


def conta_toque(est, v, proprio):
    """Updates the counter IN the state dict and returns the call step to warn about (or 0).

    `janela` is the counter's OWN key, written on every call: `ultima` only changes when the window
    crosses a step, and comparing against it would compare against an old or missing value."""
    ant = est.get("janela")
    if v and ant and v < QUEDA * ant:
        est["toques"] = 0          # the window dropped: compacted — new cycle
        est["avisado"] = 0
    if v:
        est["janela"] = v
    if not proprio:
        return 0
    est["toques"] = est.get("toques", 0) + 1
    n, ja = est["toques"], est.get("avisado", 0)
    # `>=` and not `==`: if an increment were lost, the step still lights (once, via `avisado`)
    alcancados = [t for t in TOQUES_DEGRAUS if n >= t > ja]
    if alcancados:
        est["avisado"] = max(alcancados)
        return est["avisado"]
    return 0


def aviso_toques(n):
    return (f"⚠️ {n} own tool calls since the last compaction. The loop belongs to an AGENT: "
            "build in a worker agent, gate in a gate agent that reads the logs; the "
            "session receives N of M. NEXT STEP: the next loop goes through Agent.")


def aviso(v, degrau):
    k = v / 1000.0
    custo = v / 1e6
    t = teto_configurado()
    if t:
        # the mechanism exists and should have acted: this is a FINDING
        linhas = [
            f"🚨 **WINDOW AT {k:,.0f} K WITH AUTO-COMPACT AT {t/1000:,.0f} K** — it should have "
            f"fired and did not. Each tool call costs {custo:.2f} M of input.",
            "   Cause no. 1, and the most likely: **the session was born before the ceiling was "
            "written** — the value enters the session state at the opening, so changing the settings "
            "does not reach a session already running. Then there is no defect: `/compact` (or "
            "`/autocompact` in this session) solves it, and the next session is born with the ceiling.",
            "   If the session was born AFTER the ceiling, then it is a defect: `autoCompactEnabled` off · "
            "`DISABLE_AUTO_COMPACT`/`DISABLE_COMPACT` in the environment · "
            "`CLAUDE_CODE_AUTO_COMPACT_WINDOW` overriding the settings with a larger value · "
            "the *rapid refill* breaker (too many compactions in a row) stuck.",
            "   NEXT STEP: `/compact` now to stop the bleeding, and **check the mechanism** — "
            "a ceiling that does not act is worse than no ceiling, because nobody is watching anymore.",
        ]
    else:
        linhas = [
            f"⚠️ **WINDOW AT {k:,.0f} K TOKENS** — each tool call costs {custo:.2f} M of input, and "
            f"will cost that on ALL the next ones until it compacts. **No ceiling is configured.**",
            "   Measured on the sample: a ceiling at 300 K instead of the ~620 K default cuts the cost "
            "of the session **in half** (3,205 M -> 1,511 M on the largest).",
            "   NEXT STEP: `/autocompact 300k` solves it for good (writes `autoCompactWindow` to the "
            "settings); `/compact` solves only this session.",
        ]
    return "\n".join(linhas)


def main():
    try:
        dados = json.load(sys.stdin)
    except (ValueError, OSError):
        return 0
    sid = dados.get("session_id") or "?"
    # a subagent call arrives with the PARENT's session_id and transcript_path; only agent_id tells it apart
    proprio = not dados.get("agent_id")
    caminho = transcript_de(dados)
    # a call without transcript or usage is still a call: v=None only turns off the window, not the counter
    v = janela_atual(caminho) if caminho else None
    textos = []
    fh = trava()
    try:
        est = le_estado(sid)
        mudou = False
        if v:
            d = degrau_de(v)
            ja = est.get("degrau", 0)
            # the window really dropped (compacted): re-arm — step/last as they always were
            if d < ja:
                est["degrau"], est["ultima"], mudou = d, v, True
            elif d > ja:
                mudou = True
                est["degrau"], est["ultima"] = d, v
                textos.append(aviso(v, d))
        t = conta_toque(est, v, proprio) if sid != "?" else 0
        if t:
            textos.append(aviso_toques(est["toques"]))
        if sid != "?" or mudou:
            grava_estado(sid, est)
    finally:
        if fh:
            fh.close()
    if textos:
        # plain text does NOT arrive: PostToolUse delivers through the `hookSpecificOutput` envelope.
        # The first version printed text, ran in 2 sessions and delivered in none (D6).
        # ONE envelope only: window and calls in the same call go out together — two prints break the JSON.
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PostToolUse", "additionalContext": "\n\n".join(textos)}}))
    return 0


def selftest():
    ok = n = 0
    n += 1
    # relative to the STEPS, which are DERIVED from the ceiling — a fixed number here is what
    # broke this test when the ceiling became configurable
    if (degrau_de(DEGRAUS[0] - 1) == 0 and degrau_de(DEGRAUS[0]) == DEGRAUS[0]
            and degrau_de(DEGRAUS[-1] * 2) == DEGRAUS[-1]):
        ok += 1; print(f"  OK  D1 step relative to the ceiling ({DEGRAUS}): below does not light, above saturates")
    else:
        print("  FAILED D1")
    n += 1   # NEGATIVE control: a small window must not light
    if degrau_de(DEGRAUS[0] - 1) == 0:
        ok += 1; print("  OK  D2 negative control: 1 token below the step does NOT light")
    else:
        print("  FAILED D2 — a wide predicate lights on a cheap session")
    n += 1   # the tail: must find the usage even with a huge start of file
    import tempfile
    with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False) as fh:
        fh.write(('{"type":"user","lixo":"' + "x" * 200 + '"}\n') * 6000)
        fh.write(json.dumps({"type": "assistant", "isSidechain": False,
                             "message": {"usage": {"cache_read_input_tokens": 333000}}}) + "\n")
        caminho = fh.name
    v = janela_atual(caminho)
    if v == 333000:
        ok += 1; print(f"  OK  D3 finds the last usage reading only the tail (file of {os.path.getsize(caminho)//1024} KB)")
    else:
        print(f"  FAILED D3 — read {v}, expected 333000")
    n += 1   # a subagent does not count for the parent's window
    with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False) as fh:
        fh.write(json.dumps({"type": "assistant", "isSidechain": False,
                             "message": {"usage": {"cache_read_input_tokens": 111000}}}) + "\n")
        fh.write(json.dumps({"type": "assistant", "isSidechain": True,
                             "message": {"usage": {"cache_read_input_tokens": 999000}}}) + "\n")
        c2 = fh.name
    if janela_atual(c2) == 111000:
        ok += 1; print("  OK  D4 ignores a subagent line (isSidechain) when measuring the parent's window")
    else:
        print("  FAILED D4 — a subagent would inflate the parent's window")
    n += 1   # D5: the PROPERTY (read only the tail), not the result — D3 alone passed green
    with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False) as fh:
        # the usage must NOT be the 1st line: dropping the half line would eat it, and the test
        # would pass green even reading the whole file (that is what happened in the 1st version)
        fh.write('{"type":"user","cabecalho":1}\n' * 3)
        fh.write(json.dumps({"type": "assistant", "isSidechain": False,
                             "message": {"usage": {"cache_read_input_tokens": 777000}}}) + "\n")
        fh.write(('{"type":"user","lixo":"' + "x" * 200 + '"}\n') * 6000)   # pushes the usage out of the tail
        c3 = fh.name
    if janela_atual(c3) is None:
        ok += 1; print(f"  OK  D5 does NOT read beyond the tail ({CAUDA//1024} KB): an old usage outside it stays invisible")
    else:
        print("  FAILED D5 — read the whole file; on a 50 MB transcript that slows every tool call")

    for c in (caminho, c2, c3):
        try: os.unlink(c)
        except OSError: pass
    n += 1   # D6: the ENVELOPE. Emitting is not delivering — plain text runs and vanishes.
    import io, contextlib, tempfile as _tf
    with _tf.NamedTemporaryFile("w", suffix=".jsonl", delete=False) as fh:
        fh.write('{"type":"user","x":1}\n')
        fh.write(json.dumps({"type": "assistant", "isSidechain": False,
                             "message": {"usage": {"cache_read_input_tokens": DEGRAUS[-1] * 2}}}) + "\n")
        c4 = fh.name
    est_old = globals()["ESTADO_DIR"]
    globals()["ESTADO_DIR"] = _tf.mkdtemp()
    buf = io.StringIO()
    stdin_old = sys.stdin
    sys.stdin = io.StringIO(json.dumps({"session_id": "d6", "transcript_path": c4}))
    with contextlib.redirect_stdout(buf):
        main()
    sys.stdin = stdin_old
    globals()["ESTADO_DIR"] = est_old
    saida = buf.getvalue().strip()
    try:
        env = json.loads(saida)
        ctx = env.get("hookSpecificOutput", {}).get("additionalContext", "")
        # 🚨 when a ceiling is configured (the warning is a FINDING), ⚠️ when not (a reminder)
        bom = ctx.startswith(("⚠️", "🚨")) and "WINDOW AT" in ctx
    except ValueError:
        bom = False
    if bom:
        ok += 1; print("  OK  D6 goes out in the hookSpecificOutput envelope (plain text would not arrive)")
    else:
        print(f"  FAILED D6 — output is not the envelope: {saida[:60]!r}")
    try: os.unlink(c4)
    except OSError: pass

    # -- D7-D11: the counter of own calls. Isolated ESTADO_DIR: never the real state. --
    est_old = globals()["ESTADO_DIR"]
    globals()["ESTADO_DIR"] = _tf.mkdtemp()
    tr = _tf.NamedTemporaryFile("w", suffix=".jsonl", delete=False).name
    # below the 1st window step: here only the counter may speak (350 K, or less if the steps
    # derived from the ceiling fall below that)
    alto = min(350000, DEGRAUS[0] - 1)
    baixo = alto * 86 // 350

    def usage(v):
        with open(tr, "w") as fh:
            fh.write(json.dumps({"type": "assistant", "isSidechain": False,
                                 "message": {"usage": {"cache_read_input_tokens": v}}}) + "\n")

    def roda(sid, **extra):
        entrada = {"session_id": sid, "transcript_path": tr, "hook_event_name": "PostToolUse"}
        entrada.update(extra)
        b = io.StringIO()
        old = sys.stdin
        sys.stdin = io.StringIO(json.dumps(entrada))
        with contextlib.redirect_stdout(b):
            main()
        sys.stdin = old
        return b.getvalue()

    def est(sid):
        return le_estado(sid)

    SUB = {"agent_id": "a0123456789abcdef", "agent_type": "worker"}   # shape measured on the real stdin
    usage(alto)
    n += 1   # D7: +1 per own call — starting from an OLD state, without the new keys
    grava_estado("d7", {"degrau": 0, "ultima": 78483})
    for _ in range(3):
        roda("d7")
    e7 = est("d7")
    if e7.get("toques") == 3 and e7.get("degrau") == 0 and e7.get("ultima") == 78483:
        ok += 1; print("  OK  D7 counter goes up 1 per own call (3 -> 3), old state preserved")
    else:
        print(f"  FAILED D7 — state {e7}")
    n += 1   # D8: re-arms when the window drops below 70% — and ONLY then
    usage(alto)
    for _ in range(50):
        roda("d8")
    usage(int(alto * 0.75))            # negative control: dropped, but not below 70%
    roda("d8", **SUB)
    neg = est("d8").get("toques")
    usage(baixo)                       # compacted: ~350 K -> ~86 K
    roda("d8", **SUB)                  # the one who SEES the drop here is a subagent: does not add
    zero = est("d8").get("toques")
    roda("d8")
    um = est("d8").get("toques")
    if neg == 50 and zero == 0 and um == 1:
        ok += 1; print(f"  OK  D8 re-arms on the drop ({alto//1000} K -> {baixo//1000} K: 50 -> 0); "
                       f"at 75% does NOT re-arm (stays 50)")
    else:
        print(f"  FAILED D8 — at 75%: {neg} (expected 50) · on the drop: {zero} (expected 0) · "
              f"after: {um} (expected 1)")
    n += 1   # D9: 1 warning at 60, 1 at 100 — not at 61, not at 99
    usage(alto)
    acesos = []
    for i in range(1, 102):
        s = roda("d9")
        if s.strip():
            acesos.append(i)
    if acesos == [60, 100]:
        ok += 1; print("  OK  D9 warns on exactly 2 of 101 calls: the 60th and the 100th")
    else:
        print(f"  FAILED D9 — lit on calls {acesos[:10]} (expected [60, 100])")
    n += 1   # D10: a subagent call does NOT count (arrives with the parent's sid and transcript)
    for _ in range(3):
        roda("d10")
    antes = est("d10").get("toques")
    for _ in range(70):
        s10 = roda("d10", **SUB)
    depois = est("d10").get("toques")
    if antes == 3 and depois == 3 and not s10.strip():
        ok += 1; print("  OK  D10 70 subagent calls (agent_id) add 0 to the parent (3 -> 3), no warning")
    else:
        print(f"  FAILED D10 — parent {antes} -> {depois} after 70 subagent calls")
    n += 1   # D11: goes out in the envelope; window and calls in the SAME call = ONE envelope, both texts
    usage(alto)
    grava_estado("d11", {"degrau": 0, "janela": alto, "toques": 59})
    s1 = roda("d11")
    usage(DEGRAUS[-1] * 2)             # crosses the window...
    grava_estado("d11b", {"degrau": 0, "janela": DEGRAUS[-1] * 2, "toques": 99, "avisado": 60})
    s2 = roda("d11b")                  # ...and the 100 step in the same call
    try:
        c1 = json.loads(s1)["hookSpecificOutput"]
        c2 = json.loads(s2)["hookSpecificOutput"]      # two prints = invalid JSON = exception
        bom = (c1["hookEventName"] == "PostToolUse"
               and c1["additionalContext"].startswith("⚠️ 60 own tool calls")
               and "NEXT STEP: the next loop goes through Agent." in c1["additionalContext"]
               and "WINDOW AT" in c2["additionalContext"]
               and "⚠️ 100 own tool calls" in c2["additionalContext"])
    except (ValueError, KeyError, TypeError):
        bom = False
    if bom:
        ok += 1; print("  OK  D11 goes out in the hookSpecificOutput envelope; window + calls together = 1 envelope with both")
    else:
        print(f"  FAILED D11 — outputs {s1[:60]!r} · {s2[:60]!r}")
    globals()["ESTADO_DIR"] = est_old
    try: os.unlink(tr)
    except OSError: pass

    print(f"\n{ok} of {n} assertions")
    return 0 if ok == n else 1


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)          # a hook that breaks the session is worse than a hook that stays silent
