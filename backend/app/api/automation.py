"""
Automation control API — spec sections 60-62: rule management plus
start/pause/stop. Every limit here is enforced inside
app/services/rapid_apply_service.detect_and_enqueue via
app/services/automation_rules_service.screening_block_reason — this file
only reads/writes the AutomationRule row, it doesn't re-implement any
enforcement logic itself.
"""
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database.session import get_db
from app.models.user import User
from app.schemas.automation import AutomationRuleRead, AutomationRuleUpdate
from app.services.audit_service import log_action
from app.services.automation_rules_service import get_or_create_rule

router = APIRouter(prefix="/automation", tags=["automation"])


def _client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


@router.get("/rules", response_model=AutomationRuleRead)
async def get_rules(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await get_or_create_rule(db, user)


@router.put("/rules", response_model=AutomationRuleRead)
async def update_rules(
    payload: AutomationRuleUpdate,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rule = await get_or_create_rule(db, user)
    changes = payload.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(rule, field, value)
    db.add(rule)
    if changes:
        await log_action(
            db,
            "automation.rules_updated",
            user_id=user.id,
            detail=", ".join(f"{k}={v}" for k, v in changes.items()),
            ip_address=_client_ip(request),
        )
    await db.commit()
    await db.refresh(rule)
    return rule


@router.post("/start", response_model=AutomationRuleRead)
async def start(request: Request, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    rule = await get_or_create_rule(db, user)
    rule.state = "running"
    db.add(rule)
    await log_action(db, "automation.state_changed", user_id=user.id, detail="state=running", ip_address=_client_ip(request))
    await db.commit()
    await db.refresh(rule)
    return rule


@router.post("/pause", response_model=AutomationRuleRead)
async def pause(request: Request, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    rule = await get_or_create_rule(db, user)
    rule.state = "paused"
    db.add(rule)
    await log_action(db, "automation.state_changed", user_id=user.id, detail="state=paused", ip_address=_client_ip(request))
    await db.commit()
    await db.refresh(rule)
    return rule


@router.post("/stop", response_model=AutomationRuleRead)
async def stop(request: Request, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """The global STOP button (spec section 62) — takes effect on the very
    next screening pass, regardless of Rapid Apply's own enabled toggle,
    match scores, or anything else in flight."""
    rule = await get_or_create_rule(db, user)
    rule.state = "stopped"
    db.add(rule)
    await log_action(db, "automation.state_changed", user_id=user.id, detail="state=stopped", ip_address=_client_ip(request))
    await db.commit()
    await db.refresh(rule)
    return rule
