import json
import logging
from anthropic import Anthropic
from app.config import get_settings
from app.graph.state import PatternState, SewingStep
from app.graph.utils import extract_json


logger = logging.getLogger(__name__)
settings = get_settings()
client = Anthropic(api_key=settings.anthropic_api_key)


INSTRUCTIONS_PROMPT = """You are an expert sewing instructor. Using the garment description and
pattern pieces, write complete step-by-step sewing instructions and a materials list.

Garment description:
{garment_description}

Pattern pieces:
{pattern_pieces}

Skill level: {skill_level}

Rules for sewing_steps:
- Order steps in correct construction sequence (prep → structure → assembly → finishing)
- step_number must be sequential starting from 1
- title should be short and action-oriented e.g. "Sew bust darts", "Attach collar"
- instruction should be a full, clear sentence with specific details
- tip is optional — include only when a technique is likely to trip up this skill level
- Beginner: include more tips, explain techniques, avoid jargon
- Intermediate: assume basic techniques are known, tips for trickier steps only
- Advanced: terse and technical, minimal tips

Rules for materials_list:
- Include fabric with yardage estimate based on pattern pieces
- Include all notions (zip, buttons, interfacing, thread etc.)
- Include tools needed
- Format each item as a single string e.g. "1.8m main fabric (cotton lawn, 115cm wide)"
- Limit to a maximum of 15 steps — be concise but complete


Respond ONLY with a valid JSON object. No markdown, no backticks, no explanation:

{{
    "sewing_steps": [
        {{
            "step_number": 1,
            "title": "Prepare pattern pieces",
            "instruction": "Press all pattern pieces and transfer all markings using tailor's chalk.",
            "tip": "Mark the wrong side of each fabric piece with a small chalk X to avoid confusion during assembly."
        }}
    ],
    "materials_list": [
        "1.8m main fabric (cotton lawn, 115cm wide)",
        "0.5m interfacing",
        "1 x 22cm invisible zip",
        "Matching thread",
        "Sharp fabric scissors",
        "Tailor's chalk"
    ]
}}"""


def _format_pattern_pieces(pieces: list) -> str:
    """Serialise pattern pieces list for prompt injection."""
    return json.dumps(
        [p.model_dump() for p in pieces],
        indent=2
    )


def instructions_node(state: PatternState) -> dict:
    """
    Takes garment description + pattern pieces and produces
    ordered sewing instructions and a materials list.
    Populates: sewing_steps, materials_list
    """
    logger.info("Instructions node: generating sewing instructions")

    # Guards
    if not state.get("garment_description"):
        logger.error("Instructions node: no garment description in state")
        return {
            "errors": state["errors"] + ["Instructions agent: missing garment description"],
            "current_node": "instructions",
        }

    if not state.get("pattern_pieces"):
        logger.error("Instructions node: no pattern pieces in state")
        return {
            "errors": state["errors"] + ["Instructions agent: missing pattern pieces"],
            "current_node": "instructions",
        }

    garment_desc = state["garment_description"]
    pattern_pieces = state["pattern_pieces"]
    skill_level = state["skill_level"]

    prompt = INSTRUCTIONS_PROMPT.format(
        garment_description=garment_desc.model_dump_json(indent=2),
        pattern_pieces=_format_pattern_pieces(pattern_pieces),
        skill_level=skill_level,
    )

    try:
        response = client.messages.create(
            model=settings.claude_model,
            max_tokens=4000,
            system="You are a sewing instructor that outputs ONLY valid JSON. Never truncate your response. Always close all brackets and braces. Never add commentary before or after the JSON.",
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
        )

        raw = response.content[0].text.strip()
        parsed = json.loads(extract_json(raw))

        sewing_steps = [SewingStep(**step) for step in parsed["sewing_steps"]]
        materials_list = parsed["materials_list"]

        logger.info(
            f"Instructions node: generated {len(sewing_steps)} steps, "
            f"{len(materials_list)} materials"
        )

        return {
            "sewing_steps": sewing_steps,
            "materials_list": materials_list,
            "current_node": "instructions",
        }

    except json.JSONDecodeError as e:
        logger.error(f"Instructions node: failed to parse Claude response — {e}")
        return {
            "errors": state["errors"] + ["Instructions agent returned invalid JSON"],
            "current_node": "instructions",
        }

    except KeyError as e:
        logger.error(f"Instructions node: missing expected key in response — {e}")
        return {
            "errors": state["errors"] + [f"Instructions agent response missing key: {e}"],
            "current_node": "instructions",
        }

    except Exception as e:
        logger.error(f"Instructions node: unexpected error — {e}")
        return {
            "errors": state["errors"] + [f"Instructions agent error: {str(e)}"],
            "current_node": "instructions",
        }