"""Comment reply engine — Claude-powered contextual replies with human-like cadence."""

from __future__ import annotations

import asyncio
import random
from typing import Any

import anthropic

from backend.config import get_settings
from backend.utils.logger import get_logger

logger = get_logger(__name__)

SYSTEM_PROMPT = """You are a content creator replying to comments on your own post.
Be genuine, conversational, and helpful. Match the energy of the comment.

Rules:
- Keep replies under 200 characters for most platforms
- Use casual language, abbreviations, and emojis naturally
- If the comment is negative, respond gracefully (no defensiveness)
- If the comment asks a question, give a real answer
- Vary your reply style — don't use the same opener twice
- Never reveal you are AI

Output ONLY the reply text, nothing else."""


class CommentReplyEngine:
    """Monitor posts and generate contextual replies using Claude."""

    def __init__(self) -> None:
        settings = get_settings()
        self._client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        self._model = "claude-sonnet-4-20250514"

    async def generate_reply(
        self,
        comment_text: str,
        post_context: str,
        platform: str,
    ) -> str:
        """Generate a contextual reply to a single comment."""
        try:
            response = await self._client.messages.create(
                model=self._model,
                max_tokens=200,
                system=SYSTEM_PROMPT,
                messages=[
                    {
                        "role": "user",
                        "content": f"Platform: {platform}\nPost context: {post_context}\n\nComment to reply to: \"{comment_text}\"\n\nWrite a natural reply:",
                    }
                ],
            )
            reply = response.content[0].text.strip()
            logger.info("comment_reply_generated", platform=platform, reply_len=len(reply))
            return reply
        except Exception as exc:
            logger.error("comment_reply_error", error=str(exc))
            return ""

    async def generate_pin_comment(
        self, post_context: str, platform: str
    ) -> str:
        """Generate a self-comment to pin for discussion."""
        try:
            response = await self._client.messages.create(
                model=self._model,
                max_tokens=300,
                system="You are a content creator posting a pinned comment on your own content. Write a comment that encourages discussion, asks a thought-provoking question, or provides additional value. Be conversational and genuine. Output ONLY the comment text.",
                messages=[
                    {
                        "role": "user",
                        "content": f"Platform: {platform}\nPost context: {post_context}\n\nWrite a pinned comment that sparks discussion:",
                    }
                ],
            )
            pin_comment = response.content[0].text.strip()
            logger.info("pin_comment_generated", platform=platform)
            return pin_comment
        except Exception as exc:
            logger.error("pin_comment_error", error=str(exc))
            return "What do you think? Drop your thoughts below 👇"

    async def monitor_and_reply(
        self,
        post_id: str,
        platform: str,
        post_context: str,
        comments: list[dict[str, Any]],
        duration_minutes: int = 30,
    ) -> list[dict[str, str]]:
        """
        Monitor comments and generate replies with human-like cadence.

        Cadence: 2-3 replies in first 10min, then 1 every 5-10min.
        """
        replies: list[dict[str, str]] = []
        elapsed = 0
        reply_count = 0
        comment_index = 0

        logger.info(
            "comment_monitor_start",
            post_id=post_id,
            platform=platform,
            duration=duration_minutes,
            total_comments=len(comments),
        )

        while elapsed < duration_minutes and comment_index < len(comments):
            # Determine reply cadence
            if elapsed < 10:
                # First 10 minutes: 2-3 replies
                delay = random.randint(2, 4)
            else:
                # After 10 minutes: 1 every 5-10 minutes
                delay = random.randint(5, 10)

            await asyncio.sleep(delay * 60)
            elapsed += delay

            if comment_index >= len(comments):
                break

            comment = comments[comment_index]
            comment_text = comment.get("text", "")
            comment_id = comment.get("id", f"comment_{comment_index}")

            if not comment_text:
                comment_index += 1
                continue

            reply_text = await self.generate_reply(comment_text, post_context, platform)

            if reply_text:
                replies.append({
                    "comment_id": comment_id,
                    "reply_text": reply_text,
                    "timestamp_minutes": str(elapsed),
                })
                reply_count += 1

            comment_index += 1

            logger.info(
                "comment_replied",
                post_id=post_id,
                reply_count=reply_count,
                elapsed_minutes=elapsed,
            )

        logger.info(
            "comment_monitor_complete",
            post_id=post_id,
            total_replies=len(replies),
            duration=elapsed,
        )
        return replies
