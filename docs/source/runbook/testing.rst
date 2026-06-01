.. _testing:

Testing
=======

Deployfish uses ``pytest`` for its test suite. Tests live in the top-level ``tests/`` directory.

Set up a virtual environment and install dependencies:

.. code-block:: shell

    $ uv sync
    $ source .venv/bin/activate

Run all tests:

.. code-block:: bash

    $ .venv/bin/pytest

Or use the Makefile target:

.. code-block:: bash

    $ make test

Run tests with coverage:

.. code-block:: bash

    $ make cov

Coverage is enforced in CI via ``pyproject.toml`` (``[tool.coverage.report] fail_under = 80``). The suite must stay at or above **80%** line coverage on ``deployfish/``.

Run a specific test file or test:

.. code-block:: bash

    $ .venv/bin/pytest tests/test_Config.py
    $ .venv/bin/pytest tests/test_Config.py::TestContainerDefinition_load_yaml -k load_yaml
