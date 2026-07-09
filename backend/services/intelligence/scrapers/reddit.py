"""Reddit scraper using httpx (async) with OAuth2 token management."""

from __future__ import annotations

import time
from typing import Any

import httpx

from backend.config import get_settings
from backend.services.intelligence.scrapers.base import BaseScraper, RawTopic, scraper_retry
from backend.utils.logger import get_logger

logger = get_logger(__name__)

DEFAULT_SUBREDDITS = [
    "technology", "science", "worldnews", "futurology", "gadgets",
    "programming", "dataisbeautiful", "todayilearned", "explainlikeimfive",
    "Showerthoughts", "LifeProTips", "AskReddit",
]


class RedditScraper(BaseScraper):
    """Scrape Reddit for hot posts with comment velocity and engagement signals."""

    source_name = "reddit"
    rate_limit_requests = 60
    rate_limit_window = 60

    def __init__(
        self,
        subreddits: list[str] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self._subreddits = subreddits or DEFAULT_SUBREDDITS
        self._access_token: str | None = None
        self._token_expires_at: float = 0.0
        settings = get_settings()
        self._client_id = settings.REDDIT_CLIENT_ID
        self._client_secret = settings.REDDIT_CLIENT_SECRET
        self._user_agent = settings.REDDIT_USER_AGENT

    async def _obtain_token(self) -> str:
        """Obtain OAuth2 application-only access token."""
        if self._access_token and time.time() < self._token_expires_at:
            return self._access_token

        client = await self._get_client()
        response = await client.post(
            "https://www.reddit.com/api/v1/access_token",
            data={"grant_type": "client_credentials"},
            auth=(self._client_id, self._client_secret),
            headers={"User-Agent": self._user_agent},
        )
        response.raise_for_status()
        data = response.json()
        self._access_token = data["access_token"]
        self._token_expires_at = time.time() + data.get("expires_in", 3600) - 60
        logger.info("reddit_token_obtained", expires_in=data.get("expires_in"))
        return self._access_token  # type: ignore[return-value]

    def _calculate_comment_velocity(self, post: dict[str, Any]) -> float:
        """Calculate comments per hour since the post was created."""
        created_utc = post.get("created_utc", 0)
        num_comments = post.get("num_comments", 0)
        age_hours = max((time.time() - created_utc) / 3600, 0.1)
        return round(num_comments / age_hours, 2)

    def _post_to_topic(self, post: dict[str, Any], subreddit: str) -> RawTopic:
        """Convert a Reddit post JSON object to a RawTopic."""
        comment_velocity = self._calculate_comment_velocity(post)
        score = post.get("score", 0)
        upvote_ratio = post.get("upvote_ratio", 0.0)

        return RawTopic(
            title=post.get("title", ""),
            description=post.get("selftext", "")[:500] or post.get("title", ""),
            engagement_metrics={
                "score": score,
                "upvote_ratio": upvote_ratio,
                "num_comments": post.get("num_comments", 0),
                "comment_velocity": comment_velocity,
                "gilded": post.get("gilded", 0),
                "total_awards_received": post.get("total_awards_received", 0),
            },
            source=self.source_name,
            platform="reddit",
            url=f"https://reddit.com{post.get('permalink', '')}",
            raw_data={
                "subreddit": subreddit,
                "author": post.get("author", ""),
                "created_utc": post.get("created_utc", 0),
                "is_video": post.get("is_video", False),
                "domain": post.get("domain", ""),
            },
        )

    @scraper_retry
    async def _fetch_subreddit_hot(self, subreddit: str, limit: int = 25) -> list[RawTopic]:
        """Fetch hot posts from a single subreddit."""
        token = await self._obtain_token()
        client = await self._get_client()

        response = await client.get(
            f"https://oauth.reddit.com/r/{subreddit}/hot",
            params={"limit": limit, "raw_json": 1},
            headers={
                "Authorization": f"Bearer {token}",
                "User-Agent": self._user_agent,
            },
        )
        response.raise_for_status()
        data = response.json()

        topics: list[RawTopic] = []
        for child in data.get("data", {}).get("children", []):
            post = child.get("data", {})
            if post.get("stickied"):
                continue
            topics.append(self._post_to_topic(post, subreddit))

        return topics

    async def scrape(self) -> list[RawTopic]:
        """Scrape hot posts from all configured subreddits."""
        await self._check_limit()
        all_topics: list[RawTopic] = []

        for subreddit in self._subreddits:
            try:
                topics = await self._fetch_subreddit_hot(subreddit, limit=15)
                all_topics.extend(topics)
            except Exception as exc:
                logger.error(
                    "reddit_subreddit_error",
                    subreddit=subreddit,
                    error=str(exc),
                )

        # Sort by comment velocity (highest engagement signals first)
        all_topics.sort(
            key=lambda t: t.engagement_metrics.get("comment_velocity", 0),
            reverse=True,
        )

        logger.info(
            "reddit_scrape_complete",
            subreddit_count=len(self._subreddits),
            topic_count=len(all_topics),
        )
        return all_topics

    async def health_check(self) -> bool:
        """Verify Reddit OAuth2 is working."""
        try:
            await self._obtain_token()
            return True
        except Exception as exc:
            logger.error("reddit_health_fail", error=str(exc))
            return False
