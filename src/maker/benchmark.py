"""
MAKER Benchmarking and Optimization Tools

Based on the MAKER paper's methodology for measuring:
- Per-step accuracy
- Cost efficiency (reliability-per-dollar)
- Voting convergence rates
- Red-flag filtering effectiveness
"""

import asyncio
import json
import time
import statistics
from dataclasses import dataclass, field
from typing import Any, Callable, Optional
from collections import defaultdict
import logging

from .core import (
    Microagent,
    FirstToAheadByKVoting,
    VoteStatus,
    VotingResult,
    RedFlagCriteria,
    MAKEROrchestrator,
    TaskDecomposer,
)

logger = logging.getLogger(__name__)


@dataclass
class StepMetrics:
    """Metrics for a single step execution."""
    step_id: int
    success: bool
    votes_required: int
    rounds_taken: int
    duration_ms: float
    red_flags_encountered: int
    winning_margin: int
    vote_distribution: dict[str, int]


@dataclass
class AgentMetrics:
    """Metrics for a specific microagent."""
    agent_id: str
    total_calls: int = 0
    successful_calls: int = 0
    error_rate: float = 0.0
    avg_response_time_ms: float = 0.0
    red_flag_rate: float = 0.0
    cost_per_call: float = 0.0


@dataclass
class BenchmarkResult:
    """Complete benchmark result."""
    name: str
    total_steps: int
    successful_steps: int
    failed_steps: int
    accuracy: float  # successful_steps / total_steps
    total_votes: int
    avg_votes_per_step: float
    avg_rounds_per_step: float
    total_duration_ms: float
    avg_step_duration_ms: float
    red_flag_rate: float
    total_cost: float
    cost_per_step: float
    step_metrics: list[StepMetrics] = field(default_factory=list)
    agent_metrics: dict[str, AgentMetrics] = field(default_factory=dict)
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "total_steps": self.total_steps,
            "successful_steps": self.successful_steps,
            "failed_steps": self.failed_steps,
            "accuracy": self.accuracy,
            "total_votes": self.total_votes,
            "avg_votes_per_step": self.avg_votes_per_step,
            "avg_rounds_per_step": self.avg_rounds_per_step,
            "total_duration_ms": self.total_duration_ms,
            "avg_step_duration_ms": self.avg_step_duration_ms,
            "red_flag_rate": self.red_flag_rate,
            "total_cost": self.total_cost,
            "cost_per_step": self.cost_per_step,
            "metadata": self.metadata,
        }


class MAKERBenchmark:
    """
    Benchmark suite for MAKER implementations.

    Measures key metrics from the paper:
    - Per-step error rate (should be low enough for k-voting to work)
    - Voting efficiency (rounds needed to reach consensus)
    - Cost efficiency (total cost for full task completion)
    - Scaling behavior (how metrics change with task size)
    """

    def __init__(
        self,
        orchestrator: MAKEROrchestrator,
        cost_per_vote: float = 0.001,  # Cost per LLM call
    ):
        """
        Initialize benchmark.

        Args:
            orchestrator: MAKER orchestrator to benchmark
            cost_per_vote: Estimated cost per vote/LLM call
        """
        self.orchestrator = orchestrator
        self.cost_per_vote = cost_per_vote
        self.results: list[BenchmarkResult] = []

    async def run_benchmark(
        self,
        name: str,
        tasks: list[dict[str, Any]],
        ground_truth: Optional[list[Any]] = None,
        agent_selector: Optional[Callable] = None,
    ) -> BenchmarkResult:
        """
        Run benchmark on a set of tasks.

        Args:
            name: Benchmark name
            tasks: List of tasks to execute
            ground_truth: Optional ground truth for accuracy measurement
            agent_selector: Optional agent selection function

        Returns:
            BenchmarkResult with all metrics
        """
        start_time = time.time()
        step_metrics: list[StepMetrics] = []
        total_votes = 0
        total_rounds = 0
        red_flags = 0
        successful = 0

        for i, task in enumerate(tasks):
            result = await self.orchestrator.execute_task(task, agent_selector)

            # Collect metrics from each step
            for step in result.get("steps", []):
                step_success = step.status == "completed"
                if step_success:
                    successful += 1

                # These would be tracked by the voting system
                votes = self.orchestrator.execution_stats.get("total_votes", 0)
                total_votes += votes

                step_metrics.append(StepMetrics(
                    step_id=step.step_id,
                    success=step_success,
                    votes_required=votes,
                    rounds_taken=1,  # Would be tracked per step
                    duration_ms=0,  # Would be tracked per step
                    red_flags_encountered=0,
                    winning_margin=0,
                    vote_distribution={}
                ))

        total_steps = len(step_metrics)
        duration_ms = (time.time() - start_time) * 1000

        result = BenchmarkResult(
            name=name,
            total_steps=total_steps,
            successful_steps=successful,
            failed_steps=total_steps - successful,
            accuracy=successful / max(1, total_steps),
            total_votes=total_votes,
            avg_votes_per_step=total_votes / max(1, total_steps),
            avg_rounds_per_step=total_rounds / max(1, total_steps),
            total_duration_ms=duration_ms,
            avg_step_duration_ms=duration_ms / max(1, total_steps),
            red_flag_rate=red_flags / max(1, total_votes),
            total_cost=total_votes * self.cost_per_vote,
            cost_per_step=(total_votes * self.cost_per_vote) / max(1, total_steps),
            step_metrics=step_metrics,
            metadata={"task_count": len(tasks)}
        )

        self.results.append(result)
        return result


class VotingOptimizer:
    """
    Optimizer for MAKER voting parameters.

    Based on paper equations:
    - kmin = ⌈ln(t^(-m/s) - 1) / ln((1-p)/p)⌉ = Θ(ln s)
    - Expected cost: Θ(s ln s)
    """

    def __init__(self, target_success_rate: float = 0.9999):
        """
        Initialize optimizer.

        Args:
            target_success_rate: Target full-task success rate (default 99.99%)
        """
        self.target_success_rate = target_success_rate

    def calculate_optimal_k(
        self,
        per_step_accuracy: float,
        total_steps: int,
        safety_margin: float = 1.2
    ) -> int:
        """
        Calculate optimal k value for voting.

        From paper equation 14:
        kmin = ⌈ln(t^(-m/s) - 1) / ln((1-p)/p)⌉

        Args:
            per_step_accuracy: Base accuracy per step (p)
            total_steps: Total number of steps (s)
            safety_margin: Safety multiplier for k

        Returns:
            Recommended k value
        """
        import math

        p = per_step_accuracy
        s = total_steps
        t = self.target_success_rate

        if p <= 0.5:
            # Need very high k if accuracy is low
            return max(10, int(math.log(s) * 3))

        if p >= 0.999:
            # High accuracy, k=2 might suffice
            return 2

        # Calculate kmin from paper formula
        try:
            # t^(-m/s) - 1, assuming m=1 for simplicity
            term1 = math.pow(t, -1/s) - 1
            # ln((1-p)/p)
            term2 = math.log((1 - p) / p)

            if term2 == 0:
                return 3

            k_min = math.ceil(math.log(term1) / term2)
            k_optimal = max(2, int(k_min * safety_margin))

            return min(k_optimal, 20)  # Cap at reasonable maximum
        except (ValueError, ZeroDivisionError):
            return 3  # Default fallback

    def estimate_cost(
        self,
        k: int,
        per_step_accuracy: float,
        total_steps: int,
        cost_per_vote: float
    ) -> dict[str, float]:
        """
        Estimate total cost for task completion.

        From paper equation 18-19:
        E[cost] = Θ(s ln s)

        Args:
            k: Voting threshold
            per_step_accuracy: Base accuracy (p)
            total_steps: Total steps (s)
            cost_per_vote: Cost per LLM call

        Returns:
            Cost estimates
        """
        import math

        p = per_step_accuracy
        s = total_steps

        # Average votes per step (simplified model)
        # In best case: k votes for winner
        # In worst case: exponential in k
        avg_votes_best = k + 1
        avg_votes_expected = k * (1 / (2 * p - 1)) if p > 0.5 else k * 10

        # From paper: E[cost] ≈ c*s*kmin / (v*(2p-1))
        expected_votes = avg_votes_expected * s

        return {
            "best_case_votes": avg_votes_best * s,
            "expected_votes": expected_votes,
            "worst_case_votes": expected_votes * 2,
            "best_case_cost": avg_votes_best * s * cost_per_vote,
            "expected_cost": expected_votes * cost_per_vote,
            "worst_case_cost": expected_votes * 2 * cost_per_vote,
            "cost_per_step": avg_votes_expected * cost_per_vote,
        }

    def recommend_model(
        self,
        accuracy_by_model: dict[str, float],
        cost_by_model: dict[str, float],
        total_steps: int
    ) -> dict[str, Any]:
        """
        Recommend best model based on reliability-per-dollar.

        From paper: "smaller, non-reasoning models provided best
        reliability-per-dollar"

        Args:
            accuracy_by_model: Per-step accuracy by model
            cost_by_model: Cost per call by model
            total_steps: Total steps in task

        Returns:
            Model recommendation with analysis
        """
        recommendations = []

        for model in accuracy_by_model:
            p = accuracy_by_model[model]
            cost = cost_by_model.get(model, 0.01)

            k = self.calculate_optimal_k(p, total_steps)
            cost_estimate = self.estimate_cost(k, p, total_steps, cost)

            # Success probability with this k
            import math
            if p > 0.5:
                per_step_success = 1 / (1 + math.pow((1-p)/p, k))
                full_success = math.pow(per_step_success, total_steps)
            else:
                full_success = 0.0

            recommendations.append({
                "model": model,
                "accuracy": p,
                "optimal_k": k,
                "expected_cost": cost_estimate["expected_cost"],
                "success_probability": full_success,
                "reliability_per_dollar": full_success / max(0.001, cost_estimate["expected_cost"]),
            })

        # Sort by reliability per dollar (descending)
        recommendations.sort(key=lambda x: x["reliability_per_dollar"], reverse=True)

        return {
            "recommended_model": recommendations[0]["model"] if recommendations else None,
            "analysis": recommendations,
            "notes": "Lower cost models often provide better reliability-per-dollar for simple steps"
        }


class PerformanceProfiler:
    """
    Profiler for detailed MAKER performance analysis.
    """

    def __init__(self):
        self.profiles: dict[str, list[float]] = defaultdict(list)
        self.counters: dict[str, int] = defaultdict(int)

    def record_timing(self, operation: str, duration_ms: float):
        """Record timing for an operation."""
        self.profiles[f"{operation}_time"].append(duration_ms)

    def record_count(self, metric: str, count: int = 1):
        """Record a count metric."""
        self.counters[metric] += count

    def get_summary(self) -> dict[str, Any]:
        """Get profiling summary."""
        summary = {"timings": {}, "counts": dict(self.counters)}

        for name, values in self.profiles.items():
            if values:
                summary["timings"][name] = {
                    "count": len(values),
                    "min": min(values),
                    "max": max(values),
                    "mean": statistics.mean(values),
                    "median": statistics.median(values),
                    "std": statistics.stdev(values) if len(values) > 1 else 0,
                    "p95": sorted(values)[int(len(values) * 0.95)] if values else 0,
                    "p99": sorted(values)[int(len(values) * 0.99)] if values else 0,
                }

        return summary


class ScalingAnalyzer:
    """
    Analyzes MAKER scaling behavior.

    From paper: "kmin = Θ(ln s)" means k grows logarithmically with steps.
    """

    @staticmethod
    def analyze_scaling(
        benchmark_results: list[BenchmarkResult]
    ) -> dict[str, Any]:
        """
        Analyze how metrics scale with task size.

        Args:
            benchmark_results: Results from benchmarks of varying sizes

        Returns:
            Scaling analysis
        """
        if len(benchmark_results) < 2:
            return {"error": "Need at least 2 benchmarks for scaling analysis"}

        # Extract data points
        points = [
            {
                "steps": r.total_steps,
                "votes": r.total_votes,
                "cost": r.total_cost,
                "duration": r.total_duration_ms,
                "accuracy": r.accuracy,
            }
            for r in benchmark_results
        ]

        # Sort by steps
        points.sort(key=lambda x: x["steps"])

        # Analyze scaling factors
        import math

        scaling = {
            "data_points": points,
            "votes_per_step": [],
            "cost_per_step": [],
            "time_per_step": [],
        }

        for p in points:
            s = p["steps"]
            if s > 0:
                scaling["votes_per_step"].append(p["votes"] / s)
                scaling["cost_per_step"].append(p["cost"] / s)
                scaling["time_per_step"].append(p["duration"] / s)

        # Check if scaling is logarithmic (as paper suggests)
        # votes ~ s * ln(s), so votes/step ~ ln(s)
        if len(points) >= 3:
            ln_steps = [math.log(p["steps"]) for p in points if p["steps"] > 0]
            votes_per_step = scaling["votes_per_step"]

            # Simple correlation check
            if len(ln_steps) == len(votes_per_step):
                mean_ln = sum(ln_steps) / len(ln_steps)
                mean_votes = sum(votes_per_step) / len(votes_per_step)

                numerator = sum((ln_steps[i] - mean_ln) * (votes_per_step[i] - mean_votes)
                               for i in range(len(ln_steps)))
                denominator = (sum((x - mean_ln)**2 for x in ln_steps) *
                              sum((x - mean_votes)**2 for x in votes_per_step)) ** 0.5

                correlation = numerator / denominator if denominator > 0 else 0
                scaling["logarithmic_correlation"] = correlation
                scaling["is_logarithmic"] = abs(correlation) > 0.8

        return scaling


def run_quick_benchmark(
    orchestrator: MAKEROrchestrator,
    sample_task: dict[str, Any],
    iterations: int = 10
) -> dict[str, Any]:
    """
    Run a quick benchmark for development purposes.

    Args:
        orchestrator: MAKER orchestrator
        sample_task: Sample task to benchmark
        iterations: Number of iterations

    Returns:
        Quick benchmark results
    """
    async def _run():
        benchmark = MAKERBenchmark(orchestrator)
        tasks = [sample_task] * iterations
        result = await benchmark.run_benchmark("quick_test", tasks)
        return result.to_dict()

    return asyncio.run(_run())
