"""Основные компоненты приложения: геометрия, рендеринг, UI, утилиты"""
import math
import tkinter as tk
from tkinter import ttk
from typing import List


# ГЕОМЕТРИЯ И КООРДИНАТЫ

class CoordinateConverter:
    """Конвертация между системами координат"""
    
    @staticmethod
    def polar_to_cartesian(r: float, theta: float, is_degrees: bool = True) -> tuple[float, float]:
        angle_rad = math.radians(theta) if is_degrees else theta
        return r * math.cos(angle_rad), r * math.sin(angle_rad)

    @staticmethod
    def cartesian_to_polar(x: float, y: float, is_degrees: bool = True) -> tuple[float, float]:
        r = math.hypot(x, y)
        angle_rad = math.atan2(y, x)
        return r, math.degrees(angle_rad) if is_degrees else angle_rad


class SegmentGeometry:
    """Геометрические расчёты для отрезков"""
    
    @staticmethod
    def calculate_length(x1: float, y1: float, x2: float, y2: float) -> float:
        return math.hypot(x2 - x1, y2 - y1)

    @staticmethod
    def calculate_angle(x1: float, y1: float, x2: float, y2: float, is_degrees: bool = True) -> float:
        angle_rad = math.atan2(y2 - y1, x2 - x1)
        return math.degrees(angle_rad) if is_degrees else angle_rad

    @staticmethod
    def point_to_segment_distance(px: float, py: float, x1: float, y1: float, x2: float, y2: float) -> float:
        dx, dy = x2 - x1, y2 - y1
        seg_len2 = dx * dx + dy * dy
        if seg_len2 == 0:
            return math.hypot(px - x1, py - y1)
        t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / seg_len2))
        return math.hypot(px - (x1 + t * dx), py - (y1 + t * dy))


# РЕНДЕРИНГ НА CANVAS

class CanvasRenderer:
    """Класс для отрисовки на Canvas"""
    
    def __init__(self, canvas: tk.Canvas):
        self.canvas = canvas
        self.color_bg = "#111111"
        self.color_grid = "#2a2a2a"
        self.color_axis_x = "#ff4444"
        self.color_axis_y = "#44ff44"
        self.style_manager = None  # Будет установлен извне

    def draw_grid(self, width: int, height: int, grid_manager, view_transform) -> None:
        """Отрисовка сетки и осей с учётом трансформации
        
        Args:
            width, height: Размеры canvas
            grid_manager: Менеджер сетки (GridManager)
            view_transform: Трансформация вида
        """
        self.canvas.delete("grid", "axes")
        
        if not grid_manager.visible:
            # Даже если сетка скрыта, рисуем оси
            self._draw_axes(width, height, view_transform)
            return
        
        # Видимая область в мировых координатах
        # Проверяем все 4 угла для корректной работы при повороте
        corners = [
            view_transform.screen_to_world(0, 0, width, height),
            view_transform.screen_to_world(width, 0, width, height),
            view_transform.screen_to_world(0, height, width, height),
            view_transform.screen_to_world(width, height, width, height)
        ]
        min_x = min(c[0] for c in corners)
        max_x = max(c[0] for c in corners)
        min_y = min(c[1] for c in corners)
        max_y = max(c[1] for c in corners)
        
        # Добавляем запас для плавной прокрутки
        margin = grid_manager.get_visual_step(view_transform.scale) * 2
        min_x -= margin
        max_x += margin
        min_y -= margin
        max_y += margin
        
        # Получаем линии сетки от GridManager
        minor_v, minor_h, major_v, major_h = grid_manager.get_grid_lines(
            min_x, max_x, min_y, max_y, view_transform.scale
        )
        
        # Цвета для разных типов линий
        color_minor = self.color_grid
        color_major = self._lighten_color(self.color_grid, 0.3)  # Чуть ярче
        
        # Малые вертикальные линии
        for x in minor_v:
            sx1, sy1 = view_transform.world_to_screen(x, min_y, width, height)
            sx2, sy2 = view_transform.world_to_screen(x, max_y, width, height)
            self.canvas.create_line(sx1, sy1, sx2, sy2, fill=color_minor, tags="grid")
        
        # Малые горизонтальные линии
        for y in minor_h:
            sx1, sy1 = view_transform.world_to_screen(min_x, y, width, height)
            sx2, sy2 = view_transform.world_to_screen(max_x, y, width, height)
            self.canvas.create_line(sx1, sy1, sx2, sy2, fill=color_minor, tags="grid")
        
        # Крупные вертикальные линии
        for x in major_v:
            sx1, sy1 = view_transform.world_to_screen(x, min_y, width, height)
            sx2, sy2 = view_transform.world_to_screen(x, max_y, width, height)
            self.canvas.create_line(sx1, sy1, sx2, sy2, fill=color_major, tags="grid")
        
        # Крупные горизонтальные линии
        for y in major_h:
            sx1, sy1 = view_transform.world_to_screen(min_x, y, width, height)
            sx2, sy2 = view_transform.world_to_screen(max_x, y, width, height)
            self.canvas.create_line(sx1, sy1, sx2, sy2, fill=color_major, tags="grid")
        
        # Оси координат (поверх сетки)
        self._draw_axes(width, height, view_transform, min_x, max_x, min_y, max_y)
    
    def _draw_axes(self, width: int, height: int, view_transform, 
                   min_x: float = None, max_x: float = None,
                   min_y: float = None, max_y: float = None) -> None:
        """Отрисовка осей координат"""
        # Если границы не заданы, вычисляем их
        if min_x is None:
            corners = [
                view_transform.screen_to_world(0, 0, width, height),
                view_transform.screen_to_world(width, 0, width, height),
                view_transform.screen_to_world(0, height, width, height),
                view_transform.screen_to_world(width, height, width, height)
            ]
            min_x = min(c[0] for c in corners)
            max_x = max(c[0] for c in corners)
            min_y = min(c[1] for c in corners)
            max_y = max(c[1] for c in corners)
        
        # Ось Y (вертикальная, зелёная)
        p1 = view_transform.world_to_screen(0, min_y, width, height)
        p2 = view_transform.world_to_screen(0, max_y, width, height)
        self.canvas.create_line(*p1, *p2, fill=self.color_axis_y, width=2, tags="axes")
        
        # Ось X (горизонтальная, красная)
        p1 = view_transform.world_to_screen(min_x, 0, width, height)
        p2 = view_transform.world_to_screen(max_x, 0, width, height)
        self.canvas.create_line(*p1, *p2, fill=self.color_axis_x, width=2, tags="axes")
    
    def _lighten_color(self, hex_color: str, factor: float) -> str:
        """Осветлить цвет на заданный фактор (0-1)"""
        hex_color = hex_color.lstrip('#')
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        
        r = min(255, int(r + (255 - r) * factor))
        g = min(255, int(g + (255 - g) * factor))
        b = min(255, int(b + (255 - b) * factor))
        
        return f"#{r:02x}{g:02x}{b:02x}"

    def draw_shapes(self, shapes: List, width: int, height: int, view_transform, point_radius: int = 4) -> None:
        """Отрисовка всех фигур"""
        self.clear_objects("shape")
        for shape in shapes:
            shape.draw(self, width, height, view_transform, point_radius)

    def draw_axis_indicator(self, width: int, height: int, view_transform) -> None:
        """Индикатор осей в углу экрана"""
        margin, axis_length = 60, 35
        origin_x, origin_y = width - margin, height - margin
        
        angle_rad = math.radians(view_transform.rotation)
        cos_a, sin_a = math.cos(angle_rad), math.sin(angle_rad)
        
        # Ось X (красная)
        x_end_x, x_end_y = origin_x + axis_length * cos_a, origin_y - axis_length * sin_a
        self.canvas.create_line(origin_x, origin_y, x_end_x, x_end_y, 
                                fill=self.color_axis_x, width=3, tags="axis_indicator", 
                                arrow=tk.LAST, arrowshape=(8, 10, 4))
        self.canvas.create_text(x_end_x + 10 * cos_a, x_end_y - 10 * sin_a, 
                                text="X", fill=self.color_axis_x, font=("Arial", 12, "bold"), 
                                tags="axis_indicator")
        
        # Ось Y (зелёная)
        y_end_x, y_end_y = origin_x - axis_length * sin_a, origin_y - axis_length * cos_a
        self.canvas.create_line(origin_x, origin_y, y_end_x, y_end_y, 
                                fill=self.color_axis_y, width=3, tags="axis_indicator", 
                                arrow=tk.LAST, arrowshape=(8, 10, 4))
        self.canvas.create_text(y_end_x - 10 * sin_a, y_end_y - 10 * cos_a, 
                                text="Y", fill=self.color_axis_y, font=("Arial", 12, "bold"), 
                                tags="axis_indicator")
        
        # Центральная точка
        self.canvas.create_oval(origin_x - 3, origin_y - 3, origin_x + 3, origin_y + 3, 
                                fill="#ffffff", outline="", tags="axis_indicator")
    
    def clear_objects(self, *tags: str) -> None:
        """Очистка объектов по тегам"""
        for tag in tags:
            self.canvas.delete(tag)


# UI КОМПОНЕНТЫ

class UIBuilder:
    """Вспомогательный класс для создания UI элементов"""
    
    @staticmethod
    def create_radiobutton_group(parent: ttk.Frame, title: str, options: list[tuple[str, str]], 
        variable: tk.StringVar, command) -> ttk.LabelFrame:
        """Создание группы радиокнопок"""
        group = ttk.LabelFrame(parent, text=title)
        group.pack(fill=tk.X, padx=8, pady=8)
        row = ttk.Frame(group)
        row.pack(fill=tk.X, padx=6, pady=4)
        for idx, (text, value) in enumerate(options):
            ttk.Radiobutton(row, text=text, value=value, variable=variable, 
                command=command).pack(side=tk.LEFT, padx=(0 if idx == 0 else 12))
        return group

    @staticmethod
    def create_coord_inputs(parent: ttk.Frame, fields: list[tuple[str, tk.DoubleVar]], on_change_callback) -> None:
        """Создание полей ввода координат"""
        for idx, (label_text, var) in enumerate(fields):
            if idx > 0:
                ttk.Label(parent, text="  ").pack(side=tk.LEFT)
            ttk.Label(parent, text=label_text).pack(side=tk.LEFT)
            entry = ttk.Entry(parent, textvariable=var, width=8)
            entry.pack(side=tk.LEFT, padx=2)
            entry.bind("<Return>", lambda e: on_change_callback())
            entry.bind("<FocusOut>", lambda e: on_change_callback())

    @staticmethod
    def update_text_widget(text_widget: tk.Text, content: str) -> None:
        """Безопасное обновление текстового виджета"""
        text_widget.configure(state=tk.NORMAL)
        text_widget.delete("1.0", tk.END)
        text_widget.insert(tk.END, content)
        text_widget.configure(state=tk.DISABLED)


# УТИЛИТЫ

def format_number(value: float) -> str:
    """Форматирование числа для отображения"""
    return f"{value:,.2f}".replace(",", " ") if abs(value) >= 1000 else f"{value:.4g}"


def format_segment_info(x1: float, y1: float, x2: float, y2: float, is_degrees: bool = True) -> str:
    """Форматирование информации об отрезке"""
    r1, theta1 = CoordinateConverter.cartesian_to_polar(x1, y1, is_degrees)
    dx, dy = x2 - x1, y2 - y1
    r2, theta2 = CoordinateConverter.cartesian_to_polar(dx, dy, is_degrees)
    angle_unit = "°" if is_degrees else " рад"
    length = SegmentGeometry.calculate_length(x1, y1, x2, y2)
    angle = SegmentGeometry.calculate_angle(x1, y1, x2, y2, is_degrees)
    
    fn = format_number
    return (
        f"Точка 1:\n"
        f"  декартовы: x₁ = {fn(x1)},  y₁ = {fn(y1)}\n"
        f"  полярные (от начала): r₁ = {fn(r1)},  θ₁ = {fn(theta1)}{angle_unit}\n\n"
        f"Точка 2:\n"
        f"  декартовы: x₂ = {fn(x2)},  y₂ = {fn(y2)}\n"
        f"  полярные (от точки 1): r₂ = {fn(r2)},  θ₂ = {fn(theta2)}{angle_unit}\n\n"
        f"Отрезок:\n"
        f"  длина |AB| = {fn(length)}\n"
        f"  угол наклона = {fn(angle)}{angle_unit}\n\n"
        f"Примечание: θ₂ = 0° означает направление вправо от точки 1"
    )
