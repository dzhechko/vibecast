"""
MAKER API for Vibecast Entertainment Discovery

High-level API for integrating MAKER-based recommendations
into the vibecast platform.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Optional

from .core import (
    MAKEROrchestrator,
    RedFlagCriteria,
    Step,
)
from .entertainment_agents import (
    ContentType,
    MoodCategory,
    UserPreferences,
    ContentItem,
    RecommendationResult,
    MoodAnalyzerAgent,
    GenreMatcherAgent,
    DurationFilterAgent,
    ContentScorerAgent,
    ContentRankerAgent,
    ExplanationGeneratorAgent,
    EntertainmentDiscoveryDecomposer,
    ENTERTAINMENT_RED_FLAG_CRITERIA,
)
from .config import MAKERConfig, PRODUCTION_CONFIG
from .benchmark import MAKERBenchmark, VotingOptimizer, PerformanceProfiler
from .llm_client import create_llm_client, BaseLLMClient

logger = logging.getLogger(__name__)


@dataclass
class DiscoveryRequest:
    """Request for content discovery."""
    user_input: str
    preferences: UserPreferences = field(default_factory=UserPreferences)
    candidates: list[ContentItem] = field(default_factory=list)
    top_k: int = 5
    time_available_minutes: Optional[int] = None
    content_type: Optional[ContentType] = None
    context: dict = field(default_factory=dict)


@dataclass
class DiscoveryResponse:
    """Response from content discovery."""
    recommendations: list[str]  # Content IDs
    explanations: dict[str, str]  # Content ID -> explanation
    mood: Optional[MoodCategory] = None
    matched_genres: list[str] = field(default_factory=list)
    duration_range: Optional[tuple[int, int]] = None
    stats: dict = field(default_factory=dict)
    success: bool = True
    error: Optional[str] = None


class VibecastMAKER:
    """
    Main MAKER-powered recommendation engine for Vibecast.

    Implements the entertainment discovery pipeline using:
    - Microagent architecture for atomic tasks
    - First-to-ahead-by-k voting for reliability
    - Red-flagging for quality control
    """

    def __init__(
        self,
        config: Optional[MAKERConfig] = None,
        llm_client: Optional[BaseLLMClient] = None
    ):
        """
        Initialize Vibecast MAKER engine.

        Args:
            config: MAKER configuration (defaults to production settings)
            llm_client: LLM client (created from config if not provided)
        """
        self.config = config or PRODUCTION_CONFIG
        self.llm_client = llm_client or create_llm_client(self.config.llm)

        # Initialize decomposer
        self.decomposer = EntertainmentDiscoveryDecomposer()

        # Initialize orchestrator
        self.orchestrator = MAKEROrchestrator(
            decomposer=self.decomposer,
            voting_k=self.config.voting.k,
            max_voting_rounds=self.config.voting.max_rounds,
            red_flag_criteria=ENTERTAINMENT_RED_FLAG_CRITERIA
        )

        # Register agents
        self._register_agents()

        # Initialize profiler
        self.profiler = PerformanceProfiler()

        # Benchmark and optimizer
        self.benchmark = MAKERBenchmark(self.orchestrator, self.config.benchmark.cost_per_vote)
        self.optimizer = VotingOptimizer(self.config.benchmark.target_success_rate)

    def _register_agents(self):
        """Register all microagents with the orchestrator."""
        agents = [
            MoodAnalyzerAgent(self.llm_client),
            GenreMatcherAgent(self.llm_client),
            DurationFilterAgent(self.llm_client),
            ContentScorerAgent(self.llm_client),
            ContentRankerAgent(self.llm_client),
            ExplanationGeneratorAgent(self.llm_client),
        ]

        for agent in agents:
            self.orchestrator.register_agent(agent)

    async def discover(self, request: DiscoveryRequest) -> DiscoveryResponse:
        """
        Discover content recommendations using MAKER methodology.

        Args:
            request: Discovery request with user input and preferences

        Returns:
            Discovery response with recommendations and explanations
        """
        try:
            # Build task from request
            task = {
                "user_input": request.user_input,
                "preferences": request.preferences,
                "candidates": request.candidates,
                "top_k": request.top_k,
                "time_available": request.time_available_minutes,
                "content_type": request.content_type,
                **request.context
            }

            # Select appropriate agent based on step
            def agent_selector(step: Step) -> str:
                if step.step_id == 1:
                    return "mood_analyzer"
                elif step.step_id == 2:
                    return "genre_matcher"
                elif step.step_id == 3:
                    return "duration_filter"
                elif 100 <= step.step_id < 200:
                    return "content_scorer"
                elif step.step_id == 200:
                    return "content_ranker"
                elif step.step_id >= 300:
                    return "explanation_generator"
                return "mood_analyzer"  # Default

            # Execute task
            result = await self.orchestrator.execute_task(task, agent_selector)

            # Extract response
            composed = result.get("result", {})

            return DiscoveryResponse(
                recommendations=composed.get("recommendations", []),
                explanations=composed.get("explanations", {}),
                mood=composed.get("mood"),
                matched_genres=composed.get("matched_genres", []),
                duration_range=composed.get("duration_range"),
                stats=result.get("stats", {}),
                success=True
            )

        except Exception as e:
            logger.error(f"Discovery error: {e}")
            return DiscoveryResponse(
                recommendations=[],
                explanations={},
                success=False,
                error=str(e)
            )

    async def quick_recommend(
        self,
        query: str,
        candidates: list[ContentItem],
        top_k: int = 5
    ) -> list[str]:
        """
        Quick recommendation without full pipeline.

        Args:
            query: User query
            candidates: Content to rank
            top_k: Number of recommendations

        Returns:
            List of recommended content IDs
        """
        request = DiscoveryRequest(
            user_input=query,
            candidates=candidates,
            top_k=top_k
        )

        response = await self.discover(request)
        return response.recommendations

    def get_optimization_recommendations(
        self,
        per_step_accuracy: float = 0.95,
        expected_steps: int = 100
    ) -> dict[str, Any]:
        """
        Get optimization recommendations for current setup.

        Args:
            per_step_accuracy: Measured per-step accuracy
            expected_steps: Expected steps per task

        Returns:
            Optimization recommendations
        """
        optimal_k = self.optimizer.calculate_optimal_k(
            per_step_accuracy,
            expected_steps
        )

        cost_estimate = self.optimizer.estimate_cost(
            optimal_k,
            per_step_accuracy,
            expected_steps,
            self.config.benchmark.cost_per_vote
        )

        return {
            "current_k": self.config.voting.k,
            "recommended_k": optimal_k,
            "per_step_accuracy": per_step_accuracy,
            "expected_steps": expected_steps,
            "cost_estimate": cost_estimate,
            "recommendation": (
                f"With {per_step_accuracy:.1%} accuracy and {expected_steps} steps, "
                f"k={optimal_k} is optimal. "
                f"Expected cost: ${cost_estimate['expected_cost']:.4f}"
            )
        }

    def get_stats(self) -> dict[str, Any]:
        """Get comprehensive statistics."""
        return {
            "orchestrator": self.orchestrator.execution_stats,
            "llm_client": self.llm_client.get_stats(),
            "profiler": self.profiler.get_summary(),
            "config": self.config.to_dict()
        }


# Convenience function for simple usage
async def recommend(
    query: str,
    candidates: list[dict],
    preferences: Optional[dict] = None,
    config: Optional[MAKERConfig] = None
) -> DiscoveryResponse:
    """
    Simple recommendation function.

    Args:
        query: User's content request
        candidates: List of content dicts with required fields
        preferences: Optional user preferences
        config: Optional MAKER config

    Returns:
        Discovery response with recommendations
    """
    # Convert candidate dicts to ContentItem objects
    content_items = []
    for c in candidates:
        try:
            content_items.append(ContentItem(
                content_id=c.get("id", c.get("content_id", "")),
                title=c.get("title", ""),
                content_type=ContentType(c.get("type", "movie")),
                genres=c.get("genres", []),
                duration_minutes=c.get("duration", 120),
                release_year=c.get("year", 2024),
                rating=c.get("rating", 7.0),
                platform=c.get("platform", "unknown"),
                description=c.get("description", ""),
            ))
        except (ValueError, KeyError) as e:
            logger.warning(f"Skipping invalid content: {e}")

    # Create preferences
    user_prefs = UserPreferences()
    if preferences:
        user_prefs.preferred_genres = preferences.get("genres", [])
        user_prefs.available_platforms = preferences.get("platforms", [])
        if preferences.get("max_duration"):
            user_prefs.max_duration_minutes = preferences["max_duration"]

    # Create request
    request = DiscoveryRequest(
        user_input=query,
        preferences=user_prefs,
        candidates=content_items
    )

    # Get recommendations
    engine = VibecastMAKER(config)
    return await engine.discover(request)


# Example usage and testing
if __name__ == "__main__":
    async def main():
        # Sample content
        sample_content = [
            {
                "id": "movie1",
                "title": "The Adventure Begins",
                "type": "movie",
                "genres": ["action", "adventure"],
                "duration": 120,
                "year": 2024,
                "rating": 8.5,
                "platform": "netflix",
            },
            {
                "id": "movie2",
                "title": "Quiet Evening",
                "type": "movie",
                "genres": ["drama", "romance"],
                "duration": 95,
                "year": 2023,
                "rating": 7.8,
                "platform": "hulu",
            },
            {
                "id": "show1",
                "title": "Comedy Hour",
                "type": "tv_show",
                "genres": ["comedy"],
                "duration": 30,
                "year": 2024,
                "rating": 8.0,
                "platform": "netflix",
            },
        ]

        # Get recommendations
        response = await recommend(
            query="I want something relaxing to watch tonight",
            candidates=sample_content,
            preferences={"platforms": ["netflix", "hulu"]}
        )

        print(f"Recommendations: {response.recommendations}")
        print(f"Mood detected: {response.mood}")
        print(f"Stats: {response.stats}")

    asyncio.run(main())
