import math


class ViewTransform:
    """Класс для управления видовой матрицей"""
    
    def __init__(self):
        # Параметры трансформации
        self.offset_x = 0.0  # Смещение по X
        self.offset_y = 0.0  # Смещение по Y
        self.scale = 1.0     # Масштаб
        self.rotation = 0.0  # Угол поворота в градусах
        
        # Ограничения
        self.min_scale = 0.1
        self.max_scale = 10.0
    
    def reset(self):
        """Сбросить все преобразования"""
        self.offset_x = 0.0
        self.offset_y = 0.0
        self.scale = 1.0
        self.rotation = 0.0
    
    def pan(self, dx: float, dy: float):
        """Панорамирование"""
        self.offset_x += dx
        self.offset_y += dy
    
    def zoom(self, factor: float, center_x: float = 0, center_y: float = 0):
        """Масштабирование относительно точки"""
        old_scale = self.scale
        self.scale *= factor
        
        # Ограничение масштаба
        self.scale = max(self.min_scale, min(self.max_scale, self.scale))
        
        # Корректировка смещения для масштабирования относительно точки
        actual_factor = self.scale / old_scale
        self.offset_x = center_x + (self.offset_x - center_x) * actual_factor
        self.offset_y = center_y + (self.offset_y - center_y) * actual_factor
    
    
    def rotate(self, angle_degrees: float):
        """Поворот вида вокруг центра экрана"""
        self.rotation = (self.rotation + angle_degrees) % 360
        if self.rotation > 180:
            self.rotation -= 360
    
    def rotate_90_left(self):
        """Поворот на 90° влево"""
        self.rotate(-90)
    
    def rotate_90_right(self):
        """Поворот на 90° вправо"""
        self.rotate(90)
    
    def world_to_screen(self, x: float, y: float, canvas_width: int, canvas_height: int) -> tuple[float, float]:
        """Преобразование мировых координат в экранные"""
        cx, cy = canvas_width / 2, canvas_height / 2
        x_rel, y_rel = x * self.scale + self.offset_x, y * self.scale + self.offset_y
        
        if self.rotation != 0:
            angle_rad = math.radians(self.rotation)
            cos_a, sin_a = math.cos(angle_rad), math.sin(angle_rad)
            x_rel, y_rel = x_rel * cos_a - y_rel * sin_a, x_rel * sin_a + y_rel * cos_a
        
        return cx + x_rel, cy - y_rel
    
    def screen_to_world(self, sx: float, sy: float, canvas_width: int, canvas_height: int) -> tuple[float, float]:
        """Преобразование экранных координат в мировые"""
        cx, cy = canvas_width / 2, canvas_height / 2
        x_rel, y_rel = sx - cx, -(sy - cy)
        
        if self.rotation != 0:
            angle_rad = math.radians(-self.rotation)
            cos_a, sin_a = math.cos(angle_rad), math.sin(angle_rad)
            x_rel, y_rel = x_rel * cos_a - y_rel * sin_a, x_rel * sin_a + y_rel * cos_a
        
        if self.scale != 0:
            return (x_rel - self.offset_x) / self.scale, (y_rel - self.offset_y) / self.scale
        return x_rel - self.offset_x, y_rel - self.offset_y
    
    def get_scale_percent(self) -> int:
        """Получить масштаб в процентах"""
        return int(self.scale * 100)
    
    def get_rotation_degrees(self) -> int:
        """Получить угол поворота в градусах"""
        return int(self.rotation)
    
    def fit_to_view(self, shapes_bounds: tuple[float, float, float, float], 
                    canvas_width: int, canvas_height: int, margin: float = 50):
        """Подогнать вид под все фигуры (сохраняя текущий поворот)"""
        if not shapes_bounds:
            return
        
        min_x, min_y, max_x, max_y = shapes_bounds
        width, height = max_x - min_x, max_y - min_y
        center_x, center_y = (min_x + max_x) / 2, (min_y + max_y) / 2
        
        # Обработка особых случаев (точка, вертикальная или горизонтальная линия)
        if width == 0 and height == 0:
            # Все точки в одной точке - используем масштаб 1.0 и центрируем
            self.scale = 1.0
            self.offset_x = -center_x * self.scale
            self.offset_y = -center_y * self.scale
            return
        
        # Если ширина или высота равна 0, задаем минимальный размер для вычисления масштаба
        min_size = 100.0  # минимальный размер в мировых координатах
        if width == 0:
            width = min_size
        if height == 0:
            height = min_size
        
        if self.rotation != 0:
            # Диагональ прямоугольника - это максимальный размер после любого поворота
            diagonal = math.sqrt(width * width + height * height)
            width = height = diagonal
        
        scale_x = (canvas_width - 2 * margin) / width if width > 0 else 1.0
        scale_y = (canvas_height - 2 * margin) / height if height > 0 else 1.0
        target_scale = max(self.min_scale, min(self.max_scale, min(scale_x, scale_y)))
        
        self.scale = target_scale
        self.offset_x = -center_x * target_scale
        self.offset_y = -center_y * target_scale

