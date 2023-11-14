from PyQt5.QtWidgets import QLabel

class DropLabel(QLabel):
    # a label that can accept drops

    def __init__(self, *args, **kwargs):
        self.accepts = kwargs.pop('acccepts', '')
        super(DropLabel, self).__init__(*args, **kwargs)
        self.setAcceptDrops(True)
    
    def mimeTypes(self):
        return self.accepts
    
    def dropMimeData(self, data, action, row, column, parent):
        pass
