"""Класс для представления эллипса"""
import math
from typing import List, Tuple
from .base import Shape
from core import format_number


class Ellipse(Shape):
    """Класс эллипса"""
    
    def __init__(self, cx: float, cy: float, rx: float, ry: float, rotation: float = 0):
        super().__init__()
        self.cx = cx
        self.cy = cy
        self.rx = max(0.1, abs(rx))
        self.ry = max(0.1, abs(ry))
        self.rotation = rotation
    
    @classmethod
    def from_center_and_axes(cls, cx: float, cy: float, 
                              axis1_x: float, axis1_y: float,
                              axis2_x: float, axis2_y: float) -> 'Ellipse':
        """Создание по центру и конечным точкам осей"""
        rx = math.hypot(axis1_x - cx, axis1_y - cy)
        ry = math.hypot(axis2_x - cx, axis2_y - cy)
        rotation = math.degrees(math.atan2(axis1_y - cy, axis1_x - cx))
        return cls(cx, cy, rx, ry, rotation)
    
    def get_point_on_ellipse(self, angle: float) -> Tuple[float, float]:
        x = self.rx * math.cos(math.radians(angle))
        y = self.ry * math.sin(math.radians(angle))
        rot = math.radians(self.rotation)
        cos_r, sin_r = math.cos(rot), math.sin(rot)
        return (x * cos_r - y * sin_r + self.cx, x * sin_r + y * cos_r + self.cy)
    
    def get_axis_endpoints(self) -> Tuple[Tuple[float, float], ...]:
        rot = math.radians(self.rotation)
        cos_r, sin_r = math.cos(rot), math.sin(rot)
        return ((self.cx + self.rx * cos_r, self.cy + self.rx * sin_r),
                (self.cx - self.rx * cos_r, self.cy - self.rx * sin_r),
                (self.cx - self.ry * sin_r, self.cy + self.ry * cos_r),
                (self.cx + self.ry * sin_r, self.cy - self.ry * cos_r))
    
    def draw(self, renderer, width: int, height: int, view_transform, point_radius: int = 4) -> None:
        line_width, dash_pattern, line_type, style = self._get_style_draw_params(renderer)
        
        color = "#55ff55" if self.selected else self.color
        if self.selected:
            line_width += 1
        
        # Рисуем как полигон из точек
        points = []
        for i in range(64):
            wx, wy = self.get_point_on_ellipse(i * 360 / 64)
            points.append(view_transform.world_to_screen(wx, wy, width, height))

        self._draw_styled_screen_path(
            renderer,
            points,
            color,
            line_width,
            dash_pattern,
            line_type,
            style,
            closed=True,
            smooth=True
        )
        
        # Центр и концы осей
        scx, scy = view_transform.world_to_screen(self.cx, self.cy, width, height)
        renderer.canvas.create_oval(scx - point_radius, scy - point_radius,
                                    scx + point_radius, scy + point_radius,
                                    fill=color, outline="", tags="shape")
        
        for ax, ay in self.get_axis_endpoints():
            sx, sy = view_transform.world_to_screen(ax, ay, width, height)
            renderer.canvas.create_oval(sx - point_radius + 1, sy - point_radius + 1,
                                        sx + point_radius - 1, sy + point_radius - 1,
                                        fill=color, outline="", tags="shape")
    
    def distance_to_point(self, px: float, py: float, width: int, height: int, view_transform) -> float:
        min_dist = float('inf')
        for i in range(64):
            wx, wy = self.get_point_on_ellipse(i * 360 / 64)
            sx, sy = view_transform.world_to_screen(wx, wy, width, height)
            min_dist = min(min_dist, math.hypot(px - sx, py - sy))
        return min_dist
    
    def get_info(self, is_degrees: bool = True) -> str:
        fn = format_number
        unit = "°" if is_degrees else " рад"
        rot = self.rotation if is_degrees else math.radians(self.rotation)
        h = ((self.rx - self.ry) / (self.rx + self.ry)) ** 2
        perimeter = math.pi * (self.rx + self.ry) * (1 + 3 * h / (10 + math.sqrt(4 - 3 * h)))
        
        return (f"Эллипс:\n"
                f"  Центр: ({fn(self.cx)}, {fn(self.cy)})\n"
                f"  Полуоси: {fn(self.rx)} × {fn(self.ry)}\n"
                f"  Поворот: {fn(rot)}{unit}\n"
                f"  Периметр: {fn(perimeter)}\n"
                f"  Площадь: {fn(math.pi * self.rx * self.ry)}")
    
    def get_bounds(self) -> Tuple[float, float, float, float]:
        points = [self.get_point_on_ellipse(i * 5) for i in range(72)]
        return (min(p[0] for p in points), min(p[1] for p in points),
                max(p[0] for p in points), max(p[1] for p in points))
    
    def translate(self, dx: float, dy: float) -> None:
        self.cx += dx
        self.cy += dy
    
    def get_snap_points(self) -> List[Tuple[str, float, float]]:
        points = [('center', self.cx, self.cy)]
        for ax, ay in self.get_axis_endpoints():
            points.append(('quadrant', ax, ay))
        return points
    
    def get_control_points(self) -> List[Tuple[str, float, float]]:
        axis = self.get_axis_endpoints()
        return [('center', self.cx, self.cy), ('axis_x', axis[0][0], axis[0][1]),
                ('axis_y', axis[2][0], axis[2][1])]
    
    def move_control_point(self, point_id: str, new_x: float, new_y: float) -> None:
        if point_id == 'center':
            self.cx, self.cy = new_x, new_y
        elif point_id == 'axis_x':
            self.rx = math.hypot(new_x - self.cx, new_y - self.cy)
            self.rotation = math.degrees(math.atan2(new_y - self.cy, new_x - self.cx))
        elif point_id == 'axis_y':
            self.ry = math.hypot(new_x - self.cx, new_y - self.cy)
    
    def to_dict(self) -> dict:
        return {'id': self.id, 'type': 'ellipse', 'cx': self.cx, 'cy': self.cy,
                'rx': self.rx, 'ry': self.ry, 'rotation': self.rotation,
                'color': self.color, 'line_style_name': self.line_style_name}
    
    @staticmethod
    def from_dict(data: dict) -> 'Ellipse':
        ellipse = Ellipse(data['cx'], data['cy'], data['rx'], data['ry'], data.get('rotation', 0))
        ellipse.color = data.get('color', ellipse.color)
        ellipse.line_style_name = data.get('line_style_name', ellipse.line_style_name)
        ellipse.id = data.get('id', ellipse.id)
        return ellipse
    
    def __repr__(self) -> str:
        return f"Ellipse({self.cx:.1f}, {self.cy:.1f}, {self.rx:.1f}×{self.ry:.1f})"
