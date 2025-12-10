"""Обработчик навигации (средняя кнопка мыши, колесико, инструмент "Рука")"""
import tkinter as tk
import math
from typing import Optional


class NavigationHandler:
    """Универсальный класс для всех навигационных операций"""
    
    def __init__(self, app):
        self.app = app
        self.is_panning = False
        self.last_x: Optional[float] = None
        self.last_y: Optional[float] = None
    
    def _pan(self, dx: float, dy: float) -> None:
        """Внутренний метод панорамирования с учётом поворота"""
        rotation = self.app.view_transform.rotation
        if rotation != 0:
            angle_rad = math.radians(rotation)
            cos_a, sin_a = math.cos(angle_rad), math.sin(angle_rad)
            dx, dy = dx * cos_a - dy * sin_a, dx * sin_a + dy * cos_a
        self.app.view_transform.pan(dx, -dy)
        self.app.redraw()
    
    def handle_middle_button_down(self, event: tk.Event) -> None:
        """Начало панорамирования средней кнопкой"""
        if event.num == 2:
            self.is_panning = True
            self.last_x, self.last_y = float(event.x), float(event.y)
            self.app.canvas.config(cursor="fleur")
    
    def handle_middle_button_up(self, event: tk.Event) -> None:
        """Завершение панорамирования средней кнопкой"""
        if event.num == 2:
            self.is_panning = False
            self.last_x = self.last_y = None
            self.app.update_cursor()
    
    def handle_mouse_move(self, event: tk.Event) -> None:
        """Панорамирование средней кнопкой"""
        if self.is_panning and self.last_x is not None:
            self._pan(event.x - self.last_x, event.y - self.last_y)
            self.last_x, self.last_y = float(event.x), float(event.y)
    
    def handle_mouse_wheel(self, event: tk.Event) -> None:
        """Масштабирование колесиком относительно курсора"""
        factor = 1.1 if (event.delta > 0 or event.num == 4) else 0.9 if (event.delta < 0 or event.num == 5) else None
        if factor is None:
            return
        
        w, h = self.app.canvas.winfo_width(), self.app.canvas.winfo_height()
        world_x, world_y = self.app.view_transform.screen_to_world(event.x, event.y, w, h)
        old_scale = self.app.view_transform.scale
        new_scale = max(self.app.view_transform.min_scale, min(self.app.view_transform.max_scale, old_scale * factor))
        
        # Масштабирование с сохранением точки под курсором
        offset_x = world_x * old_scale + self.app.view_transform.offset_x
        offset_y = world_y * old_scale + self.app.view_transform.offset_y
        self.app.view_transform.scale = new_scale
        self.app.view_transform.offset_x = offset_x - world_x * new_scale
        self.app.view_transform.offset_y = offset_y - world_y * new_scale
        
        self.app.redraw()
        self.app.update_status_bar()

