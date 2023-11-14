from PyQt5.QtWidgets import QMainWindow, QLabel, QComboBox, \
                            QToolBar, QPushButton
from PyQt5.QtGui import QIcon, QPixmap, QImage, qRgb
from PyQt5 import uic, QtGui
import pyqtgraph as pg
import numpy as np
from scipy.ndimage import gaussian_filter1d
from pyHegel.gui import ScientificSpinBox


class Display(QMainWindow):

    def __init__(self, lab):
        super(Display, self).__init__()
        uic.loadUi('ui/DisplayWindow.ui', self)
        self.setWindowTitle('Live display')
        self.setWindowIcon(QtGui.QIcon('resources/display.svg'))
        self.lab = lab
        
        self.swept_devs = [None, None]
        self.filter_state = ['no', 0] # (<'no', 'dx', 'dy'>, sigma)
        self.unfiltered_data = None # raw data, before derivative
        self.x_for_horiz = None # x axis for horizontal graph
        self.y_for_vert = None # y axis for vertical graph

        self.toolBar2 = QToolBar()
        self.addToolBarBreak()
        self.addToolBar(self.toolBar2)
        # combobox
        self.toolBar.addWidget(QLabel('Output:'))
        self.cb_out = QComboBox()
        self.cb_out.setMinimumWidth(150)
        self.cb_out.currentIndexChanged.connect(self.onCbOutChanged)
        self.toolBar.addWidget(self.cb_out)
        # image
        self.main = self.graph.addPlot(row=0, col=0)
        self.main.showGrid(x=True, y=True)
        self.image = pg.ImageItem()
        self.main.addItem(self.image)
        # vertical
        self.vertical = self.graph.addPlot(row=0, col=1)
        self.plot_vert = self.vertical.plot()
        self.vertical.setFixedWidth(180)
        self.vertical.setYLink(self.main)
        # horizontal
        self.horizontal = self.graph.addPlot(row=1, col=0)
        self.plot_hor = self.horizontal.plot()
        self.horizontal.setFixedHeight(180)
        self.horizontal.setXLink(self.main)
        # color bar
        self.bar = pg.ColorBarItem()
        self.bar.rounding = 0.02
        self.bar.setImageItem(self.image, insert_in=self.main)
        # combobox colorbar:
        self.cb_cmap = QComboBox()
        for cm_name in ['viridis', 'CET-D1']:
            pixmap = self.pixmapFromCmName(cm_name)
            self.cb_cmap.addItem(QIcon(pixmap), '')
            self.cb_cmap.setItemData(self.cb_cmap.count()-1, cm_name)
        self.cb_cmap.currentTextChanged.connect(self.onCMapChanged)
        self.cb_cmap.setCurrentIndex(1)
        self.toolBar.addSeparator()
        self.toolBar.addWidget(self.cb_cmap)
        # button reset bar:
        self.btn_reset_bar = QPushButton('Min/max bar')
        self.btn_reset_bar.clicked.connect(self.updateBar)
        self.toolBar.addWidget(self.btn_reset_bar)
        # combobox derivative:
        self.toolBar2.addWidget(QLabel('Derivative:'))
        self.cb_derive = QComboBox()
        self.cb_derive.addItem('No derivative', 'no')
        self.cb_derive.addItem('df/dx', 'dx')
        self.cb_derive.addItem('df/dy', 'dy')
        self.cb_derive.currentIndexChanged.connect(self.onDerivChanged)
        self.toolBar2.addWidget(self.cb_derive)
        # sigma
        self.toolBar2.addSeparator()
        self.toolBar2.addWidget(QLabel('Sigma:'))
        self.sb_sigma = ScientificSpinBox.PyScientificSpinBox()
        self.sb_sigma.setRange(1, 100)
        self.toolBar2.addWidget(self.sb_sigma)
        self.sb_sigma.valueChanged.connect(self.onDerivChanged)
        # crosshair
        self.vline_main = pg.InfiniteLine(angle=90, movable=False)
        self.hline_main = pg.InfiniteLine(angle=0, movable=False)
        self.main.addItem(self.vline_main, ignoreBounds=True)
        self.main.addItem(self.hline_main, ignoreBounds=True)
        self.target = pg.TargetItem((0,0), symbol='crosshair')
        self.main.addItem(self.target)
        self.hline = pg.InfiniteLine(angle=0, movable=False)
        self.vline = pg.InfiniteLine(angle=90, movable=False)
        self.vertical.addItem(self.hline, ignoreBounds=True)
        self.horizontal.addItem(self.vline, ignoreBounds=True)
        self.target.setZValue(10)
        self.target.sigPositionChanged.connect(self.onTargetMove)
        self.target_px_x = 0; self.target_px_y = 0

        
        # dummy data, 2d linspace:
        data = np.random.random((100, 50))
        self.unfiltered_data = data
        # dummy axis:
        self.x_for_horiz = np.linspace(0, 1, data.shape[0])
        self.y_for_vert = np.linspace(0, 1, data.shape[1])
        x_axis = np.linspace(0, 1, data.shape[0])
        y_axis = np.linspace(0, 1, data.shape[1])
        # update image
        self.image.setImage(data)
        self.image_rect = (x_axis[0],
                           y_axis[0],
                           x_axis[-1],
                           y_axis[-1])
        self.image.setRect(self.image_rect)


    # -- core functions --
    def clear(self):
        self.image.clear()
        self.image_rect = None
        self.x_for_horiz = None
        self.y_for_vert = None
        # TODO clear labels

    def drawImage(self, data, auto_range=False):
        if data is None: return
        if np.isnan(data).all(): return

        data = self.derive(data, *self.filter_state)

        self.image.setImage(data, autoLevels=False)
        self.image.setRect(*self.image_rect)

        if auto_range: self.main.autoRange()

    def drawVertical(self, x, y):
        self.plot_vert.setData(x, y)
    
    def drawHorizontal(self, x, y):
        self.plot_hor.setData(x, y)

    def updateBar(self):
        data = self.image.image
        if data is None: return
        if np.isnan(data).all(): return
        mini, maxi = np.nanmin(data), np.nanmax(data)
        self.bar.setLevels((mini, maxi))
    
    def updateSideGraphs(self):
        if self.image.image is None or \
           self.x_for_horiz is None or self.y_for_vert is None:
            return
        data = self.image.image
        self.drawHorizontal(self.x_for_horiz, data[:, self.target_px_y])
        self.drawVertical(data[self.target_px_x, :], self.y_for_vert)


    # -- connected to Display signals --
    def onCMapChanged(self):
        colormap = pg.colormap.get(self.cb_cmap.currentData())
        self.bar.setColorMap(colormap)
        self.updateBar()
    
    def onCbOutChanged(self):
        out_dev = self.cb_out.currentData()
        self.bar.setLabel('left', out_dev.getDisplayName('long'))
        self.drawSweep(out_dev, self.swept_devs)
    
    def onDerivChanged(self):
        self.filter_state = [self.cb_derive.currentData(), self.sb_sigma.value()]
        # unfilter data so that it's not filtered twice
        self.drawImage(self.unfiltered_data)
        self.updateSideGraphs()
        self.updateBar()
    
    def onTargetMove(self, pos):
        x, y = pos.x(), pos.y()
        self.vline_main.setPos(x); self.hline_main.setPos(y)
        self.vline.setPos(x); self.hline.setPos(y)
        self.target_px_x, self.target_px_y = self.coordToPixel(x, y, self.image.image, self.image_rect)
        self.updateSideGraphs()

        

    # -- on sweep signals --
    def onIteration(self, current_sweep):
        out_dev = self.cb_out.currentData()
        self.drawSweep(out_dev, current_sweep.sw_devs)
        
    def onSweepStarted(self, current_sweep):
        self.initSweep(current_sweep.out_devs, current_sweep.sw_devs)

    def initSweep(self, out_devs, sweep_devs):
        self.clear()
        self.swept_devs = sweep_devs
        # set labels and init axis for side graphs and set target and image rect
        self.main.setLabel('bottom', sweep_devs[0].getDisplayName('long'))
        self.horizontal.setLabel('bottom', sweep_devs[0].getDisplayName('long'))
        self.bar.setLabel('left', out_devs[0].getDisplayName('long'))
        if len(sweep_devs) == 1:
            self.main.setLabel('left', '')
            self.vertical.setLabel('left', '')
            self.x_for_horiz = np.linspace(sweep_devs[0].sweep[0], sweep_devs[0].sweep[1], sweep_devs[0].sweep[2])
            if sweep_devs[0].sweep[1] < sweep_devs[0].sweep[0]: # reversed sweep
                self.x_for_horiz = np.flip(self.x_for_horiz)
            self.y_for_vert = np.array([0])
            self.target.setPos(sweep_devs[0].sweep[0], 0)
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
            self.target.setPos(sweep_devs[0].sweep[0], sweep_devs[1].sweep[0])
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
        # draw empty image
        #self.drawSweep(out_devs[0], sweep_devs, auto_range=True)

    def drawSweep(self, out_dev, sweep_devs):
        if len(sweep_devs) == 1:
            data = out_dev.values.reshape(len(sweep_devs[0].values), 1)
            # check if reversed sweep
            if sweep_devs[0].sweep[1] < sweep_devs[0].sweep[0]: data = np.flip(data, axis=0)
        elif len(sweep_devs) == 2:
            data = out_dev.values.reshape(sweep_devs[0].sweep[2], sweep_devs[1].sweep[2])
            # reversed sweep, flip data
            if sweep_devs[0].sweep[1] < sweep_devs[0].sweep[0]: data = np.flip(data, axis=0)
            if sweep_devs[1].sweep[1] < sweep_devs[1].sweep[0]: data = np.flip(data, axis=1)
        self.unfiltered_data = data
        # draw
        self.drawImage(data)
        self.updateBar()
        self.updateSideGraphs()



    # -- utils (no self) --
    def pixmapFromCmName(self, name):
        cm = pg.colormap.get(name)
        lut = cm.getLookupTable(0.0, 1.0, 128)
        img = QImage(128, 128, QImage.Format_Indexed8)
   
        for i in range(lut.shape[0]):
            color = qRgb(lut[i, 0], lut[i, 1], lut[i, 2])
            img.setColor(i, color)
   
        for x in range(128):
            for y in range(128):
                index = int(((127-y)/128)*lut.shape[0])
                img.setPixel(x, y, index)
   
        return QPixmap.fromImage(img)

    def coordToPixel(self, x, y, data, image_rect):
        # get the pixel index from the coordinates
        if data is None or image_rect is None:
            return 0, 0

        x_index = int((x-image_rect[0])/(image_rect[2]/data.shape[0]))
        y_index = int((y-image_rect[1])/(image_rect[3]/data.shape[1]))
        if x_index > data.shape[0]-1: x_index = data.shape[0]-1
        if y_index > data.shape[1]-1: y_index = data.shape[1]-1
        return x_index, y_index
    
    def derive(self, data, axis, sigma):
        if sigma == 0:
            return data
        axis = {'dx': 0, 'dy': 1}.get(axis, -1)
        if axis == -1 or data.shape[axis] == 1:
            return data
        data = gaussian_filter1d(data, sigma=sigma, axis=axis, mode='nearest')
        return np.gradient(data, axis=axis)

        
