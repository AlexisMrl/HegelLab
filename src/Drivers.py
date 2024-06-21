from pyHegel.gui import ScientificSpinBox
from pyHegel import instruments, instruments_base
from PyQt5 import QtGui, uic
from PyQt5.QtCore import QThread, pyqtSignal, QTimer
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
from src.GuiInstrument import GuiInstrument, GuiDevice

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
        # load the instrument
        timer = QTimer()
        timer.setSingleShot(True)
        timer.timeout.connect(self.abort)
        timer.start(60000) # in ms

        if self.address:
            instr = self.cls(self.address, **self.kwargs)
        else:
            instr = self.cls(**self.kwargs)
        instr.header.set(self.nickname)
        instruments_base._globaldict[self.nickname] = instr
        self.loaded_signal.emit(instr)
    
    def abort(self):
        self.error_signal.emit(Exception("Timeout reached (60s)"))
    
    def run(self):
        try:
            self._run()
        except Exception as e:
            self.error_signal.emit(e)
            self.quit()

####################
# Default Driver
####################

class Default:
    # a class to inherit from when creating a custom gui for an instrument

    @staticmethod
    def load(lab, gui_instr, onFinished):
        # load the instrument, finish by calling
        # either onFinished(gui_instr, None) or onFinished(gui_instr, err)

        nickname = gui_instr.nickname
        ph_class = eval(gui_instr.ph_class)
        address = gui_instr.address
        kwargs = {}
        if gui_instr.slot is not None:
            kwargs['slot'] = gui_instr.slot

        thread = LoadThread(nickname, ph_class, address, kwargs)

        def success(instr):
            gui_instr.ph_instr = instr
            onFinished(gui_instr, None)
            gui_instr._loading_thread = None
        thread.loaded_signal.connect(success)
        
        def error(err):
            onFinished(gui_instr, err)
            gui_instr._loading_thread = None
        thread.error_signal.connect(error)

        if gui_instr._loading_thread:
            gui_instr._loading_thread.stop()
        gui_instr._loading_thread = thread # to keep a reference to it
        thread.start()

    @staticmethod
    def sweepWindow(lab, gui_dev, sig_finished):
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
        spin_start.setFocus(True)
        win.show()


####################
# American Magnetics
####################

class ami430(Default):
    @staticmethod
    def makeWindow(gui_instr):
        win = Window()
        win.setWindowIcon(QtGui.QIcon("resources/load.svg"))
        gui_instr._win = win # avoid garbage collector
        title = "Setup AMI430 vector - " + str(gui_instr.nickname)
        win.setWindowTitle(title)
        win.setFixedWidth(400)
        wid = QWidget()
        win.setCentralWidget(wid)
        form = QFormLayout()
        wid.setLayout(form)

        win.le_x, win.le_y, win.le_z = QLineEdit(), QLineEdit(), QLineEdit()
        win.le_x.setText(gui_instr.instr_dict.get('address_x'))
        win.le_y.setText(gui_instr.instr_dict.get('address_y'))
        win.le_z.setText(gui_instr.instr_dict.get('address_z'))
        form.addRow("Magnet X", win.le_x)
        form.addRow("Magnet Y", win.le_y)
        form.addRow("Magnet Z", win.le_z)
        win.lbl_status = QLabel("0/3")
        win.btn_load_all = QPushButton("Load magnets")
        form.addRow(win.lbl_status, win.btn_load_all)
        
        return win

    @staticmethod
    def load(lab, gui_vec_instr, onFinished):
        win = ami430.makeWindow(gui_vec_instr)

        # treat axes as standalone gui_instr and load them with Default.load
        gui_instr_x = GuiInstrument('magnet_x', 'instruments.AmericanMagnetics_model430', 'Drivers.Default', win.le_x.text())
        gui_instr_y = GuiInstrument('magnet_y', 'instruments.AmericanMagnetics_model430', 'Drivers.Default', win.le_y.text())
        gui_instr_z = GuiInstrument('magnet_z', 'instruments.AmericanMagnetics_model430', 'Drivers.Default', win.le_z.text())

        def onLoadAll():
            win.btn_load_all.setText('Loading...')
            win.btn_load_all.setEnabled(False)
            for gui_instr in [gui_instr_x, gui_instr_y, gui_instr_z]:
                Default.load(lab, gui_instr, onAxisLoadFinished)
        win.btn_load_all.clicked.connect(onLoadAll)

        def onAxisLoadFinished(gui_instr_ax, err):
            if err:
                onFinished(gui_vec_instr, err)
            win.lbl_status.setText(str(int(win.lbl_status.text()[0])+1) + "/3")
            if win.lbl_status.text()[0] == '3':
                kwargs = {'magnet_x':gui_instr_x.ph_instr, 'magnet_y':gui_instr_y.ph_instr, 'magnet_z':gui_instr_z.ph_instr}
                Default.load(lab, gui_vec_instr, lab.loadInstrumentFinished, kwargs)
                win.close()

        win.focus()
        win.btn_load_all.setFocus(True)

    @staticmethod
    def sweepWindow(lab, gui_dev, sig_finished):
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
            try:
                points = gui_dev.parent.ph_instr.linspace_plane(first, last, nbpts, shortest)
            except Exception as e:
                lab._popErrorC("Error", "Error while calculating sequence", str(e))
            else:
                win.plot.set_points(points)
        win.drawPath.clicked.connect(_calculate_sequence)
        def _save_sequence():
            _calculate_sequence()
            points = win.plot.all_points
            dev_sequence = gui_dev.parent.getGuiDevice('sequence')
            lab.setValue(dev_sequence, points.T)
            gui_dev.sweep = [0, len(points.T)-1, len(points.T)]
            sig_finished.emit(gui_dev, True)
            win.close()
        win.savePath.clicked.connect(_save_sequence)

        gui_dev._win_sweep = win
        win.focus()


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
