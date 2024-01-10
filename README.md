![HegelLab](./resources/logo_white.png#gh-dark-mode-only)
![HegelLab](./resources/logo_black.png#gh-light-mode-only)

# HegelLab
My attempt at building an interface for pyHegel.

This is highly inspired by Labber and VsdVg (the original interface on top of pyHegel).
It is intended to be more structured than the original VsdVg, so adding feature should be easier.

Main features:
- load 'any' instrument from pyHegel,
- edit devices (scale, ramp, limit),
- save and load instruments and custom devices,
- responsive live display,
- live monitor.

Missing for now:
- virtual gates / feedback loop,
- no support for multi output devices.


Note: live view for higher than two swept devices not supported.

# Shortcuts

| Global |   |
|---|---|
| j | down  |
| k | up  |
| l | unfold tree item  |
| k | fold tree item  |
| x | (in most places) remove item |
| w, i | show rack (instrument) window  |
| w, d | show display |
| w, m | show monitor |
| w, w | show main window  |
| t, o | focus out tree |
| t, s | focus sweep tree |
| t, g | focus log tree |
| w, q | close current window  |

| Rack |   |
|---|---|
| Shift+a | add instrument  |
| Shift+l | load instrument |
| Shift+e | edit instrument devices |
| Shift+x | remove instrument  |
| c | config device  |
| r | rename device  |
| m | toggle monitor device  |
| o | toggle out device  |
| g | toggle log device  |
| s | toggle sweep device  |
| Space | get value |
| Shift+Space  | set value  |

| Display |   |
|---|---|
| Space | add/remove fixed target  |

| Monitor |   |
|---|---|
| - | decrease interval  |
| + | increase instrument |
| left arrow | decrease history size |
| right arrow | increase history size |

# Packages
Need python in version `>=3.8`, an installation of PyHegel and the package `pyqtgraph` in version `>=0.12.3`.

# Installation (wip)

Installation procecure (the whole thing: python3, PyHegel and HegelLab):
```py
# conda create and install packages:
conda create -n py311 -c conda-forge python=3.11 ipython numpy scipy pyqt matplotlib pyserial pythonnet pypdf2 pytz pyqtgraph=0.13.1 pyvisa
conda activate py311
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
