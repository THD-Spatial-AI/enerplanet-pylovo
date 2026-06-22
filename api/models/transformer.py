"""Transformer-related Pydantic models."""
from pydantic import BaseModel
from typing import Optional, List


class AddTransformerRequest(BaseModel):
    """Request to add a new transformer at a specific location."""
    coordinates: List[float]  # [longitude, latitude] in WGS84
    kva: float  # Transformer capacity in kVA
    grid_result_ids: List[int]  # Existing grid IDs in the area to potentially reassign buildings from
    reassign_radius_m: Optional[float] = 0.0  # Radius in meters to search for buildings (0 = no auto-assign)
    user_id: Optional[str] = None  # User ID - transformer is only visible to this user
    model_id: Optional[int] = None  # Model ID - transformer is scoped to this model (existing models)
    draft_id: Optional[str] = None  # Draft ID for new models (before saving)


class FinalizeTransformersRequest(BaseModel):
    """Request to finalize transformers after saving a model."""
    draft_id: str  # The draft ID used when creating transformers
    model_id: int  # The real model ID after saving
    user_id: Optional[str] = None  # User ID for validation
