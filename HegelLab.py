import sys
from IPython import get_ipython

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QObject, pyqtSignal

from windows import MainWindow, RackWindow, DisplayWindow, MonitorWindow
from widgets import WindowWidget, TreeWidget
from src import LoaderSaver, Model, Popup, SweepThread#, Shortcuts
from src.GuiInstrument import GuiInstrument, GuiDevice
from src.SweepIdxIter import IdxIter

from src import Drivers # for eval

import numpy as np
import time
import os


# HegelLab is made to support any instrument with minimal effort.
# It should be enough to add the instrument class to the json file.

# naming rules (not always respected but yeah):
# _method : is a method called only from within its class
# sig_name : a pyqt signal
# gui_method : a method connected to a signal comming from another class ("gui-wide" signals)


class HegelLab(QObject):
    def __init__(self, app):
        super().__init__()

        self.app = app


        self.loader = LoaderSaver.LoaderSaver(self)
        self.pop = Popup.Popup()
        self.model = Model.Model(self)
        self.view_main = main = MainWindow.MainWindow(self)
        self.view_rack = rack = RackWindow.RackWindow(self)
        self.view_display = disp = DisplayWindow.DisplayWindow(self)
        self.view_monitor = moni = MonitorWindow.MonitorWindow(self)

        # shortcut:
        TreeWidget.TreeWidget.lab = self
        WindowWidget.Window.initShortcutsAll(self)

        # default instrument list
        self.default_instr_list = self.loader.importFromJSON('default_instruments.json')
        self.gui_instruments = []  # list of loaded GuiInstrument
        self.sweep_file_path = ''

        # signals -->
        self.sig_instrumentAdded.connect(rack.gui_onInstrumentAdded)
        self.sig_instrumentLoadFinished.connect(rack.gui_updateGuiInstrument)
        self.sig_deviceLoadFinished.connect(rack.gui_updateGuiDevice)
        self.sig_newDevicesAdded.connect(rack.gui_onNewDevicesAdded)
        self.sig_onInstrumentRemoved.connect(rack.gui_onInstrumentRemoved)
        self.sig_deviceRemoved.connect(rack.gui_onDeviceRemoved)
        self.sig_deviceRemoved.connect(main.gui_onDeviceRemoved)
        self.sig_deviceRemoved.connect(moni.gui_onDeviceRemoved)
        self.sig_valueGet.connect(rack.gui_onValueGet)
        self.sig_valueSet.connect(rack.gui_onValueSet)
        self.sig_deviceRenamed.connect(rack.gui_onDeviceRenamed)
        self.sig_deviceRenamed.connect(main.gui_onDeviceRenamed)
        self.sig_deviceRenamed.connect(moni.gui_onDeviceRenamed)

        self.sig_sweepDeviceSet.connect(main.gui_updateSweepDevice)
        self.sig_outDeviceSet.connect(main.gui_updateOutDevice)
        self.sig_logDeviceSet.connect(main.gui_updateLogDevice)
        self.sig_monitorDeviceSet.connect(moni.gui_updateMonitorDevice)
        self.sig_sweepDeviceSet.connect(lambda gui_dev: rack.gui_updateGuiDevice(gui_dev))
        self.sig_outDeviceSet.connect(lambda gui_dev: rack.gui_updateGuiDevice(gui_dev))
        self.sig_logDeviceSet.connect(lambda gui_dev: rack.gui_updateGuiDevice(gui_dev))
        self.sig_monitorDeviceSet.connect(lambda gui_dev: rack.gui_updateGuiDevice(gui_dev))

        # signals <--
        self.sig_instrumentLoadFinished.connect(self.onLoadInstrumentFinished)
        self.sig_setValueFinished.connect(self.onSetValueFinished)
    

        # sweep related
        self.loop_control = self.model.initLoopControl()
        self.sweep_thread = SweepThread.SweepThread(self.loop_control, self.sig_sweepProgress, self.sig_sweepError, self.sig_sweepFinished)

        self.sig_sweepStarted.connect(lambda: main.gui_onSweepStarted())
        self.sig_sweepStarted.connect(disp.gui_onSweepStarted)
        self.sig_sweepProgress.connect(main.gui_onSweepProgress)
        self.sig_sweepProgress.connect(disp.gui_onSweepProgress)
        self.sig_sweepPaused.connect(main.gui_onSweepPaused)
        self.sig_sweepResumed.connect(main.gui_onSweepResumed)

        self.sig_sweepError.connect(self.pop.sweepThreadError)
        self.sig_sweepFinished.connect(main.gui_onSweepFinished)
        

    # -- GENERAL --

    def showMain(self):
        self.view_main.focus()

    def showRack(self):
        self.view_rack.focus()

    def showDisplay(self, dual=None):
        self.view_display.focus(dual)

    def showMonitor(self):
        self.view_monitor.focus()

    def askClose(self, event):
        if self.pop.askQuit():
            self.abortSweep()
            self.sweep_thread.terminate()
            #self.model.close()
            WindowWidget.Window.killAll()
        else:
            event.ignore()
    
    def getGuiInstrument(self, instr_nickname):
        # search and return the instance of gui_instr
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
        # build GuiInstrument but leave ph_instr empty
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
        added = []
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
            type_dict = dev_dict.get('type', dict(set=None, get=None, output="None"))
            is_set = type_dict.get('set', None)
            is_get = type_dict.get('get', None)
            output_type = type_dict.get('output', None)
            try: output_type = eval(output_type)
            except: output_type = None
            gui_dev.type = [is_set, is_get, output_type]
            # limit, scale, ramp
            scale_kw = dict(dev_dict.get('scale', {}))
            gui_dev.logical_kwargs['scale'] = scale_kw

            ramp_kw = dict(dev_dict.get('ramp', {}))
            gui_dev.logical_kwargs['ramp'] = ramp_kw

            limit_kw = dict(dev_dict.get('limit', {}))
            gui_dev.logical_kwargs['limit'] = limit_kw

            gui_instr.gui_devices.append(gui_dev)
            added.append(gui_dev)
        return added

    sig_instrumentAdded = pyqtSignal(GuiInstrument)
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
        
        self.sig_instrumentAdded.emit(gui_instr)

    sig_instrumentLoadFinished = pyqtSignal(GuiInstrument, object)
    def loadGuiInstrument(self, gui_instr):
        # ask driver for loading a GuiInstrument 
        # the driver must set the gui_instr.ph_instr attribute
        # on success(fail), the driver must emit sig_success(sig_error) 
        # it also emit the signals without exception=None if success
        eval(gui_instr.driver).load(self, gui_instr, self.sig_instrumentLoadFinished)
    
    def onLoadInstrumentFinished(self, gui_instr, exception):
        # connected to sig_instrumentLoadFinished
        if exception:
            self.pop.instrLoadError(exception)
        else:
            # try load all devices
            for gui_dev in gui_instr.gui_devices:
                self.loadGuiDevice(gui_dev)
    
    sig_deviceLoadFinished = pyqtSignal(GuiDevice)
    def loadGuiDevice(self, gui_dev):
        # try to load basedev of gui_device (assuming gui_dev.parent.ph_instr is not None)
        try:
            ph_dev = self.model.getDevice(gui_dev.parent.ph_instr, gui_dev.ph_name)
            gui_dev.ph_dev = ph_dev
            # type
            set, get, output = self.model.getType(ph_dev)
            gui_dev.type = [set if gui_dev.type[0] is None else gui_dev.type[0],
                            get if gui_dev.type[1] is None else gui_dev.type[1],
                            output if gui_dev.type[2] is None else gui_dev.type[2]]
            gui_dev.multi = self.model.getFormatMulti(ph_dev)
            gui_dev.ph_choice = self.model.getChoices(ph_dev)
        except Exception as e:
            self.pop.devLoadError(e)
            self.sig_deviceLoadFinished.emit(gui_dev)
            return
        try:
            gui_dev.logical_dev = self.model.makeLogicalDevice(gui_dev,
                                                               gui_dev.logical_kwargs,
                                                               gui_dev.parent.ph_instr)
        except Exception as e:
            self.pop.devLoadLogicalError(e)
        self.sig_deviceLoadFinished.emit(gui_dev)
            
    sig_newDevicesAdded = pyqtSignal(GuiInstrument, list)
    def newDevicesFromRack(self, gui_instr, dev_dicts):
        # called when a new device is added to an instr
        # dev_dicts is a list of dict: [{ph_name:'dev1', ph_name:'dev2'...}]
        gui_dev_added = self._instanciateGuiDevices(gui_instr, dict(devices=dev_dicts))
        # signal new devices have come
        self.sig_newDevicesAdded.emit(gui_instr, gui_dev_added)
        # then load them
        [self.loadGuiDevice(gui_dev) for gui_dev in gui_dev_added]

    sig_onInstrumentRemoved = pyqtSignal(GuiInstrument)
    def removeGuiInstrument(self, gui_instr):
        if not self.pop.askRemoveInstrument(gui_instr.nickname): return

        for gui_dev in gui_instr.gui_devices:
            self.removeGuiDevice(gui_dev, ask_first=False)

        self.gui_instruments.remove(gui_instr)
        # TODO: properly delete pyhegel instrument
        if gui_instr.ph_instr is not None:
            del gui_instr.ph_instr
        self.sig_onInstrumentRemoved.emit(gui_instr)
        del gui_instr
    
    sig_deviceRemoved = pyqtSignal(GuiDevice)
    def removeGuiDevice(self, gui_dev, ask_first=True):
        if ask_first and not self.pop.askRemoveDevice(gui_dev.nickname): return

        gui_instr = gui_dev.parent
        gui_instr.gui_devices.remove(gui_dev)
        self.sig_deviceRemoved.emit(gui_dev)

    sig_valueGet = pyqtSignal(GuiDevice)
    def getValue(self, gui_dev):
        # get the value of the GuiDevice and update the gui
        # To be able to get even when the device is rapming,
        #   we get the basedevice and apply the factor after.
        try:
            dev = gui_dev.getPhDev(basedev=True)
            if dev is None: return
            value = self.model.getValue(dev)
        except Exception as e:
            self.pop.getValueError(e)
            return

        # because logical_dev is innacessible when ramping:
        factor = gui_dev.logical_kwargs['scale'].get('factor', 1.)
        if isinstance(value, (int, float)):
            value = value / factor

        gui_dev.cache_value = value
        self.sig_valueGet.emit(gui_dev)
        return value

    sig_setValueFinished = pyqtSignal(GuiDevice, object)
    def setValue(self, gui_dev, val):
        self.model.setValue(gui_dev, val)
    
    sig_valueSet = pyqtSignal(GuiDevice)
    def onSetValueFinished(self, gui_dev, exception):
        if exception:
            self.pop.setValueError(exception)
        else:
            self.sig_valueSet.emit(gui_dev)

    sig_deviceRenamed = pyqtSignal(GuiDevice)
    def renameDevice(self, gui_dev, new_nickname):
        gui_dev.nickname = new_nickname
        self.sig_deviceRenamed.emit(gui_dev)
        #self.view_main.gui_renameDevice(gui_dev)
        #self.view_rack.gui_renameDevice(gui_dev)
        #self.view_monitor.gui_renameDevice(gui_dev)

    # -- SWEEP TREES --
    # sig emitted when add/remove is finished
    sig_sweepDeviceSet = pyqtSignal(GuiDevice, bool) # True: device has been set. False: device has been removed
    sig_outDeviceSet = pyqtSignal(GuiDevice, bool)
    sig_logDeviceSet = pyqtSignal(GuiDevice, bool)
    sig_monitorDeviceSet = pyqtSignal(GuiDevice, bool)

    def setSweepDevice(self, gui_dev, boo=True):
        # bool: True for add, False for remove
        if not boo: pass
        elif not gui_dev.isLoaded() and not self.pop.devNotLoaded(): return
        elif not gui_dev.type[0] and not self.pop.notSettable(): return
        elif gui_dev.type[2] is bool and not self.pop.sweepABool(): return
        else: # launch the sweep config window for gui_dev
            driver_cls = eval(gui_dev.parent.driver)
            driver_cls.sweep(self, gui_dev, self.sig_sweepDeviceSet)
        gui_dev.status['sweep'] = boo
        self.sig_sweepDeviceSet.emit(gui_dev, boo)

    def setOutDevice(self, gui_dev, boo=True):
        # bool: True for add, False for remove
        if not boo: pass
        elif not gui_dev.isLoaded() and not self.pop.devNotLoaded(): return
        elif not gui_dev.type[1] and not self.pop.notGettable(): return
        gui_dev.status['out'] = boo
        self.sig_outDeviceSet.emit(gui_dev, boo)

    def setLogDevice(self, gui_dev, boo=True):
        # bool: True for add, False for remove
        if not boo: pass
        elif not gui_dev.isLoaded() and not self.pop.devNotLoaded(): return
        elif not gui_dev.type[1] and not self.pop.notGettable(): return
        gui_dev.status['log'] = boo
        self.sig_logDeviceSet.emit(gui_dev, boo)

    def setMonitorDevice(self, gui_dev, boo=True):
        # bool: True for add, False for remove
        if not boo: pass
        elif not gui_dev.isLoaded() and not self.pop.devNotLoaded(): return
        elif not gui_dev.type[1] and not self.pop.notGettable(): return
        gui_dev.status['monitor'] = boo
        self.sig_monitorDeviceSet.emit(gui_dev, boo)

    
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
        folder_path = self.view_main.folder_path
        date = time.strftime("%Y%m%d")
        folder_path += date
        if not os.path.exists(folder_path): os.mkdir(folder_path)

        filename = self.view_main.filename_edit.text()
        if filename == "": filename = "sweep"
        return folder_path + "/%t_" + filename + ".txt"

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
        if ph_out_devs == [] and not self.pop.sweepNoOutputDevice():
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
        # and an "custom iterator".

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

    sig_sweepStarted = pyqtSignal(SweepThread.SweepStatus)
    sig_sweepPaused = pyqtSignal()
    sig_sweepResumed = pyqtSignal()
    sig_sweepProgress = pyqtSignal(SweepThread.SweepStatus)
    sig_sweepError = pyqtSignal(Exception)
    sig_sweepFinished = pyqtSignal()
    def startSweep(self, gui_sw_devs, gui_out_devs, gui_log_devs):
        # Prepare everything and start the thread.

        # generate lists and allocate data
        ph_sw_devs, start, stop, npts, ph_out_devs, ph_log_devs = self._genLists(gui_sw_devs, gui_out_devs, gui_log_devs)
        alternate = {True: "alternate", False: False}[self.view_main.cb_alternate.isChecked()]
        self._allocData(gui_out_devs, start, stop, npts, alternate)

        # check for errors
        if self._startSweepCheckError(start, stop, npts, ph_sw_devs, ph_out_devs):
            self.sig_sweepFinished.emit()
            return

        # prepare kw
        sweep_kwargs = {
            "dev": ph_sw_devs, "start": start, "stop": stop, "npts": npts, "out": ph_out_devs,
            "filename": self._prepareFilename(),
            "extra_conf": [self.view_main.te_comment.toPlainText()] + ph_log_devs,
            "beforewait": self.view_main.sb_before_wait.value(),
            "updown": alternate,
        }

        # run sweep thread
        self.sweep_thread.initSweepKwargs(sweep_kwargs)
        self.sweep_thread.initSweepStatus(gui_sw_devs, gui_out_devs, time.time())
        self.sweep_thread.raz_sw_devs = lambda: [self.setValue(gui_dev, 0) for gui_dev in gui_sw_devs if gui_dev.raz]
        for out in gui_out_devs:
            out.alternate = self.view_main.cb_alternate.isChecked()
        self.sweep_thread.start()

        # update gui
        self.sig_sweepStarted.emit(self.sweep_thread.status)
        #self.showDisplay()

    def pauseSweep(self):
        # called by the main window
        self.loop_control.pause_enabled = True
        self.sig_sweepPaused.emit()

    def resumeSweep(self):
        # called by the main window
        self.loop_control.pause_enabled = False
        self.sig_sweepResumed.emit()

    def abortSweep(self):
        # called by the main window
        self.loop_control.abort_enabled = True
        self.loop_control.pause_enabled = False
        self.sig_sweepFinished.emit()

if __name__ == "__main__":
    from PyQt5.QtWidgets import QSplashScreen
    from PyQt5.QtGui import QPixmap
    from PyQt5 import QtCore

    print(get_ipython())

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
    splash.showMessage("Loading HegelLab...", alignment=QtCore.Qt.AlignBottom | QtCore.Qt.AlignHCenter, color=QtCore.Qt.white)
    splash.show()

    hl = HegelLab(app)
    splash.finish(hl.view_main)
    hl.showMain()
    
    if create_app:
        sys.exit(app.exec())
