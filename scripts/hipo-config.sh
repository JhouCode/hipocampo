# hipo-config.sh -- source this from a shell script to get the HIPO_* keys.
# It asks hipo_config.py, so bash and python resolve every path the same way.
# Usage:  . "$(dirname "${BASH_SOURCE[0]}")/hipo-config.sh"
_hipo_here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
eval "$(python3 "$_hipo_here/hipo_config.py")"
export HIPO_REPO HIPO_CLAUDE_DIR HIPO_WORKDIR HIPO_PROJECT_DIR HIPO_MEMORY_DIR HIPO_SETTINGS HIPO_STATE_DIR HIPO_LOG_DIR
unset _hipo_here
