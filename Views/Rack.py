from PyQt5 import QtGui, uic
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget
from PyQt5.QtWidgets import QPushButton, QVBoxLayout, QHBoxLayout, \
                            QComboBox, QLineEdit, QTreeWidgetItem, \
                            QMessageBox, QAbstractItemView
from PyQt5.QtGui import QFont, QFontDatabase
from src.GuiInstrument import GuiInstrument, GuiDevice

class Rack(QMainWindow):
    def __init__(self, lab):
        super(Rack, self).__init__()
        uic.loadUi('ui/RackWindow.ui', self)
        self.setWindowTitle('Instrument rack')
        self.setWindowIcon(QtGui.QIcon('resources/instruments.svg'))
        self.toolBar.setToolButtonStyle(2) # text beside icon
        self.fixed_font = QFontDatabase.systemFont(QFontDatabase.FixedFont)
        self.lab = lab
        
        self.tree.setDragDropMode(QAbstractItemView.DragOnly)
        self.hbox_device.setEnabled(False)

        self.win_add = QMainWindow()
    
        # -- Connect signals to slots --
        self.actionAdd.triggered.connect(self.window_loadInstrument)
        self.actionRemove.triggered.connect(self.onRemoveInstrument)
        #self.actionConfig.triggered.connect(self.onActionConfig)
        self.tree.itemSelectionChanged.connect(self.onSelectionChanged)
        self.tree.itemDoubleClicked.connect(self.onDoubleClick)
        self.dev_get_value.clicked.connect(self.onGetValue)
    
    def onSelectionChanged(self):
        selected_item = self.tree.selectedItem()
        if selected_item is None: return
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
        self.dev_set_value.setEnabled(False)
        self.dev_wrap_device.setEnabled(False)
    
    def selectIsDevice(self):
        # when a device is selected
        self.actionRemove.setEnabled(False)
        self.actionConfig.setEnabled(False)
        self.dev_get_value.setEnabled(True)
        self.dev_set_value.setEnabled(True)
        self.dev_wrap_device.setEnabled(True)

    def onDoubleClick(self, item, _):
        data = self.tree.getData(item)
        if isinstance(data, GuiInstrument):
            pass
        elif isinstance(data, GuiDevice):
            self.onGetValue()
    
    def onGetValue(self):
        # ask the lab for the value of the selected device
        selected_item = self.tree.selectedItem()
        gui_dev = self.tree.getData(selected_item)
        self.lab.getValue(gui_dev)
    
    def onRemoveInstrument(self):
        # get parent selected item:
        selected_item = self.tree.selectedItem()
        gui_instr = self.tree.getData(selected_item)
        self.lab.removeGuiInstrument(gui_instr)
        
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
        for name, cls in self.lab.supported_instruments.items():
            cb.addItem(name, self.lab.supported_instruments[name]["pyhegel_class"])
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
                              self.lab.buildGuiInstrument(le_name.text(),
                                                          cb.currentText(),
                                                          cb.currentData(),
                                                          le_address.text()))
        bt_cancel.clicked.connect(self.win_add.close)

        self.win_add.show()


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
        item.setFont(3, self.fixed_font)
        item.setText(4, {True: 'Loaded', False: 'Not loaded'}[gui_instr.ph_instr is not None])
        for gui_dev in gui_instr.gui_devices.values():
            dev_item = QTreeWidgetItem(item)
            self.tree.setData(dev_item, gui_dev)
            dev_item.setText(0, gui_dev.name)
            dev_item.setText(3, {(True, True): 'set/get', (True, False): 'set', (False, True): 'get', (False, False): '?'}[gui_dev.type])
            dev_item.setText(4, {True: '', False: 'Not found'}[gui_dev.ph_dev is not None])
        self.tree.addTopLevelItem(item)
    
    def gui_removeGuiInstrument(self, gui_instr):
        # remove the instrument item from self.tree:
        item = self.tree.findItemByData(gui_instr)
        self.tree.takeTopLevelItem(self.tree.indexOfTopLevelItem(item))
    
    def gui_updateDeviceValue(self, gui_dev, value):
        # update the value of the item corresponding to gui_dev
        dev_item = self.tree.findItemByData(gui_dev)
        dev_item.setText(1, str(value))
    # -- end gui_ --