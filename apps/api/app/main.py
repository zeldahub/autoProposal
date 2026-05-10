"""Lon BE entry point."""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.errors import LonError, lon_exception_handler
from app import models  # noqa: F401  — SQLAlchemy 모델 등록을 위한 사이드이펙트 import
from app.routers import admin, artifacts, auth, backup, categories, collaboration, files, generate, llm, notifications, projects, settings as settings_router, users
from app.services.jobs import register_jobs, scheduler, shutdown as jobs_shutdown


@asynccontextmanager
async def lifespan(_app: FastAPI):
    Path(settings.workspace_dir).mkdir(parents=True, exist_ok=True)
    (Path(settings.workspace_dir) / "attachments").mkdir(parents=True, exist_ok=True)
    (Path(settings.workspace_dir) / "outputs").mkdir(parents=True, exist_ok=True)
    register_jobs()
    if settings.jobs_enabled and not scheduler.running:
        scheduler.start()
    try:
        yield
    finally:
        jobs_shutdown()


app = FastAPI(
    title="Lon API",
    version="0.1.0",
    description="AI 사업제안서 자동 생성기 BE",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(LonError, lon_exception_handler)


@app.get("/healthz")
async def healthz():
    return JSONResponse({"status": "ok", "version": app.version})


api_prefix = "/api"
app.include_router(auth.router, prefix=f"{api_prefix}/auth", tags=["auth"])
app.include_router(users.router, prefix=f"{api_prefix}/users", tags=["users"])
app.include_router(projects.router, prefix=f"{api_prefix}/projects", tags=["projects"])
app.include_router(files.router, prefix=f"{api_prefix}/files", tags=["files"])
app.include_router(llm.router, prefix=f"{api_prefix}/llm", tags=["llm"])
app.include_router(generate.router, prefix=f"{api_prefix}/generate", tags=["generate"])
app.include_router(categories.router, prefix=f"{api_prefix}/categories", tags=["categories"])
app.include_router(artifacts.router, prefix=f"{api_prefix}/artifacts", tags=["artifacts"])
app.include_router(settings_router.router, prefix=f"{api_prefix}/settings/ai", tags=["settings"])
app.include_router(admin.router, prefix=f"{api_prefix}/admin", tags=["admin"])
app.include_router(notifications.router, prefix=f"{api_prefix}/notifications", tags=["notifications"])
app.include_router(collaboration.router, prefix=f"{api_prefix}", tags=["collaboration"])
app.include_router(backup.router, prefix=f"{api_prefix}", tags=["backup"])
