import sys
from PyQt5.QtWidgets import QTreeWidget, QAbstractItemView
from PyQt5 import QtGui, QtCore

from src.GuiInstrument import GuiInstrument, GuiDevice


class TreeWidget(QTreeWidget):
    def __init__(self, *args, **kwargs):
        super(TreeWidget, self).__init__()
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setDragDropMode(QAbstractItemView.DragDrop)
    
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
    
    @staticmethod
    def getData(item):
        # return the data of an item
        return item.data(0, QtCore.Qt.UserRole)

    def setData(self, item, data):
        # set the data of an item
        item.setData(0, QtCore.Qt.UserRole, data)
    
    def findItemByData(self, data):
        # find an item by its data, including subitems
        for i in range(self.topLevelItemCount()):
            item = self.topLevelItem(i)
            if self.getData(item) == data:
                return item
            for j in range(item.childCount()):
                subitem = item.child(j)
                if self.getData(subitem) == data:
                    return subitem
        return None

    def removeSelected(self):
        # remove selected item including its parent, brothers and sisters
        selected_index = self.indexOfTopLevelItem(self.selectedItem())
        self.takeTopLevelItem(selected_index)

    def removeByData(self, data):
        item = self.findItemByData(data)
        if item is None:
            return
        item_index = self.indexOfTopLevelItem(item)
        self.takeTopLevelItem(item_index)

    def mimeTypes(self):
        # define the mime types that can be dragged
        return ['device-nickname', 'instrument-nickname']

    def mimeData(self, items):
        # what happens when the item is dragged
        mime_data = QtCore.QMimeData()
        item = items[0]
        # get data:
        data = self.getData(item)
        if isinstance(data, GuiInstrument):
            b_name = bytes(data.nickname, 'utf-8')
            mime_data.setData('instrument-nickname', b_name)
        elif isinstance(data, GuiDevice):
            b_parent_name = bytes(data.parent.nickname, 'utf-8')
            b_name =  bytes(data.nickname, 'utf-8')
            mime_data.setData('instrument-nickname', b_parent_name)
            mime_data.setData('device-nickname', b_name)
        return mime_data
            
    def dropMimeData(self, parent, row, data, action):
        # what happens when the item is dropped
        # implemented by children
        pass