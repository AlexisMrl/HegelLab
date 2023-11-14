My attempt at building an interface for pyHegel.

This is highly inspired by Labber and VsdVg (the original interface on top of pyHegel).

It is intended to be more structured than the original VsdVg, so adding feature should be easier.
Reusing from VsdVg:
- start_qt_app, sliderVert, matplotlibfig and Display window

The objective is to make it as modular and versatile as possible.
Main feature:
- load 'any' instrument from pyHegel (with minimal prior work)
- define your custom devices
- save and load your whole experience to a file (with custom devices)

Developed with pyHegel python 3 in mind.
In a pyHegel console, run HegelLab.py

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
