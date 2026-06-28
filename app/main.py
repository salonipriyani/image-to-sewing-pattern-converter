import logging
import logging.config
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from fastapi.responses import HTMLResponse
from app.config import get_settings
from app.api.routes import health, pattern
from app.graph.graph import pipeline  # import triggers compilation at startup

settings = get_settings()


# ── Logging ──────────────────────────────────────────────────────────────────

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s | %(levelname)-8s | %(name)s — %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
        },
    },
    "root": {
        "level": "DEBUG" if settings.debug else "INFO",
        "handlers": ["console"],
    },
}

logging.config.dictConfig(LOGGING_CONFIG)
logger = logging.getLogger(__name__)


# ── Lifespan ─────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    logger.info(f"Model: {settings.claude_model}")
    logger.info(f"Debug: {settings.debug}")

    # Ensure outputs directory exists
    Path(settings.outputs_dir).mkdir(parents=True, exist_ok=True)
    logger.info(f"Outputs directory: {settings.outputs_dir}")

    # Pipeline is already compiled at import time — just confirm
    logger.info("LangGraph pipeline: ready")

    yield

    # Shutdown
    logger.info("Shutting down")


# ── App factory ───────────────────────────────────────────────────────────────

def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="""
        Upload a garment image or fashion sketch and receive a complete
        sewing pattern with instructions and a printable PDF.
        """,
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # ── Middleware ────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.debug else [],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Static files & templates ──────────────────────────────────────
    app.mount("/static", StaticFiles(directory="static"), name="static")
    templates = Jinja2Templates(directory="templates")

    # ── Routers ───────────────────────────────────────────────────────
    app.include_router(health.router, tags=["Health"])
    app.include_router(pattern.router, prefix="/api/v1", tags=["Pattern"])

    # ── Frontend route ────────────────────────────────────────────────
    @app.get("/", response_class=HTMLResponse, include_in_schema=False)
    async def index(request: Request):
        return templates.TemplateResponse(
            request=request,
            name="index.html",
            context={"app_name": settings.app_name}
        )

    return app


app = create_app()