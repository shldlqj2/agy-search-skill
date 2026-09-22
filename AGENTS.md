# Repository Agents Guide

## What

- This repository develops `agy-search-mcp`: a local stdio MCP server that exposes the installed Antigravity CLI as `agy_search` and `agy_fetch`.
- The canonical runtime is `src/agy_search_mcp/`; MCP installation is `install-mcp.sh` or `install-mcp.ps1`.
- `.agents/skills/` is a retained legacy compatibility and verification surface, not the default interface for new installations.
- Runtime traces, fetched artifacts, and source indexes belong under the configured MCP state directory or `_workspace/agy-search/`; never treat them as source code or commit them.

## Why

- AGY is generative, so fluent output or a plausible URL is not proof. The MCP backend must preserve traces and return search URLs only when AGY actually read them in the same request.
- AGY performs all web search and page retrieval. Do not add a Codex-native-search fallback.
- A tool request is one directly awaited AGY child process. Do not implement Codex subagents, watcher agents, status polling, or automatic AGY retry loops.

## How

- Run MCP tests: `python3 -m unittest discover -s tests -v`
- Run retained legacy contract tests: `python3 -m unittest discover -s .agents/skills/agy-search/tests -v`
- Check formatting whitespace: `git diff --check`
- Before live testing, confirm `agy models` succeeds. Use a dedicated ignored data directory with `AGY_SEARCH_MCP_DATA_DIR`.
- Read [plan.md](plan.md), [handoff.md](handoff.md), and [the MCP design record](docs/agy-search-mcp-plan.ko.md) before changing retrieval, timeout, evidence, or migration behavior.
