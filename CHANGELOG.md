# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.2] - 2026-03-30

### Added

- PostgreSQL backend with pgvector and tsvector (#23)
- Complete store/index protocols and backend factory (#22)
- Voyage, Cohere, and fastembed embedding adapters (#25)
- PR template (#26)
- Backend documentation and fix outdated references (#24)

### Changed

- Documentation theme: monochrome + electric blue accent, restructured nav (#27)

## [0.1.1] - 2026-03-25

### Added

- Direct knowledge injection API (#18)
- Index-based contradiction handling with audit trail (#17)
- `user_id` denormalization and knowledge CRUD operations (#16)
- Knowledge atomization for self-contained extraction (#13, #14)
- Integration and e2e tests for pipeline (#12)
- Integration tests for all stores (#11)

### Fixed

- Remove episodes from retrieval surface (#8)
- Drop duplicate embedding column from `semantic_knowledge` (#21)
- Correct `uv add` command in docs to use PyPI name `memvee`

## [0.1.0] - 2026-02-10

### Added

- Initial release
- `Memory` class — high-level API for structured, temporal memory
- Predict-calibrate knowledge extraction (importance from prediction error)
- Bi-temporal validity model for knowledge
- Hybrid retrieval with Reciprocal Rank Fusion (vector + BM25)
- Episode segmentation via LLM-based boundary detection
- Episode merging for redundancy reduction
- SQLite storage with sqlite-vec for vector search and FTS5 for text search
- OpenAI embedding adapter
- PydanticAI multi-provider LLM adapter
- Framework integration examples (PydanticAI, LangGraph, LlamaIndex, CrewAI, AutoGen)
- MkDocs documentation site with Material theme
