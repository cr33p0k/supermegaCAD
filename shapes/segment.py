"""Класс для представления отрезка"""
import math
from typing import List, Tuple, Optional
from .base import Shape
from core import CoordinateConverter, SegmentGeometry, format_segment_info


class Segment(Shape):
    """Класс отрезка"""
    
    def __init__(self, x1: float, y1: float, x2: float, y2: float):
        super().__init__()
        self.x1, self.y1 = x1, y1
        self.x2, self.y2 = x2, y2
    
    def get_midpoint(self) -> Tuple[float, float]:
        return ((self.x1 + self.x2) / 2, (self.y1 + self.y2) / 2)
    
    def get_length(self) -> float:
        return SegmentGeometry.calculate_length(self.x1, self.y1, self.x2, self.y2)
    
    def draw(self, renderer, width: int, height: int, view_transform, point_radius: int = 4) -> None:
        line_width = 3
        dash_pattern = None
        line_type = 'solid'
        
        if hasattr(renderer, 'style_manager') and renderer.style_manager:
            style = renderer.style_manager.get_style(self.line_style_name)
            if style:
                line_width = renderer.style_manager.mm_to_pixels(style.thickness_mm)
                dash_pattern = style.get_dash_pattern()
                line_type = style.line_type
        
        color = "#55ff55" if self.selected else self.color
        if self.selected:
            line_width += 1
        
        sx1, sy1 = view_transform.world_to_screen(self.x1, self.y1, width, height)
        sx2, sy2 = view_transform.world_to_screen(self.x2, self.y2, width, height)
        
        if line_type == 'wavy' and hasattr(renderer, 'style_manager') and renderer.style_manager:
            style = renderer.style_manager.get_style(self.line_style_name)
            if style:
                points = renderer.style_manager.generate_wavy_points(sx1, sy1, sx2, sy2, style.wave_amplitude, style.wave_length)
                flat = [c for pt in points for c in pt]
                if len(flat) >= 4:
                    renderer.canvas.create_line(*flat, fill=color, width=line_width, smooth=True, tags="shape")
        elif line_type == 'broken' and hasattr(renderer, 'style_manager') and renderer.style_manager:
            style = renderer.style_manager.get_style(self.line_style_name)
            if style:
                # Используем getattr для совместимости со старыми стилями
                break_height = getattr(style, 'break_height', 12.0)
                break_width = getattr(style, 'break_width', 10.0)
                break_count = getattr(style, 'break_count', 1)
                points = renderer.style_manager.generate_broken_points(sx1, sy1, sx2, sy2, 
                                                                      break_height, break_width, break_count)
            else:
                points = renderer.style_manager.generate_broken_points(sx1, sy1, sx2, sy2)
            flat = [c for pt in points for c in pt]
            if len(flat) >= 4:
                renderer.canvas.create_line(*flat, fill=color, width=line_width, tags="shape")
        else:
            renderer.canvas.create_line(sx1, sy1, sx2, sy2, fill=color, width=line_width, dash=dash_pattern, tags="shape")
        
        for sx, sy in [(sx1, sy1), (sx2, sy2)]:
            renderer.canvas.create_oval(sx - point_radius, sy - point_radius, 
                                        sx + point_radius, sy + point_radius, 
                                        fill=color, outline="", tags="shape")
    
    def distance_to_point(self, px: float, py: float, width: int, height: int, view_transform) -> float:
        sx1, sy1 = view_transform.world_to_screen(self.x1, self.y1, width, height)
        sx2, sy2 = view_transform.world_to_screen(self.x2, self.y2, width, height)
        return SegmentGeometry.point_to_segment_distance(px, py, sx1, sy1, sx2, sy2)
    
    def get_info(self, is_degrees: bool = True) -> str:
        return format_segment_info(self.x1, self.y1, self.x2, self.y2, is_degrees)
    
    def get_bounds(self) -> Tuple[float, float, float, float]:
        return min(self.x1, self.x2), min(self.y1, self.y2), max(self.x1, self.x2), max(self.y1, self.y2)
    
    def translate(self, dx: float, dy: float) -> None:
        self.x1 += dx; self.y1 += dy; self.x2 += dx; self.y2 += dy
    
    def get_snap_points(self) -> List[Tuple[str, float, float]]:
        mid = self.get_midpoint()
        return [('endpoint', self.x1, self.y1), ('endpoint', self.x2, self.y2), ('midpoint', mid[0], mid[1])]
    
    def get_control_points(self) -> List[Tuple[str, float, float]]:
        mid = self.get_midpoint()
        return [('start', self.x1, self.y1), ('end', self.x2, self.y2), ('midpoint', mid[0], mid[1])]
    
    def move_control_point(self, point_id: str, new_x: float, new_y: float) -> None:
        if point_id == 'start':
            self.x1, self.y1 = new_x, new_y
        elif point_id == 'end':
            self.x2, self.y2 = new_x, new_y
        elif point_id == 'midpoint':
            mid = self.get_midpoint()
            self.translate(new_x - mid[0], new_y - mid[1])
    
    def get_perpendicular_point(self, from_x: float, from_y: float) -> Optional[Tuple[float, float]]:
        dx, dy = self.x2 - self.x1, self.y2 - self.y1
        len2 = dx*dx + dy*dy
        if len2 == 0:
            return None
        t = ((from_x - self.x1) * dx + (from_y - self.y1) * dy) / len2
        if 0 <= t <= 1:
            return (self.x1 + t * dx, self.y1 + t * dy)
        return None
    
    def to_dict(self) -> dict:
        return {'id': self.id, 'type': 'segment', 'x1': self.x1, 'y1': self.y1, 'x2': self.x2, 'y2': self.y2,
                'color': self.color, 'line_style_name': self.line_style_name}
    
    @staticmethod
    def from_dict(data: dict) -> 'Segment':
        seg = Segment(data['x1'], data['y1'], data['x2'], data['y2'])
        seg.color = data.get('color', seg.color)
        seg.line_style_name = data.get('line_style_name', seg.line_style_name)
        seg.id = data.get('id', seg.id)
        return seg
    
    def __repr__(self) -> str:
        return f"Segment({self.x1:.1f}, {self.y1:.1f} → {self.x2:.1f}, {self.y2:.1f})"
