# MLOps PyTorch Pipeline

A production-style MLOps pipeline for CIFAR-10 image classification using PyTorch, Docker, and Kubernetes.

The project implements model training, checkpointing, containerized training and serving, persistent Kubernetes storage, health checks, a Kubernetes Service, and an HPA configuration.

## Assignment Mapping

| Coursework Area | Implementation                                                                                            |
| --------------- | --------------------------------------------------------------------------------------------------------- |
| Part A          | Public GitHub repository, `main`/`develop` workflow, feature branches, merged PRs, CI, `.gitignore`       |
| Part B          | ResNet-18 + CIFAR-10 + YAML configuration + JSONL metrics + checkpointing + early stopping + FastAPI      |
| Part C          | Multi-stage training image + CPU-only optimized dependencies + non-root serving image + HEALTHCHECK       |
| Part D          | Kubernetes Namespace + ConfigMap + PVCs + Training Job                                                    |
| Part E          | 2-replica Deployment + read-only checkpoint PVC + health probes + RollingUpdate + ClusterIP Service + HPA |
| Part F          | Docker and Kubernetes end-to-end serving validation                                                       |

## Architecture

```text
                              GitHub
                                 |
                         GitHub Actions CI
                                 |
                    +------------+------------+
                    |                         |
              Docker Images              Git Workflow
                    |                  main / develop / PRs
                    |
          Docker Desktop Kubernetes
                    |
        +-----------+-----------+
        |                       |
   Training Job           Model Serving
        |                       |
        |                  Deployment
        |                   2 replicas
        |                       |
        +---- Checkpoint PVC ---+
                    |
               ClusterIP
               Service :80
                    |
             port-forward
                    |
          /health   /predict
```

## Repository Structure

```text
mlops-pytorch-pipeline/
├── .github/workflows/ci.yml
├── configs/
│   └── training_config.yaml
├── docker/
│   ├── Dockerfile.train
│   └── Dockerfile.serve
├── k8s/
│   ├── namespace.yaml
│   ├── configmap.yaml
│   ├── pvc.yaml
│   ├── training-job.yaml
│   ├── serving-deployment.yaml
│   ├── serving-service.yaml
│   └── hpa.yaml
├── requirements/
│   ├── train.txt
│   ├── serve.txt
│   ├── test.txt
│   ├── docker-train.txt
│   └── docker-serve.txt
├── src/
│   ├── dataset.py
│   ├── model.py
│   ├── serve.py
│   └── train.py
├── tests/
├── docs/
├── data/
└── checkpoints/
```

## Mac Environment

Development was performed on macOS using:

* Python 3.11
* Docker Desktop
* Docker Desktop Kubernetes
* `kubectl`
* Git
* GitHub CLI (`gh`)

The local Python environment uses the native macOS PyTorch installation and Apple MPS when available.

## Local Python Setup

```bash
python3.11 -m venv .venv
source .venv/bin/activate

python -m pip install --upgrade pip
python -m pip install -r requirements/train.txt
python -m pip install -r requirements/test.txt
python -m pip install -r requirements/serve.txt
```

Run tests:

```bash
pytest -q
```

Expected result during validation:

```text
2 passed
```

Compile the source:

```bash
python -m compileall src tests
```

## Local Training Validation

The local development environment was validated using Apple MPS.

A one-epoch CIFAR-10 smoke run completed successfully with:

```text
device: mps
train_accuracy: 0.4402
val_accuracy: 0.5472
```

The resulting checkpoint was successfully saved and reloaded.

## Docker Training

The final Docker training image uses CPU-only PyTorch dependencies because the Docker/Kubernetes environment is CPU-based.

Build:

```bash
docker build -f docker/Dockerfile.train -t mlops-train:v2 .
```

Run:

```bash
mkdir -p data checkpoints

docker run --rm \
  -v "$(pwd)/data:/app/data" \
  -v "$(pwd)/checkpoints:/app/checkpoints" \
  mlops-train:v2
```

The validated 10-epoch Docker training run completed with:

```text
epoch 10
train_accuracy: 0.7811
val_accuracy:   0.7768
best_val_loss:  0.6464
```

The resulting checkpoint was:

```text
checkpoints/classifier_v1.pt
```

## Docker Image Optimization

The original Linux images used CUDA-enabled PyTorch wheels even though the runtime was CPU-only.

Dedicated CPU-only Docker dependencies were introduced.

Approximate image sizes observed during validation:

```text
Training image:
v1 ≈ 3.00 GB compressed
v2 ≈ 283 MB compressed

Serving image:
v1 ≈ 3.00 GB compressed
v2 ≈ 287 MB compressed
```

This represents approximately a 90% reduction in compressed image size.

The final Docker images use:

```text
torch==2.13.0+cpu
torchvision==0.28.0+cpu
```

## Docker Serving

Build:

```bash
docker build -f docker/Dockerfile.serve -t mlops-serve:v2 .
```

Run:

```bash
docker run --rm -p 8081:8080 \
  -v "$(pwd)/checkpoints:/app/checkpoints:ro" \
  mlops-serve:v2
```

The container:

* runs as the non-root `appuser`
* exposes container port 8080
* loads the checkpoint read-only
* includes a Docker HEALTHCHECK

Health:

```bash
curl -i http://localhost:8081/health
```

Expected:

```json
{"status":"ok"}
```

Prediction:

```bash
curl -X POST http://localhost:8081/predict \
  -F "image=@test_image.png"
```

The validated response returned a predicted class and 10 class probabilities.

## Kubernetes Environment

Docker Desktop Kubernetes was used as the local cluster.

Verify:

```bash
kubectl config current-context
kubectl get nodes
kubectl get pods -A
```

The validated cluster had one `Ready` control-plane node.

## Kubernetes Resources

Namespace:

```bash
kubectl apply -f k8s/namespace.yaml
```

ConfigMap:

```bash
kubectl apply -f k8s/configmap.yaml
```

Persistent storage:

```bash
kubectl apply -f k8s/pvc.yaml
```

The repository includes two PVCs:

```text
ml-data-pvc          5Gi
ml-checkpoints-pvc   2Gi
```

Both were successfully provisioned and reached `Bound`.

## Kubernetes Images

Docker Desktop Kubernetes uses the local kind node's containerd image store.

The final images were imported into the cluster with:

```bash
docker save mlops-train:v2 | \
docker exec -i desktop-control-plane ctr -n k8s.io images import -

docker save mlops-serve:v2 | \
docker exec -i desktop-control-plane ctr -n k8s.io images import -
```

The Kubernetes manifests use:

```yaml
imagePullPolicy: IfNotPresent
```

so the locally loaded images can be used without pulling from a registry.

## Kubernetes Serving

Deploy:

```bash
kubectl apply -f k8s/serving-deployment.yaml
kubectl apply -f k8s/serving-service.yaml
kubectl apply -f k8s/hpa.yaml
```

The validated Deployment reached:

```text
READY   2/2
UP-TO-DATE   2
AVAILABLE    2
```

The Deployment uses:

* 2 replicas
* RollingUpdate
* `maxSurge: 1`
* `maxUnavailable: 0`
* liveness probe on `/health`
* readiness probe on `/health`
* CPU and memory resource requests/limits
* read-only checkpoint PVC

The Service is:

```text
Type: ClusterIP
Port: 80
TargetPort: 8080
```

## Kubernetes Service Validation

Port-forward:

```bash
kubectl port-forward svc/model-serving 8081:80 -n ml-training
```

Health:

```bash
curl -i http://localhost:8081/health
```

Validated response:

```json
{"status":"ok"}
```

Prediction:

```bash
curl -X POST http://localhost:8081/predict \
  -F "image=@test_image.png"
```

The Kubernetes Service successfully routed the request to the serving Deployment and returned 10 class probabilities.

## Kubernetes Training Job

The repository includes:

```text
k8s/training-job.yaml
```

The Job uses:

* `mlops-train:v2`
* the training ConfigMap
* `ml-data-pvc`
* `ml-checkpoints-pvc`
* 2 CPU requested/limited
* 4Gi memory requested/limited

The Job infrastructure was successfully validated:

```text
Pod scheduled              ✓
v2 training image found    ✓
ConfigMap mounted          ✓
PVCs provisioned            ✓
Training container started  ✓
```

During local validation, however, the Kubernetes training process did not progress beyond its startup/download stage within the available validation window. Therefore the successful 10-epoch training result reported above is from the Docker training run, not from the Kubernetes Job.

The Docker-generated checkpoint was subsequently placed on the Kubernetes checkpoint PVC to validate the serving Deployment.

## HPA

The repository contains an `autoscaling/v2` HPA with:

```text
Minimum replicas: 2
Maximum replicas: 4
CPU target: 70%
```

During local Docker Desktop Kubernetes validation, the Metrics API was not available:

```text
/apis/metrics.k8s.io
→ NotFound
```

Therefore CPU utilization remained `unknown` and an actual CPU-driven scale event was not demonstrated.

## Git Workflow

The repository follows:

```text
main
  |
  v
develop
  |
  v
feature/*
  |
  v
Pull Request
  |
  v
develop
  |
  v
main
```

Four meaningful pull requests were merged:

```text
#1 docs: establish project workflow
#2 feat: implement pytorch training and serving pipeline
#3 perf: optimize docker images for cpu runtime
#4 feat: upgrade kubernetes workloads to optimized images
```

All four PRs passed the repository CI workflow.

## CI

GitHub Actions runs the Python test suite on pushes to `main`/`develop` and pull requests targeting those branches.

The validated CI result was:

```text
pytest
2 passed
```

## Validation Evidence

Recommended evidence to include with submission:

1. Public GitHub repository and branch structure.
2. Four merged pull requests.
3. Green GitHub Actions checks.
4. Docker training build and 10-epoch training output.
5. Docker checkpoint creation.
6. Docker serving `/health`.
7. Docker serving `/predict`.
8. Kubernetes Namespace, ConfigMap and PVCs.
9. Kubernetes Job scheduling and container startup.
10. Kubernetes Deployment showing 2/2 replicas.
11. Deployment probes/resources/rolling strategy.
12. Kubernetes Service and endpoints.
13. Kubernetes `/health`.
14. Kubernetes `/predict`.
15. HPA object and the local Metrics API limitation.

## Academic Integrity / AI-Assisted Development

AI assistance was used during development.

All AI-assisted changes were reviewed and tested locally, and the implementation should be explainable line-by-line during review, as required by the coursework instructions.
