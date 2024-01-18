import numpy as np

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

        self.instr_dict = {}  # the dict from json file (as is (not updated!)). Used ONLY for driver with extra args
        self.ph_instr = None
        self.loading = False # True when the instr is loading
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
        d = {'ph_class': self.ph_class}
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

    def toPyHegelScript(self):
        s = self.nickname + " = "
        s += self.ph_class + "("
        s += '"' + self.address + '"'
        s += f", slot={self.slot}" if self.slot is not None else ""
        s += ")"
        for gui_dev in self.gui_devices:
            s += gui_dev.toPyHegelScript()
        return s
    


class GuiDevice:
    # class attached to every item that represent a dev

    def __init__(self, nickname, ph_name, extra_args, parent):
        self.nickname = nickname
        self.ph_name = ph_name
        self.extra_args = extra_args # dict of kwargs for tuple devices
        self.parent = parent
        self.type = [None, None, None]  # (settable, gettable, output_type) = (T/F, T/F, None/bool)
        self.multi = None # a tuple giving the shape of return when get (None -> one val only)
        
        self.logical_kwargs = {'scale': {}, 'ramp':{}, 'limit':{}}
        self.logical_dev = None # limit(ramp(scale())))

        # not kept when saving
        self.ph_dev = None
        self.ph_choice = None  # ChoiceString from pyHegel
        self.sweep = [None, None, None]  # [start, stop, npts]
        self.raz = False
        self.cache_value = None  # a variable to cache the last value read
        self.status = {'sweep':False, 'out':False, 'log':False, 'monitor':False}

        # sweep
        # a np.array for when the device is in a sweep (swept or output)
        # size is allocated at the beginning of the sweep
        self.values = None
        self.sw_idx = None  # SweepIdxIter object

        # monitor
        # a np.array for when the device is monitored
        self.monitor_data = None

        # set thread
        # keep the thread use to set ph_dev value
        self.set_thread = None

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
    
    def getTypeToStr(self):
        ret = {(True, True): "set/get", (True, False): "set",
               (False, True): "get", (False, False): "?", (None, None): "?",}[tuple(self.type[:2])]
        ret += {bool: " (bool)", float: " (float)", np.array: " (np.array)", None: ""}[self.type[2]]
        return ret
    
    def getCacheValueToStr(self):
        if self.cache_value is None:
            return ''
        if self.type[2] is bool:
            try:
                str_val = str(bool(self.cache_value))
                return str_val
            except: pass
        if isinstance(self.cache_value, np.ndarray):
            with np.printoptions(threshold=5):
                return str(self.cache_value)
                #return np.array_str(self.cache_value, max_line_width=9999)
        else:
            return str(self.cache_value)

    
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
        if self.type[2] is bool:
            d['type'] = {'output': 'bool'}
        return d

    def toPyHegelScript(self):
        # write a device only if:
        #  - it has a nickname != ph_name
        #  - it has extra_args
        #  - it has a ramp/scale/limit
        #  or a combination

        s = ""

        if self.nickname == self.ph_name and \
           self.extra_args == {} and \
           self.logical_kwargs == {'scale': {}, 'ramp':{}, 'limit':{}}:
            return s

        s += "\n"
        s += self.nickname + " = "

        if self.extra_args == {} :
            s += self.parent.nickname + "." + self.ph_name
        else:
            s += f"({self.parent.nickname}.{self.ph_name}, {self.extra_args})"

        scale_kw = self.logical_kwargs['scale']
        if scale_kw != {}:
            scale_kw["only_val"] = True
            scale_kw["invert_trans"] = True
            scale_str = ", ".join([f"{k}={v}" for k, v in scale_kw.items()])
            s += f"\n{self.nickname} = instruments.ScalingDevice({self.nickname}, {scale_str})"

        ramp_kw = self.logical_kwargs['ramp']
        if ramp_kw != {}:
            ramp_str = ", ".join([f"{k}={v}" for k, v in ramp_kw.items()])
            s += f"\n{self.nickname} = instruments.RampDevice({self.nickname}, {ramp_str})"

        limit_kw = self.logical_kwargs['limit']
        if limit_kw != {}:
            limit_str = ", ".join([f"{k}={v}" for k, v in limit_kw.items()])
            s += f"\n{self.nickname} = instruments.LimitDevice({self.nickname}, {limit_str})"
            
        return s

