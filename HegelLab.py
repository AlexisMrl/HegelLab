import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget
from PyQt5 import uic, QtCore

from views import Main, Rack, Display
from src import Model, Errors


# HegelLab is made to support any instrument with minimal effort.
# It should be enough to add the instrument class to the dictionary below.
# TODO: use json file
supported_instruments = {
    "dummy": {
        "pyhegel_class": instruments.dummy,
        "has_address": False,
        "has_port": False,
        "has_gui": False,
        "devices_name": ["rand", "volt", "current"]
    }
}

# conventions:
# window_ : build and show a window
# gui_ : manage the gui
# ask_ : (from other windows) ask the lab to do something

class HegelLab(QMainWindow):

    def __init__(self):
        super(HegelLab, self).__init__()

        self.model = Model.Model()
        self.view_main = Main.Main(self)
        self.view_rack = Rack.Rack(self)
        self.view_display = Display.Display(self)
        
        self.error = Errors.Errors()

        self.supported_instruments = supported_instruments
        self.loaded_gui_instruments = {} # {nickname: GuiInstrument}

        self.showMain()
        
    def showMain(self):
        self.view_main.show()
        self.view_main.raise_()
        
    def showRack(self):
        self.view_rack.show()
        self.view_rack.raise_()

    def showDisplay(self):
        self.view_display.show()
        self.view_display.raise_()
        
    def checkInstrLoadingName(self, name):
        # check if the loading name is already used
        i = 1
        base = name
        while name in self.loaded_gui_instruments.keys():
            name = base + ' ({})'.format(i)
            i += 1
        return name

    def buildInstrDevName(self, instr, dev):
        return instr + ' - ' + dev
    
    def loadAndAddInstrument(self, instr_name, instr_nickname, address):
        # load in pyHege, instanciate GuiInstrument, update gui
        instr_cls = supported_instruments[instr_name]['pyhegel_class']
        ph_instr = self.model.loadInstrument(instr_cls, address)
        devs = self.model.getDevices(ph_instr, 
                                    *self.supported_instruments[instr_name]['devices_name'])
        if instr_nickname == '':
            instr_nickname = instr_name
        instr_nickname = self.checkInstrLoadingName(instr_nickname)
        # create the GuiInstrument
        gui_instr = GuiInstrument(instr_cls, instr_nickname, address,
                                  ph_instr,
                                  devs)
        self.loaded_gui_instruments[instr_nickname] = gui_instr
        # update gui
        self.view_rack.gui_addGuiInstrument(gui_instr)
        self.view_rack.win_add.close()
            
    def unloadAndRemoveInstrument(self, nickname):
        # unload in pyHegel, remove GuiInstrument, update gui
        gui_instr = self.loaded_gui_instruments[nickname]
        self.model.unloadInstrument(gui_instr.instr)
        del self.loaded_gui_instruments[nickname]
        self.view_rack.gui_removeInstrument()
    
    def getValueAndUpdateRack(self, nickname, dev_name):
        # get the value of a device and update the rack gui
        gui_instr = self.loaded_gui_instruments[nickname]
        dev = gui_instr.devices[dev_name]
        value = self.model.getValue(dev)
        self.view_rack.gui_updateDeviceValue(nickname, dev_name, value)
    
    def addSweepDev(self, instr_nickname, dev_name):
        # add a device to the sweep tree, launch the config window
        name = self.buildInstrDevName(instr_nickname, dev_name)
        data = {'instrument':instr_nickname, 'device':dev_name}
        self.view_main.gui_addSweepItem(name, data)
        self.view_main.tree_sw.selectLastItem()
        self.showSweepConfig()
    
    def showSweepConfig(self):
        # launch the config window for the selected sweep device
        self.view_main.setEnabled(False)
        self.view_main.window_configSweep()
    
    def addOutputDev(self, instr_nickname, dev_name):
        # add a device to the output tree, launch the config window
        name = self.buildInstrDevName(instr_nickname, dev_name)
        data = (instr_nickname, dev_name)
        self.view_main.gui_addOutItem(name, data)
    
    def setSweepValues(self, instr, dev, start, stop, npts):
        # set the sweep values for current sweep item
        self.view_main.gui_setSweepValues(start, stop, npts)
        self.view_main.win_sw_setup.close()
    
    def _prepareSweepDevsStartStopNpts(self):
        # go through self.view_main.tree_sw and return devs, start, stop, npts:
        devs, start, stop, npts = [], [], [], []
        for i in range(self.view_main.tree_sw.topLevelItemCount()):
            item = self.view_main.tree_sw.topLevelItem(i)
            dic = item.data(0, QtCore.Qt.UserRole)
            devs.append(dic['device'])
            sweep_values = dic['sweep_values']
            start.append(sweep_values[0])
            stop.append(sweep_values[1])
            npts.append(sweep_values[2])
        return devs, start, stop, npts

    def onStartSweep(self):
        # retreive all parameters
        try:
            devs, start, stop, npts = self._prepareSweepDevsStartStopNpts()
        except KeyError:
            self.error.missingSweepParameter()
            return



        # check everything is fine
        # TODO is path ok ?


        #self.model.startSweep()


        


class GuiInstrument():
    # This class is used to manage instruments in the gui.
    
    def __init__(self, instr_cls, name, address='',
                 instr=None,
                 devices={},):
        # instr_cls is the pyHegel class of the instrument
        # name is the nick_name of the instrument
        # address is the address of the instrument
        # instr is the instance of the instrument if loaded
        self.instr_cls = instr_cls
        self.name = name
        self.address = address
        self.instr = instr
        self.devices = devices



if __name__ == "__main__":
    hl = HegelLab()