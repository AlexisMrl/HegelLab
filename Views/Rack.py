from PyQt5 import QtGui, uic
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget
from PyQt5.QtWidgets import QPushButton, QVBoxLayout, QHBoxLayout, \
                            QComboBox, QLineEdit, QTreeWidgetItem, \
                            QMessageBox, QAbstractItemView
from src.GuiInstrument import GuiInstrument, GuiDevice

class Rack(QMainWindow):
    def __init__(self, lab):
        super(Rack, self).__init__()
        uic.loadUi('ui/RackWindow.ui', self)
        self.setWindowTitle('Instrument rack')
        self.setWindowIcon(QtGui.QIcon('resources/favicon/favicon.png'))
        self.toolBar.setToolButtonStyle(2) # text beside icon
        self.lab = lab
        
        self.tree.setDragDropMode(QAbstractItemView.DragOnly)

        self.win_add = QMainWindow()
    
        # -- Connect signals to slots --
        self.actionAdd.triggered.connect(self.window_loadInstrument)
        #self.actionRemove.triggered.connect(self.window_removeInstrument)
        #self.actionConfig.triggered.connect(self.onActionConfig)
        self.tree.itemSelectionChanged.connect(self.onSelectionChanged)
        self.tree.itemDoubleClicked.connect(self.onDoubleClick)
        self.dev_get_value.clicked.connect(self.triggerGetValue)
    
    def onSelectionChanged(self):
        data = self.tree.getData(self.tree.selectedItem())
        if isinstance(data, GuiInstrument):
            self.selectIsInstrument()
        elif isinstance(data, GuiDevice):
            self.selectIsDevice()

    def selectIsInstrument(self):
        # when an instrument is selected
        self.actionRemove.setEnabled(True)
        self.actionConfig.setEnabled(True)
        self.dev_get_value.setEnabled(False)
    
    def selectIsDevice(self):
        # when a device is selected
        self.actionRemove.setEnabled(False)
        self.actionConfig.setEnabled(False)
        self.dev_get_value.setEnabled(True)

    def onDoubleClick(self, item, _):
        data = self.tree.getData(item)
        if isinstance(data, GuiInstrument):
            pass
        elif isinstance(data, GuiDevice):
            self.triggerGetValue()
    
    def triggerGetValue(self):
        # ask the lab for the value of the selected device
        selected_item = self.tree.selectedItem()
        gui_dev = self.tree.getData(selected_item)
        self.lab.getValue(gui_dev)
        
    def closeEvent(self, event):
        self.win_add.close()
        event.accept()
    
    # -- windows --
    def window_loadInstrument(self):
        # minimal window for loading device
        self.win_add.setWindowTitle('Add instrument')
        self.win_add.resize(350, 100)
        self.win_add.setWindowIcon(QtGui.QIcon('resources/favicon/favicon.png'))
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
                              self.lab.loadNewInstrument(cb.currentText(),
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
        
    # -- gui_: update the gui -- (called by the lab)
    def gui_addGuiInstrument(self, gui_instr):
        # add an instrument item to self.tree:
        item = QTreeWidgetItem()
        self.tree.setData(item, gui_instr)
        item.setFlags(item.flags() & ~Qt.ItemIsDragEnabled)
        item.setText(0, gui_instr.nickname)
        item.setText(2, gui_instr.address)
        item.setText(3, gui_instr.instr_cls.__name__)
        for gui_dev in gui_instr.gui_devices.values():
            dev_item = QTreeWidgetItem(item)
            self.tree.setData(dev_item, gui_dev)
            dev_item.setText(0, gui_dev.name)
        self.tree.addTopLevelItem(item)
    
    def gui_updateDeviceValue(self, gui_dev, value):
        # update the value of the item corresponding to gui_dev
        dev_item = self.tree.findItemByData(gui_dev)
        dev_item.setText(1, str(value))
    # -- end gui_ --