import pickle

class LoaderSaver():
    def __init__(self, lab):
        self.lab = lab


    def save(self, gui_instruments, path):
        # save the lab state to a file

        # get gui_instr iwhout ph_instr and ph_dev
        to_save = {}
        for name, gui_instr in gui_instruments.items():
            to_save[name] = gui_instr.getCopy()
        self.saved = to_save
        
        # save
        with open(path, 'wb') as f:
            pickle.dump(to_save, f)
    

    def load(self, path):
        # load the lab state from a file
        
        with open(path, 'rb') as f:
            to_load = pickle.load(f) # {nickname: gui_instr}


        # restore ph_instr and ph_dev
        for gui_instr in to_load.values():
            gui_instr.nickname = self.lab.checkInstrLoadingName(gui_instr.nickname)
            ph_instr = self.lab.tryLoadPhInstr(gui_instr)
            gui_instr.ph_instr = ph_instr

            for gui_dev in gui_instr.gui_devices.values():
                ph_dev = self.lab.tryGetPhDev(gui_instr, gui_dev.name)
                gui_dev.ph_dev = ph_dev
        
            self.lab.afterLoadInstrument(gui_instr)
