# PBS

PBS is an open source tool for the complementation of Buchi automata.

In its current form, it implements the PBS algorithm developed as a part of Mikuláš Klokočka's master's thesis.
Reference will be added after the text is published in the Masaryk University archive.

## Installation

The tool is written in Python 3.7 with the Python bindings of the Spot library (for installation and more information,
see https://spot.lrde.epita.fr/).

Besides satisfying those two requirements, there is no required installation.

## Usage

To run the tool, simply use

```
python complement/complement.py <file>
```

<file> stands for an automaton preferably in the HOA format (see http://adl.github.io/hoaf/ for more information).

There are several command-line arguments, for their list run

```
python complement/complement.py --help
```

## Experimental Evaluation

For the purposes of the master's thesis, experimental evaluation of the tool against a number of other tools was
carried out.

In this repository, you can find several Jupyter notebooks in the `experiments` directory. The notebook
[Evaluation](experiments/Evaluation.ipynb) will guide you through the steps used to generate the evaluation as presented
in my thesis. It compares the tool against, most notably, Spot's own complementation procedure, a chain run of Seminator
(see https://github.com/mklokocka/seminator) and NCSB algorithm as implemented in Spot, and also against Buchifier
(see https://publish.illinois.edu/buchifier/) and the GOAL tool suite with the Fribourg plugin
(see http://goal.im.ntu.edu.tw), if they are supplied.

If the preview of the notebooks on GitHub does not work, use Jupyter nbviewer instead.
