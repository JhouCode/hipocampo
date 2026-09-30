"""hipo_config -- the single place where Hipocampo resolves paths.

Every script used to carry absolute paths of the machine it was born on. They all come
from here now, in this order (first hit wins):

  1. an environment variable with the same name (e.g. HIPO_MEMORY_DIR=...);
  2. the file `hipocampo.conf` at the repository root (KEY=VALUE lines, `#` comments,
     `~` and `$VAR` expanded);
  3. the default below, relative to the repository or to $HOME.

Keys:
  HIPO_REPO         the repository that holds docs/ and scripts/ (default: this checkout)
  HIPO_CLAUDE_DIR   the Claude Code home (default: ~/.claude)
  HIPO_WORKDIR      the directory you open sessions from; it names the project slug
                    (default: HIPO_REPO)
  HIPO_PROJECT_DIR  the session store of that project (default:
                    HIPO_CLAUDE_DIR/projects/<slug of HIPO_WORKDIR>)
  HIPO_MEMORY_DIR   the native auto-memory folder, where MEMORY.md lives
                    (default: HIPO_PROJECT_DIR/memory)
  HIPO_SETTINGS     the settings.json the runtime reads (default: HIPO_CLAUDE_DIR/settings.json)
  HIPO_STATE_DIR    scratch state of the hooks (default: $TMPDIR/hipocampo)
  HIPO_LOG_DIR      hook logs (default: HIPO_CLAUDE_DIR)

Shell scripts read the same keys through `hipo-config.sh`, which calls this module, so the
two languages cannot disagree.
"""
import os
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_REPO_DEFAULT = _HERE.parent


def slug(path):
    """Claude Code's derivation of a project folder name: every '/' and '.' becomes '-'."""
    return str(path).replace('/', '-').replace('.', '-')


def _read_conf(repo):
    conf = {}
    f = Path(repo) / 'hipocampo.conf'
    if f.is_file():
        for line in f.read_text(encoding='utf-8').splitlines():
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            k, v = line.split('=', 1)
            conf[k.strip()] = os.path.expanduser(os.path.expandvars(v.strip().strip('"\'')))
    return conf


def load():
    """Returns a dict with every key resolved to an absolute path string."""
    repo = os.environ.get('HIPO_REPO') or str(_REPO_DEFAULT)
    conf = _read_conf(repo)

    def get(key, default):
        return os.environ.get(key) or conf.get(key) or default

    cfg = {'HIPO_REPO': repo}
    cfg['HIPO_CLAUDE_DIR'] = get('HIPO_CLAUDE_DIR', str(Path.home() / '.claude'))
    cfg['HIPO_WORKDIR'] = get('HIPO_WORKDIR', repo)
    cfg['HIPO_PROJECT_DIR'] = get('HIPO_PROJECT_DIR', os.path.join(
        cfg['HIPO_CLAUDE_DIR'], 'projects', slug(cfg['HIPO_WORKDIR'])))
    cfg['HIPO_MEMORY_DIR'] = get('HIPO_MEMORY_DIR', os.path.join(cfg['HIPO_PROJECT_DIR'], 'memory'))
    cfg['HIPO_SETTINGS'] = get('HIPO_SETTINGS', os.path.join(cfg['HIPO_CLAUDE_DIR'], 'settings.json'))
    cfg['HIPO_STATE_DIR'] = get('HIPO_STATE_DIR', os.path.join(
        os.environ.get('TMPDIR', '/tmp'), 'hipocampo'))
    cfg['HIPO_LOG_DIR'] = get('HIPO_LOG_DIR', cfg['HIPO_CLAUDE_DIR'])
    return cfg


CFG = load()
REPO = CFG['HIPO_REPO']
CLAUDE_DIR = CFG['HIPO_CLAUDE_DIR']
PROJECT_DIR = CFG['HIPO_PROJECT_DIR']
MEMORY_DIR = CFG['HIPO_MEMORY_DIR']
SETTINGS = CFG['HIPO_SETTINGS']
STATE_DIR = CFG['HIPO_STATE_DIR']
LOG_DIR = CFG['HIPO_LOG_DIR']


if __name__ == '__main__':
    # `python3 hipo_config.py` prints KEY=VALUE lines; hipo-config.sh evals them.
    import shlex
    for k, v in CFG.items():
        print('%s=%s' % (k, shlex.quote(v)))
