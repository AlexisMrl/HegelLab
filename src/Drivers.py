from pyHegel.gui import ScientificSpinBox
from pyHegel import instruments, instruments_base
from PyQt5 import QtGui, uic
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import (
    QWidget,
    QGridLayout,
    QLabel,
    QSpinBox,
    QPushButton,
    QFormLayout,
    QLineEdit,
    QCheckBox,
)
from widgets.WindowWidget import Window

####################
# Loading thread
####################

class LoadThread(QThread):
    # thread for loading an instrument
    loaded_signal = pyqtSignal(object)
    error_signal = pyqtSignal(object)

    def __init__(self, nickname, cls, address=None, kwargs={}):
        super(LoadThread, self).__init__()
        self.cls = cls
        self.address = address
        self.kwargs = kwargs
        self.nickname = nickname

    def _run(self):
        if self.address:
            instr = self.cls(self.address, **self.kwargs)
        else:
            instr = self.cls(**self.kwargs)
        instr.header.set(self.nickname)
        instruments_base._globaldict[self.nickname] = instr
        self.loaded_signal.emit(instr)
    
    def run(self):
        try:
            self._run()
        except Exception as e:
            self.error_signal.emit(e)

####################
# Default Driver
####################

class Default:
    # a class to inherit from when creating a custom gui for an instrument

    @staticmethod
    def load(lab, gui_instr, sig_finished):
        # load the instrument, finish by emitting sig_finished.emit(gui_instr)

        nickname = gui_instr.nickname
        ph_class = eval(gui_instr.ph_class)
        address = gui_instr.address
        kwargs = {}
        if gui_instr.slot is not None:
            kwargs['slot'] = gui_instr.slot

        thread = LoadThread(nickname, ph_class, address, kwargs)

        def success(instr):
            gui_instr.ph_instr = instr
            sig_finished.emit(gui_instr, None)
            #lab.loadGuiDevices(gui_instr)
            del gui_instr._loading_thread
        thread.loaded_signal.connect(success)
        
        def error(err):
            sig_finished.emit(gui_instr, err)
            del gui_instr._loading_thread
        thread.error_signal.connect(error)

        gui_instr._loading_thread = thread # to keep a reference to it
        thread.start()

    @staticmethod
    def sweep(lab, gui_dev, sig_finished):
        # set the sweep attribute of gui_dev
        # gui_dev.sweep = [start, stop, npts]
        # then emit sig_finished with parameters: (gui_dev, True)
        # must save its window to avoid garbage collection

        # minimal window for defining sweep start, stop, step:
        display_name = gui_dev.getDisplayName("long")
        win = Window()
        win.setWindowTitle("Setup sweep " + display_name)
        win.setWindowIcon(QtGui.QIcon("resources/favicon/favicon.png"))
        wid = QWidget()
        win.setCentralWidget(wid)
        layout = QGridLayout()
        wid.setLayout(layout)

        # widgets:
        label_start = QLabel("Start:")
        label_stop = QLabel("Stop:")
        label_npts = QLabel("# pts:")
        label_step = QLabel("Steps:")
        label_raz = QLabel("Ret. to 0:")
        spin_start = ScientificSpinBox.PyScientificSpinBox()
        spin_stop = ScientificSpinBox.PyScientificSpinBox()
        spin_npts = QSpinBox()
        spin_npts.setMaximum(1000000)
        spin_step = ScientificSpinBox.PyScientificSpinBox(buttonSymbols=2, readOnly=True)
        check_raz = QCheckBox(checked=gui_dev.raz)
        ok_button = QPushButton("Ok")

        # set values if not None:
        sweep_values = gui_dev.sweep
        if sweep_values[0] is not None:
            spin_start.setValue(sweep_values[0])
        if sweep_values[1] is not None:
            spin_stop.setValue(sweep_values[1])
        if sweep_values[2] is not None:
            spin_npts.setValue(sweep_values[2])

        # add to layout:
        layout.addWidget(label_start, 0, 0)
        layout.addWidget(label_stop, 1, 0)
        layout.addWidget(label_npts, 2, 0)
        layout.addWidget(label_step, 3, 0)
        layout.addWidget(label_raz, 4, 0)
        layout.addWidget(spin_start, 0, 1)
        layout.addWidget(spin_stop, 1, 1)
        layout.addWidget(spin_npts, 2, 1)
        layout.addWidget(spin_step, 3, 1)
        layout.addWidget(check_raz, 4, 1)
        layout.addWidget(ok_button, 5, 1)

        # connect signals:
        def updateStep():
            start, stop = spin_start.value(), spin_stop.value(),
            nbpts = spin_npts.value()
            try:
                step = (stop-start) / (nbpts-1)
                spin_step.setValue(step)
            except:
                spin_step.setSpecialValueText('nan')
        spin_start.valueChanged.connect(updateStep)
        spin_stop.valueChanged.connect(updateStep)
        spin_npts.valueChanged.connect(updateStep)
        updateStep()

        def onOk():
            gui_dev.sweep = [spin_start.value(), spin_stop.value(), spin_npts.value()]
            gui_dev.raz = check_raz.isChecked()
            sig_finished.emit(gui_dev, True)
            win.close()
        ok_button.clicked.connect(onOk)

        gui_dev._win_sweep = win
        win.show()


####################
# American Magnetics
####################

class ami430(Default):
    @staticmethod
    def load(lab, gui_instr):
        vec_nickname = gui_instr.nickname
        vec_ph_class = eval(gui_instr.ph_class)
        vec_instr_dict = gui_instr.instr_dict

        win = Window()
        win.setWindowIcon(QtGui.QIcon("resources/load.svg"))
        gui_instr._win = win # avoid garbage collector
        title = "Setup AMI430 vector - " + str(vec_nickname)
        win.setWindowTitle(title)
        win.setFixedWidth(400)
        wid = QWidget()
        win.setCentralWidget(wid)
        form = QFormLayout()
        wid.setLayout(form)

        le_x, le_y, le_z = QLineEdit(), QLineEdit(), QLineEdit()
        le_x.setText(vec_instr_dict.get('address_x'))
        le_y.setText(vec_instr_dict.get('address_y'))
        le_z.setText(vec_instr_dict.get('address_z'))
        form.addRow("Magnet X", le_x)
        form.addRow("Magnet Y", le_y)
        form.addRow("Magnet Z", le_z)
        lbl_load = QLabel("0/3")
        btn_load_all = QPushButton("Load magnets")
        form.addRow(lbl_load, btn_load_all)

        # signal when vector is loaded
        def loaded(instr):
            gui_instr.ph_instr = instr
            del gui_instr._vec_loading_thread
            win.close()
            #lab.loadGuiDevices(gui_instr)

        # signal when an axis is loaded
        gui_instr.magnets = {'magnet_x':None, 'magnet_y':None, 'magnet_z':None}
        def loaded_ax(instr, ax):
            gui_instr.magnets[ax] = instr
            lbl_load.setText(str(int(lbl_load.text()[0])+1) + "/3")
            if None not in gui_instr.magnets.values():
                del gui_instr._loading_threads
                # create and start the vec_loading thread
                thread_vec = LoadThread(vec_nickname, vec_ph_class, kwargs=gui_instr.magnets)
                thread_vec.loaded_signal.connect(loaded)
                gui_instr._vec_loading_thread = thread_vec
                thread_vec.start()

        def onLoadAll():
            addresses = [le_x.text(), le_y.text(), le_z.text()]
            axes = ['magnet_x', 'magnet_y', 'magnet_z']
            gui_instr._loading_threads = []
            for addr, ax in zip(addresses, axes):
                nickname = ax
                # create and start axis_loading thread
                th = LoadThread(nickname, instruments.AmericanMagnetics_model430, addr)
                th.loaded_signal.connect(lambda instr, ax=ax: loaded_ax(instr, ax))
                th.error_signal.connect(lambda e: lab.loadGuiInstrumentError(gui_instr, e))
                gui_instr._loading_threads.append(th)
                th.start()
                btn_load_all.setText('Loading...')
                btn_load_all.setEnabled(False)

        btn_load_all.clicked.connect(onLoadAll)

        win.focus()

    @staticmethod
    def sweep(lab, gui_dev):
        if gui_dev.ph_name != 'ramp_to_index':
            Default.sweep(lab, gui_dev)
        # set the sweep attribute of gui_dev
        # to gui_dev.sweep = [start, stop, npts]
        vec = gui_dev.parent

        win = Window()
        uic.loadUi("ui/DriverMagnet.ui", win)
        win.setWindowIcon(QtGui.QIcon("resources/config.svg"))
        win.setWindowTitle("Setup ami")

        # no spherical for now
        win.lbl_coord.setVisible(False); win.cb_coord.setVisible(False)

        # utils function for path update first vector / last vector
        def _plot_update(update_first=False, update_last=False):
            if update_last:
                end_point = (win.coord1_e.value(), win.coord2_e.value(), win.coord3_e.value())
                win.plot.set_last_vector(end_point)
            if update_first:
                start_point = (win.coord1.value(), win.coord2.value(), win.coord3.value())
                win.plot.set_first_vector(start_point)
        def _update_last():
            _plot_update(update_last=True)
        def _update_first():
            _plot_update(update_first=True)

        win.coord1.valueChanged.connect(_update_first)
        win.coord2.valueChanged.connect(_update_first)
        win.coord3.valueChanged.connect(_update_first)
        win.coord1_e.valueChanged.connect(_update_last)
        win.coord2_e.valueChanged.connect(_update_last)
        win.coord3_e.valueChanged.connect(_update_last)

        win.cb_sphere.stateChanged.connect(win.plot.showSphere)
        win.cb_axes.stateChanged.connect(win.plot.showAxes)

        def _calculate_sequence():
            first = win.plot.first_vector
            last = win.plot.last_vector
            nbpts = win.nbpts.value()
            shortest = win.cb_shortest.checkState()
            points = gui_dev.parent.ph_instr.linspace_plane(first, last, nbpts, shortest)
            win.plot.set_points(points)
        win.drawPath.clicked.connect(_calculate_sequence)
        def _save_sequence():
            _calculate_sequence()
            points = win.plot.all_points
            dev_sequence = gui_dev.parent.getGuiDevice('sequence')
            lab.setValue(dev_sequence, points.T)
        win.savePath.clicked.connect(_save_sequence)



        gui_dev._win_sweep = win
        win.focus()


        #ok_button.clicked.connect(onOk)
        #ok_button.clicked.connect(
        #    lambda: lab.setSweepValues(
        #        gui_dev,
        #        spin_start.value(),
        #        spin_stop.value(),
        #        spin_npts.value(),
        #    )
        #)

####################
# Virtual Gates
####################

class VirtualGates(Default):

    @staticmethod
    def load(gui_instr, lab):
        win = Window()
        uic.loadUi("ui/DriverVirtualGates.ui", win)
        

    @staticmethod
    def sweep(gui_dev, lab):
        Default.sweep(gui_dev)
