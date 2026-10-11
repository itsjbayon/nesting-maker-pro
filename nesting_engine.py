import os
import math
from svgpathtools import svg2paths, wsvg, parse_path
from svgpathtools.path import transform as svg_transform
from svgpathtools.parser import parse_transform
from PyQt6.QtGui import QPainterPath, QTransform
from PyQt6.QtCore import QPointF
from shapely.geometry import Polygon, MultiPolygon
import shapely.affinity as affinity
from shapely.validation import make_valid

# Importamos el nuevo RasterNestingEngine de la carpeta raster_engine_v2
from raster_engine_v2.engine import RasterNestingEngine

class NestingEngine:
    def __init__(self):
        self.pieces = [] 
        self.quantities = {}
        self.material_w = 1200
        self.material_h = 600
        self.result_paths = []
        self.result_attributes = []
        
        self.margin = 5.0
        self.rotation_mode = 1 # 0: None, 1: 90/180, 2: Free

    def set_material_size(self, w, h):
        self.material_w = w
        self.material_h = h
        
    def set_quantities(self, qty_dict):
        self.quantities = qty_dict
        
    def set_nesting_options(self, margin, rotation_mode):
        self.margin = margin
        self.rotation_mode = rotation_mode

    def _convert_to_qpath(self, svg_path):
        qpath = QPainterPath()
        if len(svg_path) == 0: return qpath
        
        for subpath in svg_path.continuous_subpaths():
            if len(subpath) == 0: continue
            
            # Levanta el lápiz y va al inicio del nuevo sub-trazo
            start = subpath[0].start
            qpath.moveTo(start.real, start.imag)
            
            for seg in subpath:
                name = type(seg).__name__
                if name == 'Line':
                    qpath.lineTo(seg.end.real, seg.end.imag)
                elif name == 'CubicBezier':
                    qpath.cubicTo(seg.control1.real, seg.control1.imag,
                                  seg.control2.real, seg.control2.imag,
                                  seg.end.real, seg.end.imag)
                elif name == 'QuadraticBezier':
                    qpath.quadTo(seg.control.real, seg.control.imag,
                                 seg.end.real, seg.end.imag)
                else:
                    num = 20
                    for j in range(1, num + 1):
                        pt = seg.point(j / float(num))
                        qpath.lineTo(pt.real, pt.imag)
            if subpath.isclosed():
                qpath.closeSubpath()
                    
        return qpath

    def _extract_shapely_polygon(self, svg_path):
        """
        Analiza un path SVG (que puede ser un trayecto combinado con múltiples islas o huecos).
        Extrae todos los sub-trazos cerrados, determina la topología jerárquica de contornos exteriores
        e interiores (islas y huecos), y devuelve un Polygon o MultiPolygon topológicamente válido.
        """
        subpaths_points = []
        
        for sp in svg_path.continuous_subpaths():
            if len(sp) == 0:
                continue
            pts = [(sp[0].start.real, sp[0].start.imag)]
            for seg in sp:
                name = type(seg).__name__
                if name == 'Line':
                    pts.append((seg.end.real, seg.end.imag))
                else:
                    num = 30
                    for j in range(1, num + 1):
                        pt = seg.point(j / float(num))
                        pts.append((pt.real, pt.imag))
            
            if len(pts) >= 3:
                poly = Polygon(pts)
                if not poly.is_valid:
                    poly = make_valid(poly)
                if poly.is_empty:
                    continue
                if poly.geom_type == 'Polygon' and poly.area > 1e-6:
                    subpaths_points.append(poly)
                elif poly.geom_type in ('MultiPolygon', 'GeometryCollection'):
                    for sub in poly.geoms:
                        if sub.geom_type == 'Polygon' and sub.area > 1e-6:
                            subpaths_points.append(sub)
                
        if not subpaths_points: 
            return None
        
        # Ordenamos de mayor a menor área para clasificar envolventes exteriores y huecos
        subpaths_points.sort(key=lambda p: p.area, reverse=True)
        
        shells = []  # [{'poly': p, 'holes': [], 'index': i}]
        for i, p in enumerate(subpaths_points):
            enclosing = [
                j for j in range(i)
                if subpaths_points[j].covers(p) or (subpaths_points[j].intersection(p).area / p.area > 0.95)
            ]
            depth = len(enclosing)
            if depth % 2 == 0:
                # Contorno exterior sólido o isla interior a nivel par
                shells.append({'poly': p, 'holes': [], 'index': i})
            else:
                # Hueco interior: pertenece a su envolvente directa
                parent_idx = enclosing[-1]
                for s in reversed(shells):
                    if s['index'] == parent_idx:
                        s['holes'].append(list(p.exterior.coords))
                        break
                        
        result_polys = []
        for s in shells:
            poly = Polygon(s['poly'].exterior.coords, holes=s['holes'])
            if not poly.is_valid:
                poly = make_valid(poly)
            if poly.is_empty:
                continue
            if poly.geom_type == 'Polygon' and poly.area > 1e-6:
                result_polys.append(poly)
            elif poly.geom_type in ('MultiPolygon', 'GeometryCollection'):
                for sub in poly.geoms:
                    if sub.geom_type == 'Polygon' and sub.area > 1e-6:
                        result_polys.append(sub)

        if not result_polys:
            return None
        if len(result_polys) == 1:
            return result_polys[0]
        return MultiPolygon(result_polys)

    def clear_pieces(self):
        self.pieces = []
        self.quantities = {}
        self.result_paths = []
        self.result_attributes = []

    def load_multiple_svgs(self, filepaths, append=True):
        if not append:
            self.clear_pieces()
        success_any = False
        for fp in filepaths:
            if self.load_svg(fp, append=True):
                success_any = True
        return success_any

    def load_svg(self, filepath, append=True):
        try:
            if not append:
                self.clear_pieces()

            paths = []
            attributes = []
            
            # Prefer SaxDocument to correctly flatten <g transform="..."> groups and parse standard shapes
            try:
                from svgpathtools.svg_io_sax import SaxDocument
                doc = SaxDocument(filepath)
                for item in doc.tree:
                    if 'd' in item:
                        p = parse_path(item['d'])
                        mat = item.get('matrix')
                        if mat is not None:
                            p = svg_transform(p, mat)
                        cleaned_attr = {k: v for k, v in item.items() if k not in ('matrix', 'transform', 'd')}
                        paths.append(p)
                        attributes.append(cleaned_attr)
            except Exception:
                pass
            
            # Fallback to standard svg2paths if SaxDocument produced no paths
            if not paths:
                raw_paths, raw_attrs = svg2paths(filepath)
                for p, a in zip(raw_paths, raw_attrs):
                    if 'transform' in a and a['transform']:
                        try:
                            mat = parse_transform(a['transform'])
                            p = svg_transform(p, mat)
                        except Exception:
                            pass
                    ca = {k: v for k, v in a.items() if k not in ('matrix', 'transform')}
                    paths.append(p)
                    attributes.append(ca)

            source_name = os.path.basename(filepath)
            for i, path in enumerate(paths):
                try:
                    xmin, xmax, ymin, ymax = path.bbox()
                except Exception:
                    continue # ignorar paths vacíos
                    
                w = xmax - xmin
                h = ymax - ymin
                if w <= 0 or h <= 0:
                    continue
                
                # Normalizamos
                norm_path = path.translated(complex(-xmin, -ymin))
                shapely_poly = self._extract_shapely_polygon(norm_path)
                
                attr = attributes[i] if i < len(attributes) else {}
                
                if shapely_poly and shapely_poly.is_valid and shapely_poly.area > 1e-6:
                    sp_minx, sp_miny, _, _ = shapely_poly.bounds
                    # Only shift if coordinates are negative, to guard against escaping into negative space
                    shift_x = -sp_minx if sp_minx < -1e-9 else 0.0
                    shift_y = -sp_miny if sp_miny < -1e-9 else 0.0
                    if shift_x != 0.0 or shift_y != 0.0:
                        shapely_poly = affinity.translate(shapely_poly, shift_x, shift_y)
                        norm_path = norm_path.translated(complex(shift_x, shift_y))

                    base_qpath = self._convert_to_qpath(norm_path)
                    piece_id = len(self.pieces)

                    self.pieces.append({
                        'id': piece_id,
                        'svg_path': norm_path,
                        'qpath': base_qpath,
                        'shapely_poly': shapely_poly,
                        'attributes': attr,
                        'width': w,
                        'height': h,
                        'source_file': source_name
                    })
            return True
        except Exception as e:
            return False

    def get_placed_piece(self, piece, x_offset, y_offset, rotation_deg=0):
        # 1. Gráfico
        transform = QTransform()
        # En Qt, las transformaciones se aplican en orden inverso a como se escriben.
        # Queremos: Rotar en (0,0) -> luego trasladar. Se escribe primero translate y luego rotate.
        transform.translate(x_offset, y_offset)
        transform.rotate(rotation_deg)
        final_qpath = transform.map(piece['qpath'])
        
        # 2. Matemático
        # SVG path rotated sobre origin 0,0 y luego traslación
        final_svg_path = piece['svg_path'].rotated(rotation_deg, origin=0).translated(complex(x_offset, y_offset))
        
        return final_qpath, final_svg_path

    def run_nesting(self):
        self.result_paths = []
        self.result_attributes = []
        display_qpaths = []

        items_with_pid = []
        
        for pid, qty in self.quantities.items():
            if qty > 0:
                poly = self.pieces[pid]['shapely_poly']
                for _ in range(qty):
                    items_with_pid.append((pid, poly))
                    
        if not items_with_pid:
            return []
            
        shapes_only = [item[1] for item in items_with_pid]

        rotations = [0]
        if self.rotation_mode == 1:
            rotations = [0, 90, 180, 270]
        elif self.rotation_mode == 2:
            rotations = [0, 45, 90, 135, 180, 225, 270, 315]
            
        try:
            # Motor Raster v2.0
            engine = RasterNestingEngine(
                bin_width=self.material_w,
                bin_height=self.material_h,
                resolution=2.0, 
                margin=self.margin,
                allowed_rotations=rotations
            )
            
            engine.add_shapes(shapes_only)
            engine.nest()
            
            placements = engine.get_placements()
            
            if not placements:
                return []
                
            for sol_item in placements:
                original_piece_id = items_with_pid[sol_item.original_index][0]
                piece = self.pieces[original_piece_id]
                
                # RasterNestingEngine devuelve position como (x, y) y rotation
                qpath, final_svg_path = self.get_placed_piece(
                    piece, 
                    x_offset=sol_item.position[0], 
                    y_offset=sol_item.position[1], 
                    rotation_deg=sol_item.rotation
                )
                
                display_qpaths.append(qpath)
                self.result_paths.append(final_svg_path)
                self.result_attributes.append(piece['attributes'])
                
            return display_qpaths
        except Exception as e:
            print("Error Raster Nesting:", e)
            return []

    def export_svg(self, filename):
        if not self.result_paths: return False
            
        svg_attributes = {
            'width': f"{self.material_w}mm",
            'height': f"{self.material_h}mm",
            'viewBox': f"0 0 {self.material_w} {self.material_h}"
        }
        
        try:
            cleaned_result_attributes = []
            for a in self.result_attributes:
                ca = {k: v for k, v in a.items() if k not in ('transform', 'matrix')}
                cleaned_result_attributes.append(ca)

            wsvg(paths=self.result_paths, 
                 attributes=cleaned_result_attributes,
                 svg_attributes=svg_attributes,
                 filename=filename)
            return True
        except Exception as e:
            print(f"Error Exporting SVG: {e}")
            return False
