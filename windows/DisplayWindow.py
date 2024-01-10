from widgets import DisplayWidget

from PyQt5.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QComboBox,
)
from PyQt5.QtGui import qRgb, QImage, QPixmap, QIcon
from PyQt5.QtCore import Qt
import pyqtgraph as pg

from widgets.WindowWidget import Window

class DisplayWindow(Window):
    def __init__(self, lab):
        super().__init__()
        self.setWindowTitle("Live display")
        self.setWindowIcon(QIcon("resources/display1.svg"))
        self.resize(1000, 600)
        self.lab = lab

        self.dual = False
        self.displays = [
            DisplayWidget.DisplayWidget(self),
            DisplayWidget.DisplayWidget(self),
        ]
        self.swept_devs = [None, None]

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
        self.btn_show_graphs = self.toolbar.addAction(
            QIcon("resources/graphs.svg"), "graphs"
        )
        self.btn_show_graphs.setCheckable(True)
        self.btn_show_graphs.setChecked(True)
        self.btn_show_graphs.triggered.connect(self.toggleGraphs)
        # cbar show
        self.btn_show_bar = self.toolbar.addAction(QIcon("resources/cbar.svg"), "cbar")
        self.btn_show_bar.setCheckable(True)
        self.btn_show_bar.setChecked(True)
        self.btn_show_bar.triggered.connect(self.toggleColorbar)
        # cbar cb cmap
        self.cb_cmap = QComboBox()
        for cm_name in ["viridis", "CET-D1"]:
            pixmap = self.pixmapFromCmName(cm_name)
            self.cb_cmap.addItem(QIcon(pixmap), "")
            self.cb_cmap.setItemData(self.cb_cmap.count() - 1, cm_name)
        self.cb_cmap.currentTextChanged.connect(self.cMapChanged)
        self.cb_cmap.setCurrentIndex(1)
        self.toolbar.addWidget(self.cb_cmap)
        self.toolbar.addSeparator()
        # hide target lines
        self.btn_target_lines = self.toolbar.addAction(
            QIcon("resources/target.svg"), "target lines"
        )
        self.btn_target_lines.setCheckable(True)
        self.btn_target_lines.setChecked(True)
        self.btn_target_lines.triggered.connect(self.toggleTargetLines)
        self.toolbar.addSeparator()
        # link
        self.btn_link = self.toolbar.addAction("link")
        self.btn_link.setCheckable(True)
        self.btn_link.setVisible(False)
        self.btn_link.triggered.connect(self.toggleLink)

    def show_(self, dual=None):
        if dual is None:
            dual = self.dual
        self.dual = dual
        if dual:
            self.btn_link.setVisible(True)
            self.displays[1].show()
            if self.isHidden():
                self.resize(1600, 600)
        elif not dual:
            self.btn_link.setVisible(False)
            self.displays[1].hide()
            if self.isHidden():
                self.resize(1000, 600)
        self.focus()

    # -- on sweep signals --
    def onIteration(self, current_sweep):
        self.displays[0].drawSweep()
        self.displays[1].drawSweep()

    def onSweepStarted(self, current_sweep):
        out_devs = current_sweep.out_devs
        sweep_devs = current_sweep.sw_devs
        self.displays[0].initSweep(out_devs, sweep_devs)
        self.displays[1].initSweep(out_devs, sweep_devs)

    # -- toolbar --
    def toggleColorbar(self, boo):
        self.displays[0].bar.setVisible(boo)
        self.displays[1].bar.setVisible(boo)

    def cMapChanged(self):
        colormap = self.cb_cmap.currentData()
        self.displays[0].bar.setColorMap(colormap)
        self.displays[1].bar.setColorMap(colormap)

    def toggleGraphs(self, boo):
        self.displays[0].horizontal.setVisible(boo)
        self.displays[1].horizontal.setVisible(boo)
        self.displays[0].vertical.setVisible(boo)
        self.displays[1].vertical.setVisible(boo)

    def toggleLink(self, boo):
        if boo:
            self.displays[1].main.setXLink(self.displays[0].main)
            self.displays[1].main.setYLink(self.displays[0].main)
        else:
            self.displays[1].main.setXLink(None)
            self.displays[1].main.setYLink(None)

    def toggleTargetLines(self, boo):
        self.displays[0].targets_toggleLines(boo)
        self.displays[1].targets_toggleLines(boo)

    # -- utils --
    def pixmapFromCmName(self, name):
        cm = pg.colormap.get(name)
        lut = cm.getLookupTable(0.0, 1.0, 128)
        img = QImage(128, 128, QImage.Format_Indexed8)

        for i in range(lut.shape[0]):
            color = qRgb(lut[i, 0], lut[i, 1], lut[i, 2])
            img.setColor(i, color)

        for x in range(128):
            for y in range(128):
                index = int(((127 - y) / 128) * lut.shape[0])
                img.setPixel(x, y, index)

        return QPixmap.fromImage(img)
