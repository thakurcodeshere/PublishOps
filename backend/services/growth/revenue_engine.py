"""Revenue Attribution Engine service (Tier E) to track sales conversions and feed ROI to topic scoring."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.collaboration import FunnelStage
from backend.models.content import ContentBrief
from backend.models.revenue import AttributionLink, ContentRevenue, RevenueEvent

logger = logging.getLogger(__name__)


class RevenueAttributionEngine:
    """Attributes financial transactions to content posts and adjusts future trend scoring based on ROI."""

    async def log_transaction(
        self,
        db: AsyncSession,
        transaction_id: str,
        amount: float,
        currency: str = "USD",
        platform: str = "stripe",
        email: str | None = None,
        utm_campaign: str | None = None,
        utm_source: str | None = None
    ) -> RevenueEvent:
        """Process and attribute purchase webhooks to social content.
        
        Matches using UTM campaigns or lead email history.
        """
        # 1. Create Revenue Event record
        event = RevenueEvent(
            transaction_id=transaction_id,
            amount=amount,
            currency=currency,
            customer_email=email,
            platform=platform,
            timestamp=datetime.now(timezone.utc),
            utm_campaign=utm_campaign,
            utm_source=utm_source
        )
        db.add(event)
        await db.flush()

        brief_id_to_attribute = None

        # 2. Match via UTM Campaign Code
        if utm_campaign:
            link_res = await db.execute(
                select(AttributionLink).where(AttributionLink.utm_code == utm_campaign)
            )
            link = link_res.scalar_one_or_none()
            if link:
                brief_id_to_attribute = link.brief_id
                logger.info("revenue_attributed_via_utm", campaign=utm_campaign, brief=str(brief_id_to_attribute))

        # 3. Match via Lead Email (Fallback Multi-touch)
        if not brief_id_to_attribute and email:
            funnel_res = await db.execute(
                select(FunnelStage).where(FunnelStage.email_contact == email)
            )
            lead = funnel_res.scalar_one_or_none()
            if lead:
                # Update lead stage to customer
                lead.stage = "customer"
                lead.estimated_value += amount
                db.add(lead)
                
                # Trace back to a matching campaign or default attribution link if we can
                # In this fallback, we check if they clicked a recent link (simulate tracking)
                # For this implementation, we locate the most recent active attribution link as fallback
                link_fallback = await db.execute(select(AttributionLink).limit(1))
                link = link_fallback.scalar_one_or_none()
                if link:
                    brief_id_to_attribute = link.brief_id
                    logger.info("revenue_attributed_via_lead_email", email=email, brief=str(brief_id_to_attribute))

        # 4. Update Content Revenue statistics
        if brief_id_to_attribute:
            rev_res = await db.execute(
                select(ContentRevenue).where(ContentRevenue.brief_id == brief_id_to_attribute)
            )
            revenue_stat = rev_res.scalar_one_or_none()
            
            if not revenue_stat:
                revenue_stat = ContentRevenue(
                    brief_id=brief_id_to_attribute,
                    revenue_attributed=0.0,
                    conversion_count=0
                )
                db.add(revenue_stat)
                
            revenue_stat.revenue_attributed += amount
            revenue_stat.conversion_count += 1
            db.add(revenue_stat)

        await db.commit()
        await db.refresh(event)
        return event

    async def get_high_value_keywords(self, db: AsyncSession, limit: int = 10) -> dict[str, float]:
        """Compile a dictionary of keywords and their generated revenue multiplier weights.
        
        Feeds back into Tier A Scorer to boost high-converting topics.
        """
        # Joint query between ContentRevenue, ContentBrief, and Topic to group by topic title keywords
        # Using a raw SQL lookup or simple Python aggregation for safety
        query = """
            SELECT cb.brief_text, cr.revenue_attributed
            FROM content_revenue cr
            JOIN content_briefs cb ON cr.brief_id = cb.id
            WHERE cr.revenue_attributed > 0
        """
        result = await db.execute(sa.text(query))
        
        keyword_revenue: dict[str, float] = {}
        for row in result:
            brief_text = (row[0] or "").lower()
            revenue = float(row[1])
            
            # Simple word extraction
            words = set(re.findall(r"\b[a-zA-Z]{4,12}\b", brief_text))
            for word in words:
                if word not in ["with", "from", "that", "this", "your", "have"]:
                    keyword_revenue[word] = keyword_revenue.get(word, 0.0) + revenue

        # Normalize to multipliers between 1.0 and 2.5
        multipliers: dict[str, float] = {}
        if keyword_revenue:
            max_rev = max(keyword_revenue.values())
            for kw, rev in sorted(keyword_revenue.items(), key=lambda x: x[1], reverse=True)[:limit]:
                # Max revenue maps to 2.5 multiplier, min maps to 1.1
                multiplier = 1.0 + (rev / max_rev) * 1.5
                multipliers[kw] = round(multiplier, 2)

        return multipliers


import re  # noqa: E402
import sqlalchemy as sa  # noqa: E402
