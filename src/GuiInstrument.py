class GuiInstrument:
    # class attached to every item that represent an instr

    def __init__(
        self, nickname, instr_name, ph_class, driver, address, slot=None
    ):
        self.nickname = nickname
        self.instr_name = instr_name # name in the config json file
        self.ph_class = ph_class
        self.driver = driver # driver name, default = Drivers.Default
        self.address = address
        self.slot = slot

        self.instr_dict = {}  # the dict from json file (as is (not updated)). Used for driver with extra args
        self.ph_instr = None
        self.gui_devices = []  # list of GuiDevice

    def getDisplayName(self, type=""):
        # 'type' for consistency with GuiDevice
        if self.nickname != self.instr_name:
            return self.nickname + " (" + self.instr_name + ")"
        else:
            return self.nickname
    
    def getGuiDevice(self, dev_nickname):
        for gui_device in self.gui_devices:
            if gui_device.nickname != dev_nickname:
                continue
            return gui_device
        return None
    


class GuiDevice:
    # class attached to every item that represent a dev

    def __init__(self, nickname, ph_name, extra_args, parent):
        self.nickname = nickname
        self.ph_name = ph_name
        self.extra_args = extra_args # dict of kwargs for tuple devices
        self.parent = parent
        
        self.logical_kwargs = {'scale': {}, 'ramp':{}, 'limit':{}}
        self.logical_dev = None

        # not kept when saving
        self.ph_dev = None
        self.ph_choice = None  # ChoiceString from pyHegel
        self.type = (None, None)  # (settable, gettable) = (T/F, T/F)
        self.sweep = [None, None, None]  # [start, stop, npts]
        self.cache_value = None  # a variable to cache the last value read

        # a np.array for when the device is in a sweep (swept or output)
        # size is allocated at the beginning of the sweep
        self.values = None
        self.sw_idx = None  # SweepIdxIter object

    def getPhDev(self):
        if self.logical_dev is not None:
            return self.logical_dev
        dev = self.ph_dev
        if self.extra_args != {}:
            return (dev, self.extra_args)
        return dev

    def getDisplayName(self, type="short", with_instr=False):
        # type: 'short' or 'long'
        #   short: nickname
        #   long: nickname (ph_name, extra_args)
        # with_instr: True or False
        #   True: instr_nickname - getDisplayName(type)
        nickname = self.nickname
        ph_name = self.ph_name

        if with_instr:
            nickname = self.parent.nickname + " - " + nickname

        if type == "short":
            return nickname
        
        if type == "long":
            if self.extra_args != {}:
                ph_name += ", " + str(self.extra_args)
            return nickname + " (" + ph_name + ")"