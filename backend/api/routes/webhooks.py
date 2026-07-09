"""Purchase webhook API routes (Tier E) for Gumroad, Stripe, and Shopify transactions."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.services.growth.revenue_engine import RevenueAttributionEngine

router = APIRouter()
attribution_engine = RevenueAttributionEngine()
logger = get_logger(__name__)


@router.post("/stripe", response_model=dict)
async def stripe_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    """Handle Stripe webhook events (checkout.session.completed)."""
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    event_type = payload.get("type")
    
    if event_type == "checkout.session.completed":
        data = payload.get("data", {}).get("object", {})
        
        transaction_id = data.get("id")
        amount = float(data.get("amount_total", 0)) / 100.0  # Stripe lists in cents
        currency = data.get("currency", "usd").upper()
        customer_email = data.get("customer_details", {}).get("email")
        
        # Metadata typically carries UTM parameters from checkout redirects
        metadata = data.get("metadata", {})
        utm_campaign = metadata.get("utm_campaign")
        utm_source = metadata.get("utm_source")

        if transaction_id:
            await attribution_engine.log_transaction(
                db=db,
                transaction_id=transaction_id,
                amount=amount,
                currency=currency,
                platform="stripe",
                email=customer_email,
                utm_campaign=utm_campaign,
                utm_source=utm_source
            )
            logger.info("stripe_webhook_processed", tx_id=transaction_id, amount=amount)

    return {"status": "received"}


@router.post("/gumroad", response_model=dict)
async def gumroad_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    """Handle Gumroad sale webhooks."""
    try:
        # Gumroad typically posts URL-encoded form data
        form_data = await request.form()
        data = dict(form_data)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid form data payload")

    transaction_id = data.get("sale_id")
    price_cents = data.get("price")
    
    if transaction_id and price_cents:
        amount = float(price_cents) / 100.0
        customer_email = data.get("email")
        
        # Gumroad custom fields contain UTM parameters
        utm_campaign = data.get("utm_campaign")
        utm_source = data.get("utm_source")

        await attribution_engine.log_transaction(
            db=db,
            transaction_id=transaction_id,
            amount=amount,
            currency="USD",
            platform="gumroad",
            email=customer_email,
            utm_campaign=utm_campaign,
            utm_source=utm_source
        )
        logger.info("gumroad_webhook_processed", tx_id=transaction_id, amount=amount)

    return {"status": "received"}


@router.post("/shopify", response_model=dict)
async def shopify_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    """Handle Shopify order creation webhooks."""
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    transaction_id = payload.get("id")
    total_price = payload.get("total_price")
    
    if transaction_id and total_price:
        amount = float(total_price)
        currency = payload.get("currency", "USD")
        customer_email = payload.get("customer", {}).get("email")
        
        # Shopify captures landing site/UTMs in referring_site or landing_site_ref
        # Or custom attributes attached to the cart
        note_attributes = payload.get("note_attributes", [])
        utm_campaign = None
        utm_source = None
        for attr in note_attributes:
            if attr.get("name") == "utm_campaign":
                utm_campaign = attr.get("value")
            elif attr.get("name") == "utm_source":
                utm_source = attr.get("value")

        await attribution_engine.log_transaction(
            db=db,
            transaction_id=str(transaction_id),
            amount=amount,
            currency=currency,
            platform="shopify",
            email=customer_email,
            utm_campaign=utm_campaign,
            utm_source=utm_source
        )
        logger.info("shopify_webhook_processed", tx_id=str(transaction_id), amount=amount)

    return {"status": "received"}


from backend.utils.logger import get_logger  # noqa: E402
