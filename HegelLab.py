import sys, traceback

from views import Main, Rack, Display
from src import Model, Popup, SweepThread
from src.GuiInstrument import GuiInstrument, GuiDevice

# HegelLab is made to support any instrument with minimal effort.
# It should be enough to add the instrument class to the dictionary below.
# TODO: use json file
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
        super(HegelLab, self).__init__()

        # model, views
        self.model = Model.Model()
        self.view_main = Main.Main(self)
        self.view_rack = Rack.Rack(self)
        self.view_display = Display.Display(self)
        
        # popups
        self.pop = Popup.Popup()
        
        # data
        self.supported_instruments = supported_instruments
        self.gui_instruments = {} # {nickname: GuiInstrument}

        # sweep
        self.sweep_thread = SweepThread.SweepThread(self.model.startSweep)
        self.sweep_thread.progress_signal.connect(self.onSweepProgress)
        self.sweep_thread.error_signal.connect(self.onSweepError)
        self.sweep_thread.finished_signal.connect(self.onSweepFinished)


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

    def buildDevDisplayName(self, instr_name, dev_name):
        # build the display name of a device
        return instr_name + ' - ' + dev_name

    def buildGuiInstrument(self, instr_nickname, instr_cls, address):
        # instantiate a GuiInstrument
        gui_instr = GuiInstrument(instr_nickname, instr_cls, address)
        self.gui_instruments[instr_nickname] = gui_instr
        return gui_instr

    def buildGuiDevice(self, display_name, name, ph_dev):
        gui_dev = GuiDevice(display_name, name, ph_dev)
        return gui_dev

    def loadNewInstrument(self, instr_name, instr_nickname, address):
        if instr_nickname == '':
            instr_nickname = instr_name
        instr_nickname = self.checkInstrLoadingName(instr_nickname)

        # load in pyHegel
        instr_cls = supported_instruments[instr_name]['pyhegel_class']
        try:
            ph_instr = self.model.loadInstrument(instr_cls, address, instr_nickname)
        except Exception as e:
            # get traceback for the messagebox:
            tb_str = ''.join(traceback.format_tb(e.__traceback__))
            self.pop.instrLoadError(e, tb_str); return

        # build GuiInstrument
        gui_instr = self.buildGuiInstrument(instr_nickname, instr_cls, address)
        gui_instr.ph_instr = ph_instr
        
        # fill GuiInstrument with GuiDevices
        instr_devices = []
        for name in supported_instruments[instr_name]['devices_name']:
            display_name = self.buildDevDisplayName(instr_nickname, name)
            ph_dev = self.model.getDevice(ph_instr, name)
            gui_dev = self.buildGuiDevice(display_name, name, ph_dev)
            gui_dev.parent = gui_instr
            gui_instr.gui_devices[name] = gui_dev

        # update gui
        self.view_rack.gui_addGuiInstrument(gui_instr)
        self.view_rack.win_add.close()
            
    def getValue(self, gui_dev):
        # get the value of the GuiDevice and update the gui
        value = self.model.getValue(gui_dev.ph_dev)
        self.view_rack.gui_updateDeviceValue(gui_dev, value)


    # -- SWEEP --

    def addSweepDev(self, instr_nickname, dev_name):
        # add a device to the sweep tree, launch the config window
        gui_dev = self.gui_instruments[instr_nickname].gui_devices[dev_name]
        if self.view_main.tree_sw.findItemByData(gui_dev) != None:
            self.pop.devAlreadyHere(); return
        self.view_main.gui_addSweepGuiDev(gui_dev)
        self.showSweepConfig(gui_dev)

    def addOutputDev(self, instr_nickname, dev_name):
        # add a device to the output tree
        gui_dev = self.gui_instruments[instr_nickname].gui_devices[dev_name]
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
        self.setEnabled(True)
    
    def _prepareFilename(self):
        filename = self.view_main.filename_edit.text()
        if filename == '':
            filename = 'sweep'
        filename = './temp/' + filename
        return filename

    def startSweep(self):
        devs, start, stop, npts = self.view_main.gui_getSweepValues()
        out = self.view_main.gui_getOutputDevs()
        
        # errors
        if None in start or None in stop or None in npts:
            self.pop.missingSweepParameter(); return
        if devs == []:
            self.pop.noSweepDevice(); return
        if 0 in npts:
            self.pop.sweepZeroPoints(); return
        if out == [] and self.pop.noOutputDevice() == False:
            return

        # start sweep
        sweep_kwargs = {
            'dev': devs,
            'start': start,
            'stop': stop,
            'npts': npts,
            'out': out,
            'filename': self._prepareFilename(),
            'extra_conf': self.view_main.gui_getLogDevs(),
        }
        self.sweep_kwargs = sweep_kwargs # for debug only

        self.sweep_thread.setSweepKwargs(sweep_kwargs)
        #self.sweep_thread.start()
    
    def onSweepProgress(self, sw_status_obj):
        # exec after each sweep iteration
        x, y = sw_status_obj.set_vals
        o = sw_status_obj.get_vals[0]
        self.view_display.addXYval(x, y, o)
    
    def onSweepError(self, name, message):
        self.pop.sweepError(name, message)
    
    def onSweepFinished(self):
        print('sweep finished')




if __name__ == "__main__":
    hl = HegelLab()