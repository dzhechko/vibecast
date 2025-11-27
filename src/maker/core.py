"""
MAKER Framework Core Implementation

Based on "Solving a Million-Step LLM Task with Zero Errors" (arXiv:2511.09030)
MAKER = Maximal Agentic decomposition, K-threshold Error mitigation, and Red-flagging

This implementation adapts MAKER principles for entertainment discovery:
- Microagents handle atomic content recommendation tasks
- Voting ensures consensus on recommendations
- Red-flagging filters low-quality or malformed responses
"""

import asyncio
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Generic, TypeVar, Optional
from collections import Counter
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T')


class VoteStatus(Enum):
    """Status of a voting round."""
    PENDING = "pending"
    DECIDED = "decided"
    RED_FLAGGED = "red_flagged"
    TIMEOUT = "timeout"


@dataclass
class Vote(Generic[T]):
    """Represents a single vote from a microagent."""
    value: T
    agent_id: str
    timestamp: float = field(default_factory=time.time)
    confidence: float = 1.0
    metadata: dict = field(default_factory=dict)
    red_flags: list[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        """Check if vote has no red flags."""
        return len(self.red_flags) == 0


@dataclass
class VotingResult(Generic[T]):
    """Result of a voting round."""
    winner: Optional[T]
    status: VoteStatus
    vote_counts: dict[T, int]
    total_votes: int
    rounds_taken: int
    winning_margin: int
    all_votes: list[Vote[T]]
    duration_ms: float


@dataclass
class RedFlagCriteria:
    """Criteria for red-flagging responses.

    Based on MAKER paper: responses exceeding ~700 tokens or
    incorrectly formatted are red-flagged.
    """
    max_response_tokens: int = 700
    max_response_length: int = 3000  # characters
    required_fields: list[str] = field(default_factory=list)
    forbidden_patterns: list[str] = field(default_factory=list)
    min_confidence: float = 0.1

    def check(self, response: Any, metadata: dict = None) -> list[str]:
        """Check response against red-flag criteria.

        Returns list of red flag reasons (empty if valid).
        """
        flags = []
        metadata = metadata or {}

        # Check response length
        response_str = str(response)
        if len(response_str) > self.max_response_length:
            flags.append(f"response_too_long:{len(response_str)}")

        # Check token count if available
        if 'token_count' in metadata:
            if metadata['token_count'] > self.max_response_tokens:
                flags.append(f"too_many_tokens:{metadata['token_count']}")

        # Check required fields for dict responses
        if isinstance(response, dict):
            for field_name in self.required_fields:
                if field_name not in response:
                    flags.append(f"missing_field:{field_name}")

        # Check forbidden patterns
        for pattern in self.forbidden_patterns:
            if pattern.lower() in response_str.lower():
                flags.append(f"forbidden_pattern:{pattern}")

        # Check confidence
        if 'confidence' in metadata:
            if metadata['confidence'] < self.min_confidence:
                flags.append(f"low_confidence:{metadata['confidence']}")

        return flags


class FirstToAheadByKVoting(Generic[T]):
    """
    First-to-ahead-by-k voting algorithm from MAKER.

    Implements the voting scheme where a candidate wins when it achieves
    k more votes than any other candidate. This provides exponential
    convergence toward perfect consensus.

    From the paper:
    - p(ai = a*) = 1 / (1 + ((1-p)/p)^k)
    - Expected cost scales as Θ(s ln s)
    """

    def __init__(
        self,
        k: int = 3,
        max_rounds: int = 100,
        red_flag_criteria: Optional[RedFlagCriteria] = None,
        parallel_votes: int = 5
    ):
        """
        Initialize voting system.

        Args:
            k: Vote margin required to win (default 3 from paper)
            max_rounds: Maximum voting rounds before timeout
            red_flag_criteria: Criteria for filtering bad responses
            parallel_votes: Number of votes to collect in parallel
        """
        self.k = k
        self.max_rounds = max_rounds
        self.red_flag_criteria = red_flag_criteria or RedFlagCriteria()
        self.parallel_votes = parallel_votes

    async def run_voting(
        self,
        vote_fn: Callable[[], T],
        agent_id_fn: Callable[[], str] = lambda: "agent"
    ) -> VotingResult[T]:
        """
        Run first-to-ahead-by-k voting until a winner is decided.

        Args:
            vote_fn: Async function that returns a vote value
            agent_id_fn: Function that returns the voting agent's ID

        Returns:
            VotingResult with the winning value and statistics
        """
        start_time = time.time()
        votes: list[Vote[T]] = []
        vote_counts: Counter[T] = Counter()
        rounds = 0

        while rounds < self.max_rounds:
            rounds += 1

            # Collect votes in parallel batches
            if asyncio.iscoroutinefunction(vote_fn):
                vote_value = await vote_fn()
            else:
                vote_value = vote_fn()

            # Check for red flags
            red_flags = self.red_flag_criteria.check(vote_value)

            vote = Vote(
                value=vote_value,
                agent_id=agent_id_fn(),
                red_flags=red_flags
            )

            # Only count valid votes
            if vote.is_valid:
                votes.append(vote)
                vote_counts[vote_value] += 1

                # Check if we have a winner
                winner, margin = self._check_winner(vote_counts)
                if winner is not None:
                    duration_ms = (time.time() - start_time) * 1000
                    return VotingResult(
                        winner=winner,
                        status=VoteStatus.DECIDED,
                        vote_counts=dict(vote_counts),
                        total_votes=len(votes),
                        rounds_taken=rounds,
                        winning_margin=margin,
                        all_votes=votes,
                        duration_ms=duration_ms
                    )
            else:
                logger.debug(f"Vote red-flagged: {red_flags}")

        # Timeout - return most common if any votes
        duration_ms = (time.time() - start_time) * 1000
        if vote_counts:
            winner = vote_counts.most_common(1)[0][0]
            return VotingResult(
                winner=winner,
                status=VoteStatus.TIMEOUT,
                vote_counts=dict(vote_counts),
                total_votes=len(votes),
                rounds_taken=rounds,
                winning_margin=0,
                all_votes=votes,
                duration_ms=duration_ms
            )

        return VotingResult(
            winner=None,
            status=VoteStatus.RED_FLAGGED,
            vote_counts={},
            total_votes=0,
            rounds_taken=rounds,
            winning_margin=0,
            all_votes=votes,
            duration_ms=duration_ms
        )

    def _check_winner(self, vote_counts: Counter[T]) -> tuple[Optional[T], int]:
        """
        Check if any candidate is ahead by k votes.

        Returns (winner, margin) or (None, 0) if no winner yet.
        """
        if not vote_counts:
            return None, 0

        most_common = vote_counts.most_common(2)
        leader, leader_count = most_common[0]

        if len(most_common) == 1:
            # Only one candidate
            if leader_count >= self.k:
                return leader, leader_count
        else:
            # Multiple candidates - check margin
            _, second_count = most_common[1]
            margin = leader_count - second_count
            if margin >= self.k:
                return leader, margin

        return None, 0


class Microagent(ABC, Generic[T]):
    """
    Abstract base class for MAKER microagents.

    Each microagent is responsible for one atomic action, receiving
    only essential context for its assigned step. This enables:
    - Modularity: agents can be tailored to specific tasks
    - Independent development: agents can be updated/tested in isolation
    - Scalability: agents can be scaled independently
    - Fault tolerance: designed to tolerate individual failures
    """

    def __init__(
        self,
        agent_id: str,
        temperature: float = 0.1,
        max_tokens: int = 750
    ):
        """
        Initialize microagent.

        Args:
            agent_id: Unique identifier for this agent
            temperature: LLM temperature (0.1 recommended by paper)
            max_tokens: Max output tokens (750 from paper)
        """
        self.agent_id = agent_id
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.call_count = 0
        self.error_count = 0

    @abstractmethod
    async def execute(self, context: dict[str, Any]) -> T:
        """
        Execute the atomic task for this microagent.

        Args:
            context: Essential context for this step

        Returns:
            Result of the atomic action
        """
        pass

    @abstractmethod
    def validate_output(self, output: T) -> bool:
        """Validate the output format and content."""
        pass

    def get_stats(self) -> dict:
        """Get agent statistics."""
        return {
            "agent_id": self.agent_id,
            "call_count": self.call_count,
            "error_count": self.error_count,
            "error_rate": self.error_count / max(1, self.call_count)
        }


@dataclass
class Step:
    """Represents a single step in a decomposed task."""
    step_id: int
    description: str
    context: dict[str, Any]
    dependencies: list[int] = field(default_factory=list)
    result: Any = None
    status: str = "pending"


class TaskDecomposer(ABC):
    """
    Abstract base class for Maximal Agentic Decomposition (MAD).

    Decomposes complex tasks into minimal subproblems where each
    microagent handles one decision/action.
    """

    @abstractmethod
    def decompose(self, task: dict[str, Any]) -> list[Step]:
        """
        Decompose a task into atomic steps.

        Args:
            task: The complex task to decompose

        Returns:
            List of atomic steps with dependencies
        """
        pass

    @abstractmethod
    def compose_result(self, steps: list[Step]) -> Any:
        """
        Compose final result from completed steps.

        Args:
            steps: Completed atomic steps

        Returns:
            Final composed result
        """
        pass


class MAKEROrchestrator:
    """
    Main orchestrator for MAKER-based task execution.

    Coordinates:
    - Task decomposition via MAD
    - Microagent execution with voting
    - Error correction via red-flagging
    - Result composition
    """

    def __init__(
        self,
        decomposer: TaskDecomposer,
        voting_k: int = 3,
        max_voting_rounds: int = 100,
        red_flag_criteria: Optional[RedFlagCriteria] = None
    ):
        """
        Initialize MAKER orchestrator.

        Args:
            decomposer: Task decomposition strategy
            voting_k: K threshold for voting (default 3)
            max_voting_rounds: Max rounds per step
            red_flag_criteria: Criteria for red-flagging
        """
        self.decomposer = decomposer
        self.voting = FirstToAheadByKVoting(
            k=voting_k,
            max_rounds=max_voting_rounds,
            red_flag_criteria=red_flag_criteria
        )
        self.agents: dict[str, Microagent] = {}
        self.execution_stats = {
            "total_steps": 0,
            "successful_steps": 0,
            "failed_steps": 0,
            "total_votes": 0,
            "red_flagged_votes": 0,
            "avg_rounds_per_step": 0.0
        }

    def register_agent(self, agent: Microagent) -> None:
        """Register a microagent for task execution."""
        self.agents[agent.agent_id] = agent

    async def execute_task(
        self,
        task: dict[str, Any],
        agent_selector: Callable[[Step], str] = None
    ) -> dict[str, Any]:
        """
        Execute a complete task using MAKER methodology.

        Args:
            task: Task to execute
            agent_selector: Function to select agent for each step

        Returns:
            Task result with execution statistics
        """
        # Decompose task into atomic steps
        steps = self.decomposer.decompose(task)
        self.execution_stats["total_steps"] = len(steps)

        logger.info(f"Decomposed task into {len(steps)} steps")

        total_rounds = 0

        # Execute each step with voting
        for step in steps:
            agent_id = agent_selector(step) if agent_selector else self._default_agent_selector(step)
            agent = self.agents.get(agent_id)

            if not agent:
                logger.error(f"No agent found for step {step.step_id}")
                step.status = "failed"
                self.execution_stats["failed_steps"] += 1
                continue

            # Build context with dependency results
            context = self._build_context(step, steps)

            # Execute with voting
            async def vote_fn():
                return await agent.execute(context)

            result = await self.voting.run_voting(
                vote_fn,
                lambda: agent_id
            )

            total_rounds += result.rounds_taken
            self.execution_stats["total_votes"] += result.total_votes

            if result.status == VoteStatus.DECIDED:
                step.result = result.winner
                step.status = "completed"
                self.execution_stats["successful_steps"] += 1
            else:
                step.result = result.winner
                step.status = "timeout" if result.status == VoteStatus.TIMEOUT else "failed"
                if result.status == VoteStatus.RED_FLAGGED:
                    self.execution_stats["red_flagged_votes"] += 1
                self.execution_stats["failed_steps"] += 1

        # Calculate average rounds
        if len(steps) > 0:
            self.execution_stats["avg_rounds_per_step"] = total_rounds / len(steps)

        # Compose final result
        final_result = self.decomposer.compose_result(steps)

        return {
            "result": final_result,
            "steps": steps,
            "stats": self.execution_stats
        }

    def _default_agent_selector(self, step: Step) -> str:
        """Default agent selection based on step description."""
        # Return first registered agent
        if self.agents:
            return next(iter(self.agents.keys()))
        return "default"

    def _build_context(self, step: Step, all_steps: list[Step]) -> dict[str, Any]:
        """Build context for a step including dependency results."""
        context = step.context.copy()

        # Add results from dependencies
        for dep_id in step.dependencies:
            dep_step = next((s for s in all_steps if s.step_id == dep_id), None)
            if dep_step and dep_step.result is not None:
                context[f"step_{dep_id}_result"] = dep_step.result

        return context
