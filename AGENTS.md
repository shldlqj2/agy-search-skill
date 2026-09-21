# Repository Agents Guide

## What

- This repository develops `agy-search`, a repo-local skill that uses the installed Antigravity CLI as an evidence-producing web search backend.
- The canonical workflow is `.agents/skills/agy-search/SKILL.md`; the installable team contract is `.agents/skills/agy-search/references/team-spec.md`.
- Runtime evidence belongs under `_workspace/agy-search/` and must not be treated as source code.

## Why

- `agy` is a generative agent, not a deterministic search index. A fluent answer or a plausible URL is never proof by itself.
- Search, source reading, claim verification, and synthesis stay separate so unsupported claims can be rejected without discarding useful retrieval work.

## How

- Run contract tests: `python3 -m unittest discover -s .agents/skills/agy-search/tests -v`
- Run a search: `python3 .agents/skills/agy-search/scripts/agy_search.py --out-dir _workspace/agy-search/manual --query "..."`
- Install globally on Linux/macOS: `./install.sh`
- Install globally on Windows PowerShell: `.\install.ps1`
- Read `.agents/skills/agy-search/references/team-spec.md` before changing role boundaries or verification gates.
