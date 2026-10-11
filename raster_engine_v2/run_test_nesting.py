import sys
import os
import time
from shapely.geometry import Polygon
import matplotlib.pyplot as plt

# Import the engine
try:
    from raster_engine_v2.engine import RasterNestingEngine
except ImportError:
    # If run directly from raster_engine_v2 directory
    from engine import RasterNestingEngine

def create_test_shapes():
    shapes = []
    
    # 1. Large rectangle with a big hole in the center
    # Exterior: 0,0 to 200,200
    # Hole: 50,50 to 150,150
    outer = [(0, 0), (200, 0), (200, 200), (0, 200)]
    inner = [(50, 50), (50, 150), (150, 150), (150, 50)]
    shapes.append(Polygon(outer, holes=[inner]))
    
    # 2. A smaller piece that perfectly fits inside the hole (80x80)
    shapes.append(Polygon([(0, 0), (80, 0), (80, 80), (0, 80)]))
    
    # 3. An L-shape piece
    shapes.append(Polygon([(0, 0), (100, 0), (100, 30), (30, 30), (30, 100), (0, 100)]))
    
    # 4. A triangle
    shapes.append(Polygon([(0, 0), (120, 0), (60, 90)]))
    
    # 5. A cross shape
    cross_pts = [
        (30, 0), (60, 0), (60, 30), (90, 30), (90, 60),
        (60, 60), (60, 90), (30, 90), (30, 60), (0, 60),
        (0, 30), (30, 30)
    ]
    shapes.append(Polygon(cross_pts))
    
    return shapes

def verify_zero_overlap(placed_shapes):
    print("Verifying zero overlap between placed shapes...")
    for i in range(len(placed_shapes)):
        for j in range(i + 1, len(placed_shapes)):
            intersection = placed_shapes[i].intersection(placed_shapes[j])
            # Account for floating point rounding at the borders (a very small threshold)
            if intersection.area > 1e-3:
                print(f"FAILED: Overlap detected between piece {i} and {j}. Area = {intersection.area}")
                return False
    print("SUCCESS: Zero overlap confirmed.")
    return True

def verify_bin_containment(placed_shapes, bin_w, bin_h):
    print(f"Verifying all shapes are within the {bin_w}x{bin_h} bin...")
    bin_polygon = Polygon([(0, 0), (bin_w, 0), (bin_w, bin_h), (0, bin_h)])
    for i, shape in enumerate(placed_shapes):
        if not bin_polygon.contains(shape.buffer(-1e-3)): # Small buffer for float precision
            print(f"FAILED: Piece {i} is out of bin bounds!")
            return False
    print("SUCCESS: Bin containment confirmed.")
    return True

def plot_shapes(shapes, bin_w, bin_h, filename):
    fig, ax = plt.subplots(figsize=(8, 8))
    ax.set_xlim(0, bin_w)
    ax.set_ylim(0, bin_h)
    ax.set_aspect('equal')
    ax.add_patch(plt.Rectangle((0, 0), bin_w, bin_h, fill=False, color='red', linewidth=2, linestyle='--'))
    
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2']
    
    for i, shape in enumerate(shapes):
        color = colors[i % len(colors)]
        
        # Plot exterior
        x, y = shape.exterior.xy
        ax.plot(x, y, color=color, linewidth=2)
        ax.fill(x, y, alpha=0.5, color=color)
        
        # Plot holes
        for hole in shape.interiors:
            hx, hy = hole.xy
            ax.plot(hx, hy, color='white', linewidth=2)
            ax.fill(hx, hy, alpha=1.0, color='white') # Clear the hole in the plot
            
    plt.title(f"True-Shape Raster Nesting Result ({len(shapes)} pieces)")
    plt.grid(True, alpha=0.3)
    plt.savefig(filename, dpi=300, bbox_inches='tight')
    print(f"Plot saved to {filename}")

def main():
    bin_w, bin_h = 300, 300
    
    print("Initializing Raster Nesting Engine...")
    start_time = time.time()
    
    # We use a relatively large cell_size to keep tests fast, but small enough for precision
    engine = RasterNestingEngine(
        bin_width=bin_w, 
        bin_height=bin_h, 
        resolution=2.0, 
        margin=2.0, 
        allowed_rotations=[0, 90, 180, 270]
    )
    
    shapes = create_test_shapes()
    print(f"Created {len(shapes)} complex shapes for testing.")
    
    engine.add_shapes(shapes)
    
    print("Running nest algorithm...")
    placed = engine.nest()
    elapsed = time.time() - start_time
    print(f"Nesting completed in {elapsed:.2f} seconds. Placed {len(placed)} out of {len(shapes)} shapes.")
    
    assert verify_zero_overlap(placed), "Overlap verification failed!"
    assert verify_bin_containment(placed, bin_w, bin_h), "Containment verification failed!"
    
    output_img = "raster_nesting_result.png"
    plot_shapes(placed, bin_w, bin_h, output_img)
    print("Done!")

if __name__ == "__main__":
    main()
