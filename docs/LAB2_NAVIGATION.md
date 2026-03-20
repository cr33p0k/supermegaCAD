# Навигация в графическом редакторе (ЛР№2)

## Реализованный функционал

### 1. Панорамирование (Pan)
- **СКМ + перемещение** - панорамирование
- **Инструмент "Рука" (H) + ЛКМ** - панорамирование

### 2. Масштабирование (Zoom)
- **Колесико мыши** - масштаб относительно курсора
- **`+`/`=`** - увеличить, **`-`** - уменьшить
- **`F`** - показать все фигуры (сохраняя поворот)

### 3. Поворот вида
- **`[`** - поворот вправо на 90°
- **`]`** - поворот влево на 90°
- Поворот происходит вокруг центра экрана

### 4. Сброс вида
- **`Home`** - сброс всех трансформаций

## Аффинные преобразования

Навигация реализована через класс `ViewTransform` с параметрами:
- `offset_x`, `offset_y` - смещение для панорамирования
- `scale` - масштаб (1.0 = 100%)
- `rotation` - угол поворота в градусах

### Формулы преобразований:

**Панорамирование:** `x' = x + dx, y' = y + dy`

**Масштабирование:** `x' = x * scale, y' = y * scale`

**Поворот:** `x' = x*cos(θ) - y*sin(θ)`, `y' = x*sin(θ) + y*cos(θ)`

## Реализация: Код и разбор

### 1. Преобразование координат: world_to_screen()

```python
def world_to_screen(self, x, y, canvas_width, canvas_height):
    cx, cy = canvas_width / 2, canvas_height / 2
    x_scaled, y_scaled = x * self.scale, y * self.scale
    x_with_offset = x_scaled + self.offset_x
    y_with_offset = y_scaled + self.offset_y
    
    # Поворот вокруг центра экрана
    if self.rotation != 0:
        angle_rad = math.radians(self.rotation)
        cos_a, sin_a = math.cos(angle_rad), math.sin(angle_rad)
        x_rotated = x_with_offset * cos_a - y_with_offset * sin_a
        y_rotated = x_with_offset * sin_a + y_with_offset * cos_a
    else:
        x_rotated, y_rotated = x_with_offset, y_with_offset
    
    return cx + x_rotated, cy - y_rotated  # Инверсия Y
```

**Разбор:** Масштаб → Смещение → Поворот → Экранные координаты (с инверсией Y)

### 2. Обратное преобразование: screen_to_world()

```python
def screen_to_world(self, sx, sy, canvas_width, canvas_height):
    cx, cy = canvas_width / 2, canvas_height / 2
    x_relative = sx - cx
    y_relative = -(sy - cy)  # Инверсия Y
    
    # Обратный поворот
    if self.rotation != 0:
        angle_rad = math.radians(-self.rotation)  # Обратный угол!
        cos_a, sin_a = math.cos(angle_rad), math.sin(angle_rad)
        x_unrotated = x_relative * cos_a - y_relative * sin_a
        y_unrotated = x_relative * sin_a + y_relative * cos_a
    else:
        x_unrotated, y_unrotated = x_relative, y_relative
    
    return (x_unrotated - self.offset_x) / self.scale, \
           (y_unrotated - self.offset_y) / self.scale
```

**Разбор:** Обратные операции в обратном порядке. Нужно для преобразования координат курсора.

### 3. Панорамирование

```python
# view_transform.py
def pan(self, dx: float, dy: float):
    self.offset_x += dx
    self.offset_y += dy

# tools/pan_tool.py
def on_mouse_move(self, event: tk.Event) -> None:
    if self.is_panning:
        dx = event.x - self.last_x
        dy = event.y - self.last_y
        
        # Учитываем поворот экрана
        if self.app.view_transform.rotation != 0:
            angle_rad = math.radians(self.app.view_transform.rotation)
            cos_a, sin_a = math.cos(angle_rad), math.sin(angle_rad)
            dx, dy = dx * cos_a - dy * sin_a, dx * sin_a + dy * cos_a
        
        self.app.view_transform.pan(dx, -dy)  # Инвертируем dy
```

**Разбор:** Вычисляем разность координат, поворачиваем вектор при повороте экрана, инвертируем `dy`.

### 4. Масштабирование относительно курсора

```python
def handle_mouse_wheel(self, event: tk.Event) -> None:
    factor = 1.1 if (event.delta > 0) else 0.9
    
    # Получаем мировые координаты точки под курсором
    world_x, world_y = self.app.view_transform.screen_to_world(event.x, event.y, w, h)
    
    # Вычисляем offset_space: offset_space = world * scale + offset
    old_scale = self.app.view_transform.scale
    offset_space_x = world_x * old_scale + self.app.view_transform.offset_x
    offset_space_y = world_y * old_scale + self.app.view_transform.offset_y
    
    # Корректируем offset: new_offset = offset_space - world * new_scale
    new_scale = old_scale * factor
    self.app.view_transform.scale = new_scale
    self.app.view_transform.offset_x = offset_space_x - world_x * new_scale
    self.app.view_transform.offset_y = offset_space_y - world_y * new_scale
```

**Разбор:** Получаем мировые координаты курсора, вычисляем `offset_space`, после изменения масштаба корректируем offset так, чтобы точка осталась под курсором.

### 5. Поворот вида

```python
def rotate(self, angle_degrees: float):
    self.rotation += angle_degrees
    # Нормализация к [-180, 180]
    while self.rotation > 180: self.rotation -= 360
    while self.rotation < -180: self.rotation += 360
```

**Разбор:** Поворот применяется в `world_to_screen()` вокруг центра экрана. Метод `rotate()` только обновляет угол. При панорамировании и масштабировании учитывается текущий поворот.

### 6. Подгонка вида под все фигуры (F)

```python
# main.py
def fit_all_to_view(self) -> None:
    for shape in shapes:
        bounds = shape.get_bounds()
        min_x = min(min_x, bounds[0])
        max_x = max(max_x, bounds[2])
        # ... аналогично для min_y, max_y
    margin = 80  # Отступ для панели инструментов
    self.view_transform.fit_to_view((min_x, min_y, max_x, max_y), w, h, margin)

# view_transform.py
def fit_to_view(self, shapes_bounds, canvas_width, canvas_height, margin=50):
    min_x, min_y, max_x, max_y = shapes_bounds
    width, height = max_x - min_x, max_y - min_y
    
    # Вычисляем масштаб (с учётом поворота)
    if self.rotation != 0:
        diagonal = math.sqrt(width * width + height * height)
        scale_x = (canvas_width - 2 * margin) / diagonal
        scale_y = (canvas_height - 2 * margin) / diagonal
    else:
        scale_x = (canvas_width - 2 * margin) / width
        scale_y = (canvas_height - 2 * margin) / height
    
    target_scale = min(scale_x, scale_y)  # Берём меньший
    
    # Центрируем фигуры (поворот сохраняется!)
    center_x, center_y = (min_x + max_x) / 2, (min_y + max_y) / 2
    self.scale = target_scale
    self.offset_x = -center_x * target_scale
    self.offset_y = center_y * target_scale
```

**Разбор:** Собираем границы фигур, вычисляем масштаб для вписывания (с учётом поворота), центрируем фигуры. **Поворот сохраняется** - не сбрасываем `rotation`.

### 7. Отрисовка фигур

Все фигуры хранятся в мировых координатах. При отрисовке преобразуем через `world_to_screen()`:

```python
# shapes/segment.py
def draw(self, renderer, width, height, view_transform):
    sx1, sy1 = view_transform.world_to_screen(self.x1, self.y1, width, height)
    sx2, sy2 = view_transform.world_to_screen(self.x2, self.y2, width, height)
    renderer.canvas.create_line(sx1, sy1, sx2, sy2, fill=color)
```

**Разбор:** Фигуры в мировых координатах → преобразование через `world_to_screen()` → отрисовка в экранных координатах. Трансформации применяются автоматически.

## Горячие клавиши

**Инструменты:** `D` (Рисование), `S` (Выделение), `H` (Рука)  
**Навигация:** `+`/`=` (увеличить), `-` (уменьшить), `F` (показать всё), `[`/`]` (поворот), `Home` (сброс)  
**Редактирование:** `Delete` / `Backspace` (удалить)

## Реализованные возможности

✅ Панорамирование (СКМ и инструмент "Рука")  
✅ Масштабирование относительно курсора  
✅ Поворот вида на 90° вокруг центра экрана  
✅ Показать все фигуры (сохраняя поворот)  
✅ Сброс вида  
✅ Информация о навигации в реальном времени  
✅ Контекстное меню (ПКМ)  
✅ Панель инструментов с вкладками  

## Технические детали

**Модули:**
- `view_transform.py` - система аффинных преобразований
- `tools/pan_tool.py` - инструмент панорамирования
- `tools/navigation_handler.py` - обработчик СКМ и колесика

**Особенности:**
- Все инструменты работают с `ViewTransform`
- Фигуры хранятся в мировых координатах
- Трансформации применяются при отрисовке
- Поворот учитывается при панорамировании и масштабировании

---
**Приложение:** supermegaCAD  
**Версия:** 2.1.0 (ЛР№2)
