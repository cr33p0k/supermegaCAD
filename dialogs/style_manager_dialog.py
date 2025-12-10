"""Диалоговое окно управления стилями линий"""
import tkinter as tk
from tkinter import ttk, messagebox


class StyleManagerDialog(tk.Toplevel):
    """Диалог для управления стилями линий ГОСТ 2.303-68"""
    
    def __init__(self, parent, style_manager, on_update_callback=None):
        super().__init__(parent)
        self.style_manager = style_manager
        self.on_update_callback = on_update_callback
        self.current_style_name = None
        self.param_widgets = {}  # Хранит виджеты параметров
        
        self._setup_window()
        self._create_ui()
        
    def _setup_window(self):
        """Настройка окна"""
        self.title("Управление стилями линий")
        self.geometry("770x570")
        self.minsize(770, 570)
        self.transient(self.master)
        self.grab_set()
        
    def _create_ui(self):
        """Создание интерфейса"""
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=0, minsize=340)
        self.grid_columnconfigure(1, weight=1, minsize=380)
        
        self._create_style_list()
        self._create_edit_panel()
        
    def _create_style_list(self):
        """Создание списка стилей"""
        list_frame = ttk.LabelFrame(self, text="Доступные стили")
        list_frame.grid(row=0, column=0, sticky="nsew", padx=(10, 5), pady=10)
        
        scroll = ttk.Scrollbar(list_frame)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.style_listbox = tk.Listbox(list_frame, yscrollcommand=scroll.set, 
                                        font=("Consolas", 10), width=35)
        self.style_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        scroll.config(command=self.style_listbox.yview)
        
        for style in self.style_manager.get_all_styles():
            marker = "●" if style.is_standard else "○"
            self.style_listbox.insert(tk.END, f"{marker} {style.name}")
        
        self.style_listbox.bind("<<ListboxSelect>>", self._on_style_select)
        
    def _create_edit_panel(self):
        """Создание панели редактирования"""
        self.edit_frame = ttk.LabelFrame(self, text="Параметры стиля")
        self.edit_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 10), pady=10)
        
        # Название и описание (статичные)
        ttk.Label(self.edit_frame, text="Название:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.name_label = ttk.Label(self.edit_frame, text="", font=("Arial", 10, "bold"))
        self.name_label.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        
        ttk.Label(self.edit_frame, text="Тип линии:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.type_label = ttk.Label(self.edit_frame, text="")
        self.type_label.grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        
        ttk.Label(self.edit_frame, text="Описание:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        self.desc_label = ttk.Label(self.edit_frame, text="", wraplength=250)
        self.desc_label.grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Фрейм для динамических параметров
        self.params_frame = ttk.Frame(self.edit_frame)
        self.params_frame.grid(row=3, column=0, columnspan=2, sticky="nsew", pady=10)
        
        # Кнопки
        button_frame = ttk.Frame(self.edit_frame)
        button_frame.grid(row=4, column=0, columnspan=2, pady=20)
        
        ttk.Button(button_frame, text="Сохранить изменения", 
                   command=self._save_changes).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Закрыть", 
                   command=self.destroy).pack(side=tk.LEFT, padx=5)
        
        self.edit_frame.grid_columnconfigure(0, weight=1)
        self.edit_frame.grid_columnconfigure(1, weight=1)

    def _clear_params(self):
        """Очистить динамические параметры"""
        for widget in self.params_frame.winfo_children():
            widget.destroy()
        self.param_widgets.clear()

    def _add_param(self, row: int, label: str, key: str, value: float, 
                   from_: float = 0.1, to: float = 20.0, increment: float = 0.1):
        """Добавить поле параметра"""
        ttk.Label(self.params_frame, text=label).grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        var = tk.DoubleVar(value=value)
        spin = ttk.Spinbox(self.params_frame, from_=from_, to=to, increment=increment,
                           textvariable=var, width=10)
        spin.grid(row=row, column=1, sticky=tk.W, padx=5, pady=5)
        self.param_widgets[key] = var
    
    def _add_int_param(self, row: int, label: str, key: str, value: int, 
                       from_: int = 1, to: int = 10):
        """Добавить поле параметра для целых чисел"""
        ttk.Label(self.params_frame, text=label).grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        var = tk.IntVar(value=value)
        spin = ttk.Spinbox(self.params_frame, from_=from_, to=to, increment=1,
                           textvariable=var, width=10)
        spin.grid(row=row, column=1, sticky=tk.W, padx=5, pady=5)
        self.param_widgets[key] = var

    def _on_style_select(self, event):
        """Обработчик выбора стиля из списка"""
        selection = self.style_listbox.curselection()
        if not selection:
            return
            
        idx = selection[0]
        style = self.style_manager.get_all_styles()[idx]
        self.current_style_name = style.name
        
        # Обновляем статичные поля
        self.name_label.config(text=style.name)
        self.desc_label.config(text=style.description)
        
        # Названия типов линий
        type_names = {
            'solid': 'Сплошная',
            'dashed': 'Штриховая',
            'dashdot': 'Штрихпунктирная',
            'dashdotdot': 'Штрихпунктирная с двумя точками',
            'wavy': 'Волнистая',
            'broken': 'С изломом'
        }
        self.type_label.config(text=type_names.get(style.line_type, style.line_type))
        
        # Очищаем и создаём параметры в зависимости от типа
        self._clear_params()
        row = 0
        
        # Толщина - всегда есть
        self._add_param(row, "Толщина (мм):", "thickness_mm", style.thickness_mm, 
                        from_=0.1, to=2.0, increment=0.1)
        row += 1
        
        # Параметры в зависимости от типа линии
        if style.line_type == 'wavy':
            # Волнистая линия
            self._add_param(row, "Амплитуда волны (пкс):", "wave_amplitude", 
                            style.wave_amplitude, from_=1.0, to=10.0, increment=0.5)
            row += 1
            self._add_param(row, "Длина волны (пкс):", "wave_length",
                            style.wave_length, from_=4.0, to=30.0, increment=1.0)
            row += 1
            
        elif style.line_type == 'dashed':
            # Штриховая линия
            self._add_param(row, "Длина штриха:", "dash_length",
                            style.dash_length, from_=1.0, to=20.0, increment=0.5)
            row += 1
            self._add_param(row, "Длина промежутка:", "gap_length",
                            style.gap_length, from_=1.0, to=10.0, increment=0.5)
            row += 1
            
        elif style.line_type in ('dashdot', 'dashdotdot'):
            # Штрихпунктирная линия
            self._add_param(row, "Длина штриха:", "dash_length",
                            style.dash_length, from_=1.0, to=30.0, increment=0.5)
            row += 1
            self._add_param(row, "Длина промежутка:", "gap_length",
                            style.gap_length, from_=1.0, to=10.0, increment=0.5)
            row += 1
            self._add_param(row, "Длина точки:", "dot_length",
                            style.dot_length, from_=0.5, to=5.0, increment=0.5)
            row += 1
            
        elif style.line_type == 'broken':
            # Линия с изломом
            break_height = getattr(style, 'break_height', 12.0)
            break_width = getattr(style, 'break_width', 10.0)
            break_count = getattr(style, 'break_count', 1)
            self._add_param(row, "Высота излома (пкс):", "break_height",
                            break_height, from_=5.0, to=30.0, increment=1.0)
            row += 1
            self._add_param(row, "Ширина излома (пкс):", "break_width",
                            break_width, from_=5.0, to=30.0, increment=1.0)
            row += 1
            self._add_int_param(row, "Количество изломов:", "break_count",
                               int(break_count), from_=1, to=10)
            row += 1
        
        # Для solid (сплошная) - только толщина, параметры уже добавлены
            
    def _save_changes(self):
        """Сохранить изменения стиля"""
        if not self.current_style_name:
            return
            
        # Собираем все значения из виджетов
        params = {}
        for key, var in self.param_widgets.items():
            # Для IntVar возвращаем int, для DoubleVar - float
            value = var.get()
            if isinstance(var, tk.IntVar):
                params[key] = int(value)
            else:
                params[key] = float(value)
        
        self.style_manager.update_style(self.current_style_name, **params)
        messagebox.showinfo("Успешно", "Параметры стиля обновлены!", parent=self)
        
        if self.on_update_callback:
            self.on_update_callback()
