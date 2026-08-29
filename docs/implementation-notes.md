# Implementation Notes

## Deliberate decisions

1. Python 3.11 is used because it matches the assignment's Docker example and is supported by current PyTorch wheels.
2. ResNet-18 is initialized with `weights=None` because this is a coursework classifier and avoids a runtime dependency on downloading pretrained ImageNet weights.
3. The checkpoint stores architecture, class names, and model state so serving can load the model without re-reading the training YAML.
4. `k8s/pvc.yaml` is added because the assignment explicitly requires persistent volumes for `/app/data` and `/app/checkpoints` but does not include a PVC manifest in its required file list.
5. `hpa.yaml` targets 70% average CPU utilization with 2–4 replicas. This is the natural implementation of the handout's requirement that `hpa.yaml` exist, while the exact HPA policy is not specified in the handout.
6. Kubernetes images use `IfNotPresent` so Docker Desktop Kubernetes can use locally built images without an external registry.

## Important local limitation

A MacBook does not provide NVIDIA CUDA to the Linux containers used here. The training code automatically falls back to CPU. The GPU request in the assignment is therefore kept as a bonus-only extension and is not enabled in the default manifest.
