import time
from PyQt5.QtWidgets import (
    QLineEdit,
    QTreeWidgetItem,
    QLabel,
    QPushButton,
    QMenu,
    QAction,
    QFileDialog,
)
from PyQt5 import QtGui, uic
from PyQt5.QtCore import Qt
from widgets.WindowWidget import Window
from PyQt5.QtCore import pyqtSignal
from src.GuiInstrument import GuiDevice, GuiInstrument


class MainWindow(Window):
    def __init__(self, lab):
        super().__init__()
        self.folder_path = "./temp/"
        # -- ui setup --
        uic.loadUi("ui/MainWindow.ui", self)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setWindowTitle("HegelLab")
        self.setWindowIcon(QtGui.QIcon("resources/favicon/favicon.png"))
        self.resize(1100, 600)
        self.toolBar.setToolButtonStyle(2)  # text beside icon
        self.toolBar.setContextMenuPolicy(Qt.PreventContextMenu)
        # add stop and abort buttons:
        self.pause_button = QPushButton("Pause", enabled=False)
        self.abort_button = QPushButton("Abort", enabled=False)
        self.toolBar.addWidget(self.pause_button)
        self.toolBar.addWidget(self.abort_button)
        # add a line edit in the toolbar for filename (not possible from designer):
        self.toolBar.addSeparator()
        self.filename_edit = QLineEdit()
        self.filename_edit.setObjectName("filename_edit")
        self.filename_edit.setPlaceholderText("filename")
        self.filename_edit.setFixedWidth(200)
        self.toolBar.addWidget(self.filename_edit)
        # path select
        self.folder_path_button = QPushButton("Select path")
        self.folder_path_label = QLabel(self.folder_path)
        self.toolBar.addWidget(self.folder_path_button)
        self.statusBar().addPermanentWidget(self.folder_path_label)
        # display action buttons
        menu_display = QMenu()
        simple_icon = QtGui.QIcon("resources/display1.svg")
        dual_icon = QtGui.QIcon("resources/display1.svg")
        self.btn_display = QAction(simple_icon, "Display")
        self.btn_display.triggered.connect(lambda: lab.showDisplay(None))
        self.one_display_action = QAction(simple_icon, "Simple display")
        self.one_display_action.triggered.connect(lambda: lab.showDisplay(False))
        self.two_display_action = QAction(dual_icon, "Dual display")
        self.two_display_action.triggered.connect(lambda: lab.showDisplay(True))
        menu_display.addAction(self.one_display_action)
        menu_display.addAction(self.two_display_action)
        self.btn_display.setMenu(menu_display)
        self.toolBar.insertAction(self.toolBar.actions()[1], self.btn_display) # insert before the separator
        # StatusBar: add label for sweep status
        self.statusBar().addWidget(QLabel("Sweep status: "))
        self.sweep_status = QLabel("Ready")
        self.statusBar().addWidget(self.sweep_status)
        self.sweep_iteration = QLabel()
        self.statusBar().addWidget(self.sweep_iteration)
        self.sweep_estimation = QLabel()
        self.statusBar().addWidget(self.sweep_estimation)
        # width for first column for tree:
        self.tree_sw.setColumnWidth(0, 340)
        # before_wait:
        self.sb_before_wait.setMinimum(0)
        # -- end ui setup --

        self.lab = lab
        self.win_swsetup = Window()
        self.win_retroaction = self.window_Retroaction()

        self.tree_sw.remove_btn = self.sw_remove
        self.tree_out.remove_btn = self.out_remove
        self.tree_log.remove_btn = self.log_remove

        # -- Connect signals to slots --
        self.actionInstruments.triggered.connect(self.lab.showRack)
        self.actionDisplay.triggered.connect(self.lab.showDisplay)
        self.actionMonitor.triggered.connect(self.lab.showMonitor)

        self.folder_path_button.clicked.connect(self.onSelectSweepPath)

        self.tree_sw.guiDeviceDropped.connect(self.onDropSweepDev)
        self.tree_out.guiDeviceDropped.connect(self.onDropOutDev)
        self.tree_log.guiDeviceDropped.connect(self.onDropLogDev)
        self.tree_sw.itemDoubleClicked.connect(lambda item: self.lab.setSweepDevice(self.tree_sw.getData(item), True))

        self.sw_remove.clicked.connect(lambda: self.onRemoveClicked(self.tree_sw))
        self.out_remove.clicked.connect(lambda: self.onRemoveClicked(self.tree_out))
        self.log_remove.clicked.connect(lambda: self.onRemoveClicked(self.tree_log))

        self.tree_sw.itemSelectionChanged.connect(lambda: self.onSelectionChanged(self.tree_sw))
        self.tree_out.itemSelectionChanged.connect(lambda: self.onSelectionChanged(self.tree_out))
        self.tree_log.itemSelectionChanged.connect(lambda: self.onSelectionChanged(self.tree_log))

        # sweep:
        self.actionStartSweep.triggered.connect(self.onTriggerStartSweep)
        self.pause_button.clicked.connect(self.lab.pauseSweep)
        self.abort_button.clicked.connect(self.lab.abortSweep)

    def initShortcuts(self):
        super().initShortcuts()

    def closeEvent(self, event):
        self.lab.askClose(event)
    

    # -- TREE RELATED --

    def focusTreeSw(self):
        self.lab.showMain()
        self.tree_sw.setFocus(True)
    def focusTreeOut(self):
        self.lab.showMain()
        self.tree_out.setFocus(True)
    def focusTreeLog(self):
        self.lab.showMain()
        self.tree_log.setFocus(True)

    def _reorder(self, tree, gui_dev, new_row):
        # we always add to last row (new_row is threrefore not used)
        old_item = tree.findItemByData(gui_dev)
        self._makeOrUpdateItem(tree, gui_dev, force_add=True)
        old_item_row = tree.indexFromItem(old_item).row()
        tree.takeTopLevelItem(old_item_row)

    def onDropSweepDev(self, gui_dev, row):
        if not self.tree_sw.findItemByData(gui_dev):
            self.lab.setSweepDevice(gui_dev, True)
        else: self._reorder(self.tree_sw, gui_dev, row)
    def onDropOutDev(self, gui_dev, row):
        if not self.tree_out.findItemByData(gui_dev):
            self.lab.setOutDevice(gui_dev, True)
        else: self._reorder(self.tree_out, gui_dev, row)
    def onDropLogDev(self, gui_dev, row):
        if not self.tree_log.findItemByData(gui_dev):
            self.lab.setLogDevice(gui_dev, True)
        else: self._reorder(self.tree_log, gui_dev, row)

    def onRemoveClicked(self, tree):
        if (gui_dev := tree.selectedData()):
            set_fn = {self.tree_sw:self.lab.setSweepDevice,
                      self.tree_out:self.lab.setOutDevice,
                      self.tree_log:self.lab.setLogDevice}[tree]
            set_fn(gui_dev, False)
    
    def onSelectionChanged(self, tree):
        tree.remove_btn.setEnabled(tree.selectedItem() is not None)

    def _makeOrUpdateItem(self, tree, gui_dev, force_add=False):
        if force_add or not (dev_item := tree.findItemByData(gui_dev)):
            row = tree.topLevelItemCount() # we always add to last row
            dev_item= QTreeWidgetItem()
            dev_item.setChildIndicatorPolicy(QTreeWidgetItem.DontShowIndicatorWhenChildless)
            tree.setData(dev_item, gui_dev)
            tree.insertTopLevelItem(row, dev_item)
        # filling
        dev_item.setText(0, gui_dev.getDisplayName("long", with_instr=True))
        if tree == self.tree_sw:
            dev_item.setText(1, str(gui_dev.sweep[2]))
            range_text = str(gui_dev.sweep[:2])
            if gui_dev.raz: range_text += ', ret. to 0'
            dev_item.setText(2, range_text)
            #TODO: show steps

    def gui_updateSweepDevice(self, gui_dev, boo):
        if not boo: self.gui_onDeviceRemoved(gui_dev, self.tree_sw)
        else: self._makeOrUpdateItem(self.tree_sw, gui_dev)
    def gui_updateOutDevice(self, gui_dev, boo):
        if not boo: self.gui_onDeviceRemoved(gui_dev, self.tree_out)
        else: self._makeOrUpdateItem(self.tree_out, gui_dev)
    def gui_updateLogDevice(self, gui_dev, boo):
        if not boo: self.gui_onDeviceRemoved(gui_dev, self.tree_log)
        else: self._makeOrUpdateItem(self.tree_log, gui_dev)

    def gui_onDeviceRemoved(self, gui_dev, tree=None):
        # if no tree, remove from all
        # if tree, remove from tree
        if tree: tree.removeByData(gui_dev)
        else:
            [tree.removeByData(gui_dev) for tree in [self.tree_sw, self.tree_out, self.tree_log]]
    
    def gui_onDeviceRenamed(self, gui_dev):
        for tree in [self.tree_sw, self.tree_out, self.tree_log]:
            if tree.findItemByData(gui_dev):
                self._makeOrUpdateItem(tree, gui_dev)
    
    def gui_onInstrumentRenamed(self, gui_instr):
        for gui_dev in gui_instr.gui_devices:
            self.gui_onDeviceRenamed(gui_dev)


    # -- SWEEP RELATED --

    def onTriggerStartSweep(self):
        if not self.actionStartSweep.isEnabled(): return
        sw_devs = [self.tree_sw.getData(item) for item in self.tree_sw]
        out_devs = [self.tree_out.getData(item) for item in self.tree_out]
        log_devs = [self.tree_log.getData(item) for item in self.tree_log]
        self.lab.startSweep(sw_devs, out_devs, log_devs)

    def gui_onSweepStarted(self, boo=True, text='Running'):
        self.pause_button.setEnabled(boo)
        self.abort_button.setEnabled(boo)
        self.actionStartSweep.setEnabled(not boo)
        self.sweep_status.setText(text)

    def _setEta(self, start_time, current_pts, total_pts):
        # display it as h:m:s:
        if None in [start_time, current_pts, total_pts]:
            self.sweep_estimation.setText("")
            return

        elapsed = time.time() - start_time
        remaining = elapsed * (total_pts - current_pts) / current_pts

        h = remaining // 3600
        m = (remaining % 3600) // 60
        s = remaining % 60
        self.sweep_estimation.setText(f"ETA: {h:.0f}:{m:02.0f}:{s:02.0f}")

    def gui_onSweepProgress(self, sweep_status):
        # update the sweep status bar
        current_pts, total_pts = sweep_status.iteration[0], sweep_status.iteration[1]
        self._setEta(sweep_status.start_time, current_pts, total_pts)
        self.sweep_iteration.setText(f"{current_pts}/{total_pts}")

    def _changePauseButton(self, new_text, new_onClick):
        self.pause_button.setText(new_text)
        self.pause_button.clicked.disconnect()
        self.pause_button.clicked.connect(new_onClick)

    def gui_onSweepPaused(self):
        self._changePauseButton("Resume", self.lab.resumeSweep)
        self.sweep_status.setText("Paused")

    def gui_onSweepResumed(self):
        self._changePauseButton("Pause", self.lab.pauseSweep)
        self.sweep_status.setText("Running")

    def gui_onSweepFinished(self):
        self.gui_onSweepStarted(False, 'Ready')
        # Reset pause button (in case of Pause->Abort):
        self._changePauseButton("Pause", self.lab.pauseSweep)
        self._setEta(None, None, None)
    

    # -- Select sweep path --
    def onSelectSweepPath(self):
        folder_path = QFileDialog.getExistingDirectory(self, 'Select Folder')
        if folder_path:
            folder_path += "/"
            self.folder_path = folder_path 
            self.folder_path_label.setText(folder_path)
    
    # -- retroaction window --
    def window_Retroaction(self):
        win = Window()
        uic.loadUi("ui/RetroactionWindow.ui", win)
        win.setWindowTitle("Retroaction loop")
        
        def onOpen():
            selected_ids = win.combo_ids_devs.currentData()
            selected_vds = win.combo_vds_devs.currentData()
            index_ids, index_vds = -1, -1 # values used to save selected dev position
            out_devs = [self.tree_out.getData(item) for item in self.tree_out]
            win.combo_ids_devs.clear()
            win.combo_vds_devs.clear()
            for i, dev in enumerate(out_devs):
                win.combo_ids_devs.addItem(dev.getDisplayName("long", with_instr=True), dev)
                win.combo_vds_devs.addItem(dev.getDisplayName("long", with_instr=True), dev)
                if dev is selected_ids: index_ids = i
                if dev is selected_vds: index_vds = i
            if selected_ids != -1:
                win.combo_ids_devs.setCurrentIndex(index_ids)
            if selected_vds != -1:
                win.combo_vds_devs.setCurrentIndex(index_vds)

            win.focus()
            
        self.pb_retroaction.clicked.connect(onOpen)
        
        def onClose(event):
            self.pb_retroaction.setText("Enabled" if win.group.isChecked() else "Disabled")
            win.close()
        win.closeEvent = onClose

        return win