# a class to inherit from when creating a custom gui for an instrument

class CustomGui():

    def load(self, nickname, cls, address, slot=None):
        # this function must return a loaded PyHegel instrument
        pass

    def config(self):
        # this function returns nothing.
        # it's called on when asking for instrument config
        # do whatever you want
        pass

    def sweep(self, gui_dev):
        # this function returns nothing.
        # it's called on when asking for instrument sweep
        # it must set the sweep attribute of gui_dev
        # gui_dev.sweep = [start, stop, npts]
        pass