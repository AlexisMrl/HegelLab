![HegelLab](./resources/logo_white.png#gh-dark-mode-only)
![HegelLab](./resources/logo_black.png#gh-light-mode-only)

# HegelLab
My attempt at building an interface for pyHegel.

This is highly inspired by Labber and VsdVg (the original interface on top of pyHegel).
It is intended to be more structured than the original VsdVg, so adding feature should be easier.

The objective is to make it as modular and versatile as possible.

Main features (not much more than VsdVg, but cleaner and in py3):
- load 'any' instrument from pyHegel while choosing its devices (with minimal prior work),
- save and load your whole loaded instruments and custom devices to a file,
- responsive live display,
- new: renaming devices.


Note: sweep and live view for higher than two swept devices is currently not supported.

# Packages
Need a Python3 installation of PyHegel and the package `pyqtgraph` in version `>=0.12.3`.

# Installation (wip)

Installation procecure python 3, PyHegel and HegelLab:
```py
# conda create and install:
conda create -n py311 python=3.11 
conda activate py311
# activate and install PyVisa
conda install ipython numpy scipy pyqt pywin32 matplotlib pyserial pythonnet pypdf2 pytz pyqtgraph=0.13.1
conda install -c conda-forge pyvisa
# install PyHegel
cd <PyHegel dir>
pip install -e .
```

Then clone this repo and run HegelLab from `pyHegel`:
```py
git clone https://github.com/AlexisMrl/HegelLab.git
cd HegelLab
pyHegel
run HegelLab
```

Or (not fully supported yet) edit the .lnk file with your `pythonw` env path

For zi instruments:
```py
pip install zhinst 
```
