# SPDX-License-Identifier: LGPL-2.1-or-later

from setuptools import setup
import os
from freecad.CurvesWB2.version import __version__
# name: this is the name of the distribution.
# Packages using the same name here cannot be installed together

version_path = os.path.join(os.path.abspath(os.path.dirname(__file__)),
                            "freecad", "CurvesWB2", "version.py")
with open(version_path) as fp:
    exec(fp.read())

setup(name='freecad.CurvesWB2',
      version=str(__version__),
      packages=['freecad',
                'freecad.CurvesWB2'],
      maintainer="Chris_G",
      maintainer_email="cg@grellier.fr",
      url="https://github.com/tomate44/CurvesWB",
      description="Additional tools to manipulate curves and surfaces in FreeCAD",
      install_requires=['numpy'],  # should be satisfied by FreeCAD's system dependencies already
      include_package_data=True)
