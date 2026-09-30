#!/usr/bin/env python3
"""check-private -- refuses a commit that carries private data into this public repository.

WHAT IT SCANS
  Every tracked or untracked-but-not-ignored file of the repository (`git ls-files -co
  --exclude-standard`), or the files given on the command line, or a whole folder with --dir.

WHAT IT LOOKS FOR -- two lists, and the split is deliberate:
  1. GENERIC patterns, in clear below: IPv4 addresses, home folders, the store folder of a
     project whose slug is one or two characters, e-mail addresses, company/person document
     ids, UUIDs, access tokens, MAC addresses, a "not public" mark. They name no one.
  2. YOUR private terms: names, hosts, projects, clients, and the SHAPES of your own internal
     vocabulary (host shorthands, internal codes, citation formats). They live OUTSIDE the
     tracked tree, in `.private-terms` at the repository root (listed in .gitignore) or in the
     file named by $HIPO_PRIVATE_TERMS. A list of private words committed to a public repo would
     publish the very words it protects -- and so would a committed regex of your code format.
     One term per line, `#` comments:
         word                    a literal, case-insensitive
         re:<regex>              a regex, case-insensitive (scope it with `(?-i:...)`)
         re:name=<label>:<regex> the same, reported under `private-term:<label>`
     An unlabelled regex is reported as `private-term:re:<regex>`, so every hit names its rule.
  Matches that are public on purpose (the repository's own address, the article's URL) are
  cleared by `guards/private-allow.txt`, one regex per line, applied to the line BEFORE the
  search, so an allowed span can never hide a private one elsewhere on the same line.

VERDICT
  rc 0 and one green line when nothing is found; rc 1 with `file:line  pattern  -> text` for
  every hit. Without a private-terms file it still runs the generic list and says so in yellow:
  a silent green on half a list reads as "clean".

USAGE
  check-private.py                 scan the repository (this is what the pre-commit runs)
  check-private.py FILE...         scan these files
  check-private.py --dir PATH      scan a folder that is not a git repo (read-only)
  check-private.py --count         per-pattern totals instead of the hit list
  check-private.py --selftest      positive and negative controls in a temporary folder
"""
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

GENERIC = [
    ('ipv4', r'(?<![\w.])(?!127\.0\.0\.1\b)(?!0\.0\.0\.0\b)(?:\d{1,3}\.){3}\d{1,3}(?![\w.])'),
    ('home-folder', r'/home/[A-Za-z0-9_.-]+|/Users/[A-Za-z0-9_.-]+|[A-Za-z]:\\\\?Users'),
    #   A project store is named after the folder the agent ran from; a slug of one or two
    # characters means a root or near-root folder, which says how the machine is laid out. A
    # real slug (`-home-user-app`) already carries a home folder and is caught above.
    ('short-store-slug', r'projects/[-\w]{1,2}/'),
    ('email', r'[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+\.[A-Za-z]{2,}'),
    ('company-or-person-id', r'\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b|\b\d{3}\.\d{3}\.\d{3}-\d{2}\b'),
    ('uuid', r'\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b'),
    ('token', r'ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|sk-ant-[A-Za-z0-9-]{10,}'
              r'|AKIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY|xox[abp]-[A-Za-z0-9-]{10,}'),
    ('mac-address', r'\b[0-9a-fA-F]{2}(?::[0-9a-fA-F]{2}){5}\b'),
    ('not-public-mark', r'N[ÃA]O P[ÚU]BLICO|NOT PUBLIC\]'),
]

TEXT_SKIP = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.ico', '.pdf', '.woff', '.woff2', '.gz', '.zip'}


def load_terms(root):
    src = os.environ.get('HIPO_PRIVATE_TERMS') or str(Path(root) / '.private-terms')
    p = Path(src)
    if not p.is_file():
        return None, src
    out = []
    for line in p.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if line.startswith('re:name=') and ':' in line[8:]:
            label, rx = line[8:].split(':', 1)
            out.append(('private-term:' + label.strip(), rx))
        elif line.startswith('re:'):
            out.append(('private-term:re:' + line[3:], line[3:]))
        else:
            out.append(('private-term', re.escape(line)))
    return out, src


def is_term(name):
    return name.startswith('private-term')


def load_allow(root):
    p = Path(root) / 'guards' / 'private-allow.txt'
    if not p.is_file():
        return []
    return [re.compile(l.strip(), re.I) for l in p.read_text(encoding='utf-8').splitlines()
            if l.strip() and not l.strip().startswith('#')]


def repo_files(root):
    r = subprocess.run(['git', '-C', str(root), 'ls-files', '-co', '--exclude-standard', '-z'],
                       capture_output=True, text=True)
    if r.returncode != 0:
        return None
    return [Path(root) / f for f in r.stdout.split('\0') if f]


def walk(folder):
    for d, dirs, fs in os.walk(folder):
        dirs[:] = [x for x in dirs if x not in ('.git', '__pycache__')]
        for f in fs:
            yield Path(d) / f


def scan(files, patterns, allow, base):
    hits = []
    compiled = [(n, re.compile(rx, re.I if is_term(n) else 0)) for n, rx in patterns]
    for f in files:
        if f.suffix.lower() in TEXT_SKIP or not f.is_file() or f.is_symlink():
            continue
        try:
            text = f.read_text(encoding='utf-8')
        except (UnicodeDecodeError, OSError):
            continue
        rel = os.path.relpath(f, base)
        if f.resolve() == (ROOT / 'guards' / 'private-allow.txt').resolve():
            continue   # the allow list is the public exceptions themselves
        #   The checker's own source spells the generic patterns and plants test strings: on it,
        # only the private-term list runs (a private word pasted here is still caught).
        own = f.resolve() == Path(__file__).resolve()
        for i, line in enumerate(text.splitlines(), 1):
            clean = line
            for a in allow:
                clean = a.sub(' ', clean)
            for name, rx in compiled:
                if own and not is_term(name):
                    continue
                for m in rx.finditer(clean):
                    hits.append((rel, i, name, m.group(0)))
    return hits


def main(argv):
    count = '--count' in argv
    argv = [a for a in argv if a != '--count']
    if argv[:1] == ['--selftest']:
        return selftest()
    terms, terms_src = load_terms(ROOT)
    allow = load_allow(ROOT)
    patterns = GENERIC + (terms or [])
    if argv[:1] == ['--dir']:
        base = Path(argv[1]).resolve()
        files = list(walk(base))
    elif argv:
        base = Path.cwd()
        files = [Path(a) for a in argv]
    else:
        base = ROOT
        files = repo_files(ROOT)
        if files is None:
            print('check-private: not a git repository; use --dir', file=sys.stderr)
            return 2
    hits = scan(files, patterns, allow, base)
    if terms is None:
        print('\033[33m! check-private: no private-terms file (%s): only the generic list ran\033[0m' % terms_src)
    if count:
        tot = {}
        for _, _, n, _ in hits:
            tot[n] = tot.get(n, 0) + 1
        names = [n for n, _ in GENERIC] + sorted({n for n in tot if is_term(n)})
        for n in names:
            print('%-22s %d' % (n, tot.get(n, 0)))
        print('%-22s %d' % ('TOTAL', len(hits)))
        return 1 if hits else 0
    if hits:
        print('\033[31m✗ check-private: %d private occurrence(s) in %d file(s)\033[0m'
              % (len(hits), len({h[0] for h in hits})))
        for rel, i, n, t in hits:
            print('    %s:%d  %-20s -> %s' % (rel, i, n, t))
        return 1
    print('\033[32m✓ check-private: %d file(s), no private occurrence\033[0m' % len(files))
    return 0


def selftest():
    """Negative control: a clean folder comes out green. Positive control: a planted file with an
    IP, a home folder and a private host alias comes out red, naming each. Regex-term control: a
    labelled `re:name=` term of the terms file fires under its own label, and its `(?-i:...)`
    scope holds (the lower-case spelling stays green)."""
    passed = 0
    with tempfile.TemporaryDirectory() as t:
        t = Path(t)
        (t / 'guards').mkdir()
        (t / '.private-terms').write_text('myhost-live\nre:name=ticket-code:(?-i:\\bTK-\\d{3}\\b)\n',
                                          encoding='utf-8')
        (t / 'clean.md').write_text('A clean line about hooks and memory; tk-123 is lower case.\n',
                                    encoding='utf-8')
        terms, _ = load_terms(t)
        pats = GENERIC + terms
        neg = scan(list(walk(t)), pats, [], t)
        neg = [h for h in neg if h[0] != '.private-terms']
        print('  negative control (clean folder): %s' % ('green' if not neg else 'RED %r' % neg))
        passed += not neg
        (t / 'planted.md').write_text('ssh myhost-live to 10.0.0.7 and cd /home/someone/repo\n',
                                      encoding='utf-8')
        pos = [h for h in scan(list(walk(t)), pats, [], t) if h[0] == 'planted.md']
        names = sorted({h[2] for h in pos})
        want = ['home-folder', 'ipv4', 'private-term']
        print('  positive control (planted file): %s' % ', '.join('%s -> %s' % (h[2], h[3]) for h in pos))
        passed += names == want
        (t / 'ticket.md').write_text('see TK-123 in the tracker\n', encoding='utf-8')
        rxh = [h for h in scan(list(walk(t)), pats, [], t) if h[0] == 'ticket.md']
        print('  regex-term control (planted file): %s'
              % (', '.join('%s -> %s' % (h[2], h[3]) for h in rxh) or 'GREEN (missed)'))
        passed += [(h[2], h[3]) for h in rxh] == [('private-term:ticket-code', 'TK-123')]
    print('selftest: %s' % ('%d of 3' % passed if passed == 3 else 'FAILED (%d of 3)' % passed))
    return 0 if passed == 3 else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
