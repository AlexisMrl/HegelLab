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
)
from PyQt5.QtGui import QFontDatabase
import PyQt5.QtCore as QtCore
from src.GuiInstrument import GuiInstrument, GuiDevice
from pyHegel.gui.ScientificSpinBox import PyScientificSpinBox
from widgets.WindowWidget import AltDragWindow


class RackWindow(AltDragWindow):
    def __init__(self, lab):
        super().__init__()
        uic.loadUi("ui/RackWindow.ui", self)
        self.setWindowTitle("Instrument rack")
        self.setWindowIcon(QtGui.QIcon("resources/instruments.svg"))
        self.toolBar.setToolButtonStyle(2)  # text beside icon
        self.fixed_font = QFontDatabase.systemFont(QFontDatabase.FixedFont)
        self.lab = lab

        # dimension:
        self.resize(1000, 500)
        self.tree.setColumnWidth(0, 250)
        self.tree.setColumnWidth(2, 350)
        self.tree.setDragDropMode(QAbstractItemView.DragOnly)
        self.tree.setIconSize(QtCore.QSize(13, 13))  # noqa: F821
        self.hbox_device.setEnabled(False)

        self.win_add = QMainWindow()
        self.win_set = QMainWindow()
        self.win_devconfig = QMainWindow()
        self.win_rename = QMainWindow()

        # -- Connect signals to slots --
        self.actionAdd.triggered.connect(self.onAddInstrument)
        self.actionRemove.triggered.connect(self.onRemoveInstrument)
        self.actionLoad.triggered.connect(self.onActionLoad)
        self.actionConfig.triggered.connect(self.onActionConfig)
        self.tree.itemSelectionChanged.connect(self.onSelectionChanged)
        self.tree.itemDoubleClicked.connect(self.onDoubleClick)
        self.pb_get.clicked.connect(self.onGetValue)
        self.pb_set.clicked.connect(self.onSetValue)
        self.pb_rename.clicked.connect(self.onRename)
        self.pb_config.clicked.connect(self.onConfigDevice)
        self.importFromJSON.triggered.connect(self.lab.importFromJSON)
        self.exportToPyHegel.triggered.connect(self.lab.exportToPyHegel)
        self.exportToJSON.triggered.connect(self.lab.exportToJSON)

    def onSelectionChanged(self):
        selected_item = self.tree.selectedItem()
        if selected_item is None:
            # when nothing is selected
            self.actionRemove.setEnabled(False)
            self.actionLoad.setEnabled(False)
            self.actionConfig.setEnabled(False)
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
            self.actionConfig.setEnabled(True if data.ph_instr != None else False)
            self.pb_get.setEnabled(False)
            self.pb_set.setEnabled(False)
            self.pb_rename.setEnabled(False)
            self.pb_config.setEnabled(False)
        elif isinstance(data, GuiDevice):
            # when a device is selected
            self.actionRemove.setEnabled(False)
            self.actionLoad.setEnabled(False)
            self.actionConfig.setEnabled(False)
            self.pb_get.setEnabled(True)
            self.pb_rename.setEnabled(True)
            self.pb_config.setEnabled(True)
            gui_dev = data
            if gui_dev.type[0]:
                self.pb_set.setEnabled(True)
            else:
                self.pb_set.setEnabled(False)

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
            value_wid.value = value_wid.currentData
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
        self.win_set.raise_()
    
    def onConfigDevice(self):
        selected_item = self.tree.selectedItem()
        gui_dev = self.tree.getData(selected_item)
        ramp, scale, limit = gui_dev.logical_kwargs['ramp'], gui_dev.logical_kwargs['scale'], gui_dev.logical_kwargs['limit']
        # setting up window
        uic.loadUi("ui/RackParamDevice.ui", self.win_devconfig)
        win = self.win_devconfig
        win.setWindowTitle("Configure device - " + gui_dev.getDisplayName("long"))
        win.setWindowIcon(QtGui.QIcon("resources/instruments.svg"))
        if ramp != {}:
            win.cb_ramp.setChecked(True)
        win.sb_ramp.setValue(ramp.get('rate', 0))
        if scale != {}:
            win.cb_scale.setChecked(True)
            win.sb_scale.setValue(scale.get('factor', 0))
        if limit != {}:
            win.cb_limit.setChecked(True)
        win.sb_min.setValue(limit.get('min', 0))
        win.sb_max.setValue(limit.get('max', 0))
        def onCreate():
            if win.cb_ramp.isChecked():
                gui_dev.logical_kwargs['ramp'] = {'rate': win.sb_ramp.value()}
            else:
                gui_dev.logical_kwargs['ramp'] = {}
            if win.cb_scale.isChecked():
                gui_dev.logical_kwargs['scale'] = {'factor': win.sb_scale.value()}
            else:
                gui_dev.logical_kwargs['scale'] = {}
            if win.cb_limit.isChecked():
                gui_dev.logical_kwargs['limit'] = {'min': win.sb_min.value(), 'max': win.sb_max.value()}
            else:
                gui_dev.logical_kwargs['limit'] = {}
            self.lab.loadGuiLogicalDevice(gui_dev)
            self.gui_updateGuiInstrument(gui_dev.parent)
            win.close()
        win.pb_create.clicked.connect(onCreate)
        def onCancel():
            win.close()
        win.pb_cancel.clicked.connect(onCancel)
        win.show()
    
    def onActionLoad(self):
        selected_item = self.tree.selectedItem()
        self.lab.loadGuiInstrument(self.tree.getData(selected_item))

    def onActionConfig(self):
        selected_item = self.tree.selectedItem()
        self.lab.showConfig(self.tree.getData(selected_item))

    def onRemoveInstrument(self):
        # get parent selected item:
        selected_item = self.tree.selectedItem()
        gui_instr = self.tree.getData(selected_item)
        self.lab.removeGuiInstrument(gui_instr)

    def closeEvent(self, event):
        self.win_add.close()
        self.win_set.close()
        self.win_rename.close()
        self.win_devconfig.close()
        event.accept()

    # -- functions that creates windows --
    # window add device
    def onAddInstrument(self):
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
            cb_slot.clear()
            if slots:
                lbl_slot.setEnabled(True)
                cb_slot.setEnabled(True)
                cb_slot.addItems([str(s) for s in slots])
            else:
                lbl_slot.setEnabled(False)
                cb_slot.setEnabled(False)

        cb_instr.currentTextChanged.connect(
            lambda: cbInstrChanged(cb_instr.currentData())
        )

        # ok and cancel buttons in a horizontal layout
        bt_ok = QPushButton("Add")
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
                    (None, None): "?",
                }[gui_dev.type],
            )
            status_text = "Not found" if not gui_dev.isLoaded() and gui_dev.parent.isLoaded() else ""
            dev_item.setText(4, status_text)

    def gui_addGuiInstrument(self, gui_instr):
        # add an instrument item to self.tree:
        item = QTreeWidgetItem()
        self.tree.setData(item, gui_instr)
        item.setFlags(item.flags() & ~Qt.ItemIsDragEnabled)
        item.setText(0, gui_instr.getDisplayName("long"))
        item.setText(2, gui_instr.address)
        item.setText(3, gui_instr.ph_class.split('.')[-1])
        item.setFont(3, self.fixed_font)
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
        loaded_text = "Loaded" if gui_instr.isLoaded() else "Loading error"
        item.setText(4, loaded_text)
        loaded_icon_path = "resources/icon-success.svg" if gui_instr.isLoaded() else "resources/icon-error.svg"
        item.setIcon(4, QtGui.QIcon(loaded_icon_path))
        self.onSelectionChanged()

    def gui_renameDevice(self, gui_dev):
        # rename the device item in self.tree
        dev_item = self.tree.findItemByData(gui_dev)
        dev_item.setText(0, gui_dev.getDisplayName("long"))

    def gui_updateDeviceValue(self, gui_dev, value):
        # update the value of the item corresponding to gui_dev
        dev_item = self.tree.findItemByData(gui_dev)
        dev_item.setText(1, str(value))

    # -- end gui_ --
