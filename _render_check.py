import pyvista as pv
pv.OFF_SCREEN = True
from models.parameters import HyperboloidParameters
from rendering.scene import build_scene

p = pv.Plotter(off_screen=True, window_size=(900, 760))
build_scene(p, HyperboloidParameters(), show_axes=True, show_helpers=True)
p.screenshot("_render_check.png")
print("saved _render_check.png")
