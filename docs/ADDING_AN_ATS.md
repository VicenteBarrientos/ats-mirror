# Adding an ATS adapter

The business logic must never import a vendor SDK. Future adapters (Dover,
Greenhouse, Lever, Ashby) plug into the same pipeline:

```
ATSProvider → SyncService → normalized SQLite → FastAPI → UI
```

Register a **connection** (`provider` + `external_account_id`). Source identity is
`(connection_id, external_id)`, not `external_id` globally.

To add Dover (or any ATS):

1. **Implement `ATSProvider`** in `backend/app/providers/<name>.py`. Start
   read-only (`health_check`, `list_jobs` / `iter_jobs`, `get_job`,
   `list_candidates` / `iter_candidates`, `get_candidate`,
   `get_candidate_applications`, `get_stages`, `get_candidate_events`).
   If the official API documents an incremental filter, accept
   `updated_after` on `iter_jobs` / `iter_candidates` / `get_candidate_events`.
   Do not fake incremental parameters. Leave writes unimplemented until reads
   are verified against **current official** documentation.

2. **Map vendor payloads** to normalized models (`Job`, `Candidate`,
   `Application`, `RecruitingEvent`, `Stage`, `FileMetadata`). Do not leak
   vendor field names (`shortcode`, `account_id`, etc.) into those models.
   Keep a copy of the source object via `consume_raw()` so `SyncService` can
   persist `raw_ats_objects`.

3. **Paginate until exhaustion.** Never sync only the first page. Offset
   helpers live in `app/providers/pagination.py`. Workable-style `paging.next`
   uses `follow_next_pages`.

4. **Declare `capabilities`.** Only advertise operations the official API
   actually supports. Unsupported calls must raise `UnsupportedCapabilityError`.
   Do not declare write capabilities until writes are intentionally added.

5. **Register the factory** in `backend/app/providers/registry.py`:

   ```python
   _FACTORIES["dover"] = lambda settings: DoverATSProvider(settings)
   ```

6. **Add authentication configuration** to `Settings` and `.env.example`.
   Never hard-code subdomains or tokens. Never log them. Never send them to
   the frontend.

7. **Run provider contract tests**. Append an instance to
   `contract_providers()` in `backend/tests/providers/helpers.py`. Keep vendor
   HTTP mocked. Tests must pass without a real token.

8. **Sync through `SyncService`.** Do not fetch the ATS from
   `RecruitingService` or dashboard GET handlers. The dashboard reads SQLite.

Until an adapter is registered, `ATS_PROVIDER=<name>` should raise
`ProviderConfigError` with a specific message.

Interactive ATS actions (move candidate, add note) belong in official MCP
integrations, not in this mirror, unless a later milestone explicitly adds
writes.
