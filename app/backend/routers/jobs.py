"""Router de jobs: encolar, listar, ver, cancelar."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from jobs import manager
from models import Job

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


class JobCreate(BaseModel):
    type: str
    payload: dict = {}


@router.get("/types")
def api_job_types() -> dict:
    return {"types": manager.supported_types()}


@router.post("", response_model=Job)
def api_create_job(payload: JobCreate) -> Job:
    try:
        return manager.create(payload.type, payload.payload)
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("", response_model=list[Job])
def api_list_jobs() -> list[Job]:
    return manager.list()


@router.get("/{job_id}", response_model=Job)
def api_get_job(job_id: str) -> Job:
    job = manager.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    return job


@router.post("/{job_id}/cancel", response_model=Job)
def api_cancel_job(job_id: str) -> Job:
    job = manager.cancel(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    return job
