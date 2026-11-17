from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from expense_flow import __version__
from expense_flow.config import get_settings
from expense_flow.database import engine, init_db
from expense_flow.exceptions import ExpenseFlowError, PolicyViolationError
from expense_flow.router import router as claims_router


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None]:
    await init_db()
    yield
    await engine.dispose()


async def handle_domain_error(_request: Request, exc: ExpenseFlowError) -> JSONResponse:
    """Turn domain errors into JSON responses (404, 409, or 422 with a violations list)."""
    content: dict[str, object] = {"detail": str(exc)}
    if isinstance(exc, PolicyViolationError):
        content["violations"] = [{"code": v.code, "message": v.message} for v in exc.violations]
    return JSONResponse(status_code=exc.status_code, content=content)


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version=__version__, lifespan=lifespan)
    app.add_exception_handler(ExpenseFlowError, handle_domain_error)  # type: ignore[arg-type]
    app.include_router(claims_router)

    @app.get("/health", tags=["ops"])
    async def health() -> dict[str, str]:
        return {"status": "ok", "environment": settings.environment}

    return app


app = create_app()
