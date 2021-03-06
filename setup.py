#!/usr/bin/env python
# vim: set fileencoding=utf-8 :

from setuptools import setup, find_packages

setup(

    name='baker',
    version='1.5.0',
    description="Utilities for backing-up my QNAP on BackBlaze's B2",
    url='https://github.com/anjos/baker',
    license="GPLv3",
    author='Andre Anjos',
    author_email='andre.dos.anjos@gmail.com',
    long_description=open('README.rst').read(),

    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,

    install_requires=[
      'setuptools',
      'b2',
      'docopt',
      'jinja2',
      'schedule',
      'requests',
      ],

    entry_points = {
      'console_scripts': [
        'bake = baker.bake:main',
        'deploy = baker.deploy:main',
        'logs = baker.logs:main',
        'remove-test-buckets = baker.remove_test_buckets:main',
      ],
    },

    classifiers = [
      'Development Status :: 4 - Beta',
      'Intended Audience :: Developers',
      'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
      'Natural Language :: English',
      'Programming Language :: Python',
      'Programming Language :: Python :: 3',
    ],

)
