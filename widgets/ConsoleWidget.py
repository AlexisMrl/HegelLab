from qtconsole.rich_jupyter_widget import RichJupyterWidget
from qtconsole.inprocess import QtInProcessKernelManager
import IPython
from widgets.WindowWidget import Window
from PyQt5.QtGui import QIcon


class ConsoleWidget(RichJupyterWidget):

    def __init__(self, hl, *args, **kwargs):
        super(ConsoleWidget, self).__init__(*args, **kwargs)
        
        # ui stuff
        self.setWindowTitle("Console")
        self.setWindowIcon(QIcon("resources/console.svg"))
        self.banner = "HegelLab console\npyHegel commands are imported\n"
        
        # nothing seems to work...
        #self.font_family = 'Consolas'
        #self.font_size = 14
        #self.gui_completion = 'plain'
        #self.syntax_style = 'monokai'

        # console stuff
        self.console_disabled = False
        if IPython.get_ipython():
            self.print_text('Running under IPython so qtConsole is disabled.')
            self.console_disabled = True
            return


        self.kernel_manager = kernel_manager = QtInProcessKernelManager()
        #kernel_manager.start_kernel(['--TerminalInteractiveShell.display_completions=readlinelike'], show_banner=False)
        kernel_manager.start_kernel()
        kernel_manager.kernel.gui = 'qt'
        self.kernel_client = self._kernel_manager.client()
        self.kernel_client.start_channels()
        
        # init
        self.push_vars({'hl': hl})
        self.push_vars({k: v for k, v in hl.__dict__.items() if not k.startswith('_')})
        
        self.kernel_client.execute("%autocall 2", silent=True, store_history=False)
        kernel_manager.kernel.shell.ex("from pyHegel.commands import *")
        kernel_manager.kernel.shell.ex("import numpy as np")

        def stop():
            if self.console_disabled:
                return
            self.kernel_client.stop_channels()
            kernel_manager.shutdown_kernel()
        self.exit_requested.connect(stop)
    
    def focus(self):
        self._control.setFocus(True)
        self.activateWindow()
        self.raise_()
        self.show()

    def push_vars(self, variableDict):
        """
        Given a dictionary containing name / value pairs, push those variables
        to the Jupyter console widget
        """
        self.kernel_manager.kernel.shell.push(variableDict)

    def clear(self):
        self._control.clear()

    def print_text(self, text):
        self._append_plain_text(text)

    def execute_command(self, command):
        self._execute(command, False)

    def execute_nohistory(self, command):
        self.kernel_client.execute(command, silent=True, store_history=False)
