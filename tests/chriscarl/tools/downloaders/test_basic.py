#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Author:         Chris Carl
Email:          chrisbcarl@outlook.com
Date:           2026-01-07
Description:

chriscarl.tools.downloaders.basic unit test.
NOTE:
    - big thanks to pypi and NOAA

Updates:
    2026-01-07 - tests.chriscarl.tools.downloaders.basic - initial commit
'''

# stdlib imports (expected to work)
from __future__ import absolute_import, print_function, division, with_statement  # , unicode_literals
import os
import sys
import logging
import unittest
import shutil
import tempfile

# third party imports

# project imports (expected to work)
from chriscarl.core.constants import TEST_COLLATERAL_DIRPATH
from chriscarl.core.lib.stdlib.os import abspath
from chriscarl.core.lib.stdlib.unittest import UnitTest

# test imports
import chriscarl.tools.downloaders.basic as lib

SCRIPT_RELPATH = 'tests/chriscarl/tools/downloaders/test_basic.py'
if not hasattr(sys, '_MEIPASS'):
    SCRIPT_FILEPATH = os.path.abspath(__file__)
else:
    SCRIPT_FILEPATH = os.path.abspath(os.path.join(sys._MEIPASS, SCRIPT_RELPATH))  # pylint: disable=no-member
SCRIPT_DIRPATH = os.path.dirname(SCRIPT_FILEPATH)
SCRIPT_NAME = os.path.splitext(os.path.basename(__file__))[0]
THIS_MODULE = sys.modules[__name__]
LOGGER = logging.getLogger(__name__)
LOGGER.addHandler(logging.NullHandler())


class TestCase(UnitTest):

    def setUp(self):
        self.output_dirpath = tempfile.mkdtemp()
        return super().setUp()

    def tearDown(self):
        shutil.rmtree(self.output_dirpath)
        return super().tearDown()

    # @unittest.skip('lorem ipsum')
    def test_case_0_simp(self):
        url = 'https://pypi.org/simple/six/'
        # dl-basic https://pypi.org/simple/six/ --flat
        args = lib.Arguments.parse(argv=[url, '--flat', '--output-dirpath', self.output_dirpath, '--skip-page'])
        variables = [
            (
                lib.basic,
                (args.urls,),
                dict(
                    output_dirpath=args.output_dirpath,
                    recurse=args.recurse,
                    bidirectional=args.bidirectional,
                    flat=args.flat,
                    skip_exist=args.skip_exist,
                    skip_sleep=args.skip_sleep,
                    skip_page=args.skip_page
                )
            ),
        ]
        controls = [
            None,
        ]
        self.assert_null_hypothesis(variables, controls)

    def test_case_1_noaa(self):
        # TODO: --bidirectional is missing, gonna be hard to find a good one...
        # NOTE: GOD BLESS THE NATIONAL OCEANIC AND ATMOSPHERIC ADMINISTRATION
        url = 'https://tgftp.nws.noaa.gov/data/forecasts/area/'
        # dl-basic https://tgftp.nws.noaa.gov/data/forecasts/area/ --recurse --skip-sleep --log-level DEBUG
        args = lib.Arguments.parse(argv=[url, '--recurse', '--log-level', 'DEBUG', '--skip-sleep', '--debug', '--log-filepath', abspath(self.output_dirpath, 'log.txt')])
        variables = [
            (
                lib.basic,
                (args.urls,),
                dict(
                    output_dirpath=args.output_dirpath,
                    recurse=args.recurse,
                    bidirectional=args.bidirectional,
                    flat=args.flat,
                    skip_exist=args.skip_exist,
                    skip_sleep=args.skip_sleep,
                    skip_page=args.skip_page
                )
            ),
        ]
        controls = [
            None,
        ]
        self.assert_null_hypothesis(variables, controls)


if __name__ == '__main__':
    tc = TestCase()
    tc.setUp()

    tc.test_case_0_simp()
    tc.test_case_1_noaa()

    tc.tearDown()
