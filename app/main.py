from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .core import settings
from .api import api_router

# --- App initialization ---
app = FastAPI(
    title="Solar Flare Predictor Backend API",
    description="Backend service for fetching historical solar data and triggering ML predictions.",
    version="1.0.0"
)

# --- Cors Middleware (frontend access) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS, 
    allow_credentials=True,
    allow_methods=["*"],  # Allow all standard HTTP methods
    allow_headers=["*"],  # Allow all headers
)

# --- Router inclusion ---
# Include the APIRouter instance from api.py, exposing all endpoints
app.include_router(api_router)

# --- Health check ---
@app.get("/", include_in_schema=False)
async def root():
    """Simple health check endpoint for the root path."""
    return {"status": "ok", "message": "Solar Flare Predictor API is running."}


