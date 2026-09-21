---
name: agy-search
description: Use the local Antigravity CLI as a traceable web-search backend for current or source-sensitive questions, with claim-level citations and hallucination gates.
---

# AGY Search

## When to Use

- Use for web research, current facts, source discovery, comparisons, or answers that need traceable citations.
- Use when the caller explicitly asks to search with `agy` or Antigravity CLI.
- Do not use for repository-only search, calculations, transformations of already supplied text, or casual questions that do not benefit from web evidence.
- Do not use it as the sole authority for medical, legal, financial, safety-critical, or irreversible decisions; require authoritative-source review and human judgment.

## Required Inputs

- the exact research question
- freshness requirement or `current as of` date when relevant
- desired scope, language, and source preferences when provided
- risk tier: `standard`, `high`, or `critical` (default: `standard`)

Before the first run, confirm `agy --version` succeeds and `agy models` does not request sign-in. Headless mode uses cached credentials.

## Execution Model

Minimize orchestration cost: the primary Codex agent owns query framing, AGY execution,
verification, and synthesis in one continuous run. Coordinator, retriever, verifier, and
editor are logical pipeline stages, not Codex subagents.

- Do not spawn Codex subagents, workers, reviewers, coordinators, or watcher agents for
  this skill.
- Do not delegate independent subquestions. Keep them in one request and verify their
  claims sequentially in the primary agent.
- The runner starts one sandboxed AGY CLI child process for the retrieval attempt and
  waits for that process directly. Do not create an agent merely to wait for completion.
- A targeted retry, when allowed, remains in the same primary agent and does not relax
  the one-retry limit.

The runner timeout defaults to five minutes. The primary agent may set a different finite
`--timeout` without asking the user when the expected workload warrants it: about two
minutes for a tiny lookup, five minutes for a normal request, and up to ten minutes for a
complex or high-risk multi-source review. Do not extend a timed-out run automatically
unless its preserved trace shows useful progress and the single targeted-retry allowance
still applies.

## Workflow

### 1. Frame the query

Write the question, time boundary, ambiguous terms, and acceptance criteria to `_workspace/agy-search/<run>/00_request.md`. Represent multi-part requests as independently verifiable claim groups within the same request; do not dispatch them to separate agents.

### 2. Retrieve with the constrained agent

Linux/macOS:

```bash
python3 .agents/skills/agy-search/scripts/agy_search.py \
  --out-dir _workspace/agy-search/<run> \
  --query "<question>"
```

Windows PowerShell:

```powershell
py -3 .agents\skills\agy-search\scripts\agy_search.py `
  --out-dir _workspace\agy-search\<run> `
  --query "<question>"
```

When installed globally, resolve the skill directory from the runtime's discovered skill path rather than assuming the repository-local `.agents/skills` prefix.

The runner requests schema-constrained output, records the full NDJSON trace, runs in AGY's sandbox from an isolated run directory, and enforces provenance gates. It never passes `--dangerously-skip-permissions`. The repo includes a narrower `agy-web-researcher` custom-agent adapter, but the runner leaves it disabled while AGY CLI issue #585 causes headless custom-agent discovery to fall back silently to the default agent.

If the runner reports authentication failure, run `agy` interactively and sign in. If it reports `WAITING`, fix scoped web permissions interactively; do not weaken permissions globally just to finish the run.

### 3. Apply the mechanical gates

Treat `.agents/skills/agy-search/references/hallucination-control.md` as mandatory. At minimum:

- terminal status must be `SUCCESS`
- `search_web` and `read_url_content` must both appear as completed tool steps
- every cited source URL must exactly match a URL observed in a completed `read_url_content` call
- every substantive claim must cite at least one known source ID
- `answer` citation markers must reference only declared sources
- contradictions and unavailable evidence must remain visible

A passing structure check means the provenance chain is internally consistent. It does not prove the claim is true.

### 4. Verify claims independently

In the same primary Codex agent, apply `agy-search-verifier` to `01_result.json` and `01_trace.ndjson`. Independence means reopening and judging the evidence separately from the producer output; it does not require another Codex agent. Classify each atomic claim as `supported`, `contradicted`, or `insufficient`. The producer's own `verification` field is only a lead, never final evidence.

- `standard`: verify every central claim; one primary source may be enough for an uncontroversial fact.
- `high`: require a primary source plus an independent corroborating source for every consequential claim.
- `critical`: do not publish an operational recommendation from AGY alone. Provide sources and uncertainties for qualified human review.

Allow at most one targeted retrieval retry for missing evidence. Do not repeatedly re-prompt until a preferred answer appears.

### 5. Synthesize conservatively

Build the final answer only from claims marked `supported` by the independent verifier. Cite sources next to the claims they support. Distinguish publication date, event date, and retrieval date. Report meaningful disagreement and explicitly say when the evidence is insufficient.

## Outputs

- `_workspace/agy-search/<run>/00_request.md`: scoped request and risk tier
- `_workspace/agy-search/<run>/01_trace.ndjson`: immutable AGY tool/result trace
- `_workspace/agy-search/<run>/01_result.json`: structured producer result plus mechanical audit
- `_workspace/agy-search/<run>/02_verification.md`: claim-by-claim independent review
- `_workspace/agy-search/<run>/final.md`: supported synthesis and disclosed gaps

## Validation

- Run `python3 -m unittest discover -s .agents/skills/agy-search/tests -v` after changes.
- Test one normal current-fact query, one fabricated-premise query, and one source-conflict query.
- A missing or failed branch lowers confidence; synthesis must never invent substitute evidence.
- Preserve rejected claims and reasons in `02_verification.md` for auditability.

## References

- `references/hallucination-control.md` — threat model, gates, retry and refusal rules
- `references/runtime-adapter.md` — CLI behavior, permissions, cost controls, and failure handling
- `assets/search-result.schema.json` — producer output contract
- `references/team-spec.md` — role topology, handoffs, ownership, and failure policy
