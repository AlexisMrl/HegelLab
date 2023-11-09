from PyQt5.QtCore import QThread, pyqtSignal
import traceback

class SweepStatusObject():
    # class to store and pass sweep status
    def __init__(self):
        self.iteration = 0
        self.set_vals = None
        self.get_vals = None

class SweepThread(QThread):
    progress_signal = pyqtSignal(SweepStatusObject) # (SweepStatusObject)
    error_signal = pyqtSignal(str, str) # (Exception)
    finished_signal = pyqtSignal()


    def __init__(self, sw_fn):
        super(SweepThread, self).__init__()
        self.sw_fn = sw_fn

        self.sw_status = SweepStatusObject()
    
    def setSweepKwargs(self, sw_kwargs):
        self.sw_kwargs = sw_kwargs
        self.sw_kwargs["exec_after"] = self.after_get
        self.sw_kwargs["graph"] = False

    def run(self):
        try:
            self.sw_fn(**self.sw_kwargs)
        except Exception as e:
            tb_str = ''.join(traceback.format_tb(e.__traceback__))
            self.error_signal.emit(type(e).__name__, tb_str)
        finally:
            self.finished_signal.emit()

    def after_get(self, datas):
        # exec between set and get
        # datas is a dict detailed in pyHegel.commands._Sweep

        # update self.sweep_status
        self.sw_status.set_vals = datas["ask_vals"]
        self.sw_status.get_vals = datas["read_vals"]

        # emit self.progress
        self.progress_signal.emit(self.sw_status)