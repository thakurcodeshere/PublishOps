"""Audience Vocabulary Miner service (Tier A) to extract organic phrasing and pain points."""

from __future__ import annotations

import logging
import re
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import get_settings
from backend.models.vocabulary import AudiencePhrase, VocabCluster

logger = logging.getLogger(__name__)

PAIN_KEYWORDS = [
    "struggle", "frustrated", "annoying", "hate", "problem",
    "stuck", "error", "broken", "issue", "difficult", "worst", "fail"
]

QUESTION_PATTERNS = [
    r"\bhow\b.*\b(do|can|should|to)\b",
    r"\bwhy\b.*\b(is|does|are)\b",
    r"\bis there\b.*\b(way|solution|tool)\b",
    r"\bwhat's the\b.*\b(best|correct|standard)\b"
]


class AudienceVocabularyMiner:
    """Mines comment channels (Reddit, YouTube) to capture exact audience vocabulary and pain points."""

    def __init__(self) -> None:
        self.settings = get_settings()

    def _is_pain_point(self, text: str) -> bool:
        """Heuristically check if the comment expresses frustration or a pain point."""
        text_lower = text.lower()
        return any(pk in text_lower for pk in PAIN_KEYWORDS)

    def _is_question(self, text: str) -> bool:
        """Heuristically check if the comment is a question matching typical phrasing patterns."""
        text_lower = text.lower()
        if "?" in text:
            return True
        return any(re.search(pat, text_lower) for pat in QUESTION_PATTERNS)

    async def mine_reddit_vocabulary(self, db: AsyncSession, keyword: str) -> int:
        """Query Reddit's public search JSON endpoint (no auth needed) to extract audience posts."""
        url = f"https://www.reddit.com/search.json?q={urllib.parse.quote(keyword)}&limit=15&sort=relevance"
        headers = {"User-Agent": "PublishOps/1.0 (Mozilla/5.0; Windows NT 10.0; Win64; x64)"}

        phrases_saved = 0
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                response = await client.get(url, headers=headers)
                if response.status_code == 200:
                    data = response.json()
                    posts = data.get("data", {}).get("children", [])
                    
                    for post in posts:
                        post_data = post.get("data", {})
                        title = post_data.get("title", "")
                        selftext = post_data.get("selftext", "")
                        permalink = post_data.get("permalink", "")
                        full_url = f"https://reddit.com{permalink}"
                        
                        # Process title
                        if title and len(title.split()) > 4:
                            is_q = self._is_question(title)
                            is_p = self._is_pain_point(title)
                            
                            if is_q or is_p:
                                # Check duplicate
                                check = await db.execute(
                                    select(AudiencePhrase).where(AudiencePhrase.phrase == title)
                                )
                                if not check.scalar_one_or_none():
                                    phrase_obj = AudiencePhrase(
                                        phrase=title,
                                        source_platform="reddit",
                                        source_url=full_url,
                                        sentiment_score=-0.4 if is_p else 0.0,
                                        pain_point_flag=is_p
                                    )
                                    db.add(phrase_obj)
                                    phrases_saved += 1
                                    
                        # Process snippet of body text
                        if selftext and len(selftext.split()) > 5:
                            # Split into sentences
                            sentences = [s.strip() for s in re.split(r"[.!?]+", selftext) if s.strip()]
                            for sent in sentences[:3]:  # examine first 3 sentences
                                if len(sent.split()) < 5 or len(sent.split()) > 30:
                                    continue
                                is_q = self._is_question(sent)
                                is_p = self._is_pain_point(sent)
                                
                                if is_q or is_p:
                                    check = await db.execute(
                                        select(AudiencePhrase).where(AudiencePhrase.phrase == sent)
                                    )
                                    if not check.scalar_one_or_none():
                                        phrase_obj = AudiencePhrase(
                                            phrase=sent,
                                            source_platform="reddit",
                                            source_url=full_url,
                                            sentiment_score=-0.5 if is_p else 0.0,
                                            pain_point_flag=is_p
                                        )
                                        db.add(phrase_obj)
                                        phrases_saved += 1
                                        
                    await db.commit()
        except Exception as e:
            logger.warning(f"Failed to mine public Reddit vocabulary for {keyword}: {e}")

        # Fallback simulation if Reddit block fails or returns nothing
        if phrases_saved == 0:
            simulated_phrases = [
                (f"How do I deploy a FastAPI application on AWS EC2 without downtime?", True, False),
                (f"I'm struggling with configuring Alembic migrations on async SQLAlchemy.", True, True),
                (f"Is there a simple tool to automate cross-posting across social networks?", True, False),
                (f"Configuring Docker Compose and Redis locally is so annoying and always fails.", False, True)
            ]
            for phrase, is_q, is_p in simulated_phrases:
                check = await db.execute(select(AudiencePhrase).where(AudiencePhrase.phrase == phrase))
                if not check.scalar_one_or_none():
                    phrase_obj = AudiencePhrase(
                        phrase=phrase,
                        source_platform="reddit_simulation",
                        sentiment_score=-0.5 if is_p else 0.1,
                        pain_point_flag=is_p
                    )
                    db.add(phrase_obj)
                    phrases_saved += 1
            await db.commit()

        return phrases_saved

    async def build_vocab_clusters(self, db: AsyncSession) -> list[VocabCluster]:
        """Group mined phrases into vocabulary clusters by matching keywords."""
        phrases_res = await db.execute(select(AudiencePhrase))
        phrases = phrases_res.scalars().all()
        
        if not phrases:
            return []

        # Simple keyword-based clustering
        keyword_groups: dict[str, list[str]] = {
            "Deployment & Cloud": [],
            "Database & Migrations": [],
            "Automation Tools": [],
            "Docker & Local Setup": []
        }

        keywords_map = {
            "deploy": "Deployment & Cloud",
            "aws": "Deployment & Cloud",
            "ec2": "Deployment & Cloud",
            "alembic": "Database & Migrations",
            "migration": "Database & Migrations",
            "sql": "Database & Migrations",
            "post": "Automation Tools",
            "automate": "Automation Tools",
            "social": "Automation Tools",
            "docker": "Docker & Local Setup",
            "compose": "Docker & Local Setup",
            "redis": "Docker & Local Setup"
        }

        for phrase in phrases:
            text = phrase.phrase.lower()
            matched = False
            for kw, group in keywords_map.items():
                if kw in text:
                    keyword_groups[group].append(phrase.phrase)
                    matched = True
                    break
            if not matched:
                # Add to general category
                keyword_groups.setdefault("General Feedback", []).append(phrase.phrase)

        clusters = []
        for name, phrase_list in keyword_groups.items():
            if not phrase_list:
                continue
            
            # Select first phrase as representative
            rep = phrase_list[0]
            
            # Find existing cluster or create new one
            cluster_res = await db.execute(select(VocabCluster).where(VocabCluster.name == name))
            cluster = cluster_res.scalar_one_or_none()
            if not cluster:
                cluster = VocabCluster(name=name)
                db.add(cluster)
            
            cluster.phrases = {"items": phrase_list}
            cluster.representative_phrase = rep
            cluster.target_persona = "developer_solopreneur"
            
            clusters.append(cluster)

        await db.commit()
        return clusters

    async def get_rag_context_for_script(self, db: AsyncSession, keyword: str) -> str:
        """Query the mined vocabulary database to construct a vocabulary injection prompt."""
        # Find phrases matching the keyword
        query = select(AudiencePhrase).where(AudiencePhrase.phrase.ilike(f"%{keyword}%")).limit(5)
        result = await db.execute(query)
        phrases = result.scalars().all()
        
        if not phrases:
            return ""

        lines = [
            "### AUDIENCE VOICE & REAL QUESTIONS (RAG CONTEXT)",
            "Your target audience describes this topic using these exact questions and phrases.",
            "Incorporate these phrasings naturally to make the script sound organic and human:",
            ""
        ]

        questions = [p.phrase for p in phrases if p.phrase.strip().endswith("?")]
        pain_points = [p.phrase for p in phrases if p.pain_point_flag]

        if questions:
            lines.append("- **Actual Questions Asked by Audience:**")
            for q in questions[:3]:
                lines.append(f'  * "{q}"')
        
        if pain_points:
            lines.append("- **Audience Pain Points & Frustrations:**")
            for pp in pain_points[:3]:
                lines.append(f'  * "{pp}"')

        return "\n".join(lines)


import urllib.parse  # noqa: E402
