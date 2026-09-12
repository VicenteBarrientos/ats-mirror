from __future__ import annotations

import csv
from io import StringIO

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.api.deps import get_service
from app.services.recruiting import RecruitingService

router = APIRouter(prefix="/export", tags=["export"])


@router.get("/candidates.csv")
def export_candidates_csv(service: RecruitingService = Depends(get_service)) -> StreamingResponse:
    buffer = StringIO()
    writer = csv.DictWriter(
        buffer,
        fieldnames=[
            "provider",
            "connection",
            "external_candidate_id",
            "name",
            "email",
            "phone",
            "headline",
            "location",
            "current_job",
            "stage",
            "source",
            "tags",
            "created_at",
            "source_updated_at",
            "last_synced_at",
        ],
    )
    writer.writeheader()
    for row in service.export_candidate_rows():
        writer.writerow(row)
    buffer.seek(0)
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=ats-mirror-candidates.csv"},
    )
