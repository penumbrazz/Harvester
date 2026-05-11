"""Recipe API endpoints."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from harvester.api.auth import require_api_token
from harvester.api.deps import get_db_session
from harvester.api.schemas import PaginatedResponse
from harvester.db.models import Recipe
from harvester.domain.audit import write_audit
from harvester.domain.state import RECIPE_TRANSITIONS, transition_entity

router = APIRouter(prefix="/recipes", tags=["recipes"])

_Token = Depends(require_api_token)
_Session = Depends(get_db_session)

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
    risk_level: str
    approval_status: str
    version: int
    created_at: datetime
    updated_at: datetime | None = None


def _to_recipe_response(recipe: Recipe) -> RecipeResponse:
    """Serialize a Recipe ORM object to RecipeResponse."""
    return RecipeResponse(
        id=str(recipe.id),
        name=recipe.name,
        executor=recipe.executor,
        risk_level=recipe.risk_level,
        approval_status=recipe.approval_status,
        version=recipe.version,
        created_at=recipe.created_at,
        updated_at=recipe.updated_at,
    )


@router.post("", response_model=RecipeResponse, status_code=status.HTTP_201_CREATED)
def create_recipe(
    req: RecipeCreateRequest,
    _token: str = _Token,
    session: Session = _Session,
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
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
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
    return _to_recipe_response(recipe)


@router.post("/{recipe_id}/approve", response_model=RecipeResponse)
def approve_recipe(
    recipe_id: str,
    _token: str = _Token,
    session: Session = _Session,
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
    return _to_recipe_response(recipe)


class RecipeListResponse(PaginatedResponse[RecipeResponse]):
    """Paginated recipe list response."""


@router.get("", response_model=RecipeListResponse)
def list_recipes(
    _token: str = _Token,
    session: Session = _Session,
    approval_status: str | None = Query(None, description="Filter by approval status"),
    executor: str | None = Query(None, description="Filter by executor type"),
    limit: int = Query(20, ge=1, le=100, description="Page size"),
    offset: int = Query(0, ge=0, description="Page offset"),
):
    """List recipes with pagination and optional filtering."""
    query = session.query(Recipe)

    if approval_status:
        query = query.filter(Recipe.approval_status == approval_status)
    if executor:
        query = query.filter(Recipe.executor == executor)

    total = query.count()
    recipes = query.order_by(Recipe.created_at.desc()).offset(offset).limit(limit).all()
    items = [_to_recipe_response(r) for r in recipes]

    return RecipeListResponse(items=items, total=total, limit=limit, offset=offset)
