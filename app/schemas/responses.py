from pydantic import BaseModel
from typing import Optional
from app.graph.state import PatternState


class PatternPieceResponse(BaseModel):
    id: int
    name: str
    width_cm: float
    height_cm: float
    quantity: int
    seam_allowance_cm: float
    notes: str
    markings: list[str]


class SewingStepResponse(BaseModel):
    step_number: int
    title: str
    instruction: str
    tip: Optional[str] = None


class GeneratePatternResponse(BaseModel):
    # Garment summary
    garment_type: str
    silhouette: str
    construction_details: list[str]
    fabric_recommendation: str
    estimated_difficulty: str

    # Pattern data
    pattern_pieces: list[PatternPieceResponse]
    sewing_steps: list[SewingStepResponse]
    materials_list: list[str]

    # Output
    pdf_path: str

    # Metadata
    errors: list[str]


class ErrorResponse(BaseModel):
    detail: str
    errors: list[str] = []


class HealthResponse(BaseModel):
    status: str
    version: str
    model: str

def state_to_response(state: PatternState) -> GeneratePatternResponse:
    """Map the final pipeline state to the API response model."""
    garment = state["garment_description"]

    pieces = [
        PatternPieceResponse(
            id=p.id,
            name=p.name,
            width_cm=p.dimensions.width_cm,
            height_cm=p.dimensions.height_cm,
            quantity=p.dimensions.quantity,
            seam_allowance_cm=p.seam_allowance_cm,
            notes=p.dimensions.notes,
            markings=p.markings,
        )
        for p in state["pattern_pieces"]
    ]

    steps = [
        SewingStepResponse(
            step_number=s.step_number,
            title=s.title,
            instruction=s.instruction,
            tip=s.tip,
        )
        for s in state["sewing_steps"]
    ]

    return GeneratePatternResponse(
        garment_type=garment.garment_type,
        silhouette=garment.silhouette,
        construction_details=garment.construction_details,
        fabric_recommendation=garment.fabric_recommendation,
        estimated_difficulty=garment.estimated_difficulty,
        pattern_pieces=pieces,
        sewing_steps=steps,
        materials_list=state["materials_list"],
        pdf_path=state["pdf_path"],
        errors=state["errors"],
    )