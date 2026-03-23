import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.config import settings
from app.db.client import init_db, close_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await init_db()
    except Exception as e:
        import logging
        logging.getLogger("pc2").error(f"Database init failed: {e}")
    yield
    await close_db()


app = FastAPI(
    title="PC2 — Product Content Creator",
    version="2.0.0",
    description="Enterprise AI platform for end-to-end product item data processing",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)


# Global error handler
from fastapi import Request
from fastapi.responses import JSONResponse
import logging

logger = logging.getLogger("pc2")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "type": type(exc).__name__},
    )

cors_origins = [o.strip() for o in settings.cors_origins.split(",")]
# Railway wildcard support
if any("*" in o for o in cors_origins):
    cors_origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import and register routes
from app.routes import auth as auth_routes  # noqa: E402
from app.routes import users as user_routes  # noqa: E402
from app.routes import batches as batch_routes  # noqa: E402
from app.routes import products as product_routes  # noqa: E402
from app.routes import taxonomy as taxonomy_routes  # noqa: E402
from app.routes import pipeline as pipeline_routes  # noqa: E402
from app.routes import review as review_routes  # noqa: E402
from app.routes import admin as admin_routes  # noqa: E402
from app.routes import mappings as mapping_routes  # noqa: E402
from app.routes import templates as template_routes  # noqa: E402
from app.routes import publish as publish_routes  # noqa: E402
from app.routes import clients as client_routes  # noqa: E402
from app.routes import webhooks as webhook_routes  # noqa: E402

app.include_router(auth_routes.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(user_routes.router, prefix="/api/v1/admin/users", tags=["users"])
app.include_router(batch_routes.router, prefix="/api/v1/batches", tags=["batches"])
app.include_router(product_routes.router, prefix="/api/v1/products", tags=["products"])
app.include_router(taxonomy_routes.router, prefix="/api/v1/taxonomy", tags=["taxonomy"])
app.include_router(pipeline_routes.router, prefix="/api/v1/pipeline", tags=["pipeline"])
app.include_router(review_routes.router, prefix="/api/v1/review", tags=["review"])
app.include_router(admin_routes.router, prefix="/api/v1/admin", tags=["admin"])
app.include_router(mapping_routes.router, prefix="/api/v1/mappings", tags=["mappings"])
app.include_router(template_routes.router, prefix="/api/v1/templates", tags=["templates"])
app.include_router(publish_routes.router, prefix="/api/v1/products", tags=["publish"])
app.include_router(client_routes.router, prefix="/api/v1/clients", tags=["clients"])
app.include_router(webhook_routes.router, prefix="/api/v1/webhooks", tags=["webhooks"])


@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "version": "2.0.0",
        "demo_mode": settings.demo_mode,
        "ai_providers": {
            "openai": settings.has_openai,
            "anthropic": settings.has_anthropic,
            "serpapi": settings.has_serpapi,
        },
    }


# Serve frontend static files (built React app)
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
if STATIC_DIR.is_dir():
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """Serve the React SPA for all non-API routes."""
        file_path = STATIC_DIR / full_path
        if file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(STATIC_DIR / "index.html")
