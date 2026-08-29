from pathlib import Path
import sys

import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from model import get_model


def test_resnet18_output_shape() -> None:
    model = get_model("resnet18", 10)
    model.eval()
    sample = torch.randn(2, 3, 32, 32)
    output = model(sample)
    assert output.shape == (2, 10)


def test_invalid_architecture() -> None:
    try:
        get_model("unknown", 10)
    except ValueError:
        return
    raise AssertionError("Expected ValueError for unsupported architecture")
