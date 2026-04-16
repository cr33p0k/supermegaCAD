import tkinter as tk
from shapes.dimension import LinearDimension

root = tk.Tk()
dim = LinearDimension((0,0), (10,10))
print("Resolved for type_b_italic:", dim._resolve_font_spec())
dim.font_type = 'type_b'
print("Resolved for type_b:", dim._resolve_font_spec())
dim.font_type = 'type_a_italic'
print("Resolved for type_a_italic:", dim._resolve_font_spec())
dim.font_type = 'type_a'
print("Resolved for type_a:", dim._resolve_font_spec())
root.destroy()
