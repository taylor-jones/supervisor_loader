__version__ = '1.0'

import os
import sys
from setuptools import setup, find_packages

py_version = sys.version_info[:2]

if py_version < (2, 6):
    raise RuntimeError(
        'On Python 2, supervisor_loader requires Python 2.6 or later')
elif (3, 0) < py_version < (3, 2):
    raise RuntimeError(
        'On Python 3, supervisor_loader requires Python 3.2 or later')

setup(
    name = 'supervisor_loader',
    version = __version__,
    description = "supervisor_loader RPC extension for Supervisor",
    packages = find_packages(),
    install_requires = ['supervisor >= 3.1.4'],
    include_package_data = True,
    zip_safe = False,
    namespace_packages = ['supervisor_loader'],
    test_suite = 'supervisor_loader.tests'
)
