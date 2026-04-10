from dataclasses import dataclass
from typing import Protocol

import numpy as np


@dataclass(slots=True)
class Detection:
    label: str
    confidence: float
    x1: int
    y1: int
    x2: int
    y2: int


class Detector(Protocol):
    def predict(self, frame: np.ndarray) -> list[Detection]:
        ...
