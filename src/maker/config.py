"""
MAKER Configuration

Configuration settings based on MAKER paper recommendations:
- Temperature: 0.1 (low for consistency)
- Max tokens: 750 (red-flag threshold ~700)
- Voting k: 3 (first-to-ahead-by-3)
"""

import os
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


class LLMProvider(Enum):
    """Supported LLM providers."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    LOCAL = "local"


@dataclass
class LLMConfig:
    """LLM configuration based on MAKER findings."""
    provider: LLMProvider = LLMProvider.OPENAI
    model: str = "gpt-4o-mini"  # Paper found smaller models more cost-effective
    temperature: float = 0.1  # Low temperature for consistency
    max_tokens: int = 750  # Just above red-flag threshold
    api_key: Optional[str] = None

    def __post_init__(self):
        if not self.api_key:
            self.api_key = self._get_api_key()

    def _get_api_key(self) -> Optional[str]:
        """Get API key from environment."""
        key_map = {
            LLMProvider.OPENAI: "OPENAI_API_KEY",
            LLMProvider.ANTHROPIC: "ANTHROPIC_API_KEY",
            LLMProvider.GOOGLE: "GOOGLE_API_KEY",
        }
        env_var = key_map.get(self.provider)
        return os.environ.get(env_var) if env_var else None


@dataclass
class VotingConfig:
    """Voting system configuration."""
    k: int = 3  # First-to-ahead-by-k threshold
    max_rounds: int = 100  # Maximum voting rounds before timeout
    parallel_votes: int = 5  # Votes to collect in parallel
    timeout_ms: int = 30000  # Timeout per voting round


@dataclass
class RedFlagConfig:
    """Red-flagging configuration."""
    max_response_tokens: int = 700  # From paper
    max_response_length: int = 3000  # Characters
    min_confidence: float = 0.1
    forbidden_patterns: list[str] = field(default_factory=lambda: [
        "i don't know",
        "i cannot",
        "error:",
        "exception:",
        "undefined",
        "null",
    ])


@dataclass
class BenchmarkConfig:
    """Benchmarking configuration."""
    cost_per_vote: float = 0.001  # Estimated cost per LLM call
    target_success_rate: float = 0.9999  # 99.99% success target
    profiling_enabled: bool = True
    save_detailed_metrics: bool = True


@dataclass
class MAKERConfig:
    """Complete MAKER configuration."""
    llm: LLMConfig = field(default_factory=LLMConfig)
    voting: VotingConfig = field(default_factory=VotingConfig)
    red_flag: RedFlagConfig = field(default_factory=RedFlagConfig)
    benchmark: BenchmarkConfig = field(default_factory=BenchmarkConfig)

    # Entertainment-specific settings
    top_k_recommendations: int = 5
    max_candidates_per_query: int = 100
    enable_explanations: bool = True

    @classmethod
    def from_env(cls) -> "MAKERConfig":
        """Load configuration from environment variables."""
        config = cls()

        # LLM settings
        if os.environ.get("MAKER_LLM_PROVIDER"):
            config.llm.provider = LLMProvider(os.environ["MAKER_LLM_PROVIDER"])
        if os.environ.get("MAKER_LLM_MODEL"):
            config.llm.model = os.environ["MAKER_LLM_MODEL"]
        if os.environ.get("MAKER_TEMPERATURE"):
            config.llm.temperature = float(os.environ["MAKER_TEMPERATURE"])

        # Voting settings
        if os.environ.get("MAKER_VOTING_K"):
            config.voting.k = int(os.environ["MAKER_VOTING_K"])
        if os.environ.get("MAKER_MAX_ROUNDS"):
            config.voting.max_rounds = int(os.environ["MAKER_MAX_ROUNDS"])

        # Benchmark settings
        if os.environ.get("MAKER_COST_PER_VOTE"):
            config.benchmark.cost_per_vote = float(os.environ["MAKER_COST_PER_VOTE"])

        return config

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "llm": {
                "provider": self.llm.provider.value,
                "model": self.llm.model,
                "temperature": self.llm.temperature,
                "max_tokens": self.llm.max_tokens,
            },
            "voting": {
                "k": self.voting.k,
                "max_rounds": self.voting.max_rounds,
                "parallel_votes": self.voting.parallel_votes,
            },
            "red_flag": {
                "max_response_tokens": self.red_flag.max_response_tokens,
                "max_response_length": self.red_flag.max_response_length,
                "min_confidence": self.red_flag.min_confidence,
            },
            "benchmark": {
                "cost_per_vote": self.benchmark.cost_per_vote,
                "target_success_rate": self.benchmark.target_success_rate,
            },
            "recommendations": {
                "top_k": self.top_k_recommendations,
                "max_candidates": self.max_candidates_per_query,
                "explanations": self.enable_explanations,
            }
        }


# Default configurations for different scenarios
DEVELOPMENT_CONFIG = MAKERConfig(
    llm=LLMConfig(temperature=0.3, max_tokens=500),
    voting=VotingConfig(k=2, max_rounds=20),
    benchmark=BenchmarkConfig(profiling_enabled=True),
)

PRODUCTION_CONFIG = MAKERConfig(
    llm=LLMConfig(temperature=0.1, max_tokens=750),
    voting=VotingConfig(k=3, max_rounds=100),
    benchmark=BenchmarkConfig(target_success_rate=0.9999),
)

HIGH_ACCURACY_CONFIG = MAKERConfig(
    llm=LLMConfig(temperature=0.05, max_tokens=750),
    voting=VotingConfig(k=5, max_rounds=200),
    benchmark=BenchmarkConfig(target_success_rate=0.99999),
)

COST_OPTIMIZED_CONFIG = MAKERConfig(
    llm=LLMConfig(model="gpt-4o-mini", temperature=0.1, max_tokens=500),
    voting=VotingConfig(k=2, max_rounds=50),
    benchmark=BenchmarkConfig(cost_per_vote=0.0005),
)
