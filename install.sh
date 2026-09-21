#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
source_root="${script_dir}/.agents/skills"
target_root="${CODEX_HOME:-${HOME}/.codex}/skills"
dry_run=false
make_backup=true
skills=(agy-search agy-search-verifier)

usage() {
  printf '%s\n' \
    'Install agy-search and agy-search-verifier into the global Codex skill directory.' \
    '' \
    'Usage: ./install.sh [--target DIRECTORY] [--dry-run] [--no-backup]' \
    '' \
    'Defaults:' \
    '  target = $CODEX_HOME/skills when CODEX_HOME is set' \
    '  target = $HOME/.codex/skills otherwise'
}

while (($#)); do
  case "$1" in
    --target)
      [[ $# -ge 2 ]] || { printf 'install.sh: --target requires a directory\n' >&2; exit 2; }
      target_root="$2"
      shift 2
      ;;
    --dry-run)
      dry_run=true
      shift
      ;;
    --no-backup)
      make_backup=false
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      printf 'install.sh: unknown option: %s\n' "$1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ -z "$target_root" || "$target_root" == "/" || "$target_root" == "$HOME" || "$target_root" == "${CODEX_HOME:-__unset__}" ]]; then
  printf 'install.sh: refusing unsafe target directory: %s\n' "$target_root" >&2
  exit 2
fi

for skill in "${skills[@]}"; do
  source_dir="${source_root}/${skill}"
  skill_file="${source_dir}/SKILL.md"
  [[ -f "$skill_file" ]] || { printf 'install.sh: missing %s\n' "$skill_file" >&2; exit 1; }
  grep -Eq '^name:[[:space:]]*' "$skill_file" || { printf 'install.sh: missing name frontmatter in %s\n' "$skill_file" >&2; exit 1; }
  grep -Eq '^description:[[:space:]]*' "$skill_file" || { printf 'install.sh: missing description frontmatter in %s\n' "$skill_file" >&2; exit 1; }
done

if "$dry_run"; then
  for skill in "${skills[@]}"; do
    printf 'Would install %s -> %s\n' "${source_root}/${skill}" "${target_root}/${skill}"
  done
  exit 0
fi

mkdir -p "$target_root"
timestamp="$(date +%Y%m%d-%H%M%S)"

install_one() {
  local skill="$1"
  local source_dir="${source_root}/${skill}"
  local destination="${target_root}/${skill}"
  local staging
  local backup=""

  staging="$(mktemp -d "${target_root}/.${skill}.install.XXXXXX")"
  cp -R "${source_dir}/." "$staging/"

  [[ -f "${staging}/SKILL.md" ]] || {
    rmdir "$staging" 2>/dev/null || true
    printf 'install.sh: staged skill is invalid: %s\n' "$skill" >&2
    return 1
  }

  if [[ -e "$destination" ]]; then
    if "$make_backup"; then
      backup="${target_root}/.${skill}.backup.${timestamp}.$$"
      mv "$destination" "$backup"
      printf 'Backed up existing %s to %s\n' "$skill" "$backup"
    else
      find "$destination" -depth -mindepth 1 -delete
      rmdir "$destination"
    fi
  fi

  if ! mv "$staging" "$destination"; then
    if [[ -n "$backup" && -e "$backup" && ! -e "$destination" ]]; then
      mv "$backup" "$destination"
    fi
    printf 'install.sh: failed to activate %s\n' "$skill" >&2
    return 1
  fi

  if [[ -f "${destination}/scripts/agy_search.py" ]]; then
    chmod +x "${destination}/scripts/agy_search.py"
  fi
  printf 'Installed %s to %s\n' "$skill" "$destination"
}

for skill in "${skills[@]}"; do
  install_one "$skill"
done

if ! command -v agy >/dev/null 2>&1; then
  printf 'Warning: agy is not currently on PATH; the skill is installed but searches cannot run yet.\n' >&2
fi
if ! command -v python3 >/dev/null 2>&1; then
  printf 'Warning: python3 is not currently on PATH; install Python 3 before running the search adapter.\n' >&2
fi

printf 'Global installation complete. Restart Codex or reload skills if the new skills are not visible.\n'
