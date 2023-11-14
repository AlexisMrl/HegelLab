import sys, traceback

from PyQt5.QtWidgets import QApplication

from views import Main, Rack, Display
from src import LoaderSaver, Model, Popup, SweepThread
from src.GuiInstrument import GuiInstrument, GuiDevice

import numpy as np
import time


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
        "has_sweep_gui": False,
        "has_config_gui": False,
        "devices_name": ["rand", "volt", "current"]
    },
    "zurich": {
        "pyhegel_class": instruments.zurich_UHF,
        "has_address": True, "address": 'TCPIP::localhost::',
        "has_slots": False,
        "has_channels": False,
        "has_sweep_gui": False,
        "has_config_gui": False,
        "devices_name": []
    },
    "be214x": {
        "pyhegel_class": instruments.iTest_be214x,
        "has_address": True, "address":"TCPIP::192.168.150.145::5025::SOCKET",
        "has_slots": True, "slots": [1, 2, 3, 4], # 4 instruments in one
        "has_channels": True, "channels": [1, 2, 3, 4], # 4 channel per instr
        "channel_key": "ch",
        "has_sweep_gui": False,
        "has_config_gui": False,
        "devices_name": ["output_en", "range", "slope", "ramp", "level", "meas_out_volt", "meas_out_current"]
    },
    "dmm344xxA": {
        "pyhegel_class": instruments.agilent_multi_34410A,
        "has_address": True, "address":'TCPIP::K-34465A-15472.mshome.net::inst0::INSTR',
        "has_slots": False,
        "has_channels": False,
        "has_sweep_gui": False,
        "has_config_gui": False,
        "devices_name": ["readval", "nplc"]
    },
        
}

supported_devices = {
    "Limit device": {
        "pyhegel_class": instruments.LimitDevice,
        "args": ["Min: ", "Max: "], # (in the right order)
    },
    "Scaling device": {
        "pyhegel_class": instruments.ScalingDevice,
        "args": ["Scale factor: ", "Offset: "],
    },
    "Ramp device": {
        "pyhegel_class": instruments.RampDevice,
        "args": ["Rate: ", "Interval: "],
    },
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

    def showDisplay(self):
        self.view_display.show()
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

    def checkInstrLoadingName(self, name):
        # check if the loading name is already used
        i, base = 1, name
        while name in self.gui_instruments.keys():
            name = base + ' ({})'.format(i)
            i += 1
        return name
    
    def checkDevLoadingName(self, name, gui_instr):
        # check if the loading name is already used
        i, base = 1, name
        while name in gui_instr.gui_devices.keys():
            name = base + ' ({})'.format(i)
            i += 1
        return name

    def loadGuiInstrument(self, gui_instr):
        # load a GuiInstrument:
        # - make sure the nickname is unique
        gui_instr.nickname = self.checkInstrLoadingName(gui_instr.nickname)
        # - try load the pyHegel instrument
        try:
            kwargs = {}
            if gui_instr.slot is not None:
                kwargs['slot'] = gui_instr.slot
            gui_instr.ph_instr = self.model.loadInstrument(gui_instr.nickname,
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
            except Exception as e:
                tb_str = ''.join(traceback.format_tb(e.__traceback__))
                self.pop.devLoadError(e, tb_str)


    def buildGuiInstrument(self, nickname, instr_name, addr, slot=None):
        # call only by the Rack. Loading is done in loadGuiInstrument.
        # build GuiInstrument and populate dvices, but no ph_instr nor ph_dev
        settings = supported_instruments[instr_name]
        instr_cls = settings['pyhegel_class']
        gui_instr = GuiInstrument(nickname, instr_name, instr_cls, addr, slot)
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
        del self.gui_instruments[gui_instr.nickname]
            
    def getValue(self, gui_dev):
        # get the value of the GuiDevice and update the gui
        value = self.model.getValue(gui_dev.getPhDev())
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
    
    def createDevice(self, gui_dev, dev_type_name, args):
        # create a device in the instrument
        # dev_type: instruments.RampingDevice, instruments.ScalingDevice
        #dev_settings = self.supported_devices[dev_type_name]

        #dev_cls = dev_settings['pyhegel_class']
        #name = dev_cls.__name__ + '(' + gui_dev.name + ')'
        #display_name = self.makeGuiDevName(gui_dev.parent.instr_name, name)
        #ph_dev = self.model.makeDevice(gui_dev.ph_dev,
                                       #dev_settings['pyhegel_class'],
                                       #args)
        #new_dev = GuiDevice(display_name, name, gui_dev.parent)
        #new_dev.ph_dev = ph_dev
        #new_dev.is_extra = True
        #new_dev.extra_type = dev_cls
        #new_dev.extra_args = args
        #new_dev.parent.gui_extra_devices.append(new_dev)
        pass

    def renameDevice(self, gui_dev, new_nickname):
        # renamed by rack, tell the main window
        new_nickname = self.checkDevLoadingName(new_nickname, gui_dev.parent)
        gui_dev.parent.gui_devices[new_nickname] = gui_dev
        gui_dev.parent.gui_devices.pop(gui_dev.nickname)
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
        self.view_main.setEnabled(False)
        # TODO: handle custom gui
        self.view_main.window_configSweep(gui_dev)
    
    def setSweepValues(self, gui_dev, start, stop, npts):
        # set sweep values for gui_dev and update the gui
        gui_dev.sweep = [start, stop, npts]
        self.view_main.gui_updateSweepValues(gui_dev)
        self.view_main.win_sw_setup.close()
        self.view_main.setEnabled(True)
    

    # -- SWEEP THREAD --

    def _prepareFilename(self):
        filename = self.view_main.filename_edit.text()
        if filename == '':
            filename = 'sweep'
        filename = './temp/' + filename
        return filename

    def _startSweepCheckError(self, start, stop, npts, ph_sw_devs, ph_out_devs):
        if None in start or None in stop or None in npts:
            self.pop.missingSweepParameter(); return True
        if ph_sw_devs == []:
            self.pop.noSweepDevice(); return True
        if 0 in npts:
            self.pop.sweepZeroPoints(); return True
        if ph_out_devs == [] and self.pop.noOutputDevice() == False:
            return True
        return False
    
    def _genListsAndAllocData(self, gui_sw_devs, gui_out_devs, gui_log_devs):
        # allocate data in gui_devices for the live view.
        # for simplicity, we allocate the total number of points
        # even for devices that are swept (e.g not output devices)
        # NOT MEMORY EFFICIENT. If software is slow, it might be the reason. 
        total_points = 1
            
        ph_sw_devs, start, stop, npts = [], [], [], []
        for dev in gui_sw_devs:
            ph_sw_devs.append(dev.ph_dev)
            start.append(dev.sweep[0])
            stop.append(dev.sweep[1])
            npts.append(dev.sweep[2])
            total_points *= dev.sweep[2]
            
        ph_out_devs = []
        for dev in gui_out_devs:
            ph_out_devs.append(dev.ph_dev)

        ph_log_devs = []
        for dev in gui_log_devs:
            ph_log_devs.append(dev.ph_dev)
        
        for dev in gui_sw_devs + gui_out_devs:
            dev.values = np.full(total_points, np.nan)
        
        return ph_sw_devs, start, stop, npts, ph_out_devs, ph_log_devs

    def startSweep(self):
        # trigger on start sweep button
        # prepare everything and start the thread.
        gui_sw_devs = self.view_main.gui_getSweepGuiDevs()
        gui_out_devs = self.view_main.gui_getOutputGuiDevs()
        gui_log_devs = self.view_main.gui_getLogGuiDevs()
        
        # generate lists and allocate data
        ph_sw_devs, start, stop, npts, ph_out_devs, ph_log_devs = \
            self._genListsAndAllocData(gui_sw_devs, gui_out_devs, gui_log_devs)
        
        # errors
        if self._startSweepCheckError(start, stop, npts, ph_sw_devs, ph_out_devs):
            return

        # prepare kw
        sweep_kwargs = {
            'dev': ph_sw_devs, 'start': start, 'stop': stop,
            'npts': npts, 'out': ph_out_devs,
            'filename': self._prepareFilename(),
            'extra_conf': ph_log_devs,
            #'wait_after': self.sb_before_wait.value()
        }

        # run sweep thread
        self.sweep_thread.initSweepKwargs(sweep_kwargs)
        self.sweep_thread.initCurrentSweep(gui_sw_devs, gui_out_devs, time.time())
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
        self.pop.sweepError(name, message)
    
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
        self.sweep_thread.resetStartTime(time.time())
        self.view_main.gui_sweepResumed()
    
    def abortSweep(self):
        # called by the main window
        self.loop_control.abort_enabled = True
        self.loop_control.pause_enabled = False # in case of Pause->Abort
        #self.view_main.gui_sweepFinished()
        # TODO: handle abort status



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