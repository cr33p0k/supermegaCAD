"""Универсальный инструмент рисования для всех примитивов"""
import math
import tkinter as tk
from typing import Optional, List, Tuple
from enum import Enum, auto
from .base import Tool
from shapes import Segment, Circle, Arc, Rectangle, Ellipse, Polygon, Spline


class PrimitiveType(Enum):
    SEGMENT = auto()
    CIRCLE = auto()
    ARC = auto()
    RECTANGLE = auto()
    ELLIPSE = auto()
    POLYGON = auto()
    SPLINE = auto()


class CreationMode(Enum):
    SEGMENT_TWO_POINTS = auto()
    SEGMENT_LENGTH_ANGLE = auto()
    CIRCLE_CENTER_RADIUS = auto()
    CIRCLE_CENTER_DIAMETER = auto()
    CIRCLE_TWO_POINTS = auto()
    CIRCLE_THREE_POINTS = auto()
    ARC_THREE_POINTS = auto()
    ARC_CENTER_ANGLES = auto()
    RECT_TWO_POINTS = auto()
    RECT_POINT_SIZE = auto()
    RECT_CENTER_SIZE = auto()
    ELLIPSE_CENTER_AXES = auto()
    ELLIPSE_BOUNDING_BOX = auto()
    POLYGON_CENTER_RADIUS = auto()
    SPLINE_POINTS = auto()


PRIMITIVE_MODES = {
    PrimitiveType.SEGMENT: [
        (CreationMode.SEGMENT_TWO_POINTS, "Две точки"),
        (CreationMode.SEGMENT_LENGTH_ANGLE, "Длина и угол"),
    ],
    PrimitiveType.CIRCLE: [
        (CreationMode.CIRCLE_CENTER_RADIUS, "Центр и радиус"),
        (CreationMode.CIRCLE_CENTER_DIAMETER, "Центр и диаметр"),
        (CreationMode.CIRCLE_TWO_POINTS, "Две точки"),
        (CreationMode.CIRCLE_THREE_POINTS, "Три точки"),
    ],
    PrimitiveType.ARC: [
        (CreationMode.ARC_THREE_POINTS, "Три точки"),
        (CreationMode.ARC_CENTER_ANGLES, "Центр и углы"),
    ],
    PrimitiveType.RECTANGLE: [
        (CreationMode.RECT_TWO_POINTS, "Две точки"),
        (CreationMode.RECT_POINT_SIZE, "Точка и размеры"),
        (CreationMode.RECT_CENTER_SIZE, "Центр и размеры"),
    ],
    PrimitiveType.ELLIPSE: [
        (CreationMode.ELLIPSE_CENTER_AXES, "Центр и оси"),
        (CreationMode.ELLIPSE_BOUNDING_BOX, "Две точки"),
    ],
    PrimitiveType.POLYGON: [(CreationMode.POLYGON_CENTER_RADIUS, "Центр и радиус")],
    PrimitiveType.SPLINE: [(CreationMode.SPLINE_POINTS, "По точкам")],
}

PRIMITIVE_NAMES = {
    PrimitiveType.SEGMENT: "Отрезок",
    PrimitiveType.CIRCLE: "Окружность",
    PrimitiveType.ARC: "Дуга",
    PrimitiveType.RECTANGLE: "Прямоугольник",
    PrimitiveType.ELLIPSE: "Эллипс",
    PrimitiveType.POLYGON: "Многоугольник",
    PrimitiveType.SPLINE: "Сплайн",
}

MODE_POINTS = {
    CreationMode.SEGMENT_TWO_POINTS: 2,
    CreationMode.SEGMENT_LENGTH_ANGLE: 2,
    CreationMode.CIRCLE_CENTER_RADIUS: 2,
    CreationMode.CIRCLE_CENTER_DIAMETER: 2,
    CreationMode.CIRCLE_TWO_POINTS: 2,
    CreationMode.CIRCLE_THREE_POINTS: 3,
    CreationMode.ARC_THREE_POINTS: 3,
    CreationMode.ARC_CENTER_ANGLES: 3,
    CreationMode.RECT_TWO_POINTS: 2,
    CreationMode.RECT_POINT_SIZE: 2,
    CreationMode.RECT_CENTER_SIZE: 2,
    CreationMode.ELLIPSE_CENTER_AXES: 3,
    CreationMode.ELLIPSE_BOUNDING_BOX: 2,
    CreationMode.POLYGON_CENTER_RADIUS: 2,
    CreationMode.SPLINE_POINTS: -1,
}


class DrawTool(Tool):
    """Универсальный инструмент рисования"""
    
    def __init__(self, app):
        super().__init__(app)
        self._primitive_type = PrimitiveType.SEGMENT
        self._creation_mode = CreationMode.SEGMENT_TWO_POINTS
        self._points: List[Tuple[float, float]] = []
        self._temp_point: Optional[Tuple[float, float]] = None
        
        # Параметры
        self._polygon_sides = 6
        self._polygon_inscribed = True
        self._rect_corner_radius = 0.0
        self._rect_chamfer = 0.0
        self._spline_tension = 0.5
        self._arc_use_long_arc = False  # False = короткая дуга, True = длинная дуга (обратное направление)
        
        # Числовой ввод (несколько полей)
        self._input_values = ["", ""]       # Буферы для двух значений
        self._input_field_index = 0         # Какое поле редактируем (0 или 1)
        self._input_active = False
        self._last_cursor_pos = (0, 0)
    
    @property
    def primitive_type(self) -> PrimitiveType:
        return self._primitive_type
    
    @primitive_type.setter
    def primitive_type(self, value: PrimitiveType) -> None:
        if value != self._primitive_type:
            self._primitive_type = value
            modes = PRIMITIVE_MODES.get(value, [])
            if modes:
                self._creation_mode = modes[0][0]
            self._reset_state()
    
    @property
    def creation_mode(self) -> CreationMode:
        return self._creation_mode
    
    @creation_mode.setter
    def creation_mode(self, value: CreationMode) -> None:
        if value != self._creation_mode:
            self._creation_mode = value
            self._reset_state()
            # Синхронизируем UI (левое меню), если доступно
            if hasattr(self.app, "creation_mode_var"):
                self.app.creation_mode_var.set(self._creation_mode.name)
    
    def get_available_modes(self) -> List[Tuple[CreationMode, str]]:
        return PRIMITIVE_MODES.get(self._primitive_type, [])
    
    def get_primitive_name(self) -> str:
        return PRIMITIVE_NAMES.get(self._primitive_type, "")
    
    def _get_snap_point(self, event: tk.Event) -> Tuple[float, float]:
        w, h = self.get_canvas_size()
        px, py = float(event.x), float(event.y)
        self._last_cursor_pos = (px, py)
        
        if hasattr(self.app, 'snap_manager'):
            from_point = self._points[0] if self._points else None
            snap = self.app.snap_manager.find_snap_point(
                px, py, self.app.shape_manager.get_all_shapes(),
                w, h, self.app.view_transform, from_point
            )
            if snap:
                return (snap.x, snap.y)
        
        return self.app.view_transform.screen_to_world(px, py, w, h)
    
    def _get_input_value(self, index: int = 0) -> Optional[float]:
        """Получить введённое значение"""
        if index >= len(self._input_values) or not self._input_values[index]:
            return None
        try:
            return float(self._input_values[index])
        except ValueError:
            return None
    
    def _has_any_input(self) -> bool:
        """Есть ли хоть какой-то ввод"""
        return any(v for v in self._input_values)
    
    def _get_input_fields_config(self) -> List[Tuple[str, str]]:
        """Получить конфигурацию полей ввода: [(label, unit), ...]"""
        mode = self._creation_mode
        n_pts = len(self._points)
        
        # Первая точка: всегда X, Y для всех фигур
        if n_pts == 0:
            return [("X", ""), ("Y", "")]

        if mode == CreationMode.SEGMENT_TWO_POINTS:
            return [("X", ""), ("Y", "")]

        if mode == CreationMode.SEGMENT_LENGTH_ANGLE:
            return [("Длина", ""), ("Угол", "°")]
        
        
        elif mode in (CreationMode.CIRCLE_CENTER_RADIUS, CreationMode.POLYGON_CENTER_RADIUS):
            if n_pts == 1:
                return [("Радиус", "")]
            return [("Радиус", "")]
        
        elif mode == CreationMode.ARC_CENTER_ANGLES:
            if n_pts == 1:
                return [("Радиус", ""), ("Начальный угол", "°")]
            elif n_pts == 2:
                return [("Конечный угол", "°")]
            return [("Радиус", ""), ("Начальный угол", "°")]
        
        elif mode == CreationMode.CIRCLE_CENTER_DIAMETER:
            return [("Диаметр", "")]
        
        elif mode == CreationMode.CIRCLE_TWO_POINTS:
            if n_pts == 0:
                return [("X", ""), ("Y", "")]
            elif n_pts == 1:
                return [("X", ""), ("Y", "")]
            return [("X", ""), ("Y", "")]
        
        elif mode == CreationMode.CIRCLE_THREE_POINTS:
            if n_pts == 0:
                return [("X", ""), ("Y", "")]
            elif n_pts == 1:
                return [("X", ""), ("Y", "")]
            elif n_pts == 2:
                return [("X", ""), ("Y", "")]
            return [("X", ""), ("Y", "")]
        
        elif mode in (CreationMode.RECT_TWO_POINTS, CreationMode.RECT_POINT_SIZE, CreationMode.RECT_CENTER_SIZE):
            return [("Ширина", ""), ("Высота", "")]
        
        elif mode == CreationMode.ELLIPSE_CENTER_AXES:
            if n_pts == 1:
                return [("Полуось X", "")]
            else:
                return [("Полуось Y", "")]

        elif mode == CreationMode.ARC_THREE_POINTS:
            return [("X", ""), ("Y", "")]
        
        return [("Значение", "")]
    
    def _apply_numeric_input(self) -> Optional[Tuple[float, float]]:
        """Применить введённые числовые значения и вычислить точку"""
        v1 = self._get_input_value(0)
        v2 = self._get_input_value(1)
        
        if v1 is None and v2 is None:
            return None
        
        n_pts = len(self._points)

        # Первая точка: использовать введённые X, Y
        if n_pts == 0:
            if v1 is not None and v2 is not None:
                return (v1, v2)
            return None

        cx, cy = self._points[0]
        mode = self._creation_mode
        
        # Вычисляем угол от курсора (для направления)
        w, h = self.get_canvas_size()
        cursor_world = self.app.view_transform.screen_to_world(
            self._last_cursor_pos[0], self._last_cursor_pos[1], w, h
        )
        base_angle = math.atan2(cursor_world[1] - cy, cursor_world[0] - cx)
        
        # Отрезок: X/Y или длина+угол в зависимости от режима
        if mode == CreationMode.SEGMENT_TWO_POINTS:
            if v1 is not None and v2 is not None:
                return (v1, v2)
            return None

        if mode == CreationMode.SEGMENT_LENGTH_ANGLE:
            length = v1 if v1 is not None else math.hypot(cursor_world[0] - cx, cursor_world[1] - cy)
            angle = math.radians(v2) if v2 is not None else base_angle
            return (cx + length * math.cos(angle), cy + length * math.sin(angle))

        # Окружность/многоугольник/дуга - радиус
        elif mode in (CreationMode.CIRCLE_CENTER_RADIUS, CreationMode.POLYGON_CENTER_RADIUS):
            radius = v1 if v1 is not None else math.hypot(cursor_world[0] - cx, cursor_world[1] - cy)
            return (cx + radius * math.cos(base_angle), cy + radius * math.sin(base_angle))
        
        elif mode == CreationMode.CIRCLE_CENTER_DIAMETER:
            diameter = v1 if v1 is not None else math.hypot(cursor_world[0] - cx, cursor_world[1] - cy) * 2
            radius = diameter / 2
            return (cx + radius * math.cos(base_angle), cy + radius * math.sin(base_angle))
        
        elif mode == CreationMode.CIRCLE_TWO_POINTS:
            # Для окружности по двум точкам запрашиваем координаты второй точки
            if v1 is not None and v2 is not None:
                return (v1, v2)
            return None
        
        elif mode == CreationMode.CIRCLE_THREE_POINTS:
            # Для окружности по трём точкам запрашиваем координаты каждой точки
            if v1 is not None and v2 is not None:
                return (v1, v2)
            return None
        
        elif mode == CreationMode.ARC_CENTER_ANGLES:
            n_pts = len(self._points)
            if n_pts == 1:
                # Ввод радиуса и начального угла (в градусах от горизонтали)
                radius = v1 if v1 is not None else math.hypot(cursor_world[0] - cx, cursor_world[1] - cy)
                start_angle_deg = v2 if v2 is not None else math.degrees(base_angle)
                start_angle_rad = math.radians(start_angle_deg)
                return (cx + radius * math.cos(start_angle_rad), cy + radius * math.sin(start_angle_rad))
            elif n_pts == 2:
                # Ввод конечного угла (в градусах от горизонтали)
                radius = math.hypot(self._points[1][0] - cx, self._points[1][1] - cy)
                end_angle_deg = v1 if v1 is not None else math.degrees(base_angle)
                end_angle_rad = math.radians(end_angle_deg)
                return (cx + radius * math.cos(end_angle_rad), cy + radius * math.sin(end_angle_rad))
        
        # Прямоугольник: ширина x высота
        elif mode in (CreationMode.RECT_TWO_POINTS, CreationMode.RECT_POINT_SIZE, CreationMode.RECT_CENTER_SIZE):
            width = v1 if v1 is not None else abs(cursor_world[0] - cx)
            height = v2 if v2 is not None else abs(cursor_world[1] - cy)
            
            # Определяем направление от курсора
            dir_x = 1 if cursor_world[0] >= cx else -1
            dir_y = 1 if cursor_world[1] >= cy else -1
            
            if mode == CreationMode.RECT_CENTER_SIZE:
                return (cx + width * dir_x, cy + height * dir_y)
            else:
                return (cx + width * dir_x, cy + height * dir_y)
        
        # Эллипс - полуось
        elif mode == CreationMode.ELLIPSE_CENTER_AXES:
            value = v1 if v1 is not None else math.hypot(cursor_world[0] - cx, cursor_world[1] - cy)
            return (cx + value * math.cos(base_angle), cy + value * math.sin(base_angle))

        elif mode == CreationMode.ELLIPSE_BOUNDING_BOX:
            # Явный ввод второй точки прямоугольника
            if v1 is not None and v2 is not None:
                return (v1, v2)
            return cursor_world

        elif mode == CreationMode.ARC_THREE_POINTS:
            # Явный ввод координат следующей точки
            if v1 is not None and v2 is not None:
                return (v1, v2)
        
        return None
    
    def on_mouse_down(self, event: tk.Event) -> None:
        if event.num != 1:
            return
        
        # Если есть числовой ввод, используем его
        if self._has_any_input():
            pt = self._apply_numeric_input()
            if pt:
                self._points.append(pt)
                self._clear_input()
                
                required = MODE_POINTS.get(self._creation_mode, 2)
                if required > 0 and len(self._points) >= required:
                    self._create_shape()
                
                self.app.redraw()
                return
        
        self._points.append(self._get_snap_point(event))
        self._clear_input()
        
        required = MODE_POINTS.get(self._creation_mode, 2)
        if required > 0 and len(self._points) >= required:
            self._create_shape()
        
        self.app.redraw()
    
    def on_mouse_move(self, event: tk.Event) -> None:
        self._temp_point = self._get_snap_point(event)
        self.app.redraw()
    
    def on_mouse_up(self, event: tk.Event) -> None:
        pass
    
    def on_key_press(self, event: tk.Event) -> bool:
        key = event.keysym
        char = event.char
        
        # Нормализуем клавиши для проверки (проверяем и keysym, и char)
        key_lower = key.lower() if key else ""
        char_lower = char.lower() if char else ""
        
        # Переключение режима создания текущего примитива (клавиша M)
        if key_lower == 'm' or char_lower == 'm':
            modes = PRIMITIVE_MODES.get(self._primitive_type, [])
            if modes:
                mode_list = [m[0] for m in modes]
                if self._creation_mode in mode_list:
                    idx = mode_list.index(self._creation_mode)
                    # Используем setter, чтобы обновился UI
                    self.creation_mode = mode_list[(idx + 1) % len(mode_list)]
                    self.app.redraw()
                    return True
        
        # Переключение направления дуги (клавиша N) - только для дуги по центру и углам
        if (key_lower == 'n' or char_lower == 'n') and \
           self._creation_mode == CreationMode.ARC_CENTER_ANGLES:
            self._arc_use_long_arc = not self._arc_use_long_arc
            self.app.redraw()
            return True
        
        # Цифры и точка - числовой ввод
        if char and (char.isdigit() or char in '.,-'):
            if char == ',':
                char = '.'
            
            buf = self._input_values[self._input_field_index]
            
            # Проверяем корректность
            if char == '.' and '.' in buf:
                return True
            if char == '-' and buf:
                return True
            
            self._input_values[self._input_field_index] = buf + char
            self._input_active = True
            self.app.redraw()
            return True
        
        # Backspace и Delete (на Mac это разные клавиши)
        if key in ('BackSpace', 'Delete'):
            # Если есть текст в текущем поле - удаляем символ
            if self._input_values[self._input_field_index]:
                self._input_values[self._input_field_index] = self._input_values[self._input_field_index][:-1]
                # Если поле стало пустым, но было активно - оставляем активным
                if not self._input_values[self._input_field_index]:
                    self._input_active = False
                self.app.redraw()
                return True
            
            # Если текущее поле пустое, но есть ввод в другом поле - переключаемся и удаляем там
            if self._has_any_input():
                other_index = 1 - self._input_field_index
                if self._input_values[other_index]:
                    self._input_field_index = other_index
                    self._input_values[self._input_field_index] = self._input_values[self._input_field_index][:-1]
                    if not self._input_values[self._input_field_index]:
                        self._input_active = False
                    self.app.redraw()
                    return True
            
            # Если был активен ввод (даже если поля пустые) - перехватываем, чтобы не удалять фигуры
            if self._input_active:
                self._input_active = False
                self.app.redraw()
                return True
            
            # Если идет процесс создания фигуры (есть точки) - перехватываем Delete,
            # чтобы случайно не удалить уже созданные фигуры
            # Проверяем только _points, т.к. _points очищается только после создания фигуры
            # _temp_point может быть установлен даже когда фигура не создается (при движении мыши)
            if len(self._points) > 0:
                return True  # Перехватываем, чтобы не удалять фигуры во время создания
            
            # Если нет активного ввода и нет точек - не перехватываем, пусть main.py обработает
            return False
        
        # Tab - переключение между полями
        if key == 'Tab':
            fields = self._get_input_fields_config()
            if len(fields) > 1:
                self._input_field_index = (self._input_field_index + 1) % len(fields)
                self.app.redraw()
            return True
        
        # Enter - применить ввод
        if key in ('Return', 'KP_Enter'):
            if self._has_any_input():
                pt = self._apply_numeric_input()
                if pt:
                    self._points.append(pt)
                    self._clear_input()
                    
                    required = MODE_POINTS.get(self._creation_mode, 2)
                    if required > 0 and len(self._points) >= required:
                        self._create_shape()
                    
                    self.app.redraw()
                    return True
            
            # Для сплайна - завершение
            if self._creation_mode == CreationMode.SPLINE_POINTS and len(self._points) >= 2:
                self._create_shape()
                return True
        
        # Escape
        if key == 'Escape':
            if self._has_any_input():
                self._clear_input()
                self.app.redraw()
                return True
            self._reset_state()
            self.app.redraw()
            return True
        
        return False
    
    def _clear_input(self) -> None:
        """Очистить буферы ввода"""
        self._input_values = ["", ""]
        self._input_field_index = 0
        self._input_active = False
    
    def on_right_click(self, event: tk.Event) -> bool:
        if self._creation_mode == CreationMode.SPLINE_POINTS and len(self._points) >= 2:
            self._create_shape()
            return True
        elif self._points:
            self._reset_state()
            self.app.redraw()
            return True
        return False
    
    def _create_shape(self) -> None:
        shape = None
        pts = self._points
        
        try:
            mode = self._creation_mode
            
            if mode in (CreationMode.SEGMENT_TWO_POINTS, CreationMode.SEGMENT_LENGTH_ANGLE) and len(pts) >= 2:
                shape = Segment(pts[0][0], pts[0][1], pts[1][0], pts[1][1])
            
            elif mode == CreationMode.CIRCLE_CENTER_RADIUS and len(pts) >= 2:
                shape = Circle(pts[0][0], pts[0][1], math.hypot(pts[1][0]-pts[0][0], pts[1][1]-pts[0][1]))
            
            elif mode == CreationMode.CIRCLE_CENTER_DIAMETER and len(pts) >= 2:
                shape = Circle(pts[0][0], pts[0][1], math.hypot(pts[1][0]-pts[0][0], pts[1][1]-pts[0][1]) / 2)
            
            elif mode == CreationMode.CIRCLE_TWO_POINTS and len(pts) >= 2:
                shape = Circle.from_two_points(pts[0][0], pts[0][1], pts[1][0], pts[1][1])
            
            elif mode == CreationMode.CIRCLE_THREE_POINTS and len(pts) >= 3:
                shape = Circle.from_three_points(pts[0][0], pts[0][1], pts[1][0], pts[1][1], pts[2][0], pts[2][1])
            
            elif mode == CreationMode.ARC_THREE_POINTS and len(pts) >= 3:
                shape = Arc.from_three_points(pts[0][0], pts[0][1], pts[1][0], pts[1][1], pts[2][0], pts[2][1])
            
            elif mode == CreationMode.ARC_CENTER_ANGLES and len(pts) >= 3:
                cx, cy = pts[0]
                r = math.hypot(pts[1][0]-cx, pts[1][1]-cy)
                # Углы задаются в градусах от горизонтали (0° = вправо, против часовой стрелки)
                # Вычисляем углы от горизонтали на основе позиций точек
                start = math.degrees(math.atan2(pts[1][1]-cy, pts[1][0]-cx))
                end = math.degrees(math.atan2(pts[2][1]-cy, pts[2][0]-cx))
                # Нормализуем углы в диапазон [0, 360)
                while start < 0:
                    start += 360
                while start >= 360:
                    start -= 360
                while end < 0:
                    end += 360
                while end >= 360:
                    end -= 360
                
                # Если выбрана длинная дуга - меняем направление
                if self._arc_use_long_arc:
                    # Вычисляем разность углов
                    ccw_extent = (end - start) % 360  # [0, 360)
                    cw_extent = ccw_extent - 360      # (-360, 0]
                    
                    # Если короткая дуга CCW, делаем длинную CW
                    if abs(ccw_extent) <= abs(cw_extent):
                        # Короткая дуга CCW -> длинная дуга CW
                        end = start + cw_extent
                    else:
                        # Короткая дуга CW -> длинная дуга CCW
                        end = start + ccw_extent
                
                shape = Arc(cx, cy, r, start, end)
            
            elif mode == CreationMode.RECT_TWO_POINTS and len(pts) >= 2:
                shape = Rectangle.from_two_points(pts[0][0], pts[0][1], pts[1][0], pts[1][1],
                                                  self._rect_corner_radius, self._rect_chamfer)
            
            elif mode == CreationMode.RECT_POINT_SIZE and len(pts) >= 2:
                shape = Rectangle(pts[0][0], pts[0][1], pts[1][0]-pts[0][0], pts[1][1]-pts[0][1],
                                  self._rect_corner_radius, self._rect_chamfer)
            
            elif mode == CreationMode.RECT_CENTER_SIZE and len(pts) >= 2:
                w, h = abs(pts[1][0]-pts[0][0])*2, abs(pts[1][1]-pts[0][1])*2
                shape = Rectangle.from_center(pts[0][0], pts[0][1], w, h,
                                              self._rect_corner_radius, self._rect_chamfer)
            
            elif mode == CreationMode.ELLIPSE_CENTER_AXES and len(pts) >= 3:
                shape = Ellipse.from_center_and_axes(pts[0][0], pts[0][1], pts[1][0], pts[1][1], pts[2][0], pts[2][1])
            
            elif mode == CreationMode.ELLIPSE_BOUNDING_BOX and len(pts) >= 2:
                cx = (pts[0][0] + pts[1][0]) / 2
                cy = (pts[0][1] + pts[1][1]) / 2
                rx = abs(pts[1][0] - pts[0][0]) / 2
                ry = abs(pts[1][1] - pts[0][1]) / 2
                shape = Ellipse(cx, cy, rx, ry, 0)
            
            elif mode == CreationMode.POLYGON_CENTER_RADIUS and len(pts) >= 2:
                cx, cy = pts[0]
                r = math.hypot(pts[1][0]-cx, pts[1][1]-cy)
                rot = math.degrees(math.atan2(pts[1][1]-cy, pts[1][0]-cx))
                shape = Polygon(cx, cy, r, self._polygon_sides, self._polygon_inscribed, rot)
            
            elif mode == CreationMode.SPLINE_POINTS and len(pts) >= 2:
                shape = Spline(list(pts), self._spline_tension)
        
        except Exception as e:
            print(f"Ошибка создания: {e}")
        
        if shape:
            shape.line_style_name = self.app.style_manager.get_current_style_name()
            self.app.shape_manager.add_shape(shape)
        
        self._reset_state()
        self.app.redraw()
    
    def _reset_state(self) -> None:
        self._points.clear()
        self._temp_point = None
        self._clear_input()
        # Сбрасываем направление дуги при сбросе состояния
        self._arc_use_long_arc = False
    
    def on_activate(self) -> None:
        self._reset_state()
    
    def on_deactivate(self) -> None:
        self._reset_state()
    
    def get_cursor(self) -> str:
        return "crosshair"
    
    def draw_preview(self, renderer, width: int, height: int, view_transform) -> None:
        if not self._points and not self._temp_point and not self._has_any_input():
            return
        
        if hasattr(self.app, 'snap_manager'):
            self.app.snap_manager.draw_snap_indicator(renderer.canvas, width, height, view_transform)
        
        screen_pts = [view_transform.world_to_screen(px, py, width, height) for px, py in self._points]
        
        # Определяем точку для предпросмотра
        if self._has_any_input() and self._points:
            pt = self._apply_numeric_input()
            if pt:
                temp_screen = view_transform.world_to_screen(pt[0], pt[1], width, height)
            else:
                temp_screen = view_transform.world_to_screen(self._temp_point[0], self._temp_point[1], width, height) if self._temp_point else None
        else:
            temp_screen = view_transform.world_to_screen(self._temp_point[0], self._temp_point[1], width, height) if self._temp_point else None
        
        # Рисуем поставленные точки
        for i, (sx, sy) in enumerate(screen_pts):
            color, size = ("#ffff00", 6) if i == 0 else ("#88ff88", 4)
            renderer.canvas.create_oval(sx-size, sy-size, sx+size, sy+size,
                                        fill=color, outline="#fff", width=1, tags="preview")
        
        if temp_screen:
            self._draw_preview(renderer, screen_pts, temp_screen, width, height, view_transform)
        
        # Рисуем панель числового ввода
        if self._points or self._has_any_input():
            self._draw_input_panel(renderer.canvas, width, height, view_transform)
    
    def _draw_input_panel(self, canvas, width: int, height: int, view_transform) -> None:
        """Отрисовка панели числового ввода"""
        fields = self._get_input_fields_config()
        
        # Вычисляем текущие значения
        if self._points:
            cx, cy = self._points[0]
            if self._temp_point:
                current_dist = math.hypot(self._temp_point[0] - cx, self._temp_point[1] - cy)
                current_angle = math.degrees(math.atan2(self._temp_point[1] - cy, self._temp_point[0] - cx))
                current_dx = abs(self._temp_point[0] - cx)
                current_dy = abs(self._temp_point[1] - cy)
            else:
                current_dist = current_angle = current_dx = current_dy = 0
        else:
            # Для первой точки опорой служит положение курсора
            cursor_world = view_transform.screen_to_world(
                self._last_cursor_pos[0], self._last_cursor_pos[1], width, height
            )
            cx = cy = 0
            current_dist = current_angle = 0
            current_dx, current_dy = cursor_world[0], cursor_world[1]
        
        # Позиция панели
        panel_w = 240
        # Добавляем высоту для индикации направления дуги, если нужно
        extra_height = 20 if (self._creation_mode == CreationMode.ARC_CENTER_ANGLES and len(self._points) >= 2) else 0
        panel_h = 30 + len(fields) * 28 + 24 + extra_height
        panel_x = width - panel_w - 10
        panel_y = height - panel_h - 10
        
        # Фон панели
        canvas.create_rectangle(panel_x, panel_y, panel_x + panel_w, panel_y + panel_h,
                               fill="#2a2a3e", outline="#4a4a5e", width=2, tags="preview")
        
        # Заголовок
        canvas.create_text(panel_x + 10, panel_y + 12, text="Числовой ввод:",
                          fill="#aaaaaa", anchor="w", font=("Arial", 10, "bold"), tags="preview")
        
        # Поля ввода
        y_offset = panel_y + 30
        for i, (label, unit) in enumerate(fields):
            is_active = (i == self._input_field_index)
            
            # Метка
            canvas.create_text(panel_x + 10, y_offset + 10, text=f"{label}:",
                              fill="#cccccc" if is_active else "#888888", anchor="w", 
                              font=("Arial", 10), tags="preview")
            
            # Определяем текущее значение для этого поля
            if i == 0:
                if "Ширина" in label or "Полуось X" in label:
                    current_val = current_dx
                elif "Угол" in label:
                    current_val = current_angle
                elif label == "X":
                    current_val = current_dx
                else:
                    current_val = current_dist
            else:
                if "Высота" in label or "Полуось Y" in label:
                    current_val = current_dy
                elif "Угол" in label:
                    current_val = current_angle
                elif label == "Y":
                    current_val = current_dy
                else:
                    current_val = current_dist
            
            # Поле ввода
            if self._input_values[i]:
                display_value = self._input_values[i]
                bg_color = "#3a5a8a" if is_active else "#3a4a6a"
            else:
                display_value = f"{current_val:.2f}"
                bg_color = "#3a5a8a" if is_active else "#3a3a4e"
            
            field_x = panel_x + 100
            canvas.create_rectangle(field_x, y_offset, field_x + 100, y_offset + 22,
                                   fill=bg_color, outline="#6a6a8e" if is_active else "#4a4a5e", 
                                   width=2 if is_active else 1, tags="preview")
            canvas.create_text(field_x + 5, y_offset + 11, text=display_value + unit,
                              fill="#ffffff", anchor="w", font=("Consolas", 11, "bold"), tags="preview")
            
            # Индикатор активного поля
            if is_active and self._input_values[i]:
                # Курсор
                text_w = len(self._input_values[i]) * 8
                canvas.create_line(field_x + 6 + text_w, y_offset + 4, 
                                  field_x + 6 + text_w, y_offset + 18,
                                  fill="#ffffff", width=2, tags="preview")
            
            y_offset += 28
        
        # Индикация направления дуги (только для дуги по центру и углам)
        if self._creation_mode == CreationMode.ARC_CENTER_ANGLES and len(self._points) >= 2:
            direction_text = "Длинная дуга (N)" if self._arc_use_long_arc else "Короткая дуга (N)"
            direction_color = "#ffaa00" if self._arc_use_long_arc else "#88ff88"
            canvas.create_text(panel_x + 10, y_offset + 8, text=direction_text,
                              fill=direction_color, anchor="w", 
                              font=("Arial", 9, "italic"), tags="preview")
    
    def _draw_preview(self, renderer, screen_pts, temp, w, h, vt) -> None:
        mode = self._creation_mode
        canvas = renderer.canvas
        
        def line(p1, p2, dash=(4, 4)):
            canvas.create_line(p1[0], p1[1], p2[0], p2[1], fill="#88ff88", width=2, dash=dash, tags="preview")
        
        def circle(cx, cy, r):
            canvas.create_oval(cx-r, cy-r, cx+r, cy+r, outline="#88ff88", width=2, dash=(4, 4), tags="preview")
        
        def point(x, y, r=4):
            canvas.create_oval(x-r, y-r, x+r, y+r, fill="#88ff88", outline="", tags="preview")
        
        if mode in (CreationMode.SEGMENT_TWO_POINTS, CreationMode.SEGMENT_LENGTH_ANGLE):
            if screen_pts:
                line(screen_pts[0], temp)
                point(temp[0], temp[1])
        
        elif mode in (CreationMode.CIRCLE_CENTER_RADIUS, CreationMode.CIRCLE_CENTER_DIAMETER):
            if screen_pts:
                r = math.hypot(temp[0]-screen_pts[0][0], temp[1]-screen_pts[0][1])
                if mode == CreationMode.CIRCLE_CENTER_DIAMETER:
                    r /= 2
                circle(screen_pts[0][0], screen_pts[0][1], r)
        
        elif mode == CreationMode.CIRCLE_TWO_POINTS:
            if screen_pts:
                cx, cy = (screen_pts[0][0]+temp[0])/2, (screen_pts[0][1]+temp[1])/2
                r = math.hypot(temp[0]-screen_pts[0][0], temp[1]-screen_pts[0][1]) / 2
                circle(cx, cy, r)
        
        elif mode == CreationMode.CIRCLE_THREE_POINTS:
            for sp in screen_pts:
                line(sp, temp)
        
        elif mode == CreationMode.ARC_THREE_POINTS:
            if len(screen_pts) == 1:
                # Показываем линию от первой точки (начало дуги) до temp (будущий конец)
                line(screen_pts[0], temp)
            elif len(screen_pts) == 2:
                # Показываем превью дуги: от первой точки (начало) до второй (конец)
                # temp - контрольная точка, определяющая выпуклость
                # Преобразуем в мировые координаты для вычисления дуги
                p1_w = vt.screen_to_world(screen_pts[0][0], screen_pts[0][1], w, h)
                p2_w = vt.screen_to_world(screen_pts[1][0], screen_pts[1][1], w, h)
                p3_w = vt.screen_to_world(temp[0], temp[1], w, h)
                
                # Вычисляем дугу
                try:
                    arc = Arc.from_three_points(p1_w[0], p1_w[1], p2_w[0], p2_w[1], p3_w[0], p3_w[1])
                    if arc:
                        # Получаем точки дуги
                        arc_points = arc.get_arc_points(32)
                        # Преобразуем в экранные координаты
                        screen_arc_points = []
                        for px, py in arc_points:
                            sx, sy = vt.world_to_screen(px, py, w, h)
                            screen_arc_points.extend([sx, sy])
                        
                        if len(screen_arc_points) >= 4:
                            canvas.create_line(*screen_arc_points, fill="#88ff88", width=2, dash=(4, 4), smooth=True, tags="preview")
                except:
                    # Если не удалось вычислить дугу, рисуем просто линию
                    line(screen_pts[0], screen_pts[1])
        
        elif mode == CreationMode.ARC_CENTER_ANGLES:
            if len(screen_pts) == 1:
                r = math.hypot(temp[0]-screen_pts[0][0], temp[1]-screen_pts[0][1])
                circle(screen_pts[0][0], screen_pts[0][1], r)
                # Рисуем луч от центра, показывающий начальный угол
                line(screen_pts[0], temp)
            elif len(screen_pts) == 2:
                cx, cy = screen_pts[0]
                r = math.hypot(screen_pts[1][0]-cx, screen_pts[1][1]-cy)
                # Углы задаются в градусах от горизонтали
                start_angle_rad = math.atan2(screen_pts[1][1]-cy, screen_pts[1][0]-cx)
                end_angle_rad = math.atan2(temp[1]-cy, temp[0]-cx)
                
                # Нормализуем углы в градусах
                start_deg = math.degrees(start_angle_rad)
                end_deg = math.degrees(end_angle_rad)
                while start_deg < 0:
                    start_deg += 360
                while start_deg >= 360:
                    start_deg -= 360
                while end_deg < 0:
                    end_deg += 360
                while end_deg >= 360:
                    end_deg -= 360
                
                # Если выбрана длинная дуга - меняем направление
                if self._arc_use_long_arc:
                    ccw_extent = (end_deg - start_deg) % 360
                    cw_extent = ccw_extent - 360
                    if abs(ccw_extent) <= abs(cw_extent):
                        # Короткая дуга CCW -> длинная дуга CW
                        end_deg = start_deg + cw_extent
                    else:
                        # Короткая дуга CW -> длинная дуга CCW
                        end_deg = start_deg + ccw_extent
                    end_angle_rad = math.radians(end_deg)
                    arc_color = "#ffaa00"  # Оранжевый для длинной дуги
                else:
                    arc_color = "#88ff88"  # Зелёный для короткой дуги
                
                # Рисуем дугу как линию
                pts = []
                steps = 32
                for i in range(steps + 1):
                    t = i / steps
                    a = start_angle_rad + (end_angle_rad - start_angle_rad) * t
                    pts.extend([cx + r * math.cos(a), cy + r * math.sin(a)])
                if len(pts) >= 4:
                    canvas.create_line(*pts, fill=arc_color, width=2, dash=(4, 4), smooth=True, tags="preview")
        
        elif mode in (CreationMode.RECT_TWO_POINTS, CreationMode.RECT_POINT_SIZE, CreationMode.RECT_CENTER_SIZE):
            if screen_pts:
                if mode == CreationMode.RECT_CENTER_SIZE:
                    cx, cy = screen_pts[0]
                    hw, hh = abs(temp[0]-cx), abs(temp[1]-cy)
                    x1, y1, x2, y2 = cx-hw, cy-hh, cx+hw, cy+hh
                else:
                    x1, y1, x2, y2 = screen_pts[0][0], screen_pts[0][1], temp[0], temp[1]
                canvas.create_rectangle(x1, y1, x2, y2, outline="#88ff88", width=2, dash=(4, 4), tags="preview")
        
        elif mode == CreationMode.ELLIPSE_CENTER_AXES:
            if len(screen_pts) == 1:
                line(screen_pts[0], temp)
            elif len(screen_pts) == 2:
                # Преобразуем экранные координаты в мировые для правильного вычисления
                cx_w, cy_w = vt.screen_to_world(screen_pts[0][0], screen_pts[0][1], w, h)
                axis1_w = vt.screen_to_world(screen_pts[1][0], screen_pts[1][1], w, h)
                axis2_w = vt.screen_to_world(temp[0], temp[1], w, h)
                
                # Вычисляем параметры эллипса (как в from_center_and_axes)
                rx = math.hypot(axis1_w[0] - cx_w, axis1_w[1] - cy_w)
                ry = math.hypot(axis2_w[0] - cx_w, axis2_w[1] - cy_w)
                rotation = math.radians(math.degrees(math.atan2(axis1_w[1] - cy_w, axis1_w[0] - cx_w)))
                
                # Рисуем эллипс используя правильную формулу (как в get_point_on_ellipse)
                steps = 64
                pts = []
                cos_r, sin_r = math.cos(rotation), math.sin(rotation)
                for i in range(steps + 1):
                    angle = i * 360 / steps
                    angle_rad = math.radians(angle)
                    # Параметрическое уравнение эллипса в локальных координатах
                    x_local = rx * math.cos(angle_rad)
                    y_local = ry * math.sin(angle_rad)
                    # Поворот и перенос
                    x_world = x_local * cos_r - y_local * sin_r + cx_w
                    y_world = x_local * sin_r + y_local * cos_r + cy_w
                    # Преобразуем обратно в экранные координаты
                    sx, sy = vt.world_to_screen(x_world, y_world, w, h)
                    pts.extend([sx, sy])
                if len(pts) >= 4:
                    canvas.create_line(*pts, fill="#88ff88", width=2, dash=(4, 4), smooth=True, tags="preview")

        elif mode == CreationMode.ELLIPSE_BOUNDING_BOX:
            if screen_pts:
                x1, y1 = screen_pts[0]
                x2, y2 = temp
                canvas.create_oval(min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2),
                                   outline="#88ff88", width=2, dash=(4, 4), tags="preview")
        
        elif mode == CreationMode.POLYGON_CENTER_RADIUS:
            if screen_pts:
                cx, cy = screen_pts[0]
                r = math.hypot(temp[0]-cx, temp[1]-cy)
                if not self._polygon_inscribed:
                    r = r / math.cos(math.pi / self._polygon_sides)
                rot = math.atan2(temp[1]-cy, temp[0]-cx)
                pts = []
                for i in range(self._polygon_sides):
                    angle = rot + i * 2 * math.pi / self._polygon_sides
                    pts.extend([cx + r * math.cos(angle), cy + r * math.sin(angle)])
                pts.extend(pts[:2])
                canvas.create_line(*pts, fill="#88ff88", width=2, dash=(4, 4), tags="preview")
        
        elif mode == CreationMode.SPLINE_POINTS:
            all_pts = screen_pts + [temp]
            for i in range(len(all_pts) - 1):
                line(all_pts[i], all_pts[i+1])
            point(temp[0], temp[1])
    
    # Методы для UI
    def set_polygon_sides(self, sides: int) -> None:
        self._polygon_sides = max(3, min(100, sides))
    
    def get_polygon_sides(self) -> int:
        return self._polygon_sides
    
    def set_polygon_inscribed(self, inscribed: bool) -> None:
        self._polygon_inscribed = inscribed
    
    def is_polygon_inscribed(self) -> bool:
        return self._polygon_inscribed
    
    def set_rect_corner_radius(self, radius: float) -> None:
        self._rect_corner_radius = max(0, radius)
    
    def get_rect_corner_radius(self) -> float:
        return self._rect_corner_radius
    
    def set_rect_chamfer(self, chamfer: float) -> None:
        self._rect_chamfer = max(0, chamfer)
    
    def get_rect_chamfer(self) -> float:
        return self._rect_chamfer
    
    def set_spline_tension(self, tension: float) -> None:
        self._spline_tension = max(0, min(1, tension))
    
    def get_spline_tension(self) -> float:
        return self._spline_tension
