from PyQt5.QtWidgets import (
    QMainWindow,
    QTreeWidgetItem,
)
from PyQt5 import QtGui, uic
from PyQt5.QtCore import Qt, QThread, pyqtSignal

from pyHegel.gui import ScientificSpinBox

from src.GuiInstrument import GuiDevice
from widgets.WindowWidget import AltDragWindow

from pyqtgraph.dockarea import DockArea, Dock
from pyqtgraph.widgets import PlotWidget

import numpy as np


# one thread for each monitored device
class MonitorThread(QThread):
    
    update_signal = pyqtSignal(GuiDevice)

    def __init__(self, gui_dev, get_fn, interval):
        super().__init__()
        self.gui_dev = gui_dev
        self.get_fn = get_fn
        self.interval = interval
        self.pause = False
    
    def run(self):
        while True:
            self.msleep(self.interval)
            if self.pause: continue

            # because logical_dev is innacessible when ramping
            # we get the value from the basedev
            # and divide by scale if needed
            dev = self.gui_dev.getPhDev(basedev=True)
            if dev is None: continue
            val = self.get_fn(dev)
            if val is None: continue
            if isinstance(val, (list, tuple)):
                val = val[0]

            factor = self.gui_dev.logical_kwargs['scale'].get('factor', 1)
            val = val / factor
            self.gui_dev.monitor_data = np.roll(self.gui_dev.monitor_data, -1)
            self.gui_dev.monitor_data[-1] = val
            self.update_signal.emit(self.gui_dev)
    

class MonitorObj:
    def __init__(self, lab, gui_dev, interval, dev_item):
        self.lab = lab
        self.gui_dev = gui_dev
        self.dev_item = dev_item # item in tree
        self.spinbox = ScientificSpinBox.PyScientificSpinBox(buttonSymbols=2, readOnly=True)
        font = self.spinbox.font()
        font.setPointSize(14); self.spinbox.setFont(font)
        
        gui_dev.monitor_data = np.full(200, np.nan, dtype=np.float64)
        self.plot = PlotWidget.PlotWidget()
        self.curve = self.plot.plot()
        self.dock = Dock(name=gui_dev.getDisplayName("short"))
        self.dock.addWidget(self.plot)

        get_fn = self.lab.model.getValue
        self.thread = MonitorThread(gui_dev, get_fn, interval)
        self.thread.update_signal.connect(self.update)
        self.thread.start()
    
    def update(self, gui_dev):
        self.curve.setData(gui_dev.monitor_data)
        self.spinbox.setValue(gui_dev.monitor_data[-1])
        self.lab.view_rack.gui_updateDeviceValue(gui_dev, gui_dev.monitor_data[-1])

class MonitorWindow(AltDragWindow):
    def __init__(self, lab):
        super().__init__()
        self.lab = lab

        uic.loadUi("ui/MonitorWindow.ui", self)
        self.setWindowTitle("Monitor")
        self.setWindowIcon(QtGui.QIcon("resources/monitor.svg"))
        
        # ui setup
        self.dock_area = DockArea()
        self.splitter.addWidget(self.dock_area)
        self.splitter.setSizes([300, 500])
        # tree:
        def selectedGuiDev():
            item = self.tree.selectedItem()
            if not item: return
            gui_dev = self.tree.getData(item, 0)
            return gui_dev
        # TODO: fix remove button
        self.btn_remove.clicked.connect(lambda gui_dev=selectedGuiDev(): self.gui_removeDevice(gui_dev=gui_dev))
        def onDrop(data):
            instr_nickname = str(data.data("instrument-nickname"), "utf-8")
            dev_nickname = str(data.data("device-nickname"), "utf-8")
            gui_dev = self.lab.getGuiInstrument(instr_nickname).getGuiDevice(dev_nickname)
            self.addGuiDev(gui_dev)
            return True
        self.tree.dropMimeData = lambda parent, row, data, action: onDrop(data)
    
        self.monitors_dict = {}  # gui_dev: monitor_obj

    def closeEvent(self, event):
        for monitor_obj in self.monitors_dict.values():
            monitor_obj.thread.pause = True
        event.accept()
    
    def showEvent(self, event):
        for monitor_obj in self.monitors_dict.values():
            monitor_obj.thread.pause = False
        event.accept()

    def addGuiDev(self, gui_dev):
        # create and add MonitorDock
        if gui_dev in self.monitors_dict.keys():
            return
        dev_item = QTreeWidgetItem()
        monitor_obj = MonitorObj(self.lab, gui_dev, 200, dev_item)
        self.dock_area.addDock(monitor_obj.dock)

        self.monitors_dict[gui_dev] = monitor_obj
        
        # create and add tree item
        dev_item.setText(0, gui_dev.getDisplayName("short"))
        self.tree.setData(dev_item, gui_dev, 0)
        self.tree.setData(dev_item, monitor_obj, 1)
        self.tree.addTopLevelItem(dev_item)
        self.tree.setItemWidget(dev_item, 1, monitor_obj.spinbox)
        

    def gui_updateDeviceValue(self, gui_dev, value):
        # update the value of a device in the tree
        monitor_obj = self.monitors_dict.get(gui_dev)
        if monitor_obj is None: return
        spinbox = monitor_obj.spinbox
        if not isinstance(value, (float, int)):
            spinbox.setSpecialValueText(str(value))
            spinbox.setValue(spinbox.minimum())
        else:
            spinbox.setValue(gui_dev.cache_value)
    
    def gui_renameDevice(self, gui_dev):
        # rename a device in the tree
        new_nickname = gui_dev.getDisplayName("short")
        monitor_obj = self.monitors_dict.get(gui_dev)
        if monitor_obj is None: return
        monitor_obj.dock.setTitle(new_nickname)
        dev_item = self.tree.findItemByData(monitor_obj)
        dev_item.setText(0, gui_dev.getDisplayName("short"))

    def gui_removeDevice(self, gui_dev):
        monitor_obj = self.monitors_dict.get(gui_dev, None)
        if monitor_obj is None: return
        monitor_obj.thread.terminate()
        monitor_obj.dock.close()
        self.tree.removeByData(gui_dev)
        self.monitors_dict.pop(monitor_obj.gui_dev)