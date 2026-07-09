"""Cross-Platform Synergy Router service (Tier D) to map the content funnel and add UTM tracking."""

from __future__ import annotations

import urllib.parse
from typing import Any


class SynergyRouter:
    """Manages cross-platform audience migration through optimized CTA routing and UTM links."""

    def build_utm_link(self, destination_url: str, platform: str, campaign: str = "publishops_synergy") -> str:
        """Append UTM parameters to a destination link for accurate analytics tracking."""
        parsed = urllib.parse.urlparse(destination_url)
        params = urllib.parse.parse_qs(parsed.query)
        
        # Add UTM parameters
        params["utm_source"] = [platform.lower()]
        params["utm_medium"] = ["social"]
        params["utm_campaign"] = [campaign]
        
        # Reconstruct query string
        query_str = urllib.parse.urlencode(params, doseq=True)
        reconstructed = urllib.parse.ParseResult(
            scheme=parsed.scheme,
            netloc=parsed.netloc,
            path=parsed.path,
            params=parsed.params,
            query=query_str,
            fragment=parsed.fragment
        )
        return urllib.parse.urlunparse(reconstructed)

    def route_cta_by_platform(self, platform: str, destination_url: str, base_cta_text: str = "") -> str:
        """Generate platform-native call-to-actions to maximize conversion rate."""
        platform_lower = platform.lower()
        tracked_link = self.build_utm_link(destination_url, platform_lower)

        if platform_lower == "youtube":
            return f"{base_cta_text or 'For the full breakdown, click the link in the description below:'} {tracked_link}"
            
        elif platform_lower == "tiktok":
            # TikTok captions do not support clickable links
            return f"{base_cta_text or 'Check out the details in my bio link!'} 👉 [Link In Bio]"
            
        elif platform_lower == "instagram":
            # Instagram captions don't support links; recommend comment trigger funnel (e.g. ManyChat style)
            return f"{base_cta_text or 'Comment WORKFLOW below and I will DM you the step-by-step guide link!'}"
            
        elif platform_lower == "twitter" or platform_lower == "linkedin":
            # Direct clickable links work well here
            return f"{base_cta_text or 'Read the full guide here:'} {tracked_link}"
            
        elif platform_lower == "pinterest":
            # Pinterest links are attached to the Pin itself rather than description text
            return f"{base_cta_text or 'Click the Pin link to read more.'}"

        return f"{base_cta_text} {tracked_link}"
