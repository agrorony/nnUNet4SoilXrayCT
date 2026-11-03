"""Step 0.2 - off-screen PyVista render and print of the OpenGL renderer string."""
import pyvista as pv, vtk
pv.OFF_SCREEN = True
p = pv.Plotter(off_screen=True, window_size=(256, 256))
p.add_mesh(pv.Sphere())
p.show(auto_close=False)
rw = p.render_window
caps = rw.ReportCapabilities()
print(caps)
import vtkmodules.util.misc
print('pyvista', pv.__version__, 'vtk', vtk.vtkVersion.GetVTKVersion())
p.screenshot('gpu_test.png'); p.close()
