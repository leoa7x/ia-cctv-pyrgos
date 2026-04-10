from __future__ import annotations

import numpy as np

from app.detectors.base import Detection


class NullDetector:
    def predict(self, frame: np.ndarray) -> list[Detection]:
        return []
