from PyQt5.QtWidgets import QTreeWidget, QAbstractItemView
from PyQt5 import QtCore
from PyQt5.QtCore import Qt, QEvent
from PyQt5.QtGui import QKeyEvent

from src.GuiInstrument import GuiInstrument, GuiDevice


class TreeWidget(QTreeWidget):
    lab = None
    def __init__(self, *args, **kwargs):
        super().__init__()
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setDragDropMode(QAbstractItemView.DragDrop)
        self.remove_btn = None
    
    def addTopLevelItem(self, item):
        super().addTopLevelItem(item)
        self.setCurrentItem(item)
    
    def insertTopLevelItem(self, row, item):
        super().insertTopLevelItem(row, item)
        self.setCurrentItem(item)

    def __iter__(self):
        # make the tree iterable
        for i in range(self.topLevelItemCount()):
            yield self.topLevelItem(i)

    def __getitem__(self, key):
        # make the tree subscriptable
        return self.topLevelItem(key)

    def selectedItem(self):
        # return theselected item
        selected = self.selectedItems()
        if len(selected) == 0:
            return None
        return selected[0]
    
    def selectedData(self, column=0):
        selected = self.selectedItem()
        if not selected: return None
        return self.getData(selected, column)

    @staticmethod
    def getData(item, column=0):
        # return the data of an item
        return item.data(column, QtCore.Qt.UserRole)
    
    def setData(self, item, data, column=0):
        # set the data of an item
        item.setData(column, QtCore.Qt.UserRole, data)

    def findItemByData(self, data, column=0):
        # find an item by its data, including subitems
        for i in range(self.topLevelItemCount()):
            item = self.topLevelItem(i)
            if self.getData(item, column) == data:
                return item
            for j in range(item.childCount()):
                subitem = item.child(j)
                if self.getData(subitem, column) == data:
                    return subitem
        return None

    def removeSelected(self):
        # remove selected item including its parent, brothers and sisters
        selected_index = self.indexOfTopLevelItem(self.selectedItem())
        self.takeTopLevelItem(selected_index)

    def removeByData(self, data, column=0):
        item = self.findItemByData(data, column)
        if item is None:
            return
        item_index = self.indexOfTopLevelItem(item)
        self.takeTopLevelItem(item_index)

    def mimeTypes(self):
        # define the mime types that can be dropped
        return ["device-nickname", "instrument-nickname"]

    def mimeData(self, items):
        # what happens when the item is dragged
        mime_data = QtCore.QMimeData()
        item = items[0]
        # get data:
        data = self.getData(item)
        if isinstance(data, GuiInstrument):
            b_name = bytes(data.nickname, "utf-8")
            mime_data.setData("instrument-nickname", b_name)
        elif isinstance(data, GuiDevice):
            b_parent_name = bytes(data.parent.nickname, "utf-8")
            b_name = bytes(data.nickname, "utf-8")
            mime_data.setData("instrument-nickname", b_parent_name)
            mime_data.setData("device-nickname", b_name)
        return mime_data

    guiDeviceDropped = QtCore.pyqtSignal(object, int)
    def dropMimeData(self, parent, row, data, action):
        # emit signal when something is drop
        instr_nickname = str(data.data("instrument-nickname"), "utf-8")
        dev_nickname = str(data.data("device-nickname"), "utf-8")
        gui_dev = self.lab.getGuiInstrument(instr_nickname).getGuiDevice(dev_nickname)
        self.guiDeviceDropped.emit(gui_dev, row)
        return True


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
        elif key == Qt.Key_X and self.remove_btn:
            self.remove_btn.click()
        else:
            super().keyPressEvent(event)
