---
name: agy-search-verifier
description: Independently audit AGY search results by checking source existence, source contents, claim entailment, citation coverage, freshness, and conflicts.
---

# AGY Search Verifier

## When to Use

- Use after `agy-search` retrieval and before publishing factual results.
- Use when an AGY answer includes URLs, quotations, dates, comparisons, or factual recommendations.
- Do not use to generate a replacement answer before auditing the producer artifact.

## Required Inputs

- original question and time boundary
- `_workspace/agy-search/<run>/01_result.json`
- `_workspace/agy-search/<run>/01_trace.ndjson`
- declared risk tier

## Workflow

1. Confirm the mechanical audit passed; if not, mark affected claims `insufficient` without repairing the producer output silently.
2. Atomize compound claims so each row can receive one verdict.
3. Reopen each cited URL independently. Confirm identity, publisher, date, and relevant passage; a reachable page is not automatically supporting evidence.
4. Compare the claim with the cited passage:
   - `supported`: the passage directly entails the claim within its scope and date.
   - `contradicted`: the passage or a stronger authoritative source conflicts with it.
   - `insufficient`: the page is inaccessible, merely related, ambiguous, stale, or does not establish the claim.
5. Check citation completeness: every externally verifiable central claim needs support. Check citation correctness: every attached source must actually support that claim.
6. Search independently for counterevidence on central, surprising, or consequential claims. Prefer primary sources and record material disagreement.
7. Write the review table. Never upgrade confidence because the prose sounds certain or because multiple pages repeat the same unsourced statement.

## Outputs

Write `_workspace/agy-search/<run>/02_verification.md` with:

| Claim | Verdict | Evidence inspected | Freshness | Reason |
| --- | --- | --- | --- | --- |

End with `PASS`, `FIX`, or `REDO`:

- `PASS`: all central claims supported at the required risk tier.
- `FIX`: bounded deletions, qualifications, or citation changes are sufficient.
- `REDO`: retrieval missed the question, relied on fabricated provenance, or has pervasive unsupported claims.

## Validation

- Read the source and the claim side by side.
- Separate source existence, claim support, and source quality; none implies the others.
- Cite the exact URLs inspected and preserve unresolved uncertainty.
- Permit one bounded producer retry. After that, return the partial answer or refuse.
