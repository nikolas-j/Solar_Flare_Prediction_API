from typing import List
from pydantic import BaseModel, Field

# --- Response Models ---
class PredictionRecord(BaseModel):
    """
    Schema for a solar flare prediction result.
    """
    timestamp: str = Field(..., description="UTC time for what period the prediction was generated for.")
    m_class_probability: float = Field(..., ge=0.0, le=1.0, description="Probability of an M-class solar flare occurring in the next 24 hours.")
    risk_level: str = Field(..., description="Risk classification ('Low', 'Medium', 'High').")
    model_version: str = Field("1.0.0", description="Version of the ML model used for this prediction.")

class ObservationRecord(BaseModel):
    """
    Schema for a single historical solar observation record.
    """
    timestamp: str = Field(..., description="UTC time of the observation.")
    magnetic_flux: float = Field(..., description="Total magnetic flux of the active region.")

class HistoricalPredictionsResponse(BaseModel):
    """
    Schema for the response containing past historical predictions.
    """
    record_count: int = Field(..., ge=0, description="Total number of historical records returned.")
    data: List[PredictionRecord] = Field(..., description="List of historical solar flare prediction records.")

class HistoricalObservationsResponse(BaseModel):
    """
    Schema for the response containing past historical solar observations.
    """
    record_count: int = Field(..., ge=0, description="Total number of historical observation records returned.")
    data: List[ObservationRecord] = Field(..., description="List of historical solar observation records.")

# --- Pipeline POST response ---
class PipelineStatusResponse(BaseModel):
    """
    Schema for the response sent back to the Cloud Scheduler upon triggering the pipeline.
    """
    status: str = Field("accepted", description="The status of the pipeline trigger.")
    message: str = Field(..., description="A confirmation message regarding the initiation of the prediction pipeline.")
    pipeline_completed_at: str = Field(..., description="UTC time when the pipeline was completed.")
