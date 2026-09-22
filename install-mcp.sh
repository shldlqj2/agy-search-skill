#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
python_bin="${PYTHON:-python3}"
mcp_name="agy-search"
state_root="${XDG_STATE_HOME:-${HOME}/.local/state}/agy-search-mcp"
dry_run=false

usage() {
  printf '%s\n' \
    'Install and register the AGY Search MCP server for Codex.' \
    '' \
    'Usage: ./install-mcp.sh [--python PATH] [--name NAME] [--data-dir DIRECTORY] [--dry-run]' \
    '' \
    'The installer installs this package into the selected Python user site, then registers' \
    'a local stdio MCP server with Codex. It does not remove any legacy Codex skills.'
}

while (($#)); do
  case "$1" in
    --python)
      [[ $# -ge 2 ]] || { printf 'install-mcp.sh: --python requires a path\n' >&2; exit 2; }
      python_bin="$2"
      shift 2
      ;;
    --name)
      [[ $# -ge 2 ]] || { printf 'install-mcp.sh: --name requires a value\n' >&2; exit 2; }
      mcp_name="$2"
      shift 2
      ;;
    --data-dir)
      [[ $# -ge 2 ]] || { printf 'install-mcp.sh: --data-dir requires a directory\n' >&2; exit 2; }
      state_root="$2"
      shift 2
      ;;
    --dry-run)
      dry_run=true
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      printf 'install-mcp.sh: unknown option: %s\n' "$1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

[[ "$mcp_name" =~ ^[A-Za-z0-9_-]+$ ]] || {
  printf 'install-mcp.sh: --name may contain only letters, digits, hyphens, and underscores\n' >&2
  exit 2
}
command -v "$python_bin" >/dev/null 2>&1 || {
  printf 'install-mcp.sh: Python executable not found: %s\n' "$python_bin" >&2
  exit 1
}
python_bin="$(command -v "$python_bin")"
"$python_bin" - <<'PY'
import sys
if sys.version_info < (3, 10):
    raise SystemExit("install-mcp.sh: Python 3.10 or newer is required")
PY

if ! command -v codex >/dev/null 2>&1; then
  printf 'install-mcp.sh: Codex CLI is required to register the MCP server\n' >&2
  exit 1
fi
if ! command -v agy >/dev/null 2>&1; then
  printf 'install-mcp.sh: agy is not on PATH; install/authenticate AGY before registering\n' >&2
  exit 1
fi

config_root="${CODEX_HOME:-${HOME}/.codex}"
config_path="${config_root}/config.toml"
if codex mcp get "$mcp_name" >/dev/null 2>&1; then
  printf 'install-mcp.sh: MCP server %q already exists. Remove or rename it before registering this one.\n' "$mcp_name" >&2
  exit 1
fi

if "$dry_run"; then
  printf 'Would install package: %q -m pip install --user --upgrade %q\n' "$python_bin" "$script_dir"
  printf 'Would create state directory: %q\n' "$state_root"
  printf 'Would register: codex mcp add %q --env AGY_SEARCH_MCP_DATA_DIR=%q -- %q -m agy_search_mcp.server\n' \
    "$mcp_name" "$state_root" "$python_bin"
  printf 'Would set startup_timeout_sec=30 and tool_timeout_sec=660 in %q\n' "$config_path"
  exit 0
fi

mkdir -p "$state_root"
"$python_bin" -m pip install --user --upgrade "$script_dir"
codex mcp add "$mcp_name" --env "AGY_SEARCH_MCP_DATA_DIR=${state_root}" -- "$python_bin" -m agy_search_mcp.server

"$python_bin" - "$config_path" "$mcp_name" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
name = sys.argv[2]
text = path.read_text(encoding="utf-8")
header = f"[mcp_servers.{name}]\n"
if header not in text:
    raise SystemExit(f"Could not locate the new MCP section in {path}")
addition = "startup_timeout_sec = 30\ntool_timeout_sec = 660\n"
text = text.replace(header, header + addition, 1)
path.write_text(text, encoding="utf-8")
PY

printf 'Installed and registered MCP server %q. Restart Codex or start a new session before using it.\n' "$mcp_name"
printf 'Existing agy-search skills were left untouched; remove them only after confirming the MCP server works.\n'
