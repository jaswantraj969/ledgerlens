"""Derived layout groups: a coarse stand-in for vendors, fitted on train only."""

from collections.abc import Sequence

import numpy as np
from sklearn.cluster import KMeans

GRID_COLUMNS = 4
GRID_ROWS = 6
GROUP_COUNT = 12
GROUP_SEED = 20261106


def layout_descriptor(
    centers: Sequence[tuple[float, float]], width: int, height: int
) -> np.ndarray:
    """Share of word centres per grid cell, plus aspect ratio. Uses no text or labels."""
    grid = np.zeros((GRID_ROWS, GRID_COLUMNS))
    for x, y in centers:
        column = min(int(GRID_COLUMNS * x / width), GRID_COLUMNS - 1)
        row = min(int(GRID_ROWS * y / height), GRID_ROWS - 1)
        grid[max(row, 0), max(column, 0)] += 1
    if centers:
        grid /= len(centers)
    return np.append(grid.ravel(), width / height)


def fit_groups(train_descriptors: np.ndarray) -> KMeans:
    model = KMeans(n_clusters=GROUP_COUNT, n_init=10, random_state=GROUP_SEED)
    return model.fit(train_descriptors)
