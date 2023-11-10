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
        # combobox for data selection
        label = QLabel("Data:")
        self.toolBar.addWidget(label)
        self.cb_out = QComboBox()
        self.cb_out.setObjectName("cb_out")
        self.cb_out.setMinimumWidth(150)
        self.toolBar.addWidget(self.cb_out)
        # display setup
        self.display.setBackground('w')
        self.display.showGrid(x=True, y=True)

        self.init1dPlot('sweep')
        

        # image item
        self.image = pg.ImageItem() 
        self.display.addItem(self.image)
        # colorbar
        self.bar = pg.ColorBarItem()
        cm = pg.colormap.get('CET-D1')
        self.bar.setColorMap(cm)
        self.bar.setImageItem(self.image, insert_in=self.display.getPlotItem())
        
    def onIteration(self):
        self.updateCurrentPlot(self.cb_out.currentData().values)
        
    def onStartSweep(self, gui_sw_devs, gui_out_devs):
        # fill the comboboxes with the names of the devices
        self.cb_out.clear()
        for dev in gui_out_devs:
            self.cb_out.addItem(dev.display_name, dev)
        
        # init the right plot
        if len(gui_sw_devs) == 1:
            self.init1dPlot(gui_sw_devs[0])
        elif len(gui_sw_devs) == 2:
            self.init2dPlot(gui_sw_devs[0], gui_sw_devs[1])
        else:
            print('No live display for more than 2 sweep devices')
            return

        # first output by default
        self.cb_out.setCurrentIndex(0)
        
    def init1dPlot(self, bottom_label):
        self.display.setLabel('left', 'output', units='idk')
        self.display.setLabel('bottom', bottom_label, units='idk')
        self.current_plot = self.display.plot()
        self.updateCurrentPlot = self.update1dPlot
    
    def update1dPlot(self, data):
        self.current_plot.setData(data, connect="finite")
    
    def init2dPlot(self, bottom_label, left_label):
        self.display.setLabel('left', left_label, units='idk')
        self.display.setLabel('bottom', bottom_label, units='idk')
        self.updateCurrentPlot = self.update2dPlot
    
    def update2dPlot(self, data):
        self.image.setImage(data)
        self.bar.setLevels(data.min(), data.max())

        
    