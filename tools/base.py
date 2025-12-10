"""Базовый абстрактный класс для инструментов"""
from abc import ABC, abstractmethod
from typing import Any, Optional
import tkinter as tk


class Tool(ABC):
    """Абстрактный базовый класс для всех инструментов"""
    
    def __init__(self, app: Any):
        self.app = app
    
    @abstractmethod
    def on_mouse_down(self, event: tk.Event) -> None:
        """Обработка нажатия кнопки мыши"""
        pass
    
    @abstractmethod
    def on_mouse_move(self, event: tk.Event) -> None:
        """Обработка движения мыши"""
        pass
    
    @abstractmethod
    def on_mouse_up(self, event: tk.Event) -> None:
        """Обработка отпускания кнопки мыши"""
        pass
    
    @abstractmethod
    def on_activate(self) -> None:
        """Вызывается при активации инструмента"""
        pass
    
    @abstractmethod
    def on_deactivate(self) -> None:
        """Вызывается при деактивации инструмента"""
        pass
    
    @abstractmethod
    def get_cursor(self) -> str:
        """Возвращает курсор для этого инструмента"""
        pass
    
    def get_canvas_size(self) -> tuple[int, int]:
        """Вспомогательный метод для получения размеров canvas"""
        w = int(self.app.canvas.winfo_width())
        h = int(self.app.canvas.winfo_height())
        return w, h

