"""Модуль менеджеров для управления различными аспектами приложения"""
from .shape_manager import ShapeManager
from .snap_manager import SnapManager, SnapType, SnapPoint
from .grid_manager import GridManager

__all__ = ['ShapeManager', 'SnapManager', 'SnapType', 'SnapPoint', 'GridManager']
