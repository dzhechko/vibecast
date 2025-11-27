# Vibecast

**MAKER-Powered Entertainment Discovery Platform**

Solving the "45-minute decision problem" - helping users find what to watch across fragmented streaming platforms.

## Overview

Vibecast implements the [MAKER framework](https://arxiv.org/abs/2511.09030) for reliable, scalable AI-powered content recommendations:

- **M**aximal **A**gentic decomposition - Break complex tasks into atomic steps
- **K**-threshold **E**rror mitigation - Voting-based consensus for reliability
- **R**ed-flagging - Filter malformed or low-quality responses

## Key Features

- 🎯 **Mood-based recommendations** - Analyzes user intent and mood
- 🗳️ **Consensus voting** - First-to-ahead-by-k algorithm ensures accuracy
- 🚩 **Quality filtering** - Red-flagging removes problematic responses
- 📊 **Benchmarking tools** - Measure and optimize performance
- ⚡ **Scalable architecture** - Microagent design for parallel execution

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        User Query                                │
│                  "Something relaxing tonight"                    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Task Decomposition (MAD)                      │
│   Break into atomic steps: mood → genres → duration → score     │
└─────────────────────────────────────────────────────────────────┘
                              │
          ┌───────────────────┼───────────────────┐
          ▼                   ▼                   ▼
    ┌──────────┐       ┌──────────┐       ┌──────────┐
    │  Mood    │       │  Genre   │       │ Duration │
    │ Analyzer │       │ Matcher  │       │  Filter  │
    └──────────┘       └──────────┘       └──────────┘
          │                   │                   │
          └───────────────────┼───────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Content Scoring                               │
│              (Parallel microagents per item)                     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                  First-to-ahead-by-k Voting                      │
│        Multiple agents vote → consensus when k ahead             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Recommendations                              │
│        [Movie A (8.5★), Show B (8.2★), Movie C (8.0★)]          │
└─────────────────────────────────────────────────────────────────┘
```

## Installation

```bash
cd vibecast
pip install -r requirements.txt
```

## Quick Start

```python
import asyncio
from src.maker import recommend

async def main():
    candidates = [
        {"id": "1", "title": "Action Movie", "type": "movie",
         "genres": ["action"], "rating": 8.5, "platform": "netflix"},
        {"id": "2", "title": "Romance Film", "type": "movie",
         "genres": ["romance"], "rating": 7.8, "platform": "hulu"},
    ]

    response = await recommend(
        query="I want something exciting to watch",
        candidates=candidates,
        preferences={"platforms": ["netflix", "hulu"]}
    )

    print(f"Recommendations: {response.recommendations}")
    print(f"Detected mood: {response.mood}")

asyncio.run(main())
```

## Configuration

```python
from src.maker import MAKERConfig, VibecastMAKER

config = MAKERConfig(
    voting=VotingConfig(k=3),      # Voting threshold
    llm=LLMConfig(
        model="gpt-4o-mini",       # Cost-effective model
        temperature=0.1            # Low for consistency
    )
)

engine = VibecastMAKER(config)
```

### Preset Configurations

| Config | Use Case | k | Temperature |
|--------|----------|---|-------------|
| `DEVELOPMENT_CONFIG` | Testing | 2 | 0.3 |
| `PRODUCTION_CONFIG` | Production | 3 | 0.1 |
| `HIGH_ACCURACY_CONFIG` | Critical | 5 | 0.05 |
| `COST_OPTIMIZED_CONFIG` | Budget | 2 | 0.1 |

## Benchmarking

```python
from src.maker import VotingOptimizer

optimizer = VotingOptimizer(target_success_rate=0.9999)

# Calculate optimal k for your accuracy and task size
k = optimizer.calculate_optimal_k(
    per_step_accuracy=0.92,
    total_steps=100
)

# Estimate costs
cost = optimizer.estimate_cost(k, 0.92, 100, cost_per_vote=0.001)
print(f"Expected cost: ${cost['expected_cost']:.4f}")
```

## MAKER Paper Key Insights

From ["Solving a Million-Step LLM Task with Zero Errors"](https://arxiv.org/abs/2511.09030):

1. **Smaller models win on cost-efficiency** - GPT-4o-mini outperforms reasoning models on reliability-per-dollar
2. **k grows logarithmically** - k_min = Θ(ln s), so scaling is feasible
3. **Red-flagging reduces correlated errors** - Filter long/malformed outputs
4. **Voting converges exponentially** - Most steps decided in first few rounds

### Key Equations

**Per-step success probability:**
```
p(correct) = 1 / (1 + ((1-p)/p)^k)
```

**Minimum k for target success rate t:**
```
k_min = ⌈ln(t^(-1/s) - 1) / ln((1-p)/p)⌉
```

**Expected cost:**
```
E[cost] = Θ(s × ln(s))
```

## Project Structure

```
vibecast/
├── src/
│   └── maker/
│       ├── core.py              # MAKER framework core
│       ├── entertainment_agents.py  # Domain-specific agents
│       ├── benchmark.py         # Benchmarking tools
│       ├── config.py            # Configuration
│       ├── llm_client.py        # LLM integrations
│       └── api.py               # High-level API
├── tests/
│   └── test_maker.py            # Test suite
├── requirements.txt
└── README.md
```

## Microagents

| Agent | Task | Input | Output |
|-------|------|-------|--------|
| `MoodAnalyzerAgent` | Detect user mood | Query text | MoodCategory |
| `GenreMatcherAgent` | Match genres | Mood + prefs | Genre list |
| `DurationFilterAgent` | Set time bounds | Context | (min, max) |
| `ContentScorerAgent` | Score content | Item + context | Score 0-1 |
| `ContentRankerAgent` | Rank items | Scored items | Ordered IDs |
| `ExplanationGeneratorAgent` | Explain picks | Item + score | Text |

## Running Tests

```bash
pytest tests/test_maker.py -v
```

## Research Materials

The `/research` directory contains comprehensive research on enterprise AI infrastructure:

### LLM Proxy Security & Performance (2025)
Enterprise-grade best practices for production LLM Proxy deployments:

- **[LLM Proxy Security & Performance Best Practices](/research/llm-proxy-security-performance-best-practices-2025.md)** (60KB)
  - Security: Multi-layer defense, zero-trust architecture, prompt injection protection
  - Performance: Continuous batching, connection pooling, semantic caching
  - Reliability: Multi-region HA, disaster recovery, 99.95% SLA
  - Compliance: GDPR, HIPAA, SOC 2 requirements and implementation

- **[Production Checklist](/research/llm-proxy-production-checklist.md)** (12KB)
  - Quick reference guide with 5-phase roadmap
  - Security, performance, HA, and compliance checklists
  - Technology stack recommendations
  - 6-month implementation timeline

### Hybrid Cloud & AI Platforms
- [Hybrid Cloud AI Platform (2025-2045)](/research/hybrid-cloud-ai-platform-2025-2045.md)
- [Pan-Regional Hybrid Cloud AI (2024-2044)](/research/hybrid-cloud-ai-platform-pan-regional-2024-2044.md)
- [Competitive Analysis: Multi-Agent AI Platforms](/research/competitive-analysis-multi-agent-ai-platforms-cloud-ru-2025.md)

### Multi-Agent & Edge Computing
- [Multi-Agent AI Systems (2025-2045)](/research/multi-agent-ai-systems-2025-2045.md)
- [Autonomous Systems Edge Computing (2025-2045)](/research/autonomous-systems-edge-computing-2025-2045.md)
- [Edge Computing: Latency, Privacy, Localization (2025-2045)](/research/edge-computing-latency-privacy-localization-2025-2045.md)

### Multi-Agent Platform Technology Stack (Cloud.ru 2025) ⭐ NEW
Comprehensive analysis of 6 core technologies for building enterprise-grade multi-agent AI platform:

- **[Technology Stack Analysis](/research/multi-agent-platform-technology-stack-cloud-ru-2025.md)** (120KB)
  - **Technologies**: AgentDB, Milvus Vector DB, Agentic-Flow, DSPy.ts, MidStream, MAESTRO Security
  - **Architecture**: MCP-compatible orchestrator, role-based agents, graph workflows, agent memory
  - **Integration**: How technologies work together, data flows, API patterns
  - **Competitive Analysis**: vs Yandex.Cloud, AWS/Azure, cost comparison
  - **Roadmap**: 3-phase implementation (2025-2030), milestones, KPIs
  - **ROI**: 75% faster TTM, 50-70% cost reduction, 150x-12,500x performance gains
  - Note: "ruvector" not found - recommends Milvus as open-source alternative

- **[Executive Summary](/research/EXECUTIVE-SUMMARY-multi-agent-tech-stack-cloud-ru-2025.md)** (30KB)
  - C-Level decision document with Go/No-Go recommendation
  - Financial projections: $5M Phase 1 → $3B ARR by 2030
  - Risk assessment & mitigation strategies
  - Competitive positioning & unique value proposition
  - 90-day action plan with immediate next steps

- **[Architecture Diagrams](/research/multi-agent-platform-architecture-diagrams-2025.md)** (20KB)
  - 16 Mermaid diagrams: system architecture, data flows, security layers
  - Deployment patterns: orchestrator-workers, P2P, hierarchical, event-driven
  - Integration visualizations: MCP ecosystem, DSPy pipeline, memory architecture
  - Technology evolution roadmap (2025-2030)

- **[Quick Reference Guide](/research/QUICK-REFERENCE-multi-agent-technologies-2025.md)** (60KB)
  - Developer-focused practical guide for each technology
  - Code examples: TypeScript/Python for AgentDB, Milvus, Agentic-Flow, DSPy, MidStream
  - Integration patterns: complete stack example (customer service agent)
  - Best practices, troubleshooting, performance tuning
  - Links to documentation, SDKs, community resources

### IoT & Network Infrastructure
- [IoT 5G/6G Edge AI Integration (2025-2040)](/research/iot-5g-6g-edge-ai-integration-2025-2040.md)

### Competitive Advantages Analysis (Cloud.ru 2025) 🎯 LATEST
Strategic analysis of competitive advantages from ruvnet ecosystem technologies:

- **[Competitive Advantages: Technology Stack](/research/competitive-advantages-cloud-ru-tech-stack-2025.md)** (200KB)
  - **Technologies Analyzed**: ruvector, agentdb, agentic-flow, agentic-security, dspy.ts, midstream
  - **Competitive Context**: vs Yandex Cloud (YandexGPT, AI Studio), VK Cloud (ML Platform), Global Players
  - **Key Findings**:
    - **Performance**: 96-164x faster vector search (AgentDB), <50ms TTFT (MidStream)
    - **Cost Efficiency**: 40-70% LLM API reduction, 73% total cost savings
    - **Time-to-Market**: 10-15x faster (4-6 weeks vs 9-13 months)
    - **Developer Experience**: 95% less code, auto-optimization (DSPy.ts)
    - **Enterprise Readiness**: Multi-layer security (MAESTRO+A2AS), 152-ФЗ compliance
  - **Unique Differentiators**:
    - In-flight streaming analysis (worldwide exclusive)
    - Temporal attractor analysis (unique technology)
    - Semantic caching pattern (exclusive в России)
    - Agent-native vector DB (no competitor has this)
  - **ROI**: 567-1,522% return, 2-month payback, $2.3M savings (3-year TCO)
  - **Risks & Mitigation**: Comprehensive risk assessment with mitigation strategies

- **[Executive Summary: Competitive Advantages](/research/EXECUTIVE-SUMMARY-cloud-ru-tech-advantages-2025.md)** (25KB)
  - Strategic recommendation: GO FORWARD with pilot deployment
  - Budget: $42K pilot + $114K/year operations
  - Timeline: 4-6 weeks to production
  - Success metrics: P95 <100ms, 60%+ cache hit rate, 99.95% SLA
  - Competitive positioning: Unique top-right quadrant (high performance + vendor independence)
  - Marketing messaging: 3 key pillars (Sovereignty, Performance, Economics)
  - Next steps: Week 1 action plan with decision points
- [Network Topologies for Hybrid LLM Enterprise (2025-2045)](/research/network-topologies-hybrid-llm-enterprise-2025-2045.md)

### Cloud.ru Integrated Platform Architecture (2025-2045)
Enterprise-grade architecture integrating 6 core technologies for multi-agent AI platform:

- **[Integrated Platform Architecture](/research/cloud-ru-integrated-architecture-2025-2045.md)** (150KB) **⭐ COMPREHENSIVE**
  - **Technology Stack**: RuVector, AgentDB, Agentic-Flow, Agentic-Security, DSPy.ts, MidStream
  - **Unified Architecture**: 7-layer architecture from presentation to infrastructure
  - **Data Flows**: Complete integration patterns between all components
  - **API Interfaces**: REST, gRPC, WebSocket/SSE specifications
  - **Deployment Models**: Cloud, Edge, Hybrid (4 deployment patterns)
  - **Integration Roadmap**: 5-phase plan (2025-2045) with milestones
  - **Security**: 8-layer zero-trust architecture, threat models, compliance
  - **Performance**: Targets, optimization techniques, scalability patterns
  - **Cost Model**: 5-year TCO, revenue projections, ROI analysis
  - **20-Year Vision**: Path to AGI-ready infrastructure

- **[Integration Quick Reference](/research/cloud-ru-integration-quick-reference.md)** (30KB)
  - Component integration map with code examples
  - Data flow examples (simple query, multi-agent, edge-to-cloud)
  - API quick start (REST, WebSocket, gRPC)
  - Deployment commands (Docker Compose, Kubernetes, K3s)
  - Monitoring & debugging guide
  - Security checklist
  - Performance tuning recipes

- **[API Contracts & Integration Interfaces](/research/cloud-ru-api-contracts.md)** (40KB)
  - External REST APIs (Agent Management, Workflow, Vector Search)
  - Internal gRPC APIs (AgentDB, RuVector, Agentic-Flow)
  - Event schemas (NATS/Kafka) for event-driven architecture
  - Database schemas (PostgreSQL, RuVector collections)
  - Authentication & authorization (API keys, OAuth 2.0, RBAC)
  - Error handling & rate limiting

### AI Framework Research
- **[DSPy.ts Framework Deep Dive for Cloud.ru](/research/dspy-ts-framework-deep-dive-cloud-ru-2025.md)**
  - Comprehensive analysis of DSPy.ts (TypeScript port of Stanford's DSPy)
  - Automatic prompt optimization with MIPROv2 Bayesian optimizer
  - RAG systems with auto-tuning and 150x faster AgentDB
  - Multi-agent orchestration with Swarm framework
  - Comparison: DSPy vs LangChain vs Ax alternatives
  - Integration roadmap and ROI analysis for Cloud.ru platform

### Technology Stack Integration Report (Cloud.ru 2025) 🔥 NEWEST

- **[Technology Stack Integration Report](/research/TECHNOLOGY-STACK-INTEGRATION-REPORT-CLOUD-RU-2025.md)** (50KB) **⭐ FINAL SYNTHESIS**
  - **Executive Summary**: Complete assessment of 6 technologies with production readiness scores
  - **Technologies Evaluated**:
    - AgentDB (8/10) - 150x-12,500x faster state management
    - Agentic-Flow (7/10) - 352x speedup, 85-99% cost savings
    - MidStream (7/10) - <50ns real-time streaming analytics
    - Ax/@ax-llm/ax (8/10) - Recommended over dspy.ts for prompt optimization
    - MAESTRO Security (5/10) - Framework pattern, requires custom SDK
    - ruvector (N/A) - NOT FOUND, Milvus recommended as alternative
  - **Integrated Architecture**: Full technology stack diagram with data flows
  - **Sber Partnership Integration**: GigaChat as primary LLM, SberID auth, SberDevices edge
  - **Implementation Roadmap**: 3-phase plan with budget ($6.1M for 2025-2026)
  - **Success Metrics**: Technical KPIs (<50ms latency, 85% cache hit) and Business KPIs (200 clients, $20M ARR by 2026)

- **[AgentDB Research](/research/agentdb-multi-agent-memory-system-2025.md)** (40KB)
  - Multi-tier caching (L1 Hot → L2 Warm → L3 Archival)
  - 10M+ ops/sec throughput, <1ms P99 latency
  - Part of ruvnet/agentics ecosystem

- **[Agentic-Flow Research](/research/agentic-flow-research-2025.md)** (45KB)
  - Agent Booster with 352x speedup
  - Semantic caching with hash-based search
  - Multi-model routing and cost optimization

- **[MidStream Platform](/research/midstream-real-time-llm-streaming-platform-2025.md)** (35KB)
  - Temporal attractor pattern recognition
  - <50ns scheduling, <1ms message processing
  - Real-time LLM streaming analysis (unique capability)

- **[Edge Technologies Architecture](/research/edge-technologies-architecture-cloud-ru-2025-2045.md)** (60KB)
  - 4-tier edge hierarchy: Cloud → Network Edge → Mid-Edge → Far-Edge
  - 5G/6G integration for IoT and autonomous systems
  - ФЗ-152 compliance through on-premise deployment

- **[LLM Proxy Hybrid Architecture](/research/llm-proxy-hybrid-architecture-modern-stack-2025.md)** (55KB)
  - Modern stack: Kong/Envoy gateway, semantic caching, PII detection
  - Multi-model routing with fallback chains
  - Compliance-first design for Russian market

### Implementation Roadmap
- **[ROADMAP: Tech Implementation 2025-2028](/research/ROADMAP-TECH-IMPLEMENTATION-CLOUD-RU-2025-2028.md)** (40KB)
  - 4-phase implementation plan
  - Total investment: $38.4M over 3 years
  - Quarterly milestones and KPIs

- **[Executive Summary: Roadmap](/research/EXECUTIVE-SUMMARY-ROADMAP-CLOUD-RU.md)** (15KB)
  - C-Level decision document
  - GO/NO-GO recommendation with risk assessment

- **[Gantt Timeline](/research/GANTT-TIMELINE-CLOUD-RU-2025-2028.md)** (10KB)
  - Visual Mermaid timeline for project phases

## References

- **Paper**: [Solving a Million-Step LLM Task with Zero Errors](https://arxiv.org/abs/2511.09030)
- **Authors**: Meyerson, Paolo, Dailey, Shahrzad, Francon, Hayes, Qiu, Hodjat, Miikkulainen
- **Hackathon**: [Agentics Foundation TV5 Hackathon](https://agentics.org/hackathon)

## License

MIT
