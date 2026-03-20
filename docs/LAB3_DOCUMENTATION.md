# Лабораторная работа №3 — Управление стилями линий ГОСТ 2.303-68

## Цель работы

Реализация системы управления типами и толщинами линий согласно стандарту ГОСТ 2.303-68.

---

## Структура модуля стилей линий

### Основной файл: `managers/line_style_manager.py`

#### Класс `LineStyle` (dataclass)

Описывает один стиль линии:

```python
@dataclass
class LineStyle:
    name: str              # Название стиля
    thickness_mm: float    # Толщина в миллиметрах
    line_type: str         # Тип: solid, dashed, dotted, wavy, broken...
    description: str       # Описание назначения
    dash_length: float     # Длина штриха (для штриховых)
    gap_length: float      # Длина промежутка
    dot_length: float      # Длина точки (для штрихпунктирных)
```

#### Класс `LineStyleManager`

Управляет коллекцией стилей:

| Метод | Описание |
|-------|----------|
| `get_style(name)` | Получить стиль по имени |
| `get_style_names()` | Список всех названий стилей |
| `get_current_style_name()` | Текущий выбранный стиль |
| `set_current_style(name)` | Установить текущий стиль |
| `mm_to_pixels(mm)` | Конвертация мм → пиксели |
| `generate_wavy_points(...)` | Генерация точек волнистой линии |
| `generate_broken_points(...)` | Генерация точек линии с изломами |

---

## Стандартные стили ГОСТ 2.303-68

| № | Название | Тип | Толщина | Назначение |
|---|----------|-----|---------|------------|
| 1 | Сплошная основная | `solid` | 0.8 мм | Основные линии чертежа |
| 2 | Сплошная тонкая | `solid` | 0.4 мм | Размерные, выносные линии |
| 3 | Сплошная волнистая | `wavy` | 0.4 мм | Линии обрыва |
| 4 | Штриховая | `dashed` | 0.4 мм | Невидимые контуры |
| 5 | Штрихпунктирная утолщённая | `dash_dot` | 0.8 мм | Осевые линии |
| 6 | Штрихпунктирная тонкая | `dash_dot` | 0.4 мм | Центровые линии |
| 7 | Штрихпунктирная с двумя точками | `dash_dot_dot` | 0.4 мм | Линии сгиба |
| 8 | Сплошная тонкая с изломами | `broken` | 0.4 мм | Длинные линии обрыва |

---

## Интеграция с геометрическими объектами

### Базовый класс `Shape` (`shapes/base.py`)

```python
class Shape(ABC):
    line_style_name: str = "Сплошная основная"  # Имя стиля по умолчанию
```

Каждая фигура хранит имя стиля в атрибуте `line_style_name`.

### Отрисовка с учётом стиля (`shapes/segment.py`)

```python
def draw(self, renderer, width, height, view_transform, point_radius):
    # Получение стиля из менеджера
    if hasattr(renderer, 'style_manager') and renderer.style_manager:
        style = renderer.style_manager.get_style(self.line_style_name)
        if style:
            line_width = renderer.style_manager.mm_to_pixels(style.thickness_mm)
            dash_pattern = style.get_dash_pattern()
    
    # Отрисовка в зависимости от типа линии
    if style.line_type == 'wavy':
        points = renderer.style_manager.generate_wavy_points(...)
        canvas.create_line(*points, smooth=True, ...)
    elif style.line_type == 'broken':
        points = renderer.style_manager.generate_broken_points(...)
        canvas.create_line(*points, ...)
    else:
        canvas.create_line(x1, y1, x2, y2, dash=dash_pattern, ...)
```

### Применение стиля при создании (`tools/draw_tool.py`)

```python
def _create_shape(self):
    shape = Segment(...)
    shape.line_style_name = self.app.style_manager.get_current_style_name()
    self.app.shape_manager.add_shape(shape)
```

---

## Пользовательский интерфейс

### Выбор стиля для новых объектов

**Расположение:** Правая панель → "Стиль линии"

- Выпадающий список `ttk.Combobox` с названиями стилей
- При выборе вызывается `style_manager.set_current_style(name)`

### Изменение стиля существующего объекта

**Расположение:** Правая панель → "Свойства объекта" → "Стиль линии"

- Выпадающий список для выбранной фигуры
- Изменение атрибута `shape.line_style_name`

### Диалог управления стилями

**Файл:** `dialogs/style_manager_dialog.py`

**Доступ:** Кнопка "⚙ Управление стилями"

**Возможности:**
- Просмотр всех стилей в таблице
- Редактирование параметров:
  - Толщина (мм)
  - Длина штриха
  - Длина промежутка
- Предпросмотр стиля
- Сохранение изменений

---

## Технические детали

### Конвертация мм → пиксели

```python
SCREEN_DPI = 96.0  # Стандартное DPI дисплея

def mm_to_pixels(self, mm: float) -> float:
    return (mm / 25.4) * self.SCREEN_DPI
```

**Результат:** Толщина линий не зависит от масштаба отображения.

### Генерация волнистой линии

```python
def generate_wavy_points(x1, y1, x2, y2, amplitude=3.0, wavelength=12.0):
    # Генерация точек вдоль линии с синусоидальным смещением
    # amplitude - амплитуда волны в пикселях
    # wavelength - длина волны в пикселях
    # Возвращает список координат [x1, y1, x2, y2, ...]
```

### Генерация линии с изломами

```python
def generate_broken_points(x1, y1, x2, y2, segment_length=20.0, break_height=8.0):
    # Генерация зигзагообразных точек
    # segment_length - длина горизонтального сегмента
    # break_height - высота излома
    # Используется для линий обрыва большой длины
```

### Штриховые паттерны

```python
def get_dash_pattern(self) -> Optional[Tuple]:
    if self.line_type == 'dashed':
        return (self.dash_length, self.gap_length)
    elif self.line_type == 'dash_dot':
        return (self.dash_length, self.gap_length, self.dot_length, self.gap_length)
    elif self.line_type == 'dash_dot_dot':
        return (self.dash_length, self.gap_length, 
                self.dot_length, self.gap_length, 
                self.dot_length, self.gap_length)
    return None  # Сплошная линия
```

---

## Сериализация

При сохранении/загрузке фигур стиль сохраняется:

```python
# Сохранение
def to_dict(self) -> dict:
    return {
        'type': 'segment',
        'x1': self.x1, 'y1': self.y1,
        'x2': self.x2, 'y2': self.y2,
        'line_style_name': self.line_style_name,  # Стиль
        ...
    }

# Загрузка
@staticmethod
def from_dict(data: dict) -> 'Segment':
    segment = Segment(...)
    segment.line_style_name = data.get('line_style_name', 'Сплошная основная')
    return segment
```

---

## Соответствие ГОСТ 2.303-68

| Требование | Реализация |
|------------|------------|
| Типы линий | ✅ 8 стандартных типов |
| Толщины в мм | ✅ Хранение и конвертация |
| Соотношение толщин | ✅ Основная 0.8 мм, тонкая 0.4 мм |
| Волнистая линия | ✅ Через генерацию точек |
| Линия с изломами | ✅ Через генерацию точек |
| Штриховка | ✅ Dash-паттерны Tkinter |
