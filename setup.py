__version__ = '0.1.0'

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

tests_require = []
if py_version < (3, 3):
    tests_require.append('mock')

here = os.path.abspath(os.path.dirname(__file__))

DESC = """\
supervisor_loader is an RPC extension for Supervisor that allows
for dynamically injecting supervisor program configurations at runtime.
"""

CLASSIFIERS = [
    'Development Status :: 5 - Production/Stable',
    'Environment :: No Input/Output (Daemon)',
    'Intended Audience :: System Administrators',
    'License :: OSI Approved :: BSD License',
    'Natural Language :: English',
    'Operating System :: POSIX',
    'Programming Language :: Python :: 2',
    'Programming Language :: Python :: 2.6',
    'Programming Language :: Python :: 2.7',
    'Programming Language :: Python :: 3',
    'Programming Language :: Python :: 3.2',
    'Programming Language :: Python :: 3.3',
    'Programming Language :: Python :: 3.4',
    'Topic :: System :: Boot',
    'Topic :: System :: Systems Administration',
    ]

setup(
    name = 'supervisor_loader',
    version = __version__,
    license = 'License :: OSI Approved :: BSD License',
    url = 'http://github.com/taylor-jones/supervisor_loader',
    description = "supervisor_loader RPC extension for Supervisor",
    long_description= DESC,
    classifiers = CLASSIFIERS,
    author = "Taylor Jones",
    author_email = "taylorjonesdev@gmail.com",
    maintainer = "Taylor Jones",
    maintainer_email = "taylorjonesdev@gmail.com",
    packages = find_packages(),
    install_requires = ['supervisor >= 3.0a10'],
    tests_require = tests_require,
    include_package_data = True,
    zip_safe = False,
    namespace_packages = ['supervisor_loader'],
    test_suite = 'supervisor_loader.tests',
)