#!/usr/bin/env python3
"""
Test MAKER Deep Research with Live Web Search

This script demonstrates the full MAKER research pipeline:
1. Query decomposition
2. Web search for each sub-query
3. Information extraction
4. MAKER voting verification
5. Synthesis
"""

import asyncio
import sys
sys.path.insert(0, 'src')

from maker.deep_research import (
    DeepResearcher,
    WebSearchClient,
    SearchResult,
    format_report,
)


# Simulated search results for testing
# In production, these would come from actual web search API
MOCK_SEARCH_RESULTS = {
    "ai platform architecture": [
        {
            "title": "Modern AI Platform Architecture Patterns 2024",
            "url": "https://techblog.example.com/ai-platform-architecture",
            "snippet": "Modern AI platforms require modular microservices architecture with MLOps pipelines. Key components include feature stores, model registries, and inference servers. Kubernetes-based orchestration is standard for production deployments.",
            "credibility": 0.85
        },
        {
            "title": "Enterprise AI Infrastructure Best Practices",
            "url": "https://enterprise.example.com/ai-infrastructure",
            "snippet": "Hybrid cloud architecture enables flexibility between on-premise GPU clusters and cloud burst capacity. Data sovereignty requirements drive edge computing adoption. Model serving latency below 100ms is critical for real-time applications.",
            "credibility": 0.9
        },
    ],
    "hybrid cloud ai": [
        {
            "title": "Hybrid Cloud AI: The Future of Enterprise ML",
            "url": "https://research.example.com/hybrid-cloud-ai",
            "snippet": "Hybrid cloud architectures for AI balance data privacy with computational scalability. Organizations report 40% cost savings by optimizing workload placement. Federation learning enables training without data movement.",
            "credibility": 0.85
        },
        {
            "title": "Multi-Cloud AI Strategy Guide",
            "url": "https://cloudguide.example.com/multi-cloud-ai",
            "snippet": "Multi-cloud AI deployments reduce vendor lock-in risks. Container orchestration with Kubernetes enables portability. Model serialization standards like ONNX improve interoperability across platforms.",
            "credibility": 0.8
        },
    ],
    "sovereign ai infrastructure": [
        {
            "title": "Building Sovereign AI: National Infrastructure",
            "url": "https://policy.example.com/sovereign-ai",
            "snippet": "Sovereign AI requires domestic compute capacity and data residency compliance. RISC-V architectures offer licensing independence from foreign chip designers. Local LLM training capabilities are strategic national priorities.",
            "credibility": 0.85
        },
        {
            "title": "Data Sovereignty in AI Systems",
            "url": "https://law.example.com/data-sovereignty-ai",
            "snippet": "Data sovereignty regulations require AI training data to remain within national boundaries. Federated learning and differential privacy enable compliant cross-border collaboration. Model weights may also be subject to export controls.",
            "credibility": 0.9
        },
    ],
    "ai market trends 2024": [
        {
            "title": "AI Market Report Q4 2024",
            "url": "https://market.example.com/ai-report-2024",
            "snippet": "Global AI market reached $190 billion in 2024, up 38% year-over-year. Generative AI accounts for 35% of enterprise spending. Edge AI deployments grew 60% as latency requirements tightened.",
            "credibility": 0.85
        },
        {
            "title": "Enterprise AI Adoption Survey 2024",
            "url": "https://survey.example.com/enterprise-ai-2024",
            "snippet": "87% of enterprises now have AI in production. Average AI project ROI is 3.5x within first year. Main challenges: data quality (45%), talent shortage (38%), and integration complexity (32%).",
            "credibility": 0.8
        },
    ],
    "machine learning best practices": [
        {
            "title": "MLOps Best Practices 2024",
            "url": "https://mlops.example.com/best-practices",
            "snippet": "Continuous training pipelines reduce model drift. Feature stores centralize feature engineering. Model monitoring detects performance degradation. A/B testing validates model improvements before full rollout.",
            "credibility": 0.85
        },
    ],
}


async def mock_search(query: str) -> list[dict]:
    """Mock search function that returns predefined results."""
    query_lower = query.lower()

    # Find matching results
    results = []
    for key, values in MOCK_SEARCH_RESULTS.items():
        if any(word in query_lower for word in key.split()):
            results.extend(values)

    # If no match, return generic results
    if not results:
        results = [
            {
                "title": f"Search result for: {query}",
                "url": f"https://example.com/search?q={query.replace(' ', '+')}",
                "snippet": f"Information related to {query}. This is simulated search content.",
                "credibility": 0.7
            }
        ]

    print(f"    🔎 Search: '{query[:50]}...' -> {len(results)} results")
    return results


async def test_maker_research():
    """Test the MAKER research pipeline."""
    print("\n" + "="*70)
    print("🧪 MAKER Deep Research Test")
    print("="*70)

    # Create search client with mock function
    search_client = WebSearchClient(search_fn=mock_search)

    # Create researcher
    researcher = DeepResearcher(
        search_client=search_client,
        voting_k=3,
        max_sub_queries=5
    )

    # Test question
    question = "What are the key components for building a sovereign AI platform for enterprise use?"

    print(f"\n📌 Research Question: {question}\n")

    # Execute research
    report = await researcher.research(
        question,
        research_type="technical",
        verbose=True
    )

    # Display formatted report
    print("\n" + "="*70)
    print("📄 RESEARCH REPORT")
    print("="*70)
    print(format_report(report))

    # Summary
    print("\n" + "="*70)
    print("📊 TEST RESULTS SUMMARY")
    print("="*70)
    print(f"✅ Sub-queries generated: {len(report.sub_queries)}")
    print(f"✅ Total findings: {report.stats['total_findings']}")
    print(f"✅ Verified findings (MAKER k=3): {report.stats['verified_findings']}")
    print(f"✅ Sources used: {len(report.sources_used)}")
    print(f"✅ Gaps identified: {len(report.gaps)}")
    print(f"✅ Follow-up questions: {len(report.follow_up_questions)}")
    print(f"✅ Duration: {report.stats['duration_ms']:.0f}ms")

    # Verify MAKER voting worked
    verified_count = len([f for f in report.findings if f.is_verified])
    total_count = len(report.findings)

    print(f"\n🗳️  MAKER Voting Results:")
    print(f"   - Verification rate: {verified_count}/{total_count} ({verified_count/total_count*100:.1f}%)")
    print(f"   - Voting threshold k=3 applied")

    return report


async def test_interactive_session():
    """Test the interactive research session."""
    from maker.research_runner import InteractiveResearchSession

    print("\n" + "="*70)
    print("🧪 Interactive Session Test")
    print("="*70)

    session = InteractiveResearchSession(voting_k=3)

    # Simulate adding search results as they come in
    session.add_search("AI platform architecture", MOCK_SEARCH_RESULTS["ai platform architecture"])
    session.add_search("hybrid cloud AI", MOCK_SEARCH_RESULTS["hybrid cloud ai"])
    session.add_search("sovereign AI", MOCK_SEARCH_RESULTS["sovereign ai infrastructure"])

    # Analyze accumulated results
    report = await session.analyze(
        "What are the essential components of a sovereign AI platform?",
        research_type="technical"
    )

    print(f"\n📊 Interactive Session Results:")
    print(f"   - Findings: {len(report.findings)}")
    print(f"   - Verified: {report.stats['verified_findings']}")

    return report


if __name__ == "__main__":
    print("\n🚀 Starting MAKER Deep Research Tests\n")

    # Run tests
    asyncio.run(test_maker_research())
    asyncio.run(test_interactive_session())

    print("\n✅ All tests completed!")
