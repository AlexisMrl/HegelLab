import sys, traceback

from PyQt5.QtWidgets import QApplication

from views import Main, Rack, Display
from src import LoaderSaver, Model, Popup, SweepThread
from src.GuiInstrument import GuiInstrument, GuiDevice


# HegelLab is made to support any instrument with minimal effort.
# It should be enough to add the instrument class to the dictionary below.
# TODO: use json file
from pyHegel import instruments
supported_instruments = {
    "dummy": {
        "pyhegel_class": instruments.dummy,
        "has_address": False,
        "has_port": False,
        "has_sweep_gui": False,
        "has_config_gui": False,
        "devices_name": ["rand", "volt", "current"]
    },
    "zurich": {
        "pyhegel_class": instruments.zurich_UHF,
        "has_address": True,
        "has_port": False,
        "has_sweep_gui": False,
        "has_config_gui": False,
        "devices_name": []
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
        print(gui_dev.name)


    # -- RACK --

    def checkInstrLoadingName(self, name):
        # check if the loading name is already used
        i = 1
        base = name
        while name in self.gui_instruments.keys():
            name = base + ' ({})'.format(i)
            i += 1
        return name

    def tryLoadPhInstr(self, gui_instr):
        # try load in pyHegel
        try:
            ph_instr = self.model.loadInstrument(gui_instr.instr_cls,
                                                 gui_instr.address,
                                                 gui_instr.nickname)
        except Exception as e:
            # get traceback for the messagebox:
            tb_str = ''.join(traceback.format_tb(e.__traceback__))
            self.pop.instrLoadError(e, tb_str)
            return None
        return ph_instr

    def tryGetPhDev(self, gui_instr, dev_name):
        if gui_instr.ph_instr is None:
            return None
        try:
            ph_dev = self.model.getDevice(gui_instr.ph_instr, dev_name)
        except Exception as e:
            # get traceback for the messagebox:
            tb_str = ''.join(traceback.format_tb(e.__traceback__))
            self.pop.devLoadError(e, tb_str)
            return None
        return ph_dev

    def loadGuiInstrument(self, gui_instr):
        # load a GuiInstrument:
        # - make sure the nickname is unique
        nickname = self.checkInstrLoadingName(gui_instr.nickname)
        gui_instr.nickname = nickname
        # - load the pyHegel instrument
        gui_instr.ph_instr = self.tryLoadPhInstr(gui_instr)
        # - load the pyHegel devices
        for gui_dev in gui_instr.gui_devices.values():
            gui_dev.ph_dev = self.tryGetPhDev(gui_instr, gui_dev.name)
            gui_dev.type = self.model.devType(gui_dev.ph_dev)
        # - add it to the lab
        self.gui_instruments[gui_instr.nickname] = gui_instr
        self.view_rack.gui_addGuiInstrument(gui_instr)
        self.view_rack.win_add.close()
    
    def buildGuiInstrument(self, nickname, instr_name, instr_cls, address):
        # call only by the Rack. Loading is done in loadGuiInstrument.
        if nickname == '': nickname = instr_name
        gui_instr = GuiInstrument(nickname, instr_name, instr_cls, address)
        for dev_name in supported_instruments[instr_name]['devices_name']:
            dev_display_name = instr_name + ' - ' + dev_name
            gui_dev = GuiDevice(dev_display_name, dev_name, gui_instr)
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
        value = self.model.getValue(gui_dev.ph_dev)
        self.view_rack.gui_updateDeviceValue(gui_dev, value)


    # -- SWEEP TREES --

    def addSweepDev(self, instr_nickname, dev_name):
        # add a device to the sweep tree, launch the config window
        gui_dev = self.gui_instruments[instr_nickname].gui_devices[dev_name]
        if gui_dev.type[0] == False and self.pop.notSettable() == False:
            # if the device is not gettable, ask if we want to add it anyway
            return
        if self.view_main.tree_sw.findItemByData(gui_dev) != None:
            self.pop.devAlreadyHere(); return
        self.view_main.gui_addSweepGuiDev(gui_dev)
        self.showSweepConfig(gui_dev)

    def addOutputDev(self, instr_nickname, dev_name):
        # add a device to the output tree
        gui_dev = self.gui_instruments[instr_nickname].gui_devices[dev_name]
        if gui_dev.type[1] == False and self.pop.notGettable() == False:
            return
        if self.view_main.tree_out.findItemByData(gui_dev) != None:
            self.pop.devAlreadyHere(); return
        self.view_main.gui_addOutItem(gui_dev)
    
    def addLogDev(self, instr_nickname, dev_name):
        # add a device to the log tree
        gui_dev = self.gui_instruments[instr_nickname].gui_devices[dev_name]
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
        }

        # run sweep thread
        self.sweep_thread.initSweepKwargs(sweep_kwargs)
        self.sweep_thread.initCurrentSweep(gui_sw_devs, gui_out_devs, time.time())
        self.sweep_thread.start()
        
        # update gui
        self.view_main.gui_sweepStarted()
        self.view_display.gui_sweepStarted(self.sweep_thread.current_sweep)
        self.showDisplay()

    def onSweepSignalProgress(self, current_sweep):
        # called by the sweep thread
        # sweep_status is a SweepStatusObject

        # update display and status
        self.view_display.gui_onIteration(current_sweep)
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