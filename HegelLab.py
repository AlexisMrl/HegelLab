import traceback
import sys

from PyQt5.QtWidgets import QApplication

from windows import MainWindow, RackWindow, DisplayWindow, MonitorWindow
from src import LoaderSaver, Model, Popup, SweepThread, Drivers
from src.GuiInstrument import GuiInstrument, GuiDevice
from src.SweepIdxIter import IdxIter

from pyHegel import instruments # for eval

import numpy as np
import time
import os


# HegelLab is made to support any instrument with minimal effort.
# It should be enough to add the instrument class to the json file.


class HegelLab:
    def __init__(self, app=None):
        self.app = app
        self.loader = LoaderSaver.LoaderSaver(self)
        self.pop = Popup.Popup()
        # model, views
        self.model = Model.Model()
        self.view_main = MainWindow.MainWindow(self)
        self.view_rack = RackWindow.RackWindow(self)
        self.view_display = DisplayWindow.DisplayWindow(self)
        self.view_monitor = MonitorWindow.MonitorWindow(self)


        # data
        self.instr_list = self.loader.importFromJSON('default_instruments.json')
        self.gui_instruments = []  # list of GuiInstrument in rack

        # sweep related
        self.loop_control = self.model.initLoopControl()
        self.sweep_thread = SweepThread.SweepThread(
            self.model.startSweep, self.loop_control
        )
        self.sweep_thread.progress_signal.connect(self.onSweepSignalProgress)
        self.sweep_thread.error_signal.connect(self.onSweepSignalError)
        self.sweep_thread.finished_signal.connect(self.onSweepSignalFinished)

    # -- GENERAL --

    def showMain(self):
        self.view_main.show()
        self.view_main.raise_()

    def showRack(self):
        self.view_rack.show()
        self.view_rack.raise_()

    def showDisplay(self, dual=None):
        self.view_display.show_(dual)
        self.view_display.raise_()
    
    def showMonitor(self):
        self.view_monitor.show()
        self.view_monitor.raise_()

    def askClose(self, event):
        if self.pop.askQuit():
            self.view_main.close()
            self.view_rack.close()
            self.view_display.close()
            self.view_monitor.close()
            self.model.close()
            self.loader.close()
            if self.app is not None:
                self.app.closeAllWindows()
        else:
            event.ignore()
    
    def getGuiInstrument(self, instr_nickname):
        for gui_instr in self.gui_instruments:
            if gui_instr.nickname != instr_nickname:
                continue
            return gui_instr
        return None

    # -- RACK --

    def _checkInstrNickname(self, nickname):
        # construct a unique instr nickname
        i, base = 1, nickname
        for gui_instr in self.gui_instruments:
            if nickname == gui_instr.nickname:
                nickname = base + "_{}".format(i)
                i += 1
        return nickname

    def _checkDevNickname(self, nickname, gui_instr):
        # construct a unique dev nickname
        i, base = 1, nickname
        for gui_dev in gui_instr.gui_devices:
            if nickname == gui_dev.nickname:
                nickname = base + " ({})".format(i)
                i += 1
        return nickname

    def _instanciateGuiInstrument(self, nickname, addr, slot, instr_dict):
        # call only by the Rack when loading is clicked.
        # build GuiInstrument and populate dvices, but no ph_instr nor ph_dev
        # loading is done in loadGuiInstrument.
        nickname = self._checkInstrNickname(nickname)
        #ph_class = eval(instr_dict.get('ph_class'))
        ph_class = instr_dict.get('ph_class')
        #driver = eval(instr_dict.get('driver', 'Drivers.Default'))
        driver = instr_dict.get('driver', 'Drivers.Default')
        # instanciate GuiInstrument
        gui_instr = GuiInstrument(nickname, ph_class, driver, addr, slot)
        gui_instr.instr_dict = instr_dict
        return gui_instr
    
    def _instanciateGuiDevices(self, gui_instr, instr_dict):
        devices = instr_dict.get('devices', [])
        for dev_dict in devices:
            ph_name = dev_dict.get('ph_name')
            nickname = dev_dict.get('nickname', ph_name)
            nickname = self._checkDevNickname(nickname, gui_instr)
            extra_args = dict(dev_dict.get('extra_args', {}))
            # instanciate GuiDevice
            gui_dev = GuiDevice(nickname, ph_name, extra_args, parent=gui_instr)
            # type
            setget = dict(dev_dict.get('type', dict(set=None, get=None)))
            gui_dev.type = (setget['set'], setget['get'])
            # limit, scale, ramp
            scale_kw = dict(dev_dict.get('scale', {}))
            gui_dev.logical_kwargs['scale'] = scale_kw

            ramp_kw = dict(dev_dict.get('ramp', {}))
            gui_dev.logical_kwargs['ramp'] = ramp_kw

            limit_kw = dict(dev_dict.get('limit', {}))
            gui_dev.logical_kwargs['limit'] = limit_kw

            gui_instr.gui_devices.append(gui_dev)

    def newInstrumentFromRack(self, nickname, addr, slot, instr_dict):
        # control flow for instanciate GuiInstrument and load ph_instr 
        # instanciating
        gui_instr = self._instanciateGuiInstrument(nickname, addr, slot, instr_dict)
        self._instanciateGuiDevices(gui_instr, instr_dict)
        self.gui_instruments.append(gui_instr)
        # loading (not sure, featurewise)
        self.loadGuiInstrument(gui_instr)

        # "signals"
        self.view_rack.gui_addGuiInstrument(gui_instr)
        self.view_rack.win_add.close()

    def loadGuiInstrument(self, gui_instr):
        # ask for loading a GuiInstrument 
        # the driver must set the gui_instr.ph_instr attribute
        # if it fails, it must raise an exception and call loadGuiInstrumentError
        eval(gui_instr.driver).load(self, gui_instr)
    
    def loadGuiInstrumentError(self, gui_instr, exception):
        # called by drivers when loading a GuiInstrument
        tb_str = "".join(traceback.format_tb(exception.__traceback__))
        self.pop.instrLoadError(exception, tb_str)
        self.view_rack.gui_updateGuiInstrument(gui_instr)

    def loadGuiDevices(self, gui_instr):
        # called by drivers when loading a GuiInstrument
        for gui_dev in gui_instr.gui_devices:
            try:
                gui_dev.ph_dev = self.model.getDevice(
                    gui_instr.ph_instr, gui_dev.ph_name
                )
                # type
                detected_type = self.model.devType(gui_dev.ph_dev)
                type = [detected_type[0] if gui_dev.type[0] is None else gui_dev.type[0],
                        detected_type[1] if gui_dev.type[1] is None else gui_dev.type[1]]
                gui_dev.type = tuple(type)
                gui_dev.ph_choice = self.model.getChoices(gui_dev.ph_dev)
            except Exception as e:
                tb_str = "".join(traceback.format_tb(e.__traceback__))
                self.pop.devLoadError(e, tb_str)
                continue
            # logical device
            self.loadGuiLogicalDevice(gui_dev)

        self.view_rack.gui_updateGuiInstrument(gui_instr)
            
    def loadGuiLogicalDevice(self, gui_dev):
        try:
            basedev = gui_dev.getPhDev(basedev=True)
            gui_dev.logical_dev = self.model.makeLogicalDevice(basedev,
                                                               gui_dev.logical_kwargs,
                                                               gui_dev.parent.ph_instr)
        except Exception as e:
            tb_str = "".join(traceback.format_tb(e.__traceback__))
            self.pop.devLoadLogicalError(e, tb_str)

    def removeGuiInstrument(self, gui_instr):
        if self.pop.askRemoveInstrument(gui_instr.nickname) == False:
            return
        # remove its devices in the trees:
        for dev in gui_instr.gui_devices:
            self.view_main.gui_removeDevice(dev)
        self.view_rack.gui_removeGuiInstrument(gui_instr)
        for dev in gui_instr.gui_devices:
            self.view_main.gui_removeDevice(dev)
        self.gui_instruments.remove(gui_instr)

    def getValue(self, gui_dev):
        # get the value of the GuiDevice and update the gui
        dev = gui_dev.getPhDev()
        if dev is None: return
        value = self.model.getValue(gui_dev.getPhDev(basedev=True))

        # because logical_dev is innacessible when ramping:
        factor = gui_dev.logical_kwargs['scale'].get('factor', 1)
        value = value / factor

        gui_dev.cache_value = value
        self.view_rack.gui_updateDeviceValue(gui_dev, value)
        self.view_monitor.gui_updateDeviceValue(gui_dev, value)
        return value

    def setValue(self, gui_dev, val):
        # set the value of the GuiDevice and update the gui
        try:
            self.model.setValue(gui_dev.getPhDev(), val)
            QApplication.processEvents()
        except Exception as e:
            tb_str = "".join(traceback.format_tb(e.__traceback__))
            self.pop.setValueError(e, tb_str)
            return
        #self.view_rack.gui_updateDeviceValue(gui_dev, val)
        self.view_rack.win_set.close()

    def renameDevice(self, gui_dev, new_nickname):
        gui_dev.nickname = new_nickname
        self.view_main.gui_renameDevice(gui_dev)
        self.view_rack.gui_renameDevice(gui_dev)
        self.view_monitor.gui_renameDevice(gui_dev)

    # -- SWEEP TREES --

    def addSweepDev(self, instr_nickname, dev_nickname):
        # add a device to the sweep tree, launch the config window
        gui_dev = self.getGuiInstrument(instr_nickname).getGuiDevice(dev_nickname)
        
        if not gui_dev.isLoaded() and self.pop.devNotLoaded() == False:
            return

        if gui_dev.type[0] == False and self.pop.notSettable() == False:
            # if the device is not gettable, ask if we want to add it anyway
            return
        if self.view_main.tree_sw.findItemByData(gui_dev) != None:
            self.pop.devAlreadyHere()
            return
        self.view_main.gui_addSweepGuiDev(gui_dev)
        self.showSweepConfig(gui_dev)

    def addOutputDev(self, instr_nickname, dev_nickname):
        # add a device to the output tree
        gui_dev = self.getGuiInstrument(instr_nickname).getGuiDevice(dev_nickname)
        if not gui_dev.isLoaded() and self.pop.devNotLoaded() == False:
            return
        if gui_dev.type[1] == False and self.pop.notGettable() == False:
            return
        if self.view_main.tree_out.findItemByData(gui_dev) != None:
            self.pop.devAlreadyHere()
            return
        self.view_main.gui_addOutItem(gui_dev)

    def addLogDev(self, instr_nickname, dev_nickname):
        # add a device to the log tree
        gui_dev = self.getGuiInstrument(instr_nickname).getGuiDevice(dev_nickname)
        if not gui_dev.isLoaded() and self.pop.devNotLoaded() == False:
            return
            
        if self.view_main.tree_log.findItemByData(gui_dev) != None:
            self.pop.devAlreadyHere()
            return
        self.view_main.gui_addLogItem(gui_dev)

    def showSweepConfig(self, gui_dev):
        # launch the sweep config window for gui_dev
        driver_cls = eval(gui_dev.parent.driver)
        driver_cls.sweep(self, gui_dev)

    def setSweepValues(self, gui_dev, start, stop, npts):
        # set sweep values for gui_dev and update the gui
        gui_dev.sweep = [start, stop, npts]
        self.view_main.gui_updateSweepValues(gui_dev)
    
    def showConfig(self, gui_instr):
        # launch the driver config window
        driver_cls = eval(gui_instr.driver)
        driver_cls.config(self, gui_instr)
    
    def exportToJSON(self):
        self.loader.exportToJSON(self.gui_instruments)
    
    def importFromJSON(self):
        instruments_to_add = self.loader.importFromJSON()
        self.to_add = instruments_to_add
        # add the instruments
        for instr_ord_dict in instruments_to_add:
            nickname = instr_ord_dict.get('nickname', instr_ord_dict['ph_class'].split('.')[-1])
            addr = instr_ord_dict.get('address', None)
            slot = instr_ord_dict.get('slot', None)
            self.newInstrumentFromRack(nickname, addr, slot, instr_ord_dict)
    
    def exportToPyHegel(self):
        self.loader.exportToPyHegel(self.gui_instruments)

    # -- SWEEP THREAD --

    def _prepareFilename(self):
        filename = self.view_main.filename_edit.text()
        if filename == "":
            filename = "sweep"
        date = time.strftime("%Y%m%d")
        dir_path = "./temp/" + date
        if not os.path.exists(dir_path):
            os.mkdir(dir_path)
        filename = dir_path + "/%t_" + filename + ".txt"
        return filename

    def _startSweepCheckError(self, start, stop, npts, ph_sw_devs, ph_out_devs):
        if None in start or None in stop or None in npts:
            self.pop.sweepMissingDevParameter()
            return True
        if ph_sw_devs == []:
            self.pop.sweepNoDevice()
            return True
        if 0 in npts:
            self.pop.sweepZeroPoints()
            return True
        for start, stop in zip(start, stop):
            if start == stop:
                self.pop.sweepStartStopEqual()
                return True
        if ph_out_devs == [] and self.pop.sweepNoOutputDevice() == False:
            return True
        return False

    def _genLists(self, gui_sw_devs, gui_out_devs, gui_log_devs):
        # generate the lists for kwargs
        ph_sw_devs, start, stop, npts = [], [], [], []
        for dev in gui_sw_devs:
            ph_sw_devs.append(dev.getPhDev())
            start.append(dev.sweep[0])
            stop.append(dev.sweep[1])
            npts.append(dev.sweep[2])

        ph_out_devs = []
        for dev in gui_out_devs:
            ph_out_devs.append(dev.getPhDev())

        ph_log_devs = []
        for dev in gui_log_devs:
            ph_log_devs.append(dev.getPhDev())

        return ph_sw_devs, start, stop, npts, ph_out_devs, ph_log_devs

    def _allocData(self, gui_out_devs, start, stop, npts, alternate):
        # start, stop, npts are lists
        # allocate data in out_devices for the live view.
        # we allocate a numpy array for output devices
        # and an 'custom iterator' so the filling is in
        # a good order.

        reverse = [False] * len(start)
        for i, (sta, sto) in enumerate(zip(start, stop)):
            if sta > sto:
                reverse[i] = True

        if len(npts) == 1:
            npts = npts + [1]  # not .append to preserve npts
        if len(npts) == 2:
            for dev in gui_out_devs:
                dev.values = np.full(npts, np.nan)
                dev.sw_idx = IdxIter(*npts, *reverse, alternate)

    def startSweep(self):
        # trigger on start sweep button
        # prepare everything and start the thread.
        gui_sw_devs = self.view_main.gui_getSweepGuiDevs()
        gui_out_devs = self.view_main.gui_getOutputGuiDevs()
        gui_log_devs = self.view_main.gui_getLogGuiDevs()

        # generate lists and allocate data
        ph_sw_devs, start, stop, npts, ph_out_devs, ph_log_devs = self._genLists(
            gui_sw_devs, gui_out_devs, gui_log_devs
        )
        alternate = {True: "alternate", False: False}[
            self.view_main.cb_alternate.isChecked()
        ]
        self._allocData(gui_out_devs, start, stop, npts, alternate)

        # errors
        if self._startSweepCheckError(start, stop, npts, ph_sw_devs, ph_out_devs):
            return

        # prepare kw
        sweep_kwargs = {
            "dev": ph_sw_devs,
            "start": start,
            "stop": stop,
            "npts": npts,
            "out": ph_out_devs,
            "filename": self._prepareFilename(),
            "extra_conf": [self.view_main.te_comment.toPlainText()] + ph_log_devs,
            "beforewait": self.view_main.sb_before_wait.value(),
            "updown": alternate,
        }

        # run sweep thread
        self.sweep_thread.initSweepKwargs(sweep_kwargs)
        self.sweep_thread.initCurrentSweep(gui_sw_devs, gui_out_devs, time.time())
        for out in gui_out_devs:
            out.alternate = self.view_main.cb_alternate.isChecked()
        self.sweep_thread.start()

        # update gui
        self.view_display.onSweepStarted(self.sweep_thread.current_sweep)
        self.view_main.gui_sweepStarted()
        self.showDisplay()

    def onSweepSignalProgress(self, current_sweep):
        # connected to the sweep thread
        # current_sweep is a SweepStatusObject

        # update display and status
        self.view_display.onIteration(current_sweep)
        self.view_main.gui_sweepStatus(current_sweep)

    def onSweepSignalError(self, name, message):
        # called by the sweep thread
        self.pop.sweepThreadError(name, message)

    def onSweepSignalFinished(self):
        # called by the sweep thread
        self.view_main.gui_sweepFinished()

    def pauseSweep(self):
        # called by the main window
        self.loop_control.pause_enabled = True
        self.view_main.gui_sweepPaused()

    def resumeSweep(self):
        # called by the main window
        self.loop_control.pause_enabled = False
        self.view_main.gui_sweepResumed()

    def abortSweep(self):
        # called by the main window
        self.loop_control.abort_enabled = True
        self.loop_control.pause_enabled = False  # in case of Pause->Abort

if __name__ == "__main__":
    from PyQt5.QtWidgets import QSplashScreen
    from PyQt5.QtGui import QPixmap
    from PyQt5 import QtCore

    with_app = False
    if len(sys.argv) > 1 and sys.argv[1] == "--with-app":
        with_app = True
        app = QApplication([])
        app.setApplicationDisplayName("HegelLab")
    
    pixmap = QPixmap("./resources/favicon/favicon.png")
    pixmap = pixmap.scaled(256, 256)
    splash = QSplashScreen(pixmap)
    splash.showMessage(
        "Loading HegelLab...",
        alignment=QtCore.Qt.AlignBottom | QtCore.Qt.AlignHCenter,
        color=QtCore.Qt.white,
    )

    splash.show()

    hl = HegelLab()
    splash.finish(hl.view_main)

    hl.showMain()
    
    if with_app:
        sys.exit(app.exec())