from PyQt5 import QtGui, uic
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget
from PyQt5.QtWidgets import QPushButton, QVBoxLayout, QHBoxLayout, \
                            QComboBox, QLineEdit, QTreeWidgetItem, \
                            QMessageBox, QAbstractItemView


class Rack(QMainWindow):
    def __init__(self, lab):
        super(Rack, self).__init__()
        uic.loadUi('ui/RackWindow.ui', self)
        self.setWindowTitle('Instrument rack')
        self.setWindowIcon(QtGui.QIcon('resources/favicon/favicon.png'))
        self.toolBar.setToolButtonStyle(2) # text beside icon
        self.lab = lab
        
        self.tree.setDragDropMode(QAbstractItemView.DragOnly)
    
        # -- Connect signals to slots --
        self.actionAdd.triggered.connect(self.window_loadInstrument)
        self.actionRemove.triggered.connect(self.window_removeInstrument)
        self.tree.itemSelectionChanged.connect(self.selectionChanged)
        self.tree.itemDoubleClicked.connect(self.ask_getValue)
        self.dev_get_value.clicked.connect(self.ask_getValue)

    def selectionChanged(self):
        selected = self.tree.selectedItem()
        # check if selected is a device or an instrument
        # and update gui
        if selected is None:
            return
        if selected.parent() is None:
            self.gui_selectInstrument()
        else:
            self.gui_selectDevice()
    
    def getItemFromDevice(self, instr_name, dev_name):
        # return the item of a device
        for i in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(i)
            if item.text(0) == instr_name:
                for j in range(item.childCount()):
                    dev_item = item.child(j)
                    if dev_item.text(0) == dev_name:
                        return dev_item
        return None
    
    # -- windows --
    def window_loadInstrument(self):
        # minimal window for loading device
        self.win_add = QMainWindow(); self.win_add.setWindowTitle('Add instrument')
        wid = QWidget(); self.win_add.setCentralWidget(wid)
        layout = QVBoxLayout(); wid.setLayout(layout)
        
        # combobox
        cb = QComboBox()
        cb.addItems(self.lab.supported_instruments.keys())
        layout.addWidget(cb)

        # line edit for address and name
        le_address = QLineEdit(); le_address.setPlaceholderText('Address')
        le_name = QLineEdit(); le_name.setPlaceholderText('Name')
        layout.addWidget(le_address)
        layout.addWidget(le_name)

        # ok and cancel buttons in a horizontal layout
        bt_ok = QPushButton('Load')
        bt_cancel = QPushButton('Cancel')
        Hlayout = QHBoxLayout()
        Hlayout.addWidget(bt_ok)
        Hlayout.addWidget(bt_cancel)
        layout.addLayout(Hlayout)

        # connect signals to slots
        bt_ok.clicked.connect(lambda:
                              self.lab.loadAndAddInstrument(cb.currentText(),
                                                            le_name.text(),
                                                            le_address.text()))
        bt_cancel.clicked.connect(self.win_add.close)

        self.win_add.show()

    def window_removeInstrument(self):
        # msgbox to confirm the removal
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Question)
        msg.setText("Are you sure you want to remove this instrument?")
        msg.setWindowTitle("Remove instrument")
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        if msg.exec_() == QMessageBox.Yes:
            selected_item = self.tree.selectedItem()
            if selected_item is not None:
                self.lab.unloadAndRemoveInstrument(selected_item.text(0))
    # -- end windows --
        
    # -- gui_: update the gui --
    def gui_selectInstrument(self):
        # when an instrument is selected
        self.actionRemove.setEnabled(True)
        self.actionConfig.setEnabled(True)
        self.dev_get_value.setEnabled(False)
    
    def gui_selectDevice(self):
        # when a device is selected
        self.actionRemove.setEnabled(False)
        self.actionConfig.setEnabled(False)
        self.dev_get_value.setEnabled(True)

    def gui_addGuiInstrument(self, gui_instr):
        # add an instrument item to self.tree:
        item = QTreeWidgetItem(self.tree)
        item.setFlags(item.flags() & ~Qt.ItemIsDragEnabled)
        item.setText(0, gui_instr.name)
        item.setText(2, gui_instr.address)
        item.setText(3, gui_instr.instr_cls.__name__)
        for name, dev in gui_instr.devices.items():
            dev_item = QTreeWidgetItem(item)
            dev_item.setText(0, name)
    
    def gui_removeInstrument(self):
        self.removeSelected()
    
    def gui_updateDeviceValue(self, nickname, dev_name, value):
        # find the device item
        dev_item = self.getItemFromDevice(nickname, dev_name)
        if dev_item is None: return
        # update the value
        dev_item.setText(1, str(value))
    # -- end gui_ --
    
    # -- ask_: ask the lab to do something --
    def ask_getValue(self):
        # get value of the selected item
        # only if it is a device
        selected = self.tree.selectedItem()
        if selected is None: return
        if selected.parent() is not None:
            self.lab.getValueAndUpdateRack(selected.parent().text(0),
                                          selected.text(0))

