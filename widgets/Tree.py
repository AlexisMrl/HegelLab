import sys
from PyQt5.QtWidgets import QTreeWidget, QAbstractItemView
from PyQt5 import QtGui, QtCore


class Tree(QTreeWidget):
    def __init__(self, *args, **kwargs):
        super(Tree, self).__init__()
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setDragDropMode(QAbstractItemView.DragDrop)
        
    def selectedItem(self):
        # return theselected item
        selected = self.selectedItems()
        if len(selected) == 0:
            return None
        return selected[0]
    
    def selectedItemData(self):
        # return the data of the selected item
        selected = self.selectedItem()
        if selected is None:
            return None
        return selected.data(0, QtCore.Qt.UserRole)

    def addData(self, item, dic):
        # add data to an item
        item_dic = item.data(0, QtCore.Qt.UserRole)
        merge = {**item_dic, **dic}
        item.setData(0, QtCore.Qt.UserRole, merge)

    def removeSelected(self):
        # remove selected item including its parent, brothers and sisters
        selected_index = self.indexOfTopLevelItem(self.selectedItem())
        self.takeTopLevelItem(selected_index)

    def isTopLevel(self, item):
        # return True if the item is a top level item
        return item.parent() is None

    def selectLastItem(self):
        # select the last item
        self.setCurrentItem(self.topLevelItem(self.topLevelItemCount()-1))

    def mimeTypes(self):
        # define the mime types that can be dragged
        return ['device-name']

    def mimeData(self, items):
        # define the mime data that can be dragged
        mime_data = QtCore.QMimeData()
        item = items[0]
        if self.isTopLevel(item):
            b_name = bytes(item.text(0), 'utf-8')
            mime_data.setData('instrument-name', b_name)
        else:
            item_parent = items[0].parent()
            b_parent_name = bytes(item_parent.text(0), 'utf-8')
            b_name =  bytes(item.text(0), 'utf-8')
            mime_data.setData('instrument-name', b_parent_name)
            mime_data.setData('device-name', b_name)
        return mime_data
            
    def dropMimeData(self, parent, row, data, action):
        # what happens when the item is dropped
        # implemented by children
        return None