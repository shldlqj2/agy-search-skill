# AGY Search Execution Contract

## Goal

Turn the installed `agy` CLI into a traceable search backend whose final answers contain only independently supported claims. The harness optimizes for falsifiability and graceful refusal, not maximum answer rate.

## Architecture

The outer pattern is a single-agent **Pipeline** with a local **Producer–Reviewer** gate. Query planning precedes retrieval; AGY produces evidence; the primary Codex agent independently reviews it and synthesizes only approved claims.

All pipeline stages run in one primary Codex agent. The role boundaries below separate evidence responsibilities; they are not instructions to create Codex subagents. Codex subagent delegation, fan-out, reviewer agents, and completion-watcher agents are prohibited for this skill. The primary agent waits for the AGY child process directly.

## Roles

| Role | Responsibility | Implementation | Writes |
| --- | --- | --- | --- |
| Search coordinator | scope question, set freshness/risk, own final acceptance | primary Codex agent using `agy-search` | `00_request.md`, `final.md` |
| Evidence retriever | search and read pages; emit structured sources and claims | one sandboxed AGY CLI child process through the runner; repo-local custom-agent adapter remains disabled pending CLI #585 | `01_trace.ndjson`, `01_result.json` |
| Evidence verifier | independently reopen sources and judge claim entailment/coverage | same primary Codex agent applying `agy-search-verifier` | `02_verification.md` |
| Answer editor | remove failed claims, preserve caveats, attach citations | same primary Codex agent | `final.md` |

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
- Multi-part request with partial evidence: publish only supported parts and disclose the missing evidence; do not create branches or workers to retry them.

## Execution and Ownership

Do not use Codex subagents or parallel workers. The primary Codex agent owns the request,
review, and final answer. The AGY runner owns one producer artifact pair per attempt and
blocks until its child process exits. Multi-part questions remain one request and are
reviewed sequentially. The sole retry allowance is one targeted producer rerun for an
explicit evidence gap.

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
