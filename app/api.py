from fastapi import APIRouter, Depends, HTTPException, status, Request
from typing import Annotated
from datetime import datetime, timezone, timedelta

# No dependency injection for database, use Supabase API layer directly
from .core import db, Settings, get_settings
from . import models

# --- APIRouter Definition ---
api_router = APIRouter(prefix="/api")

# --- Authentication Dependency (Cloud Scheduler Security) ---
def verify_scheduler_auth(request: Request):
    """
    Authenticates requests to use pipeline trigger endpoint.
    Must validate the OIDC token sent by the Cloud Scheduler Service Account.
    """
    # Mock
    return True 

# Annotated for cleaner dependency injection
Authenticated = Annotated[bool, Depends(verify_scheduler_auth)]

# --- GET Endpoints ---
# --- Predictions ---
@api_router.get("/predictions/latest", tags=["predictions"], response_model=models.PredictionRecord)
async def get_latest_prediction(settings: Settings = Depends(get_settings)):
    """
    Fetches the latest solar flare prediction.
    """
    latest_prediction = db.table(settings.PREDICTION_TABLE_NAME).select("*").order("timestamp",desc=True).limit(1).execute()
    if not latest_prediction.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No predictions found.")
    return models.PredictionRecord(**latest_prediction.data[0])

@api_router.get("/predictions", tags=["predictions"], response_model=models.HistoricalPredictionsResponse)
async def get_historical_predictions(settings: Settings = Depends(get_settings), timeframe_hours: int = None):
    """
    Fetches latest timeframe_hours of solar flare predictions.
    """
    # Validate timeframe_hours
    if timeframe_hours is None or (timeframe_hours > settings.MAX_REQUEST_HOURS) or (timeframe_hours < 1):
        timeframe_hours = settings.DEFAULT_REQUEST_HOURS
    start_time = datetime.now(timezone.utc) - timedelta(hours=timeframe_hours)
    predictions = db.table(settings.PREDICTION_TABLE_NAME).select("*").gte("timestamp", start_time.isoformat()).execute()
    return models.HistoricalPredictionsResponse(
        record_count=len(predictions.data),
        data=[models.PredictionRecord(**item) for item in predictions.data]
    )

# --- Observations ---
@api_router.get("/data/latest", tags=["observations"], response_model=models.ObservationRecord)
async def get_latest_observation(settings: Settings = Depends(get_settings)):
    """
    Fetches the latest solar observation datapoint.
    """
    latest_observation = db.table(settings.DATA_TABLE_NAME).select("*").order("timestamp",desc=True).limit(1).execute()
    if not latest_observation.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No observations found.")
    return models.ObservationRecord(**latest_observation.data[0])

@api_router.get("/data", tags=["observations"], response_model=models.HistoricalObservationsResponse)
async def get_historical_observations(settings: Settings = Depends(get_settings), timeframe_hours: int = None):
    """
    Fetches latest timeframe_hours of solar observation data.
    """
    # Validate timeframe_hours
    if timeframe_hours is None or (timeframe_hours > settings.MAX_REQUEST_HOURS) or (timeframe_hours < 1):
        timeframe_hours = settings.DEFAULT_REQUEST_HOURS
    start_time = datetime.now(timezone.utc) - timedelta(hours=timeframe_hours)
    observations = db.table(settings.DATA_TABLE_NAME).select("*").gte("timestamp", start_time.isoformat()).execute()
    return models.HistoricalObservationsResponse(
        record_count=len(observations.data),
        data=[models.ObservationRecord(**item) for item in observations.data]
    )

# --- POST run pipeline endpoint (Cloud Scheduler Trigger) ---
@api_router.post("/run-flare-prediction-pipeline",
                 tags=["pipeline"],
                 status_code=status.HTTP_202_ACCEPTED, # What the endpoint returns on success
                 response_model=models.PipelineStatusResponse)
async def trigger_prediction_pipeline(_: Authenticated, settings: Settings = Depends(get_settings)):
    """
    Run the prediction pipeline.
    Requires a valid OIDC token in the Authorization header.
    Pipeline retrieves recent data, writes it, loads model, runs prediction, and writes result to DB.
    """
    # Import pipeline function locally to avoid circular dependencies and ensure
    # the function is called within the scope of the request.
    from .pipeline import run_prediction_pipeline
    
    # NOTE: parts of the pipeline are async - ensure proper awaits within the pipeline function.
    await run_prediction_pipeline(db, settings)

    return models.PipelineStatusResponse(
        status="accepted",
        message="Prediction pipeline successfully completed.",
        pipeline_completed_at=datetime.now(timezone.utc).isoformat()
    )
