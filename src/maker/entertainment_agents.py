"""
Entertainment Discovery Microagents

Specialized microagents for solving the "45-minute content decision problem".
Each agent handles one atomic task in the content discovery pipeline.
"""

import asyncio
import json
import re
from abc import abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional
from enum import Enum

from .core import Microagent, Step, TaskDecomposer, RedFlagCriteria


class ContentType(Enum):
    """Types of entertainment content."""
    MOVIE = "movie"
    TV_SHOW = "tv_show"
    DOCUMENTARY = "documentary"
    ANIME = "anime"
    SPORTS = "sports"
    NEWS = "news"
    PODCAST = "podcast"
    MUSIC = "music"


class MoodCategory(Enum):
    """User mood categories for content matching."""
    RELAXED = "relaxed"
    EXCITED = "excited"
    THOUGHTFUL = "thoughtful"
    NOSTALGIC = "nostalgic"
    ADVENTUROUS = "adventurous"
    ROMANTIC = "romantic"
    SOCIAL = "social"
    FOCUSED = "focused"


@dataclass
class UserPreferences:
    """User preferences for content discovery."""
    preferred_genres: list[str] = field(default_factory=list)
    disliked_genres: list[str] = field(default_factory=list)
    preferred_content_types: list[ContentType] = field(default_factory=list)
    max_duration_minutes: Optional[int] = None
    language_preferences: list[str] = field(default_factory=lambda: ["en"])
    maturity_rating: str = "PG-13"
    current_mood: Optional[MoodCategory] = None
    watch_history: list[str] = field(default_factory=list)
    available_platforms: list[str] = field(default_factory=list)


@dataclass
class ContentItem:
    """Represents a piece of entertainment content."""
    content_id: str
    title: str
    content_type: ContentType
    genres: list[str]
    duration_minutes: int
    release_year: int
    rating: float
    platform: str
    description: str = ""
    mood_tags: list[MoodCategory] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


@dataclass
class RecommendationResult:
    """Result from a recommendation microagent."""
    content_id: str
    score: float
    reasoning: str
    confidence: float
    factors: dict[str, float] = field(default_factory=dict)


# ============================================================================
# Microagent Implementations
# ============================================================================


class MoodAnalyzerAgent(Microagent[MoodCategory]):
    """
    Microagent for analyzing user's current mood from context.

    Atomic task: Given user input, determine their mood category.
    """

    def __init__(self, llm_client: Any = None):
        super().__init__(agent_id="mood_analyzer", temperature=0.1)
        self.llm_client = llm_client

    async def execute(self, context: dict[str, Any]) -> MoodCategory:
        """Analyze mood from user input."""
        self.call_count += 1

        user_input = context.get("user_input", "")
        time_of_day = context.get("time_of_day", "evening")
        day_of_week = context.get("day_of_week", "saturday")

        # Mood inference logic (would use LLM in production)
        mood_signals = {
            MoodCategory.RELAXED: ["relax", "chill", "unwind", "calm", "peaceful"],
            MoodCategory.EXCITED: ["exciting", "action", "thrill", "adventure", "fun"],
            MoodCategory.THOUGHTFUL: ["think", "deep", "meaningful", "documentary", "learn"],
            MoodCategory.NOSTALGIC: ["classic", "remember", "old", "childhood", "retro"],
            MoodCategory.ADVENTUROUS: ["new", "discover", "different", "explore", "foreign"],
            MoodCategory.ROMANTIC: ["love", "romance", "date", "couple", "heart"],
            MoodCategory.SOCIAL: ["friends", "family", "group", "party", "together"],
            MoodCategory.FOCUSED: ["work", "background", "concentrate", "quiet"],
        }

        user_lower = user_input.lower()
        scores = {}

        for mood, signals in mood_signals.items():
            score = sum(1 for signal in signals if signal in user_lower)
            # Boost based on time/day
            if mood == MoodCategory.RELAXED and time_of_day == "evening":
                score += 0.5
            if mood == MoodCategory.SOCIAL and day_of_week in ["friday", "saturday"]:
                score += 0.5
            scores[mood] = score

        # Return highest scoring mood, default to RELAXED
        best_mood = max(scores, key=scores.get)
        return best_mood if scores[best_mood] > 0 else MoodCategory.RELAXED

    def validate_output(self, output: MoodCategory) -> bool:
        return isinstance(output, MoodCategory)


class GenreMatcherAgent(Microagent[list[str]]):
    """
    Microagent for matching content genres to user preferences.

    Atomic task: Given mood and preferences, return prioritized genre list.
    """

    # Mood to genre mappings
    MOOD_GENRE_MAP = {
        MoodCategory.RELAXED: ["comedy", "romance", "slice-of-life", "animation"],
        MoodCategory.EXCITED: ["action", "thriller", "adventure", "sci-fi"],
        MoodCategory.THOUGHTFUL: ["drama", "documentary", "mystery", "biography"],
        MoodCategory.NOSTALGIC: ["classic", "retro", "family", "musical"],
        MoodCategory.ADVENTUROUS: ["foreign", "indie", "experimental", "cult"],
        MoodCategory.ROMANTIC: ["romance", "drama", "musical", "comedy"],
        MoodCategory.SOCIAL: ["comedy", "horror", "action", "game-show"],
        MoodCategory.FOCUSED: ["documentary", "ambient", "nature", "music"],
    }

    def __init__(self, llm_client: Any = None):
        super().__init__(agent_id="genre_matcher", temperature=0.1)
        self.llm_client = llm_client

    async def execute(self, context: dict[str, Any]) -> list[str]:
        """Match genres based on mood and preferences."""
        self.call_count += 1

        mood = context.get("mood", MoodCategory.RELAXED)
        preferences = context.get("preferences", UserPreferences())

        # Get mood-based genres
        mood_genres = self.MOOD_GENRE_MAP.get(mood, ["drama", "comedy"])

        # Combine with user preferences
        preferred = preferences.preferred_genres if isinstance(preferences, UserPreferences) else []
        disliked = preferences.disliked_genres if isinstance(preferences, UserPreferences) else []

        # Build prioritized list
        result = []

        # Add user preferences first (highest priority)
        for genre in preferred:
            if genre not in result and genre not in disliked:
                result.append(genre)

        # Add mood-matched genres
        for genre in mood_genres:
            if genre not in result and genre not in disliked:
                result.append(genre)

        return result[:10]  # Limit to top 10 genres

    def validate_output(self, output: list[str]) -> bool:
        return isinstance(output, list) and all(isinstance(g, str) for g in output)


class DurationFilterAgent(Microagent[tuple[int, int]]):
    """
    Microagent for determining appropriate content duration.

    Atomic task: Given context, return (min_duration, max_duration) in minutes.
    """

    def __init__(self, llm_client: Any = None):
        super().__init__(agent_id="duration_filter", temperature=0.1)
        self.llm_client = llm_client

    async def execute(self, context: dict[str, Any]) -> tuple[int, int]:
        """Determine appropriate duration range."""
        self.call_count += 1

        time_available = context.get("time_available_minutes")
        content_type = context.get("content_type")
        mood = context.get("mood", MoodCategory.RELAXED)

        # Default ranges by content type
        type_ranges = {
            ContentType.MOVIE: (80, 180),
            ContentType.TV_SHOW: (20, 60),
            ContentType.DOCUMENTARY: (45, 120),
            ContentType.ANIME: (20, 25),
            ContentType.SPORTS: (60, 180),
            ContentType.PODCAST: (30, 90),
        }

        if time_available:
            # Respect user's time constraint
            max_duration = time_available
            min_duration = max(15, time_available // 4)
            return (min_duration, max_duration)

        if content_type and content_type in type_ranges:
            return type_ranges[content_type]

        # Default based on mood
        if mood in [MoodCategory.FOCUSED, MoodCategory.RELAXED]:
            return (20, 60)  # Shorter content
        elif mood == MoodCategory.THOUGHTFUL:
            return (60, 150)  # Longer, deeper content
        else:
            return (30, 120)  # Medium range

    def validate_output(self, output: tuple[int, int]) -> bool:
        return (
            isinstance(output, tuple) and
            len(output) == 2 and
            all(isinstance(x, int) for x in output) and
            output[0] <= output[1]
        )


class ContentScorerAgent(Microagent[RecommendationResult]):
    """
    Microagent for scoring individual content items.

    Atomic task: Given one content item and context, return a score.
    """

    def __init__(self, llm_client: Any = None):
        super().__init__(agent_id="content_scorer", temperature=0.1)
        self.llm_client = llm_client

    async def execute(self, context: dict[str, Any]) -> RecommendationResult:
        """Score a single content item."""
        self.call_count += 1

        content = context.get("content")
        preferences = context.get("preferences", UserPreferences())
        matched_genres = context.get("matched_genres", [])
        mood = context.get("mood", MoodCategory.RELAXED)
        duration_range = context.get("duration_range", (0, 999))

        if not content:
            raise ValueError("No content provided for scoring")

        factors = {}

        # Genre match score (0-1)
        if hasattr(content, 'genres'):
            matching_genres = len(set(content.genres) & set(matched_genres))
            factors["genre_match"] = min(1.0, matching_genres / max(1, len(matched_genres)))
        else:
            factors["genre_match"] = 0.5

        # Rating score (0-1)
        if hasattr(content, 'rating'):
            factors["rating"] = content.rating / 10.0
        else:
            factors["rating"] = 0.5

        # Duration fit score (0-1)
        if hasattr(content, 'duration_minutes'):
            min_dur, max_dur = duration_range
            if min_dur <= content.duration_minutes <= max_dur:
                factors["duration_fit"] = 1.0
            else:
                # Penalize based on how far out of range
                if content.duration_minutes < min_dur:
                    factors["duration_fit"] = content.duration_minutes / min_dur
                else:
                    factors["duration_fit"] = max_dur / content.duration_minutes
        else:
            factors["duration_fit"] = 0.5

        # Recency boost for newer content
        if hasattr(content, 'release_year'):
            years_old = 2025 - content.release_year
            factors["recency"] = max(0.3, 1.0 - (years_old * 0.02))
        else:
            factors["recency"] = 0.5

        # Platform availability
        if hasattr(preferences, 'available_platforms') and hasattr(content, 'platform'):
            if content.platform in preferences.available_platforms:
                factors["availability"] = 1.0
            else:
                factors["availability"] = 0.3
        else:
            factors["availability"] = 0.7

        # Watch history penalty (avoid rewatches)
        if hasattr(preferences, 'watch_history') and hasattr(content, 'content_id'):
            if content.content_id in preferences.watch_history:
                factors["novelty"] = 0.1
            else:
                factors["novelty"] = 1.0
        else:
            factors["novelty"] = 1.0

        # Calculate weighted score
        weights = {
            "genre_match": 0.30,
            "rating": 0.20,
            "duration_fit": 0.15,
            "recency": 0.10,
            "availability": 0.15,
            "novelty": 0.10,
        }

        total_score = sum(factors[k] * weights[k] for k in factors)
        confidence = min(factors.values())  # Confidence based on weakest factor

        # Generate reasoning
        top_factors = sorted(factors.items(), key=lambda x: x[1], reverse=True)[:3]
        reasoning = f"Strong on: {', '.join(f[0] for f in top_factors)}"

        return RecommendationResult(
            content_id=content.content_id if hasattr(content, 'content_id') else "unknown",
            score=total_score,
            reasoning=reasoning,
            confidence=confidence,
            factors=factors
        )

    def validate_output(self, output: RecommendationResult) -> bool:
        return (
            isinstance(output, RecommendationResult) and
            0 <= output.score <= 1 and
            0 <= output.confidence <= 1
        )


class ContentRankerAgent(Microagent[list[str]]):
    """
    Microagent for ranking scored content items.

    Atomic task: Given scored items, return ordered list of content IDs.
    """

    def __init__(self, llm_client: Any = None, top_k: int = 10):
        super().__init__(agent_id="content_ranker", temperature=0.1)
        self.llm_client = llm_client
        self.top_k = top_k

    async def execute(self, context: dict[str, Any]) -> list[str]:
        """Rank content items by score."""
        self.call_count += 1

        scored_items: list[RecommendationResult] = context.get("scored_items", [])

        if not scored_items:
            return []

        # Sort by score (descending), then by confidence (descending)
        sorted_items = sorted(
            scored_items,
            key=lambda x: (x.score, x.confidence),
            reverse=True
        )

        # Return top K content IDs
        return [item.content_id for item in sorted_items[:self.top_k]]

    def validate_output(self, output: list[str]) -> bool:
        return isinstance(output, list) and all(isinstance(x, str) for x in output)


class ExplanationGeneratorAgent(Microagent[str]):
    """
    Microagent for generating human-readable recommendation explanations.

    Atomic task: Given a recommendation, explain why it was chosen.
    """

    def __init__(self, llm_client: Any = None):
        super().__init__(agent_id="explanation_generator", temperature=0.3)
        self.llm_client = llm_client

    async def execute(self, context: dict[str, Any]) -> str:
        """Generate explanation for a recommendation."""
        self.call_count += 1

        content = context.get("content")
        score_result = context.get("score_result")
        mood = context.get("mood")
        user_input = context.get("user_input", "")

        if not content or not score_result:
            return "Recommended based on your preferences."

        # Build explanation based on top factors
        factors = score_result.factors
        explanations = []

        if factors.get("genre_match", 0) > 0.7:
            explanations.append(f"matches your preferred genres")

        if factors.get("rating", 0) > 0.8:
            explanations.append(f"highly rated ({content.rating}/10)")

        if factors.get("duration_fit", 0) > 0.9:
            explanations.append(f"fits your available time")

        if factors.get("recency", 0) > 0.8:
            explanations.append(f"recently released")

        if mood:
            mood_name = mood.value if hasattr(mood, 'value') else str(mood)
            explanations.append(f"perfect for a {mood_name} mood")

        if explanations:
            return f"This {content.content_type.value if hasattr(content, 'content_type') else 'content'} " + \
                   ", ".join(explanations[:3]) + "."
        else:
            return "Recommended based on your viewing history and preferences."

    def validate_output(self, output: str) -> bool:
        return isinstance(output, str) and len(output) > 10


# ============================================================================
# Task Decomposition for Entertainment Discovery
# ============================================================================


class EntertainmentDiscoveryDecomposer(TaskDecomposer):
    """
    Decomposes entertainment discovery queries into atomic steps.

    Follows MAKER's Maximal Agentic Decomposition (MAD) principle:
    each step is minimal and focused on a single decision.
    """

    def decompose(self, task: dict[str, Any]) -> list[Step]:
        """
        Decompose a content discovery request into atomic steps.

        Standard pipeline:
        1. Analyze user mood
        2. Match genres to mood/preferences
        3. Determine duration constraints
        4. Score each candidate content
        5. Rank scored content
        6. Generate explanations for top picks
        """
        user_input = task.get("user_input", "")
        preferences = task.get("preferences", UserPreferences())
        candidate_content = task.get("candidates", [])
        top_k = task.get("top_k", 5)

        steps = []

        # Step 1: Mood Analysis
        steps.append(Step(
            step_id=1,
            description="Analyze user mood from input",
            context={
                "user_input": user_input,
                "time_of_day": task.get("time_of_day", "evening"),
                "day_of_week": task.get("day_of_week", "saturday"),
            },
            dependencies=[]
        ))

        # Step 2: Genre Matching
        steps.append(Step(
            step_id=2,
            description="Match genres to mood and preferences",
            context={
                "preferences": preferences,
            },
            dependencies=[1]  # Needs mood from step 1
        ))

        # Step 3: Duration Filtering
        steps.append(Step(
            step_id=3,
            description="Determine duration constraints",
            context={
                "time_available_minutes": task.get("time_available"),
                "content_type": task.get("content_type"),
            },
            dependencies=[1]  # Needs mood from step 1
        ))

        # Steps 4.x: Score each content item (parallel-ready)
        for i, content in enumerate(candidate_content):
            steps.append(Step(
                step_id=100 + i,  # 100+ for content scoring
                description=f"Score content: {content.title if hasattr(content, 'title') else i}",
                context={
                    "content": content,
                    "preferences": preferences,
                },
                dependencies=[2, 3]  # Needs genres and duration from steps 2, 3
            ))

        # Step 5: Rank all scored content
        scoring_step_ids = [100 + i for i in range(len(candidate_content))]
        steps.append(Step(
            step_id=200,
            description="Rank scored content items",
            context={
                "top_k": top_k,
            },
            dependencies=scoring_step_ids
        ))

        # Steps 6.x: Generate explanations for top picks
        for i in range(min(top_k, len(candidate_content))):
            steps.append(Step(
                step_id=300 + i,
                description=f"Generate explanation for recommendation {i+1}",
                context={
                    "user_input": user_input,
                },
                dependencies=[200, 100 + i]  # Needs ranking and individual score
            ))

        return steps

    def compose_result(self, steps: list[Step]) -> dict[str, Any]:
        """Compose final recommendation result from completed steps."""
        result = {
            "mood": None,
            "matched_genres": [],
            "duration_range": None,
            "recommendations": [],
            "explanations": {},
            "stats": {
                "total_steps": len(steps),
                "completed_steps": sum(1 for s in steps if s.status == "completed"),
                "failed_steps": sum(1 for s in steps if s.status == "failed"),
            }
        }

        for step in steps:
            if step.status != "completed":
                continue

            if step.step_id == 1:
                result["mood"] = step.result
            elif step.step_id == 2:
                result["matched_genres"] = step.result
            elif step.step_id == 3:
                result["duration_range"] = step.result
            elif step.step_id == 200:
                result["recommendations"] = step.result
            elif step.step_id >= 300:
                # Explanation step
                idx = step.step_id - 300
                if idx < len(result["recommendations"]):
                    content_id = result["recommendations"][idx]
                    result["explanations"][content_id] = step.result

        return result


# Red-flag criteria specific to entertainment discovery
ENTERTAINMENT_RED_FLAG_CRITERIA = RedFlagCriteria(
    max_response_tokens=500,
    max_response_length=2000,
    required_fields=[],
    forbidden_patterns=[
        "i don't know",
        "i cannot",
        "error",
        "exception",
    ],
    min_confidence=0.2
)
