"""
raster_engine_v2.rasterizer
===========================
Discrete 2D Rasterization & Rotational Kernel Caching.

Converts continuous Shapely geometries into 2D discrete boolean matrices
preserving topological holes using Pillow scanline polygon rasterization.
"""

from typing import Dict, List, Optional, Sequence, Tuple, Union, Any
import math
import numpy as np
from PIL import Image, ImageDraw
import shapely.affinity
from shapely.geometry import Polygon, MultiPolygon, GeometryCollection

from .geometry import validate_and_sanitize, apply_safety_margin


def _extract_polygons(geom: Any) -> List[Polygon]:
    """Recursively extracts all constituent Polygon instances from geometry."""
    if geom is None or geom.is_empty:
        return []
    if isinstance(geom, Polygon):
        return [geom]
    if isinstance(geom, MultiPolygon):
        return [g for g in geom.geoms if not g.is_empty and g.area > 0]
    if isinstance(geom, GeometryCollection):
        polys = []
        for g in geom.geoms:
            polys.extend(_extract_polygons(g))
        return polys
    return []


def rasterize_polygon(
    poly: Union[Polygon, MultiPolygon],
    delta: float = 1.0,
) -> np.ndarray:
    """
    Rasterizes a Shapely Polygon or MultiPolygon onto a discrete 2D grid matrix.

    Preserves topological holes by filling exterior rings with 1 and carving
    interior hole rings with 0 using Pillow C-accelerated scanline fill.

    Parameters
    ----------
    poly : Union[Polygon, MultiPolygon]
        Shapely Polygon or MultiPolygon.
    delta : float, optional
        Spatial cell size in millimeters (Delta > 0). Defaults to 1.0.

    Returns
    -------
    np.ndarray
        2D uint8 matrix of shape (h_cells, w_cells) where occupied solid
        cells are 1 and hole/background cells are 0.
        Returns shape (0, 0) if geometry is empty or degenerate.
    """
    if delta <= 0:
        raise ValueError(f"Resolution delta must be strictly positive: got {delta}")
    if poly is None or poly.is_empty or poly.area <= 0:
        return np.zeros((0, 0), dtype=np.uint8)

    minx, miny, maxx, maxy = poly.bounds
    width_mm = maxx - minx
    height_mm = maxy - miny

    if width_mm <= 0 or height_mm <= 0:
        return np.zeros((0, 0), dtype=np.uint8)

    w_cells = max(1, int(math.ceil(round(width_mm / delta, 9))))
    h_cells = max(1, int(math.ceil(round(height_mm / delta, 9))))

    img = Image.new("L", (w_cells, h_cells), 0)
    draw = ImageDraw.Draw(img)

    polygons = _extract_polygons(poly)
    for part in polygons:
        # 1. Fill exterior boundary with 1
        ext_coords = [
            (((x - minx) / delta), ((y - miny) / delta))
            for x, y in part.exterior.coords
        ]
        if len(ext_coords) >= 3:
            draw.polygon(ext_coords, fill=1)

        # 2. Carve interior rings (holes) with 0
        for interior in part.interiors:
            hole_coords = [
                (((x - minx) / delta), ((y - miny) / delta))
                for x, y in interior.coords
            ]
            if len(hole_coords) >= 3:
                draw.polygon(hole_coords, fill=0)

    return np.array(img, dtype=np.uint8)


def generate_rotation_kernels(
    poly: Union[Polygon, MultiPolygon],
    rotations: Optional[Sequence[float]] = None,
    delta: float = 1.0,
    margin: float = 2.0,
) -> Dict[float, Dict[str, Any]]:
    """
    Generates and caches rotated raster kernels for discrete angular increments.

    Parameters
    ----------
    poly : Union[Polygon, MultiPolygon]
        Continuous Shapely Polygon to rotate and rasterize.
    rotations : Optional[Sequence[float]], optional
        Sequence of rotation angles in degrees (default: [0, 90, 180, 270]).
    delta : float, optional
        Spatial resolution in millimeters. Defaults to 1.0.
    margin : float, optional
        Inter-piece safety margin in millimeters. Defaults to 2.0.

    Returns
    -------
    Dict[float, Dict[str, Any]]
        Dictionary mapping normalized angle (0.0 to 360.0) to kernel descriptors.
    """
    if rotations is None:
        angles = [0.0, 90.0, 180.0, 270.0]
    else:
        angles = list(rotations)

    if not angles:
        raise ValueError("Rotations list cannot be empty.")

    clean_poly = validate_and_sanitize(poly)
    if clean_poly is None or clean_poly.is_empty:
        raise ValueError("Cannot generate rotation kernels for empty or invalid polygon.")

    kernel_cache: Dict[float, Dict[str, Any]] = {}

    for angle in angles:
        norm_angle = float(angle % 360.0)
        if norm_angle in kernel_cache:
            continue

        # Continuous geometric rotation around origin
        poly_rot = shapely.affinity.rotate(clean_poly, angle, origin=(0.0, 0.0))
        minx, miny, maxx, maxy = poly_rot.bounds

        # Translate rotated shape to local (0, 0)
        poly_norm = shapely.affinity.translate(poly_rot, -minx, -miny)

        # Apply precision safety buffering
        poly_buf = apply_safety_margin(poly_norm, margin, delta)

        # Rasterize buffered shape
        kernel = rasterize_polygon(poly_buf, delta)
        kernel_flipped = np.flip(kernel, axis=(0, 1)).copy()

        kernel_cache[norm_angle] = {
            "kernel": kernel,
            "kernel_flipped": kernel_flipped,
            "shape": kernel.shape,
            "normalized_polygon": poly_norm,
            "rotated_polygon": poly_rot,
            "buffered_polygon": poly_buf,
            "origin_offset": (float(minx), float(miny)),
            "bounds": (float(minx), float(miny), float(maxx), float(maxy)),
            "delta": float(delta),
            "angle": float(angle),
        }

    return kernel_cache
