# Reading List

Papery, artykuły, repozytoria do przeczytania i notatki z przeczytanych.

---

## Do przeczytania

- [ ] Grounding Agent Memory in Contextual Intent — [arXiv:2601.10702](https://arxiv.org/abs/2601.10702)
- [ ] Beyond Static Summarization: Proactive Memory Extraction for LLM Agents — [arXiv:2601.04463](https://arxiv.org/abs/2601.04463)
- [ ] HiMem: Hierarchical Long-Term Memory for LLM Long-Horizon Agents — [arXiv:2601.06377](https://arxiv.org/abs/2601.06377)
- [ ] Learning How to Remember: A Meta-Cognitive Management Method for Structured and Transferable Agent Memory — [arXiv:2601.07470](https://arxiv.org/abs/2601.07470)
- [ ] MemEvolve: Meta-Evolution of Agent Memory Systems — [arXiv:2512.18746](https://arxiv.org/abs/2512.18746)
- [ ] Memento 2: Learning by Stateful Reflective Memory — [arXiv:2512.22716](https://arxiv.org/abs/2512.22716)
- [ ] Improving Language Agents through BREW — [arXiv:2511.20297](https://arxiv.org/abs/2511.20297)
- [ ] Remember Me, Refine Me: A Dynamic Procedural Memory Framework for Experience-Driven Agent Evolution — [arXiv:2512.10696](https://arxiv.org/abs/2512.10696)
- [ ] Context Engineering survey — [arXiv:2507.13334](https://arxiv.org/abs/2507.13334)
- [ ] LongMemEval benchmark — [arXiv:2407.xxxxx](https://arxiv.org/abs/2407.xxxxx)
- [ ] ...

---

## Przeczytane

### Graphiti paper — [arXiv:2501.13956](https://arxiv.org/abs/2501.13956)

**TL;DR:** Bi-temporal knowledge graph dla agentów. Edge invalidation, entity resolution, BFS retrieval.

**Key insights:**
- Bi-temporal: event time (kiedy fakt był prawdą) vs transaction time (kiedy zapisaliśmy)
- Entity resolution przez LLM similarity
- Episodic → Entity → Fact hierarchy

**Co bierzemy:** Bi-temporal model, edge invalidation concept

---

### Nemori paper — [arXiv:2508.03341](https://arxiv.org/abs/2508.03341)

**TL;DR:** Predict-calibrate extraction. Importance emerges from prediction error.

**Key insights:**
- Zamiast "oceń czy ważne" → "przewiduj co będzie, wyciągnij czego nie przewidziałeś"
- Episode segmentation przez topic detection
- Hybrid retrieval: vector + BM25

**Co bierzemy:** Predict-calibrate jako core mechanism, batch segmentation

---

### SimpleMem paper — [arXiv:2501.xxxxx](https://arxiv.org/abs/2501.xxxxx)

**TL;DR:** Write-time atomization = 56.7% temporal reasoning. Simple > complex.

**Key insights:**
- "yesterday" → absolute date AT WRITE TIME, nie retrieval time
- Coreference resolution at write time
- 531 tokens/query vs 2745 (Nemori)
- k=3 gives 99% of peak performance

**Co bierzemy:** Write-time disambiguation principle

---

### Letta benchmark — [blog post](https://www.letta.com/blog/benchmarking-ai-agent-memory)

**TL;DR:** Simple filesystem + agent tool use = 74% LoCoMo. Beat Mem0 (68.5%).

**Key insight:** Memory is about context management, not retrieval mechanism. Explicit > implicit.

---

### claude-mem — [GitHub](https://github.com/nicobailon/claude-mem)

**TL;DR:** Claude Code plugin. Spawns a passive observer LLM agent that watches tool calls, extracts structured observations, stores in SQLite + ChromaDB, injects context at session start.

**Architecture:** Lifecycle hooks (UserPromptSubmit, PostToolUse, Stop) → background worker (Bun/Express, port 37777) → SDK agent (observer-only, no tool access) → XML observation parsing → SQLite + ChromaDB.

**Key insights:**
- Granular vectorization: each fact/narrative field embedded separately in ChromaDB, not the whole observation. IDs: `obs_{id}_fact_0`, `obs_{id}_narrative`. Retrieval matches specific facts, not averaged embeddings.
- Token ROI tracking: each observation stores `discovery_tokens` (cost to extract). At injection, displays savings percentage vs re-reading source material.
- Progressive context injection: recent N observations → full narrative+facts, older ones → title+subtitle only.
- Privacy: `<private>content</private>` tags stripped at hook layer before reaching worker.
- Mode system: JSON configs for domain-specific extraction profiles (code, email-investigation, etc.) with locale inheritance (`code--ko`).
- Content hash dedup (sha256, 30s window) — no semantic dedup.

**Gaps:** No temporal model, no contradiction detection, no semantic dedup between observations, no user isolation.

**Ideas for memv:** Granular per-field vectorization (if statements get long), token ROI tracking as extension of cost tracking.

---

### cognee — [GitHub](https://github.com/topoteretes/cognee)

**TL;DR:** Document-to-knowledge-graph pipeline. ECL: Extract → Cognify → Load. LLM extracts entities+relationships per chunk, stores in property graph (Kuzu) + vector DB (LanceDB), graph-aware retrieval.

**Architecture:** `add()` → raw file storage. `cognify()` → classify → chunk → LLM extract KnowledgeGraph per chunk → expand with entities/types → write to graph+vector. `search()` → 13 retrieval strategies. `memify()` → post-cognify enrichment.

**Key insights:**
- Triplet scoring algorithm: vector-search across all DataPoint collections simultaneously, map similarity scores onto graph nodes AND edges, rank by combined score of (node1 + edge + node2). Respects graph structure — both endpoints and the relationship must match.
- Iterative context extension (GRAPH_COMPLETION_CONTEXT_EXTENSION): use initial retrieval + LLM output as next query, expand until convergence. Handles multi-hop questions.
- Chain-of-thought retrieval (GRAPH_COMPLETION_COT): validate answer, generate follow-ups, fetch more triplets, merge, re-answer. Up to 4 reasoning rounds.
- OWL ontology grounding: fuzzy-match extracted entities against controlled vocabularies (80% threshold). Grounds synonyms without the LLM needing to know the vocabulary.
- Feedback loop: classify user's next message as feedback (1-5 score) or new question. Attaches score to previous QA record.
- `FEELING_LUCKY` retrieval: LLM picks best search strategy for the query from all 13 types.
- Provenance: every DataPoint stores `source_pipeline`, `source_task`, `source_user`.
- No semantic dedup — only ID-based (deterministic hash of entity name).

**Ideas for memv:** Feedback loop on retrieval quality (section 22), iterative context extension for multi-hop queries.

---

### MemMachine — [GitHub](https://github.com/memmachineapp/memmachine)

**TL;DR:** Self-hosted server (FastAPI + Neo4j + PostgreSQL). Two parallel memory systems: episodic (graph-based, short-term deque + long-term Neo4j) and semantic (structured LLM-driven profile with ADD/DELETE commands).

**Architecture:** Message → EpisodeStorage (raw log) + ShortTermMemory (in-process deque, LLM-summarized on overflow) + LongTermMemory (Neo4j graph with Derivative nodes) + SemanticMemory (pgvector feature store, background ingestion).

**Key insights:**
- Derivative node architecture: episodes and searchable derivatives are separate node types linked by edges. Cleanly separates "what was said" from "what is indexed". Sentence-level chunking optional.
- Semantic memory as structured profile: LLM outputs ADD/DELETE commands against existing profile JSON. Not summaries — imperative mutations. Two operations only. Profile is a key-value store scoped by hierarchical set_id.
- Memory consolidation lifecycle: when features accumulate (threshold=20), LLM merges overlapping features. Prompt uses metaphor: raw ore → pure pellets → sorted bins → alloyed memories. Minimizes interference, not just count.
- Multi-dimensional set_id scoping: features fan out into org-level, user-level (cross-project), project-level, and custom sets simultaneously. A message indexes into multiple scopes at once.
- Citations on semantic features: every feature stores `citation_id`s (episode IDs that caused it). Consolidated features inherit citations from deleted sources.
- Context expansion: asymmetric forward/backward weighting (2/3 forward, 1/3 backward) around matched episodes.
- Score threshold filtering at search layer.
- Context window overflow recovery: recursive batch halving until fit.
- Per-set embedder/LLM override with cross-embedding-space protection.

**Ideas for memv:** Structured user profile layer (separate from free-form knowledge), score threshold filtering (section 16), citation preservation through compaction.

---

### OpenMemory — [GitHub](https://github.com/openmemory/openmemory)

**TL;DR:** Local cognitive memory engine. Classifies by 5 cognitive sectors (episodic, semantic, procedural, emotional, reflective), multi-sector embeddings, salience decay, waypoint graph, separate temporal KG.

**Architecture:** HSG (Hierarchical Sectored Graph). Each memory gets sector classification (regex-based), one embedding per sector, a mean vector, salience score, simhash. Waypoint graph links memories by mean-vector similarity. Temporal KG stores SPO triples with validity windows.

**Key insights:**
- Cross-sector interdependence matrix: 5×5 weight matrix encoding cognitive resonance between sectors (episodic↔reflective: 0.8, procedural↔emotional: 0.2). Penalizes irrelevant sector crossings during retrieval.
- Vector compression as forgetting: progressive dimension reduction (1536 → 128 → 32-dim fingerprint) as salience drops. Re-access triggers full re-embedding ("regeneration"). Memory exists but in low-precision form until needed.
- Salience-modulated decay: `decay_factor = exp(-lambda * (days / (salience + 0.1)))`. High-salience memories decay slower even at same tier.
- Retrieval reinforcement: boost salience by `0.18 * (1 - salience)` on access, propagate to waypoint neighbors with attenuation, strengthen traversed edges.
- Adaptive waypoint expansion: when top-k similarity < 0.55 (low confidence), BFS through waypoint graph to expand candidates. High-confidence queries skip graph expansion.
- Simhash dedup: Hamming distance ≤ 3 = duplicate, boost existing salience by 0.15 instead of inserting.
- Automatic timeline closure in temporal KG: new fact with same (subject, predicate) auto-closes the previous one.
- Segment-based random decay sampling: 3% of a 10k segment per run, O(1) not O(n).
- Reflection system: lexical clustering (Jaccard > 0.8, not LLM-based), concatenation summary stored as `reflective` sector memory.

**Gaps:** Classifier is English-only regex. SQLite vector search is full scan. Reflection is lexical, not semantic. No LLM extraction pipeline.

**Ideas for memv:** Simhash pre-dedup (section 15), retrieval reinforcement (section 19), salience-modulated decay formula, automatic temporal fact closure.

---

### ReMe — [arXiv:2512.10696](https://arxiv.org/abs/2512.10696) / [GitHub](https://github.com/AgentScope/ReMe)

**TL;DR:** "Remember Me, Refine Me" — agentic memory framework with 6 memory types (identity, personal, procedural, tool, summary, history). Two-phase summarization via ReAct agents. Dual mode: vector-based and file-based.

**Architecture:** Orchestrator agent → DelegateTask → specialized agents (PersonalSummarizer, ProceduralSummarizer, ToolSummarizer). Each runs two ReAct phases: S1 (draft + similarity check + selective add) and S2 (profile update). Built on FlowLLM runtime.

**Key insights:**
- `when_to_use` field: memory nodes have `content` (the fact) and `when_to_use` (retrieval trigger). Embedding is computed from `when_to_use` when present, not from `content`. Retrieval matches on intent, not raw text.
- History as traceable anchor: raw conversation stored as HISTORY-type node, individual facts store `ref_memory_id` linking back. Every extracted fact traceable to source conversation.
- Dedup at reasoning level: the agent sees existing similar memories BEFORE deciding to add new ones. Not post-hoc — the LLM decides whether a draft is already covered.
- Profile vs memory duality: structured key-value profiles (`name: Alice`, max 50 entries, file-based) separate from free-form episodic memory nodes (vector-indexed). Profiles always complete, always injected.
- Content-hash IDs: `sha256(content)[:16]` — identical content = same ID = natural dedup.
- Multi-phase retrieval: Phase 1 (semantic, 3-5 query formulations), Phase 2 (temporal, only if time reference detected), Phase 3 (history deep-dive, max 3 reads).
- Procedural memory enforcement: prompt strictly rejects descriptive facts, only accepts actionable patterns ("When X, do Y" not "X happened").
- Tool memory with performance stats: `ToolCallResult` with success rate, token cost, time cost, rolling averages. Enables data-driven tool selection.
- File-based mode: Markdown files (MEMORY.md + daily logs), compaction with structured sections, file watcher for auto-reindexing.
- Context compaction handles split-turn edge case: if cut falls mid-assistant-turn, separately summarizes prefix, keeps suffix.

**Ideas for memv:** Retrieval trigger field (section 18), content-hash pre-dedup (section 15), structured profile layer (future), procedural memory enforcement patterns (section 29).
