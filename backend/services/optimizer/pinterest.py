"""Pinterest optimizer service (Tier D) for SEO-optimized pins and formatting."""

from __future__ import annotations

import re
from typing import Any


class PinterestOptimizer:
    """Formats scripts and metadata into Pinterest-optimized Pins."""

    def optimize_pin(self, topic_title: str, script_body: str, landing_page_url: str = "") -> dict[str, Any]:
        """Convert a core topic and script body into a search-optimized Pinterest Pin structure.
        
        Args:
            topic_title: The core topic title.
            script_body: The generated text body.
            landing_page_url: Target URL for the Pin.
            
        Returns:
            A dictionary of Pin properties.
        """
        # 1. Clean and truncate title for Pinterest limits (max 100 chars)
        clean_title = re.sub(r"[#*`]", "", topic_title).strip()
        # Prepend SEO action keywords
        pin_title = f"How to: {clean_title}" if not clean_title.lower().startswith("how to") else clean_title
        if len(pin_title) > 100:
            pin_title = pin_title[:97] + "..."

        # 2. Build description (max 500 chars)
        # Pull first 2-3 sentences of script body
        sentences = [s.strip() for s in re.split(r"[.!?]", script_body) if s.strip()]
        desc_sentences = []
        char_count = 0
        
        for sent in sentences:
            if char_count + len(sent) + 5 > 420:  # leave room for link and tags
                break
            desc_sentences.append(sent)
            char_count += len(sent) + 1

        description_text = ". ".join(desc_sentences) + "."
        
        # Add high affinity Pinterest tags based on keywords
        tags = ["#tech", "#software", "#productivity", "#tutorial", "#developer"]
        if "ai" in script_body.lower() or "artificial" in script_body.lower():
            tags.insert(0, "#ai")
            tags.insert(1, "#artificialintelligence")
            
        description_text += " " + " ".join(tags[:4])
        if len(description_text) > 500:
            description_text = description_text[:497] + "..."

        # 3. Dynamic Board Selection based on topic
        topic_lower = topic_title.lower()
        if any(w in topic_lower for w in ["deploy", "cloud", "aws", "docker"]):
            board = "DevOps & Cloud Engineering"
        elif any(w in topic_lower for w in ["ai", "prompt", "agent", "llm"]):
            board = "AI Workflows & Agents"
        elif any(w in topic_lower for w in ["code", "python", "javascript", "program"]):
            board = "Software Development Tutorials"
        else:
            board = "Tech Innovations"

        return {
            "title": pin_title,
            "description": description_text,
            "board_name": board,
            "link": landing_page_url or "https://publishops.io/blog",
            "media_type": "image" if len(script_body) < 300 else "video"
        }
