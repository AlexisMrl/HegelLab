My attempt at building an interface for pyHegel.
This is highly inspired by Labber and VsdVg (the original interface on top of pyHegel).

Reusing from VsdVg:
- start_qt_app, sliderVert, matplotlibfig and Display window

The objective is to make it as modular and versatile as possible.
Main feature:
- load 'any' instrument from pyHegel (with minimal prior work)
- define your custom devices
- save your whole experience to a file

