# ADR_001: Multi-source MCP server with an advisory adapter layer

> **Status:** Proposed · **Date:** 2026-10-07 · **Decision owner:** RAMA-L7

---

## Context

The MCP server (`rta/api/mcp_server.py`) exposes the frozen deterministic Ṛta
backend as eight engine tools over stdio (JSON-RPC 2.0). It is a thin adapter:
it imports the JSON layer from `rta/api/api_server.py`, never modifies the
authority modules, and adds no runtime dependencies.

That server answers "what does the engine say about this SDC?". It does not
answer the two questions that surround every real engineering investigation:

* "Has someone already reported this?" — the fix may exist upstream.
* "Where is this documented, and which rule produced it?" — the rule catalogue
  and feature docs ship with the tool, but nothing exposes them to an assistant.

We now want the server to connect **three or more real data sources** and to be
verifiable as a portfolio artefact for Forward Deployed Engineer work — where
the graded skill is connecting enterprise systems against real constraints
(authentication, rate limits, partial failure), not writing another demo.

Constraints that shape the decision:

* **Determinism / Trust Model.** READY ≠ STA signoff, coverage ≠ correctness,
  and the engine can never fake a PASS. Any new surface must not create a path
  where a verdict is produced by anything other than the frozen engine.
* **Clean-room and CI safety.** The tool is offline-capable and pure standard
  library (`pyyaml` is the only runtime dependency). A test suite of 1,425
  tests must not become flaky because an upstream API throttled us.
* **Packaging.** `setuptools` ships explicit `py-modules` plus `rta*`; the
  console script is `rta-mcp`. New code must fit that shape without new
  dependencies.
* **Local-first posture.** Verification data stays on the machine
  (`Local-first · Reproducible` is part of the product's identity).
* **Resource cost.** Operators may run this alongside several other MCP
  servers; each stdio server is another process with another interpreter.

## Decision

> We choose **one MCP server with an internal advisory adapter layer**
> (`rta/sources/`) exposing GitHub issues, a local documentation corpus and an
> owned SQLite store, gated by a role capability boundary and an audit trail,
> for all source connectivity in Ṛta.

Sources are **advisory**: they supply context, provenance and history, and can
never produce or modify a verdict.

## Alternatives Considered

| Alternative | Description | Pros | Cons |
|---|---|---|---|
| A | Three separate MCP servers (`rta-mcp`, `rta-issues-mcp`, `rta-docs-mcp`) | Independent failure domains; each can be enabled per client | Triples process/interpreter cost; no single call can combine engine + sources; three capability boundaries to keep in sync; three registration steps per client; cannot express "verdict + why" atomically |
| **B** | **One server + internal adapter layer (chosen)** | **One process; one capability boundary; cross-source composition; one registration; engine contract provably untouched; adapters testable in isolation** | **Larger single module surface; a crash in an adapter could affect the server process (mitigated: adapters never raise)** |
| C | Shared MCP gateway/proxy fronting all sources | Central policy, open-core friendly | Over-engineering for a local stdio tool; adds a port and a second auth surface; conflicts with local-first and with "one process" resource goals; another component to secure and document |
| D | Call sources from inside `api_server.py` | Fewer moving parts | Violates the frozen-backend contract directly: the HTTP/JSON layer is consumed by the CLI, Web UI and reports — sources would leak into every surface and into verdict code paths |
| E | Hosted knowledge base only (Notion/Confluence) | Stronger third-party auth story | Requires a credential and a network for documentation that already ships in-repo; breaks offline/clean-room use; Confluence is paid |

## Rationale

**Operating principle: deterministic over probabilistic, and disclose rather
than infer.** The adapter layer keeps the engine's authority intact by
construction: adapters return context envelopes, and the composite tool returns
the engine payload *verbatim* under `engine` with source material in a separate
`context` object. There is no field through which a source could assert a
verdict, and `rta_source_store_record` computes its payload by calling the
engine — a caller cannot hand it a verdict to persist.

**Resource discipline.** One stdio process, one interpreter, no port, no daemon.
Alternative A triples process cost for no functional gain; alternative C adds a
port and another auth boundary to a local tool.

**Testability without network.** Because adapters are injected rather than
constructed inline, the failure matrix is asserted against a scripted transport.
The suite stays offline and deterministic while still proving rate-limit,
auth-failure, timeout, malformed-body and breaker behaviour.

**Honest degradation.** Every envelope carries `ok`, `degraded`, `cached`,
`fetched_at` and a stable `error.code`, and a failure with a usable cache entry
returns the stale value explicitly marked as stale.

## Consequences

### Positive

- One call (`rta_investigate`) returns the engine verdict plus matching docs and
  matching open issues, with provenance — the "last mile" an engineer actually
  wants.
- The capability boundary is explicit and deny-by-default: `reader` <
  `engineer` < `maintainer`, with the single mutating tool additionally behind
  `RTA_MCP_ALLOW_MUTATIONS`.
- The audit trail exists without becoming a second copy of customer data:
  arguments are stored as SHA-256 digests, never as values.
- Zero new runtime dependencies; the offline and clean-room guarantees hold.
- The engine contract is provably unchanged: the suite asserts that MCP tool
  output is byte-identical to a direct `api_server` call.

### Negative

- `rta/api/mcp_server.py` and its documentation grow; the source adapters are
  new code to maintain (≈1,000 lines plus tests).
- A misconfigured upstream can produce `degraded: true` responses, which an
  assistant may surface as a caveat — acceptable, and preferable to a silent
  failure.
- Role configuration is environmental (`RTA_MCP_ROLE`), so the effective
  capability is not visible in the client's own config; `rta_sources_health`
  reports it to compensate.

### Risks

- **Cache served as fresh.** Mitigated: cached responses are always
  `cached=true` and `degraded=true` with the original `fetched_at`.
- **Breaker hiding the root cause.** Mitigated: authentication and quota
  failures deliberately do not trip the breaker, so the real code
  (`AUTH_INVALID`, `RATE_LIMITED`) is always what surfaces first.
- **Network flakiness in CI.** Mitigated: no test in the source suite performs a
  network call; adapters are injected.
- **Audit log leaking content.** Mitigated and tested: the audit stores digests,
  and a test asserts a planted SDC string is absent from the database bytes.
- **Credential leakage.** Mitigated: tokens come from the environment, are sent
  only as an `Authorization` header, and tests assert the token never appears in
  any envelope or in `health()`.

### Trust impact

- What the tool **validates** is unchanged: only the deterministic engine
  produces readiness verdicts, coverage or gate results.
- What the tool now **discloses**: which external references were consulted,
  whether they were stale, and whether any source failed — with stable codes.
- The engine cannot misrepresent its scope through this surface, because the
  composite returns the engine payload unchanged and labels context as advisory
  in the response itself (`advisory_note`).

## Evidence

* **Frozen engine contract:** `tests/test_mcp_multi_source.py` asserts the eight
  engine tools keep their names, order and required parameters, and that
  `rta_analyze`, `rta_lint`, `rta_snapshot` and `rta_rules` return output
  byte-identical to direct `rta/api/api_server` calls.
* **Advisory-only sources:** the same file asserts the composite returns the
  engine payload verbatim, that `context` exposes exactly `{docs, issues}`, and
  that with GitHub failing the engine payload is still byte-identical and the
  response is marked `degraded`.
* **Failure matrix:** `tests/test_sources_github.py` drives every upstream
  status from the documented table — 200, 401, 403 with and without quota
  exhaustion, 404, 422, 5xx, timeout, malformed body — plus breaker opening and
  stale-cache fallback.
* **Deny-by-default access:** `tests/test_mcp_access.py` asserts the role
  ladder, that unknown tools are denied for every role, that an unrecognised
  role falls back to `reader`, and that mutations require the explicit switch.
* **Audit privacy:** asserts a planted SDC string never reaches the database
  file and that digests are stable across key ordering.
* **Golden suite / regression:** full suite **1,563 passed** (baseline 1,425
  before this change; 138 new tests), exit code 0, offline.
  Run: `python -m pytest -q`.

## Review

| Date | Reviewer | Outcome |
|---|---|---|
| | | |

## Status

- [x] Proposed
- [ ] Accepted
- [ ] Rejected (with rationale)
- [ ] Superseded by ADR_NNN

---

*ADRs are the memory of the architecture. Write them so that someone joining the team in two years can understand why this choice was made.*
