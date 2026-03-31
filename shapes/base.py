"""Базовый абстрактный класс для всех геометрических фигур"""
from abc import ABC, abstractmethod
from typing import Any, List, Tuple, Optional


import uuid

class Shape(ABC):
    """Абстрактный базовый класс для всех фигур"""
    
    def __init__(self):
        self.id = uuid.uuid4().hex  # Уникальный идентификатор
        self.color = "#ffffff"  # Цвет по умолчанию (белый для черного фона)
        self.selected = False
        self.line_style_name = "Сплошная основная"  # Стиль линии по умолчанию
    
    @abstractmethod
    def draw(self, renderer: Any, width: int, height: int, view_transform: Any, point_radius: int = 4) -> None:
        """Отрисовка фигуры на canvas"""
        pass
    
    @abstractmethod
    def distance_to_point(self, px: float, py: float, width: int, height: int, view_transform: Any) -> float:
        """Расстояние от точки (в экранных координатах) до фигуры"""
        pass
    
    @abstractmethod
    def get_info(self, is_degrees: bool = True) -> str:
        """Получить текстовую информацию о фигуре"""
        pass
    
    @abstractmethod
    def get_bounds(self) -> Tuple[float, float, float, float]:
        """Получить границы фигуры (min_x, min_y, max_x, max_y)"""
        pass
    
    @abstractmethod
    def translate(self, dx: float, dy: float) -> None:
        """Переместить фигуру на dx, dy в мировых координатах"""
        pass
    
    @abstractmethod
    def to_dict(self) -> dict:
        """Сериализация фигуры в словарь"""
        pass
    
    @staticmethod
    @abstractmethod
    def from_dict(data: dict) -> 'Shape':
        """Десериализация фигуры из словаря"""
        pass
    
    def set_selected(self, selected: bool) -> None:
        """Установить состояние выделения"""
        self.selected = selected

    def get_snap_points(self) -> List[Tuple[str, float, float]]:
        """Получить точки привязки
        
        Возвращает список кортежей (тип_привязки, x, y).
        Типы: 'endpoint', 'midpoint', 'center', 'quadrant', 'intersection', 'control'
        
        Переопределяется в подклассах.
        """
        return []
    
    def get_control_points(self) -> List[Tuple[str, float, float]]:
        """Получить контрольные точки для редактирования
        
        Возвращает список кортежей (id_точки, x, y).
        id_точки используется в move_control_point для идентификации точки.
        
        Переопределяется в подклассах.
        """
        return []
    
    def move_control_point(self, point_id: str, new_x: float, new_y: float) -> None:
        """Переместить контрольную точку
        
        Args:
            point_id: Идентификатор контрольной точки
            new_x, new_y: Новые координаты
            
        Переопределяется в подклассах.
        """
        pass
    
    def get_perpendicular_point(self, from_x: float, from_y: float) -> Optional[Tuple[float, float]]:
        """Найти точку перпендикуляра от внешней точки к фигуре
        
        Переопределяется в подклассах для фигур, поддерживающих эту привязку.
        """
        return None
    
    def get_tangent_points(self, from_x: float, from_y: float) -> List[Tuple[float, float]]:
        """Найти точки касания от внешней точки к фигуре
        
        Переопределяется в подклассах для криволинейных фигур.
        """
        return []
