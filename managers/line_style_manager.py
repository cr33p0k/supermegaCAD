from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import math

DIMENSION_STYLE_NAME = "Размерная"


@dataclass
class LineStyle:
    """Класс, описывающий стиль линии"""
    name: str
    thickness_mm: float  # Толщина в мм
    line_type: str  # 'solid', 'dashed', 'dashdot', 'dashdotdot', 'wavy', 'broken'
    description: str = ""
    is_standard: bool = False  # Стандартный стиль нельзя удалить
    is_dimension_style: bool = False  # Отдельный стиль только для размеров
    
    # Параметры для штриховых линий (в относительных единицах)
    dash_length: float = 4.0  # Длина штриха
    gap_length: float = 2.0   # Длина промежутка
    dot_length: float = 0.5   # Длина точки
    
    # Параметры для волнистых линий
    wave_amplitude: float = 2.0  # Амплитуда волны (в пикселях)
    wave_length: float = 8.0     # Длина волны (в пикселях)
    
    # Параметры для линий с изломом
    break_height: float = 12.0   # Высота излома (в пикселях)
    break_width: float = 10.0    # Ширина излома (в пикселях)
    break_count: int = 1         # Количество изломов
    
    def get_dash_pattern(self) -> Optional[Tuple[int, ...]]:
        """Получить паттерн штриховки для tkinter (только для простых типов)"""
        if self.line_type == 'solid':
            return None
        elif self.line_type == 'dashed':
            return (int(self.dash_length), int(self.gap_length))
        elif self.line_type == 'dashdot':
            return (int(self.dash_length), int(self.gap_length), 
                    int(self.dot_length), int(self.gap_length))
        elif self.line_type == 'dashdotdot':
            return (int(self.dash_length), int(self.gap_length), 
                    int(self.dot_length), int(self.gap_length),
                    int(self.dot_length), int(self.gap_length))
        # Для wavy и broken возвращаем None, т.к. они требуют специальной отрисовки
        return None


class LineStyleManager:
    """Менеджер для управления стилями линий"""
    
    # Константы толщины по ГОСТ (в мм)
    THICKNESS_MAIN = 0.8
    THICKNESS_THIN = 0.4
    
    # DPI экрана (для конвертации мм в пиксели)
    SCREEN_DPI = 96.0
    
    def __init__(self):
        self._styles: Dict[str, LineStyle] = {}
        self._current_style_name: str = "Сплошная основная"
        self._init_standard_styles()
        
    def _init_standard_styles(self) -> None:
        """Инициализация стандартных стилей ГОСТ 2.303-68"""
        
        # 1. Сплошная основная (0.8 мм)
        self.add_style(LineStyle(
            name="Сплошная основная",
            thickness_mm=self.THICKNESS_MAIN,
            line_type='solid',
            description="Линии видимого контура",
            is_standard=True
        ))
        
        # 2. Сплошная тонкая (0.4 мм)
        self.add_style(LineStyle(
            name="Сплошная тонкая",
            thickness_mm=self.THICKNESS_THIN,
            line_type='solid',
            description="Размерные и выносные линии",
            is_standard=True
        ))

        self.add_style(LineStyle(
            name=DIMENSION_STYLE_NAME,
            thickness_mm=self.THICKNESS_THIN,
            line_type='solid',
            description="Отдельный стиль для размерных, выносных линий и полок",
            is_standard=True,
            is_dimension_style=True
        ))
        
        # 3. Сплошная волнистая (0.4 мм)
        self.add_style(LineStyle(
            name="Сплошная волнистая",
            thickness_mm=self.THICKNESS_THIN,
            line_type='wavy',
            description="Линии обрыва",
            is_standard=True,
            wave_amplitude=2.5,
            wave_length=10.0
        ))
        
        # 4. Штриховая (0.4 мм)
        # ГОСТ: штрих 2-8мм, промежуток 1-2мм
        self.add_style(LineStyle(
            name="Штриховая",
            thickness_mm=self.THICKNESS_THIN,
            line_type='dashed',
            description="Линии невидимого контура",
            is_standard=True,
            dash_length=6.0,
            gap_length=3.0
        ))
        
        # 5. Штрихпунктирная утолщенная (0.8 мм)
        self.add_style(LineStyle(
            name="Штрихпунктирная утолщенная",
            thickness_mm=self.THICKNESS_MAIN,
            line_type='dashdot',
            description="Линии поверхностей, подлежащих термообработке",
            is_standard=True,
            dash_length=8.0,
            gap_length=3.0,
            dot_length=1.0
        ))
        
        # 6. Штрихпунктирная тонкая (0.4 мм)
        # ГОСТ: штрих 5-30мм, промежуток 3-5мм
        self.add_style(LineStyle(
            name="Штрихпунктирная тонкая",
            thickness_mm=self.THICKNESS_THIN,
            line_type='dashdot',
            description="Линии осевые и центровые",
            is_standard=True,
            dash_length=12.0,
            gap_length=3.0,
            dot_length=1.0
        ))
        
        # 7. Штрихпунктирная с двумя точками (0.4 мм)
        self.add_style(LineStyle(
            name="Штрихпунктирная с двумя точками",
            thickness_mm=self.THICKNESS_THIN,
            line_type='dashdotdot',
            description="Линии сгиба на развертках",
            is_standard=True,
            dash_length=12.0,
            gap_length=3.0,
            dot_length=1.0
        ))
        
        # 8. Сплошная тонкая с изломами (0.4 мм)
        self.add_style(LineStyle(
            name="Сплошная тонкая с изломами",
            thickness_mm=self.THICKNESS_THIN,
            line_type='broken',
            description="Длинные линии обрыва",
            is_standard=True,
            break_height=12.0,
            break_width=10.0,
            break_count=1
        ))

    def add_style(self, style: LineStyle) -> None:
        """Добавить новый стиль"""
        self._styles[style.name] = style
        
    def get_style(self, name: str) -> Optional[LineStyle]:
        """Получить стиль по имени"""
        return self._styles.get(name)
        
    def get_all_styles(self) -> List[LineStyle]:
        """Получить список всех стилей"""
        return list(self._styles.values())
        
    def get_style_names(self) -> List[str]:
        """Получить список имен стилей"""
        return list(self._styles.keys())

    def get_general_style_names(self) -> List[str]:
        """Получить стили, доступные для обычных примитивов"""
        return [
            name for name, style in self._styles.items()
            if not style.is_dimension_style
        ]

    def get_dimension_style_name(self) -> str:
        """Получить имя специального стиля размеров"""
        return DIMENSION_STYLE_NAME
    
    def get_standard_style_names(self) -> List[str]:
        """Получить список имен стандартных стилей"""
        return [name for name, style in self._styles.items() if style.is_standard]
    
    def get_user_style_names(self) -> List[str]:
        """Получить список имен пользовательских стилей"""
        return [name for name, style in self._styles.items() if not style.is_standard]
        
    def set_current_style(self, name: str) -> bool:
        """Установить текущий стиль"""
        if name in self._styles:
            self._current_style_name = name
            return True
        return False
        
    def get_current_style(self) -> LineStyle:
        """Получить текущий активный стиль"""
        return self._styles[self._current_style_name]
        
    def get_current_style_name(self) -> str:
        """Получить имя текущего стиля"""
        return self._current_style_name
    
    def update_style(self, name: str, **kwargs) -> bool:
        """Обновить параметры стиля"""
        if name not in self._styles:
            return False
        
        style = self._styles[name]
        
        # Обновляем только разрешенные параметры
        allowed_params = ['thickness_mm', 'dash_length', 'gap_length', 
                         'dot_length', 'wave_amplitude', 'wave_length',
                         'break_height', 'break_width', 'break_count', 'description']
        
        for param, value in kwargs.items():
            if param in allowed_params:
                # Для break_count убеждаемся, что это int
                if param == 'break_count':
                    value = int(value)
                setattr(style, param, value)
        
        return True
    
    def delete_style(self, name: str) -> bool:
        """Удалить стиль (только пользовательские)"""
        if name not in self._styles:
            return False
        
        style = self._styles[name]
        if style.is_standard:
            return False  # Нельзя удалить стандартный стиль
        
        del self._styles[name]
        
        # Если удалили текущий стиль, переключаемся на основную
        if self._current_style_name == name:
            self._current_style_name = "Сплошная основная"
        
        return True
    
    def mm_to_pixels(self, mm: float) -> int:
        """Конвертация мм в пиксели (независимо от масштаба вида)"""
        # Формула: pixels = (mm / 25.4) * DPI
        pixels = (mm / 25.4) * self.SCREEN_DPI
        return max(1, int(pixels))
    
    def generate_wavy_points(self, x1: float, y1: float, x2: float, y2: float, 
                            amplitude: float, wavelength: float) -> List[Tuple[float, float]]:
        """
        Генерация промежуточных точек для волнистой линии
        
        Args:
            x1, y1: начальная точка
            x2, y2: конечная точка
            amplitude: амплитуда волны (в пикселях)
            wavelength: длина волны (в пикселях)
        
        Returns:
            Список координат точек для отрисовки
        """
        # Длина отрезка
        length = math.hypot(x2 - x1, y2 - y1)
        
        if length < 1:
            return [(x1, y1), (x2, y2)]
        
        # Угол наклона отрезка
        angle = math.atan2(y2 - y1, x2 - x1)
        
        # Количество волн
        num_waves = max(2, int(length / wavelength))
        num_points = num_waves * 4  # 4 точки на волну для гладкости
        
        points = [(x1, y1)]
        
        for i in range(1, num_points):
            t = i / num_points
            
            # Позиция вдоль отрезка
            base_x = x1 + (x2 - x1) * t
            base_y = y1 + (y2 - y1) * t
            
            # Смещение перпендикулярно отрезку (синусоида)
            wave_offset = amplitude * math.sin(2 * math.pi * num_waves * t)
            
            # Применяем смещение перпендикулярно линии
            offset_x = -wave_offset * math.sin(angle)
            offset_y = wave_offset * math.cos(angle)
            
            points.append((base_x + offset_x, base_y + offset_y))
        
        points.append((x2, y2))
        
        return points

    def _get_polyline_length(self, points: List[Tuple[float, float]], closed: bool = False) -> float:
        """Получить длину полилинии."""
        if len(points) < 2:
            return 0.0

        total = 0.0
        segment_count = len(points) if closed else len(points) - 1
        for i in range(segment_count):
            x1, y1 = points[i]
            x2, y2 = points[(i + 1) % len(points)]
            total += math.hypot(x2 - x1, y2 - y1)
        return total

    def _sample_polyline(
        self,
        points: List[Tuple[float, float]],
        distance: float,
        closed: bool = False
    ) -> Tuple[float, float, float, float]:
        """Получить точку и касательную на полилинии на заданном расстоянии."""
        if len(points) < 2:
            x, y = points[0] if points else (0.0, 0.0)
            return x, y, 1.0, 0.0

        total_length = self._get_polyline_length(points, closed)
        if total_length <= 1e-9:
            x, y = points[0]
            return x, y, 1.0, 0.0

        if closed:
            distance = distance % total_length
        else:
            distance = max(0.0, min(distance, total_length))

        walked = 0.0
        segment_count = len(points) if closed else len(points) - 1
        fallback_tangent = (1.0, 0.0)

        for i in range(segment_count):
            x1, y1 = points[i]
            x2, y2 = points[(i + 1) % len(points)]
            dx = x2 - x1
            dy = y2 - y1
            segment_length = math.hypot(dx, dy)
            if segment_length <= 1e-9:
                continue

            tangent = (dx / segment_length, dy / segment_length)
            fallback_tangent = tangent
            next_walked = walked + segment_length

            if distance <= next_walked or i == segment_count - 1:
                local_distance = distance - walked
                t = 0.0 if segment_length <= 1e-9 else local_distance / segment_length
                t = max(0.0, min(t, 1.0))
                return (
                    x1 + dx * t,
                    y1 + dy * t,
                    tangent[0],
                    tangent[1]
                )

            walked = next_walked

        x, y = points[-1]
        return x, y, fallback_tangent[0], fallback_tangent[1]

    def generate_wavy_path_points(
        self,
        points: List[Tuple[float, float]],
        amplitude: float,
        wavelength: float,
        closed: bool = False
    ) -> List[Tuple[float, float]]:
        """Построить волнистый контур вдоль произвольной полилинии."""
        if len(points) < 2 or wavelength <= 0:
            return list(points)

        total_length = self._get_polyline_length(points, closed)
        if total_length <= 1e-9:
            return list(points)

        sample_step = max(1.0, wavelength / 4.0)
        sample_count = max(8, int(total_length / sample_step))
        result = []
        limit = sample_count if closed else sample_count + 1

        for i in range(limit):
            distance = total_length * i / sample_count
            x, y, tx, ty = self._sample_polyline(points, distance, closed)
            normal_x = -ty
            normal_y = tx
            offset = amplitude * math.sin(2.0 * math.pi * distance / wavelength)
            result.append((x + normal_x * offset, y + normal_y * offset))

        if closed and result:
            result.append(result[0])

        return result

    def generate_broken_path_points(
        self,
        points: List[Tuple[float, float]],
        break_height: float = 12.0,
        break_width: float = 10.0,
        break_count: int = 1,
        closed: bool = False
    ) -> List[Tuple[float, float]]:
        """Построить контур с изломами вдоль произвольной полилинии."""
        if len(points) < 2:
            return list(points)

        total_length = self._get_polyline_length(points, closed)
        if total_length <= 1e-9:
            return list(points)

        centers = []
        if closed:
            pattern_span = max(break_width * 6.0, 24.0)
            closed_break_count = max(3, int(total_length / pattern_span))
            spacing = total_length / closed_break_count
            centers = [spacing * (i + 0.5) for i in range(closed_break_count)]
        else:
            break_count = max(1, int(break_count))
            if break_count == 1:
                centers = [total_length / 2.0]
            else:
                margin = break_width * 2.0
                usable_length = total_length - 2.0 * margin
                if usable_length <= 0:
                    return list(points)
                spacing = usable_length / (break_count + 1)
                centers = [margin + spacing * (i + 1) for i in range(break_count)]

        sample_step = max(6.0, break_width)
        distances = []
        current = 0.0
        limit = total_length if not closed else total_length - 1e-6
        while current < limit:
            distances.append(current)
            current += sample_step
        if not closed:
            distances.append(total_length)

        offsets: Dict[float, float] = {}
        for center in centers:
            d1 = max(0.0, center - break_width)
            d2 = max(0.0, center - break_width / 3.0)
            d3 = min(total_length, center + break_width / 3.0)
            d4 = min(total_length, center + break_width)
            distances.extend([d1, d2, d3, d4])
            offsets[round(d2, 5)] = break_height
            offsets[round(d3, 5)] = -break_height

        ordered_distances = sorted(set(round(distance, 5) for distance in distances))
        result = []

        for distance_key in ordered_distances:
            distance = float(distance_key)
            x, y, tx, ty = self._sample_polyline(points, distance, closed)
            normal_x = -ty
            normal_y = tx
            offset = offsets.get(distance_key, 0.0)
            result.append((x + normal_x * offset, y + normal_y * offset))

        if closed and result:
            result.append(result[0])

        return result
    
    def generate_broken_points(self, x1: float, y1: float, x2: float, y2: float,
                                break_height: float = 12.0, break_width: float = 10.0,
                                break_count: int = 1) -> List[Tuple[float, float]]:
        """
        Генерация точек для линии с изломами
        
        Args:
            x1, y1: начальная точка
            x2, y2: конечная точка
            break_height: высота излома (пиксели)
            break_width: ширина излома (пиксели)
            break_count: количество изломов
        """
        length = math.hypot(x2 - x1, y2 - y1)
        
        if length < 20 or break_count < 1:
            return [(x1, y1), (x2, y2)]
        
        # Угол наклона отрезка
        angle = math.atan2(y2 - y1, x2 - x1)
        
        # Нормаль к линии (перпендикуляр)
        perp_x = -math.sin(angle)
        perp_y = math.cos(angle)
        
        # Направление вдоль линии
        dir_x = math.cos(angle)
        dir_y = math.sin(angle)
        
        points = [(x1, y1)]
        
        # Если один излом - размещаем в центре (старое поведение)
        if break_count == 1:
            mid_x = (x1 + x2) / 2
            mid_y = (y1 + y2) / 2
            
            # Точка перед изломом
            p1_x = mid_x - dir_x * break_width
            p1_y = mid_y - dir_y * break_width
            
            # Верхняя точка излома
            p2_x = mid_x - dir_x * (break_width / 3) + perp_x * break_height
            p2_y = mid_y - dir_y * (break_width / 3) + perp_y * break_height
            
            # Нижняя точка излома
            p3_x = mid_x + dir_x * (break_width / 3) - perp_x * break_height
            p3_y = mid_y + dir_y * (break_width / 3) - perp_y * break_height
            
            # Точка после излома
            p4_x = mid_x + dir_x * break_width
            p4_y = mid_y + dir_y * break_width
            
            points.extend([(p1_x, p1_y), (p2_x, p2_y), (p3_x, p3_y), (p4_x, p4_y)])
        else:
            # Несколько изломов - равномерно распределяем вдоль линии
            # Оставляем отступы от концов
            margin = break_width * 2
            usable_length = length - 2 * margin
            
            if usable_length <= 0:
                # Линия слишком короткая для нескольких изломов
                return [(x1, y1), (x2, y2)]
            
            # Расстояние между центрами изломов
            spacing = usable_length / (break_count + 1)
            
            for i in range(break_count):
                # Позиция центра излома вдоль линии
                t = margin + spacing * (i + 1)
                t_normalized = t / length
                
                # Центр излома
                break_x = x1 + (x2 - x1) * t_normalized
                break_y = y1 + (y2 - y1) * t_normalized
                
                # Точка перед изломом
                p1_x = break_x - dir_x * break_width
                p1_y = break_y - dir_y * break_width
                
                # Верхняя точка излома
                p2_x = break_x - dir_x * (break_width / 3) + perp_x * break_height
                p2_y = break_y - dir_y * (break_width / 3) + perp_y * break_height
                
                # Нижняя точка излома
                p3_x = break_x + dir_x * (break_width / 3) - perp_x * break_height
                p3_y = break_y + dir_y * (break_width / 3) - perp_y * break_height
                
                # Точка после излома
                p4_x = break_x + dir_x * break_width
                p4_y = break_y + dir_y * break_width
                
                points.extend([(p1_x, p1_y), (p2_x, p2_y), (p3_x, p3_y), (p4_x, p4_y)])
        
        points.append((x2, y2))
        return points
