
from PyQt5 import uic
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget

class Display(QMainWindow):
    def __init__(self, lab):
        super(Display, self).__init__()
        uic.loadUi('ui/DisplayWindow.ui', self)
        self.setWindowTitle('Display')
        self.lab = lab
        