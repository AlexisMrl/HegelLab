from PyQt5.QtWidgets import QApplication, QMainWindow, QShortcut
from PyQt5.QtCore import Qt, QEvent
from PyQt5.QtGui import QKeyEvent, QKeySequence

from src.GuiInstrument import GuiDevice


class Window(QMainWindow):
    
    # class variable
    lab = None
    windows = []
    gui_dev_buffer = None

    def __init__(self):
        super().__init__()
        Window.windows.append(self)
        if Window.lab is not None:
            self.initShortcuts()
    
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
        Window.gui_dev_buffer = None

    @staticmethod
    def initShortcutsAll():
        [win.initShortcuts() for win in Window.windows]

    
    def initShortcuts(self):
        lab = Window.lab

        self.short("w, q", self.close)
        self.short("w, i", lab.showRack)
        self.short("w, d", lab.showDisplay)
        self.short("w, m", lab.showMonitor)
        self.short("w, s", lab.showMain)

        self.short("t, s", lab.view_main.focusTreeSw)
        self.short("t, o", lab.view_main.focusTreeOut)
        self.short("t, l", lab.view_main.focusTreeLog)
        self.short("t, i", lab.view_rack.focusTree)
        self.short("t, m", lab.view_monitor.focusTree)

    def short(self, key, slot):
        # create shortcut
        shortcut = QShortcut(QKeySequence(key), self)
        shortcut.activated.connect(slot)
    
    def yankGuiDev(self, gui_dev):
        if isinstance(gui_dev, GuiDevice):
            self.gui_dev_buffer = gui_dev