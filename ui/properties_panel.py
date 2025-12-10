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
            
            # Общие свойства (стиль линии)
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
            values=self.app.style_manager.get_style_names(),
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
    
    def refresh(self) -> None:
        """Обновить значения полей"""
        if self.current_shape is None:
            return
        
        self._updating = True
        
        try:
            for attr, var in self._vars.items():
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

