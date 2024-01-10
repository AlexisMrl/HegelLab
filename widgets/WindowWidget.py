from PyQt5.QtWidgets import QApplication, QMainWindow, QShortcut
from PyQt5.QtCore import Qt, QEvent
from PyQt5.QtGui import QKeyEvent, QKeySequence

from src.GuiInstrument import GuiDevice


class Window(QMainWindow):
    
    # class variable
    lab = None
    windows = []

    def __init__(self):
        super().__init__()
        Window.windows.append(self)
    
    def focus(self):
        self.setFocus(True)
        self.activateWindow()
        self.raise_()
        self.show()

    @staticmethod
    def killAll():
        for win in Window.windows:
            win.close()
        Window.windows.clear()
        Window.lab = None

    @staticmethod
    def initShortcutsAll(lab):
        Window.lab = lab
        [win.initShortcuts() for win in Window.windows]


    # i could not find a way to do QApplication-wide shortcuts
    # so the global shortcuts are implemented at QMainWindow level.
    # and specific ones are in the instances of this class.

    def initShortcuts(self):
        lab = Window.lab

        self.short("w, q", self.close)
        self.short("w, i", lab.showRack)
        self.short("w, d", lab.showDisplay)
        self.short("w, 1, d", lambda: lab.showDisplay(dual=False))
        self.short("w, 2, d", lambda: lab.showDisplay(dual=True))
        self.short("w, m", lab.showMonitor)
        self.short("w, s", lab.showMain)
        self.short("w, w", lab.showMain)

        self.short("t, s", lab.view_main.focusTreeSw)
        self.short("t, o", lab.view_main.focusTreeOut)
        self.short("t, l", lab.view_main.focusTreeLog)
        self.short("t, g", lab.view_main.focusTreeLog)
        self.short("t, i", lab.showRack)
        self.short("t, m", lab.showMain)

        self.short("Shift+s", lab.view_main.actionStartSweep.trigger)

    def short(self, key, slot):
        # create shortcut
        shortcut = QShortcut(QKeySequence(key), self)
        shortcut.activated.connect(slot)