#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Author:         Chris Carl
Email:          chrisbcarl@outlook.com
Date:           2026-01-07
Description:

tools.downloaders.basic is a tool which you can point it to a URL and it does basic scraping for anything that looks like a file

Examples:
    # individual files by url, probably most common usage
        dl-basic https://archive.org/download/constitution00unit/constitution00unit_djvu.txt `
            https://upload.wikimedia.org/wikipedia/commons/thumb/e/ec/Mona_Lisa%2C_by_Leonardo_da_Vinci%2C_from_C2RMF_retouched.jpg/960px-Mona_Lisa%2C_by_Leonardo_da_Vinci%2C_from_C2RMF_retouched.jpg

    # scan a website for links, grab them up
        dl-basic https://www.marxists.org/archive/marx/works/download/index.htm

    # if you want more output text cause you're impatient
        dl-basic https://codex.cs.yale.edu/avi/os-book/OS10/practice-exercises/index-solu.html --debug

    # recurse downward
        dl-basic http://security.ubuntu.com/ubuntu/project/ --recurse

    # recurse downward AND upward
        dl-basic https://codex.cs.yale.edu/avi/os-book/OS10/practice-exercises/index-solu.html --recurse --bidirectional

    # if no anti-DDOS auto-timeout prevention
        dl-basic https://tgftp.nws.noaa.gov/data/forecasts/area/ --recurse --skip-sleep

    # files are linked all over the place, the filename is the only important one
        dl-basic https://pypi.org/simple/six/ --flat --output-dirpath ~/downloads/six

Updates:
    2026-01-19 - tools.downloaders.basic - re-orged into the shed
    2026-01-07 - tools.downloaders.basic - initial commit, # FEATURE: tool-dl-basic
'''

# stdlib imports
from __future__ import absolute_import, print_function, division, with_statement  # , unicode_literals
import os
import sys
import logging
import re
import urllib.error
from urllib.parse import urljoin, urlparse
from typing import List, Tuple, Generator, Optional
from dataclasses import dataclass, field
from argparse import ArgumentParser

# third party imports

# project imports
from chriscarl.core.constants import TEMP_DIRPATH
from chriscarl.core.lib.stdlib.logging import NAME_TO_LEVEL, configure_ez, DEFAULT_LOG_LEVEL
from chriscarl.core.lib.stdlib.argparse import ArgparseNiceFormat
from chriscarl.core.lib.stdlib.os import abspath, make_dirpath
from chriscarl.tools.shed.downloaders import basic as basic_lib

SCRIPT_RELPATH = 'chriscarl/tools/downloaders/basic.py'
if not hasattr(sys, '_MEIPASS'):
    SCRIPT_FILEPATH = os.path.abspath(__file__)
else:
    SCRIPT_FILEPATH = os.path.abspath(os.path.join(sys._MEIPASS, SCRIPT_RELPATH))  # pylint: disable=no-member
SCRIPT_DIRPATH = os.path.dirname(SCRIPT_FILEPATH)
SCRIPT_NAME = os.path.splitext(os.path.basename(__file__))[0]
THIS_MODULE = sys.modules[__name__]
LOGGER = logging.getLogger(__name__)
LOGGER.addHandler(logging.NullHandler())

# argument defaults
DEFAULT_FIB_INIT = [0, 1]
DEFAULT_LOG_FILEPATH = abspath(TEMP_DIRPATH, 'tools.downloaders.basic.log')

# tool constants


@dataclass
class Arguments:
    '''
    Document this class with any specifics for the process function.
    '''
    urls: List[str] = field(default_factory=lambda: [])
    output_dirpath: str = basic_lib.DEFAULT_OUTPUT_DIRPATH
    recurse: bool = False
    bidirectional: bool = False
    flat: bool = False
    skip_exist: bool = False
    skip_sleep: bool = False
    skip_page: bool = False
    debug: bool = False
    log_level: str = 'INFO'
    log_filepath: str = DEFAULT_LOG_FILEPATH

    @staticmethod
    def argparser():
        # type: () -> ArgumentParser
        parser = ArgumentParser(prog=SCRIPT_NAME, description=__doc__, formatter_class=ArgparseNiceFormat)
        app = parser.add_argument_group('app')
        app.add_argument('urls', type=str, nargs='+', help='which urls do you want to download?')
        app.add_argument('--output-dirpath', '-o', type=str, default=basic_lib.DEFAULT_OUTPUT_DIRPATH, help='where do you want to download?')
        app.add_argument('--recurse', action='store_true', help='walk all over the domain, looking for files (downward by default)')
        app.add_argument('--bidirectional', action='store_true', help='recurse downward and upward')
        app.add_argument('--flat', action='store_true', help='save files according to basename only, not according to url path as directories')
        app.add_argument('--skip-exist', action='store_true', help='if the file exists, skip it')
        app.add_argument('--skip-sleep', action='store_true', help='skip sleeping in between everything? very rude--anti DDOS likely to ensue...')
        app.add_argument('--skip-page', action='store_true', help='skip retaining the downloaded html page')

        misc = parser.add_argument_group('misc')
        misc.add_argument('--debug', action='store_true', help='chose to print debug info')
        misc.add_argument('--log-level', type=str, default='INFO', choices=NAME_TO_LEVEL, help='log level?')
        misc.add_argument('--log-filepath', type=str, default=DEFAULT_LOG_FILEPATH, help='log filepath?')
        return parser

    def process(self):
        make_dirpath(self.output_dirpath)
        if self.debug:
            self.log_level = 'DEBUG'
        configure_ez(level=self.log_level, filepath=self.log_filepath)

    @staticmethod
    def parse(parser=None, argv=None):
        # type: (Optional[ArgumentParser], Optional[List[str]]) -> Arguments
        parser = parser or Arguments.argparser()
        ns = parser.parse_args(argv)
        arguments = Arguments(**(vars(ns)))
        arguments.process()
        return arguments


def main():
    # type: () -> int
    parser = Arguments.argparser()
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)

    args = Arguments.parse(parser=parser)
    basic_lib.basic(
        args.urls,
        output_dirpath=args.output_dirpath,
        recurse=args.recurse,
        bidirectional=args.bidirectional,
        flat=args.flat,
        skip_exist=args.skip_exist,
        skip_sleep=args.skip_sleep,
        skip_page=args.skip_page,
    )

    return 0


if __name__ == '__main__':
    sys.exit(main())
