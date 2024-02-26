import json
from collections import OrderedDict
from PyQt5.QtWidgets import QFileDialog, QMainWindow, QTextEdit, QPushButton, QApplication
from PyQt5.QtWidgets import QVBoxLayout, QWidget
from PyQt5.QtGui import QFont, QIcon
from widgets.WindowWidget import Window

class LoaderSaver:
    def __init__(self, lab):
        self.lab = lab
        self.win_ph_script = None
        
    def importFromJSON(self, path=None):
        # open a file dialog to select a json file
        # return a list of instruments
        if path is None or path == "":
            path = QFileDialog.getOpenFileName(self.lab.view_rack, 'Open file', '.', "JSON files (*.json)")[0]
        if path == "":
            return []
        try:
            with open(path) as json_file:
                data = json.load(json_file, object_pairs_hook=OrderedDict)
            instruments = data.get('instruments')
            return instruments
        except Exception as e:
            self.lab.pop.loadingJSONError(e)
            return []

    def exportToJSON(self, gui_instruments, path=None):
        # open a file dialog to select a json file
        # export the instruments to the json file

        if path is None or path == "":
            path = QFileDialog.getSaveFileName(self.lab.view_rack, 'Save file', '.', "JSON files (*.json)")[0]
        if path == "":
            return None
        if not path.endswith(".json"):
            path += ".json"

        list_of_dict = []
        for gui_instr in gui_instruments:
            list_of_dict.append(gui_instr.toDict())
        
        json_dict = {'instruments': list_of_dict}
        
        with open(path, 'w') as outfile:
            json.dump(json_dict, outfile, indent=2)

    def exportToPyHegel(self, gui_instruments):
        # export rack to pyHegel loading code
        # simple window wit a textedit and a button in a vbox to copy to clipboard
        self.win_ph_script = Window()
        win = self.win_ph_script
        win.setWindowIcon(QIcon("resources/favicon/favicon.png"))
        win.setWindowTitle("Export to pyHegel")
        win.resize(800, 600)
        textedit = QTextEdit()
        textedit.setReadOnly(True)
        textedit.setFont(QFont("Courier New", 11))
        button = QPushButton("Copy to clipboard")
        button.clicked.connect(lambda: QApplication.clipboard().setText(textedit.toPlainText()))
        vbox = QVBoxLayout()
        vbox.addWidget(textedit)
        vbox.addWidget(button)
        central_widget = QWidget()
        central_widget.setLayout(vbox)
        win.setCentralWidget(central_widget)
        
        # generate text
        for gui_instr in gui_instruments:
            textedit.append(gui_instr.toPyHegelScript())
        win.focus()

            