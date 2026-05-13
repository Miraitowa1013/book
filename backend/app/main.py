import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db.init_db import init_db
from app.api.resume_routes import router as resume_router


def create_app() -> FastAPI:
    app = FastAPI(title="Resume Optimizer API", version="1.0.0")

    # 给前端开发服务器开放跨域；生产环境建议改成更严格的白名单。
    allowed_origins = os.getenv("CORS_ALLOW_ORIGINS", "*").split(",")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in allowed_origins if o.strip()],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    init_db()
    app.include_router(resume_router, prefix="/api/resume")
    return app


app = create_app()

