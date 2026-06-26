import logging
from langgraph.graph import StateGraph, START, END
from app.graph.state import PatternState
from app.graph.nodes.vision import vision_node
from app.graph.nodes.measurement import measurement_node
from app.graph.nodes.pattern import pattern_node
from app.graph.nodes.instructions import instructions_node
from app.graph.nodes.pdf_renderer import pdf_renderer_node

logger = logging.getLogger(__name__)


def should_continue(state: PatternState) -> str:
    """
    Conditional edge — abort the pipeline early if any
    node has recorded a fatal error.
    """
    if state.get("errors"):
        logger.warning(f"Pipeline aborting — errors: {state['errors']}")
        return "abort"
    return "continue"


def build_graph() -> StateGraph:
    graph = StateGraph(PatternState)

    # ── Register nodes ───────────────────────────────────────────────
    graph.add_node("vision", vision_node)
    graph.add_node("measurement", measurement_node)
    graph.add_node("pattern", pattern_node)
    graph.add_node("instructions", instructions_node)
    graph.add_node("pdf_renderer", pdf_renderer_node)

    # ── Entry point ──────────────────────────────────────────────────
    graph.add_edge(START, "vision")

    # ── Conditional edges after each agent ──────────────────────────
    # If an agent records an error, skip straight to END
    # Otherwise continue to the next node
    graph.add_conditional_edges(
        "vision",
        should_continue,
        {
            "continue": "measurement",
            "abort": END,
        },
    )

    graph.add_conditional_edges(
        "measurement",
        should_continue,
        {
            "continue": "pattern",
            "abort": END,
        },
    )

    graph.add_conditional_edges(
        "pattern",
        should_continue,
        {
            "continue": "instructions",
            "abort": END,
        },
    )

    graph.add_conditional_edges(
        "instructions",
        should_continue,
        {
            "continue": "pdf_renderer",
            "abort": END,
        },
    )

    # ── PDF renderer always goes to END ─────────────────────────────
    graph.add_edge("pdf_renderer", END)

    return graph


def compile_graph():
    """Compile the graph — call once at app startup."""
    graph = build_graph()
    compiled = graph.compile()
    logger.info("LangGraph pipeline compiled successfully")
    return compiled


# Module-level compiled graph — imported by routes
pipeline = compile_graph()