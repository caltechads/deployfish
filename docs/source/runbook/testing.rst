.. _testing:

Testing
=======

To run the unittests, you'll need to set up a virtualenv and install the requirements.

If you haven't yet, install:

* `pyenv`_
* `pyenv-virtualenv`_

Deployfish can support python 3.7 and above.

.. code-block:: shell

    $ pyenv install 3.11.9

Set up a virtualenv and install the requirements:

.. code-block:: shell

    $ pyenv virtualenv 3.11.9 deployfish
    $ pyenv local deployfish
    $ pip install --upgrade pip wheel
    $ pip install -r requirements.txt

Run all the tests:

.. code-block:: bash

    $ python -m unittest discover

For specific tests, checkout your options with: ``python -m unittest --help``


.. _`pyenv`: https://github.com/pyenv/pyenv
.. _`pyenv-virtualenv`: https://github.com/pyenv/pyenv-virtualenv
