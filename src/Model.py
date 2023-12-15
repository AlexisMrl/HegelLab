from pyHegel import commands as c
from pyHegel import instruments

from PyQt5.QtCore import QThread, pyqtSignal
class setThread(QThread):
    # thread for set commands
    finished_signal = pyqtSignal()
    error_signal = pyqtSignal(object)
    def __init__(self, dev, value):
        super().__init__()
        self.dev = dev
        self.value = value
    
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
    
    setThreads = []
    
    def close(self):
        for thread in self.setThreads:
            thread.terminate()

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

    def getValue(self, dev):
        return c.get(dev)

    def setValue(self, dev, value):
        #c.set(dev, value)
        thread = setThread(dev, value)
        self.setThreads.append(thread)
        def onFinished():
            self.setThreads.remove(thread)
        thread.error_signal.connect(self.lab._setValueError)
        thread.finished_signal.connect(onFinished)
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

    def makeLogicalDevice(self, basedev, gui_dev_kwargs, instrument):
        # kwargs = {'scale':{kw scale}, 'ramp':{kw ramp}, 'limit':{kw limit}}
        # (not dict but OrederedDict)
        # The order of creation is: 1 scale, 2 ramp, 3 limit
        limit_cls = instruments.LimitDevice
        ramp_cls = instruments.RampDevice
        scale_cls = instruments.ScalingDevice

        new_dev = basedev
        
        ramp_kw = gui_dev_kwargs.get('ramp', {}).copy()
        scale_kw = gui_dev_kwargs.get('scale', {}).copy()
        limit_kw = gui_dev_kwargs.get('limit', {}).copy()

        if ramp_kw:
            new_dev = ramp_cls(new_dev, **ramp_kw)
            new_dev._quiet_del = True
        
        if scale_kw:
            scale_kw["scale_factor"] = scale_kw.pop("factor")
            scale_kw["only_val"] = True
            new_dev = scale_cls(new_dev, **scale_kw)
            new_dev._invert_trans = True
            new_dev._quiet_del = True

        if limit_kw:
            new_dev = limit_cls(new_dev, **limit_kw)
            new_dev._quiet_del = True
            
        if new_dev == basedev:
            return None
        
        new_dev_name = f"wrap_{basedev.name}"
        if hasattr(instrument, new_dev_name):
            delattr(instrument, new_dev_name)
        setattr(instrument, f"wrap_{basedev.name}", new_dev)
        instrument._create_devs_helper()

        return new_dev

