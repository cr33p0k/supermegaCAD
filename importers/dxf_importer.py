"""
Модуль для импорта из формата DXF
"""
import math
from typing import List, Tuple, Dict, Any, Optional

from shapes import Point, Segment, Circle, Arc, Ellipse, Polygon, Spline


class DxfImporter:
    """Класс для импорта фигур из формата DXF (AutoCAD 2000/R15 и новее)"""
    
    def __init__(self):
        self.shapes = []
        self.styles = [] # Не используется пока, но можно сохранять слои как стили
        self.current_layer = "0"
        self.layers = {} # name -> properties
        
    def import_file(self, filename: str) -> List[Any]:
        """
        Импорт списка фигур из DXF файла
        
        Args:
            filename: Путь к файлу
            
        Returns:
            Список фигур (наследников Shape)
        """
        self.shapes = []
        self.layers = {}
        
        try:
            # Пытаемся читать с разными кодировками
            try:
                with open(filename, 'r', encoding='cp1251') as f:
                    content = f.readlines()
            except UnicodeDecodeError:
                with open(filename, 'r', encoding='utf-8') as f:
                    content = f.readlines()
        except Exception as e:
            print(f"Error opening file: {e}")
            return []
            
        # Парсинг пар код-значение
        pairs = []
        i = 0
        while i < len(content) - 1:
            try:
                code = int(content[i].strip())
                value = content[i+1].strip()
                pairs.append((code, value))
                i += 2
            except ValueError:
                i += 1
                continue
                
        # Обработка секции ENTITIES
        self._parse_entities(pairs)
        
        return self.shapes

    def _parse_entities(self, pairs: List[Tuple[int, str]]) -> None:
        """Парсинг секции ENTITIES"""
        in_entities_section = False
        i = 0
        
        while i < len(pairs):
            code, value = pairs[i]
            
            if code == 0 and value == "SECTION":
                # Checking next pair for section name
                if i + 1 < len(pairs) and pairs[i+1][0] == 2:
                    if pairs[i+1][1] == "ENTITIES":
                        in_entities_section = True
                        i += 2
                        continue
            
            if code == 0 and value == "ENDSEC":
                if in_entities_section:
                    in_entities_section = False
                    break
            
            if in_entities_section and code == 0:
                # Начало новой сущности
                entity_type = value
                # Собираем данные сущности до следующего кода 0
                entity_data = []
                j = i + 1
                while j < len(pairs) and pairs[j][0] != 0:
                    entity_data.append(pairs[j])
                    j += 1
                
                self._create_shape_from_entity(entity_type, entity_data)
                
                # Пропускаем обработанные пары (минус 1, так как цикл while i увеличит)
                i = j - 1
            
            i += 1

    def _get_value(self, data: List[Tuple[int, str]], code: int, default: Any = None) -> Any:
        """Получить значение по коду DXF"""
        for c, v in data:
            if c == code:
                try:
                    if isinstance(default, float):
                        return float(v)
                    if isinstance(default, int):
                        return int(v)
                    return v
                except ValueError:
                    return default
        return default

    def _get_all_values(self, data: List[Tuple[int, str]], code: int) -> List[Any]:
        """Получить все значения с данным кодом"""
        values = []
        for c, v in data:
            if c == code:
                try:
                    values.append(float(v))
                except ValueError:
                    values.append(v)
        return values

    def _create_shape_from_entity(self, entity_type: str, data: List[Tuple[int, str]]) -> None:
        """Создание фигуры из данных сущности"""
        layer = self._get_value(data, 8, "0")
        color_code = self._get_value(data, 62, 256) # 256 = ByLayer
        
        # Маппинг цвета (упрощенно)
        color = "#ffffff" # Default white
        if color_code == 1: color = "#ff5555" # Red
        elif color_code == 2: color = "#ffff55" # Yellow
        elif color_code == 3: color = "#55ff55" # Green
        elif color_code == 4: color = "#55ffff" # Cyan
        elif color_code == 5: color = "#5555ff" # Blue
        elif color_code == 6: color = "#ff55ff" # Magenta
        elif color_code == 7: color = "#ffffff" # White
        
        # Стиль линии по слою (пытаемся найти совпадение имени слоя с именем стиля)
        # В этой версии просто сохраняем имя слоя, ShapeManager/DrawTool может подхватить если стиль существует
        line_style = layer
        
        shape = None
        
        if entity_type == "POINT":
            x = self._get_value(data, 10, 0.0)
            y = self._get_value(data, 20, 0.0)
            shape = Point(x, y)
            
        elif entity_type == "LINE":
            x1 = self._get_value(data, 10, 0.0)
            y1 = self._get_value(data, 20, 0.0)
            x2 = self._get_value(data, 11, 0.0)
            y2 = self._get_value(data, 21, 0.0)
            shape = Segment(x1, y1, x2, y2)
            
        elif entity_type == "CIRCLE":
            cx = self._get_value(data, 10, 0.0)
            cy = self._get_value(data, 20, 0.0)
            r = self._get_value(data, 40, 1.0)
            shape = Circle(cx, cy, r)
            
        elif entity_type == "ARC":
            cx = self._get_value(data, 10, 0.0)
            cy = self._get_value(data, 20, 0.0)
            r = self._get_value(data, 40, 1.0)
            start_angle = self._get_value(data, 50, 0.0)
            end_angle = self._get_value(data, 51, 0.0)
            shape = Arc(cx, cy, r, start_angle, end_angle)
            
        elif entity_type == "ELLIPSE":
            cx = self._get_value(data, 10, 0.0)
            cy = self._get_value(data, 20, 0.0)
            dx = self._get_value(data, 11, 1.0)
            dy = self._get_value(data, 21, 0.0)
            ratio = self._get_value(data, 40, 1.0)
            
            rx = math.hypot(dx, dy)
            ry = rx * ratio
            rotation = math.degrees(math.atan2(dy, dx))
            
            shape = Ellipse(cx, cy, rx, ry, rotation)
            
        elif entity_type == "LWPOLYLINE":
            # Легковесная полилиния
            num_verts = self._get_value(data, 90, 0)
            flag = self._get_value(data, 70, 0)
            is_closed = (flag & 1) != 0
            
            xs = self._get_all_values(data, 10)
            ys = self._get_all_values(data, 20)
            
            points = list(zip(xs, ys))
            
            if len(points) >= 2:
                # Check for procedural style override
                final_style = line_style
                is_procedural = any(x in line_style.lower() for x in ['wavy', 'broken', 'волнист', 'излом'])
                if is_procedural:
                    final_style = "Сплошная основная"

                # Импортируем как набор сегментов для надежности
                for k in range(len(points) - 1):
                    s = Segment(points[k][0], points[k][1], points[k+1][0], points[k+1][1])
                    s.color = color
                    s.line_style_name = final_style
                    self.shapes.append(s)
                
                if is_closed:
                    s = Segment(points[-1][0], points[-1][1], points[0][0], points[0][1])
                    s.color = color
                    s.line_style_name = final_style
                    self.shapes.append(s)
                return # Специальный случай, уже добавили фигуры
            
        elif entity_type == "SPLINE":
            # Сплайн через контрольные точки
            # Degree 71
            # Knots 40
            # Control points 10, 20, 30
            
            xs = self._get_all_values(data, 10)
            ys = self._get_all_values(data, 20)
            points = list(zip(xs, ys))
            
            if points:
                shape = Spline(points)
        
        if shape:
            shape.color = color
            
            # Special handling for procedural styles on baked geometry
            # If we imported a Polyline (baked wave), we don't want to apply the wave style again
            is_procedural = any(x in line_style.lower() for x in ['wavy', 'broken', 'волнист', 'излом'])
            if is_procedural and (entity_type == "LWPOLYLINE" or entity_type == "SPLINE"):
                shape.line_style_name = "Сплошная основная" # Force solid
            else:
                shape.line_style_name = line_style
                
            self.shapes.append(shape)
