"""Модуль для работы с геометрическими фигурами"""
from .base import Shape
from .segment import Segment
from .dimension import Dimension, LinearDimension, RadialDimension, AngularDimension
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
    'Dimension', 'LinearDimension', 'RadialDimension', 'AngularDimension',
    'Circle', 
    'Arc', 
    'Rectangle', 
    'Ellipse', 
    'Polygon', 
    'Spline'
]
