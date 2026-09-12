# Architecture

ATS Mirror is a self-hosted recruiting **data layer**. Vendor APIs are adapters.
Sync, persistence, and the HTTP API speak only normalized models. The ATS stays
the system of record.

## Layers

| Layer | Responsibility | Location |
|---|---|---|
| UI | Recruiter dashboard over the local mirror | `frontend/` |
| API | HTTP, validation, error mapping | `backend/app/api/` |
| Query | Read SQLite for jobs, candidates, sync history | `backend/app/services/recruiting.py` |
| Ingestion | Provider → raw store → normalized upsert | `backend/app/sync/` |
| Domain | ATS-independent Pydantic models | `backend/app/models/domain.py` |
| Persistence | SQLite via SQLAlchemy 2.0 + Alembic | `backend/app/models/orm.py`, `backend/app/db/` |
| ATS provider | Vendor adapter + capabilities | `backend/app/providers/` |
| Dry-run | Wrap ATS **writes** so they are not sent | `backend/app/providers/dry_run.py` |

```
External ATS
    → ATSProvider
    → SyncService
    → Normalized local database
    → FastAPI
    → Next.js dashboard
```

Ingestion, storage, and querying are separate. Page loads do not call Workable
or the mock ATS. `POST /api/sync/incremental` (Sync changes) is the ordinary
action. `POST /api/sync` is a full collection refresh.

## Identity

Source identity is **connection-scoped**:

- Canonical rows: `(connection_id, external_id)`
- Raw rows: `(connection_id, object_type, external_id)`

`ats_connections` stores `provider`, `external_account_id` (Workable subdomain or `local` for mock), and `account_name`. Secrets are never stored on this table.

The same Workable `external_id` may exist on two connections. ATS Mirror assigns its own internal UUID as `id`.

`content_hash` is SHA-256 of source-controlled content only. It excludes internal UUIDs, `last_synced_at`, `last_seen_at`, sync run ids, and derived fields. See `backend/app/sync/hashing.py`.

## Incremental sync

Each `AtsConnection` has watermarks (`sync_watermarks`) for `jobs`,
`candidates`, `events`, and `mirror`. Workable jobs, candidates, and
per-candidate activities officially support `updated_after`. Stages and files
do not; they use documented fallbacks. See `docs/WORKABLE_INCREMENTAL_SYNC.md`.

A 120-second overlap is subtracted from each watermark before the next
incremental request so second-granularity timestamps cannot skip a record.

## Deletions

Sync is additive/updating. Objects missing from a later fetch are **not**
hard-deleted. `last_seen_at` records the last successful observation.
`source_status` may become `missing_from_source` only after an authoritative
**full** collection. Incremental runs never infer deletion.

## Raw source storage

`raw_ats_objects` keeps the provider payload (content-hashed) so normalization
can evolve, fields not yet modeled are not lost, and provider behavior can be
debugged. Ordinary UI screens do not expose raw JSON.

## Official MCPs

AI agents should use official Workable/Dover MCP integrations for interactive
ATS actions. ATS Mirror does not implement an MCP server, LLM calls, or ATS
writes in the Workable experiment.

Workable field mapping: `docs/WORKABLE_MAPPING.md`.

## Dry run

`DRY_RUN=true` wraps the adapter in `DryRunProvider`. Reads (including sync)
pass through. `move_candidate` / `add_candidate_note` log `Would perform: ...`
and return `WritePreview`. Syncing into SQLite is **not** an ATS write.

## Providers

`build_provider()` in `registry.py` is the only place that selects an adapter.
`MockATSProvider` remains the default for tests and offline development and
syncs through `SyncService` like any other adapter.

Workable is a read-only SPI v3 adapter (`r_jobs`, `r_candidates`). Writes are
not declared as capabilities.
