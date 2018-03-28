#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''Tests for baker'''


import os
import nose.tools
import pkg_resources

import logging
logger = logging.getLogger(__name__)

from . import restic
from .utils import TemporaryDirectory


SAMPLE_DIR = pkg_resources.resource_filename(__name__, 'data')

def test_runner():

  out = restic.run_restic([], 'version', [], 'password')

  messages = out.split('\n')[:-1] #removes last end-of-line

  nose.tools.eq_(len(messages), 2)
  assert messages[0].startswith('restic') #restic 0.8.3
  assert messages[1].startswith('compiled with go')


def test_restic_init():

  with TemporaryDirectory() as d:
    out = restic.init(d, [], 'password')

  messages = out.split('\n')[:-1] #removes last end-of-line
  nose.tools.eq_(len(messages), 5)
  assert messages[0].startswith('created restic repository')
  assert messages[0].endswith(d)


def test_restic_backup():

  with TemporaryDirectory() as d:
    restic.init(d, [], 'password')
    out = restic.backup(SAMPLE_DIR, d, [], 'hostname', [], 'password')

  messages = out.split('\n')[:-1] #removes last end-of-line
  nose.tools.eq_(len(messages), 7)
  assert messages[0] == ('scan [%s]' % SAMPLE_DIR)
  assert messages[-1].startswith('snapshot')
  assert messages[-1].endswith('saved')


def test_restic_snapshots():

  with TemporaryDirectory() as d:
    restic.init(d, [], 'password')
    restic.backup(SAMPLE_DIR, d, [], 'hostname', [], 'password')
    data = restic.snapshots(d, ['--json'], 'hostname', 'password')

  # data is a list of dictionaries with the following fields
  #   * time: The time the snapshot was taken
  #   * tree: The snapshot tree identifier?
  #   * paths: List of paths backed-up on that snapshot
  #   * hostname: The name of the host
  #   * username: The user identifier of the user that made the snapshot
  #   * uid: The user id for the snapshot file
  #   * gid: The groud id for snapshot file
  #   * id: The snapshot identifier
  #   * short_id: A shortened version of ``id``
  nose.tools.eq_(len(data), 1)
  nose.tools.eq_(data[0]['paths'], [SAMPLE_DIR])
