"""
raster_engine_v2.collision
==========================
2D FFT Cross-Correlation Collision Detection.

Computes exhaustive sheet collision maps in O(N log N) via FFT convolution,
enforces dimension guards, applies numerical thresholding, and updates bin occupancy.
"""

from typing import Tuple, Union
import numpy as np
import scipy.signal


def check_collision_map(
    bin_map: np.ndarray,
    kernel: np.ndarray,
    threshold: float = 0.5,
) -> np.ndarray:
    """
    Computes 2D collision-free candidate map using FFT cross-correlation.

    Evaluates: C = bin_map * flip(kernel) using scipy.signal.fftconvolve.
    Valid collision-free placement positions satisfy C < threshold.

    Parameters
    ----------
    bin_map : np.ndarray
        2D binary/uint8 array of shape (Ny, Nx) representing sheet occupancy.
    kernel : np.ndarray
        2D binary/uint8 array of shape (kh, kw) representing candidate piece.
    threshold : float, optional
        Residual noise cutoff. Defaults to 0.5.

    Returns
    -------
    np.ndarray
        2D boolean array of shape (Ny - kh + 1, Nx - kw + 1) where
        True indicates a collision-free placement position.
        Returns shape (0, 0) boolean array if kernel exceeds bin bounds.
    """
    if bin_map.size == 0 or kernel.size == 0:
        return np.zeros((0, 0), dtype=bool)

    kh, kw = kernel.shape
    bh, bw = bin_map.shape

    # Dimension pre-check guard: prevents SciPy ValueError & argument swapping
    if kh > bh or kw > bw:
        return np.zeros((0, 0), dtype=bool)

    # Pre-flip kernel along both axes for cross-correlation
    kernel_flipped = np.flip(kernel, axis=(0, 1))

    # Fast single-precision FFT convolution
    c = scipy.signal.fftconvolve(
        bin_map.astype(np.float32, copy=False),
        kernel_flipped.astype(np.float32, copy=False),
        mode="valid",
    )

    # Numerical thresholding eliminates machine precision residuals
    return c < threshold


def find_valid_placements(
    bin_map: np.ndarray,
    kernel: np.ndarray,
    threshold: float = 0.5,
) -> np.ndarray:
    """
    Extracts all valid (row, col) coordinates where kernel fits without collision.

    Parameters
    ----------
    bin_map : np.ndarray
        2D sheet occupancy matrix.
    kernel : np.ndarray
        2D piece kernel matrix.
    threshold : float, optional
        Numerical threshold. Defaults to 0.5.

    Returns
    -------
    np.ndarray
        Integer array of shape (N, 2) containing [row, col] candidate pairs.
    """
    valid_map = check_collision_map(bin_map, kernel, threshold=threshold)
    if valid_map.size == 0:
        return np.zeros((0, 2), dtype=int)
    return np.argwhere(valid_map)


def can_place(
    bin_map: np.ndarray,
    kernel: np.ndarray,
    row: int,
    col: int,
) -> bool:
    """
    Fast direct collision check for a single localized coordinate.

    Parameters
    ----------
    bin_map : np.ndarray
        2D sheet occupancy matrix.
    kernel : np.ndarray
        2D piece kernel matrix.
    row : int
        Row index in bin_map.
    col : int
        Column index in bin_map.

    Returns
    -------
    bool
        True if kernel can be placed at (row, col) without collision.
    """
    kh, kw = kernel.shape
    bh, bw = bin_map.shape
    if row < 0 or col < 0 or row + kh > bh or col + kw > bw:
        return False
    sub_bin = bin_map[row : row + kh, col : col + kw]
    return not np.any(np.logical_and(sub_bin, kernel))


def update_bin_map(
    bin_map: np.ndarray,
    kernel: np.ndarray,
    row: int,
    col: int,
) -> np.ndarray:
    """
    Updates the bin occupancy matrix in-place using bitwise maximum / logical OR.

    Parameters
    ----------
    bin_map : np.ndarray
        2D binary/uint8 array of shape (Ny, Nx).
    kernel : np.ndarray
        2D binary/uint8 array of shape (kh, kw).
    row : int
        Placement row index.
    col : int
        Placement column index.

    Returns
    -------
    np.ndarray
        Updated bin_map reference.
    """
    if kernel.size == 0:
        return bin_map

    kh, kw = kernel.shape
    bh, bw = bin_map.shape

    if row < 0 or col < 0:
        raise ValueError(f"Placement coordinates cannot be negative: row={row}, col={col}")
    if row + kh > bh or col + kw > bw:
        raise ValueError(
            f"Kernel placement ({row}+{kh}, {col}+{kw}) exceeds bin bounds ({bh}, {bw})"
        )

    # In-place bitwise maximum preserves existing hole voids
    target_slice = bin_map[row : row + kh, col : col + kw]
    np.maximum(target_slice, kernel, out=target_slice)
    return bin_map


def create_bin_map(
    width_mm: float,
    height_mm: float,
    delta: float = 1.0,
    border_margin: float = 0.0,
) -> np.ndarray:
    """
    Allocates an initialized 2D bin occupancy matrix with optional border margins.

    Parameters
    ----------
    width_mm : float
        Bin width along X in millimeters.
    height_mm : float
        Bin height along Y in millimeters.
    delta : float, optional
        Spatial resolution in millimeters. Defaults to 1.0.
    border_margin : float, optional
        Unplaceable sheet edge margin in millimeters. Defaults to 0.0.

    Returns
    -------
    np.ndarray
        2D uint8 matrix of shape (Ny, Nx).
    """
    if width_mm <= 0 or height_mm <= 0 or delta <= 0:
        raise ValueError("Bin dimensions and delta must be strictly positive.")

    n_x = int(np.ceil(round(width_mm / delta, 9)))
    n_y = int(np.ceil(round(height_mm / delta, 9)))

    bin_map = np.zeros((n_y, n_x), dtype=np.uint8)

    if border_margin > 0.0:
        margin_cells = int(np.ceil(round(border_margin / delta, 9)))
        if margin_cells > 0:
            bin_map[:margin_cells, :] = 1
            bin_map[-margin_cells:, :] = 1
            bin_map[:, :margin_cells] = 1
            bin_map[:, -margin_cells:] = 1

    return bin_map
