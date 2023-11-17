from PyQt5 import QtGui, uic
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget
from PyQt5.QtWidgets import QPushButton, QVBoxLayout, QHBoxLayout, \
                            QComboBox, QLineEdit, QTreeWidgetItem, \
                            QMessageBox, QAbstractItemView, QLabel, \
                            QSplitter, QGridLayout, QListWidget, \
                            QListWidgetItem
from PyQt5.QtGui import QFont, QFontDatabase
from widgets.DropLabel import DropLabel
from src.GuiInstrument import GuiInstrument, GuiDevice
from pyHegel.gui.ScientificSpinBox import PyScientificSpinBox

class Rack(QMainWindow):
    def __init__(self, lab):
        super(Rack, self).__init__()
        uic.loadUi('ui/RackWindow.ui', self)
        self.setWindowTitle('Instrument rack')
        self.setWindowIcon(QtGui.QIcon('resources/instruments.svg'))
        self.toolBar.setToolButtonStyle(2) # text beside icon
        self.fixed_font = QFontDatabase.systemFont(QFontDatabase.FixedFont)
        self.lab = lab
        
        self.tree.setColumnWidth(0, 175)
        self.tree.setDragDropMode(QAbstractItemView.DragOnly)
        self.hbox_device.setEnabled(False)

        self.win_add = QMainWindow()
        self.win_set = QMainWindow()
        self.win_create_dev = QMainWindow()
    
        # -- Connect signals to slots --
        self.actionAdd.triggered.connect(self.window_loadInstrument)
        self.actionRemove.triggered.connect(self.onRemoveInstrument)
        #self.actionConfig.triggered.connect(self.onActionConfig)
        self.tree.itemSelectionChanged.connect(self.onSelectionChanged)
        self.tree.itemDoubleClicked.connect(self.onDoubleClick)
        self.dev_get_value.clicked.connect(self.onGetValue)
        self.dev_set_value.clicked.connect(self.onSetValue)
        self.dev_create.clicked.connect(self.onCreateDevice)
        self.pb_rename.clicked.connect(self.onRename)
    
    def onSelectionChanged(self):
        selected_item = self.tree.selectedItem()
        if selected_item is None:
            # when nothing is selected
            self.actionRemove.setEnabled(False)
            self.actionConfig.setEnabled(False)
            self.dev_get_value.setEnabled(False)
            self.dev_set_value.setEnabled(False)
            self.pb_rename.setEnabled(False)
            return
        data = self.tree.getData(self.tree.selectedItem())
        if isinstance(data, GuiInstrument):
            # when an instrument is selected
            self.actionRemove.setEnabled(True)
            self.actionConfig.setEnabled(True)
            self.dev_get_value.setEnabled(False)
            self.dev_set_value.setEnabled(False)
            self.pb_rename.setEnabled(False)
        elif isinstance(data, GuiDevice):
            # when a device is selected
            self.actionRemove.setEnabled(False)
            self.actionConfig.setEnabled(False)
            self.dev_get_value.setEnabled(True)
            self.pb_rename.setEnabled(True)
            if self.tree.getData(self.tree.selectedItem()).type[0]:
                self.dev_set_value.setEnabled(True)
            else:
                self.dev_set_value.setEnabled(False)

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
    
    def onSetValue(self):
        # window with a line edit to set the value of the selected device
        selected_item = self.tree.selectedItem()
        gui_dev = self.tree.getData(selected_item)
        self.win_set.resize(300, 100)
        self.win_set.setWindowTitle(gui_dev.getDisplayName('long'))
        self.win_set.setWindowIcon(QtGui.QIcon('resources/instruments.svg'))
        wid = QWidget(); self.win_set.setCentralWidget(wid)
        layout = QVBoxLayout(); wid.setLayout(layout)
        le_value = PyScientificSpinBox()
        layout.addWidget(le_value)
        bt_ok = QPushButton('Set')
        bt_cancel = QPushButton('Cancel')
        Hlayout = QHBoxLayout()
        Hlayout.addWidget(bt_ok)
        Hlayout.addWidget(bt_cancel)
        layout.addLayout(Hlayout)
        def okClicked():
            value = le_value.value()
            self.lab.setValue(gui_dev, value)
        def cancelClicked():
            self.win_set.close()
        bt_ok.clicked.connect(okClicked)
        bt_cancel.clicked.connect(cancelClicked)
        self.win_set.show()
    
    def onCreateDevice(self):
        # load window/RackCreateDevice.ui
        win = self.win_create_dev
        win.setWindowTitle('Create device')
        win.setWindowIcon(QtGui.QIcon('resources/list-add.svg'))
        uic.loadUi('ui/RackCreateDevice.ui', win)
        win.setWindowFlags(Qt.WindowStaysOnTopHint)
        win.splitter.setSizes([100, 300])

        # fill list widget:
        for name, settings in self.lab.supported_devices.items():
            item = QListWidgetItem(name)
            item.setData(Qt.UserRole, settings)
            win.list.addItem(item)
        
        def onListItemChanged():
            item = win.list.currentItem()
            settings = item.data(Qt.UserRole)
            drawGrid(settings)
        win.list.currentItemChanged.connect(onListItemChanged)

        def drawGrid(settings):
            # clear the grid:
            while win.grid.count():
                item = win.grid.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()
            # draw
            win.grid.addWidget(QLabel('Device: '), 0, 0)
            self.lbl_drop = DropLabel('<drop here>', acccepts='device-name')
            def onDrop(data):
                print(data)
            self.lbl_drop.dropMimeData = lambda data: onDrop(data)

            win.grid.addWidget(self.lbl_drop, 0, 1)
            # dropping settings:
            
            for i, arg in enumerate(settings['args']):
                lbl = QLabel(arg)
                sb = PyScientificSpinBox()
                win.grid.addWidget(lbl, i+1, 0)
                win.grid.addWidget(sb, i+1, 1)
                


        self.win_create_dev.show()
        
        
    def onRename(self):
        # window with a line edit to rename the selected item
        # only for gui_devices for now
        selected_item = self.tree.selectedItem()
        data = self.tree.getData(selected_item)
        self.win_set.resize(300, 100)
        self.win_set.setWindowTitle('Rename ' + data.getDisplayName('long'))
        self.win_set.setWindowIcon(QtGui.QIcon('resources/instruments.svg'))
        wid = QWidget(); self.win_set.setCentralWidget(wid)
        layout = QVBoxLayout(); wid.setLayout(layout)
        le_value = QLineEdit()
        le_value.setText(data.nickname)
        layout.addWidget(le_value)
        bt_ok = QPushButton('Rename')
        bt_cancel = QPushButton('Cancel')
        Hlayout = QHBoxLayout()
        Hlayout.addWidget(bt_ok)
        Hlayout.addWidget(bt_cancel)
        layout.addLayout(Hlayout)
        def okClicked():
            value = le_value.text()
            selected_item.setText(0, data.getDisplayName('short', full=True))
            self.lab.renameDevice(data, value)
            self.win_set.close()
        def cancelClicked():
            self.win_set.close()
        bt_ok.clicked.connect(okClicked)
        bt_cancel.clicked.connect(cancelClicked)
        self.win_set.show()
    
    def onRemoveInstrument(self):
        # get parent selected item:
        selected_item = self.tree.selectedItem()
        gui_instr = self.tree.getData(selected_item)
        self.lab.removeGuiInstrument(gui_instr)
        
    def closeEvent(self, event):
        self.win_add.close()
        self.win_set.close()
        self.win_create_dev.close()
        event.accept()
    
    # -- windows --
    def window_loadInstrument(self):
        # minimal window for loading device
        self.win_add.setWindowTitle('Add instrument')
        self.win_add.resize(350, 100)
        self.win_add.setWindowIcon(QtGui.QIcon('resources/list-add.svg'))
        wid = QWidget(); self.win_add.setCentralWidget(wid)
        layout = QVBoxLayout(); wid.setLayout(layout)
        
        cb_instr = QComboBox(); layout.addWidget(cb_instr)
        le_address = QLineEdit()
        le_address.setPlaceholderText('Address')
        le_address.setEnabled(False)

        hbox = QHBoxLayout(); layout.addLayout(hbox)
        lbl_slot = QLabel('Slot: '); lbl_slot.setEnabled(False)
        cb_slot = QComboBox(); cb_slot.setEnabled(False)
        hbox.addWidget(lbl_slot)
        hbox.addWidget(cb_slot)
        # add a vertical spacer to the hbox
        # so the comboboxes are not stretched
        hbox.addStretch(1)
        

        le_nickname = QLineEdit(); le_nickname.setPlaceholderText('Name')
        layout.addWidget(le_address)
        layout.addWidget(le_nickname)

        for name, settings in self.lab.supported_instruments.items():
            cb_instr.addItem(name, settings)
        def cbInstrChanged(settings):
            if settings['has_address']:
                le_address.setEnabled(True)
                le_address.setText(settings['address'])
            else:
                le_address.setEnabled(False)
                le_address.clear()
            if settings['has_slots']:
                lbl_slot.setEnabled(True)
                cb_slot.setEnabled(True)
                cb_slot.addItems([str(p) for p in settings['slots']])
            else:
                lbl_slot.setEnabled(False)
                cb_slot.setEnabled(False)
                cb_slot.clear()
        cb_instr.currentTextChanged.connect(lambda: cbInstrChanged(cb_instr.currentData()))


        # ok and cancel buttons in a horizontal layout
        bt_ok = QPushButton('Load')
        bt_cancel = QPushButton('Cancel')
        Hlayout = QHBoxLayout()
        Hlayout.addWidget(bt_ok)
        Hlayout.addWidget(bt_cancel)
        layout.addLayout(Hlayout)

        # connect signals to slots
        def okClicked():
            name = cb_instr.currentText()
            nickname = le_nickname.text() if le_nickname.text() != '' else name
            address = le_address.text()
            slot = None
            if cb_slot.isEnabled():
                slot = int(cb_slot.currentText())
            self.lab.buildGuiInstrument(nickname, name, address, slot)

        bt_ok.clicked.connect(okClicked)
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
            dev_item.setText(0, gui_dev.getDisplayName('short', full=True))
            dev_item.setText(3, {(True, True): 'set/get', (True, False): 'set', (False, True): 'get', (False, False): '?'}[gui_dev.type])
            dev_item.setText(4, {True: '', False: 'Not found'}[gui_dev.ph_dev is not None])
        self.tree.addTopLevelItem(item)
    
    def gui_removeGuiInstrument(self, gui_instr):
        # remove the instrument item from self.tree:
        item = self.tree.findItemByData(gui_instr)
        self.tree.takeTopLevelItem(self.tree.indexOfTopLevelItem(item))
        self.onSelectionChanged()
    
    def gui_renameDevice(self, gui_dev):
        # rename the device item in self.tree
        dev_item = self.tree.findItemByData(gui_dev)
        dev_item.setText(0, gui_dev.getDisplayName('short', full=True))
    
    def gui_updateDeviceValue(self, gui_dev, value):
        # update the value of the item corresponding to gui_dev
        dev_item = self.tree.findItemByData(gui_dev)
        dev_item.setText(1, str(value))
    # -- end gui_ --