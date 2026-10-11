"""
raster_engine_v2.engine
=======================
True-Shape Raster Nesting Engine Coordinator.

Coordinates geometry sanitization, rotational kernel caching,
BLF packing on discrete 2D boolean grids, and layout metrics computation.
"""

from typing import List, Optional, Sequence, Tuple, Union, Any, Dict
from shapely.geometry import Polygon, MultiPolygon

from .packer import BLFPacker, PlacementInfo


class RasterNestingEngine:
    """
    True-Shape Raster Nesting Engine Coordinator.

    Provides a comprehensive facade for 2D irregular nesting using boolean grid
    matrices and FFT cross-correlation collision detection.
    """

    def __init__(
        self,
        bin_size: Optional[Tuple[float, float]] = None,
        bin_width: Optional[float] = None,
        bin_height: Optional[float] = None,
        resolution: float = 1.0,
        margin: float = 2.0,
        allowed_rotations: Optional[Sequence[float]] = None,
        sort_by_area: bool = True,
        cell_size_mm: Optional[float] = None,
        margin_mm: Optional[float] = None,
        rotation_step_deg: Optional[float] = None,
        **kwargs: Any,
    ):
        """
        Initializes the nesting engine coordinator.

        Parameters
        ----------
        bin_size : Optional[Tuple[float, float]], optional
            Bin dimensions as (width, height) in millimeters.
        bin_width : Optional[float], optional
            Bin width in millimeters.
        bin_height : Optional[float], optional
            Bin height in millimeters.
        resolution : float, optional
            Grid cell spatial resolution Delta in mm (default: 1.0).
        margin : float, optional
            Inter-piece clearance in mm (default: 2.0).
        allowed_rotations : Optional[Sequence[float]], optional
            Allowed rotation angles in degrees (default: [0, 90, 180, 270]).
        sort_by_area : bool, optional
            Whether to pre-sort input pieces by descending area (default: True).
        cell_size_mm : Optional[float], optional
            Alias for resolution.
        margin_mm : Optional[float], optional
            Alias for margin.
        rotation_step_deg : Optional[float], optional
            Step angle in degrees to generate allowed rotations (e.g., 90 -> [0, 90, 180, 270]).
        """
        # Resolve dimensions
        if bin_size is not None:
            w, h = float(bin_size[0]), float(bin_size[1])
        elif bin_width is not None and bin_height is not None:
            w, h = float(bin_width), float(bin_height)
        else:
            w, h = 1200.0, 600.0

        self.bin_width: float = w
        self.bin_height: float = h
        self.bin_size: Tuple[float, float] = (w, h)

        # Resolve resolution
        if cell_size_mm is not None:
            self.resolution = float(cell_size_mm)
        else:
            self.resolution = float(resolution)

        # Resolve margin
        if margin_mm is not None:
            self.margin = float(margin_mm)
        else:
            self.margin = float(margin)

        # Resolve rotations
        if rotation_step_deg is not None and rotation_step_deg > 0:
            steps = int(round(360.0 / rotation_step_deg))
            self.allowed_rotations: List[float] = [float(i * rotation_step_deg) for i in range(steps)]
        elif allowed_rotations is not None:
            self.allowed_rotations = [float(a) for a in allowed_rotations]
        else:
            self.allowed_rotations = [0.0, 90.0, 180.0, 270.0]

        self.sort_by_area: bool = sort_by_area

        self.shapes: List[Union[Polygon, MultiPolygon]] = []
        self.placements: List[PlacementInfo] = []
        self.unplaced: List[Union[Polygon, MultiPolygon]] = []
        self._packer: Optional[BLFPacker] = None

    def set_bin(self, width: float, height: float) -> None:
        """
        Sets or updates rectangular bin sheet dimensions (mm).

        Parameters
        ----------
        width : float
            Bin width along X (mm).
        height : float
            Bin height along Y (mm).
        """
        if width <= 0 or height <= 0:
            raise ValueError(f"Bin dimensions must be strictly positive: got width={width}, height={height}")
        self.bin_width = float(width)
        self.bin_height = float(height)
        self.bin_size = (self.bin_width, self.bin_height)

    def add_shapes(self, shapes: Sequence[Union[Polygon, MultiPolygon]]) -> None:
        """Appends a sequence of Shapely Polygons to the piece queue."""
        for s in shapes:
            self.shapes.append(s)

    def add_shape(self, shape: Union[Polygon, MultiPolygon], quantity: int = 1) -> None:
        """Appends a single Shapely Polygon with optional quantity replication."""
        if quantity < 1:
            return
        for _ in range(quantity):
            self.shapes.append(shape)

    def add_polygon(self, poly: Union[Polygon, MultiPolygon]) -> None:
        """Appends a single polygon to the queue."""
        self.shapes.append(poly)

    def clear(self) -> None:
        """Clears queued shapes, placements, and unplaced items."""
        self.shapes.clear()
        self.placements.clear()
        self.unplaced.clear()
        self._packer = None

    def nest(
        self,
        shapes: Optional[Sequence[Union[Polygon, MultiPolygon]]] = None,
    ) -> List[Union[Polygon, MultiPolygon]]:
        """
        Executes true-shape raster nesting.

        Parameters
        ----------
        shapes : Optional[Sequence[Union[Polygon, MultiPolygon]]], optional
            Shapes to nest. If provided, overrides existing queue.

        Returns
        -------
        List[Union[Polygon, MultiPolygon]]
            List of successfully placed transformed Shapely geometries with
            strictly zero pairwise overlap.
        """
        if shapes is not None:
            self.shapes = list(shapes)

        if not self.shapes:
            self.placements = []
            self.unplaced = []
            return []

        self._packer = BLFPacker(
            bin_width=self.bin_width,
            bin_height=self.bin_height,
            resolution=self.resolution,
            margin=self.margin,
            allowed_rotations=self.allowed_rotations,
        )

        self.placements = self._packer.pack(self.shapes, sort_by_area=self.sort_by_area)
        self.unplaced = [shape for _, shape in self._packer.unplaced_items]

        return [p.polygon for p in self.placements]

    def solve(
        self,
        shapes: Optional[Sequence[Union[Polygon, MultiPolygon]]] = None,
    ) -> List[Union[Polygon, MultiPolygon]]:
        """Alias for nest()."""
        return self.nest(shapes)

    def compute_density(self) -> float:
        """
        Computes sheet packing density (utilization ratio):
        total placed parts solid area / bin area.

        Returns
        -------
        float
            Utilization ratio in [0.0, 1.0].
        """
        bin_area = self.bin_width * self.bin_height
        if bin_area <= 0:
            return 0.0
        total_placed_area = sum(p.polygon.area for p in self.placements)
        return float(total_placed_area / bin_area)

    def get_placements(self) -> List[PlacementInfo]:
        """Returns the list of PlacementInfo records with detailed metadata."""
        return list(self.placements)

    def get_unplaced(self) -> List[Union[Polygon, MultiPolygon]]:
        """Returns list of shapes that could not fit into the bin."""
        return list(self.unplaced)
