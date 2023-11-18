![HegelLab](./resources/logo_white.png#gh-dark-mode-only)
![HegelLab](./resources/logo_black.png#gh-light-mode-only)

# HegelLab
My attempt at building an interface for pyHegel.

This is highly inspired by Labber and VsdVg (the original interface on top of pyHegel).
It is intended to be more structured than the original VsdVg, so adding feature should be easier.

The objective is to make it as modular and versatile as possible.

Main features (not much more than VsdVg, but cleaner):
- load 'any' instrument from pyHegel while choosing its devices (with minimal prior work),
- save and load your whole loaded instruments and custom devices to a file,
- responsive live display,
- new: renaming devices.


Note: that sweep and live view for higher than two swept device is currently not supported.

Note 2: you can wrap a device with a Ramping/Scaling/Limit device with `create device`. BUT, it is only possible one time: i.e. you can't wrap a wrapped device. This is a known limitation. I couldn't find a good design to implement infinite wrapping correctly, but if i (or someone) do, i'd like to make it possible.

# Packages
Need a Python3 installation of PyHegel and the package `pyqtgraph` in version `>=0.12.3`.

# Installation (wip)

Installation procecure python 3, PyHegel and HegelLab:
```py
# conda create and install:
conda create -n python38 python=3.8
conda activate py311
# activate and install PyVisa
conda install ipython numpy scipy pyqt pywin32 matplotlib pyserial pythonnet pypdf2 pytz
iconda install pyqtgraph=0.12.3
conda install -c "conda-forge/label/cf201901" pyvisa
# install PyHegel
cd <PyHegel dir>
pip install .
```
Then clone this repo and run `HegelLab.py`

