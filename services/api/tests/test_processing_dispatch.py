"""API -> Celery dispatch contract for POST /inspections/{id}/process."""

import uuid

import pytest
from app.core.task_queue import TaskDispatchError
from app.models.jobs import ProcessingJob
from sqlalchemy import select

from tests.conftest import ORG_1_ID
from tests.test_inspections import get_token

DISPATCH = "app.api.v1.endpoints.inspections.dispatch_inspection_processing"


class RecordingDispatch:
    def __init__(self):
        self.calls: list[tuple[uuid.UUID, uuid.UUID, uuid.UUID]] = []

    def __call__(self, job_id, inspection_id, organization_id):
        self.calls.append((job_id, inspection_id, organization_id))
        return str(job_id)


async def _authority_headers(async_client):
    token = await get_token(async_client, email="authority@example.com", password="AuthoritySecret123!")
    return {"Authorization": f"Bearer {token}", "X-Organization-ID": str(ORG_1_ID)}


async def _submitted_inspection(async_client, headers, with_media=True) -> str:
    created = await async_client.post("/api/v1/inspections", json={"notes": "dispatch"}, headers=headers)
    insp_id = created.json()["data"]["id"]
    if with_media:
        resp = await async_client.post(
            f"/api/v1/inspections/{insp_id}/media/complete",
            json={
                "storage_path": f"inspections/{insp_id}/a.jpg",
                "media_type": "IMAGE",
                "mime_type": "image/jpeg",
                "size_bytes": 10,
            },
            headers=headers,
        )
        assert resp.status_code == 201
    submitted = await async_client.post(f"/api/v1/inspections/{insp_id}/submit", headers=headers)
    assert submitted.status_code == 200
    return insp_id


async def _jobs_for(db_session, insp_id: str) -> list[ProcessingJob]:
    stmt = select(ProcessingJob).where(ProcessingJob.entity_id == uuid.UUID(insp_id))
    return list((await db_session.execute(stmt)).scalars().all())


@pytest.mark.asyncio
async def test_process_dispatches_task_for_committed_job(async_client, db_session, monkeypatch):
    dispatch = RecordingDispatch()
    monkeypatch.setattr(DISPATCH, dispatch)
    headers = await _authority_headers(async_client)
    insp_id = await _submitted_inspection(async_client, headers)

    resp = await async_client.post(f"/api/v1/inspections/{insp_id}/process", headers=headers)

    assert resp.status_code == 202
    job_id = resp.json()["data"]["job_id"]
    assert len(dispatch.calls) == 1
    sent_job, sent_insp, sent_org = dispatch.calls[0]
    assert (str(sent_job), str(sent_insp), sent_org) == (job_id, insp_id, ORG_1_ID)

    # The job row is durable (committed) before the worker can receive the task.
    (job,) = await _jobs_for(db_session, insp_id)
    assert str(job.id) == job_id
    assert job.status == "QUEUED"
    assert job.idempotency_key == f"inspection:{insp_id}:attempt:1"


@pytest.mark.asyncio
async def test_repeated_process_requests_return_the_active_job(async_client, db_session, monkeypatch):
    dispatch = RecordingDispatch()
    monkeypatch.setattr(DISPATCH, dispatch)
    headers = await _authority_headers(async_client)
    insp_id = await _submitted_inspection(async_client, headers)

    first = await async_client.post(f"/api/v1/inspections/{insp_id}/process", headers=headers)
    second = await async_client.post(f"/api/v1/inspections/{insp_id}/process", headers=headers)

    assert first.status_code == second.status_code == 202
    assert first.json()["data"]["job_id"] == second.json()["data"]["job_id"]
    assert len(dispatch.calls) == 1
    assert len(await _jobs_for(db_session, insp_id)) == 1


@pytest.mark.asyncio
async def test_idempotency_key_replay_returns_same_job(async_client, db_session, monkeypatch):
    dispatch = RecordingDispatch()
    monkeypatch.setattr(DISPATCH, dispatch)
    headers = await _authority_headers(async_client)
    insp_id = await _submitted_inspection(async_client, headers)
    keyed = {**headers, "Idempotency-Key": f"client-{insp_id}"}

    first = await async_client.post(f"/api/v1/inspections/{insp_id}/process", headers=keyed)
    (job,) = await _jobs_for(db_session, insp_id)
    job.status = "COMPLETED"  # even after the job finished, replay must not create new work
    await db_session.commit()
    replay = await async_client.post(f"/api/v1/inspections/{insp_id}/process", headers=keyed)

    assert replay.status_code == 202
    assert replay.json()["data"]["job_id"] == first.json()["data"]["job_id"]
    assert replay.json()["data"]["status"] == "COMPLETED"
    assert len(dispatch.calls) == 1


@pytest.mark.asyncio
async def test_dispatch_failure_marks_job_failed_and_allows_retry(async_client, db_session, monkeypatch):
    def broken_dispatch(*_args):
        raise TaskDispatchError("Error 111 connecting to redis:6379")

    monkeypatch.setattr(DISPATCH, broken_dispatch)
    headers = await _authority_headers(async_client)
    insp_id = await _submitted_inspection(async_client, headers)

    resp = await async_client.post(f"/api/v1/inspections/{insp_id}/process", headers=headers)

    assert resp.status_code == 503
    assert resp.json()["error"]["code"] == "TASK_QUEUE_UNAVAILABLE"
    (failed_job,) = await _jobs_for(db_session, insp_id)
    assert failed_job.status == "FAILED"
    assert failed_job.error_code == "TASK_DISPATCH_FAILED"
    insp = (await async_client.get(f"/api/v1/inspections/{insp_id}", headers=headers)).json()["data"]
    assert insp["status"] == "PROCESSING_FAILED"

    # Broker recovered: retry creates attempt 2 and dispatches it.
    dispatch = RecordingDispatch()
    monkeypatch.setattr(DISPATCH, dispatch)
    retry = await async_client.post(f"/api/v1/inspections/{insp_id}/process", headers=headers)

    assert retry.status_code == 202
    assert retry.json()["data"]["job_id"] != str(failed_job.id)
    assert len(dispatch.calls) == 1
    jobs = await _jobs_for(db_session, insp_id)
    assert sorted(j.idempotency_key for j in jobs) == [
        f"inspection:{insp_id}:attempt:1",
        f"inspection:{insp_id}:attempt:2",
    ]


@pytest.mark.asyncio
async def test_process_without_media_is_rejected(async_client, monkeypatch):
    dispatch = RecordingDispatch()
    monkeypatch.setattr(DISPATCH, dispatch)
    headers = await _authority_headers(async_client)
    insp_id = await _submitted_inspection(async_client, headers, with_media=False)

    resp = await async_client.post(f"/api/v1/inspections/{insp_id}/process", headers=headers)

    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "INSPECTION_HAS_NO_MEDIA"
    assert dispatch.calls == []
