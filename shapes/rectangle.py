"""Класс для представления прямоугольника"""
import math
from typing import List, Tuple
from .base import Shape
from core import format_number


class Rectangle(Shape):
    """Класс прямоугольника с поддержкой скруглений, фасок и поворота"""
    
    def __init__(self, x: float, y: float, width: float, height: float,
                 corner_radius: float = 0, chamfer: float = 0, rotation: float = 0):
        super().__init__()
        self.x = x
        self.y = y
        self.width = abs(width) if width != 0 else 1
        self.height = abs(height) if height != 0 else 1
        self.corner_radius = max(0, corner_radius)
        self.chamfer = max(0, chamfer)
        self.rotation = rotation  # Угол поворота в градусах
    
    @classmethod
    def from_two_points(cls, x1: float, y1: float, x2: float, y2: float,
                        corner_radius: float = 0, chamfer: float = 0, rotation: float = 0) -> 'Rectangle':
        """Создание по двум противоположным точкам"""
        return cls(min(x1, x2), min(y1, y2), abs(x2 - x1), abs(y2 - y1), corner_radius, chamfer, rotation)
    
    @classmethod
    def from_center(cls, cx: float, cy: float, width: float, height: float,
                    corner_radius: float = 0, chamfer: float = 0, rotation: float = 0) -> 'Rectangle':
        """Создание по центру и размерам"""
        return cls(cx - width/2, cy - height/2, width, height, corner_radius, chamfer, rotation)
    
    def _rotate_point(self, px: float, py: float, cx: float, cy: float) -> Tuple[float, float]:
        """Поворот точки (px, py) вокруг центра (cx, cy) на угол self.rotation"""
        if self.rotation == 0:
            return (px, py)
        rad = math.radians(self.rotation)
        cos_r, sin_r = math.cos(rad), math.sin(rad)
        dx, dy = px - cx, py - cy
        return (cx + dx * cos_r - dy * sin_r, cy + dx * sin_r + dy * cos_r)
    
    def get_center(self) -> Tuple[float, float]:
        return (self.x + self.width/2, self.y + self.height/2)
    
    def get_corners_unrotated(self) -> List[Tuple[float, float]]:
        """Углы без поворота: BL, BR, TR, TL (против часовой от левого нижнего)"""
        return [(self.x, self.y), (self.x + self.width, self.y),
                (self.x + self.width, self.y + self.height), (self.x, self.y + self.height)]
    
    def get_corners(self) -> List[Tuple[float, float]]:
        """Углы с учётом поворота: BL, BR, TR, TL (против часовой от левого нижнего)"""
        corners = self.get_corners_unrotated()
        if self.rotation == 0:
            return corners
        cx, cy = self.get_center()
        return [self._rotate_point(c[0], c[1], cx, cy) for c in corners]
    
    def get_corner_feature_points(self) -> List[Tuple[float, float]]:
        """Получить точки на концах скруглений/фасок (или углы, если их нет).
        
        Возвращает список точек: для каждого угла - точку входа и выхода скругления/фаски.
        Если скругления/фаски нет, возвращаются сами углы.
        """
        corners = self.get_corners()
        max_corner = min(self.width, self.height) / 2
        corner_r = min(self.corner_radius, max_corner)
        chamfer_size = min(self.chamfer, max_corner)
        
        # Если нет ни скругления, ни фаски - возвращаем углы
        if corner_r <= 0 and chamfer_size <= 0:
            return corners
        
        # Определяем размер отступа от угла
        offset = corner_r if corner_r > 0 else chamfer_size
        
        points = []
        for i, (cx, cy) in enumerate(corners):
            prev = corners[(i - 1) % 4]
            nxt = corners[(i + 1) % 4]
            
            v_prev = self._normalize(prev[0] - cx, prev[1] - cy, offset)
            v_next = self._normalize(nxt[0] - cx, nxt[1] - cy, offset)
            
            if v_prev and v_next:
                entry = (cx + v_prev[0], cy + v_prev[1])
                exit_ = (cx + v_next[0], cy + v_next[1])
                points.append(entry)
                points.append(exit_)
            else:
                # Fallback на угол если что-то пошло не так
                points.append((cx, cy))
        
        return points
    
    def get_edge_midpoints(self) -> List[Tuple[float, float]]:
        """Середины сторон с учётом поворота"""
        cx, cy = self.get_center()
        midpoints = [(cx, self.y), (self.x + self.width, cy), (cx, self.y + self.height), (self.x, cy)]
        if self.rotation == 0:
            return midpoints
        return [self._rotate_point(m[0], m[1], cx, cy) for m in midpoints]
    
    def draw(self, renderer, width: int, height: int, view_transform, point_radius: int = 4) -> None:
        line_width, dash_pattern, line_type, style = self._get_style_draw_params(renderer)
        
        color = "#55ff55" if self.selected else self.color
        if self.selected:
            line_width += 1
        
        corners = [view_transform.world_to_screen(c[0], c[1], width, height) for c in self.get_corners()]
        
        max_corner = min(self.width, self.height) / 2
        corner_r = min(self.corner_radius, max_corner) * view_transform.scale
        chamfer_size = min(self.chamfer, max_corner) * view_transform.scale
        
        if corner_r > 1 and self.corner_radius > 0:
            self._draw_rounded(renderer, corners, corner_r, color, line_width, dash_pattern, line_type, style)
        elif chamfer_size > 1 and self.chamfer > 0:
            self._draw_chamfered(renderer, corners, chamfer_size, color, line_width, dash_pattern, line_type, style)
        else:
            self._draw_styled_screen_path(
                renderer,
                corners,
                color,
                line_width,
                dash_pattern,
                line_type,
                style,
                closed=True,
                smooth=False
            )
        
        # Рисуем точки на концах скруглений/фасок или углах
        feature_points = self.get_corner_feature_points()
        screen_feature_points = [view_transform.world_to_screen(p[0], p[1], width, height) 
                                  for p in feature_points]
        
        for sx, sy in screen_feature_points:
            renderer.canvas.create_oval(sx - point_radius, sy - point_radius,
                                        sx + point_radius, sy + point_radius,
                                        fill=color, outline="", tags="shape")
    
    def _draw_rounded(self, renderer, corners, radius, color, line_width, dash, line_type, style):
        """Классическое внутреннее скругление углов (филет)."""
        pts = []
        steps = 10
        for i, (cx, cy) in enumerate(corners):
            prev = corners[(i - 1) % 4]
            nxt = corners[(i + 1) % 4]

            # направления от угла к соседним углам
            v_prev = (prev[0] - cx, prev[1] - cy)
            v_next = (nxt[0] - cx, nxt[1] - cy)
            n_prev = self._normalize(v_prev[0], v_prev[1], radius)
            n_next = self._normalize(v_next[0], v_next[1], radius)
            if not n_prev or not n_next:
                continue

            entry = (cx + n_prev[0], cy + n_prev[1])
            exit_ = (cx + n_next[0], cy + n_next[1])
            center = (cx + n_prev[0] + n_next[0], cy + n_prev[1] + n_next[1])

            start_ang = math.atan2(entry[1] - center[1], entry[0] - center[0])
            end_ang = math.atan2(exit_[1] - center[1], exit_[0] - center[0])

            # выбрать направление, соответствующее внутренней дуге (короткий путь)
            if end_ang - start_ang > math.pi:
                end_ang -= 2 * math.pi
            elif start_ang - end_ang > math.pi:
                end_ang += 2 * math.pi

            for s in range(steps + 1):
                t = s / steps
                ang = start_ang + (end_ang - start_ang) * t
                pts.append((center[0] + radius * math.cos(ang), center[1] + radius * math.sin(ang)))

        if len(pts) >= 3:
            self._draw_styled_screen_path(
                renderer,
                pts,
                color,
                line_width,
                dash,
                line_type,
                style,
                closed=True,
                smooth=True
            )
    
    def _draw_chamfered(self, renderer, corners, chamfer, color, line_width, dash, line_type, style):
        """Прямоугольник с фасками (срез углов внутрь)."""
        pts = []
        for i, (cx, cy) in enumerate(corners):
            prev = corners[(i - 1) % 4]
            nxt = corners[(i + 1) % 4]
            v_prev = self._normalize(prev[0] - cx, prev[1] - cy, chamfer)
            v_next = self._normalize(nxt[0] - cx, nxt[1] - cy, chamfer)
            if not v_prev or not v_next:
                continue
            entry = (cx + v_prev[0], cy + v_prev[1])
            exit_ = (cx + v_next[0], cy + v_next[1])
            pts.append(entry)
            pts.append(exit_)

        if len(pts) >= 3:
            self._draw_styled_screen_path(
                renderer,
                pts,
                color,
                line_width,
                dash,
                line_type,
                style,
                closed=True,
                smooth=False
            )
    
    def _normalize(self, dx, dy, length):
        d = math.hypot(dx, dy)
        return (dx/d * length, dy/d * length) if d > 0 else None

    def distance_to_point(self, px: float, py: float, width: int, height: int, view_transform) -> float:
        corners = [view_transform.world_to_screen(c[0], c[1], width, height) for c in self.get_corners()]
        
        min_dist = float('inf')
        for i in range(4):
            x1, y1 = corners[i]
            x2, y2 = corners[(i+1) % 4]
            dx, dy = x2 - x1, y2 - y1
            len2 = dx*dx + dy*dy
            t = max(0, min(1, ((px-x1)*dx + (py-y1)*dy) / len2)) if len2 > 0 else 0
            min_dist = min(min_dist, math.hypot(px - (x1 + t*dx), py - (y1 + t*dy)))
        return min_dist
    
    def get_info(self, is_degrees: bool = True) -> str:
        fn = format_number
        cx, cy = self.get_center()
        unit = "°" if is_degrees else " рад"
        rot = self.rotation if is_degrees else math.radians(self.rotation)
        
        info = (f"Прямоугольник:\n"
                f"  Позиция: ({fn(self.x)}, {fn(self.y)})\n"
                f"  Размер: {fn(self.width)} × {fn(self.height)}\n"
                f"  Центр: ({fn(cx)}, {fn(cy)})\n"
                f"  Площадь: {fn(self.width * self.height)}")
        if self.rotation != 0:
            info += f"\n  Поворот: {fn(rot)}{unit}"
        if self.corner_radius > 0:
            info += f"\n  Скругление: {fn(self.corner_radius)}"
        if self.chamfer > 0:
            info += f"\n  Фаска: {fn(self.chamfer)}"
        return info
    
    def get_bounds(self) -> Tuple[float, float, float, float]:
        """Границы с учётом поворота"""
        corners = self.get_corners()
        xs = [c[0] for c in corners]
        ys = [c[1] for c in corners]
        return (min(xs), min(ys), max(xs), max(ys))
    
    def translate(self, dx: float, dy: float) -> None:
        self.x += dx
        self.y += dy
    
    def get_snap_points(self) -> List[Tuple[str, float, float]]:
        center = self.get_center()
        points = [('center', center[0], center[1])]
        
        # Используем точки скруглений/фасок вместо углов
        feature_points = self.get_corner_feature_points()
        for fp in feature_points:
            points.append(('endpoint', fp[0], fp[1]))
        
        for m in self.get_edge_midpoints():
            points.append(('midpoint', m[0], m[1]))
        return points
    
    def get_control_points(self) -> List[Tuple[str, float, float]]:
        corners = self.get_corners()
        center = self.get_center()
        return [('corner_bl', corners[0][0], corners[0][1]),
                ('corner_br', corners[1][0], corners[1][1]),
                ('corner_tr', corners[2][0], corners[2][1]),
                ('corner_tl', corners[3][0], corners[3][1]),
                ('center', center[0], center[1])]
    
    def move_control_point(self, point_id: str, new_x: float, new_y: float) -> None:
        if point_id == 'center':
            cx, cy = self.get_center()
            self.x += new_x - cx
            self.y += new_y - cy
        elif point_id == 'corner_bl':
            self.width += self.x - new_x
            self.height += self.y - new_y
            self.x, self.y = new_x, new_y
        elif point_id == 'corner_br':
            self.width = new_x - self.x
            self.height += self.y - new_y
            self.y = new_y
        elif point_id == 'corner_tr':
            self.width = new_x - self.x
            self.height = new_y - self.y
        elif point_id == 'corner_tl':
            self.width += self.x - new_x
            self.x = new_x
            self.height = new_y - self.y

        # Нормализация
        if self.width < 0:
            self.x += self.width
            self.width = abs(self.width)
        if self.height < 0:
            self.y += self.height
            self.height = abs(self.height)
        self.width = max(1, self.width)
        self.height = max(1, self.height)
    
    def to_dict(self) -> dict:
        return {'id': self.id, 'type': 'rectangle', 'x': self.x, 'y': self.y,
                'width': self.width, 'height': self.height,
                'corner_radius': self.corner_radius, 'chamfer': self.chamfer,
                'rotation': self.rotation,
                'color': self.color, 'line_style_name': self.line_style_name}
    
    @staticmethod
    def from_dict(data: dict) -> 'Rectangle':
        rect = Rectangle(data['x'], data['y'], data['width'], data['height'],
                        data.get('corner_radius', 0), data.get('chamfer', 0),
                        data.get('rotation', 0))
        rect.color = data.get('color', rect.color)
        rect.line_style_name = data.get('line_style_name', rect.line_style_name)
        rect.id = data.get('id', rect.id)
        return rect
    
    def __repr__(self) -> str:
        return f"Rectangle({self.x:.1f}, {self.y:.1f}, {self.width:.1f}×{self.height:.1f})"
