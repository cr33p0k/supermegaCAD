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

    def _get_style_draw_params(self, renderer: Any) -> Tuple[int, Optional[Tuple[int, ...]], str, Any]:
        """Получить параметры отрисовки линии из менеджера стилей."""
        line_width = 3
        dash_pattern = None
        line_type = 'solid'
        style = None

        if hasattr(renderer, 'style_manager') and renderer.style_manager:
            style = renderer.style_manager.get_style(self.line_style_name)
            if style:
                line_width = renderer.style_manager.mm_to_pixels(style.thickness_mm)
                dash_pattern = style.get_dash_pattern()
                line_type = style.line_type

        return line_width, dash_pattern, line_type, style

    def _draw_styled_screen_path(
        self,
        renderer: Any,
        screen_points: List[Tuple[float, float]],
        color: str,
        line_width: int,
        dash_pattern: Optional[Tuple[int, ...]],
        line_type: str,
        style: Any,
        closed: bool = False,
        smooth: bool = False
    ) -> None:
        """Нарисовать контур с учетом простых и процедурных стилей линий."""
        if len(screen_points) < 2:
            return

        draw_points = list(screen_points)
        draw_smooth = smooth
        draw_dash = dash_pattern

        if hasattr(renderer, 'style_manager') and renderer.style_manager and style:
            if line_type == 'wavy':
                draw_points = renderer.style_manager.generate_wavy_path_points(
                    screen_points,
                    style.wave_amplitude,
                    style.wave_length,
                    closed=closed
                )
                draw_dash = None
                draw_smooth = True
            elif line_type == 'broken':
                draw_points = renderer.style_manager.generate_broken_path_points(
                    screen_points,
                    getattr(style, 'break_height', 12.0),
                    getattr(style, 'break_width', 10.0),
                    getattr(style, 'break_count', 1),
                    closed=closed
                )
                draw_dash = None
                draw_smooth = False
            elif closed and draw_points[0] != draw_points[-1]:
                draw_points.append(draw_points[0])
        elif closed and draw_points[0] != draw_points[-1]:
            draw_points.append(draw_points[0])

        flat_points = [coord for point in draw_points for coord in point]
        if len(flat_points) >= 4:
            renderer.canvas.create_line(
                *flat_points,
                fill=color,
                width=line_width,
                dash=draw_dash,
                smooth=draw_smooth,
                tags="shape"
            )
