# Next Steps Plan
Last updated: 2026-03-27

**Mission:** Make memv the best "remember what users said" library. Solid semantic memory first, then procedural/agent memory as the differentiator.

**Current state:** v0.2.0 nearly complete. Protocol cleanup (§7) merged (#22). PostgreSQL backend (§8) in PR #23 — all 5 stores ported to asyncpg/pgvector, tested against local Postgres (316 tests across both backends). API unified to single `db_url` parameter. Embedding adapters (§9) are the remaining v0.2.0 item.

**What's unique about memv:**
- Predict-calibrate extraction (only Nemori shares this — importance from prediction error)
- Write-time temporal normalization (only SimpleMem shares this — accounts for 56.7% of temporal reasoning per their ablation)
- Bi-temporal validity (only Graphiti shares this — event time vs transaction time)
- Episode segmentation (only Nemori shares this — topic-coherent grouping before extraction)

**What's table-stakes that memv is still missing:**
- ~~Knowledge CRUD through public API~~ (done — PR #16)
- ~~Score/relevance threshold on retrieval~~ (skipped — `top_k` sufficient, see §5)
- ~~Direct knowledge injection (bootstrapping without fake conversations)~~ (done — PR #18)
- ~~A second storage backend~~ (done — PostgreSQL via `memvee[postgres]`, PR #23)

**Related docs:**
- `notes/PLAN_v1_backup.md` — previous plan with full competitive-analysis-driven roadmap
- `notes/COMPETITIVE_ANALYSIS.md` — competitor deep dives + API comparison
- `notes/RESOURCES.md` — reading list + library analysis notes

---

## Completed: Tests

183 tests covering models, storage, pipeline, retrieval, and e2e. All passing in CI.

<details>
<summary>Completed checkboxes (click to expand)</summary>

### Storage integration tests
- [x] MessageStore: add, get, get_by_user, get_by_time_range, list_users, count, delete, clear_user, user_isolation
- [x] EpisodeStore: add, get, get_by_user, get_by_time_range (overlap/contained/no-match), count, delete, clear_user, update, JSON roundtrip
- [x] KnowledgeStore: add, get, get_by_episode, get_all, get_current, get_valid_at (bi-temporal), invalidate, count, delete, clear_by_episodes
- [x] VectorIndex: add, search (ordering, top_k, scores, user filter), clear_user
- [x] TextIndex: add, search (match, no-match, top_k, user filter, special chars), clear_user, sanitize_fts_query

### Pipeline integration tests (mock LLM/embeddings)
- [x] Messages → BatchSegmenter → episodes (topic detection, time gap splitting)
- [x] Episodes → EpisodeGenerator → narrative content
- [x] Episodes → PredictCalibrateExtractor → knowledge (cold start + warm)
- [x] Episode merging (similar episodes deduplicated)
- [x] Knowledge deduplication (similar statements filtered)

### Retrieval integration tests
- [x] Hybrid search: vector + BM25 fusion via RRF
- [x] User isolation: user A's knowledge not returned for user B
- [x] Bi-temporal filtering: at_time, include_expired

### End-to-end test
- [x] `Memory` class through full cycle: add_exchange → process → retrieve → verify results
- [x] Auto-processing: buffer threshold → background processing → retrieval

### Acceptance criteria
- [x] All stores have round-trip tests
- [x] Pipeline tested with mock LLM that returns deterministic outputs
- [x] Retrieval tested for correctness, not just no-crash
- [x] CI passes on all tests

</details>

---

## Completed: Atomization

Prompt-level rules, confidence filter, temporal parsing module. Code-level regex filters removed (English-only, moved to prompt-level enforcement for language agnosticism).

<details>
<summary>Completed checkboxes (click to expand)</summary>

### Temporal normalization in extraction prompts
- [x] "yesterday" → absolute date (requires reference timestamp)
- [x] "next Monday" → absolute date
- [x] "last week" → date range
- [x] Thread `reference_time` (from last message timestamp) through extraction pipeline

### Coreference resolution
- [x] "my kids" → "Sarah's kids" (when user_id maps to known name) — prompt-level only
- [x] "he/she/they" → named entity from conversation context — prompt-level only
- [x] "this place" → specific location from context — prompt-level only

### Self-contained statement constraint
- [x] Each extracted knowledge statement interpretable without episode context
- [x] Add explicit prompt instructions: prohibit pronouns, relative time, ambiguous references

### Extraction robustness
- [x] Confidence >= 0.7 threshold. Regex filters removed — English-only, moved to prompt-level.

### Temporal parsing
- [x] `src/memv/processing/temporal.py` — `parse_temporal_expression`, `contains_relative_time`, `backfill_temporal_fields`

### Acceptance criteria
- [x] Self-contained statements enforced via prompts
- [x] Temporal expressions resolved to absolute dates
- [x] Regression tests pass
- [ ] Before/after atomization comparison via LongMemEval (blocked on first benchmark run)

</details>

---

## Completed: Benchmark Harness

LongMemEval harness aligned with official evaluation protocol (xiaowu0162/longmemeval). Balanced 30-question run (5/type) complete.

<details>
<summary>Completed checkboxes (click to expand)</summary>

- [x] Dataset loader, ingestion, search, evaluation, config presets, runner, pipeline parallelization, `make benchmark`
- [x] Official eval protocol: gpt-4o judge, temperature=0, max_tokens=10, type-specific prompts, abstention prompt for `_abs` questions, task-averaged accuracy
- [x] Segmentation passthrough fix: `batch_threshold` wired up (was dead code). 68% fewer episodes, 54% fewer facts, 66% faster.
- [x] Balanced 30-question baseline (5/type, `balanced-5` run)

</details>

### Baseline Results (balanced-5, gpt-4o-mini, 2026-04-07)

| Type | Score | Analysis |
|------|-------|----------|
| knowledge-update | 3/5 = 60% | Supersedes partially working. Off-by-one bug (#32) causes fallback to vector search. One question returned old value instead of updated one. |
| single-session-user | 3/5 = 60% | Extraction loses context when compressing (#33). "Where did I redeem coupon?" → fact had location missing. |
| temporal-reasoning | 2/5 = 40% | Date extraction errors. MoMA→Met got "30 days" instead of 7. One answer was "zero days." |
| multi-session | 2/5 = 40% | Retrieval recall — found 1 of 3 needle sessions. top_k=10 may not surface all fragments. |
| single-session-assistant | 1/5 = 20% | Extraction prompt focuses on user facts, assistant-generated content not extracted. Architectural mismatch — see note below. |
| single-session-preference | 0/5 = 0% | Extraction doesn't capture preferences. Top priority fix. |
| **Task-averaged** | **36.7%** | |

**Note on single-session-assistant:** This type tests "remember what the assistant said" (shift schedules, restaurant recommendations, book descriptions). Extracting assistant content would bloat the KB with generic responses in production. This is a benchmark/architecture mismatch, not a bug. We accept lower scores here and report task-averaged-excluding-assistant as a secondary metric.

---

## v0.1.1 — "Make it usable"

**Goal:** A developer can pip install memv, feed conversations, inspect what was learned, fix mistakes, seed known facts, and trust that retrieval doesn't return garbage. Table-stakes for any memory library.

**Internal order:** user_id denorm → CRUD → Contradiction → Injection → ~~Score threshold~~ → ~~Benchmarks~~

**Status:** All items complete. Ready to tag and publish.

### 1. Add user_id to SemanticKnowledge

Knowledge is only linked to users through episodes (join required). Unblocks CRUD, injection, simpler queries.

**Model** (`src/memv/models.py`):
- [x] Add `user_id: str | None = None` to `SemanticKnowledge` (None for backwards compat)

**Schema** (`src/memv/storage/sqlite/_knowledge.py`):
- [x] Migration: `ALTER TABLE semantic_knowledge ADD COLUMN user_id TEXT`
- [x] Index: `CREATE INDEX idx_sk_user_id ON semantic_knowledge(user_id)`
- [x] Backfill: `UPDATE semantic_knowledge SET user_id = (SELECT user_id FROM episodes WHERE id = source_episode_id)`
- [x] Update `add()`, `_row_to_knowledge()`

**Pipeline** (`src/memv/memory/_pipeline.py`):
- [x] Set `user_id` when creating `SemanticKnowledge`

### 2. Knowledge CRUD

Can't use a system you can't inspect. Every competitor has at least add/search/delete.

**New KnowledgeStore methods** (`src/memv/storage/sqlite/_knowledge.py`):
- [x] `list_by_user(user_id, limit=50, offset=0, include_expired=False)`
- [x] `count_by_user(user_id, include_expired=False)`

**New VectorIndex/TextIndex methods**:
- [x] `delete(uuid)` — per-entry delete (currently only `clear_user` exists)

**New Memory API** (`src/memv/memory/_api.py`, `memory.py`):
- [x] `list_knowledge(user_id, limit, offset, include_expired)`
- [x] `get_knowledge(knowledge_id)`
- [x] `invalidate_knowledge(knowledge_id)` — soft-delete (set expired_at)
- [x] `delete_knowledge(knowledge_id)` — hard-delete (DB + vector index + text index)

### 3. Contradiction Handling

Index-based supersedes: existing knowledge passed as numbered list to extraction prompt, LLM outputs index of entry being replaced.

**Model** (`src/memv/models.py`):
- [x] Add `supersedes: int | None = None` to `ExtractedKnowledge` (index into numbered list)
- [x] Add `superseded_by: UUID | None = None` to `SemanticKnowledge`

**Schema** (`src/memv/storage/sqlite/_knowledge.py`):
- [x] Migration: `ALTER TABLE semantic_knowledge ADD COLUMN superseded_by TEXT`
- [x] `invalidate_with_successor(knowledge_id, successor_id)` — atomic expired_at + superseded_by

**Prompts** (`src/memv/processing/prompts.py`):
- [x] `extraction_prompt_with_prediction` accepts `existing_knowledge_numbered` param, inserts numbered list, adds `supersedes` to output format

**Extractor** (`src/memv/processing/extraction.py`):
- [x] `_extract_gaps` passes existing knowledge as numbered list to warm prompt
- [x] `_format_numbered_knowledge` helper

**Pipeline** (`src/memv/memory/_pipeline.py`):
- [x] Index-based: `supersedes` in bounds → `invalidate_with_successor(old_id, new_id)`
- [x] Fallback: `supersedes` is None or out of bounds → vector-based matching
- [x] Handle `knowledge_type == "update"` same as "contradiction"
- [x] Store new entry first, then invalidate old (audit trail needs successor ID)

### 4. Direct Knowledge Injection

Bootstrapping requmires fake conversations without this. Every competitor with a managed API has an inject/add endpoint.

**API** (`src/memv/memory/_api.py`, `memory.py`):
- [x] `add_knowledge(user_id, statement, valid_at=None, invalid_at=None) → SemanticKnowledge`
- [x] `add_knowledge_batch(user_id, items: list[...])` with `embed_batch`

**Implementation**:
- [x] Embed statement, optional dedup check, index in vector + text
- [x] Make `source_episode_id` nullable (None = injected)
- [x] Return the created entry

### 5. Score Threshold Filtering — SKIPPED

PR #19 closed. `top_k` is sufficient for now — with per-user knowledge bases (typically 50-200 facts), retrieval quality isn't a problem. If users report "retrieval returns irrelevant junk," revisit with cosine similarity pre-filter approach (filter vector search candidates before RRF fusion, not normalized RRF scores post-fusion). See PROGRESS.md 2026-03-25 for full rationale.

### 6. Benchmark Runs — DEFERRED to v0.2.0+

Moved out of v0.1.1. Harness is built and smoke-tested (3 questions, 66.7% on fast config). Full run deferred — not blocking adoption. Run when marketing needs numbers.

### v0.1.1 Verification

- All 229 tests pass
- New tests for: CRUD (list, get, invalidate, delete), contradiction (supersedes flow, audit trail), injection (single, batch, dedup check)
- Duplicate embedding column removed (#21) — ~50% DB size reduction
- `make all` passes

---

## v0.2.0 — "Production-ready"

**Goal:** memv can be deployed in production with Postgres. Pluggable backends via protocols, PostgreSQL as first alternative. This unblocks real-world testing and makes the library marketable.

**Internal order:** Protocol cleanup → PostgreSQL backend

### 7. Protocol Cleanup

Current protocols are incomplete — they define read interfaces but omit mutation methods the codebase actually calls. `VectorIndex` and `TextIndex` have no protocol at all. `LifecycleManager` imports concrete SQLite classes directly. This blocks any alternative backend.

- [x] Complete store protocols — add all user-scoped methods (KnowledgeStore: `invalidate`, `invalidate_with_successor`, `delete`, `clear_by_episodes`, `list_by_user`, `count_by_user`; MessageStore: `list_users`, `count`, `delete`, `clear_user`; EpisodeStore: `count`, `delete`, `clear_user`, `update`). Unscoped methods (`get_all`, `get_current`, `get_valid_at`, `count`) intentionally excluded — violate user isolation. SQLite keeps them for dashboard; scoped versions will be added to protocol when needed.
- [x] Add `VectorIndex` protocol (`open`, `close`, `add`, `search`, `search_with_scores`, `has_near_duplicate`, `delete`, `clear_user`)
- [x] Add `TextIndex` protocol (`open`, `close`, `add`, `search`, `delete`, `clear_user`)
- [x] Add `open`/`close` to all store protocols
- [x] Backend factory in `LifecycleManager` — config-driven creation via `MemoryConfig.backend`, lazy imports
- [x] Fix Retriever imports — import from `memv.protocols` instead of `memv.storage`

### 8. PostgreSQL Backend

Production-grade alternative. SQLite is fine for dev/single-process, but anything multi-process or deployed needs Postgres.

| Store | SQLite | PostgreSQL |
|-------|--------|------------|
| MessageStore | Regular SQL | Regular SQL (trivial port) |
| EpisodeStore | SQL + JSON | SQL + `jsonb` |
| KnowledgeStore | SQL + JSON | SQL + `jsonb` |
| VectorIndex | `sqlite-vec` | `pgvector` (`vector` type, `<->` L2) |
| TextIndex | FTS5 | `tsvector`/`tsquery` + GIN index |

- [x] All 5 stores implemented for Postgres (asyncpg + pgvector) — `src/memv/storage/postgres/`
- [x] `db_url` parameter on `Memory` (`postgresql://...`), auto-detects `backend="postgres"`
- [x] Optional dependency: `pip install memvee[postgres]`
- [x] Parametrized tests via `--backend` CLI option (fixture-level, existing tests unchanged)
- [x] CI service container for Postgres (`pgvector/pgvector:pg17`)

### v0.2.0 Verification

- Parametrized test suite passes on both SQLite and Postgres
- All protocols have complete method coverage matching actual usage
- A new backend can be implemented purely from protocols (no need to read SQLite source)
- `make all` passes

### 9. Embedding Adapters

Only OpenAI today. Users want provider choice and a no-API-key local option. The `EmbeddingClient` protocol is 2 methods — each adapter is ~15 lines.

**Adapters:**
- [ ] Voyage AI (`memvee[voyage]`) — `voyageai` SDK, `voyage-3-lite` default
- [ ] Cohere (`memvee[cohere]`) — `cohere` SDK, `embed-v4.0` default
- [ ] Local/fastembed (`memvee[local]`) — `fastembed` (ONNX, no GPU required), `BAAI/bge-small-en-v1.5` default (384 dims)
- [ ] Update `MemoryConfig.embedding_dimensions` handling — adapters should declare their dimensions so users don't have to set it manually

**Not adding:**
- Sentence-transformers — heavier dependency (PyTorch). `fastembed` covers the local use case with ONNX.
- More vector DB backends (Qdrant, Pinecone, Milvus, Chroma) — they only replace VectorIndex, not TextIndex. memv's hybrid retrieval (vector + BM25 via RRF) is a strength. Splitting storage across two systems adds operational complexity without clear demand. Revisit if users request it.
- More LLM adapters — PydanticAI already supports OpenAI, Anthropic, Google, Groq, Ollama, and others. No work needed.

### 10. Extraction Quality Fixes

Prompt-level fixes in `prompts.py`, prioritized by benchmark impact.

**Benchmark-driven (highest impact on task-averaged):**
- [ ] **Preference extraction** — extraction prompt captures facts ("User graduated with BA") but not preferences that emerge from dialogue ("User prefers Adobe Premiere Pro"). LongMemEval single-session-preference: 0/5. Fix: add preference/opinion extraction rules to prompt — "When user expresses preferences through choices, corrections, or repeated patterns, extract as 'User prefers X over Y' or 'User wants X.'" (#1 priority)
- [ ] **Self-contained facts** (#33) — extracted facts lose context from surrounding conversation. "User redeemed coupon" drops "at Target" because it seemed obvious in context. Fix: instruct extractor to make every fact answerable without original context — "each fact must include who, what, where, when if mentioned anywhere in the conversation."
- [ ] **Supersedes off-by-one** (#32) — LLM returns 1-based index for 0-based list. Fix: clarify prompt + handle off-by-one in code.

**Found in manual testing:**
- [ ] **Assistant self-description leak** — extractor stores assistant statements about itself as facts (e.g. "Assistant does not have memories like a human does"). EXCLUSIONS cover assistant *suggestions* but not self-descriptions. Fix: add explicit exclusion for statements about the assistant's own nature, capabilities, or limitations.
- [ ] **"User named X" phrasing** — third-person rewrite produces awkward headlines ("User named Bartosz won the Anthropic Hackathon"). The extraction prompt uses "User" as subject, but combining it with the user's actual name reads unnaturally. Fix: refine the coreference/naming rules in the extraction prompt.

---

## After v0.1.2: Agent/Procedural Memory

Semantic memory is solid. The unsolved problem — and memv's long-term differentiator — is **procedural memory for agents**. Agents don't just have conversations; they have runs with actions, tool calls, decisions, and outcomes. Learning *how to do things better* from past runs is what no one has solved well.

This is big enough to be its own planning effort. Key questions to answer before committing:

1. **Same library or separate package?** `memvee[agent]` extra vs `agentmemory` as a separate library that depends on memv for semantic storage.
2. **What's the minimum viable procedural memory?** The old plan had 3 levels (tool patterns → workflows → strategies). Maybe level 1 alone is enough to ship and learn.
3. **Which agent framework to target first?** PydanticAI is the obvious choice given existing adapter work.
4. **What does the API look like?** `start_run()` → `add_action()` → `end_run()` → `process_runs()` → `retrieve_for_tool()` is the sketch, but needs validation against real agent architectures.

Defer detailed planning until v0.2.0 ships and there's real usage data for semantic memory.

---

## Purpose-Built Memory Construction Engine

**Status:** Exploration (2026-04-02)
**Trigger:** Chroma Context-1 report, Gemma 4 release, Mem-α paper (ICLR 2026)
**Full design notes:** `notes/internal/RL_EXTRACTION_MODEL.md`

### Thesis

RL-train a small open model (Gemma 4 E4B, 4.5B params) as a **full memory construction engine** — the entire policy of what to store, update, and delete. Not just extraction, but the complete memory management pipeline in one model call.

Validated by Mem-α (ICLR 2026): RL training on Qwen3-4B produces a memory agent that surpasses GPT-4.1-mini (0.642 vs 0.517 avg accuracy). The approach works.

### Architecture: dual processing paths

```
Generic LLM path (current):
  Messages → [Segmenter] → [EpisodeGen] → [PredictCalibrate] → Knowledge
               LLM call      LLM call        2 LLM calls

Trained engine path (new):
  Messages + KB → [MemoryEngine] → operations → Knowledge
                    one call           ↓
                              episode record (provenance only)
```

Same storage. Same retrieval. Same API. Two paths through the pipeline.

Episodes under the engine path are lightweight provenance records (message group + timestamps + links to produced knowledge), not narrative intermediates.

### Predict-calibrate — implicit via reward

The engine receives `existing_knowledge` as input. Predict-calibrate behavior emerges from training:
- Insert something already in KB → redundancy penalty
- Miss something novel → low QA accuracy
- Correctly skip known info → compression reward

Same principle as the explicit two-step pipeline, learned rather than architected. Optional chain-of-thought in output gives the model a scratchpad for explicit comparison reasoning.

### Action space: expandable by knowledge type

```json
{"operations": [
  {"op": "insert", "type": "semantic", "statement": "...", "confidence": 0.9},
  {"op": "update", "type": "semantic", "supersedes": 3, "statement": "..."},
  {"op": "delete", "type": "semantic", "target": 7}
]}
```

Grows as memv adds types: `semantic` (today) → `episodic` → `procedural` → `core` (user summary, à la Mem-α). Each new type is an incremental training run — the model already understands novelty detection, compression, and contradiction handling.

### Why this is the moat

Every competitor prompts a generic LLM. A purpose-built engine that outperforms GPT-4.1-mini creates a moat through:

- **Training pipeline** — synthetic data generator + reward model + iteration knowledge. Reusable across knowledge types. The asset is the pipeline, not the weights.
- **Reward design** — composite signal (QA accuracy + tool format + compression + content quality) encoding deep understanding of memory quality.
- **Compounding** — semantic is the training ground, procedural is where the moat pays off most (generic LLMs struggle hardest, nobody else competing). Building the pipeline now means procedural memory ships with a trained backbone.

### Reward signal (adapted from Mem-α)

| Reward | What it measures | Weight |
|---|---|---|
| r1: Correctness | Downstream QA accuracy over built memory (via LongMemEval harness) | 1.0 |
| r2: Tool format | Valid structured output, correct operation format | 1.0 |
| r3: Compression | `1 - memory_tokens / input_tokens` | β = 0.05 |
| r4: Content quality | Semantic validity per operation (LLM judge) | γ = 0.1 |

Plus memv-specific: temporal correctness (absolute dates), supersedes accuracy, self-containedness (no pronouns/relative time).

**Algorithm:** GRPO (no critic needed), TRL + Unsloth. Single A100/H100.

### How it reaches users

```
memv library (open source)
├── Storage, retrieval, pipeline — local
└── Processing — pick one:
    ├── Any LLM via PydanticAI (multi-step pipeline, bring your own key)
    ├── memv engine locally (download weights, single-call processing)
    └── memv engine API (hosted, best quality, no GPU needed)
```

Hosted API: `POST /v1/process { messages, existing_knowledge } → { operations[] }`. Revenue: Voyage AI / Cohere model — open source library, charge for hosted engine. API also enables RL flywheel (production signals feed retraining).

### Phases

1. **Benchmark baseline** — LongMemEval with GPT-4 (ceiling) and base Gemma E4B (floor). If gap <10%, deprioritize.
2. **Synthetic environment** — Conversation generator + QA question generator + evaluation pipeline.
3. **SFT warmup** — Distill frontier model operation traces into E4B.
4. **RL fine-tuning** — GRPO with composite reward. Ablate components. Compare against SFT-only and frontier.
5. **Ship** — HuggingFace weights (Apache 2.0), `MemoryEngine` protocol + adapter, hosted API.

### Open questions

1. Is E4B sufficient after SFT alone? Phase 1 answers this.
2. Reward hacking — model gaming QA with trivially true statements? Mem-α's ablation (β=0, γ=0 degenerate) is informative.
3. Multilingual reward components.
4. Model distribution — HuggingFace download on first use vs bundled (~3-5GB quantized).
5. New `MemoryEngine` protocol needed — doesn't fit `LLMClient` (generate/generate_structured).
6. Episode provenance detail level — minimal (timestamps + links) or richer (auto-generated summary)?

---

## Ideas Parking Lot

Not committed to. Revisit based on usage data, benchmark results, and user feedback.

| Idea | Source | Notes |
|------|--------|-------|
| Knowledge relationships (`extends` + cascade) | Supermemory | Deferred from v0.2.0 — open design questions on cascade aggression and undo. See PROGRESS.md 2026-03-25. |
| User profiles (static/dynamic split) | Supermemory | Deferred from v0.2.0 — open question on how to classify static vs dynamic (age-based is wrong). |
| DX: improved `to_prompt()` | — | Temporal annotations, source info, configurable format. |
| DX: token-budgeted retrieval | — | `max_tokens` as alternative to `top_k`, accumulate by descending RRF rank. |
| DX: stats API | — | `count_knowledge/messages/episodes(user_id)` through public API. |
| DX: idempotent writes | Supermemory | `custom_id` on add methods for upsert semantics. Prevents duplicates on retry/replay. |
| DX: simplify constructor | — | `MemoryConfig` only, remove 16 duplicate kwargs from `Memory.__init__`. |
| Benchmark runs (LongMemEval) | —, MemPalace | Baseline: 36.7% task-averaged (5/type, gpt-4o-mini). Extraction quality is the bottleneck, not retrieval. Next: re-run after §10 preference + self-contained fixes. Full 500-question run after extraction quality improves. MemPalace publishes 96.6% R@5 with zero extraction. |
| Score threshold filtering | PR #19 | If revisited, use cosine similarity pre-filter, not normalized RRF. See PROGRESS.md 2026-03-25. |
| Episode-level retrieval fallback | MemPalace | Index episode content (narrative or original_messages) in vector/text indices as a lower-weight RRF signal alongside extracted knowledge. Addresses MemPalace's core argument: extraction loses the "why." memv already stores episodes as ground truth but doesn't search them. Cheap to implement, testable against benchmark. |
| Hierarchical retrieval scoping | MemPalace, multiple competitors | MemPalace measures +34% R@10 from wing/room pre-filtering on 22K+ memories. If benchmark run shows retrieval precision degrades with knowledge count, this is the known fix. Not the same as knowledge categorization — this is search-time scoping, not taxonomy. |
| Retrieval trigger field (`when_to_use`) | ReMe | Interesting but adds LLM output field + extra embedding per fact. Revisit after benchmarks show retrieval is the bottleneck. |
| Retrieval reinforcement | OpenMemory | Boost frequently-retrieved facts. Adds complexity to scoring. Need data showing it helps. |
| Knowledge compaction | MemMachine | Cluster and merge related facts. Solve when knowledge growth is actually a problem. |
| Simhash pre-dedup | ReMe, OpenMemory | Cheap Hamming distance check before embedding comparison. Optimization — solve when dedup cost is measured. |
| Conversation-aware retrieval | cognee, ReMe | LLM query expansion from conversation context. Adds LLM call to retrieval path. |
| Feedback loop | cognee | Confidence adjustment from user corrections. Requires agent framework integration. |
| Extraction cost tracking | — | `ProcessingResult` from `process()`. Nice-to-have observability. |
| Hooks/Events | — | `EventBus` for composability. Useful for framework integration. |
| Memory scoping | — | Namespaces for different memory spaces. No concrete request yet. |
| MCP server | MemPalace | MemPalace ships 19 MCP tools + Claude Code hooks. Real gap for Claude Code early adopters. Separate package. |
| Search results with graph context | Supermemory | Return `context.parents[]` + `context.children[]` with relationship types in retrieval results. Depends on §7 (extends). Retrieval-time join. |
| Memory Router (proxy pattern) | Supermemory | Reverse proxy between app and LLM provider, auto-injects memories. Great adoption UX but wrong layer for a library. Revisit as separate package. |
| `derives` relationship | Supermemory | Inferred knowledge from combining facts, marked `isInference=true`. No validated use case yet. |
| `forgetAfter` / scheduled expiration | Supermemory | Auto-expire memories after a date. We have `invalid_at` (event time) but no automatic pruning at retrieval. |

### Not doing
| Item | Why |
|------|-----|
| Full Knowledge Graph | `extends` + cascade invalidation adopted (§7). Full graph (Neo4j, entity-relation triples, graph traversal queries) is still overkill. `derives` relationship deferred — no validated use case yet. MemPalace has entity-relation triples (SQLite) with temporal validity — solves a different problem than memv's bi-temporal fields (navigable relationships vs. fact versioning). Whether memv needs relational structure is open, not settled. |
| Neo4j backend | Niche. Postgres covers production needs. |
| Background consolidation | Premature without knowledge growth data. |
| `reflect()`-style generation | Wrong layer — memory retrieves, agent generates. |
| Entropy-based pre-filtering | Predict-calibrate already handles extraction quality. |
| Cognitive sector classification | Over-engineered (OpenMemory's 5-sector taxonomy with 5x5 resonance matrix). |
| Multi-phase chain-of-thought retrieval | Adds latency and LLM calls to retrieval. |
