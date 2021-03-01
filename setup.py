"""Setup file for aecg package: tools for annotated ECG HL7 XML files.

**Authors**

***Jose Vicente Ruiz*** <jose.vicenteruiz@fda.hhs.gov>

    Division of Cardiology and Nephrology
    Office of Cardiology, Hematology, Endocrinology and Nephrology
    Office of New Drugs
    Center for Drug Evaluation and Research
    U.S. Food and Drug Administration


* LICENSE *
===========
This code is in the public domain within the United States, and copyright and
related rights in the work worldwide are waived through the CC0 1.0 Universal
Public Domain Dedication. This example is distributed in the hope that it will
be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See DISCLAIMER section
below, the COPYING file in the root directory of this project and
https://creativecommons.org/publicdomain/zero/1.0/ for more details.

* Disclaimer *
==============
FDA assumes no responsibility whatsoever for use by other parties of the
Software, its source code, documentation or compiled executables, and makes no
guarantees, expressed or implied, about its quality, reliability, or any other
characteristic. Further, FDA makes no representations that the use of the
Software will not infringe any patent or proprietary rights of third parties.
The use of this code in no way implies endorsement by the FDA or confers any
advantage in regulatory decisions.

"""


from setuptools import setup, find_packages

import codecs
import os
import pathlib


setup_path = pathlib.Path(__file__).parent.resolve()
long_description = (setup_path / 'README.md').read_text(encoding='utf-8')
history_log = (setup_path / 'HISTORY.md').read_text(encoding='utf-8')


def read(rel_path):
    here = os.path.abspath(os.path.dirname(__file__))
    with codecs.open(os.path.join(here, rel_path), 'r') as fp:
        return fp.read()


def get_version(rel_path):
    for line in read(rel_path).splitlines():
        if line.startswith('__version__'):
            delim = '"' if '"' in line else "'"
            return line.split(delim)[1]
    else:
        raise RuntimeError("Unable to find version string.")


setup(name="aecg",
      version=get_version("src/aecg/__init__.py"),
      description="Validation and reader tools for annotated "
                  "electrocardiograms (aECG) in HL7 xml format",
      long_description=long_description + history_log,
      long_description_content_type="text/markdown",

      url='https://github.com/FDA/aecg-python',

      author="Jose Vicente Ruiz",
      author_email="jose.vicenteruiz@fda.hhs.gov",

      keywords='fda, aecg, ecg, hl7, xml, qt',

      package_dir={'': 'src'},
      packages=find_packages(where='src'),

      license="CC0",

      install_requires=["lxml==4.5.1",
                        "matplotlib==3.2.2",
                        "numpy==1.18.5",
                        "openpyxl==3.0.5",
                        "pandas==1.0.5",
                        "pytest==5.4.3",
                        "scipy==1.4.1",
                        "tqdm==4.46.1"],

      package_data={"aecg": [
          "cfg/aecg_logging.conf",
          "aecg/data/*",
          "aecg/resources/*"]},
      include_package_data=True,

      entry_points={
          'console_scripts': [
              'aecg = aecg.tools.aecg_cli:main'
              ]},

      project_urls={
          'Bug Reports': 'https://github.com/FDA/aecg-python/issues',
          'Source': 'https://github.com/FDA/aecg-python',
          },

      python_requires='>=3.7.7',)
