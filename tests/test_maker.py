"""
Tests for MAKER Framework

Tests the core functionality, voting algorithm, and entertainment agents.
"""

import asyncio
import pytest
from typing import Any

import sys
sys.path.insert(0, '/home/user/vibecast/src')

from maker.core import (
    Vote,
    VoteStatus,
    VotingResult,
    RedFlagCriteria,
    FirstToAheadByKVoting,
    Step,
)
from maker.entertainment_agents import (
    ContentType,
    MoodCategory,
    UserPreferences,
    ContentItem,
    MoodAnalyzerAgent,
    GenreMatcherAgent,
    DurationFilterAgent,
    ContentScorerAgent,
    EntertainmentDiscoveryDecomposer,
)
from maker.config import MAKERConfig, DEVELOPMENT_CONFIG
from maker.benchmark import VotingOptimizer


class TestRedFlagCriteria:
    """Tests for red-flagging system."""

    def test_valid_response(self):
        """Test that valid responses pass."""
        criteria = RedFlagCriteria(
            max_response_length=1000,
            required_fields=["action"],
            forbidden_patterns=["error"]
        )

        response = {"action": "recommend", "content": "Movie A"}
        flags = criteria.check(response)

        assert len(flags) == 0

    def test_long_response_flagged(self):
        """Test that long responses are flagged."""
        criteria = RedFlagCriteria(max_response_length=100)

        long_response = "x" * 200
        flags = criteria.check(long_response)

        assert any("response_too_long" in f for f in flags)

    def test_missing_field_flagged(self):
        """Test that missing required fields are flagged."""
        criteria = RedFlagCriteria(required_fields=["action", "result"])

        response = {"action": "recommend"}  # Missing "result"
        flags = criteria.check(response)

        assert any("missing_field:result" in f for f in flags)

    def test_forbidden_pattern_flagged(self):
        """Test that forbidden patterns are flagged."""
        criteria = RedFlagCriteria(forbidden_patterns=["i don't know", "error"])

        response = "I don't know what to recommend"
        flags = criteria.check(response)

        assert any("forbidden_pattern" in f for f in flags)


class TestFirstToAheadByKVoting:
    """Tests for voting algorithm."""

    @pytest.mark.asyncio
    async def test_unanimous_vote(self):
        """Test voting with unanimous agreement."""
        voting = FirstToAheadByKVoting(k=3)

        # All votes return same value
        async def vote_fn():
            return "movie_a"

        result = await voting.run_voting(vote_fn)

        assert result.status == VoteStatus.DECIDED
        assert result.winner == "movie_a"
        assert result.winning_margin >= 3

    @pytest.mark.asyncio
    async def test_mixed_votes_converge(self):
        """Test that mixed votes eventually converge."""
        voting = FirstToAheadByKVoting(k=2, max_rounds=50)

        counter = {"count": 0}

        async def vote_fn():
            counter["count"] += 1
            # 70% vote for A, 30% for B
            return "A" if counter["count"] % 10 < 7 else "B"

        result = await voting.run_voting(vote_fn)

        assert result.status in [VoteStatus.DECIDED, VoteStatus.TIMEOUT]
        if result.status == VoteStatus.DECIDED:
            assert result.winner == "A"

    @pytest.mark.asyncio
    async def test_red_flagged_votes_filtered(self):
        """Test that red-flagged votes are filtered."""
        criteria = RedFlagCriteria(max_response_length=10)
        voting = FirstToAheadByKVoting(k=2, red_flag_criteria=criteria)

        counter = {"count": 0}

        async def vote_fn():
            counter["count"] += 1
            if counter["count"] % 2 == 0:
                return "x" * 100  # Will be flagged
            return "valid"

        result = await voting.run_voting(vote_fn)

        # Should still converge on valid responses
        assert result.winner == "valid"


class TestMoodAnalyzer:
    """Tests for mood analysis agent."""

    @pytest.mark.asyncio
    async def test_relaxed_mood_detection(self):
        """Test detection of relaxed mood."""
        agent = MoodAnalyzerAgent()

        context = {
            "user_input": "I want to relax and unwind tonight",
            "time_of_day": "evening"
        }

        mood = await agent.execute(context)

        assert mood == MoodCategory.RELAXED

    @pytest.mark.asyncio
    async def test_excited_mood_detection(self):
        """Test detection of excited mood."""
        agent = MoodAnalyzerAgent()

        context = {
            "user_input": "Looking for something exciting and thrilling!",
            "time_of_day": "afternoon"
        }

        mood = await agent.execute(context)

        assert mood == MoodCategory.EXCITED

    @pytest.mark.asyncio
    async def test_default_mood_on_neutral_input(self):
        """Test default mood on neutral input."""
        agent = MoodAnalyzerAgent()

        context = {
            "user_input": "show me something",
            "time_of_day": "evening"
        }

        mood = await agent.execute(context)

        # Should default to RELAXED for evening
        assert isinstance(mood, MoodCategory)


class TestGenreMatcher:
    """Tests for genre matching agent."""

    @pytest.mark.asyncio
    async def test_mood_based_genres(self):
        """Test genre matching based on mood."""
        agent = GenreMatcherAgent()

        context = {
            "mood": MoodCategory.EXCITED,
            "preferences": UserPreferences()
        }

        genres = await agent.execute(context)

        assert "action" in genres or "thriller" in genres

    @pytest.mark.asyncio
    async def test_user_preferences_prioritized(self):
        """Test that user preferences are prioritized."""
        agent = GenreMatcherAgent()

        prefs = UserPreferences(preferred_genres=["documentary", "nature"])

        context = {
            "mood": MoodCategory.RELAXED,
            "preferences": prefs
        }

        genres = await agent.execute(context)

        # User preferences should be first
        assert genres[0] in ["documentary", "nature"]


class TestContentScorer:
    """Tests for content scoring agent."""

    @pytest.mark.asyncio
    async def test_scoring_returns_result(self):
        """Test that scoring returns a valid result."""
        agent = ContentScorerAgent()

        content = ContentItem(
            content_id="test1",
            title="Test Movie",
            content_type=ContentType.MOVIE,
            genres=["action", "adventure"],
            duration_minutes=120,
            release_year=2024,
            rating=8.5,
            platform="netflix"
        )

        context = {
            "content": content,
            "preferences": UserPreferences(available_platforms=["netflix"]),
            "matched_genres": ["action"],
            "mood": MoodCategory.EXCITED,
            "duration_range": (90, 150)
        }

        result = await agent.execute(context)

        assert 0 <= result.score <= 1
        assert 0 <= result.confidence <= 1
        assert result.content_id == "test1"

    @pytest.mark.asyncio
    async def test_genre_match_affects_score(self):
        """Test that genre matching affects score."""
        agent = ContentScorerAgent()

        content = ContentItem(
            content_id="test1",
            title="Test Movie",
            content_type=ContentType.MOVIE,
            genres=["action", "adventure"],
            duration_minutes=120,
            release_year=2024,
            rating=7.0,
            platform="netflix"
        )

        # High genre match
        context1 = {
            "content": content,
            "matched_genres": ["action", "adventure"],
            "preferences": UserPreferences(),
            "duration_range": (0, 999)
        }

        # Low genre match
        context2 = {
            "content": content,
            "matched_genres": ["romance", "drama"],
            "preferences": UserPreferences(),
            "duration_range": (0, 999)
        }

        result1 = await agent.execute(context1)
        result2 = await agent.execute(context2)

        assert result1.factors["genre_match"] > result2.factors["genre_match"]


class TestTaskDecomposition:
    """Tests for task decomposition."""

    def test_decomposition_creates_steps(self):
        """Test that decomposition creates proper steps."""
        decomposer = EntertainmentDiscoveryDecomposer()

        candidates = [
            ContentItem(
                content_id=f"c{i}",
                title=f"Content {i}",
                content_type=ContentType.MOVIE,
                genres=["drama"],
                duration_minutes=100,
                release_year=2024,
                rating=7.0,
                platform="netflix"
            )
            for i in range(3)
        ]

        task = {
            "user_input": "something fun",
            "candidates": candidates,
            "top_k": 2
        }

        steps = decomposer.decompose(task)

        # Should have: mood, genres, duration, 3 scorings, 1 ranking, 2 explanations
        assert len(steps) >= 8

        # Check step IDs are unique
        step_ids = [s.step_id for s in steps]
        assert len(step_ids) == len(set(step_ids))

    def test_step_dependencies_valid(self):
        """Test that step dependencies reference valid steps."""
        decomposer = EntertainmentDiscoveryDecomposer()

        task = {
            "user_input": "test",
            "candidates": [],
            "top_k": 3
        }

        steps = decomposer.decompose(task)
        step_ids = {s.step_id for s in steps}

        for step in steps:
            for dep in step.dependencies:
                assert dep in step_ids, f"Step {step.step_id} has invalid dependency {dep}"


class TestVotingOptimizer:
    """Tests for voting optimization."""

    def test_optimal_k_calculation(self):
        """Test optimal k calculation."""
        optimizer = VotingOptimizer(target_success_rate=0.99)

        # High accuracy needs lower k
        k_high = optimizer.calculate_optimal_k(0.95, 100)

        # Low accuracy needs higher k
        k_low = optimizer.calculate_optimal_k(0.7, 100)

        assert k_low > k_high

    def test_cost_estimation(self):
        """Test cost estimation."""
        optimizer = VotingOptimizer()

        cost = optimizer.estimate_cost(
            k=3,
            per_step_accuracy=0.9,
            total_steps=100,
            cost_per_vote=0.001
        )

        assert "expected_cost" in cost
        assert cost["expected_cost"] > 0
        assert cost["best_case_cost"] <= cost["expected_cost"]

    def test_model_recommendation(self):
        """Test model recommendation."""
        optimizer = VotingOptimizer()

        accuracy = {"gpt-4": 0.98, "gpt-4o-mini": 0.92, "gpt-3.5": 0.85}
        costs = {"gpt-4": 0.03, "gpt-4o-mini": 0.001, "gpt-3.5": 0.0005}

        rec = optimizer.recommend_model(accuracy, costs, total_steps=100)

        assert rec["recommended_model"] is not None
        # Cheaper models often win on reliability-per-dollar
        assert rec["recommended_model"] in ["gpt-4o-mini", "gpt-3.5"]


class TestIntegration:
    """Integration tests."""

    @pytest.mark.asyncio
    async def test_full_pipeline_mock(self):
        """Test full recommendation pipeline with mock data."""
        from maker.api import VibecastMAKER, DiscoveryRequest

        # Use development config for testing
        engine = VibecastMAKER(config=DEVELOPMENT_CONFIG)

        candidates = [
            ContentItem(
                content_id="movie1",
                title="Action Hero",
                content_type=ContentType.MOVIE,
                genres=["action", "adventure"],
                duration_minutes=120,
                release_year=2024,
                rating=8.5,
                platform="netflix"
            ),
            ContentItem(
                content_id="movie2",
                title="Romantic Evening",
                content_type=ContentType.MOVIE,
                genres=["romance", "drama"],
                duration_minutes=95,
                release_year=2023,
                rating=7.8,
                platform="hulu"
            ),
        ]

        request = DiscoveryRequest(
            user_input="I want something exciting",
            candidates=candidates,
            top_k=2,
            preferences=UserPreferences(
                available_platforms=["netflix", "hulu"]
            )
        )

        response = await engine.discover(request)

        assert response.success
        assert response.mood is not None
        assert len(response.matched_genres) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
