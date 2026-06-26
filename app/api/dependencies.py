from fastapi import Depends
from app.config import Settings, get_settings


def get_pipeline_settings(settings: Settings = Depends(get_settings)) -> Settings:
    """
    Dependency for route handlers that need settings.
    Extend this later for auth, rate limiting etc.
    """
    return settings