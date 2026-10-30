# Aegis Deployment & Infrastructure Guide

## 1. Local Development (Zero Docker Dependencies)

Aegis can be executed locally without Docker or Kubernetes using Python 3.11+ and its built-in SQLite async fallback.

### Prerequisites:
- Python 3.11, 3.12, or 3.13
- macOS, Linux, or WSL2

### Steps:
```bash
# 1. Setup virtualenv and install pinned requirements
make install

# 2. Run chronological model training pipeline
make train

# 3. Launch the API and Aegis Command Center
make run
```

Access the application:
- **Command Center UI**: `http://localhost:8000`
- **Swagger Interactive API**: `http://localhost:8000/docs`
- **Prometheus Scrape Endpoint**: `http://localhost:8000/metrics`
- **Live Transaction WebSocket**: `ws://localhost:8000/ws/transactions`

---

## 2. Docker Compose Deployment (10 Services)

For containerized integration testing, Aegis provides a multi-container `docker-compose.yml` deploying the complete distributed stack.

### Architecture Topology:
- **`kafka`**: Apache Kafka KRaft broker on port `9092` (no ZooKeeper required).
- **`postgres`**: Relational store on port `5432` with automated `init.sql` schema migration.
- **`redis`**: Hot feature cache and idempotency lock store on port `6379`.
- **`scoring`**: XGBoost microservice on port `8001`.
- **`api`**: FastAPI gateway on port `8000`.
- **`spark`**: PySpark Structured Streaming worker.
- **`producer`**: High-velocity synthetic transaction generator.
- **`frontend`**: React Nginx production container on port `3000`.
- **`prometheus`**: Scrapes metrics from `api` and `scoring` on port `9090`.
- **`grafana`**: Pre-configured dashboards on port `3001` (`admin`/`aegis`).

### Launching the Stack:
```bash
# Build and start all services in the background
make docker-up

# Inspect running container logs
docker compose logs -f api scoring spark

# Teardown containers and remove volumes
make docker-down
```

---

## 3. Kubernetes Production Architecture (`k8s/`)

Aegis provides production-ready Kubernetes manifests designed for deployment on EKS, GKE, AKS, or local Minikube clusters.

```
k8s/
├── namespace.yaml           # Dedicated 'aegis' namespace
├── postgres/                # StatefulSet + PVC + Secret + Service
├── kafka/                   # KRaft Kafka StatefulSet + Headless Service
├── scoring/                 # Deployment + Service + HorizontalPodAutoscaler (HPA)
├── api/                     # Deployment + ClusterIP Service
├── spark/                   # PySpark Streaming Deployment + Checkpoint PVC
├── frontend/                # Nginx Deployment + Service
├── prometheus/              # ConfigMap + Deployment + Service
├── grafana/                 # ConfigMap + Deployment + Service
└── ingress.yaml             # NGINX Ingress Controller routing rules
```

### 3.1. Autoscaling with HorizontalPodAutoscaler (HPA)
The scoring microservice is CPU-bound during peak fraud spikes. Aegis configures an HPA to scale pods dynamically between 2 and 10 replicas:

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: aegis-scoring-hpa
  namespace: aegis
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: aegis-scoring
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

### 3.2. Deploying to Kubernetes:
```bash
make k8s-deploy
```

Verify deployment status:
```bash
kubectl get pods -n aegis
kubectl get hpa -n aegis
kubectl get ingress -n aegis
```
