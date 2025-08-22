# Architecture

```mermaid
flowchart LR
  subgraph Clients
    A[Apps/BI/ETL]
  end
  subgraph Proxy
    P[SQLumAI Proxy - TCP/TLS TDS]
    API[Rules API]
  end
  subgraph SQL[Microsoft SQL Server]
    XE[Extended Events: rpc_completed + sql_batch_completed]
  end
  subgraph Analysis
    R[Readers: ring/file] --> AGG[Aggregation & Profiles]
    AGG --> LLM[LLM Summaries]
    LLM --> FEED[Slack/Jira/Webhook]
  end

  A <--> P
  P <--> SQL
  XE --> R
  API --> P
```

Notes
- Real‑time decisions in the proxy are deterministic (rules engine). No LLM calls happen on the hot path.
- LLM processing is asynchronous: scheduler jobs read aggregated data and generate insights and proposed rules.
