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
        self.filename_edit.setPlaceholderText('filename')
        self.filename_edit.setFixedWidth(200)
        self.toolBar.addWidget(self.filename_edit)
        # -- end ui setup --
        self.lab = lab
        self.tree_sw.dropMimeData = lambda parent, row, data, action: \
            self.onDrop(self.tree_sw, parent, row, data, action)
        self.tree_out.dropMimeData = lambda parent, row, data, action: \
            self.onDrop(self.tree_out, parent, row, data, action)


        # -- Connect signals to slots --
        self.actionInstruments.triggered.connect(self.lab.showRack)
        self.actionDisplay.triggered.connect(self.lab.showDisplay)
        # trees:
        self.tree_sw.itemSelectionChanged.connect(self.gui_selectionSweepChanged)
        self.tree_out.itemSelectionChanged.connect(self.gui_selectionOutChanged)
        self.sw_remove.clicked.connect(self.tree_sw.removeSelected)
        self.out_remove.clicked.connect(self.tree_out.removeSelected)
        self.tree_sw.itemDoubleClicked.connect(self.lab.showSweepConfig)
        
        # sweep:
        self.actionStartSweep.triggered.connect(self.lab.onStartSweep)

    def onDrop(self, tree, parent, row, data, action):
        # what happens when the item is dropped
        # extract data:
        instr_name = str(data.data('instrument-name'), 'utf-8')
        dev_name = str(data.data('device-name'), 'utf-8')
        if tree == self.tree_sw:
            self.lab.addSweepDev(instr_name, dev_name)
        elif tree == self.tree_out:
            self.lab.addOutputDev(instr_name, dev_name)
        return True
    
    # -- windows --
    def window_configSweep(self):
        # minimal window for defining sweep start, stop, step:
        self.win_sw_setup = QMainWindow()
        fullname = self.tree_sw.selectedItem().text(0)
        self.win_sw_setup.setWindowTitle('Setup sweep ' + fullname)
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
            self.tree_sw.selectedItemData()['instrument'],
            self.tree_sw.selectedItemData()['device'],
            spin_start.value(),
            spin_stop.value(),
            spin_npts.value(),
        ))
        # on close:
        self.win_sw_setup.closeEvent = lambda event: self.setEnabled(True)

        self.win_sw_setup.show()
    # -- end windows --
    
    # -- gui --
    def gui_selectionSweepChanged(self):
        selected = self.tree_sw.selectedItem()
        self.sw_remove.setEnabled(selected is not None)
    
    def gui_selectionOutChanged(self):
        selected = self.tree_out.selectedItem()
        self.out_remove.setEnabled(selected is not None)

    def _gui_makeItem(self, tree, name, data):
        item = QTreeWidgetItem(tree)
        item.setChildIndicatorPolicy(QTreeWidgetItem.DontShowIndicatorWhenChildless)
        item.setText(0, name)
        item.setData(0, QtCore.Qt.UserRole, data)
        tree.addTopLevelItem(item)
        
    def gui_addSweepItem(self, name, data):
        # add item to the sweep tree:
        self._gui_makeItem(self.tree_sw, name, data)
    
    def gui_addOutItem(self, name, data):
        # add item to the output tree:
        self._gui_makeItem(self.tree_out, name, data)
    
    def gui_setSweepValues(self, start, stop, npts):
        # set sweep values to self.tree_sw.selectedItem()
        item = self.tree_sw.selectedItem()
        self.tree_sw.addData(item, {'sweep_values':[start, stop, npts]})
        item.setText(1, str(npts))
        item.setText(2, str([start, stop]))
    # -- end gui --

