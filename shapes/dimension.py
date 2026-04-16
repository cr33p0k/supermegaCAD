"""Классы для представления размеров (ГОСТ 2.307-2011)"""
import ctypes
import ctypes.util
import math
from pathlib import Path
import sys
import tkinter as tk
import tkinter.font as tkfont
from typing import List, Tuple, Optional, Any
from .base import Shape
from core import CoordinateConverter, SegmentGeometry
from managers.line_style_manager import DIMENSION_STYLE_NAME

# Формы стрелок
ARROW_SHAPES = ['triangle', 'square', 'circle', 'tick', 'none']
ARROW_SHAPE_NAMES = {
    'triangle': 'Обычная',
    'square': 'Квадратная',
    'circle': 'Круглая',
    'tick': 'Засечка',
    'none': 'Нет'
}

# Устаревшие типы стрелок оставлены для обратной совместимости
ARROW_TYPES = ['filled', 'open', 'dot', 'tick', 'none']
ARROW_NAMES = {
    'filled': 'Заполненная', 'open': 'Открытая',
    'dot': 'Точка', 'tick': 'Засечка', 'none': 'Нет'
}
LINEAR_DIMENSION_MODES = ['aligned', 'horizontal', 'vertical']
LINEAR_DIMENSION_MODE_NAMES = {
    'aligned': 'Выровненный',
    'horizontal': 'Горизонтальный',
    'vertical': 'Вертикальный',
}
DIMENSION_PREFIX_PRESETS = ['', 'R', '⌀', '□', '±', 'M']
RADIAL_DISPLAY_MODES = ['leader', 'aligned', 'outside']
RADIAL_DISPLAY_MODE_NAMES = {
    'leader': 'Полка',
    'aligned': 'По линии',
    'outside': 'Снаружи',
}
DIMENSION_FONT_TYPES = ['type_b_italic', 'type_b', 'type_a_italic', 'type_a']
DIMENSION_FONT_TYPE_NAMES = {
    'type_b_italic': 'ГОСТ Type B наклонный',
    'type_b': 'ГОСТ Type B',
    'type_a_italic': 'ГОСТ Type A наклонный',
    'type_a': 'ГОСТ Type A',
}
DIMENSION_FONT_FILE_CANDIDATES = {
    'type_b_italic': ['ГОСТ тип В наклонный.ttf', 'GOST_BU.TTF'],
    'type_b': ['ГОСТ тип В.ttf', 'GOST_0.TTF'],
    'type_a_italic': ['ГОСТ тип А наклонный.ttf', 'GOST_AU.TTF'],
    'type_a': ['ГОСТ тип А.ttf', 'GOST.TTF'],
}
DIMENSION_FONT_CANDIDATES = {
    'type_b_italic': [
        ('ГОСТ тип В', 'italic'),
        ('ГОСТ тип В', 'roman'),
        ('GOST type B', 'italic'),
        ('GOST Type B', 'italic'),
        ('GOST Type BU', 'roman'),
        ('Arial', 'italic'),
    ],
    'type_b': [
        ('ГОСТ тип В', 'roman'),
        ('GOST type B', 'roman'),
        ('GOST Type B', 'roman'),
        ('Gost Type B', 'roman'),
        ('GOST_B', 'roman'),
        ('Arial', 'roman'),
    ],
    'type_a_italic': [
        ('ГОСТ тип А', 'italic'),
        ('ГОСТ тип А', 'roman'),
        ('GOST type A', 'italic'),
        ('GOST Type A', 'italic'),
        ('GOST Type AU', 'roman'),
        ('Arial', 'italic'),
    ],
    'type_a': [
        ('ГОСТ тип А', 'roman'),
        ('GOST type A', 'roman'),
        ('GOST Type A', 'roman'),
        ('Gost Type A', 'roman'),
        ('GOST_A', 'roman'),
        ('Arial', 'roman'),
    ],
}
SHELF_DIRECTION_NAMES = {
    0: 'Авто',
    1: 'Вправо',
    -1: 'Влево'
}


class Dimension(Shape):
    """Абстрактный класс размера"""
    _bundled_fonts_registration_attempted = False
    _font_cache: dict[Tuple[str, int, str], tkfont.Font] = {}

    def __init__(self):
        super().__init__()
        self.color = "#ffffff"
        self.line_style_name = DIMENSION_STYLE_NAME
        self.text_override = ""
        self.text_prefix = ""
        self.text_pos_x = 0.0
        self.text_pos_y = 0.0
        self.layer = "Размеры"
        # Настройки оформления
        self.font_size = 12          # Размер шрифта (пт)
        self.font_type = 'type_b_italic'    # ГОСТ Type B наклонный по умолчанию
        self.arrow_shape = 'triangle'
        self.arrow_filled = True
        self.arrow_type = 'filled'   # legacy-представление для старых файлов
        self.arrow_size = 15.0       # Длина стрелки (px)
        self.show_shelf = False      # Текст на полке
        self.shelf_length = 40.0     # Длина полки (px)
        self.shelf_offset = 15.0     # Вынос полки от размерной линии
        self.shelf_dir_override = 0  # 0=авто, 1=вправо, -1=влево
        self.line_width_dim = 1      # Толщина размерных линий

    def _get_line_params(self, renderer) -> Tuple[int, Optional[Tuple[int, ...]]]:
        """Получить толщину и dash-паттерн из отдельного стиля размеров."""
        line_width = self.line_width_dim
        dash_pattern = None

        if hasattr(renderer, 'style_manager') and renderer.style_manager:
            style = renderer.style_manager.get_style(self.line_style_name)
            if style:
                line_width = renderer.style_manager.mm_to_pixels(style.thickness_mm)
                dash_pattern = style.get_dash_pattern()

        if self.selected:
            line_width += 1

        return line_width, dash_pattern

    def set_shelf_direction_override(self, direction: int) -> None:
        """Установить направление полки."""
        if direction in (-1, 0, 1):
            self.shelf_dir_override = direction

    def cycle_shelf_direction(self) -> int:
        """Переключить направление полки по циклу авто -> вправо -> влево."""
        current = self.shelf_dir_override
        next_dir = 1 if current == 0 else (-1 if current == 1 else 0)
        self.shelf_dir_override = next_dir
        return next_dir

    def get_shelf_direction_name(self) -> str:
        """Получить имя текущего направления полки."""
        return SHELF_DIRECTION_NAMES.get(self.shelf_dir_override, 'Авто')

    def _draw_arrow(self, renderer, x: float, y: float, angle_rad: float,
                    color: str, line_width: int) -> None:
        """Отрисовка стрелки по выбранному типу"""
        a_len = self.arrow_size
        a_w = a_len / 3.0
        cos_a = math.cos(angle_rad)
        sin_a = math.sin(angle_rad)

        if self.arrow_shape == 'triangle':
            pts = []
            for px, py in [(0, 0), (-a_len, a_w / 2), (-a_len, -a_w / 2)]:
                rx = px * cos_a - py * sin_a
                ry = px * sin_a + py * cos_a
                pts.extend([x + rx, y + ry])
            renderer.canvas.create_polygon(
                *pts,
                fill=color if self.arrow_filled else "",
                outline=color,
                width=line_width,
                tags="shape"
            )
        elif self.arrow_shape == 'square':
            side = max(4.0, a_len * 0.55)
            pts = []
            half_side = side / 2.0
            for px, py in [
                (half_side, -half_side),
                (half_side, half_side),
                (-half_side, half_side),
                (-half_side, -half_side)
            ]:
                rx = px * cos_a - py * sin_a
                ry = px * sin_a + py * cos_a
                pts.extend([x + rx, y + ry])
            renderer.canvas.create_polygon(
                *pts,
                fill=color if self.arrow_filled else "",
                outline=color,
                width=line_width,
                tags="shape"
            )
        elif self.arrow_shape == 'circle':
            radius = max(2.0, a_len * 0.28)
            renderer.canvas.create_oval(
                x - radius, y - radius, x + radius, y + radius,
                fill=color if self.arrow_filled else "",
                outline=color,
                width=line_width,
                tags="shape"
            )
        elif self.arrow_shape == 'tick':
            tick_len = a_len * 0.55
            t_angle = angle_rad + math.pi / 4
            dx1 = tick_len * math.cos(t_angle)
            dy1 = tick_len * math.sin(t_angle)
            renderer.canvas.create_line(x + dx1, y + dy1, x - dx1, y - dy1,
                                        fill=color, width=max(2, line_width), tags="shape")
        # 'none' — ничего не рисуем

    def _sync_legacy_arrow_type(self) -> None:
        """Синхронизировать legacy-поле arrow_type для старых сохранений."""
        if self.arrow_shape == 'triangle':
            self.arrow_type = 'filled' if self.arrow_filled else 'open'
        elif self.arrow_shape == 'circle':
            self.arrow_type = 'dot'
        elif self.arrow_shape == 'tick':
            self.arrow_type = 'tick'
        elif self.arrow_shape == 'none':
            self.arrow_type = 'none'
        else:
            self.arrow_type = 'filled' if self.arrow_filled else 'open'

    def _apply_legacy_arrow_type(self, arrow_type: str) -> None:
        """Прочитать старое представление типа стрелки."""
        if arrow_type == 'filled':
            self.arrow_shape = 'triangle'
            self.arrow_filled = True
        elif arrow_type == 'open':
            self.arrow_shape = 'triangle'
            self.arrow_filled = False
        elif arrow_type == 'dot':
            self.arrow_shape = 'circle'
            self.arrow_filled = True
        elif arrow_type == 'tick':
            self.arrow_shape = 'tick'
            self.arrow_filled = False
        elif arrow_type == 'none':
            self.arrow_shape = 'none'
            self.arrow_filled = False
        else:
            self.arrow_shape = 'triangle'
            self.arrow_filled = True
        self._sync_legacy_arrow_type()

    def _format_value(self, value: float) -> str:
        if self.text_override:
            return self.text_override
        return f"{value:.2f}"

    @classmethod
    def _register_bundled_fonts(cls) -> None:
        """Зарегистрировать приложенные TTF-шрифты в текущем процессе."""
        if cls._bundled_fonts_registration_attempted:
            return

        cls._bundled_fonts_registration_attempted = True
        if sys.platform != 'darwin':
            return

        font_dirs = [
            Path(__file__).resolve().parent.parent / 'fonts-GOST',
            Path(__file__).resolve().parent.parent / 'fonts',
        ]
        font_files: List[Path] = []
        seen_paths: set[Path] = set()

        for font_dir in font_dirs:
            if not font_dir.exists():
                continue

            for font_type in DIMENSION_FONT_TYPES:
                for file_name in DIMENSION_FONT_FILE_CANDIDATES.get(font_type, []):
                    font_path = font_dir / file_name
                    if font_path.exists() and font_path not in seen_paths:
                        font_files.append(font_path)
                        seen_paths.add(font_path)

            for pattern in ('*.ttf', '*.TTF', '*.otf', '*.OTF', '*.ttc', '*.TTC'):
                for font_path in font_dir.glob(pattern):
                    if font_path not in seen_paths:
                        font_files.append(font_path)
                        seen_paths.add(font_path)

        if not font_files:
            return

        core_foundation_name = ctypes.util.find_library('CoreFoundation')
        core_text_name = ctypes.util.find_library('CoreText')
        if not core_foundation_name or not core_text_name:
            return

        try:
            core_foundation = ctypes.CDLL(core_foundation_name)
            core_text = ctypes.CDLL(core_text_name)
        except OSError:
            return

        core_foundation.CFURLCreateFromFileSystemRepresentation.argtypes = [
            ctypes.c_void_p,
            ctypes.c_char_p,
            ctypes.c_long,
            ctypes.c_bool,
        ]
        core_foundation.CFURLCreateFromFileSystemRepresentation.restype = ctypes.c_void_p
        core_foundation.CFRelease.argtypes = [ctypes.c_void_p]
        core_foundation.CFRelease.restype = None

        core_text.CTFontManagerRegisterFontsForURL.argtypes = [
            ctypes.c_void_p,
            ctypes.c_uint32,
            ctypes.POINTER(ctypes.c_void_p),
        ]
        core_text.CTFontManagerRegisterFontsForURL.restype = ctypes.c_bool

        k_ct_font_manager_scope_process = 1
        for font_path in font_files:
            url_ref = core_foundation.CFURLCreateFromFileSystemRepresentation(
                None,
                str(font_path).encode('utf-8'),
                len(str(font_path).encode('utf-8')),
                False,
            )
            if not url_ref:
                continue
            error_ref = ctypes.c_void_p()
            core_text.CTFontManagerRegisterFontsForURL(
                url_ref,
                k_ct_font_manager_scope_process,
                ctypes.byref(error_ref),
            )
            if error_ref:
                core_foundation.CFRelease(error_ref)
            core_foundation.CFRelease(url_ref)

    @classmethod
    def _get_available_font_families(cls) -> set[str]:
        """Получить список доступных семейств шрифтов Tk."""
        try:
            cls._register_bundled_fonts()
            return set(tkfont.families())
        except tk.TclError:
            return set()

    def _resolve_font_spec(self) -> Tuple[str, str]:
        """Подобрать семейство и наклон для выбранного ГОСТ-шрифта."""
        font_type = self.font_type if self.font_type in DIMENSION_FONT_TYPES else 'type_b_italic'
        available = self._get_available_font_families()
        for family, slant in DIMENSION_FONT_CANDIDATES[font_type]:
            if family in available:
                return family, slant
        if 'Arial' in available or not available:
            fallback_slant = 'italic' if 'italic' in font_type else 'roman'
            return 'Arial', fallback_slant
        return 'TkDefaultFont', 'roman'

    def _get_text_font(self) -> tkfont.Font:
        """Получить шрифт для размерного текста."""
        family, slant = self._resolve_font_spec()
        cache_key = (family, self.font_size, slant)
        cached_font = self._font_cache.get(cache_key)
        if cached_font is not None:
            return cached_font

        font = tkfont.Font(
            family=family,
            size=self.font_size,
            slant=slant,
            weight='normal'
        )
        self._font_cache[cache_key] = font
        return font

    def _compose_dimension_text(self, value: float, auto_prefix: str = "",
                                auto_suffix: str = "") -> str:
        """Собрать отображаемый текст размера с учётом префикса."""
        prefix = self.text_prefix if self.text_prefix else auto_prefix
        if prefix == 'Ø':
            prefix = '⌀'
        return f"{prefix}{self._format_value(value)}{auto_suffix}"

    def _measure_text_width(self, text: str) -> float:
        """Оценить ширину текста в экранных пикселях."""
        font = self._get_text_font()
        return float(font.measure(text))
    
    def _draw_text(self, renderer, text: str, x: float, y: float, angle_rad: float,
                   color: str, line_width: int, shelf_offset: float = 15.0,
                   force_shelf: bool = False, shelf_length: Optional[float] = None,
                   shelf_dir_override: Optional[int] = None,
                   allow_shelf: bool = True) -> None:
        """Отрисовка размерного текста (над размерной линией или на полке)"""
        font = self._get_text_font()
        
        if allow_shelf and (self.show_shelf or force_shelf):
            self._draw_text_on_shelf(
                renderer, text, x, y, angle_rad, color, line_width,
                shelf_offset, shelf_length, shelf_dir_override
            )
            return
        
        angle_deg = math.degrees(angle_rad)
        if 90 < angle_deg <= 270 or -270 < angle_deg <= -90:
            angle_deg += 180
        tk_angle = -angle_deg
        offset = 5.0
        renderer.canvas.create_text(x, y - offset, text=text, fill=color,
                                    font=font, angle=tk_angle, anchor="s", tags="shape")
    
    def _draw_text_on_shelf(self, renderer, text: str, x: float, y: float,
                            angle_rad: float, color: str, line_width: int,
                            shelf_offset: float,
                            shelf_length: Optional[float] = None,
                            shelf_dir_override: Optional[int] = None) -> None:
        """Отрисовка текста на полке (выноске)"""
        font = self._get_text_font()
        resolved_dir = self.shelf_dir_override if shelf_dir_override is None else shelf_dir_override
        if resolved_dir != 0:
            shelf_dir = resolved_dir
        else:
            shelf_dir = 1 if math.cos(angle_rad) >= 0 else -1
            
        shelf_len = self.shelf_length if shelf_length is None else shelf_length
        nx, ny = -math.sin(angle_rad), math.cos(angle_rad)
        base_x = x + nx * shelf_offset
        base_y = y + ny * shelf_offset
        renderer.canvas.create_line(
            x, y, base_x, base_y, fill=color, width=line_width, tags="shape"
        )
        shelf_end_x = base_x + shelf_dir * shelf_len
        renderer.canvas.create_line(
            base_x, base_y, shelf_end_x, base_y, fill=color, width=line_width, tags="shape"
        )
        text_x = base_x + shelf_dir * (shelf_len / 2)
        renderer.canvas.create_text(text_x, base_y - 5, text=text, fill=color,
                                    font=font, anchor="s", tags="shape")
    
    def _base_dict(self) -> dict:
        """Общие поля для сериализации"""
        return {
            'color': self.color,
            'line_style_name': self.line_style_name,
            'text_override': self.text_override,
            'text_prefix': self.text_prefix,
            'text_pos_x': self.text_pos_x,
            'text_pos_y': self.text_pos_y,
            'font_size': self.font_size,
            'font_type': self.font_type,
            'arrow_shape': self.arrow_shape,
            'arrow_filled': self.arrow_filled,
            'arrow_type': self.arrow_type,
            'arrow_size': self.arrow_size,
            'show_shelf': self.show_shelf,
            'shelf_length': self.shelf_length,
            'shelf_offset': self.shelf_offset,
            'shelf_dir_override': self.shelf_dir_override,
            'line_width_dim': self.line_width_dim,
        }
    
    def _apply_base_dict(self, data: dict) -> None:
        """Загрузить общие поля из словаря"""
        self.color = data.get('color', self.color)
        self.line_style_name = data.get('line_style_name', self.line_style_name)
        self.text_override = data.get('text_override', '')
        self.text_prefix = data.get('text_prefix', '')
        if self.text_prefix == 'Ø':
            self.text_prefix = '⌀'
        self.text_pos_x = data.get('text_pos_x', 0.0)
        self.text_pos_y = data.get('text_pos_y', 0.0)
        self.font_size = data.get('font_size', 12)
        raw_font_type = data.get('font_type', 'type_b_italic')
        self.font_type = raw_font_type if raw_font_type in DIMENSION_FONT_TYPES else 'type_b_italic'
        raw_arrow_shape = data.get('arrow_shape')
        if raw_arrow_shape in ARROW_SHAPES:
            self.arrow_shape = raw_arrow_shape
            self.arrow_filled = bool(
                data.get('arrow_filled', raw_arrow_shape not in ('tick', 'none'))
            )
            self._sync_legacy_arrow_type()
        else:
            self._apply_legacy_arrow_type(data.get('arrow_type', 'filled'))
        self.arrow_size = data.get('arrow_size', 15.0)
        self.show_shelf = data.get('show_shelf', False)
        self.shelf_length = data.get('shelf_length', 40.0)
        self.shelf_offset = data.get('shelf_offset', 15.0)
        self.shelf_dir_override = data.get('shelf_dir_override', 0)
        self.line_width_dim = data.get('line_width_dim', 1)


class LinearDimension(Dimension):
    """Линейный размер"""
    def __init__(self, p1: Tuple[float, float], p2: Tuple[float, float],
                 offset: float = 30.0, measurement_mode: str = 'aligned'):
        super().__init__()
        self.p1_x, self.p1_y = p1
        self.p2_x, self.p2_y = p2
        self.offset = offset  # Отступ размерной линии от измеряемого отрезка
        self.measurement_mode = measurement_mode if measurement_mode in LINEAR_DIMENSION_MODES else 'aligned'
        
        # Ссылки на базовые фигуры (по id)
        self.base_shape_id1 = None
        self.base_point_id1 = None
        self.base_shape_id2 = None
        self.base_point_id2 = None

    def _get_vectors(self) -> Optional[Tuple[float, float, float, float, float]]:
        """Получить направляющий и нормальный векторы в мировых координатах."""
        if self.measurement_mode == 'horizontal':
            direction = 1.0 if self.p2_x >= self.p1_x else -1.0
            angle_rad = 0.0 if direction >= 0 else math.pi
            return angle_rad, direction, 0.0, 0.0, 1.0

        if self.measurement_mode == 'vertical':
            direction = 1.0 if self.p2_y >= self.p1_y else -1.0
            angle_rad = math.pi / 2 if direction >= 0 else -math.pi / 2
            return angle_rad, 0.0, direction, -1.0, 0.0

        dx = self.p2_x - self.p1_x
        dy = self.p2_y - self.p1_y
        length = math.hypot(dx, dy)
        if length < 1e-5:
            return None

        angle_rad = math.atan2(dy, dx)
        lx, ly = math.cos(angle_rad), math.sin(angle_rad)
        nx, ny = -math.sin(angle_rad), math.cos(angle_rad)
        return angle_rad, lx, ly, nx, ny

    def get_measurement_mode_name(self) -> str:
        """Получить имя режима линейного размера."""
        return LINEAR_DIMENSION_MODE_NAMES.get(self.measurement_mode, 'Выровненный')

    def get_measurement_value(self) -> float:
        """Получить фактическое значение линейного размера."""
        if self.measurement_mode == 'horizontal':
            return abs(self.p2_x - self.p1_x)
        if self.measurement_mode == 'vertical':
            return abs(self.p2_y - self.p1_y)
        return SegmentGeometry.calculate_length(self.p1_x, self.p1_y, self.p2_x, self.p2_y)

    def _get_dimension_world_points(self) -> Tuple[Tuple[float, float], Tuple[float, float]]:
        """Получить концы размерной линии в мировых координатах."""
        if self.measurement_mode == 'horizontal':
            base_y = max(self.p1_y, self.p2_y) if self.offset >= 0 else min(self.p1_y, self.p2_y)
            dim_y = base_y + self.offset
            return (self.p1_x, dim_y), (self.p2_x, dim_y)

        if self.measurement_mode == 'vertical':
            base_x = max(self.p1_x, self.p2_x) if self.offset >= 0 else min(self.p1_x, self.p2_x)
            dim_x = base_x + self.offset
            return (dim_x, self.p1_y), (dim_x, self.p2_y)

        vectors = self._get_vectors()
        if vectors is None:
            return (self.p1_x, self.p1_y), (self.p2_x, self.p2_y)
        _, _, _, nx, ny = vectors
        return (
            (self.p1_x - nx * self.offset, self.p1_y - ny * self.offset),
            (self.p2_x - nx * self.offset, self.p2_y - ny * self.offset),
        )

    def set_offset_from_point(self, anchor_x: float, anchor_y: float) -> None:
        """Обновить отступ размерной линии по опорной точке."""
        if self.measurement_mode == 'horizontal':
            max_y = max(self.p1_y, self.p2_y)
            min_y = min(self.p1_y, self.p2_y)
            middle_y = (max_y + min_y) / 2.0
            self.offset = anchor_y - (max_y if anchor_y >= middle_y else min_y)
            return

        if self.measurement_mode == 'vertical':
            max_x = max(self.p1_x, self.p2_x)
            min_x = min(self.p1_x, self.p2_x)
            middle_x = (max_x + min_x) / 2.0
            self.offset = anchor_x - (max_x if anchor_x >= middle_x else min_x)
            return

        vectors = self._get_vectors()
        if vectors is None:
            return
        _, _, _, nx, ny = vectors
        mx = anchor_x - self.p1_x
        my = anchor_y - self.p1_y
        self.offset = -(mx * nx + my * ny)

    def _get_text_anchor_world(self) -> Tuple[float, float]:
        """Получить опорную точку текста на размерной линии в мировых координатах."""
        vectors = self._get_vectors()
        if vectors is None:
            return ((self.p1_x + self.p2_x) / 2, (self.p1_y + self.p2_y) / 2)

        _, lx, ly, nx, ny = vectors
        dim_p1, dim_p2 = self._get_dimension_world_points()
        mid_x = (dim_p1[0] + dim_p2[0]) / 2
        mid_y = (dim_p1[1] + dim_p2[1]) / 2

        return (
            mid_x + lx * self.text_pos_x,
            mid_y + ly * self.text_pos_x
        )

    def _update_points(self, bg_manager: Any = None) -> None:
        """Обновить точки из ассоциированных фигур.
        
        base_point_id хранит индекс snap-точки в списке get_snap_points() фигуры.
        Это однозначно идентифицирует точку (в отличие от типа, где у отрезка два 'endpoint').
        """
        if not bg_manager:
            return
            
        if self.base_shape_id1:
            s1 = bg_manager.get_shape_by_id(self.base_shape_id1)
            if s1:
                snap_pts = s1.get_snap_points()
                idx = self.base_point_id1
                if isinstance(idx, int) and 0 <= idx < len(snap_pts):
                    self.p1_x, self.p1_y = snap_pts[idx][1], snap_pts[idx][2]
                        
        if self.base_shape_id2:
            s2 = bg_manager.get_shape_by_id(self.base_shape_id2)
            if s2:
                snap_pts = s2.get_snap_points()
                idx = self.base_point_id2
                if isinstance(idx, int) and 0 <= idx < len(snap_pts):
                    self.p2_x, self.p2_y = snap_pts[idx][1], snap_pts[idx][2]

    def draw(self, renderer, width: int, height: int, view_transform, point_radius: int = 4) -> None:
        color = "#55ff55" if self.selected else self.color
        line_width, dash_pattern = self._get_line_params(renderer)
        
        # Попытка обновить точки, если передан менеджер фигур (хак: берем его из приложения, если доступно)
        if hasattr(renderer, "app"):
            self._update_points(renderer.app.shape_manager)

        base_sp1 = view_transform.world_to_screen(self.p1_x, self.p1_y, width, height)
        base_sp2 = view_transform.world_to_screen(self.p2_x, self.p2_y, width, height)
        dim_wp1, dim_wp2 = self._get_dimension_world_points()
        sp1 = view_transform.world_to_screen(dim_wp1[0], dim_wp1[1], width, height)
        sp2 = view_transform.world_to_screen(dim_wp2[0], dim_wp2[1], width, height)

        # Вычисление угла и нормали
        dx = sp2[0] - sp1[0]
        dy = sp2[1] - sp1[1]
        length = math.hypot(dx, dy)
        
        if length < 1e-5:
            return
            
        angle_rad = math.atan2(dy, dx)

        extend_screen = 2.0 * view_transform.scale

        def _extension_end(base_point: Tuple[float, float],
                           dim_point: Tuple[float, float]) -> Tuple[float, float]:
            ext_dx = dim_point[0] - base_point[0]
            ext_dy = dim_point[1] - base_point[1]
            ext_length = math.hypot(ext_dx, ext_dy)
            if ext_length < 1e-5:
                return dim_point
            return (
                dim_point[0] + ext_dx / ext_length * extend_screen,
                dim_point[1] + ext_dy / ext_length * extend_screen
            )

        dim_p1 = sp1
        dim_p2 = sp2
        ext1_end = _extension_end(base_sp1, dim_p1)
        ext2_end = _extension_end(base_sp2, dim_p2)
        
        renderer.canvas.create_line(
            base_sp1[0], base_sp1[1], ext1_end[0], ext1_end[1],
            fill=color, width=line_width, dash=dash_pattern, tags="shape"
        )
        renderer.canvas.create_line(
            base_sp2[0], base_sp2[1], ext2_end[0], ext2_end[1],
            fill=color, width=line_width, dash=dash_pattern, tags="shape"
        )
        
        val = self.get_measurement_value()
        text = self._compose_dimension_text(val)
        text_width = self._measure_text_width(text)
        half_text = text_width / 2.0

        # Текст всегда располагается над размерной линией.
        # Если не влезает между стрелками, продолжаем линию за стрелку
        # и ставим текст над этим продолжением.
        mid_x = (dim_p1[0] + dim_p2[0]) / 2
        mid_y = (dim_p1[1] + dim_p2[1]) / 2
        screen_txt_offset_x = self.text_pos_x * view_transform.scale
        lx, ly = math.cos(angle_rad), math.sin(angle_rad)
        arrow_clearance = self.arrow_size * 1.5
        text_clearance = max(10.0, self.font_size * 0.9)
        screen_offset = math.hypot(dim_p1[0] - base_sp1[0], dim_p1[1] - base_sp1[1])
        ext_dx = dim_p1[0] - base_sp1[0]
        ext_dy = dim_p1[1] - base_sp1[1]
        if math.hypot(ext_dx, ext_dy) > 1e-5:
            nx = ext_dx / max(1e-5, math.hypot(ext_dx, ext_dy))
            ny = ext_dy / max(1e-5, math.hypot(ext_dx, ext_dy))
        else:
            nx = -math.sin(angle_rad)
            ny = math.cos(angle_rad)
        text_side_sign = -1.0 if self.offset <= 0 else 1.0
        inside_limit = max(0.0, length / 2 - arrow_clearance - half_text - 6.0)
        must_outside = (length / 2) <= (arrow_clearance + half_text + 6.0)
        is_outside = must_outside or abs(screen_txt_offset_x) > inside_limit

        renderer.canvas.create_line(
            dim_p1[0], dim_p1[1], dim_p2[0], dim_p2[1],
            fill=color, width=line_width, dash=dash_pattern, tags="shape"
        )

        if is_outside:
            direction = 1 if screen_txt_offset_x >= 0 else -1
            arrow_point = dim_p2 if direction > 0 else dim_p1
            overflow = abs(screen_txt_offset_x) - inside_limit
            center_dist = half_text + max(12.0, overflow)
            line_text_x = arrow_point[0] + direction * lx * center_dist
            line_text_y = arrow_point[1] + direction * ly * center_dist
            continuation_end = (
                line_text_x + direction * lx * (half_text + 6.0),
                line_text_y + direction * ly * (half_text + 6.0)
            )
            renderer.canvas.create_line(
                arrow_point[0], arrow_point[1], continuation_end[0], continuation_end[1],
                fill=color, width=line_width, dash=dash_pattern, tags="shape"
            )
        else:
            clamped_screen_offset = max(-inside_limit, min(inside_limit, screen_txt_offset_x))
            line_text_x = mid_x + lx * clamped_screen_offset
            line_text_y = mid_y + ly * clamped_screen_offset

        is_vertical_dim = abs(ly) > abs(lx)
        is_horizontal_dim = not is_vertical_dim
        if is_vertical_dim:
            text_side_sign = -1.0 if nx > 0 else 1.0
        elif is_horizontal_dim:
            text_side_sign = -1.0 if ny > 0 else 1.0

        text_x = line_text_x + nx * text_side_sign * text_clearance
        text_y = line_text_y + ny * text_side_sign * text_clearance

        # Стрелки рисуем поверх линии.
        self._draw_arrow(renderer, dim_p1[0], dim_p1[1], angle_rad + math.pi, color, line_width)
        self._draw_arrow(renderer, dim_p2[0], dim_p2[1], angle_rad, color, line_width)

        angle_deg = math.degrees(angle_rad)
        if 90 < angle_deg <= 270 or -270 < angle_deg <= -90:
            angle_deg += 180
        text_angle = -angle_deg
        if is_vertical_dim:
            text_angle = 90
        renderer.canvas.create_text(
            text_x, text_y, text=text, fill=color,
            font=self._get_text_font(), angle=text_angle,
            anchor="center", tags="shape"
        )

    def get_info(self, is_degrees: bool = True) -> str:
        val = self.get_measurement_value()
        return (
            f"Линейный размер\n"
            f"Тип: {self.get_measurement_mode_name()}\n"
            f"Значение: {self._format_value(val)}\n"
            f"Отступ: {self.offset:.1f}"
        )

    def get_bounds(self) -> Tuple[float, float, float, float]:
        # Упрощенные границы по базовым точкам
        min_x = min(self.p1_x, self.p2_x)
        min_y = min(self.p1_y, self.p2_y)
        max_x = max(self.p1_x, self.p2_x)
        max_y = max(self.p1_y, self.p2_y)
        # Добавляем отступ (приближенно)
        extra = abs(self.offset) + abs(self.text_pos_x) + (self.font_size * 3)
        return min_x - extra, min_y - extra, max_x + extra, max_y + extra

    def translate(self, dx: float, dy: float) -> None:
        if not self.base_shape_id1 and not self.base_shape_id2:
            self.p1_x += dx; self.p1_y += dy
            self.p2_x += dx; self.p2_y += dy

    def get_control_points(self) -> List[Tuple[str, float, float]]:
        """Контрольные точки для текста и выносных точек."""
        anchor_x, anchor_y = self._get_text_anchor_world()
        return [
            ('text_anchor', anchor_x, anchor_y),
            ('p1_anchor', self.p1_x, self.p1_y),
            ('p2_anchor', self.p2_x, self.p2_y),
        ]

    def move_control_point(self, point_id: str, new_x: float, new_y: float) -> None:
        """Переместить текст/полку вдоль и поперек размерной линии."""
        vectors = self._get_vectors()
        if vectors is None:
            return

        _, lx, ly, _, _ = vectors
        dim_p1, dim_p2 = self._get_dimension_world_points()
        mid_x = (dim_p1[0] + dim_p2[0]) / 2
        mid_y = (dim_p1[1] + dim_p2[1]) / 2
        if point_id == 'text_anchor':
            rel_x = new_x - mid_x
            rel_y = new_y - mid_y
            self.text_pos_x = rel_x * lx + rel_y * ly
            self.set_offset_from_point(new_x, new_y)
        elif point_id == 'p1_anchor':
            self.base_shape_id1 = None
            self.base_point_id1 = None
            self.p1_x, self.p1_y = new_x, new_y
        elif point_id == 'p2_anchor':
            self.base_shape_id2 = None
            self.base_point_id2 = None
            self.p2_x, self.p2_y = new_x, new_y

    def distance_to_point(self, px: float, py: float, width: int, height: int, view_transform) -> float:
        # Упрощенная проверка клика - по размерной линии
        dim_wp1, dim_wp2 = self._get_dimension_world_points()
        dim_p1 = view_transform.world_to_screen(dim_wp1[0], dim_wp1[1], width, height)
        dim_p2 = view_transform.world_to_screen(dim_wp2[0], dim_wp2[1], width, height)
        return SegmentGeometry.point_to_segment_distance(px, py, dim_p1[0], dim_p1[1], dim_p2[0], dim_p2[1])

    def to_dict(self) -> dict:
        d = self._base_dict()
        d.update({
            'id': self.id,
            'type': 'linear_dimension',
            'p1_x': self.p1_x, 'p1_y': self.p1_y,
            'p2_x': self.p2_x, 'p2_y': self.p2_y,
            'offset': self.offset,
            'measurement_mode': self.measurement_mode,
            'base_shape_id1': self.base_shape_id1,
            'base_point_id1': self.base_point_id1,
            'base_shape_id2': self.base_shape_id2,
            'base_point_id2': self.base_point_id2
        })
        return d

    @staticmethod
    def from_dict(data: dict) -> 'LinearDimension':
        dim = LinearDimension(
            (data['p1_x'], data['p1_y']),
            (data['p2_x'], data['p2_y']),
            data.get('offset', 30.0),
            data.get('measurement_mode', 'aligned')
        )
        dim.id = data.get('id', dim.id)
        dim._apply_base_dict(data)
        dim.base_shape_id1 = data.get('base_shape_id1')
        dim.base_point_id1 = data.get('base_point_id1')
        dim.base_shape_id2 = data.get('base_shape_id2')
        dim.base_point_id2 = data.get('base_point_id2')
        return dim


class RadialDimension(Dimension):
    """Радиальный размер"""
    def __init__(self, cx: float, cy: float, radius: float, is_diameter: bool = False):
        super().__init__()
        self.cx = cx
        self.cy = cy
        self.radius = radius
        self.is_diameter = is_diameter
        
        self.angle_rad = math.pi / 4  # Угол наклона размерной линии
        self.display_mode = 'leader'
        self.outside_orientation = 'horizontal'
        self.outside_side = -1
        self.outside_offset = 20.0
        self.line_extension = 24.0
        self.base_shape_id = None
        self._last_view_scale = 1.0
        
    def _update_params(self, bg_manager: Any = None) -> None:
        if not bg_manager or not self.base_shape_id:
            return
        shape = bg_manager.get_shape_by_id(self.base_shape_id)
        if shape:
            if hasattr(shape, 'x') and hasattr(shape, 'y') and hasattr(shape, 'radius'):
                self.cx = shape.x
                self.cy = shape.y
                self.radius = shape.radius
            elif hasattr(shape, 'cx') and hasattr(shape, 'cy') and hasattr(shape, 'radius'):
                self.cx = shape.cx
                self.cy = shape.cy
                self.radius = shape.radius

    def draw(self, renderer, width: int, height: int, view_transform, point_radius: int = 4) -> None:
        color = "#55ff55" if self.selected else self.color
        line_width, dash_pattern = self._get_line_params(renderer)
        if hasattr(renderer, "app"):
            self._update_params(renderer.app.shape_manager)
        self._last_view_scale = max(1e-6, view_transform.scale)

        sc = view_transform.world_to_screen(self.cx, self.cy, width, height)
        radius_screen = self.radius * view_transform.scale
        ux = math.cos(self.angle_rad)
        uy = math.sin(self.angle_rad)
        
        # Точка на окружности
        px = self.cx + self.radius * ux
        py = self.cy + self.radius * uy
        sp = view_transform.world_to_screen(px, py, width, height)
        opposite = view_transform.world_to_screen(
            self.cx - self.radius * ux, self.cy - self.radius * uy, width, height
        )
        screen_angle = math.atan2(sp[1] - sc[1], sp[0] - sc[0])

        val = self.radius * 2 if self.is_diameter else self.radius
        prefix = "⌀" if self.is_diameter else "R"
        text = self._compose_dimension_text(val, auto_prefix=prefix)
        text_width = self._measure_text_width(text)

        if self.display_mode == 'aligned':
            self._draw_aligned_radial(
                renderer, color, line_width, dash_pattern, sc, sp, opposite,
                ux, uy, screen_angle, text, text_width
            )
        elif self.display_mode == 'outside' and self.is_diameter:
            self._draw_outside_diameter(
                renderer, color, line_width, dash_pattern, sc, radius_screen, text, text_width
            )
        else:
            self._draw_leader_radial(
                renderer, color, line_width, dash_pattern, sc, sp, opposite,
                ux, uy, screen_angle, text, text_width
            )

    def _draw_leader_radial(self, renderer, color: str, line_width: int, dash_pattern: Optional[Tuple[int, ...]],
                            sc: Tuple[float, float], sp: Tuple[float, float], opposite: Tuple[float, float],
                            ux: float, uy: float, screen_angle: float,
                            text: str, text_width: float) -> None:
        """Полка с горизонтальной выноской."""
        if self.shelf_dir_override != 0:
            shelf_dir = self.shelf_dir_override
        else:
            shelf_dir = 1 if ux >= 0 else -1
        shelf_length = max(28.0, text_width + 22.0)
        shelf_start = (
            sp[0] + math.cos(screen_angle) * self.shelf_offset,
            sp[1] + math.sin(screen_angle) * self.shelf_offset
        )

        if self.is_diameter:
            renderer.canvas.create_line(
                opposite[0], opposite[1], sp[0], sp[1],
                fill=color, width=line_width, dash=dash_pattern, tags="shape"
            )
            self._draw_arrow(renderer, opposite[0], opposite[1], screen_angle + math.pi, color, line_width)
        else:
            renderer.canvas.create_line(
                sc[0], sc[1], sp[0], sp[1],
                fill=color, width=line_width, dash=dash_pattern, tags="shape"
            )

        renderer.canvas.create_line(
            sp[0], sp[1], shelf_start[0], shelf_start[1],
            fill=color, width=line_width, dash=dash_pattern, tags="shape"
        )
        shelf_end = (shelf_start[0] + shelf_dir * shelf_length, shelf_start[1])
        renderer.canvas.create_line(
            shelf_start[0], shelf_start[1], shelf_end[0], shelf_end[1],
            fill=color, width=line_width, dash=dash_pattern, tags="shape"
        )
        self._draw_arrow(renderer, sp[0], sp[1], screen_angle, color, line_width)
        text_x = shelf_start[0] + shelf_dir * (shelf_length / 2)
        renderer.canvas.create_text(
            text_x, shelf_start[1] - max(8.0, self.font_size * 0.8),
            text=text, fill=color, font=self._get_text_font(),
            anchor="s", tags="shape"
        )

    def _draw_aligned_radial(self, renderer, color: str, line_width: int, dash_pattern: Optional[Tuple[int, ...]],
                             sc: Tuple[float, float], sp: Tuple[float, float], opposite: Tuple[float, float],
                             ux: float, uy: float, screen_angle: float,
                             text: str, text_width: float) -> None:
        """Размер по наклонной линии с текстом вдоль неё."""
        start = opposite if self.is_diameter else sc
        end = sp
        extension = max(10.0, self.line_extension)
        dx = math.cos(screen_angle)
        dy = math.sin(screen_angle)
        ext_end = (end[0] + dx * extension, end[1] + dy * extension)

        renderer.canvas.create_line(
            start[0], start[1], ext_end[0], ext_end[1],
            fill=color, width=line_width, dash=dash_pattern, tags="shape"
        )
        if self.is_diameter:
            self._draw_arrow(renderer, opposite[0], opposite[1], screen_angle + math.pi, color, line_width)
        self._draw_arrow(renderer, sp[0], sp[1], screen_angle, color, line_width)

        half_text = text_width / 2.0
        text_gap = max(10.0, self.font_size * 0.9)
        nx = -math.sin(screen_angle)
        ny = math.cos(screen_angle)
        if ny > 0:
            nx = -nx
            ny = -ny
        text_end_inset = half_text + 8.0
        text_center = (
            ext_end[0] - dx * text_end_inset + nx * text_gap,
            ext_end[1] - dy * text_end_inset + ny * text_gap
        )
        angle_deg = math.degrees(screen_angle)
        if 90 < angle_deg <= 270 or -270 < angle_deg <= -90:
            angle_deg += 180
        renderer.canvas.create_text(
            text_center[0], text_center[1], text=text, fill=color,
            font=self._get_text_font(), angle=-angle_deg,
            anchor="center", tags="shape"
        )

    def _draw_outside_diameter(self, renderer, color: str, line_width: int,
                               dash_pattern: Optional[Tuple[int, ...]], sc: Tuple[float, float],
                               radius_screen: float, text: str, text_width: float) -> None:
        """Наружный диаметр горизонтально или вертикально."""
        offset = radius_screen + max(14.0, self.outside_offset)
        text_gap = max(10.0, self.font_size * 0.8)

        if self.outside_orientation == 'horizontal':
            x1 = sc[0] - radius_screen
            x2 = sc[0] + radius_screen
            y = sc[1] + self.outside_side * offset
            ext_end_y = y
            renderer.canvas.create_line(x1, sc[1], x1, ext_end_y, fill=color, width=line_width, dash=dash_pattern, tags="shape")
            renderer.canvas.create_line(x2, sc[1], x2, ext_end_y, fill=color, width=line_width, dash=dash_pattern, tags="shape")
            renderer.canvas.create_line(x1, y, x2, y, fill=color, width=line_width, dash=dash_pattern, tags="shape")
            self._draw_arrow(renderer, x1, y, math.pi, color, line_width)
            self._draw_arrow(renderer, x2, y, 0.0, color, line_width)
            renderer.canvas.create_text(
                (x1 + x2) / 2, y - text_gap,
                text=text, fill=color, font=self._get_text_font(),
                anchor="s", tags="shape"
            )
        else:
            y1 = sc[1] - radius_screen
            y2 = sc[1] + radius_screen
            x = sc[0] + self.outside_side * offset
            ext_end_x = x
            renderer.canvas.create_line(sc[0], y1, ext_end_x, y1, fill=color, width=line_width, dash=dash_pattern, tags="shape")
            renderer.canvas.create_line(sc[0], y2, ext_end_x, y2, fill=color, width=line_width, dash=dash_pattern, tags="shape")
            renderer.canvas.create_line(x, y1, x, y2, fill=color, width=line_width, dash=dash_pattern, tags="shape")
            self._draw_arrow(renderer, x, y1, -math.pi / 2, color, line_width)
            self._draw_arrow(renderer, x, y2, math.pi / 2, color, line_width)
            renderer.canvas.create_text(
                x - text_gap, (y1 + y2) / 2,
                text=text, fill=color, font=self._get_text_font(),
                angle=90,
                anchor="center", tags="shape"
            )

    def get_info(self, is_degrees: bool = True) -> str:
        val = self.radius * 2 if self.is_diameter else self.radius
        prefix = "Диаметр" if self.is_diameter else "Радиус"
        return f"{prefix}ой размер\nЗначение: {self._format_value(val)}"

    def get_bounds(self) -> Tuple[float, float, float, float]:
        val = self.radius * 2 if self.is_diameter else self.radius
        prefix = "⌀" if self.is_diameter else "R"
        text_width = self._measure_text_width(self._compose_dimension_text(val, auto_prefix=prefix))
        leader_extent = self.shelf_offset + max(28.0, text_width + 22.0)
        r = self.radius + max(
            leader_extent,
            self.line_extension,
            self.outside_offset,
            self.font_size * 2
        )
        return self.cx - r, self.cy - r, self.cx + r, self.cy + r

    def distance_to_point(self, px: float, py: float, width: int, height: int, view_transform) -> float:
        sc = view_transform.world_to_screen(self.cx, self.cy, width, height)
        p_x = self.cx + self.radius * math.cos(self.angle_rad)
        p_y = self.cy + self.radius * math.sin(self.angle_rad)
        sp = view_transform.world_to_screen(p_x, p_y, width, height)
        return SegmentGeometry.point_to_segment_distance(px, py, sc[0], sc[1], sp[0], sp[1])

    def get_control_points(self) -> List[Tuple[str, float, float]]:
        """Контрольная точка для ручного выноса полки."""
        ux = math.cos(self.angle_rad)
        uy = math.sin(self.angle_rad)
        scale = max(1e-6, self._last_view_scale)

        if self.display_mode == 'leader':
            offset_world = self.shelf_offset / scale
            anchor_x = self.cx + (self.radius + offset_world) * ux
            anchor_y = self.cy + (self.radius + offset_world) * uy
            return [('shelf_anchor', anchor_x, anchor_y)]

        if self.display_mode == 'aligned':
            ext_world = self.line_extension / scale
            anchor_x = self.cx + (self.radius + ext_world) * ux
            anchor_y = self.cy + (self.radius + ext_world) * uy
            return [('line_extension_anchor', anchor_x, anchor_y)]

        if self.display_mode == 'outside':
            outside_world = self.outside_offset / scale
            if self.outside_orientation == 'horizontal':
                anchor_x = self.cx
                anchor_y = self.cy + self.outside_side * (self.radius + outside_world)
            else:
                anchor_x = self.cx + self.outside_side * (self.radius + outside_world)
                anchor_y = self.cy
            return [('outside_offset_anchor', anchor_x, anchor_y)]

        return []

    def move_control_point(self, point_id: str, new_x: float, new_y: float) -> None:
        """Переместить вынос полки вдоль размерной линии."""
        ux = math.cos(self.angle_rad)
        uy = math.sin(self.angle_rad)
        base_x = self.cx + self.radius * ux
        base_y = self.cy + self.radius * uy
        projected_world = (new_x - base_x) * ux + (new_y - base_y) * uy
        projected_screen = projected_world * max(1e-6, self._last_view_scale)

        if point_id == 'shelf_anchor':
            self.shelf_offset = max(0.0, projected_screen)
        elif point_id == 'line_extension_anchor':
            self.line_extension = max(10.0, projected_screen)
        elif point_id == 'outside_offset_anchor':
            if self.outside_orientation == 'horizontal':
                self.outside_offset = max(
                    0.0, (new_y - self.cy) * self.outside_side * max(1e-6, self._last_view_scale) - self.radius * max(1e-6, self._last_view_scale)
                )
            else:
                self.outside_offset = max(
                    0.0, (new_x - self.cx) * self.outside_side * max(1e-6, self._last_view_scale) - self.radius * max(1e-6, self._last_view_scale)
                )

    def to_dict(self) -> dict:
        d = self._base_dict()
        d.update({
            'id': self.id,
            'type': 'radial_dimension',
            'cx': self.cx, 'cy': self.cy,
            'radius': self.radius,
            'is_diameter': self.is_diameter,
            'angle_rad': self.angle_rad,
            'display_mode': self.display_mode,
            'outside_orientation': self.outside_orientation,
            'outside_side': self.outside_side,
            'outside_offset': self.outside_offset,
            'line_extension': self.line_extension,
            'base_shape_id': self.base_shape_id
        })
        return d

    @staticmethod
    def from_dict(data: dict) -> 'RadialDimension':
        dim = RadialDimension(data['cx'], data['cy'], data['radius'], data.get('is_diameter', False))
        dim.id = data.get('id', dim.id)
        dim.angle_rad = data.get('angle_rad', math.pi / 4)
        dim._apply_base_dict(data)
        raw_mode = data.get('display_mode', 'leader')
        if raw_mode == 'outside_horizontal':
            dim.display_mode = 'outside'
            dim.outside_orientation = 'vertical'
        elif raw_mode == 'outside_vertical':
            dim.display_mode = 'outside'
            dim.outside_orientation = 'horizontal'
        else:
            dim.display_mode = raw_mode
            dim.outside_orientation = data.get('outside_orientation', 'horizontal')
        dim.outside_side = data.get('outside_side', -1)
        dim.outside_offset = data.get('outside_offset', 20.0)
        dim.line_extension = data.get('line_extension', 24.0)
        dim.base_shape_id = data.get('base_shape_id')
        return dim

    def translate(self, dx: float, dy: float) -> None:
        if not self.base_shape_id:
            self.cx += dx; self.cy += dy

class AngularDimension(Dimension):
    """Угловой размер"""
    def __init__(self, cx: float, cy: float, p1: Tuple[float, float], p2: Tuple[float, float], radius: float = 30.0):
        super().__init__()
        self.cx, self.cy = cx, cy
        self.p1_x, self.p1_y = p1
        self.p2_x, self.p2_y = p2
        self.radius = radius
        self.use_reflex = False
        self.base_shape_id1 = None
        self.base_shape_id2 = None
        self.ray_point_id1 = None
        self.ray_point_id2 = None

    @staticmethod
    def _normalize_angle(angle_rad: float) -> float:
        """Нормализовать угол в диапазон [0, 2pi)."""
        return angle_rad % (2 * math.pi)

    @staticmethod
    def _normalize_signed_delta(delta_rad: float) -> float:
        """Нормализовать разницу углов в диапазон (-pi, pi]."""
        while delta_rad <= -math.pi:
            delta_rad += 2 * math.pi
        while delta_rad > math.pi:
            delta_rad -= 2 * math.pi
        return delta_rad

    @staticmethod
    def _find_line_intersection_points(seg1: Any, seg2: Any) -> Optional[Tuple[float, float]]:
        """Найти пересечение бесконечных прямых, заданных двумя отрезками."""
        x1, y1, x2, y2 = seg1.x1, seg1.y1, seg1.x2, seg1.y2
        x3, y3, x4, y4 = seg2.x1, seg2.y1, seg2.x2, seg2.y2
        denominator = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
        if abs(denominator) < 1e-9:
            return None

        det1 = x1 * y2 - y1 * x2
        det2 = x3 * y4 - y3 * x4
        px = (det1 * (x3 - x4) - (x1 - x2) * det2) / denominator
        py = (det1 * (y3 - y4) - (y1 - y2) * det2) / denominator
        return (px, py)

    @staticmethod
    def _resolve_vertex(seg1: Any, seg2: Any) -> Optional[Tuple[float, float]]:
        """Найти вершину угла по двум отрезкам."""
        endpoints1 = [(seg1.x1, seg1.y1), (seg1.x2, seg1.y2)]
        endpoints2 = [(seg2.x1, seg2.y1), (seg2.x2, seg2.y2)]

        for p1 in endpoints1:
            for p2 in endpoints2:
                if math.hypot(p1[0] - p2[0], p1[1] - p2[1]) <= 1e-6:
                    return p1

        return AngularDimension._find_line_intersection_points(seg1, seg2)

    def _update_points(self, bg_manager: Any = None) -> None:
        """Обновить вершину и лучи из связанных отрезков."""
        if not bg_manager or not self.base_shape_id1 or not self.base_shape_id2:
            return

        seg1 = bg_manager.get_shape_by_id(self.base_shape_id1)
        seg2 = bg_manager.get_shape_by_id(self.base_shape_id2)
        if seg1 is None or seg2 is None:
            return
        if not all(hasattr(seg, attr) for seg in (seg1, seg2) for attr in ('x1', 'y1', 'x2', 'y2')):
            return

        vertex = self._resolve_vertex(seg1, seg2)
        if vertex is None:
            return

        endpoints1 = [(seg1.x1, seg1.y1), (seg1.x2, seg1.y2)]
        endpoints2 = [(seg2.x1, seg2.y1), (seg2.x2, seg2.y2)]
        self.cx, self.cy = vertex
        if isinstance(self.ray_point_id1, int) and 0 <= self.ray_point_id1 < len(endpoints1):
            self.p1_x, self.p1_y = endpoints1[self.ray_point_id1]
        if isinstance(self.ray_point_id2, int) and 0 <= self.ray_point_id2 < len(endpoints2):
            self.p2_x, self.p2_y = endpoints2[self.ray_point_id2]

    def _get_ray_angles(self) -> Tuple[float, float, float]:
        """Получить углы лучей и меньший угол между ними."""
        angle1 = math.atan2(self.p1_y - self.cy, self.p1_x - self.cx)
        angle2 = math.atan2(self.p2_y - self.cy, self.p2_x - self.cx)
        minor_delta = self._normalize_signed_delta(angle2 - angle1)
        return angle1, angle2, minor_delta

    def update_arc_side(self, cursor_x: float, cursor_y: float) -> None:
        """Выбрать меньший или больший угол по положению курсора."""
        cursor_angle = math.atan2(cursor_y - self.cy, cursor_x - self.cx)
        angle1, _, minor_delta = self._get_ray_angles()
        cursor_delta = self._normalize_signed_delta(cursor_angle - angle1)

        if minor_delta >= 0:
            in_minor_sector = 0.0 <= cursor_delta <= minor_delta
        else:
            in_minor_sector = minor_delta <= cursor_delta <= 0.0

        self.use_reflex = not in_minor_sector

    def _get_arc_delta(self) -> float:
        """Получить текущий угол дуги с учетом выбранной стороны."""
        _, _, minor_delta = self._get_ray_angles()
        if self.use_reflex:
            return minor_delta - (2 * math.pi) if minor_delta > 0 else minor_delta + (2 * math.pi)
        return minor_delta

    def _build_arc_points(self, sc: Tuple[float, float], radius: float,
                          start_angle: float, delta_angle: float,
                          segments: int = 48) -> List[float]:
        """Построить точки дуги в экранных координатах."""
        points: List[float] = []
        segments = max(12, segments)
        for i in range(segments + 1):
            t = i / segments
            angle = start_angle + delta_angle * t
            points.extend([
                sc[0] + radius * math.cos(angle),
                sc[1] + radius * math.sin(angle)
            ])
        return points

    @staticmethod
    def _get_arc_tangent_angle(angle: float, delta_angle: float) -> float:
        """Получить угол касательной к дуге в экранных координатах."""
        if delta_angle >= 0:
            tx, ty = -math.sin(angle), math.cos(angle)
        else:
            tx, ty = math.sin(angle), -math.cos(angle)
        return math.atan2(ty, tx)
        
    def draw(self, renderer, width: int, height: int, view_transform, point_radius: int = 4) -> None:
        color = "#55ff55" if self.selected else self.color
        line_width, dash_pattern = self._get_line_params(renderer)
        if hasattr(renderer, "app"):
            self._update_points(renderer.app.shape_manager)
        
        sc = view_transform.world_to_screen(self.cx, self.cy, width, height)
        sp1 = view_transform.world_to_screen(self.p1_x, self.p1_y, width, height)
        sp2 = view_transform.world_to_screen(self.p2_x, self.p2_y, width, height)

        ray_angle1 = math.atan2(sp1[1] - sc[1], sp1[0] - sc[0])
        ray_angle2 = math.atan2(sp2[1] - sc[1], sp2[0] - sc[0])
        minor_delta = self._normalize_signed_delta(ray_angle2 - ray_angle1)
        arc_delta = self._get_arc_delta()
        if self.use_reflex:
            arc_delta = minor_delta - (2 * math.pi) if minor_delta > 0 else minor_delta + (2 * math.pi)
        else:
            arc_delta = minor_delta

        val_deg = abs(math.degrees(arc_delta))
            
        screen_radius = self.radius * view_transform.scale
        
        # Выносные линии от центра к точкам (длиннее радиуса дуги)
        ext_r = screen_radius + (5 * view_transform.scale)
        e1x = sc[0] + ext_r * math.cos(ray_angle1)
        e1y = sc[1] + ext_r * math.sin(ray_angle1)
        e2x = sc[0] + ext_r * math.cos(ray_angle2)
        e2y = sc[1] + ext_r * math.sin(ray_angle2)
        
        renderer.canvas.create_line(
            sc[0], sc[1], e1x, e1y,
            fill=color, width=line_width, dash=dash_pattern, tags="shape"
        )
        renderer.canvas.create_line(
            sc[0], sc[1], e2x, e2y,
            fill=color, width=line_width, dash=dash_pattern, tags="shape"
        )
        
        # Дуга размера
        arc_points = self._build_arc_points(sc, screen_radius, ray_angle1, arc_delta)
        renderer.canvas.create_line(
            *arc_points, fill=color, width=line_width,
            smooth=True, dash=dash_pattern, tags="shape"
        )
        
        mid_angle = ray_angle1 + arc_delta / 2
        
        # Стрелки
        self._draw_arrow(
            renderer,
            sc[0] + screen_radius * math.cos(ray_angle1),
            sc[1] + screen_radius * math.sin(ray_angle1),
            self._get_arc_tangent_angle(ray_angle1, arc_delta),
            color,
            line_width
        )
        self._draw_arrow(
            renderer,
            sc[0] + screen_radius * math.cos(ray_angle2),
            sc[1] + screen_radius * math.sin(ray_angle2),
            self._get_arc_tangent_angle(ray_angle2, arc_delta) + math.pi,
            color,
            line_width
        )
        
        # Текст
        text_radius = screen_radius + max(14.0, self.font_size * 1.2)
        tx = sc[0] + text_radius * math.cos(mid_angle)
        ty = sc[1] + text_radius * math.sin(mid_angle)
        text = self._compose_dimension_text(val_deg, auto_suffix="°")
        tangent_angle = self._get_arc_tangent_angle(mid_angle, arc_delta)
        tangent_deg = math.degrees(tangent_angle)
        if 90 < tangent_deg <= 270 or -270 < tangent_deg <= -90:
            tangent_deg += 180
        renderer.canvas.create_text(
            tx, ty, text=text, fill=color,
            font=self._get_text_font(), angle=-tangent_deg,
            anchor="center", tags="shape"
        )
        
    def get_info(self, is_degrees: bool = True) -> str:
        return f"Угловой размер"

    def get_bounds(self) -> Tuple[float, float, float, float]:
        return self.cx - self.radius, self.cy - self.radius, self.cx + self.radius, self.cy + self.radius

    def distance_to_point(self, px: float, py: float, width: int, height: int, view_transform) -> float:
        sc = view_transform.world_to_screen(self.cx, self.cy, width, height)
        dist = math.hypot(px - sc[0], py - sc[1])
        screen_radius = self.radius * view_transform.scale
        return abs(dist - screen_radius)

    def translate(self, dx: float, dy: float) -> None:
        self.cx += dx; self.cy += dy
        self.p1_x += dx; self.p1_y += dy
        self.p2_x += dx; self.p2_y += dy

    def get_control_points(self) -> List[Tuple[str, float, float]]:
        """Контрольные точки радиуса дуги и лучей."""
        mid_angle = math.atan2(self.p1_y - self.cy, self.p1_x - self.cx) + self._get_arc_delta() / 2.0
        return [
            ('radius_anchor', self.cx + self.radius * math.cos(mid_angle), self.cy + self.radius * math.sin(mid_angle)),
            ('ray1_anchor', self.p1_x, self.p1_y),
            ('ray2_anchor', self.p2_x, self.p2_y),
        ]

    def move_control_point(self, point_id: str, new_x: float, new_y: float) -> None:
        """Переместить радиус дуги или лучи угла."""
        if point_id == 'radius_anchor':
            self.radius = max(0.1, math.hypot(new_x - self.cx, new_y - self.cy))
            self.update_arc_side(new_x, new_y)
        elif point_id == 'ray1_anchor':
            self.base_shape_id1 = None
            self.ray_point_id1 = None
            self.p1_x, self.p1_y = new_x, new_y
        elif point_id == 'ray2_anchor':
            self.base_shape_id2 = None
            self.ray_point_id2 = None
            self.p2_x, self.p2_y = new_x, new_y

    def to_dict(self) -> dict:
        d = self._base_dict()
        d.update({
            'id': self.id,
            'type': 'angular_dimension',
            'cx': self.cx, 'cy': self.cy,
            'p1_x': self.p1_x, 'p1_y': self.p1_y,
            'p2_x': self.p2_x, 'p2_y': self.p2_y,
            'radius': self.radius,
            'use_reflex': self.use_reflex,
            'base_shape_id1': self.base_shape_id1,
            'base_shape_id2': self.base_shape_id2,
            'ray_point_id1': self.ray_point_id1,
            'ray_point_id2': self.ray_point_id2
        })
        return d

    @staticmethod
    def from_dict(data: dict) -> 'AngularDimension':
        dim = AngularDimension(data['cx'], data['cy'], (data['p1_x'], data['p1_y']), (data['p2_x'], data['p2_y']), data.get('radius', 30.0))
        dim.id = data.get('id', dim.id)
        dim._apply_base_dict(data)
        dim.use_reflex = data.get('use_reflex', False)
        dim.base_shape_id1 = data.get('base_shape_id1')
        dim.base_shape_id2 = data.get('base_shape_id2')
        dim.ray_point_id1 = data.get('ray_point_id1')
        dim.ray_point_id2 = data.get('ray_point_id2')
        return dim
