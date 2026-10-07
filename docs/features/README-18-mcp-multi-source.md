# Ṛta MCP Server — context sources and the failure matrix

Feature 16 exposes the frozen engine as MCP tools. This feature adds **advisory
context sources** around those tools: a local documentation corpus, a GitHub
issue tracker, and an owned SQLite store of recorded runs.

- **What it is** — 6 additional MCP tools (14 total) over the same stdio server
- **What it is not** — a second opinion. Sources are advisory and cannot produce
  or change a verdict
- **New dependencies** — none (stdlib `urllib`, `sqlite3`, `json`, `hashlib`)
- **Network required** — only for `rta_source_issues_search` and the issue half
  of `rta_investigate`; everything else works offline
- **Architecture decision** — `rta/docs/company/ADR_001_mcp_multi_source.md`

---

## 1. The three sources

| Source | Kind | Credential | Network | What it answers |
|---|---|---|---|---|
| `corpus` | Local documentation corpus | none | no | "Where is this documented? Which rule fires this?" |
| `github` | Issue tracker (GitHub REST) | optional `GITHUB_TOKEN` | yes | "Has this already been reported?" |
| `store` | SQLite store you own | none | no | "What did we run before, and on what evidence?" |

The corpus indexes `docs/`, `rta/docs/`, `samples/`, `engineer_test_kit/` and
the top-level `README.md` / `CHANGELOG.md` / `CONTRIBUTING.md` by default.

---

## 2. Tools

### Engine tools (unchanged — authority)

`rta_analyze`, `rta_lint`, `rta_convert`, `rta_generate`, `rta_snapshot`,
`rta_diff`, `rta_corners`, `rta_rules` — see feature 16. Their names, order and
required parameters are frozen and asserted by tests.

### Source tools (new — advisory)

| Tool | Purpose | Key arguments |
|---|---|---|
| `rta_sources_health` | Per-source configuration, breaker state, cache stats, active role. **Never calls the network.** | — |
| `rta_source_docs_search` | Search the local corpus | `query` (required), `limit`, `path_filter` |
| `rta_source_issues_search` | Search issues | `query`, `state` (`open`/`closed`/`all`), `labels`, `limit`, `include_pull_requests` |
| `rta_source_store_query` | Read recorded runs, evidence and the audit trail | `limit`, `verdict`, `rule_id`, `run_id`, `audit`, `tool` |
| `rta_source_store_record` | Record an engine run + provenance — **the only mutating tool** | `sdc` (required), `netlist`, `top`, `run_id`, `evidence[]` |
| `rta_investigate` | Engine analysis + matching docs + matching issues in one call | `sdc` (required), `netlist`, `top`, `baseline`, `gate`, `context_limit`, `issue_limit` |

### Response shape

Every source tool returns the same stable envelope:

```json
{
  "ok": true,
  "source": "github",
  "data": { "issues": [], "returned": 0, "auth_mode": "anonymous" },
  "degraded": false,
  "cached": false,
  "fetched_at": "2026-10-07T17:07:48Z",
  "error": null,
  "note": "anonymous GitHub access — set GITHUB_TOKEN for reliable results"
}
```

`rta_investigate` composes the two worlds without mixing them:

```json
{
  "authority": "engine",
  "engine": { "...": "byte-identical to a plain rta_analyze call" },
  "engine_facts": { "verdict": "REVIEW_REQUIRED", "rule_ids": ["SDC-028", "SDC-029"] },
  "context": { "docs": { "...": "corpus envelope" }, "issues": { "...": "github envelope" } },
  "sources_used": ["corpus", "github"],
  "degraded": false,
  "advisory_note": "Context sources are advisory. The verdict above was produced only by the deterministic engine; no source can change it."
}
```

---

## 3. Access control (deny by default)

| Role | Capability |
|---|---|
| `reader` *(default)* | the 8 engine tools, `rta_sources_health`, `rta_source_docs_search` |
| `engineer` | reader + `rta_source_issues_search`, `rta_source_store_query`, `rta_investigate` |
| `maintainer` | engineer + `rta_source_store_record` (still requires the mutation switch) |

* A tool that appears in **no** role is allowed for **nobody**.
* An unset or unrecognised `RTA_MCP_ROLE` falls back to `reader` — never upward.
* Mutations need `RTA_MCP_ALLOW_MUTATIONS=1` in addition to `maintainer`.
* A denied call returns `isError: true` with `code: "FORBIDDEN"` naming the role
  that would be required, and is recorded in the audit trail.

```json
{
  "code": "FORBIDDEN",
  "decision": { "allowed": false, "role": "reader", "tool": "rta_source_issues_search",
                "reason": "DENY_ROLE_LACKS_TOOL", "required_role": "engineer" }
}
```

---

## 4. Reliability policy

| Control | Default | Environment variable |
|---|---|---|
| Request timeout | 5 s | `RTA_SOURCE_TIMEOUT_S` |
| Retries | 1 (timeouts, connection errors, 5xx only) | `RTA_SOURCE_RETRIES` |
| Breaker threshold | 3 consecutive failures | `RTA_SOURCE_BREAKER_THRESHOLD` |
| Breaker cooldown | 60 s | `RTA_SOURCE_BREAKER_COOLDOWN_S` |
| Cache TTL | 300 s | `RTA_SOURCE_CACHE_TTL_S` |
| Max items per call | 25 | `RTA_SOURCE_MAX_ITEMS` |
| Cache location | `~/.rta/source-cache` | `RTA_SOURCE_CACHE_DIR` |
| Store location | `~/.rta/store/rta_store.db` | `RTA_STORE_DB` |
| Disable the store | off | `RTA_STORE_DISABLE=1` |
| GitHub target repo | `RAMA-L7/rta-constraint-intelligence` | `RTA_GITHUB_REPO` |
| GitHub token | none (anonymous) | `GITHUB_TOKEN`, `GH_TOKEN`, `RTA_GITHUB_TOKEN` |

The cache and store live **outside the repository** by default, so running the
server never leaves untracked files in a clean checkout.

---

## 5. Failure matrix

Observed behaviour for each source, per failure. Asserted by
`tests/test_sources_github.py` (scripted transport — the suite never touches the
network) and `tests/test_sources_corpus.py`.

| Source | Failure | Code | Retried | Trips breaker | What the assistant sees |
|---|---|---|---|---|---|
| github | Timeout | `TIMEOUT` | yes (1×) | yes | error + `retry_after` when known; cached issues if available |
| github | Connection error | `UNAVAILABLE` | yes (1×) | yes | as above |
| github | 5xx | `UNAVAILABLE` | yes (1×) | yes | `GitHub returned HTTP 503` |
| github | 429 / 403 with `x-ratelimit-remaining: 0` | `RATE_LIMITED` | no | **no** | `retry_after` computed from `x-ratelimit-reset` |
| github | 403 without quota exhaustion | `AUTH_INVALID` | no | **no** | credential rejected — do not retry |
| github | 401 | `AUTH_INVALID` | no | **no** | credential rejected |
| github | 404 | `NOT_FOUND` | no | no | repository not visible to this credential |
| github | 422 | `BAD_RESPONSE` | no | no | query malformed — check the search terms |
| github | 2xx with a non-JSON body | `BAD_RESPONSE` | **no** | yes | malformed upstream body |
| github | Breaker open | `BREAKER_OPEN` | no call made | — | `retry_after` = remaining cooldown |
| corpus | Roots absent | `NOT_FOUND` | n/a | n/a | no corpus on this machine |
| corpus | Partial index (unreadable path) | `LOCAL_IO` | n/a | n/a | partial results + `note` |
| store | Database locked / unreadable | `LOCAL_IO` | n/a | n/a | envelope error, never an exception |
| store | Disabled by config | `DISABLED` | n/a | n/a | store turned off via `RTA_STORE_DISABLE` |
| any | Role lacks the tool | `FORBIDDEN` | no | n/a | required role named in the response |

**Cached fallback rule:** if a request fails and a cached value exists (regardless
of TTL), the value is returned with `cached: true`, `degraded: true`, the original
`fetched_at`, and a note naming the failure code. Stale data is never presented
as fresh.

**Design note (deliberate):** authentication and quota failures do not trip the
breaker. A missing token is a configuration fact, not an outage; opening the
breaker would hide `AUTH_INVALID` behind `BREAKER_OPEN` and send an engineer
looking in the wrong place.

---

## 6. The store: what is recorded, and what is deliberately not

| Table | Contents | Privacy decision |
|---|---|---|
| `runs` | Run id, time, tool, role, SDC SHA-256 and byte count, engine verdict/counts, sources used | The **hash** is stored, not the constraint file |
| `findings` | Per-rule rows copied from the engine payload | Verdict values are copied verbatim from the engine |
| `source_evidence` | `run_id`, source, reference, content hash, fetch time, freshness | Provenance without storing the referenced content |
| `tool_audit` | Timestamp, tool, role, **argument digest**, argument key names, outcome, duration, degraded flag | Argument **values** are never written |

`rta_source_store_record` runs the engine itself and persists the result — a
caller cannot supply a verdict, a count, or a finding. This is the mechanism
that keeps "the engine can never fake a PASS" true after persistence.

---

## 7. Verification

```bash
python -m pytest -q                                   # full suite
python -m pytest tests/test_sources_github.py -q      # failure matrix
python -m pytest tests/test_mcp_access.py -q          # capability boundary
python -m pytest tests/test_mcp_multi_source.py -q    # engine contract + composite
```

What the suite asserts:

1. The eight engine tools keep their names, order and required parameters, and
   their output is **byte-identical** to a direct `rta/api/api_server` call.
2. With GitHub failing, `rta_investigate` still returns the engine payload
   unchanged, marks the response `degraded`, and reports the source error.
3. Every row of the failure matrix above, including breaker opening and
   stale-cache fallback.
4. Deny-by-default: unknown tools are denied for every role; an unrecognised
   role resolves to `reader`; mutations need the explicit switch.
5. Secrets never leak: a planted token appears in no envelope and not in
   `health()`.
6. The audit log contains digests only — a planted SDC string is absent from the
   database bytes.

Run the server yourself:

```bash
RTA_MCP_ROLE=engineer python -m rta.api.mcp_server
```

---

## 8. Known limitations

- **Corpus ranking is lexical**, not semantic. It finds rule ids, file names and
  phrases reliably; it will not infer that "hold violation" means
  `set_input_delay -min`. A hosted knowledge base with embeddings can be added
  later behind the same adapter contract.
- **`rta_investigate` searches issues with the rule ids that fired** — a useful
  default, not a perfect retrieval strategy. Pass `query` explicitly through
  `rta_source_issues_search` when you know the symptom.
- **Anonymous GitHub access** is rate-limited to a small shared quota; set
  `GITHUB_TOKEN` for dependable results. The response says which mode was used.
- **The store is single-machine and unencrypted.** It holds run metadata and
  hashes, not constraint text, but it is not a multi-user service.
- **Sources cannot validate anything.** A matching issue or a matching document
  is context for a human decision; it does not change a verdict, and no source
  failure can mask an engine failure.
