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
