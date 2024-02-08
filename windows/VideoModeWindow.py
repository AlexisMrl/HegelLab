from PyQt5 import uic
from PyQt5.QtWidgets import QPushButton, QTreeWidgetItem
from pyHegel.gui import ScientificSpinBox
from widgets.WindowWidget import Window
import pyqtgraph as pg


class VideoModeWindow(Window):
    # proof of concept for video mode.
    # fixed step for param and sweep devs
    
    # video mode is not the same as live display
    # it does the full sweep, THEN display the data
    def __init__(self, lab):
        super().__init__()
        uic.loadUi("ui/VideoModeWindow.ui", self)
        self.setWindowTitle("Video mode - Pre-pre alpha, proof of concept")
        self.lab = lab
        
        self.plot = self.graph.addPlot(row=0, col=0)
        self.image = pg.ImageItem()
        self.plot.addItem(self.image)

        #self.tree.hide() # for now
        self.splitter.setSizes([400,250])
        self.tree.setColumnWidth(0,75)
        self.tree.setColumnWidth(1,50)
        self.tree.setColumnWidth(3,50)

        self.btn_play.clicked.connect(self.onPlay)
        self.btn_left.clicked.connect(self.onLeft)
        self.btn_right.clicked.connect(self.onRight)
        self.btn_up.clicked.connect(self.onUp)
        self.btn_down.clicked.connect(self.onDown)
        
        self.tree.guiDeviceDropped.connect(self.onDrop)

        # dimension:
        #self.resize(1000, 500)
    def _move(self, x, y):
        t = self.lab.video_thread
        t.new_bound = True
        t.start_[0] += x*t.step[0]
        t.stop[0] += x*t.step[0]
        t.start_[1] += y*t.step[1]
        t.stop[1] += y*t.step[1]
        
    def onLeft(self):
        self._move(-self.spin_nbpts.value(), 0)
    def onRight(self):
        self._move(self.spin_nbpts.value(), 0)
    def onUp(self):
        self._move(0, self.spin_nbpts.value())
    def onDown(self):
        self._move(0, -self.spin_nbpts.value())
    
    def onPlay(self):
        t = self.lab.video_thread
        if t.running:
            t.running = False
            self.btn_play.setText("Play")
        else:
            t.running = True
            self.btn_play.setText("Pause")
    
    def closeEvent(self, event):
        self.btn_play.click()
        event.accept()
        
    def onDrop(self, gui_dev):
        self._makeOrUpdateDeviceItem(gui_dev)
    
    def _makeOrUpdateDeviceItem(self, gui_dev):
        item_dev = None
        for i in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(i)
            if self.tree.getData(item, 0) == gui_dev:
                item_dev = item
                break
        if not item_dev:
            btn_plus = QPushButton("+")
            btn_minus = QPushButton("-")
            spin = ScientificSpinBox.PyScientificSpinBox(buttonSymbols=2, readOnly=True)
            spin.setValue(self.lab.getValue(gui_dev))
            
            def setValue(new_val):
                self.lab.setValue(gui_dev, new_val)
                spin.setValue(new_val)
            btn_plus.clicked.connect(lambda: setValue(self.lab.getValue(gui_dev) + 0.1))
            btn_minus.clicked.connect(lambda: setValue(self.lab.getValue(gui_dev) - 0.1))

            item_dev = QTreeWidgetItem()
            self.tree.addTopLevelItem(item_dev)
            #self.tree.setData(item_dev, gui_dev, 0)
            #self.tree.setData(item_dev, spin, 2)
            self.tree.setItemWidget(item_dev, 1, btn_minus)
            self.tree.setItemWidget(item_dev, 2, spin)
            self.tree.setItemWidget(item_dev, 3, btn_plus)

        # TODO: connect to signal onValueGet
        item_dev.setText(0, gui_dev.getDisplayName("short"))
    
    def gui_onFrameReady(self, gui_dev):
        # called by the gui when a frame is ready
        self.image.setImage(gui_dev.values)
        t = self.lab.video_thread
        x, y, w, h = t.start_[0], t.start_[1], t.stop[0] - t.start_[0], t.stop[1] - t.start_[1]
        self.image.setRect(x, y, w, h)


        