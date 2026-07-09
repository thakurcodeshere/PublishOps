"""Master repackager — delegates to per-platform optimizers and stores variants."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.content import ContentAsset
from backend.models.platform_variant import PlatformVariant, VariantStatus
from backend.services.optimizer.instagram import InstagramOptimizer
from backend.services.optimizer.linkedin import LinkedInOptimizer
from backend.services.optimizer.tiktok import TikTokOptimizer
from backend.services.optimizer.twitter import TwitterOptimizer
from backend.services.optimizer.youtube import YouTubeOptimizer
from backend.services.optimizer.pinterest import PinterestOptimizer
from backend.utils.logger import get_logger

logger = get_logger(__name__)


class MasterRepackager:
    """Orchestrate platform-specific optimisation for content assets."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._youtube = YouTubeOptimizer()
        self._tiktok = TikTokOptimizer()
        self._instagram = InstagramOptimizer()
        self._twitter = TwitterOptimizer()
        self._linkedin = LinkedInOptimizer()
        self._pinterest = PinterestOptimizer()

    async def repackage(
        self,
        content_asset: ContentAsset,
        target_platforms: list[str],
        title: str = "",
        hook_text: str = "",
        talking_points: list[str] | None = None,
        script_text: str = "",
        keywords: list[str] | None = None,
    ) -> list[PlatformVariant]:
        """
        Repackage a content asset for all target platforms.

        Delegates to per-platform handlers and stores variants.
        """
        variants: list[PlatformVariant] = []
        points = talking_points or []
        kws = keywords or []

        for platform in target_platforms:
            try:
                variant = await self._optimize_for_platform(
                    platform=platform,
                    asset=content_asset,
                    title=title,
                    hook_text=hook_text,
                    talking_points=points,
                    script_text=script_text,
                    keywords=kws,
                )
                if variant:
                    variants.append(variant)
            except Exception as exc:
                logger.error(
                    "repackage_platform_error",
                    platform=platform,
                    asset_id=str(content_asset.id),
                    error=str(exc),
                )

        logger.info(
            "repackage_complete",
            asset_id=str(content_asset.id),
            platforms=target_platforms,
            variants_created=len(variants),
        )
        return variants

    async def _optimize_for_platform(
        self,
        platform: str,
        asset: ContentAsset,
        title: str,
        hook_text: str,
        talking_points: list[str],
        script_text: str,
        keywords: list[str],
    ) -> PlatformVariant | None:
        """Run platform-specific optimisation and create a variant record."""
        platform_lower = platform.lower()
        video_s3_key = asset.s3_key or ""

        caption = ""
        hashtags: list[str] = []
        aspect_ratio = "16:9"
        variant_title = title
        specs: dict[str, Any] = {}

        if platform_lower == "youtube":
            yt = await self._youtube.optimize(
                title=title,
                script_text=script_text,
                keywords=keywords,
                video_s3_key=video_s3_key,
            )
            variant_title = yt.title
            caption = yt.description
            hashtags = yt.tags
            aspect_ratio = yt.aspect_ratio
            specs = yt.specs

        elif platform_lower == "tiktok":
            tt = self._tiktok.optimize(
                title=title,
                hook_text=hook_text,
                script_text=script_text,
                keywords=keywords,
                video_s3_key=video_s3_key,
            )
            caption = tt.caption
            hashtags = tt.hashtags
            aspect_ratio = tt.aspect_ratio
            specs = tt.specs

        elif platform_lower == "instagram":
            ig = self._instagram.optimize(
                title=title,
                talking_points=talking_points,
                hook_text=hook_text,
                keywords=keywords,
                video_s3_key=video_s3_key,
            )
            caption = ig.reel_caption
            hashtags = ig.hashtags
            aspect_ratio = ig.reel_aspect_ratio
            specs = ig.specs

        elif platform_lower == "twitter":
            tw = self._twitter.optimize(
                title=title,
                talking_points=talking_points,
                hook_text=hook_text,
                keywords=keywords,
            )
            caption = "\n---\n".join(tw.tweets)
            hashtags = tw.hashtags
            aspect_ratio = "16:9"
            specs = tw.specs

        elif platform_lower == "linkedin":
            li = self._linkedin.optimize(
                title=title,
                talking_points=talking_points,
                hook_text=hook_text,
                keywords=keywords,
            )
            caption = li.text_post
            hashtags = li.hashtags
            aspect_ratio = "1:1"
            specs = li.specs

        elif platform_lower == "pinterest":
            pin = self._pinterest.optimize_pin(
                topic_title=title,
                script_body=script_text,
                landing_page_url="https://publishops.io/blog"
            )
            variant_title = pin["title"]
            caption = pin["description"]
            hashtags = []
            aspect_ratio = "2:3" if pin["media_type"] == "image" else "9:16"
            specs = {
                "board_name": pin["board_name"],
                "link": pin["link"],
                "media_type": pin["media_type"]
            }

        else:
            logger.warning("unknown_platform", platform=platform)
            return None

        # Create variant record
        variant = PlatformVariant(
            asset_id=asset.id,
            brief_id=asset.brief_id,
            platform=platform_lower,
            aspect_ratio=aspect_ratio,
            title=variant_title,
            caption=caption,
            hashtags=hashtags,
            s3_key=video_s3_key,
            specs=specs,
            status=VariantStatus.READY,
        )
        self._session.add(variant)
        await self._session.flush()

        logger.info(
            "variant_created",
            variant_id=str(variant.id),
            platform=platform_lower,
            aspect_ratio=aspect_ratio,
        )
        return variant
