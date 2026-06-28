import logging
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer,
    Table, TableStyle, HRFlowable
)
from app.config import get_settings
from app.graph.state import PatternState
from app.graph.utils import extract_json


logger = logging.getLogger(__name__)
settings = get_settings()

# ── Colour palette ────────────────────────────────────────────────────────────
INK        = colors.HexColor("#1a1410")
SEPIA      = colors.HexColor("#8b6f47")
SEPIA_LIGHT= colors.HexColor("#c4a882")
CREAM      = colors.HexColor("#faf7f2")
PARCHMENT  = colors.HexColor("#f5f0e8")
ACCENT     = colors.HexColor("#c4633a")


def _build_styles():
    base = getSampleStyleSheet()

    title = ParagraphStyle(
        "Title",
        parent=base["Normal"],
        fontName="Times-Roman",
        fontSize=28,
        textColor=INK,
        spaceAfter=4,
        leading=32,
    )

    section = ParagraphStyle(
        "Section",
        parent=base["Normal"],
        fontName="Times-Roman",
        fontSize=12,
        textColor=SEPIA,
        spaceBefore=20,
        spaceAfter=8,
        leading=16,
    )

    body = ParagraphStyle(
        "Body",
        parent=base["Normal"],
        fontName="Times-Roman",
        fontSize=10,
        textColor=INK,
        spaceAfter=4,
        leading=15,
    )

    label = ParagraphStyle(
        "Label",
        parent=base["Normal"],
        fontName="Times-Bold",
        fontSize=9,
        textColor=SEPIA,
        spaceAfter=2,
    )

    tip = ParagraphStyle(
        "Tip",
        parent=base["Normal"],
        fontName="Times-Italic",
        fontSize=9,
        textColor=SEPIA,
        leftIndent=12,
        spaceAfter=6,
        leading=13,
    )

    return {"title": title, "section": section, "body": body, "label": label, "tip": tip}


def _section_header(title: str, styles: dict) -> list:
    """Returns a styled section header with a rule."""
    return [
        Paragraph(title.upper(), styles["section"]),
        HRFlowable(width="100%", thickness=0.5, color=SEPIA_LIGHT, spaceAfter=8),
    ]


def _build_story(state: PatternState, styles: dict) -> list:
    story = []
    garment = state["garment_description"]

    # ── Title ─────────────────────────────────────────────────────────
    story.append(Paragraph(garment.garment_type.upper(), styles["title"]))
    story.append(HRFlowable(width="100%", thickness=1.5, color=INK, spaceAfter=8))

    # ── Meta row ──────────────────────────────────────────────────────
    meta_data = [
        ["SILHOUETTE", "DIFFICULTY", "SKILL LEVEL", "FABRIC"],
        [
            garment.silhouette,
            garment.estimated_difficulty,
            state["skill_level"].capitalize(),
            garment.fabric_recommendation,
        ],
    ]
    meta_table = Table(meta_data, colWidths=[4.5*cm, 3*cm, 3*cm, 7*cm])
    meta_table.setStyle(TableStyle([
        ("FONTNAME",    (0, 0), (-1, 0), "Times-Bold"),
        ("FONTSIZE",    (0, 0), (-1, 0), 7),
        ("TEXTCOLOR",   (0, 0), (-1, 0), SEPIA),
        ("FONTNAME",    (0, 1), (-1, 1), "Times-Roman"),
        ("FONTSIZE",    (0, 1), (-1, 1), 9),
        ("TEXTCOLOR",   (0, 1), (-1, 1), INK),
        ("TOPPADDING",  (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 4),
        ("LINEBELOW",   (0, 0), (-1, 0), 0.25, SEPIA_LIGHT),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 0.4*cm))

    # ── Construction details ──────────────────────────────────────────
    if garment.construction_details:
        details_text = "  ·  ".join(garment.construction_details)
        story.append(Paragraph(details_text, styles["tip"]))

    # ── Measurements ─────────────────────────────────────────────────
    story += _section_header("Body Measurements", styles)
    measurements = state["measurements"]
    meas_data = [["MEASUREMENT", "VALUE"]] + [
        [k.replace("_", " ").title(), f"{v} cm"]
        for k, v in measurements.items()
    ]
    meas_table = Table(meas_data, colWidths=[8*cm, 4*cm])
    meas_table.setStyle(TableStyle([
        ("FONTNAME",     (0, 0), (-1, 0), "Times-Bold"),
        ("FONTSIZE",     (0, 0), (-1, 0), 8),
        ("TEXTCOLOR",    (0, 0), (-1, 0), SEPIA),
        ("FONTNAME",     (0, 1), (-1, -1), "Times-Roman"),
        ("FONTSIZE",     (0, 1), (-1, -1), 9),
        ("TEXTCOLOR",    (0, 1), (-1, -1), INK),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [CREAM, PARCHMENT]),
        ("TOPPADDING",   (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 5),
        ("LEFTPADDING",  (0, 0), (-1, -1), 8),
        ("LINEBELOW",    (0, 0), (-1, 0), 0.25, SEPIA_LIGHT),
    ]))
    story.append(meas_table)

    # ── Pattern pieces ────────────────────────────────────────────────
    story += _section_header("Pattern Pieces", styles)
    pieces_data = [["#", "PIECE NAME", "DIMENSIONS", "QTY", "SA", "NOTES"]]
    for p in state["pattern_pieces"]:
        pieces_data.append([
            str(p.id),
            p.name,
            f"{p.dimensions.width_cm} × {p.dimensions.height_cm} cm",
            f"× {p.dimensions.quantity}",
            f"{p.seam_allowance_cm} cm",
            p.dimensions.notes,
        ])
    pieces_table = Table(
        pieces_data,
        colWidths=[1*cm, 4*cm, 3.5*cm, 1.5*cm, 1.5*cm, 6*cm]
    )
    pieces_table.setStyle(TableStyle([
        ("FONTNAME",      (0, 0), (-1, 0), "Times-Bold"),
        ("FONTSIZE",      (0, 0), (-1, 0), 8),
        ("TEXTCOLOR",     (0, 0), (-1, 0), SEPIA),
        ("FONTNAME",      (0, 1), (-1, -1), "Times-Roman"),
        ("FONTSIZE",      (0, 1), (-1, -1), 9),
        ("TEXTCOLOR",     (0, 1), (-1, -1), INK),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [CREAM, PARCHMENT]),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 6),
        ("LINEBELOW",     (0, 0), (-1, 0), 0.25, SEPIA_LIGHT),
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(pieces_table)

    # Markings per piece
    for p in state["pattern_pieces"]:
        if p.markings:
            story.append(Spacer(1, 0.2*cm))
            story.append(Paragraph(f"<b>Piece {p.id} — {p.name} markings:</b>", styles["label"]))
            for mark in p.markings:
                story.append(Paragraph(f"· {mark}", styles["body"]))

    # ── Materials ─────────────────────────────────────────────────────
    story += _section_header("Materials & Notions", styles)
    for item in state["materials_list"]:
        story.append(Paragraph(f"· {item}", styles["body"]))

    # ── Sewing instructions ───────────────────────────────────────────
    story += _section_header("Sewing Instructions", styles)
    for step in state["sewing_steps"]:
        story.append(Paragraph(
            f"<b>{step.step_number}.  {step.title}</b>",
            styles["body"]
        ))
        story.append(Paragraph(step.instruction, styles["body"]))
        if step.tip:
            story.append(Paragraph(f"✦  {step.tip}", styles["tip"]))
        story.append(Spacer(1, 0.2*cm))

    # ── Errors ────────────────────────────────────────────────────────
    if state.get("errors"):
        story += _section_header("Pipeline Warnings", styles)
        for err in state["errors"]:
            story.append(Paragraph(f"· {err}", styles["tip"]))

    return story


def pdf_renderer_node(state: PatternState) -> dict:
    """
    Renders all pipeline outputs into a printable PDF pattern.
    Populates: pdf_path
    """
    logger.info("PDF renderer: generating pattern PDF")

    if not state.get("pattern_pieces"):
        return {
            "errors": state["errors"] + ["PDF renderer: missing pattern pieces"],
            "current_node": "pdf_renderer",
        }

    if not state.get("sewing_steps"):
        return {
            "errors": state["errors"] + ["PDF renderer: missing sewing steps"],
            "current_node": "pdf_renderer",
        }

    try:
        outputs_dir = Path(settings.outputs_dir)
        outputs_dir.mkdir(parents=True, exist_ok=True)

        garment_type = state["garment_description"].garment_type
        safe_name = garment_type.lower().replace(" ", "_").replace("/", "_")
        pdf_path = outputs_dir / f"{safe_name}_pattern.pdf"

        doc = SimpleDocTemplate(
            str(pdf_path),
            pagesize=A4,
            leftMargin=2*cm,
            rightMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm,
        )

        styles = _build_styles()
        story = _build_story(state, styles)
        doc.build(story)

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