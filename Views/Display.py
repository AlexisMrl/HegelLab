
from PyQt5 import QtGui, uic
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget

class Display(QMainWindow):
    def __init__(self, lab):
        super(Display, self).__init__()
        uic.loadUi('ui/DisplayWindow.ui', self)
        self.setWindowTitle('Live display')
        self.setWindowIcon(QtGui.QIcon('resources/favicon/favicon.png'))
        self.lab = lab
        