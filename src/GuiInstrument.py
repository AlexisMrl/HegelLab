class GuiInstrument:
    # class attached to every item that represent an instr

    def __init__(
        self, nickname, ph_class, driver, address, slot=None
    ):
        self.nickname = nickname
        self.ph_class = ph_class # a string that can be eval() to get the class
        self.driver = driver # driver name, default = "Drivers.Default" (str too)
        self.address = address
        self.slot = slot

        self.instr_dict = {}  # the dict from json file (as is (not updated)). Used for driver with extra args
        self.ph_instr = None
        self.gui_devices = []  # list of GuiDevice

    def getDisplayName(self, type="short"):
        # 'type'
        #   short: nickname
        #   long: nickname (ph_name, extra_args)
        
        if type == "short":
            return self.nickname

        class_name = self.ph_class.split(".")[-1]
        if self.nickname != class_name:
            return f"{self.nickname} ({class_name})"
        else:
            return self.nickname
    
    def isLoaded(self):
        return self.ph_instr is not None
    
    def getGuiDevice(self, dev_nickname):
        for gui_device in self.gui_devices:
            if gui_device.nickname != dev_nickname:
                continue
            return gui_device
        return None

    def toDict(self):
        # for json file saving
        d = {
            'ph_class': self.ph_class,
        }
        if self.nickname != self.ph_class.split(".")[-1]:
            d['nickname'] = self.nickname
        if self.driver != 'Drivers.Default':
            d['driver'] = self.driver
        if self.address is not None:
            d['address'] = self.address
        if self.slot is not None:
            d['slot'] = self.slot
        d['devices'] = []
        for gui_dev in self.gui_devices:
            d['devices'].append(gui_dev.toDict())

        return d

    


class GuiDevice:
    # class attached to every item that represent a dev

    def __init__(self, nickname, ph_name, extra_args, parent):
        self.nickname = nickname
        self.ph_name = ph_name
        self.extra_args = extra_args # dict of kwargs for tuple devices
        self.parent = parent
        self.type = (None, None)  # (settable, gettable) = (T/F, T/F)
        
        self.logical_kwargs = {'scale': {}, 'ramp':{}, 'limit':{}}
        self.logical_dev = None

        # not kept when saving
        self.ph_dev = None
        self.ph_choice = None  # ChoiceString from pyHegel
        self.sweep = [None, None, None]  # [start, stop, npts]
        self.cache_value = None  # a variable to cache the last value read

        # sweep
        # a np.array for when the device is in a sweep (swept or output)
        # size is allocated at the beginning of the sweep
        self.values = None
        self.sw_idx = None  # SweepIdxIter object

        # monitor
        # a np.array for when the device is monitored
        self.monitor_data = None

    def getPhDev(self, basedev=False):
        if self.logical_dev is not None and not basedev:
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
            if self.nickname == ph_name:
                return nickname
            return nickname + " (" + ph_name + ")"
    
    def isLoaded(self):
        return self.ph_dev is not None
    
    def toDict(self):
        # for json file saving
        d = {}
        if self.nickname != self.ph_name:
            d['nickname'] = self.nickname
        d['ph_name'] = self.ph_name
        if self.extra_args != {}:
            d['extra_args'] = self.extra_args
        if self.logical_kwargs['ramp'] != {}:
            d['ramp'] = self.logical_kwargs['ramp']
        if self.logical_kwargs['scale'] != {}:
            d['scale'] = self.logical_kwargs['scale']
        if self.logical_kwargs['limit'] != {}:
            d['limit'] = self.logical_kwargs['limit']
        return d