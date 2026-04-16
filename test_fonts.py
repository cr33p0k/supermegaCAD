import tkinter as tk
import tkinter.font as tkfont
from shapes.dimension import Dimension

root = tk.Tk()
Dimension._register_bundled_fonts()
fams = tkfont.families()
for f in sorted(fams):
    if 'GOST' in f.upper() or 'ГОСТ' in f.upper():
        print("FOUND FONT:", f)
    if 'Arial' in f:
        print("FOUND FONT:", f)
root.destroy()
