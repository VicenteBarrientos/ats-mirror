# Workable incremental sync

Official Recruiter API (SPI v3) as of the current Workable docs. ATS Mirror
does not invent incremental filters. If an endpoint has no safe `updated_after`
(or equivalent), the fallback is explicit.

Timestamps are sent as official SPI input, e.g. `20150708T115616Z`.
`updated_after` / `created_after` also accept Unix time.

## Per-object matrix

| Object | Endpoint | Incremental parameter? | Parameter | Timestamp semantics | Pagination | Fallback |
|---|---|---|---|---|---|---|
| Jobs | `GET /jobs` | Yes | `updated_after` | Results **updated after** the timestamp (ISO8601 or Unix). Also `created_after`, `since_id`. Must still pass `state`. | `paging.next` until exhausted | Full collection of all four states |
| Candidates | `GET /candidates` | Yes | `updated_after` | Results **updated after** the timestamp. Also `created_after`, `since_id`, `shortcode`. | `paging.next` | Full candidate collection |
| Applications | Derived from candidate payloads | No dedicated collection | — | Application identity is `{candidate_id}:{shortcode}` | — | Incremental: refresh applications only for candidates returned by `updated_after`. Full: every mirrored candidate |
| Stages | `GET /stages` and `GET /jobs/{shortcode}/stages` | No | — | No `updated_after` | Single collection (no paging documented) | Re-fetch the account collection and per-job stages |
| Activities / events | `GET /candidates/{id}/activities` | Yes | `updated_after` | Official: activities **updated equal or later** than the date. Also `since_id`, `actions`. | `limit` / `since_id` | Incremental: every mirrored candidate with `updated_after`. Full: every activity page |
| File metadata | `GET /candidates/{id}/files` | No | — | No incremental filter. `preview_url` is temporary and is not stored | — | Incremental: files for incrementally fetched candidates only. Full: every mirrored candidate. File-only changes that do not bump `candidate.updated_at` wait for a full sync |

`GET /jobs/{shortcode}/activities` has `since_id` / `max_id` but **no** `updated_after`. ATS Mirror uses the per-candidate activities endpoint, which does.

## Watermarks

State is per `AtsConnection`, never global:

| Column | Meaning |
|---|---|
| `connection_id` | Isolated account |
| `sync_scope` | `jobs`, `candidates`, `events`, `mirror` |
| `last_successful_watermark` | `started_at` of the last run that completed that scope without missed pages |
| `last_attempt_at` | Last time that scope was attempted |
| `last_success_at` | When the watermark last advanced |

A watermark advances only when that scope finished without collection failure and without object-level errors that could drop records. A failed candidate collection does not advance the candidate watermark. Jobs can still advance independently.

If no successful jobs+candidates watermarks exist, **Sync changes** runs a full sync.

## Overlap

```
effective_since = last_successful_watermark - INCREMENTAL_OVERLAP_SECONDS
```

Default overlap is **120 seconds**.

Why:

- Official copy says `updated_after` returns results updated **after** the timestamp (exclusive of the exact instant).
- Workable timestamps are often second-granularity.
- Small clock skew between ATS Mirror and Workable should not skip a candidate.

Content hashes and idempotent upserts make overlapping reads harmless. Duplicate reads are preferred over missed records.

## Missing source objects

`source_status` is `present` or `missing_from_source`. Rows are never hard-deleted.

Missing detection runs only after an **authoritative full** collection:

- Jobs: all four states, pagination exhausted, no collection error
- Candidates: full list + details, pagination exhausted
- Stages: account stages plus every mirrored job's stages

Incremental results are partial. They never mark objects missing.

## Read-only

Incremental sync issues **GET** requests only. No POST/PUT/PATCH/DELETE against Workable.
