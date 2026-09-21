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

## Workflow

### 1. Frame the query

Write the question, time boundary, ambiguous terms, and acceptance criteria to `_workspace/agy-search/<run>/00_request.md`. Split multi-part requests into independently verifiable subquestions. Do not split a tiny lookup merely to create parallel work.

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

Use `agy-search-verifier` on `01_result.json` and `01_trace.ndjson`. The verifier reopens cited sources independently and classifies each atomic claim as `supported`, `contradicted`, or `insufficient`. The producer's own `verification` field is only a lead, never final evidence.

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
