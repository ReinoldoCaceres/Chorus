# 🧭 Technical Architecture Document — *Chorus Live‑Chat Platform*

**Version 0.9 ( *****Draft for Executive Review***** )**\
Author : Principal Architect — Reinoldo/ChatGPT\
Date : 30 Jul 2025

---

## 1 · Executive Summary

Chorus is an omnichannel live‑chat extension for the Enkisys (Orchestra) agent platform. It provides real‑time human hand‑off, Web‑socket messaging, contextual summaries, and analytics while honouring Enkisys’ multi‑tenant, RBAC and cost‑tracking model.\
This document defines the *full scope* required to build, deploy and operate Chorus in production with no open questions, pending only numerical parameter confirmation (⚠️ highlighted as **TODO**).

---

## 2 · Business Context & Objectives

| Objective                        | KPI / Target                                   |
| -------------------------------- | ---------------------------------------------- |
| Seamless bot‑to‑human escalation | Escalation success rate ≥ 95 %                 |
| Reduce average handle time (AHT) | AHT ≤  **TODO X** s (P90)                      |
| Improve CSAT                     | CSAT ≥ 4.5/5 average                           |
| Support 5 primary channels       | SMS, WhatsApp, FB Messenger, E‑mail, WebWidget |
| New revenue stream               | +15 % ARR via Live‑Chat add‑on                 |

---

## 3 · Architectural Vision (C4 — Context)

```
[ Customer ] ⇄  (Channel Gateway)  ⇄  ALB  ⇄  Chorus Edge   ⇄  Enkisys Core
                               ⇅             ⇅
                        Redis Pub/Sub   PostgreSQL  ←→  ChromaDB
```

- Full C4 diagrams supplied in Appendix A.

---

## 4 · High‑Level Components

| #  | Component               | Purpose                                        | Tech             | Owner        |
| -- | ----------------------- | ---------------------------------------------- | ---------------- | ------------ |
| C1 | **WebSocket Gateway**   | Upgrade HTTP to WS, auth, multiplex tenants    | Go + Gorilla WS  | Platform     |
| C2 | **Chat‑Service API**    | CRUD conversations, persistence, typing events | Python FastAPI   | AI Team      |
| C3 | **Presence Service**    | Track online/offline, TTL heartbeats in Redis  | Go               | SRE          |
| C4 | **Summary Engine**      | LLM‑powered contextual summaries               | Python LangChain | ML Team      |
| C5 | **Notification Worker** | Push, e‑mail & SMS alerts                      | Node.js (BullMQ) | Integrations |
| C6 | **Admin UI**            | Agents’ console (React)                        | React + Vite     | Front‑end    |

---

## 5 · Deployment Topology

- \*\*Cloud \*\*: AWS us‑east‑2
- \*\*Runtime \*\*: Docker compose → ECS Fargate
- \*\*Network \*\*: VPC /24, 2 AZ, public+private subnets
- \*\*Ingress \*\*: Existing ALB, WS‐enabled target group
- \*\*Secrets \*\*: AWS SSM Parameter Store, 6 h rotation
- \*\*CDN \*\*: CloudFront for static webchat bundle.

---

## 6 · Data Model Extensions

### `messages`

```sql
ALTER TABLE messages
  ADD COLUMN delivered_at TIMESTAMP NULL,
  ADD COLUMN read_at       TIMESTAMP NULL,
  ADD COLUMN message_type  VARCHAR(50) DEFAULT 'text';
```

### `live_chat_sessions`

```sql
CREATE TABLE live_chat_sessions (
  id UUID PRIMARY KEY,
  conversation_id UUID REFERENCES conversations(id),
  tenant_id UUID NOT NULL,
  user_socket_id VARCHAR(255),
  agent_socket_id VARCHAR(255),
  status VARCHAR(20) DEFAULT 'active',
  started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  ended_at TIMESTAMP
);
```

---

## 7 · Interfaces & Contracts

### 7.1 · WebSocket Protocol (`/ws/v1/conversations/{conversationId}`)

| Event      | Payload               | Ack                      |
| ---------- | --------------------- | ------------------------ |
| `auth`     | JWT                   | required                 |
| `message`  | `{id, role, content}` | server emits `delivered` |
| `typing`   | `{role, state}`       | fire‑and‑forget          |
| `presence` | `{userId, status}`    | broadcast                |

### 7.2 · REST Extensions (Chat‑Service)

- `POST /livechat/escalate`
- `GET  /livechat/summary/{conversationId}`
- `POST /livechat/ack/{messageId}`

All endpoints inherit JWT‑tenant middleware from `ms-auth`.

---

## 8 · Non‑Functional Requirements

| Category          | Requirement                                                                                                |
| ----------------- | ---------------------------------------------------------------------------------------------------------- |
| **Scalability**   | Handle **TODO 1** concurrent WS (global) and **TODO 2** per tenant. Auto‑scale Fargate tasks (CPU > 70 %). |
| **Performance**   | P95 message RTT < **TODO 3** ms; summary generation ≤ 2 s.                                                 |
| **Availability**  | 99.9 % monthly; multi‑AZ; ALB health checks 30 s.                                                          |
| **Security**      | TLS 1.2+, oauth2 scopes, WAF rate‑limit 10 k req/5 min.                                                    |
| **Compliance**    | GDPR & PIPEDA; configurable retention (**TODO 4** days default).                                           |
| **Observability** | Logs → CloudWatch; traces → X‑Ray; Prometheus + Grafana dashboards.                                        |

---

## 9 · Detailed Component Design

### C1 · WebSocket Gateway

- **Libraries** : Gorilla‐websocket, jwt‑go.
- **Auth flow** : JWT in `Sec-WebSocket-Protocol` header → tenant claim cached 5 min.
- **Back‑pressure** : write timeout 5 s; drop connection after 3 × retries.

### C2 · Chat‑Service API

- **Framework** : FastAPI + Uvicorn.
- **DB access** : SQLModel; connection pool 30.
- **Endpoints** : synchronous REST + gRPC for internal calls.

### C4 · Summary Engine

- Invoked via Celery worker.
- Model selection based on subscription tier (see `ModelAccess`).
- Caches summary in `conversations.metadata.summary`.

Full component specs in Appendix B.

---

## 10 · Security Architecture

- **STRIDE analysis** in Appendix C.
- **Threat mitigations** : 
  - Replay → WS signed nonce.
  - Injection → parameterised queries + ORM.
  - DDoS → AWS WAF & Shield.
- **Pentest** : external audit **T‑30 days** before GA.

---

## 11 · Observability & SRE

- **Metrics**: `ws_connections`, `msg_rtt_ms`, `escalations_total`, `summary_latency_ms`.
- **Alerts**:
  - Sev1 : P95 RTT > **TODO 5** ms 10 min.
  - Sev2 : WS disconnect error rate > 2 %.
- **Runbooks** stored in `on‑call/chorus.md`.

---

## 12 · CI/CD Pipeline

```
GitHub → Actions → Docker build → ECR → Fargate deploy (blue/green) → Smoke tests
```

- Feature flags via Unleash.
- k6 performance gate (≥ **TODO 6** RPS sustainable).

---

## 13 · Disaster Recovery & Backups

| Layer      | RPO          | RTO    | Strategy                 |
| ---------- | ------------ | ------ | ------------------------ |
| PostgreSQL | **TODO** min | 15 min | RDS snapshots + PITR     |
| ChromaDB   | 30 min       | 30 min | EBS snapshot             |
| Redis      | 5 min        | 10 min | Replication group        |
| S3 uploads | n/a          | n/a    | Cross‑region replication |

Multi‑region active‑passive cut‑over script in Appendix D.

---

## 14 · Cost Estimate (monthly)

| Item                          | Unit | Qty        | Cost    | Sub‑total     |
| ----------------------------- | ---- | ---------- | ------- | ------------- |
| Fargate Task (0.5 vCPU/1 GB)  | hr   | **TODO 7** | \$0.041 | **TODO**      |
| Redis (ElastiCache)           | node | 1          | \$27    | \$27          |
| RDS (PostgreSQL db.t3.medium) | hr   | 730        | \$0.068 | \$50          |
| ALB & WAF                     |      |            |         | \$35          |
| **Estimated total**           |      |            |         | **< \$ TODO** |

---

## 15 · Testing & QA Strategy

- **Unit** : pytest, go‑test, jest. Coverage ≥ 80 %.
- **Contract** : Pact between WS Gateway & Chat‑Service.
- **Load** : k6 script `load/ws_10k.js` achieving P95 < **TODO** ms.
- **Chaos** : Gremlin scenario “Redis down 5 min”.

---

## 16 · Roll‑‑Out Plan

1. Dev → Staging WS (internal agents only).
2. Beta tenants opt‑in (flag `enable_livechat`).
3. GA once SLA met for 30 consecutive days.

---

## 17 · RACI Matrix (excerpt)

| Task              | Product | Arch | Dev | QA | SRE |
| ----------------- | ------- | ---- | --- | -- | --- |
| WS Gateway design | C       | A    | R   | I  | I   |
| Summary engine    | I       | C    | A   | R  | I   |
| CI/CD pipeline    | I       | C    | R   | I  | A   |

Full matrix in Appendix E.

---

## 18 · Risks & Mitigations

| Risk                      | Impact | Likelihood | Mitigation                       |
| ------------------------- | ------ | ---------- | -------------------------------- |
| Redis single‑node failure | High   | Med        | Multi‑AZ cluster                 |
| Rapid traffic spike       | Med    | High       | Auto‑scale + queue back‑pressure |
| Abuse via free tier       | High   | Med        | Captcha & WAF rules              |

---

## 19 · Glossary

- **AHT** : Average Handle Time
- **WS** : WebSocket
- **SLA/SLO** : Service Level Agreement / Objective

---

## Appendices

- **A** : C4 diagrams (Context, Container, Component, Code)
- **B** : Detailed API specs (OpenAPI 3.1)
- **C** : STRIDE threat model worksheets
- **D** : DR fail‑over runbooks
- **E** : Comprehensive RACI

---

###
