from PyQt5.QtCore import QThread, pyqtSignal
import traceback

from pyHegel.commands import sweep_multi


class SweepStatus:
    # object emitted in every progress signals
    def __init__(self):
        self.start_time = None  # time.time() at the beginning of the sweep
        self.iteration = [None, None]  # i out of n
        self.sw_devs = None  # list of swept gui_devs
        self.out_devs = None  # list of out gui_devs
        self.datas = None  # full dict of datas from the sweep


class SweepThread(QThread):
    # The sweep thread:
    # runs the sweep and calls 'after_get' every point
    # sending a SweepStatusObject to the main thread.

    def __init__(self, loop_control, sig_progress, sig_error, sig_finished):
        super(SweepThread, self).__init__()
        self.loop_control = loop_control
        self.sig_progress = sig_progress
        self.sig_error = sig_error
        self.sig_finished = sig_finished
        self.enable_live = True

        self.fn_kwargs = None
        self.status = SweepStatus()
        self.raz_sw_devs = lambda: None

    def initSweepKwargs(self, sweep_multi_kwargs):
        self.fn_kwargs = sweep_multi_kwargs
        self.fn_kwargs["loop_control"] = self.loop_control
        self.fn_kwargs["exec_after"] = self.after_get
        self.fn_kwargs["graph"] = False

    def initSweepStatus(self, gui_sw_devs, gui_out_devs, start_time):
        self.status.sw_devs = gui_sw_devs
        self.status.out_devs = gui_out_devs
        self.status.start_time = start_time
        self.enable_live = len(gui_sw_devs) <= 2

    def run(self):
        try:
            sweep_multi(**self.fn_kwargs)  # THE SWEEP
        except Exception as e:
            self.sig_error.emit(e)
        finally:
            self.raz_sw_devs()
            self.sig_finished.emit()

    def after_get(self, datas):
        # exec between set and get
        # datas is a dict detailed in pyHegel.commands._Sweep

        self.status.iteration[0] = datas["iter_part"]
        self.status.iteration[1] = datas["iter_total"] 
        self.status.datas = datas

        # this used to be done in the main thread,
        # but it led to a bug where it sometimes
        # missed some points
        if self.enable_live:
            for out_dev, val in zip(self.status.out_devs, datas["read_vals"]):
                out_dev.values[out_dev.sw_idx.current()] = val
    
        # for sw_dev, val in zip(self.status.sw_devs,
        # datas["ask_vals"]):
        # sw_dev.values[*out_dev.idx.current()] = val

        # emit self.progress
        self.sig_progress.emit(self.status)