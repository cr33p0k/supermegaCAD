"""Инструмент для выделения и перемещения фигур"""
import math
import tkinter as tk
from typing import Optional, Tuple, Any
from .base import Tool


class SelectTool(Tool):
    """Инструмент выделения и перемещения фигур"""
    
    THRESHOLD_DISTANCE = 8.0  # Расстояние для выбора фигуры
    CONTROL_POINT_RADIUS = 6
    CONTROL_POINT_HIT_RADIUS = 10
    
    def __init__(self, app):
        super().__init__(app)
        
        # Для перетаскивания
        self._dragging_shape: Optional[Any] = None
        self._drag_start: Optional[Tuple[float, float]] = None
        
        # Для редактирования контрольных точек
        self._dragging_point: Optional[Tuple[Any, str]] = None
    
    def on_mouse_down(self, event: tk.Event) -> None:
        """Обработка нажатия левой кнопки мыши"""
        if event.num != 1:
            return
        
        w, h = self.get_canvas_size()
        px, py = float(event.x), float(event.y)
        
        # Сначала проверяем контрольные точки выделенной фигуры
        selected = self.app.shape_manager.get_selected_shape()
        
        if selected and hasattr(selected, 'get_control_points'):
            control_point = self._find_control_point(selected, px, py, w, h)
            if control_point:
                self._dragging_point = (selected, control_point)
                return
        
        # Ищем фигуру под курсором
        shapes = self.app.shape_manager.get_all_shapes()
        if not shapes:
            self.app.shape_manager.deselect_all()
            self.app.redraw()
            return
        
        best_shape = min(shapes, key=lambda s: s.distance_to_point(px, py, w, h, self.app.view_transform))
        best_distance = best_shape.distance_to_point(px, py, w, h, self.app.view_transform)
        
        if best_distance <= self.THRESHOLD_DISTANCE:
            self.app.shape_manager.select_shape(best_shape)
            
            # Начинаем перетаскивание
            world_x, world_y = self.app.view_transform.screen_to_world(px, py, w, h)
            self._dragging_shape = best_shape
            self._drag_start = (world_x, world_y)
        else:
            self.app.shape_manager.deselect_all()
        
        self.app.redraw()
    
    def on_mouse_move(self, event: tk.Event) -> None:
        """Обработка движения мыши"""
        w, h = self.get_canvas_size()
        px, py = float(event.x), float(event.y)
        
        # Перетаскивание контрольной точки
        if self._dragging_point:
            shape, point_id = self._dragging_point
            
            # Применяем привязки
            world_point = self._get_snap_point(event)
            
            if hasattr(shape, 'move_control_point'):
                shape.move_control_point(point_id, world_point[0], world_point[1])
            
            # Обновляем панель свойств в реальном времени
            if hasattr(self.app, 'properties_panel'):
                self.app.properties_panel.refresh()
            
            self.app.redraw()
            return
        
        # Перетаскивание фигуры
        if self._dragging_shape and self._drag_start:
            world_x, world_y = self.app.view_transform.screen_to_world(px, py, w, h)
            dx = world_x - self._drag_start[0]
            dy = world_y - self._drag_start[1]
            
            self._dragging_shape.translate(dx, dy)
            self._drag_start = (world_x, world_y)
            
            # Обновляем панель свойств в реальном времени
            if hasattr(self.app, 'properties_panel'):
                self.app.properties_panel.refresh()
            
            self.app.redraw()
    
    def on_mouse_up(self, event: tk.Event) -> None:
        """Обработка отпускания кнопки мыши"""
        self._dragging_point = None
        self._dragging_shape = None
        self._drag_start = None
    
    def _get_snap_point(self, event: tk.Event) -> Tuple[float, float]:
        """Получить точку с учётом привязок"""
        w, h = self.get_canvas_size()
        px, py = float(event.x), float(event.y)
        
        if hasattr(self.app, 'snap_manager'):
            snap = self.app.snap_manager.find_snap_point(
                px, py,
                self.app.shape_manager.get_all_shapes(),
                w, h,
                self.app.view_transform
            )
            if snap:
                return (snap.x, snap.y)
        
        return self.app.view_transform.screen_to_world(px, py, w, h)
    
    def _find_control_point(self, shape: Any, px: float, py: float,
                            w: int, h: int) -> Optional[str]:
        """Найти контрольную точку под курсором"""
        if not hasattr(shape, 'get_control_points'):
            return None
        
        control_points = shape.get_control_points()
        
        for point_id, wx, wy in control_points:
            sx, sy = self.app.view_transform.world_to_screen(wx, wy, w, h)
            dist = math.hypot(px - sx, py - sy)
            
            if dist <= self.CONTROL_POINT_HIT_RADIUS:
                return point_id
        
        return None
    
    def on_activate(self) -> None:
        """Активация инструмента"""
        pass
    
    def on_deactivate(self) -> None:
        """Деактивация инструмента"""
        self._dragging_point = None
        self._dragging_shape = None
        self._drag_start = None
    
    def get_cursor(self) -> str:
        """Курсор для режима выделения"""
        return "arrow"
    
    def draw_control_points(self, renderer, width: int, height: int, view_transform) -> None:
        """Отрисовка контрольных точек выделенной фигуры"""
        renderer.canvas.delete("control_points")
        
        selected = self.app.shape_manager.get_selected_shape()
        if not selected or not hasattr(selected, 'get_control_points'):
            return
        
        control_points = selected.get_control_points()
        
        for point_id, wx, wy in control_points:
            sx, sy = view_transform.world_to_screen(wx, wy, width, height)
            r = self.CONTROL_POINT_RADIUS
            
            # Разные цвета для разных типов точек
            if 'center' in point_id:
                fill = "#ff00ff"
                outline = "#ffffff"
            elif 'start' in point_id or 'end' in point_id or 'corner' in point_id:
                fill = "#00ffff"
                outline = "#ffffff"
            else:
                fill = "#ffff00"
                outline = "#ffffff"
            
            renderer.canvas.create_rectangle(
                sx - r, sy - r, sx + r, sy + r,
                fill=fill, outline=outline, width=2,
                tags="control_points"
            )
        
        # Отрисовка индикатора привязки (при перетаскивании)
        if (self._dragging_point or self._dragging_shape) and hasattr(self.app, 'snap_manager'):
            self.app.snap_manager.draw_snap_indicator(
                renderer.canvas, width, height, view_transform
            )
