import json
from collections import OrderedDict

class LoaderSaver:
    def __init__(self, lab):
        self.lab = lab
        
    def importFromJSON(self, path='instruments.json'):
        # return path.json as a dict
        with open(path) as json_file:
            data = json.load(json_file, object_pairs_hook=OrderedDict)
        instruments = data.get('instruments')
        return instruments

    def exportToJSON(self, gui_instruments, path="temp/rack.json"):
        # export gui_instruments to json file
        list_of_dict = []
        for gui_instr in gui_instruments:
            list_of_dict.append(gui_instr.toDict())
        
        json_dict = {'instruments': list_of_dict}
        
        with open(path, 'w') as outfile:
            json.dump(json_dict, outfile, indent=4)

    def exportToPyHegel(self, gui_instruments):
        # export rack to pyHegel loading code
        s = ""
        for gui_instr in gui_instruments.values():
            s += gui_instr.nickname + ' = '
            s += 'instruments.' + gui_instr.instr_cls.__name__ + '('
            s += '"' + gui_instr.address + '"'
            s += ')\n'
        print(s)
            