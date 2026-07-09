"""Lexical analyzer service (Tier C) for profiling creator's writing style."""

from __future__ import annotations

import re
from collections import Counter
from typing import Any

# Standard filler words to track
DEFAULT_FILLER_WORDS = [
    "like", "so", "actually", "basically", "literally", 
    "just", "you know", "mean", "right", "well", "seriously",
    "honestly", "essentially", "definitely", "obviously"
]

# Standard contractions to count
CONTRACTIONS = [
    r"\b[a-zA-Z]+'t\b",  # don't, can't, won't
    r"\b[a-zA-Z]+'ve\b",  # I've, they've
    r"\b[a-zA-Z]+'re\b",  # we're, they're
    r"\b[a-zA-Z]+'d\b",   # I'd, he'd
    r"\b[a-zA-Z]+'ll\b",  # I'll, you'll
    r"\bI'm\b",
    r"\b[a-zA-Z]+'s\b",   # it's, he's
]


class LexicalAnalyzer:
    """Analyzes text/scripts to build a lexical profile of a creator's style."""

    def count_syllables(self, word: str) -> int:
        """Estimate syllable count in a word using basic linguistic rules."""
        word = word.lower().strip()
        if not word:
            return 0
        
        # Remove trailing e, es, ed if not preceding l/d/t
        word = re.sub(r"[!?.,:;\"'()]", "", word)
        if len(word) <= 3:
            return 1
            
        # Count vowel groups
        vowels = "aeiouy"
        count = 0
        prev_is_vowel = False
        for char in word:
            is_vowel = char in vowels
            if is_vowel and not prev_is_vowel:
                count += 1
            prev_is_vowel = is_vowel
            
        if word.endswith("e"):
            count -= 1
        if word.endswith("le") and len(word) > 2 and word[-3] not in vowels:
            count += 1
        if count == 0:
            count = 1
        return count

    def analyze_text(self, text: str) -> dict[str, Any]:
        """Analyze a single text or combined scripts to extract style metrics.
        
        Returns:
            A dictionary containing:
            - word_count (int)
            - sentence_count (int)
            - average_word_length (float)
            - average_sentence_length (float)
            - vocabulary_richness (float) - TTR
            - contractions_ratio (float)
            - filler_words (dict[str, int])
            - readability_score (float) - Flesch-Kincaid Reading Ease
            - sentence_length_distribution (dict[str, int])
        """
        if not text or not text.strip():
            return {
                "word_count": 0,
                "sentence_count": 0,
                "average_word_length": 0.0,
                "average_sentence_length": 0.0,
                "vocabulary_richness": 0.0,
                "contractions_ratio": 0.0,
                "filler_words": {},
                "readability_score": 100.0,
                "sentence_length_distribution": {
                    "short": 0,    # < 8 words
                    "medium": 0,   # 8-15 words
                    "long": 0,     # 16-25 words
                    "very_long": 0 # > 25 words
                }
            }

        # Tokenize sentences
        sentences = [s.strip() for s in re.split(r"[.!?]+", text) if s.strip()]
        sentence_count = max(len(sentences), 1)

        # Tokenize words
        words = re.findall(r"\b[a-zA-Z'-]+\b", text)
        word_count = len(words)
        
        if word_count == 0:
            return self.analyze_text("")

        # Readability analysis: total syllables
        total_syllables = sum(self.count_syllables(w) for w in words)

        # Average lengths
        avg_word_len = sum(len(w) for w in words) / word_count
        avg_sentence_len = word_count / sentence_count

        # Flesch-Kincaid Reading Ease: 206.835 - 1.015 * (total_words/total_sentences) - 84.6 * (total_syllables/total_words)
        flesch_reading_ease = 206.835 - (1.015 * avg_sentence_len) - (84.6 * (total_syllables / word_count))
        # Bound readability score between 0 and 100
        flesch_reading_ease = max(0.0, min(100.0, flesch_reading_ease))

        # Vocabulary richness: Type-Token Ratio (TTR)
        unique_words = set(w.lower() for w in words)
        ttr = len(unique_words) / word_count

        # Contractions count
        contraction_count = 0
        for pat in CONTRACTIONS:
            matches = re.findall(pat, text, re.IGNORECASE)
            contraction_count += len(matches)
        contractions_ratio = contraction_count / word_count

        # Filler words mapping
        filler_counts: dict[str, int] = {}
        text_lower = text.lower()
        for fw in DEFAULT_FILLER_WORDS:
            # Match word boundary, or phrase
            pattern = rf"\b{re.escape(fw)}\b"
            matches = re.findall(pattern, text_lower)
            if len(matches) > 0:
                filler_counts[fw] = len(matches)

        # Sentence length distribution
        sent_lengths = [len(re.findall(r"\b[a-zA-Z'-]+\b", s)) for s in sentences]
        distribution = {"short": 0, "medium": 0, "long": 0, "very_long": 0}
        for sl in sent_lengths:
            if sl < 8:
                distribution["short"] += 1
            elif sl <= 15:
                distribution["medium"] += 1
            elif sl <= 25:
                distribution["long"] += 1
            else:
                distribution["very_long"] += 1

        # Normalize sentence distribution as percentages if we have sentences
        total_sents = sum(distribution.values())
        if total_sents > 0:
            for k in distribution:
                distribution[k] = round((distribution[k] / total_sents) * 100, 1)

        return {
            "word_count": word_count,
            "sentence_count": sentence_count,
            "average_word_length": round(avg_word_len, 2),
            "average_sentence_length": round(avg_sentence_len, 2),
            "vocabulary_richness": round(ttr, 4),
            "contractions_ratio": round(contractions_ratio, 4),
            "filler_words": filler_counts,
            "readability_score": round(flesch_reading_ease, 2),
            "sentence_length_distribution": distribution
        }

    def analyze_multiple(self, texts: list[str]) -> dict[str, Any]:
        """Aggregate analysis over a list of historical scripts/posts."""
        combined_text = "\n\n".join(texts)
        analysis = self.analyze_text(combined_text)
        
        # Calculate per-document variance/averages if needed
        # (for now, the combined metrics are sufficient representation)
        return {
            **analysis,
            "document_count": len(texts)
        }
