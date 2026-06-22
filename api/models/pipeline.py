"""Pipeline-related Pydantic models."""
from pydantic import BaseModel
from typing import Optional, List
from dataclasses import dataclass, field
from datetime import datetime


class PipelineRunRequest(BaseModel):
    plz_codes: List[str]
    workers: Optional[int] = 4
    no_cache: Optional[bool] = False


@dataclass
class PipelineJob:
    """Tracks state and progress of a pipeline run."""
    job_id: str
    plz_codes: List[str]
    status: str = "pending"
    current_step: str = ""
    progress: float = 0.0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    logs: List[str] = field(default_factory=list)
