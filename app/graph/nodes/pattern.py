import json
import logging
from anthropic import Anthropic
from app.config import get_settings
from app.graph.state import PatternState, PatternPiece, PatternDimension

logger = logging.getLogger(__name__)
settings = get_settings()
client = Anthropic(api_key=settings.anthropic_api_key)


PATTERN_PROMPT = """You are an expert pattern maker. Using the garment description and calculated
pattern dimensions, produce the final pattern pieces with all technical markings a sewist needs.

Garment description:
{garment_description}

Calculated pattern dimensions:
{pattern_dimensions}

Skill level: {skill_level}

Rules:
- Add a seam_allowance_cm appropriate for the garment type (typically 1.0–1.5 cm)
- markings must be specific and actionable e.g. "notch 2cm from hem", "bust dart 8cm long"
- id must be a unique integer starting from 1
- Include ALL pieces needed — don't skip facings, interfacings, or linings if required
- Tailor the detail level of markings to the skill level

Respond ONLY with a valid JSON array. No markdown, no backticks, no explanation:

[
    {{
        "id": 1,
        "name": "Bodice Front",
        "dimensions": {{
            "piece_name": "Bodice Front",
            "width_cm": 42.0,
            "height_cm": 38.0,
            "quantity": 1,
            "notes": "cut on straight grain, place centre front on fold"
        }},
        "seam_allowance_cm": 1.5,
        "markings": [
            "notch at side seam 15cm from hem",
            "bust dart: 8cm long, 3cm wide at side seam"
        ]
    }}
]"""


def _format_dimensions(dimensions: list[PatternDimension]) -> str:
    """Serialise pattern dimensions list for prompt injection."""
    return json.dumps(
        [d.model_dump() for d in dimensions],
        indent=2
    )


def pattern_node(state: PatternState) -> dict:
    """
    Takes garment description + pattern dimensions and produces
    fully marked-up pattern pieces ready for cutting.
    Populates: pattern_pieces
    """
    logger.info("Pattern node: drafting pattern pieces")

    # Guards
    if not state.get("garment_description"):
        logger.error("Pattern node: no garment description in state")
        return {
            "errors": state["errors"] + ["Pattern agent: missing garment description"],
            "current_node": "pattern",
        }

    if not state.get("pattern_dimensions"):
        logger.error("Pattern node: no pattern dimensions in state")
        return {
            "errors": state["errors"] + ["Pattern agent: missing pattern dimensions"],
            "current_node": "pattern",
        }

    garment_desc = state["garment_description"]
    pattern_dimensions = state["pattern_dimensions"]
    skill_level = state["skill_level"]

    prompt = PATTERN_PROMPT.format(
        garment_description=garment_desc.model_dump_json(indent=2),
        pattern_dimensions=_format_dimensions(pattern_dimensions),
        skill_level=skill_level,
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
        parsed = json.loads(raw)

        pattern_pieces = [PatternPiece(**piece) for piece in parsed]

        logger.info(
            f"Pattern node: drafted {len(pattern_pieces)} pattern pieces"
        )

        return {
            "pattern_pieces": pattern_pieces,
            "current_node": "pattern",
        }

    except json.JSONDecodeError as e:
        logger.error(f"Pattern node: failed to parse Claude response — {e}")
        return {
            "errors": state["errors"] + ["Pattern agent returned invalid JSON"],
            "current_node": "pattern",
        }

    except Exception as e:
        logger.error(f"Pattern node: unexpected error — {e}")
        return {
            "errors": state["errors"] + [f"Pattern agent error: {str(e)}"],
            "current_node": "pattern",
        }