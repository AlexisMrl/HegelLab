
class GuiInstrument():
    # This class is used to manage instruments in the gui.
    
    def __init__(self, nickname, instr_cls,
                 address=''):

        self.instr_cls = instr_cls
        self.nickname = nickname
        self.address = address

        self.ph_instr = None
        self.gui_devices = {} # {name: GuiDevice}



class GuiDevice():

    def __init__(self, display_name, name, ph_dev):
        self.display_name = display_name
        self.name = name
        self.ph_dev = ph_dev

        self.parent = None
        self.sweep = [None, None, None] # [start, stop, npts]
        self.limits = [None, None]
        
        # a np.array for when the device is in a sweep
        # size is allocated at the beginning of the sweep
        self.values = None