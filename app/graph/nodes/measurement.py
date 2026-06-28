import json
import logging
from anthropic import Anthropic
from app.config import get_settings
from app.graph.state import PatternState, PatternDimension
from app.graph.utils import extract_json

logger = logging.getLogger(__name__)
settings = get_settings()
client = Anthropic(api_key=settings.anthropic_api_key)


MEASUREMENT_PROMPT = """You are an expert pattern maker. Using the garment description and body
measurements provided, calculate the pattern piece dimensions needed to construct this garment.

Garment description:
{garment_description}

Body measurements (cm):
{measurements}

Rules:
- Add ease allowances appropriate for the garment type and fit
- Do NOT include seam allowance in dimensions (that is added later)
- quantity is how many times the piece is cut from fabric
- notes must include grain line direction, any fold instructions, or mirroring

Respond ONLY with a valid JSON array. No markdown, no backticks, no explanation:

[
    {{
        "piece_name": "e.g. Bodice Front",
        "width_cm": 42.0,
        "height_cm": 38.0,
        "quantity": 1,
        "notes": "cut on straight grain, place centre front on fold"
    }}
]

Be precise and technically accurate. Cover every piece needed to construct the garment."""


def _format_measurements(measurements: dict) -> str:
    """Format measurements dict into readable string for the prompt."""
    labels = {
        "bust": "Bust / Chest",
        "waist": "Waist",
        "hips": "Hips",
        "height": "Height",
        "shoulder_width": "Shoulder Width",
    }
    lines = []
    for key, label in labels.items():
        value = measurements.get(key)
        if value:
            lines.append(f"  {label}: {value} cm")
    return "\n".join(lines) if lines else "No measurements provided"


def measurement_node(state: PatternState) -> dict:
    """
    Takes garment description + body measurements and calculates
    pattern piece dimensions with ease allowances.
    Populates: pattern_dimensions
    """
    logger.info("Measurement node: calculating pattern dimensions")

    # Guard — vision node must have succeeded
    if not state.get("garment_description"):
        logger.error("Measurement node: no garment description in state")
        return {
            "errors": state["errors"] + ["Measurement agent: missing garment description"],
            "current_node": "measurement",
        }

    garment_desc = state["garment_description"]
    measurements = state["measurements"]

    prompt = MEASUREMENT_PROMPT.format(
        garment_description=garment_desc.model_dump_json(indent=2),
        measurements=_format_measurements(measurements),
    )

    try:
        response = client.messages.create(
            model=settings.claude_model,
            max_tokens=2000,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
        )

        raw = response.content[0].text.strip()
        parsed = json.loads(extract_json(raw))

        pattern_dimensions = [PatternDimension(**piece) for piece in parsed]

        logger.info(
            f"Measurement node: calculated {len(pattern_dimensions)} pattern pieces"
        )

        return {
            "pattern_dimensions": pattern_dimensions,
            "current_node": "measurement",
        }

    except json.JSONDecodeError as e:
        logger.error(f"Measurement node: failed to parse Claude response — {e}")
        return {
            "errors": state["errors"] + ["Measurement agent returned invalid JSON"],
            "current_node": "measurement",
        }

    except Exception as e:
        logger.error(f"Measurement node: unexpected error — {e}")
        return {
            "errors": state["errors"] + [f"Measurement agent error: {str(e)}"],
            "current_node": "measurement",
        }