from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any
from .core import Settings, get_settings, db
from supabase import Client
import requests

settings = get_settings()

# --- Pipeline Helpers ---
async def fetch_solar_data(start_time: datetime) -> List[Dict[str,Any]]:
    """
    Fetches solar observation data from external API for the given interval.
    Cleans and filters the data accordingly.
    Returns a list of clean observations. # NOTE: Future implementation with DATA_RESOLUTION_MINUTES averages.
    """
    try:
        response = requests.get(settings.GOAS_19_XRAY_LONG)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}")

    # Filter data for energy "0.1-0.8nm" only and after start_time
    filtered_data = [record for record in data if record.get('energy') == '0.1-0.8nm']
    filtered_data = [record for record in filtered_data if start_time <= datetime.fromisoformat(record['time_tag'].replace("Z", "+00:00"))]
    # Retain only time_tag and xray_flux
    cleaned_data = [{'timestamp': record['time_tag'], 'xray_flux': record['flux']} for record in filtered_data]
    return cleaned_data

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
    # MOCK PREDICTION LOGIC
    flux_prediction = sum([record['xray_flux'] for record in data]) / len(data) if data else 0.0
    # Simple threshold-based risk level determination
    if flux_prediction > 1e-4:
        risk_level = "High"
    elif flux_prediction > 1e-6:
        risk_level = "Medium"
    else:
        risk_level = "Low"

    # Mock probability calculation
    m_class_probability = flux_prediction / data[-1]['xray_flux'] if data and data[-1]['xray_flux'] > 0 else 0.0

    result = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "m_class_probability": m_class_probability,
        "risk_level": risk_level,
        "model_version": "N/A"
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

    # 2. Fetch new solar data from GOAS API
    new_data = await fetch_solar_data(start_time)
    if not new_data:
        print("No new solar observation data fetched.")
        return
    print(f"Fetched {len(new_data)} new solar observation records from GOAS API.")

    # 3. Write new data to Supabase, timestamp as primary key
    for record in new_data:
        db.table(settings.DATA_TABLE_NAME).upsert(record).execute()
    print(f"Wrote {len(new_data)} new solar observation records to Supabase.")

    # 4. Query db for model input data for prediction
    lookback_start_time = datetime.now(timezone.utc) - timedelta(hours=settings.ML_LOOKBACK_HOURS)
    model_input_response = db.table(settings.DATA_TABLE_NAME).select("*").gte("timestamp", lookback_start_time.isoformat()).execute()
    model_input_data = model_input_response.data if model_input_response.data else []

    if not model_input_data:
        print("No model input data available for prediction after lookback filtering. Aborting pipeline.")
        return
    print(f"Fetched {len(model_input_data)} solar observation records for prediction.")

    # 5. Load production ML model
    model = await load_model_from_registry()

    # 6. Run prediction
    prediction_result = await predict(model, model_input_data)
    print(f"Generated prediction: {prediction_result}")

    # 7. Write prediction result to Supabase
    # timestamp as primary key
    db.table(settings.PREDICTION_TABLE_NAME).upsert(prediction_result).execute()
    print(f"Wrote prediction result to Supabase.")

    print("Prediction pipeline completed successfully.")
