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

### IoT & Network Infrastructure
- [IoT 5G/6G Edge AI Integration (2025-2040)](/research/iot-5g-6g-edge-ai-integration-2025-2040.md)

## References

- **Paper**: [Solving a Million-Step LLM Task with Zero Errors](https://arxiv.org/abs/2511.09030)
- **Authors**: Meyerson, Paolo, Dailey, Shahrzad, Francon, Hayes, Qiu, Hodjat, Miikkulainen
- **Hackathon**: [Agentics Foundation TV5 Hackathon](https://agentics.org/hackathon)

## License

MIT
