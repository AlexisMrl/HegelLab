import time
from PyQt5.QtWidgets import (
    QMainWindow,
    QLineEdit,
    QTreeWidgetItem,
    QLabel,
    QPushButton,
    QMenu,
    QAction,
)
from PyQt5 import QtGui, uic
from PyQt5.QtCore import Qt
from widgets.WindowWidget import AltDragWindow


class MainWindow(AltDragWindow):
    def __init__(self, lab):
        super().__init__()
        # -- ui setup --
        uic.loadUi("ui/MainWindow.ui", self)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setWindowTitle("HegelLab")
        self.setWindowIcon(QtGui.QIcon("resources/favicon/favicon.png"))
        self.resize(1100, 600)
        self.toolBar.setToolButtonStyle(2)  # text beside icon
        self.toolBar.setContextMenuPolicy(Qt.PreventContextMenu)
        # add a line edit in the toolbar for filename (not possible from designer):
        self.filename_edit = QLineEdit()
        self.filename_edit.setObjectName("filename_edit")
        self.filename_edit.setPlaceholderText("filename")
        self.filename_edit.setFixedWidth(200)
        self.toolBar.addWidget(self.filename_edit)
        # add disabled stop, abort buttons:
        self.pause_button = QPushButton("Pause")
        self.pause_button.setEnabled(False)
        self.toolBar.addWidget(self.pause_button)
        self.abort_button = QPushButton("Abort")
        self.abort_button.setEnabled(False)
        self.toolBar.addWidget(self.abort_button)
        # display buttons
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
        # could not find a better way to insert before the separator
        self.toolBar.insertAction(self.toolBar.actions()[1], self.btn_display)
        # add label for sweep status to status bar
        self.statusBar().addWidget(QLabel("Sweep status: "))
        self.sweep_status = QLabel("Ready")
        self.statusBar().addWidget(self.sweep_status)
        self.sweep_iteration = QLabel()
        self.statusBar().addWidget(self.sweep_iteration)
        self.sweep_estimation = QLabel()
        self.statusBar().addWidget(self.sweep_estimation)
        # console button
        self.btn_console = QAction(QtGui.QIcon("resources/console.svg"), "Console")
        self.btn_console.triggered.connect(lambda: lab.showConsole())
        #self.toolBar.insertAction(self.toolBar.actions()[0], self.btn_console)
        # width for first column for tree:
        self.tree_sw.setColumnWidth(0, 340)
        # before_wait:
        self.sb_before_wait.setMinimum(0)

        # -- end ui setup --
        self.lab = lab
        self.tree_sw.dropMimeData = lambda parent, row, data, action: self.onDrop(
            self.tree_sw, parent, row, data, action
        )
        self.tree_out.dropMimeData = lambda parent, row, data, action: self.onDrop(
            self.tree_out, parent, row, data, action
        )
        self.tree_log.dropMimeData = lambda parent, row, data, action: self.onDrop(
            self.tree_log, parent, row, data, action
        )

        # -- windows --
        self.win_sw_setup = QMainWindow()

        # -- Connect signals to slots --
        self.actionInstruments.triggered.connect(self.lab.showRack)
        self.actionDisplay.triggered.connect(self.lab.showDisplay)
        self.actionMonitor.triggered.connect(self.lab.showMonitor)
        # trees:
        self.tree_sw.itemSelectionChanged.connect(self.onSweepSelectionChanged)
        self.tree_out.itemSelectionChanged.connect(self.onOutSelectionChanged)
        self.tree_log.itemSelectionChanged.connect(self.onLogSelectionChanged)
        self.sw_remove.clicked.connect(self.tree_sw.removeSelected)
        self.out_remove.clicked.connect(self.tree_out.removeSelected)
        self.log_remove.clicked.connect(self.tree_log.removeSelected)
        self.tree_sw.itemDoubleClicked.connect(self.triggerShowSweepConfig)

        # sweep:
        self.actionStartSweep.triggered.connect(self.triggerStartSweep)
        self.pause_button.clicked.connect(self.lab.pauseSweep)
        self.abort_button.clicked.connect(self.lab.abortSweep)

    def onDrop(self, tree, parent, row, data, action):
        # what happens when the item is dropped
        # extract data:
        instr_nickname = str(data.data("instrument-nickname"), "utf-8")
        dev_nickname = str(data.data("device-nickname"), "utf-8")
        if tree == self.tree_sw:
            self.lab.addSweepDev(instr_nickname, dev_nickname)
        elif tree == self.tree_out:
            self.lab.addOutputDev(instr_nickname, dev_nickname)
        elif tree == self.tree_log:
            self.lab.addLogDev(instr_nickname, dev_nickname)
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

    def triggerStartSweep(self):
        # ask the lab to start the sweep
        self.gui_sweepStarting
        self.lab.startSweep()

    def closeEvent(self, event):
        self.lab.askClose(event)

    # -- gui -- (called by the lab)
    def _gui_makeItem(self, tree, gui_dev):
        item = QTreeWidgetItem()
        item.setChildIndicatorPolicy(QTreeWidgetItem.DontShowIndicatorWhenChildless)
        item.setText(0, gui_dev.getDisplayName("long", with_instr=True))
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

    def gui_renameDevice(self, gui_dev):
        item = self.tree_sw.findItemByData(gui_dev)
        if item is not None:
            item.setText(0, gui_dev.getDisplayName("long", with_instr=True))
        item = self.tree_out.findItemByData(gui_dev)
        if item is not None:
            item.setText(0, gui_dev.getDisplayName("long", with_instr=True))
        item = self.tree_log.findItemByData(gui_dev)
        if item is not None:
            item.setText(0, gui_dev.getDisplayName("long", with_instr=True))

    def gui_updateSweepValues(self, gui_dev):
        # set sweep values to self.tree_sw.selectedItem()
        dev_item = self.tree_sw.findItemByData(gui_dev)
        dev_item.setText(1, str(gui_dev.sweep[2]))
        dev_item.setText(2, str(gui_dev.sweep[:2]))

    def gui_getSweepGuiDevs(self):
        # go through self.tree_sw and return devs, start, stop, npts
        return [self.tree_sw.getData(item) for item in self.tree_sw]

    def gui_getOutputGuiDevs(self):
        return [self.tree_out.getData(item) for item in self.tree_out]

    def gui_getLogGuiDevs(self):
        return [self.tree_log.getData(item) for item in self.tree_log]
    
    def gui_sweepStarting(self):
        self.sweep_status.setText("Starting")

    def gui_sweepStarted(self):
        self.pause_button.setEnabled(True)
        self.abort_button.setEnabled(True)
        self.actionStartSweep.setEnabled(False)
        self.gb_sweep.setEnabled(False)
        self.gb_out.setEnabled(False)
        self.gb_log.setEnabled(False)
        self.gb_param.setEnabled(False)
        self.gb_comment.setEnabled(False)
        self.filename_edit.setEnabled(False)
        self.sweep_status.setText("Running")

    def gui_sweepFinished(self):
        self.pause_button.setEnabled(False)
        self.abort_button.setEnabled(False)
        self.actionStartSweep.setEnabled(True)
        self.gb_sweep.setEnabled(True)
        self.gb_out.setEnabled(True)
        self.gb_log.setEnabled(True)
        self.gb_param.setEnabled(True)
        self.gb_comment.setEnabled(True)
        self.filename_edit.setEnabled(True)
        # Reset pause button (in case of Pause->Abort):
        if self.pause_button.text() == "Resume":
            self.gui_sweepResumed()
        self.sweep_status.setText("Ready")
        self.sweep_iteration.setText("")
        self.sweep_estimation.setText("")

    def gui_sweepPaused(self):
        self.pause_button.setText("Resume")
        self.pause_button.clicked.disconnect()
        self.pause_button.clicked.connect(self.lab.resumeSweep)
        self.sweep_status.setText("Paused")

    def gui_sweepResumed(self):
        self.pause_button.setText("Pause")
        self.pause_button.clicked.disconnect()
        self.pause_button.clicked.connect(self.lab.pauseSweep)
        self.sweep_status.setText("Running")

    def gui_removeDevice(self, gui_dev):
        # remove the device from the trees
        self.tree_sw.removeByData(gui_dev)
        self.tree_out.removeByData(gui_dev)
        self.tree_log.removeByData(gui_dev)

    def _gui_progress(self, current_pts, total_pts):
        # i/n
        self.sweep_iteration.setText(f"{current_pts}/{total_pts}")

    def _gui_eta(self, start_time, current_pts, total_pts):
        # display it as h:m:s:
        elapsed = time.time() - start_time
        remaining = elapsed * (total_pts - current_pts) / current_pts

        h = remaining // 3600
        m = (remaining % 3600) // 60
        s = remaining % 60
        self.sweep_estimation.setText(f"ETA: {h:.0f}:{m:02.0f}:{s:02.0f}")

    def gui_sweepStatus(self, current_sweep):
        # update the sweep status bar
        self._gui_progress(current_sweep.iteration[0], current_sweep.iteration[1])
        self._gui_eta(
            current_sweep.start_time,
            current_sweep.iteration[0],
            current_sweep.iteration[1],
        )

    # -- end gui --
