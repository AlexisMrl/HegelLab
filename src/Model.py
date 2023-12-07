from pyHegel import commands as c
from pyHegel import instruments


class Model:
    # The model is the only one doing the pyHegel commands
    # except for the loading drivers

    def getDevice(self, instr, name):
        dev = getattr(instr, name)
        return dev

    def getChoices(self, dev):
        if hasattr(dev, "choices"):
            return dev.choices
        else:
            return None

    def getValue(self, dev):
        return c.get(dev)

    def setValue(self, dev, value):
        c.set(dev, value)

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


    def makeLogicalDevice(self, base_dev, kwargs):
        # kwargs = {'scale':{kw scale}, 'ramp':{kw ramp}, 'limit':{kw limit}}
        # (not dict but OrederedDict)
        # The order of creation is: 1 scale, 2 ramp, 3 limit
        limit_cls = instruments.LimitDevice
        ramp_cls = instruments.RampDevice
        scale_cls = instruments.ScalingDevice
        new_dev = base_dev
        ramp_kw = kwargs.get('ramp', {})
        if ramp_kw:
            new_dev = ramp_cls(new_dev, **ramp_kw)
            new_dev._quiet_del = True
        
        scale_kw = kwargs.get('scale', {})
        if scale_kw:
            new_dev = scale_cls(new_dev, **scale_kw)
            new_dev._quiet_del = True

        limit_kw = kwargs.get('limit', {})
        if limit_kw:
            new_dev = limit_cls(new_dev, **limit_kw)
            new_dev._quiet_del = True

        return new_dev

