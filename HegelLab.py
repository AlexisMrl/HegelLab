import traceback
import sys

from PyQt5.QtWidgets import QApplication

from views import Main, Rack, Display, Console
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
    def __init__(self, app):
        self.app = app
        self.loader = LoaderSaver.LoaderSaver(self)
        self.pop = Popup.Popup()
        # model, views
        self.model = Model.Model()
        self.view_main = Main.Main(self)
        self.view_rack = Rack.Rack(self)
        self.view_display = Display.Display(self)
        self.view_console = Console.Console(self)
        
        # push variables to console
        self.view_console.push_vars({"hl": self})
        self.view_console.push_vars({"app": self.app})
        self.view_console.push_vars({"vm": self.view_main})
        self.view_console.push_vars({"vr": self.view_rack})
        self.view_console.push_vars({"vd": self.view_display})
        self.view_console.push_vars({"vc": self.view_console})

        # data
        self.instr_list = self.loader.importJsonFile('instruments.json')
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
    
    def showConsole(self):
        self.view_console.show()
        self.view_console.raise_()

    def askClose(self, event):
        if self.pop.askQuit():
            self.view_main.close()
            self.view_rack.close()
            self.view_display.close()
            self.view_console.close()
            if self.app is not None:
                self.app.closeAllWindows()
        else:
            event.ignore()

    def showInstrumentConfig(self, gui_instr):
        # launch the config window for the selected instrument
        # self.view_rack.setEnabled(False)
        # self.view_rack.window_configInstrument(gui_instr)
        print(gui_instr.nickname)

    def showDeviceConfig(self, gui_dev):
        # launch the config window for the selected device
        # self.view_rack.setEnabled(False)
        # self.view_rack.window_configDevice(gui_dev)
        print(gui_dev.nickname)
    
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
        instr_name = instr_dict.get('name')
        ph_class = eval(instr_dict.get('ph_class'))
        driver = eval(instr_dict.get('driver', 'Drivers.Default'))
        # instanciate GuiInstrument
        gui_instr = GuiInstrument(nickname, instr_name, ph_class, driver, addr, slot)
        gui_instr.instr_dict = instr_dict
        return gui_instr
    
    def _instanciateGuiDevices(self, gui_instr, instr_dict):
        devices = instr_dict.get('devices')
        for dev_dict in devices:
            ph_name = dev_dict.get('ph_name')
            nickname = dev_dict.get('nickname', ph_name)
            nickname = self._checkDevNickname(nickname, gui_instr)
            extra_args = dev_dict.get('extra_args', {})
            # instanciate GuiDevice
            gui_dev = GuiDevice(nickname, ph_name, extra_args, parent=gui_instr)
            
            # limit, scale, ramp
            scale_kw = dict(dev_dict.get('scale', {}))
            scale_kw['quiet_del'] = True
            if "divisor" in scale_kw.values():
                scale_kw['invert_trans'] = True
                scale_kw['scale_factor'] = scale_kw.pop('divisor')
            elif "multiplier" in scale_kw.values():
                scale_kw['scale_factor'] = scale_kw.pop('multiplier')
                
            gui_dev.logical_kwargs['scale'] = scale_kw

            ramp_kw = dict(dev_dict.get('ramp', {}))
            ramp_kw['quiet_del'] = True
            gui_dev.logical_kwargs['ramp'] = ramp_kw

            limit_kw = dict(dev_dict.get('limit', {}))
            limit_kw['quiet_del'] = True
            gui_dev.logical_kwargs['limit'] = limit_kw

            gui_instr.gui_devices.append(gui_dev)

    def newInstrumentFromRack(self, nickname, addr, slot, instr_dict):
        # control flow for instanciate GuiInstrument and load ph_instr 
        # instanciating
        gui_instr = self._instanciateGuiInstrument(nickname, addr, slot, instr_dict)
        self._instanciateGuiDevices(gui_instr, instr_dict)
        self.gui_instruments.append(gui_instr)
        # loading
        #self._loadGuiInstrument(gui_instr)
        #self._loadGuiDevices(gui_instr)

        # "signals"
        self.view_rack.gui_addGuiInstrument(gui_instr)
        self.view_rack.win_add.close()
        self.view_console.push_vars({gui_instr.nickname: gui_instr.ph_instr})

        self.view_rack.win_create_dev.close()

    def _loadGuiInstrument(self, gui_instr):
        # try loading a GuiInstrument == set its ph_instr attribute
        try:
            gui_instr.driver.load(gui_instr)
        except Exception as e:
            tb_str = "".join(traceback.format_tb(e.__traceback__))
            self.pop.instrLoadError(e, tb_str)
            return False
        return True

    def _loadGuiDevices(self, gui_instr):
        for gui_dev in gui_instr.gui_devices:
            try:
                gui_dev.ph_dev = self.model.getDevice(
                    gui_instr.ph_instr, gui_dev.ph_name
                )
                gui_dev.type = self.model.devType(gui_dev.ph_dev)
                gui_dev.ph_choice = self.model.getChoices(gui_dev.ph_dev)
            except Exception as e:
                tb_str = "".join(traceback.format_tb(e.__traceback__))
                self.pop.devLoadError(e, tb_str)
                continue
            
            # logical device
            try:
                gui_dev.logical_dev = self.model.makeLogicalDevice(gui_dev.getPhDev(), gui_dev.logical_kwargs)
            except Exception as e:
                tb_str = "".join(traceback.format_tb(e.__traceback__))
                self.pop.devLoadLogicalError(e, tb_str)
    
    def loadGuiInstrument(self, gui_instr):
        # control flow for loading a GuiInstrument
        if self._loadGuiInstrument(gui_instr):
            self._loadGuiDevices(gui_instr)
        self.view_rack.gui_updateGuiInstrument(gui_instr)

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
        if gui_dev.ph_dev is None: return
        value = self.model.getValue(gui_dev.getPhDev())
        gui_dev.cache_value = value
        self.view_rack.gui_updateDeviceValue(gui_dev, value)

    def setValue(self, gui_dev, val):
        # set the value of the GuiDevice and update the gui
        try:
            self.model.setValue(gui_dev.getPhDev(), val)
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

    # -- SWEEP TREES --

    def addSweepDev(self, instr_nickname, dev_nickname):
        # add a device to the sweep tree, launch the config window
        gui_dev = self.getGuiInstrument(instr_nickname).getGuiDevice(dev_nickname)

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
        if gui_dev.type[1] == False and self.pop.notGettable() == False:
            return
        if self.view_main.tree_out.findItemByData(gui_dev) != None:
            self.pop.devAlreadyHere()
            return
        self.view_main.gui_addOutItem(gui_dev)

    def addLogDev(self, instr_nickname, dev_nickname):
        # add a device to the log tree
        gui_dev = self.getGuiInstrument(instr_nickname).getGuiDevice(dev_nickname)
        if self.view_main.tree_log.findItemByData(gui_dev) != None:
            self.pop.devAlreadyHere()
            return
        self.view_main.gui_addLogItem(gui_dev)

    def showSweepConfig(self, gui_dev):
        # launch the config window for gui_dev sweep device
        driver_cls = gui_dev.parent.driver
        driver_cls.sweep(self, gui_dev)

    def setSweepValues(self, gui_dev, start, stop, npts):
        # set sweep values for gui_dev and update the gui
        gui_dev.sweep = [start, stop, npts]
        self.view_main.gui_updateSweepValues(gui_dev)

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

def run(with_app=True):

    app = None
    if with_app:
        app = QApplication(sys.argv)
        app.setApplicationDisplayName("HegelLab")
    hl = HegelLab(app)

    # splash screen
    from PyQt5.QtWidgets import QSplashScreen
    from PyQt5.QtGui import QPixmap
    from PyQt5 import QtCore
    pixmap = QPixmap("./resources/favicon/favicon.png")
    pixmap = pixmap.scaled(256, 256)
    splash = QSplashScreen(pixmap)
    splash.showMessage(
        "Loading HegelLab...",
        alignment=QtCore.Qt.AlignBottom | QtCore.Qt.AlignHCenter,
        color=QtCore.Qt.white,
    )
    splash.show()
    splash.finish(hl.view_main)

    hl.showMain()
    
    # TODO: redirect to console
    if with_app:
        sys.stdout = open("logs/stdout.log", "w")
        sys.stderr = open("logs/stderr.log", "w")
        sys.exit(app.exec_())
    
    return hl

if __name__ == "__main__":
    args = sys.argv[1:]
    hl = run(with_app= "--no-app" not in args)