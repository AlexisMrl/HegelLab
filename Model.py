from pyHegel import commands as c
from pyHegel import instruments

class Model():
    # The model is the only one knowing and doing the pyHegel commands
    # and dealing with the instruments.
    

    def loadInstrument(self, cls, addr):
        return cls(addr)

    def unloadInstrument(self, instr):
        del instr 

    def getDevices(self, instr, *names):
        # get the devices of an instrument by their names
        # return a dictionary {name: device}
        devs = {}
        for name in names:
            devs[name] = getattr(instr, name)
        return devs

    def getValue(self, dev):
        return c.get(dev)