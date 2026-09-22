# AGY Search MCP

[한국어](README.ko.md) | English

`agy-search-mcp` makes the locally installed Antigravity CLI (`agy`) available to Codex as two local MCP tools:

- `agy_search` — search the current web and return only result URLs that AGY opened in the same request
- `agy_fetch` — read one URL, or a `source_id` returned by `agy_search`, through AGY

AGY is the only web-search and page-read backend. There is no automatic Codex-native-search fallback.

## Why MCP instead of a skill?

The previous skill workflow asked Codex to coordinate retrieval, review, and synthesis in its prompt. This MCP server moves the bounded retrieval job into ordinary local code. A tool call starts one sandboxed AGY child process, waits for it directly, and returns its final result. It does **not** create Codex subagents, watcher agents, completion polls, or model-driven retry loops.

AGY is still generative, not a deterministic search index. The server therefore keeps a per-request NDJSON trace and rejects a search response when AGY did not both search and open every returned URL. It rejects dangerous AGY tool use too. That provenance gate is not a truth guarantee: use primary sources and independently check important claims.

## Requirements

- Codex CLI with local stdio MCP support
- `agy` on `PATH`, with an authenticated session (`agy models` succeeds)
- Python 3.10 or later and `pip`
- Linux/macOS with Bash, or Windows PowerShell

The implementation was live-tested with AGY 1.2.7 and MCP Python SDK 2.2.0.

## Install

Run the MCP installer from this repository. It installs the Python package to the selected Python user's site, registers a local `agy-search` server in Codex, and sets a 660-second client tool timeout so a deep AGY request can finish.

Linux/macOS:

```bash
chmod +x install-mcp.sh
./install-mcp.sh
```

Windows PowerShell:

```powershell
.\install-mcp.ps1
```

Preview without changing anything:

```bash
./install-mcp.sh --dry-run
```

```powershell
.\install-mcp.ps1 -DryRun
```

The default server state directory is `~/.local/state/agy-search-mcp` on Linux/macOS and `%LOCALAPPDATA%\agy-search-mcp` on Windows. It stores traces and the small local `source_id` index; it may contain retrieved content and should be treated accordingly. Use `--data-dir` or `-DataDir` to change it.

Restart Codex or start a new session after registration. The installer does not remove existing `agy-search` skills; confirm the MCP server first, then remove legacy skills yourself if they cause unwanted skill routing.

### Manual registration

If installation must be done manually, install this package with the same Python that Codex will launch, then register it:

```bash
python3 -m pip install --user --upgrade .
codex mcp add agy-search \
  --env "AGY_SEARCH_MCP_DATA_DIR=$HOME/.local/state/agy-search-mcp" \
  -- python3 -m agy_search_mcp.server
```

Add these two lines under `[mcp_servers.agy-search]` in `$CODEX_HOME/config.toml` (or `~/.codex/config.toml`):

```toml
startup_timeout_sec = 30
tool_timeout_sec = 660
```

## Tool contract

`agy_search` accepts a natural-language `query` plus optional `max_results` (1–10), domain allowlist, source-language preference, freshness date, and depth:

| Depth | Default AGY deadline | Intended use |
| --- | ---: | --- |
| `quick` | 180 seconds | narrow lookup |
| `standard` | 300 seconds | normal research |
| `deep` | 600 seconds | multi-source or conflict-sensitive research |

An explicit `timeout_seconds` (1–600) overrides that policy. The default normal search remains five minutes. `agy_fetch` defaults to five minutes and supports the same explicit override.

Search results have a server-local `source_id`, URL, short AGY-grounded summary, excerpt, and provenance. Pass that ID to `agy_fetch` when more page content is needed. `agy_fetch` labels returned content as either:

- `agy_read_artifact`: text extracted from AGY's own read artifact for that request
- `agy_generated_extract`: AGY's clearly labeled fallback extract when no safe artifact is available

Do not represent the latter as a verbatim quote. A source ID persists only while the server's state directory is retained; a direct `url` can always be fetched again through AGY.

The server allows one active AGY request. A concurrent call receives an explicit `busy` error rather than waiting in a hidden queue or polling for status. There is intentionally no `status` or `poll` tool.

## Evidence and failure behavior

Each call writes a separate directory beneath the configured state directory:

```text
runs/<request_id>/
  trace.ndjson
  stderr.log
  run.json
  mcp-response.json
source-index.json
```

On authentication, permission, provenance, timeout, cancellation, or process failures, partial trace and stderr files are preserved. A failure is returned as a structured error result, never silently converted to an empty search result. The server does not automatically rerun AGY.

Only AGY is asked to perform web retrieval. The rest of the answer, including citation style and critical-claim verification, remains the caller's responsibility. For medical, legal, financial, security, or irreversible decisions, inspect authoritative sources and use qualified human judgment.

## Development and validation

Install the package in the current environment, then run both the MCP tests and the retained legacy contract tests:

```bash
python3 -m pip install --user -e .
python3 -m unittest discover -s tests -v
python3 -m unittest discover -s .agents/skills/agy-search/tests -v
git diff --check
```

For a local live fetch after `agy models` confirms authentication:

```bash
AGY_SEARCH_MCP_DATA_DIR=_workspace/agy-search/manual-mcp \
python3 -m agy_search_mcp.server
```

The last command starts a stdio server, so use it through an MCP client rather than a terminal prompt. Runtime evidence under `_workspace/agy-search/` is intentionally not committed.

## Migration and project docs

- [Migration design and research notes](docs/agy-search-mcp-plan.ko.md)
- [Resumable implementation plan](plan.md)
- [Current handoff state](handoff.md)
- [Legacy skill execution contract](.agents/skills/agy-search/references/team-spec.md)

The legacy skill sources remain in `.agents/skills/` for compatibility and for their contract tests. Their `install.sh` / `install.ps1` flow is still available only for users intentionally keeping the prompt-driven skill workflow; new installations should use the MCP installers above.
