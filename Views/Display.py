from PyQt5.QtWidgets import QMainWindow, QLabel, QComboBox
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
        self.setWindowIcon(QtGui.QIcon('resources/favicon/favicon.png'))
        self.lab = lab
        
        # ui (things not possible in QtDesigner)
        label = QLabel("Data:")
        self.toolBar.addWidget(label)
        cb = QComboBox()
        cb.setObjectName("cb_data")
        cb.setMinimumWidth(150)
        self.toolBar.addWidget(cb)
        
        self.show() # for debug only, quick launch
        self.raise_() # same
        
        # Create the ImageItem
        self.data = np.full((100, 100), np.nan, dtype=float)
        self.img = pg.ImageItem(image=self.data)  # Create the ImageItem once
        self.display.addItem(self.img)
        
        self.display.setBackground('w')

        # Create the ColorBarItem
        self.bar = pg.ColorBarItem(values=(-10, 10), cmap=pg.colormap.get('CET-D9'))
        #self.bar.setImageItem(self.img, insert_in=self.display.getPlotItem())

        
    def setDataDimensions(self, x, y):
        del self.data
        self.data = np.full((x, y), np.nan, dtype=float)
        self.img.updateImage()
    
    def addXYval(self, x, y=0, val=0):
        self.data[x, y] = val
        self.img.updateImage()
    