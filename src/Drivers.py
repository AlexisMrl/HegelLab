from pyHegel import commands as ca
from pyHegel import instruments

from PyQt5 import QtGui
from PyQt5.QtWidgets import QMainWindow, QWidget, QGridLayout, \
                            QLabel, QSpinBox, QPushButton, \
                            QFormLayout, QLineEdit, QDialog
from pyHegel.gui import ScientificSpinBox

class Driver():
# a class to inherit from when creating a custom gui for an instrument

    sweep_window = QMainWindow()
    load_window = QMainWindow()

    @staticmethod
    def load(nickname, ph_cls, address, slot=None):
        # this function must return a loaded PyHegel instrument
        pass

    @staticmethod
    def sweep(gui_dev):
        # this function returns nothing.
        # it's called on when asking for instrument sweep
        # it must set the sweep attribute of gui_dev
        # gui_dev.sweep = [start, stop, npts]
        pass

####################
# Default Driver
####################

class Default(Driver):

    @staticmethod
    def load(nickname, ph_cls, address, **kwargs):
        instr = ph_cls(address, **kwargs)
        instr.header.set(nickname)
        return instr

    @staticmethod
    def config():
        pass

    @staticmethod
    def sweep(lab, gui_dev):
        # minimal window for defining sweep start, stop, step:
        display_name = gui_dev.getDisplayName('long')
        win = Driver.sweep_window
        win.setWindowTitle('Setup sweep ' + display_name)
        win.setWindowIcon(QtGui.QIcon('resources/favicon/favicon.png'))
        wid = QWidget(); win.setCentralWidget(wid)
        layout = QGridLayout(); wid.setLayout(layout)
        
        # widgets:
        label_start = QLabel('Start:')
        label_stop = QLabel('Stop:')
        label_step = QLabel('# pts:')
        spin_start = ScientificSpinBox.PyScientificSpinBox()
        spin_stop = ScientificSpinBox.PyScientificSpinBox()
        spin_npts = QSpinBox()
        spin_npts.setMaximum(1000000)
        ok_button = QPushButton('Ok')
        
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
        layout.addWidget(label_step, 2, 0)
        layout.addWidget(spin_start, 0, 1)
        layout.addWidget(spin_stop, 1, 1)
        layout.addWidget(spin_npts, 2, 1)
        layout.addWidget(ok_button, 3, 1)
        
        # connect signals:
        def onOk():
            win.close()
        ok_button.clicked.connect(onOk)
        ok_button.clicked.connect(lambda: lab.setSweepValues(
            gui_dev,
            spin_start.value(),
            spin_stop.value(),
            spin_npts.value(),
        ))

        win.show()

####################
# American Magnetics
####################

class ami430(Driver):
    
    @staticmethod
    def load(nickname, ph_cls, address, slot=None):
        win = Driver.load_window
        title = "Setup AMI430 vector - " + str(nickname)
        win.setWindowTitle(title)
        wid = QWidget(); win.setCentralWidget(wid)
        form = QFormLayout(); wid.setLayout(form)
        
        le_x, le_y, le_z = QLineEdit(), QLineEdit(), QLineEdit()
        le_x.setText('A6013_X')
        le_y.setText('A5072_Y')
        le_z.setText('A6021_Z')
        form.addRow('Magnet X', le_x)
        form.addRow('Magnet Y', le_y)
        form.addRow('Magnet Z', le_z)
        btn_load_all = QPushButton('Load magnets')
        lbl_load = QLabel('0/3')
        form.addRow(lbl_load, btn_load_all)
        btn_load_vector = QPushButton('Load vector')
        btn_cancel = QPushButton('Cancel')
        form.addRow(btn_load_vector, btn_cancel)

        magnets = mx, my, mz = [None]*3
        line_edits = [le_x, le_y, le_z]
        axes = ['x', 'y', 'z']
        def onLoadAll():
            for i, (ax, le) in enumerate(zip(axes, line_edits)):
                nickname = 'ami_' + ax
                #ph_ami = Default.load(nickname,
                                      #instruments.AmericanMagnetics_model430,
                                      #address.format(ip_name=le.text()))
                                      
                #magnets[i] = ph_ami
                print(nickname, address.format(ip_name=le.text()))
        btn_load_all.clicked.connect(onLoadAll)
        def onCancel():
            win.close()
        btn_cancel.clicked.connect(onCancel)
        def onLoadVector():
            vector = Default.load(nickname, ph_cls, *magnets)
            win.close()


        win.show()
        
