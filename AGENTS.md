# AGENTS.md - supermegaCAD Development Guide

## Project Overview

supermegaCAD is a Python tkinter-based geometric editor for CAD operations.

**Requirements:** Python 3.10+

---

## Build/Lint/Test Commands

### Running the Application
```bash
python main.py
```

### Running Tests
Tests are standalone scripts, not pytest/unittest-based:

```bash
# Test DXF export functionality
python test_wavy_export.py

# Test complex line types
python test_complex_ltype.py

# Verify lab exports
python verify_labs.py

# Run any specific test
python <test_file.py>
```

### Verification
```bash
# Verify DXF compliance
python verify_dxf_compliance.py
```

---

## Code Style Guidelines

### Type Hints
- Always use type hints for function parameters and return types
- Use `Optional[X]` instead of `X | None`
- Use `List[X]`, `Dict[K, V]`, `Tuple[X, Y]` from `typing`
- Python 3.10+ union syntax acceptable for simple cases

```python
def foo(x: int, y: float) -> Optional[tuple[float, float]]:
    ...

def bar(items: List[Shape]) -> Dict[str, Any]:
    ...
```

### Imports
Order: stdlib → third-party → local modules

```python
# stdlib
import math
import tkinter as tk
from tkinter import ttk, messagebox
from typing import List, Any, Optional

# local
from shapes import Segment
from managers import ShapeManager
from tools import DrawTool
from exporters.dxf_exporter import DxfExporter
```

### Naming Conventions
| Element | Convention | Example |
|---------|------------|---------|
| Classes | PascalCase | `GeometryApp`, `ShapeManager` |
| Methods/Variables | snake_case | `get_bounds()`, `line_style_name` |
| Private methods | `_prefixed` | `_build_ui()`, `_init_snap_vars()` |
| Constants | SCREAMING_SNAKE_CASE or camelCase | `POINT_RADIUS = 4` |
| Enums | PascalCase | `PrimitiveType.SEGMENT` |
| Package private | prefix with `_` | `_internal_helper()` |

### Class Structure

#### Base Classes (ABC pattern)
```python
from abc import ABC, abstractmethod

class Shape(ABC):
    """Docstring describing the class"""
    
    def __init__(self) -> None:
        self.color = "#ff5555"
        self.selected = False
    
    @abstractmethod
    def draw(self, renderer: Any, ...) -> None:
        """Required method docstring"""
        pass
    
    def optional_method(self) -> None:
        """Optional method with default implementation"""
        pass
```

#### Tool Classes
```python
class Tool(ABC):
    def __init__(self, app: Any) -> None:
        self.app = app
    
    @abstractmethod
    def on_mouse_down(self, event: tk.Event) -> None: ...
    @abstractmethod
    def on_mouse_move(self, event: tk.Event) -> None: ...
    @abstractmethod
    def on_mouse_up(self, event: tk.Event) -> None: ...
    @abstractmethod
    def on_activate(self) -> None: ...
    @abstractmethod
    def on_deactivate(self) -> None: ...
    @abstractmethod
    def get_cursor(self) -> str: ...
```

### Docstrings
Use triple-quoted docstrings (no `#` comments for documentation):
- Classes: First line summarizes, blank line, detailed description
- Methods: Describe purpose, Args, Returns, Raises sections when needed

```python
class CanvasRenderer:
    """Class for drawing on Canvas"""
    
    def draw_grid(self, width: int, height: int, ...) -> None:
        """Draw grid and axes with transformation.
        
        Args:
            width, height: Canvas dimensions
            grid_manager: Grid manager instance
            view_transform: View transformation
        """
```

### Error Handling
- Use specific exception types when possible
- Wrap risky operations in try/except
- Allow propagation for unexpected errors

```python
try:
    step = float(self.grid_step_var.get())
    self.grid_manager.base_step = step
except (ValueError, tk.TclError):
    pass  # Ignore invalid input
```

### File Organization

```
lab1/
├── main.py              # Entry point, GeometryApp class
├── core.py               # Core utilities (geometry, rendering, UI helpers)
├── view_transform.py     # View transformation class
├── shapes/              # Shape classes
│   ├── __init__.py     # Public exports
│   ├── base.py          # Abstract Shape class
│   └── segment.py       # Segment implementation
├── tools/               # Tool implementations
│   ├── __init__.py
│   ├── base.py          # Abstract Tool class
│   └── draw_tool.py     # Draw tool
├── managers/            # Manager classes
│   ├── __init__.py
│   ├── shape_manager.py
│   └── snap_manager.py
├── exporters/           # Export functionality
├── importers/           # Import functionality
├── dialogs/             # Dialog windows
└── ui/                  # UI components
```

### Canvas Rendering Pattern
```python
def draw(self, renderer: CanvasRenderer, width: int, height: int, 
         view_transform: ViewTransform, point_radius: int = 4) -> None:
    """Draw shape on canvas using renderer"""
    # Get transformed coordinates
    sx1, sy1 = view_transform.world_to_screen(self.x1, self.y1, width, height)
    # Use renderer for all drawing
    self.canvas.create_line(sx1, sy1, sx2, sy2, ...)
```

### Tkinter Event Handling
```python
# Mouse events
canvas.bind("<Button-1>", self._on_left_click)      # Left click
canvas.bind("<Button-3>", self._on_right_click)     # Right click
canvas.bind("<Motion>", self._on_mouse_move)         # Mouse move
canvas.bind("<MouseWheel>", handler)                 # Scroll wheel

# Keyboard
self.bind("<KeyPress>", self._on_key_press)
```

### Module `__init__.py` Pattern
```python
"""Package docstring"""
from .module1 import Class1
from .module2 import Class2

__all__ = ['Class1', 'Class2']
```

### Constants
Define at class level in PascalCase style for configuration constants:
```python
class GeometryApp(tk.Tk):
    POINT_RADIUS = 4  # Class constant
    COLOR_SELECTION = "#00ff00"
```

---

## Common Patterns

### Main Application Class
```python
class GeometryApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("supermegaCAD")
        # Initialize managers
        self.shape_manager = ShapeManager()
        self.view_transform = ViewTransform()
        # Initialize tools
        self.current_tool = None
        # Build UI and bind events
        self._build_ui()
        self._bind_events()
        self.redraw()
    
    def _build_ui(self) -> None: ...
    def _bind_events(self) -> None: ...
    def redraw(self) -> None: ...
```

### Singleton-like Managers
Managers are instantiated once in `GeometryApp.__init__` and passed to tools:
```python
self.draw_tool = DrawTool(self)  # Tools access app.managers
```

---

## Working with Shapes

### Creating a New Shape
1. Create `shapes/new_shape.py` with class inheriting from `Shape`
2. Implement required abstract methods
3. Add to `shapes/__init__.py` exports
4. Update tools if needed (e.g., `PrimitiveType` enum)

### Shape Interface Requirements
```python
def draw(self, renderer, width, height, view_transform, point_radius) -> None
def distance_to_point(self, px, py, width, height, view_transform) -> float
def get_info(self, is_degrees=True) -> str
def get_bounds(self) -> tuple[float, float, float, float]  # min_x, min_y, max_x, max_y
def translate(self, dx, dy) -> None
def to_dict(self) -> dict
@staticmethod
def from_dict(data: dict) -> 'NewShape'
```

---

## DXF Export Notes
- Uses cp1251 encoding for DXF files
- AutoCAD 2000/R15 format (AC1015)
- Line styles defined in `managers/line_style_manager.py`
- Supports complex linetypes (SHAPE-based patterns)
