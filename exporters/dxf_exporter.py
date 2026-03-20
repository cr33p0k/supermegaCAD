"""
Модуль для экспорта в формат DXF
"""
import math
from typing import List, Any, Dict, Optional, IO
from datetime import datetime


class DxfExporter:
    """Класс для экспорта фигур в формат DXF (AutoCAD 2000/R15)"""
    
    def __init__(self):
        self.handle_seed = 0x10
        self.filename = ""
        self.shapes: List[Any] = []
        self.styles: List[Any] = []
        self.f: Optional[IO] = None
        self.ext_min = (0.0, 0.0)
        self.ext_max = (100.0, 100.0)
        self.margin = 20.0
        
        # Хранение важных handles
        self.handles = {
            "0": "0", # Not used really
            "BLOCK_RECORD_TABLE": "1", # Reserved
            "LAYER_TABLE": "2",
            "STYLE_TABLE": "3",
            "LTYPE_TABLE": "5",
            "VIEW_TABLE": "6",
            "UCS_TABLE": "7",
            "VPORT_TABLE": "8",
            "APPID_TABLE": "9",
            "DIMSTYLE_TABLE": "A",
            
            "ACAD_GROUP": None, # Will affect later
            "T_MODEL_SPACE": None, # Block Record handle for ModelSpace
            "T_PAPER_SPACE": None, # Block Record handle for PaperSpace
            "B_MODEL_SPACE": None, # Block handle
            "B_PAPER_SPACE": None, # Block handle
        }
        
    def _next_handle(self) -> str:
        """Генерация следующего уникального handle"""
        h = f"{self.handle_seed:X}"
        self.handle_seed += 1
        return h

    def export(self, filename: str, shapes: List[Any], styles: List[Any], margin: float = 20.0) -> None:
        """
        Экспорт списка фигур в DXF файл
        """
        self.filename = filename
        self.shapes = shapes
        self.styles = styles
        self.margin = margin
        
        # Reset seed to safe start (after reserved 0-F)
        self.handle_seed = 0x20
        
        # Предварительная генерация handles для критических структур
        self.handles["T_MODEL_SPACE"] = self._next_handle()
        self.handles["T_PAPER_SPACE"] = self._next_handle()
        self.handles["B_MODEL_SPACE"] = self._next_handle()
        self.handles["B_PAPER_SPACE"] = self._next_handle()
        self.handles["DICTIONARY_ROOT"] = self._next_handle()
        self.handles["ACAD_GROUP"] = self._next_handle()
        
        # Вычисление границ
        min_x, min_y, max_x, max_y = 0.0, 0.0, 100.0, 100.0
        if self.shapes:
            try:
                bounds_list = [s.get_bounds() for s in self.shapes]
                min_x = min(b[0] for b in bounds_list)
                min_y = min(b[1] for b in bounds_list)
                max_x = max(b[2] for b in bounds_list)
                max_y = max(b[3] for b in bounds_list)
            except Exception:
                pass # Default bounds if error
                
        # Apply margin
        self.ext_min = (min_x - margin, min_y - margin)
        self.ext_max = (max_x + margin, max_y + margin)
        
        with open(filename, 'w', encoding='cp1251') as f:
            self.f = f
            
            # 1. Header Section
            self._write_header()
            
            # 2. Classes Section
            self._write_classes()
            
            # 3. Tables Section
            self._write_tables()
            
            # 4. Blocks Section
            self._write_blocks()
            
            # 5. Entities Section
            self._write_entities()
            
            # 6. Objects Section
            self._write_objects()
            
            # 7. EOF
            self._write_pair(0, "EOF")

    def _write_pair(self, code: int, value: Any) -> None:
        """Запись пары код-значение"""
        if (10 <= code <= 59) or (140 <= code <= 147) or code in [210, 220, 230]:
            try:
                self.f.write(f"{code}\n{float(value):.6f}\n")
            except (ValueError, TypeError):
                self.f.write(f"{code}\n{value}\n")
        else:
            self.f.write(f"{code}\n{value}\n")

    def _write_header(self) -> None:
        """Запись секции HEADER"""
        self._write_pair(0, "SECTION")
        self._write_pair(2, "HEADER")
        
        self._write_pair(9, "$ACADVER")
        self._write_pair(1, "AC1015")
        
        self._write_pair(9, "$DWGCODEPAGE")
        self._write_pair(3, "ANSI_1251")
        
        self._write_pair(9, "$INSUNITS")
        self._write_pair(70, 4) 
        
        self._write_pair(9, "$HANDSEED")
        self._write_pair(5, "FFFF") 
        
        # Границы чертежа с учетом отступа
        self._write_pair(9, "$EXTMIN")
        self._write_pair(10, self.ext_min[0])
        self._write_pair(20, self.ext_min[1])
        self._write_pair(30, 0.0)
        
        self._write_pair(9, "$EXTMAX")
        self._write_pair(10, self.ext_max[0])
        self._write_pair(20, self.ext_max[1])
        self._write_pair(30, 0.0)
        
        # Лимиты чертежа (размер "листа")
        self._write_pair(9, "$LIMMIN")
        self._write_pair(10, self.ext_min[0])
        self._write_pair(20, self.ext_min[1])
        
        self._write_pair(9, "$LIMMAX")
        self._write_pair(10, self.ext_max[0])
        self._write_pair(20, self.ext_max[1])
        
        # Масштаб типов линий
        self._write_pair(9, "$LTSCALE")
        self._write_pair(40, 1.0)
        self._write_pair(9, "$CELTSCALE")
        self._write_pair(40, 1.0)

        self._write_pair(0, "ENDSEC")

    def _write_classes(self) -> None:
        self._write_pair(0, "SECTION")
        self._write_pair(2, "CLASSES")
        self._write_pair(0, "ENDSEC")

    def _write_tables(self) -> None:
        """Запись таблиц"""
        self._write_pair(0, "SECTION")
        self._write_pair(2, "TABLES")
        
        self._write_table_vport()
        self._write_table_ltype()
        self._write_table_layer()
        self._write_table_style()
        self._write_table_view()
        self._write_table_ucs()
        self._write_table_appid()
        self._write_table_dimstyle()
        self._write_table_block_record() # Mandatory
        
        self._write_pair(0, "ENDSEC")
        
    def _write_table_head(self, name: str, handle: str, count: int = 0):
        self._write_pair(0, "TABLE")
        self._write_pair(2, name)
        self._write_pair(5, handle)
        self._write_pair(330, 0)
        self._write_pair(100, "AcDbSymbolTable")
        self._write_pair(70, count)

    def _write_table_vport(self):
        self._write_table_head("VPORT", self.handles["VPORT_TABLE"])
        
        # Active VPORT *Active
        h = self._next_handle()
        self._write_pair(0, "VPORT")
        self._write_pair(5, h)
        self._write_pair(330, self.handles["VPORT_TABLE"])
        self._write_pair(100, "AcDbSymbolTableRecord")
        self._write_pair(100, "AcDbViewportTableRecord")
        self._write_pair(2, "*Active")
        self._write_pair(70, 0)
        
        # Center point (view center)
        cx = (self.ext_min[0] + self.ext_max[0]) / 2.0
        cy = (self.ext_min[1] + self.ext_max[1]) / 2.0
        self._write_pair(10, cx)
        self._write_pair(20, cy)
        
        self._write_pair(11, 1.0)
        self._write_pair(21, 1.0)
        self._write_pair(12, 0.0) 
        self._write_pair(22, 0.0)
        
        # View Height
        height = self.ext_max[1] - self.ext_min[1]
        self._write_pair(40, height if height > 0 else 100.0) 
        
        self._write_pair(41, 1.0) 
        self._write_pair(79, 0) 
        self._write_pair(146, 0.0) 
        
        self._write_pair(0, "ENDTAB")

    def _get_ltype_pattern(self, style) -> List[float]:
        """Преобразование параметров стиля в паттерн DXF (штрихи > 0, пробелы < 0)"""
        lt = style.line_type
        dl, gl, dot = style.dash_length, style.gap_length, style.dot_length
        
        if lt == 'dashed':
            return [dl, -gl]
        elif lt == 'dashdot':
            return [dl, -gl, dot, -gl]
        elif lt == 'dashdotdot':
            return [dl, -gl, dot, -gl, dot, -gl]
        return []

    def _write_table_ltype(self):
        self._write_table_head("LTYPE", self.handles["LTYPE_TABLE"])
        
        # 1. Обязательные стандартные типы
        base_ltypes = [
            ("ByBlock", "", []), 
            ("ByLayer", "", []), 
            ("Continuous", "Solid line", [])
        ]
        
        # 2. Генерация типов из стилей приложения
        style_ltypes = []
        for style in self.styles:
            if style.line_type in ['solid', 'wavy', 'broken']:
                continue
                
            ltype_name = f"LT_{self._sanitize_name(style.name)}"
            pattern = self._get_ltype_pattern(style)
            desc = f"Pattern: {style.line_type}"
            style_ltypes.append((ltype_name, desc, pattern))
            
        for name, desc, pat in base_ltypes + style_ltypes:
            h = self._next_handle()
            self._write_pair(0, "LTYPE")
            self._write_pair(5, h)
            self._write_pair(330, self.handles["LTYPE_TABLE"])
            self._write_pair(100, "AcDbSymbolTableRecord")
            self._write_pair(100, "AcDbLinetypeTableRecord")
            self._write_pair(2, name)
            self._write_pair(70, 0)
            self._write_pair(3, desc)
            self._write_pair(72, 65) # Alignment code 'A'
            
            length = sum(abs(x) for x in pat)
            self._write_pair(73, len(pat))
            self._write_pair(40, length)
            
            for val in pat:
                self._write_pair(49, val)
                self._write_pair(74, 0)
        
        self._write_pair(0, "ENDTAB")

    def _write_table_layer(self):
        self._write_table_head("LAYER", self.handles["LAYER_TABLE"])
        
        # 0 Layer
        h = self._next_handle()
        self._write_pair(0, "LAYER")
        self._write_pair(5, h)
        self._write_pair(330, self.handles["LAYER_TABLE"])
        self._write_pair(100, "AcDbSymbolTableRecord")
        self._write_pair(100, "AcDbLayerTableRecord")
        self._write_pair(2, "0")
        self._write_pair(70, 0)
        self._write_pair(62, 7)
        self._write_pair(6, "Continuous")
        self._write_pair(390, "F")
        
        for style in self.styles:
            safe_name = self._sanitize_name(style.name)
            if safe_name == "0": continue
            
            # Определяем имя типа линии для этого слоя
            if style.line_type in ['solid', 'wavy', 'broken']:
                ltype = "Continuous"
            else:
                ltype = f"LT_{safe_name}"
            
            h = self._next_handle()
            self._write_pair(0, "LAYER")
            self._write_pair(5, h)
            self._write_pair(330, self.handles["LAYER_TABLE"])
            self._write_pair(100, "AcDbSymbolTableRecord")
            self._write_pair(100, "AcDbLayerTableRecord")
            self._write_pair(2, safe_name)
            self._write_pair(70, 0)
            self._write_pair(62, 7)
            self._write_pair(6, ltype)
            self._write_pair(390, "F")

        # Sheet_Border Layer
        h = self._next_handle()
        self._write_pair(0, "LAYER")
        self._write_pair(5, h)
        self._write_pair(330, self.handles["LAYER_TABLE"])
        self._write_pair(100, "AcDbSymbolTableRecord")
        self._write_pair(100, "AcDbLayerTableRecord")
        self._write_pair(2, "Sheet_Border")
        self._write_pair(70, 0)
        self._write_pair(62, 8) # Grayish
        self._write_pair(6, "Continuous")
        self._write_pair(390, "F")

        self._write_pair(0, "ENDTAB")

    def _write_table_style(self):
        self._write_table_head("STYLE", self.handles["STYLE_TABLE"])
        
        h = self._next_handle()
        self._write_pair(0, "STYLE")
        self._write_pair(5, h)
        self._write_pair(330, self.handles["STYLE_TABLE"])
        self._write_pair(100, "AcDbSymbolTableRecord")
        self._write_pair(100, "AcDbTextStyleTableRecord")
        self._write_pair(2, "Standard")
        self._write_pair(70, 0)
        self._write_pair(40, 0.0)
        self._write_pair(41, 1.0)
        self._write_pair(50, 0.0)
        self._write_pair(71, 0)
        self._write_pair(42, 2.5)
        self._write_pair(3, "txt")
        self._write_pair(4, "")
        
        self._write_pair(0, "ENDTAB")

    def _write_table_view(self):
        self._write_table_head("VIEW", self.handles["VIEW_TABLE"])
        self._write_pair(0, "ENDTAB")

    def _write_table_ucs(self):
        self._write_table_head("UCS", self.handles["UCS_TABLE"])
        self._write_pair(0, "ENDTAB")

    def _write_table_appid(self):
        self._write_table_head("APPID", self.handles["APPID_TABLE"])
        
        h = self._next_handle()
        self._write_pair(0, "APPID")
        self._write_pair(5, h)
        self._write_pair(330, self.handles["APPID_TABLE"])
        self._write_pair(100, "AcDbSymbolTableRecord")
        self._write_pair(100, "AcDbRegAppTableRecord")
        self._write_pair(2, "ACAD")
        self._write_pair(70, 0)
        
        self._write_pair(0, "ENDTAB")

    def _write_table_dimstyle(self):
        self._write_table_head("DIMSTYLE", self.handles["DIMSTYLE_TABLE"])
        
        h = self._next_handle()
        self._write_pair(0, "DIMSTYLE")
        self._write_pair(5, h)
        self._write_pair(330, self.handles["DIMSTYLE_TABLE"])
        self._write_pair(100, "AcDbSymbolTableRecord")
        self._write_pair(100, "AcDbDimStyleTableRecord")
        self._write_pair(2, "Standard")
        self._write_pair(70, 0)
        self._write_pair(3, "")
        self._write_pair(4, "")
        self._write_pair(5, "")
        self._write_pair(6, "")
        self._write_pair(7, "")
        self._write_pair(40, 1.0)
        self._write_pair(41, 2.5)
        self._write_pair(42, 0.625)
        self._write_pair(43, 3.75)
        self._write_pair(44, 1.25)
        self._write_pair(141, 2.5)
        self._write_pair(143, 0.03937007874016)
        
        self._write_pair(0, "ENDTAB")

    def _write_table_block_record(self):
        self._write_table_head("BLOCK_RECORD", "1") # Handle 1 is standard
        
        # Model Space Record
        self._write_pair(0, "BLOCK_RECORD")
        self._write_pair(5, self.handles["T_MODEL_SPACE"])
        self._write_pair(330, "1")
        self._write_pair(100, "AcDbSymbolTableRecord")
        self._write_pair(100, "AcDbBlockTableRecord")
        self._write_pair(2, "*Model_Space")
        self._write_pair(340, "22") # Layout handle (placeholder)
        
        # Paper Space Record
        self._write_pair(0, "BLOCK_RECORD")
        self._write_pair(5, self.handles["T_PAPER_SPACE"])
        self._write_pair(330, "1")
        self._write_pair(100, "AcDbSymbolTableRecord")
        self._write_pair(100, "AcDbBlockTableRecord")
        self._write_pair(2, "*Paper_Space")
        self._write_pair(340, "22") # Layout handle

        self._write_pair(0, "ENDTAB")

    def _write_blocks(self):
        self._write_pair(0, "SECTION")
        self._write_pair(2, "BLOCKS")
        
        # Model Space Block
        self._write_pair(0, "BLOCK")
        self._write_pair(5, self.handles["B_MODEL_SPACE"])
        self._write_pair(330, self.handles["T_MODEL_SPACE"])
        self._write_pair(100, "AcDbEntity")
        self._write_pair(67, 0)
        self._write_pair(8, "0")
        self._write_pair(100, "AcDbBlockBegin")
        self._write_pair(2, "*Model_Space")
        self._write_pair(70, 0)
        self._write_pair(10, 0.0)
        self._write_pair(20, 0.0)
        self._write_pair(30, 0.0)
        self._write_pair(3, "")
        self._write_pair(1, "")
        
        self._write_pair(0, "ENDBLK")
        self._write_pair(5, self._next_handle())
        self._write_pair(330, self.handles["T_MODEL_SPACE"])
        self._write_pair(100, "AcDbEntity")
        self._write_pair(67, 0)
        self._write_pair(8, "0")
        self._write_pair(100, "AcDbBlockEnd")
        
        # Paper Space Block
        self._write_pair(0, "BLOCK")
        self._write_pair(5, self.handles["B_PAPER_SPACE"])
        self._write_pair(330, self.handles["T_PAPER_SPACE"])
        self._write_pair(100, "AcDbEntity")
        self._write_pair(67, 1) # Paper space
        self._write_pair(8, "0")
        self._write_pair(100, "AcDbBlockBegin")
        self._write_pair(2, "*Paper_Space")
        self._write_pair(70, 0)
        self._write_pair(10, 0.0)
        self._write_pair(20, 0.0)
        self._write_pair(30, 0.0)
        self._write_pair(3, "")
        self._write_pair(1, "")
        
        self._write_pair(0, "ENDBLK")
        self._write_pair(5, self._next_handle())
        self._write_pair(330, self.handles["T_PAPER_SPACE"])
        self._write_pair(100, "AcDbEntity")
        self._write_pair(67, 1)
        self._write_pair(8, "0")
        self._write_pair(100, "AcDbBlockEnd")
        
        self._write_pair(0, "ENDSEC")

    def _write_entities(self):
        self._write_pair(0, "SECTION")
        self._write_pair(2, "ENTITIES")
        
        for shape in self.shapes:
            try:
                self._write_entity(shape)
            except Exception as e:
                print(f"Error exporting shape {shape}: {e}")
                
        # Draw physical boundary for sheet (to enforce margin in tools like T-FLEX)
        self._write_pair(0, "LWPOLYLINE")
        self._write_pair(5, self._next_handle())
        
        self._write_pair(330, self.handles["T_MODEL_SPACE"])
        self._write_pair(100, "AcDbEntity")
        self._write_pair(8, "Sheet_Border") # Special layer
        self._write_pair(62, 8) # Gray color
        self._write_pair(6, "Continuous")
        self._write_pair(100, "AcDbPolyline")
        
        self._write_pair(90, 4) # 4 vertices
        self._write_pair(70, 1) # Closed bool
        self._write_pair(43, 0.0) # Constant width
        
        verts = [
            (self.ext_min[0], self.ext_min[1]),
            (self.ext_max[0], self.ext_min[1]),
            (self.ext_max[0], self.ext_max[1]),
            (self.ext_min[0], self.ext_max[1])
        ]
        
        for vx, vy in verts:
            self._write_pair(10, vx)
            self._write_pair(20, vy)
                
        self._write_pair(0, "ENDSEC")

    def _write_objects(self):
        self._write_pair(0, "SECTION")
        self._write_pair(2, "OBJECTS")
        
        # Root Dictionary
        self._write_pair(0, "DICTIONARY")
        self._write_pair(5, self.handles["DICTIONARY_ROOT"])
        self._write_pair(330, 0)
        self._write_pair(100, "AcDbDictionary")
        self._write_pair(280, 0) # Hard owner
        self._write_pair(281, 1) # Merge style
        self._write_pair(3, "ACAD_GROUP")
        self._write_pair(350, self.handles["ACAD_GROUP"])
        
        # ACAD_GROUP Dictionary
        self._write_pair(0, "DICTIONARY")
        self._write_pair(5, self.handles["ACAD_GROUP"])
        self._write_pair(330, self.handles["DICTIONARY_ROOT"])
        self._write_pair(100, "AcDbDictionary")
        self._write_pair(280, 0)
        self._write_pair(281, 1)
        
        self._write_pair(0, "ENDSEC")
        
    def _sanitize_name(self, name: str) -> str:
        """Очистка имени для использования в DXF (убираем пробелы и спецсимволы)"""
        return name.replace(" ", "_").replace(".", "").replace(",", "")

    def _map_color(self, hex_color: str) -> int:
        hex_map = {
            "#ff5555": 1, "#ffff55": 2, "#55ff55": 3, "#55ffff": 4,
            "#5555ff": 5, "#ff55ff": 6, "#ffffff": 7, "#000000": 7
        }
        return hex_map.get(hex_color.lower(), 256)

    def _get_true_color(self, hex_color: str) -> int:
        c = str(hex_color)
        if c.startswith("#") and len(c) == 7:
            r = int(c[1:3], 16)
            g = int(c[3:5], 16)
            b = int(c[5:7], 16)
            return (r << 16) | (g << 8) | b
        return 0

    def _write_common_entity_props(self, entity_type: str, shape: Any, force_continuous: bool = False, force_layer: Optional[str] = None):
        """Запись общих свойств примитива"""
        self._write_pair(0, entity_type)
        self._write_pair(5, self._next_handle())
        
        # CRITICAL: Link to Model Space
        self._write_pair(330, self.handles["T_MODEL_SPACE"])
        
        self._write_pair(100, "AcDbEntity")
        
        # Layer
        layer = force_layer if force_layer is not None else self._sanitize_name(shape.line_style_name)
        self._write_pair(8, layer or "0")
        
        # Цвет
        aci = self._map_color(shape.color)
        if aci != 256:
             self._write_pair(62, aci)
        else:
             self._write_pair(420, self._get_true_color(shape.color))
             
        if force_continuous:
            self._write_pair(6, "Continuous")
        else:
            self._write_pair(6, "BYLAYER")
        
        self._write_pair(100, f"AcDb{entity_type.title().replace('Lwpolyline', 'Polyline')}")

    def _write_entity(self, shape: Any):
        stype = shape.to_dict().get('type')
        if stype == 'point': self._write_point(shape)
        elif stype == 'segment': self._write_line(shape)
        elif stype == 'circle': self._write_circle(shape)
        elif stype == 'arc': self._write_arc(shape)
        elif stype == 'ellipse': self._write_ellipse(shape)
        elif stype == 'rectangle': self._write_lwpolyline_rect(shape)
        elif stype == 'polygon': self._write_lwpolyline_poly(shape)
        elif stype == 'spline': self._write_spline(shape)

    def _write_point(self, shape):
        self._write_common_entity_props("POINT", shape)
        self._write_pair(10, shape.x)
        self._write_pair(20, shape.y)
        self._write_pair(30, 0.0)

    def _write_line(self, shape):
        # Check if style requires geometric emulation
        style_name = shape.line_style_name
        # Find style definition
        style = next((s for s in self.styles if s.name == style_name), None)
        
        if style and style.line_type in ['wavy', 'broken']:
            # Emulate as Polyline using arcs (bulges) instead of point clouds
            if style.line_type == 'wavy':
                verts = self._generate_wavy_vertices(shape.x1, shape.y1, shape.x2, shape.y2, 
                                                   style.wave_amplitude, style.wave_length)
            else: # broken
                pts = self._generate_broken_points(shape.x1, shape.y1, shape.x2, shape.y2,
                                                 style.break_height, style.break_width, style.break_count)
                verts = [(vx, vy, 0.0) for vx, vy in pts]
            
            # Write as open LWPOLYLINE
            self._write_common_entity_props("LWPOLYLINE", shape, force_continuous=True, force_layer="0")
            self._write_pair(90, len(verts)) 
            self._write_pair(70, 0) # Open
            self._write_pair(43, 0.0) 
            
            for vx, vy, bulge in verts:
                self._write_pair(10, vx)
                self._write_pair(20, vy)
                if abs(bulge) > 0.000001:
                    self._write_pair(42, bulge)
        else:
            # Standard Line
            self._write_common_entity_props("LINE", shape)
            self._write_pair(10, shape.x1)
            self._write_pair(20, shape.y1)
            self._write_pair(30, 0.0)
            self._write_pair(11, shape.x2)
            self._write_pair(21, shape.y2)
            self._write_pair(31, 0.0)

    def _write_circle(self, shape):
        self._write_common_entity_props("CIRCLE", shape)
        self._write_pair(10, shape.cx)
        self._write_pair(20, shape.cy)
        self._write_pair(30, 0.0)
        self._write_pair(40, shape.radius)

    def _write_arc(self, shape):
        self._write_common_entity_props("ARC", shape)
        self._write_pair(10, shape.cx)
        self._write_pair(20, shape.cy)
        self._write_pair(30, 0.0)
        self._write_pair(40, shape.radius)
        self._write_pair(50, shape.start_angle)
        self._write_pair(51, shape.end_angle)

    def _write_ellipse(self, shape):
        self._write_common_entity_props("ELLIPSE", shape)
        self._write_pair(10, shape.cx)
        self._write_pair(20, shape.cy)
        self._write_pair(30, 0.0)
        
        import math
        rad = math.radians(shape.rotation)
        dx = shape.rx * math.cos(rad)
        dy = shape.rx * math.sin(rad)
        
        self._write_pair(11, dx)
        self._write_pair(21, dy)
        self._write_pair(31, 0.0)
        
        ratio = shape.ry / shape.rx if shape.rx != 0 else 1.0
        self._write_pair(40, ratio)
        self._write_pair(41, 0.0)
        self._write_pair(42, 6.28318530718)

    def _write_lwpolyline_rect(self, shape):
        self._write_common_entity_props("LWPOLYLINE", shape)
        self._write_pair(90, 4) 
        self._write_pair(70, 1) 
        self._write_pair(43, 0.0) 

        left = min(shape.x, shape.x + shape.width)
        right = max(shape.x, shape.x + shape.width)
        top = min(shape.y, shape.y + shape.height)
        bottom = max(shape.y, shape.y + shape.height)
        
        verts = [(left, top), (right, top), (right, bottom), (left, bottom)]
        for vx, vy in verts:
            self._write_pair(10, vx)
            self._write_pair(20, vy)

    def _write_lwpolyline_poly(self, shape):
        self._write_common_entity_props("LWPOLYLINE", shape)
        
        if hasattr(shape, 'get_vertices'):
             verts = shape.get_vertices()
        else:
             # Fallback
             verts = []
             cx, cy = shape.cx, shape.cy
             r = shape.radius
             sides = shape.num_sides
             rot = math.radians(shape.rotation)
             step = 2.0 * math.pi / sides
             for i in range(sides):
                 angle = rot + i * step
                 verts.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
             
        self._write_pair(90, len(verts))
        self._write_pair(70, 1) 
        for vx, vy in verts:
            self._write_pair(10, vx)
            self._write_pair(20, vy)

    def _write_spline(self, shape):
        self._write_common_entity_props("SPLINE", shape)
        pts = shape.points
        degree = 3
        
        self._write_pair(210, 0.0)
        self._write_pair(220, 0.0)
        self._write_pair(230, 1.0)
        self._write_pair(70, 8) 
        self._write_pair(71, degree) 
        self._write_pair(72, len(pts)) 
        self._write_pair(73, len(pts)) 
        self._write_pair(74, 0) 
        
        num_knots = len(pts) + degree + 1
        for i in range(num_knots):
             self._write_pair(40, float(i))
             
        for px, py in pts:
            self._write_pair(10, px)
            self._write_pair(20, py)
            self._write_pair(30, 0.0)

    def _generate_wavy_vertices(self, x1, y1, x2, y2, amplitude, wavelength):
        length = math.hypot(x2 - x1, y2 - y1)
        if length < 1: return [(x1, y1, 0.0), (x2, y2, 0.0)]
        
        angle = math.atan2(y2 - y1, x2 - x1)
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)
        
        # A wave consists of 2 bumps (up and down) per wavelength.
        bump_length = wavelength / 2.0
        num_bumps = max(2, int(length / bump_length))
        
        # To hit the target exactly, we adjust bump_length slightly to perfectly divide the length
        bump_length = length / num_bumps
        
        # Bulge = 2 * h / d, where h = amplitude, d = bump_length
        bulge = (2.0 * amplitude) / bump_length
        
        vertices = []
        for i in range(num_bumps):
            t = i * bump_length
            vx = x1 + t * cos_a
            vy = y1 + t * sin_a
            # Alternate bulge direction
            b = bulge if i % 2 == 0 else -bulge
            vertices.append((vx, vy, b))
            
        # The last point has no bulge (0.0)
        vertices.append((x2, y2, 0.0))
        return vertices

    def _generate_broken_points(self, x1, y1, x2, y2, break_height, break_width, break_count):
        length = math.hypot(x2 - x1, y2 - y1)
        if length < 20 or break_count < 1: return [(x1, y1), (x2, y2)]
        angle = math.atan2(y2 - y1, x2 - x1)
        perp_x = -math.sin(angle)
        perp_y = math.cos(angle)
        dir_x = math.cos(angle)
        dir_y = math.sin(angle)
        points = [(x1, y1)]
        
        margin = break_width * 2
        usable_length = length - 2 * margin
        if usable_length <= 0: return [(x1, y1), (x2, y2)]
        spacing = usable_length / (break_count + 1)
        
        for i in range(break_count):
            t = margin + spacing * (i + 1)
            t_normalized = t / length
            break_x = x1 + (x2 - x1) * t_normalized
            break_y = y1 + (y2 - y1) * t_normalized
            
            p1_x = break_x - dir_x * break_width
            p1_y = break_y - dir_y * break_width
            p2_x = break_x - dir_x * (break_width / 3) + perp_x * break_height
            p2_y = break_y - dir_y * (break_width / 3) + perp_y * break_height
            p3_x = break_x + dir_x * (break_width / 3) - perp_x * break_height
            p3_y = break_y + dir_y * (break_width / 3) - perp_y * break_height
            p4_x = break_x + dir_x * break_width
            p4_y = break_y + dir_y * break_width
            
            points.extend([(p1_x, p1_y), (p2_x, p2_y), (p3_x, p3_y), (p4_x, p4_y)])
            
        points.append((x2, y2))
        return points

