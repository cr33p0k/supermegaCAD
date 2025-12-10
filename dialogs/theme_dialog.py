"""Диалоговое окно настроек темы оформления"""
import tkinter as tk
from tkinter import ttk, colorchooser


class ThemeDialog(tk.Toplevel):
    """Диалог для настройки цветов темы"""
    
    def __init__(self, parent, renderer, on_update_callback=None):
        """
        Args:
            parent: Родительское окно
            renderer: Экземпляр CanvasRenderer
            on_update_callback: Функция для вызова при обновлении
        """
        super().__init__(parent)
        self.renderer = renderer
        self.on_update_callback = on_update_callback
        
        # Текущие цвета
        self.colors = {
            'bg': renderer.color_bg,
            'grid': renderer.color_grid,
            'axis_x': renderer.color_axis_x,
            'axis_y': renderer.color_axis_y
        }
        
        self._setup_window()
        self._create_ui()
        
    def _setup_window(self):
        """Настройка окна"""
        self.title("Настройки темы")
        self.geometry("580x450")
        self.minsize(580, 450)
        self.transient(self.master)
        self.grab_set()
        
    def _create_ui(self):
        """Создание интерфейса"""
        main_frame = ttk.Frame(self, padding=15)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(main_frame, text="Настройка цветов", 
                 font=("Arial", 13, "bold")).pack(pady=(0, 15))
        
        # Список цветов для настройки
        color_items = [
            ('bg', 'Цвет фона'),
            ('grid', 'Цвет сетки'),
            ('axis_x', 'Цвет оси X (красная)'),
            ('axis_y', 'Цвет оси Y (зеленая)')
        ]
        
        # Создание строк выбора цвета
        self.color_canvas = {}
        self.color_labels = {}
        
        for key, label in color_items:
            frame = ttk.Frame(main_frame)
            frame.pack(fill=tk.X, pady=6)
            
            ttk.Label(frame, text=label, width=22).pack(side=tk.LEFT, padx=(0, 10))
            
            # Canvas для отображения цвета (работает на macOS)
            canvas = tk.Canvas(frame, width=40, height=25, highlightthickness=1, highlightbackground="#999")
            canvas.pack(side=tk.LEFT, padx=5)
            canvas.create_rectangle(0, 0, 40, 25, fill=self.colors[key], outline="")
            self.color_canvas[key] = canvas
            
            # Метка с hex значением
            hex_label = ttk.Label(frame, text=self.colors[key], width=10, font=("Courier", 11))
            hex_label.pack(side=tk.LEFT, padx=5)
            self.color_labels[key] = hex_label
            
            # Кнопка выбора
            ttk.Button(frame, text="Выбрать...", width=12,
                      command=lambda k=key: self._choose_color(k)).pack(side=tk.LEFT, padx=5)
        
        # Предустановленные темы
        ttk.Separator(main_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=15)
        
        ttk.Label(main_frame, text="Быстрые темы:", font=("Arial", 11)).pack(anchor=tk.W, pady=(0, 8))
        
        themes_frame = ttk.Frame(main_frame)
        themes_frame.pack(fill=tk.X, pady=5)
        
        themes = [
            ("Темная", {'bg': '#111111', 'grid': '#2a2a2a', 'axis_x': '#ff4444', 'axis_y': '#44ff44'}),
            ("Светлая", {'bg': '#ffffff', 'grid': '#e0e0e0', 'axis_x': '#ff0000', 'axis_y': '#00aa00'})
        ]
        
        for theme_name, theme_colors in themes:
            ttk.Button(themes_frame, text=theme_name, width=15,
                      command=lambda c=theme_colors: self._apply_theme(c)).pack(side=tk.LEFT, padx=5)
        
        # Кнопки управления
        ttk.Separator(main_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=15)
        
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(button_frame, text="Применить", width=12,
                  command=self._apply_colors).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Сбросить", width=12,
                  command=self._reset_colors).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Закрыть", width=12,
                  command=self.destroy).pack(side=tk.RIGHT, padx=5)
        
    def _choose_color(self, key):
        """Выбрать цвет"""
        color = colorchooser.askcolor(self.colors[key], title=f"Выберите цвет", parent=self)
        if color[1]:  # color[1] - hex значение
            self.colors[key] = color[1]
            self.color_canvas[key].delete("all")
            self.color_canvas[key].create_rectangle(0, 0, 40, 25, fill=color[1], outline="")
            self.color_labels[key].config(text=color[1])
            
    def _apply_theme(self, theme_colors):
        """Применить предустановленную тему"""
        self.colors.update(theme_colors)
        for key, color in theme_colors.items():
            self.color_canvas[key].delete("all")
            self.color_canvas[key].create_rectangle(0, 0, 40, 25, fill=color, outline="")
            self.color_labels[key].config(text=color)
        self._apply_colors()
        
    def _apply_colors(self):
        """Применить выбранные цвета"""
        self.renderer.color_bg = self.colors['bg']
        self.renderer.color_grid = self.colors['grid']
        self.renderer.color_axis_x = self.colors['axis_x']
        self.renderer.color_axis_y = self.colors['axis_y']
        
        if self.on_update_callback:
            self.on_update_callback()
            
    def _reset_colors(self):
        """Сбросить к темным цветам по умолчанию"""
        default = {'bg': '#111111', 'grid': '#2a2a2a', 'axis_x': '#ff4444', 'axis_y': '#44ff44'}
        self._apply_theme(default)
