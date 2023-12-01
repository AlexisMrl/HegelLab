from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QMainWindow
import IPython

#from pyqtconsole.console import PythonConsole
#from pyqtconsole.highlighter import format

from qtconsole.rich_jupyter_widget import RichJupyterWidget
from qtconsole.inprocess import QtInProcessKernelManager

class Console(QMainWindow):
    def __init__(self, lab):
        super().__init__()
        self.setWindowTitle("Console")
        self.setWindowIcon(QIcon("resources/console.svg"))
        self.resize(1000, 600)
        self.lab = lab

        self.console = RichJupyterWidget()
        self.setCentralWidget(self.console)
        
        self.disable = False
        if IPython.get_ipython():
            self.disable = True
            return

        self.console.change_font_size(5)
        #self.console.set_default_style(colors='Linux')
        
        self.console.kernel_manager = QtInProcessKernelManager()
        self.console.kernel_manager.start_kernel(show_banner=False)
        self.console.kernel_manager.kernel.gui = 'qt'
        
        self.console.kernel_client = self.console.kernel_manager.client()
        self.console.kernel_client.start_channels()
        




    def push_vars(self, variableDict):
        if self.disable: return
        self.console.kernel_manager.kernel.shell.push(variableDict)

        