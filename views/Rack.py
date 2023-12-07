from PyQt5 import QtGui, uic
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QMainWindow, QWidget
from PyQt5.QtWidgets import (
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QComboBox,
    QLineEdit,
    QTreeWidgetItem,
    QAbstractItemView,
    QLabel,
    QListWidgetItem,
)
from PyQt5.QtGui import QFontDatabase
from src.GuiInstrument import GuiInstrument, GuiDevice
from pyHegel.gui.ScientificSpinBox import PyScientificSpinBox


class Rack(QMainWindow):
    def __init__(self, lab):
        super(Rack, self).__init__()
        uic.loadUi("ui/RackWindow.ui", self)
        self.setWindowTitle("Instrument rack")
        self.setWindowIcon(QtGui.QIcon("resources/instruments.svg"))
        self.toolBar.setToolButtonStyle(2)  # text beside icon
        self.fixed_font = QFontDatabase.systemFont(QFontDatabase.FixedFont)
        self.lab = lab

        self.tree.setColumnWidth(0, 175)
        self.tree.setDragDropMode(QAbstractItemView.DragOnly)
        self.hbox_device.setEnabled(False)

        self.win_add = QMainWindow()
        self.win_set = QMainWindow()
        self.win_create_dev = QMainWindow()
        self.win_rename = QMainWindow()

        # -- Connect signals to slots --
        self.actionAdd.triggered.connect(self.onLoadInstrument)
        self.actionRemove.triggered.connect(self.onRemoveInstrument)
        self.actionLoad.triggered.connect(self.onActionLoad)
        self.tree.itemSelectionChanged.connect(self.onSelectionChanged)
        self.tree.itemDoubleClicked.connect(self.onDoubleClick)
        self.pb_get.clicked.connect(self.onGetValue)
        self.pb_set.clicked.connect(self.onSetValue)
        self.pb_rename.clicked.connect(self.onRename)

    def onSelectionChanged(self):
        selected_item = self.tree.selectedItem()
        if selected_item is None:
            # when nothing is selected
            self.actionRemove.setEnabled(False)
            self.actionLoad.setEnabled(False)
            self.pb_get.setEnabled(False)
            self.pb_set.setEnabled(False)
            self.pb_rename.setEnabled(False)
            self.pb_config.setEnabled(False)
            return
        data = self.tree.getData(self.tree.selectedItem())
        if isinstance(data, GuiInstrument):
            # when an instrument is selected
            self.actionRemove.setEnabled(True)
            self.actionLoad.setEnabled(True)
            self.pb_get.setEnabled(False)
            self.pb_set.setEnabled(False)
            self.pb_rename.setEnabled(False)
            self.pb_config.setEnabled(False)
        elif isinstance(data, GuiDevice):
            # when a device is selected
            self.actionRemove.setEnabled(False)
            self.actionLoad.setEnabled(False)
            self.pb_get.setEnabled(True)
            self.pb_rename.setEnabled(True)
            gui_dev = data
            if gui_dev.type[0]:
                self.pb_set.setEnabled(True)
            else:
                self.pb_set.setEnabled(False)

    def onDoubleClick(self, item, _):
        print("double click")
        data = self.tree.getData(item)
        print("find: ", data)
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
        self.win_set.setWindowTitle("Set value")
        self.win_set.setWindowIcon(QtGui.QIcon("resources/instruments.svg"))
        wid = QWidget()
        self.win_set.setCentralWidget(wid)
        layout = QVBoxLayout()
        wid.setLayout(layout)
        lbl = QLabel("New value for: " + gui_dev.getDisplayName("long"))
        layout.addWidget(lbl)
        if gui_dev.ph_choice is not None:
            value_wid = QComboBox()
            for choice in gui_dev.ph_choice:
                value_wid.addItem(str(choice), choice)
            #value_wid.value = value_wid.currentData
            layout.addWidget(value_wid)
        else:  # spinbox by default
            value_wid = PyScientificSpinBox()
            layout.addWidget(value_wid)
        bt_ok = QPushButton("Set")
        bt_cancel = QPushButton("Cancel")
        Hlayout = QHBoxLayout()
        Hlayout.addWidget(bt_ok)
        Hlayout.addWidget(bt_cancel)
        layout.addLayout(Hlayout)

        def okClicked():
            to_set = value_wid.value()
            self.lab.setValue(gui_dev, to_set)

        def cancelClicked():
            self.win_set.close()

        bt_ok.clicked.connect(okClicked)
        bt_cancel.clicked.connect(cancelClicked)
        self.win_set.show()
    
    def onActionLoad(self):
        selected_item = self.tree.selectedItem()
        self.lab.loadGuiInstrument(self.tree.getData(selected_item))

    def onRemoveInstrument(self):
        # get parent selected item:
        selected_item = self.tree.selectedItem()
        gui_instr = self.tree.getData(selected_item)
        self.lab.removeGuiInstrument(gui_instr)

    def closeEvent(self, event):
        self.win_add.close()
        self.win_set.close()
        self.win_create_dev.close()
        self.win_rename.close()
        event.accept()

    # -- functions that creates windows --
    # window load device
    def onLoadInstrument(self):
        # minimal window for loading device
        self.win_add.setWindowTitle("Add instrument")
        self.win_add.resize(350, 100)
        self.win_add.setWindowIcon(QtGui.QIcon("resources/list-add.svg"))
        wid = QWidget()
        self.win_add.setCentralWidget(wid)
        layout = QVBoxLayout()
        wid.setLayout(layout)

        cb_instr = QComboBox()
        layout.addWidget(cb_instr)
        le_address = QLineEdit()
        le_address.setPlaceholderText("Address")
        le_address.setEnabled(False)

        hbox = QHBoxLayout()
        layout.addLayout(hbox)
        lbl_slot = QLabel("Slot: ")
        lbl_slot.setEnabled(False)
        cb_slot = QComboBox()
        cb_slot.setEnabled(False)
        hbox.addWidget(lbl_slot)
        hbox.addWidget(cb_slot)
        # add a vertical spacer to the hbox
        # so the comboboxes are not stretched
        hbox.addStretch(1)

        le_nickname = QLineEdit()
        le_nickname.setPlaceholderText("Name")
        layout.addWidget(le_address)
        layout.addWidget(le_nickname)

        for instrument in self.lab.instr_list:
            cb_instr.addItem(instrument.get('name'), instrument)

        def cbInstrChanged(settings):
            address = settings.get('address', None)
            if address:
                le_address.setEnabled(True)
                le_address.setText(address)
            else:
                le_address.setEnabled(False)
                le_address.clear()
            slots = settings.get('slots', None)
            if slots:
                lbl_slot.setEnabled(True)
                cb_slot.setEnabled(True)
                cb_slot.addItems([str(s) for s in slots])
            else:
                lbl_slot.setEnabled(False)
                cb_slot.setEnabled(False)
                cb_slot.clear()

        cb_instr.currentTextChanged.connect(
            lambda: cbInstrChanged(cb_instr.currentData())
        )

        # ok and cancel buttons in a horizontal layout
        bt_ok = QPushButton("Load")
        bt_cancel = QPushButton("Cancel")
        Hlayout = QHBoxLayout()
        Hlayout.addWidget(bt_ok)
        Hlayout.addWidget(bt_cancel)
        layout.addLayout(Hlayout)

        # connect signals to slots
        def okClicked():
            name = cb_instr.currentText()
            nickname = le_nickname.text() if le_nickname.text() != "" else name
            address = le_address.text()
            slot = int(cb_slot.currentText()) if cb_slot.isEnabled() else None
            instr_dict = cb_instr.currentData()
            self.lab.newInstrumentFromRack(nickname, address, slot, instr_dict)

        bt_ok.clicked.connect(okClicked)
        bt_cancel.clicked.connect(self.win_add.close)

        self.win_add.show()

    # window rename device
    def onRename(self):
        # window with a line edit to rename the selected item
        # only for gui_devices for now
        selected_item = self.tree.selectedItem()
        data = self.tree.getData(selected_item)
        self.win_rename.resize(300, 100)
        self.win_rename.setWindowTitle("Rename")
        self.win_rename.setWindowIcon(QtGui.QIcon("resources/instruments.svg"))
        wid = QWidget()
        self.win_rename.setCentralWidget(wid)
        layout = QVBoxLayout()
        wid.setLayout(layout)
        lbl = QLabel("New name for: " + data.getDisplayName("long"))
        layout.addWidget(lbl)
        le_value = QLineEdit()
        le_value.setText(data.nickname)
        layout.addWidget(le_value)
        bt_ok = QPushButton("Rename")
        bt_cancel = QPushButton("Cancel")
        Hlayout = QHBoxLayout()
        Hlayout.addWidget(bt_ok)
        Hlayout.addWidget(bt_cancel)
        layout.addLayout(Hlayout)

        def okClicked():
            value = le_value.text()
            selected_item.setText(0, data.getDisplayName("long"))
            self.lab.renameDevice(data, value)
            self.win_rename.close()

        def cancelClicked():
            self.win_rename.close()

        bt_ok.clicked.connect(okClicked)
        bt_cancel.clicked.connect(cancelClicked)
        self.win_rename.show()


    # -- end windows --

    # -- gui_: update the gui -- (called by the lab)
    def _logicalParamStr(self, logical_kwargs):
        string = ''
        for key, value in logical_kwargs.items():
            if not value:
                continue
            string += str(value) + ', '
        return string

    def gui_fillGuiInstrument(self, gui_instr):
        instr_item = self.tree.findItemByData(gui_instr)
        # fill the instrument item with its devices
        for gui_dev in gui_instr.gui_devices:
            dev_item = QTreeWidgetItem(instr_item)
            self.tree.setData(dev_item, gui_dev)
            dev_item.setText(0, gui_dev.getDisplayName("long"))
            dev_item.setText(
                1, str(gui_dev.cache_value) if gui_dev.cache_value is not None else ""
            )
            dev_item.setText(2, str(self._logicalParamStr(gui_dev.logical_kwargs)))
            dev_item.setText(
                3,
                {
                    (True, True): "set/get",
                    (True, False): "set",
                    (False, True): "get",
                    (False, False): "?",
                }[gui_dev.type],
            )
            dev_item.setText(
                4, {True: "", False: "Not found"}[gui_dev.ph_dev is not None]
            )

    def gui_addGuiInstrument(self, gui_instr):
        # add an instrument item to self.tree:
        item = QTreeWidgetItem()
        self.tree.setData(item, gui_instr)
        item.setFlags(item.flags() & ~Qt.ItemIsDragEnabled)
        item.setText(0, gui_instr.getDisplayName("long"))
        item.setText(2, gui_instr.address)
        item.setText(3, gui_instr.ph_class.__name__)
        item.setFont(3, self.fixed_font)
        item.setText(
            4, {True: "Loaded", False: "Not loaded"}[gui_instr.ph_instr is not None]
        )
        self.tree.addTopLevelItem(item)
        self.gui_fillGuiInstrument(gui_instr)

    def gui_removeGuiInstrument(self, gui_instr):
        # remove the instrument item from self.tree:
        item = self.tree.findItemByData(gui_instr)
        self.tree.takeTopLevelItem(self.tree.indexOfTopLevelItem(item))
        self.onSelectionChanged()

    def gui_updateGuiInstrument(self, gui_instr):
        item = self.tree.findItemByData(gui_instr)
        # remove
        for i in range(item.childCount()):
            item.removeChild(item.child(0))
        # refill
        self.gui_fillGuiInstrument(gui_instr)
        # instr status:
        item.setText(
            4, {True: "Loaded", False: "Not loaded"}[gui_instr.ph_instr is not None]
        )

    def gui_renameDevice(self, gui_dev):
        # rename the device item in self.tree
        dev_item = self.tree.findItemByData(gui_dev)
        dev_item.setText(0, gui_dev.getDisplayName("long"))

    def gui_updateDeviceValue(self, gui_dev, value):
        # update the value of the item corresponding to gui_dev
        dev_item = self.tree.findItemByData(gui_dev)
        dev_item.setText(1, str(value))

    # -- end gui_ --
