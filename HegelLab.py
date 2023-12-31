import traceback
import sys

from PyQt5.QtWidgets import QApplication

from windows import MainWindow, RackWindow, DisplayWindow, MonitorWindow
from widgets import WindowWidget
from src import LoaderSaver, Model, Popup, SweepThread#, Shortcuts
from src.GuiInstrument import GuiInstrument, GuiDevice
from src.SweepIdxIter import IdxIter

from src import Drivers # for eval

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
        self.model = Model.Model(self)
        self.view_main = MainWindow.MainWindow(self)
        self.view_rack = RackWindow.RackWindow(self)
        self.view_display = DisplayWindow.DisplayWindow(self)
        self.view_monitor = MonitorWindow.MonitorWindow(self)

        # shortcut:
        WindowWidget.Window.lab = self
        WindowWidget.Window.initShortcutsAll()

        

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
        self.view_main.focus()

    def showRack(self):
        self.view_rack.focus()

    def showDisplay(self, dual=None):
        self.view_display.focus()
    
    def showMonitor(self):
        self.view_monitor.focus()

    def askClose(self, event):
        if self.pop.askQuit():
            self.sweep_thread.terminate()
            #self.model.close()
            WindowWidget.Window.killAll()
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
        ph_class = instr_dict.get('ph_class')
        driver = instr_dict.get('driver', 'Drivers.Default')
        # instanciate GuiInstrument
        gui_instr = GuiInstrument(nickname, ph_class, driver, addr, slot)
        gui_instr.instr_dict = instr_dict
        return gui_instr
    
    def _instanciateGuiDevices(self, gui_instr, instr_dict):
        # instanciate all the devices in instr_dict[devices] and add them to gui_instr
        devices = instr_dict.get('devices', [])
        for dev_dict in devices:
            ph_name = dev_dict.get('ph_name')
            nickname = dev_dict.get('nickname', ph_name)
            nickname_multi = dev_dict.get('nickname_multi', [])
            extra_args = dict(dev_dict.get('extra_args', {}))  #   <-, this one
            extra_args_multi = dict(dev_dict.get('extra_args_multi', {}))

            if extra_args_multi:
                # extra_args_multi = {'arg_name1': [arg_dev1, arg_dev2, ...], ... }
                # assume all lists have the same length
                nb_of_dev = len(list(extra_args_multi.values())[0])
                def gen_extra_args(i):
                    extra_args_keys = list(extra_args_multi.keys())
                    for key in extra_args_keys: 
                        # addd keys to the original extra_args dict -^
                        extra_args[key] = extra_args_multi[key][i]
                    return extra_args
                # recursive:
                for i in range(nb_of_dev):
                    if len(nickname_multi) == nb_of_dev:
                        new_nickname = nickname_multi[i]
                    else:
                        new_nickname = nickname.replace("%i", str(i))
                    dev_instr_dict = dict(dev_dict)
                    dev_instr_dict.pop('extra_args_multi')
                    dev_instr_dict['nickname'] = new_nickname
                    dev_instr_dict['extra_args'] = gen_extra_args(i)
                    self._instanciateGuiDevices(gui_instr, dict(devices=[dev_instr_dict]))
                continue

            # instanciate GuiDevice
            nickname = self._checkDevNickname(nickname, gui_instr)
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
        auto_load = instr_dict.get('auto_load', False)
        if auto_load:
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
        # try to load gui_devices of gui_instr that are not loaded yet
        for gui_dev in gui_instr.gui_devices:
            if gui_dev.isLoaded(): continue
            try:
                ph_dev = self.model.getDevice(gui_instr.ph_instr, gui_dev.ph_name)
                gui_dev.ph_dev = ph_dev
                # type
                detected_type = self.model.devType(ph_dev)
                type = [detected_type[0] if gui_dev.type[0] is None else gui_dev.type[0],
                        detected_type[1] if gui_dev.type[1] is None else gui_dev.type[1]]
                gui_dev.type = tuple(type)
                gui_dev.ph_choice = self.model.getChoices(ph_dev)
            except Exception as e:
                tb_str = "".join(traceback.format_tb(e.__traceback__))
                self.pop.devLoadError(e, tb_str)
                continue


            # logical device
            self.loadGuiLogicalDevice(gui_dev)

        self.view_rack.gui_updateGuiInstrument(gui_instr)
            
    def setGuiDevExtraArgs(self, gui_dev, extra_args_str):
        # extra_args_str will be eval in a dict, so it must be like:
        # "ch=1, vals='r'"
        # try to eval extra_args_str and set if succeed
        try:
            extra_args_dict = eval(f"dict({extra_args_str})")
            gui_dev.extra_args = extra_args_dict
        except Exception as e:
            tb_str = "".join(traceback.format_tb(e.__traceback__))
            self.pop.devExtraArgsEvalFail(e, tb_str)

    def loadGuiLogicalDevice(self, gui_dev):
        # try to build the logical device based on logical_kwargs
        ramp_rate = gui_dev.logical_kwargs['ramp'].get('rate', -1)
        if ramp_rate == 0:
            self.pop.devRampZero()
            return
        scale_factor = gui_dev.logical_kwargs['scale'].get('factor', -1)
        if scale_factor == 0:
            self.pop.devScaleZero()
            return
        try:
            gui_dev.logical_dev = self.model.makeLogicalDevice(gui_dev,
                                                               gui_dev.logical_kwargs,
                                                               gui_dev.parent.ph_instr)
        except Exception as e:
            tb_str = "".join(traceback.format_tb(e.__traceback__))
            self.pop.devLoadLogicalError(e, tb_str)
            return
        self.view_rack.gui_updateGuiInstrument(gui_dev.parent)
        self.view_rack.win_devconfig.close()
    
    def newDevicesFromRack(self, gui_instr, dev_dicts):
        # dev_dicts is a list of dict: [{ph_name:'dev1', ph_name:'dev2'...}]
        self._instanciateGuiDevices(gui_instr, dict(devices=dev_dicts))
        self.loadGuiDevices(gui_instr)
        self.view_rack.gui_updateGuiInstrument(gui_instr)

    def removeGuiInstrument(self, gui_instr):
        if self.pop.askRemoveInstrument(gui_instr.nickname) == False:
            return
        # remove its devices in the trees:
        for dev in gui_instr.gui_devices:
            self.view_main.gui_removeDevice(dev)
            self.view_monitor.gui_removeDevice(dev)
        self.gui_instruments.remove(gui_instr)
        self.view_rack.gui_removeGuiInstrument(gui_instr)
        if gui_instr.ph_instr is not None:
            del gui_instr.ph_instr
        del gui_instr

    def getValue(self, gui_dev):
        # get the value of the GuiDevice and update the gui
        # To be able to get even when the device is rapming,
        #   we get the basedevice and apply the factor after.
        try:
            dev = gui_dev.getPhDev(basedev=True)
            if dev is None: return
            value = self.model.getValue(dev)
        except Exception as e:
            tb_str = "".join(traceback.format_tb(e.__traceback__))
            self.pop.getValueError(e, tb_str)
            return

        # because logical_dev is innacessible when ramping:
        factor = gui_dev.logical_kwargs['scale'].get('factor', 1)
        if isinstance(value, (int, float)):
            value = value / factor

        gui_dev.cache_value = value
        self.view_rack.gui_updateDeviceValue(gui_dev, value)
        self.view_monitor.gui_updateDeviceValue(gui_dev, value)
        return value

    def setValue(self, gui_dev, val):
        # set the value of the GuiDevice and update the gui
        self.model.setValue(gui_dev, val)
        self.view_rack.win_set.close()
    
    def setValueError(self, e):
        tb_str = "".join(traceback.format_tb(e.__traceback__))
        self.pop.setValueError(e, tb_str)

    def renameDevice(self, gui_dev, new_nickname):
        gui_dev.nickname = new_nickname
        self.view_main.gui_renameDevice(gui_dev)
        self.view_rack.gui_renameDevice(gui_dev)
        self.view_monitor.gui_renameDevice(gui_dev)

    # -- SWEEP TREES --

    def addSweepDev(self, gui_dev, row):
        # add a device to the sweep tree, launch the config window
        if not gui_dev.isLoaded() and self.pop.devNotLoaded() == False:
            return
        # if the device is not gettable, ask if we want to add it anyway
        if gui_dev.type[0] == False and self.pop.notSettable() == False:
            return
        self.view_main.gui_addSweepGuiDev(gui_dev, row)
        self.showSweepConfig(gui_dev)

    def addOutputDev(self, gui_dev, row):
        # add a device to the output tree
        if not gui_dev.isLoaded() and self.pop.devNotLoaded() == False:
            return
        if gui_dev.type[1] == False and self.pop.notGettable() == False:
            return
        self.view_main.gui_addOutItem(gui_dev, row)

    def addLogDev(self, gui_dev, row):
        # add a device to the log tree
        if not gui_dev.isLoaded() and self.pop.devNotLoaded() == False:
            return
        self.view_main.gui_addLogItem(gui_dev, row)

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

    create_app = False
    app = None
    if len(sys.argv) > 1 and sys.argv[1] == "--with-app":
        create_app = True
        QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
        QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)
        app = QApplication([])
        app.setApplicationDisplayName("HegelLab")

        class Logger():
            def __init__(self, filename):
                self.log = open(filename, "a")
            def write(self, message):
                self.log.write(message)
            def flush(self):
                pass
        sys.stdout = Logger("logs/stdout.txt")
        sys.stderr = Logger("logs/stderr.txt")
    
    pixmap = QPixmap("./resources/favicon/favicon.png")
    pixmap = pixmap.scaled(256, 256)
    splash = QSplashScreen(pixmap)
    splash.showMessage(
        "Loading HegelLab...",
        alignment=QtCore.Qt.AlignBottom | QtCore.Qt.AlignHCenter,
        color=QtCore.Qt.white,
    )

    splash.show()

    hl = HegelLab(app)
    splash.finish(hl.view_main)

    hl.showMain()
    
    if create_app:
        sys.exit(app.exec())