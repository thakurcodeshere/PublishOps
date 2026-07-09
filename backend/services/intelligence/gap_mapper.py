"""Competitive Gap Mapper service (Tier A) to identify high-demand, low-coverage topics."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.competitor import Competitor, CompetitorContent, CoverageMatrix

logger = logging.getLogger(__name__)


class CompetitiveGapMapper:
    """Scrapes competitor posts and builds keyword coverage gap matrices."""

    async def scrape_competitor_recent_posts(self, db: AsyncSession, competitor_id: uuid.UUID) -> int:
        """Fetch and index recent posts for a competitor.
        
        Uses platform credentials or RSS stubs to fetch recent content.
        """
        result = await db.execute(select(Competitor).where(Competitor.id == competitor_id))
        competitor = result.scalar_one_or_none()
        if not competitor:
            raise ValueError("Competitor not found")

        # In a real environment, this crawls their YouTube channel, Twitter profile, etc.
        # Here we simulate finding 2 new articles/videos containing topic-related keywords.
        num_new_posts = 2
        
        simulated_titles = [
            f"How to build autonomous agentic systems on {competitor.name}",
            f"Why the future of AI is agentic workflows - {competitor.name} Opinion"
        ]

        now = datetime.now(timezone.utc)
        
        for i, title in enumerate(simulated_titles):
            # Check if post already exists by URL
            url = f"{competitor.url}/post/{now.strftime('%Y%m%d')}_{i}"
            check = await db.execute(select(CompetitorContent).where(CompetitorContent.url == url))
            if not check.scalar_one_or_none():
                post = CompetitorContent(
                    competitor_id=competitor.id,
                    title=title,
                    content_text=f"This is a detailed analysis of agentic systems by {competitor.name}.",
                    url=url,
                    publish_date=now,
                    views=1500 * (i + 1),
                    engagement_rate=0.045,
                    platform=competitor.platform
                )
                db.add(post)

        await db.commit()
        return num_new_posts

    async def build_coverage_matrix(
        self,
        db: AsyncSession,
        keyword_clusters: list[str],
        cluster_demands: dict[str, float]
    ) -> list[CoverageMatrix]:
        """Aggregate competitor content and calculate the coverage/demand gap per cluster.
        
        Args:
            keyword_clusters: List of keywords/clusters to map.
            cluster_demands: Dict mapping clusters to demand score (0.0 - 1.0).
            
        Returns:
            List of updated CoverageMatrix records.
        """
        # Fetch all competitors and content
        comp_res = await db.execute(select(Competitor))
        competitors = comp_res.scalars().all()
        
        coverage_records = []

        # Clear old matrix entries
        await db.execute(delete(CoverageMatrix))

        for competitor in competitors:
            # Fetch all content for this competitor
            content_res = await db.execute(
                select(CompetitorContent).where(CompetitorContent.competitor_id == competitor.id)
            )
            posts = content_res.scalars().all()
            
            for cluster in keyword_clusters:
                # Calculate coverage density: count how many posts match the keyword/cluster
                matching_posts = 0
                for post in posts:
                    text_to_check = f"{post.title or ''} {post.content_text or ''}".lower()
                    if cluster.lower() in text_to_check:
                        matching_posts += 1
                
                # Normalize coverage score: 0 to 1 based on match counts (cap at 5 posts for full coverage)
                coverage_score = min(1.0, matching_posts / 5.0)
                
                demand_score = cluster_demands.get(cluster, 0.5)
                # Gap is where demand exceeds competitor coverage
                gap_score = max(-1.0, min(1.0, demand_score - coverage_score))

                record = CoverageMatrix(
                    competitor_id=competitor.id,
                    keyword_cluster=cluster,
                    coverage_score=round(coverage_score, 2),
                    demand_score=round(demand_score, 2),
                    gap_score=round(gap_score, 2)
                )
                db.add(record)
                coverage_records.append(record)

        await db.commit()
        return coverage_records
        
    async def get_top_gaps(self, db: AsyncSession, limit: int = 5) -> list[dict[str, Any]]:
        """Identify keyword clusters with the highest gap scores (demand > competitor coverage)."""
        # Select average gap scores across competitors grouped by cluster
        # Using a raw text query or SQLAlchemy grouping
        query = """
            SELECT keyword_cluster, AVG(demand_score) as avg_demand, AVG(coverage_score) as avg_coverage, AVG(gap_score) as avg_gap
            FROM coverage_matrices
            GROUP BY keyword_cluster
            ORDER BY avg_gap DESC
            LIMIT :limit
        """
        result = await db.execute(text(query), {"limit": limit})
        
        gaps = []
        for row in result:
            gaps.append({
                "keyword_cluster": row[0],
                "demand_score": round(float(row[1]), 2),
                "coverage_score": round(float(row[2]), 2),
                "gap_score": round(float(row[3]), 2)
            })
        return gaps


import uuid
from sqlalchemy import text # noqa: E402
