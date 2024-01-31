from PyQt5.QtWidgets import (
    QTreeWidgetItem,
)
from PyQt5 import QtGui, uic
from PyQt5.QtCore import Qt, QThread, pyqtSignal

from pyHegel.gui import ScientificSpinBox

from src.GuiInstrument import GuiDevice
from widgets.WindowWidget import Window

from pyqtgraph.dockarea import DockArea, Dock
from pyqtgraph.widgets import PlotWidget

import numpy as np


# one thread for each monitored device
class MonitorThread(QThread):

    def __init__(self, gui_dev, fn_get):
        super().__init__()
        self.gui_dev = gui_dev
        self.fn_get = fn_get

        from pyHegel.commands import get
        self.get = get

        self.interval = 1000 # in ms
        self.data = np.full(100, np.nan, dtype=np.float64)
        self.pause = False

        self.spinbox = None
        self.curve = None

    def setNbpts(self, new_value):
        if new_value <= 0: return
        if new_value > len(self.data):
            # concatenate new-old,old
            old_length = len(self.data)
            extension = np.full(new_value - old_length, np.nan, dtype=np.float64)
            self.data = np.concatenate([extension, self.data])
            self.updateDisplay()
        elif new_value < len(self.data):
            self.data = self.data[-new_value:]
            self.updateDisplay()
        else: pass
    
    def start_(self):
        self.pause = False
        if not self.isRunning(): self.start()
    
    def run(self):
        while True:
            self.msleep(self.interval)
            if self.pause: continue

            val = self.fn_get(self.gui_dev)
            if isinstance(val, (tuple, list)):
                val = val[0]

            self.data = np.roll(self.data, -1)
            self.data[-1] = val
            self.updateDisplay()
    
    def updateDisplay(self):
        try:
            self.spinbox.setValue(float(self.data[-1]))
            self.curve.setData(self.data)
        except Exception as e:
            # because it may have been deleted
            return

class MonitorWindow(Window):
    def __init__(self, lab):
        super().__init__()
        self.lab = lab
        self.threads = {} # gui_dev:thread

        # ui setup
        uic.loadUi("ui/MonitorWindow.ui", self)
        self.setWindowTitle("Monitor")
        self.setWindowIcon(QtGui.QIcon("resources/monitor.svg"))
        self.dock_area = DockArea()
        self.splitter.addWidget(self.dock_area)
        self.splitter.setSizes([300, 500])
        # end ui setup

        #tree data columns: 0 gui_dev, 1 thread, 2 dock

        # signals:
        self.btn_remove.clicked.connect(self.onRemoveClicked)
        self.tree.guiDeviceDropped.connect(self.onDrop)
    
    
    # -- SHORTCUTS

    def initShortcuts(self):
        super().initShortcuts()
        self.short("x", self.btn_remove.click)
        # Ctrl+a +,  Ctrl+x - interval, 
        self.short("Ctrl+x", lambda: self._setIntervalForSelected('decr'))
        self.short("-", lambda: self._setIntervalForSelected('decr'))
        self.short("Ctrl+a", lambda: self._setIntervalForSelected('incr'))
        self.short("+", lambda: self._setIntervalForSelected('incr'))
        # left/right nbpts
        self.short("Left", lambda: self._setNbptsForSelected('decr'))
        self.short("h", lambda: self._setNbptsForSelected('decr'))
        self.short("Right", lambda: self._setNbptsForSelected('incr'))
        self.short("l", lambda: self._setNbptsForSelected('incr'))

    def closeEvent(self, event):
        #self.pauseAll()
        event.accept()
    
    def focus(self):
        super().focus()
        self.tree.setFocus(True)

    # -- core --
    def _isMonitored(self, gui_dev):
        return self.tree.findItemByData(gui_dev)
    
    def _setPauseAll(self, boo):
        for item in self.tree:
            self.tree.getData(item, 1).setPause(boo)
    
    def onDrop(self, gui_dev, _):
        if not self.tree.findItemByData(gui_dev):
            self.lab.setMonitorDevice(gui_dev, True)
    
    def onRemoveClicked(self):
        gui_dev = self.tree.selectedData()
        if isinstance(gui_dev, GuiDevice):
            self.lab.setMonitorDevice(gui_dev, False)

    def _makeOrUpdateDeviceItem(self, gui_dev):
        thread = self.threads.get(gui_dev, None)
        item_dev = self.tree.findItemByData(gui_dev)
        if not item_dev:
            def makeSpinbox():
                spin = ScientificSpinBox.PyScientificSpinBox(buttonSymbols=2, readOnly=True)
                font = spin.font()
                font.setPointSize(14)
                spin.setFont(font)
                return spin
            
            def makeCurve():
                plot = PlotWidget.PlotWidget()
                plot.getPlotItem().showGrid(True, True)   
                plot.enableAutoRange(axis='xy')
                plot.setAutoVisible(x=True, y=True)
                curve = plot.plot()

                dock = Dock(name=gui_dev.getDisplayName("short", with_instr=True))
                dock.addWidget(plot)
                self.dock_area.addDock(dock)
                return dock, curve

            item_dev = QTreeWidgetItem()
            spinbox = makeSpinbox()
            dock, curve = makeCurve()
            thread = MonitorThread(gui_dev, self.lab.getValue) if not thread else thread
            thread.spinbox, thread.curve, = spinbox, curve
            self.threads[gui_dev] = thread
            thread.start_()

            self.tree.addTopLevelItem(item_dev)
            self.tree.setItemWidget(item_dev, 1, spinbox)
            self.tree.setData(item_dev, gui_dev, 0)
            self.tree.setData(item_dev, dock, 1)

        item_dev.setText(0, gui_dev.getDisplayName("short", with_instr=True))

    def _setIntervalForSelected(self, direction='', amount=100):
        # amount in ms
        gui_dev = self.tree.selectedData()
        thread = self.threads.get(gui_dev, None)
        if isinstance(gui_dev, GuiDevice) and direction in ('decr', 'incr') and thread:
            thread.interval = int(max(100, thread.interval + amount * (-1 if direction == 'decr' else 1)))
    
    def _setNbptsForSelected(self, direction='', amount=50):
        gui_dev = self.tree.selectedData()
        thread = self.threads.get(gui_dev, None)
        if isinstance(gui_dev, GuiDevice) and direction in ('decr', 'incr') and thread:
            thread.setNbpts(int(max(100, len(thread.data) + amount * (-1 if direction == 'decr' else 1))))




    def gui_updateMonitorDevice(self, gui_dev, boo):
        if not boo: self.gui_onDeviceRemoved(gui_dev)
        else:
            self._makeOrUpdateDeviceItem(gui_dev)
    
    def gui_onDeviceRemoved(self, gui_dev):
        item_dev = self.tree.findItemByData(gui_dev)
        if not item_dev: return

        thread = self.threads.get(gui_dev)
        dock = self.tree.getData(item_dev, 1)
        dock.close()
        thread.pause = True
        self.tree.removeByData(gui_dev)
    
    def gui_onDeviceRenamed(self, gui_dev):
        if self.tree.findItemByData(gui_dev):
            self._makeOrUpdateDeviceItem(gui_dev)

    def gui_onInstrumentRenamed(self, gui_instr):
        for gui_dev in gui_instr.gui_devices:
            self.gui_onDeviceRenamed(gui_dev)