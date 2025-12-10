"""Инструмент панорамирования (Рука)"""
import tkinter as tk
from .base import Tool


class PanTool(Tool):
    """Инструмент для панорамирования холста"""
    
    def on_mouse_down(self, event: tk.Event) -> None:
        if event.num == 1:
            nav = self.app.navigation_handler
            nav.is_panning = True
            nav.last_x, nav.last_y = float(event.x), float(event.y)
            self.app.update_cursor()
    
    def on_mouse_move(self, event: tk.Event) -> None:
        nav = self.app.navigation_handler
        if nav.is_panning and nav.last_x is not None:
            nav._pan(event.x - nav.last_x, event.y - nav.last_y)
            nav.last_x, nav.last_y = float(event.x), float(event.y)
    
    def on_mouse_up(self, event: tk.Event) -> None:
        if event.num == 1:
            nav = self.app.navigation_handler
            nav.is_panning = False
            nav.last_x = nav.last_y = None
            self.app.update_cursor()
    
    def on_activate(self) -> None:
        nav = self.app.navigation_handler
        nav.is_panning = False
        nav.last_x = nav.last_y = None
    
    def on_deactivate(self) -> None:
        nav = self.app.navigation_handler
        nav.is_panning = False
        nav.last_x = nav.last_y = None
    
    def get_cursor(self) -> str:
        return "fleur" if self.app.navigation_handler.is_panning else "hand2"

