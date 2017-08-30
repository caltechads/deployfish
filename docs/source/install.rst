************
Installation
************

deployfish is a pure python package.  As such, it can be installed in the
usual python ways.  For the following instructions, either install it into your
global python install, or use a python `virtual environment <https://python-guide-pt-br.readthedocs.io/en/latest/dev/virtualenvs/>`_ to install it
without polluting your global python environment.

Install via pip
===============

::

    pip install deployfish


Install via `setup.py`
======================

Clone or download from `Github <https://github.com/caltechads/deployfish>`_.

::

    cd deployfish-0.15.6
    python setup.py install


Using pyenv to install into a virtual environment
=================================================

(Recommended for Python programming)

If you use python and frequently need to install additional python modules,
`pyenv <https://github.com/pyenv/pyenv>`_ and `pyenv-virtualenv <https://github.com/pyenv/pyenv-virtualenv>`_
are extremely useful.  They allow some very useful things:

* Manage your virtualenvs easily on a per-project basis
* Provide support for per-project Python versions.

