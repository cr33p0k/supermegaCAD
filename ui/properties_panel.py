"""Панель свойств для редактирования параметров фигур"""
import tkinter as tk
from tkinter import ttk
from typing import Any, Optional, Callable
import math


class PropertiesPanel:
    """Динамическая панель свойств для редактирования фигур"""
    
    def __init__(self, parent: ttk.Frame, app: Any):
        self.parent = parent
        self.app = app
        self.current_shape = None
        self._widgets = {}
        self._vars = {}
        self._updating = False  # Флаг для предотвращения рекурсии
        
        self._build_ui()
    
    def _build_ui(self) -> None:
        """Построение UI панели"""
        # Заголовок
        self.title_label = ttk.Label(self.parent, text="Свойства объекта", 
                                      font=("Arial", 10, "bold"))
        self.title_label.pack(anchor=tk.W, padx=6, pady=(6, 2))
        
        # Контейнер для свойств
        self.props_frame = ttk.Frame(self.parent)
        self.props_frame.pack(fill=tk.BOTH, expand=True, padx=6, pady=4)
        
        # Сообщение когда ничего не выбрано
        self.no_selection_label = ttk.Label(
            self.props_frame, 
            text="Выберите объект\nдля редактирования",
            justify=tk.CENTER
        )
        self.no_selection_label.pack(expand=True)
    
    def update_for_shape(self, shape: Any) -> None:
        """Обновить панель для выбранной фигуры"""
        if self._updating:
            return
        
        self._updating = True
        
        try:
            # Очищаем предыдущие виджеты
            for widget in self.props_frame.winfo_children():
                widget.destroy()
            
            self._widgets.clear()
            self._vars.clear()
            self.current_shape = shape
            
            if shape is None:
                self.title_label.config(text="Свойства объекта")
                self.no_selection_label = ttk.Label(
                    self.props_frame,
                    text="Выберите объект\nдля редактирования",
                    justify=tk.CENTER
                )
                self.no_selection_label.pack(expand=True)
                return
            
            # Определяем тип фигуры и создаём соответствующие поля
            shape_type = type(shape).__name__
            self.title_label.config(text=f"Свойства: {self._get_shape_name(shape_type)}")
            
            # Создаём поля в зависимости от типа фигуры
            if shape_type == 'Segment':
                self._build_segment_props(shape)
            elif shape_type == 'Circle':
                self._build_circle_props(shape)
            elif shape_type == 'Arc':
                self._build_arc_props(shape)
            elif shape_type == 'Rectangle':
                self._build_rectangle_props(shape)
            elif shape_type == 'Ellipse':
                self._build_ellipse_props(shape)
            elif shape_type == 'Polygon':
                self._build_polygon_props(shape)
            elif shape_type == 'Spline':
                self._build_spline_props(shape)
            elif shape_type in ('LinearDimension', 'RadialDimension', 'AngularDimension'):
                self._build_dimension_props(shape)
            
            # Общие свойства (стиль линии)
            if shape_type in ('LinearDimension', 'RadialDimension', 'AngularDimension'):
                self._build_dimension_style_props(shape)
            else:
                self._build_common_props(shape)
        
        finally:
            self._updating = False
    
    def _get_shape_name(self, shape_type: str) -> str:
        """Получить название фигуры на русском"""
        names = {
            'Segment': 'Отрезок',
            'Circle': 'Окружность',
            'Arc': 'Дуга',
            'Rectangle': 'Прямоугольник',
            'Ellipse': 'Эллипс',
            'Polygon': 'Многоугольник',
            'Spline': 'Сплайн',
            'LinearDimension': 'Линейный размер',
            'RadialDimension': 'Радиальный размер',
            'AngularDimension': 'Угловой размер',
        }
        return names.get(shape_type, shape_type)
    
    def _create_field(self, label: str, attr: str, shape: Any, 
                      row: int, min_val: float = None, max_val: float = None) -> None:
        """Создать поле ввода для атрибута"""
        ttk.Label(self.props_frame, text=label).grid(
            row=row, column=0, sticky=tk.W, padx=2, pady=2
        )
        
        var = tk.DoubleVar(value=getattr(shape, attr, 0))
        self._vars[attr] = var
        
        entry = ttk.Entry(self.props_frame, textvariable=var, width=12)
        entry.grid(row=row, column=1, sticky=tk.EW, padx=2, pady=2)
        self._widgets[attr] = entry
        
        def on_change(event=None):
            if self._updating:
                return
            try:
                value = float(var.get())
                if min_val is not None:
                    value = max(min_val, value)
                if max_val is not None:
                    value = min(max_val, value)
                setattr(shape, attr, value)
                self.app.redraw()
            except (ValueError, tk.TclError):
                pass
            # При Enter убираем фокус с поля
            if event and event.keysym == 'Return':
                self.app.canvas.focus_set()
        
        entry.bind('<Return>', on_change)
        entry.bind('<FocusOut>', on_change)
    
    def _create_int_field(self, label: str, attr: str, shape: Any,
                          row: int, min_val: int = None, max_val: int = None) -> None:
        """Создать поле ввода для целочисленного атрибута"""
        ttk.Label(self.props_frame, text=label).grid(
            row=row, column=0, sticky=tk.W, padx=2, pady=2
        )
        
        var = tk.IntVar(value=getattr(shape, attr, 0))
        self._vars[attr] = var
        
        spinbox = ttk.Spinbox(self.props_frame, textvariable=var, width=10,
                              from_=min_val or 3, to=max_val or 100)
        spinbox.grid(row=row, column=1, sticky=tk.EW, padx=2, pady=2)
        self._widgets[attr] = spinbox
        
        def on_change(event=None):
            if self._updating:
                return
            try:
                value = int(var.get())
                if min_val is not None:
                    value = max(min_val, value)
                if max_val is not None:
                    value = min(max_val, value)
                setattr(shape, attr, value)
                self.app.redraw()
            except (ValueError, tk.TclError):
                pass
            # При Enter убираем фокус с поля
            if event and hasattr(event, 'keysym') and event.keysym == 'Return':
                self.app.canvas.focus_set()
        
        spinbox.bind('<Return>', on_change)
        spinbox.bind('<FocusOut>', on_change)
        spinbox.config(command=on_change)
    
    def _create_checkbox(self, label: str, attr: str, shape: Any, row: int) -> None:
        """Создать чекбокс для булевого атрибута"""
        var = tk.BooleanVar(value=getattr(shape, attr, False))
        self._vars[attr] = var
        
        checkbox = ttk.Checkbutton(self.props_frame, text=label, variable=var)
        checkbox.grid(row=row, column=0, columnspan=2, sticky=tk.W, padx=2, pady=2)
        self._widgets[attr] = checkbox
        
        def on_change():
            if self._updating:
                return
            setattr(shape, attr, var.get())
            self.app.redraw()
        
        checkbox.config(command=on_change)
    
    def _build_segment_props(self, shape: Any) -> None:
        """Свойства отрезка"""
        self._create_field("X₁:", "x1", shape, 0)
        self._create_field("Y₁:", "y1", shape, 1)
        self._create_field("X₂:", "x2", shape, 2)
        self._create_field("Y₂:", "y2", shape, 3)
        
        # Вычисляемые свойства (только для отображения)
        ttk.Separator(self.props_frame, orient=tk.HORIZONTAL).grid(
            row=4, column=0, columnspan=2, sticky=tk.EW, pady=6
        )
        
        length = math.hypot(shape.x2 - shape.x1, shape.y2 - shape.y1)
        angle = math.degrees(math.atan2(shape.y2 - shape.y1, shape.x2 - shape.x1))
        
        ttk.Label(self.props_frame, text=f"Длина: {length:.2f}").grid(
            row=5, column=0, columnspan=2, sticky=tk.W, padx=2
        )
        ttk.Label(self.props_frame, text=f"Угол: {angle:.1f}°").grid(
            row=6, column=0, columnspan=2, sticky=tk.W, padx=2
        )
    
    def _build_circle_props(self, shape: Any) -> None:
        """Свойства окружности"""
        self._create_field("Центр X:", "cx", shape, 0)
        self._create_field("Центр Y:", "cy", shape, 1)
        self._create_field("Радиус:", "radius", shape, 2, min_val=0.1)
        
        ttk.Separator(self.props_frame, orient=tk.HORIZONTAL).grid(
            row=3, column=0, columnspan=2, sticky=tk.EW, pady=6
        )
        
        diameter = shape.radius * 2
        circumference = 2 * math.pi * shape.radius
        area = math.pi * shape.radius ** 2
        
        ttk.Label(self.props_frame, text=f"Диаметр: {diameter:.2f}").grid(
            row=4, column=0, columnspan=2, sticky=tk.W, padx=2
        )
        ttk.Label(self.props_frame, text=f"Длина: {circumference:.2f}").grid(
            row=5, column=0, columnspan=2, sticky=tk.W, padx=2
        )
        ttk.Label(self.props_frame, text=f"Площадь: {area:.2f}").grid(
            row=6, column=0, columnspan=2, sticky=tk.W, padx=2
        )
    
    def _build_arc_props(self, shape: Any) -> None:
        """Свойства дуги"""
        self._create_field("Центр X:", "cx", shape, 0)
        self._create_field("Центр Y:", "cy", shape, 1)
        self._create_field("Радиус:", "radius", shape, 2, min_val=0.1)
        self._create_field("Начальный угол:", "start_angle", shape, 3)
        self._create_field("Конечный угол:", "end_angle", shape, 4)
        
        ttk.Separator(self.props_frame, orient=tk.HORIZONTAL).grid(
            row=5, column=0, columnspan=2, sticky=tk.EW, pady=6
        )
        
        arc_length = shape.get_arc_length() if hasattr(shape, 'get_arc_length') else 0
        ttk.Label(self.props_frame, text=f"Длина дуги: {arc_length:.2f}").grid(
            row=6, column=0, columnspan=2, sticky=tk.W, padx=2
        )
    
    def _build_rectangle_props(self, shape: Any) -> None:
        """Свойства прямоугольника"""
        self._create_field("X:", "x", shape, 0)
        self._create_field("Y:", "y", shape, 1)
        self._create_field("Ширина:", "width", shape, 2, min_val=0.1)
        self._create_field("Высота:", "height", shape, 3, min_val=0.1)
        self._create_field("Поворот:", "rotation", shape, 4)
        
        ttk.Separator(self.props_frame, orient=tk.HORIZONTAL).grid(
            row=5, column=0, columnspan=2, sticky=tk.EW, pady=6
        )
        
        ttk.Label(self.props_frame, text="Модификаторы:").grid(
            row=6, column=0, columnspan=2, sticky=tk.W, padx=2
        )
        
        self._create_field("Скругление:", "corner_radius", shape, 7, min_val=0)
        self._create_field("Фаска:", "chamfer", shape, 8, min_val=0)
        
        ttk.Separator(self.props_frame, orient=tk.HORIZONTAL).grid(
            row=9, column=0, columnspan=2, sticky=tk.EW, pady=6
        )
        
        perimeter = 2 * (shape.width + shape.height)
        area = shape.width * shape.height
        diagonal = math.hypot(shape.width, shape.height)
        
        ttk.Label(self.props_frame, text=f"Периметр: {perimeter:.2f}").grid(
            row=10, column=0, columnspan=2, sticky=tk.W, padx=2
        )
        ttk.Label(self.props_frame, text=f"Площадь: {area:.2f}").grid(
            row=11, column=0, columnspan=2, sticky=tk.W, padx=2
        )
        ttk.Label(self.props_frame, text=f"Диагональ: {diagonal:.2f}").grid(
            row=12, column=0, columnspan=2, sticky=tk.W, padx=2
        )
    
    def _build_ellipse_props(self, shape: Any) -> None:
        """Свойства эллипса"""
        self._create_field("Центр X:", "cx", shape, 0)
        self._create_field("Центр Y:", "cy", shape, 1)
        self._create_field("Полуось X:", "rx", shape, 2, min_val=0.1)
        self._create_field("Полуось Y:", "ry", shape, 3, min_val=0.1)
        self._create_field("Поворот:", "rotation", shape, 4)
        
        ttk.Separator(self.props_frame, orient=tk.HORIZONTAL).grid(
            row=5, column=0, columnspan=2, sticky=tk.EW, pady=6
        )
        
        # Приближённый периметр
        h = ((shape.rx - shape.ry) / (shape.rx + shape.ry)) ** 2
        perimeter = math.pi * (shape.rx + shape.ry) * (1 + 3 * h / (10 + math.sqrt(4 - 3 * h)))
        area = math.pi * shape.rx * shape.ry
        
        ttk.Label(self.props_frame, text=f"Периметр: {perimeter:.2f}").grid(
            row=6, column=0, columnspan=2, sticky=tk.W, padx=2
        )
        ttk.Label(self.props_frame, text=f"Площадь: {area:.2f}").grid(
            row=7, column=0, columnspan=2, sticky=tk.W, padx=2
        )
    
    def _build_polygon_props(self, shape: Any) -> None:
        """Свойства многоугольника"""
        self._create_field("Центр X:", "cx", shape, 0)
        self._create_field("Центр Y:", "cy", shape, 1)
        self._create_field("Радиус:", "radius", shape, 2, min_val=0.1)
        self._create_int_field("Сторон:", "num_sides", shape, 3, min_val=3, max_val=100)
        self._create_field("Поворот:", "rotation", shape, 4)
        
        self._create_checkbox("Вписанный", "inscribed", shape, 5)
        
        ttk.Separator(self.props_frame, orient=tk.HORIZONTAL).grid(
            row=6, column=0, columnspan=2, sticky=tk.EW, pady=6
        )
        
        # Вычисляемые свойства
        if hasattr(shape, 'get_side_length'):
            side = shape.get_side_length()
            apothem = shape.get_apothem()
            perimeter = side * shape.num_sides
            area = 0.5 * perimeter * apothem
            
            ttk.Label(self.props_frame, text=f"Сторона: {side:.2f}").grid(
                row=7, column=0, columnspan=2, sticky=tk.W, padx=2
            )
            ttk.Label(self.props_frame, text=f"Апофема: {apothem:.2f}").grid(
                row=8, column=0, columnspan=2, sticky=tk.W, padx=2
            )
            ttk.Label(self.props_frame, text=f"Периметр: {perimeter:.2f}").grid(
                row=9, column=0, columnspan=2, sticky=tk.W, padx=2
            )
            ttk.Label(self.props_frame, text=f"Площадь: {area:.2f}").grid(
                row=10, column=0, columnspan=2, sticky=tk.W, padx=2
            )
            
    def _create_string_field(self, label: str, attr: str, shape: Any, row: int) -> None:
        """Создать текстовое поле ввода для атрибута"""
        ttk.Label(self.props_frame, text=label).grid(
            row=row, column=0, sticky=tk.W, padx=2, pady=2
        )
        
        var = tk.StringVar(value=getattr(shape, attr, ""))
        self._vars[attr] = var
        
        entry = ttk.Entry(self.props_frame, textvariable=var, width=12)
        entry.grid(row=row, column=1, sticky=tk.EW, padx=2, pady=2)
        self._widgets[attr] = entry
        
        def on_change(event=None):
            if self._updating:
                return
            setattr(shape, attr, var.get())
            self.app.redraw()
            if event and event.keysym == 'Return':
                self.app.canvas.focus_set()
                
        entry.bind('<Return>', on_change)
        entry.bind('<FocusOut>', on_change)
            
    def _build_dimension_props(self, shape: Any) -> None:
        """Свойства размера"""
        from shapes import DIMENSION_PREFIX_PRESETS
        from shapes.dimension import (
            RADIAL_DISPLAY_MODES, RADIAL_DISPLAY_MODE_NAMES,
            DIMENSION_FONT_TYPES, DIMENSION_FONT_TYPE_NAMES,
            ARROW_SHAPES, ARROW_SHAPE_NAMES
        )
        
        row = 0
        self._create_string_field("Переопределение:", "text_override", shape, row)
        row += 1
        
        ttk.Separator(self.props_frame, orient=tk.HORIZONTAL).grid(
            row=row, column=0, columnspan=2, sticky=tk.EW, pady=6
        )
        row += 1
        
        # Фактическое значение
        if type(shape).__name__ == "LinearDimension":
            val = shape.get_measurement_value() if hasattr(shape, 'get_measurement_value') else __import__('core').SegmentGeometry.calculate_length(shape.p1_x, shape.p1_y, shape.p2_x, shape.p2_y)
            ttk.Label(self.props_frame, text=f"Фактическое: {val:.2f}").grid(row=row, column=0, columnspan=2, sticky=tk.W, padx=2)
            row += 1
            if hasattr(shape, 'get_measurement_mode_name'):
                ttk.Label(self.props_frame, text=f"Тип: {shape.get_measurement_mode_name()}").grid(
                    row=row, column=0, columnspan=2, sticky=tk.W, padx=2
                )
                row += 1
            self._create_field("Отступ:", "offset", shape, row)
            row += 1
            self._create_field("Смещение текста:", "text_pos_x", shape, row)
            row += 1
            
        elif type(shape).__name__ == "RadialDimension":
            val = shape.radius * 2 if shape.is_diameter else shape.radius
            prefix = "⌀" if shape.is_diameter else "R"
            ttk.Label(self.props_frame, text=f"Фактическое: {prefix}{val:.2f}").grid(row=row, column=0, columnspan=2, sticky=tk.W, padx=2)
            row += 1
            ttk.Label(self.props_frame, text="Оформление:").grid(
                row=row, column=0, sticky=tk.W, padx=2, pady=2
            )
            available_mode_keys = RADIAL_DISPLAY_MODES if shape.is_diameter else ['leader', 'aligned']
            mode_labels = {
                RADIAL_DISPLAY_MODE_NAMES[key]: key for key in available_mode_keys
            }
            current_mode_key = shape.display_mode if shape.display_mode in available_mode_keys else 'leader'
            current_mode_label = RADIAL_DISPLAY_MODE_NAMES.get(current_mode_key, current_mode_key)
            mode_var = tk.StringVar(value=current_mode_label)
            self._vars['display_mode_label'] = mode_var
            mode_combo = ttk.Combobox(
                self.props_frame,
                textvariable=mode_var,
                values=list(mode_labels.keys()),
                state="readonly",
                width=18
            )
            mode_combo.grid(row=row, column=1, sticky=tk.EW, padx=2, pady=2)

            def on_mode_change(event=None):
                if self._updating:
                    return
                shape.display_mode = mode_labels[mode_var.get()]
                self.update_for_shape(shape)
                self.app.redraw()

            mode_combo.bind("<<ComboboxSelected>>", on_mode_change)
            row += 1
            if current_mode_key == 'leader':
                self._create_field("Вынос полки:", "shelf_offset", shape, row, min_val=0, max_val=300)
                row += 1
            elif current_mode_key == 'aligned':
                self._create_field("Вынос линии:", "line_extension", shape, row, min_val=10, max_val=300)
                row += 1
            elif current_mode_key == 'outside':
                self._create_field("Наружный отступ:", "outside_offset", shape, row, min_val=5, max_val=200)
                row += 1
            
        elif type(shape).__name__ == "AngularDimension":
            import math as _math
            angle1 = _math.atan2(shape.p1_y - shape.cy, shape.p1_x - shape.cx)
            angle2 = _math.atan2(shape.p2_y - shape.cy, shape.p2_x - shape.cx)
            diff = angle2 - angle1
            val_deg = _math.degrees(diff) if diff > 0 else _math.degrees(diff + 2 * _math.pi)
            if val_deg > 180: val_deg = 360 - val_deg
            ttk.Label(self.props_frame, text=f"Угол: {val_deg:.1f}°").grid(row=row, column=0, columnspan=2, sticky=tk.W, padx=2)
            row += 1
            self._create_field("Радиус дуги:", "radius", shape, row, min_val=0.1)
            row += 1
            ttk.Label(self.props_frame, text="Сторона:").grid(
                row=row, column=0, sticky=tk.W, padx=2, pady=2
            )
            angle_side_var = tk.StringVar(value="Больший" if shape.use_reflex else "Меньший")
            self._vars['angle_side'] = angle_side_var
            angle_side_combo = ttk.Combobox(
                self.props_frame,
                textvariable=angle_side_var,
                values=["Меньший", "Больший"],
                state="readonly",
                width=18
            )
            angle_side_combo.grid(row=row, column=1, sticky=tk.EW, padx=2, pady=2)

            def on_angle_side_change(event=None):
                if self._updating:
                    return
                shape.use_reflex = angle_side_var.get() == "Больший"
                self.app.redraw()

            angle_side_combo.bind("<<ComboboxSelected>>", on_angle_side_change)
            row += 1

        layer_name = getattr(shape, 'layer', '')
        if layer_name:
            ttk.Label(self.props_frame, text=f"Слой: {layer_name}").grid(
                row=row, column=0, columnspan=2, sticky=tk.W, padx=2
            )
            row += 1
        
        # --- Настройки оформления ---
        ttk.Separator(self.props_frame, orient=tk.HORIZONTAL).grid(
            row=row, column=0, columnspan=2, sticky=tk.EW, pady=6
        )
        row += 1
        
        ttk.Label(self.props_frame, text="Оформление", font=("Arial", 9, "bold")).grid(
            row=row, column=0, columnspan=2, sticky=tk.W, padx=2, pady=(2, 4)
        )
        row += 1
        
        # Размер шрифта
        self._create_int_field("Шрифт (пт):", "font_size", shape, row, min_val=6, max_val=72)
        row += 1

        ttk.Label(self.props_frame, text="Тип шрифта:").grid(
            row=row, column=0, sticky=tk.W, padx=2, pady=2
        )
        font_type_labels = [DIMENSION_FONT_TYPE_NAMES[key] for key in DIMENSION_FONT_TYPES]
        current_font_type = shape.font_type if shape.font_type in DIMENSION_FONT_TYPES else 'type_b_italic'
        font_type_var = tk.StringVar(value=DIMENSION_FONT_TYPE_NAMES[current_font_type])
        self._vars['font_type_label'] = font_type_var
        font_type_combo = ttk.Combobox(
            self.props_frame,
            textvariable=font_type_var,
            values=font_type_labels,
            state="readonly",
            width=18
        )
        font_type_combo.grid(row=row, column=1, sticky=tk.EW, padx=2, pady=2)

        def on_font_type_change(event=None):
            if self._updating:
                return
            label_to_type = {
                value: key for key, value in DIMENSION_FONT_TYPE_NAMES.items()
            }
            shape.font_type = label_to_type.get(font_type_var.get(), 'type_b_italic')
            self.app.redraw()

        font_type_combo.bind("<<ComboboxSelected>>", on_font_type_change)
        row += 1

        ttk.Label(self.props_frame, text="Префикс:").grid(
            row=row, column=0, sticky=tk.W, padx=2, pady=2
        )
        prefix_var = tk.StringVar(value=shape.text_prefix)
        self._vars['text_prefix'] = prefix_var
        prefix_combo = ttk.Combobox(
            self.props_frame,
            textvariable=prefix_var,
            values=DIMENSION_PREFIX_PRESETS,
            state="normal",
            width=18
        )
        prefix_combo.grid(row=row, column=1, sticky=tk.EW, padx=2, pady=2)

        def on_prefix_change(event=None):
            if self._updating:
                return
            shape.text_prefix = prefix_var.get().strip()
            self.app.redraw()
            if event and hasattr(event, 'keysym') and event.keysym == 'Return':
                self.app.canvas.focus_set()

        prefix_combo.bind("<<ComboboxSelected>>", on_prefix_change)
        prefix_combo.bind('<Return>', on_prefix_change)
        prefix_combo.bind('<FocusOut>', on_prefix_change)
        row += 1
        
        # Форма стрелки
        ttk.Label(self.props_frame, text="Стрелка:").grid(row=row, column=0, sticky=tk.W, padx=2, pady=2)
        arrow_shape_var = tk.StringVar(
            value=ARROW_SHAPE_NAMES.get(getattr(shape, 'arrow_shape', 'triangle'), ARROW_SHAPE_NAMES['triangle'])
        )
        self._vars['arrow_shape_label'] = arrow_shape_var
        arrow_combo = ttk.Combobox(
            self.props_frame, textvariable=arrow_shape_var,
            values=[ARROW_SHAPE_NAMES[key] for key in ARROW_SHAPES], state="readonly", width=18
        )
        arrow_combo.grid(row=row, column=1, sticky=tk.EW, padx=2, pady=2)

        arrow_fill_var = tk.BooleanVar(value=getattr(shape, 'arrow_filled', True))
        self._vars['arrow_filled'] = arrow_fill_var

        def update_arrow_fill_state() -> None:
            current_shape = getattr(shape, 'arrow_shape', 'triangle')
            arrow_fill_check.configure(
                state="normal" if current_shape in ('triangle', 'square', 'circle') else "disabled"
            )

        def on_arrow_change(event=None):
            if self._updating:
                return
            label_to_shape = {
                value: key for key, value in ARROW_SHAPE_NAMES.items()
            }
            shape.arrow_shape = label_to_shape.get(arrow_shape_var.get(), 'triangle')
            if shape.arrow_shape not in ('triangle', 'square', 'circle'):
                shape.arrow_filled = False
                arrow_fill_var.set(False)
            shape._sync_legacy_arrow_type()
            update_arrow_fill_state()
            self.app.redraw()
        arrow_combo.bind("<<ComboboxSelected>>", on_arrow_change)
        row += 1

        arrow_fill_check = ttk.Checkbutton(
            self.props_frame,
            text="Заполненная",
            variable=arrow_fill_var
        )
        arrow_fill_check.grid(row=row, column=0, columnspan=2, sticky=tk.W, padx=2, pady=2)

        def on_arrow_fill_change():
            if self._updating:
                return
            shape.arrow_filled = arrow_fill_var.get()
            shape._sync_legacy_arrow_type()
            self.app.redraw()

        arrow_fill_check.config(command=on_arrow_fill_change)
        update_arrow_fill_state()
        row += 1

        # Размер стрелки
        self._create_field("Размер стрелок:", "arrow_size", shape, row, min_val=3, max_val=50)
        row += 1
        
    def _build_spline_props(self, shape: Any) -> None:
        """Свойства сплайна"""
        self._create_field("Натяжение:", "tension", shape, 0, min_val=0, max_val=1)
        
        ttk.Separator(self.props_frame, orient=tk.HORIZONTAL).grid(
            row=1, column=0, columnspan=2, sticky=tk.EW, pady=6
        )
        
        num_points = len(shape.points) if hasattr(shape, 'points') else 0
        length = shape.get_length() if hasattr(shape, 'get_length') else 0
        
        ttk.Label(self.props_frame, text=f"Точек: {num_points}").grid(
            row=2, column=0, columnspan=2, sticky=tk.W, padx=2
        )
        ttk.Label(self.props_frame, text=f"Длина: {length:.2f}").grid(
            row=3, column=0, columnspan=2, sticky=tk.W, padx=2
        )
        
        # Кнопки управления точками
        ttk.Separator(self.props_frame, orient=tk.HORIZONTAL).grid(
            row=4, column=0, columnspan=2, sticky=tk.EW, pady=6
        )
        
        ttk.Label(self.props_frame, text="Контрольные точки:").grid(
            row=5, column=0, columnspan=2, sticky=tk.W, padx=2
        )
        
        # Список точек (ограничиваем до 10 для UI)
        if hasattr(shape, 'points'):
            for i, (px, py) in enumerate(shape.points[:10]):
                text = f"  {i+1}: ({px:.1f}, {py:.1f})"
                ttk.Label(self.props_frame, text=text, font=("Consolas", 9)).grid(
                    row=6 + i, column=0, columnspan=2, sticky=tk.W, padx=2
                )
            
            if len(shape.points) > 10:
                ttk.Label(self.props_frame, text=f"  ... и ещё {len(shape.points) - 10}").grid(
                    row=16, column=0, columnspan=2, sticky=tk.W, padx=2
                )
    
    def _build_common_props(self, shape: Any) -> None:
        """Общие свойства (стиль линии)"""
        # Находим последнюю строку
        rows = self.props_frame.grid_size()[1]
        
        ttk.Separator(self.props_frame, orient=tk.HORIZONTAL).grid(
            row=rows, column=0, columnspan=2, sticky=tk.EW, pady=6
        )
        
        ttk.Label(self.props_frame, text="Стиль линии:").grid(
            row=rows + 1, column=0, sticky=tk.W, padx=2, pady=2
        )
        
        style_var = tk.StringVar(value=shape.line_style_name)
        self._vars['line_style_name'] = style_var
        
        style_combo = ttk.Combobox(
            self.props_frame, 
            textvariable=style_var,
            values=self.app.style_manager.get_general_style_names(),
            state="readonly",
            width=18
        )
        style_combo.grid(row=rows + 1, column=1, sticky=tk.EW, padx=2, pady=2)
        self._widgets['line_style_name'] = style_combo
        
        def on_style_change(event=None):
            if self._updating:
                return
            shape.line_style_name = style_var.get()
            self.app.redraw()
        
        style_combo.bind("<<ComboboxSelected>>", on_style_change)
        
        # Настраиваем расширение колонки
        self.props_frame.columnconfigure(1, weight=1)

    def _build_dimension_style_props(self, shape: Any) -> None:
        """Показать отдельный стиль размеров без ручного выбора стиля для объекта."""
        rows = self.props_frame.grid_size()[1]

        ttk.Separator(self.props_frame, orient=tk.HORIZONTAL).grid(
            row=rows, column=0, columnspan=2, sticky=tk.EW, pady=6
        )
        ttk.Label(self.props_frame, text="Стиль размера:").grid(
            row=rows + 1, column=0, sticky=tk.W, padx=2, pady=2
        )
        ttk.Label(self.props_frame, text=shape.line_style_name).grid(
            row=rows + 1, column=1, sticky=tk.W, padx=2, pady=2
        )
        ttk.Button(
            self.props_frame,
            text="Редактировать стиль",
            command=self.app._open_style_manager
        ).grid(row=rows + 2, column=0, columnspan=2, sticky=tk.EW, padx=2, pady=(4, 2))

        self.props_frame.columnconfigure(1, weight=1)
    
    def refresh(self) -> None:
        """Обновить значения полей"""
        if self.current_shape is None:
            return

        from shapes.dimension import DIMENSION_FONT_TYPE_NAMES, ARROW_SHAPE_NAMES
        
        self._updating = True
        
        try:
            for attr, var in self._vars.items():
                if attr == 'font_type_label':
                    font_type = getattr(self.current_shape, 'font_type', 'type_b_italic')
                    var.set(DIMENSION_FONT_TYPE_NAMES.get(font_type, DIMENSION_FONT_TYPE_NAMES['type_b_italic']))
                    continue
                if attr == 'arrow_shape_label':
                    arrow_shape = getattr(self.current_shape, 'arrow_shape', 'triangle')
                    var.set(ARROW_SHAPE_NAMES.get(arrow_shape, ARROW_SHAPE_NAMES['triangle']))
                    continue
                if hasattr(self.current_shape, attr):
                    value = getattr(self.current_shape, attr)
                    if isinstance(var, tk.DoubleVar):
                        var.set(float(value))
                    elif isinstance(var, tk.IntVar):
                        var.set(int(value))
                    elif isinstance(var, tk.BooleanVar):
                        var.set(bool(value))
                    elif isinstance(var, tk.StringVar):
                        var.set(str(value))
        finally:
            self._updating = False
