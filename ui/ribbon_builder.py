"""Построитель ribbon панелей"""
import tkinter as tk
from tkinter import ttk


class RibbonBuilder:
    """Класс для построения ribbon-панелей с различными элементами"""
    
    @staticmethod
    def build_ribbon_panel(parent, ribbon_data, handlers):
        """
        Построить ribbon панель из данных
        
        Args:
            parent: Родительский фрейм
            ribbon_data: Список групп [(название_группы, элементы)]
            handlers: Словарь с обработчиками и переменными
        """
        for group_title, items in ribbon_data:
            group_frame = ttk.LabelFrame(parent, text=group_title, padding=4)
            group_frame.pack(side=tk.LEFT, fill=tk.BOTH, padx=3, pady=3)
            
            row_idx = 0
            for item in items:
                item_type = item[0]
                
                if item_type == "radio":
                    RibbonBuilder._create_radio(group_frame, item, handlers, row_idx)
                elif item_type == "button":
                    RibbonBuilder._create_button(group_frame, item, row_idx)
                elif item_type == "style_combo":
                    row_idx = RibbonBuilder._create_style_combo(group_frame, item, handlers, row_idx)
                elif item_type == "spinbox":
                    row_idx = RibbonBuilder._create_spinbox(group_frame, item, row_idx)
                elif item_type == "angle_radio":
                    row_idx = RibbonBuilder._create_angle_radio(group_frame, item, row_idx)
                
                row_idx += 1
    
    @staticmethod
    def _create_radio(group_frame, item, handlers, row_idx):
        """Создать радио-кнопку"""
        _, text, value, command, width = item
        ttk.Radiobutton(group_frame, text=text, variable=handlers['tool_var'], 
                        value=value, command=command, width=width).grid(
                        row=row_idx, column=0, sticky=tk.W+tk.E, pady=2, padx=4)
    
    @staticmethod
    def _create_button(group_frame, item, row_idx):
        """Создать кнопку"""
        _, text, command, width = item
        ttk.Button(group_frame, text=text, command=command, width=width).grid(
                   row=row_idx, column=0, sticky=tk.W+tk.E, pady=2, padx=4)
    
    @staticmethod
    def _create_style_combo(group_frame, item, handlers, row_idx):
        """Создать комбобокс стилей"""
        _, label_text, style_var = item
        ttk.Label(group_frame, text=label_text).grid(row=row_idx, column=0, sticky=tk.W, padx=3)
        row_idx += 1
        
        style_combo = ttk.Combobox(group_frame, textvariable=style_var, 
                                   values=handlers['style_names'],
                                   state="readonly", width=22)
        style_combo.bind("<<ComboboxSelected>>", handlers['on_style_changed'])
        style_combo.grid(row=row_idx, column=0, padx=3, pady=2, sticky=tk.W+tk.E)
        return row_idx
    
    @staticmethod
    def _create_spinbox(group_frame, item, row_idx):
        """Создать spinbox"""
        _, label_text, var, from_, to, increment, command = item
        ttk.Label(group_frame, text=label_text).grid(row=row_idx, column=0, sticky=tk.W, padx=3)
        row_idx += 1
        ttk.Spinbox(group_frame, from_=from_, to=to, increment=increment,
                   textvariable=var, width=10, command=command).grid(
                   row=row_idx, column=0, padx=3, pady=2)
        return row_idx
    
    @staticmethod
    def _create_angle_radio(group_frame, item, row_idx):
        """Создать радио-кнопки для выбора единиц углов"""
        _, label_text, var, command = item
        ttk.Label(group_frame, text=label_text).grid(row=row_idx, column=0, sticky=tk.W, padx=3)
        row_idx += 1
        angle_frame = ttk.Frame(group_frame)
        angle_frame.grid(row=row_idx, column=0, padx=3, pady=2)
        ttk.Radiobutton(angle_frame, text="Градусы", variable=var, 
                   value="deg", command=command).pack(side=tk.LEFT)
        ttk.Radiobutton(angle_frame, text="Радианы", variable=var, 
                   value="rad", command=command).pack(side=tk.LEFT, padx=(5, 0))
        return row_idx
