"""Менеджер для управления коллекцией фигур"""
from typing import List, Optional
from shapes import Shape


class ShapeManager:
    """Класс для управления всеми фигурами на холсте"""
    
    def __init__(self):
        self._shapes: List[Shape] = []
        self._selected_shape: Optional[Shape] = None
    
    def add_shape(self, shape: Shape) -> None:
        """Добавить фигуру"""
        self._shapes.append(shape)
    
    def remove_shape(self, shape: Shape) -> None:
        """Удалить фигуру и зависимые размеры"""
        if shape in self._shapes:
            self._shapes.remove(shape)
            if self._selected_shape == shape:
                self._selected_shape = None
            # Каскадное удаление зависимых размеров
            shape_id = getattr(shape, 'id', None)
            if shape_id:
                self._remove_dependent_dimensions(shape_id)
    
    def _remove_dependent_dimensions(self, shape_id: str) -> None:
        """Удалить размеры, привязанные к фигуре с данным id"""
        to_remove = self.find_dependent_dimensions(shape_id)
        for s in to_remove:
            if s in self._shapes:
                self._shapes.remove(s)
                if self._selected_shape == s:
                    self._selected_shape = None
    
    def find_dependent_dimensions(self, shape_id: str) -> list:
        """Найти все размеры, привязанные к фигуре с данным id"""
        deps = []
        for s in self._shapes:
            if hasattr(s, 'base_shape_id1') and hasattr(s, 'base_shape_id2'):
                if s.base_shape_id1 == shape_id or s.base_shape_id2 == shape_id:
                    deps.append(s)
            elif hasattr(s, 'base_shape_id') and getattr(s, 'base_shape_id', None) == shape_id:
                deps.append(s)
        return deps
    
    def remove_shape_no_cascade(self, shape: Shape) -> None:
        """Удалить фигуру без каскадного удаления зависимых размеров"""
        if shape in self._shapes:
            self._shapes.remove(shape)
            if self._selected_shape == shape:
                self._selected_shape = None
    
    def remove_selected(self) -> bool:
        """Удалить выделенную фигуру"""
        if self._selected_shape is not None:
            self.remove_shape(self._selected_shape)
            return True
        return False
    
    def remove_last(self) -> bool:
        """Удалить последнюю фигуру"""
        if self._shapes:
            last_shape = self._shapes[-1]
            self.remove_shape(last_shape)
            return True
        return False
    
    def clear_all(self) -> None:
        """Очистить все фигуры"""
        self._shapes.clear()
        self._selected_shape = None
    
    def get_all_shapes(self) -> List[Shape]:
        """Получить все фигуры"""
        return self._shapes.copy()
    
    def get_shape_by_id(self, shape_id: str) -> Optional[Shape]:
        """Получить фигуру по идентификатору"""
        for shape in self._shapes:
            if getattr(shape, 'id', None) == shape_id:
                return shape
        return None
    
    def get_shape_count(self) -> int:
        """Получить количество фигур"""
        return len(self._shapes)
    
    def select_shape(self, shape: Shape) -> None:
        """Выделить фигуру"""
        for s in self._shapes:
            s.set_selected(s == shape)
        if shape in self._shapes:
            self._selected_shape = shape
    
    def deselect_all(self) -> None:
        """Снять выделение со всех фигур"""
        for shape in self._shapes:
            shape.set_selected(False)
        self._selected_shape = None
    
    def get_selected_shape(self) -> Optional[Shape]:
        """Получить выделенную фигуру"""
        return self._selected_shape
    
    def get_selected_index(self) -> Optional[int]:
        """Получить индекс выделенной фигуры"""
        return self._shapes.index(self._selected_shape) if self._selected_shape in self._shapes else None
    
    def select_by_index(self, index: int) -> bool:
        """Выделить фигуру по индексу"""
        if 0 <= index < len(self._shapes):
            self.select_shape(self._shapes[index])
            return True
        return False
    
    def has_shapes(self) -> bool:
        """Проверить, есть ли фигуры"""
        return bool(self._shapes)
    
    def export_to_list(self) -> List[dict]:
        """Экспорт всех фигур в список словарей"""
        return [shape.to_dict() for shape in self._shapes]
    
    def import_from_list(self, shapes_data: List[dict]) -> None:
        """Импорт фигур из списка словарей"""
        from shapes import Segment, Circle, Arc, Rectangle, Ellipse, Polygon, Spline, Point, LinearDimension, RadialDimension, AngularDimension
        
        self.clear_all()
        
        shape_factories = {
            'segment': Segment.from_dict,
            'circle': Circle.from_dict,
            'arc': Arc.from_dict,
            'rectangle': Rectangle.from_dict,
            'ellipse': Ellipse.from_dict,
            'polygon': Polygon.from_dict,
            'spline': Spline.from_dict,
            'point': Point.from_dict,
            'linear_dimension': LinearDimension.from_dict,
            'radial_dimension': RadialDimension.from_dict,
            'angular_dimension': AngularDimension.from_dict,
        }
        
        for data in shapes_data:
            shape_type = data.get('type', 'segment')
            factory = shape_factories.get(shape_type)
            if factory:
                self.add_shape(factory(data))
