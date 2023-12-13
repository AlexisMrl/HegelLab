from PyQt5.QtWidgets import (
    QMainWindow,
    QTreeWidgetItem,
)
from PyQt5 import QtGui, uic
from PyQt5.QtCore import Qt, QThread, pyqtSignal

from pyHegel.gui import ScientificSpinBox

from src.GuiInstrument import GuiDevice

from pyqtgraph.dockarea import DockArea, Dock
from pyqtgraph.widgets import PlotWidget

import numpy as np


# one thread for each monitored device
class MonitorThread(QThread):
    
    update_signal = pyqtSignal(GuiDevice)

    def __init__(self, gui_dev, get_fn, interval):
        super().__init__()
        self.gui_dev = gui_dev
        self.ph_dev = gui_dev.getPhDev()
        self.get_fn = get_fn
        self.interval = interval
        self.pause = False
    
    def run(self):
        while True:
            self.sleep(self.interval)
            if self.pause: continue

            val = self.get_fn(self.gui_dev)
            if val is None: continue
            if isinstance(val, (list, tuple)):
                val = val[0]
            self.gui_dev.monitor_data = np.roll(self.gui_dev.monitor_data, -1)
            self.gui_dev.monitor_data[-1] = val
            self.update_signal.emit(self.gui_dev)
    

class MonitorObj:
    def __init__(self, gui_dev, get_fn, interval):
        self.gui_dev = gui_dev
        # todo: bigger spinbox font
        self.spinbox = ScientificSpinBox.PyScientificSpinBox(buttonSymbols=2, readOnly=True)
        
        gui_dev.monitor_data = np.full(100, 0)
        self.plot = PlotWidget.PlotWidget()
        self.curve = self.plot.plot()
        self.dock = Dock(name=gui_dev.getDisplayName("short"))
        self.dock.addWidget(self.plot)

        self.thread = MonitorThread(gui_dev, get_fn, interval)
        self.thread.update_signal.connect(self.update)
        self.thread.start()
    
    def update(self, gui_dev):
        self.curve.setData(gui_dev.monitor_data)


class MonitorWindow(QMainWindow):
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
        def tree_onRemove():
            selected = self.tree.selectedItem()
            if not selected: return
            monitor_obj = self.tree.getData(selected)
            monitor_obj.thread.terminate()
            monitor_obj.dock.close()
            self.tree.removeSelected()
            del monitor_obj
        self.btn_remove.clicked.connect(tree_onRemove)
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
        gui_dev_name = gui_dev.getDisplayName("short")
        monitor_obj = MonitorObj(gui_dev, self.lab.getValue, 1)
        self.dock_area.addDock(monitor_obj.dock)

        self.monitors_dict[gui_dev] = monitor_obj
        
        # create and add tree item
        dev_item = QTreeWidgetItem()
        dev_item.setText(0, gui_dev_name)
        dev_item.setData(0, Qt.UserRole, monitor_obj)
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