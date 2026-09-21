# AGY Search Harness Team

## Goal

Turn the installed `agy` CLI into a traceable search backend whose final answers contain only independently supported claims. The harness optimizes for falsifiability and graceful refusal, not maximum answer rate.

## Architecture

The outer pattern is a **Pipeline** with a local **Producer–Reviewer** gate. Query planning precedes retrieval; the retriever produces evidence; a verifier independently reviews it; an editor synthesizes only approved claims.

Independent subquestions may use bounded fan-out during retrieval, but all branches must share the same request snapshot, write separate artifacts, and return to one verifier. Default delegation depth is one.

## Roles

| Role | Responsibility | Implementation | Writes |
| --- | --- | --- | --- |
| Search coordinator | scope question, set freshness/risk, own final acceptance | `agy-search` skill | `00_request.md`, `final.md` |
| Evidence retriever | search and read pages; emit structured sources and claims | sandboxed default AGY through runner; repo-local custom-agent adapter remains disabled pending CLI #585 | `01_trace.ndjson`, `01_result.json` |
| Evidence verifier | independently reopen sources and judge claim entailment/coverage | `agy-search-verifier` skill | `02_verification.md` |
| Answer editor | remove failed claims, preserve caveats, attach citations | coordinator role | `final.md` |

The coordinator is the synthesis owner. The retriever never approves itself, and the editor may not restore rejected claims.

## Phase Order and Completion Gates

### 0. Intake

- Input: user question, date, scope, and risk tier.
- Output: `_workspace/agy-search/<run>/00_request.md`.
- Complete when ambiguous terms and evidence threshold are explicit.

### 1. Retrieval

- Run the AGY adapter in stateless headless mode.
- Outputs: `01_trace.ndjson` and `01_result.json`.
- Complete only when terminal status and all mechanical provenance gates pass.

### 2. Independent Review

- Reopen cited sources; assess claim entailment, quality, freshness, completeness, and conflict.
- Output: `02_verification.md` ending in `PASS`, `FIX`, or `REDO`.
- Complete when every central claim has a verdict and evidence trail.

### 3. Synthesis

- Build `final.md` only from supported claims.
- Complete when citations and limitations are disclosed.

## Handoff Contract

- Paths are deterministic beneath `_workspace/agy-search/<run>/`.
- `01_trace.ndjson` is append-only evidence and must not be rewritten to make a run pass.
- `01_result.json` includes the terminal structured output and runner audit.
- Review cites source URLs and claim IDs. Final synthesis maps back to reviewed claims.

## Failure Policy

- Authentication, permission, timeout, and non-success status: preserve trace, stop, and report the exact class.
- Missing search/read evidence, dangerous-tool use, or unread declared URL: hard fail and `REDO`.
- Isolated unsupported claim: `FIX` by deletion or qualification.
- Pervasive unsupported claims or wrong question: at most one targeted `REDO`.
- Conflicting authoritative sources: report the conflict; never resolve it by majority vote alone.
- Partial fan-out failure: use remaining branches only if they still satisfy the evidence threshold and disclose the missing branch.

## Parallelism and Ownership

Parallelize only independent, read-heavy subquestions. Each worker owns a distinct `01_<branch>_*` artifact pair. No parallel writer may modify the skill, schema, shared trace, review, or final answer. The coordinator merges; the verifier reviews the merged claim inventory. Maximum delegation depth is one.

## Removable Runtime Logic

AGY-specific event parsing, tool names, timeout defaults, and recovery wording live in `scripts/agy_search.py` and `references/runtime-adapter.md`. The stable contract—actual retrieval, claim-level evidence, independent verification, and refusal—must survive replacement of AGY.

## Validation Scenarios

1. Normal/current fact with official source and successful tool provenance.
2. Fabricated premise with evidence-backed rejection or `insufficient`.
3. Plausible but unread URL, which must hard fail.
4. Credible source conflict, which must remain visible.
5. Authentication or permission failure with no synthesis.
6. Local repository lookup near miss, which should not select this skill.

## Acceptance Criteria

- contract tests pass
- normal live canary executes search and URL-read tools
- fabricated or unread URLs fail mechanically
- verifier checks source contents against claims
- no retry loop exceeds one targeted redo
- critical-risk requests never become autonomous operational advice
