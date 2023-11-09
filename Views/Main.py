from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, \
                            QLineEdit, QTreeWidgetItem, QGridLayout, \
                            QSpinBox, QLabel, QPushButton
from PyQt5 import QtCore, QtGui, uic
from pyHegel.gui import ScientificSpinBox

class Main(QMainWindow):
    def __init__(self, lab):
        super(Main, self).__init__()
        # -- ui setup --
        uic.loadUi('ui/MainWindow.ui', self)
        self.setWindowTitle('HegelLab')
        self.setWindowIcon(QtGui.QIcon('resources/favicon/favicon.png'))
        self.toolBar.setToolButtonStyle(2) # text beside icon
        # add a line edit in the toolbar for filename (not possible from designer):
        self.filename_edit = QLineEdit()
        self.filename_edit.setObjectName('filename_edit')
        self.filename_edit.setPlaceholderText('filename')
        self.filename_edit.setFixedWidth(200)
        self.toolBar.addWidget(self.filename_edit)
        # -- end ui setup --
        self.lab = lab
        self.tree_sw.dropMimeData = lambda parent, row, data, action: \
            self.onDrop(self.tree_sw, parent, row, data, action)
        self.tree_out.dropMimeData = lambda parent, row, data, action: \
            self.onDrop(self.tree_out, parent, row, data, action)
        self.tree_log.dropMimeData = lambda parent, row, data, action: \
            self.onDrop(self.tree_log, parent, row, data, action)

        # -- windows --
        self.win_sw_setup = QMainWindow()

        # -- Connect signals to slots --
        self.actionInstruments.triggered.connect(self.lab.showRack)
        self.actionDisplay.triggered.connect(self.lab.showDisplay)
        # trees:
        self.tree_sw.itemSelectionChanged.connect(self.onSweepSelectionChanged)
        self.tree_out.itemSelectionChanged.connect(self.onOutSelectionChanged)
        self.tree_log.itemSelectionChanged.connect(self.onLogSelectionChanged)
        self.sw_remove.clicked.connect(self.tree_sw.removeSelected)
        self.out_remove.clicked.connect(self.tree_out.removeSelected)
        self.log_remove.clicked.connect(self.tree_log.removeSelected)
        self.tree_sw.itemDoubleClicked.connect(self.triggerShowSweepConfig)
        
        # sweep:
        self.actionStartSweep.triggered.connect(self.onStartSweep)

    def onDrop(self, tree, parent, row, data, action):
        # what happens when the item is dropped
        # extract data:
        instr_name = str(data.data('instrument-name'), 'utf-8')
        dev_name = str(data.data('device-name'), 'utf-8')
        if tree == self.tree_sw:
            self.lab.addSweepDev(instr_name, dev_name)
        elif tree == self.tree_out:
            self.lab.addOutputDev(instr_name, dev_name)
        elif tree == self.tree_log:
            self.lab.addLogDev(instr_name, dev_name)
        return True
    
    def onSweepSelectionChanged(self):
        selected = self.tree_sw.selectedItem()
        self.sw_remove.setEnabled(selected is not None)
    
    def onOutSelectionChanged(self):
        selected = self.tree_out.selectedItem()
        self.out_remove.setEnabled(selected is not None)
    
    def onLogSelectionChanged(self):
        selected = self.tree_log.selectedItem()
        self.log_remove.setEnabled(selected is not None)
    
    def triggerShowSweepConfig(self, item, _):
        # ask the lab to show the sweep config window for the selected device
        selected = self.tree_sw.selectedItem()
        gui_dev = self.tree_sw.getData(selected)
        self.lab.showSweepConfig(gui_dev)
    
    def onStartSweep(self):
        self.lab.startSweep()
    
    def closeEvent(self, event):
        if self.lab.close():
            event.accept()
        else:
            event.ignore()
    
    # -- windows --
    def window_configSweep(self, gui_dev):
        # minimal window for defining sweep start, stop, step:
        display_name = gui_dev.display_name
        self.win_sw_setup.setWindowTitle('Setup sweep ' + display_name)
        self.win_sw_setup.setWindowIcon(QtGui.QIcon('resources/favicon/favicon.png'))
        wid = QWidget(); self.win_sw_setup.setCentralWidget(wid)
        layout = QGridLayout(); wid.setLayout(layout)
        
        # widgets:
        label_start = QLabel('Start:')
        label_stop = QLabel('Stop:')
        label_step = QLabel('# pts:')
        spin_start = ScientificSpinBox.PyScientificSpinBox()
        spin_stop = ScientificSpinBox.PyScientificSpinBox()
        spin_npts = QSpinBox()
        spin_npts.setMaximum(1000000)
        ok_button = QPushButton('Ok')
        
        # set values if not None:
        sweep_values = gui_dev.sweep
        if sweep_values[0] is not None:
            spin_start.setValue(sweep_values[0])
        if sweep_values[1] is not None:
            spin_stop.setValue(sweep_values[1])
        if sweep_values[2] is not None:
            spin_npts.setValue(sweep_values[2])
        
        # add to layout:
        layout.addWidget(label_start, 0, 0)
        layout.addWidget(label_stop, 1, 0)
        layout.addWidget(label_step, 2, 0)
        layout.addWidget(spin_start, 0, 1)
        layout.addWidget(spin_stop, 1, 1)
        layout.addWidget(spin_npts, 2, 1)
        layout.addWidget(ok_button, 3, 1)
        
        # connect signals:
        ok_button.clicked.connect(lambda: self.lab.setSweepValues(
            gui_dev,
            spin_start.value(),
            spin_stop.value(),
            spin_npts.value(),
        ))
        # on close:
        self.win_sw_setup.closeEvent = lambda event: self.setEnabled(True)

        self.win_sw_setup.show()
    # -- end windows --
    
    # -- gui -- (called by the lab)
    def _gui_makeItem(self, tree, gui_dev):
        item = QTreeWidgetItem()
        item.setChildIndicatorPolicy(QTreeWidgetItem.DontShowIndicatorWhenChildless)
        item.setText(0, gui_dev.display_name)
        tree.setData(item, gui_dev)
        tree.addTopLevelItem(item)
        
    def gui_addSweepGuiDev(self, gui_dev):
        # add item to the sweep tree:
        self._gui_makeItem(self.tree_sw, gui_dev)
    
    def gui_addOutItem(self, gui_dev):
        # add item to the output tree:
        self._gui_makeItem(self.tree_out, gui_dev)
    
    def gui_addLogItem(self, gui_dev):
        # add item to the log tree:
        self._gui_makeItem(self.tree_log, gui_dev)
    
    def gui_updateSweepValues(self, gui_dev):
        # set sweep values to self.tree_sw.selectedItem()
        dev_item = self.tree_sw.findItemByData(gui_dev)
        dev_item.setText(1, str(gui_dev.sweep[2]))
        dev_item.setText(2, str(gui_dev.sweep[:2]))
    
    def gui_getSweepValues(self):
        # go through self.tree_sw and return devs, start, stop, npts
        devs, start, stop, npts = [], [], [], []
        for item in self.tree_sw:
            gui_dev = self.tree_sw.getData(item)
            devs.append(gui_dev.ph_dev)
            start.append(gui_dev.sweep[0])
            stop.append(gui_dev.sweep[1])
            npts.append(gui_dev.sweep[2])
        return devs, start, stop, npts
    
    def gui_getOutputDevs(self):
        devs = []
        for item in self.tree_out:
            gui_dev = self.tree_out.getData(item)
            devs.append(gui_dev.ph_dev)
        return devs
    
    def gui_getLogDevs(self):
        devs = []
        for item in self.tree_log:
            gui_dev = self.tree_log.getData(item)
            devs.append(gui_dev.ph_dev)
        return devs
    # -- end gui --

