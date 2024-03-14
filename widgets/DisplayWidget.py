from PyQt5.QtWidgets import QMainWindow, QLabel, QComboBox, QToolBar
from PyQt5.QtCore import QPoint
from PyQt5 import uic, QtCore
import pyqtgraph as pg
import numpy as np
from scipy.ndimage import gaussian_filter1d
from pyHegel.gui import ScientificSpinBox

class DisplaySweepData:
    def __init__(self):
        self.filter_state = "no" # "dx", "dy"
        self.sigma = 1
        self.resetData()
    
    def resetData(self):
        self.raw_data = np.full((1, 1), np.nan)
        self.data = np.full((1, 1), np.nan)
        self.image_rect = (-0.5, -0.5, 1, 1) # x, y, w, h
        self.steps = [0, 0]
        self.sweep_range = [[0, 1, 1], [0, 1, 1]] # [[start1, stop1, nbpts1], [..2]]
        self.label_x = "x"
        self.label_y = "y"
        self.label_out = "out"
        self.transpose = False
    
    def makeImageRect(self):
        start1, stop1, nbpts1 = self.sweep_range[0]
        start2, stop2, nbpts2 = self.sweep_range[1]
        step1, step2 = 0, 0
        if nbpts1 != 1: step1 = abs((stop1-start1) / (nbpts1 - 1))
        if nbpts2 != 1: step2 = abs((stop2-start2) / (nbpts2 - 1))
        self.steps = [step1, step2]
        self.image_rect = [min(start1, stop1)-step1/2,
                           min(start2, stop2)-step2/2,
                           np.abs(stop1-start1)+step1,
                           np.abs(stop2-start2)+step2]
    
    def filteredData(self, gui_dev):
        if gui_dev is not None:
            self.raw_data = gui_dev.values
            self.label_out = gui_dev.getDisplayName("short", with_instr=True)
        else:
            self.label_out = "out"

        axis = {"dx": 0, "dy": 1}.get(self.filter_state, -1)
        if axis == -1 or self.raw_data.shape[axis] == 1:
            self.data = np.copy(self.raw_data)
        else:
            self.data = gaussian_filter1d(self.raw_data, sigma=self.sigma, axis=axis, mode="nearest")
            self.data = np.gradient(self.data, axis=axis)
        if self.transpose:
            self.data = np.transpose(self.data)
        return self.data


class DisplayWidget(QMainWindow):
    def __init__(self, view):
        super().__init__()
        uic.loadUi("ui/DisplayWindow.ui", self)
        self.view = view
        self.disp_data = DisplaySweepData()
        self.disable = False # True when sweeping more than 2 device
        self.live_trace = True
        self.last_mouse_pos = QPoint(0,0)
        self.target_color = 0
        self.target = []

        # -- plot things --
        # image
        self.main = self.graph.addPlot(row=0, col=0, colspan=2)
        self.main.showGrid(x=True, y=True)
        self.main.hideButtons()
        self.image = pg.ImageItem()
        self.main.addItem(self.image)
        # histogram lut
        self.hist = pg.HistogramLUTItem(image=self.image)
        self.hist.setImageItem(self.image)
        self.hist.axis.setWidth(50)
        self.hist.autoHistogramRange()
        self.hist.gradient.sigGradientChanged.connect(lambda: self.hist.gradient.showTicks(False))
        self.hist.gradient.menu.actions()[-4].trigger() # pick the last colormap
        self.graph.addItem(self.hist, row=0, col=2)
        # vertical plot
        self.vertical = self.graph.addPlot(row=1, col=1)
        self.vertical.hideButtons()
        self.vertical.showGrid(x=True, y=True)
        self.vertical.getAxis('left').setWidth(50)
        self.vPlot = self.vertical.plot()
        # horizontal plot
        self.horizontal = self.graph.addPlot(row=1, col=0)
        self.horizontal.hideButtons()
        self.horizontal.showGrid(x=True, y=True)
        self.horizontal.getAxis('left').setWidth(50)
        self.hPlot = self.horizontal.plot()
        # plot links
        #self.vertical.setYLink(self.main)
        #self.horizontal.setXLink(self.main)
        # cross hair
        self.vLine = pg.InfiniteLine(angle=90, movable=False)
        self.hLine = pg.InfiniteLine(angle=0, movable=False)
        self.main.addItem(self.vLine, ignoreBounds=True)
        self.main.addItem(self.hLine, ignoreBounds=True)
        self.main.scene().sigMouseMoved.connect(self.onMouseMoved)
        # targets
        self.targets = []

        # -- toolbars --
        self.toolBar2 = QToolBar()
        self.addToolBarBreak()
        self.addToolBar(self.toolBar2)
        self.toolBar.setContextMenuPolicy(QtCore.Qt.PreventContextMenu)
        self.toolBar2.setContextMenuPolicy(QtCore.Qt.PreventContextMenu)
        self.toolBar.setFloatable(False)
        self.toolBar2.setFloatable(False)
        # tb1 combobox
        self.toolBar.addWidget(QLabel("Output:"))
        self.cb_out = QComboBox()
        self.cb_out.setMinimumWidth(250)
        self.cb_out.currentIndexChanged.connect(self.onCbOutChanged)
        self.toolBar.addWidget(self.cb_out)
        self.toolBar.addSeparator()
        # tb1 button reset view:
        self.btn_reset_view = self.toolBar.addAction("Recenter")
        self.btn_reset_view.triggered.connect(self.recenter)
        # reset cbar
        self.btn_reset_bar = self.toolBar.addAction("Reset bar")
        self.btn_reset_bar.triggered.connect(self.resetHist)
        # tb2 combobox derivative:
        self.toolBar2.addWidget(QLabel("Derivative:"))
        self.cb_derive = QComboBox()
        self.cb_derive.addItem("No derivative", "no")
        self.cb_derive.addItem("df/dx", "dx")
        self.cb_derive.addItem("df/dy", "dy")
        self.cb_derive.currentIndexChanged.connect(self.onFilterChanged)
        self.toolBar2.addWidget(self.cb_derive)
        # sigma
        self.toolBar2.addWidget(QLabel(" Sigma:"))
        self.sb_sigma = ScientificSpinBox.PyScientificSpinBox()
        self.sb_sigma.setRange(1, 100)
        self.toolBar2.addWidget(self.sb_sigma)
        self.sb_sigma.valueChanged.connect(self.onFilterChanged)

        # -- statusbar --
        self.lbl_mouse_coord = QLabel()
        self.statusbar.addWidget(self.lbl_mouse_coord)

        ## crosshair/mouse
        self.targets = []
        self._updateImage()
    
    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Space:
            nb_targets = len(self.targets)
            for t in self.targets:
                if t.mouseHovering:
                    t.onRemove()
                    self.targets.remove(t)
                    break
            if nb_targets == len(self.targets):
                self.addTarget()
        event.accept()

    def onMouseMoved(self, pos):
        if self.main.sceneBoundingRect().contains(pos):
            self.last_mouse_pos = pos
            mousePoint = self.main.vb.mapSceneToView(pos)
            self.vLine.setPos(mousePoint.x())
            self.hLine.setPos(mousePoint.y())
            x, y = self._coordToIndexes(mousePoint)
            # coord in statusbar
            #self.sweep_range = [[0, 1, 1], [0, 1, 1]] # [[start1, stop1, nbpts1], [..2]]
            start1, stop1, nbpts1 = self.disp_data.sweep_range[0]
            start2, stop2, nbpts2 = self.disp_data.sweep_range[1]
            min1, min2 = min(start1, stop1), min(start2, stop2)

            step1, step2 = self.disp_data.steps

            self.lbl_mouse_coord.setText(f"x = {round(min1 + x*step1, 6)}, y = {round(min2 + y*step2, 6)}")
            # live trace
            if self.live_trace:
                self._plotTraces(self.hPlot, self.vPlot, (x,y))
            self.hLine.setVisible(self.live_trace)
            self.hPlot.setVisible(self.live_trace)
            self.vLine.setVisible(self.live_trace)
            self.vPlot.setVisible(self.live_trace)


    def recenter(self):
        self.horizontal.autoRange()
        self.vertical.autoRange()
        self.main.autoRange(padding=0)

    def resetHist(self):
        data = self.disp_data.data
        if np.all(np.isnan(data)): return
        mini, maxi = np.nanmin(data), np.nanmax(data)
        self.hist.setLevels(mini, maxi)
        self.hist.vb.autoRange()

    def onTranspose(self):
        self.disp_data.transpose = not self.disp_data.transpose
        self.disp_data.label_x, self.disp_data.label_y = self.disp_data.label_y, self.disp_data.label_x
        self.disp_data.image_rect = (self.disp_data.image_rect[1], self.disp_data.image_rect[0], self.disp_data.image_rect[3], self.disp_data.image_rect[2])
        self._updateImage()
        self.recenter()

    def onCbOutChanged(self):
        self._updateImage()
        self.resetHist()
    
    def onFilterChanged(self):
        self.disp_data.filter_state = self.cb_derive.currentData()
        self.disp_data.sigma = self.sb_sigma.value()
        self._updateImage()
        self.resetHist()
    
    def addTarget(self):
        x, y = self.vLine.pos().x(), self.hLine.pos().y()
        self.targets.append(Target(self, (x, y)))

    def removeAllTargets(self):
        [t.onRemove() for t in self.targets]
        self.targets.clear()

    def _coordToIndexes(self, coord):
        image_rect = self.disp_data.image_rect
        raw_data = self.disp_data.raw_data
        x_index = int((coord.x() - image_rect[0]) / (image_rect[2] / raw_data.shape[0]))
        y_index = int((coord.y() - image_rect[1]) / (image_rect[3] / raw_data.shape[1]))
        x_index = min(x_index, raw_data.shape[0]-1); y_index = min(y_index, raw_data.shape[1]-1)
        x_index = max(x_index, 0);                   y_index = max(y_index, 0)
        return x_index, y_index

    def _plotTraces(self, h_plot, v_plot, indexes):
        x, y  = indexes
        horiz_trace = self.disp_data.data[:, y]
        vert_trace = self.disp_data.data[x]
        self.horiz_trace = horiz_trace
        self.vert_trace = vert_trace

        h_x_axis = np.linspace(*self.disp_data.sweep_range[0])
        v_x_axis = np.linspace(*self.disp_data.sweep_range[1])
        
        if self.disp_data.transpose:
            horiz_trace, vert_trace = vert_trace, horiz_trace
            h_x_axis, v_x_axis = v_x_axis, h_x_axis

        if len(h_x_axis) == len(horiz_trace):
            h_plot.setData(x=h_x_axis, y=horiz_trace)
        if len(np.unique(horiz_trace)) > 2: # autorange only if non-nan val >= 2
            self.horizontal.autoRange()

        if len(v_x_axis) == len(vert_trace):
            v_plot.setData(x=v_x_axis, y=vert_trace)
        if len(np.unique(vert_trace)) > 2:
            self.vertical.autoRange()

    def _updateImage(self):
        gui_dev = self.cb_out.currentData()
        to_display = self.disp_data.filteredData(gui_dev)
        if not np.all(np.isnan(to_display)):
            self.image.setImage(to_display, autoLevels=False)
            self.image.setRect(self.disp_data.image_rect)

        self._setLabels()
        self.onMouseMoved(self.last_mouse_pos)
        [t.onTargetMove() for t in self.targets]

    def _setLabels(self):
        new_lbls = [self.disp_data.label_x, self.disp_data.label_y, self.disp_data.label_out]
        axes_x = [self.main.getAxis("bottom"), self.horizontal.getAxis("bottom")]
        axes_y = [self.main.getAxis("left"), self.vertical.getAxis("bottom")]
        axes_out = [self.horizontal.getAxis("left"), self.vertical.getAxis("left")]
        #hist.getAxis("left", name) # must investigate how to put a label on histogram/gradient
        for new_lbl, axes in zip(new_lbls, [axes_x, axes_y, axes_out]):
            [ax.setLabel(new_lbl) for ax in axes]


    # -- called by DisplayWindow --
    def initSweep(self, out_devs, sweep_devs):
        # set labels, cb and range

        self.disp_data.resetData()
        self.disable = False
        self.removeAllTargets()

        if len(sweep_devs) > 2:
            self.disable = True
            return
        
        gui_dev1 = sweep_devs[0]
        start1, stop1, nbpts1 = gui_dev1.sweep
        self.disp_data.sweep_range[0] = gui_dev1.sweep
        self.disp_data.label_x = gui_dev1.getDisplayName("short", with_instr=True)
        
        if len(sweep_devs) == 2:
            gui_dev2 = sweep_devs[1]
            start2, stop2, nbpts2 = gui_dev2.sweep
            self.disp_data.label_y = gui_dev2.getDisplayName("short", with_instr=True)
            self.disp_data.sweep_range[1] = gui_dev2.sweep
        
        self.disp_data.makeImageRect()
        self.hPlot.clear()
        self.vPlot.clear()
        self.image.clear()
        self.cb_out.clear()

        for gui_dev in out_devs:
            self.cb_out.addItem(gui_dev.getDisplayName("short", with_instr=True), gui_dev)
        self.cb_out.setCurrentIndex(0)
    
        self._updateImage()
    
    def progressSweep(self, sweep_status):
        self._updateImage()
        current_pts = sweep_status.iteration[0]
        if current_pts == 1: self.recenter()
        if current_pts % 10 == 1:
            self.resetHist()


class Target(pg.TargetItem):
    def __init__(self, parent, pos):
        self.parent = parent
        self.color = pg.intColor(self.parent.target_color)
        self.parent.target_color += 1

        #super().__init__(pos, pen=pg.mkPen(self.color, width=1), label=True)
        super().__init__(pos, pen=pg.mkPen(self.color, width=1))
        self.setMouseHover(True)

        self.hPlot = self.parent.horizontal.plot()
        self.hPlot.setPen(pg.mkPen(self.color))
        self.vPlot = self.parent.vertical.plot()
        self.vPlot.setPen(pg.mkPen(self.color))

        self.sigPositionChanged.connect(self.onTargetMove)
        self.onTargetMove()
        parent.main.addItem(self)

    def onRemove(self):
        self.parent.main.removeItem(self)
        self.parent.horizontal.removeItem(self.hPlot)
        self.parent.vertical.removeItem(self.vPlot)

    def onTargetMove(self, pos=None):
        if pos is None: pos = self.pos()
        x, y = self.parent._coordToIndexes(pos)
        self.parent._plotTraces(self.hPlot, self.vPlot, (x,y))
