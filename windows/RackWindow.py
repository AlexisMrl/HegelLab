from PyQt5 import QtGui, uic
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget
from PyQt5.QtWidgets import (
    QPushButton,
    QCheckBox,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QListWidget,
    QLineEdit,
    QTreeWidgetItem,
    QAbstractItemView,
    QLabel,
    QMenu,
)
from PyQt5.QtGui import QFontDatabase
import PyQt5.QtCore as QtCore
from src.GuiInstrument import GuiInstrument, GuiDevice
from pyHegel.gui.ScientificSpinBox import PyScientificSpinBox
from widgets.WindowWidget import Window
from widgets.ComboboxWidget import Combobox


class RackWindow(Window):
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
        self.tree.setIconSize(QtCore.QSize(13, 13))
        self.hbox_device.setEnabled(False)

        self.win_add = Window()
        self.win_editdevices = Window()
        self.win_instrconfig = Window()
        self.win_set = Window()
        self.win_devconfig = Window()
        self.win_devconfig.gui_dev = None
        self.win_rename = Window()

        # context menu
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.onItemRightClick)

        # -- Connect signals to slots --
        self.tree.itemSelectionChanged.connect(self.onSelectionChanged)
        self.tree.itemDoubleClicked.connect(self.onDoubleClick)

        self.actionLoad.triggered.connect(self.onActionLoadTrigger)
        self.actionEditDevices.triggered.connect(self.onActionEditDevicesTrigger)
        self.actionAdd.triggered.connect(self.onAddInstrumentTrigger)
        self.actionRemove.triggered.connect(self.onRemoveInstrumentTrigger)

        self.pb_get.clicked.connect(self.onGetValueClick)
        self.pb_set.clicked.connect(self.onSetValueClick)
        self.pb_config.clicked.connect(self.onConfigDeviceClick)
        self.pb_remove_dev.clicked.connect(self.onRemoveDevClick)
        self.pb_rename.clicked.connect(self.onRenameItemClick)


        self.importFromJSON.triggered.connect(self.lab.importFromJSON)
        self.exportToPyHegel.triggered.connect(self.lab.exportToPyHegel)
        self.exportToJSON.triggered.connect(self.lab.exportToJSON)

    def initShortcuts(self):
        super().initShortcuts()
        self.short("Shift+a", self.actionAdd.trigger)
        self.short("Shift+l", self.actionLoad.trigger)
        self.short("Shift+e", self.actionEditDevices.trigger)
        self.short("Shift+x", self.actionRemove.trigger)
        ## device
        self.short("Space", self.pb_get.click)
        self.short("Shift+Space", self.pb_set.click)
        self.short("c", self.pb_config.click)
        self.short("r", self.pb_rename.click)
        self.short("s", lambda: self.itemToggleSOL(self.tree.selectedItem(), 'sweep'))
        self.short("o", lambda: self.itemToggleSOL(self.tree.selectedItem(), 'out'))
        self.short("g", lambda: self.itemToggleSOL(self.tree.selectedItem(), 'log'))
        self.short("m", lambda: self.itemToggleSOL(self.tree.selectedItem(), 'monitor'))
        self.short("x", self.pb_remove_dev.click)
    
    def itemToggleSOL(self, item, str_type):
        # str_type = 'sweep', 'out' or 'log'
        set_fn = {'sweep':self.lab.setSweepDevice, 'out':self.lab.setOutDevice,
                  'log':self.lab.setLogDevice, 'monitor':self.lab.setMonitorDevice}[str_type]
        if item and (gui_dev := self.tree.getData(item)):
            if isinstance(gui_dev, GuiDevice):
                set_fn(gui_dev, not gui_dev.status[str_type])

    def closeEvent(self, event):
        self.win_add.close()
        self.win_editdevices.close()
        self.win_set.close()
        self.win_devconfig.close()
        self.win_rename.close()
        event.accept()
    
    def focus(self):
        super().focus()
        self.tree.setFocus(True)
    


    def onSelectionChanged(self):
        # setEnabled buttons based on the selected item
        showAction, showEditDevices, showSet, showGet = [False]*4
        selected_item = self.tree.selectedItem()
        if selected_item is not None:
            data = self.tree.getData(selected_item)
            if isinstance(data, GuiInstrument):
                showAction = True
                showEditDevices = True if data.ph_instr else False
            elif isinstance(data, GuiDevice):
                showAction = False
                showSet = data.type[0] or False
                showGet = data.type[1] or False

        self.actionRemove.setEnabled(showAction)
        self.actionLoad.setEnabled(showAction)
        self.actionEditDevices.setEnabled(showEditDevices)
        self.pb_rename.setEnabled(not showAction)
        self.pb_config.setEnabled(not showAction)
        self.pb_remove_dev.setEnabled(not showAction)
        self.pb_get.setEnabled(showGet)
        self.pb_set.setEnabled(showSet)

    def onDoubleClick(self, item, column):
        if isinstance(data := self.tree.getData(item), GuiInstrument):
            pass
        elif isinstance(data, GuiDevice):
            self.lab.getValue(data)
    
    def onActionLoadTrigger(self):
        if not isinstance(gui_instr := self.tree.selectedData(), GuiInstrument):
            return
        self.lab.loadGuiInstrument(gui_instr)

    def onActionEditDevicesTrigger(self):
        if not isinstance(gui_instr := self.tree.selectedData(), GuiInstrument):
            return
        self.window_SelectDevices(gui_instr)
        self.win_editdevices.focus()

    def onAddInstrumentTrigger(self):
        self.window_AddInstrument()
        self.win_add.focus()
        self.win_add.cb_instr.setFocus(True)

    def onRemoveInstrumentTrigger(self):
        if isinstance(gui_instr := self.tree.selectedData(), GuiInstrument):
            self.lab.removeGuiInstrument(gui_instr)

    def onGetValueClick(self):
        # ask the lab for the value of the selected device
        if isinstance(gui_dev := self.tree.selectedData(), GuiDevice):
            self.lab.getValue(gui_dev)

    def onSetValueClick(self):
        if not isinstance(gui_dev := self.tree.selectedData(), GuiDevice):
            return
        self.window_DeviceSet(gui_dev)
        self.win_set.focus()
        self.win_set.value_wid.setFocus(True)

    def onConfigDeviceClick(self):
        if not isinstance(gui_dev := self.tree.selectedData(), GuiDevice):
            return
        self.window_DeviceConfigWindow(gui_dev)
        self.win_devconfig.focus()
    
    def onRemoveDevClick(self):
        gui_dev = self.tree.selectedData()
        if not isinstance(gui_dev, GuiDevice): return
        self.lab.removeGuiDevice(gui_dev)
    
    def onRenameItemClick(self):
        gui_dev_or_instr = self.tree.selectedData()
        self.window_Rename(gui_dev_or_instr)
        self.win_rename.focus()
        self.win_rename.le_value.setFocus(True)
    
    def onChangeAddressClick(self):
        gui_instr = self.tree.selectedData()
        if not isinstance(gui_instr, GuiInstrument): return
        self.window_InstrumentConfigWindow(gui_instr)
        self.win_instrconfig.focus()
        self.win_instrconfig.le_value.setFocus(True)

    def onItemRightClick(self, point):
        index = self.tree.indexAt(point)
        if not index.isValid(): return
        selected_item = self.tree.itemAt(point)
        data = self.tree.getData(selected_item)

        menu = QMenu()
        if isinstance(data, GuiInstrument):
            menu.addAction("Load/Reload (L)", self.actionLoad.trigger)
            menu.addAction("Edit devices (E)", self.actionEditDevices.trigger)
            menu.addAction("Edit address", self.onChangeAddressClick)
            menu.addAction("Rename", self.onRenameItemClick)
            menu.addSeparator()
            menu.addAction("Remove instrument (X)", self.actionRemove.trigger)
        elif isinstance(data, GuiDevice):
            # TODO: if dev is bool: addAction("toggle")
            menu.addAction("Get (space)", self.pb_get.click)
            menu.addAction("Set (shift+space)", self.pb_set.click)
            menu.addSeparator()
            menu.addAction("Rename (r)", self.pb_rename.click)
            menu.addAction("Config device (c)", self.pb_config.click)
            menu.addSeparator()
            menu.addAction("Monitor (m)", lambda: self.itemToggleSOL(self.tree.selectedItem(), 'monitor'))
            menu.addSeparator()
            menu.addAction("Remove device (x)", self.pb_remove_dev.click)


        menu.exec_(self.tree.mapToGlobal(point))

    def _logicalParamStr(self, logical_kwargs):
        string = ''
        for key, value in logical_kwargs.items():
            if not value:
                continue
            string += str(value) + ', '
        return string

    def _fillGuiInstrumentItem(self, instr_item):
        # fill text of the instrument item
        gui_instr = self.tree.getData(instr_item)
        instr_item.setFlags(instr_item.flags() & ~Qt.ItemIsDragEnabled)
        instr_item.setText(0, gui_instr.getDisplayName("long"))
        instr_item.setText(2, gui_instr.address + (f" - slot {gui_instr.slot}" if gui_instr.slot is not None else ""))
        instr_item.setText(3, gui_instr.ph_class.split('.')[-1])
        instr_item.setFont(3, self.fixed_font)
        instr_item.setIcon(4, QtGui.QIcon("resources/icon-grey.svg"))

    def _fillGuiDeviceItem(self, dev_item):
        # fill text of the device item
        gui_dev = self.tree.getData(dev_item)
        dev_item.setText(0, gui_dev.getDisplayName("long"))
        dev_item.setText(1, gui_dev.getCacheValueToStr())
        dev_item.setForeground(1, QtGui.QBrush(QtGui.QColor("black")))
        dev_item.setText(2, str(self._logicalParamStr(gui_dev.logical_kwargs)))
        dev_item.setText(3, gui_dev.getTypeToStr())
            
        status_str = []
        if gui_dev.status['sweep']: status_str.append('sweep')
        if gui_dev.status['out']: status_str.append('out')
        if gui_dev.status['log']: status_str.append('log')
        if gui_dev.status['monitor']: status_str.append('monitor')
        if not gui_dev.isLoaded() and gui_dev.parent.isLoaded():
            status_str.append("(Not found)")
        status_str = ', '.join(status_str)
        dev_item.setText(4, status_str)

    def _addGuiDevice(self, gui_dev):
        # make and add gui_dev_item to its parent
        instr_item = self.tree.findItemByData(gui_dev.parent)
        dev_item = QTreeWidgetItem(instr_item)
        self.tree.setData(dev_item, gui_dev)
        self._fillGuiDeviceItem(dev_item)

    # -- gui_: update the gui -- (called by the lab)

    def gui_onInstrumentAdded(self, gui_instr):
        # add and fill an instrument item:
        item = QTreeWidgetItem()
        self.tree.setData(item, gui_instr)
        self._fillGuiInstrumentItem(item)
        self.tree.addTopLevelItem(item)
        self.tree.setCurrentItem(item)
        # then add and fill its devices
        for gui_dev in gui_instr.gui_devices:
            self._addGuiDevice(gui_dev)

    def gui_updateGuiDevice(self, gui_dev):
        item = self.tree.findItemByData(gui_dev)
        self._fillGuiDeviceItem(item)
        if self.win_devconfig.gui_dev == gui_dev: self.win_devconfig.close()

    def gui_updateGuiInstrument(self, gui_instr):
        item = self.tree.findItemByData(gui_instr)
        if not item: return
        # refill
        self._fillGuiInstrumentItem(item)
        # update instr status:
        if gui_instr.loading:
            item.setText(4, "Loading...")
            item.setIcon(4, QtGui.QIcon("resources/icon-grey.svg"))
        else:
            loaded_text = "Loaded" if gui_instr.isLoaded() else "Loading error"
            item.setText(4, loaded_text)
            loaded_icon_path = "resources/icon-success.svg" if gui_instr.isLoaded() else "resources/icon-error.svg"
            item.setIcon(4, QtGui.QIcon(loaded_icon_path))
        self.onSelectionChanged()

    def gui_onNewDevicesAdded(self, gui_instr, gui_dev_list):
        for gui_dev in gui_dev_list:
            self._addGuiDevice(gui_dev)

    def gui_onInstrumentRemoved(self, gui_instr):
        # remove the instrument item from self.tree:
        item = self.tree.findItemByData(gui_instr)
        self.tree.takeTopLevelItem(self.tree.indexOfTopLevelItem(item))
        self.onSelectionChanged()
    
    def gui_onDeviceRemoved(self, gui_dev):
        instr_item = self.tree.findItemByData(gui_dev.parent)
        dev_item = self.tree.findItemByData(gui_dev)
        dev_index = instr_item.indexOfChild(dev_item)
        instr_item.takeChild(dev_index)
    
    def gui_onValueGet(self, gui_dev):
        # update the value of the item corresponding to gui_dev
        if dev_item := self.tree.findItemByData(gui_dev):
            dev_item.setText(1, gui_dev.getCacheValueToStr())
            dev_item.setForeground(1, QtGui.QBrush(QtGui.QColor("black")))
    
    def gui_onValueSet(self, gui_dev):
        # switch to grey font color
        if (item := self.tree.findItemByData(gui_dev)):
            item.setForeground(1, QtGui.QBrush(QtGui.QColor("grey")))
    
    def gui_onDeviceRenamed(self, gui_dev):
        # rename the device item in self.tree
        dev_item = self.tree.findItemByData(gui_dev)
        dev_item.setText(0, gui_dev.getDisplayName("long"))
    
    def gui_onInstrumentRenamed(self, gui_instr):
        instr_item = self.tree.findItemByData(gui_instr)
        instr_item.setText(0, gui_instr.getDisplayName("long"))

    # -- end gui_ --


    # -- WINDOWS --

    def window_AddInstrument(self):
        # minimal window for loading device
        self.win_add.setWindowTitle("Add instrument")
        self.win_add.resize(350, 100)
        self.win_add.setWindowIcon(QtGui.QIcon("resources/list-add.svg"))
        wid = QWidget()
        self.win_add.setCentralWidget(wid)
        layout = QVBoxLayout()
        wid.setLayout(layout)

        cb_instr = Combobox()
        self.win_add.cb_instr = cb_instr
        layout.addWidget(cb_instr)
        le_address = QLineEdit()
        le_address.setPlaceholderText("Address")
        le_address.setEnabled(False)

        hbox = QHBoxLayout()
        layout.addLayout(hbox)
        lbl_slot = QLabel("Slot: ")
        lbl_slot.setEnabled(False)
        cb_slot = Combobox()
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

        for instrument in self.lab.default_instr_list:
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

        cb_instr.currentTextChanged.connect(lambda: cbInstrChanged(cb_instr.currentData()))

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
            self.win_add.close()
            self.tree.setFocus(True)

        bt_ok.clicked.connect(okClicked)
        bt_cancel.clicked.connect(self.win_add.close)



    def window_DeviceSet(self, gui_dev):
        # window with a line edit to set the value of the selected device
        self.win_set.resize(300, 100)
        self.win_set.setWindowTitle("Set value")
        self.win_set.setWindowIcon(QtGui.QIcon("resources/instruments.svg"))
        wid = QWidget()
        self.win_set.setCentralWidget(wid)
        layout = QVBoxLayout()
        wid.setLayout(layout)
        lbl = QLabel("New value for: " + gui_dev.getDisplayName("long"))
        layout.addWidget(lbl)

        if gui_dev.ph_choice is not None: # use combobox
            value_wid = Combobox()
            for choice in gui_dev.ph_choice:
                value_wid.addItem(str(choice), choice)
            value_wid.value = value_wid.currentData
            layout.addWidget(value_wid)
        elif gui_dev.type[2] is bool:  # checkbox
            value_wid = QCheckBox(gui_dev.getDisplayName("long"))
            lbl.setText("Set boolean: ")
            value_wid.setChecked(bool(gui_dev.cache_value))
            value_wid.value = lambda: value_wid.isChecked()
            layout.addWidget(value_wid)
        else:  # spinbox by default
            value_wid = PyScientificSpinBox()
            layout.addWidget(value_wid)
        self.win_set.value_wid = value_wid

        bt_ok = QPushButton("Set")
        bt_cancel = QPushButton("Cancel")
        Hlayout = QHBoxLayout()
        Hlayout.addWidget(bt_ok)
        Hlayout.addWidget(bt_cancel)
        layout.addLayout(Hlayout)

        def okClicked():
            to_set = value_wid.value()
            self.lab.setValue(gui_dev, to_set)
            self.win_set.close()

        def cancelClicked():
            self.win_set.close()

        bt_ok.clicked.connect(okClicked)
        bt_cancel.clicked.connect(cancelClicked)
        


    def window_DeviceConfigWindow(self, gui_dev):
        # setting up window from ui file
        self.win_devconfig.gui_dev = gui_dev
        win = self.win_devconfig
        uic.loadUi("ui/RackParamDevice.ui", self.win_devconfig)
        win.setWindowTitle("Configure device - " + gui_dev.getDisplayName("long"))
        win.setWindowIcon(QtGui.QIcon("resources/instruments.svg"))

        # setting ui values
        is_settable, is_gettable, out_type = gui_dev.type
        win.cb_set.setChecked(is_settable if is_settable is not None else False)
        win.cb_get.setChecked(is_gettable if is_gettable is not None else False)
        win.cb_out_type.clear()
        list_types = {bool: 'bool', None: 'Undefined'} # curent list of allowed types. will fail if not in this list
        for data, lbl in list_types.items():
            win.cb_out_type.addItem(lbl, data)
        if (index := win.cb_out_type.findData(out_type)) != -1:
            win.cb_out_type.setCurrentIndex(index)

        ramp, scale, limit = gui_dev.logical_kwargs['ramp'], gui_dev.logical_kwargs['scale'], gui_dev.logical_kwargs['limit']
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

        win.le_kwargs.setText(", ".join([f"{key}={repr(val)}" for key, val in gui_dev.extra_args.items()]))

        def onCreate():
            gui_dev.type = [win.cb_set.isChecked(), win.cb_get.isChecked(), win.cb_out_type.currentData()]
            # try eval the kwargs:
            try:
                extra_args_dict = eval(f"dict({win.le_kwargs.text()})")
            except:
                self.lab.pop.devExtraArgsEvalFail()
                return
            else:
                gui_dev.extra_args = extra_args_dict

            # getting values
            if win.cb_ramp.isChecked():
                if (rate := win.sb_ramp.value()) == 0:
                    self.lab.pop.devRampZero()
                    return
                gui_dev.logical_kwargs['ramp'] = {'rate': rate}
            else:
                gui_dev.logical_kwargs['ramp'] = {}

            if win.cb_scale.isChecked():
                if (factor := win.sb_scale.value()) == 0:
                    self.lab.pop.devScaleZero()
                    return
                gui_dev.logical_kwargs['scale'] = {'factor': factor}
            else:
                gui_dev.logical_kwargs['scale'] = {}

            if win.cb_limit.isChecked():
                gui_dev.logical_kwargs['limit'] = {'min': win.sb_min.value(), 'max': win.sb_max.value()}
            else:
                gui_dev.logical_kwargs['limit'] = {}

            self.lab.loadGuiDevice(gui_dev)
        win.pb_create.clicked.connect(onCreate)

        def onCancel():
            win.close()
        win.pb_cancel.clicked.connect(onCancel)
    

    
    def window_InstrumentConfigWindow(self, gui_instr):
        # window with a line edit to change address
        # TODO: add slot if instr has it
        win = self.win_instrconfig
        win.resize(300, 100)
        win.setWindowTitle("Change address")
        win.setWindowIcon(QtGui.QIcon("resources/instruments.svg"))
        wid = QWidget(); win.setCentralWidget(wid)
        layout = QVBoxLayout(); wid.setLayout(layout)
        lbl = QLabel("New address for: " + gui_instr.getDisplayName("long"))
        layout.addWidget(lbl)
        le_value = QLineEdit(gui_instr.address)
        layout.addWidget(le_value)
        win.le_value = le_value

        if gui_instr.slot is not None:
            lbl_slot = QLabel("Slot: ")
            slots = gui_instr.instr_dict.get('slots', None)
            cb_slot = Combobox()
            for s in slots:
                cb_slot.addItem(str(s), s)
            layout.addWidget(lbl_slot)
            layout.addWidget(cb_slot)
            cb_slot.setCurrentIndex(gui_instr.slot-1)
            win.cb_slot = cb_slot

        bt_ok = QPushButton("Apply")
        bt_cancel = QPushButton("Cancel")
        Hlayout = QHBoxLayout()
        Hlayout.addWidget(bt_ok)
        Hlayout.addWidget(bt_cancel)
        layout.addLayout(Hlayout)

        def okClicked():
            value = le_value.text()
            gui_instr.address = value
            if gui_instr.slot is not None:
                gui_instr.slot = win.cb_slot.currentData()
            self.gui_updateGuiInstrument(gui_instr)
            win.close()

        def cancelClicked():
            win.close()

        bt_ok.clicked.connect(okClicked)
        bt_cancel.clicked.connect(cancelClicked)




    def window_Rename(self, gui_dev_or_instr):
        # window with a line edit to rename the selected item
        data = gui_dev_or_instr
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
        self.win_rename.le_value = le_value
        bt_ok = QPushButton("Rename")
        bt_cancel = QPushButton("Cancel")
        Hlayout = QHBoxLayout()
        Hlayout.addWidget(bt_ok)
        Hlayout.addWidget(bt_cancel)
        layout.addLayout(Hlayout)

        def okClicked():
            value = le_value.text()
            if isinstance(data, GuiInstrument):
                self.lab.renameInstrument(data, value)
            elif isinstance(data, GuiDevice):
                self.lab.renameDevice(data, value)
            self.win_rename.close()

        def cancelClicked():
            self.win_rename.close()

        bt_ok.clicked.connect(okClicked)
        bt_cancel.clicked.connect(cancelClicked)



    def window_SelectDevices(self, gui_instr):
        win = self.win_editdevices

        win.setWindowTitle("Add devices " + gui_instr.getDisplayName())
        win.setWindowIcon(QtGui.QIcon("resources/instruments.svg"))
        wid = QWidget()
        win.setCentralWidget(wid)
        layout = QGridLayout()
        wid.setLayout(layout)

        # widgets
        lw = QListWidget()
        lw.setSelectionMode(2)
        dev_list = self.lab.model.getDevicesList(gui_instr.ph_instr)
        lw.addItems(dev_list)
        btn_add = QPushButton('Add devices')
        btn_cancel = QPushButton('Cancel')

        layout.addWidget(lw, 0, 0, 1, 2)
        layout.addWidget(btn_add, 1, 0)
        layout.addWidget(btn_cancel, 1, 1)

        def onAdd():
            devices = []
            for item in lw.selectedItems():
                devices.append(dict(ph_name=item.text()))
            self.lab.newDevicesFromRack(gui_instr, devices)
            win.close()

        btn_add.clicked.connect(onAdd)
        btn_cancel.clicked.connect(win.close)

