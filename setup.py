#!/usr/bin/env python
from setuptools import setup, find_packages

with open("README.md", "r", encoding='utf-8') as fh:
    long_description = fh.read()

setup(
    name="deployfish",
    version="1.10.0",
    description="AWS ECS related deployment tools",
    author="Caltech IMSS ADS",
    author_email="imss-ads-staff@caltech.edu",
    url="https://github.com/caltechads/deployfish",
    long_description=long_description,
    long_description_content_type="text/markdown",
    keywords=['aws', 'ecs', 'docker', 'devops'],
    classifiers=[
       "Programming Language :: Python :: 3"
    ],
    packages=find_packages(),
    include_package_data=True,
    package_data={'deployfish': ["py.typed"]},
    install_requires=[
        "boto3 >= 1.17",
        "cement>=3.0.0",
        "click >= 6.7",
        "colorlog",
        "jinja2 >= 2.11",
        "jsondiff2 >= 1.2.3",
        "pytz",
        "PyYAML >= 5.1",
        "requests >= 2.18.4",
        "shellescape >= 3.8.1",
        "tabulate >= 0.8.1",
        "typing_extensions",
        "tzlocal >= 4.0.1",
    ],
    entry_points={'console_scripts': [
        'deploy = deployfish.main:main',
        'dpy = deployfish.main:main'
    ]}
)
