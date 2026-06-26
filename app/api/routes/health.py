from fastapi import APIRouter, Depends
from app.config import Settings, get_settings
from app.schemas.responses import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health_check(settings: Settings = Depends(get_settings)):
    return HealthResponse(
        status="ok",
        version=settings.app_version,
        model=settings.claude_model,
    )