import sys, traceback

from PyQt5.QtWidgets import QApplication

from views import Main, Rack, Display
from src import LoaderSaver, Model, Popup, SweepThread, Drivers
from src.GuiInstrument import GuiInstrument, GuiDevice
from src.SweepIdxIter import IdxIter

import numpy as np
import time
import os


# HegelLab is made to support any instrument with minimal effort.
# It should be enough to add the instrument class to the dictionary below.
# TODO: use json file
from pyHegel import instruments
supported_instruments = {
    "dummy": {
        "pyhegel_class": instruments.dummy,
        "has_address": False,
        "has_slots": False,
        "has_channels": False,
        "has_custom_driver": False,
        "devices_name": ["rand", "volt", "current"]
    },
    "zurich": {
        "pyhegel_class": instruments.zurich_UHF,
        "has_address": True, "address": 'TCPIP::localhost::',
        "has_slots": False,
        "has_channels": False,
        "has_custom_driver": False,
        "devices_name": []
    },
    "be214x": {
        "pyhegel_class": instruments.iTest_be214x,
        "has_address": True, "address":"TCPIP::192.168.150.145::5025::SOCKET",
        "has_slots": True, "slots": [1, 2, 3, 4], # 4 instruments in one
        "has_channels": True, "channels": [1, 2, 3, 4], # 4 channel per instr
        "channel_key": "ch",
        "has_custom_driver": False,
        "devices_name": ["output_en", "range", "slope", "ramp", "level", "meas_out_volt", "meas_out_current"]
    },
    "dmm344xxA": {
        "pyhegel_class": instruments.agilent_multi_34410A,
        "has_address": True, "address":'USB0::0x2A8D::0x0101::MY57515472',
        "has_slots": False,
        "has_channels": False,
        "has_custom_driver": False,
        "devices_name": ["mode", "autorange", "sample_count", "nplc", "readval"]
    },
    "ami430": {
        "pyhegel_class": instruments.AmericanMagnetics_vector,
        "has_address": True, "address":'TCPIP::{ip_name}-AX.local::7180::socket',
        "has_slots": False,
        "has_channels": False,
        "has_custom_driver": True, "driver": Drivers.ami430,
        "devices_name": []
    },
        
}

supported_devices = {
    "limit": {
        "name": "Limit device", "key": "limit",
        "pyhegel_class": instruments.LimitDevice,
        "arg_kw": ["min", "max"],
        "arg_labels": ["Min: ", "Max: "],
        "arg_defaults": [0, 1],
    },
    "scaling": {
        "name": "Scaling device", "key": "scaling",
        "pyhegel_class": instruments.ScalingDevice,
        "arg_kw": ["scale_factor", "offset"],
        "arg_labels": ["Scale factor: ", "Offset: "],
        "arg_defaults": [1, 0],
    },
    "ramp": {
        "name": "Ramp device", "key": "ramp",
        "pyhegel_class": instruments.RampDevice,
        "arg_kw": ["rate", 'internal_dt'],
        "arg_labels": ["Rate (unit/s): ", 'Internale dt (s): '],
        "arg_defaults": [1, 0.1],
    },
    # "Average device": if needed, one day
}

class HegelLab():

    def __init__(self):
        # app
        self.loader = LoaderSaver.LoaderSaver(self)
        self.pop = Popup.Popup()
        # model, views
        self.model = Model.Model()
        self.view_main = Main.Main(self)
        self.view_rack = Rack.Rack(self)
        self.view_display = Display.Display(self)
        
        # data
        self.supported_instruments = supported_instruments
        self.supported_devices = supported_devices
        self.gui_instruments = {} # {nickname: GuiInstrument}

        # sweep related
        self.loop_control = self.model.initLoopControl()
        self.sweep_thread = SweepThread.SweepThread(self.model.startSweep, self.loop_control)
        self.sweep_thread.progress_signal.connect(self.onSweepSignalProgress)
        self.sweep_thread.error_signal.connect(self.onSweepSignalError)
        self.sweep_thread.finished_signal.connect(self.onSweepSignalFinished)

        # show main window
        self.showMain()
        
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
    
    def close(self):
        # close all the windows
        if self.pop.askQuit() == True:
            self.view_display.close()
            self.view_rack.close()
            self.view_display.close()
            return True
        return False
        
    def showInstrumentConfig(self, gui_instr):
        # launch the config window for the selected instrument
        #self.view_rack.setEnabled(False)
        #self.view_rack.window_configInstrument(gui_instr)
        print(gui_instr.nickname)

    def showDeviceConfig(self, gui_dev):
        # launch the config window for the selected device
        #self.view_rack.setEnabled(False)
        #self.view_rack.window_configDevice(gui_dev)
        print(gui_dev.nickname)


    # -- RACK --

    def checkInstrNickname(self, name):
        # check if the loading name is already used
        i, base = 1, name
        while name in self.gui_instruments.keys():
            name = base + ' ({})'.format(i)
            i += 1
        return name
    
    def checkDevNickname(self, name, gui_instr):
        # check if the loading name is already used
        i, base = 1, name
        while name in gui_instr.gui_devices.keys():
            name = base + ' ({})'.format(i)
            i += 1
        return name

    def loadGuiInstrument(self, gui_instr):
        # load a GuiInstrument:
        # - make sure the nickname is unique
        gui_instr.nickname = self.checkInstrNickname(gui_instr.nickname)
        # - try load the pyHegel instrument
        try:
            # -- if no loading gui
            kwargs = {}
            if gui_instr.slot is not None:
                kwargs['slot'] = gui_instr.slot
            gui_instr.ph_instr = gui_instr.instr_driver.load(gui_instr.nickname,
                                                 gui_instr.instr_cls,
                                                 gui_instr.address,
                                                 **kwargs)
        except Exception as e:
            tb_str = ''.join(traceback.format_tb(e.__traceback__))
            self.pop.instrLoadError(e, tb_str)
        # - try load the pyHegel devices
        if gui_instr.ph_instr is not None:
            self.loadGuiDevices(gui_instr)
        # - add it to the lab
        self.gui_instruments[gui_instr.nickname] = gui_instr
        self.view_rack.gui_addGuiInstrument(gui_instr)
        self.view_rack.win_add.close()
    
    def loadGuiDevices(self, gui_instr):
        for gui_dev in gui_instr.gui_devices.values():
            #gui_dev.nickname = self.checkDevLoadingName(gui_dev.nickname, gui_instr)
            try:
                gui_dev.ph_dev = self.model.getDevice(gui_instr.ph_instr, gui_dev.dev_name)
                gui_dev.type = self.model.devType(gui_dev.ph_dev)
                gui_dev.ph_choice = self.model.getChoices(gui_dev.ph_dev)
            except Exception as e:
                tb_str = ''.join(traceback.format_tb(e.__traceback__))
                self.pop.devLoadError(e, tb_str)


    def buildGuiInstrument(self, nickname, instr_name, addr, slot=None):
        # call only by the Rack. Loading is done in loadGuiInstrument.
        # build GuiInstrument and populate dvices, but no ph_instr nor ph_dev
        settings = supported_instruments[instr_name]
        instr_cls = settings['pyhegel_class']
        instr_driver = settings['driver'] if settings['has_custom_driver'] else Drivers.Default
        gui_instr = GuiInstrument(nickname, instr_name, instr_cls, instr_driver, addr, slot)
        print(addr)
        for dev_name in settings['devices_name']:
            if settings['has_channels']:
                for ch in settings['channels']:
                    auto_nickname = dev_name + '_' + str(ch)
                    gui_dev = GuiDevice(auto_nickname, dev_name, gui_instr)
                    gui_dev.ph_dict = dict(ch=ch)
                    gui_instr.gui_devices[auto_nickname] = gui_dev
            else:
                gui_dev = GuiDevice(dev_name, dev_name, gui_instr)
                gui_instr.gui_devices[dev_name] = gui_dev
        self.loadGuiInstrument(gui_instr)

    def removeGuiInstrument(self, gui_instr):
        if self.pop.askRemoveInstrument(gui_instr.nickname) == False:
            return
        # remove its devices in the trees:
        for dev in gui_instr.gui_devices.values():
            self.view_main.gui_removeDevice(dev)
        self.view_rack.gui_removeGuiInstrument(gui_instr)
        for dev in gui_instr.gui_devices.values():
            self.view_main.gui_removeDevice(dev)
        del self.gui_instruments[gui_instr.nickname]
    
    def removeGuiDevice(self, gui_dev):
        if len(gui_dev.needed_by) > 0:
            self.pop.devIsNeeded(); return
        if self.pop.askRemoveDevice(gui_dev.getDisplayName('long')) == False:
            return
        # update dependencies
        for needed_gui_dev in gui_dev.needs:
            needed_gui_dev.needed_by.remove(gui_dev)
            needed_gui_dev.hide = False
        gui_instr = gui_dev.parent
        gui_instr.gui_devices.pop(gui_dev.nickname)
        self.view_rack.gui_updateGuiInstrument(gui_instr)
        self.view_main.gui_removeDevice(gui_dev)
        del gui_dev
            
    def getValue(self, gui_dev):
        # get the value of the GuiDevice and update the gui
        value = self.model.getValue(gui_dev.getPhDev())
        gui_dev.cache_value = value
        self.view_rack.gui_updateDeviceValue(gui_dev, value)
    
    def setValue(self, gui_dev, val):
        # set the value of the GuiDevice and update the gui
        try:
            self.model.setValue(gui_dev.getPhDev(), val)
        except Exception as e:
            tb_str = ''.join(traceback.format_tb(e.__traceback__))
            self.pop.setValueError(e, tb_str)
            return
        self.view_rack.gui_updateDeviceValue(gui_dev, val)
        self.view_rack.win_set.close()
    
    def createWrapDevice(self,
                         base_gui_dev,
                         dev_type,
                         ph_kwargs,
                         gui_dev_nickname,
                         base_hide):

        ph_class = self.supported_devices[dev_type]['pyhegel_class']
        dev_name = ph_class.__name__ + '_' \
                   + base_gui_dev.dev_name
        if base_gui_dev.ph_dict is not None:
            dev_name += '_' + str(base_gui_dev.ph_dict.get('ch',''))
        try:
            new_ph_dev = self.model.makeDevice(
                                            base_gui_dev.getPhDev(),
                                            dev_name,
                                            ph_class,
                                            ph_kwargs,
                                            base_gui_dev.parent.ph_instr)
        except Exception as e:
            tb_str = ''.join(traceback.format_tb(e.__traceback__))
            self.pop.devLoadError(e, tb_str)
            return

        base_gui_dev.hide = base_hide
        # create the host GuiDevice
        gui_instr = base_gui_dev.parent
        nickname = self.checkDevNickname(gui_dev_nickname, gui_instr)
        gui_dev = GuiDevice(nickname, dev_name, gui_instr)

        gui_dev.ph_dev = new_ph_dev
        gui_dev.type = base_gui_dev.type
        gui_dev.needs.append(base_gui_dev)
        gui_dev.extra_type = dev_type
        gui_dev.extra_args = ph_kwargs

        gui_instr.gui_devices[nickname] = gui_dev
        base_gui_dev.needed_by.append(gui_dev)

        # view
        self.view_rack.gui_updateGuiInstrument(gui_instr)

    def renameDevice(self, gui_dev, new_nickname):
        gui_dev = gui_dev.parent.gui_devices.pop(gui_dev.nickname) # remove first
        new_nickname = self.checkDevNickname(new_nickname, gui_dev.parent)
        gui_dev.parent.gui_devices[new_nickname] = gui_dev
        gui_dev.nickname = new_nickname
        self.view_main.gui_renameDevice(gui_dev)
        self.view_rack.gui_renameDevice(gui_dev)

    # -- SWEEP TREES --

    def addSweepDev(self, instr_nickname, dev_nickname):
        # add a device to the sweep tree, launch the config window
        gui_dev = self.gui_instruments[instr_nickname].gui_devices[dev_nickname]
        if gui_dev.type[0] == False and self.pop.notSettable() == False:
            # if the device is not gettable, ask if we want to add it anyway
            return
        if self.view_main.tree_sw.findItemByData(gui_dev) != None:
            self.pop.devAlreadyHere(); return
        self.view_main.gui_addSweepGuiDev(gui_dev)
        self.showSweepConfig(gui_dev)

    def addOutputDev(self, instr_nickname, dev_nickname):
        # add a device to the output tree
        gui_dev = self.gui_instruments[instr_nickname].gui_devices[dev_nickname]
        if gui_dev.type[1] == False and self.pop.notGettable() == False:
            return
        if self.view_main.tree_out.findItemByData(gui_dev) != None:
            self.pop.devAlreadyHere(); return
        self.view_main.gui_addOutItem(gui_dev)
    
    def addLogDev(self, instr_nickname, dev_nickname):
        # add a device to the log tree
        gui_dev = self.gui_instruments[instr_nickname].gui_devices[dev_nickname]
        if self.view_main.tree_log.findItemByData(gui_dev) != None:
            self.pop.devAlreadyHere(); return
        self.view_main.gui_addLogItem(gui_dev)
    
    def showSweepConfig(self, gui_dev):
        # launch the config window for gui_dev sweep device
        driver_cls = gui_dev.parent.instr_driver
        driver_cls.sweep(self, gui_dev)
    
    def setSweepValues(self, gui_dev, start, stop, npts):
        # set sweep values for gui_dev and update the gui
        gui_dev.sweep = [start, stop, npts]
        self.view_main.gui_updateSweepValues(gui_dev)
    

    # -- SWEEP THREAD --

    def _prepareFilename(self):
        filename = self.view_main.filename_edit.text()
        if filename == '':
            filename = 'sweep'
        date = time.strftime("%Y%m%d")
        dir_path = './temp/' + date
        if not os.path.exists(dir_path):
            os.mkdir(dir_path)
        filename = dir_path + '/%t_' + filename + '.txt'
        return filename

    def _startSweepCheckError(self, start, stop, npts, ph_sw_devs, ph_out_devs):
        if None in start or None in stop or None in npts:
            self.pop.sweepMissingDevParameter(); return True
        if ph_sw_devs == []:
            self.pop.sweepNoDevice(); return True
        if 0 in npts:
            self.pop.sweepZeroPoints(); return True
        for start, stop in zip(start, stop):
            if start == stop:
                self.pop.sweepStartStopEqual(); return True
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

        reverse = [False]*len(start)
        for i, (sta, sto) in enumerate(zip(start, stop)):
            if sta > sto: reverse[i] = True

        if len(npts)==1:
            npts = npts + [1] # not .append to preserve npts
        if len(npts)==2:
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
        ph_sw_devs, start, stop, npts, ph_out_devs, ph_log_devs = \
            self._genLists(gui_sw_devs, gui_out_devs, gui_log_devs)
        alternate = {True:'alternate', False:False}[self.view_main.cb_alternate.isChecked()]
        self._allocData(gui_out_devs, start, stop, npts, alternate)
        
        # errors
        if self._startSweepCheckError(start, stop, npts, ph_sw_devs, ph_out_devs):
            return

        # prepare kw
        sweep_kwargs = {
            'dev': ph_sw_devs, 'start': start, 'stop': stop,
            'npts': npts, 'out': ph_out_devs,
            'filename': self._prepareFilename(),
            'extra_conf': [self.view_main.te_comment.toPlainText()] + ph_log_devs,
            'beforewait': self.view_main.sb_before_wait.value(),
            'updown': alternate,
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
        self.loop_control.pause_enabled = False # in case of Pause->Abort



if __name__ == "__main__":
    
    # splash screen
    from PyQt5.QtWidgets import QSplashScreen
    from PyQt5.QtGui import QPixmap
    from PyQt5 import QtCore
    pixmap = QPixmap("./resources/favicon/favicon.png")
    pixmap = pixmap.scaled(256, 256)
    splash = QSplashScreen(pixmap)
    splash.showMessage('Loading HegelLab...',
                       alignment=QtCore.Qt.AlignBottom | QtCore.Qt.AlignHCenter,
                       color=QtCore.Qt.white)
    splash.show()
    hl = HegelLab()
    splash.finish(hl.view_main)
