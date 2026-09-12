# Workable mapping

Evidence for ATS Mirror's canonical schema, based on:

- Official Recruiter API SPI v3 (`https://{subdomain}.workable.com/spi/v3`)
- Official docs: [jobs](https://workable.readme.io/reference/jobs), [candidates](https://workable.readme.io/reference/job-candidates-index)
- HTTP-mocked adapter tests
- Read-only inspection of a live Workable account via the **official Workable MCP** (sample jobs/candidates). That MCP is **not** ATS Mirror's database and is not used at runtime.

Auth for ATS Mirror itself: `Authorization: Bearer <account token>` with scopes `r_jobs` and `r_candidates`. Subdomain is the connection account id. Secrets stay in env (`WORKABLE_SUBDOMAIN`, `WORKABLE_ACCESS_TOKEN`).

Identity:

| Layer | Key |
|---|---|
| Connection | `ats_connections.provider=workable` + `external_account_id=<subdomain>` |
| Canonical / raw | `(connection_id, external_id)` / `(connection_id, object_type, external_id)` |

## Jobs — `GET /jobs`

Full mirror iterates `state=published|draft|closed|archived` and follows `paging.next`. Defaulting to a single state would miss closed/draft/archived roles (observed: published empty, closed present).

| Workable source | Canonical destination | Transformation | Nullability | Lost if not in raw |
|---|---|---|---|---|
| `shortcode` | `Job.external_id` | string | required (fallback `id`) | no |
| `id` | raw only | vendor job id, distinct from shortcode | required in API | canonical uses shortcode |
| `title` | `Job.title` | string | required | no |
| `full_title` | raw | unused | optional | yes, unless raw kept |
| `code` | raw | editor job code | optional | yes |
| `state` | `Job.status` | `published→open`, `draft→draft`, `closed→closed`, `archived→archived` | required | original slug kept in raw |
| `department` | `Job.department` | string | optional (often null) | no |
| `department_hierarchy` | raw | ancestor list | optional | yes |
| `location.location_str` or city/region/country | `Job.location` | joined string | optional | structured location object stays in raw |
| `locations[]` | raw | all locations | optional | yes |
| `workplace_type` | raw | `on_site/hybrid/remote` | optional | yes |
| `description` / `full_description` | `Job.description` | via `include_fields=description` | optional | no |
| `created_at` | `Job.created_at` | ISO datetime | required (fallback now) | no |
| `updated_at` | `source_updated_at` + raw hash | ISO datetime | optional | no |
| `salary.*` | raw | integers + currency | optional | yes |
| `confidential` | raw | bool | optional | yes |
| `sample` | raw | bool (demo data) | optional | yes |
| `url` / `application_url` / `shortlink` | raw | URLs | optional | yes |
| `keywords` | raw | | optional | yes |

## Candidates — `GET /candidates` then `GET /candidates/{id}`

List payloads are **application-centric**: the same person can appear once per job. Canonical `Candidate.external_id` is Workable `id`. Duplicates are collapsed during iteration.

| Workable source | Canonical destination | Transformation | Nullability | Lost if not in raw |
|---|---|---|---|---|
| `id` | `Candidate.external_id` | string | required | no |
| `name` | `Candidate.name` | string | required (fallback Unnamed) | no |
| `firstname` / `lastname` | raw | | optional | split name only in raw |
| `headline` | `Candidate.headline` | string | optional | no |
| `email` | `Candidate.email` | string | optional | no |
| `phone` | `Candidate.phone` | string | optional | no |
| `address` | `Candidate.location` fallback | string | optional | structured address only if `location` object present |
| `location` | `Candidate.location` | same helper as jobs | optional | no |
| `stage` | `Candidate.current_stage` | list-view stage for this job application | optional | per-application stage is the application row |
| `stage_kind` | raw | `applied/sourced/assessment/hired/…` | optional | yes |
| `summary` | `Candidate.summary` | from detail | optional | no |
| `skills` | `Candidate.skills` | string or `{name}` list | optional | no |
| `tags` | `Candidate.tags` | string list | optional | no |
| `common_source` else `domain` | `Candidate.source` | prefer `common_source` | optional | `common_source_category` only in raw |
| `social_profiles[]` | `Candidate.social_links` | `{network,name,url}` | optional | extra keys stay in raw |
| `experience_entries[]` | `Candidate.experience` | dicts as returned | optional | no |
| `education_entries[]` | `Candidate.education` | dicts as returned | optional | no |
| `created_at` / `updated_at` | `created_at` / `source_updated_at` | ISO datetime | created required | no |
| `account.subdomain` / `account.name` | connection account | used to label `ats_connections` | optional | no |
| `profile_url` | raw | | optional | yes |
| `anonymized` / `disqualification_reason` | raw | | optional | yes |
| `resume_metadata` | raw (+ file metadata if files API returns it) | `{filename,filetype,created_at,updated_at}` | optional | binary CV is **not** downloaded |
| `job.shortcode` | application, not candidate | see below | required for application | a candidate without `job` cannot form an application |

## Applications

Workable has no standalone application id in the list API. ATS Mirror synthesizes:

`external_id = {candidate.id}:{job.shortcode}`

| Workable source | Canonical destination | Transformation | Nullability | Notes |
|---|---|---|---|---|
| `id` (candidate) | `Application.candidate_id` (external) then FK | | required | |
| `job.shortcode` | `Application.job_id` (external) then FK | | required | |
| `stage` | `Application.stage` | string | optional | |
| `disqualified` / `withdrew` / `hired_at` / `stage_kind` | `Application.status` | rejected / withdrawn / hired / else active | derived | original flags stay in raw |
| `created_at` | `Application.created_at` | ISO datetime | optional | |

Information lost without raw: `moved_to_offer_at`, `sourced`, `outlet`.

## Stages — `GET /stages` and `GET /jobs/{shortcode}/stages`

| Workable source | Canonical destination | Transformation | Nullability | Notes |
|---|---|---|---|---|
| `slug` or `id` or `name` | `Stage.external_id` | `{job_id}:{slug}` when job-scoped | required | |
| `name` | `Stage.name` | string | required | |
| `position` | `Stage.position` | int else 0 | optional | |
| `kind` | raw | | optional | |

## Events — `GET /candidates/{id}/activities`

| Workable source | Canonical destination | Transformation | Nullability | Notes |
|---|---|---|---|---|
| synthetic hash of candidate+action+created_at+stage+member | `RecruitingEvent.external_id` | SHA-256 prefix | required | Workable activities have no stable public id |
| `action` | `event_type` + metadata.action | mapped set (applied, moved, comment, …) else `other` | required | |
| `created_at` | `timestamp` | ISO datetime | required | |
| `stage_name` / `target_stage.name` / `member.name` | metadata | | optional | |
| `body` | **omitted** | not stored on the event or in raw | | PII / email-like content |

## File metadata — `GET /candidates/{id}/files`

| Workable source | Canonical destination | Transformation | Nullability | Notes |
|---|---|---|---|---|
| hash(candidate, name, source) | `FileMetadata.external_id` | SHA-256 prefix | required | files have no durable id in the payload used here |
| `name` | `filename` | string | required | |
| `kind` | `file_type` | string | optional | |
| `source`/`kind` | `source_ref` | string | optional | |
| `created_at` | `created_at` | ISO datetime | optional | |
| `preview_url` | **dropped** | temporary S3 URL | | `preview_url_omitted=true` in raw |

`DOWNLOAD_ATTACHMENTS=false`. CV binaries are not fetched.

## Pagination

`paging.next` is followed until absent. Next URLs may be on `www.workable.com/spi/v3/accounts/{subdomain}/...`. The adapter follows the URL as returned with the same Bearer header. `since_id` appears on subsequent pages.

## Incremental filters

Jobs and candidates accept official `updated_after`. Candidate activities also
accept `updated_after`. Stages and files do not. Details:
[Workable incremental sync](WORKABLE_INCREMENTAL_SYNC.md).

## Deletions

ATS Mirror does **not** hard-delete local rows when a Workable object is missing
from a later fetch. After an authoritative **full** jobs/candidates/stages
collection, unseen rows are marked `source_status=missing_from_source`.
`last_seen_at` is left as the last successful observation. Incremental runs
never infer deletion.

## What this implies for a later multi-ATS model

Keep as first-class:

- Job shortcode-like **external id that is not the vendor numeric id**
- Application as a first-class entity even when the vendor nests it on the candidate
- Stage kind vs stage name
- Source vs source category
- File metadata without durable vendor file ids
- Activity streams without stable ids (hash carefully; exclude bodies)

Do not force Workable salary, workplace_type, or department hierarchy into generic columns until a second ATS proves they are shared.
