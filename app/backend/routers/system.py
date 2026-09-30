"""Router de sistema: estado de backends (Phase 19 + cambio_IA.md)."""
from fastapi import APIRouter

import system
import video_backends

router = APIRouter(prefix="/api/system", tags=["system"])


@router.get("/status")
def api_system_status() -> dict:
    return system.full_status()


@router.get("/video-backends")
def api_video_backends() -> dict:
    return {
        "default": video_backends.DEFAULT_BACKEND,
        "backends": video_backends.list_backends(),
    }
