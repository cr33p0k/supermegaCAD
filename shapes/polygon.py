"""Класс для представления правильного многоугольника"""
import math
from typing import List, Tuple
from .base import Shape
from core import format_number


class Polygon(Shape):
    """Класс правильного многоугольника"""
    
    def __init__(self, cx: float, cy: float, radius: float, 
                 num_sides: int = 6, inscribed: bool = True, rotation: float = 0):
        super().__init__()
        self.cx = cx
        self.cy = cy
        self.radius = max(0.1, radius)
        self.num_sides = max(3, num_sides)
        self.inscribed = inscribed
        self.rotation = rotation
    
    def get_effective_radius(self) -> float:
        if self.inscribed:
            return self.radius
        return self.radius / math.cos(math.pi / self.num_sides)
    
    def get_apothem(self) -> float:
        if self.inscribed:
            return self.radius * math.cos(math.pi / self.num_sides)
        return self.radius
    
    def get_vertices(self) -> List[Tuple[float, float]]:
        r = self.get_effective_radius()
        return [(self.cx + r * math.cos(math.radians(self.rotation + i * 360 / self.num_sides)),
                 self.cy + r * math.sin(math.radians(self.rotation + i * 360 / self.num_sides)))
                for i in range(self.num_sides)]
    
    def get_edge_midpoints(self) -> List[Tuple[float, float]]:
        v = self.get_vertices()
        return [((v[i][0] + v[(i+1) % len(v)][0]) / 2,
                 (v[i][1] + v[(i+1) % len(v)][1]) / 2) for i in range(len(v))]
    
    def get_side_length(self) -> float:
        return 2 * self.get_effective_radius() * math.sin(math.pi / self.num_sides)
    
    def draw(self, renderer, width: int, height: int, view_transform, point_radius: int = 4) -> None:
        line_width, dash_pattern, line_type, style = self._get_style_draw_params(renderer)
        
        color = "#55ff55" if self.selected else self.color
        if self.selected:
            line_width += 1
        
        vertices = [view_transform.world_to_screen(v[0], v[1], width, height) for v in self.get_vertices()]
        self._draw_styled_screen_path(
            renderer,
            vertices,
            color,
            line_width,
            dash_pattern,
            line_type,
            style,
            closed=True,
            smooth=False
        )
        
        for sx, sy in vertices:
            renderer.canvas.create_oval(sx - point_radius, sy - point_radius,
                                        sx + point_radius, sy + point_radius,
                                        fill=color, outline="", tags="shape")
        
        scx, scy = view_transform.world_to_screen(self.cx, self.cy, width, height)
        renderer.canvas.create_oval(scx - point_radius, scy - point_radius,
                                    scx + point_radius, scy + point_radius,
                                    fill=color, outline="", tags="shape")
    
    def distance_to_point(self, px: float, py: float, width: int, height: int, view_transform) -> float:
        vertices = [view_transform.world_to_screen(v[0], v[1], width, height) for v in self.get_vertices()]
        
        min_dist = float('inf')
        for i in range(len(vertices)):
            x1, y1 = vertices[i]
            x2, y2 = vertices[(i+1) % len(vertices)]
            dx, dy = x2 - x1, y2 - y1
            len2 = dx*dx + dy*dy
            t = max(0, min(1, ((px-x1)*dx + (py-y1)*dy) / len2)) if len2 > 0 else 0
            min_dist = min(min_dist, math.hypot(px - (x1 + t*dx), py - (y1 + t*dy)))
        return min_dist
    
    def get_info(self, is_degrees: bool = True) -> str:
        fn = format_number
        unit = "°" if is_degrees else " рад"
        rot = self.rotation if is_degrees else math.radians(self.rotation)
        side = self.get_side_length()
        apothem = self.get_apothem()
        
        return (f"Правильный {self.num_sides}-угольник:\n"
                f"  Центр: ({fn(self.cx)}, {fn(self.cy)})\n"
                f"  Тип: {'Вписанный' if self.inscribed else 'Описанный'}\n"
                f"  Радиус: {fn(self.radius)}\n"
                f"  Сторона: {fn(side)}\n"
                f"  Периметр: {fn(side * self.num_sides)}\n"
                f"  Площадь: {fn(0.5 * side * self.num_sides * apothem)}\n"
                f"  Поворот: {fn(rot)}{unit}")
    
    def get_bounds(self) -> Tuple[float, float, float, float]:
        v = self.get_vertices()
        return (min(p[0] for p in v), min(p[1] for p in v),
                max(p[0] for p in v), max(p[1] for p in v))
    
    def translate(self, dx: float, dy: float) -> None:
        self.cx += dx
        self.cy += dy
    
    def get_snap_points(self) -> List[Tuple[str, float, float]]:
        points = [('center', self.cx, self.cy)]
        for v in self.get_vertices():
            points.append(('endpoint', v[0], v[1]))
        for m in self.get_edge_midpoints():
            points.append(('midpoint', m[0], m[1]))
        return points
    
    def get_control_points(self) -> List[Tuple[str, float, float]]:
        v = self.get_vertices()
        return [('center', self.cx, self.cy)] + ([('radius', v[0][0], v[0][1])] if v else [])
    
    def move_control_point(self, point_id: str, new_x: float, new_y: float) -> None:
        if point_id == 'center':
            self.cx, self.cy = new_x, new_y
        elif point_id == 'radius':
            new_r = math.hypot(new_x - self.cx, new_y - self.cy)
            self.radius = new_r if self.inscribed else new_r * math.cos(math.pi / self.num_sides)
            self.rotation = math.degrees(math.atan2(new_y - self.cy, new_x - self.cx))
    
    def to_dict(self) -> dict:
        return {'id': self.id, 'type': 'polygon', 'cx': self.cx, 'cy': self.cy, 'radius': self.radius,
                'num_sides': self.num_sides, 'inscribed': self.inscribed, 'rotation': self.rotation,
                'color': self.color, 'line_style_name': self.line_style_name}
    
    @staticmethod
    def from_dict(data: dict) -> 'Polygon':
        poly = Polygon(data['cx'], data['cy'], data['radius'],
                       data.get('num_sides', 6), data.get('inscribed', True), data.get('rotation', 0))
        poly.color = data.get('color', poly.color)
        poly.line_style_name = data.get('line_style_name', poly.line_style_name)
        poly.id = data.get('id', poly.id)
        return poly
    
    def __repr__(self) -> str:
        return f"Polygon({self.num_sides}, {self.cx:.1f}, {self.cy:.1f})"
