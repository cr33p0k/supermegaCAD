"""Классы для представления размеров (ГОСТ 2.307-2011)"""
import math
from typing import List, Tuple, Optional, Any
from .base import Shape
from core import CoordinateConverter, SegmentGeometry


class Dimension(Shape):
    """Абстрактный класс размера"""
    def __init__(self):
        super().__init__()
        self.color = "#ffffff"  # Размеры белые по умолчанию для контраста на черном фоне
        self.text_override = ""  # Пользовательский текст (если пустой, генерируется автоматически)
        self.text_pos_x = 0.0
        self.text_pos_y = 0.0
        self.layer = "Размеры"
        
    def _draw_arrow(self, renderer, x: float, y: float, angle_rad: float, color: str) -> None:
        """Отрисовка стрелки (ГОСТ: узкая, длинная, соотношение примерно 3:1)"""
        arrow_length = 15.0
        arrow_width = 5.0
        
        # Точки стрелки в локальных координатах (острие в 0,0)
        p1 = (0, 0)
        p2 = (-arrow_length, arrow_width / 2)
        p3 = (-arrow_length, -arrow_width / 2)
        
        # Поворот и смещение
        cos_a = math.cos(angle_rad)
        sin_a = math.sin(angle_rad)
        
        pts = []
        for px, py in [p1, p2, p3]:
            rx = px * cos_a - py * sin_a
            ry = px * sin_a + py * cos_a
            pts.extend([x + rx, y + ry])
            
        renderer.canvas.create_polygon(*pts, fill=color, outline=color, tags="shape")

    def _format_value(self, value: float) -> str:
        if self.text_override:
            return self.text_override
        return f"{value:.2f}"
    
    def _draw_text(self, renderer, text: str, x: float, y: float, angle_rad: float, color: str) -> None:
        """Отрисовка размерного текста"""
        angle_deg = math.degrees(angle_rad)
        # Поворот текста так, чтобы он всегда читался снизу или справа
        if 90 < angle_deg <= 270 or -270 < angle_deg <= -90:
            angle_deg += 180
            
        # Canvas create_text angle works differently (counter-clockwise)
        tk_angle = -angle_deg
        
        # Отступ текста от линии (над линией)
        offset = 5.0
        
        renderer.canvas.create_text(x, y - offset, text=text, fill=color, 
                                    font=("Arial", 10), angle=tk_angle, anchor="s", tags="shape")


class LinearDimension(Dimension):
    """Линейный размер"""
    def __init__(self, p1: Tuple[float, float], p2: Tuple[float, float], offset: float = 30.0):
        super().__init__()
        self.p1_x, self.p1_y = p1
        self.p2_x, self.p2_y = p2
        self.offset = offset  # Отступ размерной линии от измеряемого отрезка
        
        # Ссылки на базовые фигуры (по id)
        self.base_shape_id1 = None
        self.base_point_id1 = None
        self.base_shape_id2 = None
        self.base_point_id2 = None
        
    def _update_points(self, bg_manager: Any = None) -> None:
        """Обновить точки из ассоциированных фигур"""
        if not bg_manager:
            return
            
        if self.base_shape_id1:
            s1 = bg_manager.get_shape_by_id(self.base_shape_id1)
            if s1:
                snap_pts = s1.get_snap_points() + s1.get_control_points()
                for pt in snap_pts:
                    if pt[0] == self.base_point_id1 or str(pt[1])+str(pt[2]) == self.base_point_id1: # Простая идентификация
                        self.p1_x, self.p1_y = pt[1], pt[2]
                        break
                        
        if self.base_shape_id2:
            s2 = bg_manager.get_shape_by_id(self.base_shape_id2)
            if s2:
                snap_pts = s2.get_snap_points() + s2.get_control_points()
                for pt in snap_pts:
                    if pt[0] == self.base_point_id2 or str(pt[1])+str(pt[2]) == self.base_point_id2:
                        self.p2_x, self.p2_y = pt[1], pt[2]
                        break

    def draw(self, renderer, width: int, height: int, view_transform, point_radius: int = 4) -> None:
        color = "#55ff55" if self.selected else self.color
        
        # Попытка обновить точки, если передан менеджер фигур (хак: берем его из приложения, если доступно)
        if hasattr(renderer, "app"):
            self._update_points(renderer.app.shape_manager)

        sp1 = view_transform.world_to_screen(self.p1_x, self.p1_y, width, height)
        sp2 = view_transform.world_to_screen(self.p2_x, self.p2_y, width, height)
        
        # Вычисление угла и нормали
        dx = sp2[0] - sp1[0]
        dy = sp2[1] - sp1[1]
        length = math.hypot(dx, dy)
        
        if length < 1e-5:
            return
            
        angle_rad = math.atan2(dy, dx)
        
        # Нормаль для отступа размерной линии
        nx = -math.sin(angle_rad)
        ny = math.cos(angle_rad)
        
        screen_offset = self.offset * view_transform.scale
        
        # Точки размерной линии
        dim_p1 = (sp1[0] + nx * screen_offset, sp1[1] + ny * screen_offset)
        dim_p2 = (sp2[0] + nx * screen_offset, sp2[1] + ny * screen_offset)
        
        # Выносные линии (с выступом на 2мм за размерную по ГОСТ)
        extend_mm = 2.0 * view_transform.scale
        ext1_end = (dim_p1[0] + nx * extend_mm, dim_p1[1] + ny * extend_mm)
        ext2_end = (dim_p2[0] + nx * extend_mm, dim_p2[1] + ny * extend_mm)
        
        renderer.canvas.create_line(sp1[0], sp1[1], ext1_end[0], ext1_end[1], fill=color, width=1, tags="shape")
        renderer.canvas.create_line(sp2[0], sp2[1], ext2_end[0], ext2_end[1], fill=color, width=1, tags="shape")
        
        # Размерная линия
        renderer.canvas.create_line(dim_p1[0], dim_p1[1], dim_p2[0], dim_p2[1], fill=color, width=1, tags="shape")
        
        # Стрелки
        self._draw_arrow(renderer, dim_p1[0], dim_p1[1], angle_rad + math.pi, color)
        self._draw_arrow(renderer, dim_p2[0], dim_p2[1], angle_rad, color)
        
        # Текст
        mid_x = (dim_p1[0] + dim_p2[0]) / 2
        mid_y = (dim_p1[1] + dim_p2[1]) / 2
        
        val = SegmentGeometry.calculate_length(self.p1_x, self.p1_y, self.p2_x, self.p2_y)
        self._draw_text(renderer, self._format_value(val), mid_x, mid_y, angle_rad, color)

    def get_info(self, is_degrees: bool = True) -> str:
        val = SegmentGeometry.calculate_length(self.p1_x, self.p1_y, self.p2_x, self.p2_y)
        return f"Линейный размер\nЗначение: {self._format_value(val)}\nОтступ: {self.offset:.1f}"

    def get_bounds(self) -> Tuple[float, float, float, float]:
        # Упрощенные границы по базовым точкам
        min_x = min(self.p1_x, self.p2_x)
        min_y = min(self.p1_y, self.p2_y)
        max_x = max(self.p1_x, self.p2_x)
        max_y = max(self.p1_y, self.p2_y)
        # Добавляем отступ (приближенно)
        return min_x - abs(self.offset), min_y - abs(self.offset), max_x + abs(self.offset), max_y + abs(self.offset)

    def translate(self, dx: float, dy: float) -> None:
        if not self.base_shape_id1 and not self.base_shape_id2:
            self.p1_x += dx; self.p1_y += dy
            self.p2_x += dx; self.p2_y += dy

    def distance_to_point(self, px: float, py: float, width: int, height: int, view_transform) -> float:
        # Упрощенная проверка клика - по размерной линии
        sp1 = view_transform.world_to_screen(self.p1_x, self.p1_y, width, height)
        sp2 = view_transform.world_to_screen(self.p2_x, self.p2_y, width, height)
        dx = sp2[0] - sp1[0]; dy = sp2[1] - sp1[1]
        angle_rad = math.atan2(dy, dx)
        nx = -math.sin(angle_rad)
        ny = math.cos(angle_rad)
        screen_offset = self.offset * view_transform.scale
        dim_p1 = (sp1[0] + nx * screen_offset, sp1[1] + ny * screen_offset)
        dim_p2 = (sp2[0] + nx * screen_offset, sp2[1] + ny * screen_offset)
        return SegmentGeometry.point_to_segment_distance(px, py, dim_p1[0], dim_p1[1], dim_p2[0], dim_p2[1])

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'type': 'linear_dimension',
            'p1_x': self.p1_x, 'p1_y': self.p1_y,
            'p2_x': self.p2_x, 'p2_y': self.p2_y,
            'offset': self.offset,
            'color': self.color,
            'text_override': self.text_override,
            'base_shape_id1': self.base_shape_id1,
            'base_point_id1': self.base_point_id1,
            'base_shape_id2': self.base_shape_id2,
            'base_point_id2': self.base_point_id2
        }

    @staticmethod
    def from_dict(data: dict) -> 'LinearDimension':
        dim = LinearDimension((data['p1_x'], data['p1_y']), (data['p2_x'], data['p2_y']), data.get('offset', 30.0))
        dim.id = data.get('id', dim.id)
        dim.color = data.get('color', dim.color)
        dim.text_override = data.get('text_override', '')
        dim.base_shape_id1 = data.get('base_shape_id1')
        dim.base_point_id1 = data.get('base_point_id1')
        dim.base_shape_id2 = data.get('base_shape_id2')
        dim.base_point_id2 = data.get('base_point_id2')
        return dim


class RadialDimension(Dimension):
    """Радиальный размер"""
    def __init__(self, cx: float, cy: float, radius: float, is_diameter: bool = False):
        super().__init__()
        self.cx = cx
        self.cy = cy
        self.radius = radius
        self.is_diameter = is_diameter
        
        self.angle_rad = math.pi / 4  # Угол наклона размерной линии
        self.base_shape_id = None
        
    def _update_params(self, bg_manager: Any = None) -> None:
        if not bg_manager or not self.base_shape_id:
            return
        shape = bg_manager.get_shape_by_id(self.base_shape_id)
        if shape:
            if hasattr(shape, 'x') and hasattr(shape, 'y') and hasattr(shape, 'radius'):
                self.cx = shape.x
                self.cy = shape.y
                self.radius = shape.radius
            elif hasattr(shape, 'cx') and hasattr(shape, 'cy') and hasattr(shape, 'radius'):
                self.cx = shape.cx
                self.cy = shape.cy
                self.radius = shape.radius

    def draw(self, renderer, width: int, height: int, view_transform, point_radius: int = 4) -> None:
        color = "#55ff55" if self.selected else self.color
        if hasattr(renderer, "app"):
            self._update_params(renderer.app.shape_manager)

        sc = view_transform.world_to_screen(self.cx, self.cy, width, height)
        radius_screen = self.radius * view_transform.scale
        
        # Точка на окружности
        px = self.cx + self.radius * math.cos(self.angle_rad)
        py = self.cy + self.radius * math.sin(self.angle_rad)
        sp = view_transform.world_to_screen(px, py, width, height)
        
        # Полка
        shelf_len = 30.0
        shelf_dir = 1 if math.cos(self.angle_rad) >= 0 else -1
        shelf_end = (sp[0] + shelf_dir * shelf_len, sp[1])
        
        renderer.canvas.create_line(sc[0], sc[1], sp[0], sp[1], fill=color, width=1, tags="shape")
        renderer.canvas.create_line(sp[0], sp[1], shelf_end[0], shelf_end[1], fill=color, width=1, tags="shape")
        
        # Стрелка у окружности
        self._draw_arrow(renderer, sp[0], sp[1], self.angle_rad, color)
        
        val = self.radius * 2 if self.is_diameter else self.radius
        prefix = "Ø" if self.is_diameter else "R"
        text = f"{prefix}{self._format_value(val)}"
        
        # Текст над полкой
        text_x = sp[0] + (shelf_dir * shelf_len / 2)
        renderer.canvas.create_text(text_x, sp[1] - 5, text=text, fill=color, font=("Arial", 10), anchor="s", tags="shape")

    def get_info(self, is_degrees: bool = True) -> str:
        val = self.radius * 2 if self.is_diameter else self.radius
        prefix = "Диаметр" if self.is_diameter else "Радиус"
        return f"{prefix}ой размер\nЗначение: {self._format_value(val)}"

    def get_bounds(self) -> Tuple[float, float, float, float]:
        r = self.radius
        return self.cx - r, self.cy - r, self.cx + r, self.cy + r

    def distance_to_point(self, px: float, py: float, width: int, height: int, view_transform) -> float:
        sc = view_transform.world_to_screen(self.cx, self.cy, width, height)
        p_x = self.cx + self.radius * math.cos(self.angle_rad)
        p_y = self.cy + self.radius * math.sin(self.angle_rad)
        sp = view_transform.world_to_screen(p_x, p_y, width, height)
        return SegmentGeometry.point_to_segment_distance(px, py, sc[0], sc[1], sp[0], sp[1])

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'type': 'radial_dimension',
            'cx': self.cx, 'cy': self.cy,
            'radius': self.radius,
            'is_diameter': self.is_diameter,
            'angle_rad': self.angle_rad,
            'color': self.color,
            'text_override': self.text_override,
            'base_shape_id': self.base_shape_id
        }

    @staticmethod
    def from_dict(data: dict) -> 'RadialDimension':
        dim = RadialDimension(data['cx'], data['cy'], data['radius'], data.get('is_diameter', False))
        dim.id = data.get('id', dim.id)
        dim.angle_rad = data.get('angle_rad', math.pi / 4)
        dim.color = data.get('color', dim.color)
        dim.text_override = data.get('text_override', '')
        dim.base_shape_id = data.get('base_shape_id')
        return dim

    def translate(self, dx: float, dy: float) -> None:
        if not self.base_shape_id:
            self.cx += dx; self.cy += dy

class AngularDimension(Dimension):
    """Угловой размер"""
    def __init__(self, cx: float, cy: float, p1: Tuple[float, float], p2: Tuple[float, float], radius: float = 30.0):
        super().__init__()
        self.cx, self.cy = cx, cy
        self.p1_x, self.p1_y = p1
        self.p2_x, self.p2_y = p2
        self.radius = radius
        self.base_shape_id1 = None
        self.base_shape_id2 = None
        
    def draw(self, renderer, width: int, height: int, view_transform, point_radius: int = 4) -> None:
        color = "#55ff55" if self.selected else self.color
        
        sc = view_transform.world_to_screen(self.cx, self.cy, width, height)
        sp1 = view_transform.world_to_screen(self.p1_x, self.p1_y, width, height)
        sp2 = view_transform.world_to_screen(self.p2_x, self.p2_y, width, height)
        
        angle1 = math.atan2(self.p1_y - self.cy, self.p1_x - self.cx)
        angle2 = math.atan2(self.p2_y - self.cy, self.p2_x - self.cx)
        
        # Разница углов
        diff = angle2 - angle1
        val_deg = math.degrees(diff) if diff > 0 else math.degrees(diff + 2 * math.pi)
        if val_deg > 180:
            val_deg = 360 - val_deg
            
        screen_radius = self.radius * view_transform.scale
        
        # Выносные линии от центра к точкам (длиннее радиуса дуги)
        ext_r = screen_radius + (5 * view_transform.scale)
        e1x = sc[0] + ext_r * math.cos(-angle1)
        e1y = sc[1] + ext_r * math.sin(-angle1)
        e2x = sc[0] + ext_r * math.cos(-angle2)
        e2y = sc[1] + ext_r * math.sin(-angle2)
        
        renderer.canvas.create_line(sc[0], sc[1], e1x, e1y, fill=color, width=1, tags="shape")
        renderer.canvas.create_line(sc[0], sc[1], e2x, e2y, fill=color, width=1, tags="shape")
        
        # Дуга размера
        bb_sc = (sc[0] - screen_radius, sc[1] - screen_radius, sc[0] + screen_radius, sc[1] + screen_radius)
        a1_deg = math.degrees(-angle1)
        extent = math.degrees(-(angle2 - angle1))
        
        # Tkinter arc logic
        while extent <= -180: extent += 360
        while extent > 180: extent -= 360
            
        renderer.canvas.create_arc(*bb_sc, start=a1_deg, extent=extent, style=tk.ARC, outline=color, width=1, tags="shape")
        
        import tkinter as tk
        mid_angle = angle1 + math.radians(extent/2) if extent > 0 else angle1 + math.radians(extent/2) # approximate
        
        # Стрелки
        self._draw_arrow(renderer, sc[0] + screen_radius * math.cos(-angle1), sc[1] + screen_radius * math.sin(-angle1), -angle1 + math.pi/2, color)
        self._draw_arrow(renderer, sc[0] + screen_radius * math.cos(-angle2), sc[1] + screen_radius * math.sin(-angle2), -angle2 - math.pi/2, color)
        
        # Текст
        tx = sc[0] + (screen_radius + 10) * math.cos(-mid_angle)
        ty = sc[1] + (screen_radius + 10) * math.sin(-mid_angle)
        text = f"{self._format_value(val_deg)}°"
        self._draw_text(renderer, text, tx, ty, 0, color)
        
    def get_info(self, is_degrees: bool = True) -> str:
        return f"Угловой размер"

    def get_bounds(self) -> Tuple[float, float, float, float]:
        return self.cx - self.radius, self.cy - self.radius, self.cx + self.radius, self.cy + self.radius

    def distance_to_point(self, px: float, py: float, width: int, height: int, view_transform) -> float:
        sc = view_transform.world_to_screen(self.cx, self.cy, width, height)
        dist = math.hypot(px - sc[0], py - sc[1])
        screen_radius = self.radius * view_transform.scale
        return abs(dist - screen_radius)

    def translate(self, dx: float, dy: float) -> None:
        self.cx += dx; self.cy += dy
        self.p1_x += dx; self.p1_y += dy
        self.p2_x += dx; self.p2_y += dy

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'type': 'angular_dimension',
            'cx': self.cx, 'cy': self.cy,
            'p1_x': self.p1_x, 'p1_y': self.p1_y,
            'p2_x': self.p2_x, 'p2_y': self.p2_y,
            'radius': self.radius,
            'color': self.color,
            'text_override': self.text_override,
            'base_shape_id1': self.base_shape_id1,
            'base_shape_id2': self.base_shape_id2
        }

    @staticmethod
    def from_dict(data: dict) -> 'AngularDimension':
        dim = AngularDimension(data['cx'], data['cy'], (data['p1_x'], data['p1_y']), (data['p2_x'], data['p2_y']), data.get('radius', 30.0))
        dim.id = data.get('id', dim.id)
        dim.color = data.get('color', dim.color)
        dim.text_override = data.get('text_override', '')
        dim.base_shape_id1 = data.get('base_shape_id1')
        dim.base_shape_id2 = data.get('base_shape_id2')
        return dim
