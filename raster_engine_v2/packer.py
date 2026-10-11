"""
raster_engine_v2.packer
=======================
Bottom-Left-Fill (BLF) Raster Packing Engine.

Implements discrete grid packing heuristics with multi-criteria BLF cost scoring,
automatic hole-fill bonus, and continuous Euclidean coordinate recovery.
"""

import math
from dataclasses import dataclass, asdict
from typing import List, Tuple, Optional, Sequence, Union, Dict, Any
import numpy as np
import shapely.affinity
from shapely.geometry import Polygon, MultiPolygon

from .geometry import (
    validate_and_sanitize,
    apply_safety_margin,
    recover_continuous_polygon,
)
from .rasterizer import rasterize_polygon
from .collision import check_collision_map, update_bin_map


@dataclass
class PlacementInfo:
    """Metadata record for a placed polygon."""
    item_id: Union[int, str]
    polygon: Union[Polygon, MultiPolygon]
    original_index: int
    position: Tuple[float, float]
    rotation: float
    grid_position: Tuple[int, int]
    placed_in_hole: bool = False
    host_item_id: Optional[Union[int, str]] = None
    bounds: Tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)
    area: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Exports placement metadata as a dictionary."""
        d = asdict(self)
        d["polygon"] = self.polygon
        return d


class BLFPacker:
    """
    Bottom-Left-Fill (BLF) packing algorithm using 2D grid boolean matrices
    and FFT cross-correlation collision detection.
    """

    def __init__(
        self,
        bin_width: float,
        bin_height: float,
        resolution: float = 1.0,
        margin: float = 2.0,
        allowed_rotations: Optional[Sequence[float]] = None,
        weight_bbox: float = 1.0,
        weight_x: float = 10.0,
        weight_y: float = 5.0,
        weight_c: float = 1.0,
        weight_r: float = 0.5,
        hole_bonus: float = 1e7,
    ):
        if bin_width <= 0 or bin_height <= 0:
            raise ValueError(f"Bin dimensions must be strictly positive: {bin_width}x{bin_height}")
        if resolution <= 0:
            raise ValueError(f"Resolution must be strictly positive: {resolution}")

        self.bin_width = float(bin_width)
        self.bin_height = float(bin_height)
        self.resolution = float(resolution)
        self.margin = float(margin)
        self.allowed_rotations = (
            tuple(allowed_rotations) if allowed_rotations is not None else (0.0, 90.0, 180.0, 270.0)
        )

        self.weight_bbox = weight_bbox
        self.weight_x = weight_x
        self.weight_y = weight_y
        self.weight_c = weight_c
        self.weight_r = weight_r
        self.hole_bonus = hole_bonus

        self.N_x = max(1, int(math.ceil(round(self.bin_width / self.resolution, 9))))
        self.N_y = max(1, int(math.ceil(round(self.bin_height / self.resolution, 9))))

        self.bin_map = np.zeros((self.N_y, self.N_x), dtype=np.uint8)
        self._apply_boundary_mask()
        self.current_max_c: int = 0
        self.current_max_r: int = 0

        self.placed_items: List[PlacementInfo] = []
        self.unplaced_items: List[Tuple[int, Union[Polygon, MultiPolygon]]] = []

    def _apply_boundary_mask(self) -> None:
        """
        Masks out fractional overhang boundary cells in bin_map.

        When bin_width or bin_height is not an exact integer multiple of resolution,
        discrete ceiling allocation extends beyond the physical sheet. Cells at or
        exceeding the continuous boundary are marked as 1 (occupied) so FFT
        convolution immediately prevents placements into the overhang margin.
        """
        cut_x = int(round(self.bin_width / self.resolution, 9))
        cut_y = int(round(self.bin_height / self.resolution, 9))
        if cut_x < self.N_x:
            self.bin_map[:, cut_x:] = 1
        if cut_y < self.N_y:
            self.bin_map[cut_y:, :] = 1

    def reset(self) -> None:
        """Resets the packing grid and item lists."""
        self.bin_map.fill(0)
        self._apply_boundary_mask()
        self.current_max_c = 0
        self.current_max_r = 0
        self.placed_items.clear()
        self.unplaced_items.clear()

    def pack(
        self,
        shapes: Sequence[Union[Polygon, MultiPolygon]],
        sort_by_area: bool = True,
    ) -> List[PlacementInfo]:
        """
        Packs the given sequence of shapes into the bin.

        Parameters
        ----------
        shapes : Sequence[Union[Polygon, MultiPolygon]]
            Shapes to nest.
        sort_by_area : bool, optional
            Whether to pre-sort shapes by descending solid area. Defaults to True.

        Returns
        -------
        List[PlacementInfo]
            List of successfully placed item metadata records.
        """
        self.reset()

        # 1. Validate and sanitize
        valid_items: List[Tuple[int, Union[Polygon, MultiPolygon]]] = []
        for idx, s in enumerate(shapes):
            clean_s = validate_and_sanitize(s)
            if clean_s is not None and not clean_s.is_empty and clean_s.area > 0:
                valid_items.append((idx, clean_s))

        # 2. Pre-sort descending by area
        if sort_by_area:
            valid_items.sort(
                key=lambda it: (
                    it[1].area,
                    (it[1].bounds[2] - it[1].bounds[0]) ** 2 + (it[1].bounds[3] - it[1].bounds[1]) ** 2,
                    -it[0],
                ),
                reverse=True,
            )

        # 3. Sequentially place each shape
        for orig_idx, shape in valid_items:
            self._place_shape(orig_idx, shape)

        return self.placed_items

    def _place_shape(
        self,
        orig_idx: int,
        shape: Union[Polygon, MultiPolygon],
    ) -> Optional[PlacementInfo]:
        """
        Evaluates all candidate rotations and positions for a single shape,
        commits the optimal placement to the bin grid, and records metadata.
        """
        placed_polys = [it.polygon for it in self.placed_items]
        candidates = []

        for theta in self.allowed_rotations:
            # Continuous rotation around origin
            norm_theta = float(theta % 360.0)
            if abs(norm_theta) > 1e-9:
                poly_rot = shapely.affinity.rotate(shape, norm_theta, origin=(0.0, 0.0))
            else:
                poly_rot = shape

            minx, miny, maxx, maxy = poly_rot.bounds
            poly_norm = shapely.affinity.translate(poly_rot, -minx, -miny)
            norm_bounds = poly_norm.bounds

            # Apply precision safety buffering
            poly_buf = apply_safety_margin(poly_norm, self.margin, self.resolution)
            buf_minx, buf_miny, _, _ = poly_buf.bounds

            kernel = rasterize_polygon(poly_buf, self.resolution)
            kh, kw = kernel.shape

            # Dimension pre-check guard
            if kh > self.N_y or kw > self.N_x:
                continue

            # FFT cross-correlation collision check
            valid_map = check_collision_map(self.bin_map, kernel)
            rows, cols = np.where(valid_map)
            if len(rows) == 0:
                continue

            # Continuous bounding box sheet containment check
            tx_cands = cols * self.resolution - buf_minx
            ty_cands = rows * self.resolution - buf_miny
            valid_containment = (
                (tx_cands >= -1e-9)
                & (ty_cands >= -1e-9)
                & (tx_cands + norm_bounds[2] <= self.bin_width + 1e-9)
                & (ty_cands + norm_bounds[3] <= self.bin_height + 1e-9)
            )
            rows = rows[valid_containment]
            cols = cols[valid_containment]
            if len(rows) == 0:
                continue

            # Vectorized multi-criteria cost scoring
            c_max = cols + kw
            r_max = rows + kh
            c_new = np.maximum(self.current_max_c, c_max)
            r_new = np.maximum(self.current_max_r, r_max)

            in_envelope = (c_max <= self.current_max_c) & (r_max <= self.current_max_r)

            costs = (
                self.weight_bbox * (c_new.astype(np.float64) * r_new.astype(np.float64))
                + self.weight_x * c_max.astype(np.float64)
                + self.weight_y * r_max.astype(np.float64)
                + self.weight_c * cols.astype(np.float64)
                + self.weight_r * rows.astype(np.float64)
                - in_envelope.astype(np.float64) * self.hole_bonus
            )

            k_candidates = min(len(rows), 100)
            sorted_indices = np.argsort(costs)[:k_candidates]
            for idx in sorted_indices:
                candidates.append((
                    float(costs[idx]),
                    theta,
                    int(rows[idx]),
                    int(cols[idx]),
                    poly_norm,
                    kernel,
                    buf_minx,
                    buf_miny,
                    float(minx),
                    float(miny),
                ))

        # Sort candidate positions globally across all rotations by BLF cost
        candidates.sort(key=lambda x: x[0])

        best_candidate = None

        # Filter candidate positions against continuous Euclidean geometry
        for cand in candidates:
            cost, theta, r, c, poly_norm, kernel, buf_minx, buf_miny, rot_minx, rot_miny = cand
            tx = c * self.resolution - buf_minx
            ty = r * self.resolution - buf_miny
            p_cand = shapely.affinity.translate(poly_norm, tx, ty)

            # Continuous boundary containment check (guards against fractional spill)
            if (p_cand.bounds[0] < -1e-7 or
                p_cand.bounds[1] < -1e-7 or
                p_cand.bounds[2] > self.bin_width + 1e-7 or
                p_cand.bounds[3] > self.bin_height + 1e-7):
                continue

            # Continuous pairwise intersection check against already placed shapes
            has_overlap = False
            for p_prev in placed_polys:
                # Fast AABB disjoint rejection
                if not (p_cand.bounds[0] >= p_prev.bounds[2] or
                        p_cand.bounds[2] <= p_prev.bounds[0] or
                        p_cand.bounds[1] >= p_prev.bounds[3] or
                        p_cand.bounds[3] <= p_prev.bounds[1]):
                    inter = p_cand.intersection(p_prev)
                    if inter.area > 1e-9:
                        has_overlap = True
                        break
            if not has_overlap:
                best_candidate = (theta, r, c, poly_norm, kernel, buf_minx, buf_miny, rot_minx, rot_miny)
                break

        if best_candidate is None:
            self.unplaced_items.append((orig_idx, shape))
            return None

        # Commit optimal candidate
        theta, best_r, best_c, norm_poly, kernel, buf_minx, buf_miny, rot_minx, rot_miny = best_candidate

        # Continuous Euclidean recovery
        tx = best_c * self.resolution - buf_minx
        ty = best_r * self.resolution - buf_miny
        p_placed = shapely.affinity.translate(norm_poly, tx, ty)

        # Numerical stabilization guard against sub-atomic boundary overhang (< 1e-9)
        # Guarantees strictly: bounds[0] >= 0.0, bounds[1] >= 0.0,
        # bounds[2] <= bin_width, bounds[3] <= bin_height
        shift_x = 0.0
        shift_y = 0.0
        if p_placed.bounds[0] < 0.0:
            shift_x = -p_placed.bounds[0]
        elif p_placed.bounds[2] > self.bin_width:
            shift_x = self.bin_width - p_placed.bounds[2]

        if p_placed.bounds[1] < 0.0:
            shift_y = -p_placed.bounds[1]
        elif p_placed.bounds[3] > self.bin_height:
            shift_y = self.bin_height - p_placed.bounds[3]

        if abs(shift_x) > 0.0 or abs(shift_y) > 0.0:
            p_placed = shapely.affinity.translate(p_placed, shift_x, shift_y)
            tx += shift_x
            ty += shift_y

        # Exact continuous transformation offset to position the original shape after rotation:
        # translate(rotate(shape, theta, origin=(0.0, 0.0)), pos_x, pos_y) == p_placed
        pos_x = tx - rot_minx
        pos_y = ty - rot_miny

        # In-place bitwise bin matrix update
        self.bin_map = update_bin_map(self.bin_map, kernel, best_r, best_c)

        # Update bounding extents
        self.current_max_c = max(self.current_max_c, best_c + kernel.shape[1])
        self.current_max_r = max(self.current_max_r, best_r + kernel.shape[0])

        # Topological hole nesting check against previous placements
        placed_in_hole = False
        host_id = None
        for host in self.placed_items:
            interiors = []
            if isinstance(host.polygon, Polygon):
                interiors = host.polygon.interiors
            elif isinstance(host.polygon, MultiPolygon):
                for part in host.polygon.geoms:
                    interiors.extend(part.interiors)

            for ring in interiors:
                hole_poly = Polygon(ring)
                if hole_poly.covers(p_placed) or hole_poly.contains(p_placed.centroid):
                    placed_in_hole = True
                    host_id = host.item_id
                    break
            if placed_in_hole:
                break

        info = PlacementInfo(
            item_id=orig_idx,
            polygon=p_placed,
            original_index=orig_idx,
            position=(float(pos_x), float(pos_y)),
            rotation=float(theta),
            grid_position=(best_r, best_c),
            placed_in_hole=placed_in_hole,
            host_item_id=host_id,
            bounds=p_placed.bounds,
            area=float(p_placed.area),
        )

        self.placed_items.append(info)
        return info
