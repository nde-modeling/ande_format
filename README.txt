This repository contains information on the ANDE (advanced NDE)
file format.

A draft version of the specification(from the
ande_specification repository) is included in ande.pdf

A python module for reading the ANDE format is included
in advanced_nde.py

A multi-channel interactive viewer is included in the
SpatialNDE2 project as the ande_viewer application:
https://thermal.cnde.iastate.edu/spatialnde2.xhtml
https://github.com/isuthermography/spatialnde2

Example data files are included in example.ande and
SCANINFO_EG5_singleframe.ande.

You can try advanced_nde.py as a viewer by providing the
name of an example on the command line, e.g. 
     python advanced_nde.py example.ande
or from Spyder / Jupyter Qtconsole via:
     %run advanced_nde.py example.ande
(you may want to enable Qt mode via %matplotlib qt)

To explore the contents of the example files at a format
level, you can use HDF5 tools such as HDFView and h5dump.


