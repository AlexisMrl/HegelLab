from PyQt5.QtWidgets import QMessageBox, QWidget
from PyQt5 import QtGui


class Popup:
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
        msg.setWindowIcon(QtGui.QIcon("resources/favicon/favicon.png"))
        msg.exec_()

    def _popErrorWithDetails(self, win_type, title, message, details):
        # pop an error window with details
        msg = QMessageBox(win_type, title, message)
        msg.setDetailedText(details)
        msg.setWindowIcon(QtGui.QIcon("resources/favicon/favicon.png"))
        msg.exec_()

    def sweepMissingDevParameter(self):
        self._popError(
            QMessageBox.Warning, "Warning", "A device is missing its sweep parameters"
        )
        return

    def sweepNoDevice(self):
        self._popError(QMessageBox.Warning, "Warning", "No device is set to sweep")
        return

    def sweepZeroPoints(self):
        self._popError(
            QMessageBox.Warning, "Warning", "A device is set to sweep 0 points"
        )
        return

    def sweepStartStopEqual(self):
        self._popError(
            QMessageBox.Warning,
            "Warning",
            "A device is set to sweep from a value to the same value",
        )
        return

    def devAlreadyHere(self):
        self._popError(
            QMessageBox.Information, "Information", "This device is already in here"
        )
        return

    def instrLoadError(self, exception, traceback):
        self._popErrorWithDetails(
            QMessageBox.Critical,
            "Error",
            "Error while loading instrument: " + str(exception),
            traceback,
        )
        return

    def devLoadError(self, exception, traceback):
        self._popErrorWithDetails(
            QMessageBox.Critical,
            "Error",
            "Error while loading device: "
            + str(exception)
            + "\nThis device will not be loaded.",
            traceback,
        )
        return

    def devLoadLogicalError(self, exception, traceback):
        self._popErrorWithDetails(
            QMessageBox.Critical,
            "Error",
            "Error while loading logical device: "
            + str(exception)
            + "\nThe base device is still loaded.",
            traceback,
        )
        return

    def sweepThreadError(self, exception, traceback):
        self._popErrorWithDetails(
            QMessageBox.Critical,
            "Sweep error",
            "Error from pyHegel thread while sweeping: " + str(exception),
            traceback,
        )
        return

    def setValueError(self, exception, traceback):
        self._popErrorWithDetails(
            QMessageBox.Warning,
            "Error",
            "Error while setting value: " + str(exception),
            traceback,
        )
        return

    def devIsNeeded(self):
        self._popError(
            QMessageBox.Warning,
            "Warning",
            "This device is needed for another device. Cannot remove it.",
        )
        return

    # -- yes/no --
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

    def askRemoveInstrument(self, nickname):
        msg = "Are you sure you want to remove " + nickname + "?"
        return self._popYesNo("Remove instrument", msg)

    def askQuit(self):
        return self._popYesNo("Quit", "Are you sure you want to quit?")

    def notSettable(self):
        return self._popYesNo(
            "Not settable", "This device is not settable. Try sweeping it anyway?"
        )

    def notGettable(self):
        return self._popYesNo(
            "Not gettable", "This device is not gettable. Try as output device anyway?"
        )

    def askRemoveDevice(self, nickname):
        msg = "Are you sure you want to remove " + nickname + "?"
        return self._popYesNo("Remove device", msg)
