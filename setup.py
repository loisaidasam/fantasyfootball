#!/usr/bin/env python

from distutils.core import setup

setup(name='fantasyfootball',
      version='0.1',
      description='A fantasy football python wrapper, with data sourced by API + scraping',
      author='@loisaidasam',
      url='https://github.com/loisaidasam/fantasyfootball',
      packages=['fantasyfootball'],
      requires=['requests', 'beautifulsoup4', 'lxml', 'git+git://github.com/loisaidasam/holycow.git'],
)
