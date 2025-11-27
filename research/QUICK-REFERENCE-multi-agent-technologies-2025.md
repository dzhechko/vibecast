# Quick Reference: Multi-Agent Technologies для Cloud.ru Platform

**Для**: Development Team
**Цель**: Быстрый старт с каждой технологией
**Дата**: Ноябрь 2025

---

## 1. AgentDB — Agent State Management

### Что это?
Serverless база данных, спроектированная специально для AI-агентов. Создание БД так же просто, как генерация UUID.

### Ключевые концепции
- **Ephemeral DBs**: Временные БД для коротких задач (auto-cleanup)
- **Persistent DBs**: Долгосрочное хранение состояния
- **MCP-native**: Работает как MCP Server из коробки
- **Templates**: Pre-defined schemas для типовых use cases

### Установка
```bash
npm install @agentdb/core
# or
pip install agentdb
```

### Quick Start (TypeScript)
```typescript
import { AgentDB } from '@agentdb/core';

// 1. Создать ephemeral DB для задачи
const taskDB = await AgentDB.create(generateUUID(), {
  template: 'customer-service',  // Готовая схема
  engine: 'sqlite',               // SQLite или DuckDB
  lifecycle: 'ephemeral'          // Автоудаление
});

// 2. Использовать как обычную БД
await taskDB.query(
  'INSERT INTO conversations (user_id, message) VALUES (?, ?)',
  [userId, message]
);

const history = await taskDB.query(
  'SELECT * FROM conversations WHERE user_id = ?',
  [userId]
);

// 3. Сохранить в long-term (опционально)
await taskDB.persist({ name: 'customer-123-session' });

// 4. Ephemeral DB автоматически удалится через X минут
```

### Интеграция с MCP
```typescript
// AgentDB как MCP Server
import { MCPServer } from '@agentdb/mcp';

const mcpServer = new MCPServer({
  agentdb: taskDB,
  exposedTables: ['conversations', 'user_preferences']
});

// Agent может теперь запрашивать через MCP
const result = await agent.call('agentdb://query', {
  sql: 'SELECT * FROM conversations LIMIT 10'
});
```

### Best Practices
- ✅ Используйте ephemeral для task state (5 мин - 2 часа)
- ✅ Persist только критичные данные в long-term
- ✅ Используйте templates для быстрого старта
- ❌ Не храните PII в ephemeral (может потеряться)

### Performance
- **150x-12,500x** быстрее traditional DBs для agent workloads
- **Latency**: <1ms для ephemeral, <10ms для persistent

### Links
- Docs: https://agentdb.dev/
- GitHub: https://github.com/agentdb/agentdb (if open-source)
- MCP Integration: https://agentdb.dev/mcp

---

## 2. Milvus — Vector Database

### Что это?
Open-source vector database для хранения и поиска embeddings (semantic memory агентов).

### Ключевые концепции
- **Collections**: Аналог таблиц, но для векторов
- **Embeddings**: Числовые представления текста/изображений
- **ANN Search**: Approximate Nearest Neighbor (быстрый semantic search)
- **Hybrid Search**: Векторный + metadata filtering

### Установка (Docker)
```bash
# Standalone (dev)
docker run -d -p 19530:19530 -p 9091:9091 milvusdb/milvus:latest standalone

# Cluster (production) — use Helm chart
helm repo add milvus https://milvus-io.github.io/milvus-helm/
helm install milvus milvus/milvus
```

### Quick Start (Python)
```python
from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType
import openai  # or GigaChat SDK

# 1. Подключиться
connections.connect(host='localhost', port='19530')

# 2. Создать collection
fields = [
    FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
    FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=1536),  # GigaChat embeddings
    FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=65535),
    FieldSchema(name="user_id", dtype=DataType.VARCHAR, max_length=64)
]
schema = CollectionSchema(fields=fields)
collection = Collection(name="customer_interactions", schema=schema)

# 3. Создать индекс (для быстрого поиска)
index_params = {
    "metric_type": "COSINE",  # Или L2, IP
    "index_type": "HNSW",     # Hierarchical Navigable Small World
    "params": {"M": 16, "efConstruction": 256}
}
collection.create_index(field_name="embedding", index_params=index_params)
collection.load()  # Загрузить в память

# 4. Вставить данные
texts = ["Customer asked about refund policy", "User complained about delivery"]
embeddings = [get_embedding(t) for t in texts]  # GigaChat API

entities = [
    embeddings,  # Векторы
    texts,       # Исходный текст
    ["user123", "user456"]  # Metadata
]
collection.insert(entities)

# 5. Поиск (Semantic Search)
query_text = "How do I return a product?"
query_embedding = get_embedding(query_text)

results = collection.search(
    data=[query_embedding],
    anns_field="embedding",
    param={"metric_type": "COSINE", "params": {"ef": 64}},
    limit=5,  # Top-5 похожих
    expr='user_id == "user123"'  # Hybrid: фильтр по metadata
)

for hit in results[0]:
    print(f"Score: {hit.score}, Text: {hit.entity.get('text')}")
```

### TypeScript SDK
```typescript
import { MilvusClient } from '@zilliz/milvus2-sdk-node';

const client = new MilvusClient({ address: 'localhost:19530' });

// Search
const searchResults = await client.search({
  collection_name: 'customer_interactions',
  vectors: [queryEmbedding],
  search_params: { nprobe: 10 },
  limit: 5,
  filter: 'user_id == "user123"'
});
```

### Best Practices для Multi-Agent
- ✅ **Одна collection на тип памяти**:
  - `agent_episodic_memory` (past interactions)
  - `knowledge_base` (domain documents)
  - `user_profiles` (personalization)
- ✅ **Index strategy**: HNSW для <10M vectors, IVF_FLAT для >10M
- ✅ **Batch insert**: 500-1000 vectors за раз (производительность)
- ❌ Не храните большие тексты в vectors (только embeddings + короткий metadata)

### Performance Tuning
```python
# Для production:
# 1. Включить resource groups (multi-tenancy)
collection.set_properties({'resource_group': 'agent_memory'})

# 2. Query node replicas для HA
collection.load(replica_number=2)

# 3. Partition по времени (для quick cleanup старых данных)
collection.create_partition("p2025_Q1")
collection.insert(entities, partition_name="p2025_Q1")
```

### Links
- Docs: https://milvus.io/docs
- Python SDK: https://github.com/milvus-io/pymilvus
- Node.js SDK: https://github.com/milvus-io/milvus-sdk-node
- Performance Tuning: https://milvus.io/docs/performance_tuning.md

---

## 3. Agentic-Flow — Workflow Orchestration

### Что это?
Фреймворк для оркестрации мультиагентных workflows, часть экосистемы Claude-Flow (ruvnet).

### Ключевые концепции
- **Patterns**: Готовые паттерны (Orchestrator-Workers, P2P, Hierarchical, Event-Driven)
- **MCP Integration**: Нативная поддержка Model Context Protocol
- **Swarm Intelligence**: Координация tens of thousands agents
- **State Management**: Интеграция с AgentDB

### Установка
```bash
npm install @ruvnet/agentic-flow
# or via Claude-Flow
npm install @ruvnet/claude-flow
```

### Quick Start: Orchestrator-Workers Pattern
```typescript
import { AgenticFlow, OrchestratorPattern } from '@ruvnet/agentic-flow';
import { AgentDB } from '@agentdb/core';

// 1. Определить agents
const researchAgent = {
  name: 'researcher',
  role: 'Data collection',
  model: 'gigachat-pro',
  systemPrompt: 'You are a research specialist...'
};

const analysisAgent = {
  name: 'analyzer',
  role: 'Data processing',
  model: 'gigachat-pro',
  systemPrompt: 'You are a data analyst...'
};

const writerAgent = {
  name: 'writer',
  role: 'Content generation',
  model: 'gigachat-lite',  // Cheaper model для writing
  systemPrompt: 'You are a professional writer...'
};

// 2. Создать workflow
const workflow = new AgenticFlow({
  pattern: OrchestratorPattern,
  agents: {
    orchestrator: {
      name: 'orchestrator',
      model: 'gigachat-pro',
      systemPrompt: 'Decompose task and coordinate workers'
    },
    workers: [researchAgent, analysisAgent, writerAgent]
  },
  stateManagement: {
    provider: 'agentdb',
    config: { lifecycle: 'ephemeral' }
  }
});

// 3. Выполнить workflow
const result = await workflow.execute({
  input: 'Write a report on AI trends in Russia 2025',
  context: {
    maxTokens: 2000,
    temperature: 0.7
  }
});

console.log('Final report:', result.output);
console.log('Agent steps:', result.trace);  // Для debugging
```

### Peer-to-Peer Pattern
```typescript
import { P2PPattern } from '@ruvnet/agentic-flow';

const p2pWorkflow = new AgenticFlow({
  pattern: P2PPattern,
  agents: [
    { name: 'customer_service', model: 'gigachat-pro' },
    { name: 'technical_support', model: 'gigachat-pro' },
    { name: 'billing', model: 'gigachat-lite' }
  ],
  communication: {
    type: 'event-bus',  // Kafka, Redis Streams
    config: { broker: 'kafka://localhost:9092' }
  }
});

// Агенты автоматически координируются через event bus
```

### Event-Driven Pattern
```typescript
import { EventDrivenPattern } from '@ruvnet/agentic-flow';

const eventWorkflow = new AgenticFlow({
  pattern: EventDrivenPattern,
  agents: [
    {
      name: 'order_processor',
      subscribes: ['order.created', 'payment.completed']
    },
    {
      name: 'inventory_manager',
      subscribes: ['order.created', 'shipment.ready']
    }
  ]
});

// Publish event
await eventWorkflow.publish('order.created', { orderId: '123', items: [...] });
```

### MCP Integration
```typescript
// Agents могут использовать MCP servers для tools
const workflow = new AgenticFlow({
  pattern: OrchestratorPattern,
  agents: { ... },
  mcpServers: [
    {
      name: '1c-integration',
      url: 'mcp://localhost:3000/1c',
      tools: ['query_customers', 'create_invoice']
    },
    {
      name: 'email-sender',
      url: 'mcp://localhost:3001/email',
      tools: ['send_email', 'schedule_email']
    }
  ]
});

// Agents автоматически получают доступ к tools
```

### Best Practices
- ✅ **Orchestrator-Workers**: Для structured tasks (reports, data processing)
- ✅ **P2P**: Для dynamic collaboration (customer support)
- ✅ **Event-Driven**: Для real-time, high-frequency events (e-commerce)
- ✅ **State Management**: Всегда используйте AgentDB для multi-step workflows
- ❌ Не используйте P2P для simple linear workflows (overhead)

### Debugging
```typescript
// Enable tracing
workflow.configure({
  tracing: true,
  logLevel: 'debug'
});

const result = await workflow.execute(input);

// Inspect agent steps
result.trace.forEach(step => {
  console.log(`Agent: ${step.agent}, Action: ${step.action}, Tokens: ${step.tokens}`);
});
```

### Links
- GitHub: https://github.com/ruvnet/claude-flow
- Docs: https://github.com/ruvnet/claude-flow/wiki
- Examples: https://github.com/ruvnet/claude-flow/tree/main/examples

---

## 4. DSPy.ts — Prompt Optimization

### Что это?
Фреймворк для программной работы с LLM: вместо manual prompting → декларативные signatures + автоматическая оптимизация.

### Ключевые концепции
- **Signatures**: Input/Output спецификации (вместо промптов)
- **Modules**: Стратегии (ChainOfThought, ReAct, ProgramOfThought)
- **Optimizers**: Автоматические оптимизаторы промптов (MIPROv2, BootstrapFewShot)
- **Compilation**: Процесс оптимизации signature → optimized prompt

### Установка (TypeScript)
```bash
# Рекомендуется: Ax (official TypeScript impl)
npm install @ax-llm/ax

# Альтернативы:
npm install dspy.ts           # ruvnet implementation
npm install @ts-dspy/core     # Community implementation
```

### Quick Start (Ax)
```typescript
import { ChainOfThought, Signature, Input, Output, BootstrapFewShot } from '@ax-llm/ax';
import { GigaChatLLM } from './gigachat-adapter';  // Custom adapter

// 1. Определить Signature (что хотим от LLM)
class CustomerServiceQA extends Signature {
  @Input("Customer question")
  question: string;

  @Input("Customer history (past interactions)")
  history: string;

  @Output("Helpful, empathetic response")
  answer: string;
}

// 2. Выбрать Module (стратегию)
const llm = new GigaChatLLM({ apiKey: process.env.GIGACHAT_API_KEY });
const qa = new ChainOfThought(CustomerServiceQA, { llm });

// 3. Использовать (DSPy автоматически генерирует промпт)
const response = await qa.forward({
  question: "How do I return a product?",
  history: "User purchased laptop 2 weeks ago"
});

console.log(response.answer);
// → "I'd be happy to help you with a return! Since you purchased..."
```

### Optimization (BootstrapFewShot)
```typescript
// Обучающие примеры
const trainingData = [
  {
    question: "Refund policy?",
    history: "New customer",
    answer: "We offer 30-day full refund..."
  },
  // ... 50-100 examples
];

// Метрика качества
const accuracyMetric = (prediction, example) => {
  // Implement your metric (e.g., ROUGE, human eval)
  return score;
};

// Optimizer
const optimizer = new BootstrapFewShot({
  metric: accuracyMetric,
  maxBootstrappedDemos: 3,  // Сколько examples включить в prompt
  maxLabeledDemos: 2
});

// Compile (оптимизация)
const optimizedQA = await optimizer.compile(qa, {
  trainset: trainingData,
  valset: validationData
});

// Теперь optimizedQA использует best промпт + few-shot examples
const betterResponse = await optimizedQA.forward({ question, history });
```

### MIPROv2 Optimizer (Advanced)
```typescript
import { MIPROv2 } from '@ax-llm/ax';

const mipro = new MIPROv2({
  metric: accuracyMetric,
  numCandidates: 10,      // Сколько промптов попробовать
  initTemperature: 1.0,   // Bayesian optimization params
  verbose: true
});

// MIPROv2 автоматически:
// 1. Генерирует candidate instructions
// 2. Тестирует на validation set
// 3. Выбирает best via Bayesian Optimization
const optimized = await mipro.compile(qa, { trainset, valset });
```

### Multi-Model Adaptation
```typescript
// DSPy автоматически адаптирует промпт для разных моделей
const gigaChatQA = await optimizer.compile(qa, {
  trainset,
  llm: new GigaChatLLM()
});

const yandexQA = await optimizer.compile(qa, {
  trainset,
  llm: new YandexGPTLLM()
});

// Каждая версия оптимизирована для своей модели!
```

### ReAct Pattern (Reasoning + Acting)
```typescript
import { ReAct } from '@ax-llm/ax';

class ResearchTask extends Signature {
  @Input("Research question")
  question: string;

  @Output("Answer with sources")
  answer: string;
}

const researcher = new ReAct(ResearchTask, {
  llm,
  tools: [
    { name: 'search_web', fn: searchWebTool },
    { name: 'read_pdf', fn: readPDFTool }
  ],
  maxIters: 5  // Max reasoning steps
});

// Agent will automatically:
// 1. Think about what to do
// 2. Act (call tool)
// 3. Observe result
// 4. Repeat until answer found
const result = await researcher.forward({
  question: "What are GigaChat's capabilities in 2025?"
});
```

### Best Practices
- ✅ Начните с ChainOfThought для большинства задач
- ✅ Используйте ReAct когда нужны tools/actions
- ✅ Optimize с BootstrapFewShot (проще) или MIPROv2 (лучше, но дороже)
- ✅ Соберите 50-100 quality training examples для optimization
- ✅ Re-compile каждые 1000-10000 production interactions (continuous learning)
- ❌ Не optimize без validation set (overfitting!)

### Integration с Agentic-Flow
```typescript
import { AgenticFlow } from '@ruvnet/agentic-flow';
import { ChainOfThought, BootstrapFewShot } from '@ax-llm/ax';

// 1. Optimize agent с DSPy
const optimizedAgent = await optimizer.compile(agentSignature, { trainset });

// 2. Use в workflow
const workflow = new AgenticFlow({
  agents: {
    customer_service: {
      implementation: optimizedAgent  // DSPy-optimized
    }
  }
});
```

### Links
- Ax (recommended): https://github.com/ax-llm/ax
- dspy.ts: https://github.com/ruvnet/dspy.ts
- DSPy (Python original): https://dspy.ai/
- Tutorial: https://www.pondhouse-data.com/blog/dspy-build-better-ai-systems-with-automated-prompt-optimization

---

## 5. MidStream — Real-time Streaming Analytics

### Что это?
Платформа для real-time анализа LLM responses в процессе генерации (token-by-token).

### Ключевые концепции
- **Stream Introspection**: Анализ токенов по мере генерации
- **Pattern Detection**: Sentiment, confidence, hallucination, topic drift
- **Action Triggers**: Instant reactions на detected patterns
- **Multi-Modal**: Text, audio, video streams

### Установка
```bash
npm install midstream
# Rust core (for performance)
cargo add midstream  # If building from source
```

### Quick Start (TypeScript)
```typescript
import { MidStream, Pattern } from 'midstream';
import { GigaChatLLM } from './gigachat-adapter';

const llm = new GigaChatLLM();

// 1. Создать MidStream analyzer
const analyzer = new MidStream({
  patterns: [
    Pattern.SentimentAnalysis(),
    Pattern.ConfidenceTracking({ threshold: 0.5 }),
    Pattern.HallucinationDetection(),
    Pattern.PolicyViolation({ rules: ['no_medical_advice', 'no_financial_advice'] })
  ]
});

// 2. Обработка streaming response
const stream = llm.streamCompletion({
  prompt: "User question here",
  onToken: async (token, metadata) => {
    // MidStream анализирует каждый токен
    const events = await analyzer.analyze(token, metadata);

    events.forEach(event => {
      if (event.type === 'negative_sentiment' && event.severity > 0.7) {
        console.log('🚨 Negative sentiment detected! Escalating to human...');
        llm.abort();  // Stop generation
        escalateToHuman(conversationId);
      }

      if (event.type === 'low_confidence' && event.confidence < 0.5) {
        console.log('⚠️ Low confidence. Triggering RAG search...');
        // Enrich with knowledge base
        enrichWithContext(event.context);
      }

      if (event.type === 'policy_violation') {
        console.log('🛑 Policy violation! Aborting...');
        llm.abort();
        auditLog.record({ event, timestamp, userId });
      }
    });

    // Stream token to user
    userInterface.appendToken(token);
  }
});

await stream.complete();
```

### Pattern Detectors

#### Sentiment Analysis
```typescript
const sentimentPattern = Pattern.SentimentAnalysis({
  model: 'lightweight',  // or 'accurate' (slower)
  language: 'ru',        // Russian language support
  threshold: 0.6
});

analyzer.on('sentiment', (event) => {
  console.log(`Sentiment: ${event.score} (${event.label})`);
  // score: -1 (very negative) to +1 (very positive)
  // label: 'positive', 'neutral', 'negative'
});
```

#### Confidence Tracking
```typescript
const confidencePattern = Pattern.ConfidenceTracking({
  windowSize: 50,  // Analyze last 50 tokens
  threshold: 0.5
});

analyzer.on('confidence_drop', (event) => {
  if (event.confidence < 0.5) {
    // Agent uncertain → fetch more context
    triggerRAG(event.context);
  }
});
```

#### Hallucination Detection
```typescript
const hallucinationPattern = Pattern.HallucinationDetection({
  factCheck: true,            // Enable fact-checking (requires external API)
  factCheckProvider: 'web',   // or 'knowledge_base'
  threshold: 0.7
});

analyzer.on('hallucination', (event) => {
  console.warn('Possible hallucination detected:', event.statement);
  // Options:
  // 1. Abort generation
  // 2. Inject factual correction
  // 3. Flag for human review
});
```

### Multi-Agent Orchestration
```typescript
import { AgenticFlow } from '@ruvnet/agentic-flow';
import { MidStream } from 'midstream';

const workflow = new AgenticFlow({
  agents: [researchAgent, analysisAgent, writerAgent],

  // MidStream для каждого агента
  monitoring: {
    provider: 'midstream',
    config: {
      patterns: [
        Pattern.SentimentAnalysis(),
        Pattern.TopicDrift({ maxDivergence: 0.3 })
      ],
      actions: {
        onTopicDrift: async (agent, event) => {
          // Orchestrator redirects agent back to task
          console.log(`Agent ${agent.name} drifted off-topic. Refocusing...`);
          await workflow.refocus(agent, originalTask);
        },
        onAgentStuck: async (agent, duration) => {
          if (duration > 10000) {  // 10 seconds
            // Reassign task to another agent
            console.log(`Agent ${agent.name} stuck. Reassigning task...`);
            await workflow.reassign(task, backupAgent);
          }
        }
      }
    }
  }
});
```

### Voice Assistant (Barge-in)
```typescript
import { MidStream, Pattern } from 'midstream';

const voiceAgent = {
  speak: async (text) => { /* TTS */ },
  listen: async () => { /* STT */ }
};

const analyzer = new MidStream({
  patterns: [Pattern.UserInterruption()]
});

// Agent начинает говорить
const stream = voiceAgent.speak("The capital of Russia is Moscow, which...");

analyzer.on('user_interruption', async (event) => {
  // User starts speaking → agent immediately stops
  console.log('User interrupted at:', event.timestamp);
  stream.abort();

  // Resume from interruption point (contextual)
  const userInput = await voiceAgent.listen();
  const resumeContext = stream.getContextAt(event.timestamp);

  // Continue conversation
  await handleUserInput(userInput, resumeContext);
});
```

### Performance Metrics
```typescript
// MidStream overhead: <2ms per token
analyzer.getMetrics();
// → {
//     tokensAnalyzed: 1523,
//     averageLatency: 1.2ms,
//     patternsDetected: { sentiment: 45, confidence_drop: 3 },
//     totalTime: 1.8s
//   }
```

### Best Practices
- ✅ **Customer-facing agents**: Always monitor sentiment (escalate негатив)
- ✅ **Compliance-critical**: Policy violation detection обязателен
- ✅ **Voice assistants**: User interruption для natural barge-in
- ✅ **Multi-agent**: Topic drift detection для orchestration
- ❌ Не используйте too many patterns одновременно (latency overhead)

### Links
- GitHub: https://github.com/ruvnet/midstream
- Docs: https://github.com/ruvnet/midstream/wiki
- Google Research: https://developers.googleblog.com/en/beyond-request-response-architecting-real-time-bidirectional-streaming-multi-agent-system/

---

## 6. MAESTRO Security Framework

### Что это?
**Multi-Agent Environment, Security, Threat, Risk, and Outcome** — threat modeling фреймворк от Cloud Security Alliance для agentic AI.

### Ключевые угрозы для Multi-Agent Systems
1. **Memory Poisoning**: Инъекция ложной информации в agent memory
2. **Tool Orchestration Attacks**: Cascading compromises через agent tools
3. **Multi-Agent Collusion**: Secret coordination между агентами
4. **Prompt Injection**: Advanced indirect injection через shared data
5. **Data Exfiltration**: Unauthorized access via agent actions

### Implementation (TypeScript)
```typescript
import { MAESTRO, ThreatModel, SecurityPolicy } from '@cloudru/agentic-security';

// 1. Определить threat model для agent
const customerServiceThreatModel = new ThreatModel({
  agentType: 'customer_service',
  dataAccess: ['customer_db', 'order_history'],
  toolAccess: ['send_email', 'create_ticket'],
  threats: [
    'memory_poisoning',
    'prompt_injection',
    'data_exfiltration'
  ]
});

// 2. Создать security policy
const policy = new SecurityPolicy({
  framework: MAESTRO,
  threatModel: customerServiceThreatModel,

  // Identity & Access
  identity: {
    type: 'zero_trust',
    agentID: generateCryptoID(),
    authentication: 'mutual_tls'
  },

  // Data Protection
  dataProtection: {
    encryption: {
      atRest: 'GOST_28147_89',  // Russian standard
      inTransit: 'TLS_1.3'
    },
    piiHandling: {
      detect: true,
      mask: true,
      logAccess: true
    }
  },

  // Tool Permissions
  toolGovernance: {
    allowlist: ['send_email', 'create_ticket'],
    rateLimit: { maxPerMinute: 100 },
    requireApproval: ['delete_customer']  // Human-in-the-loop
  },

  // Memory Protection
  memoryProtection: {
    anomalyDetection: true,
    poisoningPrevention: {
      validateSources: true,
      crossCheck: true
    }
  },

  // Compliance
  compliance: {
    frameworks: ['152FZ', 'GDPR', 'CBR'],  // Russian regulations
    auditLog: {
      enabled: true,
      immutable: true,
      retention: '7_years'
    }
  }
});

// 3. Apply policy to agent
const securedAgent = await policy.secure(customerServiceAgent);
```

### Memory Poisoning Prevention
```typescript
import { MemoryGuard } from '@cloudru/agentic-security';

const memoryGuard = new MemoryGuard({
  anomalyDetection: {
    enabled: true,
    model: 'isolation_forest',
    threshold: 0.8
  },
  sourceValidation: {
    trustedSources: ['agentdb://verified', 'milvus://production'],
    rejectUnknown: true
  },
  crossChecking: {
    enabled: true,
    minConfidence: 0.7
  }
});

// Перед сохранением в memory
const dataToStore = { userId: '123', preference: 'premium_plan' };

const validationResult = await memoryGuard.validate(dataToStore, {
  source: 'user_input',  // Untrusted source
  context: conversationHistory
});

if (validationResult.safe) {
  await agentDB.store(dataToStore);
} else {
  console.warn('Potential memory poisoning:', validationResult.threats);
  // Log для security team
  await securityLog.record({ type: 'memory_poisoning_attempt', ...validationResult });
}
```

### Tool Permission Governance
```typescript
// Agent пытается вызвать tool
async function executeAgentAction(agent, toolName, params) {
  // 1. Check allowlist
  if (!policy.toolGovernance.allowlist.includes(toolName)) {
    throw new SecurityError(`Tool ${toolName} not in allowlist`);
  }

  // 2. Rate limiting
  const rateLimit = await rateLimiter.check(agent.id, toolName);
  if (!rateLimit.allowed) {
    throw new RateLimitError(`Tool ${toolName} rate limit exceeded`);
  }

  // 3. Human-in-the-loop для sensitive actions
  if (policy.toolGovernance.requireApproval.includes(toolName)) {
    const approval = await requestHumanApproval({
      agent: agent.id,
      tool: toolName,
      params: params,
      reason: agent.reasoning
    });

    if (!approval.granted) {
      throw new SecurityError('Human approval denied');
    }
  }

  // 4. Audit log (immutable)
  await auditLog.record({
    timestamp: Date.now(),
    agent: agent.id,
    action: toolName,
    params: sanitize(params),  // Remove PII
    approved: true
  });

  // 5. Execute with sandboxing
  return await sandbox.execute(toolName, params, {
    timeout: 30000,
    memoryLimit: '256MB',
    networkAccess: policy.toolGovernance.networkAccess[toolName] || false
  });
}
```

### Compliance Automation (152-ФЗ)
```typescript
import { ComplianceChecker } from '@cloudru/agentic-security';

const checker = new ComplianceChecker({
  framework: '152FZ',  // Russian personal data law
  strictMode: true
});

// Перед отправкой response пользователю
const agentResponse = "Your order #12345 will be delivered to user@example.com";

const complianceCheck = await checker.validate(agentResponse);

if (!complianceCheck.compliant) {
  console.error('Compliance violation:', complianceCheck.violations);
  // violations: [{ type: 'PII_exposure', field: 'email', severity: 'high' }]

  // Auto-redact
  const redactedResponse = await checker.redact(agentResponse);
  // → "Your order #12345 will be delivered to [REDACTED]"

  return redactedResponse;
}
```

### Red-Team Testing
```typescript
// Adversarial agent для testing
import { AdversarialAgent, AttackScenarios } from '@cloudru/agentic-security';

const redTeamAgent = new AdversarialAgent({
  scenarios: [
    AttackScenarios.PromptInjection,
    AttackScenarios.MemoryPoisoning,
    AttackScenarios.ToolChaining,
    AttackScenarios.DataExfiltration
  ]
});

// Run attack simulation
const results = await redTeamAgent.attack(customerServiceAgent, {
  duration: '1_hour',
  intensity: 'high',
  recordAll: true
});

console.log('Vulnerabilities found:', results.vulnerabilities);
// → [
//     { type: 'prompt_injection', severity: 'medium', poc: '...' },
//     { type: 'rate_limit_bypass', severity: 'low', poc: '...' }
//   ]
```

### Links
- CSA MAESTRO: https://cloudsecurityalliance.org/blog/2025/02/06/agentic-ai-threat-modeling-framework-maestro
- AWS Security Matrix: https://aws.amazon.com/blogs/security/the-agentic-ai-security-scoping-matrix-a-framework-for-securing-autonomous-ai-systems/
- OWASP Agentic AI: (Expected Q2 2025)

---

## 7. Integration Example: Complete Stack

### Полный пример: Customer Service Agent

```typescript
import { AgenticFlow, OrchestratorPattern } from '@ruvnet/agentic-flow';
import { AgentDB } from '@agentdb/core';
import { ChainOfThought, BootstrapFewShot } from '@ax-llm/ax';
import { MidStream, Pattern } from 'midstream';
import { SecurityPolicy, MAESTRO } from '@cloudru/agentic-security';
import { MilvusClient } from '@zilliz/milvus2-sdk-node';

// 1. SECURITY POLICY
const securityPolicy = new SecurityPolicy({
  framework: MAESTRO,
  compliance: ['152FZ', 'GDPR'],
  dataProtection: { encryption: 'GOST_28147_89' },
  toolGovernance: { allowlist: ['query_db', 'send_email'] }
});

// 2. VECTOR DB для long-term memory
const vectorDB = new MilvusClient({ address: 'milvus.cloudru.internal' });

// 3. AGENT STATE с AgentDB
const conversationDB = await AgentDB.create(generateUUID(), {
  template: 'customer-service',
  lifecycle: 'session'
});

// 4. DSPY OPTIMIZATION
class CustomerServiceAgent extends Signature {
  @Input("Customer question") question: string;
  @Input("Customer history") history: string;
  @Output("Helpful response") answer: string;
}

const optimizer = new BootstrapFewShot({ metric: csatMetric });
const optimizedAgent = await optimizer.compile(
  new ChainOfThought(CustomerServiceAgent, { llm: gigaChatLLM }),
  { trainset: trainingData }
);

// 5. WORKFLOW ORCHESTRATION
const workflow = new AgenticFlow({
  pattern: OrchestratorPattern,
  agents: {
    primary: optimizedAgent,
    escalation: humanSupervisor
  },
  stateManagement: { provider: conversationDB },
  security: securityPolicy
});

// 6. EXECUTION с MidStream monitoring
async function handleCustomerQuery(userQuery, userId) {
  // Retrieve customer history (RAG)
  const customerHistory = await vectorDB.search({
    collection_name: 'customer_interactions',
    vectors: [await embedQuery(userQuery)],
    limit: 5,
    filter: `user_id == "${userId}"`
  });

  // MidStream analyzer
  const analyzer = new MidStream({
    patterns: [
      Pattern.SentimentAnalysis(),
      Pattern.ConfidenceTracking({ threshold: 0.5 }),
      Pattern.PolicyViolation({ rules: ['no_pii'] })
    ]
  });

  // Execute workflow
  const response = await workflow.execute({
    input: {
      question: userQuery,
      history: customerHistory.map(h => h.entity.text).join('\n')
    },

    // Real-time monitoring
    streaming: {
      analyzer,
      onEvent: async (event) => {
        if (event.type === 'negative_sentiment' && event.severity > 0.7) {
          await workflow.escalate('humanSupervisor');
        }
        if (event.type === 'policy_violation') {
          workflow.abort();
          await auditLog.record({ event, userId });
        }
      }
    }
  });

  // Store interaction
  await conversationDB.query(
    'INSERT INTO interactions (user_id, query, response) VALUES (?, ?, ?)',
    [userId, userQuery, response.answer]
  );

  await vectorDB.insert({
    collection_name: 'customer_interactions',
    data: [{
      vector: await embedInteraction(userQuery, response.answer),
      text: response.answer,
      user_id: userId,
      timestamp: Date.now()
    }]
  });

  return response;
}

// 7. CONTINUOUS LEARNING
setInterval(async () => {
  const recentInteractions = await conversationDB.query(
    'SELECT * FROM interactions WHERE timestamp > ?',
    [Date.now() - 86400000]  // Last 24 hours
  );

  if (recentInteractions.length >= 1000) {
    console.log('Re-optimizing agent with recent data...');
    const improvedAgent = await optimizer.compile(
      optimizedAgent,
      { trainset: recentInteractions }
    );
    workflow.updateAgent('primary', improvedAgent);
  }
}, 86400000);  // Daily
```

---

## Полезные Ссылки

### Documentation
- **AgentDB**: https://agentdb.dev/
- **Milvus**: https://milvus.io/docs
- **Agentic-Flow**: https://github.com/ruvnet/claude-flow
- **DSPy**: https://dspy.ai/ (Python), https://github.com/ax-llm/ax (TypeScript)
- **MidStream**: https://github.com/ruvnet/midstream
- **MAESTRO**: https://cloudsecurityalliance.org/blog/2025/02/06/agentic-ai-threat-modeling-framework-maestro

### Community
- **ruvnet GitHub**: https://github.com/ruvnet (Creator of many tools)
- **MCP Ecosystem**: https://github.com/topics/model-context-protocol
- **Cloud.ru Internal**: Slack #multi-agent-platform

### Training
- **DSPy Tutorial**: https://www.pondhouse-data.com/blog/dspy-build-better-ai-systems-with-automated-prompt-optimization
- **Milvus Course**: https://www.youtube.com/playlist?list=PLPOTzZz4A8F5yMVwYJzYVcGLYEHYUX2XT
- **LangGraph Academy**: https://academy.langchain.com/

---

## Troubleshooting

### AgentDB: Connection refused
```bash
# Check if AgentDB server running
curl http://localhost:3000/health

# Restart server
docker restart agentdb-server
```

### Milvus: "Collection not found"
```python
# List all collections
from pymilvus import utility
utility.list_collections()

# Create if missing
collection.create()
```

### DSPy: Optimization fails
```typescript
// Common issue: insufficient training data
// Solution: Increase trainset size (min 50 examples)

// Debug optimization
optimizer.compile(agent, {
  trainset,
  verbose: true,  // See detailed logs
  numThreads: 4   // Parallel optimization
});
```

### MidStream: High latency
```typescript
// Reduce number of patterns
const analyzer = new MidStream({
  patterns: [
    Pattern.SentimentAnalysis({ model: 'lightweight' })  // Use lighter model
  ]
});

// Or increase batch size
analyzer.configure({ batchSize: 50 });  // Process 50 tokens at once
```

---

**Last Updated**: November 2025
**Maintained by**: Cloud.ru Multi-Agent Platform Team
**Questions?**: Slack #multi-agent-platform
