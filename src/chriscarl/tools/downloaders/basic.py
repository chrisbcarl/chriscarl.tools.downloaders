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
    2026-01-07 - tools.downloaders.basic - initial commit, FEATURE: dl-basic
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
from chriscarl.core.lib.stdlib.urllib import WEB_FILENAME_EXTENSIONS, download, download_pool, get_basename
from chriscarl.core.functors.parse.html import html_to_dom

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
DEFAULT_OUTPUT_DIRPATH = abspath(TEMP_DIRPATH, 'tools.downloaders.basic')
DEFAULT_LOG_FILEPATH = abspath(TEMP_DIRPATH, 'tools.downloaders.basic.log')

# tool constants
EMAIL_REGEX = re.compile(r'([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]{2,4})')  # https://emailregex.com/#google_vignette



def url_walk_files_and_links(url, is_a='link', skip_sleep=False, bidirectional=False, skip_page=False):
    # type: (str, str, bool, bool, bool) -> Tuple[List[str], List[str]]
    original_url = url
    LOGGER.debug('%s', url)
    link_urls = []
    file_urls = []

    parsed = urlparse(url)
    hostname = parsed.hostname or ''

    try:
        downloaded_filepath, url = download(url, '/temp', is_a=is_a, skip_exist=False, skip_sleep=skip_sleep)
        if url != original_url:
            LOGGER.debug('requested %s changed to %s on download...', original_url, url)
    except urllib.error.HTTPError:
        LOGGER.warning('download failed on %s', url)
        LOGGER.debug('download failed on %s', url, exc_info=True)
        return file_urls, link_urls

    try:
        dom = html_to_dom(downloaded_filepath)
    except UnicodeDecodeError:
        LOGGER.warning('%s downloaded to "%s" is probably a binary file, ending walk')
        return file_urls, link_urls
    finally:
        os.remove(downloaded_filepath)

    if not skip_page:
        file_urls.append(url)
    logically_the_same_place = urljoin(url, '.')
    logically_above = urljoin(url, '..')

    anchors = dom.get_elements_by_tag('a')
    for anchor in anchors:
        orig_href = anchor.attrs.get('href')
        if not orig_href:
            continue

        href = urljoin(url, orig_href)
        logical = href.split('?')[0]

        if EMAIL_REGEX.search(logical):
            # things like mailto:
            continue

        ext = os.path.splitext(urlparse(href).path)[-1]
        if ext and ext not in WEB_FILENAME_EXTENSIONS:
            file_urls.append(href)
        else:
            if logical == logically_the_same_place:
                continue
            if not bidirectional and logical == logically_above:
                continue

            if hostname in href:
                link_urls.append(href)

    if bidirectional:
        link_urls.append(logically_above)

    LOGGER.debug('%s came away with %d files and %s other links', url, len(file_urls), len(link_urls))
    return file_urls, link_urls


def domain_walk_find_files(url, is_a='link', skip_sleep=False, bidirectional=False, skip_page=False):
    # type: (str, str, bool, bool, bool) -> Generator[str, None, None]
    max_queue_size = -1
    processed = 0
    files = 0
    queue = [url]

    visited_links = set()
    visited_files = set()

    # # this would cause every invocation to start from the top... dont bother
    # parsed = urlparse(url)
    # root = f'{parsed.scheme}://{parsed.hostname}'
    # queue.insert(0, root)

    while queue:
        max_queue_size = max([max_queue_size, len(queue)])

        url = queue.pop(0)
        processed += 1
        if processed % 10 == 0:
            LOGGER.info('url walk queue: %d / %d, %0.2f%% done, %d files discovered', processed, max_queue_size, processed / max_queue_size * 100, files)
        if url in visited_links:
            continue

        visited_links.add(url)
        file_urls, link_urls = url_walk_files_and_links(url, is_a=is_a, skip_sleep=skip_sleep, bidirectional=bidirectional, skip_page=skip_page)
        is_a = 'unknown'  # we know the first is probably a link
        queue += link_urls
        for file_url in file_urls:
            if file_url not in visited_files:
                yield file_url
                visited_files.add(file_url)
                files += 1


@dataclass
class Arguments:
    '''
    Document this class with any specifics for the process function.
    '''
    urls: List[str] = field(default_factory=lambda: [])
    output_dirpath: str = DEFAULT_OUTPUT_DIRPATH
    recurse: bool = False
    bidirectional: bool = False
    flat: bool = False
    skip_exist: bool = False
    skip_sleep: bool =False
    skip_page: bool =False
    debug: bool = False
    log_level: str = 'INFO'
    log_filepath: str = DEFAULT_LOG_FILEPATH

    @staticmethod
    def argparser():
        # type: () -> ArgumentParser
        parser = ArgumentParser(prog=SCRIPT_NAME, description=__doc__, formatter_class=ArgparseNiceFormat)
        app = parser.add_argument_group('app')
        app.add_argument('urls', type=str, nargs='+', help='which urls do you want to download?')
        app.add_argument('--output-dirpath', '-o', type=str, default=DEFAULT_OUTPUT_DIRPATH, help='where do you want to download?')
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


def basic(
    urls,
    output_dirpath=DEFAULT_OUTPUT_DIRPATH,
    recurse=False,
    bidirectional=False,
    flat=False,
    skip_exist=False,
    skip_sleep=False,
    skip_page=False,
    **kwargs
):
    # type: (List[str], str, bool, bool, bool, bool, bool, bool, dict) -> None
    batch_urls = []
    for u, url in enumerate(urls):
        href = urlparse(url)
        logical = href.path.split('?')[0]
        ext = os.path.splitext(logical)[-1]
        if ext and ext not in WEB_FILENAME_EXTENSIONS:
            LOGGER.info('%02d / %02d - %s - file download', u + 1, len(urls), url)
            download(url, output_dirpath, is_a='file', flat=True, skip_exist=skip_exist, skip_sleep=True)
        else:
            LOGGER.info('%02d / %02d - %s - %s walk', u + 1, len(urls), url, 'domain' if recurse else 'url')
            if recurse:
                batch_urls.extend(list(domain_walk_find_files(url, is_a='link', skip_sleep=skip_sleep, skip_page=skip_page)))
            else:
                file_urls, _ = url_walk_files_and_links(url, is_a='link', skip_sleep=skip_sleep, bidirectional=bidirectional, skip_page=skip_page)
                batch_urls.extend(file_urls)

    if batch_urls:
        LOGGER.info('discovered %d urls from the original %d, downloading all...', len(batch_urls), len(urls))
        results, failures = download_pool(batch_urls, dirpath=output_dirpath, flat=flat, skip_exist=skip_exist, skip_sleep=skip_sleep)
        LOGGER.info('downloaded %d files to "%s", %d failures!', len(results), output_dirpath, failures)

    LOGGER.info('done')


def main():
    # type: () -> int
    parser = Arguments.argparser()
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)

    args = Arguments.parse(parser=parser)
    basic(
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
