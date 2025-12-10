"""Класс для представления сплайна (Катмулла-Рома)"""
import math
from typing import List, Tuple
from .base import Shape
from core import format_number


class Spline(Shape):
    """Класс сплайна Катмулла-Рома"""
    
    def __init__(self, points: List[Tuple[float, float]] = None, tension: float = 0.5):
        super().__init__()
        self.points = points if points else []
        self.tension = max(0, min(1, tension))
    
    def add_point(self, x: float, y: float) -> None:
        self.points.append((x, y))
    
    def remove_point(self, index: int) -> bool:
        if 0 <= index < len(self.points) and len(self.points) > 2:
            self.points.pop(index)
            return True
        return False
    
    def move_point(self, index: int, x: float, y: float) -> bool:
        if 0 <= index < len(self.points):
            self.points[index] = (x, y)
            return True
        return False
    
    def _catmull_rom(self, p0, p1, p2, p3, t: float) -> Tuple[float, float]:
        t2, t3 = t * t, t * t * t
        a = self.tension
        
        def calc(i):
            return ((-a*p0[i] + (2-a)*p1[i] + (a-2)*p2[i] + a*p3[i]) * t3 +
                    (2*a*p0[i] + (a-3)*p1[i] + (3-2*a)*p2[i] - a*p3[i]) * t2 +
                    (-a*p0[i] + a*p2[i]) * t + p1[i])
        return (calc(0), calc(1))
    
    def get_curve_points(self, segments: int = 20) -> List[Tuple[float, float]]:
        if len(self.points) < 2:
            return list(self.points)
        if len(self.points) == 2:
            return list(self.points)
        
        curve = []
        n = len(self.points)
        for i in range(n - 1):
            p0, p1 = self.points[max(0, i-1)], self.points[i]
            p2, p3 = self.points[min(n-1, i+1)], self.points[min(n-1, i+2)]
            for j in range(segments):
                curve.append(self._catmull_rom(p0, p1, p2, p3, j / segments))
        curve.append(self.points[-1])
        return curve
    
    def get_length(self) -> float:
        pts = self.get_curve_points()
        return sum(math.hypot(pts[i+1][0] - pts[i][0], pts[i+1][1] - pts[i][1])
                   for i in range(len(pts) - 1)) if len(pts) >= 2 else 0
    
    def draw(self, renderer, width: int, height: int, view_transform, point_radius: int = 4) -> None:
        color = "#55ff55" if self.selected else self.color
        
        if len(self.points) < 2:
            for px, py in self.points:
                sx, sy = view_transform.world_to_screen(px, py, width, height)
                renderer.canvas.create_oval(sx - point_radius, sy - point_radius,
                                            sx + point_radius, sy + point_radius,
                                            fill=color, outline="", tags="shape")
            return
        
        line_width = 3
        dash_pattern = None
        if hasattr(renderer, 'style_manager') and renderer.style_manager:
            style = renderer.style_manager.get_style(self.line_style_name)
            if style:
                line_width = renderer.style_manager.mm_to_pixels(style.thickness_mm)
                dash_pattern = style.get_dash_pattern()
        if self.selected:
            line_width += 1
        
        screen_pts = []
        for px, py in self.get_curve_points():
            sx, sy = view_transform.world_to_screen(px, py, width, height)
            screen_pts.extend([sx, sy])
        
        if len(screen_pts) >= 4:
            renderer.canvas.create_line(*screen_pts, fill=color, width=line_width,
                                        dash=dash_pattern, smooth=True, tags="shape")
        
        for i, (px, py) in enumerate(self.points):
            sx, sy = view_transform.world_to_screen(px, py, width, height)
            r = point_radius + 1 if i in (0, len(self.points)-1) else point_radius - 1
            renderer.canvas.create_oval(sx - r, sy - r, sx + r, sy + r,
                                        fill=color, outline="#fff" if self.selected else "", tags="shape")
    
    def distance_to_point(self, px: float, py: float, width: int, height: int, view_transform) -> float:
        pts = self.get_curve_points()
        if len(pts) < 2:
            if self.points:
                sx, sy = view_transform.world_to_screen(self.points[0][0], self.points[0][1], width, height)
                return math.hypot(px - sx, py - sy)
            return float('inf')
        
        min_dist = float('inf')
        for i in range(len(pts) - 1):
            sx1, sy1 = view_transform.world_to_screen(pts[i][0], pts[i][1], width, height)
            sx2, sy2 = view_transform.world_to_screen(pts[i+1][0], pts[i+1][1], width, height)
            dx, dy = sx2 - sx1, sy2 - sy1
            len2 = dx*dx + dy*dy
            t = max(0, min(1, ((px-sx1)*dx + (py-sy1)*dy) / len2)) if len2 > 0 else 0
            min_dist = min(min_dist, math.hypot(px - (sx1 + t*dx), py - (sy1 + t*dy)))
        return min_dist
    
    def get_info(self, is_degrees: bool = True) -> str:
        fn = format_number
        info = f"Сплайн:\n  Точек: {len(self.points)}\n  Натяжение: {fn(self.tension)}\n  Длина: {fn(self.get_length())}"
        if self.points:
            info += "\n  Точки:"
            for i, (px, py) in enumerate(self.points):
                info += f"\n    {i+1}: ({fn(px)}, {fn(py)})"
        return info
    
    def get_bounds(self) -> Tuple[float, float, float, float]:
        pts = self.get_curve_points() or self.points
        if not pts:
            return (0, 0, 0, 0)
        return (min(p[0] for p in pts), min(p[1] for p in pts),
                max(p[0] for p in pts), max(p[1] for p in pts))
    
    def translate(self, dx: float, dy: float) -> None:
        self.points = [(x + dx, y + dy) for x, y in self.points]
    
    def get_snap_points(self) -> List[Tuple[str, float, float]]:
        return [('endpoint' if i in (0, len(self.points)-1) else 'control', px, py)
                for i, (px, py) in enumerate(self.points)]
    
    def get_control_points(self) -> List[Tuple[str, float, float]]:
        return [(f'point_{i}', px, py) for i, (px, py) in enumerate(self.points)]
    
    def move_control_point(self, point_id: str, new_x: float, new_y: float) -> None:
        if point_id.startswith('point_'):
            try:
                self.move_point(int(point_id.split('_')[1]), new_x, new_y)
            except (ValueError, IndexError):
                pass
    
    def to_dict(self) -> dict:
        return {'type': 'spline', 'points': self.points, 'tension': self.tension,
                'color': self.color, 'line_style_name': self.line_style_name}
    
    @staticmethod
    def from_dict(data: dict) -> 'Spline':
        spline = Spline([tuple(p) for p in data.get('points', [])], data.get('tension', 0.5))
        spline.color = data.get('color', spline.color)
        spline.line_style_name = data.get('line_style_name', spline.line_style_name)
        return spline
    
    def __repr__(self) -> str:
        return f"Spline({len(self.points)} pts)"
