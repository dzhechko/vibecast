"""
MAKER Deep Research - Working Implementation

This module provides a fully functional deep research system using MAKER principles:
- Query decomposition into atomic sub-queries
- Parallel source discovery via web search
- Information extraction from search results
- Fact verification through MAKER voting
- Synthesis of verified findings
- Gap identification and follow-up generation

Usage:
    from maker.deep_research import DeepResearcher

    researcher = DeepResearcher()
    result = await researcher.research("Your research question here")
"""

import asyncio
import hashlib
import json
import re
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional
from enum import Enum
from collections import Counter
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# Data Models
# ============================================================================

class ConfidenceLevel(Enum):
    HIGH = "high"           # Multiple sources agree, verified
    MEDIUM = "medium"       # Some sources, partially verified
    LOW = "low"             # Single source or unverified
    SPECULATIVE = "speculative"  # Inference, not directly stated


@dataclass
class SearchResult:
    """Result from a web search."""
    title: str
    url: str
    snippet: str
    source_type: str = "web"
    credibility_score: float = 0.7

    def __hash__(self):
        return hash(self.url)


@dataclass
class Finding:
    """A research finding extracted from sources."""
    finding_id: str
    claim: str
    evidence: list[str]
    sources: list[SearchResult]
    confidence: ConfidenceLevel
    verification_votes: int = 0
    refutation_votes: int = 0

    @property
    def is_verified(self) -> bool:
        return self.verification_votes >= 3 and self.verification_votes > self.refutation_votes


@dataclass
class ResearchReport:
    """Complete research report."""
    question: str
    sub_queries: list[str]
    findings: list[Finding]
    synthesis: str
    gaps: list[str]
    follow_up_questions: list[str]
    sources_used: list[SearchResult]
    stats: dict
    timestamp: float = field(default_factory=time.time)


# ============================================================================
# Search Integration
# ============================================================================

class WebSearchClient:
    """
    Web search client abstraction.

    In production, this would call actual search APIs.
    For demo, it expects a search_fn to be provided.
    """

    def __init__(self, search_fn: Optional[Callable] = None):
        """
        Initialize search client.

        Args:
            search_fn: Async function that takes a query and returns search results.
                       Signature: async def search(query: str) -> list[dict]
        """
        self.search_fn = search_fn
        self.cache: dict[str, list[SearchResult]] = {}
        self.search_count = 0

    async def search(self, query: str, max_results: int = 10) -> list[SearchResult]:
        """Execute a web search."""
        # Check cache
        cache_key = hashlib.md5(query.encode()).hexdigest()
        if cache_key in self.cache:
            logger.info(f"Cache hit for: {query[:50]}...")
            return self.cache[cache_key]

        self.search_count += 1

        if self.search_fn:
            try:
                raw_results = await self.search_fn(query)
                results = [
                    SearchResult(
                        title=r.get("title", ""),
                        url=r.get("url", ""),
                        snippet=r.get("snippet", r.get("content", "")),
                        source_type=r.get("type", "web"),
                        credibility_score=r.get("credibility", 0.7)
                    )
                    for r in raw_results[:max_results]
                ]
            except Exception as e:
                logger.error(f"Search error: {e}")
                results = []
        else:
            # Demo mode - return empty
            logger.warning("No search function provided, returning empty results")
            results = []

        self.cache[cache_key] = results
        return results


# ============================================================================
# MAKER Voting Implementation
# ============================================================================

@dataclass
class Vote:
    """A single vote in the verification process."""
    value: bool  # True = verified, False = refuted
    confidence: float
    reasoning: str


class MAKERVoting:
    """
    First-to-ahead-by-k voting for fact verification.

    Based on MAKER paper: a claim is verified when it receives
    k more verification votes than refutation votes.
    """

    def __init__(self, k: int = 3, max_rounds: int = 10):
        self.k = k
        self.max_rounds = max_rounds

    async def verify(
        self,
        claim: str,
        evidence: list[str],
        vote_fn: Callable[[str, list[str]], Vote]
    ) -> tuple[bool, int, int]:
        """
        Verify a claim through voting.

        Args:
            claim: The claim to verify
            evidence: Supporting evidence
            vote_fn: Function that produces a vote given claim and evidence

        Returns:
            (is_verified, verification_votes, refutation_votes)
        """
        verify_count = 0
        refute_count = 0

        for round_num in range(self.max_rounds):
            # Get a vote
            vote = await asyncio.get_event_loop().run_in_executor(
                None, lambda: vote_fn(claim, evidence)
            )

            if vote.value:
                verify_count += 1
            else:
                refute_count += 1

            # Check if we have a winner
            if verify_count - refute_count >= self.k:
                return True, verify_count, refute_count
            if refute_count - verify_count >= self.k:
                return False, verify_count, refute_count

        # No clear winner - go with majority
        return verify_count > refute_count, verify_count, refute_count


# ============================================================================
# Research Agents
# ============================================================================

class QueryDecomposer:
    """Decomposes research questions into atomic sub-queries."""

    DECOMPOSITION_TEMPLATES = {
        "general": [
            "What is {topic}?",
            "What are the key components of {topic}?",
            "What are recent developments in {topic}?",
            "What are the main challenges with {topic}?",
            "What are expert opinions on {topic}?",
        ],
        "comparison": [
            "What are the options for {topic}?",
            "What are advantages of each approach to {topic}?",
            "What are disadvantages of each approach to {topic}?",
            "How do experts compare approaches to {topic}?",
        ],
        "technical": [
            "How does {topic} work technically?",
            "What is the architecture of {topic}?",
            "What are best practices for {topic}?",
            "What are common problems with {topic}?",
            "What tools are used for {topic}?",
        ],
        "market": [
            "What is the market size for {topic}?",
            "Who are the main players in {topic}?",
            "What are market trends in {topic}?",
            "What is the growth forecast for {topic}?",
            "What are investment trends in {topic}?",
        ],
    }

    def decompose(
        self,
        question: str,
        research_type: str = "general",
        max_queries: int = 5
    ) -> list[str]:
        """
        Decompose a question into sub-queries.

        Args:
            question: The main research question
            research_type: Type of research (general, comparison, technical, market)
            max_queries: Maximum number of sub-queries

        Returns:
            List of specific sub-queries
        """
        # Extract topic from question
        topic = self._extract_topic(question)

        # Get templates for research type
        templates = self.DECOMPOSITION_TEMPLATES.get(
            research_type,
            self.DECOMPOSITION_TEMPLATES["general"]
        )

        # Generate sub-queries
        sub_queries = []

        # Always include the original question
        sub_queries.append(question)

        # Add templated queries
        for template in templates[:max_queries - 1]:
            sub_queries.append(template.format(topic=topic))

        return sub_queries

    def _extract_topic(self, question: str) -> str:
        """Extract main topic from question."""
        # Remove common question words
        topic = question.lower()
        for word in ["what", "how", "why", "when", "where", "who", "is", "are", "the", "?"]:
            topic = topic.replace(word, " ")

        # Clean up
        topic = " ".join(topic.split())
        return topic if topic else question


class InformationExtractor:
    """Extracts findings from search results."""

    def extract(
        self,
        query: str,
        results: list[SearchResult]
    ) -> list[Finding]:
        """
        Extract findings from search results.

        Args:
            query: The search query
            results: Search results to extract from

        Returns:
            List of findings
        """
        findings = []

        for i, result in enumerate(results):
            if not result.snippet:
                continue

            # Create a finding from each substantial result
            finding = Finding(
                finding_id=f"finding_{hashlib.md5(result.url.encode()).hexdigest()[:8]}",
                claim=self._extract_claim(result.snippet),
                evidence=[result.snippet],
                sources=[result],
                confidence=self._assess_confidence(result),
            )

            findings.append(finding)

        return findings

    def _extract_claim(self, snippet: str) -> str:
        """Extract main claim from snippet."""
        # Take first sentence or first 200 chars
        sentences = snippet.split(".")
        if sentences:
            claim = sentences[0].strip()
            if len(claim) > 200:
                claim = claim[:200] + "..."
            return claim
        return snippet[:200]

    def _assess_confidence(self, result: SearchResult) -> ConfidenceLevel:
        """Assess confidence based on source."""
        score = result.credibility_score

        if score >= 0.8:
            return ConfidenceLevel.HIGH
        elif score >= 0.6:
            return ConfidenceLevel.MEDIUM
        elif score >= 0.4:
            return ConfidenceLevel.LOW
        else:
            return ConfidenceLevel.SPECULATIVE


class FactVerifier:
    """Verifies findings using MAKER voting."""

    def __init__(self, voting_k: int = 3):
        self.voting = MAKERVoting(k=voting_k)

    def create_vote_fn(self, all_findings: list[Finding]):
        """
        Create a voting function based on cross-referencing findings.

        The vote function checks:
        1. Evidence quality (snippet length, credibility)
        2. Cross-reference support from other findings
        3. Source credibility score
        """
        def vote_fn(claim: str, evidence: list[str]) -> Vote:
            import random

            # Base score from evidence quality
            evidence_score = 0.0
            if evidence:
                avg_length = sum(len(e) for e in evidence) / len(evidence)
                evidence_score = min(1.0, avg_length / 100)  # 100 chars = full score

            # Cross-reference score
            claim_words = set(claim.lower().split())
            # Remove common words
            claim_words -= {"the", "a", "an", "is", "are", "of", "for", "to", "in", "and", "with"}
            support_count = 0

            for finding in all_findings:
                if finding.claim == claim:
                    continue

                finding_words = set(finding.claim.lower().split())
                finding_words -= {"the", "a", "an", "is", "are", "of", "for", "to", "in", "and", "with"}

                # Check for any meaningful overlap
                overlap = len(claim_words & finding_words)
                if overlap >= 2:  # At least 2 meaningful words overlap
                    support_count += 1

            cross_ref_score = min(1.0, support_count * 0.3)

            # Find this claim's source credibility
            source_score = 0.5
            for finding in all_findings:
                if finding.claim == claim and finding.sources:
                    source_score = max(s.credibility_score for s in finding.sources)
                    break

            # Combined score with some randomness (simulating multiple agents)
            combined_score = (
                evidence_score * 0.3 +
                cross_ref_score * 0.3 +
                source_score * 0.3 +
                random.uniform(0, 0.1)  # Agent variation
            )

            # Verify if score above threshold
            verified = combined_score >= 0.5

            return Vote(
                value=verified,
                confidence=combined_score,
                reasoning=f"Evidence: {evidence_score:.2f}, CrossRef: {cross_ref_score:.2f} ({support_count} matches), Source: {source_score:.2f}"
            )

        return vote_fn

    async def verify_findings(
        self,
        findings: list[Finding]
    ) -> list[Finding]:
        """
        Verify all findings using MAKER voting.

        Args:
            findings: List of findings to verify

        Returns:
            Findings with verification status updated
        """
        vote_fn = self.create_vote_fn(findings)

        for finding in findings:
            verified, v_count, r_count = await self.voting.verify(
                finding.claim,
                finding.evidence,
                vote_fn
            )

            finding.verification_votes = v_count
            finding.refutation_votes = r_count

        return findings


class Synthesizer:
    """Synthesizes findings into coherent summary."""

    def synthesize(
        self,
        question: str,
        findings: list[Finding]
    ) -> str:
        """
        Synthesize findings into a summary.

        Args:
            question: Original research question
            findings: Verified findings

        Returns:
            Synthesized summary
        """
        if not findings:
            return f"No verified findings for: {question}"

        # Group findings by confidence
        high_conf = [f for f in findings if f.confidence == ConfidenceLevel.HIGH and f.is_verified]
        medium_conf = [f for f in findings if f.confidence == ConfidenceLevel.MEDIUM and f.is_verified]
        other = [f for f in findings if f not in high_conf and f not in medium_conf and f.is_verified]

        # Build synthesis
        parts = []
        parts.append(f"## Research Summary: {question}\n")

        if high_conf:
            parts.append("\n### High Confidence Findings\n")
            for f in high_conf[:5]:
                parts.append(f"- {f.claim}")
                parts.append(f"  (Verified: {f.verification_votes} votes, Sources: {len(f.sources)})\n")

        if medium_conf:
            parts.append("\n### Medium Confidence Findings\n")
            for f in medium_conf[:5]:
                parts.append(f"- {f.claim}")
                parts.append(f"  (Verified: {f.verification_votes} votes)\n")

        if other:
            parts.append("\n### Additional Findings\n")
            for f in other[:3]:
                parts.append(f"- {f.claim}\n")

        # Statistics
        total = len(findings)
        verified = len([f for f in findings if f.is_verified])
        parts.append(f"\n### Statistics\n")
        parts.append(f"- Total findings: {total}\n")
        parts.append(f"- Verified (MAKER k=3): {verified}\n")
        parts.append(f"- Verification rate: {verified/total*100:.1f}%\n")

        return "".join(parts)


class GapIdentifier:
    """Identifies gaps in research coverage."""

    def identify_gaps(
        self,
        sub_queries: list[str],
        findings: list[Finding]
    ) -> list[str]:
        """
        Identify gaps in research coverage.

        Args:
            sub_queries: Original sub-queries
            findings: All findings

        Returns:
            List of identified gaps
        """
        gaps = []

        # Check which queries have no findings
        finding_text = " ".join(f.claim.lower() for f in findings)

        for query in sub_queries:
            query_words = set(query.lower().split())
            # Remove common words
            query_words -= {"what", "how", "why", "is", "are", "the", "a", "an", "?"}

            # Check if query concepts appear in findings
            matches = sum(1 for word in query_words if word in finding_text)

            if matches < len(query_words) * 0.3:  # Less than 30% coverage
                gaps.append(f"Limited coverage: {query}")

        # Check for low verification rate
        verified = [f for f in findings if f.is_verified]
        if len(verified) < len(findings) * 0.5:
            gaps.append("Low verification rate - findings may need more sources")

        return gaps


class FollowUpGenerator:
    """Generates follow-up research questions."""

    def generate(
        self,
        question: str,
        findings: list[Finding],
        gaps: list[str]
    ) -> list[str]:
        """
        Generate follow-up questions.

        Args:
            question: Original question
            findings: Research findings
            gaps: Identified gaps

        Returns:
            List of follow-up questions
        """
        follow_ups = []

        # Generate from gaps
        for gap in gaps[:2]:
            if "Limited coverage" in gap:
                topic = gap.replace("Limited coverage:", "").strip()
                follow_ups.append(f"Deep dive: {topic}")

        # Generate from low-confidence findings
        low_conf = [f for f in findings if f.confidence in [ConfidenceLevel.LOW, ConfidenceLevel.SPECULATIVE]]
        for f in low_conf[:2]:
            follow_ups.append(f"Verify: {f.claim[:100]}...")

        # Standard follow-ups
        follow_ups.extend([
            f"What are the implications of these findings?",
            f"What do critics say about {question[:50]}...?",
        ])

        return follow_ups[:5]


# ============================================================================
# Main Deep Researcher
# ============================================================================

class DeepResearcher:
    """
    MAKER-based Deep Research System.

    Orchestrates the full research pipeline with voting-based verification.
    """

    def __init__(
        self,
        search_client: Optional[WebSearchClient] = None,
        voting_k: int = 3,
        max_sub_queries: int = 5
    ):
        """
        Initialize the researcher.

        Args:
            search_client: Web search client
            voting_k: K threshold for MAKER voting
            max_sub_queries: Maximum sub-queries to generate
        """
        self.search_client = search_client or WebSearchClient()
        self.voting_k = voting_k
        self.max_sub_queries = max_sub_queries

        # Initialize agents
        self.decomposer = QueryDecomposer()
        self.extractor = InformationExtractor()
        self.verifier = FactVerifier(voting_k=voting_k)
        self.synthesizer = Synthesizer()
        self.gap_identifier = GapIdentifier()
        self.followup_generator = FollowUpGenerator()

        # Stats
        self.stats = {
            "total_searches": 0,
            "total_findings": 0,
            "verified_findings": 0,
            "duration_ms": 0
        }

    async def research(
        self,
        question: str,
        research_type: str = "general",
        verbose: bool = True
    ) -> ResearchReport:
        """
        Execute deep research on a question.

        Args:
            question: The research question
            research_type: Type of research (general, comparison, technical, market)
            verbose: Print progress

        Returns:
            Complete research report
        """
        start_time = time.time()

        if verbose:
            print(f"\n{'='*60}")
            print(f"MAKER Deep Research")
            print(f"Question: {question}")
            print(f"{'='*60}\n")

        # Step 1: Decompose query
        if verbose:
            print("📋 Step 1: Decomposing query...")

        sub_queries = self.decomposer.decompose(
            question,
            research_type,
            self.max_sub_queries
        )

        if verbose:
            for i, q in enumerate(sub_queries, 1):
                print(f"   {i}. {q}")

        # Step 2: Search for each sub-query (parallel)
        if verbose:
            print(f"\n🔍 Step 2: Searching ({len(sub_queries)} queries)...")

        search_tasks = [
            self.search_client.search(query)
            for query in sub_queries
        ]
        all_results = await asyncio.gather(*search_tasks)

        # Flatten and deduplicate results
        seen_urls = set()
        unique_results = []
        for results in all_results:
            for result in results:
                if result.url not in seen_urls:
                    seen_urls.add(result.url)
                    unique_results.append(result)

        self.stats["total_searches"] = len(sub_queries)

        if verbose:
            print(f"   Found {len(unique_results)} unique sources")

        # Step 3: Extract findings
        if verbose:
            print(f"\n📝 Step 3: Extracting findings...")

        all_findings = []
        for i, (query, results) in enumerate(zip(sub_queries, all_results)):
            findings = self.extractor.extract(query, results)
            all_findings.extend(findings)

        self.stats["total_findings"] = len(all_findings)

        if verbose:
            print(f"   Extracted {len(all_findings)} findings")

        # Step 4: Verify findings with MAKER voting
        if verbose:
            print(f"\n✅ Step 4: MAKER Voting (k={self.voting_k})...")

        verified_findings = await self.verifier.verify_findings(all_findings)

        verified_count = len([f for f in verified_findings if f.is_verified])
        self.stats["verified_findings"] = verified_count

        if verbose:
            print(f"   Verified: {verified_count}/{len(all_findings)} findings")

        # Step 5: Synthesize
        if verbose:
            print(f"\n📊 Step 5: Synthesizing...")

        synthesis = self.synthesizer.synthesize(question, verified_findings)

        # Step 6: Identify gaps
        if verbose:
            print(f"\n🔎 Step 6: Identifying gaps...")

        gaps = self.gap_identifier.identify_gaps(sub_queries, verified_findings)

        if verbose and gaps:
            for gap in gaps:
                print(f"   - {gap}")

        # Step 7: Generate follow-ups
        if verbose:
            print(f"\n❓ Step 7: Generating follow-up questions...")

        follow_ups = self.followup_generator.generate(
            question, verified_findings, gaps
        )

        if verbose:
            for q in follow_ups:
                print(f"   - {q}")

        # Finalize
        duration_ms = (time.time() - start_time) * 1000
        self.stats["duration_ms"] = duration_ms

        if verbose:
            print(f"\n{'='*60}")
            print(f"Research complete in {duration_ms:.0f}ms")
            print(f"{'='*60}\n")

        return ResearchReport(
            question=question,
            sub_queries=sub_queries,
            findings=verified_findings,
            synthesis=synthesis,
            gaps=gaps,
            follow_up_questions=follow_ups,
            sources_used=unique_results,
            stats=self.stats.copy()
        )


# ============================================================================
# CLI Runner
# ============================================================================

async def run_research(
    question: str,
    search_results: Optional[list[dict]] = None,
    research_type: str = "general"
) -> ResearchReport:
    """
    Run research with provided search results.

    Args:
        question: Research question
        search_results: Optional pre-fetched search results
        research_type: Type of research

    Returns:
        Research report
    """
    # Create search function from provided results
    if search_results:
        async def search_fn(query: str) -> list[dict]:
            # Filter results that match query
            return [r for r in search_results if any(
                word.lower() in r.get("snippet", "").lower()
                for word in query.split()
            )][:10]
    else:
        search_fn = None

    search_client = WebSearchClient(search_fn=search_fn)
    researcher = DeepResearcher(search_client=search_client)

    return await researcher.research(question, research_type)


def format_report(report: ResearchReport) -> str:
    """Format research report for display."""
    output = []
    output.append(f"\n{'#'*60}")
    output.append(f"# MAKER Deep Research Report")
    output.append(f"{'#'*60}\n")

    output.append(f"**Question:** {report.question}\n")
    output.append(f"**Generated:** {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(report.timestamp))}\n")

    output.append("\n## Sub-Queries Explored\n")
    for i, q in enumerate(report.sub_queries, 1):
        output.append(f"{i}. {q}")

    output.append("\n## Synthesis\n")
    output.append(report.synthesis)

    if report.gaps:
        output.append("\n## Research Gaps\n")
        for gap in report.gaps:
            output.append(f"- {gap}")

    if report.follow_up_questions:
        output.append("\n## Suggested Follow-Up Questions\n")
        for q in report.follow_up_questions:
            output.append(f"- {q}")

    output.append("\n## Statistics\n")
    output.append(f"- Searches performed: {report.stats.get('total_searches', 0)}")
    output.append(f"- Total findings: {report.stats.get('total_findings', 0)}")
    output.append(f"- Verified findings: {report.stats.get('verified_findings', 0)}")
    output.append(f"- Duration: {report.stats.get('duration_ms', 0):.0f}ms")
    output.append(f"- Sources used: {len(report.sources_used)}")

    return "\n".join(output)


# Example usage
if __name__ == "__main__":
    async def main():
        # Example with mock search results
        mock_results = [
            {
                "title": "AI Market Report 2024",
                "url": "https://example.com/ai-report",
                "snippet": "The global AI market reached $150 billion in 2024, with 35% growth.",
            },
            {
                "title": "Machine Learning Trends",
                "url": "https://example.com/ml-trends",
                "snippet": "Generative AI adoption exceeded 80% in enterprise by 2024.",
            },
        ]

        report = await run_research(
            "What are the latest AI market trends?",
            search_results=mock_results,
            research_type="market"
        )

        print(format_report(report))

    asyncio.run(main())
