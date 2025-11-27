"""
MAKER Framework for Vibecast

Implementation of "Solving a Million-Step LLM Task with Zero Errors" (arXiv:2511.09030)
adapted for entertainment discovery and content recommendation.

Paper: https://arxiv.org/abs/2511.09030
Authors: Meyerson, Paolo, Dailey, Shahrzad, Francon, Hayes, Qiu, Hodjat, Miikkulainen

Key Concepts:
- MAKER = Maximal Agentic decomposition, K-threshold Error mitigation, and Red-flagging
- Microagents: Each agent handles one atomic action
- First-to-ahead-by-k voting: Consensus mechanism for reliability
- Red-flagging: Filter malformed or suspicious responses
"""

from .core import (
    Vote,
    VoteStatus,
    VotingResult,
    RedFlagCriteria,
    FirstToAheadByKVoting,
    Microagent,
    Step,
    TaskDecomposer,
    MAKEROrchestrator,
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
)

from .config import (
    MAKERConfig,
    LLMConfig,
    VotingConfig,
    RedFlagConfig,
    DEVELOPMENT_CONFIG,
    PRODUCTION_CONFIG,
    HIGH_ACCURACY_CONFIG,
    COST_OPTIMIZED_CONFIG,
)

from .benchmark import (
    MAKERBenchmark,
    VotingOptimizer,
    PerformanceProfiler,
    ScalingAnalyzer,
    BenchmarkResult,
)

from .api import (
    VibecastMAKER,
    DiscoveryRequest,
    DiscoveryResponse,
    recommend,
)

from .research_agents import (
    ResearchType,
    SourceType,
    Source,
    Finding,
    ResearchQuery,
    ResearchResult,
    QueryDecomposerAgent,
    SourceDiscoveryAgent,
    InformationExtractorAgent,
    FactVerifierAgent,
    SynthesisAgent,
    GapIdentifierAgent,
    FollowUpGeneratorAgent,
    ResearchDecomposer,
    RESEARCH_RED_FLAG_CRITERIA,
)

from .universal_solver import (
    # Protocols (technology-agnostic interfaces)
    Reasoning,
    Memory,
    Tool,
    # Mathematical foundations
    MathematicalGuarantees,
    # Universal problem representation
    ProblemType,
    UniversalProblem,
    Solution,
    # Decomposition
    DecompositionStrategy,
    RecursiveDecomposition,
    AnalogicalDecomposition,
    MetaDecomposer,
    # Voting
    VoteWithProof,
    UniversalVoting,
    # Agents
    UniversalAgent,
    AgentFactory,
    # Main solver
    UMAPS,
    create_universal_solver,
)

__version__ = "0.1.0"

__all__ = [
    # Core
    "Vote",
    "VoteStatus",
    "VotingResult",
    "RedFlagCriteria",
    "FirstToAheadByKVoting",
    "Microagent",
    "Step",
    "TaskDecomposer",
    "MAKEROrchestrator",
    # Entertainment Agents
    "ContentType",
    "MoodCategory",
    "UserPreferences",
    "ContentItem",
    "RecommendationResult",
    "MoodAnalyzerAgent",
    "GenreMatcherAgent",
    "DurationFilterAgent",
    "ContentScorerAgent",
    "ContentRankerAgent",
    "ExplanationGeneratorAgent",
    "EntertainmentDiscoveryDecomposer",
    # Config
    "MAKERConfig",
    "LLMConfig",
    "VotingConfig",
    "RedFlagConfig",
    "DEVELOPMENT_CONFIG",
    "PRODUCTION_CONFIG",
    "HIGH_ACCURACY_CONFIG",
    "COST_OPTIMIZED_CONFIG",
    # Benchmark
    "MAKERBenchmark",
    "VotingOptimizer",
    "PerformanceProfiler",
    "ScalingAnalyzer",
    "BenchmarkResult",
    # API
    "VibecastMAKER",
    "DiscoveryRequest",
    "DiscoveryResponse",
    "recommend",
    # Research Agents
    "ResearchType",
    "SourceType",
    "Source",
    "Finding",
    "ResearchQuery",
    "ResearchResult",
    "QueryDecomposerAgent",
    "SourceDiscoveryAgent",
    "InformationExtractorAgent",
    "FactVerifierAgent",
    "SynthesisAgent",
    "GapIdentifierAgent",
    "FollowUpGeneratorAgent",
    "ResearchDecomposer",
    "RESEARCH_RED_FLAG_CRITERIA",
    # Universal Solver
    "Reasoning",
    "Memory",
    "Tool",
    "MathematicalGuarantees",
    "ProblemType",
    "UniversalProblem",
    "Solution",
    "DecompositionStrategy",
    "RecursiveDecomposition",
    "AnalogicalDecomposition",
    "MetaDecomposer",
    "VoteWithProof",
    "UniversalVoting",
    "UniversalAgent",
    "AgentFactory",
    "UMAPS",
    "create_universal_solver",
]
