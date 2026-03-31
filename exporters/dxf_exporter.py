"""
Модуль для экспорта в формат DXF
"""
import math
from typing import List, Any, Dict, Optional, IO
from datetime import datetime


# Маппинг внутренних типов линий на стандартные DXF-имена,
# которые T-FLEX, AutoCAD и NanoCAD знают нативно
LINETYPE_MAP = {
    'solid': 'Continuous',
    'dashed': 'HIDDEN',
    'dashdot': 'CENTER',
    'dashdotdot': 'PHANTOM',
    'wavy': 'WAVES',
    'broken': 'ZIGZAG',
}


class DxfExporter:
    """Класс для экспорта фигур в формат DXF (AutoCAD 2004/R18)"""
    
    def __init__(self):
        self.handle_seed = 0x10
        self.filename = ""
        self.shapes: List[Any] = []
        self.styles: List[Any] = []
        self.f: Optional[IO] = None
        self.ext_min = (0.0, 0.0)
        self.ext_max = (100.0, 100.0)
        self.margin = 40.0
        
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

    def export(self, filename: str, shapes: List[Any], styles: List[Any], margin: float = 40.0) -> None:
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

    def _get_dxf_linetype(self, style) -> str:
        """Получить стандартное имя DXF-типа линии для стиля"""
        return LINETYPE_MAP.get(style.line_type, 'Continuous')

    def _get_ltype_pattern(self, style) -> List[float]:
        """Преобразование параметров стиля в паттерн DXF (штрихи > 0, пробелы < 0)"""
        lt = style.line_type
        dl, gl, dot = style.dash_length, style.gap_length, style.dot_length
        
        if lt == 'dashed':
            return [dl, -gl]
        elif lt == 'dashdot':
            space = (gl - dot) / 2.0 if gl > dot else 1.0
            return [dl, -space, dot, -space]
        elif lt == 'dashdotdot':
            space = (gl - 2.0 * dot) / 3.0 if gl > 2.0 * dot else 1.0
            return [dl, -space, dot, -space, dot, -space]
        return []

    def _write_table_ltype(self):
        self._write_table_head("LTYPE", self.handles["LTYPE_TABLE"])
        
        # Обязательные системные типы
        system_ltypes = [
            ("ByBlock", "", []),
            ("ByLayer", "", []),
            ("Continuous", "Solid line", []),
        ]
        
        # Стандартные типы, которые T-FLEX/AutoCAD знают нативно
        # WAVES и ZIGZAG — пустой паттерн, CAD использует свои внутренние определения
        standard_ltypes = [
            ("WAVES", "Wavy line", []),
            ("ZIGZAG", "Zigzag line", []),
        ]
        
        # Типы из стилей (dashed, dashdot, dashdotdot)
        seen_names = set()
        dynamic_ltypes = []
        for style in self.styles:
            dxf_name = self._get_dxf_linetype(style)
            if dxf_name in ('Continuous', 'WAVES', 'ZIGZAG'):
                continue
            if dxf_name in seen_names:
                continue
            seen_names.add(dxf_name)
            pattern = self._get_ltype_pattern(style)
            dynamic_ltypes.append((dxf_name, f"{style.line_type}", pattern))
            
        for name, desc, pat in system_ltypes + standard_ltypes + dynamic_ltypes:
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
        
        # Слой 0 (обязательный)
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
        
        # Слой Defpoints для невидимых точек границ (отступов)
        h = self._next_handle()
        self._write_pair(0, "LAYER")
        self._write_pair(5, h)
        self._write_pair(330, self.handles["LAYER_TABLE"])
        self._write_pair(100, "AcDbSymbolTableRecord")
        self._write_pair(100, "AcDbLayerTableRecord")
        self._write_pair(2, "Defpoints")
        self._write_pair(70, 0)
        self._write_pair(62, 8) # Серый цвет
        self._write_pair(6, "Continuous")
        self._write_pair(290, 0) # Флаг: не печатать (Plot=False)
        self._write_pair(390, "F")
        
        for style in self.styles:
            safe_name = self._sanitize_name(style.name)
            if safe_name == "0": continue
            
            dxf_ltype = self._get_dxf_linetype(style)
            
            h = self._next_handle()
            self._write_pair(0, "LAYER")
            self._write_pair(5, h)
            self._write_pair(330, self.handles["LAYER_TABLE"])
            self._write_pair(100, "AcDbSymbolTableRecord")
            self._write_pair(100, "AcDbLayerTableRecord")
            self._write_pair(2, safe_name)
            self._write_pair(70, 0)
            self._write_pair(62, 7)
            self._write_pair(6, dxf_ltype)
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
                
        # --- ФОРСИРУЕМ ОТСТУПЫ (MARGIN) ---
        # T-FLEX часто определяет границы чертежа исключительно по геометрии, 
        # игнорируя $LIMMIN / $EXTMIN. Чтобы задать реальный отступ,
        # поставим две POINT в противоположных углах margin-области 
        # на непечатаемом слое Defpoints.
        self._write_margin_points()
                
        self._write_pair(0, "ENDSEC")

    def _write_margin_points(self):
        """Отрисовка невидимых точек для принудительного расширения границ в CAD"""
        for pt in [self.ext_min, self.ext_max]:
            self._write_pair(0, "POINT")
            self._write_pair(5, self._next_handle())
            self._write_pair(330, self.handles["T_MODEL_SPACE"])
            self._write_pair(100, "AcDbEntity")
            self._write_pair(8, "Defpoints") # Непечатаемый слой AutoCAD
            self._write_pair(100, "AcDbPoint")
            self._write_pair(10, pt[0])
            self._write_pair(20, pt[1])
            self._write_pair(30, 0.0)

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

    def _write_common_entity_props(self, entity_type: str, shape: Any, force_layer: Optional[str] = None):
        """Запись общих свойств примитива"""
        self._write_pair(0, entity_type)
        self._write_pair(5, self._next_handle())
        
        # Привязка к Model Space
        self._write_pair(330, self.handles["T_MODEL_SPACE"])
        
        self._write_pair(100, "AcDbEntity")
        
        # Слой
        layer = force_layer if force_layer is not None else self._sanitize_name(shape.line_style_name)
        self._write_pair(8, layer or "0")
        
        # Цвет (TrueColor через код 420)
        self._write_pair(420, self._get_true_color(shape.color))
        
        # Тип линии — напрямую из стиля фигуры
        style = self._get_shape_style(shape)
        if style:
            dxf_ltype = self._get_dxf_linetype(style)
            self._write_pair(6, dxf_ltype)
            
            # Масштаб типа линии, чтобы волны/штрихи не были огромными
            ltscale = 1.0
            if style.line_type == 'wavy':
                # Для T-FLEX масштаб типа линии напрямую влияет на плотность и амплитуду волн
                # Уменьшаем масштаб в 10 раз по сравнению с предыдущим, чтобы волны были меньше
                # и не вылезали за страницы и границы bounding box-а
                ltscale = max(0.001, style.wave_length / 1000.0)
            elif style.line_type == 'broken':
                ltscale = max(0.001, style.break_width / 500.0)
            elif style.line_type in ('dashed', 'dashdot', 'dashdotdot'):
                ltscale = max(0.01, style.dash_length / 10.0)
                
            self._write_pair(48, ltscale)
        else:
            self._write_pair(6, "Continuous")
            self._write_pair(48, 1.0)
        
        self._write_pair(100, f"AcDb{entity_type.title().replace('Lwpolyline', 'Polyline')}")

    def _get_shape_style(self, shape: Any):
        """Найти стиль фигуры в списке стилей"""
        return next((s for s in self.styles if s.name == shape.line_style_name), None)

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
        
        for vx, vy in [(left, top), (right, top), (right, bottom), (left, bottom)]:
            self._write_pair(10, vx)
            self._write_pair(20, vy)

    def _write_lwpolyline_poly(self, shape):
        if hasattr(shape, 'get_vertices'):
            corners = shape.get_vertices()
        else:
            corners = []
            cx, cy = shape.cx, shape.cy
            r = shape.radius
            sides = shape.num_sides
            rot = math.radians(shape.rotation)
            step = 2.0 * math.pi / sides
            for i in range(sides):
                angle = rot + i * step
                corners.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
        
        self._write_common_entity_props("LWPOLYLINE", shape)
        self._write_pair(90, len(corners))
        self._write_pair(70, 1)
        for vx, vy in corners:
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
