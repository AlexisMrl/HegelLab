import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget
from PyQt5 import uic

import Model
import Rack
import Display


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
        # -- ui setup --
        uic.loadUi('ui/HegelLabWindow.ui', self)
        self.setWindowTitle('HegelLab')
        #self.setWindowIcon(QtGui.QIcon('resources/favicon/hegelLab.svg'))
        self.toolBar.setToolButtonStyle(2) # text beside icon



        self.model = Model.Model()
        self.rack = Rack.Rack(self)
        self.display = Display.Display(self)

        self.supported_instruments = supported_instruments
        self.loaded_gui_instruments = {} # {nickname: GuiInstrument}

        # -- Connect signals to slots --
        self.actionInstruments.triggered.connect(self.rack.show)
        self.actionDisplay.triggered.connect(self.display.show)
        
    def checkName(self, name):
        # check if the name is already used
        i = 1
        while name in self.loaded_gui_instruments.keys():
            name = name + ' ({})'.format(i)
            i += 1
        return name

    def loadAndAddInstrument(self, instrument_name, nickname, address):
        # load in pyHegel
        instrument_cls = supported_instruments[instrument_name]['pyhegel_class']
        ph_instr = self.model.loadInstrument(instrument_cls, address)
        # prepare everything for the GuiInstrument
        devs = self.model.getDevices(ph_instr, 
                                    *self.supported_instruments[instrument_name]['devices_name'])
        if nickname == '':
            nickname = instrument_name
        nickname = self.checkName(nickname)
        # create the GuiInstrument, update gui
        gui_instr = GuiInstrument(instrument_cls, nickname, address,
                                  ph_instr,
                                  devs)
        self.loaded_gui_instruments[nickname] = gui_instr
        self.rack.gui_addGuiInstrument(gui_instr)
        self.rack.win_add.close()
            
    def unloadAndRemoveInstrument(self, nickname):
        gui_instr = self.loaded_gui_instruments[nickname]
        self.model.unloadInstrument(gui_instr.instr)
        del self.loaded_gui_instruments[nickname]
        self.rack.gui_removeInstrument()
    
    def getValueAndUpdateRack(self, nickname, dev_name):
        gui_instr = self.loaded_gui_instruments[nickname]
        dev = gui_instr.devices[dev_name]
        value = self.model.getValue(dev)
        self.rack.gui_updateDeviceValue(nickname, dev_name, value)
        
        


class GuiInstrument():
    # This class is used to manage instruments in the gui.
    
    def __init__(self, instrument_cls, name, address='',
                 instr=None,
                 devices={},):
        # instrument_cls is the pyHegel class of the instrument
        # name is the nick_name of the instrument
        # address is the address of the instrument
        # instr is the instance of the instrument if loaded
        self.instrument_cls = instrument_cls
        self.name = name
        self.address = address
        self.instr = instr
        self.devices = devices


 

if __name__ == "__main__":
    hl = HegelLab()
    hl.show()