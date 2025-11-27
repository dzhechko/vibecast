#!/usr/bin/env python3
"""
MAKER Research Runner - Live Web Search Integration

This script demonstrates the MAKER research system with real web search.
It can be used both programmatically and as a CLI tool.

Usage:
    # As a module
    from maker.research_runner import MAKERResearchRunner
    runner = MAKERResearchRunner()
    report = await runner.run("Your question here")

    # As CLI
    python -m maker.research_runner "Your question here"
"""

import asyncio
import json
import sys
import time
from dataclasses import dataclass, asdict
from typing import Any, Optional, Callable
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from maker.deep_research import (
    DeepResearcher,
    WebSearchClient,
    SearchResult,
    ResearchReport,
    format_report,
)


@dataclass
class WebSearchResponse:
    """Parsed web search response."""
    results: list[dict]
    query: str
    raw_content: str = ""


class MAKERResearchRunner:
    """
    Production-ready MAKER research runner.

    Integrates with external search APIs and provides
    comprehensive research reports.
    """

    def __init__(
        self,
        search_provider: Optional[Callable] = None,
        voting_k: int = 3,
        max_queries: int = 5,
        verbose: bool = True
    ):
        """
        Initialize the research runner.

        Args:
            search_provider: Async function for web search
                             Signature: async def search(query: str) -> list[dict]
            voting_k: MAKER voting threshold
            max_queries: Maximum sub-queries to explore
            verbose: Print progress
        """
        self.search_provider = search_provider
        self.voting_k = voting_k
        self.max_queries = max_queries
        self.verbose = verbose

        # Search history for this session
        self.search_history: list[dict] = []

    def log(self, message: str):
        """Log message if verbose."""
        if self.verbose:
            print(message)

    async def run(
        self,
        question: str,
        research_type: str = "general",
        provided_searches: Optional[list[dict]] = None
    ) -> ResearchReport:
        """
        Run deep research on a question.

        Args:
            question: The research question
            research_type: Type (general, technical, market, comparison)
            provided_searches: Pre-fetched search results (if available)

        Returns:
            Complete research report
        """
        start_time = time.time()

        self.log(f"\n{'='*70}")
        self.log(f"🔬 MAKER Deep Research System")
        self.log(f"{'='*70}")
        self.log(f"\n📌 Question: {question}")
        self.log(f"📊 Type: {research_type}")
        self.log(f"🗳️ Voting threshold (k): {self.voting_k}")
        self.log(f"{'='*70}\n")

        # Create search client
        if provided_searches:
            # Use provided search results
            search_data = provided_searches
            async def search_fn(query: str) -> list[dict]:
                # Match provided results to query
                return self._filter_results(search_data, query)
        elif self.search_provider:
            # Use external search provider
            async def search_fn(query: str) -> list[dict]:
                return await self.search_provider(query)
        else:
            # No search available - demo mode
            self.log("⚠️ No search provider - running in demo mode")
            search_fn = None

        search_client = WebSearchClient(search_fn=search_fn)

        # Create researcher
        researcher = DeepResearcher(
            search_client=search_client,
            voting_k=self.voting_k,
            max_sub_queries=self.max_queries
        )

        # Execute research
        report = await researcher.research(
            question,
            research_type=research_type,
            verbose=self.verbose
        )

        # Log completion
        duration = time.time() - start_time
        self.log(f"\n✅ Research completed in {duration:.2f}s")
        self.log(f"📈 Findings: {report.stats.get('verified_findings', 0)} verified / {report.stats.get('total_findings', 0)} total")

        return report

    def _filter_results(self, all_results: list[dict], query: str) -> list[dict]:
        """Filter search results relevant to query."""
        query_words = set(query.lower().split())
        # Remove common words
        query_words -= {"what", "how", "why", "is", "are", "the", "a", "an", "?", "of", "in", "for"}

        scored_results = []
        for result in all_results:
            text = (
                result.get("title", "") + " " +
                result.get("snippet", "") + " " +
                result.get("content", "")
            ).lower()

            score = sum(1 for word in query_words if word in text)
            if score > 0:
                scored_results.append((score, result))

        # Sort by score and return top results
        scored_results.sort(key=lambda x: x[0], reverse=True)
        return [r for _, r in scored_results[:10]]

    def add_search_results(self, query: str, results: list[dict]):
        """Add search results to history."""
        self.search_history.append({
            "query": query,
            "results": results,
            "timestamp": time.time()
        })

    def get_all_search_results(self) -> list[dict]:
        """Get all accumulated search results."""
        all_results = []
        seen_urls = set()

        for search in self.search_history:
            for result in search.get("results", []):
                url = result.get("url", "")
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    all_results.append(result)

        return all_results


def parse_web_search_output(raw_output: str) -> list[dict]:
    """
    Parse raw web search output into structured results.

    Handles various formats from search tools.
    """
    results = []

    # Try to find URL patterns
    import re

    # Pattern for markdown links [title](url)
    md_links = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', raw_output)
    for title, url in md_links:
        results.append({
            "title": title,
            "url": url,
            "snippet": ""
        })

    # Extract text content near URLs as snippets
    lines = raw_output.split('\n')
    for i, line in enumerate(lines):
        if 'http' in line:
            # Find surrounding context
            context_start = max(0, i - 2)
            context_end = min(len(lines), i + 3)
            context = ' '.join(lines[context_start:context_end])

            # Update snippet for matching result
            for result in results:
                if result['url'] in line:
                    result['snippet'] = context[:500]

    return results


# ============================================================================
# Interactive Session
# ============================================================================

class InteractiveResearchSession:
    """
    Interactive research session that accumulates search results.

    Usage:
        session = InteractiveResearchSession()

        # Add search results as they come in
        session.add_search("query 1", [results...])
        session.add_search("query 2", [results...])

        # Run analysis when ready
        report = await session.analyze("main question")
    """

    def __init__(self, voting_k: int = 3):
        self.runner = MAKERResearchRunner(voting_k=voting_k)
        self.searches: list[dict] = []

    def add_search(self, query: str, results: list[dict]):
        """Add search results."""
        self.searches.append({
            "query": query,
            "results": results
        })
        print(f"✅ Added {len(results)} results for: {query[:50]}...")

    async def analyze(
        self,
        question: str,
        research_type: str = "general"
    ) -> ResearchReport:
        """Analyze accumulated search results."""
        # Flatten all results
        all_results = []
        for search in self.searches:
            all_results.extend(search.get("results", []))

        return await self.runner.run(
            question,
            research_type=research_type,
            provided_searches=all_results
        )

    def clear(self):
        """Clear accumulated searches."""
        self.searches = []
        print("🗑️ Session cleared")


# ============================================================================
# Example with Mock Data
# ============================================================================

async def demo_research():
    """Demonstrate research with mock data."""

    # Mock search results simulating real web search
    mock_results = [
        {
            "title": "BRICS AI Alliance Launched at AI Journey 2024",
            "url": "https://example.com/brics-ai",
            "snippet": "In December 2024, the BRICS+ AI Alliance was launched in Moscow with 20+ tech companies from 6 countries.",
            "credibility": 0.9
        },
        {
            "title": "Russian AI Market Reaches 900 Billion Rubles",
            "url": "https://example.com/russian-ai-market",
            "snippet": "The Russian AI market exceeded 900 billion rubles in 2024, showing 36.6% year-over-year growth.",
            "credibility": 0.85
        },
        {
            "title": "GigaChat vs YandexGPT Comparison 2024",
            "url": "https://example.com/gigachat-yandex",
            "snippet": "YandexGPT 5 Pro is comparable to GPT-4o for Russian language tasks. GigaChat focuses on safety and multimodality.",
            "credibility": 0.8
        },
        {
            "title": "Saudi Arabia Launches $100B AI Initiative",
            "url": "https://example.com/saudi-ai",
            "snippet": "Project Transcendence aims to invest $100 billion in AI, positioning Saudi Arabia as a global AI hub.",
            "credibility": 0.85
        },
        {
            "title": "UAE G42 AI Infrastructure Investment",
            "url": "https://example.com/uae-g42",
            "snippet": "MGX, backed by Mubadala and G42, plans $100 billion investment in AI infrastructure and technologies.",
            "credibility": 0.85
        },
        {
            "title": "Federated Learning for Data Sovereignty",
            "url": "https://example.com/federated-learning",
            "snippet": "Federated learning enables AI training without raw data leaving regional boundaries, ensuring data sovereignty.",
            "credibility": 0.8
        },
        {
            "title": "Huawei Ascend AI Chips for Russian Market",
            "url": "https://example.com/huawei-ascend",
            "snippet": "Huawei Ascend chips are becoming the primary AI accelerator option for Russian enterprises under sanctions.",
            "credibility": 0.75
        },
        {
            "title": "RISC-V Architecture for Sovereign Computing",
            "url": "https://example.com/risc-v-russia",
            "snippet": "Russia plans transition to RISC-V architecture for Baikal processors to reduce dependency on ARM licensing.",
            "credibility": 0.7
        }
    ]

    # Create session and add results
    session = InteractiveResearchSession(voting_k=3)

    # Simulate multiple searches
    session.add_search("BRICS AI cooperation", mock_results[:3])
    session.add_search("Middle East AI investment", mock_results[3:5])
    session.add_search("sovereign AI infrastructure", mock_results[5:8])

    # Run analysis
    report = await session.analyze(
        "What are the key components for building a sovereign AI platform for BRICS+ regions?",
        research_type="technical"
    )

    # Print report
    print("\n" + format_report(report))

    return report


# ============================================================================
# CLI Entry Point
# ============================================================================

if __name__ == "__main__":
    if len(sys.argv) > 1:
        question = " ".join(sys.argv[1:])
        print(f"Research question: {question}")
        print("Note: Running demo with mock data. For real search, use as a module.")

    asyncio.run(demo_research())
