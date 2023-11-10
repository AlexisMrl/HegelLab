from pyHegel import commands as c
from pyHegel import instruments

class Model():
    # The model is the only one doing the pyHegel commands
    # except for the sweep thread
    
    def loadInstrument(self, cls, addr, nickname):
        instr = cls(addr)
        instr.header.set(nickname)
        return instr

    def getDevice(self, instr, name):
        dev = getattr(instr, name)
        return dev

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