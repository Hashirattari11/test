"""Billing routes: Stripe Checkout, Billing Portal, and webhook handling."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, Header
from pydantic import BaseModel

from ..billing import (
    create_checkout_session,
    create_billing_portal_session,
    process_stripe_webhook,
    check_plan_limit,
    get_user_plan_info,
    get_subscription_billing_period,
)
from ..db import db
from ..deps import get_current_user_id
from ..schemas import (
    CheckoutSessionIn,
    CheckoutSessionOut,
    BillingPortalOut,
    BillingStatusOut,
)

router = APIRouter(prefix="/billing", tags=["billing"])
logger = logging.getLogger("billing")


# ---------------------------------------------------------------------------
# Checkout Session
# ---------------------------------------------------------------------------
@router.post("/create-checkout-session", response_model=CheckoutSessionOut)
def create_checkout(body: CheckoutSessionIn, user_id: str = Depends(get_current_user_id)) -> CheckoutSessionOut:
    """Create a Stripe Checkout session for the selected plan."""
    if body.plan not in ("starter", "growth", "enterprise"):
        raise HTTPException(status_code=400, detail="Invalid plan")

    # Get user email for Stripe customer
    user = db().table("users").select("email").eq("id", user_id).limit(1).execute()
    if not user.data:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        session_id, url = create_checkout_session(
            user_id=user_id,
            plan=body.plan,
            success_url=body.success_url,
            cancel_url=body.cancel_url,
            customer_email=user.data[0]["email"],
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception:
        logger.exception("create-checkout-session failed for user %s", user_id)
        raise HTTPException(status_code=502, detail="Billing service error")

    return CheckoutSessionOut(session_id=session_id, url=url)


# ---------------------------------------------------------------------------
# Billing Portal
# ---------------------------------------------------------------------------
@router.get("/portal", response_model=BillingPortalOut)
def billing_portal(user_id: str = Depends(get_current_user_id)) -> BillingPortalOut:
    """Generate a Stripe Billing Portal session for the current user."""
    # Get frontend URL for return_url
    from ..config import settings
    return_url = settings.frontend_origins.split(",")[0].strip() + "/dashboard/billing"

    try:
        url = create_billing_portal_session(user_id, return_url)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception:
        logger.exception("billing-portal failed for user %s", user_id)
        raise HTTPException(status_code=502, detail="Billing service error")

    return BillingPortalOut(url=url)


# ---------------------------------------------------------------------------
# Billing Status (for dashboard)
# ---------------------------------------------------------------------------
@router.get("/status", response_model=BillingStatusOut)
def billing_status(user_id: str = Depends(get_current_user_id)) -> BillingStatusOut:
    """Get current billing status and usage for the dashboard."""
    info = get_user_plan_info(user_id)
    if not info:
        raise HTTPException(status_code=404, detail="User not found")

    # Determine plan name from status/limit
    plan_status = info["plan_status"]
    limit = info["monitored_api_limit"]

    if plan_status == "trial":
        plan = "trial"
    elif limit == 10:
        plan = "starter"
    elif limit == 50:
        plan = "growth"
    elif limit == -1:
        plan = "enterprise"
    else:
        plan = "trial"

    # Honest billing-period fields: derived from the live Stripe subscription
    # when one exists; otherwise we report what we actually know (no period =
    # no active subscription). Never fabricate `None`/False.
    period_end, cancel_at = get_subscription_billing_period(user_id)

    return BillingStatusOut(
        plan=plan,
        plan_status=plan_status,
        monitored_api_limit=limit,
        monitored_api_count=info["monitored_api_count"],
        current_period_end=period_end,
        cancel_at_period_end=cancel_at,
    )


# ---------------------------------------------------------------------------
# Stripe Webhook (no auth - uses Stripe signature)
# ---------------------------------------------------------------------------
class WebhookRequest(BaseModel):
    pass  # We read raw body


@router.post("/webhooks/stripe/billing")
async def stripe_billing_webhook(
    request: Request,
    stripe_signature: str | None = Header(default=None, alias="Stripe-Signature"),
):
    """Handle Stripe billing webhooks (checkout, subscription updates, etc.)."""
    if not stripe_signature:
        raise HTTPException(status_code=400, detail="Missing Stripe-Signature header")

    payload = await request.body()
    try:
        result = process_stripe_webhook(payload, stripe_signature)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception:
        logger.exception("stripe billing webhook processing failed")
        raise HTTPException(status_code=500, detail="Webhook processing failed")

    return result