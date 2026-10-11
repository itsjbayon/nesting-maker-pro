"""
raster_engine_v2.geometry
=========================
Core geometric validation, normalization, precision safety buffering,
and continuous Euclidean coordinate recovery for True-Shape raster nesting.
"""

import math
from typing import Any, List, Optional, Tuple, Union
import shapely
from shapely.geometry import GeometryCollection, MultiPolygon, Polygon
from shapely.geometry.base import BaseGeometry
from shapely.validation import make_valid
import shapely.affinity as affinity


def compute_safety_margin_distance(margin: float, delta: float) -> float:
    """
    Calculate the precision safety buffer distance epsilon.

    Formula:
        epsilon = max(margin / 2.0, (sqrt(2) / 2.0) * delta)

    Parameters
    ----------
    margin : float
        Physical part-to-part spacing requested by user in mm (>= 0.0).
    delta : float
        Grid cell spatial resolution in mm/unit (> 0.0).

    Returns
    -------
    float
        Safety buffer distance epsilon. Guaranteed to be strictly positive (> 0.0).

    Raises
    ------
    ValueError
        If margin < 0.0 or delta <= 0.0.
    """
    if margin < 0.0:
        raise ValueError(f"margin must be non-negative (>= 0.0), got {margin}")
    if delta <= 0.0:
        raise ValueError(f"delta must be strictly positive (> 0.0), got {delta}")

    min_epsilon = (math.sqrt(2.0) / 2.0) * delta
    return max(margin / 2.0, min_epsilon)


def validate_and_sanitize(geom: Any) -> Union[Polygon, MultiPolygon]:
    """
    Validate, repair, and clean input geometry, strictly returning a 2D Polygon or MultiPolygon.

    Uses `shapely.validation.make_valid` to resolve self-intersections, bowties,
    and non-manifold boundaries. Filters out non-2D degenerate artifacts
    (points, lines, dangling spikes) often returned inside GeometryCollections.

    Parameters
    ----------
    geom : Any
        Input geometry expected to be a Shapely Polygon, MultiPolygon, or BaseGeometry.

    Returns
    -------
    Union[Polygon, MultiPolygon]
        A topologically valid 2D Polygon or MultiPolygon with area > 1e-9.

    Raises
    ------
    TypeError
        If geom is None or not an instance of Shapely BaseGeometry.
    ValueError
        If geom is empty or contains no 2D polygonal surface after repair.
    """
    if geom is None:
        raise TypeError("Input geometry cannot be None")
    if not isinstance(geom, BaseGeometry):
        raise TypeError(f"Expected Shapely geometry, got {type(geom).__name__}")
    if geom.is_empty:
        raise ValueError("Input geometry is empty")

    # 1. Fast-path: already valid 2D Polygon
    if isinstance(geom, Polygon) and geom.is_valid and geom.area > 1e-9:
        return geom

    # 2. Specialized repair for Polygons with interior holes that touch or cross exterior boundary
    if isinstance(geom, Polygon) and len(geom.interiors) > 0:
        try:
            ext_poly = Polygon(geom.exterior)
            if ext_poly.is_valid and ext_poly.area > 1e-9:
                inset_ext = ext_poly.buffer(-1e-3)
                new_holes = []
                for h in geom.interiors:
                    hp = Polygon(h)
                    if not hp.is_valid:
                        hp = make_valid(hp)
                    shares_segment = ext_poly.boundary.intersection(hp.boundary).length > 1e-7
                    exceeds_exterior = not ext_poly.covers(hp)
                    if exceeds_exterior or shares_segment:
                        clipped = hp.intersection(inset_ext)
                        if clipped.geom_type == "Polygon" and clipped.area > 1e-6:
                            new_holes.append(clipped.exterior.coords)
                        elif clipped.geom_type in ("MultiPolygon", "GeometryCollection"):
                            for sub in clipped.geoms:
                                if sub.geom_type == "Polygon" and sub.area > 1e-6:
                                    new_holes.append(sub.exterior.coords)
                    else:
                        new_holes.append(hp.exterior.coords if hasattr(hp, "exterior") else h)
                if new_holes:
                    candidate = Polygon(geom.exterior, new_holes)
                    if candidate.is_valid and candidate.area > 1e-9:
                        return candidate
        except Exception:
            pass

    repaired = make_valid(geom)
    if repaired.is_empty:
        raise ValueError("Geometry is empty after repair")

    polys: List[Polygon] = []

    def _collect(g: Any) -> None:
        if g is None or g.is_empty:
            return
        if g.geom_type == "Polygon":
            if g.area > 1e-9:
                polys.append(g)
        elif g.geom_type == "MultiPolygon":
            for sub in g.geoms:
                _collect(sub)
        elif g.geom_type == "GeometryCollection":
            for sub in g.geoms:
                _collect(sub)

    _collect(repaired)

    if not polys:
        raise ValueError("Geometry contains no valid 2D polygonal area (area <= 1e-9)")

    if len(polys) == 1:
        return polys[0]
    return MultiPolygon(polys)


def normalize_polygon(
    geom: Union[Polygon, MultiPolygon],
    angle: float = 0.0,
) -> Tuple[Union[Polygon, MultiPolygon], Tuple[float, float, float, float]]:
    """
    Rotate a geometry by candidate angle and translate its envelope origin to (0.0, 0.0).

    Parameters
    ----------
    geom : Union[Polygon, MultiPolygon]
        The continuous Shapely polygon or multipolygon.
    angle : float, optional
        Rotation angle in degrees counter-clockwise around (0, 0). Defaults to 0.0.

    Returns
    -------
    Tuple[Union[Polygon, MultiPolygon], Tuple[float, float, float, float]]
        - norm_geom: Geometry shifted so that its bounding box starts at (0.0, 0.0).
        - bounds: (minx, miny, maxx, maxy) continuous bounds of the rotated geometry
          prior to origin shifting. (minx, miny) is the origin offset.
    """
    valid_geom = validate_and_sanitize(geom)

    norm_angle = angle % 360.0
    if abs(norm_angle) > 1e-9:
        rotated = affinity.rotate(valid_geom, norm_angle, origin=(0.0, 0.0))
    else:
        rotated = valid_geom

    minx, miny, maxx, maxy = rotated.bounds
    norm_geom = affinity.translate(rotated, -minx, -miny)
    return norm_geom, (minx, miny, maxx, maxy)


def compute_discrete_bounds(
    bounds: Tuple[float, float, float, float],
    delta: float,
) -> Tuple[int, int]:
    """
    Compute discrete grid dimensions (cols, rows) required to rasterize bounds.

    Parameters
    ----------
    bounds : Tuple[float, float, float, float]
        Bounding box (minx, miny, maxx, maxy).
    delta : float
        Grid cell spatial resolution (> 0.0).

    Returns
    -------
    Tuple[int, int]
        (cols, rows) grid kernel dimensions (width in cols, height in rows).
    """
    if delta <= 0.0:
        raise ValueError(f"delta must be strictly positive (> 0.0), got {delta}")

    minx, miny, maxx, maxy = bounds
    w = max(0.0, maxx - minx)
    h = max(0.0, maxy - miny)
    cols = max(1, int(math.ceil(round(w / delta, 9))))
    rows = max(1, int(math.ceil(round(h / delta, 9))))
    return cols, rows


def is_axis_aligned(
    geom: Union[Polygon, MultiPolygon],
    tol: float = 1e-7,
) -> bool:
    """
    Determine whether all boundary edges of a polygon are parallel to coordinate axes (X or Y).

    Parameters
    ----------
    geom : Union[Polygon, MultiPolygon]
        Continuous Shapely polygon geometry.
    tol : float, optional
        Coordinate comparison numerical tolerance (default: 1e-7).

    Returns
    -------
    bool
        True if all edges in all exterior and interior rings are strictly horizontal
        or vertical; False if any diagonal, slanted, or curved boundary edge is present.
    """
    if geom is None or geom.is_empty:
        return True

    geoms = [geom] if isinstance(geom, Polygon) else (geom.geoms if isinstance(geom, MultiPolygon) else [])
    for part in geoms:
        coords = list(part.exterior.coords)
        for (x1, y1), (x2, y2) in zip(coords[:-1], coords[1:]):
            if abs(x1 - x2) > tol and abs(y1 - y2) > tol:
                return False
        for ring in part.interiors:
            coords = list(ring.coords)
            for (x1, y1), (x2, y2) in zip(coords[:-1], coords[1:]):
                if abs(x1 - x2) > tol and abs(y1 - y2) > tol:
                    return False
    return True


def apply_safety_margin(
    geom: Union[Polygon, MultiPolygon],
    margin: float,
    delta: float,
    join_style: str = "mitre",
) -> Union[Polygon, MultiPolygon]:
    """
    Apply continuous precision safety buffering / morphological dilation.

    When margin == 0.0 and geometry is strictly axis-aligned, returns the clean
    unbuffered geometry to permit exact edge-to-edge sheet abutment and bin-filling pieces.
    When margin == 0.0 and geometry is non-axis-aligned, applies a sub-pixel precision
    safety buffer epsilon = (sqrt(2) / 2.0) * delta to prevent discrete raster aliasing.
    When margin > 0.0, computes epsilon = max(margin / 2.0, (sqrt(2) / 2.0) * delta)
    and expands the outer boundary while contracting interior holes.

    Parameters
    ----------
    geom : Union[Polygon, MultiPolygon]
        The continuous Shapely geometry.
    margin : float
        Desired part-to-part clearance in mm (>= 0.0).
    delta : float
        Spatial resolution in mm (> 0.0).
    join_style : str, optional
        Buffer join style: 'mitre' (default) or 'round'.

    Returns
    -------
    Union[Polygon, MultiPolygon]
        Topologically sanitized buffered geometry.
    """
    clean_geom = validate_and_sanitize(geom)
    if margin <= 0.0:
        if is_axis_aligned(clean_geom):
            return clean_geom
        epsilon = (math.sqrt(2.0) / 2.0) * delta
    else:
        epsilon = compute_safety_margin_distance(margin, delta)

    style_val = 2 if join_style.lower() == "mitre" else 1
    buffered = clean_geom.buffer(epsilon, join_style=style_val)
    return validate_and_sanitize(buffered)


def recover_continuous_polygon(
    poly: Union[Polygon, MultiPolygon],
    col: int,
    row: int,
    delta: float,
    origin_offset: Tuple[float, float] = (0.0, 0.0),
    buf_offset: Tuple[float, float] = (0.0, 0.0),
) -> Union[Polygon, MultiPolygon]:
    """
    Recover continuous Euclidean coordinates for a placed polygon using:
        t_x = col * delta - origin_offset[0] - buf_offset[0]
        t_y = row * delta - origin_offset[1] - buf_offset[1]

    Parameters
    ----------
    poly : Union[Polygon, MultiPolygon]
        The geometry to position.
    col : int
        Grid column placement index (x-axis).
    row : int
        Grid row placement index (y-axis).
    delta : float
        Grid resolution in mm (> 0.0).
    origin_offset : Tuple[float, float], optional
        (x_min, y_min) offset. Defaults to (0.0, 0.0).
    buf_offset : Tuple[float, float], optional
        (buf_minx, buf_miny) offset of safety buffered kernel. Defaults to (0.0, 0.0).

    Returns
    -------
    Union[Polygon, MultiPolygon]
        Translated Shapely polygon at continuous sheet position.
    """
    if delta <= 0.0:
        raise ValueError(f"delta must be strictly positive (> 0.0), got {delta}")

    tx = col * delta - origin_offset[0] - buf_offset[0]
    ty = row * delta - origin_offset[1] - buf_offset[1]
    return affinity.translate(poly, tx, ty)


def place_polygon(
    geom: Union[Polygon, MultiPolygon],
    angle: float,
    col: int,
    row: int,
    delta: float,
    origin_offset: Optional[Tuple[float, float]] = None,
    buf_offset: Tuple[float, float] = (0.0, 0.0),
) -> Union[Polygon, MultiPolygon]:
    """
    High-level convenience function: rotates and translates an original polygon
    to its continuous placed position on the sheet.

    Parameters
    ----------
    geom : Union[Polygon, MultiPolygon]
        The original unrotated, unshifted polygon.
    angle : float
        Rotation angle in degrees.
    col : int
        Discrete grid column placement index.
    row : int
        Discrete grid row placement index.
    delta : float
        Grid resolution in mm.
    origin_offset : Optional[Tuple[float, float]], optional
        Pre-computed (minx, miny) of rotated geometry. If None, computed automatically.
    buf_offset : Tuple[float, float], optional
        (buf_minx, buf_miny) offset of safety buffered kernel. Defaults to (0.0, 0.0).

    Returns
    -------
    Union[Polygon, MultiPolygon]
        The final placed continuous Shapely geometry.
    """
    norm_angle = angle % 360.0
    if abs(norm_angle) > 1e-9:
        rotated = affinity.rotate(geom, norm_angle, origin=(0.0, 0.0))
    else:
        rotated = geom

    if origin_offset is None:
        minx, miny, _, _ = rotated.bounds
    else:
        minx, miny = origin_offset[0], origin_offset[1]

    tx = col * delta - minx - buf_offset[0]
    ty = row * delta - miny - buf_offset[1]
    return affinity.translate(rotated, tx, ty)
