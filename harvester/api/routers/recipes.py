"""Recipe API endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from harvester.api.auth import require_api_token
from harvester.api.deps import get_db_session
from harvester.db.models import Recipe
from harvester.domain.audit import write_audit
from harvester.domain.state import RECIPE_TRANSITIONS, transition_entity

router = APIRouter(prefix="/recipes", tags=["recipes"])

APPROVED_EXECUTORS = {"firecrawl", "http_fetch", "rss_parse", "static"}


class RecipeCreateRequest(BaseModel):
    name: str
    executor: str
    config: dict | None = None
    risk_level: str = "low"
    auth_profile: dict | None = None


class RecipeResponse(BaseModel):
    id: str
    name: str
    executor: str
    status: str
    risk_level: str
    approval_status: str
    version: int
    created_at: datetime


@router.post("", response_model=RecipeResponse, status_code=status.HTTP_201_CREATED)
def create_recipe(
    req: RecipeCreateRequest,
    _token: str = Depends(require_api_token),
    session: Session = Depends(get_db_session),
):
    """Create a draft recipe."""
    if req.executor not in APPROVED_EXECUTORS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown executor '{req.executor}'. Approved: {sorted(APPROVED_EXECUTORS)}",
        )

    recipe = Recipe(
        id=uuid.uuid4(),
        name=req.name,
        executor=req.executor,
        config=req.config,
        risk_level=req.risk_level,
        approval_status="pending",
        version=1,
        auth_profile=req.auth_profile,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    session.add(recipe)
    write_audit(
        session,
        actor="api",
        action="recipe.create",
        entity_type="recipe",
        entity_id=recipe.id,
        after_state={"name": req.name, "executor": req.executor, "approval_status": "pending"},
    )
    session.commit()
    session.refresh(recipe)
    return RecipeResponse(
        id=str(recipe.id),
        name=recipe.name,
        executor=recipe.executor,
        status="draft",
        risk_level=recipe.risk_level,
        approval_status=recipe.approval_status,
        version=recipe.version,
        created_at=recipe.created_at,
    )


@router.post("/{recipe_id}/approve", response_model=RecipeResponse)
def approve_recipe(
    recipe_id: str,
    _token: str = Depends(require_api_token),
    session: Session = Depends(get_db_session),
):
    """Approve a pending recipe."""
    recipe = session.get(Recipe, recipe_id)
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")

    try:
        transition_entity(
            session, recipe, RECIPE_TRANSITIONS, "approved", "api", "recipe",
            status_attr="approval_status",
        )
    except ValueError as e:
        session.rollback()
        raise HTTPException(status_code=400, detail=str(e)) from e

    session.commit()
    session.refresh(recipe)
    return RecipeResponse(
        id=str(recipe.id),
        name=recipe.name,
        executor=recipe.executor,
        status="approved",
        risk_level=recipe.risk_level,
        approval_status=recipe.approval_status,
        version=recipe.version,
        created_at=recipe.created_at,
    )
