"""
MAKER Research Agents

Extends MAKER framework for deep research tasks:
- Multi-source information gathering
- Fact verification through voting
- Synthesis with citation tracking
- Hallucination detection via red-flagging

The same principles that enable million-step task completion
apply to research: decompose → vote → filter → synthesize.
"""

import asyncio
from dataclasses import dataclass, field
from typing import Any, Optional
from enum import Enum
from datetime import datetime

from .core import Microagent, Step, TaskDecomposer, RedFlagCriteria


class ResearchType(Enum):
    """Types of research tasks."""
    EXPLORATORY = "exploratory"      # Open-ended discovery
    COMPARATIVE = "comparative"       # Compare options/approaches
    ANALYTICAL = "analytical"         # Deep dive on specific topic
    FACT_CHECK = "fact_check"        # Verify claims
    LITERATURE = "literature"         # Academic review
    TECHNICAL = "technical"          # Technical documentation


class SourceType(Enum):
    """Types of information sources."""
    ACADEMIC = "academic"            # Papers, journals
    WEB = "web"                      # General web
    NEWS = "news"                    # News articles
    DOCUMENTATION = "documentation"  # Technical docs
    DATABASE = "database"            # Structured data
    EXPERT = "expert"                # Expert opinions


@dataclass
class Source:
    """Represents an information source."""
    source_id: str
    url: Optional[str]
    title: str
    source_type: SourceType
    credibility_score: float  # 0-1
    date_published: Optional[datetime] = None
    authors: list[str] = field(default_factory=list)
    content_snippet: str = ""
    metadata: dict = field(default_factory=dict)


@dataclass
class Finding:
    """A research finding with supporting evidence."""
    finding_id: str
    claim: str
    confidence: float  # 0-1
    supporting_sources: list[str]  # Source IDs
    contradicting_sources: list[str] = field(default_factory=list)
    verification_votes: int = 0
    refutation_votes: int = 0
    metadata: dict = field(default_factory=dict)

    @property
    def verification_ratio(self) -> float:
        """Ratio of verification to total votes."""
        total = self.verification_votes + self.refutation_votes
        return self.verification_votes / total if total > 0 else 0.5


@dataclass
class ResearchQuery:
    """A research query to investigate."""
    query_id: str
    question: str
    context: str = ""
    research_type: ResearchType = ResearchType.EXPLORATORY
    depth: int = 3  # Levels of follow-up questions
    required_sources: int = 5
    source_types: list[SourceType] = field(default_factory=list)


@dataclass
class ResearchResult:
    """Complete research result."""
    query: ResearchQuery
    findings: list[Finding]
    sources: list[Source]
    synthesis: str
    confidence: float
    gaps_identified: list[str] = field(default_factory=list)
    follow_up_questions: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


# ============================================================================
# Research Microagents
# ============================================================================


class QueryDecomposerAgent(Microagent[list[str]]):
    """
    Decomposes complex research questions into atomic sub-queries.

    Atomic task: Given a research question, break it into specific,
    answerable sub-questions.
    """

    def __init__(self, llm_client: Any = None):
        super().__init__(agent_id="query_decomposer", temperature=0.2)
        self.llm_client = llm_client

    async def execute(self, context: dict[str, Any]) -> list[str]:
        """Decompose research question into sub-queries."""
        self.call_count += 1

        question = context.get("question", "")
        research_type = context.get("research_type", ResearchType.EXPLORATORY)
        depth = context.get("depth", 3)

        # Decomposition strategies by research type
        strategies = {
            ResearchType.EXPLORATORY: [
                "What is {topic}?",
                "What are the key components of {topic}?",
                "What are the main applications of {topic}?",
                "What are current trends in {topic}?",
                "Who are the key players/researchers in {topic}?",
            ],
            ResearchType.COMPARATIVE: [
                "What are the options for {topic}?",
                "What are the pros of each option?",
                "What are the cons of each option?",
                "How do they compare on key metrics?",
                "What do experts recommend?",
            ],
            ResearchType.ANALYTICAL: [
                "What is the core mechanism of {topic}?",
                "What evidence supports {topic}?",
                "What are the limitations of {topic}?",
                "How does {topic} relate to other concepts?",
                "What are the implications of {topic}?",
            ],
            ResearchType.FACT_CHECK: [
                "What is the original claim about {topic}?",
                "What sources support this claim?",
                "What sources contradict this claim?",
                "What is the consensus view on {topic}?",
                "What context is missing from {topic}?",
            ],
            ResearchType.LITERATURE: [
                "What are seminal papers on {topic}?",
                "What are recent developments in {topic}?",
                "What methodologies are used in {topic}?",
                "What are open questions in {topic}?",
                "What are the main research groups in {topic}?",
            ],
            ResearchType.TECHNICAL: [
                "How does {topic} work technically?",
                "What are the implementation details of {topic}?",
                "What are best practices for {topic}?",
                "What are common pitfalls with {topic}?",
                "What alternatives exist to {topic}?",
            ],
        }

        # Extract topic from question
        topic = question  # Simplified; would use NLP in production

        # Generate sub-queries
        template_queries = strategies.get(research_type, strategies[ResearchType.EXPLORATORY])
        sub_queries = [q.format(topic=topic) for q in template_queries[:depth]]

        return sub_queries

    def validate_output(self, output: list[str]) -> bool:
        return isinstance(output, list) and len(output) > 0


class SourceDiscoveryAgent(Microagent[list[Source]]):
    """
    Discovers relevant sources for a research query.

    Atomic task: Given a query, find credible sources.
    """

    def __init__(self, llm_client: Any = None, search_client: Any = None):
        super().__init__(agent_id="source_discovery", temperature=0.1)
        self.llm_client = llm_client
        self.search_client = search_client

    async def execute(self, context: dict[str, Any]) -> list[Source]:
        """Find sources for research query."""
        self.call_count += 1

        query = context.get("query", "")
        source_types = context.get("source_types", [SourceType.WEB])
        max_sources = context.get("max_sources", 5)

        # In production, this would call actual search APIs
        # (Google Scholar, Semantic Scholar, web search, etc.)

        # Mock sources for demonstration
        sources = []
        for i in range(min(max_sources, 3)):
            sources.append(Source(
                source_id=f"src_{i}",
                url=f"https://example.com/source/{i}",
                title=f"Source {i} on {query[:30]}",
                source_type=source_types[0] if source_types else SourceType.WEB,
                credibility_score=0.7 + (i * 0.05),
                content_snippet=f"Relevant content about {query}...",
            ))

        return sources

    def validate_output(self, output: list[Source]) -> bool:
        return isinstance(output, list)


class InformationExtractorAgent(Microagent[list[Finding]]):
    """
    Extracts findings from source content.

    Atomic task: Given source content, extract key claims and findings.
    """

    def __init__(self, llm_client: Any = None):
        super().__init__(agent_id="info_extractor", temperature=0.1)
        self.llm_client = llm_client

    async def execute(self, context: dict[str, Any]) -> list[Finding]:
        """Extract findings from source content."""
        self.call_count += 1

        source = context.get("source")
        query = context.get("query", "")

        if not source:
            return []

        # In production, would use LLM to extract claims
        # For now, create mock finding
        findings = [
            Finding(
                finding_id=f"finding_{source.source_id}",
                claim=f"Finding extracted from {source.title}",
                confidence=source.credibility_score,
                supporting_sources=[source.source_id],
            )
        ]

        return findings

    def validate_output(self, output: list[Finding]) -> bool:
        return isinstance(output, list)


class FactVerifierAgent(Microagent[bool]):
    """
    Verifies a finding against multiple sources.

    Atomic task: Given a finding, vote on its veracity.
    This is where MAKER's voting really shines - multiple agents
    independently verify claims.
    """

    def __init__(self, llm_client: Any = None):
        super().__init__(agent_id="fact_verifier", temperature=0.1)
        self.llm_client = llm_client

    async def execute(self, context: dict[str, Any]) -> bool:
        """Verify a finding."""
        self.call_count += 1

        finding = context.get("finding")
        supporting_content = context.get("supporting_content", [])

        if not finding:
            return False

        # In production, would use LLM to verify claim against sources
        # Multiple agents vote on verification using MAKER's voting

        # Simple mock: verify if confidence > 0.5
        return finding.confidence > 0.5

    def validate_output(self, output: bool) -> bool:
        return isinstance(output, bool)


class SynthesisAgent(Microagent[str]):
    """
    Synthesizes findings into coherent research output.

    Atomic task: Given verified findings, create synthesis.
    """

    def __init__(self, llm_client: Any = None):
        super().__init__(agent_id="synthesizer", temperature=0.3)
        self.llm_client = llm_client

    async def execute(self, context: dict[str, Any]) -> str:
        """Synthesize findings into research summary."""
        self.call_count += 1

        findings = context.get("findings", [])
        query = context.get("original_query", "")

        if not findings:
            return "No verified findings to synthesize."

        # In production, would use LLM to synthesize
        verified = [f for f in findings if f.verification_ratio > 0.5]

        synthesis = f"Research Summary for: {query}\n\n"
        synthesis += f"Found {len(verified)} verified findings:\n"

        for i, finding in enumerate(verified, 1):
            synthesis += f"\n{i}. {finding.claim} (confidence: {finding.confidence:.0%})"

        return synthesis

    def validate_output(self, output: str) -> bool:
        return isinstance(output, str) and len(output) > 0


class GapIdentifierAgent(Microagent[list[str]]):
    """
    Identifies gaps in research coverage.

    Atomic task: Given findings and query, identify what's missing.
    """

    def __init__(self, llm_client: Any = None):
        super().__init__(agent_id="gap_identifier", temperature=0.4)
        self.llm_client = llm_client

    async def execute(self, context: dict[str, Any]) -> list[str]:
        """Identify research gaps."""
        self.call_count += 1

        findings = context.get("findings", [])
        sub_queries = context.get("sub_queries", [])

        gaps = []

        # Check which sub-queries have no findings
        finding_topics = {f.claim.lower() for f in findings}

        for query in sub_queries:
            query_lower = query.lower()
            if not any(topic in query_lower or query_lower in topic for topic in finding_topics):
                gaps.append(f"No findings for: {query}")

        # Check for low-confidence areas
        low_confidence = [f for f in findings if f.confidence < 0.5]
        if low_confidence:
            gaps.append(f"{len(low_confidence)} findings need more verification")

        return gaps

    def validate_output(self, output: list[str]) -> bool:
        return isinstance(output, list)


class FollowUpGeneratorAgent(Microagent[list[str]]):
    """
    Generates follow-up research questions.

    Atomic task: Based on findings and gaps, suggest next questions.
    """

    def __init__(self, llm_client: Any = None):
        super().__init__(agent_id="followup_generator", temperature=0.5)
        self.llm_client = llm_client

    async def execute(self, context: dict[str, Any]) -> list[str]:
        """Generate follow-up questions."""
        self.call_count += 1

        findings = context.get("findings", [])
        gaps = context.get("gaps", [])
        original_query = context.get("original_query", "")

        follow_ups = []

        # Generate from gaps
        for gap in gaps[:3]:
            follow_ups.append(f"Deep dive: {gap}")

        # Generate from contradictions
        contradicted = [f for f in findings if f.contradicting_sources]
        for f in contradicted[:2]:
            follow_ups.append(f"Resolve contradiction: {f.claim}")

        # Generate expansion questions
        if findings:
            follow_ups.append(f"What are the implications of these findings?")
            follow_ups.append(f"How do these findings compare to prior work?")

        return follow_ups

    def validate_output(self, output: list[str]) -> bool:
        return isinstance(output, list)


# ============================================================================
# Research Task Decomposition
# ============================================================================


class ResearchDecomposer(TaskDecomposer):
    """
    Decomposes research tasks into atomic steps.

    Research pipeline:
    1. Decompose query into sub-queries
    2. Discover sources for each sub-query (parallel)
    3. Extract findings from each source (parallel)
    4. Verify each finding through voting
    5. Synthesize verified findings
    6. Identify gaps
    7. Generate follow-up questions
    """

    def decompose(self, task: dict[str, Any]) -> list[Step]:
        """Decompose research task into atomic steps."""
        query = task.get("query", ResearchQuery(
            query_id="default",
            question=task.get("question", ""),
        ))

        steps = []

        # Step 1: Query decomposition
        steps.append(Step(
            step_id=1,
            description="Decompose research question",
            context={
                "question": query.question,
                "research_type": query.research_type,
                "depth": query.depth,
            },
            dependencies=[]
        ))

        # Steps 2.x: Source discovery for each sub-query
        # (These will be created dynamically based on step 1 results)
        # For now, assume 5 sub-queries
        for i in range(5):
            steps.append(Step(
                step_id=100 + i,
                description=f"Discover sources for sub-query {i+1}",
                context={
                    "source_types": query.source_types,
                    "max_sources": query.required_sources,
                },
                dependencies=[1]
            ))

        # Steps 3.x: Information extraction from sources
        # Assume 3 sources per sub-query = 15 extraction steps
        for i in range(15):
            sub_query_idx = i // 3
            steps.append(Step(
                step_id=200 + i,
                description=f"Extract findings from source {i+1}",
                context={},
                dependencies=[100 + sub_query_idx]
            ))

        # Steps 4.x: Fact verification for each finding
        for i in range(15):
            steps.append(Step(
                step_id=300 + i,
                description=f"Verify finding {i+1}",
                context={},
                dependencies=[200 + i]
            ))

        # Step 5: Synthesis
        verification_deps = list(range(300, 315))
        steps.append(Step(
            step_id=400,
            description="Synthesize verified findings",
            context={"original_query": query.question},
            dependencies=verification_deps
        ))

        # Step 6: Gap identification
        steps.append(Step(
            step_id=500,
            description="Identify research gaps",
            context={},
            dependencies=[1, 400]
        ))

        # Step 7: Follow-up generation
        steps.append(Step(
            step_id=600,
            description="Generate follow-up questions",
            context={"original_query": query.question},
            dependencies=[400, 500]
        ))

        return steps

    def compose_result(self, steps: list[Step]) -> ResearchResult:
        """Compose research result from completed steps."""
        findings = []
        sources = []
        synthesis = ""
        gaps = []
        follow_ups = []

        for step in steps:
            if step.status != "completed":
                continue

            if 200 <= step.step_id < 300:
                # Extraction results
                if isinstance(step.result, list):
                    findings.extend(step.result)
            elif 100 <= step.step_id < 200:
                # Source discovery results
                if isinstance(step.result, list):
                    sources.extend(step.result)
            elif step.step_id == 400:
                synthesis = step.result or ""
            elif step.step_id == 500:
                gaps = step.result or []
            elif step.step_id == 600:
                follow_ups = step.result or []

        # Calculate overall confidence
        if findings:
            avg_confidence = sum(f.confidence for f in findings) / len(findings)
        else:
            avg_confidence = 0.0

        return ResearchResult(
            query=ResearchQuery(query_id="result", question=""),
            findings=findings,
            sources=sources,
            synthesis=synthesis,
            confidence=avg_confidence,
            gaps_identified=gaps,
            follow_up_questions=follow_ups,
        )


# Red-flag criteria specific to research
RESEARCH_RED_FLAG_CRITERIA = RedFlagCriteria(
    max_response_tokens=1000,  # Research needs more context
    max_response_length=5000,
    required_fields=[],
    forbidden_patterns=[
        "i made this up",
        "i'm not sure but",
        "i think maybe",
        "hallucination",
        "as an ai",
    ],
    min_confidence=0.3
)
