"""Twitter/X optimizer — thread format with hook → value tweets → CTA."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from backend.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class TwitterVariant:
    """Twitter-optimised content variant (thread format)."""

    tweets: list[str] = field(default_factory=list)
    hashtags: list[str] = field(default_factory=list)
    thread_hook: str = ""
    media_s3_keys: list[str] = field(default_factory=list)
    specs: dict[str, Any] = field(default_factory=dict)


class TwitterOptimizer:
    """Optimise content for Twitter/X: thread format."""

    MAX_TWEET_LENGTH = 280

    def optimize(
        self,
        title: str,
        talking_points: list[str],
        hook_text: str = "",
        cta_text: str = "",
        keywords: list[str] | None = None,
        media_s3_keys: list[str] | None = None,
    ) -> TwitterVariant:
        """Create a Twitter thread-optimised variant."""
        tweets = self._build_thread(title, talking_points, hook_text, cta_text)
        hashtags = self._generate_hashtags(keywords or [])

        variant = TwitterVariant(
            tweets=tweets,
            hashtags=hashtags,
            thread_hook=tweets[0] if tweets else "",
            media_s3_keys=media_s3_keys or [],
            specs={
                "max_tweet_length": 280,
                "max_thread_length": 25,
                "media_per_tweet": 4,
                "format": "text_thread",
            },
        )

        logger.info(
            "twitter_optimized",
            title=title[:60],
            tweet_count=len(tweets),
        )
        return variant

    def _truncate_tweet(self, text: str, suffix: str = "") -> str:
        """Truncate a tweet to ≤280 chars, preserving word boundaries."""
        max_len = self.MAX_TWEET_LENGTH - len(suffix)
        if len(text) <= max_len:
            return text + suffix

        truncated = text[:max_len - 3]
        last_space = truncated.rfind(" ")
        if last_space > max_len // 2:
            truncated = truncated[:last_space]
        return truncated + "..." + suffix

    def _build_thread(
        self,
        title: str,
        talking_points: list[str],
        hook_text: str,
        cta_text: str,
    ) -> list[str]:
        """Build a numbered thread: hook → value → recap → CTA."""
        tweets: list[str] = []

        # Tweet 1: Hook
        hook = hook_text or f"🧵 {title}"
        hook = self._truncate_tweet(hook, "\n\nThread 🧵👇")
        tweets.append(hook)

        # Value tweets from talking points
        for i, point in enumerate(talking_points[:8]):
            number = i + 2
            tweet = f"{number}/ {point}"
            tweets.append(self._truncate_tweet(tweet))

        # Recap tweet
        if talking_points:
            recap_items = [f"• {tp[:40]}" for tp in talking_points[:4]]
            recap = f"📋 Quick recap:\n\n" + "\n".join(recap_items)
            tweets.append(self._truncate_tweet(recap))

        # CTA tweet
        cta = cta_text or "If you found this valuable:\n\n♻️ Repost for your audience\n❤️ Like to bookmark\n👤 Follow for more threads like this"
        tweets.append(self._truncate_tweet(cta))

        return tweets

    def _generate_hashtags(self, keywords: list[str]) -> list[str]:
        """Generate 2-3 relevant hashtags (Twitter prefers fewer)."""
        hashtags: list[str] = []
        for kw in keywords[:3]:
            tag = kw.replace(" ", "")
            if len(tag) > 2:
                hashtags.append(f"#{tag}")
        return hashtags
