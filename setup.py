#!/usr/bin/env python

from distutils.core import setup

setup(name='fantasyfootball',
      version='0.2',
      description='A fantasy football python wrapper, data via scraping',
      author='@loisaidasam',
      url='https://github.com/loisaidasam/fantasyfootball',
      packages=['fantasyfootball'],
      requires=['requests', 'beautifulsoup4', 'lxml'])
