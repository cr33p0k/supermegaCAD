"""Менеджер сетки - единый источник правды для отрисовки и привязки к сетке"""
import math
from typing import Tuple, Optional


class GridManager:
    """
    Единый менеджер сетки для CAD-приложения.
    
    Концепция:
    - grid_step - шаг сетки в МИРОВЫХ координатах (реальных единицах чертежа)
    - При масштабировании сетка масштабируется вместе с чертежом
    - Для удобства визуализации используется адаптивная сетка:
      если ячейки становятся слишком маленькими/большими - меняем кратность
    """
    
    # Минимальный и максимальный размер ячейки сетки в ПИКСЕЛЯХ на экране
    MIN_CELL_PIXELS = 10   # Меньше - слишком густо
    MAX_CELL_PIXELS = 100  # Больше - слишком редко
    
    # Множители для адаптации сетки (стандартные для CAD: 1, 2, 5, 10...)
    MULTIPLIERS = [1, 2, 5, 10, 20, 50, 100, 200, 500, 1000]
    
    def __init__(self, base_step: float = 25.0):
        """
        Args:
            base_step: Базовый шаг сетки в мировых координатах
        """
        self._base_step = max(0.001, base_step)  # Базовый шаг (задаётся пользователем)
        self._visible = True                      # Видимость сетки
        self._snap_enabled = False                # Привязка к сетке включена
    
    @property
    def base_step(self) -> float:
        """Базовый шаг сетки в мировых координатах"""
        return self._base_step
    
    @base_step.setter
    def base_step(self, value: float):
        """Установить базовый шаг сетки"""
        self._base_step = max(0.001, value)
    
    @property
    def visible(self) -> bool:
        return self._visible
    
    @visible.setter
    def visible(self, value: bool):
        self._visible = value
    
    @property
    def snap_enabled(self) -> bool:
        return self._snap_enabled
    
    @snap_enabled.setter
    def snap_enabled(self, value: bool):
        self._snap_enabled = value
    
    def get_visual_step(self, scale: float) -> float:
        """
        Получить визуальный шаг сетки для отрисовки.
        
        Адаптирует шаг так, чтобы ячейки были комфортного размера на экране.
        
        Args:
            scale: Текущий масштаб (view_transform.scale)
            
        Returns:
            Шаг сетки в мировых координатах для отрисовки
        """
        # Размер базовой ячейки в пикселях
        base_pixels = self._base_step * scale
        
        if base_pixels < self.MIN_CELL_PIXELS:
            # Ячейки слишком маленькие - нужно увеличить шаг (кратно)
            # Находим минимальный множитель, чтобы ячейки стали >= MIN_CELL_PIXELS
            for mult in self.MULTIPLIERS:
                if self._base_step * mult * scale >= self.MIN_CELL_PIXELS:
                    return self._base_step * mult
            return self._base_step * self.MULTIPLIERS[-1]
        
        elif base_pixels > self.MAX_CELL_PIXELS:
            # Ячейки слишком большие - делим шаг
            # Находим делитель, чтобы ячейки стали <= MAX_CELL_PIXELS
            for div in [10, 5, 2]:
                if self._base_step / div * scale <= self.MAX_CELL_PIXELS:
                    return self._base_step / div
            return self._base_step / 10
        
        return self._base_step
    
    def get_major_step(self, visual_step: float) -> float:
        """
        Получить шаг крупной сетки (каждая N-ая линия).
        
        Args:
            visual_step: Визуальный шаг (от get_visual_step)
            
        Returns:
            Шаг крупной сетки в мировых координатах
        """
        # Крупная сетка - каждые 5 ячеек (стандарт для CAD)
        return visual_step * 5
    
    def snap_to_grid(self, world_x: float, world_y: float) -> Tuple[float, float]:
        """
        Привязать координаты к ближайшей точке сетки.
        
        ВАЖНО: Привязка всегда происходит к БАЗОВОМУ шагу,
        независимо от визуального отображения!
        
        Args:
            world_x, world_y: Мировые координаты
            
        Returns:
            Координаты ближайшей точки сетки
        """
        step = self._base_step
        gx = round(world_x / step) * step
        gy = round(world_y / step) * step
        return gx, gy
    
    def get_nearest_grid_point(self, world_x: float, world_y: float) -> Tuple[float, float, float]:
        """
        Найти ближайшую точку сетки и расстояние до неё.
        
        Args:
            world_x, world_y: Мировые координаты
            
        Returns:
            (grid_x, grid_y, distance) - координаты и расстояние в мировых единицах
        """
        gx, gy = self.snap_to_grid(world_x, world_y)
        dist = math.hypot(world_x - gx, world_y - gy)
        return gx, gy, dist
    
    def get_grid_lines(self, min_x: float, max_x: float, min_y: float, max_y: float, 
                       scale: float) -> Tuple[list, list, list, list]:
        """
        Получить координаты линий сетки для отрисовки.
        
        Args:
            min_x, max_x, min_y, max_y: Границы видимой области (мировые координаты)
            scale: Текущий масштаб
            
        Returns:
            (minor_v, minor_h, major_v, major_h) - списки координат
            minor_v - малые вертикальные линии (X координаты)
            minor_h - малые горизонтальные линии (Y координаты)
            major_v - крупные вертикальные линии (X координаты)
            major_h - крупные горизонтальные линии (Y координаты)
        """
        visual_step = self.get_visual_step(scale)
        major_step = self.get_major_step(visual_step)
        
        minor_v, minor_h = [], []
        major_v, major_h = [], []
        
        # Вертикальные линии (по X)
        x = math.floor(min_x / visual_step) * visual_step
        while x <= max_x:
            # Проверяем, является ли это крупной линией
            if abs(x % major_step) < visual_step * 0.01 or abs((x % major_step) - major_step) < visual_step * 0.01:
                major_v.append(x)
            else:
                minor_v.append(x)
            x += visual_step
        
        # Горизонтальные линии (по Y)
        y = math.floor(min_y / visual_step) * visual_step
        while y <= max_y:
            if abs(y % major_step) < visual_step * 0.01 or abs((y % major_step) - major_step) < visual_step * 0.01:
                major_h.append(y)
            else:
                minor_h.append(y)
            y += visual_step
        
        return minor_v, minor_h, major_v, major_h
