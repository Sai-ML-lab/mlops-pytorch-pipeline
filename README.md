# MLOps PyTorch Pipeline

A production-style PyTorch image classification pipeline implementing the coursework requirements for repository discipline, Dockerized training, Kubernetes training Jobs, persistent storage, model serving, health checks, configuration, and autoscaling.

## Assignment mapping

| Coursework area | Implementation |
|---|---|
| Part A | GitHub repository structure, branches, PR workflow, CI, `.gitignore` |
| Part B | ResNet-18 + CIFAR-10 + YAML-driven training + JSONL metrics + checkpoint + early stopping + FastAPI |
| Part C | Multi-stage training Dockerfile + slim non-root serving image + healthcheck |
| Part D | Kubernetes Namespace + ConfigMap + PVCs + training Job |
| Part E | 2-replica Deployment + PVC read-only mount + probes + rolling update + Service |
| Part F | End-to-end Kubernetes validation + port-forward + prediction request |

## Architecture

```text
                    ┌──────────────────────┐
                    │       GitHub         │
                    │ main / develop / PRs │
                    └──────────┬───────────┘
                               │
                        GitHub Actions CI
                               │
                 ┌─────────────▼─────────────┐
                 │        Docker Images      │
                 │  mlops-train / mlops-serve│
                 └─────────────┬─────────────┘
                               │
                    Docker Desktop Kubernetes
                               │
        ┌──────────────────────┼───────────────────────┐
        │                      │                       │
┌───────▼────────┐     ┌───────▼────────┐      ┌───────▼────────┐
│ ConfigMap      │     │ Training Job   │      │ Serving Deploy │
│ YAML config    │────►│ PyTorch/CIFAR10│─────►│ 2 replicas     │
└────────────────┘     └───────┬────────┘      └───────┬────────┘
                               │                       │
                         ┌─────▼─────┐           ┌─────▼─────┐
                         │ Checkpoint │◄──────────│ Read-only │
                         │ PVC        │           │ checkpoint│
                         └───────────┘           └─────┬─────┘
                                                       │
                                                 ┌─────▼─────┐
                                                 │ ClusterIP │
                                                 │ Service   │
                                                 │ :80→:8080 │
                                                 └─────┬─────┘
                                                       │
                                               kubectl port-forward
                                                       │
                                                 POST /predict
```

## Mac environment

The recommended setup is:

- macOS
- Python 3.11 for local development
- Docker Desktop
- Docker Desktop Kubernetes
- `kubectl`
- Git and GitHub CLI (`gh`)

PyTorch's current macOS guidance recommends Python 3.9–3.12, and the pinned project version (`torch==2.13.0`) has Python 3.11 macOS ARM64 wheels. 

## Local Python setup

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements/train.txt
python -m pip install -r requirements/test.txt
```

Run tests:

```bash
pytest -q
```

## Local training without Docker

The config defaults to `/app/...` because Kubernetes/Docker uses those mount paths. For a local run, copy the config and override the two paths:

```bash
cp configs/training_config.yaml configs/local_training_config.yaml
sed -i '' 's#/app/data#./data#; s#/app/checkpoints#./checkpoints#' configs/local_training_config.yaml
TRAINING_CONFIG_PATH=configs/local_training_config.yaml python src/train.py
```

## Docker training

Build:

```bash
docker build -f docker/Dockerfile.train -t mlops-train:v1 .
```

Run:

```bash
mkdir -p data checkpoints
docker run --rm \
  -v "$(pwd)/data:/app/data" \
  -v "$(pwd)/checkpoints:/app/checkpoints" \
  mlops-train:v1
```

The training process downloads CIFAR-10 into `data/`, writes JSONL metrics to stdout, and stores the best checkpoint at `checkpoints/classifier_v1.pt`.

## Docker serving

Build:

```bash
docker build -f docker/Dockerfile.serve -t mlops-serve:v1 .
```

Run:

```bash
docker run --rm -p 8080:8080 \
  -v "$(pwd)/checkpoints:/app/checkpoints:ro" \
  mlops-serve:v1
```

Health:

```bash
curl http://localhost:8080/health
```

Prediction:

```bash
curl -X POST http://localhost:8080/predict \
  -F "image=@test_image.png"
```

`test_image.png` can be any RGB image. The model resizes it to the 32×32 CIFAR-10 input shape.

## Kubernetes on Docker Desktop

Enable Kubernetes in Docker Desktop, then verify:

```bash
kubectl config current-context
kubectl get nodes
```

For this coursework, the Docker Desktop Kubernetes context is sufficient; a cloud cluster is not required.

### Load local images into Docker Desktop Kubernetes

Docker Desktop Kubernetes can use locally built images with `imagePullPolicy: IfNotPresent`. Build both images before creating the Job/Deployment:

```bash
docker build -f docker/Dockerfile.train -t mlops-train:v1 .
docker build -f docker/Dockerfile.serve -t mlops-serve:v1 .
```

### Deploy training

The coursework requires a ConfigMap and persistent storage. The handout lists the Job and Deployment manifests but does not list a separate PVC YAML file, so this repository adds `k8s/pvc.yaml` to make the storage requirement executable.

```bash
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/pvc.yaml
kubectl apply -f k8s/training-job.yaml
```

Monitor:

```bash
kubectl get pvc -n ml-training
kubectl get jobs -n ml-training
kubectl get pods -n ml-training
kubectl logs job/pytorch-training -n ml-training -f
```

Wait for the Job to show `1/1` completions.

### Deploy serving

```bash
kubectl apply -f k8s/serving-deployment.yaml
kubectl apply -f k8s/serving-service.yaml
kubectl apply -f k8s/hpa.yaml
```

Verify:

```bash
kubectl get pods -n ml-training
kubectl describe deployment model-serving -n ml-training
kubectl get hpa -n ml-training
```

Port-forward:

```bash
kubectl port-forward svc/model-serving 8080:80 -n ml-training
```

In another terminal:

```bash
curl http://localhost:8080/health
curl -X POST http://localhost:8080/predict \
  -F "image=@test_image.png"
```

## Git workflow required by the coursework

The assignment requires `main` → `develop`, then feature branches, and at least four merged PRs: two per week.

Suggested sequence:

```text
main
  └── develop
        ├── feature/repository-ci
        ├── feature/pytorch-model
        ├── feature/docker-images
        └── feature/kubernetes-deployment
```

Use Conventional Commit messages such as:

```text
chore: initialize mlops repository
feat: add cifar10 resnet18 training pipeline
feat: add dockerized training and serving
feat: add kubernetes training and serving manifests
ci: add python test workflow
```

Every AI-assisted change must be disclosed in the commit message according to the assignment's academic-integrity instruction, and you should be able to explain every line during review.

## Submission evidence checklist

Collect screenshots/terminal logs for:

1. Repository structure and branches.
2. CI passing on PRs.
3. Docker training build and successful checkpoint creation.
4. Docker serving health and prediction.
5. Kubernetes namespace/config/PVC/Job creation.
6. Training Job completion and logs.
7. Two serving replicas becoming Ready.
8. Deployment description showing probes/resources/rolling strategy.
9. HPA object.
10. Port-forwarded `/health` and `/predict` responses.
11. Final merged PR containing validation evidence.
