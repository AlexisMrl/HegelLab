from PyQt5.QtWidgets import QMessageBox, QWidget
from PyQt5 import QtGui

class Popup():
    # This class is used to manage popup and errors.
    def __init__(self):
        self.win = QWidget()
        
    def _popError(self, win_type, title, message):
        # pop an error window
        # win_type:
        #   QMessageBox.Critical
        #   QMessageBox.Information
        #   QMessageBox.Question
        #   QMessageBox.Warning
        msg = QMessageBox(win_type, title, message)
        msg.setWindowIcon(QtGui.QIcon('resources/favicon/favicon.png'))
        msg.exec_()
    
    def _popErrorWithDetails(self, win_type, title, message, details):
        # pop an error window with details
        msg = QMessageBox(win_type, title, message)
        msg.setDetailedText(details)
        msg.setWindowIcon(QtGui.QIcon('resources/favicon/favicon.png'))
        msg.exec_()
    
    def missingSweepParameter(self):
        self._popError(QMessageBox.Warning,
                      'Warning',
                      'A device is missing its sweep parameters')
        return

    def noSweepDevice(self):
        self._popError(QMessageBox.Warning,
                      'Warning',
                      'No device is set to sweep')
        return
    
    def sweepZeroPoints(self):
        self._popError(QMessageBox.Warning,
                      'Warning',
                      'A device is set to sweep 0 points')
        return
    
    def devAlreadyHere(self):
        self._popError(QMessageBox.Warning,
                      'Warning',
                      'This device is already in here')
        return

    def instrLoadError(self, exception, traceback):
        self._popErrorWithDetails(QMessageBox.Critical,
                      'Error',
                      'Error while loading instrument: ' + str(exception),
                      traceback)
        return
    
    def sweepError(self, exception, traceback):
        self._popErrorWithDetails(QMessageBox.Critical,
                      'Sweep error',
                      'Error from pyHegel while sweeping: ' + str(exception),
                      traceback)
        return


    # -- yes/no --
    def _popYesNo(self, title, message):
        # pop a yes/no window
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Question)
        msg.setText(message)
        msg.setWindowTitle(title)
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg.setWindowIcon(QtGui.QIcon('resources/favicon/favicon.png'))
        return msg.exec_() == QMessageBox.Yes

    def noOutputDevice(self):
        return self._popYesNo('No output device',
                              'No output device is set. Continue?')
        
    def askQuit(self):
        return self._popYesNo('Quit',
                              'Are you sure you want to quit?')
