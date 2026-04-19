from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from atlas.api.deps import get_db

router = APIRouter(tags=["health"])


@router.get(
    "/health",
    summary="Liveness and database connectivity",
    response_model=None,
)
async def health(db: Annotated[AsyncSession, Depends(get_db)]) -> dict[str, str] | JSONResponse:
    db_status = "ok"
    try:
        await db.execute(text("SELECT 1"))
    except Exception:
        db_status = "error"

    payload: dict[str, str] = {"status": "ok", "db": db_status}
    if db_status != "ok":
        return JSONResponse(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content=payload)
    return payload
