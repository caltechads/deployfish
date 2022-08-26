************
Installation
************

deployfish is a pure python package.  As such, it can be installed in the
usual python ways.  For the following instructions, either install it into your
global python install, or use a python `virtual environment <https://python-guide-pt-br.readthedocs.io/en/latest/dev/virtualenvs/>`_ to install it
without polluting your global python environment.

Install deployfish
==================

::

    pip install deployfish


Install AWS CLI v2
==================

deployfish requries AWS CLI v2 for some of its functionality, notably EXEC'ing into FARGATE containers.  While AWS CLI v1
was installable via `pip`, AWS CLI v2 is not, so we have to do the install manually.  Here's how to set that up on a Mac::

    # Uninstall any old versions of the cli
    pip uninstall awscli

    # Deactivate any pyenv environment so we can be in the system-wide Python interpreter
    cd ~

    # Install the new AWS CLI from brew -- it's no longer pip installable
    brew update
    brew install awscli

    # Install the Session Manager plugin
    curl "https://s3.amazonaws.com/session-manager-downloads/plugin/latest/mac/sessionmanager-bundle.zip" -o "sessionmanager-bundle.zip"
    unzip sessionmanager-bundle.zip
    sudo ./sessionmanager-bundle/install -i /usr/local/sessionmanagerplugin -b /usr/local/bin/session-manager-plugin


If later on you have issues with EXEC'ing or with the `aws` command in general, check to ensure you're getting your
global v2 version of `aws` instead of an old v1 one from your current virtual environment::

    aws --version

If the version string shows version < 2::

    pip uninstall awscli
