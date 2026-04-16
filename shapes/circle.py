"""Класс для представления окружности"""
import math
from typing import List, Tuple, Optional
from .base import Shape
from core import format_number


class Circle(Shape):
    """Класс окружности"""
    
    def __init__(self, cx: float, cy: float, radius: float):
        super().__init__()
        self.cx = cx
        self.cy = cy
        self.radius = max(0.1, radius)
    
    @classmethod
    def from_two_points(cls, x1: float, y1: float, x2: float, y2: float) -> 'Circle':
        """Создание по двум точкам (диаметр)"""
        return cls((x1 + x2) / 2, (y1 + y2) / 2, math.hypot(x2 - x1, y2 - y1) / 2)
    
    @classmethod
    def from_three_points(cls, x1: float, y1: float, x2: float, y2: float, 
                          x3: float, y3: float) -> Optional['Circle']:
        """Создание по трём точкам на окружности"""
        d = 2 * (x1 * (y2 - y3) + x2 * (y3 - y1) + x3 * (y1 - y2))
        if abs(d) < 1e-10:
            return None
        
        ux = ((x1*x1 + y1*y1) * (y2 - y3) + (x2*x2 + y2*y2) * (y3 - y1) + (x3*x3 + y3*y3) * (y1 - y2)) / d
        uy = ((x1*x1 + y1*y1) * (x3 - x2) + (x2*x2 + y2*y2) * (x1 - x3) + (x3*x3 + y3*y3) * (x2 - x1)) / d
        
        return cls(ux, uy, math.hypot(x1 - ux, y1 - uy))
    
    def draw(self, renderer, width: int, height: int, view_transform, point_radius: int = 4) -> None:
        line_width, dash_pattern, line_type, style = self._get_style_draw_params(renderer)
        
        color = "#55ff55" if self.selected else self.color
        if self.selected:
            line_width += 1
        
        contour_points = []
        for i in range(64):
            angle = 2.0 * math.pi * i / 64.0
            wx = self.cx + self.radius * math.cos(angle)
            wy = self.cy + self.radius * math.sin(angle)
            contour_points.append(view_transform.world_to_screen(wx, wy, width, height))

        self._draw_styled_screen_path(
            renderer,
            contour_points,
            color,
            line_width,
            dash_pattern,
            line_type,
            style,
            closed=True,
            smooth=True
        )

        scx, scy = view_transform.world_to_screen(self.cx, self.cy, width, height)
        renderer.canvas.create_oval(scx - point_radius, scy - point_radius,
                                    scx + point_radius, scy + point_radius,
                                    fill=color, outline="", tags="shape")
    
    def distance_to_point(self, px: float, py: float, width: int, height: int, view_transform) -> float:
        scx, scy = view_transform.world_to_screen(self.cx, self.cy, width, height)
        return abs(math.hypot(px - scx, py - scy) - self.radius * view_transform.scale)
    
    def get_info(self, is_degrees: bool = True) -> str:
        fn = format_number
        return (f"Окружность:\n"
                f"  Центр: ({fn(self.cx)}, {fn(self.cy)})\n"
                f"  Радиус: {fn(self.radius)}\n"
                f"  Диаметр: {fn(self.radius * 2)}\n"
                f"  Длина: {fn(2 * math.pi * self.radius)}\n"
                f"  Площадь: {fn(math.pi * self.radius ** 2)}")
    
    def get_bounds(self) -> Tuple[float, float, float, float]:
        return (self.cx - self.radius, self.cy - self.radius,
                self.cx + self.radius, self.cy + self.radius)
    
    def translate(self, dx: float, dy: float) -> None:
        self.cx += dx
        self.cy += dy
    
    def get_snap_points(self) -> List[Tuple[str, float, float]]:
        return [('center', self.cx, self.cy),
                ('quadrant', self.cx + self.radius, self.cy),
                ('quadrant', self.cx - self.radius, self.cy),
                ('quadrant', self.cx, self.cy + self.radius),
                ('quadrant', self.cx, self.cy - self.radius)]
    
    def get_control_points(self) -> List[Tuple[str, float, float]]:
        return [('center', self.cx, self.cy), ('radius', self.cx + self.radius, self.cy)]
    
    def move_control_point(self, point_id: str, new_x: float, new_y: float) -> None:
        if point_id == 'center':
            self.cx, self.cy = new_x, new_y
        elif point_id == 'radius':
            self.radius = max(0.1, math.hypot(new_x - self.cx, new_y - self.cy))
    
    def to_dict(self) -> dict:
        return {'id': self.id, 'type': 'circle', 'cx': self.cx, 'cy': self.cy, 'radius': self.radius,
                'color': self.color, 'line_style_name': self.line_style_name}
    
    @staticmethod
    def from_dict(data: dict) -> 'Circle':
        circle = Circle(data['cx'], data['cy'], data['radius'])
        circle.color = data.get('color', circle.color)
        circle.line_style_name = data.get('line_style_name', circle.line_style_name)
        circle.id = data.get('id', circle.id)
        return circle
    
    def __repr__(self) -> str:
        return f"Circle({self.cx:.1f}, {self.cy:.1f}, r={self.radius:.1f})"
