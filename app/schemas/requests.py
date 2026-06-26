from pydantic import BaseModel, Field, field_validator


class Measurements(BaseModel):
    bust: float = Field(..., gt=0, le=200, description="Bust/chest in cm")
    waist: float = Field(..., gt=0, le=200, description="Waist in cm")
    hips: float = Field(..., gt=0, le=200, description="Hips in cm")
    height: float = Field(..., gt=0, le=250, description="Height in cm")
    shoulder_width: float = Field(..., gt=0, le=80, description="Shoulder width in cm")


class GeneratePatternRequest(BaseModel):
    measurements: Measurements
    skill_level: str = Field(
        default="intermediate",
        description="Sewer skill level"
    )

    @field_validator("skill_level")
    @classmethod
    def validate_skill_level(cls, v: str) -> str:
        allowed = {"beginner", "intermediate", "advanced"}
        if v.lower() not in allowed:
            raise ValueError(f"skill_level must be one of: {', '.join(allowed)}")
        return v.lower()