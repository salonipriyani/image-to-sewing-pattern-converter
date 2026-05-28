from typing import TypedDict, Optional
from pydantic import BaseModel


# ── Sub-models for structured agent outputs ──────────────────────────────────

class GarmentDescription(BaseModel):
    garment_type: str                # e.g. "A-line dress", "tailored blazer"
    silhouette: str                  # e.g. "fitted bodice, flared skirt"
    construction_details: list[str]  # e.g. ["side zip", "princess seams"]
    fabric_recommendation: str       # e.g. "medium-weight woven, cotton or linen"
    estimated_difficulty: str        # "Easy" / "Moderate" / "Advanced"


class PatternDimension(BaseModel):
    piece_name: str                  # e.g. "Bodice Front"
    width_cm: float
    height_cm: float
    quantity: int                    # how many times to cut
    notes: str                       # grain line, fold, mirror etc.


class PatternPiece(BaseModel):
    id: int
    name: str
    dimensions: PatternDimension
    seam_allowance_cm: float
    markings: list[str]              # e.g. ["notch at waist", "dart at bust"]


class SewingStep(BaseModel):
    step_number: int
    title: str
    instruction: str
    tip: Optional[str] = None        # skill-level-specific tip


# ── Main shared state ─────────────────────────────────────────────────────────

class PatternState(TypedDict):

    # ── Inputs (set once at pipeline start) ─────────────────────────
    image_base64: str
    image_media_type: str            # "image/jpeg", "image/png", "image/webp"
    measurements: dict               # bust, waist, hips, height, shoulder_width
    skill_level: str                 # "beginner" / "intermediate" / "advanced"

    # ── Vision node output ───────────────────────────────────────────
    garment_description: Optional[GarmentDescription]

    # ── Measurement node output ──────────────────────────────────────
    pattern_dimensions: Optional[list[PatternDimension]]

    # ── Pattern drafter node output ──────────────────────────────────
    pattern_pieces: Optional[list[PatternPiece]]

    # ── Instructions node output ─────────────────────────────────────
    sewing_steps: Optional[list[SewingStep]]
    materials_list: Optional[list[str]]

    # ── PDF renderer output ──────────────────────────────────────────
    pdf_path: Optional[str]

    # ── Pipeline metadata ────────────────────────────────────────────
    errors: list[str]
    current_node: Optional[str]


# ── State initialiser ─────────────────────────────────────────────────────────

def initial_state(
    image_base64: str,
    image_media_type: str,
    measurements: dict,
    skill_level: str,
) -> PatternState:
    return PatternState(
        image_base64=image_base64,
        image_media_type=image_media_type,
        measurements=measurements,
        skill_level=skill_level,
        garment_description=None,
        pattern_dimensions=None,
        pattern_pieces=None,
        sewing_steps=None,
        materials_list=None,
        pdf_path=None,
        errors=[],
        current_node=None,
    )