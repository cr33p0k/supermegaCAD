"""Класс для представления дуги"""
import math
from typing import List, Tuple, Optional
from .base import Shape
from core import format_number


class Arc(Shape):
    """Класс дуги"""
    
    def __init__(self, cx: float, cy: float, radius: float, 
                 start_angle: float, end_angle: float):
        super().__init__()
        self.cx = cx
        self.cy = cy
        self.radius = max(0.1, radius)
        self.start_angle = start_angle
        self.end_angle = end_angle
    
    def _normalize_angle(self, angle: float) -> float:
        """Нормализует угол в диапазон [0, 360)"""
        while angle < 0:
            angle += 360
        while angle >= 360:
            angle -= 360
        return angle
    
    def _get_extent(self) -> float:
        """
        Вычисляет правильный extent (угловой размах) дуги.
        Возвращает значение в градусах, может быть отрицательным для CW дуг.
        Сохраняет исходное направление, даже если дуга > 180°.
        """
        # Используем исходные углы без нормализации, чтобы сохранить направление
        # Если дуга была создана с extent > 180°, это сохранится
        raw_extent = self.end_angle - self.start_angle
        
        # Если разность слишком большая (вероятно, дуга проходит через 0°),
        # нормализуем углы и пересчитываем
        if abs(raw_extent) > 360:
            start_norm = self._normalize_angle(self.start_angle)
            end_norm = self._normalize_angle(self.end_angle)
            
            # Вычисляем разность в обоих направлениях
            ccw_extent = (end_norm - start_norm) % 360  # [0, 360)
            if ccw_extent == 0 and end_norm != start_norm:
                ccw_extent = 360  # Полная окружность
            cw_extent = ccw_extent - 360  # (-360, 0]
            
            # Выбираем меньший по модулю (короткая дуга)
            # Если они равны (180°), выбираем CCW
            if abs(ccw_extent) <= abs(cw_extent):
                return ccw_extent
            else:
                return cw_extent
        
        return raw_extent
    
    @classmethod
    def from_three_points(cls, x1: float, y1: float, x2: float, y2: float,
                          x3: float, y3: float) -> Optional['Arc']:
        """Создание дуги по трём точкам:
        x1, y1 - начало дуги
        x2, y2 - конец дуги
        x3, y3 - точка на дуге, определяющая её положение и выпуклость
        Все три точки лежат на одной окружности.
        """
        # Находим окружность, проходящую через все три точки
        # Используем формулу для центра окружности через три точки
        d = 2 * (x1 * (y2 - y3) + x2 * (y3 - y1) + x3 * (y1 - y2))
        if abs(d) < 1e-10:
            # Точки коллинеарны, нельзя построить окружность
            return None
        
        # Центр окружности
        cx = ((x1*x1 + y1*y1) * (y2 - y3) + (x2*x2 + y2*y2) * (y3 - y1) + (x3*x3 + y3*y3) * (y1 - y2)) / d
        cy = ((x1*x1 + y1*y1) * (x3 - x2) + (x2*x2 + y2*y2) * (x1 - x3) + (x3*x3 + y3*y3) * (x2 - x1)) / d
        
        # Радиус
        radius = math.hypot(x1 - cx, y1 - cy)
        
        if radius < 1e-10:
            return None
        
        # Углы от центра к трем точкам (в радианах)
        a1 = math.atan2(y1 - cy, x1 - cx)
        a2 = math.atan2(y2 - cy, x2 - cx)
        a3 = math.atan2(y3 - cy, x3 - cx)
        
        # Нормализуем углы в диапазон [0, 2π)
        def normalize_angle(angle):
            while angle < 0:
                angle += 2 * math.pi
            while angle >= 2 * math.pi:
                angle -= 2 * math.pi
            return angle
        
        a1_norm = normalize_angle(a1)
        a2_norm = normalize_angle(a2)
        a3_norm = normalize_angle(a3)
        
        # Определяем направление дуги: она должна проходить через третью точку (a3)
        # Вычисляем два возможных пути от a1 до a2:
        # 1. Против часовой стрелки (CCW): a1 -> a3 -> a2
        # 2. По часовой стрелке (CW): a1 -> a2 (минуя a3, или в другую сторону)
        
        # Проверяем, находится ли a3 между a1 и a2 при движении против часовой стрелки
        ccw_extent = (a2_norm - a1_norm) % (2 * math.pi)
        if ccw_extent < 1e-9:
            ccw_extent = 2 * math.pi  # Полная окружность
        
        # Проверяем, проходит ли путь CCW от a1 до a2 через a3
        a3_rel_ccw = (a3_norm - a1_norm) % (2 * math.pi)
        a3_on_ccw_path = 0 <= a3_rel_ccw <= ccw_extent + 1e-9
        
        if a3_on_ccw_path:
            # Третья точка на пути CCW - используем CCW дугу
            extent_rad = ccw_extent
            start_angle = math.degrees(a1)
            end_angle = math.degrees(a1 + extent_rad)
        else:
            # Третья точка не на пути CCW - используем CW дугу
            cw_extent = ccw_extent - 2 * math.pi
            extent_rad = cw_extent
            start_angle = math.degrees(a1)
            end_angle = math.degrees(a1 + extent_rad)
        
        return cls(cx, cy, radius, start_angle, end_angle)
    
    def get_start_point(self) -> Tuple[float, float]:
        rad = math.radians(self.start_angle)
        return (self.cx + self.radius * math.cos(rad), 
                self.cy + self.radius * math.sin(rad))
    
    def get_end_point(self) -> Tuple[float, float]:
        rad = math.radians(self.end_angle)
        return (self.cx + self.radius * math.cos(rad),
                self.cy + self.radius * math.sin(rad))
    
    def get_mid_point(self) -> Tuple[float, float]:
        """Вычисляет среднюю точку дуги с учётом правильного направления"""
        start_rad = math.radians(self.start_angle)
        extent_rad = math.radians(self._get_extent())
        mid_rad = start_rad + extent_rad / 2
        return (self.cx + self.radius * math.cos(mid_rad),
                self.cy + self.radius * math.sin(mid_rad))
    
    def get_arc_length(self) -> float:
        """Вычисляет длину дуги с учётом правильного углового размаха"""
        extent = self._get_extent()
        return abs(self.radius * math.radians(extent))
    
    def get_arc_points(self, num_segments: int = 32) -> List[Tuple[float, float]]:
        """
        Получить точки дуги для отрисовки.
        Правильно обрабатывает дуги, проходящие через 0° и дуги > 180°.
        """
        points = []
        start_rad = math.radians(self.start_angle)
        extent_rad = math.radians(self._get_extent())
        
        for i in range(num_segments + 1):
            t = i / num_segments
            angle_rad = start_rad + extent_rad * t
            x = self.cx + self.radius * math.cos(angle_rad)
            y = self.cy + self.radius * math.sin(angle_rad)
            points.append((x, y))
        
        return points
    
    def draw(self, renderer, width: int, height: int, view_transform, point_radius: int = 4) -> None:
        line_width, dash_pattern, line_type, style = self._get_style_draw_params(renderer)
        
        color = "#55ff55" if self.selected else self.color
        if self.selected:
            line_width += 1
        
        arc_points = self.get_arc_points(48)
        screen_points = [
            view_transform.world_to_screen(px, py, width, height)
            for px, py in arc_points
        ]
        self._draw_styled_screen_path(
            renderer,
            screen_points,
            color,
            line_width,
            dash_pattern,
            line_type,
            style,
            closed=False,
            smooth=True
        )
        
        # Концевые точки
        for pt in [self.get_start_point(), self.get_end_point()]:
            sx, sy = view_transform.world_to_screen(pt[0], pt[1], width, height)
            renderer.canvas.create_oval(sx - point_radius, sy - point_radius,
                                        sx + point_radius, sy + point_radius,
                                        fill=color, outline="", tags="shape")
        
        # Центр
        scx, scy = view_transform.world_to_screen(self.cx, self.cy, width, height)
        renderer.canvas.create_oval(scx - 2, scy - 2, scx + 2, scy + 2,
                                    fill=color, outline="", tags="shape")
    
    def distance_to_point(self, px: float, py: float, width: int, height: int, view_transform) -> float:
        # Проверяем расстояние до каждого сегмента дуги
        arc_points = self.get_arc_points(32)
        min_dist = float('inf')
        
        for i in range(len(arc_points) - 1):
            p1 = arc_points[i]
            p2 = arc_points[i + 1]
            
            sx1, sy1 = view_transform.world_to_screen(p1[0], p1[1], width, height)
            sx2, sy2 = view_transform.world_to_screen(p2[0], p2[1], width, height)
            
            # Расстояние до отрезка
            dx, dy = sx2 - sx1, sy2 - sy1
            len2 = dx * dx + dy * dy
            if len2 > 0:
                t = max(0, min(1, ((px - sx1) * dx + (py - sy1) * dy) / len2))
                proj_x = sx1 + t * dx
                proj_y = sy1 + t * dy
                dist = math.hypot(px - proj_x, py - proj_y)
            else:
                dist = math.hypot(px - sx1, py - sy1)
            
            min_dist = min(min_dist, dist)
        
        return min_dist
    
    def get_info(self, is_degrees: bool = True) -> str:
        fn = format_number
        unit = "°" if is_degrees else " рад"
        start = self.start_angle if is_degrees else math.radians(self.start_angle)
        end = self.end_angle if is_degrees else math.radians(self.end_angle)
        
        return (f"Дуга:\n"
                f"  Центр: ({fn(self.cx)}, {fn(self.cy)})\n"
                f"  Радиус: {fn(self.radius)}\n"
                f"  Углы: {fn(start)}{unit} → {fn(end)}{unit}\n"
                f"  Длина: {fn(self.get_arc_length())}")
    
    def get_bounds(self) -> Tuple[float, float, float, float]:
        points = self.get_arc_points(16)
        if not points:
            return (self.cx - self.radius, self.cy - self.radius,
                    self.cx + self.radius, self.cy + self.radius)
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        return (min(xs), min(ys), max(xs), max(ys))
    
    def translate(self, dx: float, dy: float) -> None:
        self.cx += dx
        self.cy += dy
    
    def get_snap_points(self) -> List[Tuple[str, float, float]]:
        sp, ep, mp = self.get_start_point(), self.get_end_point(), self.get_mid_point()
        return [('center', self.cx, self.cy), ('endpoint', sp[0], sp[1]),
                ('endpoint', ep[0], ep[1]), ('midpoint', mp[0], mp[1])]
    
    def get_control_points(self) -> List[Tuple[str, float, float]]:
        sp, ep = self.get_start_point(), self.get_end_point()
        return [('center', self.cx, self.cy), ('start', sp[0], sp[1]), ('end', ep[0], ep[1])]
    
    def move_control_point(self, point_id: str, new_x: float, new_y: float) -> None:
        if point_id == 'center':
            self.cx, self.cy = new_x, new_y
        elif point_id == 'start':
            self.radius = math.hypot(new_x - self.cx, new_y - self.cy)
            self.start_angle = math.degrees(math.atan2(new_y - self.cy, new_x - self.cx))
        elif point_id == 'end':
            self.radius = math.hypot(new_x - self.cx, new_y - self.cy)
            self.end_angle = math.degrees(math.atan2(new_y - self.cy, new_x - self.cx))
    
    def to_dict(self) -> dict:
        return {'id': self.id, 'type': 'arc', 'cx': self.cx, 'cy': self.cy, 'radius': self.radius,
                'start_angle': self.start_angle, 'end_angle': self.end_angle,
                'color': self.color, 'line_style_name': self.line_style_name}
    
    @staticmethod
    def from_dict(data: dict) -> 'Arc':
        arc = Arc(data['cx'], data['cy'], data['radius'], data['start_angle'], data['end_angle'])
        arc.color = data.get('color', arc.color)
        arc.line_style_name = data.get('line_style_name', arc.line_style_name)
        arc.id = data.get('id', arc.id)
        return arc
    
    def __repr__(self) -> str:
        return f"Arc(cx={self.cx:.1f}, cy={self.cy:.1f}, r={self.radius:.1f})"
