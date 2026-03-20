"""Модуль для работы с геометрическими фигурами"""
from .base import Shape
from .segment import Segment
from .circle import Circle
from .arc import Arc
from .rectangle import Rectangle
from .ellipse import Ellipse
from .polygon import Polygon
from .spline import Spline
from .point import Point

__all__ = [
    'Shape', 
    'Segment', 
    'Circle', 
    'Arc', 
    'Rectangle', 
    'Ellipse', 
    'Polygon', 
    'Spline'
]
