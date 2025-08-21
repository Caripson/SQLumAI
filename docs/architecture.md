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
