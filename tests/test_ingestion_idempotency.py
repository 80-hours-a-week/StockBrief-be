from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.orm import Base, IngestionRun
from app.services.ingestion_idempotency import IngestionIdempotencyService


@pytest.fixture()
def db_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def test_compute_input_hash_is_stable_for_key_order() -> None:
    left = {"provider": "OpenDART", "ticker": "005930", "date": "2026-06-18"}
    right = {"date": "2026-06-18", "ticker": "005930", "provider": "OpenDART"}

    assert IngestionIdempotencyService.compute_input_hash(left) == (
        IngestionIdempotencyService.compute_input_hash(right)
    )


def test_start_run_persists_started_state_and_json_scope(db_session: Session) -> None:
    service = IngestionIdempotencyService(db_session)
    input_hash = service.compute_input_hash({"ticker": "005930"})

    run = service.start_run(
        run_id="opendart-20260618-005930",
        job_type="disclosure",
        provider="OpenDART",
        target_scope={"ticker": "005930"},
        input_hash=input_hash,
    )

    assert run.status == "started"
    assert run.target_scope == {"ticker": "005930"}
    assert run.result_counts == {}
    assert run.completed_at is None


def test_run_id_is_unique(db_session: Session) -> None:
    input_hash = "hash-1"
    db_session.add(
        IngestionRun(
            run_id="naver-20260618-005930",
            job_type="news",
            provider="NAVER",
            target_scope={"ticker": "005930"},
            status="started",
            input_hash=input_hash,
            started_at=datetime.now(timezone.utc),
            result_counts={},
        )
    )
    db_session.commit()

    db_session.add(
        IngestionRun(
            run_id="naver-20260618-005930",
            job_type="news",
            provider="NAVER",
            target_scope={"ticker": "005930"},
            status="started",
            input_hash="hash-2",
            started_at=datetime.now(timezone.utc),
            result_counts={},
        )
    )
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_duplicate_detection_only_counts_succeeded_runs(db_session: Session) -> None:
    service = IngestionIdempotencyService(db_session)
    input_hash = service.compute_input_hash({"ticker": "005930"})
    run = service.start_run(
        run_id="krx-20260618-005930",
        job_type="price",
        provider="KRX",
        target_scope={"ticker": "005930"},
        input_hash=input_hash,
    )

    assert service.is_duplicate(run_id=run.run_id, input_hash=input_hash) is False

    service.mark_succeeded(run=run, result_counts={"inserted": 1, "updated": 0})

    assert service.is_duplicate(run_id=run.run_id, input_hash="other") is True
    assert service.is_duplicate(run_id="other", input_hash=input_hash) is True


def test_status_transitions_record_completion_payloads(db_session: Session) -> None:
    service = IngestionIdempotencyService(db_session)
    run = service.start_run(
        run_id="score-20260618",
        job_type="score",
        provider="StockBrief",
        target_scope={"as_of": "2026-06-18"},
        input_hash="score-hash",
    )

    service.mark_partial_failed(
        run=run,
        result_counts={"inserted": 2, "failed": 1},
        error_summary={"code": "provider_timeout"},
    )

    assert run.status == "partial_failed"
    assert run.completed_at is not None
    assert run.result_counts == {"inserted": 2, "failed": 1}
    assert run.error_summary == {"code": "provider_timeout"}

    service.mark_failed(run=run, error_summary={"code": "replay_failed"})

    assert run.status == "failed"
    assert run.error_summary == {"code": "replay_failed"}
