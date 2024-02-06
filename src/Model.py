from pyHegel import commands as c
from pyHegel import instruments

from PyQt5.QtCore import QThread, pyqtSignal
class SetThread(QThread):
    # thread for set commands
    finished_signal = pyqtSignal(object)

    def __init__(self, dev, stop_fn):
        super().__init__()
        self.dev = dev
        self.stopping_function = stop_fn
        self.val = None
    
    def stop(self):
        self.stopping_function()
    
    def run(self):
        try:
            c.set(self.dev, self.value)
        except Exception as e:
            self.finished_signal.emit(e)
        else:
            self.finished_signal.emit(None)

class Model:
    # The model is the only one doing the pyHegel commands
    # except for the loading drivers

    def __init__(self, lab):
        self.lab = lab

    def getInstrumentList(self):
        # NOT USED, NOT FINISHED
        # return a string list of instrument classes
        # the criteria for being an instrument is:
        #    - not starting with '_'
        #    - not being in blacklist
        #    - not being BaseInstrument
        #    - inheriting from BaseInstrument
        ret = []
        blacklist = ['instrument_base']
        for instr_str in dir(instruments):
            if instr_str.startswith("_") and instr_str not in blacklist:
                continue
            instr = getattr(instruments, instr_str)
            if not isinstance(instr, type):
                continue
            if instr is instruments.BaseInstrument:
                continue
            if not issubclass(instr, instruments.BaseInstrument):
                continue
            ret.append(instr)
        return ret

    def getDevicesList(self, instr, cls_only=False):
        # return a string list of device name
        # the criteria for being a device is:
        #    - having a get attr
        #    - having a set attr
        #    - not starting with '_'
        dev_list = []
        for dev_str in dir(instr):
            if dev_str.startswith('_'):
                continue
            dev = getattr(instr, dev_str)
            if hasattr(dev, 'get') and hasattr(dev, 'set'):
                dev_list.append(dev_str)
        return dev_list

    def getDevice(self, instr, name):
        dev = getattr(instr, name)
        return dev

    def getChoices(self, dev):
        # return possible choices to a list
        if hasattr(dev, "choices"):
            choices = dev.choices
            list_choices = None
            try: list_choices = list(choices)
            except: pass
            try: list_choices = list(choices.dict.values())
            except: pass
            return list_choices
        else:
            return None
    
    def getType(self, dev):
        # return the type of a device:
        # set, get or set/get:
        settable = True if dev._setdev_p is not None else False
        gettable = True if dev._getdev_p is not None else False
        output_type = None
        return settable, gettable, output_type
    
    def getFormatMulti(self, dev):
        return dev.getformat().get('multi', None) if hasattr(dev, 'getformat') else None

    def initLoopControl(self):
        return c.Loop_Control()

    def getValue(self, dev, fn_after=None):
        return c.get(dev)
        #thread = getThread(dev)
        #setattr(dev, '_HLgetThread', thread)
        #def onFinished(value):
            #delattr(dev, '_HLgetThread')
            #if fn_after: fn_after(value)
        #thread.finished_signal.connect(onFinished)
        #thread.error_signal.connect(self.lab.getValueError)
        #thread.start()

    def _initSetThread(self, gui_dev, dev, stop_fn):
        # called by makeLogicalDevice
        # every device has a set_thread
        thread = SetThread(dev, stop_fn)
        def onFinished(exception):
            self.lab.sig_setValueFinished.emit(gui_dev, exception)
        thread.finished_signal.connect(onFinished)
        return thread
    
    def setValue(self, gui_dev, value):
        # start set thread
        thread = gui_dev.set_thread
        thread.stop()
        thread.wait()
        thread.value = value
        thread.start()

    def makeLogicalDevice(self, gui_dev, gui_dev_kwargs, instrument):
        # kwargs = {'scale':{kw scale}, 'ramp':{kw ramp}, 'limit':{kw limit}}
        # (not dict but OrederedDict)
        # The order of creation is: 1 scale, 2 ramp, 3 limit

        basedev = gui_dev.getPhDev(basedev=True)

        limit_cls = instruments.LimitDevice
        ramp_cls = instruments.RampDevice
        scale_cls = instruments.ScalingDevice

        new_dev = basedev
        # we define a stop function, called before setting a new value
        def stop_fn(): None if not isinstance(basedev, instruments.RampDevice) else basedev.stop()
    
        ramp_kw = gui_dev_kwargs.get('ramp', {}).copy()
        scale_kw = gui_dev_kwargs.get('scale', {}).copy()
        limit_kw = gui_dev_kwargs.get('limit', {}).copy()

        if ramp_kw: #RAMP
            new_dev = ramp_cls(new_dev, **ramp_kw)
            new_dev._quiet_del = True
            stop_fn = new_dev.stop
        else:
            gui_dev.stop_ramping_function = lambda: None
        if scale_kw: #SCALE
            scale_kw["scale_factor"] = scale_kw.pop("factor")
            scale_kw["only_val"] = True
            new_dev = scale_cls(new_dev, **scale_kw)
            new_dev._invert_trans = True
            new_dev._quiet_del = True
        if limit_kw: #LIMIT
            new_dev = limit_cls(new_dev, **limit_kw)
            new_dev._quiet_del = True
        
        # init set thread:
        thread = self._initSetThread(gui_dev, new_dev, stop_fn)
        gui_dev.set_thread = thread

        if new_dev == basedev:
            return None
        
        # make new dev an actual device of instr
        basedev_dev = basedev[0] if isinstance(basedev, tuple) else basedev
        new_dev_name = f"_{basedev_dev.name}"
        if hasattr(instrument, new_dev_name):
            delattr(instrument, new_dev_name)
        setattr(instrument, f"_{basedev_dev.name}", new_dev)
        instrument._create_devs_helper()

        return new_dev

