"""Инструмент для простановки размерных линий"""
import math
import tkinter as tk
from typing import Optional, List, Tuple
from .base import Tool
from shapes import Dimension, LinearDimension, RadialDimension, AngularDimension, Segment, Circle, Arc
from managers import SnapType


class DimensionTool(Tool):
    """Инструмент для создания размеров"""
    
    def __init__(self, app):
        super().__init__(app)
        self.mode = "linear" # 'linear', 'radius', 'diameter', 'angular'
        
        self.points: List[Tuple[float, float, str, str]] = []  # (x, y, shape_id, click_id)
        self.current_dim: Optional[Dimension] = None
        
        # Для углового размера нам нужно выбрать 2 отрезка
        self.lines: List[Segment] = []
        self.circle_arc = None
        
    def set_mode(self, mode: str) -> None:
        self.mode = mode
        self.reset()
        
    def reset(self) -> None:
        if self.current_dim and self.current_dim in self.app.shape_manager.get_all_shapes():
            # Если мы не закончили фигуру, удаляем черновик
            self.app.shape_manager.remove_shape(self.current_dim)
        self.points.clear()
        self.lines.clear()
        self.circle_arc = None
        self.current_dim = None
        self.app.redraw()
        
    def on_mouse_down(self, event: tk.Event) -> None:
        w, h = self.get_canvas_size()
        wx, wy = self.app.view_transform.screen_to_world(event.x, event.y, w, h)
        
        rx, ry, snap_type, snap_shape = self.app.snap_manager.get_snap(event.x, event.y, w, h, self.app.view_transform, self.app.shape_manager)
        
        # Если привязка сработала, используем её координаты
        if snap_type:
            wx, wy = rx, ry
        
        shape_id = snap_shape.id if snap_shape else None
        point_id = snap_type if snap_type else None
            
        if self.mode == "linear":
            if len(self.points) == 0:
                self.points.append((wx, wy, shape_id, point_id))
            elif len(self.points) == 1:
                self.points.append((wx, wy, shape_id, point_id))
                self.current_dim = LinearDimension((self.points[0][0], self.points[0][1]), (wx, wy), offset=0.0)
                self.current_dim.base_shape_id1 = self.points[0][2]
                self.current_dim.base_point_id1 = self.points[0][3]
                self.current_dim.base_shape_id2 = shape_id
                self.current_dim.base_point_id2 = point_id
                self.app.shape_manager.add_shape(self.current_dim)
            elif len(self.points) == 2:
                # Фиксация offset
                self.current_dim = None
                self.points.clear()
                
        elif self.mode in ("radius", "diameter"):
            if self.circle_arc is None:
                # Выбор окружности/дуги
                clicked_shape = None
                for shape in reversed(self.app.shape_manager.get_all_shapes()):
                    if isinstance(shape, (Circle, Arc)):
                        dist = shape.distance_to_point(event.x, event.y, w, h, self.app.view_transform)
                        if dist < 10:
                            clicked_shape = shape
                            break
                
                if clicked_shape:
                    self.circle_arc = clicked_shape
                    cx, cy = getattr(clicked_shape, 'x', 0), getattr(clicked_shape, 'y', 0)
                    if hasattr(clicked_shape, 'cx'): cx = clicked_shape.cx
                    if hasattr(clicked_shape, 'cy'): cy = clicked_shape.cy
                    
                    self.current_dim = RadialDimension(cx, cy, clicked_shape.radius, is_diameter=(self.mode == "diameter"))
                    self.current_dim.base_shape_id = clicked_shape.id
                    self.app.shape_manager.add_shape(self.current_dim)
            else:
                self.current_dim = None
                self.circle_arc = None
                self.points.clear()
                
        elif self.mode == "angular":
            if len(self.lines) < 2:
                clicked_shape = None
                for shape in reversed(self.app.shape_manager.get_all_shapes()):
                    if isinstance(shape, Segment):
                        dist = shape.distance_to_point(event.x, event.y, w, h, self.app.view_transform)
                        if dist < 10:
                            clicked_shape = shape
                            break
                            
                if clicked_shape:
                    self.lines.append(clicked_shape)
                    if len(self.lines) == 2:
                        # Пересечение прямых для нахождения центра
                        l1, l2 = self.lines[0], self.lines[1]
                        import core
                        # Упрощенное нахождение пересечения для AngularDimension (в идеале нужно искать пересечение)
                        # Пока временно возьмем первую общую точку (если привязаны) или середину между концами
                        cx = (l1.x1 + l1.x2 + l2.x1 + l2.x2) / 4
                        cy = (l1.y1 + l1.y2 + l2.y1 + l2.y2) / 4
                        
                        self.current_dim = AngularDimension(cx, cy, (l1.x1, l1.y1), (l2.x1, l2.y1))
                        self.current_dim.base_shape_id1 = l1.id
                        self.current_dim.base_shape_id2 = l2.id
                        self.app.shape_manager.add_shape(self.current_dim)
            else:
                self.current_dim = None
                self.lines.clear()

        self.app.redraw()

    def on_mouse_move(self, event: tk.Event) -> None:
        w, h = self.get_canvas_size()
        wx, wy = self.app.view_transform.screen_to_world(event.x, event.y, w, h)
        
        if self.current_dim:
            if isinstance(self.current_dim, LinearDimension):
                dx = self.current_dim.p2_x - self.current_dim.p1_x
                dy = self.current_dim.p2_y - self.current_dim.p1_y
                angle = math.atan2(dy, dx)
                # Дистанция от мыши до прямой
                mx, my = wx - self.current_dim.p1_x, wy - self.current_dim.p1_y
                # Проекция на нормаль
                nx, ny = -math.sin(angle), math.cos(angle)
                offset_world = mx * nx + my * ny
                self.current_dim.offset = offset_world
                
            elif isinstance(self.current_dim, RadialDimension):
                dx = wx - self.current_dim.cx
                dy = wy - self.current_dim.cy
                self.current_dim.angle_rad = math.atan2(dy, dx)
                
            elif isinstance(self.current_dim, AngularDimension):
                dist = math.hypot(wx - self.current_dim.cx, wy - self.current_dim.cy)
                self.current_dim.radius = dist
                
            self.app.redraw()

    def on_mouse_up(self, event: tk.Event) -> None:
        pass

    def on_right_click(self, event: tk.Event) -> bool:
        """Правый клик сбрасывает текущее построение"""
        if self.points or self.lines or self.circle_arc:
            self.reset()
            return True
        return False
        
    def on_key_press(self, event: tk.Event) -> bool:
        if event.keysym.lower() == 'escape':
            self.reset()
            return True
        return False

    def on_activate(self) -> None:
        self.reset()
        
    def on_deactivate(self) -> None:
        self.reset()

    def get_cursor(self) -> str:
        return "crosshair"
