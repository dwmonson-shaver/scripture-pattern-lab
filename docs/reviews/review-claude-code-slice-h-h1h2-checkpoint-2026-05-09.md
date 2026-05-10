---
type: code review
flavor: claude-fallback
slice: H — NL→DSL translator + first LLM dependency
checkpoint: H1+H2 mid-slice
base_sha: da0b4c9
head_sha: 18a8d1a
date: 2026-05-09
codex_blocked_reason: ~/.codex/sessions permission denied (same pattern as Slices E+F; Bucket 5 re-open). Single-line note only — chown fix is out of scope for this artifact.
verdict: minor-fixes-recommended
findings_summary: "0 P0, 0 P1, 1 P2, 5 P3, 2 info"
---

# Independent Review — Slice H Mid-Slice Checkpoint #1 (H1+H2)

**Scope:** `git diff da0b4c9..18a8d1a`
**Files in scope (read in full):**
- `src/nlp/llm_client.py` (NEW, 96 lines)
- `src/nlp/translator.py` (NEW, 144 lines)
- `src/nlp/prompts/system_prompt.py` (NEW, 67 lines)
- `src/nlp/prompts/__init__.py` (NEW, empty)
- `tests/unit/test_llm_client.py` (NEW, 150 lines, 13 tests)
- `tests/unit/test_translator.py` (NEW, 171 lines, 19 tests)
- `pyproject.toml` (MODIFIED — runtime dep, marker, addopts)
- `src/nlp/explainer.py` (MODIFIED — drive-by ruff cleanup; not in scope, cleanup is well-scoped)
- `uv.lock` (MODIFIED — anthropic + transitive deps)

**Calibration:** read `docs/reviews/review-codex-code-slice-g-g1g2g3g4-checkpoint-2026-05-09.md` (severity discipline) and `docs/reviews/review-claude-code-slice-e-close-2026-05-09.md` (fallback-flavor pattern).

---

## Summary of Findings

| ID | Severity | Category | File | Title |
|----|----------|----------|------|-------|
| H-H1H2-001 | P2 | Correctness / contract | `src/nlp/llm_client.py:74–75` | `BadRequestError` (and other 4xx code-bug subclasses of `APIError`) wrapped as 503 `LLMUnavailable`, hiding translator-side defects |
| H-H1H2-002 | P3 | Correctness | `src/nlp/llm_client.py:67–75` | `WorkloadIdentityError` is a sibling of `APIError`, not a subclass — escapes the except chain unwrapped |
| H-H1H2-003 | P3 | Correctness / extraction | `src/nlp/translator.py:56–61` | `_ALT_SECTION` regex terminates on the first blank line — well-spaced LLM bullets silently truncate |
| H-H1H2-004 | P3 | Epistemic honesty | `src/nlp/translator.py:119–129` | Out-of-range / unparseable `Confidence:` defaults to `1.0` (max), inflating apparent fidelity on translator-side parse failure |
| H-H1H2-005 | P3 | Resource hygiene | `src/nlp/llm_client.py:55, 41–57` | No `close()` / `__del__` and no public access to inner `httpx` pool — fine for MVP, but worth a docstring note about lifespan-scoped reuse |
| H-H1H2-006 | P3 | Convention | `src/nlp/translator.py:41` | Mutable default `alternatives: list[str] = []` on a Pydantic v2 frozen model — works correctly here, but is the project's first instance and worth standardizing |
| H-H1H2-007 | info | Test fragility | `tests/unit/test_llm_client.py:21–28, 77–90` | `MagicMock` response shape (`.content[i].type == "text"`) silently shadows real anthropic response shape; SDK upgrade can pass tests while breaking production (or vice versa) |
| H-H1H2-008 | info | Test fragility | `tests/unit/test_translator.py:53–64` | `SYSTEM_PROMPT` content assertions (`"DSL Cookbook for Agents" in SYSTEM_PROMPT`) couple unit tests to cookbook-document strings — cookbook copy edits will break tests |

**Clean categories** (verified against the focus list, no findings):

- **Security / api_key handling.** `AnthropicLLMClient.__init__` does not retain `api_key` on `self`; it passes it directly to `anthropic.Anthropic(api_key=...)`. `vars(client)` shows only `_client`, `_model`, `_max_tokens`. Default `repr()` is non-leaking. (Note in H-H1H2-005: the inner `anthropic.Anthropic` SDK client DOES expose `.api_key` as a public attribute — that's an SDK behavior, not a project bug, but worth being aware of when logging or error-formatting around the client object.)
- **Prompt injection.** Translator is single-shot per DEC-071. `translate()` does not feed LLM output back into another LLM call. No injection surface within this slice. Verified.
- **Contract / canonical-09 §2.** `TranslationResult` matches §2's specified fields (`dsl: str`, `confidence: float`, `alternatives: list[str]`, `explanation: str`). The `translate(nl_query, context, llm_client)` signature adds `llm_client` beyond §2's `translate(nl_query, context)` — this is the documented IoC seam from DEC-067; canonical-09 §2 amendment is scheduled for H6.
- **Pydantic v2 + frozen.** Both `TranslationContext` and `TranslationResult` use `ConfigDict(frozen=True)`. `LLMUnavailable` carries `# noqa: N818` matching the `ValidationUnsupported` precedent (canonical-09 §1).
- **Type hints.** All public signatures in `src/nlp/llm_client.py`, `src/nlp/translator.py`, `src/nlp/prompts/system_prompt.py` carry full type hints. Test helpers (`FakeLLMClient.__init__`, `FailingLLMClient.complete`, `_fake_message`, `_ctx`) all annotated.
- **Imports order.** `src/nlp/translator.py:13–20`: `__future__` → stdlib (`re`) → third-party (`pydantic`) → project (`src.nlp.*`). `src/nlp/llm_client.py:11–15`: same. `src/nlp/prompts/system_prompt.py:11–13`: same. Compliant.
- **Architecture boundaries.** `src/nlp/translator.py` imports from `src.nlp.llm_client` and `src.nlp.prompts.system_prompt` only. `src/nlp/llm_client.py` imports stdlib + `anthropic` only. `src/nlp/prompts/system_prompt.py` imports `pathlib` only. No HTTP/FastAPI imports leaking into `src/nlp/`. Compliant.
- **Catastrophic-backtracking probe.** `_DSL_LINE`, `_CONFIDENCE_LINE`, `_ALT_BULLET`, `_ALT_SECTION`, `_EXPLANATION_LINE` all anchored with `re.MULTILINE` and bounded character classes. Probed against 100k random input + trailing `DSL: faith\n`: matched in <1 ms. No catastrophic-backtracking risk.
- **Anchored extraction is robust to chain-of-thought.** Tested LLM output that prefixes prose ("Final answer:\nDSL: foo") — regex still extracts correctly. The system prompt instructs the LLM to omit prose, but the parser tolerates noise. Forgiving design.
- **First-DSL-wins on duplicates.** `_DSL_LINE.search(...)` returns the first match. Confirmed: if the LLM emits two `DSL:` lines, the first wins. Documented behavior, no bug.
- **Lowercase / indented `DSL:` rejected.** Anchored `^DSL:` with `re.MULTILINE` does NOT match `  DSL:` (indented) or `dsl:` (lowercase). Strict format enforcement matches the system prompt's "MANDATORY" directive.
- **Empty / whitespace-only DSL string rejected.** `dsl_match.group(1).strip()` followed by `if not dsl: raise NLCompileError` — verified via `tests/unit/test_translator.py:117–120`.

---

## Detailed Findings

### H-H1H2-001 — P2 — Correctness / contract

**Severity:** P2 — must-fix-before-slice-close
**File:** `src/nlp/llm_client.py:74–75`
**Category:** Correctness / HTTP-status contract

**Finding:** The bare `except anthropic.APIError as exc:` branch wraps **all** `APIError` subclasses as `LLMUnavailable`, which the route layer (per DEC-070) maps to HTTP 503. But several `APIError` subclasses are 4xx errors that signal a translator-side or request-shape bug, not LLM availability:

- `anthropic.BadRequestError` (HTTP 400) — malformed request body. If the translator builds a request with an invalid `model` or oversized `system` prompt, the SDK raises this. Wrapping as 503 says "LLM is down"; the truth is "we sent garbage."
- `anthropic.NotFoundError` (HTTP 404) — typically misnamed model. Same class of issue.
- `anthropic.UnprocessableEntityError` (HTTP 422) — schema-rejected request. Same class.
- `anthropic.PermissionDeniedError` (HTTP 403) — account / scope issue. Arguably availability, but distinct from the user-facing service availability story.

The structure outline (`thoughts/structure-slice-h-nl-translator-2026-05-09.md:32`) does state "All other anthropic.APIError subclasses propagate as LLMUnavailable" — so the implementation matches the spec. But the spec itself is the issue: it conflates "LLM provider unavailable" (network, auth, rate-limit) with "we built the request wrong" (4xx code bugs). At slice close, the canonical-09 §1 status table will document `llm_unavailable` as 503 — having a 400-class translator bug surface as a transient 503 misleads operators and breaks the cardinal canonical-09 contract that 5xx means "system fault, not your fault."

**Suggested fix (before slice close):** Either:
1. Tighten the wrapping list to only the genuinely-availability cases (keep the four explicit ones at lines 67–72; let other `APIError` subclasses propagate uncaught so they bubble as HTTP 500). The route handler at H4 can then decide whether to map them.
2. Add a second branded exception (e.g., `LLMRequestInvalid`) for `BadRequestError` / `UnprocessableEntityError` / `NotFoundError`, mapped to 500 (server bug, not LLM-side) at the route. This matches the design's spirit: 503 = "ask the user to retry"; 500 = "we have a bug, retry won't help."

Either path needs a DEC update (DEC-070 amendment or DEC-075). Recommend resolving at H4 (route exception mapping) since that's where the HTTP-status decision actually materializes.

---

### H-H1H2-002 — P3 — Correctness

**Severity:** P3
**File:** `src/nlp/llm_client.py:67–75`
**Category:** Correctness / exception coverage

**Finding:** `anthropic.WorkloadIdentityError` is a direct subclass of `anthropic.AnthropicError` but **not** of `anthropic.APIError`. Verified via `inspect`:

```
issubclass(anthropic.WorkloadIdentityError, anthropic.APIError) → False
```

The current except chain only catches the four specific exceptions and the bare `anthropic.APIError`. A `WorkloadIdentityError` raised from `messages.create(...)` (relevant for Vertex / Bedrock / GCP-mediated auth setups) would propagate uncaught from `complete()`, escaping the `LLMUnavailable` envelope.

**Risk severity:** Low for current MVP (project uses direct `ANTHROPIC_API_KEY`, not workload-identity routes). But the structure outline's stated invariant ("All other anthropic.APIError subclasses propagate as LLMUnavailable") is mathematically incomplete: there exist `AnthropicError` subclasses that `APIError` does not cover.

**Suggested fix:** Either change the bare except to `except anthropic.AnthropicError as exc:` (covers everything in the SDK's exception hierarchy), or add `anthropic.WorkloadIdentityError` to the explicit list. The first option is more robust and matches the design intent of "anything from the SDK becomes LLMUnavailable." Recommend pairing with H-H1H2-001 — both involve revisiting the wrapping policy.

---

### H-H1H2-003 — P3 — Correctness / extraction

**Severity:** P3
**File:** `src/nlp/translator.py:56–61`
**Category:** Correctness / regex parsing

**Finding:** The `_ALT_SECTION` regex:

```python
_ALT_SECTION = re.compile(
    r"^Alternatives:[ \t]*\n((?:[\-\*][ \t]*.+\n?)*)",
    re.MULTILINE,
)
```

Greedy-matches consecutive bullet lines. The bullet group `(?:[\-\*][ \t]*.+\n?)*` requires each bullet line to start with `-` or `*` directly (no whitespace tolerance, fine), but the group ZERO-OR-MORE quantifier terminates on the first non-matching line — including a **blank line**. Probed:

```
Input: "DSL: x\nAlternatives:\n- a\n\n- b\n"
Section captured: "- a\n"
Bullets extracted: ["a"]   # "b" silently dropped
```

If the LLM emits well-spaced alternatives separated by a blank line (a perfectly natural human style), only the bullets up to the first blank line survive. The user sees a truncated `alternatives` list and never knows the LLM tried to suggest more.

**Risk:** The MVP system prompt instructs the LLM to use a tight bullet block (no blank lines), so the natural production behavior is fine. But the parser is brittle — any LLM that diverges loses content silently.

**Suggested fix:** Either (a) document the blank-line termination as intentional in the docstring, (b) tolerate blank lines inside the section by using a more permissive regex (e.g., `((?:[ \t]*\n)?[\-\*][ \t]*.+\n?)*` or capture the section by lookahead to the next `Confidence:` / `Explanation:` header), or (c) add a unit test asserting the truncation behavior so future regressions are visible. Option (b) is the most honest — silently dropping alternatives violates the canonical-09 §2 constraint "Must surface ambiguity rather than silently resolve it."

---

### H-H1H2-004 — P3 — Epistemic honesty

**Severity:** P3
**File:** `src/nlp/translator.py:119–129`
**Category:** Epistemic honesty / surfaced confidence

**Finding:** Three branches of `_extract_confidence` default to **`1.0` (maximum confidence)** on parse failure:

```python
if match is None:           return 1.0   # no Confidence: line
except ValueError:          return 1.0   # malformed float (e.g., "0.5.5")
if value < 0 or value > 1:  return 1.0   # out-of-range
```

This is in-spec per the structure outline ("malformed confidence (defaults to 1.0)") but it conflicts with the project's epistemic charter (CLAUDE.md: "the corpus is ground truth … the system tests priors, not confirms them"). Defaulting to MAX confidence on translator-side parse failure inflates the apparent fidelity of a query the LLM may have failed to confidently produce. A caller relying on `confidence` to decide whether to trust the translation will be misled.

The right default depends on intent:
- If the LLM didn't bother to volunteer confidence, treating it as "I have no signal" is honest — a sentinel like `confidence = -1.0`, `confidence: float | None = None`, or a low default (`0.0`) better matches the truth.
- If the LLM emitted garbage in the Confidence slot, that's evidence it's not confident — defaulting to max is the wrong direction.

**Risk:** Low for MVP (DEC-072 says no auto-gating, so callers see the raw value and can decide), but the value is documented as "the LLM's self-assessment of translation fidelity" — and right now it can be MAX without ANY self-assessment occurring.

**Suggested fix:** Change the default to a low / sentinel value (`0.0` or `None`) and update the structure outline + DEC-072 narrative to match. Alternatively, add a second field `confidence_source: Literal["llm", "default"]` so the caller can distinguish "LLM said 1.0" from "LLM said nothing parseable, system fell back to 1.0." Either way, decide before slice close so the canonical-09 §2 amendment in H6 reflects shipped reality.

---

### H-H1H2-005 — P3 — Resource hygiene / docstring

**Severity:** P3
**File:** `src/nlp/llm_client.py:55, 41–57`
**Category:** Resource lifecycle

**Finding:** `AnthropicLLMClient` does not implement `close()` or `__del__` and exposes no method to flush the inner SDK's connection pool. The Anthropic SDK manages an `httpx.Client` internally with its own pool lifecycle (verified: SDK's `_base_client.py` uses `SyncHttpxClientWrapper`).

For MVP this is fine — the design (DEC-074) calls for one client per app lifespan, instantiated at startup, never disposed. The Anthropic SDK's `httpx.Client` will be garbage-collected at process exit, and the SDK has its own `__del__` that flushes the pool. Slice G's lifespan disposes the SQLAlchemy engine but explicitly does NOT plan to dispose the LLM client (per the design).

**Concern:** The class docstring (lines 41–57) doesn't say this. A future maintainer adding an LLM-second-provider or refactoring the lifespan may not know. Worse: the inner `anthropic.Anthropic` client exposes `.api_key` as a public attribute (verified: `c.api_key == "sk-secret-..."`). Anyone adding `vars()` / `repr()` / `dir()`-based logging on `_client` would leak the key. The current code does not do this; the docstring should warn.

**Suggested fix:** Add to the `AnthropicLLMClient` docstring: (a) "instances are intended to be lifespan-scoped (one per FastAPI app) and not explicitly disposed; the SDK's HTTP pool is reclaimed at process exit"; (b) "the inner anthropic.Anthropic client exposes `api_key` as a public attribute — never log `vars(self._client)` or include `self._client` in error messages."

---

### H-H1H2-006 — P3 — Convention / Pydantic style

**Severity:** P3
**File:** `src/nlp/translator.py:41`
**Category:** Convention

**Finding:** `TranslationResult.alternatives: list[str] = []` uses a mutable default. Pydantic v2 handles this correctly by deep-copying the default per instance (verified by the existing `test_missing_alternatives_defaults_to_empty_list`), so it works — but project convention is unsettled here. Looking at the existing frozen Pydantic models in `src/engine/models.py`, `src/validation/validator.py`, and `src/app/schemas.py`, none of them currently use a mutable default value. This is the first instance.

**Risk:** Low (Pydantic v2 isolates instances). But mixing styles across the codebase invites confusion — a future maintainer who copies this pattern into a non-Pydantic dataclass / NamedTuple will hit a real shared-state bug.

**Suggested fix:** Either (a) explicitly use `Field(default_factory=list)` to match standard Pydantic-with-mutable-default idiom, or (b) document via a comment that Pydantic v2 deep-copies the default. (a) is cleaner and matches PEP 8's general guidance against mutable defaults. Recommend (a).

---

### H-H1H2-007 — info — Test fragility / SDK shape

**Severity:** info
**File:** `tests/unit/test_llm_client.py:21–28, 77–90`
**Category:** Test fragility

**Finding:** The mock builder `_fake_message(text)` constructs:

```python
text_block.type = "text"
text_block.text = text
response.content = [text_block]
```

This assumes the anthropic SDK's response shape is exactly `response.content` is a list of objects with `.type` and `.text` attributes. If the SDK upgrades from 0.40 → 0.50 and changes the response model (e.g., wraps text in `TextBlock(type="text", text=..., citations=...)`, or changes `content` to a property, or returns `ContentBlock` Pydantic objects with different field names), the **production code** at `src/nlp/llm_client.py:77` (`block.text for block in response.content if block.type == "text"`) might break, but the test's MagicMock will continue to return whatever the fake says.

The pyproject pin `anthropic>=0.40,<1.0` allows ~9 minor versions of drift. The current shape is correct as of 0.40+ (verified). But this is a known asymmetry in mock-based tests against external SDK shapes. The Slice G live-DB integration test pattern (DEC-G3) is the right complement: the H5 live-LLM exit gate is what catches SDK shape drift.

**Mitigation already in place:** H5's `tests/integration/test_app_nl_route_live_llm.py` (planned per structure outline) hits a real Anthropic endpoint — that's what would catch shape drift. No action needed in H1+H2; flagged so future SDK upgrades are paired with a manual `pytest -m live_llm` run before merging the version bump.

---

### H-H1H2-008 — info — Test fragility / cookbook coupling

**Severity:** info
**File:** `tests/unit/test_translator.py:53–64`
**Category:** Test fragility

**Finding:** Three assertions in `TestSystemPromptBuild` couple unit tests to literal cookbook strings:

```python
assert "DSL Cookbook for Agents" in SYSTEM_PROMPT     # line 58
assert "BEGIN DSL COOKBOOK" in SYSTEM_PROMPT          # line 59 (framing)
assert "END DSL COOKBOOK" in SYSTEM_PROMPT            # line 60 (framing)
```

Lines 59 and 60 are stable (they're hard-coded in `system_prompt.py`'s `_TRANSLATOR_FRAMING`). Line 58 (`"DSL Cookbook for Agents"`) is whatever H1 of `docs/agent/dsl-cookbook.md` happens to say today. If a Slice E follow-up edits the cookbook header to "DSL Cookbook (v2)" or "DSL Cookbook — Agent-Facing Reference," this test breaks even though the system prompt is functionally fine. Per DEC-071, cookbook edits don't require translator code changes — but they DO require this test edit, which couples the cookbook to the test suite.

**Mitigation:** Replace the assertion with something more behavioral, e.g.:
```python
assert len(SYSTEM_PROMPT) > 5000  # cookbook is non-trivial
assert "concept:" in SYSTEM_PROMPT  # cookbook documents the concept: prefix
```

Or assert against a programmatic check (`DEFAULT_COOKBOOK_PATH.read_text() in SYSTEM_PROMPT`). Not blocking; flagged for slice close.

---

## Verdict Rationale

**Verdict: minor-fixes-recommended.**

H1 + H2 land cleanly. The LLMClient seam is concrete (matches DEC-067), `TranslationResult` matches canonical-09 §2's specified fields, the regex extraction is robust to common LLM noise patterns (catastrophic-backtracking-free, chain-of-thought tolerant, anchored against indent/case attacks), and api_key handling on the project side is non-leaking. All 13 + 19 new tests pass per the project_status memory cue (462 → 467 → 475 cumulative).

The one P2 (H-H1H2-001) is a contract issue, not a code-correctness issue — but the contract issue (4xx code bugs masquerading as 503 service-unavailable) violates the canonical-09 §1 invariant that 5xx == "system fault, not your fault." It's must-fix-before-slice-close because it gets harder to fix once H4's route mappings concretize the wire-level behavior. The five P3s are real but small, and two of them (H-H1H2-001 and H-H1H2-002) cluster around the same exception-wrapping policy and can be resolved together at H4.

**Severity histogram:**
- P0: 0
- P1: 0
- P2: 1 (H-H1H2-001)
- P3: 5 (H-H1H2-002 through H-H1H2-006)
- info: 2 (H-H1H2-007, H-H1H2-008)

---

## Next Steps

**What must close before H3 starts:**
- None of these block H3. H3 (schemas + run_nl_query orchestration) only touches new code that consumes `translate()` and `TranslationResult` by their stable shapes. None of the findings above change those shapes.

**What must close before slice close:**
- **H-H1H2-001** (P2). Resolve at H4 alongside the route's exception mapping (the natural place to decide 503 vs. 500 vs. 422). DEC-070 amendment likely required; or add DEC-075 covering the 4xx-vs-5xx distinction.

**What can land inline at H3 / H4 cheaply:**
- H-H1H2-002 (one-line widening of the except chain to `anthropic.AnthropicError`).
- H-H1H2-006 (`Field(default_factory=list)` rename — one line in `translator.py`).
- H-H1H2-005 (docstring addition — three lines in `llm_client.py`).

**What should be triaged at slice close:**
- H-H1H2-003 (alternatives blank-line truncation) — fix-or-document.
- H-H1H2-004 (confidence default-on-failure semantics) — DEC-072 narrative update + code change.
- H-H1H2-007, H-H1H2-008 (test fragility) — note in reviews-log; let H5 + future SDK-bump discipline cover them.

Verification trust: project_status memory states 462 tests green at base SHA da0b4c9 + structure outline H1 says 462 → 467, H2 says 467 → 475. Local re-run blocked by sandbox `.env` permission (independent of the code in scope); user has confirmed green via /implement phase commits.
