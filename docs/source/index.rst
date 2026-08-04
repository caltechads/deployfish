.. deployfish documentation master file, created by
   sphinx-quickstart on Tue Jun 13 16:54:27 2017.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

============
Deployfish
============

.. include:: quickintro.rst

.. toctree::
   :maxdepth: 1
   :hidden:
   :caption: User Guide

   intro
   install
   tutorials
   plugins/plugins
   yaml

.. toctree::
   :hidden:
   :caption: Developer Guide

   runbook/contributing
   runbook/architecture
   runbook/adapters
   runbook/extending
   runbook/testing

.. toctree::
   :hidden:
   :caption: Rebuild Architecture Specs

   architecture/context
   architecture/00-overview
   architecture/01-configuration-model
   architecture/02-ecs-cluster
   architecture/03-ecs-service-lifecycle
   architecture/04-standalone-tasks
   architecture/05-secrets-management
   architecture/06-remote-access
   architecture/07-observability
   architecture/08-supporting-infra
   architecture/09-extensibility

.. toctree::
   :hidden:
   :caption: Reference

   api/main
   api/config/index
   api/controllers/index
   api/loaders
   api/adapters/index
   api/models/index
   api/renderers

..
   Indices and tables
   ==================

   * :ref:`genindex`
   * :ref:`modindex`
   * :ref:`search`
