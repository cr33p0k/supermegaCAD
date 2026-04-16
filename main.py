import tkinter as tk
from tkinter import ttk, messagebox

from core import CoordinateConverter, CanvasRenderer, UIBuilder
from managers import ShapeManager, SnapManager, SnapType, GridManager
from managers.line_style_manager import LineStyleManager
from tools import DrawTool, SelectTool, PanTool, NavigationHandler, DimensionTool, PrimitiveType, CreationMode, PRIMITIVE_NAMES, PRIMITIVE_MODES
from shapes import Segment, Circle, Arc, Rectangle, Ellipse, Polygon, Spline, Dimension
from shapes.dimension import (
    RADIAL_DISPLAY_MODES, RADIAL_DISPLAY_MODE_NAMES,
    LINEAR_DIMENSION_MODE_NAMES, ARROW_SHAPES, ARROW_SHAPE_NAMES, DIMENSION_PREFIX_PRESETS,
    DIMENSION_FONT_TYPES, DIMENSION_FONT_TYPE_NAMES
)
from view_transform import ViewTransform
from dialogs import StyleManagerDialog, ThemeDialog
from ui import RibbonBuilder, PropertiesPanel
from exporters.dxf_exporter import DxfExporter
from importers.dxf_importer import DxfImporter


class GeometryApp(tk.Tk):
    """Главное приложение для работы с геометрическими фигурами - supermegaCAD"""
    
    POINT_RADIUS = 4

    def __init__(self) -> None:
        super().__init__()
        self.title("supermegaCAD")
        self.geometry("1500x950")
        self.minsize(1300, 850)

        # Настройка стилей
        self._setup_styles()

        # Менеджеры
        self.shape_manager = ShapeManager()
        self.view_transform = ViewTransform()
        self.style_manager = LineStyleManager()
        self.grid_manager = GridManager(base_step=25.0)
        self.snap_manager = SnapManager()
        self.snap_manager.set_grid_manager(self.grid_manager)  # Связываем с GridManager
        
        # Инструменты
        self.navigation_handler = NavigationHandler(self)
        self.draw_tool = DrawTool(self)
        self.select_tool = SelectTool(self)
        self.pan_tool = PanTool(self)
        self.dimension_tool = DimensionTool(self)
        
        self.current_tool = self.draw_tool
        self.tool_var = tk.StringVar(value="draw")
        
        self.tools = {
            "draw": (self.draw_tool, "Рисование"),
            "select": (self.select_tool, "Выделение"),
            "pan": (self.pan_tool, "Панорамирование"),
            "dimension": (self.dimension_tool, "Размеры")
        }
        
        # Переменные настроек
        self.grid_step_var = tk.DoubleVar(value=25.0)
        self.current_style_var = tk.StringVar(value=self.style_manager.get_current_style_name())
        self.primitive_type_var = tk.StringVar(value="segment")
        self.creation_mode_var = tk.StringVar(value="default")
        self.dimension_mode_var = tk.StringVar(value="linear")
        self.dimension_linear_mode_var = tk.StringVar(
            value=LINEAR_DIMENSION_MODE_NAMES['aligned']
        )
        self.dimension_display_mode_var = tk.StringVar(
            value=RADIAL_DISPLAY_MODE_NAMES['leader']
        )
        self.dimension_shelf_offset_var = tk.DoubleVar(value=15.0)
        self.dimension_font_size_var = tk.IntVar(value=12)
        self.dimension_font_type_var = tk.StringVar(
            value=DIMENSION_FONT_TYPE_NAMES['type_b_italic']
        )
        self.dimension_arrow_shape_var = tk.StringVar(value=ARROW_SHAPE_NAMES['triangle'])
        self.dimension_arrow_filled_var = tk.BooleanVar(value=True)
        self.dimension_arrow_size_var = tk.DoubleVar(value=15.0)
        self.dimension_text_prefix_var = tk.StringVar(value="")
        
        # Параметры примитивов
        self.polygon_sides_var = tk.IntVar(value=6)
        self.polygon_inscribed_var = tk.BooleanVar(value=True)
        self.rect_corner_radius_var = tk.DoubleVar(value=0)
        self.rect_chamfer_var = tk.DoubleVar(value=0)
        
        # Переменные привязок
        self.snap_enabled_var = tk.BooleanVar(value=self.snap_manager.is_enabled())
        self.snap_type_vars = {}
        self._init_snap_vars()
        
        # Координаты курсора
        self.cursor_world_x = self.cursor_world_y = 0.0
        
        # Для отслеживания изменений выделения
        self._last_selected_shape = None

        self._build_ui()
        self._bind_events()
        # Шаг сетки теперь управляется через GridManager
        self.grid_manager.base_step = self.grid_step_var.get()
        
        self.redraw()
        self.update_status_bar()
    
    def _setup_styles(self) -> None:
        """Настройка стилей ttk"""
        style = ttk.Style()
        
        # Стиль для активной кнопки примитива
        style.configure("Active.TButton", background="#4a9eff")
        
        # Стиль для заголовков секций
        style.configure("Header.TLabel", font=("Segoe UI", 9, "bold"))
    
    def _init_snap_vars(self) -> None:
        """Инициализация переменных привязок"""
        for snap_type in SnapType:
            var = tk.BooleanVar(value=self.snap_manager.is_snap_type_enabled(snap_type))
            self.snap_type_vars[snap_type] = var

    def _build_ui(self) -> None:
        """Построение интерфейса"""
        self._create_menu()
        self._create_toolbar()
        
        # Основной контейнер
        main_container = ttk.Frame(self)
        main_container.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # Левая панель - инструменты и примитивы
        left_panel = self._create_left_panel(main_container)
        left_panel.pack(side=tk.LEFT, fill=tk.Y)

        # Canvas
        canvas_container = ttk.Frame(main_container)
        canvas_container.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.canvas = tk.Canvas(canvas_container, background="#0a0a0a", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.renderer = CanvasRenderer(self.canvas)
        self.renderer.app = self
        self.renderer.style_manager = self.style_manager
        self.renderer.color_bg = "#0a0a0a"
        self.renderer.color_grid = "#1a1a1a"

        # Правая панель - свойства и привязки
        right_panel = self._create_right_panel(main_container)
        right_panel.pack(side=tk.RIGHT, fill=tk.Y)
        
        self._create_status_bar()
    
    def _create_left_panel(self, parent) -> ttk.Frame:
        """Создание левой панели с инструментами"""
        panel = ttk.Frame(parent, width=200)
        panel.pack_propagate(False)
        
        # === Инструменты ===
        self.tools_frame = ttk.LabelFrame(panel, text="  Инструменты  ", padding=8)
        self.tools_frame.pack(fill=tk.X, padx=6, pady=6)
        
        tools_data = [
            ("🖊 Рисование", "draw", "D"),
            ("👆 Выделение", "select", "S"),
            ("✋ Панорама", "pan", "H"),
            ("📐 Размеры", "dimension", "M"),
        ]
        
        for text, value, hotkey in tools_data:
            frame = ttk.Frame(self.tools_frame)
            frame.pack(fill=tk.X, pady=2)
            ttk.Radiobutton(frame, text=text, variable=self.tool_var,
                           value=value, command=lambda v=value: self.set_tool(v),
                           width=14).pack(side=tk.LEFT)
            ttk.Label(frame, text=hotkey, foreground="#888888", 
                     font=("Consolas", 9)).pack(side=tk.RIGHT, padx=4)
        
        # === Примитивы ===
        self.prims_frame = ttk.LabelFrame(panel, text="  Примитивы  ", padding=8)
        self.prims_frame.pack(fill=tk.X, padx=6, pady=6)
        
        primitives = [
            ("╱ Отрезок", PrimitiveType.SEGMENT),
            ("○ Окружность", PrimitiveType.CIRCLE),
            ("◠ Дуга", PrimitiveType.ARC),
            ("• Точка", PrimitiveType.POINT),
            ("▭ Прямоугольник", PrimitiveType.RECTANGLE),
            ("⬭ Эллипс", PrimitiveType.ELLIPSE),
            ("⬡ Многоугольник", PrimitiveType.POLYGON),
            ("〰 Сплайн", PrimitiveType.SPLINE),
        ]
        
        self.primitive_buttons = {}
        for text, ptype in primitives:
            btn = ttk.Button(self.prims_frame, text=text, width=18,
                            command=lambda pt=ptype: self._set_primitive_type(pt))
            btn.pack(fill=tk.X, pady=2)
            self.primitive_buttons[ptype] = btn
        
        # === Режим создания ===
        self.modes_frame = ttk.LabelFrame(panel, text="  Режим создания  ", padding=8)
        self.modes_frame.pack(fill=tk.X, padx=6, pady=6)
        
        self.modes_container = ttk.Frame(self.modes_frame)
        self.modes_container.pack(fill=tk.X)
        
        # === Типы размеров ===
        self.dim_modes_frame = ttk.LabelFrame(panel, text="  Режим размеров  ", padding=8)
        # Упаковываем динамически
        
        self._update_creation_modes()
        
        # === Параметры примитива ===
        self.params_frame = ttk.LabelFrame(panel, text="  Параметры  ", padding=8)
        self.params_frame.pack(fill=tk.X, padx=6, pady=6)
        
        self._build_primitive_params()
        
        # === Быстрые действия ===
        actions_frame = ttk.LabelFrame(panel, text="  Действия  ", padding=8)
        actions_frame.pack(fill=tk.X, padx=6, pady=6, side=tk.BOTTOM)
        
        ttk.Button(actions_frame, text="🔍 Показать всё", 
                  command=self.fit_all_to_view).pack(fill=tk.X, pady=2)
        ttk.Button(actions_frame, text="🔄 Сбросить вид", 
                  command=self.reset_view).pack(fill=tk.X, pady=2)
        ttk.Button(actions_frame, text="🗑 Очистить всё", 
                  command=self._on_clear_all).pack(fill=tk.X, pady=2)
        
        return panel
    
    def _create_right_panel(self, parent) -> ttk.Frame:
        """Создание правой панели со свойствами и привязками"""
        panel = ttk.Frame(parent, width=280)
        panel.pack_propagate(False)
        
        # === Привязки (в одном месте!) ===
        snap_frame = ttk.LabelFrame(panel, text="  Объектные привязки  ", padding=8)
        snap_frame.pack(fill=tk.X, padx=6, pady=6)
        
        # Главный переключатель
        main_snap = ttk.Frame(snap_frame)
        main_snap.pack(fill=tk.X, pady=(0, 8))
        
        ttk.Checkbutton(main_snap, text="Включить привязки",
                        variable=self.snap_enabled_var,
                        command=self._toggle_snap).pack(side=tk.LEFT)
        
        # Типы привязок в два столбца
        snap_grid = ttk.Frame(snap_frame)
        snap_grid.pack(fill=tk.X)
        snap_grid.columnconfigure(0, weight=1)
        snap_grid.columnconfigure(1, weight=1)
        
        snap_types = [
            (SnapType.ENDPOINT, "⬜ Конец"),
            (SnapType.MIDPOINT, "△ Середина"),
            (SnapType.CENTER, "○ Центр"),
            (SnapType.QUADRANT, "◇ Квадрант"),
            (SnapType.INTERSECTION, "✕ Пересеч."),
            (SnapType.PERPENDICULAR, "⊥ Перпенд."),
            (SnapType.TANGENT, "◎ Касат."),
            (SnapType.GRID, "# Сетка"),
        ]
        
        for i, (snap_type, label) in enumerate(snap_types):
            row, col = i // 2, i % 2
            ttk.Checkbutton(snap_grid, text=label,
                           variable=self.snap_type_vars[snap_type],
                           command=lambda st=snap_type: self._toggle_snap_type(st)
                           ).grid(row=row, column=col, sticky=tk.W, padx=2, pady=1)
        
        # === Свойства объекта ===
        props_frame = ttk.LabelFrame(panel, text="  Свойства объекта  ", padding=8)
        props_frame.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        
        self.properties_panel = PropertiesPanel(props_frame, self)
        
        # === Стиль линии ===
        style_frame = ttk.LabelFrame(panel, text="  Стиль линии  ", padding=8)
        style_frame.pack(fill=tk.X, padx=6, pady=6)
        
        self.style_combo = ttk.Combobox(style_frame, textvariable=self.current_style_var,
                                        values=self.style_manager.get_general_style_names(),
                                        state="readonly")
        self.style_combo.bind("<<ComboboxSelected>>", self._on_current_style_changed)
        self.style_combo.pack(fill=tk.X, pady=(0, 4))
        
        ttk.Button(style_frame, text="⚙ Управление стилями",
                  command=self._open_style_manager).pack(fill=tk.X)
        
        # === Информация ===
        info_frame = ttk.LabelFrame(panel, text="  Информация  ", padding=8)
        info_frame.pack(fill=tk.X, padx=6, pady=6, side=tk.BOTTOM)
        
        self.info_text = tk.Text(info_frame, height=4, wrap=tk.WORD,
                                 background="#2a2a3e", foreground="#cccccc",
                                 font=("Consolas", 9), relief=tk.FLAT,
                                 padx=6, pady=4)
        self.info_text.pack(fill=tk.X)
        self.info_text.configure(state=tk.DISABLED)
        
        return panel
    
    def _build_primitive_params(self) -> None:
        """Построение параметров примитивов"""
        # Многоугольник
        self.polygon_params = ttk.Frame(self.params_frame)
        
        row1 = ttk.Frame(self.polygon_params)
        row1.pack(fill=tk.X, pady=2)
        ttk.Label(row1, text="Стороны:").pack(side=tk.LEFT)
        sides_spin = ttk.Spinbox(row1, from_=3, to=100,
                                textvariable=self.polygon_sides_var, width=6,
                                command=self._on_polygon_sides_changed)
        sides_spin.pack(side=tk.RIGHT)
        sides_spin.bind('<Return>', lambda e: self._on_polygon_sides_changed())
        
        ttk.Checkbutton(self.polygon_params, text="Вписанный",
                       variable=self.polygon_inscribed_var,
                       command=self._on_polygon_inscribed_changed).pack(anchor=tk.W, pady=2)
        
        # Прямоугольник
        self.rect_params = ttk.Frame(self.params_frame)
        
        row1 = ttk.Frame(self.rect_params)
        row1.pack(fill=tk.X, pady=2)
        ttk.Label(row1, text="Скругление:").pack(side=tk.LEFT)
        corner_spin = ttk.Spinbox(row1, from_=0, to=1000,
                   textvariable=self.rect_corner_radius_var, width=6,
                   command=self._on_rect_corner_changed)
        corner_spin.pack(side=tk.RIGHT)
        corner_spin.bind('<Return>', lambda e: self._on_rect_corner_changed())
        corner_spin.bind('<FocusOut>', lambda e: self._on_rect_corner_changed())
        
        row2 = ttk.Frame(self.rect_params)
        row2.pack(fill=tk.X, pady=2)
        ttk.Label(row2, text="Фаска:").pack(side=tk.LEFT)
        chamfer_spin = ttk.Spinbox(row2, from_=0, to=1000,
                   textvariable=self.rect_chamfer_var, width=6,
                   command=self._on_rect_chamfer_changed)
        chamfer_spin.pack(side=tk.RIGHT)
        chamfer_spin.bind('<Return>', lambda e: self._on_rect_chamfer_changed())
        chamfer_spin.bind('<FocusOut>', lambda e: self._on_rect_chamfer_changed())
        
        # Пустая заглушка
        self.empty_params = ttk.Label(self.params_frame, 
                                      text="Нет параметров",
                                      foreground="#888888")

        self.dimension_params = ttk.Frame(self.params_frame)

        dim_linear_row = ttk.Frame(self.dimension_params)
        dim_linear_row.pack(fill=tk.X, pady=2)
        self.dimension_linear_label = ttk.Label(dim_linear_row, text="Линейный:")
        self.dimension_linear_label.pack(side=tk.LEFT)
        self.dimension_linear_mode_combo = ttk.Combobox(
            dim_linear_row,
            textvariable=self.dimension_linear_mode_var,
            values=list(LINEAR_DIMENSION_MODE_NAMES.values()),
            state="readonly",
            width=18
        )
        self.dimension_linear_mode_combo.pack(side=tk.RIGHT)
        self.dimension_linear_mode_combo.bind(
            "<<ComboboxSelected>>",
            self._on_dimension_linear_mode_changed
        )

        dim_mode_row = ttk.Frame(self.dimension_params)
        dim_mode_row.pack(fill=tk.X, pady=2)
        self.dimension_display_label = ttk.Label(dim_mode_row, text="Оформление:")
        self.dimension_display_label.pack(side=tk.LEFT)
        self.dimension_display_mode_combo = ttk.Combobox(
            dim_mode_row,
            textvariable=self.dimension_display_mode_var,
            state="readonly",
            width=18
        )
        self.dimension_display_mode_combo.pack(side=tk.RIGHT)
        self.dimension_display_mode_combo.bind(
            "<<ComboboxSelected>>",
            self._on_dimension_display_mode_changed
        )

        dim_shelf_row = ttk.Frame(self.dimension_params)
        dim_shelf_row.pack(fill=tk.X, pady=2)
        self.dimension_shelf_label = ttk.Label(dim_shelf_row, text="Вынос полки:")
        self.dimension_shelf_label.pack(side=tk.LEFT)
        self.dimension_shelf_spin = ttk.Spinbox(
            dim_shelf_row,
            from_=0,
            to=300,
            increment=5,
            textvariable=self.dimension_shelf_offset_var,
            width=8,
            command=self._on_dimension_shelf_offset_changed
        )
        self.dimension_shelf_spin.pack(side=tk.RIGHT)
        self.dimension_shelf_spin.bind(
            '<Return>', lambda e: self._on_dimension_shelf_offset_changed()
        )
        self.dimension_shelf_spin.bind(
            '<FocusOut>', lambda e: self._on_dimension_shelf_offset_changed()
        )

        dim_font_row = ttk.Frame(self.dimension_params)
        dim_font_row.pack(fill=tk.X, pady=2)
        ttk.Label(dim_font_row, text="Шрифт (пт):").pack(side=tk.LEFT)
        self.dimension_font_spin = ttk.Spinbox(
            dim_font_row,
            from_=6,
            to=72,
            increment=1,
            textvariable=self.dimension_font_size_var,
            width=8,
            command=self._on_dimension_font_size_changed
        )
        self.dimension_font_spin.pack(side=tk.RIGHT)
        self.dimension_font_spin.bind(
            '<Return>', lambda e: self._on_dimension_font_size_changed()
        )
        self.dimension_font_spin.bind(
            '<FocusOut>', lambda e: self._on_dimension_font_size_changed()
        )

        dim_font_type_row = ttk.Frame(self.dimension_params)
        dim_font_type_row.pack(fill=tk.X, pady=2)
        ttk.Label(dim_font_type_row, text="Тип шрифта:").pack(side=tk.LEFT)
        self.dimension_font_type_combo = ttk.Combobox(
            dim_font_type_row,
            textvariable=self.dimension_font_type_var,
            values=[DIMENSION_FONT_TYPE_NAMES[key] for key in DIMENSION_FONT_TYPES],
            state="readonly",
            width=18
        )
        self.dimension_font_type_combo.pack(side=tk.RIGHT)
        self.dimension_font_type_combo.bind(
            "<<ComboboxSelected>>",
            self._on_dimension_font_type_changed
        )

        dim_arrow_row = ttk.Frame(self.dimension_params)
        dim_arrow_row.pack(fill=tk.X, pady=2)
        ttk.Label(dim_arrow_row, text="Стрелка:").pack(side=tk.LEFT)
        self.dimension_arrow_shape_combo = ttk.Combobox(
            dim_arrow_row,
            textvariable=self.dimension_arrow_shape_var,
            values=[ARROW_SHAPE_NAMES[key] for key in ARROW_SHAPES],
            state="readonly",
            width=18
        )
        self.dimension_arrow_shape_combo.pack(side=tk.RIGHT)
        self.dimension_arrow_shape_combo.bind(
            "<<ComboboxSelected>>",
            self._on_dimension_arrow_shape_changed
        )

        dim_arrow_fill_row = ttk.Frame(self.dimension_params)
        dim_arrow_fill_row.pack(fill=tk.X, pady=2)
        self.dimension_arrow_fill_check = ttk.Checkbutton(
            dim_arrow_fill_row,
            text="Заполненная",
            variable=self.dimension_arrow_filled_var,
            command=self._on_dimension_arrow_filled_changed
        )
        self.dimension_arrow_fill_check.pack(side=tk.LEFT)

        dim_arrow_size_row = ttk.Frame(self.dimension_params)
        dim_arrow_size_row.pack(fill=tk.X, pady=2)
        ttk.Label(dim_arrow_size_row, text="Размер стрелок:").pack(side=tk.LEFT)
        self.dimension_arrow_size_spin = ttk.Spinbox(
            dim_arrow_size_row,
            from_=3,
            to=50,
            increment=1,
            textvariable=self.dimension_arrow_size_var,
            width=8,
            command=self._on_dimension_arrow_size_changed
        )
        self.dimension_arrow_size_spin.pack(side=tk.RIGHT)
        self.dimension_arrow_size_spin.bind(
            '<Return>', lambda e: self._on_dimension_arrow_size_changed()
        )
        self.dimension_arrow_size_spin.bind(
            '<FocusOut>', lambda e: self._on_dimension_arrow_size_changed()
        )

        dim_prefix_row = ttk.Frame(self.dimension_params)
        dim_prefix_row.pack(fill=tk.X, pady=2)
        ttk.Label(dim_prefix_row, text="Префикс:").pack(side=tk.LEFT)
        self.dimension_prefix_combo = ttk.Combobox(
            dim_prefix_row,
            textvariable=self.dimension_text_prefix_var,
            values=DIMENSION_PREFIX_PRESETS,
            state="normal",
            width=18
        )
        self.dimension_prefix_combo.pack(side=tk.RIGHT)
        self.dimension_prefix_combo.bind(
            "<<ComboboxSelected>>",
            self._on_dimension_text_prefix_changed
        )
        self.dimension_prefix_combo.bind(
            '<Return>', lambda e: self._on_dimension_text_prefix_changed()
        )
        self.dimension_prefix_combo.bind(
            '<FocusOut>', lambda e: self._on_dimension_text_prefix_changed()
        )

        ttk.Button(
            self.dimension_params,
            text="⚙ Стиль размеров",
            command=self._open_style_manager
        ).pack(fill=tk.X, pady=(6, 2))

        self.dimension_params_hint = ttk.Label(
            self.dimension_params,
            text="Параметры применяются сразу\nк новому размеру",
            foreground="#888888",
            justify=tk.LEFT
        )
        self.dimension_params_hint.pack(anchor=tk.W, pady=(6, 0))
        
        self._update_params_visibility()
        # Инициализация параметров в DrawTool
        self._on_polygon_sides_changed()
        self._on_polygon_inscribed_changed()
        self._on_rect_corner_changed()
        self._on_rect_chamfer_changed()
        self.sync_dimension_ui_from_tool()
    
    def _update_params_visibility(self) -> None:
        """Обновить видимость параметров"""
        self.polygon_params.pack_forget()
        self.rect_params.pack_forget()
        self.dimension_params.pack_forget()
        self.empty_params.pack_forget()
        
        self.empty_params.pack_forget()
        
        ptype = self.draw_tool.primitive_type
        
        if self.tool_var.get() == "dimension":
            self.dimension_params.pack(fill=tk.X)
            self.sync_dimension_ui_from_tool()
        elif ptype == PrimitiveType.POLYGON:
            self.polygon_params.pack(fill=tk.X)
        elif ptype == PrimitiveType.RECTANGLE:
            self.rect_params.pack(fill=tk.X)
        else:
            self.empty_params.pack(anchor=tk.W)

    def _set_dimension_mode(self, mode: str) -> None:
        """Установить режим размеров и обновить параметры."""
        self.dimension_mode_var.set(mode)
        self.dimension_tool.set_mode(mode)
        self._update_params_visibility()
        if hasattr(self, "canvas"):
            self.canvas.focus_set()

    def _on_dimension_linear_mode_changed(self, event=None) -> None:
        """Изменение режима линейного размера."""
        label = self.dimension_linear_mode_var.get()
        label_to_mode = {
            value: key for key, value in LINEAR_DIMENSION_MODE_NAMES.items()
        }
        mode = label_to_mode.get(label)
        if mode:
            self.dimension_tool.set_linear_mode(mode)
            self.sync_dimension_ui_from_tool()
        if hasattr(self, "canvas"):
            self.canvas.focus_set()

    def _get_available_dimension_display_modes(self) -> list[str]:
        """Доступные варианты оформления для текущего типа радиального размера."""
        if self.dimension_mode_var.get() == "diameter":
            return RADIAL_DISPLAY_MODES
        return ['leader', 'aligned']

    def _on_dimension_display_mode_changed(self, event=None) -> None:
        """Изменение оформления радиального размера."""
        label = self.dimension_display_mode_var.get()
        label_to_mode = {
            RADIAL_DISPLAY_MODE_NAMES[key]: key
            for key in self._get_available_dimension_display_modes()
        }
        mode = label_to_mode.get(label)
        if mode:
            self.dimension_tool.set_radial_display_mode(mode)
            self.sync_dimension_ui_from_tool()
        if hasattr(self, "canvas"):
            self.canvas.focus_set()

    def _on_dimension_shelf_offset_changed(self) -> None:
        """Изменение выноса радиального размера для текущего режима."""
        try:
            value = float(self.dimension_shelf_offset_var.get())
        except (ValueError, tk.TclError):
            return
        current_mode = self.dimension_tool.default_radial_display_mode
        if current_mode == 'leader':
            self.dimension_tool.set_radial_shelf_offset(value)
        elif current_mode == 'aligned':
            self.dimension_tool.set_radial_line_extension(value)
        elif current_mode == 'outside':
            self.dimension_tool.set_radial_outside_offset(value)
        if hasattr(self, "canvas"):
            self.canvas.focus_set()

    def _on_dimension_font_size_changed(self) -> None:
        """Изменение размера шрифта размеров."""
        try:
            value = int(self.dimension_font_size_var.get())
        except (ValueError, tk.TclError):
            return
        self.dimension_tool.set_font_size(value)
        if hasattr(self, "canvas"):
            self.canvas.focus_set()

    def _on_dimension_font_type_changed(self, event=None) -> None:
        """Изменение типа шрифта размеров."""
        label = self.dimension_font_type_var.get()
        label_to_type = {
            value: key for key, value in DIMENSION_FONT_TYPE_NAMES.items()
        }
        font_type = label_to_type.get(label)
        if font_type:
            self.dimension_tool.set_font_type(font_type)
            self.sync_dimension_ui_from_tool()
        if hasattr(self, "canvas"):
            self.canvas.focus_set()

    def _is_fillable_arrow_shape(self, arrow_shape: str) -> bool:
        """Проверить, поддерживает ли форма заполнение."""
        return arrow_shape in ('triangle', 'square', 'circle')

    def _update_dimension_arrow_fill_state(self) -> None:
        """Обновить доступность галочки заполнения."""
        if not hasattr(self, 'dimension_arrow_fill_check'):
            return
        arrow_shape = self.dimension_tool.default_arrow_shape
        state = "normal" if self._is_fillable_arrow_shape(arrow_shape) else "disabled"
        self.dimension_arrow_fill_check.configure(state=state)

    def _on_dimension_arrow_shape_changed(self, event=None) -> None:
        """Изменение формы стрелки размеров."""
        label = self.dimension_arrow_shape_var.get()
        label_to_shape = {
            value: key for key, value in ARROW_SHAPE_NAMES.items()
        }
        arrow_shape = label_to_shape.get(label)
        if arrow_shape:
            self.dimension_tool.set_arrow_shape(arrow_shape)
            self.sync_dimension_ui_from_tool()
        if hasattr(self, "canvas"):
            self.canvas.focus_set()

    def _on_dimension_arrow_filled_changed(self) -> None:
        """Изменение заполнения стрелок."""
        self.dimension_tool.set_arrow_filled(self.dimension_arrow_filled_var.get())
        if hasattr(self, "canvas"):
            self.canvas.focus_set()

    def _on_dimension_arrow_size_changed(self) -> None:
        """Изменение размера стрелок."""
        try:
            value = float(self.dimension_arrow_size_var.get())
        except (ValueError, tk.TclError):
            return
        self.dimension_tool.set_arrow_size(value)
        if hasattr(self, "canvas"):
            self.canvas.focus_set()

    def _on_dimension_text_prefix_changed(self, event=None) -> None:
        """Изменение префикса размера."""
        self.dimension_tool.set_text_prefix(self.dimension_text_prefix_var.get())
        if hasattr(self, "canvas"):
            self.after_idle(self.canvas.focus_set)

    def sync_dimension_ui_from_tool(self) -> None:
        """Синхронизировать панель параметров размеров с текущим инструментом."""
        mode = self.dimension_tool.mode
        available_modes = self._get_available_dimension_display_modes()
        mode_labels = [RADIAL_DISPLAY_MODE_NAMES[key] for key in available_modes]
        self.dimension_display_mode_combo.configure(values=mode_labels)

        current_mode = self.dimension_tool.default_radial_display_mode
        if current_mode not in available_modes:
            current_mode = available_modes[0]
        self.dimension_display_mode_var.set(RADIAL_DISPLAY_MODE_NAMES[current_mode])
        self.dimension_linear_mode_var.set(
            LINEAR_DIMENSION_MODE_NAMES.get(
                self.dimension_tool.default_linear_mode, LINEAR_DIMENSION_MODE_NAMES['aligned']
            )
        )
        self.dimension_font_size_var.set(self.dimension_tool.default_font_size)
        self.dimension_font_type_var.set(
            DIMENSION_FONT_TYPE_NAMES.get(
                self.dimension_tool.default_font_type, DIMENSION_FONT_TYPE_NAMES['type_b_italic']
            )
        )
        self.dimension_arrow_shape_var.set(
            ARROW_SHAPE_NAMES.get(
                self.dimension_tool.default_arrow_shape, ARROW_SHAPE_NAMES['triangle']
            )
        )
        self.dimension_arrow_filled_var.set(self.dimension_tool.default_arrow_filled)
        self.dimension_arrow_size_var.set(self.dimension_tool.default_arrow_size)
        self.dimension_text_prefix_var.set(self.dimension_tool.default_text_prefix)
        self._update_dimension_arrow_fill_state()

        is_radial_mode = mode in ("radius", "diameter")
        is_linear_mode = mode == "linear"
        self.dimension_linear_mode_combo.configure(
            state="readonly" if is_linear_mode else "disabled"
        )
        if is_radial_mode:
            self.dimension_display_mode_combo.configure(state="readonly")
            self.dimension_display_label.configure(text="Оформление:")
            if current_mode == 'leader':
                self.dimension_shelf_label.configure(text="Вынос полки:")
                self.dimension_shelf_offset_var.set(self.dimension_tool.default_radial_shelf_offset)
                self.dimension_shelf_spin.configure(state="normal")
            elif current_mode == 'aligned':
                self.dimension_shelf_label.configure(text="Вынос линии:")
                self.dimension_shelf_offset_var.set(self.dimension_tool.default_radial_line_extension)
                self.dimension_shelf_spin.configure(state="normal")
            elif current_mode == 'outside':
                self.dimension_shelf_label.configure(text="Отступ размера:")
                self.dimension_shelf_offset_var.set(self.dimension_tool.default_radial_outside_offset)
                self.dimension_shelf_spin.configure(state="normal")
            else:
                self.dimension_shelf_label.configure(text="Вынос полки:")
                self.dimension_shelf_offset_var.set(self.dimension_tool.default_radial_shelf_offset)
                self.dimension_shelf_spin.configure(state="disabled")
            self.dimension_params_hint.configure(
                text="Параметры применяются сразу\nк новому размеру"
            )
        else:
            self.dimension_display_mode_combo.configure(state="disabled")
            self.dimension_shelf_spin.configure(state="disabled")
            self.dimension_display_label.configure(text="Оформление:")
            self.dimension_shelf_label.configure(text="Вынос полки:")
            self.dimension_params_hint.configure(
                text="Общие параметры применяются сразу\nк новому размеру"
            )
    
    def _create_toolbar(self) -> None:
        """Создание панели инструментов (toolbar)"""
        toolbar = ttk.Frame(self, relief=tk.RAISED)
        toolbar.pack(side=tk.TOP, fill=tk.X)
        
        # Левая часть - основные инструменты
        left = ttk.Frame(toolbar)
        left.pack(side=tk.LEFT, padx=4, pady=4)
        
        ttk.Button(left, text="📂", width=3, 
                  command=self._on_open).pack(side=tk.LEFT, padx=1)
        ttk.Button(left, text="💾", width=3,
                  command=self._on_save).pack(side=tk.LEFT, padx=1)
        
        ttk.Separator(left, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=6)
        
        ttk.Button(left, text="🔍+", width=3,
                  command=lambda: self.zoom_by_factor(1.2)).pack(side=tk.LEFT, padx=1)
        ttk.Button(left, text="🔍-", width=3,
                  command=lambda: self.zoom_by_factor(0.8)).pack(side=tk.LEFT, padx=1)
        ttk.Button(left, text="🔍◻", width=3,
                  command=self.fit_all_to_view).pack(side=tk.LEFT, padx=1)
        
        ttk.Separator(left, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=6)
        
        ttk.Button(left, text="↺", width=3,
                  command=self.rotate_right).pack(side=tk.LEFT, padx=1)
        ttk.Button(left, text="↻", width=3,
                  command=self.rotate_left).pack(side=tk.LEFT, padx=1)
        
        # Правая часть - настройки
        right = ttk.Frame(toolbar)
        right.pack(side=tk.RIGHT, padx=4, pady=4)
        
        ttk.Label(right, text="Сетка:").pack(side=tk.LEFT, padx=(0, 4))
        grid_spin = ttk.Spinbox(right, from_=5, to=100, increment=5,
                               textvariable=self.grid_step_var, width=5,
                               command=self._on_grid_step_changed)
        grid_spin.pack(side=tk.LEFT)
        grid_spin.bind('<Return>', lambda e: (self._on_grid_step_changed(), self.canvas.focus_set()))
        
        ttk.Button(right, text="🎨", width=3,
                  command=self._open_theme_settings).pack(side=tk.LEFT, padx=(10, 0))
    
    def _create_menu(self) -> None:
        """Создание меню"""
        menubar = tk.Menu(self)
        self.config(menu=menubar)
        
        # Файл
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Файл", menu=file_menu)
        file_menu.add_command(label="Очистить всё", command=self._on_clear_all)
        file_menu.add_separator()
        file_menu.add_command(label="Экспорт в DXF...", command=self._on_export_dxf)
        file_menu.add_separator()
        file_menu.add_command(label="Выход", command=self.quit)
        
        # Вид
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Вид", menu=view_menu)
        view_menu.add_command(label="Увеличить", command=lambda: self.zoom_by_factor(1.2), accelerator="=")
        view_menu.add_command(label="Уменьшить", command=lambda: self.zoom_by_factor(0.8), accelerator="-")
        view_menu.add_command(label="Показать всё", command=self.fit_all_to_view, accelerator="F")
        view_menu.add_separator()
        view_menu.add_command(label="Сбросить вид", command=self.reset_view, accelerator="Home")
        view_menu.add_separator()
        view_menu.add_command(label="Настройки темы...", command=self._open_theme_settings)
        
        # Инструменты
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Инструменты", menu=tools_menu)
        tools_menu.add_radiobutton(label="Рисование", command=lambda: self.set_tool("draw"), 
                                   accelerator="D", variable=self.tool_var, value="draw")
        tools_menu.add_radiobutton(label="Выделение", command=lambda: self.set_tool("select"), 
                                   accelerator="S", variable=self.tool_var, value="select")
        tools_menu.add_radiobutton(label="Панорамирование", command=lambda: self.set_tool("pan"), 
                                   accelerator="H", variable=self.tool_var, value="pan")
        
        # Справка
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Справка", menu=help_menu)
        help_menu.add_command(label="Горячие клавиши", command=self._show_hotkeys)
    
    def _show_hotkeys(self) -> None:
        """Показать окно с горячими клавишами"""
        hotkeys = """
Горячие клавиши supermegaCAD:

ИНСТРУМЕНТЫ:
  D - Рисование
  S - Выделение
  H - Панорама
  M - Размеры

ВИД:
  + / = - Увеличить
  - - Уменьшить
  F - Показать всё
  [ - Повернуть влево
  ] - Повернуть вправо
  Home - Сбросить вид

РЕДАКТИРОВАНИЕ:
  Delete/Backspace - Удалить
  Escape - Отмена
  Enter - Завершить сплайн

НАВИГАЦИЯ:
  СКМ (зажать) - Панорамирование
  Колёсико - Масштаб
        """
        messagebox.showinfo("Горячие клавиши", hotkeys.strip())
    
    def _update_creation_modes(self) -> None:
        """Обновить режимы создания"""
        for widget in self.modes_container.winfo_children():
            widget.destroy()
        
        modes = self.draw_tool.get_available_modes()
        
        if len(modes) <= 1:
            ttk.Label(self.modes_container, text="По умолчанию",
                     foreground="#888888").pack(anchor=tk.W)
            return
        
        current = self.creation_mode_var.get()
        mode_names = [m[0].name for m in modes]
        # Если текущий режим недоступен для выбранного примитива — берем первый
        if current not in mode_names:
            current = modes[0][0].name
            self.creation_mode_var.set(current)
        for mode, label in modes:
            ttk.Radiobutton(
                self.modes_container, text=label,
                variable=self.creation_mode_var, value=mode.name,
                command=lambda m=mode: self._set_creation_mode(m)
            ).pack(anchor=tk.W, pady=1)
            
    def _update_dimension_modes(self) -> None:
        """Обновить панель типов размеров"""
        for widget in self.dim_modes_frame.winfo_children():
            widget.destroy()
            
        dim_modes = [
            ("linear", "Линейный"),
            ("radius", "Радиус"),
            ("diameter", "Диаметр"),
            ("angular", "Угловой")
        ]
        
        for mode, label in dim_modes:
            ttk.Radiobutton(
                self.dim_modes_frame, text=label,
                variable=self.dimension_mode_var, value=mode,
                command=lambda m=mode: self._set_dimension_mode(m)
            ).pack(anchor=tk.W, pady=1)

    
    def _set_primitive_type(self, ptype: PrimitiveType) -> None:
        """Установить тип примитива"""
        self.draw_tool.primitive_type = ptype
        self.primitive_type_var.set(ptype.name.lower())
        self._update_creation_modes()
        self._update_params_visibility()
        self.set_tool("draw")
    
    def _set_creation_mode(self, mode: CreationMode) -> None:
        self.creation_mode_var.set(mode.name)
        self.draw_tool.creation_mode = mode
        if hasattr(self, "canvas"):
            self.canvas.focus_set()
    
    def _on_polygon_sides_changed(self) -> None:
        self.draw_tool.set_polygon_sides(self.polygon_sides_var.get())
    
    def _on_polygon_inscribed_changed(self) -> None:
        self.draw_tool.set_polygon_inscribed(self.polygon_inscribed_var.get())
    
    def _on_rect_corner_changed(self) -> None:
        self.draw_tool.set_rect_corner_radius(self.rect_corner_radius_var.get())
        if hasattr(self, "canvas"):
            self.canvas.focus_set()
    
    def _on_rect_chamfer_changed(self) -> None:
        self.draw_tool.set_rect_chamfer(self.rect_chamfer_var.get())
        if hasattr(self, "canvas"):
            self.canvas.focus_set()
    
    def _toggle_snap(self) -> None:
        self.snap_manager.set_enabled(self.snap_enabled_var.get())
        self.update_status_bar()
    
    def _toggle_snap_type(self, snap_type: SnapType) -> None:
        self.snap_manager.set_snap_type_enabled(snap_type, self.snap_type_vars[snap_type].get())
    
    def _on_grid_step_changed(self) -> None:
        """Обработка изменения шага сетки"""
        try:
            step = float(self.grid_step_var.get())
            self.grid_manager.base_step = step
        except (ValueError, tk.TclError):
            pass
        self.redraw()

    def _create_status_bar(self) -> None:
        """Создание строки состояния"""
        status_frame = ttk.Frame(self)
        status_frame.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Цветной индикатор привязок
        self.snap_indicator = tk.Canvas(status_frame, width=12, height=12, 
                                        highlightthickness=0, bg="#2a2a3e")
        self.snap_indicator.pack(side=tk.LEFT, padx=(8, 2), pady=4)
        
        labels = [
            ('snap_label', "Привязки", 10),
            ('coord_label', "X: 0.00  Y: 0.00", 22),
            ('zoom_label', "100%", 8),
            ('rotation_label', "0°", 6),
            ('tool_label', "Рисование", None),
        ]
        
        for i, (attr_name, text, width) in enumerate(labels):
            if i > 0:
                ttk.Separator(status_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=6)
            label = ttk.Label(status_frame, text=text, width=width) if width else \
                    ttk.Label(status_frame, text=text)
            label.pack(side=tk.LEFT, padx=2)
            setattr(self, attr_name, label)

        # Подсказка справа
        self.hint_label = ttk.Label(status_frame, text="", foreground="#888888")
        self.hint_label.pack(side=tk.RIGHT, padx=8)

    def _bind_events(self) -> None:
        """Привязка событий"""
        self.canvas.bind("<Configure>", lambda e: self.redraw())
        self.canvas.bind("<Button-1>", self._on_left_click)
        self.canvas.bind("<ButtonRelease-1>", self._on_left_release)
        self.canvas.bind("<Button-2>", lambda e: self.navigation_handler.handle_middle_button_down(e))
        self.canvas.bind("<ButtonRelease-2>", lambda e: self.navigation_handler.handle_middle_button_up(e))
        self.canvas.bind("<Button-3>", self._on_right_click)
        self.canvas.bind("<Motion>", self._on_mouse_move)
        self.canvas.bind("<MouseWheel>", lambda e: self.navigation_handler.handle_mouse_wheel(e))
        self.canvas.bind("<Button-4>", lambda e: self.navigation_handler.handle_mouse_wheel(e))
        self.canvas.bind("<Button-5>", lambda e: self.navigation_handler.handle_mouse_wheel(e))
        self.bind("<KeyPress>", self._on_key_press)

    def _on_key_press(self, event: tk.Event) -> None:
        """Обработка горячих клавиш"""
        # Проверяем, находится ли фокус на поле ввода
        focused = self.focus_get()
        is_entry = isinstance(focused, (tk.Entry, ttk.Entry, tk.Text, ttk.Spinbox))
        
        # Если фокус на поле ввода - не перехватываем большинство клавиш
        if is_entry:
            return  # Пусть виджет обрабатывает сам
        
        if isinstance(self.current_tool, DrawTool):
            if self.current_tool.on_key_press(event):
                return
        
        if isinstance(self.current_tool, DimensionTool):
            if self.current_tool.on_key_press(event):
                return
        
        key = event.keysym.lower()
        key_map = {
            'd': lambda: self.set_tool("draw"),
            's': lambda: self.set_tool("select"),
            'h': lambda: self.set_tool("pan"),
            'm': lambda: self.set_tool("dimension"),
            'equal': lambda: self.zoom_by_factor(1.2),
            'plus': lambda: self.zoom_by_factor(1.2),
            'minus': lambda: self.zoom_by_factor(0.8),
            'f': self.fit_all_to_view,
            'bracketleft': self.rotate_right,
            'bracketright': self.rotate_left,
            'home': self.reset_view,
            'delete': self._on_delete_shape,
            'backspace': self._on_delete_shape
        }
        if key in key_map:
            key_map[key]()

    def set_tool(self, tool_name: str) -> None:
        """Установить активный инструмент"""
        self.current_tool.on_deactivate()
        if tool_name in self.tools:
            self.current_tool, label = self.tools[tool_name]
            self.tool_label.config(text=label)
        self.current_tool.on_activate()
        self.update_cursor()
        self.tool_var.set(tool_name)
        
        # При переключении на рисование снимаем выделение
        if tool_name == "draw" or tool_name == "dimension":
            self.shape_manager.deselect_all()
            self.properties_panel.update_for_shape(None)
            
        # Обновление UI панелей
        if tool_name == "dimension":
            self.modes_frame.pack_forget()
            self.prims_frame.pack_forget()
            self.dim_modes_frame.pack(fill=tk.X, padx=6, pady=6, after=self.tools_frame)
            self._update_dimension_modes()
        elif tool_name == "draw":
            self.dim_modes_frame.pack_forget()
            self.prims_frame.pack(fill=tk.X, padx=6, pady=6, after=self.tools_frame)
            self.modes_frame.pack(fill=tk.X, padx=6, pady=6, after=self.prims_frame)
        else:
            self.dim_modes_frame.pack_forget()
        
        self._update_params_visibility()
        
        # Обновляем подсказку
        hints = {
            "draw": "Кликните для указания точек",
            "select": "Кликните для выбора объекта",
            "pan": "Зажмите ЛКМ для панорамирования",
            "dimension": "Кликните для выбора точек/объектов"
        }
        self.hint_label.config(text=hints.get(tool_name, ""))
        self.canvas.focus_set()
        
        self.redraw()

    def update_cursor(self) -> None:
        self.canvas.config(cursor=self.current_tool.get_cursor())

    def _on_left_click(self, event: tk.Event) -> None:
        self.current_tool.on_mouse_down(event)

    def _on_left_release(self, event: tk.Event) -> None:
        self.current_tool.on_mouse_up(event)

    def _on_right_click(self, event: tk.Event) -> None:
        if isinstance(self.current_tool, DrawTool):
            if self.current_tool.on_right_click(event):
                return
        
        if isinstance(self.current_tool, DimensionTool):
            if self.current_tool.on_right_click(event):
                return
        
        # Контекстное меню
        context_menu = tk.Menu(self, tearoff=0)
        
        for label, cmd in [("Увеличить", lambda: self.zoom_by_factor(1.2)),
                           ("Уменьшить", lambda: self.zoom_by_factor(0.8)),
                           ("Показать всё", self.fit_all_to_view)]:
            context_menu.add_command(label=label, command=cmd)
        
        context_menu.add_separator()
        
        for label, value in [("Рисование", "draw"), ("Выделение", "select"), ("Панорама", "pan")]:
            context_menu.add_radiobutton(label=label, variable=self.tool_var, value=value, 
                                        command=lambda v=value: self.set_tool(v))
        
        try:
            context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            context_menu.grab_release()

    def _on_mouse_move(self, event: tk.Event) -> None:
        """Обработка движения мыши"""
        w, h = self.canvas.winfo_width(), self.canvas.winfo_height()
        self.cursor_world_x, self.cursor_world_y = self.view_transform.screen_to_world(event.x, event.y, w, h)
        self.update_status_bar()
        self.navigation_handler.handle_mouse_move(event)
        self.current_tool.on_mouse_move(event)

    def _redraw_and_update(self) -> None:
        self.redraw()
        self.update_status_bar()

    def zoom_by_factor(self, factor: float) -> None:
        self.view_transform.zoom(factor, 0, 0)
        self._redraw_and_update()

    def rotate_left(self) -> None:
        self.view_transform.rotate_90_left()
        self._redraw_and_update()
    
    def rotate_right(self) -> None:
        self.view_transform.rotate_90_right()
        self._redraw_and_update()

    def reset_view(self) -> None:
        self.view_transform.reset()
        self._redraw_and_update()

    def fit_all_to_view(self) -> None:
        shapes = self.shape_manager.get_all_shapes()
        if not shapes:
            messagebox.showinfo("Информация", "Нет фигур для отображения")
            return
        
        bounds_list = [shape.get_bounds() for shape in shapes]
        min_x = min(b[0] for b in bounds_list)
        min_y = min(b[1] for b in bounds_list)
        max_x = max(b[2] for b in bounds_list)
        max_y = max(b[3] for b in bounds_list)
        
        w, h = self.canvas.winfo_width(), self.canvas.winfo_height()
        
        # Dynamic margin: 10% of the smallest dimension, but at least 50px
        margin = max(50, int(min(w, h) * 0.1))
        
        self.view_transform.fit_to_view((min_x, min_y, max_x, max_y), w, h, margin=margin)
        self._redraw_and_update()

    def update_status_bar(self) -> None:
        self.coord_label.config(text=f"X: {self.cursor_world_x:.2f}  Y: {self.cursor_world_y:.2f}")
        self.zoom_label.config(text=f"{self.view_transform.get_scale_percent()}%")
        self.rotation_label.config(text=f"{self.view_transform.get_rotation_degrees()}°")

        # Цветной индикатор привязок
        snap_on = self.snap_manager.is_enabled()
        color = "#44ff44" if snap_on else "#ff4444"
        self.snap_indicator.delete("all")
        self.snap_indicator.create_oval(2, 2, 10, 10, fill=color, outline="")
        self.snap_label.config(text="Привязки" if snap_on else "Откл.")

    def _on_delete_shape(self) -> None:
        if not self.shape_manager.has_shapes():
            return
        
        # Определяем, какую фигуру удаляем
        shape_to_delete = self.shape_manager.get_selected_shape()
        if not shape_to_delete:
            shape_to_delete = self.shape_manager.get_all_shapes()[-1] if self.shape_manager.get_all_shapes() else None
        
        if not shape_to_delete:
            return
        
        # Проверяем, есть ли привязанные размеры (только если удаляем НЕ размер)
        if not isinstance(shape_to_delete, Dimension):
            shape_id = getattr(shape_to_delete, 'id', None)
            if shape_id:
                deps = self.shape_manager.find_dependent_dimensions(shape_id)
                if deps:
                    n = len(deps)
                    answer = messagebox.askyesnocancel(
                        "Удаление элемента",
                        f"К этому элементу привязано {n} размер(ов).\n\n"
                        "Да — удалить элемент вместе с размерами\n"
                        "Нет — удалить только элемент (размеры останутся)\n"
                        "Отмена — не удалять"
                    )
                    if answer is None:  # Отмена
                        return
                    if answer:  # Да — каскадное удаление (поведение по умолчанию)
                        self.shape_manager.remove_shape(shape_to_delete)
                    else:  # Нет — удалить без каскада
                        self.shape_manager.remove_shape_no_cascade(shape_to_delete)
                    self.redraw()
                    return
        
        # Обычное удаление (без зависимых размеров или удаляем сам размер)
        self.shape_manager.remove_shape(shape_to_delete)
        self.redraw()

    def _on_export_dxf(self) -> None:
        """Экспорт в DXF"""
        from tkinter import filedialog
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".dxf",
            filetypes=[("DXF Files", "*.dxf"), ("All Files", "*.*")],
            title="Экспорт в DXF"
        )
        
        if not filename:
            return
            
        # Ask for margin
        from tkinter import simpledialog
        margin = simpledialog.askfloat("Экспорт", "Отступ (мм):", initialvalue=40.0, minvalue=0.0)
        if margin is None:
            margin = 40.0 # Default if cancelled, or return? Let's default.
            
        try:
            from exporters.dxf_exporter import DxfExporter
            
            shapes = self.shape_manager.get_all_shapes()
            styles = self.style_manager.get_all_styles()
            
            exporter = DxfExporter()
            exporter.export(filename, shapes, styles, margin=margin)
            
            messagebox.showinfo("Успех", f"Файл успешно сохранен:\n{filename}")
            
        except Exception as e:
            messagebox.showerror("Ошибка экспорта", f"Не удалось сохранить файл:\n{e}")

    def _on_save(self) -> None:
        """Сохранить (пока просто экспорт в DXF)"""
        self._on_export_dxf()

    def _on_open(self) -> None:
        """Открыть файл"""
        from tkinter import filedialog
        
        filename = filedialog.askopenfilename(
            filetypes=[("DXF Files", "*.dxf"), ("All Files", "*.*")],
            title="Открыть файл"
        )
        
        if not filename:
            return
            
        try:
            # Импортируем
            importer = DxfImporter()
            shapes = importer.import_file(filename)
            
            if shapes:
                # Попытка восстановить имена стилей (обратное отображение из DXF Layer)
                known_styles = self.style_manager.get_style_names()
                
                # Создаем карту: {sanitized_name: real_name}
                # Используем логику очистки как в экспортере (простая замена)
                style_map = {}
                for name in known_styles:
                    sanitized = name.replace(" ", "_").replace(".", "").replace(",", "")
                    style_map[sanitized] = name
                    # Также добавим прямое совпадение на случай если имя не менялось
                    style_map[name] = name

                for shape in shapes:
                    # Если стиль найден в карте (по очищенному имени), восстанавливаем оригинал
                    if shape.line_style_name in style_map:
                        shape.line_style_name = style_map[shape.line_style_name]
                    else:
                        # Эвристика: заменяем подчеркивания на пробелы
                        fuzzy_name = shape.line_style_name.replace("_", " ")
                        if fuzzy_name in known_styles:
                            shape.line_style_name = fuzzy_name

                if self.shape_manager.has_shapes():
                    if not messagebox.askyesno("Импорт", "Добавить к существующим фигурам?\n(Нет - очистить холст)"):
                        self.shape_manager.clear_all()
                
                for shape in shapes:
                    self.shape_manager.add_shape(shape)
                
                self.fit_all_to_view()
                self.redraw()
                messagebox.showinfo("Успех", f"Импортировано фигур: {len(shapes)}")
            else:
                messagebox.showwarning("Импорт", "Не удалось прочитать фигуры из файла")
                
        except Exception as e:
            messagebox.showerror("Ошибка импорта", f"Не удалось открыть файл:\n{e}")

    def _on_clear_all(self) -> None:
        if self.shape_manager.has_shapes() and messagebox.askyesno("Подтверждение", "Удалить все фигуры?"):
                self.shape_manager.clear_all()
                self.redraw()

    def _on_current_style_changed(self, event=None) -> None:
        style_name = self.current_style_var.get()
        self.style_manager.set_current_style(style_name)

    def _open_style_manager(self) -> None:
        StyleManagerDialog(self, self.style_manager, on_update_callback=self.redraw)
    
    def _open_theme_settings(self) -> None:
        ThemeDialog(self, self.renderer, on_update_callback=self.redraw)

    def redraw(self) -> None:
        """Главная функция отрисовки"""
        w, h = int(self.canvas.winfo_width()), int(self.canvas.winfo_height())
        if w <= 2 or h <= 2:
            return

        self.canvas.configure(background=self.renderer.color_bg)
        self.renderer.draw_grid(w, h, self.grid_manager, self.view_transform)
        self.renderer.clear_objects("shape", "preview", "axis_indicator", "control_points", "snap_indicator")
        self.renderer.draw_shapes(self.shape_manager.get_all_shapes(), w, h, self.view_transform, self.POINT_RADIUS)
        
        if isinstance(self.current_tool, (DrawTool, DimensionTool)):
            self.current_tool.draw_preview(self.renderer, w, h, self.view_transform)
        
        if isinstance(self.current_tool, SelectTool):
            self.current_tool.draw_control_points(self.renderer, w, h, self.view_transform)
        
        self.renderer.draw_axis_indicator(w, h, self.view_transform)
        self._update_info_panel()
        
        # Обновляем панель свойств ТОЛЬКО если выделение изменилось
        selected = self.shape_manager.get_selected_shape()
        if selected != self._last_selected_shape:
            self._last_selected_shape = selected
            self.properties_panel.update_for_shape(selected)

    def _update_info_panel(self) -> None:
        """Обновление информационной панели"""
        shapes = self.shape_manager.get_all_shapes()
        
        if not shapes:
            UIBuilder.update_text_widget(self.info_text, 
                "Нет объектов\n\n"
                "Выберите примитив слева\n"
                "и кликните на холсте")
            return
        
        lines = [f"Объектов: {len(shapes)}"]
        
        selected_index = self.shape_manager.get_selected_index()
        if selected_index is not None:
            lines.append(f"Выбран: #{selected_index + 1}")
        
        if isinstance(self.current_tool, DrawTool):
            lines.append(f"Примитив: {self.draw_tool.get_primitive_name()}")
        
        UIBuilder.update_text_widget(self.info_text, "\n".join(lines))


def main() -> None:
    app = GeometryApp()
    app.mainloop()


if __name__ == "__main__":
    main()
