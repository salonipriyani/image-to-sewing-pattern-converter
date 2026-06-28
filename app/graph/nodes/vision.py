import json
import logging
from anthropic import Anthropic
from app.config import get_settings
from app.graph.state import PatternState, GarmentDescription
from app.graph.utils import extract_json


logger = logging.getLogger(__name__)
settings = get_settings()
client = Anthropic(api_key=settings.anthropic_api_key)

VISION_PROMPT = """You are an expert fashion designer and pattern maker with decades of experience.
Analyze this garment image carefully and extract the following details.

Respond ONLY with a valid JSON object. No markdown, no backticks, no explanation. Exact structure:

{
    "garment_type": "specific garment name e.g. A-line dress, tailored blazer, wrap skirt",
    "silhouette": "description of the overall shape and fit",
    "construction_details": [
        "list of specific construction features e.g. princess seams, side zip, notched collar"
    ],
    "fabric_recommendation": "fabric type, weight and fibre suggestions",
    "estimated_difficulty": "Easy | Moderate | Advanced"
}

Be specific and technical. A pattern maker will use this output to draft pattern pieces."""


def vision_node(state: PatternState) -> dict:
    """
    Analyzes the garment image and extracts a structured description.
    Populates: garment_description
    """
    logger.info("Vision node: analysing garment image")

    try:
        response = client.messages.create(
            model=settings.claude_model,
            max_tokens=1000,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": state["image_media_type"],
                                "data": state["image_base64"],
                            },
                        },
                        {
                            "type": "text",
                            "text": VISION_PROMPT,
                        },
                    ],
                }
            ],
        )

        raw = response.content[0].text.strip()
        parsed = json.loads(extract_json(raw))
        garment_description = GarmentDescription(**parsed)

        logger.info(f"Vision node: identified '{garment_description.garment_type}'")

        return {
            "garment_description": garment_description,
            "current_node": "vision",
        }

    except json.JSONDecodeError as e:
        logger.error(f"Vision node: failed to parse Claude response — {e}")
        return {
            "errors": state["errors"] + ["Vision agent returned invalid JSON"],
            "current_node": "vision",
        }

    except Exception as e:
        logger.error(f"Vision node: unexpected error — {e}")
        return {
            "errors": state["errors"] + [f"Vision agent error: {str(e)}"],
            "current_node": "vision",
        }