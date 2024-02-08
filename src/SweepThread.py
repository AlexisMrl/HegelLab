from PyQt5.QtCore import QThread

from pyHegel.commands import sweep_multi
import pyHegel.commands as c
import numpy as np


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
    



class VideoModeThread(QThread):
    # execute a sweep in loop
    # it does not save the data in a file but in the provided array.
    def __init__(self, sig_frame_done):
        super().__init__()
        self.sig_frame_done = sig_frame_done
        self.running = False
        self.new_bound = True
        
        self.resetIdxs_fn = None
        
        self.ph_dev_x, self.ph_dev_y = None, None
        self.start_, self.stop, self.nbpts = [], [], []
        self.ax_x, self.ax_y = None, None
        self.ph_out_dev = None
        self.gui_out_dev = None

    def run(self):
        import time
        self.running = True
        while True:
            if not self.running:
                # sleep pyqt thread:
                self.sleep(1)
                continue

            # remake axes if needed:
            if self.new_bound:
                self.makeAxes()
                self.new_bound = False

            start_time = time.time()
            print("frame start")
            self.sweep()
            finish_time = time.time()
            frame_time = finish_time - start_time
            print("frame done in ", frame_time)

            # limit to 10 fps:
            if frame_time < 0.1:
                time.sleep(0.1 - (frame_time))

            self.sig_frame_done.emit(self.gui_out_dev)
            
    
    def sweep(self):
        for val_x in self.ax_x:
            c.set(self.ph_dev_x, val_x)
            for val_y in self.ax_y:
                c.set(self.ph_dev_y, val_y)
                val_out = c.get(self.ph_out_dev)
                self.gui_out_dev.values[self.gui_out_dev.sw_idx.current()] = val_out
        self.gui_out_dev.sw_idx.reset()
    
    def makeAxes(self):
        self.ax_x = np.linspace(self.start_[0], self.stop[0], self.nbpts[0])
        self.ax_y = np.linspace(self.start_[1], self.stop[1], self.nbpts[1])
        self.resetIdxs_fn(self.start_, self.stop, self.nbpts)

    def initDevs(self, gui_sw_devs, gui_out_devs, start, stop, nbpts):
        self.ph_dev_x = gui_sw_devs[0].getPhDev()
        self.ph_dev_y = gui_sw_devs[1].getPhDev()
        self.start_, self.stop, self.nbpts = start, stop, nbpts
        x_step = (stop[0] - start[0]) / (nbpts[0] - 1)
        y_step = (stop[1] - start[1]) / (nbpts[1] - 1)
        self.step = [x_step, y_step]
        print("ax_x", self.ax_x)
        print("ax_y", self.ax_y)
        print("start", start)
        print("stop", stop)
        print("nbpts", nbpts)
        self.gui_out_dev = gui_out_devs[0]
        self.ph_out_dev = gui_out_devs[0].getPhDev()
    
    