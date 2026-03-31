"""Класс для представления точки"""
from typing import List, Tuple, Any
from .base import Shape
import math


class Point(Shape):
    """Класс точки"""
    
    def __init__(self, x: float, y: float):
        super().__init__()
        self.x = x
        self.y = y
        # Точка всегда сплошная, стиль линии на неё не влияет, но сохраним для совместимости
        self.line_style_name = "Сплошная основная"
    
    def draw(self, renderer: Any, width: int, height: int, view_transform: Any, point_radius: int = 4) -> None:
        """Отрисовка точки"""
        sx, sy = view_transform.world_to_screen(self.x, self.y, width, height)
        
        color = "#55ff55" if self.selected else self.color
        
        # Рисуем как крестик или закрашенный круг
        r = point_radius
        
        # Если точка выделена - рисуем рамку
        if self.selected:
            renderer.canvas.create_rectangle(sx - r - 2, sy - r - 2, 
                                            sx + r + 2, sy + r + 2, 
                                            outline=color, width=1, tags="shape")
            
        # Рисуем саму точку (перекрестие)
        renderer.canvas.create_line(sx - r, sy, sx + r, sy, fill=color, width=2, tags="shape")
        renderer.canvas.create_line(sx, sy - r, sx, sy + r, fill=color, width=2, tags="shape")

    def distance_to_point(self, px: float, py: float, width: int, height: int, view_transform: Any) -> float:
        sx, sy = view_transform.world_to_screen(self.x, self.y, width, height)
        return math.hypot(sx - px, sy - py)
    
    def get_info(self, is_degrees: bool = True) -> str:
        return f"Точка ({self.x:.2f}, {self.y:.2f})"
    
    def get_bounds(self) -> Tuple[float, float, float, float]:
        # Точка имеет нулевой размер, но для bounds дадим небольшой отступ
        return self.x - 0.1, self.y - 0.1, self.x + 0.1, self.y + 0.1
    
    def translate(self, dx: float, dy: float) -> None:
        self.x += dx
        self.y += dy
    
    def get_snap_points(self) -> List[Tuple[str, float, float]]:
        return [('endpoint', self.x, self.y), ('center', self.x, self.y)]
    
    def get_control_points(self) -> List[Tuple[str, float, float]]:
        return [('center', self.x, self.y)]
    
    def move_control_point(self, point_id: str, new_x: float, new_y: float) -> None:
        if point_id == 'center':
            self.x, self.y = new_x, new_y
            
    def to_dict(self) -> dict:
        return {'id': self.id, 
            'type': 'point', 
            'x': self.x, 
            'y': self.y,
            'color': self.color,
            'line_style_name': self.line_style_name
        }
    
    @staticmethod
    def from_dict(data: dict) -> 'Point':
        p = Point(data['x'], data['y'])
        p.color = data.get('color', p.color)
        p.line_style_name = data.get('line_style_name', p.line_style_name)
        p.id = data.get('id', p.id)
        return p
    
    def __repr__(self) -> str:
        return f"Point({self.x:.1f}, {self.y:.1f})"
