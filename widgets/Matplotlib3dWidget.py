# -*- coding: utf-8 -*-
from PyQt5 import QtCore, QtWidgets

from numpy import radians, pi, sin, cos
import numpy as np

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure

class Matplotlib3dWidget(QtWidgets.QWidget):
    #
    # this widget allows to plot rotation settings for the magnets
    #
    def __init__(self, *args, **kwargs):
        super(Matplotlib3dWidget, self).__init__()
        self.fig = Figure((1.0, 3.0), dpi=100)
        self.canvas = FigureCanvas(self.fig)
        self.canvas.setParent(self)
        self.toolbar = NavigationToolbar(self.canvas, self)

        self.vbox = QtWidgets.QVBoxLayout()
        self.vbox.addWidget(self.toolbar)
        self.vbox.addWidget(self.canvas)

        self.setLayout(self.vbox)
        #self.canvas.setFocusPolicy(QtCore.Qt.StrongFocus)

         # checkbox to toggle plot
        self.toggle_checkbox = QtWidgets.QCheckBox("Toggle Plot")
        self.toggle_checkbox.setChecked(False)
        self.toggle_checkbox.stateChanged.connect(self.toggle_plot)
        self.toolbar.addWidget(self.toggle_checkbox)
        self.plot_visible = False

        self.max_r = 1
        self.cartesian = True

        # create the figure
        self.fig.suptitle('Field path')
        self.ax = self.fig.add_subplot(111, projection='3d')
        self.ax.set_xlim([-self.max_r, self.max_r])
        self.ax.set_ylim([-self.max_r, self.max_r])
        self.ax.set_zlim([-self.max_r, self.max_r])
        #self.ax.set_aspect('equal')

        # "disable" mouse coordinates
        self.ax.format_coord = lambda x, y: ''

        # init elements:
        self.show_unit_vectors = True
        self.show_unit_sphere = True
        self.show_plane = False
        self.fill_plane = False
        self.show_normal_vector = False
        self.line_path = True  # draw a line between all points

        self.first_vector = np.array([1, 0, 0]) # x, y, z
        self.normal_vector = np.array([0, 0, 1])
        self.last_vector = np.array([0, 1, 0])
        self.plane = self.compute_plane()
        self.all_points = []

        # unit sphere
        u = np.linspace(0, 2*pi, 25)
        v = np.linspace(0, pi, 25)
        x = np.outer(cos(u), sin(v))
        y = np.outer(sin(u), sin(v))
        z = np.outer(np.ones(np.size(u)), cos(v))
        self.sphere = [x, y, z]
        
    def do_plot(self):
        elev, azim = self.ax.elev, self.ax.azim
        xlim, ylim, zlim = self.ax.set_xlim(), self.ax.set_ylim(), self.ax.set_zlim()
        self.ax.cla() # clear
        self.ax.view_init(azim=azim, elev=elev)
        self.ax.set_xlim(xlim); self.ax.set_ylim(ylim); self.ax.set_zlim(zlim)
        self.ax.set_xlabel('X')
        self.ax.set_ylabel('Y')
        self.ax.set_zlabel('Z')

        if not self.plot_visible:
            return

        if self.show_unit_vectors:
            self.ax.quiver(0, 0, 0, 1, 0, 0, color='r', alpha=0.2)
            self.ax.quiver(0, 0, 0, 0, 1, 0, color='g', alpha=0.2)
            self.ax.quiver(0, 0, 0, 0, 0, 1, color='b', alpha=0.2)

        if self.show_unit_sphere:
            self.trace_surface(self.sphere, linewidth=0)
        if self.show_plane:
            self.trace_surface(self.plane)
        
        self.trace_vector(self.first_vector)
        self.trace_vector(self.last_vector)
        if self.show_normal_vector:
            self.trace_vector(self.normal_vector, color='grey', alpha=0.5, marker='')

        if len(self.all_points) > 0:
            if np.allclose(self.all_points.T[0], self.first_vector) \
                and np.allclose(self.all_points.T[-1], self.last_vector):
                for i, xyz in enumerate(self.all_points.T):
                    self.trace_vector(xyz, alpha=1)
                    if self.line_path and i > 0:
                        self.trace_vector(xyz, self.all_points.T[i-1], linestyle='dotted', marker='')

        self.canvas.draw()

    def clear_plot(self):
        self.ax.clear()
        self.canvas.draw()
    
    def toggle_plot(self, state):
        if state == QtCore.Qt.Checked:
            self.plot_visible = True
            self.do_plot()
        else:
            self.plot_visible = False
            self.clear_plot()
    
    def trace_vector(self, xyz, xyz0=[0,0,0], color='pink', linestyle='-', marker='o', **kwargs):
        x0, y0, z0 = xyz0
        x1, y1, z1 = xyz
        self.ax.plot([x0, x1], [y0, y1], [z0, z1], color=color, linestyle=linestyle, marker=marker, markersize=4, markevery=[1], **kwargs)

    def trace_surface(self, XYZ, alpha=0.05, color='grey', **kwargs):
        self.ax.plot_surface(XYZ[0], XYZ[1], XYZ[2], alpha=alpha, color=color, **kwargs)
    
    def set_first_vector(self, xyz):
        self.first_vector = xyz
        self.do_plot()
        return xyz
    
    def set_last_vector(self, xyz):
        self.last_vector = xyz
        self.do_plot()
        return xyz

    def set_normal_vector(self, xyz):
        self.normal_vector = xyz
        self.do_plot()
        return xyz
    
    def set_points(self, all_points):
        self.all_points = all_points
        self.do_plot()
        return all_points

    def compute_plane(self, point=None, normal_vec=None):
        if point is None:
            point = self.first_vector
        if normal_vec is None:
            normal_vec = self.normal_vector
        a, b, c = normal_vec
        # a(x-xp) + b(y-yp) + c(z-zp) = 0
        # ax + by + cz = axp + byp + czp = d
        d = np.dot(normal_vec, point)
        x = np.linspace(-1, 1, 2)
        y = np.linspace(-1, 1, 2)
        X, Y = np.meshgrid(x, y)
        Z = (d - a*X - b*Y) / c
        self.plane = (X, Y, Z)
        return self.plane
    
    def showAxes(self, boo):
        self.show_unit_vectors = boo
        self.do_plot()

    def showSphere(self, boo):
        self.show_unit_sphere = boo
        self.do_plot()
    
    def showPlane(self, boo):
        """ 0:hidden, 1:edges only, 2:filled """
        self.show_plane = boo
        self.do_plot()
    
    def showNormalVector(self, boo):
        self.show_normal_vector = boo
        self.do_plot()
    
    def _asSpherical(self, xyz):
        x,y,z = xyz
        r = np.sqrt(x*x+y*y+z*z)
        t = np.degrees(np.arccos(z/r))
        p = np.degrees(np.arctan2(y,x))
        return np.array([r,t,p])
        
    def _asCartesian(self, rtp):
        r,t,p = rtp[0], radians(rtp[1]), radians(rtp[2])
        x,y,z = r*sin(t)*cos(p), r*sin(t)*sin(p), r*cos(t)
        return np.array([x,y,z])