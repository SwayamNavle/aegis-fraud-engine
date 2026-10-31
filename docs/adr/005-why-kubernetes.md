# ADR 005: Selection of Kubernetes for Container Orchestration & Dynamic Scaling

## Context & Problem Statement
Aegis comprises multiple heterogeneous services: high-throughput stateless REST/WebSocket APIs, Kafka consumer stream workers, stateful distributed brokers (Kafka KRaft), relational databases (PostgreSQL), and monitoring agents (Prometheus/Grafana). The production deployment architecture requires declarative configuration, automated health monitoring with self-healing, zero-downtime rolling upgrades, and automatic horizontal scaling responsive to event spikes.

## Decision
We adopted **Kubernetes (K8s)** as the production container orchestration platform, supplemented with Docker Compose for single-command local development.

## Key Technical Rationale
1. **Horizontal Pod Autoscaling (HPA)**:
   Financial payment volume experiences sharp diurnal peaks (e.g. Black Friday, mid-day payroll runs). Kubernetes HPAs automatically scale scoring API and consumer worker pods between 3 and 10 replicas based on CPU utilization and custom Prometheus Kafka consumer lag metrics.
2. **Self-Healing Pod Lifecycle**:
   If an inference worker experiences an unhandled exception or memory leak, Kubernetes liveness probes (`/health`) automatically terminate and restart the container within seconds. Readiness probes ensure pods do not receive Kafka or API traffic until the in-memory XGBoost model has completed warm-up.
3. **Zero-Downtime Rolling Deployments**:
   When promoting new model versions or updating application code, Kubernetes performs rolling updates with configurable `maxSurge` and `maxUnavailable` parameters. New pods are validated against readiness probes before traffic is shifted away from previous pods.
4. **Declarative Service Discovery & Isolation**:
   Internal service communication is decoupled using Kubernetes Service resources (`aegis-api-service`, `aegis-kafka-service`, `aegis-postgres-service`), while sensitive credentials (database passwords, API signing keys) are secured via Kubernetes Secrets and injected as environment variables.
5. **Multi-Environment Manifest Parity**:
   The Kubernetes manifests defined in `kubernetes/` provide a standard baseline runnable across Minikube, Kind, AWS EKS, Google GKE, and Azure AKS with consistent resource limits (`limits.cpu: 1000m`, `limits.memory: 1Gi`).

## Tradeoffs & Considered Alternatives
- **Docker Compose Only**: Ideal for single-node developer workstations and small demos, but lacks automated node failure recovery, auto-scaling, distributed secret management, and multi-node workload scheduling.
- **Serverless (AWS Lambda / Google Cloud Functions)**: High elasticity, but incurs significant cold-start penalties (500ms - 2s), lacks persistent in-memory model caches, and increases cost at sustained thousands of events per second compared to provisioned K8s node pools.

