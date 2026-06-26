import logging
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML
from app.config import get_settings
from app.graph.state import PatternState

logger = logging.getLogger(__name__)
settings = get_settings()


def _get_jinja_env() -> Environment:
    """Set up Jinja2 environment pointing at templates directory."""
    return Environment(
        loader=FileSystemLoader("templates"),
        autoescape=True,
    )


def _build_template_context(state: PatternState) -> dict:
    """Assemble all state data into a clean dict for the template."""
    garment = state["garment_description"]
    return {
        "garment_type": garment.garment_type,
        "silhouette": garment.silhouette,
        "construction_details": garment.construction_details,
        "fabric_recommendation": garment.fabric_recommendation,
        "estimated_difficulty": garment.estimated_difficulty,
        "skill_level": state["skill_level"].capitalize(),
        "measurements": state["measurements"],
        "pattern_pieces": [p.model_dump() for p in state["pattern_pieces"]],
        "sewing_steps": [s.model_dump() for s in state["sewing_steps"]],
        "materials_list": state["materials_list"],
        "errors": state["errors"],
    }


def pdf_renderer_node(state: PatternState) -> dict:
    """
    Renders all pipeline outputs into a printable PDF pattern.
    Populates: pdf_path
    """
    logger.info("PDF renderer: generating pattern PDF")

    # Guards
    if not state.get("pattern_pieces"):
        logger.error("PDF renderer: no pattern pieces in state")
        return {
            "errors": state["errors"] + ["PDF renderer: missing pattern pieces"],
            "current_node": "pdf_renderer",
        }

    if not state.get("sewing_steps"):
        logger.error("PDF renderer: no sewing steps in state")
        return {
            "errors": state["errors"] + ["PDF renderer: missing sewing steps"],
            "current_node": "pdf_renderer",
        }

    try:
        # Ensure outputs directory exists
        outputs_dir = Path(settings.outputs_dir)
        outputs_dir.mkdir(parents=True, exist_ok=True)

        # Build output path using garment type as filename
        garment_type = state["garment_description"].garment_type
        safe_name = garment_type.lower().replace(" ", "_").replace("/", "_")
        pdf_path = outputs_dir / f"{safe_name}_pattern.pdf"

        # Render HTML template
        env = _get_jinja_env()
        template = env.get_template(settings.pdf_template)
        context = _build_template_context(state)
        html_content = template.render(**context)

        # Convert to PDF
        HTML(string=html_content).write_pdf(str(pdf_path))

        logger.info(f"PDF renderer: saved to {pdf_path}")

        return {
            "pdf_path": str(pdf_path),
            "current_node": "pdf_renderer",
        }

    except Exception as e:
        logger.error(f"PDF renderer: unexpected error — {e}")
        return {
            "errors": state["errors"] + [f"PDF renderer error: {str(e)}"],
            "current_node": "pdf_renderer",
        }