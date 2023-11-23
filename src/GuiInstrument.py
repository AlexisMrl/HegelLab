
class GuiInstrument():
    # class attached to every item that represent an instr
    
    def __init__(self, nickname, instr_name, instr_cls, instr_driver, address, slot=None):

        self.nickname = nickname
        self.instr_name = instr_name
        self.instr_cls = instr_cls
        self.instr_driver = instr_driver
        self.address = address
        self.slot = slot

        self.ph_instr = None
        self.gui_devices = {} # {nickname: GuiDevice}
    
    def getDisplayName(self, type=''):
        # type for consistency with GuiDevice
        if self.nickname != self.instr_name:
            return self.nickname + ' (' + self.instr_name + ')'
        else:
            return self.nickname

    def getGuiDevByDevName(self, dev_name): # name is not the nickname
        for gui_dev in self.gui_devices.values():
            if gui_dev.dev_name == dev_name:
                return gui_dev
        return None

    def getCopy(self):
        # return a 'copy' of self without ph_instr and ph_dev
        # so pickle can save it, and ph devs are not dereferenced
        me = GuiInstrument(self.nickname, self.instr_name, self.instr_cls, self.address)
        return me


class GuiDevice():
    # class attached to every item that represent a dev

    def __init__(self, nickname, dev_name, parent):
        self.nickname = nickname
        self.dev_name = dev_name
        self.parent = parent

        # kept when saving/loading
        self.hide = False # if True, the device is not shown in the gui
        self.ph_dict = None # if the device is a tuple, holds the kwargs
        # for ramping and scaling devices
        self.needed_by = [] # list of gui_dev: device that needs this one
        self.needs = [] # list of gui_dev: device that this one needs
        self.extra_type = None # key of supported_devices
        self.extra_args = None # {arg_name: arg_value}


        # not kept when saving
        self.ph_dev = None
        self.ph_choice = None # ChoiceString from pyHegel
        self.type = (False, False) # (settable, gettable)
        self.sweep = [None, None, None] # [start, stop, npts]
        self.cache_value = None # a value to cache the last value read
    
        # a np.array for when the device is in a sweep (swept or output)
        # size is allocated at the beginning of the sweep
        self.values = None
        self.sw_idx = None # SweepIdxIter object
    
    def getDisplayName(self, type='short'):
        # type: 'short' or 'long'
        #   short: nickname + dev_name
        #   long: instr_name + nickname + dev_name
        dev_name = self.dev_name
        if self.ph_dict is not None:
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

