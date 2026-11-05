from backend.app.schemas.incident import UploadAnalysisResponse
from backend.app.services.image_ingestion_service import ImageIngestionService


def _batch(batch_id: str) -> UploadAnalysisResponse:
    return UploadAnalysisResponse(
        batch_id=batch_id,
        received_at="2026-10-28T00:00:00+00:00",
        total_analyzed=1,
        faults_detected=0,
        discarded_clean=1,
        dashboard_active=False,
    )


def test_recent_batches_are_newest_first_and_limited():
    service = ImageIngestionService(history_limit=3)
    for batch_id in ("one", "two", "three", "four"):
        service.record(_batch(batch_id))

    assert [batch.batch_id for batch in service.recent(2)] == ["four", "three"]
    assert [batch.batch_id for batch in service.recent()] == ["four", "three", "two"]
