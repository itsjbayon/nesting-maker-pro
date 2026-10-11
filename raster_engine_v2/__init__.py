"""
raster_engine_v2: True-Shape Raster-Based Nesting Engine
========================================================
High-performance 2D irregular shape nesting using discrete boolean grids
and FFT cross-correlation collision detection.
"""

from .engine import RasterNestingEngine
from .packer import BLFPacker, PlacementInfo
from .geometry import (
    validate_and_sanitize,
    normalize_polygon,
    compute_discrete_bounds,
    compute_safety_margin_distance,
    apply_safety_margin,
    recover_continuous_polygon,
    place_polygon,
)
from .rasterizer import (
    rasterize_polygon,
    generate_rotation_kernels,
)
from .collision import (
    check_collision_map,
    find_valid_placements,
    can_place,
    update_bin_map,
    create_bin_map,
)

__version__ = "2.0.0"

__all__ = [
    "RasterNestingEngine",
    "BLFPacker",
    "PlacementInfo",
    "validate_and_sanitize",
    "normalize_polygon",
    "compute_discrete_bounds",
    "compute_safety_margin_distance",
    "apply_safety_margin",
    "recover_continuous_polygon",
    "place_polygon",
    "rasterize_polygon",
    "generate_rotation_kernels",
    "check_collision_map",
    "find_valid_placements",
    "can_place",
    "update_bin_map",
    "create_bin_map",
]
