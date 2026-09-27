"""Modelos de datos del proyecto (docs/14_DATA_MODELS.md)."""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, Field


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    return uuid4().hex[:12]


class ProjectSettings(BaseModel):
    aspect_ratio: str = "9:16"
    scene_count: int = 6
    style: str = "anime cinematografico"
    target_duration_seconds: int = 60


class Project(BaseModel):
    id: str = Field(default_factory=_new_id)
    title: str
    created_at: str = Field(default_factory=_now_iso)
    updated_at: str = Field(default_factory=_now_iso)
    settings: ProjectSettings = Field(default_factory=ProjectSettings)


class ProjectCreate(BaseModel):
    title: str
    settings: Optional[ProjectSettings] = None


class SceneStatus(BaseModel):
    image: str = "pending"
    video: str = "pending"
    audio: str = "pending"
    subtitle: str = "pending"


class Scene(BaseModel):
    scene_id: str = "scene-01"
    order: int = 1
    title: str = ""
    purpose: str = ""
    duration_seconds: int = 8
    image_prompt: str = ""
    motion_prompt: str = ""
    narration: str = ""
    subtitle_text: str = ""
    image_path: Optional[str] = None
    video_path: Optional[str] = None
    audio_path: Optional[str] = None
    subtitle_json_path: Optional[str] = None
    subtitle_ass_path: Optional[str] = None
    status: SceneStatus = Field(default_factory=SceneStatus)


class StoryPlan(BaseModel):
    hook: str = ""
    summary: str = ""
    cliffhanger: str = ""
    scenes: list[Scene] = Field(default_factory=list)


class JobType(str, Enum):
    story = "story"
    image = "image"
    video = "video"
    audio = "audio"
    subtitle = "subtitle"
    render = "render"
    ping = "ping"  # solo test/dev del job system


class JobStatus(str, Enum):
    queued = "queued"
    running = "running"
    done = "done"
    error = "error"
    cancelled = "cancelled"


class Job(BaseModel):
    job_id: str = Field(default_factory=_new_id)
    type: JobType = JobType.story
    status: JobStatus = JobStatus.queued
    progress: int = 0
    message: str = ""


class IdeaStatus(str, Enum):
    pending = "pending"
    active = "active"
    favorite = "favorite"
    archived = "archived"
    discarded = "discarded"
    selected_for_story = "selected_for_story"


class IdeaNode(BaseModel):
    id: str = Field(default_factory=_new_id)
    project_id: str
    parent_id: Optional[str] = None
    depth: int = 0
    title: str
    summary: str = ""
    hook: str = ""
    conflict: str = ""
    cliffhanger: str = ""
    status: IdeaStatus = IdeaStatus.pending
    created_at: str = Field(default_factory=_now_iso)
