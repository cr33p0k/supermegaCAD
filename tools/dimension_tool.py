"""Инструмент для простановки размерных линий"""
import math
import tkinter as tk
from typing import Optional, List, Tuple, Any
from .base import Tool
from shapes import Dimension, LinearDimension, RadialDimension, AngularDimension, Segment, Circle, Arc
from shapes.dimension import (
    RADIAL_DISPLAY_MODES, LINEAR_DIMENSION_MODES, DIMENSION_FONT_TYPES, ARROW_SHAPES
)
from managers import SnapType


class DimensionTool(Tool):
    """Инструмент для создания размеров"""
    
    def __init__(self, app):
        super().__init__(app)
        self.mode = "linear" # 'linear', 'radius', 'diameter', 'angular'
        self.default_linear_mode = 'aligned'
        self.default_show_shelf = False
        self.default_shelf_dir_override = 0
        self.default_radial_display_mode = 'leader'
        self.default_radial_shelf_length = 40.0
        self.default_radial_shelf_offset = 15.0
        self.default_radial_line_extension = 24.0
        self.default_radial_outside_offset = 20.0
        self.default_font_size = 12
        self.default_font_type = 'type_b_italic'
        self.default_arrow_shape = 'triangle'
        self.default_arrow_filled = True
        self.default_arrow_size = 15.0
        self.default_text_prefix = ""
        
        self.points: List[Tuple[float, float, str, str]] = []  # (x, y, shape_id, click_id)
        self.current_dim: Optional[Dimension] = None
        self.radial_step = 0
        self.linear_center_snap_active = False
        
        # Для углового размера нам нужно выбрать 2 отрезка
        self.lines: List[Tuple[Segment, Tuple[float, float]]] = []
        self.circle_arc = None
        self.hover_circle_arc: Optional[Any] = None

    def _sync_dimension_ui(self) -> None:
        """Синхронизировать элементы UI, если приложение умеет это делать."""
        if hasattr(self.app, 'sync_dimension_ui_from_tool'):
            self.app.sync_dimension_ui_from_tool()

    def _apply_defaults(self, dim: Dimension) -> None:
        """Применить текущие настройки инструмента к новому размеру."""
        dim.show_shelf = self.default_show_shelf
        dim.set_shelf_direction_override(self.default_shelf_dir_override)
        dim.font_size = self.default_font_size
        dim.font_type = self.default_font_type
        dim.arrow_shape = self.default_arrow_shape
        dim.arrow_filled = self.default_arrow_filled
        dim._sync_legacy_arrow_type()
        dim.arrow_size = self.default_arrow_size
        dim.text_prefix = self.default_text_prefix
        if isinstance(dim, LinearDimension):
            dim.measurement_mode = self.default_linear_mode
        if isinstance(dim, RadialDimension):
            dim.display_mode = self._normalize_radial_display_mode(
                self.default_radial_display_mode
            )
            dim.shelf_length = self.default_radial_shelf_length
            dim.shelf_offset = self.default_radial_shelf_offset
            dim.line_extension = self.default_radial_line_extension
            dim.outside_offset = self.default_radial_outside_offset

    def _normalize_radial_display_mode(self, mode: str) -> str:
        """Нормализовать режим радиального размера для текущего типа."""
        if mode not in RADIAL_DISPLAY_MODES:
            return 'leader'
        if self.mode == "radius" and mode not in ('leader', 'aligned'):
            return 'leader'
        return mode

    def set_linear_mode(self, mode: str, apply_to_current: bool = True) -> None:
        """Задать режим линейного размера по умолчанию."""
        if mode not in LINEAR_DIMENSION_MODES:
            return
        self.default_linear_mode = mode
        if apply_to_current and isinstance(self.current_dim, LinearDimension):
            self.current_dim.measurement_mode = mode
            self.app.redraw()
        self._sync_dimension_ui()

    def set_font_size(self, size: int, apply_to_current: bool = True) -> None:
        """Задать размер шрифта размеров по умолчанию."""
        try:
            value = max(6, min(72, int(size)))
        except (TypeError, ValueError):
            return
        self.default_font_size = value
        if apply_to_current and self.current_dim:
            self.current_dim.font_size = value
            self.app.redraw()
        self._sync_dimension_ui()

    def set_font_type(self, font_type: str, apply_to_current: bool = True) -> None:
        """Задать тип ГОСТ-шрифта для размеров по умолчанию."""
        if font_type not in DIMENSION_FONT_TYPES:
            return
        self.default_font_type = font_type
        if apply_to_current and self.current_dim:
            self.current_dim.font_type = font_type
            self.app.redraw()
        self._sync_dimension_ui()

    def set_arrow_shape(self, arrow_shape: str, apply_to_current: bool = True) -> None:
        """Задать форму стрелки по умолчанию."""
        if arrow_shape not in ARROW_SHAPES:
            return
        self.default_arrow_shape = arrow_shape
        if apply_to_current and self.current_dim:
            self.current_dim.arrow_shape = arrow_shape
            self.current_dim._sync_legacy_arrow_type()
            self.app.redraw()
        self._sync_dimension_ui()

    def set_arrow_filled(self, filled: bool, apply_to_current: bool = True) -> None:
        """Включить или выключить заполнение стрелок по умолчанию."""
        self.default_arrow_filled = bool(filled)
        if apply_to_current and self.current_dim:
            self.current_dim.arrow_filled = self.default_arrow_filled
            self.current_dim._sync_legacy_arrow_type()
            self.app.redraw()
        self._sync_dimension_ui()

    def set_arrow_size(self, size: float, apply_to_current: bool = True) -> None:
        """Задать размер стрелок по умолчанию."""
        try:
            value = max(3.0, min(50.0, float(size)))
        except (TypeError, ValueError):
            return
        self.default_arrow_size = value
        if apply_to_current and self.current_dim:
            self.current_dim.arrow_size = value
            self.app.redraw()
        self._sync_dimension_ui()

    def set_text_prefix(self, prefix: str, apply_to_current: bool = True) -> None:
        """Задать текстовый префикс по умолчанию."""
        normalized_prefix = str(prefix).strip()
        if normalized_prefix == 'Ø':
            normalized_prefix = '⌀'
        self.default_text_prefix = normalized_prefix
        if apply_to_current and self.current_dim:
            self.current_dim.text_prefix = self.default_text_prefix
            self.app.redraw()
        self._sync_dimension_ui()

    def set_show_shelf(self, enabled: bool, apply_to_current: bool = True) -> None:
        """Включить или выключить полку по умолчанию."""
        self.default_show_shelf = enabled
        if apply_to_current and self.current_dim:
            self.current_dim.show_shelf = enabled
            self.app.redraw()
        self._sync_dimension_ui()

    def set_shelf_direction_override(self, direction: int, apply_to_current: bool = True) -> None:
        """Задать направление полки по умолчанию."""
        if direction not in (-1, 0, 1):
            return

        self.default_shelf_dir_override = direction
        if apply_to_current and self.current_dim:
            self.current_dim.set_shelf_direction_override(direction)
            self.app.redraw()
        self._sync_dimension_ui()

    def cycle_shelf_direction(self, apply_to_current: bool = True) -> int:
        """Переключить направление полки для новых и текущего размера."""
        current = self.default_shelf_dir_override
        next_dir = 1 if current == 0 else (-1 if current == 1 else 0)
        self.set_shelf_direction_override(next_dir, apply_to_current=apply_to_current)
        return next_dir

    def set_radial_display_mode(self, mode: str, apply_to_current: bool = True) -> None:
        """Задать оформление радиуса/диаметра по умолчанию."""
        normalized = self._normalize_radial_display_mode(mode)
        self.default_radial_display_mode = normalized
        if apply_to_current and isinstance(self.current_dim, RadialDimension):
            self.current_dim.display_mode = self._normalize_radial_display_mode(normalized)
            self.app.redraw()
        self._sync_dimension_ui()

    def set_radial_shelf_length(self, length: float, apply_to_current: bool = True) -> None:
        """Задать длину полки радиального размера."""
        try:
            value = max(10.0, float(length))
        except (TypeError, ValueError):
            return

        self.default_radial_shelf_length = value
        if apply_to_current and isinstance(self.current_dim, RadialDimension):
            self.current_dim.shelf_length = value
            self.app.redraw()
        self._sync_dimension_ui()

    def set_radial_shelf_offset(self, offset: float, apply_to_current: bool = True) -> None:
        """Задать вынос полки от окружности."""
        try:
            value = max(0.0, float(offset))
        except (TypeError, ValueError):
            return

        self.default_radial_shelf_offset = value
        if apply_to_current and isinstance(self.current_dim, RadialDimension):
            self.current_dim.shelf_offset = value
            self.app.redraw()
        self._sync_dimension_ui()

    def set_radial_line_extension(self, extension: float, apply_to_current: bool = True) -> None:
        """Задать длину продолжения линии для режима по линии."""
        try:
            value = max(10.0, float(extension))
        except (TypeError, ValueError):
            return

        self.default_radial_line_extension = value
        if apply_to_current and isinstance(self.current_dim, RadialDimension):
            self.current_dim.line_extension = value
            self.app.redraw()
        self._sync_dimension_ui()

    def set_radial_outside_offset(self, offset: float, apply_to_current: bool = True) -> None:
        """Задать внешний отступ для наружного диаметра."""
        try:
            value = max(0.0, float(offset))
        except (TypeError, ValueError):
            return

        self.default_radial_outside_offset = value
        if apply_to_current and isinstance(self.current_dim, RadialDimension):
            self.current_dim.outside_offset = value
            self.app.redraw()
        self._sync_dimension_ui()
        
    def set_mode(self, mode: str) -> None:
        self.mode = mode
        self.default_radial_display_mode = self._normalize_radial_display_mode(
            self.default_radial_display_mode
        )
        self.reset()
        
    def reset(self) -> None:
        if self.current_dim and self.current_dim in self.app.shape_manager.get_all_shapes():
            # Если мы не закончили фигуру, удаляем черновик
            self.app.shape_manager.remove_shape(self.current_dim)
        self.points.clear()
        self.lines.clear()
        self.circle_arc = None
        self.hover_circle_arc = None
        self.radial_step = 0
        self.linear_center_snap_active = False
        self.current_dim = None
        self._sync_dimension_ui()
        self.app.redraw()

    def _finish_dimension_creation(self) -> None:
        """Завершить текущую постановку размера без удаления созданной фигуры."""
        self.points.clear()
        self.lines.clear()
        self.circle_arc = None
        self.hover_circle_arc = None
        self.radial_step = 0
        self.linear_center_snap_active = False
        self.current_dim = None
        self._sync_dimension_ui()

    def _update_radial_leader_preview(self, world_x: float, world_y: float,
                                      screen_x: float, view_scale: float) -> None:
        """Обновить вынос и положение полки по курсору."""
        if not isinstance(self.current_dim, RadialDimension):
            return

        ux = math.cos(self.current_dim.angle_rad)
        uy = math.sin(self.current_dim.angle_rad)
        base_x = self.current_dim.cx + self.current_dim.radius * ux
        base_y = self.current_dim.cy + self.current_dim.radius * uy
        offset_world = max(0.0, (world_x - base_x) * ux + (world_y - base_y) * uy)
        self.current_dim.shelf_offset = offset_world * max(1e-6, view_scale)

        shelf_start_world_x = base_x + ux * offset_world
        shelf_start_world_y = base_y + uy * offset_world
        width, height = self.get_canvas_size()
        shelf_start_screen_x, _ = self.app.view_transform.world_to_screen(
            shelf_start_world_x, shelf_start_world_y, width, height
        )
        self.current_dim.set_shelf_direction_override(
            1 if screen_x >= shelf_start_screen_x else -1
        )

    def _update_radial_aligned_preview(self, world_x: float, world_y: float,
                                       view_scale: float) -> None:
        """Обновить длину продолжения линии по курсору."""
        if not isinstance(self.current_dim, RadialDimension):
            return

        ux = math.cos(self.current_dim.angle_rad)
        uy = math.sin(self.current_dim.angle_rad)
        base_x = self.current_dim.cx + self.current_dim.radius * ux
        base_y = self.current_dim.cy + self.current_dim.radius * uy
        extension_world = max(0.0, (world_x - base_x) * ux + (world_y - base_y) * uy)
        self.current_dim.line_extension = max(10.0, extension_world * max(1e-6, view_scale))

    def _update_radial_outside_preview(self, screen_x: float, screen_y: float) -> None:
        """Обновить отступ наружного диаметра по курсору."""
        if not isinstance(self.current_dim, RadialDimension):
            return

        width, height = self.get_canvas_size()
        scx, scy = self.app.view_transform.world_to_screen(
            self.current_dim.cx, self.current_dim.cy, width, height
        )
        radius_screen = self.current_dim.radius * self.app.view_transform.scale

        if abs(screen_x - scx) > abs(screen_y - scy):
            self.current_dim.outside_orientation = 'vertical'
            self.current_dim.outside_side = 1 if screen_x >= scx else -1
        else:
            self.current_dim.outside_orientation = 'horizontal'
            self.current_dim.outside_side = -1 if screen_y <= scy else 1

        if self.current_dim.outside_orientation == 'horizontal':
            distance = abs(screen_y - scy) - radius_screen
        else:
            distance = abs(screen_x - scx) - radius_screen

        self.current_dim.outside_offset = max(0.0, distance)

    def _find_circle_arc_at(self, screen_x: float, screen_y: float,
                            width: int, height: int) -> Optional[Any]:
        """Найти окружность или дугу под курсором."""
        for shape in reversed(self.app.shape_manager.get_all_shapes()):
            if isinstance(shape, (Circle, Arc)):
                dist = shape.distance_to_point(
                    screen_x, screen_y, width, height, self.app.view_transform
                )
                if dist < 10:
                    return shape
        return None

    def _draw_circle_arc_highlight(self, renderer, shape: Any,
                                   width: int, height: int, view_transform) -> None:
        """Подсветить окружность или дугу в режиме радиальных размеров."""
        color = "#ffd54f"
        line_width = 3
        dash_pattern = (8, 4)

        if isinstance(shape, Circle):
            scx, scy = view_transform.world_to_screen(shape.cx, shape.cy, width, height)
            sr = shape.radius * view_transform.scale
            renderer.canvas.create_oval(
                scx - sr, scy - sr, scx + sr, scy + sr,
                outline=color, width=line_width, dash=dash_pattern, tags="preview"
            )
        elif isinstance(shape, Arc):
            arc_points = shape.get_arc_points(48)
            screen_points = []
            for px, py in arc_points:
                sx, sy = view_transform.world_to_screen(px, py, width, height)
                screen_points.extend([sx, sy])

            if len(screen_points) >= 4:
                renderer.canvas.create_line(
                    *screen_points,
                    fill=color, width=line_width, dash=dash_pattern,
                    smooth=True, tags="preview"
                )
        
    def _find_snap_index(self, shape, snap_x: float, snap_y: float) -> Optional[int]:
        """Найти индекс snap-точки фигуры, ближайший к координатам"""
        if not shape or not hasattr(shape, 'get_snap_points'):
            return None
        snap_pts = shape.get_snap_points()
        best_idx = None
        best_d = float('inf')
        for i, (_, px, py) in enumerate(snap_pts):
            d = math.hypot(px - snap_x, py - snap_y)
            if d < best_d:
                best_d = d
                best_idx = i
        return best_idx if best_d < 1e-3 else None

    def _is_same_point(self, p1: Tuple[float, float], p2: Tuple[float, float], tol: float = 1e-6) -> bool:
        """Проверить, совпадают ли две точки."""
        return math.hypot(p1[0] - p2[0], p1[1] - p2[1]) <= tol

    def _find_line_intersection(self, seg1: Segment, seg2: Segment) -> Optional[Tuple[float, float]]:
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

    def _resolve_angular_vertex(self, seg1: Segment, seg2: Segment) -> Optional[Tuple[float, float]]:
        """Найти вершину угла: общую точку отрезков или пересечение прямых."""
        endpoints1 = [(seg1.x1, seg1.y1), (seg1.x2, seg1.y2)]
        endpoints2 = [(seg2.x1, seg2.y1), (seg2.x2, seg2.y2)]

        for p1 in endpoints1:
            for p2 in endpoints2:
                if self._is_same_point(p1, p2):
                    return p1

        return self._find_line_intersection(seg1, seg2)

    def _resolve_angular_ray_point(self, seg: Segment, click_point: Tuple[float, float],
                                   vertex: Tuple[float, float]) -> Optional[Tuple[float, float]]:
        """Определить, какой луч от вершины пользователь имел в виду."""
        p1 = (seg.x1, seg.y1)
        p2 = (seg.x2, seg.y2)
        clicked_endpoint = p1 if math.hypot(click_point[0] - p1[0], click_point[1] - p1[1]) <= \
            math.hypot(click_point[0] - p2[0], click_point[1] - p2[1]) else p2
        other_endpoint = p2 if clicked_endpoint == p1 else p1

        if self._is_same_point(clicked_endpoint, vertex):
            return other_endpoint
        return clicked_endpoint

    def _resolve_angular_ray_endpoint_index(self, seg: Segment, click_point: Tuple[float, float],
                                            vertex: Tuple[float, float]) -> Optional[int]:
        """Определить индекс конца отрезка, задающего луч углового размера."""
        ray_point = self._resolve_angular_ray_point(seg, click_point, vertex)
        if ray_point is None:
            return None
        endpoints = [(seg.x1, seg.y1), (seg.x2, seg.y2)]
        for idx, endpoint in enumerate(endpoints):
            if self._is_same_point(endpoint, ray_point):
                return idx
        return None

    def on_mouse_down(self, event: tk.Event) -> None:
        w, h = self.get_canvas_size()
        wx, wy = self.app.view_transform.screen_to_world(event.x, event.y, w, h)
        
        snap = self.app.snap_manager.find_snap_point(
            event.x, event.y, self.app.shape_manager.get_all_shapes(),
            w, h, self.app.view_transform
        )
        
        # Если привязка сработала, используем её координаты
        snap_shape = None
        snap_index = None
        if snap:
            wx, wy = snap.x, snap.y
            snap_shape = snap.shape
            if snap_shape:
                snap_index = self._find_snap_index(snap_shape, snap.x, snap.y)
            
        if self.mode == "linear":
            if len(self.points) == 0:
                self.points.append((wx, wy, 
                                    snap_shape.id if snap_shape else None, 
                                    snap_index))
            elif len(self.points) == 1:
                self.points.append((wx, wy,
                                    snap_shape.id if snap_shape else None,
                                    snap_index))
                self.current_dim = LinearDimension(
                    (self.points[0][0], self.points[0][1]), (wx, wy),
                    offset=0.0, measurement_mode=self.default_linear_mode
                )
                self._apply_defaults(self.current_dim)
                self.current_dim.base_shape_id1 = self.points[0][2]
                self.current_dim.base_point_id1 = self.points[0][3]
                self.current_dim.base_shape_id2 = self.points[1][2]
                self.current_dim.base_point_id2 = self.points[1][3]
                self.app.shape_manager.add_shape(self.current_dim)
            elif len(self.points) == 2:
                # Фиксация offset
                self.current_dim = None
                self.points.clear()
                self._sync_dimension_ui()
                
        elif self.mode in ("radius", "diameter"):
            if self.circle_arc is None:
                # Выбор окружности/дуги
                clicked_shape = self._find_circle_arc_at(event.x, event.y, w, h)
                
                if clicked_shape:
                    self.circle_arc = clicked_shape
                    self.hover_circle_arc = clicked_shape
                    cx, cy = getattr(clicked_shape, 'x', 0), getattr(clicked_shape, 'y', 0)
                    if hasattr(clicked_shape, 'cx'): cx = clicked_shape.cx
                    if hasattr(clicked_shape, 'cy'): cy = clicked_shape.cy
                    
                    self.current_dim = RadialDimension(cx, cy, clicked_shape.radius, is_diameter=(self.mode == "diameter"))
                    self._apply_defaults(self.current_dim)
                    self.current_dim.base_shape_id = clicked_shape.id
                    self.app.shape_manager.add_shape(self.current_dim)
                    self.radial_step = 1
            else:
                if not isinstance(self.current_dim, RadialDimension):
                    self._finish_dimension_creation()
                elif self.radial_step <= 1:
                    dx = wx - self.current_dim.cx
                    dy = wy - self.current_dim.cy
                    if math.hypot(dx, dy) > 1e-6:
                        self.current_dim.angle_rad = math.atan2(dy, dx)

                    if self.current_dim.display_mode in ('leader', 'aligned', 'outside'):
                        self.radial_step = 2
                    else:
                        self._finish_dimension_creation()
                else:
                    if self.current_dim.display_mode == 'leader':
                        self._update_radial_leader_preview(wx, wy, float(event.x), self.app.view_transform.scale)
                    elif self.current_dim.display_mode == 'aligned':
                        self._update_radial_aligned_preview(wx, wy, self.app.view_transform.scale)
                    else:
                        self._update_radial_outside_preview(float(event.x), float(event.y))
                    self._finish_dimension_creation()
                
        elif self.mode == "angular":
            if len(self.lines) < 2:
                clicked_shape = None
                for shape in reversed(self.app.shape_manager.get_all_shapes()):
                    if isinstance(shape, Segment):
                        dist = shape.distance_to_point(event.x, event.y, w, h, self.app.view_transform)
                        if dist < 10:
                            clicked_shape = shape
                            break
                            
                if clicked_shape:
                    self.lines.append((clicked_shape, (wx, wy)))
                    if len(self.lines) == 2:
                        (l1, click1), (l2, click2) = self.lines[0], self.lines[1]
                        vertex = self._resolve_angular_vertex(l1, l2)

                        if vertex is not None:
                            ray_p1 = self._resolve_angular_ray_point(l1, click1, vertex)
                            ray_p2 = self._resolve_angular_ray_point(l2, click2, vertex)
                            ray_idx1 = self._resolve_angular_ray_endpoint_index(l1, click1, vertex)
                            ray_idx2 = self._resolve_angular_ray_endpoint_index(l2, click2, vertex)

                            if ray_p1 is not None and ray_p2 is not None:
                                self.current_dim = AngularDimension(vertex[0], vertex[1], ray_p1, ray_p2)
                                self._apply_defaults(self.current_dim)
                                self.current_dim.base_shape_id1 = l1.id
                                self.current_dim.base_shape_id2 = l2.id
                                self.current_dim.ray_point_id1 = ray_idx1
                                self.current_dim.ray_point_id2 = ray_idx2
                                self.app.shape_manager.add_shape(self.current_dim)
            else:
                self.current_dim = None
                self.lines.clear()
                self._sync_dimension_ui()

        self.app.redraw()

    def on_mouse_move(self, event: tk.Event) -> None:
        w, h = self.get_canvas_size()
        
        # Обновляем привязку для предпросмотра (подсветка точек на экране)
        snap = self.app.snap_manager.find_snap_point(
            event.x, event.y, self.app.shape_manager.get_all_shapes(),
            w, h, self.app.view_transform
        )
        if snap:
            wx, wy = snap.x, snap.y
        else:
            wx, wy = self.app.view_transform.screen_to_world(event.x, event.y, w, h)

        if self.mode in ("radius", "diameter"):
            self.hover_circle_arc = self.circle_arc or self._find_circle_arc_at(event.x, event.y, w, h)
        else:
            self.hover_circle_arc = None
            self.linear_center_snap_active = False
        
        if self.current_dim:
            if isinstance(self.current_dim, LinearDimension):
                dx = self.current_dim.p2_x - self.current_dim.p1_x
                dy = self.current_dim.p2_y - self.current_dim.p1_y
                length = math.hypot(dx, dy)
                if length > 1e-5:
                    self.current_dim.set_offset_from_point(wx, wy)

                    vectors = self.current_dim._get_vectors()
                    if vectors is None:
                        self.linear_center_snap_active = False
                        self.app.redraw()
                        return
                    _, lx, ly, _, _ = vectors
                    dim_p1, dim_p2 = self.current_dim._get_dimension_world_points()
                    mid_x = (dim_p1[0] + dim_p2[0]) / 2.0
                    mid_y = (dim_p1[1] + dim_p2[1]) / 2.0
                    rel_x = wx - mid_x
                    rel_y = wy - mid_y
                    pos_along = rel_x * lx + rel_y * ly
                    center_snap_world = 12.0 / max(1e-6, self.app.view_transform.scale)
                    if abs(pos_along) <= center_snap_world:
                        self.current_dim.text_pos_x = 0.0
                        self.linear_center_snap_active = True
                    else:
                        self.current_dim.text_pos_x = pos_along
                        self.linear_center_snap_active = False
                
            elif isinstance(self.current_dim, RadialDimension):
                if self.radial_step <= 1:
                    dx = wx - self.current_dim.cx
                    dy = wy - self.current_dim.cy
                    if math.hypot(dx, dy) > 1e-6:
                        self.current_dim.angle_rad = math.atan2(dy, dx)
                else:
                    if self.current_dim.display_mode == 'leader':
                        self._update_radial_leader_preview(wx, wy, float(event.x), self.app.view_transform.scale)
                    elif self.current_dim.display_mode == 'aligned':
                        self._update_radial_aligned_preview(wx, wy, self.app.view_transform.scale)
                    else:
                        self._update_radial_outside_preview(float(event.x), float(event.y))
                
            elif isinstance(self.current_dim, AngularDimension):
                dist = math.hypot(wx - self.current_dim.cx, wy - self.current_dim.cy)
                self.current_dim.radius = dist
                self.current_dim.update_arc_side(wx, wy)
        
        self.app.redraw()

    def on_mouse_up(self, event: tk.Event) -> None:
        pass

    def on_right_click(self, event: tk.Event) -> bool:
        """Правый клик сбрасывает текущее построение"""
        if self.points or self.lines or self.circle_arc:
            self.reset()
            return True
        return False
        
    def on_key_press(self, event: tk.Event) -> bool:
        key = event.keysym.lower()
        if key == 'escape':
            self.reset()
            return True
        return False

    def on_activate(self) -> None:
        self.reset()
        
    def on_deactivate(self) -> None:
        self.reset()

    def get_cursor(self) -> str:
        return "crosshair"

    def draw_preview(self, renderer, width: int, height: int, view_transform) -> None:
        if self.hover_circle_arc is not None and self.mode in ("radius", "diameter"):
            self._draw_circle_arc_highlight(
                renderer, self.hover_circle_arc, width, height, view_transform
            )
        if self.linear_center_snap_active and isinstance(self.current_dim, LinearDimension):
            anchor_x, anchor_y = self.current_dim._get_text_anchor_world()
            sx, sy = view_transform.world_to_screen(anchor_x, anchor_y, width, height)
            renderer.canvas.create_rectangle(
                sx - 5, sy - 5, sx + 5, sy + 5,
                outline="#ffd54f", width=2, tags="preview"
            )
        if hasattr(self.app, 'snap_manager'):
            self.app.snap_manager.draw_snap_indicator(renderer.canvas, width, height, view_transform)
