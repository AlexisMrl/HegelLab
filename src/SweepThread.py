from PyQt5.QtCore import QThread, pyqtSignal
import traceback

class CurrentSweep():
    def __init__(self):
        self.start_time = None # time.time() at the beginning of the sweep
        self.iteration = [None, None] # i out of n
        self.sw_devs = None # list of swept gui_devs
        self.out_devs = None # list of out gui_devs
        self.datas = None # full dict of datas from the sweep
    
class SweepThread(QThread):
    progress_signal = pyqtSignal(CurrentSweep) # (CurrentSweep)
    error_signal = pyqtSignal(str, str) # (Exception)
    finished_signal = pyqtSignal()
    
    # The sweep thread:
    # runs the sweep and calls 'after_get' every point
    # sending a SweepStatusObject to the main thread.

    def __init__(self, sweep_multi_fn, loop_control):
        super(SweepThread, self).__init__()
        self.sweep_multi_fn = sweep_multi_fn
        self.loop_control = loop_control

        self.current_sweep = CurrentSweep()
    
    def initSweepKwargs(self, sweep_multi_kwargs):
        self.fn_kwargs = sweep_multi_kwargs
        self.fn_kwargs["loop_control"] = self.loop_control
        self.fn_kwargs["exec_after"] = self.after_get
        self.fn_kwargs["graph"] = False
        
    def initCurrentSweep(self, gui_sw_devs, gui_out_devs, start_time):
        self.current_sweep.sw_devs = gui_sw_devs
        self.current_sweep.out_devs = gui_out_devs
        self.current_sweep.start_time = start_time
    
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

        self.current_sweep.iteration[0] = datas["iter_part"]
        self.current_sweep.iteration[1] = datas["iter_total"] # no need, but for consistency 
        self.current_sweep.datas = datas
        
        # this used to be done in the main thread,
        # but it led to a bug where it sometimes
        # missed some points
        i = datas["iter_part"]-1
        for out_dev, val in zip(self.current_sweep.out_devs,
                                datas["read_vals"]):
            out_dev.values[i] = val

        for sw_dev, val in zip(self.current_sweep.sw_devs,
                               datas["ask_vals"]):
            sw_dev.values[i] = val

        # emit self.progress
        self.progress_signal.emit(self.current_sweep)
    
    def resetStartTime(self, time):
        self.current_sweep.start_time = time