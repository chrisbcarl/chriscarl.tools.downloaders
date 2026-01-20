#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Author:         Chris Carl
Email:          chrisbcarl@outlook.com
Date:           2026-01-17
Description:

tools.shed.downloaders.basic is... TODO: lorem ipsum
tool are modules that define usually cli tools or mini applets that I or other people may find interesting or useful.

Updates:
    2026-01-17 - tools.shed.downloaders.basic - initial commit
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

# third party imports

# project imports
from chriscarl.core.constants import TEMP_DIRPATH
from chriscarl.core.lib.stdlib.logging import NAME_TO_LEVEL, configure_ez, DEFAULT_LOG_LEVEL
from chriscarl.core.lib.stdlib.argparse import ArgparseNiceFormat
from chriscarl.core.lib.stdlib.os import abspath, make_dirpath
from chriscarl.core.lib.stdlib.urllib import WEB_FILENAME_EXTENSIONS, download, download_pool, get_basename
from chriscarl.core.functors.parse.html import html_to_dom

SCRIPT_RELPATH = 'chriscarl/tools/shed/downloaders/basic.py'
if not hasattr(sys, '_MEIPASS'):
    SCRIPT_FILEPATH = os.path.abspath(__file__)
else:
    SCRIPT_FILEPATH = os.path.abspath(os.path.join(sys._MEIPASS, SCRIPT_RELPATH))  # pylint: disable=no-member
SCRIPT_DIRPATH = os.path.dirname(SCRIPT_FILEPATH)
SCRIPT_NAME = os.path.splitext(os.path.basename(__file__))[0]
THIS_MODULE = sys.modules[__name__]
LOGGER = logging.getLogger(__name__)
LOGGER.addHandler(logging.NullHandler())

EMAIL_REGEX = re.compile(r'([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]{2,4})')  # https://emailregex.com/#google_vignette
DEFAULT_OUTPUT_DIRPATH = abspath(TEMP_DIRPATH, 'tools.downloaders.basic')


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


def basic(urls, output_dirpath=DEFAULT_OUTPUT_DIRPATH, recurse=False, bidirectional=False, flat=False, skip_exist=False, skip_sleep=False, skip_page=False, **kwargs):
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
