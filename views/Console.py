from qtconsole import inprocess
import IPython

class Console(inprocess.QtInProcessRichJupyterWidget):
    def __init__(self, lab):
        super().__init__()
        self.lab = lab
        
        #self.kernel_manager = inprocess.QtInProcessKernelManager()
        #self.kernel_manager.start_kernel()
        #self.kernel_client = self.kernel_manager.client()
        #self.kernel_client.start_channels()
