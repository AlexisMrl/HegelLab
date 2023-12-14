import sys
from PyQt5.QtWidgets import QApplication, QMainWindow
from PyQt5.QtCore import Qt, QEvent


class AltDragWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.installEventFilter(self)

    def eventFilter(self, obj, event):
        if event.type() == QEvent.MouseButtonPress:
            if event.button() == Qt.LeftButton:
                modifiers = QApplication.keyboardModifiers()
                if modifiers == Qt.AltModifier:
                    # Alt+LeftClick detected
                    self.drag_start_position = event.globalPos() - self.pos()
                    event.accept()
                    return True
            elif event.button() == Qt.MiddleButton:
                # MiddleClick detected
                self.close()
                event.accept()
                return True
        elif event.type() == QEvent.MouseMove and hasattr(self, 'drag_start_position'):
            self.move(event.globalPos() - self.drag_start_position)
            event.accept()
            return True
        elif event.type() == QEvent.MouseButtonRelease and event.button() == Qt.LeftButton:
            if hasattr(self, 'drag_start_position'):
                delattr(self, 'drag_start_position')
                event.accept()
                return True
        return super().eventFilter(obj, event)