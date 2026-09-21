# agy-search skill

[한국어](README.ko.md) | English

Use the local Antigravity CLI (`agy`) as a traceable web-search backend from Codex. The skill records AGY's tool trace, requires claim-level sources, rejects citations to pages that were not actually read, and routes the result through an independent verification contract before synthesis.

## Why this exists

An agent can return a fluent answer while inventing a URL, citing a real but unread page, or attaching a related source that does not support the claim. `agy-search` treats AGY as an untrusted retrieval producer rather than a deterministic search index.

The harness separates four responsibilities:

1. scope the question and freshness requirement
2. search and read sources with AGY
3. audit provenance and independently verify atomic claims
4. synthesize only supported claims, preserving conflicts and uncertainty

These are logical stages in one primary Codex agent, not separate Codex subagents. The
skill prohibits subagent fan-out and watcher agents: Codex starts one AGY CLI child
process, waits for it directly, and performs verification and synthesis in the same run.

## Requirements

- Codex with skill discovery enabled
- Antigravity CLI `agy` on `PATH`
- an authenticated AGY session (`agy models` should succeed)
- Python 3
- Linux/macOS with Bash, or Windows with PowerShell

The currently tested AGY version is 1.2.4.

## Global installation

Clone this repository, then run the installer from its root. It installs both `agy-search` and `agy-search-verifier` into the global Codex skill directory.

Linux/macOS:

```bash
chmod +x install.sh
./install.sh
```

Windows PowerShell:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\install.ps1
```

Default destinations:

- `$CODEX_HOME/skills` when `CODEX_HOME` is defined
- `~/.codex/skills` on Linux/macOS otherwise
- `$HOME\.codex\skills` on Windows otherwise

Use a custom destination when testing:

```bash
./install.sh --target /tmp/codex-skills --dry-run
```

```powershell
.\install.ps1 -Target C:\temp\codex-skills -DryRun
```

Existing installations are moved to timestamped backups before replacement. Pass `--no-backup` or `-NoBackup` only when you intentionally want replacement without recovery. Restart Codex or reload skills after installation.

This skill belongs in Codex's global skill directory. Do not install it as an Antigravity skill: it invokes `agy` as an external backend, so installing it inside AGY would create the wrong execution boundary.

## Usage

Invoke the skill naturally or explicitly:

```text
$agy-search Find the latest stable Python release and verify it against the official release page.
```

The bundled adapter can also be run directly from the installed skill directory.
Its default AGY timeout is five minutes. Codex may choose a shorter finite timeout for a
tiny lookup or up to ten minutes for a complex multi-source review.

Linux/macOS:

```bash
python3 ~/.codex/skills/agy-search/scripts/agy_search.py \
  --out-dir _workspace/agy-search/python-release \
  --query "What is the latest stable Python release?"
```

Windows PowerShell:

```powershell
py -3 "$HOME\.codex\skills\agy-search\scripts\agy_search.py" `
  --out-dir "_workspace\agy-search\python-release" `
  --query "What is the latest stable Python release?"
```

## Hallucination controls

The mechanical audit requires:

- a successful terminal result
- completed `search_web` and `read_url_content` calls
- every declared source URL to exactly match a URL observed in a completed read call
- every factual claim to reference declared source IDs
- answer citations to reference only declared sources
- no command, write, MCP, scheduling, or subagent tool use
- a parseable, schema-constrained result and preserved NDJSON trace

A mechanical pass proves provenance consistency, not truth. The `agy-search-verifier` skill must still reopen sources and classify claims as `supported`, `contradicted`, or `insufficient`. High-risk medical, legal, financial, security, or irreversible decisions require authoritative sources and qualified human review.

## Artifacts

Each run uses deterministic handoffs under `_workspace/agy-search/<run>/`:

```text
00_request.md
01_trace.ndjson
01_result.json
01_stderr.log
02_verification.md
final.md
```

The raw trace is audit evidence and should not be rewritten to make a failed run pass.

## Validation

```bash
python3 -m unittest discover -s .agents/skills/agy-search/tests -v
```

The repository includes contract tests for closed-book answers, unread URLs, unknown source IDs, missing and grouped citations, and dangerous-tool usage. Live canaries cover a normal current-fact query and a fabricated premise.

## Known AGY limitation

AGY CLI 1.2.4 reproduced [google-antigravity/antigravity-cli#585](https://github.com/google-antigravity/antigravity-cli/issues/585): a requested workspace custom agent can silently fall back to the default agent. The runner therefore uses the default agent in `--sandbox`, reports broad tool exposure, and fails closed if a dangerous tool is actually used. The restricted custom-agent adapter remains disabled until `init.tools` proves it loaded correctly.

See the [team contract](.agents/skills/agy-search/references/team-spec.md), [hallucination controls](.agents/skills/agy-search/references/hallucination-control.md), and [validation record](docs/harness/agy-search/validation.md) for the full design.
