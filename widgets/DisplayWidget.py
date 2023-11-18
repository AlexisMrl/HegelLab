from PyQt5.QtWidgets import QMainWindow, QLabel, QComboBox, \
                            QToolBar, QPushButton, QAction, \
                            QMenu
from PyQt5.QtGui import QIcon, QPixmap, QImage, qRgb
from PyQt5.QtCore import QPoint
from PyQt5 import uic, QtGui, QtCore
import pyqtgraph as pg
import numpy as np
from scipy.ndimage import gaussian_filter1d
from pyHegel.gui import ScientificSpinBox


class DisplayWidget(QMainWindow):

    def __init__(self, view):
        super(DisplayWidget, self).__init__()
        uic.loadUi('ui/DisplayWindow.ui', self)
        self.view = view
        
        self.filter_state = ['no', 0] # (<'no', 'dx', 'dy'>, sigma)
        self.unfiltered_data = np.random.rand(10, 10)  # raw data, before derivative and transpose
        self.image_rect = (-5, -5, 10, 10) # rectangle for transform: x, y, w, h
        self.x_for_horiz = np.linspace(0, 10, 10) # x axis for horizontal graph
        self.y_for_vert = np.linspace(0, 10, 10) # y axis for vertical graph


        # -- setting up the window --
        # image
        self.main = self.graph.addPlot(row=0, col=0, colspan=2)
        self.main.showGrid(x=True, y=True)
        self.image = pg.ImageItem()
        self.main.addItem(self.image)

        # vertical plot
        self.vertical = self.graph.addPlot(row=1, col=1)
        self.plot_vert = self.vertical.plot()
        # horizontal plot
        self.horizontal = self.graph.addPlot(row=1, col=0)
        self.plot_hor = self.horizontal.plot()
        # plot links
        self.vertical.setYLink(self.main)
        self.horizontal.setXLink(self.main)
        # color bar
        self.bar = pg.ColorBarItem()
        self.bar.rounding = 0.02
        self.bar.setImageItem(self.image, insert_in=self.main)
        # -- toolbars
        self.toolBar2 = QToolBar()
        #self.addToolBarBreak()
        self.addToolBar(self.toolBar2)
        self.toolBar.setContextMenuPolicy(QtCore.Qt.PreventContextMenu)
        self.toolBar2.setContextMenuPolicy(QtCore.Qt.PreventContextMenu)
        # tb1 combobox
        self.toolBar.addWidget(QLabel('Output:'))
        self.cb_out = QComboBox()
        self.cb_out.setMinimumWidth(250)
        self.cb_out.currentIndexChanged.connect(self.onCbOutChanged)
        self.toolBar.addWidget(self.cb_out)
        self.toolBar.addSeparator()
        # tb1 button reset view:
        self.btn_reset_view = QAction('Recenter')
        self.btn_reset_view.triggered.connect(self.main.autoRange)
        self.toolBar.addAction(self.btn_reset_view)
        # reset cbar
        self.btn_reset_bar = self.toolBar.addAction('Reset cbar')
        self.btn_reset_bar.triggered.connect(self.updateBar)
        # transpose:
        self.btn_transpose = self.toolBar.addAction('Transpose')
        self.btn_transpose.setCheckable(True)
        self.btn_transpose.setChecked(False)
        # cursor toolbutton:
        #self.btn_cursor = QAction('Cursor')
        #self.btn_cursor.setCheckable(True)
        #menu = QMenu()
        #menu.addAction('Follow mouse')
        #menu.addAction('Target')
        #self.btn_cursor.setMenu(menu)
        #self.toolBar.addAction(self.btn_cursor)

        # tb2 combobox derivative:
        self.toolBar2.addWidget(QLabel('Derivative:'))
        self.cb_derive = QComboBox()
        self.cb_derive.addItem('No derivative', 'no')
        self.cb_derive.addItem('df/dx', 'dx')
        self.cb_derive.addItem('df/dy', 'dy')
        self.cb_derive.currentIndexChanged.connect(self.filterChange)
        self.toolBar2.addWidget(self.cb_derive)
        # sigma
        self.toolBar2.addWidget(QLabel('Sigma:'))
        self.sb_sigma = ScientificSpinBox.PyScientificSpinBox()
        self.sb_sigma.setRange(1, 100)
        self.toolBar2.addWidget(self.sb_sigma)
        self.sb_sigma.valueChanged.connect(self.filterChange)
        # crosshair
        #self.vline_main = pg.InfiniteLine(angle=90, movable=False)
        #self.hline_main = pg.InfiniteLine(angle=0, movable=False)
        #self.main.addItem(self.vline_main, ignoreBounds=True)
        #self.main.addItem(self.hline_main, ignoreBounds=True)
        #self.target = pg.TargetItem((0,0), symbol='crosshair')
        #self.main.addItem(self.target)
        #self.hline = pg.InfiniteLine(angle=0, movable=True)
        #self.vline = pg.InfiniteLine(angle=90, movable=True)
        #self.vertical.addItem(self.hline, ignoreBounds=True)
        #self.horizontal.addItem(self.vline, ignoreBounds=True)
        #self.hline.sigPositionChanged.connect(lambda: self.onTargetMove(QPoint(self.hline.value(), self.vline.value())))
        #self.vline.sigPositionChanged.connect(lambda: self.onTargetMove(QPoint(self.hline.value(), self.vline.value())))
        #self.target.setZValue(10)
        #self.target.sigPositionChanged.connect(self.onTargetMove)
        #self.target_px_x = 0; self.target_px_y = 0


    # -- core functions --
    def clear(self):
        self.image.clear()
        self.main.setLabel('bottom', '')
        self.main.setLabel('left', '')
        self.horizontal.setLabel('bottom', '')
        self.horizontal.setLabel('left', '')
        self.vertical.setLabel('bottom', '')
        self.vertical.setLabel('left', '')
        self.cb_out.clear()
        #self.target.setPos(0, 0)
         

    def drawRaw(self, data):
        #if np.isnan(data).all(): return

        if self.btn_transpose.isChecked():
            data = self.filter_(data.T, *self.filter_state)
            image_rect = (self.image_rect[1], self.image_rect[0], self.image_rect[3], self.image_rect[2])
        else:
            data = self.filter_(data, *self.filter_state)
            image_rect = self.image_rect

        self.image.setImage(data, autoLevels=False)
        self.image.setRect(*self.image_rect)
    
    #def updateSideGraphs(self):
    #    if self.image.image is None or \
    #       self.x_for_horiz is None or self.y_for_vert is None:
    #        return
    #    data = self.image.image
    #    self.plot_hor.setData(self.x_for_horiz, data[:, self.target_px_y])
    #    self.plot_vert.setData(data[self.target_px_x, :], self.y_for_vert)
    
    def initSweep(self, out_devs, sweep_devs):
        self.clear()
        self.swept_devs = sweep_devs
        # set labels and init axis for side graphs and set target and image rect
        self.main.setLabel('bottom', sweep_devs[0].getDisplayName('long'))
        self.horizontal.setLabel('bottom', sweep_devs[0].getDisplayName('long'))
        self.bar.setLabel('left', out_devs[0].getDisplayName('long'))

        if len(sweep_devs) == 1:
            self.x_for_horiz = np.linspace(sweep_devs[0].sweep[0], sweep_devs[0].sweep[1], sweep_devs[0].sweep[2])
            if sweep_devs[0].sweep[1] < sweep_devs[0].sweep[0]: # reversed sweep
                self.x_for_horiz = np.flip(self.x_for_horiz)
            self.y_for_vert = np.array([0])
            # rectangle for transform: x, y, w, h
            self.image_rect = (min(sweep_devs[0].sweep[:2]), 0,
                          np.abs(sweep_devs[0].sweep[1]-sweep_devs[0].sweep[0]), 1)

        elif len(sweep_devs) == 2:
            self.main.setLabel('left', sweep_devs[1].getDisplayName('long'))
            self.vertical.setLabel('left', sweep_devs[1].getDisplayName('long'))
            self.x_for_horiz = np.linspace(sweep_devs[0].sweep[0], sweep_devs[0].sweep[1], sweep_devs[0].sweep[2])
            self.y_for_vert = np.linspace(sweep_devs[1].sweep[0], sweep_devs[1].sweep[1], sweep_devs[1].sweep[2])
            if sweep_devs[0].sweep[1] < sweep_devs[0].sweep[0]:
                self.x_for_horiz = np.flip(self.x_for_horiz)
            if sweep_devs[1].sweep[1] < sweep_devs[1].sweep[0]:
                self.y_for_vert = np.flip(self.y_for_vert)
            # rectangle for transform: x, y, w, h
            self.image_rect = (min(sweep_devs[0].sweep[:2]), min(sweep_devs[1].sweep[:2]),
                          np.abs(sweep_devs[0].sweep[1]-sweep_devs[0].sweep[0]),
                          np.abs(sweep_devs[1].sweep[1]-sweep_devs[1].sweep[0]))
        # set cb_out
        self.cb_out.currentIndexChanged.disconnect(self.onCbOutChanged)
        self.cb_out.clear()
        for dev in out_devs:
            self.cb_out.addItem(dev.getDisplayName('long'), dev)
        self.cb_out.currentIndexChanged.connect(self.onCbOutChanged)
        self.cb_out.setCurrentIndex(0)
    
    def drawSweep(self):
        data = self.cb_out.currentData().values
        self.unfiltered_data = data
        self.drawRaw(data)


    # -- connected to signals --
    
#    def onTargetMove(self, pos):
#        x, y = pos.x(), pos.y()
#        self.vline_main.setPos(x); self.hline_main.setPos(y)
#        self.vline.setPos(x); self.hline.setPos(y)
#        if self.image.image is None: return
#        self.target_px_x, self.target_px_y = self.coordToPixel(x, y, self.image.image, self.image_rect)
#        self.updateSideGraphs()

    def updateBar(self):
        data = self.image.image
        if data is None: return
        if np.isnan(data).all(): return
        mini, maxi = np.nanmin(data), np.nanmax(data)
        self.bar.setLevels((mini, maxi))
        

    # -- signal from toolbar --
    def filterChange(self):
        self.filter_state = [self.cb_derive.currentData(),
                             self.sb_sigma.value(),
                             self.btn_transpose.isChecked()]
        self.drawRaw(self.unfiltered_data)
    
    def onCbOutChanged(self):
        out_dev = self.cb_out.currentData()
        self.bar.setLabel('left', out_dev.getDisplayName('long'))
        self.drawSweep(self.swept_devs)

    def onCMapChanged(self):
        colormap = pg.colormap.get(self.cb_cmap.currentData())
        self.bar.setColorMap(colormap)
        self.updateBar()
    
    def onTranspose(self, boo):
        self.image_rect = (self.image_rect[1], self.image_rect[0], self.image_rect[3], self.image_rect[2])
        #labels
        tmp = self.main.labelAxis('bottom')

    
    
    # -- events --
    def resizeEvent(self, event):
        QMainWindow.resizeEvent(self, event)
        self.horizontal.setFixedWidth(self.graph.width()/2)
        self.vertical.setFixedWidth(self.graph.width()/2)




    # -- utils (no self) --
    def coordToPixel(self, x, y, data, image_rect):
        # get the pixel index from the coordinates
        if data is None or image_rect is None:
            return 0, 0

        x_index = int((x-image_rect[0])/(image_rect[2]/data.shape[0]))
        y_index = int((y-image_rect[1])/(image_rect[3]/data.shape[1]))
        if x_index > data.shape[0]-1: x_index = data.shape[0]-1
        if y_index > data.shape[1]-1: y_index = data.shape[1]-1
        return x_index, y_index
    
    def filter_(self, data, axis, sigma):
        axis = {'dx': 0, 'dy': 1}.get(axis, -1)
        if axis == -1 or data.shape[axis] == 1:
            return data
        data = gaussian_filter1d(data, sigma=sigma, axis=axis, mode='nearest')
        return np.gradient(data, axis=axis)

        
