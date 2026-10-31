# Kubernetes Orchestration Architecture

This document details the production Kubernetes topology, autoscaling configurations, services, and ingress routing for Aegis.

```mermaid
flowchart TD
    subgraph INGRESS["External Traffic Ingress"]
        LB["Load Balancer / Ingress Controller"]
    end

    subgraph NAMESPACE["Kubernetes Namespace: aegis"]
        subgraph API_DEPLOYMENT["Deployment: aegis-api (3 to 10 Replicas)"]
            POD1["aegis-api-pod-1"]
            POD2["aegis-api-pod-2"]
            POD3["aegis-api-pod-3"]
            HPA["Horizontal Pod Autoscaler (Target: 70% CPU / Lag > 500)"]
        end

        subgraph STREAMING_WORKERS["Deployment: aegis-consumers (3 Replicas)"]
            CW1["aegis-consumer-pod-1"]
            CW2["aegis-consumer-pod-2"]
            CW3["aegis-consumer-pod-3"]
        end

        subgraph STATEFUL_INFRA["Stateful Infrastructure (StatefulSets / PVCs)"]
            KAFKA["Kafka Cluster (KRaft StatefulSet - 3 Nodes)"]
            POSTGRES["PostgreSQL 16 (StatefulSet with PV / PVC)"]
            REDIS["Redis Hot Feature Cache (StatefulSet)"]
        end

        subgraph OBSERVABILITY["Monitoring Stack"]
            PROM["Prometheus Server Pod"]
            GRAF["Grafana Dashboard Pod"]
        end
    end

    LB -->|"HTTP / WebSocket Traffic"| POD1
    LB -->|"HTTP / WebSocket Traffic"| POD2
    LB -->|"HTTP / WebSocket Traffic"| POD3
    
    HPA -.->|"Scale Out Replicas"| API_DEPLOYMENT

    POD1 <-->|"Publish Events"| KAFKA
    POD2 <-->|"Publish Events"| KAFKA
    POD3 <-->|"Publish Events"| KAFKA

    KAFKA -->|"Assigned Partitions"| CW1
    KAFKA -->|"Assigned Partitions"| CW2
    KAFKA -->|"Assigned Partitions"| CW3

    CW1 <-->|"Online Features"| REDIS
    CW2 <-->|"Online Features"| REDIS
    CW3 <-->|"Online Features"| REDIS

    CW1 -->|"Persist Predictions"| POSTGRES
    CW2 -->|"Persist Predictions"| POSTGRES
    CW3 -->|"Persist Predictions"| POSTGRES

    PROM -.->|"Scrape /metrics"| API_DEPLOYMENT
    PROM -.->|"Scrape /metrics"| KAFKA
    GRAF -->|"Query"| PROM
```

## Pod Resource Specifications
```yaml
resources:
  requests:
    cpu: "250m"
    memory: "512Mi"
  limits:
    cpu: "1000m"
    memory: "1Gi"
livenessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 15
  periodSeconds: 10
readinessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 5
  periodSeconds: 5
```

