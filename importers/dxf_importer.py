import math
import re
from typing import List, Any
import ezdxf

from shapes import Point, Segment, Circle, Arc, Ellipse, Spline

class DxfImporter:
    """Класс для импорта фигур из формата DXF через ezdxf"""
    
    def __init__(self):
        self.shapes = []
        
    def import_file(self, filename: str) -> List[Any]:
        self.shapes = []
        
        try:
            doc = ezdxf.readfile(filename)
            msp = doc.modelspace()
            
            # Разворачиваем блоки (INSERT -> базовые примитивы)
            while True:
                inserts = msp.query('INSERT')
                if not inserts:
                    break
                for insert in inserts:
                    insert.explode()
                    
            for entity in msp:
                layer_name, style_name, color_hex = self._get_entity_style(entity, doc)
                if layer_name.lower() in ("sheet_border", "defpoints"):
                    continue
                    
                self._create_shape_from_entity(entity, layer_name, style_name, color_hex)
                
            print(f"DXF успешно импортирован. Версия: {doc.dxfversion}")
            print(f"Загружено примитивов: {len(self.shapes)}")
            
            return self.shapes
        except Exception as e:
            print(f"Error importing DXF: {e}")
            return []

    def _rgb_to_hex(self, rgb):
        return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"

    def _decode_autocad_text(self, text):
        if not isinstance(text, str):
            return text
        return re.sub(r'\\U\+([0-9A-Fa-f]{4})', lambda m: chr(int(m.group(1), 16)), text)

    def _get_entity_style(self, entity, doc):
        """Определяем слой, стиль линии (в терминологии программы) и цвет (в HEX)"""
        
        # 1. СЛОЙ
        raw_layer = entity.dxf.layer if entity.dxf.hasattr('layer') else '0'
        layer_name = self._decode_autocad_text(raw_layer)
            
        # 2. ТИП ЛИНИИ -> СТИЛЬ
        dxf_linetype = entity.dxf.linetype if entity.dxf.hasattr('linetype') else 'ByLayer'
        if dxf_linetype.upper() == 'BYLAYER':
            try:
                layer_obj = doc.layers.get(raw_layer)
                dxf_linetype = layer_obj.dxf.linetype
            except Exception:
                dxf_linetype = 'Continuous'
                
        base_linetype = dxf_linetype.upper().split('_')[0]
        
        DXF_TO_STYLE = {
            'CONTINUOUS': 'Сплошная основная',
            'THIN': 'Сплошная тонкая',
            'WAVES': 'Сплошная волнистая',
            'ZIGZAG': 'Сплошная тонкая с изломами',
            'HIDDEN': 'Штриховая',
            'CENTER2': 'Штрихпунктирная утолщенная',
            'CENTER': 'Штрихпунктирная тонкая',
            'PHANTOM': 'Штрихпунктирная с двумя точками'
        }
        style_name = DXF_TO_STYLE.get(base_linetype, 'Сплошная основная')
        
        # Если Continuous — определяем толщину (основная или тонкая)
        if style_name == 'Сплошная основная':
            lineweight = entity.dxf.lineweight if entity.dxf.hasattr('lineweight') else -1
            if lineweight == -1: # ByLayer
                try:
                    layer_obj = doc.layers.get(raw_layer)
                    lineweight = layer_obj.dxf.lineweight if layer_obj.dxf.hasattr('lineweight') else -3
                except Exception:
                    lineweight = -3
            
            # Если толщина задана и она меньше 0.6мм (60 в ezdxf), считаем линию тонкой
            if 0 <= lineweight < 60:
                style_name = 'Сплошная тонкая'
                
        # В fallback (если T-FLEX пишет тип линии прямо в имя слоя)
        if layer_name in DXF_TO_STYLE.values() and base_linetype == 'CONTINUOUS':
            style_name = layer_name
        elif base_linetype == 'CONTINUOUS':
            layer_style_name = layer_name.replace("_", " ")
            if layer_style_name in DXF_TO_STYLE.values():
                style_name = layer_style_name
            
        # 3. ЦВЕТ
        rgb = (255, 255, 255)
        color_index = entity.dxf.color if entity.dxf.hasattr('color') else 256
        
        if entity.dxf.hasattr('true_color'):
            rgb = ezdxf.colors.int2rgb(entity.dxf.true_color)
        elif color_index == 256: # ByLayer
            try:
                layer_obj = doc.layers.get(raw_layer)
                if layer_obj.dxf.hasattr('true_color'):
                    rgb = ezdxf.colors.int2rgb(layer_obj.dxf.true_color)
                else:
                    rgb = ezdxf.colors.aci2rgb(abs(layer_obj.color))
            except Exception:
                pass
        elif color_index != 0:
            rgb = ezdxf.colors.aci2rgb(color_index)
            
        color_hex = self._rgb_to_hex(rgb)
        return layer_name, style_name, color_hex

    def _create_shape_from_entity(self, entity, layer_name, style_name, color_hex):
        etype = entity.dxftype()
        shapes_to_add = []
        
        if etype == 'LINE':
            s = Segment(entity.dxf.start.x, entity.dxf.start.y, entity.dxf.end.x, entity.dxf.end.y)
            shapes_to_add.append(s)
            
        elif etype == 'POINT':
            s = Point(entity.dxf.location.x, entity.dxf.location.y)
            shapes_to_add.append(s)
            
        elif etype == 'CIRCLE':
            s = Circle(entity.dxf.center.x, entity.dxf.center.y, entity.dxf.radius)
            shapes_to_add.append(s)
            
        elif etype == 'ARC':
            s = Arc(
                entity.dxf.center.x, entity.dxf.center.y, entity.dxf.radius,
                entity.dxf.start_angle,
                entity.dxf.end_angle
            )
            shapes_to_add.append(s)
            
        elif etype == 'ELLIPSE':
            center = (entity.dxf.center.x, entity.dxf.center.y)
            major_axis = entity.dxf.major_axis
            ratio = entity.dxf.ratio
            
            a_x = center[0] + major_axis[0]
            a_y = center[1] + major_axis[1]
            
            major_len = math.hypot(major_axis[0], major_axis[1])
            minor_len = major_len * ratio
            
            if major_len > 1e-9:
                nx, ny = major_axis[0] / major_len, major_axis[1] / major_len
            else:
                nx, ny = 1.0, 0.0
                
            extrusion = getattr(entity.dxf, 'extrusion', (0,0,1))
            if extrusion[2] < 0:
                ox, oy = ny, -nx
            else:
                ox, oy = -ny, nx
                
            b_x = center[0] + ox * minor_len
            b_y = center[1] + oy * minor_len
            
            s = Ellipse.from_center_and_axes(center[0], center[1], a_x, a_y, b_x, b_y)
            shapes_to_add.append(s)
            
        elif etype in ('LWPOLYLINE', 'POLYLINE'):
            points = []
            if etype == 'POLYLINE':
                for v in entity.vertices: points.append((v.dxf.location.x, v.dxf.location.y))
            else:
                with entity.points() as pts:
                    for p in pts: points.append((p[0], p[1]))
            
            if not points:
                return
                
            is_procedural = any(x in style_name.lower() for x in ['волнист', 'излом', 'wavy', 'broken'])
            is_closed = False
            try:
                is_closed = bool(entity.closed)
            except Exception:
                if len(points) > 2:
                    is_closed = math.hypot(points[0][0]-points[-1][0], points[0][1]-points[-1][1]) < 1e-5

            ellipse_shape = None
            reconstructed_shape = None
            if is_closed and len(points) >= 32:
                reconstructed_shape = self._try_create_circle_from_polyline(points)
                if reconstructed_shape is None:
                    reconstructed_shape = self._try_create_ellipse_from_polyline(points)
            elif not is_closed and not is_procedural and len(points) >= 12:
                reconstructed_shape = self._try_create_arc_from_polyline(points)
            if reconstructed_shape is not None:
                shapes_to_add.append(reconstructed_shape)
            
            # Оптимизация 1: Схлопываем процедурные линии (волнистая/с изломами) в единый отрезок
            elif is_procedural and len(points) > 2:
                if is_closed:
                    if len(points) > 20:
                        step = max(1, len(points) // 20)
                        decimated = points[::step]
                        if decimated[-1] != points[-1]:
                            decimated.append(points[-1])
                        s = Spline(decimated)
                    else:
                        s = Spline(points)
                    shapes_to_add.append(s)
                else:
                    s = Segment(points[0][0], points[0][1], points[-1][0], points[-1][1])
                    shapes_to_add.append(s)
            
            elif len(points) > 20:
                # Оптимизация 2: Децимация обычных сплайнов/тяжелых полилиний
                # Берем каждую N-ую точку, чтобы не перегружать рендерер
                step = max(1, len(points) // 20)  # максимум ~20 опорных точек
                decimated = points[::step]
                if decimated[-1] != points[-1]:
                    decimated.append(points[-1])
                    
                s = Spline(decimated)
                shapes_to_add.append(s)
                
            elif len(points) > 2 and math.hypot(points[0][0]-points[-1][0], points[0][1]-points[-1][1]) < 1e-5:
                # Замкнутый полигон
                for i in range(len(points) - 1):
                    shapes_to_add.append(Segment(points[i][0], points[i][1], points[i+1][0], points[i+1][1]))
            else:
                # Раскладываем виртуальные примитивы (чтобы поддержать bulge дуги в LWPOLYLINE)
                for v_ent in entity.virtual_entities():
                    if v_ent.dxftype() == 'LINE':
                        shapes_to_add.append(Segment(v_ent.dxf.start.x, v_ent.dxf.start.y, v_ent.dxf.end.x, v_ent.dxf.end.y))
                    elif v_ent.dxftype() == 'ARC':
                        shapes_to_add.append(Arc(
                            v_ent.dxf.center.x, v_ent.dxf.center.y, v_ent.dxf.radius,
                            v_ent.dxf.start_angle,
                            v_ent.dxf.end_angle
                        ))

        elif etype == 'SPLINE':
            pts = []
            if hasattr(entity, 'control_points') and entity.control_points:
                pts = [(p[0], p[1]) for p in entity.control_points]
            elif hasattr(entity, 'fit_points') and entity.fit_points:
                pts = [(p[0], p[1]) for p in entity.fit_points]
                
            if pts:
                is_procedural = any(x in style_name.lower() for x in ['волнист', 'излом', 'wavy', 'broken'])
                
                if is_procedural and len(pts) > 2:
                    s = Segment(pts[0][0], pts[0][1], pts[-1][0], pts[-1][1])
                    shapes_to_add.append(s)
                else:
                    if len(pts) > 20:
                        step = max(1, len(pts) // 20)
                        decimated = pts[::step]
                        if decimated[-1] != pts[-1]:
                            decimated.append(pts[-1])
                        pts = decimated
                        
                    s = Spline(pts)
                    shapes_to_add.append(s)
                
        # Настраиваем свойства для всех сгенерированных фигур
        for shape in shapes_to_add:
            shape.color = color_hex
            
            # Раньше мы сбрасывали стиль на основную линию:
            # is_procedural = any(x in style_name.lower() for x in ['волнист', 'излом', 'wavy', 'broken'])
            # if is_procedural and etype in ('LWPOLYLINE', 'SPLINE'):
            #     shape.line_style_name = 'Сплошная основная'
            
            # Теперь мы оставляем честный стиль, так как схлопнули точки в 1 отрезок!
            shape.line_style_name = style_name
            shape.layer_name = layer_name
            self.shapes.append(shape)

    def _try_create_ellipse_from_polyline(self, points):
        """Попытаться восстановить эллипс из плотной замкнутой полилинии."""
        if len(points) < 16:
            return None

        normalized_points = [(float(x), float(y)) for x, y in points]
        count = len(normalized_points)

        cx = sum(x for x, _ in normalized_points) / count
        cy = sum(y for _, y in normalized_points) / count

        centered = [(x - cx, y - cy) for x, y in normalized_points]
        xx = sum(x * x for x, _ in centered) / count
        yy = sum(y * y for _, y in centered) / count
        xy = sum(x * y for x, y in centered) / count

        angle = 0.5 * math.atan2(2.0 * xy, xx - yy)
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)

        local_points = [
            (x * cos_a + y * sin_a, -x * sin_a + y * cos_a)
            for x, y in centered
        ]

        min_x = min(x for x, _ in local_points)
        max_x = max(x for x, _ in local_points)
        min_y = min(y for _, y in local_points)
        max_y = max(y for _, y in local_points)

        local_cx = (min_x + max_x) / 2.0
        local_cy = (min_y + max_y) / 2.0

        world_dx = local_cx * cos_a - local_cy * sin_a
        world_dy = local_cx * sin_a + local_cy * cos_a
        cx += world_dx
        cy += world_dy

        refined_points = []
        for x, y in normalized_points:
            dx = x - cx
            dy = y - cy
            refined_points.append((
                dx * cos_a + dy * sin_a,
                -dx * sin_a + dy * cos_a
            ))

        rx = max(abs(x) for x, _ in refined_points)
        ry = max(abs(y) for _, y in refined_points)
        if rx <= 1e-6 or ry <= 1e-6:
            return None

        residuals = [
            abs((x / rx) ** 2 + (y / ry) ** 2 - 1.0)
            for x, y in refined_points
        ]
        mean_residual = sum(residuals) / len(residuals)
        max_residual = max(residuals)

        if mean_residual > 0.03 or max_residual > 0.12:
            return None

        return Ellipse(cx, cy, rx, ry, math.degrees(angle))

    def _try_create_circle_from_polyline(self, points):
        """Попытаться восстановить окружность из плотной замкнутой полилинии."""
        if len(points) < 16:
            return None

        normalized_points = [(float(x), float(y)) for x, y in points]
        count = len(normalized_points)

        cx = sum(x for x, _ in normalized_points) / count
        cy = sum(y for _, y in normalized_points) / count

        radii = [math.hypot(x - cx, y - cy) for x, y in normalized_points]
        mean_radius = sum(radii) / len(radii)
        if mean_radius <= 1e-6:
            return None

        rel_errors = [abs(radius - mean_radius) / mean_radius for radius in radii]
        mean_rel_error = sum(rel_errors) / len(rel_errors)
        max_rel_error = max(rel_errors)

        if mean_rel_error > 0.06 or max_rel_error > 0.16:
            return None

        return Circle(cx, cy, mean_radius)

    def _try_create_arc_from_polyline(self, points):
        """Попытаться восстановить дугу из плотной незамкнутой полилинии."""
        if len(points) < 8:
            return None

        start = points[0]
        middle = points[len(points) // 2]
        end = points[-1]

        candidate = Arc.from_three_points(
            start[0], start[1],
            end[0], end[1],
            middle[0], middle[1]
        )
        if candidate is None:
            return None

        radii = [
            math.hypot(px - candidate.cx, py - candidate.cy)
            for px, py in points
        ]
        mean_radius = sum(radii) / len(radii)
        if mean_radius <= 1e-6:
            return None

        rel_errors = [abs(radius - mean_radius) / mean_radius for radius in radii]
        if (sum(rel_errors) / len(rel_errors)) > 0.03 or max(rel_errors) > 0.08:
            return None

        start_point = candidate.get_start_point()
        end_point = candidate.get_end_point()
        start_error = math.hypot(start_point[0] - start[0], start_point[1] - start[1])
        end_error = math.hypot(end_point[0] - end[0], end_point[1] - end[1])
        if start_error > mean_radius * 0.05 or end_error > mean_radius * 0.05:
            return None

        if abs(candidate._get_extent()) < 1.0:
            return None

        return candidate
