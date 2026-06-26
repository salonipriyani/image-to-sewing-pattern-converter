import base64
import logging
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pathlib import Path
from app.config import Settings, get_settings
from app.graph.graph import pipeline
from app.graph.state import initial_state
from app.schemas.requests import GeneratePatternRequest, Measurements
from app.schemas.responses import GeneratePatternResponse, ErrorResponse, state_to_response

logger = logging.getLogger(__name__)
router = APIRouter()


def _validate_image(file: UploadFile, settings: Settings) -> None:
    """Validate image content type and size."""
    if file.content_type not in settings.allowed_image_types:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported image type: {file.content_type}. "
                   f"Allowed: {', '.join(settings.allowed_image_types)}"
        )


async def _read_image(file: UploadFile, settings: Settings) -> tuple[str, str]:
    """Read and base64-encode the uploaded image."""
    contents = await file.read()

    max_bytes = settings.max_image_size_mb * 1024 * 1024
    if len(contents) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"Image too large. Maximum size: {settings.max_image_size_mb}MB"
        )

    image_base64 = base64.b64encode(contents).decode("utf-8")
    return image_base64, file.content_type


@router.post(
    "/generate",
    response_model=GeneratePatternResponse,
    responses={
        413: {"model": ErrorResponse, "description": "Image too large"},
        415: {"model": ErrorResponse, "description": "Unsupported image type"},
        422: {"model": ErrorResponse, "description": "Validation error"},
        500: {"model": ErrorResponse, "description": "Pipeline error"},
    },
    summary="Generate a sewing pattern from a garment image",
    description="""
    Upload a garment image or fashion sketch along with body measurements
    to generate a complete sewing pattern with instructions and a printable PDF.
    """,
)
async def generate_pattern(
    image: UploadFile = File(..., description="Garment image or fashion sketch"),
    bust: float = Form(..., description="Bust/chest measurement in cm"),
    waist: float = Form(..., description="Waist measurement in cm"),
    hips: float = Form(..., description="Hips measurement in cm"),
    height: float = Form(..., description="Height in cm"),
    shoulder_width: float = Form(..., description="Shoulder width in cm"),
    skill_level: str = Form(default="intermediate", description="beginner | intermediate | advanced"),
    settings: Settings = Depends(get_settings),
):
    # Validate image
    _validate_image(image, settings)
    image_base64, media_type = await _read_image(image, settings)

    # Validate measurements and skill level via schema
    try:
        request = GeneratePatternRequest(
            measurements=Measurements(
                bust=bust,
                waist=waist,
                hips=hips,
                height=height,
                shoulder_width=shoulder_width,
            ),
            skill_level=skill_level,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    # Build initial state
    state = initial_state(
        image_base64=image_base64,
        image_media_type=media_type,
        measurements=request.measurements.model_dump(),
        skill_level=request.skill_level,
    )

    # Run pipeline
    logger.info(f"Running pipeline — skill level: {request.skill_level}")
    try:
        result = pipeline.invoke(state)
    except Exception as e:
        logger.error(f"Pipeline invocation failed — {e}")
        raise HTTPException(status_code=500, detail=f"Pipeline error: {str(e)}")

    # Check for fatal errors (pipeline aborted early)
    if not result.get("pdf_path"):
        logger.error(f"Pipeline did not produce a PDF — errors: {result.get('errors')}")
        raise HTTPException(
            status_code=500,
            detail=f"Pattern generation failed: {result.get('errors', ['Unknown error'])}"
        )

    return state_to_response(result)


@router.get(
    "/download/{filename}",
    summary="Download a generated PDF pattern",
    response_class=FileResponse,
    responses={
        404: {"model": ErrorResponse, "description": "PDF not found"},
    },
)
def download_pdf(
    filename: str,
    settings: Settings = Depends(get_settings),
):
    # Sanitise filename — prevent path traversal
    safe_filename = Path(filename).name
    pdf_path = Path(settings.outputs_dir) / safe_filename

    if not pdf_path.exists() or pdf_path.suffix != ".pdf":
        raise HTTPException(status_code=404, detail=f"PDF not found: {filename}")

    return FileResponse(
        path=str(pdf_path),
        media_type="application/pdf",
        filename=safe_filename,
    )