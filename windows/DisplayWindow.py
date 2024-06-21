from widgets import DisplayWidget

from PyQt5.QtWidgets import (
    QWidget,
    QHBoxLayout,
)
from PyQt5.QtGui import QIcon
import pyqtgraph as pg
import matplotlib.pyplot as plt
import matplotlib.cm as mplcm
import numpy as np

from widgets.WindowWidget import Window

class DisplayWindow(Window):
    def __init__(self, lab):
        super().__init__()
        self.setWindowTitle("Live display")
        self.setWindowIcon(QIcon("resources/display1.svg"))
        self.resize(1000, 600)
        self.lab = lab

        self._setupGradientList()

        self.dual = False
        self.displays = [DisplayWidget.DisplayWidget(self),
                         DisplayWidget.DisplayWidget(self),]

        # ui setup
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QHBoxLayout()
        central_widget.setLayout(layout)
        # add displays
        layout.addWidget(self.displays[0])
        layout.addWidget(self.displays[1])
        # remove padding
        layout.setContentsMargins(0, 0, 0, 0)
        # toolbar
        self.toolbar = self.addToolBar("Toolbar")
        self.toolbar.setContextMenuPolicy(3)  # preventcontextmenu
        self.toolbar.setMovable(False)
        self.toolbar.setFloatable(False)
        # tb1 button show side graphs:
        self.btn_side_graphs = self.toolbar.addAction(QIcon("resources/graphs.svg"), "graphs")
        self.btn_side_graphs.setCheckable(True)
        self.btn_side_graphs.setChecked(True)
        self.btn_side_graphs.triggered.connect(self.toggleGraphs)
        # cbar show
        self.btn_show_bar = self.toolbar.addAction(QIcon("resources/cbar.svg"), "cbar")
        self.btn_show_bar.setCheckable(True)
        self.btn_show_bar.setChecked(True)
        self.btn_show_bar.triggered.connect(self.toggleColorbar)
        self.toolbar.addSeparator()
        # hide target lines
        self.btn_live_crosshair = self.toolbar.addAction(QIcon("resources/target.svg"), "live crosshair")
        self.btn_live_crosshair.setCheckable(True)
        self.btn_live_crosshair.setChecked(True)
        self.btn_live_crosshair.triggered.connect(self.toggleLiveCrosshair)
        self.toolbar.addSeparator()
        # link
        self.btn_link = self.toolbar.addAction("&Link")
        self.btn_link.setCheckable(True)
        self.btn_link.triggered.connect(self.toggleLink)
        # transpose:
        self.btn_transpose = self.toolbar.addAction("&Transpose", self.toggleTranspose)
        self.btn_transpose.setVisible(False) # not implemented yet

    def focus(self, dual=None):
        self.dual = dual if dual is not None else self.dual
        if self.dual:
            self.btn_link.setVisible(True)
            self.displays[1].show()
            if self.isHidden():
                self.resize(1600, 600)
        elif not self.dual:
            self.btn_link.setVisible(False)
            self.displays[1].hide()
            if self.isHidden():
                self.resize(1000, 600)
        super().focus()



    # -- on sweep signals --
    def gui_onSweepStarted(self, sweep_status):
        out_devs = sweep_status.out_devs
        sweep_devs = sweep_status.sw_devs
        self.displays[0].initSweep(out_devs, sweep_devs)
        self.displays[1].initSweep(out_devs, sweep_devs)

    def gui_onSweepProgress(self, sweep_status):
        self.displays[0].progressSweep(sweep_status)
        self.displays[1].progressSweep(sweep_status)
    
    def gui_onSweepFinished(self):
        self.displays[0].resetHist()
        self.displays[1].resetHist()


    # -- signals from toolbar --
    def toggleColorbar(self, boo):
        self.displays[0].hist.setVisible(boo)
        self.displays[1].hist.setVisible(boo)

    def toggleGraphs(self, boo):
        self.displays[0].horizontal.setVisible(boo)
        self.displays[1].horizontal.setVisible(boo)
        self.displays[0].vertical.setVisible(boo)
        self.displays[1].vertical.setVisible(boo)

    def toggleLink(self, boo):
        self.displays[1].main.setXLink(self.displays[0].main if boo else None)
        self.displays[1].main.setYLink(self.displays[0].main if boo else None)
    
    def toggleTranspose(self):
        self.displays[0].onTranspose()
        self.displays[1].onTranspose()

    def toggleLiveCrosshair(self, boo):
        self.displays[0].live_trace = boo
        self.displays[0].hPlot.clear()
        self.displays[0].vPlot.clear()
        self.displays[1].live_trace = boo
        self.displays[1].hPlot.clear()
        self.displays[1].vPlot.clear()


    # ----
    def _buildCmapFromMatplotlib(self, cmap_name):
        cmap = mplcm.get_cmap(cmap_name)
        stops = np.linspace(0, 1, 256)
        colors = [cmap(s) for s in stops]
        colors = [(int(r*255), int(g*255), int(b*255), int(a*255)) for r, g, b, a in colors]
        ticks = list(zip(stops, colors))
        return ticks
    
    def _getCmapFromPyqtgraph(self, cmap_name):
        cm = pg.colormap.get(cmap_name)
        stops = cm.getStops()
        ticks = [(stop, tuple(color)) for stop, color in zip(stops[0], stops[1])]
        return ticks

    def _setupGradientList(self):
        cm_str = 'CET-D1'
        ticks = self._getCmapFromPyqtgraph(cm_str)
        pg.graphicsItems.GradientEditorItem.Gradients[cm_str] = {'ticks': ticks, 'mode': 'rgb'}
        
        cm_str = 'RdBu_r'
        ticks = self._buildCmapFromMatplotlib(cm_str)
        pg.graphicsItems.GradientEditorItem.Gradients[cm_str] = {'ticks': ticks, 'mode': 'rgb'}
        


