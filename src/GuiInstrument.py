
class GuiInstrument():
    # class attached to every item that represent an instr
    
    def __init__(self, nickname, instr_name, instr_cls, address, slot=None):

        self.nickname = nickname
        self.instr_name = instr_name
        self.instr_cls = instr_cls
        self.address = address
        self.slot = slot

        self.ph_instr = None
        self.gui_devices = {} # {name: GuiDevice}
        self.gui_extra_devices = {} # {nickname: GuiDevice} (ramping/scaling devs)
    
    def getDisplayName(self, type, full=False):
        if self.nickname != self.instr_name:
            return self.nickname + ' (' + self.instr_name + ')'

    def getCopy(self):
        # return a 'copy' of self without ph_instr and ph_dev
        # so pickle can save it, and ph devs are not dereferenced
        me = GuiInstrument(self.nickname, self.instr_name, self.instr_cls, self.address)
        gui_devices = {}
        for name, gui_dev in self.gui_devices.items():
            gui_dev_copy = gui_dev.getCopy(me)
            gui_devices[name] = gui_dev_copy
        me.gui_devices = gui_devices
        gui_extra_devices = {}
        for name, gui_dev in self.gui_extra_devices.items():
            gui_dev_copy = gui_dev.getCopy(me)
            gui_extra_devices[name] = gui_dev_copy
        me.gui_extra_devices = gui_extra_devices
        return me


class GuiDevice():
    # class attached to every item that represent a dev

    def __init__(self, nickname, dev_name, parent):
        self.nickname = nickname
        self.dev_name = dev_name
        self.parent = parent

        # kept when saving/loading
        self.ph_dict = None # if the device is a tuple, holds the kwargs
        self.sweep = [None, None, None] # [start, stop, npts]
            # for ramping and scaling devices
        self.is_extra = False
        self.extra_type = None
        self.extra_args = None # (*args)

        self.ph_dev = None
        self.type = (False, False) # (settable, gettable)
    
        # a np.array for when the device is in a sweep (swept or output)
        # size is allocated at the beginning of the sweep
        self.values = None
    
    def getDisplayName(self, type, full=False):
        # if full: dev_name = dev_name + ph_dict
        dev_name = self.dev_name
        if full and self.ph_dict is not None:
            str_ars = [str(k) + '=' + str(v) for k, v in self.ph_dict.items()]
            dev_name = dev_name + ', ' + ''.join(str_ars)
        if type=='short':
            if self.nickname != self.dev_name:
                return self.nickname + ' (' + dev_name + ')'
            return self.nickname
        if type=='long':
            if self.nickname != self.dev_name:
                return self.parent.nickname + ' - ' + self.nickname + ' (' + dev_name + ')'
            return self.parent.nickname + ' - ' + self.nickname
    
    def getPhDev(self):
        dev = self.ph_dev
        if self.ph_dict is not None:
            return (dev, self.ph_dict)
        return dev
    
    def getCopy(self, parent):
        me = GuiDevice(self.display_name, self.name, parent)
        me.is_extra = self.is_extra
        me.extra_type = self.extra_type
        me.extra_args = self.extra_args
        return me