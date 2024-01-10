from PyQt5.QtWidgets import QComboBox
from PyQt5.QtCore import Qt, QEvent
from PyQt5.QtGui import QKeyEvent

class Combobox(QComboBox):
    def __init__(self, *args, **kwargs):
        super().__init__()

    def keyPressEvent(self, event):
        # vim jkhl, d(own), u(p), g, G
        key = event.key()
        def pressKey(key):
            self.keyPressEvent(QKeyEvent(QEvent.KeyPress, key, Qt.NoModifier))
        if key == Qt.Key_J:
            pressKey(Qt.Key_Down)
        elif key == Qt.Key_K:
            pressKey(Qt.Key_Up)
        elif key == Qt.Key_H:
            pressKey(Qt.Key_Left)
        elif key == Qt.Key_L:
            pressKey(Qt.Key_Right)
        elif key == Qt.Key_D:
            for _ in range(5):
                pressKey(Qt.Key_Down)
        elif key == Qt.Key_U:
            for _ in range(5):
                pressKey(Qt.Key_Up)
        elif key == Qt.Key_G:
            if event.modifiers() == Qt.ShiftModifier:
                pressKey(Qt.Key_End)
            elif event.modifiers() == Qt.NoModifier:
                pressKey(Qt.Key_Home)
        else:
            super().keyPressEvent(event)
