"""Менеджер системы привязок (Object Snapping)"""
import math
from typing import List, Tuple, Optional, Any, TYPE_CHECKING
from dataclasses import dataclass
from enum import Enum, auto

if TYPE_CHECKING:
    from .grid_manager import GridManager


class SnapType(Enum):
    ENDPOINT = auto()
    MIDPOINT = auto()
    CENTER = auto()
    QUADRANT = auto()
    INTERSECTION = auto()
    PERPENDICULAR = auto()
    TANGENT = auto()
    GRID = auto()


@dataclass
class SnapPoint:
    snap_type: SnapType
    x: float
    y: float
    shape: Any = None
    priority: int = 0


class SnapManager:
    SNAP_RADIUS = 15.0
    PRIORITIES = {SnapType.ENDPOINT: 1, SnapType.MIDPOINT: 2, SnapType.CENTER: 2,
                  SnapType.INTERSECTION: 3, SnapType.QUADRANT: 4, SnapType.PERPENDICULAR: 5,
                  SnapType.TANGENT: 5, SnapType.GRID: 20}
    COLORS = {SnapType.ENDPOINT: "#00ff00", SnapType.MIDPOINT: "#00ffff", SnapType.CENTER: "#ff00ff",
              SnapType.QUADRANT: "#ffff00", SnapType.INTERSECTION: "#ff8800", SnapType.PERPENDICULAR: "#88ff00",
              SnapType.TANGENT: "#ff0088", SnapType.GRID: "#666666"}
    NAMES = {SnapType.ENDPOINT: "Конец", SnapType.MIDPOINT: "Середина", SnapType.CENTER: "Центр",
             SnapType.QUADRANT: "Квадрант", SnapType.INTERSECTION: "Пересечение",
             SnapType.PERPENDICULAR: "Перпендикуляр", SnapType.TANGENT: "Касательная",
             SnapType.GRID: "Сетка"}
    
    def __init__(self):
        self._enabled = {st: st != SnapType.GRID for st in SnapType}
        self._snap_on = True
        self._current: Optional[SnapPoint] = None
        self._grid_manager: Optional['GridManager'] = None
    
    def set_grid_manager(self, gm: 'GridManager') -> None:
        """Установить ссылку на GridManager для привязки к сетке"""
        self._grid_manager = gm
    
    def is_enabled(self) -> bool: return self._snap_on
    def set_enabled(self, v: bool): self._snap_on = v
    def toggle(self) -> bool: self._snap_on = not self._snap_on; return self._snap_on
    def is_snap_type_enabled(self, t: SnapType) -> bool: return self._enabled.get(t, False)
    def set_snap_type_enabled(self, t: SnapType, v: bool): self._enabled[t] = v
    def get_current_snap(self) -> Optional[SnapPoint]: return self._current
    def get_snap_type_label(self, t: SnapType) -> str: return self.NAMES.get(t, "")
    
    # Для обратной совместимости - делегируем в GridManager
    def set_grid_step(self, step: float):
        if self._grid_manager:
            self._grid_manager.base_step = step
    
    def get_grid_step(self) -> float:
        if self._grid_manager:
            return self._grid_manager.base_step
        return 25.0
    
    def find_snap_point(self, cx: float, cy: float, shapes: List[Any], w: int, h: int,
                        vt: Any, from_pt: Optional[Tuple[float, float]] = None) -> Optional[SnapPoint]:
        """
        Найти точку привязки.
        
        Args:
            cx, cy: Экранные координаты курсора
            shapes: Список фигур
            w, h: Размеры canvas
            vt: ViewTransform
            from_pt: Начальная точка (для перпендикуляра/касательной)
            
        Returns:
            Ближайшая точка привязки или None
        """
        if not self._snap_on:
            self._current = None
            return None
        
        # Преобразуем экранные координаты в мировые
        wx, wy = vt.screen_to_world(cx, cy, w, h)
        pts: List[SnapPoint] = []
        
        # Собираем точки привязки от фигур
        for s in shapes:
            pts.extend(self._shape_snaps(s, wx, wy, from_pt))
        
        # Точки пересечений
        if self._enabled.get(SnapType.INTERSECTION):
            for ix, iy in self._all_intersections(shapes):
                pts.append(SnapPoint(SnapType.INTERSECTION, ix, iy, priority=self.PRIORITIES[SnapType.INTERSECTION]))
        
        # Привязка к сетке через GridManager
        if self._enabled.get(SnapType.GRID) and self._grid_manager:
            gx, gy = self._grid_manager.snap_to_grid(wx, wy)
            pts.append(SnapPoint(SnapType.GRID, gx, gy, priority=self.PRIORITIES[SnapType.GRID]))
        
        # Находим ближайшую точку привязки
        best, best_d = None, float('inf')
        for p in pts:
            # Преобразуем точку привязки в экранные координаты
            sx, sy = vt.world_to_screen(p.x, p.y, w, h)
            # Расстояние в экранных пикселях
            d = math.hypot(cx - sx, cy - sy)
            # Учитываем приоритет (меньше = важнее)
            if d <= self.SNAP_RADIUS and d + p.priority * 0.1 < best_d:
                best_d = d + p.priority * 0.1
                best = p
        
        self._current = best
        return best
    
    def _shape_snaps(self, s: Any, wx: float, wy: float, from_pt) -> List[SnapPoint]:
        pts = []
        TYPE_MAP = {'endpoint': SnapType.ENDPOINT, 'midpoint': SnapType.MIDPOINT, 'center': SnapType.CENTER,
                    'quadrant': SnapType.QUADRANT, 'control': SnapType.ENDPOINT}
        
        if hasattr(s, 'get_snap_points'):
            for t, x, y in s.get_snap_points():
                st = TYPE_MAP.get(t.lower())
                if st and self._enabled.get(st):
                    pts.append(SnapPoint(st, x, y, s, self.PRIORITIES.get(st, 10)))
        
        if from_pt and self._enabled.get(SnapType.PERPENDICULAR):
            p = self._perp(s, from_pt[0], from_pt[1])
            if p: pts.append(SnapPoint(SnapType.PERPENDICULAR, p[0], p[1], s, self.PRIORITIES[SnapType.PERPENDICULAR]))
        
        if from_pt and self._enabled.get(SnapType.TANGENT):
            for tx, ty in self._tangent(s, from_pt[0], from_pt[1]):
                pts.append(SnapPoint(SnapType.TANGENT, tx, ty, s, self.PRIORITIES[SnapType.TANGENT]))
        
        return pts
    
    # === Геометрические вычисления ===
    
    def _seg_seg(self, x1, y1, x2, y2, x3, y3, x4, y4) -> Optional[Tuple[float, float]]:
        d = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
        if abs(d) < 1e-10: return None
        t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / d
        u = -((x1 - x2) * (y1 - y3) - (y1 - y2) * (x1 - x3)) / d
        return (x1 + t * (x2 - x1), y1 + t * (y2 - y1)) if 0 <= t <= 1 and 0 <= u <= 1 else None
    
    def _seg_circ(self, x1, y1, x2, y2, cx, cy, r) -> List[Tuple[float, float]]:
        dx, dy, fx, fy = x2 - x1, y2 - y1, x1 - cx, y1 - cy
        a = dx*dx + dy*dy
        if a < 1e-10: return []
        b, c = 2 * (fx*dx + fy*dy), fx*fx + fy*fy - r*r
        disc = b*b - 4*a*c
        if disc < 0: return []
        sd = math.sqrt(disc)
        return [(x1 + t*dx, y1 + t*dy) for t in [(-b - sd) / (2*a), (-b + sd) / (2*a)] if 0 <= t <= 1]
    
    def _circ_circ(self, x1, y1, r1, x2, y2, r2) -> List[Tuple[float, float]]:
        d = math.hypot(x2 - x1, y2 - y1)
        if d > r1 + r2 or d < abs(r1 - r2) or d == 0: return []
        a = (r1*r1 - r2*r2 + d*d) / (2*d)
        h2 = r1*r1 - a*a
        if h2 < 0: return []
        h = math.sqrt(h2)
        px, py = x1 + a * (x2 - x1) / d, y1 + a * (y2 - y1) / d
        if h < 0.001: return [(px, py)]
        return [(px + h * (y2 - y1) / d, py - h * (x2 - x1) / d),
                (px - h * (y2 - y1) / d, py + h * (x2 - x1) / d)]
    
    def _on_arc(self, p, arc) -> bool:
        """Return True if point angle lies on arc defined by start->end (with sign)."""
        angle = math.degrees(math.atan2(p[1] - arc.cy, p[0] - arc.cx))
        start = arc.start_angle
        extent = arc.end_angle - arc.start_angle

        # Compare using directed angular distance to correctly handle spans > 180°
        eps = 1e-6
        if extent >= 0:
            rel = (angle - start) % 360
            return rel <= extent + eps
        else:
            rel = -((start - angle) % 360)
            return rel >= extent - eps
    
    def _get_segs(self, shape) -> List[Tuple[float, float, float, float]]:
        t = type(shape).__name__
        if t == 'Rectangle':
            c = shape.get_corners()
            return [(c[i][0], c[i][1], c[(i+1)%4][0], c[(i+1)%4][1]) for i in range(4)]
        if t == 'Polygon':
            v = shape.get_vertices()
            return [(v[i][0], v[i][1], v[(i+1)%len(v)][0], v[(i+1)%len(v)][1]) for i in range(len(v))]
        if t == 'Ellipse':
            pts = [shape.get_point_on_ellipse(i * 360 / 48) for i in range(48)]
            return [(pts[i][0], pts[i][1], pts[(i+1)%48][0], pts[(i+1)%48][1]) for i in range(48)]
        if t == 'Spline':
            pts = shape.get_curve_points(12)
            return [(pts[i][0], pts[i][1], pts[i+1][0], pts[i+1][1]) for i in range(len(pts)-1)]
        return []
    
    def _all_intersections(self, shapes) -> List[Tuple[float, float]]:
        result = []
        for i, s1 in enumerate(shapes):
            for s2 in shapes[i+1:]:
                result.extend(self._intersect(s1, s2))
        # Remove duplicates
        unique = []
        for p in result:
            if not any(math.hypot(p[0]-u[0], p[1]-u[1]) < 0.01 for u in unique):
                unique.append(p)
        return unique
    
    def _intersect(self, s1, s2) -> List[Tuple[float, float]]:
        t1, t2 = type(s1).__name__, type(s2).__name__
        
        # Segment-Segment
        if t1 == 'Segment' and t2 == 'Segment':
            p = self._seg_seg(s1.x1, s1.y1, s1.x2, s1.y2, s2.x1, s2.y1, s2.x2, s2.y2)
            return [p] if p else []
        
        # Segment-Circle
        if t1 == 'Segment' and t2 == 'Circle':
            return self._seg_circ(s1.x1, s1.y1, s1.x2, s1.y2, s2.cx, s2.cy, s2.radius)
        if t1 == 'Circle' and t2 == 'Segment':
            return self._seg_circ(s2.x1, s2.y1, s2.x2, s2.y2, s1.cx, s1.cy, s1.radius)
        
        # Circle-Circle
        if t1 == 'Circle' and t2 == 'Circle':
            return self._circ_circ(s1.cx, s1.cy, s1.radius, s2.cx, s2.cy, s2.radius)
        
        # Arc with circle/arc
        if t2 == 'Arc':
            if t1 == 'Segment':
                return [p for p in self._seg_circ(s1.x1, s1.y1, s1.x2, s1.y2, s2.cx, s2.cy, s2.radius) if self._on_arc(p, s2)]
            if t1 == 'Circle':
                return [p for p in self._circ_circ(s1.cx, s1.cy, s1.radius, s2.cx, s2.cy, s2.radius) if self._on_arc(p, s2)]
            if t1 == 'Arc':
                return [p for p in self._circ_circ(s1.cx, s1.cy, s1.radius, s2.cx, s2.cy, s2.radius) if self._on_arc(p, s1) and self._on_arc(p, s2)]
        if t1 == 'Arc':
            if t2 == 'Segment':
                return [p for p in self._seg_circ(s2.x1, s2.y1, s2.x2, s2.y2, s1.cx, s1.cy, s1.radius) if self._on_arc(p, s1)]
            if t2 == 'Circle':
                return [p for p in self._circ_circ(s2.cx, s2.cy, s2.radius, s1.cx, s1.cy, s1.radius) if self._on_arc(p, s1)]
        
        # Segment with polygon-like shapes
        segs2 = self._get_segs(s2)
        if t1 == 'Segment' and segs2:
            return [p for seg in segs2 for p in ([self._seg_seg(s1.x1, s1.y1, s1.x2, s1.y2, *seg)] if self._seg_seg(s1.x1, s1.y1, s1.x2, s1.y2, *seg) else [])]
        
        segs1 = self._get_segs(s1)
        if t2 == 'Segment' and segs1:
            return [p for seg in segs1 for p in ([self._seg_seg(s2.x1, s2.y1, s2.x2, s2.y2, *seg)] if self._seg_seg(s2.x1, s2.y1, s2.x2, s2.y2, *seg) else [])]
        
        # Circle with polygon-like shapes
        if t1 == 'Circle' and segs2:
            return [p for seg in segs2 for p in self._seg_circ(*seg, s1.cx, s1.cy, s1.radius)]
        if t2 == 'Circle' and segs1:
            return [p for seg in segs1 for p in self._seg_circ(*seg, s2.cx, s2.cy, s2.radius)]
        
        # Arc with polygon-like shapes
        if t1 == 'Arc' and segs2:
            return [p for seg in segs2 for p in self._seg_circ(*seg, s1.cx, s1.cy, s1.radius) if self._on_arc(p, s1)]
        if t2 == 'Arc' and segs1:
            return [p for seg in segs1 for p in self._seg_circ(*seg, s2.cx, s2.cy, s2.radius) if self._on_arc(p, s2)]
        
        # Polygon-like with polygon-like
        if segs1 and segs2:
            return [p for seg1 in segs1 for seg2 in segs2 for p in ([self._seg_seg(*seg1, *seg2)] if self._seg_seg(*seg1, *seg2) else [])]
        
        return []
    
    # === Перпендикуляр и касательная ===
    
    def _nearest_seg(self, x1, y1, x2, y2, fx, fy) -> Tuple[float, float]:
        dx, dy = x2 - x1, y2 - y1
        len2 = dx*dx + dy*dy
        if len2 == 0: return (x1, y1)
        t = max(0, min(1, ((fx - x1) * dx + (fy - y1) * dy) / len2))
        return (x1 + t * dx, y1 + t * dy)
    
    def _perp_seg(self, x1, y1, x2, y2, fx, fy) -> Optional[Tuple[float, float]]:
        dx, dy = x2 - x1, y2 - y1
        len2 = dx*dx + dy*dy
        if len2 == 0: return None
        t = ((fx - x1) * dx + (fy - y1) * dy) / len2
        return (x1 + t * dx, y1 + t * dy) if 0 <= t <= 1 else None
    
    def _perp(self, s, fx, fy) -> Optional[Tuple[float, float]]:
        t = type(s).__name__
        
        if t == 'Segment':
            return self._perp_seg(s.x1, s.y1, s.x2, s.y2, fx, fy)
        
        if t == 'Circle':
            d = math.hypot(fx - s.cx, fy - s.cy)
            return (s.cx + s.radius * (fx - s.cx) / d, s.cy + s.radius * (fy - s.cy) / d) if d > 0.001 else None
        
        if t == 'Arc':
            d = math.hypot(fx - s.cx, fy - s.cy)
            if d < 0.001: return None
            p = (s.cx + s.radius * (fx - s.cx) / d, s.cy + s.radius * (fy - s.cy) / d)
            return p if self._on_arc(p, s) else None
        
        segs = self._get_segs(s)
        if segs:
            best, best_d = None, float('inf')
            for seg in segs:
                p = self._perp_seg(*seg, fx, fy)
                if p:
                    d = math.hypot(p[0] - fx, p[1] - fy)
                    if d < best_d: best, best_d = p, d
            return best
        
        return None
    
    def _tangent(self, s, fx, fy) -> List[Tuple[float, float]]:
        """
        Найти точки касания на фигуре для касательной от внешней точки (fx, fy).
        
        Для окружности: от внешней точки можно провести 2 касательные.
        Точки касания находятся на окружности под углом ±acos(r/d) от направления на центр.
        """
        t = type(s).__name__
        
        if t in ('Circle', 'Arc'):
            cx, cy, r = s.cx, s.cy, s.radius
            d = math.hypot(fx - cx, fy - cy)
            if d <= r + 0.001:  # Точка внутри или на окружности - касательной нет
                return []
            
            # angle = угол между линией (центр -> внешняя точка) и линией (центр -> точка касания)
            angle = math.acos(r / d)
            # base = угол направления от центра к внешней точке
            base = math.atan2(fy - cy, fx - cx)
            
            # Две точки касания: base + angle и base - angle
            pts = [
                (cx + r * math.cos(base + angle), cy + r * math.sin(base + angle)),
                (cx + r * math.cos(base - angle), cy + r * math.sin(base - angle))
            ]
            return [p for p in pts if t == 'Circle' or self._on_arc(p, s)]
        
        if t == 'Ellipse':
            pts = [s.get_point_on_ellipse(i * 5) for i in range(72)]
            result = []
            for i, p in enumerate(pts):
                pp, pn = pts[(i-1) % 72], pts[(i+1) % 72]
                tx, ty = pn[0] - pp[0], pn[1] - pp[1]
                vx, vy = fx - p[0], fy - p[1]
                tl, vl = math.hypot(tx, ty), math.hypot(vx, vy)
                if tl > 0 and vl > 0 and abs(tx*vx + ty*vy) / (tl * vl) < 0.1:
                    result.append(p)
            return result[:2]
        
        return []
    
    # === Отрисовка ===
    
    def draw_snap_indicator(self, canvas, w: int, h: int, vt) -> None:
        canvas.delete("snap_indicator")
        if not self._current: return
        
        s = self._current
        sx, sy = vt.world_to_screen(s.x, s.y, w, h)
        c, sz = self.COLORS.get(s.snap_type, "#fff"), 10
        tag = "snap_indicator"
        
        if s.snap_type == SnapType.ENDPOINT:
            canvas.create_rectangle(sx-sz, sy-sz, sx+sz, sy+sz, outline=c, width=2, tags=tag)
        elif s.snap_type == SnapType.MIDPOINT:
            canvas.create_polygon(sx, sy-sz, sx-sz, sy+sz, sx+sz, sy+sz, outline=c, fill="", width=2, tags=tag)
        elif s.snap_type == SnapType.CENTER:
            canvas.create_oval(sx-sz, sy-sz, sx+sz, sy+sz, outline=c, width=2, tags=tag)
        elif s.snap_type == SnapType.QUADRANT:
            canvas.create_polygon(sx, sy-sz, sx+sz, sy, sx, sy+sz, sx-sz, sy, outline=c, fill="", width=2, tags=tag)
        elif s.snap_type == SnapType.INTERSECTION:
            canvas.create_line(sx-sz, sy-sz, sx+sz, sy+sz, fill=c, width=2, tags=tag)
            canvas.create_line(sx-sz, sy+sz, sx+sz, sy-sz, fill=c, width=2, tags=tag)
        elif s.snap_type == SnapType.PERPENDICULAR:
            canvas.create_line(sx-sz, sy+sz, sx-sz, sy-sz, fill=c, width=2, tags=tag)
            canvas.create_line(sx-sz, sy, sx+sz, sy, fill=c, width=2, tags=tag)
        elif s.snap_type == SnapType.TANGENT:
            canvas.create_oval(sx-5, sy-5, sx+5, sy+5, outline=c, width=2, tags=tag)
            canvas.create_line(sx-sz, sy+sz, sx+sz, sy-sz, fill=c, width=2, tags=tag)
        elif s.snap_type == SnapType.GRID:
            # Маленький крестик для сетки
            canvas.create_line(sx-4, sy, sx+4, sy, fill=c, width=2, tags=tag)
            canvas.create_line(sx, sy-4, sx, sy+4, fill=c, width=2, tags=tag)
        else:
            canvas.create_oval(sx-sz, sy-sz, sx+sz, sy+sz, outline=c, width=2, tags=tag)
        
        canvas.create_text(sx+sz+5, sy-sz-5, text=self.NAMES.get(s.snap_type, ""), fill=c, anchor="sw", font=("Arial", 9), tags=tag)
