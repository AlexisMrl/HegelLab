from pyHegel import commands as c
from pyHegel import instruments

from PyQt5.QtCore import QThread, pyqtSignal
class setThread(QThread):
    # thread for set commands
    finished_signal = pyqtSignal()
    error_signal = pyqtSignal(object)

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
            self.error_signal.emit(e)
        self.finished_signal.emit()

class Model:
    # The model is the only one doing the pyHegel commands
    # except for the loading drivers

    def __init__(self, lab):
        self.lab = lab

    def getDevice(self, instr, name):
        dev = getattr(instr, name)
        return dev
    
    def getDevicesList(self, instr):
        # return a string list of device name
        # the *very loose* criteria for being a device is:
        #    - having a get attr
        #    - having a set attr
        #    - does not start with '_'
        dev_list = []
        for dev_str in dir(instr):
            if dev_str.startswith('_'):
                continue
            dev = getattr(instr, dev_str)
            if hasattr(dev, 'get') and hasattr(dev, 'set'):
                dev_list.append(dev_str)
        return dev_list


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

    def setValue(self, gui_dev, value):
        #c.set(dev, value)
        thread = gui_dev.set_thread
        thread.stop()
        thread.wait()
        thread.value = value
        thread.start()

    def startSweep(self, **kwargs):
        return c.sweep_multi(**kwargs)

    def initLoopControl(self):
        return c.Loop_Control()

    def devType(self, dev):
        # check the type of a device:
        # set, get or set/get:
        settable = True if dev._setdev_p is not None else False
        gettable = True if dev._getdev_p is not None else False
        return (settable, gettable)
    
    def _initSetThread(self, dev, stop_fn):
        thread = setThread(dev, stop_fn)
        #thread.finished_signal.connect(onFinished)
        thread.error_signal.connect(self.lab.setValueError)
        return thread
        
    def makeLogicalDevice(self, gui_dev, gui_dev_kwargs, instrument):
        # kwargs = {'scale':{kw scale}, 'ramp':{kw ramp}, 'limit':{kw limit}}
        # (not dict but OrederedDict)
        # The order of creation is: 1 scale, 2 ramp, 3 limit

        basedev = gui_dev.getPhDev(basedev=True)

        limit_cls = instruments.LimitDevice
        ramp_cls = instruments.RampDevice
        scale_cls = instruments.ScalingDevice

        new_dev = basedev
        stop_fn = lambda: None if not isinstance(basedev, instruments.RampDevice) else basedev.stop
    
        
        
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
        thread = self._initSetThread(new_dev, stop_fn)
        gui_dev.set_thread = thread

        if new_dev == basedev:
            return None
        
        # make new dev an actual device of instr
        basedev_dev = basedev[0] if isinstance(basedev, tuple) else basedev
        new_dev_name = f"_wrap_{basedev_dev.name}"
        if hasattr(instrument, new_dev_name):
            delattr(instrument, new_dev_name)
        setattr(instrument, f"_wrap_{basedev_dev.name}", new_dev)
        instrument._create_devs_helper()

        return new_dev

