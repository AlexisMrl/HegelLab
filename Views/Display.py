from PyQt5.QtWidgets import QMainWindow, QLabel, QComboBox
from PyQt5.QtGui import QIcon, QPixmap, QImage, qRgb
from PyQt5 import uic, QtGui
import pyqtgraph as pg
import numpy as np

class Display(QMainWindow):
    # the only view that has some data
    # it keep the swept data in a numpy array
    # and updates the image in the display

    def __init__(self, lab):
        super(Display, self).__init__()
        uic.loadUi('ui/DisplayWindow.ui', self)
        self.setWindowTitle('Live display')
        self.setWindowIcon(QtGui.QIcon('resources/display.svg'))
        self.lab = lab
        
        self.swept_devs = [None, None]
        
        # combobox
        #self.cb_out = QComboBox()
        #self.cb_out.setMinimumWidth(150)
        #self.toolBar.addWidget(self.cb_out)
        # image
        self.main = self.graph.addPlot(row=0, col=0)
        self.main.showGrid(x=True, y=True)
        self.image = pg.ImageItem()
        self.main.addItem(self.image)
        # vertical
        self.vertical = self.graph.addPlot(row=0, col=1)
        self.plot_vert = self.vertical.plot()
        # horizontal
        self.horizontal = self.graph.addPlot(row=1, col=0)
        self.plot_hor = self.horizontal.plot()
        # color bar
        self.bar = pg.ColorBarItem()
        self.bar.setImageItem(self.image, insert_in=self.main)
        # combobox colorbar:
        self.cb_cmap = QComboBox()
        self.cb_cmap.currentTextChanged.connect(lambda: self.bar.setColorMap(pg.colormap.get(self.cb_cmap.currentText())))
        for cm_name in ['CET-D1', 'viridis']:
            pixmap = self.pixmapFromCmName(cm_name)
            self.cb_cmap.addItem(QIcon(pixmap), cm_name)
        self.toolBar.addWidget(self.cb_cmap)
        
        # link things
        self.vertical.setFixedWidth(180)
        self.vertical.setYLink(self.main)
        self.horizontal.setFixedHeight(180)
        self.horizontal.setXLink(self.main)
        
        # crosshair
        self.vline_main = pg.InfiniteLine(angle=90, movable=False)
        self.hline_main = pg.InfiniteLine(angle=0, movable=False)
        self.main.addItem(self.vline_main, ignoreBounds=True)
        self.main.addItem(self.hline_main, ignoreBounds=True)
        self.hline = pg.InfiniteLine(angle=0, movable=False)
        self.vline = pg.InfiniteLine(angle=90, movable=False)
        self.vertical.addItem(self.hline, ignoreBounds=True)
        self.horizontal.addItem(self.vline, ignoreBounds=True)
        self.mouse_col = None
        self.mouse_row = None

        def mouseMoved(evt):
            pos = evt[0] # position in the scene

            # crosshair
            #if self.main.sceneBoundingRect().contains(pos):
            mousePoint = self.main.vb.mapSceneToView(pos)
            x, y = mousePoint.x(), mousePoint.y()
            self.vline.setPos(x); self.hline.setPos(y)
            self.vline_main.setPos(x); self.hline_main.setPos(y)

            # side graphs
            if self.image.image is not None and self.image_rect is not None:
                pos_pixel = self.image.mapFromScene(pos)
                col, row = int(pos_pixel.x()), int(pos_pixel.y())
                self.mouse_col, self.mouse_row = col, row
                self.updateSideGraphs()

        self.proxy = pg.SignalProxy(self.main.scene().sigMouseMoved, rateLimit=60, slot=mouseMoved)
        
        # dummy data, 2d linspace:
        self.data = np.random.random((100, 100))
        # dummy axis:
        self.x_axis = np.linspace(-50, self.data.shape[1], self.data.shape[1])*1e-3
        self.y_axis = np.linspace(-50, self.data.shape[0], self.data.shape[0])*1e-3
        # update image
        self.image.setImage(self.data)
        self.image_rect = (self.x_axis[0],
                            self.y_axis[0],
                            self.x_axis[-1],
                            self.y_axis[-1])
        self.image.setRect(self.image_rect)
        
        
        # no combo box for now
        # only sweep 1d or 2d:
        # sweep 1d: swept_devs[0] is swept, swept_devs[1] is None
    
    def updateSideGraphs(self):
        if self.image.image is None or self.image_rect is None:
            return
        if self.mouse_col is None or self.mouse_row is None:
            return
        if self.mouse_col < 0 or self.mouse_row < 0:
            return
        if self.mouse_col >= self.image.image.shape[0] or \
           self.mouse_row >= self.image.image.shape[1]:
            return
        data = self.image.image
        y_for_vert = np.linspace(self.image_rect[1],
                                 self.image_rect[3],
                                 data.shape[1])
        x_for_horiz = np.linspace(self.image_rect[0],
                                  self.image_rect[2],
                                  data.shape[0])
        self.plot_vert.setData(data[self.mouse_col,:], y_for_vert)
        self.plot_hor.setData(x_for_horiz, data[:,self.mouse_row])

    def update(self, data):
        self.image.setImage(data)
        self.updateSideGraphs()

    def gui_onIteration(self, current_sweep):
        cs = current_sweep
        data = cs.out_devs[0].values
        
        if len(cs.sw_devs) == 1:
            # 1d sweep
            data = data.reshape(len(data), 1)
            if cs.sw_devs[0].sweep[1] < cs.sw_devs[0].sweep[0]:
                # reversed sweep, flip data
                data = np.flip(data, axis=0)
            self.update(data)

            # rectangle for transform: x, y, w, h
            self.image_rect = (min(cs.sw_devs[0].sweep[:2]),
                               0,
                               np.abs(cs.sw_devs[0].sweep[1]-cs.sw_devs[0].sweep[0]),
                               1)
            self.image.setRect(*self.image_rect)
        else:
            # 2d sweep
            data = data.reshape(cs.sw_devs[0].sweep[2],
                                cs.sw_devs[1].sweep[2])
            if cs.sw_devs[0].sweep[1] < cs.sw_devs[0].sweep[0]:
                # reversed sweep, flip data
                data = np.flip(data, axis=0)
            if cs.sw_devs[1].sweep[1] < cs.sw_devs[1].sweep[0]:
                # reversed sweep, flip data
                data = np.flip(data, axis=1)
            self.update(data)

            # rectangle for transform: x, y, w, h
            self.image_rect = (min(cs.sw_devs[0].sweep[:2]),
                               min(cs.sw_devs[1].sweep[:2]),
                               np.abs(cs.sw_devs[0].sweep[1]-cs.sw_devs[0].sweep[0]),
                               np.abs(cs.sw_devs[1].sweep[1]-cs.sw_devs[1].sweep[0]))
            self.image.setRect(*self.image_rect)
        
    def gui_sweepStarted(self, current_sweep):
        self.image.clear()

        self.main.setLabel('bottom', current_sweep.sw_devs[0].display_name)
        if len(current_sweep.sw_devs) == 1:
            self.main.setLabel('left', '')
        elif len(current_sweep.sw_devs) == 2:
            self.main.setLabel('left', current_sweep.sw_devs[1].display_name)


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
                y = 127 - y
                index = int((y/128)*lut.shape[0])
                img.setPixel(x, y, index)
   
        return QPixmap.fromImage(img)
   
