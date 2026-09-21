# Research Notes

## Domain Summary

`agy-search` treats Antigravity as a generative retrieval producer, not as a trusted search index. Expected deliverables are a trace, structured sources and claims, an independent audit, and a citation-grounded answer or explicit refusal.

The repository was initially empty. The local environment contains `agy` 1.2.4, Python 3, and curl; `jq` is absent. After authentication, `agy models` succeeded and a live current-version query used both `search_web` and `read_url_content`.

## Findings That Shaped the Harness

- Official headless mode supports JSON, NDJSON, JSON Schema, terminal statuses, tool steps, and cached authentication. This enables deterministic provenance checks: https://antigravity.google/docs/cli/headless/
- Antigravity exposes built-in `search_web` and `read_url_content` tools: https://antigravity.google/docs/sdk/tools/
- Custom agents can constrain tool lists, so retrieval does not need command or write privileges: https://antigravity.google/docs/subagents?tab=cli
- AGY 1.2.1 introduced `excludeDefaultComponents`; the live canary showed that omitting it left default command tools available despite a curated `tools` list: https://antigravity.google/changelog
- ALCE shows that answer quality and citation quality are separate and that fluent answers can lack complete citation support: https://arxiv.org/abs/2305.14627
- SAFE validates long-form answers by decomposing them into atomic facts, searching, and judging support fact by fact: https://deepmind.google/research/publications/85420/

## Live Observation

On 2026-09-21, a query for the current stable Python release successfully read python.org pages and returned a plausible, traceable answer. The NDJSON trace also showed repeated viewing of generated source content and roughly 124k total tokens for one lookup. This justifies schema-constrained results, finite timeouts, stateless runs, one targeted retry, and no unbounded producer-reviewer loop.

The first end-to-end runner canary correctly failed: AGY declared a second source that it fetched through `run_command`/`curl` rather than the required `read_url_content` provenance path. This exposed default-tool inheritance and led to both `excludeDefaultComponents: true` and explicit dangerous-tool exposure/use gates.

A second canary and CLI log inspection showed `Agent "agy-web-researcher" not found, falling back to default`, reproducing the open custom-agent CLI problem https://github.com/google-antigravity/antigravity-cli/issues/585. The current adapter therefore does not claim tool restriction that the runtime failed to apply: it runs the default agent in `--sandbox` from the run directory, treats broad tool exposure as a visible warning, and rejects any actual dangerous-tool use.

The third canary avoided dangerous tools and read both relevant official pages, but declared an unobserved related URL (`/downloads/windows/`) in its final source object. The exact read-URL membership gate rejected it. The producer prompt now requires copying the literal `read_url_content` argument and forbids canonical, redirect-target, parent/child, platform-specific, or related URL substitution.

## Task Inventory

- classify request and risk
- formulate time-bounded subquestions
- retrieve and read sources through AGY
- validate tool provenance and URL membership mechanically
- independently verify claim entailment, quality, freshness, coverage, and conflict
- synthesize supported claims or refuse
- preserve trace and review artifacts for audit

## Reuse Notes

- The harness pattern, skill frontmatter, deterministic handoffs, reviewer status, and failure tests follow the repository-local Harness guidance.
- AGY-specific behavior is isolated in the runtime adapter and runner so another search backend can replace it without rewriting the evidence policy.
