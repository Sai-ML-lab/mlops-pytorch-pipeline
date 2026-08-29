"""Model factory for CIFAR-10 image classification."""

from __future__ import annotations

import torch.nn as nn
from torchvision import models


def get_model(architecture: str, num_classes: int) -> nn.Module:
    """Build the configured classifier.

    The assignment specifies either a CNN or torchvision model. ResNet-18 is used
    here and its final classification layer is replaced for CIFAR-10's 10 classes.
    """
    architecture = architecture.lower()
    if architecture != "resnet18":
        raise ValueError(f"Unsupported architecture: {architecture}")

    model = models.resnet18(weights=None)
    model.fc = nn.Linear(model.fc.in_features, num_classes)
    return model
