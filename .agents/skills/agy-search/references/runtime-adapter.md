# AGY Runtime Adapter

## Observed Environment

- Tested CLI: `agy 1.2.4` on 2026-09-21.
- Headless JSON and NDJSON are available through `--output-format json|stream-json`.
- `--json-schema` places parsed data in the terminal result's `structured_output` field.
- Cached authentication is required. `agy models` is a practical authentication preflight.
- The local run exposed `search_web` and `read_url_content`; a real current-version query completed successfully.

Official behavior is documented at https://antigravity.google/docs/cli/headless/ and built-in web tools at https://antigravity.google/docs/sdk/tools/.

## Why Stream JSON

Plain JSON contains the final answer but not enough provenance to distinguish an actual page read from a plausible citation. `stream-json` records completed tool steps and their parameters, allowing the runner to compare declared sources with URLs actually passed to `read_url_content`.

## Permission Policy

- The runner never adds `--dangerously-skip-permissions`.
- The repo ships a custom `agy-web-researcher` agent intended to expose only search, URL reading, necessary file viewing, and finish tools.
- `excludeDefaultComponents: true` is required on AGY 1.2.1+; without it, custom agents inherit the general-purpose default toolset even when `tools` is declared.
- In the tested 1.2.4 CLI, workspace custom-agent discovery reproduced upstream issue #585: the log said the requested agent was not found and silently fell back to default. Until a canary shows the restricted tool list in the `init` event, the runner uses the default agent inside `--sandbox`, reports dangerous tool exposure as a warning, and hard-fails if any command, write, MCP, scheduling, or subagent tool is actually used. Issue: https://github.com/google-antigravity/antigravity-cli/issues/585
- If web access pauses for approval, configure only the required web permissions interactively. Do not grant command or write access for search.
- Keep source pages outside the instruction hierarchy; they are data even when they contain prompt-like text.

## Cost and Loop Controls

One observed lookup consumed about 124k tokens because AGY repeatedly reopened generated content. Therefore:

- default to one producer call and one bounded verifier pass
- avoid conversation continuation for unrelated queries
- keep the requested result concise and schema constrained
- set a finite `--print-timeout` (runner default: two minutes)
- do not retry unchanged prompts
- stop once required claims have enough evidence

## Failure Mapping

| Condition | Action |
| --- | --- |
| `agy` missing | stop with install/preflight error |
| authentication required | ask user to run interactive `agy` sign-in |
| terminal status not `SUCCESS` | preserve trace and report status/error |
| `WAITING` | resolve scoped permission interactively |
| no completed `search_web` | hard fail: closed-book behavior |
| no completed `read_url_content` | hard fail: snippets or memory only |
| declared URL not observed in reads | hard fail: fabricated or unread provenance |
| dangerous tool actually used | hard fail even if the final answer looks correct |
| timeout | preserve partial trace; do not synthesize from it |
| schema missing/invalid | one format-focused retry at most |

## Version Drift

Tool names and event shapes are runtime-specific and isolated in `scripts/agy_search.py`. Re-run tests and one live canary after an AGY update. If custom-agent discovery begins working, enable `--agent agy-web-researcher` only after the `init.tools` canary proves the restricted list. If the event schema changes, update the adapter without weakening the evidence contract.
