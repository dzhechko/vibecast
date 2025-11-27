# CLOUD.RU PLATFORM: Quick Integration Reference

**Версия:** 1.0
**Дата:** 27 ноября 2025

---

## 1-MINUTE ARCHITECTURE OVERVIEW

```
Client Request
     ↓
[API Gateway] → [Agentic-Security] → Validate & Authorize
     ↓
[Agentic-Flow] → Orchestrate workflow
     ↓
[Agent Runtime] → Execute business logic
     ↓
[DSPy.ts] → Optimize prompt
     ↓
[LLM Gateway] → Route to LLM provider
     ↓         ↘
[RuVector]     [GigaChat/YandexGPT/Qwen]
(Cache Check)        ↓
     ↓              Response
[MidStream] ← ───────┘
     ↓
[AgentDB] → Save state
     ↓
Client Response (SSE/WebSocket)
```

---

## COMPONENT INTEGRATION MAP

### RuVector Integration Points

```typescript
// 1. Agent Memory (Long-term)
AgentDB.saveMemory() → RuVector.insert({
  collection: 'agent-memory',
  vector: embedding,
  metadata: { agent_id, timestamp, context }
})

// 2. LLM Semantic Cache
LLMGateway.beforeRequest() → RuVector.search({
  collection: 'llm-cache',
  query: requestEmbedding,
  threshold: 0.95
})
→ Cache hit? Return cached response
→ Cache miss? Call LLM + RuVector.insert(response)

// 3. RAG Knowledge Base
Agent.execute() → RuVector.search({
  collection: 'knowledge-base',
  query: userQuery,
  top_k: 5
})
→ Retrieve contexts → DSPy.constructPrompt(contexts)
```

### AgentDB Integration Points

```typescript
// 1. Workflow State Persistence
AgenticFlow.executeStep() → AgentDB.upsert({
  agent_id: 'agt_123',
  state: { current_step, variables, history },
  snapshot: true  // For rollback
})

// 2. Multi-Agent Coordination
Agent1.complete() → AgentDB.update({
  status: 'completed',
  output: result
})
→ Event → AgenticFlow.triggerNextStep(Agent2)

// 3. Session Management
Client.connect() → AgentDB.loadState({
  agent_id: 'agt_123',
  session_id: 'sess_xyz'
})
→ Restore conversation history, variables
```

### Agentic-Flow Integration Points

```typescript
// 1. Task Queue (Redis)
AgenticFlow.createWorkflow() → Redis.lpush('task-queue', {
  workflow_id: 'wf_456',
  steps: [step1, step2, step3]
})

Worker.poll() → Redis.brpop('task-queue')
→ AgentDB.loadAgent()
→ Agent.execute()
→ AgenticFlow.onStepComplete()

// 2. Event-Driven Coordination
AgenticFlow.on('step.complete', (event) => {
  if (event.step === 'extract') {
    AgenticFlow.startStep('summarize', event.output)
  }
})

// 3. Human-in-the-Loop
AgenticFlow.executeStep('approval-required') → {
  status: 'waiting_approval',
  webhook: 'https://app.com/approve/wf_456'
}
→ User approves → AgenticFlow.resume('wf_456')
```

### MidStream Integration Points

```typescript
// 1. LLM Token Streaming
LLMGateway.stream(request) → async generator {
  for await (const token of llm.stream()) {
    MidStream.broadcast({
      channel: `agent.${agent_id}`,
      data: { type: 'token', content: token }
    })
  }
}

// 2. Multi-Agent Collaboration
Agent1.emit('finding', data) → MidStream.publish({
  topic: 'collaboration.findings',
  data: data
})

Agent2.subscribe('collaboration.findings') → {
  MidStream.on('message', (msg) => {
    Agent2.processUpdate(msg.data)
  })
}

// 3. Progress Tracking
AgenticFlow.onProgress((progress) => {
  MidStream.send({
    channel: `workflow.${workflow_id}`,
    data: { step: progress.current, total: progress.total }
  })
})
→ Client UI updates in real-time
```

### DSPy.ts Integration Points

```typescript
// 1. Prompt Optimization
Agent.beforeLLMCall() → DSPy.optimize({
  task: 'summarization',
  examples: fewShotExamples,
  metric: 'accuracy'
})
→ Optimized prompt template

// 2. Chain-of-Thought
DSPy.chainOfThought({
  question: userQuery,
  steps: ['understand', 'analyze', 'conclude']
})
→ Structured prompt with reasoning steps

// 3. Evaluation
DSPy.evaluate({
  model: 'gigachat-pro',
  dataset: testCases,
  metrics: ['accuracy', 'cost', 'latency']
})
→ Best model selection
```

### Agentic-Security Integration Points

```typescript
// 1. Request Validation (Layer 6)
APIGateway.onRequest() → AgenticSecurity.validate({
  input: request.body,
  checks: ['schema', 'prompt-injection', 'pii']
})
→ Pass: Continue
→ Fail: Reject + Audit log

// 2. PII Masking (Layer 3)
LLMGateway.beforeSend() → AgenticSecurity.maskPII({
  text: userInput,
  entities: ['NAME', 'INN', 'PHONE']
})
→ Masked text → LLM
→ LLM response → AgenticSecurity.restorePII()

// 3. Output Validation (Layer 2)
LLMGateway.afterReceive() → AgenticSecurity.validateOutput({
  text: llmResponse,
  checks: ['toxicity', 'hallucination', 'bias']
})
→ Pass: Return to user
→ Fail: Regenerate or block
```

---

## DATA FLOW EXAMPLES

### Example 1: Simple Agent Query

```
1. User → "What is the weather in Moscow?"
2. API Gateway → Agentic-Security (validate)
3. Agentic-Security → AgentDB (load agent state)
4. AgentDB → RuVector (load memory)
5. Agent Runtime → DSPy.ts (optimize prompt)
6. DSPy.ts → "Given context..., answer: What is the weather in Moscow?"
7. LLM Gateway → RuVector (cache check)
8. RuVector → Cache miss
9. LLM Gateway → GigaChat API
10. GigaChat → "The weather in Moscow is 5°C, cloudy"
11. LLM Gateway → RuVector (cache result)
12. LLM Gateway → Agentic-Security (output validation)
13. Agentic-Security → MidStream (stream to client)
14. MidStream → AgentDB (save interaction)
15. MidStream → User (response)

Total latency: ~400ms
```

### Example 2: Multi-Agent Workflow

```
1. User → "Analyze this 100-page PDF report"
2. Agentic-Flow → Create workflow:
   Step 1: PDF Extraction (Agent A)
   Step 2: Summarization (Agent B)
   Step 3: Key Findings (Agent C)
   Step 4: Executive Summary (Agent D)

3. Agentic-Flow → Redis task queue (4 tasks)

4. Worker 1 → Agent A executes:
   - AgentDB.loadState('agent_a')
   - Extract text from PDF
   - AgentDB.saveState({status: 'completed', output: text})
   - MidStream.emit('step.complete', {step: 1})

5. Agentic-Flow → Trigger Step 2 (depends on Step 1)

6. Worker 2 → Agent B executes:
   - AgentDB.loadState('agent_b')
   - DSPy.ts → Optimize summarization prompt
   - LLM Gateway → GigaChat (summarize text)
   - AgentDB.saveState({status: 'completed', output: summary})
   - MidStream.emit('step.complete', {step: 2})

7-8. Similar for Agent C and Agent D

9. Agentic-Flow → All steps complete → Final output
10. MidStream → User (final executive summary)

Total latency: ~15 seconds (parallel execution)
```

### Example 3: Edge-to-Cloud Sync

```
EDGE NODE (Factory Floor):
1. IoT Sensor → Temperature anomaly detected (95°C)
2. Edge Agent → Local inference (NVIDIA Jetson)
3. Local AgentDB → Check local rules
4. Local RuVector → Search similar incidents
5. Edge Agent → Anomaly confirmed, escalate to cloud

6. MidStream → Stream telemetry to cloud
   MQTT topic: factory/moscow/sensor-123/alert

CLOUD:
7. MidStream → Receive alert
8. Agentic-Flow → Trigger escalation workflow
9. Cloud Agent → Analyze historical data (RuVector search)
10. Cloud Agent → Generate recommendations
11. MidStream → Stream response to edge
12. Edge Agent → Execute automated response (shutdown machine)

SYNC (Periodic):
13. Edge AgentDB → Cloud AgentDB (delta sync every 5 min)
14. Edge RuVector → Cloud RuVector (incremental every 15 min)

Latency (edge decision): <100ms
Latency (cloud escalation): ~2 seconds
```

---

## API QUICK START

### REST API

```bash
# Create Agent
curl -X POST https://api.cloud.ru/v1/agents \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "customer-support",
    "type": "conversational",
    "config": {
      "llm": "gigachat-pro",
      "temperature": 0.7
    }
  }'

# Execute Agent (Sync)
curl -X POST https://api.cloud.ru/v1/agents/agt_123/execute \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "input": "Hello, I need help with my order",
    "stream": false
  }'

# Execute Agent (Streaming)
curl -X POST https://api.cloud.ru/v1/agents/agt_123/execute \
  -H "Authorization: Bearer $TOKEN" \
  -H "Accept: text/event-stream" \
  -d '{
    "input": "Explain quantum computing",
    "stream": true
  }'
```

### WebSocket (MidStream)

```javascript
const ws = new WebSocket('wss://stream.cloud.ru/v1/agents/agt_123');

ws.on('open', () => {
  ws.send(JSON.stringify({
    type: 'subscribe',
    auth: 'Bearer TOKEN'
  }));

  ws.send(JSON.stringify({
    type: 'message',
    input: 'Hello!'
  }));
});

ws.on('message', (data) => {
  const event = JSON.parse(data);

  if (event.type === 'token') {
    process.stdout.write(event.content);
  } else if (event.type === 'done') {
    console.log('\nMetadata:', event.metadata);
  }
});
```

### gRPC (Internal Services)

```typescript
// AgentDB Client
import { AgentDBClient } from '@cloud-ru/agentdb';

const client = new AgentDBClient('agentdb.cloud.ru:443');

const state = await client.getAgentState({
  agent_id: 'agt_123'
});

await client.upsertAgentState({
  agent_id: 'agt_123',
  state: {
    variables: { last_topic: 'weather' },
    status: 'active'
  }
});

// RuVector Client
import { RuVectorClient } from '@cloud-ru/ruvector';

const vecClient = new RuVectorClient('ruvector.cloud.ru:443');

const results = await vecClient.search({
  collection: 'knowledge-base',
  query: 'how to reset password',
  top_k: 5
});

console.log(results); // [{id, score, text, metadata}]
```

---

## DEPLOYMENT COMMANDS

### Local Development (Docker Compose)

```bash
# Clone repo
git clone https://github.com/cloudru/platform.git
cd platform

# Start all services
docker-compose up -d

# Services will be available:
# - API Gateway: http://localhost:8080
# - AgentDB: localhost:5432 (PostgreSQL)
# - RuVector: http://localhost:8081
# - MidStream: ws://localhost:8082
# - Redis: localhost:6379

# Check health
curl http://localhost:8080/health

# View logs
docker-compose logs -f agentdb
```

### Production (Kubernetes)

```bash
# Install with Helm
helm repo add cloudru https://charts.cloud.ru
helm repo update

# Install full platform
helm install cloudru-platform cloudru/platform \
  --namespace cloudru \
  --create-namespace \
  --set global.domain=platform.mycompany.com \
  --set agentdb.replicas=3 \
  --set ruvector.shards=3 \
  --set ruvector.replicationFactor=2 \
  --set llmGateway.providers.gigachat.apiKey=$GIGACHAT_KEY

# Check deployment
kubectl get pods -n cloudru

# Access dashboard
kubectl port-forward -n cloudru svc/platform-dashboard 8080:80
# Open http://localhost:8080
```

### Edge Deployment (K3s)

```bash
# Install K3s (edge node)
curl -sfL https://get.k3s.io | sh -

# Deploy edge stack
kubectl apply -f https://platform.cloud.ru/manifests/edge-stack.yaml

# Configure cloud sync
kubectl create secret generic cloud-sync \
  --from-literal=endpoint=https://api.cloud.ru \
  --from-literal=token=$CLOUD_TOKEN

# Enable sync
kubectl apply -f - <<EOF
apiVersion: sync.cloud.ru/v1
kind: SyncConfig
metadata:
  name: agentdb-sync
spec:
  source: local
  destination: cloud
  interval: 5m
  mode: delta
EOF
```

---

## MONITORING & DEBUGGING

### Key Metrics to Monitor

```yaml
AgentDB:
  - connection_pool_usage (should be <80%)
  - query_latency_p95 (should be <50ms)
  - replication_lag (should be <5s)

RuVector:
  - search_latency_p95 (should be <50ms)
  - index_memory_usage (should be <90%)
  - cache_hit_rate (target: 40-70%)

LLM Gateway:
  - requests_per_second
  - cache_hit_rate (target: 40-70%)
  - cost_per_request (track spend)
  - latency_by_provider

MidStream:
  - active_connections
  - messages_per_second
  - websocket_errors

Agentic-Flow:
  - active_workflows
  - step_success_rate (should be >95%)
  - workflow_completion_time
```

### Debug Commands

```bash
# AgentDB: Check agent state
kubectl exec -it agentdb-0 -- psql -U postgres -d agentdb
SELECT * FROM agents WHERE agent_id = 'agt_123';

# RuVector: Check collection stats
curl http://ruvector:8081/collections/knowledge-base/stats

# Redis: Check task queue
kubectl exec -it redis-0 -- redis-cli
LLEN task-queue
LRANGE task-queue 0 10

# View MidStream connections
curl http://midstream:8082/metrics | grep active_connections

# Check Agentic-Flow workflows
curl http://agentic-flow:8083/workflows?status=running
```

### Common Issues & Solutions

```
Issue: High LLM latency (>1s)
Solution:
  1. Check cache hit rate (should be >40%)
  2. Enable semantic caching in RuVector
  3. Use faster LLM (e.g., gigachat-lite instead of pro)
  4. Enable request batching

Issue: AgentDB connection pool exhausted
Solution:
  1. Increase pool size in PgBouncer
  2. Check for connection leaks (unclosed connections)
  3. Add read replicas for read-heavy workloads

Issue: RuVector search slow (>100ms)
Solution:
  1. Tune HNSW parameters (reduce M, efSearch)
  2. Add sharding if >10M vectors
  3. Enable GPU acceleration (if available)
  4. Use IVF-PQ index for large datasets

Issue: MidStream WebSocket disconnects
Solution:
  1. Enable heartbeat/ping-pong
  2. Increase timeout (default 60s)
  3. Check load balancer settings (sticky sessions)
  4. Use connection pooling on client side
```

---

## SECURITY CHECKLIST

### Production Deployment

- [ ] TLS 1.3 enabled for all external endpoints
- [ ] mTLS enabled for internal service-to-service communication
- [ ] API keys rotated (every 90 days)
- [ ] Secrets stored in vault (not environment variables)
- [ ] WAF rules configured (OWASP Core Rule Set)
- [ ] Rate limiting enabled (per IP, per user)
- [ ] Audit logging enabled (immutable, 6-year retention)
- [ ] PII detection enabled (Presidio)
- [ ] Prompt injection defense enabled
- [ ] Multi-factor authentication (MFA) required for admin access
- [ ] RBAC policies configured (least privilege)
- [ ] Security scanning (SAST, DAST) in CI/CD
- [ ] Penetration testing completed
- [ ] Incident response plan documented
- [ ] Compliance certifications (ФЗ-152, ISO 27001)

### Data Protection

- [ ] Data encrypted at rest (AES-256)
- [ ] Data encrypted in transit (TLS 1.3)
- [ ] PII automatically masked before LLM calls
- [ ] Data residency enforced (no cross-border transfer)
- [ ] Backup encryption enabled
- [ ] Backup retention policy configured (30 days)
- [ ] Disaster recovery plan tested
- [ ] Data deletion procedures (GDPR right to erasure)

---

## PERFORMANCE TUNING

### RuVector Optimization

```python
# For small datasets (<1M vectors)
index_type = 'HNSW'
params = {'M': 16, 'efConstruction': 100, 'efSearch': 50}
# Expected: Latency 20-30ms, Recall 90%+

# For medium datasets (1-10M vectors)
index_type = 'HNSW'
params = {'M': 32, 'efConstruction': 200, 'efSearch': 100}
# Expected: Latency 40-50ms, Recall 95%+

# For large datasets (>10M vectors)
index_type = 'IVF_PQ'
params = {'nlist': 1024, 'nprobe': 16, 'm': 8}
# Expected: Latency 30-50ms, Recall 90%+, 10x memory savings
```

### LLM Gateway Optimization

```yaml
# Semantic caching
semantic_cache:
  enabled: true
  similarity_threshold: 0.95  # Higher = fewer false hits
  ttl: 604800  # 7 days
  embedding_model: 'e5-mistral-7b'

# Connection pooling
connection_pool:
  max_connections: 100
  min_connections: 10
  timeout: 30s
  keepalive: true

# Request batching
batching:
  enabled: true
  max_batch_size: 32
  max_wait_time: 50ms  # Wait up to 50ms to fill batch

# Expected improvement:
#   Cache hit rate: 40-70%
#   Latency reduction: 95% (cached), 30% (batching)
#   Cost reduction: 40-70%
```

### AgentDB Optimization

```sql
-- Query optimization
EXPLAIN ANALYZE SELECT * FROM agents WHERE status = 'active';

-- Add index if needed
CREATE INDEX CONCURRENTLY idx_agents_status ON agents(status);

-- Connection pooling (PgBouncer config)
max_client_conn = 10000
default_pool_size = 25  # Per database
pool_mode = transaction  # More efficient than session mode

-- Read replicas for read-heavy workloads
-- Primary: writes + reads
-- Replica 1, 2, 3: reads only (load balanced)
```

---

## LINKS & RESOURCES

### Documentation
- Platform Docs: https://docs.cloud.ru/platform
- API Reference: https://api.cloud.ru/docs
- Developer Portal: https://developers.cloud.ru

### GitHub Repositories
- Platform Core: https://github.com/cloudru/platform
- AgentDB: https://github.com/cloudru/agentdb
- RuVector: https://github.com/cloudru/ruvector
- Agentic-Flow: https://github.com/cloudru/agentic-flow
- Agentic-Security: https://github.com/cloudru/agentic-security
- DSPy.ts: https://github.com/cloudru/dspy-ts
- MidStream: https://github.com/cloudru/midstream

### Community
- Discord: https://discord.gg/cloudru
- Forum: https://community.cloud.ru
- Stack Overflow: [cloud-ru] tag

### Support
- Email: support@cloud.ru
- Enterprise Support: enterprise@cloud.ru
- Status Page: https://status.cloud.ru

---

**Last Updated:** 27 ноября 2025
**Version:** 1.0
