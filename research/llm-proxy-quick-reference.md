# LLM Proxy Quick Reference Card

**Enterprise-Grade LLM Proxy для Cloud.ru** | Версия: 1.0 | Дата: 27.11.2025

---

## 🎯 Target Metrics (Production)

| Category | Metric | Target | Status |
|----------|--------|--------|--------|
| **Availability** | Uptime SLA | 99.95% | 4.38h downtime/year |
| **Performance** | P95 Latency | <100ms | Best-in-class |
| **Performance** | Throughput | >1000 RPS | Load tested |
| **Performance** | GPU Utilization | >85% | Cost optimized |
| **Security** | Auth Success | >99% | Enterprise-grade |
| **Security** | Security Incidents | 0 | Zero tolerance |
| **Reliability** | MTTR | <15min | Auto-recovery |
| **Reliability** | MTBF | >30 days | Fault tolerant |
| **Compliance** | Audit Coverage | 100% | SOC 2 ready |
| **Cost** | Savings | 50-60% | vs baseline |

---

## 🛡️ Security Stack

```
┌─────────────────────────────────────────────────────────────┐
│                    User Request                              │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  Layer 1: WAF + TLS 1.3 + Rate Limiting                     │
│  - AWS WAF / Cloudflare                                     │
│  - 60-300 req/min (users), 1000+ (admin)                    │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  Layer 2: Authentication & Authorization                    │
│  - OAuth 2.0 / OpenID Connect                               │
│  - MFA mandatory                                            │
│  - RBAC (user/developer/admin)                              │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  Layer 3: Input Validation & Prompt Injection Defense       │
│  - Pattern matching (blocked prompts)                       │
│  - Length validation (max 4096 tokens)                      │
│  - Encoding checks                                          │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  Layer 4: AI Gateway + Enterprise Guardrails                │
│  - Azure AI Content Safety / AWS Bedrock                    │
│  - Context isolation (Spotlighting)                         │
│  - Policy enforcement                                       │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  Layer 5: LLM Gateway (Multi-Provider Failover)             │
│  - LiteLLM / OpenRouter                                     │
│  - Circuit breaker pattern                                  │
│  - OpenAI → Anthropic → Azure (automatic)                   │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  Layer 6: Content Filtering & Moderation                    │
│  - Rule-based → ML → LLM (cascaded)                         │
│  - PII detection & redaction                                │
│  - Risk assessment (critical/high/medium/low)               │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  Layer 7: Output Validation                                 │
│  - Format validation                                        │
│  - Toxicity check                                           │
│  - Data leakage prevention                                  │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  Layer 8: Audit Logging & Monitoring                        │
│  - Tamper-proof logs (CloudWatch/S3 Object Lock)            │
│  - SIEM integration (Splunk/Elastic)                        │
│  - Real-time alerting (PagerDuty)                           │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
                    Response to User
```

---

## ⚡ Performance Stack

```
┌─────────────────────────────────────────────────────────────┐
│  Performance Layer 1: Connection Pooling                    │
│  ┌──────────────────┬─────────────────────────────────────┐ │
│  │ PostgreSQL       │ Pool size: 10-20                    │ │
│  │                  │ Batch writes: 60s                   │ │
│  ├──────────────────┼─────────────────────────────────────┤ │
│  │ Redis            │ Connection pooling: 100 max         │ │
│  │                  │ Keepalive: 60s                      │ │
│  ├──────────────────┼─────────────────────────────────────┤ │
│  │ HTTP             │ HTTP/2 multiplexing                 │ │
│  │                  │ TLS session cache: 1000 sessions    │ │
│  └──────────────────┴─────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  Performance Layer 2: Semantic Caching                      │
│  - Redis + RediSearch vector DB                             │
│  - Similarity threshold: 0.95                               │
│  - Cache hit rate: >60%                                     │
│  - Savings: 40-70% LLM API calls                            │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  Performance Layer 3: Request Batching                      │
│  - Batch size: 32-64 requests                               │
│  - Batch timeout: 100ms                                     │
│  - Async/await throughout                                   │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  Performance Layer 4: Continuous Batching (vLLM)            │
│  - Iteration-level scheduling                               │
│  - Paged attention                                          │
│  - GPU utilization: 85-95%                                  │
│  - Throughput: 9x improvement                               │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  Performance Layer 5: SSJF Scheduling                       │
│  - Proxy model predicts sequence length                     │
│  - Shortest-job-first scheduling                            │
│  - Throughput: +2.2x to +3.6x                               │
└─────────────────────────────────────────────────────────────┘
```

**Performance Gains:**
- Continuous Batching: **450 tokens/sec** (9x from 50)
- Latency: **0.8s** (3.1x from 2.5s)
- GPU Cost: **-40%**
- Connection Pooling: **-60-80%** connection time
- Semantic Caching: **-40-70%** API calls

---

## 🌐 High Availability Architecture

```
                        Route 53 (Latency-based Routing)
                                    │
            ┌───────────────────────┼───────────────────────┐
            │                       │                       │
            ▼                       ▼                       ▼
    ┌──────────────┐        ┌──────────────┐      ┌──────────────┐
    │  EU-Central  │        │   EU-West    │      │   US-East    │
    │   (Primary)  │        │ (Secondary)  │      │     (DR)     │
    │   70% load   │        │   30% load   │      │   Standby    │
    └──────────────┘        └──────────────┘      └──────────────┘
            │                       │                       │
    ┌───────┴───────┐       ┌───────┴───────┐       ┌───────┴───────┐
    │ AZ-a  AZ-b  AZ-c│      │ AZ-a  AZ-b    │       │ AZ-a  AZ-b    │
    └─────────────────┘      └─────────────────┘      └───────────────┘
            │                       │                       │
            ▼                       ▼                       ▼
    ┌──────────────┐        ┌──────────────┐      ┌──────────────┐
    │ Kubernetes   │        │ Kubernetes   │      │ Kubernetes   │
    │ 6+ Pods      │        │ 4+ Pods      │      │ 2+ Pods      │
    │ HPA: 6-50    │        │ HPA: 4-30    │      │ HPA: 2-20    │
    └──────────────┘        └──────────────┘      └──────────────┘
            │                       │                       │
            ▼                       ▼                       ▼
    ┌──────────────┐        ┌──────────────┐      ┌──────────────┐
    │ PostgreSQL   │◄───────►│ PostgreSQL   │◄─────►│ PostgreSQL   │
    │ Patroni HA   │  Async  │ Patroni HA   │ Async │ Patroni HA   │
    │ 3 replicas   │  Repl.  │ 2 replicas   │ Repl. │ 2 replicas   │
    └──────────────┘         └──────────────┘       └──────────────┘
            │                       │                       │
            ▼                       ▼                       ▼
    ┌──────────────┐        ┌──────────────┐      ┌──────────────┐
    │ Redis        │◄───────►│ Redis        │◄─────►│ Redis        │
    │ Sentinel     │         │ Sentinel     │       │ Sentinel     │
    │ 3 nodes      │         │ 3 nodes      │       │ 2 nodes      │
    └──────────────┘         └──────────────┘       └──────────────┘
            │                       │                       │
            └───────────────────────┼───────────────────────┘
                                    ▼
                        Multi-Provider LLM Gateway
                    ┌──────────┬──────────┬──────────┐
                    │ OpenAI   │Anthropic │  Azure   │
                    │Priority 1│Priority 2│Priority 3│
                    └──────────┴──────────┴──────────┘
```

**HA Guarantees:**
- SLA: **99.95%** (4.38h/year downtime)
- MTTR: **<15 minutes**
- MTBF: **>30 days**
- RTO: **15 minutes**
- RPO: **5 minutes**

---

## 📋 5-Phase Implementation Roadmap

| Phase | Timeline | Focus | Success Criteria |
|-------|----------|-------|------------------|
| **1. Security Foundation** | Month 1-2 | OAuth 2.0, MFA, RBAC, encryption, audit logs | Secure for pilot customers |
| **2. Advanced Security** | Month 2-3 | Guardrails, prompt injection defense, SIEM | Production-ready security |
| **3. Performance** | Month 3-4 | Continuous batching, caching, monitoring | P95 < 100ms, 1K+ RPS |
| **4. High Availability** | Month 4-5 | Multi-region, failover, PostgreSQL HA | 99.95% availability |
| **5. Compliance** | Month 5-6 | SOC 2, GDPR, HIPAA, pen testing | Certified & compliant |

**Total Timeline:** 6 months to production-ready enterprise LLM Proxy

---

## 🔧 Technology Stack (Recommended)

| Component | Primary | Alternative | Notes |
|-----------|---------|-------------|-------|
| **LLM Gateway** | LiteLLM | OpenRouter, Kong AI | Multi-provider support |
| **Inference** | vLLM | TensorRT-LLM | Continuous batching |
| **Authentication** | Azure AD | Keycloak | OAuth 2.0 + MFA |
| **Database** | PostgreSQL 15+ | - | With Patroni HA |
| **Cache** | Redis | KeyDB | With Sentinel |
| **Monitoring** | Prometheus | Datadog | + Grafana dashboards |
| **Logging** | ELK Stack | Splunk | Centralized logging |
| **Security** | Azure AI Safety | AWS Bedrock | Enterprise guardrails |
| **Orchestration** | Kubernetes | - | EKS/AKS/GKE |
| **IaC** | Terraform | Pulumi | Infrastructure as Code |
| **CI/CD** | GitLab CI | GitHub Actions | Automated deployments |

---

## 💰 Cost Optimization Formula

```
Total Savings = Caching + Batching + Routing + Deduplication + Scaling

Semantic Caching:      40-70% ─┐
Continuous Batching:   40%     │
Intelligent Routing:   30%     ├─→ Total: 50-60% reduction
Request Deduplication: 10-20%  │
Auto-scaling:          20-30%  ┘
```

**Expected Monthly Savings:**
- Baseline cost: $50,000/month
- After optimization: $20,000-25,000/month
- **Savings: $25,000-30,000/month**

---

## 🔒 Compliance Matrix

| Requirement | GDPR | HIPAA | SOC 2 | Status |
|-------------|------|-------|-------|--------|
| **Data Encryption** | ✓ | ✓ | ✓ | AES-256, TLS 1.3 |
| **Access Controls** | ✓ | ✓ | ✓ | OAuth 2.0 + MFA + RBAC |
| **Audit Logging** | ✓ | ✓ | ✓ | Tamper-proof, 6-year retention |
| **Data Minimization** | ✓ | - | ✓ | Only necessary data |
| **Right to Erasure** | ✓ | - | - | API endpoint provided |
| **Right to Access** | ✓ | - | - | Data export API |
| **BAA Required** | - | ✓ | - | OpenAI/Anthropic signed |
| **Penetration Testing** | - | - | ✓ | Annual requirement |
| **Incident Response** | ✓ | ✓ | ✓ | 24/7 monitoring |

**Retention Policies:**
- GDPR: **30 days** default (with consent: custom)
- HIPAA: **6 years** for audit logs & PHI
- SOC 2: **1-3 years** for system/security logs

---

## 🚨 Critical Alerts Configuration

| Alert | Condition | Severity | Action |
|-------|-----------|----------|--------|
| **High Error Rate** | >1% errors for 5min | CRITICAL | PagerDuty escalation |
| **High Latency** | P95 >150ms for 5min | WARNING | Auto-scale trigger |
| **Provider Down** | Health check fails 1min | CRITICAL | Failover + alert |
| **Low Availability** | <99.9% over 10min | CRITICAL | Incident declared |
| **Security Incident** | Malicious pattern detected | CRITICAL | Block + SIEM alert |
| **Replication Lag** | >200MB lag for 5min | WARNING | DBA notification |
| **Cost Spike** | >150% of baseline | WARNING | Finance alert |
| **Compliance Violation** | Policy breach detected | CRITICAL | Security team alert |

---

## 📊 Monitoring Dashboard (Prometheus + Grafana)

```yaml
Key Metrics to Display:

Performance Panel:
  - P50/P95/P99 Latency (target: 50/100/200ms)
  - Requests per Second (target: >1000)
  - Tokens per Second (track: trending up)
  - Cache Hit Rate (target: >60%)
  - GPU Utilization (target: >85%)

Reliability Panel:
  - Availability % (target: >99.95%)
  - Error Rate % (target: <0.1%)
  - Provider Health Status (3/3 green)
  - Active Connections (track: stable)
  - Circuit Breaker Status (closed)

Security Panel:
  - Auth Success Rate (target: >99%)
  - Blocked Malicious Requests (track: daily)
  - Failed Login Attempts (alert: >10/min)
  - Rate Limit Violations (track: by user)
  - PII Detections (track: redacted count)

Infrastructure Panel:
  - Pod Count by Zone (balanced)
  - Database Replication Lag (target: <100MB)
  - Redis Memory Usage (alert: >80%)
  - CPU/Memory per Pod (alert: >80%)
  - Network Throughput (track: trending)
```

---

## 🎯 First Week Quick Wins

**Security (Day 1-2):**
1. Enable TLS 1.3 everywhere → **1 hour**
2. Deploy rate limiting → **2 hours**
3. Configure API key rotation → **2 hours**
4. Enable basic audit logging → **2 hours**

**Performance (Day 3-4):**
1. Enable database connection pooling → **2 hours**
2. Configure semantic caching → **4 hours**
3. Deploy Prometheus monitoring → **4 hours**
4. Set up Grafana dashboards → **2 hours**

**Total:** 1 week for foundational improvements

---

## 📞 Emergency Procedures

### Provider Outage
```bash
# Automatic failover via circuit breaker
# Manual intervention if needed:
kubectl scale deployment llm-proxy --replicas=10  # Scale up
kubectl rollout restart deployment llm-proxy      # Force refresh
# Check provider status:
curl https://status.openai.com/api/v2/status.json
```

### High Latency Spike
```bash
# Check cache hit rate
redis-cli INFO stats | grep keyspace_hits
# Check batch sizes
kubectl logs -l app=llm-proxy | grep "batch_size"
# Scale horizontally
kubectl patch hpa llm-proxy --patch '{"spec":{"maxReplicas":75}}'
```

### Security Incident
```bash
# Block suspicious IP
kubectl exec -it llm-proxy-xxx -- redis-cli SADD blocked_ips "1.2.3.4"
# Check audit logs
kubectl exec -it postgres-0 -- psql -c "SELECT * FROM audit_logs WHERE severity='CRITICAL' ORDER BY timestamp DESC LIMIT 100"
# Alert security team
curl -X POST https://hooks.slack.com/services/XXX -d '{"text":"Security incident detected"}'
```

---

## 📚 Key Documentation Links

### Internal Docs
- [Full Research (60KB)](/research/llm-proxy-security-performance-best-practices-2025.md)
- [Production Checklist (12KB)](/research/llm-proxy-production-checklist.md)

### External Resources
- [LiteLLM Production Docs](https://docs.litellm.ai/docs/proxy/prod)
- [vLLM Documentation](https://docs.vllm.ai/)
- [OWASP LLM Top 10](https://genai.owasp.org/)
- [Microsoft LLM Security](https://learn.microsoft.com/en-us/ai/playbook/technology-guidance/generative-ai/mlops-in-openai/security/security-plan-llm-application)
- [AWS Well-Architected (AI/ML)](https://docs.aws.amazon.com/wellarchitected/latest/machine-learning-lens/welcome.html)

---

**Version:** 1.0
**Last Updated:** 27 ноября 2025
**Owner:** Cloud.ru AI Platform Team
**Status:** Production Ready
