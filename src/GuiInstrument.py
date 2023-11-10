
class GuiInstrument():
    # class attached to every item that represent an instr
    
    def __init__(self, nickname, instr_name, instr_cls,
                 address=''):

        self.nickname = nickname
        self.instr_name = instr_name
        self.instr_cls = instr_cls
        self.address = address

        self.ph_instr = None
        self.gui_devices = {} # {name: GuiDevice}

    def getCopy(self):
        # return a 'copy' of self without ph_instr and ph_dev
        # so pickle can save it, and ph devs are not dereferenced
        me = GuiInstrument(self.nickname, self.instr_name, self.instr_cls,
                           self.address)
        gui_devices = {}
        for name, gui_dev in self.gui_devices.items():
            gui_dev_copy = gui_dev.getCopy()
            gui_dev_copy.parent = me
            gui_devices[name] = gui_dev_copy
        me.gui_devices = gui_devices
        return me


class GuiDevice():
    # class attached to every item that represent a dev

    def __init__(self, display_name, name, ph_dev, parent=None):
        self.display_name = display_name # instr_name + ' - ' + dev_name
        self.name = name # dev_name
        self.ph_dev = ph_dev
        self.parent = parent

        self.sweep = [None, None, None] # [start, stop, npts]
        self.limits = [None, None]
        
        # a np.array for when the device is in a sweep (swept or output)
        # size is allocated at the beginning of the sweep
        self.values = None
    
    def getCopy(self):
        me = GuiDevice(self.display_name, self.name, None)
        me.sweep = self.sweep
        me.limits = self.limits
        return me