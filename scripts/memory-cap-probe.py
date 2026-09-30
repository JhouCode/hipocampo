#!/usr/bin/env python3
"""Which MEMORY.md cap bites first, and where it cuts.

Published in anthropics/claude-code#82056 (comment 5395998744) after v1 was
taken down by two defects pointed out in the thread and a third that showed up in the fix:

  1. the line test sat AFTER the loop -> a file that blows both caps always
     came back "size-bound". Found by @DanceNitra.
  2. the 'last line loaded' column used ceil() -> it names a line that does not fit,
     and errs by reporting MORE content loaded than there is. Found by @pjt222.
  3. split('\n') on a file ending in a newline creates a ghost line ->
     an index of exactly 200 lines was declared cut when it was not. (ours)

Proven both ways: 3 fixtures from the report + 4 edge controls
(200 with/without newline, 201, 199) + a negative control. See docs/CONTEXTO.md.

⚠️ This is ARITHMETIC on the file, not an observation of what the session loaded.
   It predicts the cut; it does not measure it. CAP=25000 is documented and round — the bracket
   measured by @pjt222 is [24958, 25018).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hipo_config as HC

def measure(path, LINES=200, CAP=25000):
    """Which cap binds first, and where it cuts. CAP is the documented figure;
    pjt222's four-width bracket puts the real boundary in [24958, 25018)."""
    s = open(path, encoding='utf-8').read()
    lines = s.split('\n')
    if lines and lines[-1] == '':
        lines.pop()                      # trailing newline is not a line

    size_cut = None
    acc = 0
    for i, l in enumerate(lines, 1):
        acc += len((l + '\n').encode('utf-16-le')) // 2
        if acc > CAP:
            size_cut = i                 # first line that does NOT fit whole
            break

    line_cut = LINES + 1 if len(lines) > LINES else None

    cuts = [(c, w) for c, w in ((size_cut, 'size'), (line_cut, 'line')) if c]
    if not cuts:
        return f"no cut ({len(lines)}/{LINES} lines, {acc}/{CAP} units)"
    cut, which = min(cuts)               # whichever bites first
    return f"{which}-bound, first line dropped: {cut} (last kept: {cut - 1})"


# ---------------------------------------------------------------------------
# THE RULER IN THE PATH.
#
# measure() above is published in thread #82056 and is NOT touched. What was missing
# was a VOICE: `python3 memory-cap-probe.py` exited rc=0 with ZERO output — and silence
# is indistinguishable from "all is well". The ruler sat in a drawer; a ruler outside
# the path does not prevent the error.
#
# Measured on the day this was written: the live index was at 185/200 lines.
# 15 of slack, and BOTH cap warnings fire on PostToolUse:Edit — a session that
# only READS the index passes 200 without seeing anything (docs/CONTEXTO.md).
# ---------------------------------------------------------------------------

def metrics(path, LINES=200, CAP=25000):
    """The same figures as measure(), but as NUMBERS — measure() only gives prose.
    The selftest demands that both agree: a new instrument that disagrees with the
    published one is a wrong instrument."""
    s = open(path, encoding='utf-8').read()
    lines = s.split('\n')
    if lines and lines[-1] == '':
        lines.pop()
    units = sum(len((l + '\n').encode('utf-16-le')) // 2 for l in lines)
    # THE BINDING SLACK (docs/MEMORIA.md): the index has TWO ceilings and the one that
    # closes FIRST rules. The size slack becomes line-equivalents through the REAL density
    # of this index (units/line) — in a size-bound regime it is the smaller one.
    dens = units / len(lines) if lines else 1.0
    size_free_lines = int((CAP - units) / dens) if dens > 0 else LINES
    binding_free = min(LINES - len(lines), size_free_lines)
    return {'lines': len(lines), 'lines_cap': LINES, 'lines_free': LINES - len(lines),
            'units': units, 'units_cap': CAP, 'units_free': CAP - units,
            'size_free_lines': size_free_lines, 'binding_free': binding_free}


def _claude(home=None):
    """The Claude Code home: HIPO_CLAUDE_DIR from the configuration, or <home>/.claude when a
    (forged) home is given, which is how the selftest points the probe at its test trees."""
    return os.path.join(home, '.claude') if home else HC.CLAUDE_DIR


def stores(home=None):
    """Every MEMORY.md of every slug — INCLUDING the unreachable ones.

    The store slug derives from the cwd Claude runs from. Change the cwd, the
    slug changes, and the old store becomes unreachable without telling anyone: it is
    the 'store identity' class raised in thread #82056. Listing all of them is the only
    way for the ghost to show up."""
    import glob, os
    return sorted(glob.glob(os.path.join(_claude(home), 'projects', '*', 'memory', 'MEMORY.md')))


def _selftest():
    """Proves the ruler BOTH WAYS before any number counts.

    Positive control = cases that MUST cut. Negative control = cases that
    must NOT cut. A check that never failed on purpose is worth nothing."""
    import tempfile, os
    casos = [
        # (name,                  content,                           must cut?,       expected edge)
        ('199 lines',            'x\n' * 199,                       False, None),
        ('200 lines w/ newline',   'x\n' * 200,                      False, None),
        ('200 lines w/o newline',  'x\n' * 199 + 'x',                False, None),
        ('201 lines',             'x\n' * 201,                      True,  'line'),
        ('1 giant line',        'y' * 30000 + '\n',               True,  'size'),
        ('empty',                  '',                               False, None),
    ]
    ok = True
    for nome, conteudo, deve_cortar, borda in casos:
        fd, p = tempfile.mkstemp(suffix='.md'); os.close(fd)
        open(p, 'w', encoding='utf-8').write(conteudo)
        try:
            r = measure(p)
            cortou = not r.startswith('no cut')
            bate = (cortou == deve_cortar) and (not borda or r.startswith(borda))
            # the new instrument must agree with the published one
            m = metrics(p)
            coerente = (m['lines_free'] < 0) == (cortou and borda == 'line')
            bate = bate and coerente
            print(f"  {'ok  ' if bate else 'FAILED'}  {nome:24s} -> {r}")
            ok = ok and bate
        finally:
            os.unlink(p)
    return ok


# ---------------------------------------------------------------------------
# THE HOOK — SessionStart. (origin: thread #82056, @tonydzi).
#
# The question belongs to TURN ONE: which store did this session load, and how much slack.
# Without this, a session opened outside the usual directory works with an empty memory and
# does not know it.
#
# ⚠️ MEASURED SIZE — read before thinking this is big: 8 of 98 sessions (8.2%) ran
#    outside the usual directory. The original count said 38.7%, but it counted
#    subagents as sessions. This is ONE WARNING LINE, not a subsystem — and it makes no
#    extra memory be read: recall stays manual.
#
# THREE RULES, and none is a preference:
#   1. SILENCE when all is well. Noise on every session turns into blindness in 2 weeks.
#   2. FAIL-OPEN. Any exception = silence + rc=0. A session hook never blocks the
#      session. Proven by injecting the error, not by filtering.
#   3. ASK THE TARGET. The slug comes from the transcript_path the payload delivers — it
#      IS the store. Deriving from the cwd is the watcher, and only enters as a fallback.
# ---------------------------------------------------------------------------

def _slug_do_cwd(cwd):
    """Claude Code's derivation: every '/' and every '.' become '-'.
    Checked against 9 slugs on disk — including the ugly case
    '/srv/work/.claude/projects/-' -> '-srv-work--claude-projects--'."""
    return cwd.replace('/', '-').replace('.', '-')


def _store_da_sessao(payload, home=None):
    """(slug, source). The transcript_path is the TARGET: it names the real store.
    The cwd is the watcher — used only when the payload did not bring the target."""
    import os
    tp = (payload or {}).get('transcript_path') or ''
    if '/projects/' in tp:
        return tp.split('/projects/')[-1].split('/')[0], 'transcript_path'
    cwd = (payload or {}).get('cwd') or os.getcwd()
    return _slug_do_cwd(cwd), 'cwd'


def hook_linhas(payload, home=None, piso=15):
    """The lines the hook prints. EMPTY LIST = silence = all is well.

    PURE function (receives home): the selftest calls it directly against forged trees,
    with no subprocess and without touching the real memory."""
    import os, glob
    slug, fonte = _store_da_sessao(payload, home)
    base = os.path.join(_claude(home), 'projects')
    idx = os.path.join(base, slug, 'memory', 'MEMORY.md')

    if not os.path.exists(idx):
        # The named memory did not load. Say WHERE it is, otherwise the warning is
        # only a scare — and declare that the rest (map, oracle) arrived anyway.
        maiores = []
        for outro in stores(home):
            s = outro.split('/projects/')[-1].split('/memory/')[0]
            n = len([f for f in glob.glob(os.path.join(os.path.dirname(outro), '*.md'))
                     if os.path.basename(f) != 'MEMORY.md'])
            if n:
                maiores.append((n, s))
        maiores.sort(reverse=True)
        onde = (" — the memory lives in '%s' (%d memories), reachable from cwd '%s'"
                % (maiores[0][1], maiores[0][0],
                   maiores[0][1].replace('-', '/', 1) if maiores[0][1] != '-' else '/')
                ) if maiores else " — and no other store has memories"
        return ["[memory] store of this cwd: %s — MEMORY DID NOT LOAD%s" % (slug, onde),
                "[memory] map, oracle and triggers do NOT depend on the cwd and arrived; "
                "what is missing is only the named memory (docs/CONTEXTO.md)."]

    m = metrics(idx)
    out = []
    cortou = not measure(idx).startswith('no cut')
    if cortou:
        out.append("[memory] index TRUNCATED: %d/%d lines, %d/%d units — "
                   "what passes the cut does NOT arrive. Trimming is the user's decision."
                   % (m['lines'], m['lines_cap'], m['units'], m['units_cap']))
    elif m['binding_free'] < piso:
        out.append("[memory] index: %d/%d lines · %d/%d units — BINDING slack %d "
                   "(lines %d · size %d; floor %d) — bring a trimming proposal, do not execute."
                   % (m['lines'], m['lines_cap'], m['units'], m['units_cap'],
                      m['binding_free'], m['lines_free'], m['size_free_lines'], piso))
    return out


def _hook(argv):
    """The hook's mouth. Swallows EVERYTHING and exits 0 — including broken stdin, a payload
    without json, a nonexistent home. Silence by error must be indistinguishable from
    'all is well' FOR THE SESSION, without dying loudly or hanging."""
    import sys, json
    try:
        piso = 15
        if '--gate' in argv:
            i = argv.index('--gate')
            if i + 1 < len(argv):
                piso = int(argv[i + 1])
        raw = ''
        if not sys.stdin.isatty():
            raw = sys.stdin.read()
        try:
            payload = json.loads(raw) if raw.strip() else {}
        except Exception:
            payload = {}
        linhas = hook_linhas(payload, piso=piso)
        for l in linhas:
            print(l)
        _log_do_hook(payload, linhas)
    except Exception:
        pass                              # fail-open: the session never blocks
    return 0


def _log_do_hook(payload, linhas):
    """ONE line per firing, EVEN when the hook stays mute.

    Without this, 'ran and stayed silent' and 'did not run' are the same silence seen from
    outside — counting ZERO arrivals does not tell whether the channel closed or the emitter is
    mute. Silence is the rule for the CONTEXT, never for the disk.
    Fail-open inside fail-open: a log that breaks must not take the hook down."""
    import os, time
    try:
        slug, fonte = _store_da_sessao(payload)
        with open(os.path.join(HC.LOG_DIR,
                               'memoria-hook.log'), 'a', encoding='utf-8') as f:
            f.write("%s · slug=%s · source=%s · lines=%d%s\n"
                    % (time.strftime('%Y-%m-%d %H:%M:%S'), slug, fonte, len(linhas),
                       ' · MUTE (all ok)' if not linhas else ' · ' + linhas[0][:70]))
    except Exception:
        pass


def _selftest_hook():
    """The 7 controls, BOTH ways. Cases 6 and 7 are the ones that catch the defect
    of the class (fail-open) — and they are proven by INJECTING the error."""
    import os, tempfile, shutil, subprocess, sys

    def arvore(raiz, slugs):
        """slugs: {slug: (n_index_lines, n_memories)}; None = no store"""
        for slug, v in slugs.items():
            if v is None:
                os.makedirs(os.path.join(raiz, '.claude', 'projects', slug), exist_ok=True)
                continue
            nl, nm = v
            d = os.path.join(raiz, '.claude', 'projects', slug, 'memory')
            os.makedirs(d, exist_ok=True)
            open(os.path.join(d, 'MEMORY.md'), 'w').write('x\n' * nl)
            for k in range(nm):
                open(os.path.join(d, 'm%d.md' % k), 'w').write('c')
        return raiz

    ok = True
    casos = []

    # 1..5 — the pure function, against forged trees
    for nome, slugs, cwd, espera in [
        ('1 cwd / , high slack',      {'-': (145, 224)},                    '/',                  'silencio'),
        ('2 cwd /srv/work/repo',      {'-': (145, 224), '-srv-work-repo': None}, '/srv/work/repo', 'nao carregou'),
        ('3 nonexistent slug',        {'-': (145, 224)},                    '/tmp/xyz',           'nao carregou'),
        ('4 index 195 lines',         {'-': (195, 224)},                    '/',                  'folga'),
        ('5 index 201 lines',         {'-': (201, 224)},                    '/',                  'cortado'),
    ]:
        raiz = tempfile.mkdtemp()
        try:
            arvore(raiz, slugs)
            linhas = hook_linhas({'cwd': cwd}, home=raiz)
            txt = ' '.join(linhas).lower()
            if espera == 'silencio':
                bate = not linhas
            elif espera == 'nao carregou':
                bate = bool(linhas) and 'did not load' in txt
            elif espera == 'folga':
                bate = bool(linhas) and 'slack' in txt and 'truncated' not in txt
            else:
                bate = bool(linhas) and 'truncated' in txt
            casos.append((nome, bate, (linhas[0][:88] if linhas else '(silence)')))
            ok = ok and bate
        finally:
            shutil.rmtree(raiz, ignore_errors=True)

    # 6 and 7 — the REAL command of settings.json, with the error really INJECTED
    eu = os.path.abspath(__file__)
    tmpd = tempfile.mkdtemp()
    try:
        # 6 · probe missing/renamed: the settings command must exit 0 and mute
        ausente = os.path.join(tmpd, 'nao-existe.py')
        cmd6 = 'python3 %s --hook 2>/dev/null || true' % ausente
        r6 = subprocess.run(['bash', '-c', cmd6], input='{}', capture_output=True, text=True)
        b6 = r6.returncode == 0 and r6.stdout.strip() == ''
        casos.append(('6 probe missing', b6, 'rc=%d out=%r' % (r6.returncode, r6.stdout[:40])))
        ok = ok and b6

        # 7 · probe raising an exception: real copy with a raise planted
        quebrada = os.path.join(tmpd, 'quebrada.py')
        src = open(eu, encoding='utf-8').read()
        open(quebrada, 'w', encoding='utf-8').write(
            src.replace("if __name__ == '__main__':",
                        "raise RuntimeError('injected defect')\n\nif __name__ == '__main__':", 1))
        cmd7 = 'python3 %s --hook 2>/dev/null || true' % quebrada
        r7 = subprocess.run(['bash', '-c', cmd7], input='{}', capture_output=True, text=True)
        b7 = r7.returncode == 0 and r7.stdout.strip() == ''
        casos.append(('7 probe with exception', b7, 'rc=%d out=%r' % (r7.returncode, r7.stdout[:40])))
        ok = ok and b7

        # NEGATIVE CONTROL of the selftest itself: the GOOD probe, in the same command,
        # with an empty store, MUST speak. If it also stays mute, cases 6 and 7
        # passed for the wrong reason (the command would always be mute).
        raiz = tempfile.mkdtemp()
        try:
            arvore(raiz, {'-': (145, 224), '-tmp-vazio': None})
            env = dict(os.environ, HOME=raiz)
            cmd8 = 'python3 %s --hook 2>/dev/null || true' % eu
            r8 = subprocess.run(['bash', '-c', cmd8], input='{"cwd":"/tmp/vazio"}',
                                capture_output=True, text=True, env=env)
            b8 = r8.returncode == 0 and 'MEMORY DID NOT LOAD' in r8.stdout
            casos.append(('NC the command is NOT always mute', b8, r8.stdout.strip()[:88] or '(mute!)'))
            ok = ok and b8
        finally:
            shutil.rmtree(raiz, ignore_errors=True)
    finally:
        shutil.rmtree(tmpd, ignore_errors=True)

    for nome, bate, detalhe in casos:
        print("  %s  %-32s %s" % ('ok  ' if bate else 'FAILED', nome, detalhe))
    return ok


if __name__ == '__main__':
    import sys
    argv = sys.argv[1:]

    if '--hook' in argv:
        sys.exit(_hook(argv))

    if '--selftest-hook' in argv:
        print("HOOK SELFTEST — the 7 controls + the negative control of the test itself:")
        sys.exit(0 if _selftest_hook() else 1)

    if '--selftest' in argv:
        print("SELFTEST — edge controls both ways:")
        ok = _selftest()
        print("HOOK SELFTEST — the 7 controls + the negative control of the test itself:")
        ok = _selftest_hook() and ok
        sys.exit(0 if ok else 1)

    # gate: exits != 0 when the slack falls below N lines (default 15)
    piso = 15
    if '--gate' in argv:
        i = argv.index('--gate')
        if i + 1 < len(argv):
            piso = int(argv[i + 1])

    alvos = [a for a in argv if not a.startswith('--') and not a.isdigit()] or stores()
    if not alvos:
        print("COULD NOT SEARCH: no MEMORY.md found in ~/.claude/projects/*/memory/")
        sys.exit(2)                      # zero is not a result

    pior = 10 ** 9
    for p in alvos:
        m = metrics(p)
        slug = p.split('/projects/')[-1].split('/memory/')[0] if '/projects/' in p else p
        print(f"{slug}")
        print(f"    {m['lines']}/{m['lines_cap']} lines ({m['lines_free']} of slack) | "
              f"{m['units']}/{m['units_cap']} UTF-16 units ({m['units_free']} of slack)")
        print(f"    BINDING SLACK: {m['binding_free']} lines "
              f"(lines {m['lines_free']} · size {m['size_free_lines']} — the SMALLER decides)")
        print(f"    {measure(p)}")
        pior = min(pior, m['binding_free'])

    if len(alvos) > 1:
        print(f"\n⚠️  {len(alvos)} stores found. Only the one of the current cwd loads; "
              f"the others are UNREACHABLE (store identity, thread #82056).")

    if pior < piso:
        print(f"\n❌ SLACK BELOW THE FLOOR: {pior} < {piso} lines. "
              f"Trimming the index is the user's decision — "
              f"bring a proposal, do not execute.")
        sys.exit(1)
    print(f"\n✅ slack ok ({pior} lines, floor {piso})")
