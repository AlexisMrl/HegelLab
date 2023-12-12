from PyQt5.QtWidgets import QMainWindow, QLabel, QComboBox, QToolBar
from PyQt5.QtCore import QPoint
from PyQt5 import uic, QtCore
import pyqtgraph as pg
import numpy as np
from scipy.ndimage import gaussian_filter1d
from pyHegel.gui import ScientificSpinBox


class DisplayWidget(QMainWindow):
    def initVars(self):
        self.filter_state = ["no", 1]  # (<'no', 'dx', 'dy'>, sigma)
        # self.raw_data = np.random.rand(10, 10)  # raw data, before derivative and transpose
        self.raw_data = np.full(
            (10, 10), np.nan
        )  # raw data, before derivative and transpose
        self.image_rect = (-5, -5, 10, 10)  # rectangle for transform: x, y, w, h
        self.axes = {"x": np.linspace(-5, 5, 10), "y": np.linspace(-5, 5, 10)}
        self.labels = {"x": "x sweep", "y": "y sweep", "out": "out"}
        self.int_color = 0  # color for targets

    def __init__(self, view):
        super(DisplayWidget, self).__init__()
        uic.loadUi("ui/DisplayWindow.ui", self)
        self.view = view

        # -- setting up the window --
        # image
        self.main = self.graph.addPlot(row=0, col=0)
        self.main.showGrid(x=True, y=True)
        self.main.hideButtons()
        self.image = pg.ImageItem()
        self.main.addItem(self.image)

        # vertical plot
        self.vertical = self.graph.addPlot(row=0, col=1)
        self.vertical.hideButtons()
        self.vertical.setMaximumWidth(200)
        # horizontal plot
        self.horizontal = self.graph.addPlot(row=1, col=0)
        self.horizontal.hideButtons()
        self.horizontal.setMaximumHeight(200)
        # plot links
        self.vertical.setYLink(self.main)
        self.horizontal.setXLink(self.main)
        # color bar
        self.bar = pg.ColorBarItem()
        self.bar.rounding = 0.02
        self.bar.setImageItem(self.image, insert_in=self.main)

        # -- toolbars
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
        self.btn_reset_view = self.toolBar.addAction("Reset view")
        self.btn_reset_view.triggered.connect(self.resetView)
        # reset cbar
        self.btn_reset_bar = self.toolBar.addAction("Reset cbar")
        self.btn_reset_bar.triggered.connect(self.updateBar)
        # transpose:
        self.btn_transpose = self.toolBar.addAction("Transpose")
        self.btn_transpose.setCheckable(True)
        self.btn_transpose.setChecked(False)
        self.btn_transpose.triggered.connect(self.onTranspose)
        self.btn_transpose.setVisible(False) # TODO: transpose not implemented yet

        # tb2 combobox derivative:
        self.toolBar2.addWidget(QLabel("Derivative:"))
        self.cb_derive = QComboBox()
        self.cb_derive.addItem("No derivative", "no")
        self.cb_derive.addItem("df/dx", "dx")
        self.cb_derive.addItem("df/dy", "dy")
        self.cb_derive.currentIndexChanged.connect(
            lambda: self.updateFilter(filter_=self.cb_derive.currentData())
        )
        self.toolBar2.addWidget(self.cb_derive)
        # sigma
        self.toolBar2.addWidget(QLabel("Sigma:"))
        self.sb_sigma = ScientificSpinBox.PyScientificSpinBox()
        self.sb_sigma.setRange(1, 100)
        self.toolBar2.addWidget(self.sb_sigma)
        self.sb_sigma.valueChanged.connect(
            lambda: self.updateFilter(sigma=self.sb_sigma.value())
        )
        # crosshair/mouse
        self.toolBar2.addSeparator()
        self.btn_add_crosshair = self.toolBar2.addAction("Add crosshair")

        def onAddCrosshair():
            if len(self.targets) < 5:
                self.targets.append(Target(self))

        self.btn_add_crosshair.triggered.connect(onAddCrosshair)
        self.btn_remove_crosshair = self.toolBar2.addAction("Remove crosshair")

        def onRemoveCrosshair():
            if len(self.targets) > 1:
                tgt = self.targets.pop()
                tgt.remove()

        self.btn_remove_crosshair.triggered.connect(onRemoveCrosshair)

        # variables
        self.initVars()
        self.targets = [Target(self)]
        self.drawRaw()
        self.updateLabels()

    # -- core functions --
    def clear(self):
        self.image.clear()
        self.updateLabels(x="", y="", out="")
        self.cb_out.clear()

    def resetView(self):
        self.horizontal.autoRange()
        self.vertical.autoRange()
        self.main.autoRange(padding=0)

    def drawRaw(self):
        to_draw = self.raw_data.T if self.btn_transpose.isChecked() else self.raw_data
        to_draw = self.filter_(to_draw, *self.filter_state)

        self.image.setImage(to_draw, autoLevels=False)
        self.image.setRect(self.image_rect)
        self.updateBar()
        self.updateTargets()

    def drawSweep(self):
        out_dev = self.cb_out.currentData()
        if out_dev is None:
            return
        self.raw_data = out_dev.values
        self.drawRaw()

    def initSweep(self, out_devs, sweep_devs):
        self.clear()
        self.swept_devs = sweep_devs
        # set labels and init axis for side graphs and set target and image rect

        if len(sweep_devs) == 1:
            x_for_horiz = np.linspace(
                sweep_devs[0].sweep[0], sweep_devs[0].sweep[1], sweep_devs[0].sweep[2]
            )
            if sweep_devs[0].sweep[1] < sweep_devs[0].sweep[0]:
                x_for_horiz = np.flip(x_for_horiz)  # reversed sweep
            y_for_vert = np.array([0])
            # rectangle for transform: x, y, w, h
            self.image_rect = (
                min(sweep_devs[0].sweep[:2]),
                0,
                np.abs(sweep_devs[0].sweep[1] - sweep_devs[0].sweep[0]),
                1,
            )
            self.updateLabels(
                x=sweep_devs[0].getDisplayName("short"),
                out=out_devs[0].getDisplayName("short"),
            )

        elif len(sweep_devs) == 2:
            self.main.setLabel("left", sweep_devs[1].getDisplayName("short"))
            self.vertical.setLabel("left", sweep_devs[1].getDisplayName("short"))
            x_for_horiz = np.linspace(
                sweep_devs[0].sweep[0], sweep_devs[0].sweep[1], sweep_devs[0].sweep[2]
            )
            y_for_vert = np.linspace(
                sweep_devs[1].sweep[0], sweep_devs[1].sweep[1], sweep_devs[1].sweep[2]
            )
            if sweep_devs[0].sweep[1] < sweep_devs[0].sweep[0]:
                x_for_horiz = np.flip(x_for_horiz)
            if sweep_devs[1].sweep[1] < sweep_devs[1].sweep[0]:
                y_for_vert = np.flip(y_for_vert)
            # rectangle for transform: x, y, w, h
            self.image_rect = (
                min(sweep_devs[0].sweep[:2]),
                min(sweep_devs[1].sweep[:2]),
                np.abs(sweep_devs[0].sweep[1] - sweep_devs[0].sweep[0]),
                np.abs(sweep_devs[1].sweep[1] - sweep_devs[1].sweep[0]),
            )
            self.updateLabels(
                x=sweep_devs[0].getDisplayName("short"),
                y=sweep_devs[1].getDisplayName("short"),
                out=out_devs[0].getDisplayName("short"),
            )

        self.axes = {"x": x_for_horiz, "y": y_for_vert}
        self.drawRaw()
        self.resetView()
        self.targets_reset()

        # set cb_out
        self.cb_out.currentIndexChanged.disconnect(self.onCbOutChanged)
        for dev in out_devs:
            self.cb_out.addItem(dev.getDisplayName("short"), dev)
        self.cb_out.currentIndexChanged.connect(self.onCbOutChanged)
        self.cb_out.setCurrentIndex(0)

    # -- connected to signals --

    #    def onTargetMove(self, pos):
    #        x, y = pos.x(), pos.y()
    #        self.vline_main.setPos(x); self.hline_main.setPos(y)
    #        self.vline.setPos(x); self.hline.setPos(y)
    #        if self.image.image is None: return
    #        self.target_px_x, self.target_px_y = self.coordToPixel(x, y, self.image.image, self.image_rect)
    #        self.updateSideGraphs()

    def updateLabels(self, x=None, y=None, out=None):
        if x:
            self.labels["x"] = x
        if y:
            self.labels["y"] = y
        if out:
            self.labels["out"] = out
        self.main.setLabel("bottom", self.labels["x"])
        self.horizontal.setLabel("bottom", self.labels["x"])
        self.main.setLabel("left", self.labels["y"])
        self.vertical.setLabel("left", self.labels["y"])
        self.horizontal.setLabel("left", self.labels["out"])
        self.vertical.setLabel("bottom", self.labels["out"])
        self.bar.setLabel("left", self.labels["out"])

    def updateBar(self):
        data = self.image.image
        if data is None:
            return
        if np.isnan(data).all():
            return
        mini, maxi = np.nanmin(data), np.nanmax(data)
        self.bar.setLevels((mini, maxi))
    
    def updateFilter(self, filter_=None, sigma=None):
        if filter_:
            self.filter_state[0] = filter_
        if sigma:
            self.filter_state[1] = sigma
        self.drawRaw()

    def onTranspose(self, boo):
        self.updateLabels(
            x=self.labels["y"], y=self.labels["x"], out=self.labels["out"]
        )
        self.image_rect = (
            self.image_rect[1],
            self.image_rect[0],
            self.image_rect[3],
            self.image_rect[2],
        )
        self.targets_reset()
        self.drawRaw()
        self.resetView()

    def onCbOutChanged(self):
        out_dev = self.cb_out.currentData()
        if out_dev is None:
            return
        self.updateLabels(out=out_dev.getDisplayName("short"))
        self.drawSweep()

    # -- targets --
    def updateTargets(self):
        for target in self.targets:
            target.update()

    def targets_toggleLines(self, boo):
        for target in self.targets:
            target.vline.setVisible(boo)
            target.hline.setVisible(boo)
            target.label.setVisible(boo)

    def targets_reset(self):
        # reset targets to center of image_rect
        center = (
            self.image_rect[0] + self.image_rect[2] / 2,
            self.image_rect[1] + self.image_rect[3] / 2,
        )
        for target in self.targets:
            target.target.setPos(*center)

    # -- utils (no self) --

    def filter_(self, data, axis, sigma):
        axis = {"dx": 0, "dy": 1}.get(axis, -1)
        if axis == -1 or data.shape[axis] == 1:
            return data
        data = gaussian_filter1d(data, sigma=sigma, axis=axis, mode="nearest")
        return np.gradient(data, axis=axis)


class Target:
    def __init__(self, parent):
        self.parent = parent

        self.color = pg.intColor(self.parent.int_color)
        self.parent.int_color += 1

        self.target = pg.TargetItem(
            (0, 0), symbol="crosshair", pen=pg.mkPen(self.color, width=1)
        )
        self.label = pg.TargetLabel(
            self.target, text="", color=self.color, offset=(10, 10)
        )
        self.vline = pg.InfiniteLine(
            angle=90, movable=False, pen=pg.mkPen(self.color, width=2)
        )
        self.hline = pg.InfiniteLine(
            angle=0, movable=False, pen=pg.mkPen(self.color, width=2)
        )

        self.horizontal = self.parent.horizontal.plot()
        self.horizontal.setPen(pg.mkPen(self.color, width=1))
        self.vertical = self.parent.vertical.plot()
        self.vertical.setPen(pg.mkPen(self.color, width=1))

        self.target.setZValue(10)
        self.vline.setZValue(10)
        self.hline.setZValue(10)
        self.target.sigPositionChanged.connect(self.onTargetMove)
        self.onTargetMove(QPoint(0, 0))

        parent.main.addItem(self.target)
        parent.main.addItem(self.vline)
        parent.main.addItem(self.hline)

    def remove(self):
        self.parent.int_color -= 1
        self.parent.main.removeItem(self.target)
        self.parent.main.removeItem(self.vline)
        self.parent.main.removeItem(self.hline)
        self.parent.horizontal.removeItem(self.horizontal)
        self.parent.vertical.removeItem(self.vertical)

    def _coordToPixel(self, image, image_rect):
        x, y = self.target.pos().x(), self.target.pos().y()
        x_index = int((x - image_rect[0]) / (image_rect[2] / image.shape[0]))
        y_index = int((y - image_rect[1]) / (image_rect[3] / image.shape[1]))
        if x_index > image.shape[0] - 1:
            x_index = -1
        if y_index > image.shape[1] - 1:
            y_index = -1
        if x_index < 0:
            x_index = -1
        if y_index < 0:
            y_index = -1
        return x_index, y_index

    def onTargetMove(self, pos):
        self.vline.setPos(pos.x())
        self.hline.setPos(pos.y())
        if self.parent.image.image is None:
            return
        self.update()

    def update(self):
        # update label and traces
        x, y = self._coordToPixel(self.parent.image.image, self.parent.image_rect)
        self._updateLabel(x, y)
        self._updateTraces(x, y)

    def _updateLabel(self, x, y):
        if x == -1 or y == -1:
            self.label.setText("")
            return
        string = str(self.parent.image.image[x, y])
        # self.label.setText(string if string != 'nan' else '')
        self.label.setText(string)

    def _updateTraces(self, x, y):
        if x != -1:
            data_col = self.parent.image.image[x]
            if data_col.shape[0] == self.parent.axes["y"].shape[0]:
                self.vertical.setData(data_col, self.parent.axes["y"])
            mi, ma = min(data_col), max(data_col)
            if str(mi) != 'nan' and str(ma) != 'nan':
                self.parent.vertical.setXRange(mi, ma)
        if y != -1:
            data_row = self.parent.image.image[:, y]
            if data_row.shape[0] == self.parent.axes["x"].shape[0]:
                self.horizontal.setData(self.parent.axes["x"], data_row)
            mi, ma = min(data_row), max(data_row)
            if str(mi) != 'nan' and str(ma) != 'nan':
                self.parent.horizontal.setYRange(mi, ma)
