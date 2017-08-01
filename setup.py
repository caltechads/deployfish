#!/usr/bin/env python
from deployfish import __version__
from setuptools import setup, find_packages  # @UnresolvedImport


setup(name="deployfish",
      version=__version__,
      description="ECS related deployment tools",
      author="IMSS ADS",
      author_email="imss-ads-staff@caltech.edu",
      url="https://github.com/caltechads/deployfish",
      download_url='https://github.com/caltechads/deployfish/archive/%s.tar.gz' % __version__,
      keywords=['aws', 'ecs', 'docker', 'devops'],
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
