from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any
from .core import Settings, get_settings, db
from supabase import Client

settings = get_settings()

# --- Pipeline Helpers ---
async def fetch_solar_data(start_time: datetime, end_time: datetime) -> List[Dict[str,Any]]:
    """
    Fetches solar observation data from external API for the given interval.
    Augments missing values with averages and cleans the data.
    Returns a list of clean observations.
    """
    # KEEP MOCK return statement since no real API integration is implemented yet
    data = [
        {
            "timestamp": start_time.isoformat(),
            "magnetic_flux": 1234.5,
        }
    ]

    return data

async def load_model_from_registry():
    """
    Loads the production ML model from the model registry.
    """
    return {}

async def predict(model: Dict[str, Any], data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Runs the ML prediction on the provided data using the specified model.
    Returns the prediction result.
    """
    # KEEP MOCK return statement since no model is implemented yet
    result = {
        "flare_risk": "Low",
        "m_class_probability": 0.15,
        "risk_level": "Low",
        "model_version": "THIS IS A TEST STATEMENT"
    }

    return result

# --- PIPELINE EXECUTION ---
async def run_prediction_pipeline(db: Client, settings: Settings):
    """
    The main prediction pipeline executed by the Cloud Scheduler trigger.

    Args:
        db: The initialized async Supabase client.
        settings: The application settings for lookback times, table names.
    """

    print("Starting prediction pipeline...")

    # 1. Determine time range for new data fetch
    # NOTE: Timestamp format is isofomat UTC, In Supabase timestampz datatype.
    latest_record = db.table(settings.DATA_TABLE_NAME).select("timestamp").order("timestamp", desc=True).limit(1).execute()
    date_str = latest_record.data[0]["timestamp"]
    date_obj = datetime.fromisoformat(date_str).replace(tzinfo=timezone.utc)

    if date_obj < (datetime.now(timezone.utc) - timedelta(hours=settings.DATA_RETRIEVAL_HOURS)):
        start_time = datetime.now(timezone.utc) - timedelta(hours=settings.DATA_RETRIEVAL_HOURS)
    else:
        start_time = date_obj
    start_time -= timedelta(hours=settings.BUFFER_HOURS)  # Apply buffer
    end_time = datetime.now(timezone.utc)

    # 2. Fetch new solar data from GOAS API
    new_data = await fetch_solar_data(start_time, end_time)
    if not new_data:
        print("No new solar observation data fetched.")
        return
    print(f"Fetched {len(new_data)} new solar observation records from GOAS API.")

    # 3. Write new data to Supabase, makes sure no duplicates
    for record in new_data:
        db.table(settings.DATA_TABLE_NAME).upsert(record).execute()
    print(f"Wrote {len(new_data)} new solar observation records to Supabase.")

    # 4. Query db for recent data for prediction
    lookback_start_time = datetime.now(timezone.utc) - timedelta(hours=settings.ML_LOOKBACK_HOURS)
    recent_data_response = db.table(settings.DATA_TABLE_NAME).select("*").gte("timestamp", lookback_start_time.isoformat()).execute()
    recent_data = recent_data_response.data if recent_data_response.data else []

    if not recent_data:
        print("No recent data available for prediction after lookback filtering. Aborting pipeline.")
        return
    print(f"Fetched {len(recent_data)} solar observation records for prediction.")

    # 5. Load production ML model
    model = await load_model_from_registry()

    # 6. Run prediction
    prediction_result = await predict(model, recent_data)
    print(f"Generated prediction: {prediction_result}")

    # 7. Write prediction result to Supabase
    current_time = datetime.now(timezone.utc).isoformat()
    prediction_entry = {
        "timestamp": current_time,
        "m_class_probability": prediction_result.get("m_class_probability", 0.0),
        "risk_level": prediction_result.get("risk_level", "Unknown"),
        "model_version": prediction_result.get("model_version", "1.0.0")
    }

    # Allow duplicates
    db.table(settings.PREDICTION_TABLE_NAME).insert(prediction_entry).execute()
    print(f"Wrote prediction result to Supabase at {current_time}.")

    print("Prediction pipeline completed successfully.")
