# CLOUD.RU PLATFORM: API Contracts & Integration Interfaces

**Версия:** 1.0
**Дата:** 27 ноября 2025

---

## OVERVIEW

Этот документ определяет API контракты между всеми компонентами платформы Cloud.ru:

1. **External APIs** (REST/GraphQL) — для клиентов платформы
2. **Internal APIs** (gRPC) — для inter-service communication
3. **Event Schemas** (NATS/Kafka) — для event-driven architecture
4. **Storage Schemas** — для AgentDB, RuVector

---

## PART 1: EXTERNAL REST APIs

### 1.1 Agent Management API

#### POST /api/v1/agents
Создание нового агента

**Request:**
```json
{
  "name": "customer-support-agent",
  "description": "Handles customer inquiries and support tickets",
  "type": "conversational",
  "config": {
    "llm": {
      "provider": "gigachat",
      "model": "gigachat-pro",
      "temperature": 0.7,
      "max_tokens": 2000
    },
    "tools": [
      {
        "name": "search",
        "type": "mcp",
        "endpoint": "https://tools.cloud.ru/search"
      },
      {
        "name": "calculator",
        "type": "builtin"
      }
    ],
    "memory": {
      "short_term": {
        "type": "redis",
        "ttl": 3600
      },
      "long_term": {
        "type": "ruvector",
        "collection": "agent-memory-cs",
        "max_entries": 10000
      }
    },
    "guardrails": {
      "max_turns": 50,
      "timeout_seconds": 300,
      "allowed_topics": ["support", "products", "billing"]
    }
  },
  "security": {
    "rbac_policy": "customer-support-policy",
    "pii_detection": true,
    "pii_entities": ["NAME", "EMAIL", "PHONE", "INN"],
    "prompt_injection_defense": "strict",
    "audit_level": "full"
  },
  "metadata": {
    "department": "customer-service",
    "owner": "team-cs@company.com",
    "cost_center": "CS-001"
  }
}
```

**Response (201 Created):**
```json
{
  "agent_id": "agt_2J5K9L3M7N1P4Q6R",
  "name": "customer-support-agent",
  "status": "created",
  "created_at": "2025-11-27T10:30:00Z",
  "endpoints": {
    "execute_sync": "https://api.cloud.ru/v1/agents/agt_2J5K9L3M7N1P4Q6R/execute",
    "execute_stream": "wss://stream.cloud.ru/v1/agents/agt_2J5K9L3M7N1P4Q6R",
    "status": "https://api.cloud.ru/v1/agents/agt_2J5K9L3M7N1P4Q6R",
    "metrics": "https://api.cloud.ru/v1/agents/agt_2J5K9L3M7N1P4Q6R/metrics"
  },
  "api_key": "sk_live_abc123def456..."
}
```

#### POST /api/v1/agents/{agent_id}/execute
Выполнение агента (синхронно)

**Request:**
```json
{
  "input": "What is the status of order #12345?",
  "context": {
    "user_id": "usr_ABC123",
    "session_id": "sess_XYZ789",
    "language": "ru",
    "metadata": {
      "channel": "web",
      "ip": "192.168.1.1"
    }
  },
  "options": {
    "stream": false,
    "include_reasoning": true,
    "include_tool_calls": true,
    "max_tokens": 1000,
    "temperature_override": 0.5
  }
}
```

**Response (200 OK):**
```json
{
  "agent_id": "agt_2J5K9L3M7N1P4Q6R",
  "execution_id": "exe_9K8L7M6N5P4Q",
  "output": {
    "text": "Order #12345 is currently in transit. Expected delivery: November 30, 2025. Tracking number: RU123456789.",
    "confidence": 0.95,
    "sources": [
      {
        "type": "database",
        "query": "SELECT status FROM orders WHERE id = 12345",
        "result": "in_transit"
      }
    ]
  },
  "reasoning": {
    "steps": [
      "Extracted order number: 12345",
      "Queried order database",
      "Retrieved status: in_transit",
      "Formatted response for user"
    ]
  },
  "tool_calls": [
    {
      "tool": "database_query",
      "input": "SELECT * FROM orders WHERE id = 12345",
      "output": {
        "status": "in_transit",
        "tracking": "RU123456789",
        "eta": "2025-11-30"
      },
      "latency_ms": 45
    }
  ],
  "metadata": {
    "tokens_used": {
      "input": 124,
      "output": 67,
      "total": 191
    },
    "latency_ms": 324,
    "cost_usd": 0.0023,
    "llm_provider": "gigachat",
    "llm_model": "gigachat-pro",
    "cache_hit": false,
    "pii_detected": false
  },
  "created_at": "2025-11-27T10:35:12Z"
}
```

#### POST /api/v1/agents/{agent_id}/execute (Streaming)

**Request:**
```json
{
  "input": "Explain quantum computing in simple terms",
  "stream": true
}
```

**Response (200 OK, text/event-stream):**
```
event: start
data: {"execution_id": "exe_ABC123"}

event: token
data: {"content": "Quantum"}

event: token
data: {"content": " computing"}

event: token
data: {"content": " is"}

event: token
data: {"content": " a"}

event: tool_call
data: {"tool": "search", "query": "quantum computing basics"}

event: token
data: {"content": " revolutionary"}

...

event: done
data: {"tokens": 234, "latency_ms": 1560, "cost_usd": 0.0045}
```

### 1.2 Workflow API (Agentic-Flow)

#### POST /api/v1/workflows
Создание workflow

**Request:**
```json
{
  "name": "document-analysis-pipeline",
  "description": "Extracts, summarizes, and classifies documents",
  "steps": [
    {
      "id": "extract",
      "name": "PDF Text Extraction",
      "agent": "pdf-extractor",
      "inputs": {
        "document_url": "{{workflow.inputs.document_url}}"
      },
      "timeout_seconds": 300
    },
    {
      "id": "summarize",
      "name": "Document Summarization",
      "agent": "summarizer",
      "inputs": {
        "text": "{{steps.extract.output.text}}",
        "max_length": 500
      },
      "depends_on": ["extract"],
      "timeout_seconds": 120
    },
    {
      "id": "classify",
      "name": "Document Classification",
      "agent": "classifier",
      "inputs": {
        "text": "{{steps.summarize.output.summary}}"
      },
      "depends_on": ["summarize"],
      "timeout_seconds": 60
    },
    {
      "id": "approval",
      "name": "Human Review",
      "type": "human_in_the_loop",
      "inputs": {
        "summary": "{{steps.summarize.output}}",
        "classification": "{{steps.classify.output}}"
      },
      "depends_on": ["classify"],
      "timeout_seconds": 86400
    }
  ],
  "error_handling": {
    "retry": {
      "max_attempts": 3,
      "backoff": "exponential",
      "initial_delay_seconds": 1
    },
    "on_failure": "rollback"
  },
  "notifications": {
    "on_complete": {
      "webhook": "https://myapp.com/webhooks/workflow-complete",
      "email": "team@company.com"
    },
    "on_failure": {
      "webhook": "https://myapp.com/webhooks/workflow-failed",
      "pagerduty": "service-key-123"
    }
  }
}
```

**Response (201 Created):**
```json
{
  "workflow_id": "wf_9K2L5M8N4P7Q",
  "name": "document-analysis-pipeline",
  "status": "created",
  "created_at": "2025-11-27T11:00:00Z",
  "endpoints": {
    "execute": "https://api.cloud.ru/v1/workflows/wf_9K2L5M8N4P7Q/execute",
    "status": "https://api.cloud.ru/v1/workflows/wf_9K2L5M8N4P7Q/status"
  }
}
```

#### POST /api/v1/workflows/{workflow_id}/execute
Запуск workflow

**Request:**
```json
{
  "inputs": {
    "document_url": "https://storage.cloud.ru/docs/quarterly-report-q4-2025.pdf"
  },
  "options": {
    "priority": "high",
    "notifications": {
      "email": "analyst@company.com"
    }
  }
}
```

**Response (202 Accepted):**
```json
{
  "workflow_id": "wf_9K2L5M8N4P7Q",
  "execution_id": "wfe_5M8N4P7Q2K9L",
  "status": "running",
  "started_at": "2025-11-27T11:05:00Z",
  "progress": {
    "current_step": "extract",
    "current_step_index": 0,
    "completed_steps": 0,
    "total_steps": 4,
    "percentage": 0
  },
  "endpoints": {
    "status": "https://api.cloud.ru/v1/workflows/wf_9K2L5M8N4P7Q/executions/wfe_5M8N4P7Q2K9L",
    "stream": "wss://stream.cloud.ru/v1/workflows/wf_9K2L5M8N4P7Q/executions/wfe_5M8N4P7Q2K9L"
  }
}
```

#### GET /api/v1/workflows/{workflow_id}/executions/{execution_id}
Получить статус выполнения

**Response (200 OK):**
```json
{
  "workflow_id": "wf_9K2L5M8N4P7Q",
  "execution_id": "wfe_5M8N4P7Q2K9L",
  "status": "completed",
  "started_at": "2025-11-27T11:05:00Z",
  "completed_at": "2025-11-27T11:07:34Z",
  "duration_seconds": 154,
  "steps": [
    {
      "id": "extract",
      "status": "completed",
      "started_at": "2025-11-27T11:05:00Z",
      "completed_at": "2025-11-27T11:05:45Z",
      "duration_seconds": 45,
      "output": {
        "text": "Full extracted text...",
        "pages": 127,
        "word_count": 45678
      }
    },
    {
      "id": "summarize",
      "status": "completed",
      "started_at": "2025-11-27T11:05:45Z",
      "completed_at": "2025-11-27T11:06:30Z",
      "duration_seconds": 45,
      "output": {
        "summary": "Q4 2025 showed strong growth...",
        "key_points": ["Revenue +23%", "New customers +15%"]
      }
    },
    {
      "id": "classify",
      "status": "completed",
      "started_at": "2025-11-27T11:06:30Z",
      "completed_at": "2025-11-27T11:06:42Z",
      "duration_seconds": 12,
      "output": {
        "category": "financial_report",
        "confidence": 0.98,
        "tags": ["quarterly", "public", "financial"]
      }
    },
    {
      "id": "approval",
      "status": "completed",
      "started_at": "2025-11-27T11:06:42Z",
      "completed_at": "2025-11-27T11:07:34Z",
      "duration_seconds": 52,
      "output": {
        "approved": true,
        "approver": "user_ABC123",
        "comments": "Looks good"
      }
    }
  ],
  "output": {
    "summary": "Q4 2025 showed strong growth...",
    "classification": "financial_report",
    "approved": true
  },
  "metadata": {
    "total_cost_usd": 0.156,
    "total_tokens": 12456
  }
}
```

### 1.3 Vector Search API (RuVector)

#### POST /api/v1/vector/search
Семантический поиск

**Request:**
```json
{
  "collection": "knowledge-base",
  "query": "How do I reset my password?",
  "top_k": 5,
  "filters": {
    "category": {
      "$eq": "faq"
    },
    "language": {
      "$eq": "ru"
    },
    "updated_at": {
      "$gte": "2025-01-01T00:00:00Z"
    }
  },
  "options": {
    "include_metadata": true,
    "include_vectors": false,
    "similarity_metric": "cosine",
    "min_score": 0.7
  }
}
```

**Response (200 OK):**
```json
{
  "collection": "knowledge-base",
  "query": "How do I reset my password?",
  "results": [
    {
      "id": "doc_kb_12345",
      "score": 0.94,
      "text": "Для сброса пароля перейдите в раздел 'Настройки' → 'Безопасность' → 'Сменить пароль'. Введите текущий пароль и новый пароль дважды.",
      "metadata": {
        "category": "faq",
        "language": "ru",
        "title": "Смена пароля",
        "updated_at": "2025-10-15T14:30:00Z",
        "views": 1234,
        "helpful_votes": 89
      }
    },
    {
      "id": "doc_kb_67890",
      "score": 0.87,
      "text": "Если вы забыли пароль, нажмите 'Забыли пароль?' на странице входа. На вашу почту будет отправлена ссылка для сброса.",
      "metadata": {
        "category": "faq",
        "language": "ru",
        "title": "Восстановление пароля",
        "updated_at": "2025-09-20T10:15:00Z"
      }
    }
  ],
  "metadata": {
    "total_results": 2,
    "latency_ms": 34,
    "embedding_model": "e5-mistral-7b",
    "embedding_latency_ms": 12,
    "search_latency_ms": 22
  }
}
```

#### POST /api/v1/vector/insert
Вставка векторов

**Request:**
```json
{
  "collection": "agent-memory",
  "documents": [
    {
      "id": "mem_usr123_001",
      "text": "User prefers morning meetings between 9-11 AM",
      "metadata": {
        "user_id": "usr_123",
        "type": "preference",
        "category": "scheduling",
        "confidence": 0.9,
        "timestamp": "2025-11-27T10:00:00Z"
      }
    },
    {
      "id": "mem_usr123_002",
      "text": "User's favorite coffee is cappuccino",
      "metadata": {
        "user_id": "usr_123",
        "type": "preference",
        "category": "personal",
        "timestamp": "2025-11-27T10:05:00Z"
      }
    }
  ],
  "options": {
    "embedding_model": "e5-mistral-7b",
    "upsert": true,
    "batch_size": 100
  }
}
```

**Response (200 OK):**
```json
{
  "collection": "agent-memory",
  "inserted": 2,
  "updated": 0,
  "failed": 0,
  "ids": ["mem_usr123_001", "mem_usr123_002"],
  "metadata": {
    "latency_ms": 67,
    "embedding_latency_ms": 45,
    "insert_latency_ms": 22
  }
}
```

---

## PART 2: INTERNAL gRPC APIs

### 2.1 AgentDB Service

```protobuf
syntax = "proto3";

package agentdb.v1;

service AgentDB {
  // Agent State Management
  rpc UpsertAgentState(UpsertAgentStateRequest) returns (UpsertAgentStateResponse);
  rpc GetAgentState(GetAgentStateRequest) returns (GetAgentStateResponse);
  rpc DeleteAgentState(DeleteAgentStateRequest) returns (DeleteAgentStateResponse);

  // Agent Lifecycle
  rpc CreateAgent(CreateAgentRequest) returns (CreateAgentResponse);
  rpc SuspendAgent(SuspendAgentRequest) returns (SuspendAgentResponse);
  rpc ResumeAgent(ResumeAgentRequest) returns (ResumeAgentResponse);
  rpc TerminateAgent(TerminateAgentRequest) returns (TerminateAgentResponse);

  // Query
  rpc QueryAgents(QueryAgentsRequest) returns (stream Agent);
  rpc GetAgentMetrics(GetAgentMetricsRequest) returns (GetAgentMetricsResponse);
}

message UpsertAgentStateRequest {
  string agent_id = 1;
  AgentState state = 2;
  bool create_snapshot = 3;
  string snapshot_id = 4;
}

message AgentState {
  string agent_id = 1;
  AgentStatus status = 2;
  map<string, string> variables = 3;
  repeated Conversation conversations = 4;
  AgentMemory memory = 5;
  int64 updated_at = 6;
  int32 version = 7;
}

enum AgentStatus {
  AGENT_STATUS_UNSPECIFIED = 0;
  AGENT_STATUS_CREATED = 1;
  AGENT_STATUS_ACTIVE = 2;
  AGENT_STATUS_SUSPENDED = 3;
  AGENT_STATUS_TERMINATED = 4;
  AGENT_STATUS_ERROR = 5;
}

message Conversation {
  string conversation_id = 1;
  repeated Message messages = 2;
  int64 created_at = 3;
  int64 updated_at = 4;
}

message Message {
  string message_id = 1;
  MessageRole role = 2;
  string content = 3;
  map<string, string> metadata = 4;
  int64 timestamp = 5;
}

enum MessageRole {
  MESSAGE_ROLE_UNSPECIFIED = 0;
  MESSAGE_ROLE_USER = 1;
  MESSAGE_ROLE_ASSISTANT = 2;
  MESSAGE_ROLE_SYSTEM = 3;
  MESSAGE_ROLE_TOOL = 4;
}

message AgentMemory {
  ShortTermMemory short_term = 1;
  LongTermMemory long_term = 2;
  EpisodicMemory episodic = 3;
}

message ShortTermMemory {
  map<string, string> session_variables = 1;
  int64 ttl_seconds = 2;
}

message LongTermMemory {
  string ruvector_collection = 1;
  repeated string vector_ids = 2;
}

message EpisodicMemory {
  repeated Episode episodes = 1;
}

message Episode {
  string episode_id = 1;
  string description = 2;
  int64 timestamp = 3;
  map<string, string> context = 4;
}
```

**Example Usage (TypeScript):**
```typescript
import { AgentDBClient } from '@cloud-ru/agentdb-grpc';

const client = new AgentDBClient('agentdb.cloud.ru:443', {
  credentials: grpc.credentials.createSsl(),
  interceptors: [authInterceptor]
});

// Upsert agent state
const response = await client.upsertAgentState({
  agentId: 'agt_123',
  state: {
    agentId: 'agt_123',
    status: AgentStatus.AGENT_STATUS_ACTIVE,
    variables: {
      last_topic: 'weather',
      user_preference: 'detailed_responses'
    },
    conversations: [
      {
        conversationId: 'conv_456',
        messages: [
          {
            messageId: 'msg_789',
            role: MessageRole.MESSAGE_ROLE_USER,
            content: 'What is the weather?',
            timestamp: Date.now()
          }
        ]
      }
    ],
    updatedAt: Date.now(),
    version: 1
  },
  createSnapshot: true
});

console.log('State saved:', response);
```

### 2.2 RuVector Service

```protobuf
syntax = "proto3";

package ruvector.v1;

service RuVector {
  // Search
  rpc Search(SearchRequest) returns (SearchResponse);
  rpc BatchSearch(BatchSearchRequest) returns (stream SearchResponse);

  // Insert/Update/Delete
  rpc Insert(InsertRequest) returns (InsertResponse);
  rpc BatchInsert(BatchInsertRequest) returns (BatchInsertResponse);
  rpc Delete(DeleteRequest) returns (DeleteResponse);

  // Collection Management
  rpc CreateCollection(CreateCollectionRequest) returns (CreateCollectionResponse);
  rpc DeleteCollection(DeleteCollectionRequest) returns (DeleteCollectionResponse);
  rpc GetCollectionInfo(GetCollectionInfoRequest) returns (GetCollectionInfoResponse);
}

message SearchRequest {
  string collection = 1;
  oneof query {
    repeated float query_vector = 2;
    string query_text = 3;
  }
  int32 top_k = 4;
  Filter filter = 5;
  SearchOptions options = 6;
}

message Filter {
  repeated FilterCondition conditions = 1;
  FilterOperator operator = 2;
}

message FilterCondition {
  string field = 1;
  FilterOperator operator = 2;
  oneof value {
    string string_value = 3;
    int64 int_value = 4;
    double double_value = 5;
    bool bool_value = 6;
  }
}

enum FilterOperator {
  FILTER_OPERATOR_UNSPECIFIED = 0;
  FILTER_OPERATOR_EQ = 1;
  FILTER_OPERATOR_NE = 2;
  FILTER_OPERATOR_GT = 3;
  FILTER_OPERATOR_GTE = 4;
  FILTER_OPERATOR_LT = 5;
  FILTER_OPERATOR_LTE = 6;
  FILTER_OPERATOR_IN = 7;
  FILTER_OPERATOR_AND = 8;
  FILTER_OPERATOR_OR = 9;
}

message SearchOptions {
  string similarity_metric = 1; // cosine, l2, inner_product
  float min_score = 2;
  bool include_metadata = 3;
  bool include_vectors = 4;
}

message SearchResponse {
  string collection = 1;
  repeated SearchResult results = 2;
  SearchMetadata metadata = 3;
}

message SearchResult {
  string id = 1;
  float score = 2;
  string text = 3;
  repeated float vector = 4;
  map<string, string> metadata = 5;
}

message SearchMetadata {
  int32 total_results = 1;
  int64 latency_ms = 2;
  string embedding_model = 3;
}
```

### 2.3 Agentic-Flow Service

```protobuf
syntax = "proto3";

package agenticflow.v1;

service AgenticFlow {
  // Workflow Execution
  rpc ExecuteWorkflow(ExecuteWorkflowRequest) returns (stream WorkflowEvent);
  rpc GetWorkflowStatus(GetWorkflowStatusRequest) returns (WorkflowStatus);

  // Workflow Control
  rpc PauseWorkflow(PauseWorkflowRequest) returns (PauseWorkflowResponse);
  rpc ResumeWorkflow(ResumeWorkflowRequest) returns (ResumeWorkflowResponse);
  rpc CancelWorkflow(CancelWorkflowRequest) returns (CancelWorkflowResponse);

  // Human-in-the-Loop
  rpc ApproveStep(ApproveStepRequest) returns (ApproveStepResponse);
  rpc RejectStep(RejectStepRequest) returns (RejectStepResponse);
}

message ExecuteWorkflowRequest {
  string workflow_id = 1;
  map<string, Value> inputs = 2;
  ExecutionOptions options = 3;
}

message ExecutionOptions {
  string priority = 1; // low, normal, high
  int64 timeout_seconds = 2;
  map<string, string> labels = 3;
}

message WorkflowEvent {
  EventType type = 1;
  string step_id = 2;
  Value output = 3;
  WorkflowMetadata metadata = 4;
  int64 timestamp = 5;
}

enum EventType {
  EVENT_TYPE_UNSPECIFIED = 0;
  EVENT_TYPE_WORKFLOW_START = 1;
  EVENT_TYPE_STEP_START = 2;
  EVENT_TYPE_STEP_COMPLETE = 3;
  EVENT_TYPE_STEP_ERROR = 4;
  EVENT_TYPE_STEP_RETRY = 5;
  EVENT_TYPE_WORKFLOW_COMPLETE = 6;
  EVENT_TYPE_WORKFLOW_ERROR = 7;
  EVENT_TYPE_HUMAN_INPUT_REQUIRED = 8;
}

message Value {
  oneof kind {
    string string_value = 1;
    int64 int_value = 2;
    double double_value = 3;
    bool bool_value = 4;
    bytes bytes_value = 5;
    google.protobuf.Struct struct_value = 6;
  }
}
```

---

## PART 3: EVENT SCHEMAS (NATS/Kafka)

### 3.1 Agent Events

```json
{
  "event_type": "agent.created",
  "event_id": "evt_abc123def456",
  "timestamp": "2025-11-27T10:30:00Z",
  "source": "agentdb.v1",
  "data": {
    "agent_id": "agt_123",
    "name": "customer-support-agent",
    "type": "conversational",
    "created_by": "usr_ABC"
  }
}

{
  "event_type": "agent.state_changed",
  "event_id": "evt_def789ghi012",
  "timestamp": "2025-11-27T10:35:00Z",
  "source": "agentdb.v1",
  "data": {
    "agent_id": "agt_123",
    "old_status": "created",
    "new_status": "active",
    "changed_by": "system"
  }
}

{
  "event_type": "agent.execution_complete",
  "event_id": "evt_ghi345jkl678",
  "timestamp": "2025-11-27T10:36:00Z",
  "source": "agent-runtime.v1",
  "data": {
    "agent_id": "agt_123",
    "execution_id": "exe_789",
    "duration_ms": 324,
    "tokens_used": 191,
    "cost_usd": 0.0023,
    "success": true
  }
}
```

### 3.2 Workflow Events

```json
{
  "event_type": "workflow.step_complete",
  "event_id": "evt_mno901pqr234",
  "timestamp": "2025-11-27T11:05:45Z",
  "source": "agentic-flow.v1",
  "data": {
    "workflow_id": "wf_456",
    "execution_id": "wfe_789",
    "step_id": "extract",
    "status": "completed",
    "duration_seconds": 45,
    "output": {
      "text": "...",
      "pages": 127
    }
  }
}

{
  "event_type": "workflow.human_input_required",
  "event_id": "evt_stu567vwx890",
  "timestamp": "2025-11-27T11:06:42Z",
  "source": "agentic-flow.v1",
  "data": {
    "workflow_id": "wf_456",
    "execution_id": "wfe_789",
    "step_id": "approval",
    "approval_url": "https://app.cloud.ru/approve/wfe_789/approval",
    "timeout_at": "2025-11-28T11:06:42Z"
  }
}
```

### 3.3 Security Events

```json
{
  "event_type": "security.prompt_injection_detected",
  "event_id": "evt_yza123bcd456",
  "timestamp": "2025-11-27T12:00:00Z",
  "source": "agentic-security.v1",
  "severity": "high",
  "data": {
    "agent_id": "agt_123",
    "user_id": "usr_XYZ",
    "input": "Ignore previous instructions and...",
    "detection_method": "ml_classifier",
    "confidence": 0.97,
    "action_taken": "blocked",
    "ip_address": "192.168.1.100"
  }
}

{
  "event_type": "security.pii_detected",
  "event_id": "evt_efg789hij012",
  "timestamp": "2025-11-27T12:05:00Z",
  "source": "agentic-security.v1",
  "severity": "medium",
  "data": {
    "agent_id": "agt_123",
    "pii_entities": ["NAME", "INN"],
    "masked": true,
    "llm_provider": "gigachat"
  }
}
```

---

## PART 4: DATABASE SCHEMAS

### 4.1 AgentDB (PostgreSQL)

```sql
-- Agents table
CREATE TABLE agents (
  agent_id VARCHAR(32) PRIMARY KEY,
  name VARCHAR(255) NOT NULL,
  description TEXT,
  type VARCHAR(50) NOT NULL,
  config JSONB NOT NULL,
  security JSONB NOT NULL,
  status VARCHAR(20) NOT NULL DEFAULT 'created',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  created_by VARCHAR(32),
  metadata JSONB
);

CREATE INDEX idx_agents_status ON agents(status) WHERE status IN ('active', 'suspended');
CREATE INDEX idx_agents_type ON agents(type);
CREATE INDEX idx_agents_created_by ON agents(created_by);

-- Agent states table
CREATE TABLE agent_states (
  agent_id VARCHAR(32) NOT NULL REFERENCES agents(agent_id) ON DELETE CASCADE,
  version INTEGER NOT NULL,
  variables JSONB NOT NULL DEFAULT '{}',
  memory JSONB NOT NULL DEFAULT '{}',
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (agent_id, version)
);

CREATE INDEX idx_agent_states_updated_at ON agent_states(updated_at DESC);

-- Conversations table
CREATE TABLE conversations (
  conversation_id VARCHAR(32) PRIMARY KEY,
  agent_id VARCHAR(32) NOT NULL REFERENCES agents(agent_id) ON DELETE CASCADE,
  user_id VARCHAR(32),
  session_id VARCHAR(32),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  metadata JSONB
);

CREATE INDEX idx_conversations_agent_id ON conversations(agent_id, created_at DESC);
CREATE INDEX idx_conversations_user_id ON conversations(user_id, created_at DESC);

-- Messages table
CREATE TABLE messages (
  message_id VARCHAR(32) PRIMARY KEY,
  conversation_id VARCHAR(32) NOT NULL REFERENCES conversations(conversation_id) ON DELETE CASCADE,
  role VARCHAR(20) NOT NULL,
  content TEXT NOT NULL,
  metadata JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_messages_conversation_id ON messages(conversation_id, created_at);

-- Executions table (for metrics)
CREATE TABLE executions (
  execution_id VARCHAR(32) PRIMARY KEY,
  agent_id VARCHAR(32) NOT NULL REFERENCES agents(agent_id) ON DELETE CASCADE,
  input TEXT NOT NULL,
  output TEXT,
  status VARCHAR(20) NOT NULL,
  tokens_used INTEGER,
  cost_usd DECIMAL(10, 6),
  latency_ms INTEGER,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  completed_at TIMESTAMPTZ,
  error TEXT
);

CREATE INDEX idx_executions_agent_id ON executions(agent_id, created_at DESC);
CREATE INDEX idx_executions_status ON executions(status);
```

### 4.2 RuVector Collection Schema

```json
{
  "collection_name": "agent-memory",
  "dimension": 768,
  "index_type": "HNSW",
  "index_params": {
    "M": 32,
    "efConstruction": 200
  },
  "similarity_metric": "cosine",
  "schema": {
    "id": {
      "type": "string",
      "indexed": true
    },
    "vector": {
      "type": "float_vector",
      "dimension": 768
    },
    "text": {
      "type": "string",
      "indexed": false
    },
    "metadata": {
      "agent_id": {
        "type": "string",
        "indexed": true
      },
      "user_id": {
        "type": "string",
        "indexed": true
      },
      "type": {
        "type": "string",
        "indexed": true
      },
      "timestamp": {
        "type": "int64",
        "indexed": true
      },
      "confidence": {
        "type": "float",
        "indexed": false
      }
    }
  },
  "created_at": "2025-11-27T10:00:00Z"
}
```

---

## PART 5: AUTHENTICATION & AUTHORIZATION

### 5.1 API Key Authentication

```bash
# Header-based
curl -H "Authorization: Bearer sk_live_abc123def456..." \
  https://api.cloud.ru/v1/agents

# Query parameter (not recommended for production)
curl "https://api.cloud.ru/v1/agents?api_key=sk_live_abc123def456..."
```

### 5.2 OAuth 2.0 / OIDC

```typescript
// Authorization Code Flow
const authUrl = 'https://auth.cloud.ru/oauth/authorize?' +
  'client_id=app_123&' +
  'redirect_uri=https://myapp.com/callback&' +
  'response_type=code&' +
  'scope=agents:read agents:write workflows:execute&' +
  'state=random_state_123';

// Exchange code for token
const tokenResponse = await fetch('https://auth.cloud.ru/oauth/token', {
  method: 'POST',
  headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  body: new URLSearchParams({
    grant_type: 'authorization_code',
    code: authCode,
    client_id: 'app_123',
    client_secret: 'secret_456',
    redirect_uri: 'https://myapp.com/callback'
  })
});

const { access_token, refresh_token, expires_in } = await tokenResponse.json();

// Use access token
fetch('https://api.cloud.ru/v1/agents', {
  headers: { 'Authorization': `Bearer ${access_token}` }
});
```

### 5.3 RBAC Policies (Open Policy Agent)

```rego
package cloud_ru.authz

# Allow if user has 'admin' role
allow {
  input.user.roles[_] == "admin"
}

# Allow agent creation if user has 'agent:create' permission
allow {
  input.action == "agent:create"
  input.user.permissions[_] == "agent:create"
}

# Allow agent execution only for owned agents
allow {
  input.action == "agent:execute"
  input.resource.agent_id
  data.agents[input.resource.agent_id].owner == input.user.id
}

# Allow workflow execution with approval for high-cost workflows
allow {
  input.action == "workflow:execute"
  input.resource.estimated_cost_usd < 10
}

allow {
  input.action == "workflow:execute"
  input.resource.estimated_cost_usd >= 10
  input.approval.approved == true
  input.approval.approver_role == "manager"
}
```

---

## PART 6: ERROR HANDLING

### 6.1 Standard Error Response

```json
{
  "error": {
    "code": "INVALID_INPUT",
    "message": "Invalid agent configuration: missing required field 'llm.model'",
    "details": {
      "field": "config.llm.model",
      "expected": "string",
      "received": "null"
    },
    "request_id": "req_abc123def456",
    "timestamp": "2025-11-27T10:30:00Z",
    "documentation_url": "https://docs.cloud.ru/errors/INVALID_INPUT"
  }
}
```

### 6.2 Error Codes

| HTTP Status | Error Code | Description |
|-------------|------------|-------------|
| 400 | `INVALID_INPUT` | Invalid request parameters |
| 401 | `UNAUTHORIZED` | Missing or invalid authentication |
| 403 | `FORBIDDEN` | Insufficient permissions |
| 404 | `NOT_FOUND` | Resource not found |
| 409 | `CONFLICT` | Resource conflict (e.g., duplicate ID) |
| 422 | `UNPROCESSABLE_ENTITY` | Validation failed |
| 429 | `RATE_LIMIT_EXCEEDED` | Too many requests |
| 500 | `INTERNAL_ERROR` | Internal server error |
| 503 | `SERVICE_UNAVAILABLE` | Service temporarily unavailable |

### 6.3 Rate Limiting

```http
HTTP/1.1 429 Too Many Requests
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1732704000
Retry-After: 60

{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "API rate limit exceeded. Limit: 1000 requests per hour.",
    "retry_after_seconds": 60
  }
}
```

---

**Документ подготовлен:** 27 ноября 2025
**Версия:** 1.0
**Статус:** PRODUCTION-READY
