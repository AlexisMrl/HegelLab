from PyQt5.QtCore import QThread, pyqtSignal
import traceback

class SweepStatusObject():
    # class to pass sweep status
    def __init__(self):
        self.iteration = [None, None] # i out of n
        self.time = None # epoch
        self.sw_devs = None # list of swept gui_devs
        self.sw_devs_vals = None
        self.out_devs = None # list of out gui_devs
        self.out_devs_vals = None

        self.datas = None # dict of all datas, for debug

class SweepThread(QThread):
    progress_signal = pyqtSignal(SweepStatusObject) # (SweepStatusObject)
    error_signal = pyqtSignal(str, str) # (Exception)
    finished_signal = pyqtSignal()
    
    # The sweep thread:
    # runs the sweep and calls 'after_get' every point
    # sending a SweepStatusObject to the main thread.


    def __init__(self, sweep_multi_fn, loop_control):
        super(SweepThread, self).__init__()
        self.sweep_multi_fn = sweep_multi_fn
        self.loop_control = loop_control

        self.sweep_status = SweepStatusObject()
    
    def initSweepKwargs(self, sweep_multi_kwargs):
        self.fn_kwargs = sweep_multi_kwargs
        self.fn_kwargs["loop_control"] = self.loop_control
        self.fn_kwargs["exec_after"] = self.after_get
        self.fn_kwargs["graph"] = False
        
    def initSweepStatus(self, gui_sw_devs, gui_out_devs):
        self.sweep_status.sw_devs = gui_sw_devs
        self.sweep_status.out_devs = gui_out_devs
    
    def run(self):
        try:
            self.sweep_multi_fn(**self.fn_kwargs) # THE SWEEP
        except Exception as e:
            tb_str = ''.join(traceback.format_tb(e.__traceback__))
            self.error_signal.emit(type(e).__name__, tb_str)
        finally:
            self.finished_signal.emit()

    def after_get(self, datas):
        # exec between set and get
        # datas is a dict detailed in pyHegel.commands._Sweep

        # update self.sweep_status
        self.sweep_status.sw_devs_vals = datas["ask_vals"]
        self.sweep_status.out_devs_vals = datas["read_vals"]
        self.sweep_status.time = datas["saved_vals"][-1]
        self.sweep_status.iteration[0] = datas["iter_part"]
        self.sweep_status.iteration[1] = datas["iter_total"] # no need, but for consistency 
        self.sweep_status.datas = datas

        # emit self.progress
        self.progress_signal.emit(self.sweep_status)
        print(self.loop_control.abort_completed)