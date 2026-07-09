"""Platform uploader — upload content to each platform via their APIs."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

import httpx

from backend.config import get_settings
from backend.utils.logger import get_logger
from backend.utils.s3 import S3Client

logger = get_logger(__name__)


class PlatformUploader:
    """Upload content to various social media platforms."""

    def __init__(self) -> None:
        self._s3 = S3Client()
        settings = get_settings()
        self._youtube_api_key = settings.YOUTUBE_API_KEY
        self._twitter_bearer = settings.TWITTER_BEARER_TOKEN
        self._linkedin_token = settings.LINKEDIN_ACCESS_TOKEN

    async def upload(
        self,
        platform: str,
        s3_key: str,
        title: str = "",
        description: str = "",
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Route upload to the correct platform handler."""
        platform_lower = platform.lower()
        handlers = {
            "youtube": self._upload_youtube,
            "twitter": self._upload_twitter,
            "linkedin": self._upload_linkedin,
            "tiktok": self._upload_tiktok,
            "instagram": self._upload_instagram,
            "pinterest": self._upload_pinterest,
        }

        handler = handlers.get(platform_lower)
        if not handler:
            raise ValueError(f"Unsupported platform: {platform}")

        return await handler(
            s3_key=s3_key,
            title=title,
            description=description,
            tags=tags or [],
            metadata=metadata or {},
        )

    async def _upload_youtube(
        self,
        s3_key: str,
        title: str,
        description: str,
        tags: list[str],
        metadata: dict[str, Any],
    ) -> dict[str, Any]:
        """Upload video to YouTube via Data API v3 (youtube.videos.insert)."""
        video_data = await self._s3.download_file(s3_key)

        async with httpx.AsyncClient(timeout=300.0) as client:
            # Step 1: Initiate resumable upload
            init_response = await client.post(
                "https://www.googleapis.com/upload/youtube/v3/videos",
                params={
                    "uploadType": "resumable",
                    "part": "snippet,status",
                    "key": self._youtube_api_key,
                },
                headers={"Content-Type": "application/json"},
                json={
                    "snippet": {
                        "title": title[:100],
                        "description": description[:5000],
                        "tags": tags[:30],
                        "categoryId": "22",
                    },
                    "status": {
                        "privacyStatus": "public",
                        "selfDeclaredMadeForKids": False,
                    },
                },
            )
            init_response.raise_for_status()
            upload_url = init_response.headers.get("Location", "")

            if not upload_url:
                raise RuntimeError("YouTube did not return resumable upload URL")

            # Step 2: Upload video bytes
            upload_response = await client.put(
                upload_url,
                content=video_data,
                headers={"Content-Type": "video/mp4"},
            )
            upload_response.raise_for_status()
            result = upload_response.json()

        post_id = result.get("id", "")
        logger.info("youtube_upload_complete", video_id=post_id)

        return {
            "platform": "youtube",
            "post_id": post_id,
            "url": f"https://www.youtube.com/watch?v={post_id}",
            "uploaded_at": datetime.now(timezone.utc).isoformat(),
        }

    async def _upload_twitter(
        self,
        s3_key: str,
        title: str,
        description: str,
        tags: list[str],
        metadata: dict[str, Any],
    ) -> dict[str, Any]:
        """Post a tweet via Twitter API v2."""
        tweet_text = title
        if tags:
            tag_text = " ".join(tags[:3])
            if len(tweet_text) + len(tag_text) + 1 <= 280:
                tweet_text += f" {tag_text}"

        if len(tweet_text) > 280:
            tweet_text = tweet_text[:277] + "..."

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.twitter.com/2/tweets",
                headers={
                    "Authorization": f"Bearer {self._twitter_bearer}",
                    "Content-Type": "application/json",
                },
                json={"text": tweet_text},
            )
            response.raise_for_status()
            result = response.json()

        post_id = result.get("data", {}).get("id", "")
        logger.info("twitter_upload_complete", tweet_id=post_id)

        return {
            "platform": "twitter",
            "post_id": post_id,
            "url": f"https://twitter.com/i/status/{post_id}",
            "uploaded_at": datetime.now(timezone.utc).isoformat(),
        }

    async def _upload_linkedin(
        self,
        s3_key: str,
        title: str,
        description: str,
        tags: list[str],
        metadata: dict[str, Any],
    ) -> dict[str, Any]:
        """Post to LinkedIn via UGC Posts API."""
        post_text = description or title
        if tags:
            post_text += "\n\n" + " ".join(tags)

        async with httpx.AsyncClient(timeout=30.0) as client:
            # Get user profile URN
            profile_resp = await client.get(
                "https://api.linkedin.com/v2/me",
                headers={"Authorization": f"Bearer {self._linkedin_token}"},
            )
            profile_resp.raise_for_status()
            profile = profile_resp.json()
            author_urn = f"urn:li:person:{profile.get('id', '')}"

            # Create UGC post
            response = await client.post(
                "https://api.linkedin.com/v2/ugcPosts",
                headers={
                    "Authorization": f"Bearer {self._linkedin_token}",
                    "Content-Type": "application/json",
                    "X-Restli-Protocol-Version": "2.0.0",
                },
                json={
                    "author": author_urn,
                    "lifecycleState": "PUBLISHED",
                    "specificContent": {
                        "com.linkedin.ugc.ShareContent": {
                            "shareCommentary": {"text": post_text[:3000]},
                            "shareMediaCategory": "NONE",
                        }
                    },
                    "visibility": {
                        "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
                    },
                },
            )
            response.raise_for_status()
            result = response.json()

        post_id = result.get("id", "")
        logger.info("linkedin_upload_complete", post_id=post_id)

        return {
            "platform": "linkedin",
            "post_id": post_id,
            "url": f"https://www.linkedin.com/feed/update/{post_id}",
            "uploaded_at": datetime.now(timezone.utc).isoformat(),
        }

    async def _upload_tiktok(
        self,
        s3_key: str,
        title: str,
        description: str,
        tags: list[str],
        metadata: dict[str, Any],
    ) -> dict[str, Any]:
        """Upload to TikTok via TikTok Content Posting API."""
        settings = get_settings()
        video_data = await self._s3.download_file(s3_key)
        presigned_url = await self._s3.generate_presigned_url(s3_key)

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                "https://open.tiktokapis.com/v2/post/publish/video/init/",
                headers={
                    "Authorization": f"Bearer {settings.TIKTOK_ACCESS_TOKEN}",
                    "Content-Type": "application/json",
                },
                json={
                    "post_info": {
                        "title": title[:150],
                        "privacy_level": "PUBLIC_TO_EVERYONE",
                        "disable_duet": False,
                        "disable_stitch": False,
                        "disable_comment": False,
                    },
                    "source_info": {
                        "source": "PULL_FROM_URL",
                        "video_url": presigned_url,
                    },
                },
            )
            response.raise_for_status()
            result = response.json()

        post_id = result.get("data", {}).get("publish_id", "")
        logger.info("tiktok_upload_complete", publish_id=post_id)

        return {
            "platform": "tiktok",
            "post_id": post_id,
            "url": "",
            "uploaded_at": datetime.now(timezone.utc).isoformat(),
        }

    async def _upload_instagram(
        self,
        s3_key: str,
        title: str,
        description: str,
        tags: list[str],
        metadata: dict[str, Any],
    ) -> dict[str, Any]:
        """Upload to Instagram via Graph API (requires Facebook Business account)."""
        presigned_url = await self._s3.generate_presigned_url(s3_key)
        caption = description or title
        if tags:
            caption += "\n\n" + " ".join(tags)

        # Instagram requires a two-step process: create container, then publish
        async with httpx.AsyncClient(timeout=120.0) as client:
            # Step 1: Create media container
            container_resp = await client.post(
                "https://graph.facebook.com/v18.0/me/media",
                params={
                    "video_url": presigned_url,
                    "caption": caption[:2200],
                    "media_type": "REELS",
                    "share_to_feed": "true",
                },
            )
            container_resp.raise_for_status()
            container_id = container_resp.json().get("id", "")

            # Step 2: Publish
            publish_resp = await client.post(
                "https://graph.facebook.com/v18.0/me/media_publish",
                params={"creation_id": container_id},
            )
            publish_resp.raise_for_status()
            result = publish_resp.json()

        post_id = result.get("id", "")
        logger.info("instagram_upload_complete", post_id=post_id)

        return {
            "platform": "instagram",
            "post_id": post_id,
            "url": "",
            "uploaded_at": datetime.now(timezone.utc).isoformat(),
        }

    async def _upload_pinterest(
        self,
        s3_key: str,
        title: str,
        description: str,
        tags: list[str],
        metadata: dict[str, Any],
    ) -> dict[str, Any]:
        """Upload pin to Pinterest using the Pinterest API v5."""
        settings = get_settings()
        pinterest_token = getattr(settings, "PINTEREST_ACCESS_TOKEN", "") or "mock"
        presigned_url = await self._s3.generate_presigned_url(s3_key)

        board_id = metadata.get("board_id", "default_board")
        link_url = metadata.get("link", "https://publishops.io")

        if pinterest_token and pinterest_token != "mock":
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    "https://api.pinterest.com/v5/pins",
                    headers={
                        "Authorization": f"Bearer {pinterest_token}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "title": title[:100],
                        "description": description[:500],
                        "link": link_url,
                        "board_id": board_id,
                        "media_source": {
                            "source_type": "video_url" if s3_key.endswith(".mp4") else "image_url",
                            "url": presigned_url,
                        }
                    },
                )
                response.raise_for_status()
                result = response.json()
                post_id = result.get("id", "")
        else:
            # Simulate successfully posted pin if no API key is set
            post_id = f"pin_{uuid.uuid4().hex[:12]}"
            logger.info("pinterest_upload_mocked", pin_id=post_id)

        return {
            "platform": "pinterest",
            "post_id": post_id,
            "url": f"https://pinterest.com/pin/{post_id}",
            "uploaded_at": datetime.now(timezone.utc).isoformat(),
        }
