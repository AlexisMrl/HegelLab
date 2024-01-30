from PyQt5.QtWidgets import QMessageBox, QWidget
from PyQt5 import QtGui
import traceback

class Popup:
    # This class is used to manage popup and errors.
    def __init__(self):
        self.win = QWidget()
    
    def _excToStr(self, exception):
        return "".join(traceback.format_tb(exception.__traceback__))
    
    def _popError(self, win_type, title, message, details=None):
        # pop an error window
        # win_type:
        #   QMessageBox.Critical
        #   QMessageBox.Information
        #   QMessageBox.Question
        #   QMessageBox.Warning
        msg = QMessageBox(win_type, title, message)
        msg.setWindowIcon(QtGui.QIcon("resources/favicon/favicon.png"))
        if details: msg.setDetailedText(details)
        msg.exec_()
    
    def _popErrorC(self, title, message, detail=None):
        self._popError(QMessageBox.Critical, title, message, detail)
    def _popErrorW(self, title, message, detail=None):
        self._popError(QMessageBox.Warning, title, message, detail)
    def _popErrorI(self, title, message, detail=None):
        self._popError(QMessageBox.Information, title, message, detail)
    def _popErrorQ(self, title, message, detail=None):
        self._popError(QMessageBox.Question, title, message, detail)

    def sweepMissingDevParameter(self):
        self._popErrorW("Warning", "A device is missing its sweep parameters")

    def sweepNoDevice(self):
        self._popErrorW("Warning", "No device is set to sweep")

    def sweepZeroPoints(self):
        self._popError("Warning", "A device is set to sweep 0 points")

    def sweepStartStopEqual(self):
        self._popError("Warning", "A device is set to sweep from a value to the same value",)

    def instrLoadError(self, exception, nickname=''):
        self._popErrorC(f"Error - {nickname}",
            "Error while loading instrument: " + str(exception),
            self._excToStr(exception))

    def devLoadError(self, exception):
        self._popErrorC("Error",
            f"Error while loading device: {str(exception)}\nThis device will not be loaded.",
            self._excToStr(exception))
    
    def devRampZero(self):
        self._popErrorW("Warning", "Ramp rate cannot be 0.")

    def devScaleZero(self):
        self._popErrorW("Warning", "Scale factor cannot be 0.")
    
    def devExtraArgsEvalFail(self):
        self._popErrorW("Warning",
            """Fail to understand keywords arguments for device.\n
            The string must be valid for: `dict(eval(<input>))`.
            """)

    def devLoadLogicalError(self, exception):
        self._popErrorC("Error",
            f"Error while loading logical device: {str(exception)}\nThe base device is still loaded.",
            self._excToStr(exception))

    def sweepThreadError(self, exception):
        self._popErrorC("Sweep error",
            "Error from pyHegel thread while sweeping: " + str(exception),
            self._excToStr(exception))

    def setValueError(self, exception):
        self._popErrorW("Error",
            "Error while setting value: " + str(exception),
            self._excToStr(exception))

    def getValueError(self, exception):
        self._popErrorW("Error",
            "Error while getting value: " + str(exception),
            self._excToStr(exception))

    def devIsNeeded(self):
        self._popErrorW("Warning",
            "This device is needed for another device. Cannot remove it.")


    # -- YES/NO --

    def _popYesNo(self, title, message):
        # pop a yes/no window
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Question)
        msg.setText(message)
        msg.setWindowTitle(title)
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg.setWindowIcon(QtGui.QIcon("resources/favicon/favicon.png"))
        return msg.exec_() == QMessageBox.Yes

    def sweepNoOutputDevice(self):
        return self._popYesNo("No output device", "No output device is set. Continue?")

    def devNotLoaded(self):
        return self._popYesNo("Device not loaded", "This device is not loaded. Continue?")

    def askRemoveInstrument(self, nickname):
        msg = "Are you sure you want to remove " + nickname + "?"
        return self._popYesNo("Remove instrument", msg)

    def askQuit(self):
        return self._popYesNo("Quit", "Are you sure you want to quit?")

    def notSettable(self):
        return self._popYesNo("Not settable", "This device is detected as not settable. Try sweeping it anyway?")

    def notGettable(self):
        return self._popYesNo("Not gettable", "This device is not gettable. Try to add it anyway?")

    def sweepABool(self):
        return self._popYesNo("Sweep boolean", "This device's output type is define as boolean. Want to sweep it?")

    def askRemoveDevice(self, nickname):
        msg = f"Are you sure you want to remove the device '{nickname}' ?"
        return self._popYesNo("Remove device", msg)
