"""Router de sistema: estado de backends (Phase 19)."""
from fastapi import APIRouter

import system

router = APIRouter(prefix="/api/system", tags=["system"])


@router.get("/status")
def api_system_status() -> dict:
    return system.full_status()
