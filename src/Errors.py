from PyQt5.QtWidgets import QMessageBox, QWidget

class Errors():
    # This class is used to manage errors.
    def __init__(self):
        self.win = QWidget()
        
    def popError(self, win_type, title, message):
        # pop an error window
        # win_type:
        #   QMessageBox.Critical
        #   QMessageBox.Information
        #   QMessageBox.Question
        #   QMessageBox.Warning
        msg = QMessageBox(win_type, title, message)
        msg.exec_()

    def missingSweepParameter(self):
        self.popError(QMessageBox.Warning,
                      'Warning',
                      'A device is missing its sweep parameters')
        return


 