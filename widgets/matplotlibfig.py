# -*- coding: utf-8 -*-
"""
Created on Wed Feb  7 16:36:39 2018

@author: ethc3601
"""

import numpy as np
import widgets.sliderVert as SliderVert
import math


#from pyqtgraph.widgets.MatplotlibWidget import MatplotlibWidget, QtCore
from matplotlib.widgets import Cursor, Slider
from scipy.ndimage import filters
from matplotlib.backend_bases import key_press_handler

########################################
# Extracting code from pyqtgraph.widgets.MatplotlibWidget
from PyQt5 import QtCore, QtWidgets
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure

class MatplotlibWidget(QtWidgets.QWidget):
    """
    Implements a Matplotlib figure inside a QWidget.
    Use getFigure() and redraw() to interact with matplotlib.
    
    Example::
    
        mw = MatplotlibWidget()
        subplot = mw.getFigure().add_subplot(111)
        subplot.plot(x,y)
        mw.draw()
    """
    def __init__(self, size=(5.0, 4.0), dpi=100):
        QtWidgets.QWidget.__init__(self)
        self.fig = Figure(size, dpi=dpi)
        self.canvas = FigureCanvas(self.fig)
        self.canvas.setParent(self)
        self.toolbar = NavigationToolbar(self.canvas, self)

        self.vbox = QtWidgets.QVBoxLayout()
        self.vbox.addWidget(self.toolbar)
        self.vbox.addWidget(self.canvas)

        self.setLayout(self.vbox)

    def getFigure(self):
        return self.fig

    def draw(self):
        self.canvas.draw()

########################################

class MatPlotLibFig(MatplotlibWidget):
    #
    #this widget allows to plot taken data
    #
    def __init__(self, *args, **kwargs):
        MatplotlibWidget.__init__(self, size=(10.0, 10.0), dpi=100)
        # connect default keyboard handler
        self.key_press_handler_id = self.canvas.mpl_connect('key_press_event', self.key_press)
        self.canvas.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.toolbar.addAction('Reset', self.reset)
        #
        #basic initialisation of the plot
        #

        #create the figure
        self.fig = self.getFigure()
        self.fig.suptitle('Data plot')
        
        self.colorPlot = self.fig.add_subplot(211)
        self.colorPlot.set_xlabel('X')
        self.colorPlot.set_ylabel('Y')
        self.colorPlot.tick_params('both', which='both', direction='out')
        
        #initialization of the figures for the slices
        self.verticalSlice = self.fig.add_subplot(223)
        self.verticalSlice.set_title('Horizontal slice')
        self.verticalSlice.set_xlabel('X')
        self.verticalSlice.set_ylabel('G')
        self.verticalSlice.tick_params('both', which='both', direction='in')
        self.horizontalSlice = self.fig.add_subplot(224)
        self.horizontalSlice.set_title('Vertical slice')
        self.horizontalSlice.set_xlabel('Y')
        self.horizontalSlice.set_ylabel('G')
        self.horizontalSlice.tick_params('both', which='both', direction='in')

        self.fig.tight_layout()
        self.fig.tight_layout(rect=(0.05, 0.05, 0.95, 0.95))
        self.fig.subplots_adjust(left=None, bottom=None, right=None, top=None,wspace=0.35, hspace=0.25)
        
        # Allows to interact with the canvas by the function 'onclick'
        self.cid = self.fig.canvas.mpl_connect('button_press_event', self.onclick)
        
        # Arbitrary initialization
        self.nb_subline_max = 2
        
        self.plot_status = 0
        self.plot_sigma = 1
        
        # Declaration of the bar
        self.bar = None

        # Declaration of sliders
        self.sliderMin = None 
        self.sliderMax = None 
        self.plotSliderMin = None
        self.plotSliderMax = None

        self.zMin = None
        self.zMax = None

        self.visuMem = None

        self.current_hv_line = None

        self.z = None
        self.z_converted = None

    def key_press(self, event):
        key_press_handler(event, self.canvas, self.toolbar)

    def reset(self):
        self.colorPlot.autoscale()
        self.verticalSlice.autoscale()
        self.horizontalSlice.autoscale()
        self.draw()

    def convert_z(self, z, visu):
        self.z = z
        if z.dtype == np.complex128:
            if visu == "R":
                data = np.abs(self.z)
            elif visu == "Real":
                data = np.real(self.z)
            elif visu == "Theta":
                data = np.angle(self.z, deg=True)
            elif visu == "Imag":
                data = np.imag(self.z)
        else:
            data = z
        
        if self.plot_status == 1:
            derivative_data= self.Dfilter(self.vg_x, data, self.plot_sigma,axis=1)#derivative for x
            data = derivative_data[1]
        elif self.plot_status == 2:
            derivative_data=self.Dfilter(self.vsd_x, data, self.plot_sigma,axis=0)#derivative for y
            data = derivative_data[1]
        
        self.z_converted = data
        return data

    def stop_cut_tracking(self):
        self.current_hv_line = None

    def actualizePlot(self, z, visu, no_cb_update=False):
        #
        # Actualization of the plot
        #
        data = self.convert_z(z, visu)
        
        self.c.set_data(data)
        self.visuMem = visu
        if not no_cb_update:
            self.drawSliders()
        self.bar.draw_all()

        # This updates the last line cut
        current_hv = self.current_hv_line
        if current_hv is not None:
            plh, plv, pos_x, pos_y = current_hv
            plv.set_ydata(data[pos_y])
            plh.set_ydata(data[:, pos_x])
            if not no_cb_update:
                self.verticalSlice.relim()
                self.verticalSlice.autoscale(enable=None)
                self.horizontalSlice.relim()
                self.horizontalSlice.autoscale(enable=None)

        self.draw()

    def updateSliderMin(self, value): #Check if a value is lower than the max authorized
        if value < self.bar.vmax:
            self.bar.set_clim(value, self.bar.vmax)
            self.bar.draw_all()
            self.draw()
        else:
            return None

    def updateSliderMax(self, value): #Check if a value is upper than the max authorized
        if value > self.bar.vmin:
            self.bar.set_clim(self.bar.vmin, value)
            self.bar.draw_all()
            self.draw()
        else:
            return None

    def drawSliders(self): #Add slider on graph
        self.zMin = np.nanmin(self.z_converted)
        self.zMax = np.nanmax(self.z_converted)

        if math.isnan(self.zMin):
            self.zMin = self.bar.vmin
        if math.isnan(self.zMax):
            self.zMax = self.bar.vmax

        if self.sliderMin is None:
            self.plotSliderMin = self.fig.add_subplot(2, 32, 31)
            self.sliderMin = SliderVert.VertSlider(self.plotSliderMin, 'Min', self.bar.vmin, self.zMax, valinit=self.bar.vmin)
            self.sliderMin.on_changed(self.updateSliderMin)
        else:
            self.sliderMin.ax.set_ylim(self.zMin, self.zMax)
            self.sliderMin.valmin = self.zMin
            self.sliderMin.valmax = self.zMax
            self.sliderMin.val = self.zMin
            self.sliderMin.poly.xy[:,1] = [self.zMin, self.zMin, self.zMin, self.zMin, self.zMin]
            if self.updateSliderMin(self.zMin) is None:
                self.bar.set_clim(np.nanmin(self.z_converted), np.nanmax(self.z_converted))

        if self.sliderMax is None:
            self.plotSliderMax = self.fig.add_subplot(2, 32, 32)
            self.sliderMax = SliderVert.VertSlider(self.plotSliderMax, 'Max', self.bar.vmin, self.bar.vmax, valinit=self.bar.vmax)
            self.sliderMax.on_changed(self.updateSliderMax)
        else:
            self.sliderMax.ax.set_ylim(self.zMin, self.zMax)
            self.sliderMax.valmin = self.zMin
            self.sliderMax.valmax = self.zMax
            self.sliderMax.poly.xy[:,1] = [self.zMin, self.zMax, self.zMax, self.zMin, self.zMin]
            if self.updateSliderMax(self.zMax) is None:
                self.bar.set_clim(np.nanmin(self.z_converted), np.nanmax(self.z_converted))
    
    def SliceSetLabel(self, xname='X', yname='Y', gname='G'):
        self.verticalSlice.set_xlabel(xname)
        self.verticalSlice.set_ylabel(gname)
        self.horizontalSlice.set_xlabel(yname)
        self.horizontalSlice.set_ylabel(gname)

    def doplot(self, VgMin, VgMax, VsdMin, VsdMax, z, nbx, nby, visu , xname='X', yname='Y', colorOfPlot='RdBu_r'):

        # First draw of the plot.
        # formplot is the argument to specify derivative for x or y or no derivative

        self.colorPlot.cla()
        self.colorPlot.set_xlabel(xname)
        self.colorPlot.set_ylabel(yname)
        if self.bar is not None:
            self.bar.remove()
            self.bar = None

        if VgMin == VgMax:
            VgMin = 0
            VgMax = nbx
        if VsdMin == VsdMax:
            VsdMin = 0
            VsdMax = nby

        self.nbx = nbx
        self.nby = nby
        self.vgmax = VgMax
        self.vgmin = VgMin
        self.vsdmax = VsdMax
        self.vsdmin = VsdMin 
        self.z = z
        self.vg_x = np.linspace(VgMin, VgMax, nbx)
        self.vsd_x = np.linspace(VsdMin, VsdMax, nby)
        self.stop_cut_tracking()

        data = self.convert_z(self.z, visu)
        self.c = self.colorPlot.imshow(data, extent=[VgMin,VgMax,VsdMin,VsdMax], origin="lower", aspect="auto", cmap=colorOfPlot )

        # Color bar update
        if self.bar is None:
            self.bar = self.fig.colorbar(self.c, ax=self.colorPlot)
        # data is all nan.
        #self.bar.set_clim(np.nanmin(self.z), np.nanmax(self.z))

        #definition of the cursors
        self.cursor_colorPlot = Cursor(self.colorPlot, useblit=True)
        self.cursor_vertical = Cursor(self.verticalSlice, useblit=True)
        self.cursor_horizontal = Cursor(self.horizontalSlice, useblit=True)
        
        # Visual update
        self.bar.draw_all()
        self.draw()

    def onclick(self, event):
        #
        #this is an event to allow clicking on some point on the graph and obtaining somes slices on x and y of the 2D plot
        #

        if event.inaxes != self.colorPlot:
            return

        if self.z_converted is None:
            return

        if self.toolbar._active is not None:
            return

        #these are the x and y position of the click
        self.xdata = event.xdata
        self.ydata = event.ydata

        # Getting the x and y position of click in the matrix
        def interp(x, xp, fp):
            # xp needs to be in increasing order
            if xp[-1] < xp[0]:
                xp = xp[::-1]
                fp = fp[::-1]
            return np.interp(x, xp, fp)
        pos_x = interp(self.xdata, [self.vgmin, self.vgmax],[0, self.nbx])
        pos_x = max(min(pos_x, self.nbx-1), 0)
        pos_y = interp(self.ydata, [self.vsdmin, self.vsdmax],[0, self.nby])
        pos_y = max(min(pos_y, self.nby-1), 0)

        # Just making sure
        pos_x = int(pos_x)
        pos_y = int(pos_y)

        # Checking if ze have reached the limit of subline to display or not
        if len(self.verticalSlice.axes.lines) >= self.nb_subline_max:
            self.verticalSlice.axes.lines = self.verticalSlice.axes.lines[1:]
            self.horizontalSlice.axes.lines = self.horizontalSlice.axes.lines[1:]

        # Displaying data
        plv = self.verticalSlice.plot(self.vg_x, self.z_converted[pos_y])
        plh = self.horizontalSlice.plot(self.vsd_x, self.z_converted[:,pos_x])
        self.current_hv_line = plh[0], plv[0], pos_x, pos_y

        # Re-ajusting scales
        self.verticalSlice.relim()
        self.horizontalSlice.relim()

        # Visual update
        self.draw()

    def clearSubline(self):
        del self.verticalSlice.axes.lines[:]
        del self.horizontalSlice.axes.lines[:]
        self.horizontalSlice.axes.set_xlim(auto=True)
        self.horizontalSlice.axes.set_ylim(auto=True)
        self.verticalSlice.axes.set_xlim(auto=True)
        self.verticalSlice.axes.set_ylim(auto=True)
        self.stop_cut_tracking()
        self.draw()

    def setNbSubline(self, nb):
        self.nb_subline_max = nb

    #Derivative function
    def Dfilter(self, x, y, sigma, axis=-1, mode='reflect', cval=0.):
        """ gaussian filter of size sigma and order 1
            Data should be equally space for filter to make sense
            (sigma in units of dx)
            can use mode= 'nearest'. 'wrap', 'reflect', 'constant'
            cval is for 'constant'
            """
        if len(x) == 1:
            return x, y
        dx = x[1]-x[0]
        yf = filters.gaussian_filter1d(y, sigma, axis=axis, mode=mode, cval=cval, order=1)
        return x, yf/dx
        #return D1(x, yf, axis=axis)

