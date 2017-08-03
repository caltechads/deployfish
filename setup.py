#!/usr/bin/env python
from deployfish import __version__
from setuptools import setup, find_packages  # @UnresolvedImport

intro = open('docs/source/intro.rst').read()

setup(name="deployfish",
      version=__version__,
      description="AWS ECS related deployment tools",
      author="IMSS ADS",
      author_email="imss-ads-staff@caltech.edu",
      url="https://github.com/caltechads/deployfish",
      long_description=intro,
      keywords=['aws', 'ecs', 'docker', 'devops'],
      classifiers = [
          "Programming Language :: Python :: 2.7",
          "Programming Language :: Python :: 3"
      ],
      packages=find_packages(),
      include_package_data=True,
      install_requires=[
          "boto3 >= 1.4.4",
          "click >= 6.7",
          "PyYAML == 3.12",
          "tzlocal == 1.4"
      ],
      entry_points={'console_scripts': [
          'deploy = deployfish.dplycli:main',
          'dpy = deployfish.dplycli:main'
      ]}
      )
