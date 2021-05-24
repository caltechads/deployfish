#!/usr/bin/env python
import os.path

from deployfish import __version__
from setuptools import setup, find_packages  # @UnresolvedImport

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(name="deployfish",
      version=__version__,
      description="AWS ECS related deployment tools",
      author="Caltech IMSS ADS",
      author_email="imss-ads-staff@caltech.edu",
      url="https://github.com/caltechads/deployfish",
      long_description=long_description,
      long_description_content_type="text/markdown",
      keywords=['aws', 'ecs', 'docker', 'devops'],
      classifiers=[
          "Programming Language :: Python :: 2.7",
          "Programming Language :: Python :: 3"
      ],
      packages=find_packages(),
      include_package_data=True,
      install_requires=[
          "boto3 >= 1.17",
          "click >= 6.7",
          "PyYAML >= 5.1",
          "tzlocal >= 1.4",
          "requests >= 2.18.4",
          "jsondiff2 >= 1.2.3",
          "inspect2 >= 0.1.2",
          "tabulate >= 0.8.1",
          "shellescape >= 3.8.1",
          "jinja2 >= 2.11"
      ],
      entry_points={'console_scripts': [
          'deploy = deployfish.main:main',
          'dpy = deployfish.main:main'
      ]}
      )
