import sys
import os
import math

# Добавляем путь к корню проекта, чтобы импорты работали
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from exporters.dxf_exporter import DxfExporter
from managers.line_style_manager import LineStyleManager, LineStyle
from shapes.point import Point
from shapes.segment import Segment
from shapes.circle import Circle
from shapes.arc import Arc
from shapes.ellipse import Ellipse
from shapes.polygon import Polygon
from shapes.rectangle import Rectangle
from shapes.spline import Spline

def verify_labs():
    print("Starting Lab 5 & 6 Verification Export...")
    
    style_manager = LineStyleManager()
    exporter = DxfExporter()
    
    shapes = []
    
    # 1. Point
    p = Point(10, 10)
    p.line_style_name = "Сплошная основная"
    shapes.append(p)
    
    # 2. Segment (Line)
    s = Segment(20, 10, 50, 40)
    s.line_style_name = "Штриховая"
    shapes.append(s)
    
    # 3. Circle
    c = Circle(70, 20, 15)
    c.line_style_name = "Сплошная тонкая"
    shapes.append(c)
    
    # 4. Arc
    a = Arc(100, 20, 15, 0, 180) # Semicircle
    a.line_style_name = "Штрихпунктирная тонкая"
    shapes.append(a)
    
    # 5. Ellipse
    e = Ellipse(30, 70, 25, 15, 30) # Rotated ellipse
    e.line_style_name = "Сплошная основная"
    shapes.append(e)
    
    # 6. Polygon
    poly = Polygon(70, 70, 20, num_sides=6) # Hexagon
    poly.line_style_name = "Сплошная основная"
    shapes.append(poly)
    
    # 7. Spline
    pts = [(100, 50), (120, 80), (140, 60), (160, 90)]
    spl = Spline(pts)
    spl.line_style_name = "Сплошная тонкая"
    shapes.append(spl)
    
    # 8. Rectangle (Bonus, usually Polygon in DXF)
    rect = Rectangle(10, 100, 40, 20)
    rect.line_style_name = "Сплошная основная"
    shapes.append(rect)
    
    # 9. Wavy Line (Baked as Bulge Polyline)
    wavy = Segment(60, 100, 140, 100)
    wavy.line_style_name = "Сплошная волнистая"
    shapes.append(wavy)
    
    output_file = "lab_verification.dxf"
    exporter.export(output_file, shapes, style_manager.get_all_styles(), margin=30.0)
    
    if os.path.exists(output_file):
        print(f"Success! {output_file} created with {len(shapes)} shapes.")
        print(f"File size: {os.path.getsize(output_file)} bytes")
    else:
        print("Failed to create DXF file.")

if __name__ == "__main__":
    verify_labs()
