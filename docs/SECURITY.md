# Security

## Secrets

- API tokens and keys live in environment variables / `.env`. `.env` is gitignored.
- The HTTP API, logs, and UI must never return `WORKABLE_ACCESS_TOKEN`,
  `OPENAI_API_KEY`, `Authorization` headers, or Bearer tokens.
- `ats_connections` stores account labels only. Tokens stay in environment variables.
- Structured logging redacts known secret field names.

## Local PII storage

ATS Mirror stores a **normalized local copy** of jobs, candidates, applications,
events, stages, file metadata, and **raw ATS payloads**. Candidate records
include personal information (name, email, phone, location, and whatever the
ATS included in the source JSON).

SQLite is a local-development store. It is not encrypted at rest. Do not point
this process at a shared production database without a retention and access
review.

| Data | Stored locally | Notes |
|---|---|---|
| Job metadata and description | Yes | Dashboard + analytics |
| Candidate PII | Yes | Mirror of ATS fields |
| Application / stage / event metadata | Yes | History |
| Raw ATS JSON | Yes | In `raw_ats_objects`; not shown on ordinary screens |
| File / resume **metadata** | Yes | Name, type, source reference |
| Resume **binaries** | **No** by default | `DOWNLOAD_ATTACHMENTS=false` |
| Vendor access tokens | Env only | Never in SQLite |
| Email / message bodies | Avoided in events | Activity `body` is not copied into event metadata |

## Database location

Default: `sqlite:///./recruiting_ops.db` relative to the process working
directory (usually `backend/`). Override with `DATABASE_URL`. Restrict OS
permissions on that file. Treat backups of the file as PII.

## Retention

Milestone 3 has no automatic purge. Delete the SQLite file (or drop tables) to
wipe the local copy. Plan retention before using this against live recruiting
data.

## Exports

`GET /api/export/candidates.csv` writes normalized candidate fields only
(provider, connection, external id, name, email, phone, headline, location,
current job, stage, source, tags, timestamps). It does not include raw JSON or
CV binaries. Anyone who can read the SQLite file or call the local API can
read mirrored PII. Bind the API to localhost in development.

## Raw payloads

Raw objects exist so normalization can change later. They may contain fields
the UI does not show, including custom fields. Do not dump raw candidate JSON
into logs, error messages, or dashboard tables.

## Resume handling

Workable file `preview_url` values are temporary pre-signed URLs. They are
omitted from stored file metadata. ATS Mirror does not download CV binaries
in Milestone 3.

## Logs

Do not log:

- full resumes
- full raw candidate payloads
- access tokens / Authorization headers
- email bodies from ATS activities

Log sync run ids, object types, external ids, counts, and HTTP status codes.

## Product constraints

ATS Mirror must not:

- modify the ATS (Milestone 3 is read-only toward Workable)
- auto-reject or auto-hire
- infer protected or sensitive characteristics
- score people on age, gender, race, ethnicity, disability, religion, politics,
  health, or family status

Humans make employment decisions. The ATS remains the system of record.

## Local reset

Delete `backend/recruiting_ops.db` (or the file in `DATABASE_URL`) to wipe the
local copy. Then run **Sync now** again if you still have ATS credentials.
